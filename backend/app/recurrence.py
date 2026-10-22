import calendar
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc


def local_date(dt: datetime, tz_name: str) -> date:
    return dt.astimezone(ZoneInfo(tz_name)).date()


def _add_months(base: date, months: int, anchor_day: int) -> date:
    year, month0 = divmod(base.year * 12 + base.month - 1 + months, 12)
    month = month0 + 1
    # 31-е в коротком месяце -> последний день месяца
    return date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))


def _nth_date(start: date, freq: str, n: int) -> date:
    if freq == "daily":
        return start + timedelta(days=n)
    if freq == "weekly":
        return start + timedelta(weeks=n)
    if freq == "monthly":
        # считаем от исходного дня, а не от предыдущего вхождения:
        # 31 янв -> 28 фев -> 31 мар, без «дрейфа» на 28-е
        return _add_months(start, n, start.day)
    raise ValueError(f"unknown freq: {freq}")


def _first_index(start: date, freq: str, from_local: date) -> int:
    """Индекс, с которого можно начинать перебор (с запасом в один шаг)."""
    if freq == "daily":
        delta = (from_local - start).days
    elif freq == "weekly":
        delta = (from_local - start).days // 7
    else:
        delta = (from_local.year - start.year) * 12 + from_local.month - start.month
    return max(0, delta - 1)


def expand(
    starts_at: datetime,
    tz_name: str,
    freq: str,
    until: date | None,
    date_from: datetime,
    date_to: datetime,
) -> list[datetime]:
    """Вхождения серии в полуинтервале [date_from, date_to), в UTC.

    «9:00» понимается как настенное время в поясе серии, поэтому после перехода
    на летнее время момент в UTC сдвигается, а локальное время остаётся прежним.
    until включительно и считается в поясе серии.
    """
    tz = ZoneInfo(tz_name)
    start_local = starts_at.astimezone(tz)
    start_date, wall = start_local.date(), start_local.time()

    n = _first_index(start_date, freq, date_from.astimezone(tz).date())
    result: list[datetime] = []
    while True:
        d = _nth_date(start_date, freq, n)
        if until is not None and d > until:
            break
        occ = datetime.combine(d, wall, tzinfo=tz).astimezone(UTC)
        if occ >= date_to:
            break
        if occ >= date_from:
            result.append(occ)
        n += 1
    return result


def is_occurrence(
    starts_at: datetime, tz_name: str, freq: str, until: date | None, candidate: datetime
) -> bool:
    found = expand(
        starts_at, tz_name, freq, until, candidate, candidate + timedelta(microseconds=1)
    )
    return candidate in found