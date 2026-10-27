"""Unit tests for CT log client (T-022).

Tests use mocked httpx since crt.sh is not accessible locally.
Covers:
- Valid domain queries crt.sh with correct URL
- Invalid domain raises ValueError
- Connect error returns empty list
- Timeout returns empty list
- Non-200 status returns empty list
- JSON parsing extracts subdomains
- Wildcard prefix stripped
- Deduplication preserves order
- Newline-separated names in name_value
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.discovery.ct_logs import fetch_ct_subdomains


class TestFetchCtSubdomains:
    """Tests for fetch_ct_subdomains."""

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_valid_domain_queries_ct_sh(self, mock_client_class):
        """Valid domain triggers crt.sh query with correct URL."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[])
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        mock_client.get.assert_called_once()
        url = mock_client.get.call_args[0][0]
        assert "crt.sh" in url
        assert "example.com" in url
        assert result == []

    def test_invalid_domain_raises_value_error(self):
        """Invalid domain format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid domain"):
            fetch_ct_subdomains("not a hostname")

    def test_empty_domain_raises_value_error(self):
        """Empty domain raises ValueError."""
        with pytest.raises(ValueError, match="Invalid domain"):
            fetch_ct_subdomains("")

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_connect_error_returns_empty(self, mock_client_class):
        """Connection error returns empty list."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        import httpx

        mock_client.get = MagicMock(side_effect=httpx.ConnectError("conn failed"))

        result = fetch_ct_subdomains("example.com")

        assert result == []

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_timeout_returns_empty(self, mock_client_class):
        """Timeout returns empty list."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        import httpx

        mock_client.get = MagicMock(side_effect=httpx.TimeoutException("timeout"))

        result = fetch_ct_subdomains("example.com")

        assert result == []

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_non_200_returns_empty(self, mock_client_class):
        """Non-200 status returns empty list."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        assert result == []

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_json_parsing_extracts_subdomains(self, mock_client_class):
        """JSON response with name_value is parsed correctly."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {"name_value": "sub1.example.com"},
                {"name_value": "sub2.example.com"},
            ]
        )
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        assert "sub1.example.com" in result
        assert "sub2.example.com" in result

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_wildcard_prefix_stripped(self, mock_client_class):
        """Wildcard prefix (*.) is stripped from subdomains."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {"name_value": "*.example.com"},
            ]
        )
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        assert "example.com" in result
        assert "*." not in result[0]

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_newline_separated_names(self, mock_client_class):
        """Multiple names in name_value (newline-separated) are all extracted."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {"name_value": "sub1.example.com\nsub2.example.com"},
            ]
        )
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        assert "sub1.example.com" in result
        assert "sub2.example.com" in result

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_deduplication_preserves_order(self, mock_client_class):
        """Duplicate subdomains are removed, first occurrence kept."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {"name_value": "sub.example.com"},
                {"name_value": "sub.example.com"},
                {"name_value": "other.example.com"},
            ]
        )
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        assert result == ["sub.example.com", "other.example.com"]

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_root_domain_excluded(self, mock_client_class):
        """The root domain itself is excluded from results."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value=[
                {"name_value": "example.com"},
                {"name_value": "sub.example.com"},
            ]
        )
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        assert "example.com" not in result
        assert "sub.example.com" in result

    @patch("app.services.discovery.ct_logs.httpx.Client")
    def test_json_parse_error_returns_empty(self, mock_client_class):
        """JSON parse error returns empty list."""
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_class.return_value.__exit__ = MagicMock(return_value=False)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(side_effect=ValueError("bad json"))
        mock_client.get = MagicMock(return_value=mock_response)

        result = fetch_ct_subdomains("example.com")

        assert result == []
