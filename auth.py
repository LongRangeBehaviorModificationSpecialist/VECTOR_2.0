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
from inspect import iscoroutinefunction
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
def _session_store():
    """This browser's own storage. Raises outside a browser request."""
    return app.storage.user


def _signed_in() -> bool:
    """Whether this browser signed in, with a session still current.

    A session is valid only while the generation counters it was
    stamped with at sign-in still match. That is what lets an admin end
    someone else's session; without the check, deleting an account left
    its session working until the browser closed.
    """
    try:
        store = _session_store()
        if not store.get("authenticated", False):
            return False

        if store.get("session_generation", 0) < global_generation():
            return False

        user_name = store.get("USERNAME", "")
        # A session stored before the keys were renamed has no USERNAME.
        # Treat it as signed out rather than letting it through nameless.
        if not user_name:
            return False

        if store.get("user_generation", 0) < user_generation(user_name):
            return False

        return True

    except Exception:
        # No request in scope; see the note above.
        return False


def password_change_pending() -> bool:
    """Whether this session signed in with a temporary password that has
    not been replaced yet."""
    try:
        return bool(_session_store().get("must_change_password", False))
    except Exception:
        # No request in scope; see the note above.
        return False


def is_authenticated() -> bool:
    """Checks if the current user is signed in (defaults to False).

    A temporary password -- a new account's, or one an administrator
    has just reset -- does not count. It opens one page, Change
    Password. It used to be a full sign-in: the change was offered once,
    and Home, or any page typed into the address bar, carried on without
    it, so a temporary password could stay in use for good.
    """
    return _signed_in() and not password_change_pending()


def signed_in_with_temporary_password() -> bool:
    """Signed in, but only to replace a temporary password."""
    return _signed_in() and password_change_pending()


def where_to_sign_in() -> str:
    """The page for a browser that is not fully signed in."""
    return "/change-password" if signed_in_with_temporary_password() else "/"


def get_current_user_name() -> str:
    """Gets the current username (defaults to empty)."""
    try:
        return _session_store().get("USERNAME", "")
    except Exception:
        # No request in scope; see the note above.
        return ""


def get_is_admin() -> bool:
    """Checks if the current user is an admin (defaults to False).

    Only while the session is current. An administrator's page left
    open after Sign Everyone Out, or after a password reset, could
    otherwise still create, reset and delete accounts.
    """
    if not is_authenticated():
        return False
    try:
        return bool(_session_store().get("ISADMIN", False))
    except Exception:
        # No request in scope; see the note above.
        return False


def sign_in(
        user_name: str,
        is_admin: bool,
        must_change_password: bool = False,
) -> None:
    """Records a successful authentication in the session.

    The generation counters are stamped here and checked on every
    request, which is what makes it possible to sign a user out
    remotely -- see invalidate_user_sessions(). With
    must_change_password the session opens Change Password and nothing
    else, until finish_password_change().
    """
    store = _session_store()
    store["authenticated"] = True
    store["USERNAME"] = user_name
    store["ISADMIN"] = is_admin
    store["must_change_password"] = bool(must_change_password)
    store["session_ended_notice"] = False
    store["session_generation"] = global_generation()
    store["user_generation"] = user_generation(user_name)


def finish_password_change(user_name: str, is_admin: bool) -> bool:
    """Makes this session a full sign-in once a temporary password has
    been replaced.

    Every other session of the account ends first -- including one
    opened somewhere else with the same temporary password, which could
    otherwise set a password of its own over this one. Returns False
    when those sessions could not be ended.
    """
    ended = invalidate_user_sessions(user_name)
    sign_in(user_name, is_admin)
    return ended


def sign_out() -> None:
    """Clears the session."""
    store = _session_store()
    store["authenticated"] = False
    store["USERNAME"] = ""
    store["ISADMIN"] = False
    store["must_change_password"] = False
    store["session_ended_notice"] = False
    store["session_generation"] = 0
    store["user_generation"] = 0


# ----- A page whose session has ended -----
# Ending a session -- deleting the account, resetting its password, Sign
# Everyone Out -- stopped the next page load, but a page already open
# kept working: it saved, deleted and uploaded until somebody moved off
# it, under the name of an account that might no longer exist. Each page
# now notices within a few seconds (see idle.py), and every save,
# delete, upload, import and export checks before it acts.
def note_session_ended() -> None:
    """Leaves word for the sign-in page that this device was signed out,
    so it can say so rather than simply appearing.

    Only for a session ended from elsewhere, which still reads as signed
    in here. Logout and the idle timeout clear the session themselves,
    and someone who pressed Logout needs no explanation.
    """
    try:
        store = _session_store()
        if store.get("authenticated", False):
            store["session_ended_notice"] = True
    except Exception:
        # No request in scope; see the note above.
        pass


def session_ended_notice() -> bool:
    """Whether this device was signed out from elsewhere.

    Kept until the next sign-in or Logout, rather than cleared once read:
    two actions refused on the same ended page each send it to the
    sign-in page, and the second visit lost the explanation.
    """
    try:
        return bool(_session_store().get("session_ended_notice", False))
    except Exception:
        # No request in scope; see the note above.
        return False


def leave_ended_session() -> None:
    """Sends a page whose session has ended to the sign-in page."""
    note_session_ended()
    ui.navigate.to(where_to_sign_in())


def require_session(handler):
    """Refuses an action from a page whose session has ended.

    For the handlers behind buttons, not for pages: a route checks the
    session as it is drawn, with require_login. An async handler -- the
    file upload -- stays async, so NiceGUI still awaits it.
    """
    if iscoroutinefunction(handler):
        @wraps(handler)
        async def async_guarded(*args, **kwargs):
            if not is_authenticated():
                leave_ended_session()
                return None

            return await handler(*args, **kwargs)

        return async_guarded

    @wraps(handler)
    def guarded(*args, **kwargs):
        if not is_authenticated():
            leave_ended_session()
            return None

        return handler(*args, **kwargs)

    return guarded


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


def _expired(record, now: datetime) -> bool:
    """Whether a failure record no longer counts for anything: its
    failures have aged out, and any lock it set has run out."""
    try:
        first_seen = datetime.fromisoformat(record.get("first_seen", ""))
        if now - first_seen <= timedelta(minutes=FAILURE_WINDOW_MINUTES):
            return False
        locked_until = record.get("locked_until")
        return not locked_until or datetime.fromisoformat(locked_until) <= now
    except (AttributeError, TypeError, ValueError):
        # Unreadable, so it can neither slow nor lock anybody.
        return True


def _without_expired(failures: dict) -> dict:
    """The failure records that still count.

    Every name ever tried used to stay on the list, and a name that was
    never an account is never cleared by a successful sign-in -- so
    anyone who could reach the port could grow it without limit, by
    trying made-up names.
    """
    now = _now()
    return {
        name: record for name, record in failures.items()
        if not _expired(record, now)
    }


def record_login_failure(user_name: str) -> int:
    """Counts one failed attempt. Returns the new failure count."""
    failures = _without_expired(_failures())
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
            ui.navigate.to(where_to_sign_in())
            return None

        return page_builder(*args, **kwargs)

    return guarded


def require_admin(page_builder):
    """Restricts a page to admin accounts."""

    @wraps(page_builder)
    def guarded(*args, **kwargs):
        if not is_authenticated():
            ui.navigate.to(where_to_sign_in())
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
