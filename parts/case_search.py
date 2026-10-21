#!/usr/bin/env python3

"""
case_search.py

One search box, in the top bar, over the whole case: evidence, rooms,
agents, people, notes and files.

Each page has its own search above its table, but finding a serial
number, or everything a name turns up in, meant guessing which page to
look on. This looks on all of them at once and lists what it found; a
result opens its page with that page's own search already filled in.

search_case() is a plain function, apart from the dialog, so it can be
tested without a browser. navbar.py draws the button.
"""

from dataclasses import dataclass
from urllib.parse import quote

from nicegui import ui
from sqlalchemy import or_

from auth import require_session
from models import (
    Agents,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
    get_session,
)
from utils import evidence_number_key, room_label_key

# Shorter than this matches nearly everything.
MIN_LENGTH = 2

# Enough to find something; a search that matches more is too broad.
MAX_HITS = 60


@dataclass
class Hit:
    kind: str       # "Item", "Room", ...
    title: str      # what the record is called
    found: str      # the field it matched, and that field's text
    route: str      # its page, with that page's search filled in


# What is searched, page by page: the model, its page, the columns with
# the label each has on screen, and how a record is named.
SOURCES = [
    (
        "Item", Evidence, "/evidence",
        [
            ("EVIDNUM", "Item No."), ("EVIDDESC", "Description"),
            ("EVIDMODELNUMBER", "Model #"), ("EVIDSERIALNUMBER", "Serial #"),
            ("EVIDLOCROOM", "Room"), ("EVIDLOCROOMDETAIL", "Where"),
            ("EVIDFOUNDBY", "Found By"),
            ("EVIDFOUNDBYWITNESS", "Witnessed By"),
            ("EVIDTRIAGEDBY", "Triaged By"), ("EVIDNOTE", "Notes"),
        ],
        lambda e: f"Item {e.EVIDNUM}: {e.EVIDDESC or ''}",
    ),
    (
        "Room", Rooms, "/rooms",
        [
            ("ROOMLABEL", "Room Label"), ("ROOMDESC", "Description"),
            ("ROOMFIRSTAGENT", "First Agent"),
            ("ROOMSECONDAGENT", "Second Agent"), ("ROOMNOTE", "Notes"),
        ],
        lambda r: f"Room {r.ROOMLABEL} ({r.ROOMDESC or ''})",
    ),
    (
        "Agent", Agents, "/agents",
        [
            ("AGENTNAME", "Name"), ("AGENTPARENTAGENCY", "Agency"),
            ("AGENTPRIMARYROLE", "Role"), ("AGENTPHONE", "Phone"),
            ("AGENTEMAIL", "Email"), ("AGENTNOTE", "Notes"),
        ],
        lambda a: a.AGENTNAME or "",
    ),
    (
        "Person", Persons, "/persons",
        [
            ("PERSONNAME", "Name"), ("PERSONDOB", "DOB"),
            ("PERSONADDRESS", "Address"), ("PERSONPHONE", "Phone"),
            ("PERSONNOTE", "Notes"),
        ],
        lambda p: p.PERSONNAME or "",
    ),
    (
        "Note", Notes, "/notes",
        [("NOTETEXT", "Note"), ("NOTEAUTHOR", "Author")],
        lambda n: f"Note by {n.NOTEAUTHOR or 'unknown'}, {n.NOTEDATETIME or ''}",
    ),
    (
        "File", UploadedFiles, "/uploads",
        [
            ("FILENAME", "File name"), ("FILESHA256", "SHA-256"),
            ("FILEUPLOADEDBY", "Added by"),
        ],
        lambda f: f.FILENAME or "",
    ),
]

# The order results are listed in within each kind.
_ORDER = {
    "Item": lambda e: evidence_number_key(e.EVIDNUM),
    "Room": lambda r: room_label_key(r.ROOMLABEL),
}


def _like(text: str) -> str:
    """A LIKE pattern matching text anywhere, with % and _ taken literally."""
    escaped = (
        text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escaped}%"


def _snippet(value: str, text: str, width: int = 70) -> str:
    """The part of a long value around what matched."""
    value = " ".join(str(value).split())
    if len(value) <= width:
        return value
    at = max(0, value.lower().find(text.lower()) - width // 3)
    piece = value[at:at + width]
    return ("..." if at else "") + piece + ("..." if at + width < len(value) else "")


def search_case(text: str) -> list[Hit]:
    """Every record whose text contains `text`, ignoring case.

    Nothing for fewer than MIN_LENGTH characters. Attachments are found by
    their name, fingerprint and who added them; their contents are never
    read.
    """
    text = (text or "").strip()
    if len(text) < MIN_LENGTH:
        return []

    pattern = _like(text)
    hits: list[Hit] = []
    with get_session() as session:
        for kind, model, route, columns, name in SOURCES:
            matches = (
                session.query(model)
                .filter(or_(*(
                    getattr(model, column).ilike(pattern, escape="\\")
                    for column, _label in columns
                )))
                .all()
            )
            if kind in _ORDER:
                matches.sort(key=_ORDER[kind])
            for record in matches:
                column, label = next(
                    (
                        (column, label) for column, label in columns
                        if text.lower()
                        in str(getattr(record, column) or "").lower()
                    ),
                    # The database and Python can disagree about the case
                    # of a letter outside English.
                    columns[0],
                )
                value = _snippet(getattr(record, column), text)
                hits.append(Hit(
                    kind=kind,
                    title=name(record),
                    found=f"{label}: {value}",
                    route=f"{route}?find={quote(text)}",
                ))
                if len(hits) >= MAX_HITS:
                    return hits
    return hits


# ----- The button and its dialog -----
def search_button(classes: str = "") -> None:
    """The search button in the top bar, and the dialog it opens."""
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-4"):
        ui.label("Search the case").classes("text-lg font-bold")
        box = ui.input(
            placeholder="A serial number, a name, a word from a note...",
        ).props("autofocus clearable outlined dense").classes("w-full")
        said = ui.label().classes("text-sm text-[var(--vsp-gray)]")
        results = ui.column().classes("w-full gap-1 max-h-[60vh] overflow-y-auto")

        @require_session
        def show(_event=None) -> None:
            results.clear()
            text = (box.value or "").strip()
            if len(text) < MIN_LENGTH:
                said.set_text(
                    f"Type at least {MIN_LENGTH} characters."
                    if text else ""
                )
                return
            hits = search_case(text)
            if not hits:
                said.set_text(f'Nothing in this case matches "{text}".')
                return
            said.set_text(
                f"{len(hits)}{'+' if len(hits) >= MAX_HITS else ''} found. "
                "Choose one to open its page."
            )
            with results:
                for hit in hits:
                    with ui.row().classes(
                        "search-hit w-full items-start no-wrap gap-3 p-2 "
                        "rounded cursor-pointer"
                    ).on("click", lambda route=hit.route: ui.navigate.to(route)):
                        ui.badge(hit.kind).props("outline").classes("mt-1")
                        with ui.column().classes("gap-0"):
                            ui.label(hit.title).classes("text-sm font-semibold")
                            ui.label(hit.found).classes(
                                "text-xs text-[var(--vsp-gray)]"
                            )

        box.on_value_change(show)

        with ui.row().classes("w-full justify-end"):
            ui.button("Close", on_click=dialog.close, color="transparent").props(
                "flat"
            ).classes("p-3 hover-border-blue")

    ui.button(
        icon="search",
        on_click=dialog.open,
    ).props('flat round dense color=white aria-label="Search the case"').classes(
        f"p-2 hover-border-blue {classes}"
    ).tooltip("Search the case")
