#!/usr/bin/env python3

"""
auth.py

Session state and route guards.

Imports nothing from the pages, and from the rest of the application
only the message timeouts in utils. Every page module previously reached
into main.py for these three helpers, while main.py imported the pages
-- a cycle that forced function-level imports throughout the codebase
and left report routes unregistered until someone happened to visit
/reports.
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
import logging
from utils import WARN_TIMEOUT

from nicegui import app, ui

# The same logger as failures.log, named directly so this module keeps
# importing nothing from the rest of the application.
log = logging.getLogger("vector")


# ----- Login throttling -----
# Guessing is slowed after a few failures and stopped after ten. The
# numbers are deliberately forgiving: an agent mistyping a password at
# 3am on a scene must not be locked out of evidence logging.
SLOW_AFTER_FAILURES = 3
LOCK_AFTER_FAILURES = 10
LOCKOUT_MINUTES = 15
FAILURE_WINDOW_MINUTES = 30


# ----- Session state -----
# app.storage.user only exists inside a browser request. Outside one -- at
# startup, in a background task, in the test suite -- the readers below
# answer "not signed in" rather than raising. Ending sessions is different:
# if that fails, an administrator would be told a session is over when it
# is not, so those failures are logged and reported to the caller.
# ----- Reading the session -----
# Every reader below reaches for app.storage, which needs a browser
# request in scope. A timer, a background task, a test or a page being
# torn down has none, and NiceGUI raises rather than returning nothing.
#
# Each catch below is that case, and each answers the way that fails
# safe: not signed in, no name, not an admin, generation zero. The two
# writers further down are different -- a failure there means an admin
# is told a session ended when it did not, so those are logged and
# reported to the caller.
def is_authenticated() -> bool:
    """Checks if the current user is signed in (defaults to False).

    A session is valid only while the generation counters it was
    stamped with at sign-in still match. That is what lets an admin end
    someone else's session; without the check, deleting an account left
    its session working until the browser closed.
    """
    try:
        if not app.storage.user.get("authenticated", False):
            return False

        if app.storage.user.get("session_generation", 0) < (
            global_generation()
        ):
            return False

        user_name = app.storage.user.get("USERNAME", "")
        # A session stored before the keys were renamed has no USERNAME.
        # Treat it as signed out rather than letting it through nameless.
        if not user_name:
            return False

        if app.storage.user.get("user_generation", 0) < user_generation(
            user_name
        ):
            return False

        return True
    except Exception:
        # No request in scope; see the note above.
        return False


def get_current_user_name() -> str:
    """Gets the current username (defaults to empty)."""
    try:
        return app.storage.user.get("USERNAME", "")
    except Exception:
        # No request in scope; see the note above.
        return ""


def get_is_admin() -> bool:
    """Checks if the current user is an admin (defaults to False)."""
    try:
        return app.storage.user.get("ISADMIN", False)
    except Exception:
        # No request in scope; see the note above.
        return False


def sign_in(user_name: str, is_admin: bool) -> None:
    """Records a successful authentication in the session.

    The generation counters are stamped here and checked on every
    request, which is what makes it possible to sign a user out
    remotely -- see invalidate_user_sessions().
    """
    app.storage.user["authenticated"] = True
    app.storage.user["USERNAME"] = user_name
    app.storage.user["ISADMIN"] = is_admin
    app.storage.user["session_generation"] = global_generation()
    app.storage.user["user_generation"] = user_generation(user_name)


def sign_out() -> None:
    """Clears the session."""
    app.storage.user["authenticated"] = False
    app.storage.user["USERNAME"] = ""
    app.storage.user["ISADMIN"] = False
    app.storage.user["session_generation"] = 0
    app.storage.user["user_generation"] = 0


# ----- Session invalidation -----
# Both counters were previously written at login and never read, so a
# deleted or deactivated account kept working until the browser was
# closed. A session is valid only while the generations it was stamped
# with still match.
def global_generation() -> int:
    """Bumped to sign every user out at once."""
    try:
        return app.storage.general.get("session_generation", 0)
    except Exception:
        # No request in scope; see the note above.
        return 0


def user_generation(user_name: str) -> int:
    """Bumped to sign one user out."""
    try:
        return app.storage.general.get("user_generations", {}).get(
            user_name, 0
        )
    except Exception:
        # No request in scope; see the note above.
        return 0


def invalidate_user_sessions(user_name: str) -> bool:
    """Ends every active session for one account, immediately.

    Called when an account is deleted, deactivated, or has its password
    reset -- a password reset that leaves the old session working is not
    a reset. Returns False when the sessions could not be ended, so the
    caller can say so.
    """
    try:
        generations = dict(app.storage.general.get("user_generations", {}))
        generations[user_name] = generations.get(user_name, 0) + 1
        app.storage.general["user_generations"] = generations
    except Exception:
        log.exception("Could not end the sessions of %s", user_name)
        return False
    return True


def invalidate_all_sessions() -> bool:
    """Ends every active session for every account.

    Returns False when the sessions could not be ended.
    """
    try:
        app.storage.general["session_generation"] = global_generation() + 1
    except Exception:
        log.exception("Could not end every session")
        return False
    return True


# ----- Login throttling -----
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _failures() -> dict:
    try:
        return dict(app.storage.general.get("login_failures", {}))
    except Exception:
        # No request in scope; see the note above. No record of failures
        # means no throttling this call, not a refused sign-in.
        return {}


def _save_failures(failures: dict) -> None:
    try:
        app.storage.general["login_failures"] = failures
    except Exception:
        # Sign-in still works, but without the throttling, so say so.
        log.exception("Could not record failed sign-ins")


def lockout_seconds_remaining(user_name: str) -> int:
    """Seconds until this account may try again; 0 when it may now."""
    record = _failures().get(user_name)
    if not record:
        return 0
    locked_until = record.get("locked_until")
    if not locked_until:
        return 0
    try:
        expiry = datetime.fromisoformat(locked_until)
    except (TypeError, ValueError):
        return 0
    remaining = (expiry - _now()).total_seconds()
    return max(0, int(remaining))


def failure_delay_seconds(user_name: str) -> float:
    """A small, growing pause once an account starts failing.

    Enough to make scripted guessing impractical without punishing a
    genuine mistype.
    """
    count = _failures().get(user_name, {}).get("count", 0)
    if count < SLOW_AFTER_FAILURES:
        return 0.0
    return min(2.0, 0.5 * (count - SLOW_AFTER_FAILURES + 1))


def record_login_failure(user_name: str) -> int:
    """Counts one failed attempt. Returns the new failure count."""
    failures = _failures()
    record = failures.get(user_name, {})

    # Failures age out, so an account is not locked by attempts spread
    # across a whole shift.
    first_seen = record.get("first_seen")
    if first_seen:
        try:
            age = _now() - datetime.fromisoformat(first_seen)
            if age > timedelta(minutes=FAILURE_WINDOW_MINUTES):
                record = {}
        except (TypeError, ValueError):
            record = {}

    count = record.get("count", 0) + 1
    record["count"] = count
    record.setdefault("first_seen", _now().isoformat())

    if count >= LOCK_AFTER_FAILURES:
        record["locked_until"] = (
            _now() + timedelta(minutes=LOCKOUT_MINUTES)
        ).isoformat()

    failures[user_name] = record
    _save_failures(failures)
    return count


def clear_login_failures(user_name: str) -> None:
    """Forgets an account's failures after a successful sign-in."""
    failures = _failures()
    if failures.pop(user_name, None) is not None:
        _save_failures(failures)


# ----- Route guards -----
def require_login(page_builder):
    """Sends unauthenticated visitors to the login page.

    Wrapping the builder means the guard cannot be written incorrectly
    at one call site and correctly at another -- the mistake that left
    /admin reachable by any signed-in user, and /shutdown reachable by
    anyone at all.
    """

    @wraps(page_builder)
    def guarded(*args, **kwargs):
        if not is_authenticated():
            ui.navigate.to("/")
            return None
        return page_builder(*args, **kwargs)

    return guarded


def require_admin(page_builder):
    """Restricts a page to admin accounts."""

    @wraps(page_builder)
    def guarded(*args, **kwargs):
        if not is_authenticated():
            ui.navigate.to("/")
            return None
        if not get_is_admin():
            ui.notify(
                "Admin access is required to access this page.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            ui.navigate.to("/")
            return None
        return page_builder(*args, **kwargs)

    return guarded
