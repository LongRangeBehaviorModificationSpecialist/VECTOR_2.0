#!/usr/bin/env python3

"""
drafts.py

Keeps what has been typed into an add form until it is saved.

A form filled in and not yet saved went with the page: an idle sign-out,
a tablet dropping off the Wi-Fi, a page reloaded by mistake, and an item
described in full had to be described again. What is typed is kept now,
as it is typed, and put back the next time the form opens -- for the same
account, on the same browser, in the same case -- until it is saved, or
cleared with Clear.

Kept in the browser's own server-side session store (app.storage.user),
not in the case database: a draft is not part of the case until it is
saved. Which case it was typed in is kept with it. Start New Case, an
import or the demo case put a different case on this computer, and a
half-typed item from the last search must not turn up in the next one's
form, one click from being saved there.
"""

DRAFTS = "drafts"

# Audit actions after which the case on this computer is a different one.
CASE_REPLACED = ("DELETE_ALL", "IMPORT", "DEMO_SEED")


def _store():
    """This browser's own storage. Raises outside a browser request."""
    from nicegui import app
    return app.storage.user


def case_marker() -> str:
    """Which case a draft is typed in: the newest audit entry that cleared
    or replaced the case, so it changes whenever the case does."""
    from sqlalchemy import func

    from models import AuditLog, get_session

    try:
        with get_session() as session:
            newest = (
                session.query(func.max(AuditLog.id))
                .filter(AuditLog.action.in_(CASE_REPLACED))
                .scalar()
            )
    except Exception:
        # No database to ask: nothing typed now is put back later.
        return "unknown"
    return str(newest or 0)


def _account() -> str:
    from auth import get_current_user_name
    return f"{get_current_user_name()}|"


def _key(page: str, case: str) -> str:
    return f"{_account()}{case}|{page}"


def load_draft(page: str, case: str) -> dict:
    """What was typed on this page's add form in this case and not saved,
    or {}."""
    try:
        draft = dict(_store().get(DRAFTS, {})).get(_key(page, case), {})
    except Exception:
        # No request in scope: nothing to restore.
        return {}
    return dict(draft) if isinstance(draft, dict) else {}


def save_draft(page: str, case: str, values: dict) -> None:
    """Keeps these values for the page; nothing typed removes the draft.

    This account's drafts from any other case are dropped at the same
    time: that case has gone from this computer.
    """
    try:
        account = _account()
        this_case = f"{account}{case}|"
        drafts = {
            key: draft
            for key, draft in dict(_store().get(DRAFTS, {})).items()
            if not key.startswith(account) or key.startswith(this_case)
        }
        if values:
            drafts[_key(page, case)] = dict(values)
        else:
            drafts.pop(_key(page, case), None)
        _store()[DRAFTS] = drafts
    except Exception:
        # A draft that cannot be kept costs only the convenience.
        pass


def clear_draft(page: str, case: str) -> None:
    """Forgets the page's draft: it has been saved, or cleared."""
    save_draft(page, case, {})
