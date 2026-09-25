#!/usr/bin/env python3

"""
audit_page.py

Read-only view of the append-only audit trail. Admin only.

There is no edit and no delete here by design: the value of the trail is
that it cannot be adjusted after the fact, including from inside the
application that writes it.
"""

import json

from nicegui import ui

from auth import get_current_user_name, get_is_admin
import clock
from live import refresh_on_change
from models import audit_version, get_session, verify_audit_chain, AuditLog
from navbar import build_navbar


ACTION_CHOICES = [
    "All",
    "CREATE",
    "UPDATE",
    "DELETE",
    "DELETE_ALL",
    "IMPORT",
    "LOGIN",
    "LOGIN_FAILED",
    "LOGOUT_IDLE",
    "SETTING_CHANGED",
]

# A long case runs to thousands of entries, and all of them at once is a
# page nobody can read. Older ones are a button away rather than out of
# reach, which they were when the newest 500 were all the page would show.
PAGE_SIZE = 500


def _format_changes(before: str | None, after: str | None) -> str:
    """Renders changed fields as readable 'field: old -> new' lines."""
    try:
        before_data = json.loads(before) if before else {}
        after_data = json.loads(after) if after else {}
    except (json.JSONDecodeError, TypeError):
        return ""

    if not isinstance(before_data, dict):
        before_data = {}
    if not isinstance(after_data, dict):
        after_data = {}

    keys = list(dict.fromkeys([*after_data.keys(), *before_data.keys()]))
    lines = []
    for key in keys:
        old = before_data.get(key, "")
        new = after_data.get(key, "")
        old = "(blank)" if old in (None, "") else old
        new = "(blank)" if new in (None, "") else new
        lines.append(f"{key}: {old} -> {new}")
    return "\n".join(lines)


def show_chain_check() -> None:
    """Walks the fingerprint chain and says what it found."""
    intact, message = verify_audit_chain()

    with ui.dialog() as result, ui.card().classes("max-w-md p-6"):
        ui.label("Check of the audit trail").classes(
            "text-lg font-bold mb-2"
        )
        ui.label(message).classes(
            "text-sm mb-4 "
            + ("text-green-400" if intact else "text-red-400")
        )
        ui.label(
            "The check finds an entry changed or removed after it was "
            "written. It cannot prove the trail is complete on its own, "
            "because anyone able to write to the database could "
            "recompute the chain: keep exports, which carry the trail as "
            "it stood when they were made."
        ).classes("text-xs text-gray-400 mb-4")

        with ui.row().classes("w-full justify-end"):
            ui.button("Close", on_click=result.close).props("flat")

    result.open()


