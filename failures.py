#!/usr/bin/env python3

"""
failures.py

Plain-language reasons for failures, and the log that keeps the detail.

Saves, imports and exports used to put the raw exception on screen. For a
database error that meant the SQL statement and every parameter, with the
reason somewhere in the middle -- and on the Files page a failed delete
showed nothing at all. The person at the scene now gets the reason in
words; the full traceback goes to the console window for whoever has to
fix it.

Imports nothing from the rest of the application, so any module can use
it.
"""

import errno
import logging
import re

log = logging.getLogger("vector")


def explain(err: BaseException, labels: dict | None = None) -> str:
    """One or two sentences saying why something failed.

    labels maps column names to what the page calls them, so a clash on
    EVIDNUM reads as the "Evidence Number" the agent typed.
    """
    labels = labels or {}
    # SQLAlchemy wraps the driver's error, and its own message appends
    # the SQL statement and parameters. The driver's message is the reason.
    original = getattr(err, "orig", None) or err
    text = " ".join(str(original).split())
    lowered = text.lower()

    def name(column: str) -> str:
        return labels.get(column, column)

    unique = re.search(
        r"unique constraint failed: ([\w.]+(?:, [\w.]+)*)",
        text,
        re.IGNORECASE
    )
    if unique:
        columns = [
            part.split(".")[-1] for part in unique.group(1).split(", ")
        ]
        fields = " and ".join(name(column) for column in columns)
        return (
            f"Another record already has that {fields}, and it has to be "
            "different."
        )

    not_null = re.search(
        r"not null constraint failed: \w+\.(\w+)",
        text,
        re.IGNORECASE
    )
    if not_null:
        return f"{name(not_null.group(1))} cannot be left empty."

    if "database is locked" in lowered:
        return "The database was busy with another save. Try again in a moment."

    if "readonly database" in lowered:
        return (
            "VECTOR is not allowed to write to its database. Check that the "
            "db folder is not read-only."
        )

    if "disk is full" in lowered or getattr(
        original,
        "errno",
        None
    ) == errno.ENOSPC:
        return "The disk is full. Free some space and try again."

    if isinstance(original, PermissionError):
        target = getattr(original, "filename", None)
        where = f" for {target}" if target else ""
        return (
            f"Permission was refused{where}. Another program may have the "
            "file open."
        )

    if "bad password" in lowered:
        return "The password is wrong."

    # pyzipper carries its own copy of zipfile, so match the class by name.
    if type(original).__name__ in ("BadZipFile", "BadZipfile"):
        return "The file is not a ZIP archive, or it is damaged."

    if isinstance(original, UnicodeDecodeError):
        return (
            "The file is not in the expected text format. It may be damaged, "
            "or not a VECTOR export."
        )

    return (
        f"{type(original).__name__}: {text}"
        if text else type(original).__name__
    )
