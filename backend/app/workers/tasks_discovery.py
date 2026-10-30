"""VIXOR �?" Discovery Celery tasks (T-025).

Chains subfinder → CT logs → DNS enumeration → httpx probe to discover
assets for a domain. Results are stored as Asset records with scope_guard
enforcement. Partial failures are handled gracefully.
"""

import json
from datetime import UTC, datetime
from typing import Any

from app.core.logging import get_logger
from app.deps import get_session_factory
from app.models.asset import Asset, ScopeStatus
from app.models.domain import Domain, DomainStatus
from app.services.discovery.ct_logs import fetch_ct_subdomains
from app.services.discovery.dns_enum import enumerate_dns
from app.services.discovery.httpx_probe import probe_host
from app.services.discovery.subfinder import (
    filter_subdomains_by_scope,
    run_subfinder,
)
from app.services.scope_guard import is_in_scope
from app.workers.celery_app import celery_app

logger = get_logger("workers.discovery")


def _publish_progress(domain_id: str, event: dict[str, Any]) -> None:
    """Publish a discovery progress event to Redis pub/sub."""
    try:
        from app.redis import get_redis_client

        redis = get_redis_client()
        redis.publish(
            f"discovery:{domain_id}",
            json.dumps({"domain_id": domain_id, **event}),
        )
    except Exception:
        logger.exception("discovery_progress_publish_failed", domain_id=domain_id)


@celery_app.task(bind=True, name="app.workers.tasks_discovery.run_discovery")  # type: ignore[untyped-decorator]
def run_discovery(  # type: ignore[no-untyped-def]
    self, domain_id: str
) -> dict[str, Any]:
    """Run the discovery pipeline for a domain.

    Steps:
    1. subfinder - enumerate subdomains
    2. CT logs - enumerate more subdomains from crt.sh
    3. Deduplicate and filter by scope
    4. DNS enumeration - resolve A records, detect wildcard
    5. httpx probe - check liveness and technologies
    6. Store results as Asset records with scope_guard enforcement

    Handles partial failures: if one tool fails, continues with others.
    """
    db = get_session_factory()()
    try:
        domain = db.query(Domain).filter(Domain.id == domain_id).first()
        if not domain:
            logger.error("domain_not_found", domain_id=domain_id)
            return {"domain_id": domain_id, "error": "domain not found"}

        if domain.status != DomainStatus.verified:
            logger.warning(
                "domain_not_verified",
                domain_id=domain_id,
                status=domain.status.value,
            )
            return {
                "domain_id": domain_id,
                "error": f"domain not verified (status: {domain.status.value})",
            }

        domain_in_scope, scope_reason = is_in_scope(
            domain, domain.root_domain, resolve_dns=False
        )
        if not domain_in_scope:
            return {
                "domain_id": domain_id,
                "status": "failed",
                "error": scope_reason or "domain verification is stale",
            }

        root_domain = domain.root_domain

        _publish_progress(
            domain_id,
            {"status": "started", "root_domain": root_domain},
        )

        # Step 1: subfinder
        subfinder_subdomains: list[str] = []
        try:
            subfinder_subdomains = run_subfinder(root_domain)
            logger.info(
                "subfinder_complete",
                domain_id=domain_id,
                count=len(subfinder_subdomains),
            )
        except Exception as exc:  # noqa: BLE001 - intentional partial failure handling
            logger.warning("subfinder_failed", domain_id=domain_id, error=str(exc))

        # Step 2: CT logs
        ct_subdomains: list[str] = []
        try:
            ct_subdomains = fetch_ct_subdomains(root_domain)
            logger.info(
                "ct_logs_complete",
                domain_id=domain_id,
                count=len(ct_subdomains),
            )
        except Exception as exc:  # noqa: BLE001 - intentional partial failure handling
            logger.warning("ct_logs_failed", domain_id=domain_id, error=str(exc))

        # Step 3: Combine and deduplicate
        all_subdomains = list(dict.fromkeys(subfinder_subdomains + ct_subdomains))
        # Filter to only subdomains of the root domain
        scoped_subdomains = filter_subdomains_by_scope(all_subdomains, root_domain)

        logger.info(
            "discovery_combined",
            domain_id=domain_id,
            total=len(all_subdomains),
            scoped=len(scoped_subdomains),
        )

        _publish_progress(
            domain_id,
            {
                "status": "subdomains_found",
                "total": len(all_subdomains),
                "scoped": len(scoped_subdomains),
            },
        )

        # Step 4: DNS enumeration + wildcard detection
        dns_results = enumerate_dns(root_domain, scoped_subdomains)
        wildcard_detected = dns_results.pop("_wildcard_detected", False)

        logger.info(
            "dns_enum_complete",
            domain_id=domain_id,
            resolved=len(dns_results),
            wildcard=wildcard_detected,
        )

        # Step 5: httpx probe for live hosts
        assets_created = 0
        assets_updated = 0
        for hostname, ips in dns_results.items():
            try:
                # scope_guard enforcement
                in_scope, reason = is_in_scope(domain, hostname, resolve_dns=True)
                if not in_scope:
                    logger.warning(
                        "asset_out_of_scope",
                        domain_id=domain_id,
                        hostname=hostname,
                        reason=reason,
                    )
                    continue

                # httpx probe
                probe_result = probe_host(hostname)

                if not probe_result.get("live", False):
                    continue

                # Check if asset already exists
                existing = (
                    db.query(Asset)
                    .filter(
                        Asset.domain_id == domain_id,
                        Asset.hostname == hostname,
                    )
                    .first()
                )
                if existing:
                    # Update existing asset
                    existing.ips = ips
                    existing.is_live = True
                    existing.scope_status = ScopeStatus.in_scope
                    existing.scope_reason = None
                    existing.technologies = probe_result.get("technologies")
                    existing.last_seen = datetime.now(UTC)
                    assets_updated += 1
                else:
                    # Create new asset
                    asset = Asset(
                        domain_id=domain_id,
                        hostname=hostname,
                        ips=ips,
                        is_live=True,
                        scope_status=ScopeStatus.in_scope,
                        scope_reason=None,
                        technologies=probe_result.get("technologies"),
                    )
                    db.add(asset)
                    assets_created += 1

            except Exception as exc:
                logger.exception(
                    "asset_processing_failed",
                    domain_id=domain_id,
                    hostname=hostname,
                    error=str(exc),
                )
                continue

        db.commit()

        _publish_progress(
            domain_id,
            {
                "status": "completed",
                "assets_created": assets_created,
                "assets_updated": assets_updated,
                "wildcard_detected": wildcard_detected,
            },
        )

        return {
            "domain_id": domain_id,
            "root_domain": root_domain,
            "subdomains_found": len(scoped_subdomains),
            "assets_created": assets_created,
            "assets_updated": assets_updated,
            "wildcard_detected": wildcard_detected,
            "status": "completed",
        }
    except Exception as exc:
        logger.exception("discovery_failed", domain_id=domain_id, error=str(exc))
        return {"domain_id": domain_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()
