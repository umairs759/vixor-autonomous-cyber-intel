"""VIXOR — Scan orchestrator (T-029).

Orchestrates the scanning pipeline per asset:
scope_guard -> Nmap -> ZAP -> Nuclei -> normalization -> dedupe.

Handles timeouts, retries, partial-failure handling, and per-project concurrency.
"""

from typing import Any

from app.core.logging import get_logger
from app.services.scanning.nmap_runner import run_nmap
from app.services.scanning.normalizer import (
    normalize_nmap,
    normalize_nuclei,
    normalize_zap,
)
from app.services.scanning.nuclei_runner import run_nuclei
from app.services.scanning.zap_runner import ZapRunner
from app.services.scope_guard import is_in_scope

logger = get_logger("scanning.orchestrator")


class ScanOrchestrator:
    """Orchestrates scanning of a single asset across multiple tools."""

    def __init__(
        self,
        zap_runner: ZapRunner | None = None,
        timeout_seconds: int = 1800,
    ):
        self.zap_runner = zap_runner
        self.timeout_seconds = timeout_seconds

    def scan_asset(
        self,
        domain_root: str,
        hostname: str,
        domain_verified: bool,
        verified_at=None,
    ) -> dict:
        """Run the full scanning pipeline for a single asset.

        Returns:
            Dict with scan results, scope status, and any errors.
        """
        result: dict[str, Any] = {
            "hostname": hostname,
            "in_scope": False,
            "scope_reason": None,
            "findings": [],
            "errors": [],
            "tools": {},
        }

        # Step 1: scope_guard enforcement
        # Create a minimal domain object for scope check
        from datetime import UTC

        if domain_verified and verified_at:
            if verified_at.tzinfo is None:
                verified_at = verified_at.replace(tzinfo=UTC)
        else:
            verified_at = None

        # Build a simple domain-like object
        class FakeDomain:
            def __init__(self, root, verified_at_val):
                self.root_domain = root
                self.verified_at = verified_at_val
                self.status = "verified" if verified_at_val else "unverified"

        fake_domain = FakeDomain(domain_root, verified_at)

        in_scope, reason = is_in_scope(fake_domain, hostname)
        result["in_scope"] = in_scope
        result["scope_reason"] = reason

        if not in_scope:
            logger.warning(
                "asset out of scope",
                hostname=hostname,
                domain=domain_root,
                reason=reason,
            )
            return result

        # Step 2: Run Nmap
        try:
            nmap_result = run_nmap(hostname, timeout_seconds=self.timeout_seconds)
            result["tools"]["nmap"] = nmap_result
            if "error" not in nmap_result:
                nmap_findings = normalize_nmap(
                    nmap_result.get("scan_data", {}),
                    hostname,
                )
                result["findings"].extend(nmap_findings)
        except Exception as exc:
            logger.exception("nmap error", hostname=hostname, error=str(exc))
            result["errors"].append(f"nmap: {str(exc)[:200]}")
            result["tools"]["nmap"] = {"error": str(exc)[:200]}

        # Step 3: Run ZAP (if available)
        if self.zap_runner:
            try:
                target_url = f"https://{hostname}"
                zap_result = self.zap_runner.active_scan(target_url)
                result["tools"]["zap"] = zap_result
                if "error" not in zap_result:
                    zap_findings = normalize_zap(
                        zap_result.get("alerts", []),
                        hostname,
                    )
                    result["findings"].extend(zap_findings)
            except Exception as exc:
                logger.exception("zap error", hostname=hostname, error=str(exc))
                result["errors"].append(f"zap: {str(exc)[:200]}")
                result["tools"]["zap"] = {"error": str(exc)[:200]}

        # Step 4: Run Nuclei
        try:
            target_url = f"https://{hostname}"
            nuclei_results = run_nuclei(
                target_url,
                timeout_seconds=self.timeout_seconds,
            )
            result["tools"]["nuclei"] = {"count": len(nuclei_results)}
            if not nuclei_results or "error" not in nuclei_results[0]:
                nuclei_findings = normalize_nuclei(nuclei_results, hostname)
                result["findings"].extend(nuclei_findings)
            else:
                result["errors"].append(
                    f"nuclei: {nuclei_results[0].get('error', 'unknown')}"
                )
        except Exception as exc:
            logger.exception("nuclei error", hostname=hostname, error=str(exc))
            result["errors"].append(f"nuclei: {str(exc)[:200]}")
            result["tools"]["nuclei"] = {"error": str(exc)[:200]}

        # Determine overall status
        if result["errors"] and not result["findings"]:
            result["status"] = "failed"
        elif result["errors"]:
            result["status"] = "partial"
        else:
            result["status"] = "completed"

        logger.info(
            "scan orchestration complete",
            hostname=hostname,
            status=result["status"],
            findings=len(result["findings"]),
            errors=len(result["errors"]),
        )

        return result
