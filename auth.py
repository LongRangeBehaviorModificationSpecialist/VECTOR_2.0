#!/usr/bin/env python3

"""
auth.py

Session state and route guards.

Deliberately imports nothing from the rest of the application. Every
page module previously reached into main.py for these three helpers,
while main.py imported the pages -- a cycle that forced function-level
imports throughout the codebase and left report routes unregistered
until someone happened to visit /reports.
"""

from functools import wraps

from nicegui import app, ui


# ----- Session state -----
def is_authenticated() -> bool:
    """Checks if the current user is signed in (defaults to False)."""
    try:
        return app.storage.user.get("authenticated", False)
    except Exception:
        return False


def get_current_user_name() -> str:
    """Gets the current username (defaults to empty)."""
    try:
        return app.storage.user.get("user_name", "")
    except Exception:
        return ""


def get_is_admin() -> bool:
    """Checks if the current user is an admin (defaults to False)."""
    try:
        return app.storage.user.get("is_admin", False)
    except Exception:
        return False


def sign_in(user_name: str, is_admin: bool) -> None:
    """Records a successful authentication in the session."""
    app.storage.user["authenticated"] = True
    app.storage.user["user_name"] = user_name
    app.storage.user["is_admin"] = is_admin


def sign_out() -> None:
    """Clears the session."""
    app.storage.user["authenticated"] = False
    app.storage.user["user_name"] = ""
    app.storage.user["is_admin"] = False


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
                "Admin access required.",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            ui.navigate.to("/")
            return None
        return page_builder(*args, **kwargs)

    return guarded
