from datetime import datetime, timedelta, timezone

EAST_EIGHT = timezone(timedelta(hours=8))


def now() -> dict:
    instant = datetime.now(timezone.utc)
    return describe(instant)


def describe(instant: datetime) -> dict:
    local = instant.astimezone(EAST_EIGHT)
    # Integer arithmetic keeps all timestamp fields tied to the same instant.
    delta = instant - datetime(1970, 1, 1, tzinfo=timezone.utc)
    micros = (delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds
    return {
        "date": local.date().isoformat(),
        "time": local.strftime("%H:%M:%S") + f".{local.microsecond // 1000:03d}",
        "iso_datetime": local.isoformat(timespec="milliseconds"),
        "timezone": "UTC+08:00", "weekday": local.isoweekday(),
        "unix_seconds": str(micros // 1_000_000),
        "unix_milliseconds": str(micros // 1000),
    }

