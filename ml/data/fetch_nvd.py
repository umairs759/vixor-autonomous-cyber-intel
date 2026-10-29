"""VIXOR - NVD CVE feed client (T-032).

Fetches CVE records from the NIST NVD 2.0 API with timeouts and no
external-network assumptions in tests (httpx is mocked).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    if "T" not in value:
        value = value + "T00:00:00.000"
    return value


def fetch_nvd(
    cve_id: str | None = None,
    keyword: str | None = None,
    results_per_page: int = 100,
    start_date: str | None = None,
    end_date: str | None = None,
    api_key: str | None = None,
    timeout_seconds: int = 30,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"resultsPerPage": results_per_page}
    if cve_id:
        params["cveId"] = cve_id
    if keyword:
        params["keywordSearch"] = keyword
    if start_date:
        params["pubStartDate"] = _parse_date(start_date)
    if end_date:
        params["pubEndDate"] = _parse_date(end_date)

    headers: dict[str, str] = {}
    if api_key:
        headers["apiKey"] = api_key

    try:
        with httpx.Client(timeout=timeout_seconds, follow_redirects=False) as client:
            response = client.get(NVD_API_URL, params=params, headers=headers)
    except (httpx.ConnectError, httpx.TimeoutException):
        return []
    except Exception:  # noqa: BLE001
        return []

    if response.status_code != 200:
        return []

    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return []

    vulnerabilities = payload.get("vulnerabilities", [])
    cves: list[dict[str, Any]] = []
    for item in vulnerabilities:
        cve = item.get("cve")
        if isinstance(cve, dict):
            cves.append(cve)
    return cves


def save_nvd_json(records: list[dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)


if __name__ == "__main__":
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    records = fetch_nvd(
        start_date=start.strftime("%Y-%m-%d"),
        end_date=end.strftime("%Y-%m-%d"),
    )
    out = os.path.join(os.path.dirname(__file__), "raw", "nvd_recent.json")
    save_nvd_json(records, out)
    print(f"Fetched {len(records)} CVEs -> {out}")
PY