from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.recurrence import expand, is_occurrence

UTC = timezone.utc


def dt(*args) -> datetime:
    return datetime(*args, tzinfo=UTC)


def test_daily_range_is_half_open():
    res = expand(dt(2026, 11, 1, 9), "UTC", "daily", None, dt(2026, 11, 3), dt(2026, 11, 6))
    assert res == [dt(2026, 11, 3, 9), dt(2026, 11, 4, 9), dt(2026, 11, 5, 9)]


def test_weekly_until_is_inclusive():
    res = expand(dt(2026, 11, 2, 9), "UTC", "weekly", date(2026, 11, 16), dt(2026, 11, 1), dt(2027, 1, 1))
    assert res == [dt(2026, 11, 2, 9), dt(2026, 11, 9, 9), dt(2026, 11, 16, 9)]


def test_monthly_31st_clamps_without_drift():
    res = expand(dt(2026, 1, 31, 9), "UTC", "monthly", None, dt(2026, 1, 1), dt(2026, 6, 1))
    assert [r.date() for r in res] == [
        date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31),
        date(2026, 4, 30), date(2026, 5, 31),
    ]


def test_dst_keeps_wall_clock_time():
    # В Нью-Йорке 1 ноября 2026 заканчивается летнее время
    ny = ZoneInfo("America/New_York")
    start = datetime(2026, 10, 31, 9, 0, tzinfo=ny).astimezone(UTC)
    res = expand(start, "America/New_York", "daily", None, dt(2026, 10, 31), dt(2026, 11, 3))
    assert res == [dt(2026, 10, 31, 13), dt(2026, 11, 1, 14), dt(2026, 11, 2, 14)]


def test_old_series_is_fast_and_correct():
    res = expand(dt(2020, 1, 1, 8), "UTC", "daily", None, dt(2026, 11, 1), dt(2026, 11, 4))
    assert res == [dt(2026, 11, 1, 8), dt(2026, 11, 2, 8), dt(2026, 11, 3, 8)]


def test_until_before_range_and_start_after_range():
    assert expand(dt(2026, 11, 2, 9), "UTC", "daily", date(2026, 11, 5), dt(2026, 11, 10), dt(2026, 11, 20)) == []
    assert expand(dt(2026, 12, 1, 9), "UTC", "daily", None, dt(2026, 11, 1), dt(2026, 11, 20)) == []


def test_is_occurrence():
    start = dt(2026, 11, 2, 9)
    assert is_occurrence(start, "UTC", "weekly", None, dt(2026, 11, 9, 9))
    assert not is_occurrence(start, "UTC", "weekly", None, dt(2026, 11, 9, 10))
    assert not is_occurrence(start, "UTC", "weekly", None, dt(2026, 11, 10, 9))