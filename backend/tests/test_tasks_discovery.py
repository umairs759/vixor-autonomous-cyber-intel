"""Unit tests for discovery Celery tasks (T-025).

Tests use mocks for all external tools (subfinder, crt.sh, DNS, httpx)
and the database session. Covers:
- Full discovery pipeline creates assets
- Domain not found returns error
- Domain not verified returns error
- Scope guard filtering excludes out-of-scope assets
- Partial tool failures handled gracefully
- Wildcard detection included in results
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from app.models.domain import Domain, DomainStatus
from app.workers.tasks_discovery import run_discovery


def _make_domain(
    domain_id="domain-1",
    root_domain="example.com",
    status=DomainStatus.verified,
    verified_at=None,
):
    """Create a mock domain object."""
    domain = MagicMock()
    domain.id = domain_id
    domain.root_domain = root_domain
    domain.status = status
    domain.verified_at = verified_at or datetime.now(UTC)
    return domain


def _make_db_session(domain=None):
    """Create a mock database session.

    query(Domain).filter().first() returns the domain.
    query(Asset).filter().first() returns None (no existing asset).
    """
    db = MagicMock()

    def query_side_effect(model):
        mock = MagicMock()
        if model is Domain:
            mock.filter.return_value.first.return_value = domain
        else:
            mock.filter.return_value.first.return_value = None
        return mock

    db.query.side_effect = query_side_effect
    return db


class TestRunDiscovery:
    """Tests for the run_discovery Celery task."""

    @patch("app.workers.tasks_discovery.get_session_factory")
    @patch("app.workers.tasks_discovery.run_subfinder")
    @patch("app.workers.tasks_discovery.fetch_ct_subdomains")
    @patch("app.workers.tasks_discovery.enumerate_dns")
    @patch("app.workers.tasks_discovery.probe_host")
    @patch("app.workers.tasks_discovery.is_in_scope")
    def test_full_discovery_pipeline(
        self,
        mock_is_in_scope,
        mock_probe,
        mock_enum_dns,
        mock_ct,
        mock_subfinder,
        mock_get_session,
    ):
        """Full discovery pipeline creates assets."""
        domain = _make_domain(verified_at=datetime.now(UTC))
        db = _make_db_session(domain)
        mock_get_session.return_value.return_value = db

        mock_subfinder.return_value = ["sub1.example.com", "sub2.example.com"]
        mock_ct.return_value = ["sub2.example.com", "sub3.example.com"]
        mock_enum_dns.return_value = {
            "sub1.example.com": ["1.2.3.4"],
            "sub2.example.com": ["5.6.7.8"],
            "_wildcard_detected": False,
        }
        mock_probe.return_value = {
            "live": True,
            "technologies": ["nginx"],
        }
        mock_is_in_scope.return_value = (True, None)

        result = run_discovery("domain-1")

        assert result["status"] == "completed"
        assert result["domain_id"] == "domain-1"
        assert result["wildcard_detected"] is False
        assert db.add.called or db.commit.called

    @patch("app.workers.tasks_discovery.get_session_factory")
    def test_domain_not_found(self, mock_get_session):
        """Domain not found returns error."""
        db = _make_db_session(None)
        mock_get_session.return_value.return_value = db

        result = run_discovery("nonexistent")

        assert result["error"] == "domain not found"

    @patch("app.workers.tasks_discovery.get_session_factory")
    def test_domain_not_verified(self, mock_get_session):
        """Unverified domain returns error."""
        domain = _make_domain(status=DomainStatus.unverified)
        db = _make_db_session(domain)
        mock_get_session.return_value.return_value = db

        result = run_discovery("domain-1")

        assert "not verified" in result["error"]

    @patch("app.workers.tasks_discovery.get_session_factory")
    @patch("app.workers.tasks_discovery.run_subfinder")
    @patch("app.workers.tasks_discovery.fetch_ct_subdomains")
    @patch("app.workers.tasks_discovery.enumerate_dns")
    @patch("app.workers.tasks_discovery.probe_host")
    @patch("app.workers.tasks_discovery.is_in_scope")
    def test_partial_failures_handled(
        self,
        mock_is_in_scope,
        mock_probe,
        mock_enum_dns,
        mock_ct,
        mock_subfinder,
        mock_get_session,
    ):
        """Partial tool failures don't crash the pipeline."""
        domain = _make_domain(verified_at=datetime.now(UTC))
        db = _make_db_session(domain)
        mock_get_session.return_value.return_value = db

        # subfinder fails
        mock_subfinder.side_effect = Exception("subfinder error")
        # ct_logs works
        mock_ct.return_value = ["sub1.example.com"]
        # DNS works
        mock_enum_dns.return_value = {
            "sub1.example.com": ["1.2.3.4"],
            "_wildcard_detected": False,
        }
        # httpx probe finds nothing live
        mock_probe.return_value = {"live": False}
        mock_is_in_scope.return_value = (True, None)

        db.query.return_value.filter.return_value.first.return_value = None

        result = run_discovery("domain-1")

        assert result["status"] == "completed"

    @patch("app.workers.tasks_discovery.get_session_factory")
    @patch("app.workers.tasks_discovery.run_subfinder")
    @patch("app.workers.tasks_discovery.fetch_ct_subdomains")
    @patch("app.workers.tasks_discovery.enumerate_dns")
    @patch("app.workers.tasks_discovery.probe_host")
    @patch("app.workers.tasks_discovery.is_in_scope")
    def test_scope_guard_excludes_out_of_scope(
        self,
        mock_is_in_scope,
        mock_probe,
        mock_enum_dns,
        mock_ct,
        mock_subfinder,
        mock_get_session,
    ):
        """Out-of-scope assets are excluded."""
        domain = _make_domain(verified_at=datetime.now(UTC))
        db = _make_db_session(domain)
        mock_get_session.return_value.return_value = db

        mock_subfinder.return_value = ["evil.com"]
        mock_ct.return_value = []
        mock_enum_dns.return_value = {
            "_wildcard_detected": False,
        }
        mock_is_in_scope.return_value = (False, "out of scope")

        result = run_discovery("domain-1")

        assert result["status"] == "completed"
        # probe_host should not be called for out-of-scope assets
        mock_probe.assert_not_called()

    @patch("app.workers.tasks_discovery.get_session_factory")
    @patch("app.workers.tasks_discovery.run_subfinder")
    @patch("app.workers.tasks_discovery.fetch_ct_subdomains")
    @patch("app.workers.tasks_discovery.enumerate_dns")
    def test_all_tools_fail(
        self, mock_enum_dns, mock_ct, mock_subfinder, mock_get_session
    ):
        """All tools failing still returns completed status."""
        domain = _make_domain(verified_at=datetime.now(UTC))
        db = _make_db_session(domain)
        mock_get_session.return_value.return_value = db

        mock_subfinder.side_effect = Exception("subfinder error")
        mock_ct.side_effect = Exception("ct error")
        mock_enum_dns.return_value = {"_wildcard_detected": False}

        result = run_discovery("domain-1")

        assert result["status"] == "completed"
