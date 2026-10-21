#!/usr/bin/env python3

"""
drafts.py

Keeps what has been typed into an add form until it is saved.

A form filled in and not yet saved went with the page: an idle sign-out,
a tablet dropping off the Wi-Fi, a page reloaded by mistake, and an item
described in full had to be described again. What is typed is kept now,
as it is typed, and put back the next time the form opens -- for the same
account, on the same browser -- until it is saved, or cleared with Clear.

Kept in the browser's own server-side session store (app.storage.user),
not in the case database: a draft is not part of the case until it is
saved.
"""

DRAFTS = "drafts"


def _store():
    """This browser's own storage. Raises outside a browser request."""
    from nicegui import app
    return app.storage.user


def _key(page: str) -> str:
    from auth import get_current_user_name
    return f"{get_current_user_name()}|{page}"


def load_draft(page: str) -> dict:
    """What was typed on this page's add form and not saved, or {}."""
    try:
        draft = dict(_store().get(DRAFTS, {})).get(_key(page), {})
    except Exception:
        # No request in scope: nothing to restore.
        return {}
    return dict(draft) if isinstance(draft, dict) else {}


def save_draft(page: str, values: dict) -> None:
    """Keeps these values for the page; nothing typed removes the draft."""
    try:
        drafts = dict(_store().get(DRAFTS, {}))
        if values:
            drafts[_key(page)] = dict(values)
        else:
            drafts.pop(_key(page), None)
        _store()[DRAFTS] = drafts
    except Exception:
        # A draft that cannot be kept costs only the convenience.
        pass


def clear_draft(page: str) -> None:
    """Forgets the page's draft: it has been saved, or cleared."""
    save_draft(page, {})
