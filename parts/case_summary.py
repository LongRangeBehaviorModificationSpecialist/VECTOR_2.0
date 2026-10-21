#!/usr/bin/env python3

"""
case_summary.py

What the Home page shows about the open case: how much has been recorded
-- items, rooms, agents, people, notes, files -- and a short list of what
to check before leaving the scene.

The checks are the things that are easy to miss at the end of a long
search and awkward to put right afterwards: a room with only one agent
named, an item nobody marked as photographed or answered triage for, the
case's end time left blank, and changes made since the last export. None
of them stops anything; each says what it found and where to fix it.

The counting and the checks are plain functions, apart from the page, so
they can be tested without a browser. home_page.py draws them.
"""

from dataclasses import dataclass

from nicegui import ui
from sqlalchemy import func

from live import refresh_on_change
from models import (
    Agents,
    AuditLog,
    Cases,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
    get_session,
)
from utils import evidence_number_key, room_label_key


# The pages, in the order an agent works through them.
COUNTED = [
    ("Items", Evidence, "/evidence"),
    ("Rooms", Rooms, "/rooms"),
    ("Agents", Agents, "/agents"),
    ("People", Persons, "/persons"),
    ("Notes", Notes, "/notes"),
    ("Files", UploadedFiles, "/uploads"),
]

# Audit actions that change the case. An export after the last of these
# holds everything; one before it does not.
CASE_CHANGES = ("CREATE", "UPDATE", "DELETE", "IMPORT", "DELETE_ALL", "DEMO_SEED")


@dataclass
class Check:
    """One thing to check before leaving."""
    ok: bool
    text: str
    route: str = ""      # where to put it right; "" for the Home page itself
    button: str = ""     # what the button to it says


def case_counts() -> list[tuple[str, int, str]]:
    """(label, how many, page) for each kind of record in the case."""
    with get_session() as session:
        return [
            (label, session.query(func.count(model.Z_PK)).scalar() or 0, route)
            for label, model, route in COUNTED
        ]


def _listed(labels: list[str], limit: int = 8) -> str:
    """"3, 7 and 12", shortened when there are many."""
    shown = [str(label) for label in labels[:limit]]
    if len(labels) > limit:
        return ", ".join(shown) + f" and {len(labels) - limit} more"
    if len(shown) > 1:
        return ", ".join(shown[:-1]) + " and " + shown[-1]
    return shown[0] if shown else ""


def _plural(count: int, one: str, many: str) -> str:
    return one if count == 1 else many


