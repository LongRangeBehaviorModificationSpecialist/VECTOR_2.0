#!/usr/bin/env python3

"""
live.py

Keeps open pages current while several devices work the same case.

A page used to show what was in the database when it was opened, so an
entry made on one tablet appeared on another only after someone reloaded
it. Each page now checks a number every couple of seconds -- a comparison
in memory, not a database query -- and reloads what it shows when that
number has moved. Case pages watch models.data_version(); the Audit
Trail page watches models.audit_version(), because a sign-in changes no
case data but does belong on that page.
"""

from typing import Callable
from nicegui import ui
from models import data_version


CHECK_EVERY_SECONDS = 2.0


def refresh_on_change(
    callback: Callable[[], None],
    version: Callable[[], int] = data_version,
) -> ui.timer:
    """Calls callback once the watched number has moved since last time.

    version says which signal to watch: case data by default, or
    models.audit_version for a page showing the trail itself.

    Waits while a dialog is open on the page. Rebuilding a table under an
    open edit or delete dialog removes the dialog along with whatever had
    been typed into it; the reload happens as soon as the dialog closes.
    """
    client = ui.context.client
    seen = version()

    def check() -> None:
        nonlocal seen
        current = version()
        if current == seen:
            return
        if any(
            isinstance(element, ui.dialog) and element.value
            for element in list(client.elements.values())
        ):
            return
        seen = current
        callback()

    return ui.timer(CHECK_EVERY_SECONDS, check)
