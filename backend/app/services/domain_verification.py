"""VIXOR — Domain ownership verification service (T-019).

Supports two verification methods:
1. DNS TXT: Check for a TXT record at _vixor-verify.<root_domain> equal to the token.
2. File: GET https://<root>/.well-known/vixor-verification.txt containing the token.
   - No redirects to other hosts (SSRF protection)
   - 5 second timeout
   - Block private IPs (SSRF protection)
"""

from datetime import UTC, datetime
from typing import Any

import dns.resolver
import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.models.domain import Domain, DomainStatus
from app.services.audit_service import write_audit_log

logger = get_logger("domain_verification")
settings = get_settings()

VERIFICATION_FILE_PATH = "/.well-known/vixor-verification.txt"
VERIFICATION_TIMEOUT = 5  # seconds
VERIFY_DNS_TXT_RECORD = "_vixor-verify"


class DomainVerificationError(Exception):
    """Raised when domain verification fails with a specific reason."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def is_private_ip(host: str) -> bool:
    """Check if a hostname resolves to a private/RFC1918 IP (SSRF protection)."""
    try:
        import ipaddress

        # Try to parse as IP directly
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            pass

        # Resolve hostname and check IPs
        answers = dns.resolver.resolve(host, "A")
        for answer in answers:
            ip = ipaddress.ip_address(str(answer))
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return True
        return False
    except Exception:  # noqa: BLE001 - catch-all for DNS resolver errors, return safe failure
        # If we can't resolve, err on the side of caution
        return True


async def verify_dns_txt(root_domain: str, token: str) -> tuple[bool, str | None]:
    """Verify ownership via DNS TXT record at _vixor-verify.<root_domain>.

    Returns (success, reason). On failure, reason explains why.
    """
    txt_record_name = f"{VERIFY_DNS_TXT_RECORD}.{root_domain}"
    try:
        answers = dns.resolver.resolve(txt_record_name, "TXT")
        for answer in answers:
            # TXT records may be quoted; join the text parts
            txt_value = b"".join(answer.strings).decode("utf-8", errors="replace")
            if txt_value == token:
                return True, None
        return (
            False,
            f"No TXT record at {txt_record_name} matches the verification token",
        )
    except dns.resolver.NXDOMAIN:
        return False, f"No DNS TXT record found at {txt_record_name}"
    except dns.resolver.NoAnswer:
        return False, f"No TXT answer for {txt_record_name}"
    except dns.resolver.NoNameservers:
        return False, f"No nameservers available for {txt_record_name}"
    except dns.exception.Timeout:
        return False, f"DNS query timed out for {txt_record_name}"
    except Exception as exc:
        logger.exception(
            "dns_txt_verification_error", domain=root_domain, error=str(exc)
        )
        return False, f"DNS verification error: {exc!s}"


async def verify_file(root_domain: str, token: str) -> tuple[bool, str | None]:
    """Verify ownership via file at https://<root>/.well-known/vixor-verification.txt.

    Security:
    - No redirects to other hosts (SSRF protection)
    - 5 second timeout
    - Block private IPs (SSRF protection)

    Returns (success, reason). On failure, reason explains why.
    """
    url = f"https://{root_domain}{VERIFICATION_FILE_PATH}"

    # Block private IP scanning (SSRF protection)
    if is_private_ip(root_domain):
        return (
            False,
            f"Domain {root_domain} resolves to a private IP; file verification blocked",
        )

    try:
        async with httpx.AsyncClient(
            timeout=VERIFICATION_TIMEOUT,
            follow_redirects=False,  # No redirects to other hosts
        ) as client:
            response = await client.get(url)

        if response.status_code != 200:
            return False, (
                f"File verification returned HTTP {response.status_code}; "
                f"expected 200 with token content"
            )

        content = response.text.strip()
        if content == token:
            return True, None
        return False, "File content does not match the verification token"

    except httpx.ConnectError:
        return False, f"Could not connect to {url}"
    except httpx.TimeoutException:
        return False, f"File verification timed out after {VERIFICATION_TIMEOUT}s"
    except httpx.TooManyRedirects:
        return False, "Too many redirects (redirects to other hosts are blocked)"
    except httpx.RequestError as exc:
        return False, f"File verification request error: {exc!s}"
    except Exception as exc:
        logger.exception("file_verification_error", domain=root_domain, error=str(exc))
        return False, f"File verification error: {exc!s}"


async def verify_domain_ownership(
    root_domain: str,
    token: str,
    method: str,
) -> tuple[bool, str | None]:
    """Verify domain ownership using the specified method.

    Returns (success, reason). On success, reason is None.
    """
    if method == "dns_txt":
        return await verify_dns_txt(root_domain, token)
    elif method == "file":
        return await verify_file(root_domain, token)
    else:
        return False, f"Unknown verification method: {method}"


async def perform_verification(
    domain: Domain,
    db: Any,
    user_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[bool, str | None]:
    """Perform domain ownership verification and update the domain record.

    Returns (success, reason). On success, domain status is set to VERIFIED
    and verified_at is set. On failure, status remains unchanged and reason
    explains why.
    """
    success, reason = await verify_domain_ownership(
        root_domain=domain.root_domain,
        token=domain.verification_token,
        method=domain.verification_method.value,
    )

    if success:
        domain.status = DomainStatus.verified
        domain.verified_at = datetime.now(UTC)
        db.commit()
        db.refresh(domain)

        write_audit_log(
            db,
            action="domain_verified",
            resource_type="domain",
            resource_id=domain.id,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            metadata={
                "root_domain": domain.root_domain,
                "verification_method": domain.verification_method.value,
            },
        )
        logger.info(
            "domain_verified", domain_id=domain.id, root_domain=domain.root_domain
        )
    else:
        write_audit_log(
            db,
            action="domain_verification_failed",
            resource_type="domain",
            resource_id=domain.id,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            metadata={
                "root_domain": domain.root_domain,
                "verification_method": domain.verification_method.value,
                "reason": reason,
            },
        )
        logger.warning(
            "domain_verification_failed",
            domain_id=domain.id,
            root_domain=domain.root_domain,
            reason=reason,
        )

    return success, reason


async def reverify_domain(
    domain: Domain,
    db: Any,
) -> tuple[bool, str | None]:
    """Re-verify a domain that was previously verified.

    Used by the periodic re-verification task. On failure, sets domain
    status to SUSPENDED.
    """
    success, reason = await verify_domain_ownership(
        root_domain=domain.root_domain,
        token=domain.verification_token,
        method=domain.verification_method.value,
    )

    if success:
        domain.verified_at = datetime.now(UTC)
        domain.last_reverified_at = datetime.now(UTC)
        domain.status = DomainStatus.verified
        db.commit()
        db.refresh(domain)

        write_audit_log(
            db,
            action="domain_reverified",
            resource_type="domain",
            resource_id=domain.id,
            ip=None,
            user_agent=None,
            metadata={
                "root_domain": domain.root_domain,
                "verification_method": domain.verification_method.value,
            },
        )
        logger.info(
            "domain_reverified", domain_id=domain.id, root_domain=domain.root_domain
        )
        return True, None
    else:
        domain.status = DomainStatus.suspended
        domain.last_reverified_at = datetime.now(UTC)
        db.commit()
        db.refresh(domain)

        write_audit_log(
            db,
            action="domain_suspended",
            resource_type="domain",
            resource_id=domain.id,
            ip=None,
            user_agent=None,
            metadata={
                "root_domain": domain.root_domain,
                "reason": reason,
            },
        )
        logger.warning(
            "domain_suspended_after_reverify_failure",
            domain_id=domain.id,
            root_domain=domain.root_domain,
            reason=reason,
        )
        return False, reason