def build_audit_page() -> None:
    """Builds the audit trail page."""

    if not get_is_admin():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):

        ui.label("Audit Trail").classes("text-2xl font-bold m-4")

        ui.label(
            "Every change to case data, in the order it happened. "
            "Append-only -- entries cannot be edited or removed. Each "
            "entry is fingerprinted onto the one before it, and Check "
            "the trail walks that chain."
        ).classes("text-sm text-gray-400 mb-4 text-center max-w-2xl")

        with ui.row().classes(
            "w-full max-w-5xl justify-center gap-4 mb-2 items-end"
        ):
            action_filter = ui.select(
                options=ACTION_CHOICES,
                value="All",
                label="Action",
            ).classes("w-40")

            search_input = ui.input(
                label="Search who / record type / item",
            ).classes("w-72")

            ui.button(
                "Search",
                on_click=lambda: search_again(),
                color="var(--vsp-blue)",
            ).props("push").classes("text-[var(--vsp-white)]")

            ui.button(
                "Check the trail",
                on_click=lambda: show_chain_check(),
            ).props("flat").classes("text-[var(--vsp-blue)]")

        table_container = ui.column().classes(
            "w-full max-w-[1536px] px-2 mx-auto items-center gap-2"
        )

        shown = {"limit": PAGE_SIZE}

        def search_again() -> None:
            """A new search starts at the newest entries again."""
            shown["limit"] = PAGE_SIZE
            refresh_audit_table()

        def show_older() -> None:
            shown["limit"] += PAGE_SIZE
            refresh_audit_table()

        def refresh_audit_table() -> None:
            table_container.clear()

            with get_session() as session:
                query = session.query(AuditLog)

                if action_filter.value and action_filter.value != "All":
                    query = query.filter(
                        AuditLog.action == action_filter.value
                    )

                term = (search_input.value or "").strip()
                if term:
                    like = f"%{term}%"
                    query = query.filter(
                        AuditLog.actor.ilike(like)
                        | AuditLog.table_name.ilike(like)
                        | AuditLog.summary.ilike(like)
                    )

                matching = query.count()
                entries = (
                    query.order_by(AuditLog.id.desc())
                    .limit(shown["limit"])
                    .all()
                )

                rows = [
                    {
                        "id": entry.id,
                        # Stored in UTC, as the trail always has been;
                        # shown in this machine's time zone.
                        "ts_utc": clock.show_utc(entry.ts_utc),
                        "actor": entry.actor or "",
                        "action": entry.action or "",
                        "table_name": entry.table_name or "",
                        "summary": entry.summary or "",
                        "changes": _format_changes(entry.before, entry.after),
                    }
                    for entry in entries
                ]

                total = session.query(AuditLog).count()

            with table_container:
                if not rows:
                    ui.label(
                        "No audit entries match."
                    ).classes("text-gray-500 italic")
                    return

                counted = f"Showing {len(rows)} of {matching} entries"
                if matching != total:
                    counted += f" that match, out of {total} in the trail"
                ui.label(f"{counted}, most recent first.").classes(
                    "text-xs text-gray-500 mb-1"
                )

                columns = [
                    {
                        "name": "ts_utc",
                        "label": "When",
                        "field": "ts_utc",
                        # Most recent first already; as text the dates
                        # would sort by month, not by when.
                        "sortable": False,
                        "align": "left",
                    },
                    {
                        "name": "actor",
                        "label": "Who",
                        "field": "actor",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "action",
                        "label": "Action",
                        "field": "action",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "table_name",
                        "label": "Record type",
                        "field": "table_name",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "summary",
                        "label": "Item",
                        "field": "summary",
                        "align": "left",
                    },
                    {
                        "name": "changes",
                        "label": "What changed",
                        "field": "changes",
                        "align": "left",
                    },
                ]

                table = ui.table(
                    columns=columns,
                    rows=rows,
                    row_key="id",
                ).classes("w-full")

                table.props("dense flat wrap-cells")

                # Deletions have to stand out when scanning a long trail.
                table.add_slot(
                    "body-cell-action",
                    """
                    <q-td :props="props">
                        <span :class="props.row.action.indexOf('DELETE') === 0
                                ? 'text-red-500'
                                : props.row.action === 'UPDATE'
                                ? 'text-orange-400'
                                : props.row.action === 'CREATE'
                                ? 'text-green-500'
                                : 'text-blue-400'"
                              style="font-weight:600">
                            {{ props.row.action }}
                        </span>
                    </q-td>
                    """,
                )

                table.add_slot(
                    "body-cell-changes",
                    """
                    <q-td :props="props">
                        <div style="white-space:pre-wrap; font-size:11px;
                                    max-width:460px; line-height:1.5">
                            {{ props.row.changes }}
                        </div>
                    </q-td>
                    """,
                )

                if len(rows) < matching:
                    remaining = matching - len(rows)
                    ui.button(
                        f"Show {min(PAGE_SIZE, remaining)} older "
                        f"{'entry' if remaining == 1 else 'entries'}",
                        on_click=show_older,
                    ).props("flat").classes("text-[var(--vsp-blue)] mt-2")

        action_filter.on_value_change(lambda _: search_again())
        search_input.on("keydown.enter", search_again)

        refresh_audit_table()

        # Follows the trail itself rather than case data: a sign-in on
        # another device writes an entry and changes nothing else.
        refresh_on_change(refresh_audit_table, version=audit_version)
