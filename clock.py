#!/usr/bin/env python3

"""
clock.py

The machine's own clock and time zone, for every time VECTOR stamps or
shows.

VECTOR used to stamp notes, entry times and uploads in UTC, so a note
written at 08:45 at a scene read 12:45. Times now follow the time zone of
the machine VECTOR runs on -- every device signed in to it sees the same
times -- and each stamp carries its offset from UTC, so it stays
unambiguous if the laptop is later set to another zone.

The audit trail is the exception: it goes on storing UTC, and is only
shown in local time.

Imports nothing from the rest of the application.
"""

from datetime import datetime, timedelta, timezone

STAMP_FORMAT = "%m-%d-%Y %H:%M:%S"
CASE_TIME_FORMAT = "%m-%d-%Y %H:%M"


def now() -> datetime:
    """The time now, in this machine's time zone."""
    return datetime.now().astimezone()


def zone_label(moment: datetime | None = None) -> str:
    """The offset from UTC at `moment`, written as "UTC-04:00".

    An offset rather than a name: Windows names its zones in full --
    "Eastern Daylight Time" -- and a short name can mean more than one zone.
    """
    moment = moment or now()
    minutes = int((moment.utcoffset() or timedelta(0)).total_seconds()) // 60
    sign = "+" if minutes >= 0 else "-"
    hours, minutes = divmod(abs(minutes), 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def stamp(moment: datetime | None = None) -> str:
    """A time VECTOR records itself: "09-15-2026 08:45:12 UTC-04:00"."""
    moment = moment or now()
    return f"{moment.strftime(STAMP_FORMAT)} {zone_label(moment)}"


def case_time_now() -> str:
    """The time now, as a case time is typed: "09-15-2026 08:45"."""
    return now().strftime(CASE_TIME_FORMAT)


def from_utc(value: datetime) -> datetime:
    """A UTC time -- as the database keeps upload times -- in local time."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone()


def show_utc(value) -> str:
    """A stored UTC time, shown as a local stamp.

    Takes the database's naive UTC datetimes and the audit trail's
    "2026-09-15T12:45:12Z" strings. Anything else comes back as it was.
    """
    if isinstance(value, datetime):
        return stamp(from_utc(value))
    text = "" if value is None else str(value)
    try:
        parsed = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return text
    return stamp(from_utc(parsed))
