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

from home_page import confirm_new_case_handler
from auth import get_current_user_name, get_is_admin
from models import get_session, AuditLog
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
]


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


def build_audit_page() -> None:
    """Builds the audit trail page."""

    if not get_is_admin():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label("Audit Trail").classes("text-2xl font-bold m-4")

        ui.label(
            "Every change to case data, in the order it happened. "
            "Append-only -- entries cannot be edited or removed."
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
                on_click=lambda: refresh_audit_table(),
                color="var(--vsp-blue)",
            ).props("unelevated").classes("text-[var(--vsp-white)]")

        table_container = ui.column().classes(
            "w-full max-w-6xl mx-auto items-center gap-2"
        )

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

                entries = query.order_by(AuditLog.id.desc()).limit(500).all()

                rows = [
                    {
                        "id": entry.id,
                        "ts_utc": entry.ts_utc or "",
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

                ui.label(
                    f"Showing {len(rows)} of {total} entries, "
                    "most recent first."
                ).classes("text-xs text-gray-500 mb-1")

                columns = [
                    {
                        "name": "ts_utc",
                        "label": "When (UTC)",
                        "field": "ts_utc",
                        "sortable": True,
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

        action_filter.on_value_change(lambda _: refresh_audit_table())
        search_input.on("keydown.enter", lambda: refresh_audit_table())

        refresh_audit_table()
