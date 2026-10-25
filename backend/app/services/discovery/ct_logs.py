"""VIXOR — Certificate Transparency log client (T-022).

Queries crt.sh for certificate transparency records.
Uses httpx with timeout and no-redirect policy to prevent SSRF.
"""

import httpx

from app.core.logging import get_logger
from app.services.scope_guard import validate_hostname

logger = get_logger("discovery.ct_logs")

CT_SH_API = "https://crt.sh/?q={domain}&output=json"


def fetch_ct_subdomains(
    domain: str,
    timeout_seconds: int = 10,
) -> list[str]:
    """Fetch subdomains from crt.sh certificate transparency logs.

    Security:
    - No redirects to other hosts (follow_redirects=False)
    - Timeout enforced
    - Domain validated before request
    """
    valid, reason = validate_hostname(domain)
    if not valid:
        raise ValueError(f"Invalid domain: {reason}")

    url = CT_SH_API.format(domain=domain)

    try:
        with httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = client.get(url)
    except httpx.ConnectError:
        logger.warning("ct_sh connect error", domain=domain)
        return []
    except httpx.TimeoutException:
        logger.warning("ct_sh timeout", domain=domain)
        return []
    except Exception as exc:
        logger.exception("ct_sh error", domain=domain, error=str(exc))
        return []

    if response.status_code != 200:
        logger.warning(
            "ct_sh non-200",
            domain=domain,
            status_code=response.status_code,
        )
        return []

    subdomains: list[str] = []
    try:
        entries = response.json()
        for entry in entries:
            name = entry.get("name_value", "")
            if not name:
                continue
            # crt.sh may return multiple names per entry (newline-separated)
            for n in name.splitlines():
                n = n.strip().lower()
                if n and n != domain and n.endswith("." + domain):
                    # Strip wildcard prefix
                    n = n.removeprefix("*.")
                    subdomains.append(n)
    except Exception:  # noqa: BLE001 - catch-all for JSON parse errors
        logger.warning("ct_sh json parse error", domain=domain)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in subdomains:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    logger.info(
        "ct_sh completed",
        domain=domain,
        subdomains_found=len(unique),
    )
    return unique
