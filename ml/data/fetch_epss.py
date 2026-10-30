"""VIXOR - EPSS score client (T-032)."""

from __future__ import annotations

import httpx

EPSS_API_URL = "https://api.first.org/data/v1/epss"


def fetch_epss(
    cve_ids: list[str],
    timeout_seconds: int = 30,
) -> dict[str, float]:
    """Fetch EPSS scores for a list of CVE IDs.

    Returns a mapping of CVE ID -> EPSS score (0.0-1.0).
    """
    if not cve_ids:
        return {}

    params = {"cve": ",".join(cve_ids)}
    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.get(EPSS_API_URL, params=params)
    except Exception:  # noqa: BLE001
        return {}

    if response.status_code != 200:
        return {}

    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return {}

    result: dict[str, float] = {}
    for item in payload.get("data", []):
        cve = item.get("cve")
        score = item.get("epss")
        if cve and score is not None:
            try:
                result[cve] = float(score)
            except (TypeError, ValueError):
                continue
    return result