def scene_checks() -> list[Check]:
    """What to look at before leaving the scene, ok or not.

    Empty when no case is open: there is nothing to check yet.
    """
    with get_session() as session:
        case = session.query(Cases).order_by(Cases.Z_PK).first()
        if case is None:
            return []

        rooms = sorted(
            session.query(Rooms).all(),
            key=lambda room: room_label_key(room.ROOMLABEL),
        )
        items = sorted(
            session.query(Evidence).all(),
            key=lambda item: evidence_number_key(item.EVIDNUM),
        )

        ended = bool((case.CASEDATETIMEEND or "").strip())
        short_rooms = [
            room.ROOMLABEL for room in rooms
            if not (room.ROOMFIRSTAGENT or "").strip()
            or not (room.ROOMSECONDAGENT or "").strip()
        ]
        not_photographed = [
            item.EVIDNUM for item in items
            if (item.EVIDPICTAKEN or "").strip() != "Yes"
        ]
        triage_unanswered = [
            item.EVIDNUM for item in items
            if not (item.EVIDTRIAGED or "").strip()
        ]

        last_export = (
            session.query(func.max(AuditLog.id))
            .filter(AuditLog.action == "EXPORT")
            .scalar()
        )
        last_change = (
            session.query(func.max(AuditLog.id))
            .filter(AuditLog.action.in_(CASE_CHANGES))
            .scalar()
        )

    checks = [
        Check(
            ended,
            "The case's end date and time are filled in."
            if ended else
            "The case has no end date and time yet. Every report prints "
            "them.",
            "/cases", "Case page",
        ),
    ]

    if not rooms:
        checks.append(Check(False, "No rooms have been entered.", "/rooms",
                            "Rooms page"))
    else:
        checks.append(Check(
            not short_rooms,
            "Every room has two agents named."
            if not short_rooms else
            f"{_plural(len(short_rooms), 'Room', 'Rooms')} "
            f"{_listed(short_rooms)} "
            f"{_plural(len(short_rooms), 'has', 'have')} fewer than two "
            "agents named.",
            "/rooms", "Rooms page",
        ))

    if not items:
        checks.append(Check(False, "No evidence has been entered.",
                            "/evidence", "Evidence page"))
    else:
        checks.append(Check(
            not not_photographed,
            "Every item is marked as photographed."
            if not not_photographed else
            f"{_plural(len(not_photographed), 'Item', 'Items')} "
            f"{_listed(not_photographed)} "
            f"{_plural(len(not_photographed), 'is', 'are')} not marked as "
            "photographed.",
            "/evidence", "Evidence page",
        ))
        checks.append(Check(
            not triage_unanswered,
            "Every item has an answer for Item Triaged."
            if not triage_unanswered else
            f"{_plural(len(triage_unanswered), 'Item', 'Items')} "
            f"{_listed(triage_unanswered)} "
            f"{_plural(len(triage_unanswered), 'has', 'have')} no answer for "
            "Item Triaged.",
            "/evidence", "Evidence page",
        ))

    exported = last_export is not None and (
        last_change is None or last_export > last_change
    )
    checks.append(Check(
        exported,
        "The case was exported after its last change."
        if exported else
        ("The case has not been exported yet." if last_export is None
         else "The case has changed since it was last exported.")
        + " Use Export Case Data below.",
    ))
    return checks


# ----- On the Home page -----
def case_overview() -> None:
    """The counts and the checklist, kept up to date as entries are made
    on any device."""
    # Redrawn with every entry on any device; the checklist stays open
    # or closed as it was left.
    opened = {"value": False}

    @ui.refreshable
    def overview() -> None:
        checks = scene_checks()
        if not checks:
            # No case open: Start New Case is the next step, and the
            # page already says so.
            return

        with ui.column().classes("w-full max-w-3xl mx-auto items-center gap-3 mb-2"):

            with ui.row().classes("w-full justify-center gap-3"):
                for label, count, route in case_counts():
                    with ui.card().classes(
                        "case-count cursor-pointer items-center px-5 py-3 gap-0"
                    ).on("click", lambda route=route: ui.navigate.to(route)):
                        ui.label(str(count)).classes("text-2xl font-bold")
                        ui.label(label).classes("text-xs uppercase tracking-wide")

            to_check = [check for check in checks if not check.ok]
            title = (
                "Before you leave the scene: all checked"
                if not to_check else
                f"Before you leave the scene: {len(to_check)} "
                f"{_plural(len(to_check), 'thing', 'things')} to check"
            )
            with ui.expansion(
                title,
                icon="checklist",
                value=opened["value"],
                on_value_change=lambda event: opened.update(value=event.value),
            ).classes(
                "w-full rounded-lg border border-[#3a3a3a]"
            ).props('header-class="text-base font-semibold"'):
                for check in checks:
                    with ui.row().classes("w-full items-center no-wrap gap-3 py-1"):
                        ui.icon(
                            "check_circle" if check.ok else "warning",
                            color="positive" if check.ok else "warning",
                        ).classes("text-xl")
                        ui.label(check.text).classes("text-sm grow")
                        if check.route and not check.ok:
                            ui.button(
                                check.button or "Open",
                                on_click=lambda route=check.route:
                                    ui.navigate.to(route),
                            ).props("flat dense no-caps").classes(
                                "hover-border-blue"
                            )

    overview()
    refresh_on_change(overview.refresh)
