from datetime import UTC, datetime

from app.services.cron_schedule import is_due, is_valid_cron


def test_cron_validation_and_due_minute():
    now = datetime(2026, 10, 30, 12, 15, tzinfo=UTC)
    assert is_valid_cron("*/15 * * * *")
    assert not is_valid_cron("60 * * * *")
    assert not is_valid_cron("* * *")
    assert is_due("*/15 * * * *", now, datetime(2026, 10, 30, 12, 1, tzinfo=UTC))
    assert not is_due("*/15 * * * *", now, datetime(2026, 10, 30, 12, 15, tzinfo=UTC))
    assert not is_due("0 0 * * *", now, datetime(2026, 10, 30, 12, 1, tzinfo=UTC))
