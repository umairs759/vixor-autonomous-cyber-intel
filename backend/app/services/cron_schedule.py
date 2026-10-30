from datetime import datetime


def _field_matches(field: str, value: int, minimum: int, maximum: int) -> bool:
    for item in field.split(","):
        base, slash, step_text = item.partition("/")
        step = int(step_text) if slash else 1
        if step < 1:
            return False
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            left, right = base.split("-", 1)
            start, end = int(left), int(right)
        else:
            start = end = int(base)
        if start < minimum or end > maximum or start > end:
            return False
        if start <= value <= end and (value - start) % step == 0:
            return True
    return False


def is_valid_cron(expression: str) -> bool:
    try:
        fields = expression.split()
        if len(fields) != 5:
            return False
        bounds = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
        return all(
            _field_matches(field, low, low, high) or _field_matches(field, high, low, high)
            or any(_field_matches(field, probe, low, high) for probe in range(low, high + 1))
            for field, (low, high) in zip(fields, bounds, strict=True)
        )
    except (ValueError, TypeError):
        return False


def is_due(expression: str, now: datetime, last_run_at: datetime | None) -> bool:
    if last_run_at is None:
        return True
    if last_run_at.tzinfo is None:
        last_run_at = last_run_at.replace(tzinfo=now.tzinfo)
    candidate = now.replace(second=0, microsecond=0)
    last_minute = last_run_at.replace(second=0, microsecond=0)
    if candidate <= last_minute:
        return False
    minute, hour, day, month, weekday = expression.split()
    cron_weekday = (candidate.weekday() + 1) % 7
    return (
        _field_matches(minute, candidate.minute, 0, 59)
        and _field_matches(hour, candidate.hour, 0, 23)
        and _field_matches(day, candidate.day, 1, 31)
        and _field_matches(month, candidate.month, 1, 12)
        and _field_matches(weekday, cron_weekday, 0, 7)
    )
