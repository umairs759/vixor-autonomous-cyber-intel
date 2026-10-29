"""VIXOR - CISA KEV client (T-032)."""

from __future__ import annotations

from typing import Any

import httpx

KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/"
    "known_exploited_vulnerabilities.json"
)


def fetch_kev(timeout_seconds: int = 30) -> list[dict[str, Any]]:
    """Fetch the CISA Known Exploited Vulnerabilities catalog."""
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.get(KEV_URL)
    except Exception:  # noqa: BLE001
        return []

    if response.status_code != 200:
        return []

    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return []

    vulns = payload.get("vulnerabilities", [])
    return [v for v in vulns if isinstance(v, dict)]


def get_kev_cve_ids(timeout_seconds: int = 30) -> set[str]:
    """Return a set of CVE IDs listed in the CISA KEV catalog."""
    ids: set[str] = set()
    for item in fetch_kev(timeout_seconds=timeout_seconds):
        cve_id = item.get("cveID")
        if cve_id:
            ids.add(str(cve_id))
    return ids
PY