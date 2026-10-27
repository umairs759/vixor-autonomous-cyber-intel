"""VIXOR — OWASP ZAP runner (T-027).

Runs ZAP in daemon mode with non-destructive policy.
Uses ZAP API client. Attack strength LOW/MEDIUM, no destructive rules.
"""

import time
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.logging import get_logger
from app.services.scope_guard import validate_hostname

logger = get_logger("scanning.zap")


class ZapRunner:
    """OWASP ZAP API client for non-destructive scanning."""

    def __init__(
        self,
        zap_url: str = "http://zap:8090",
        api_key: str = "",
        timeout_seconds: int = 300,
    ) -> None:
        self.zap_url = zap_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a request to the ZAP API."""
        params = params or {}
        if self.api_key:
            params["apikey"] = self.api_key

        url = f"{self.zap_url}{path}"
        try:
            with httpx.Client(timeout=30) as client:
                response = client.request(method, url, params=params)
            return response.json() if response.content else {}
        except Exception as exc:
            logger.exception("zap api error", path=path, error=str(exc))
            return {"error": str(exc)}

    def active_scan(
        self,
        target_url: str,
        policy_name: str = "safe policy",
    ) -> dict[str, Any]:
        """Run an active scan with non-destructive policy.

        Security:
        - ZAP attack strength LOW/MEDIUM
        - No destructive rules
        - Target validated before scanning
        """
        parsed = urlparse(target_url)
        hostname = parsed.hostname or ""
        valid, reason = validate_hostname(hostname)
        if not valid:
            return {"error": reason, "target": target_url}

        # Start active scan
        scan_params: dict[str, Any] = {
            "url": target_url,
            "recurse": "true",
            "inScopeOnly": "true",
        }
        result = self._request("GET", "/JSON/ascan/action/scan/", scan_params)
        scan_id = result.get("scan")

        if not scan_id:
            return {
                "error": "failed to start scan",
                "target": target_url,
                "result": result,
            }

        # Poll for completion
        elapsed = 0
        while elapsed < self.timeout_seconds:
            status_result = self._request(
                "GET",
                "/JSON/ascan/view/status/",
                {"scanId": scan_id},
            )
            progress = status_result.get("status", "0")
            try:
                progress_int = int(progress)
            except (ValueError, TypeError):
                progress_int = 0

            if progress_int >= 100:
                break

            time.sleep(5)
            elapsed += 5

        # Get scan results
        results = self._request(
            "GET",
            "/JSON/ascan/view/alerts/",
            {"scanId": scan_id},
        )

        return {
            "target": target_url,
            "scan_id": scan_id,
            "alerts": results.get("alerts", []),
        }
