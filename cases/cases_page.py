#!/usr/bin/env python3

"""
cases_page.py — NiceGUI conversion of Flask cases blueprint routes.

Consolidates four Flask routes into one interactive page:
    /case_list       →  table display + delete
    /case_add_page    →  add form (with jurisdiction from JURISDICTIONS)
    /case_update      →  inline edit dialog
    /case_delete      →  delete with confirmation
"""

from nicegui import ui

from main_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler,
)
from models import get_session, Cases
from navbar import build_navbar
from program.inc.jurisdictions import JURISDICTIONS


NOTIFICATION_TIMEOUT = 1500


# ── Helper: Load jurisdiction options ─────────────────────────
def load_jurisdiction_options() -> list[str]:
    """
    Returns jurisdiction choices from JURISDICTIONS.
    Handles both plain-string and (value, label) tuple formats.
    """

    if not JURISDICTIONS:
        return []
    if isinstance(JURISDICTIONS[0], tuple):
        return [j[1] for j in JURISDICTIONS]
    return list(JURISDICTIONS)


# ── Main Page Builder ────────────────────────────────────────
def build_cases_page():
    """Builds the full Cases page UI."""

    # ── Header / Navbar ──────────────────────────────────────

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label("Case Management").classes("text-2xl font-bold mb-4")

        # ── Input Form ────────────────────────────────────────────
        with ui.card().classes("w-full max-w-lg p-6 mx-auto"):
            ui.label(
                "Open New Case"
            ).classes("text-lg font-semibold mb-4")

            case_number_input = ui.input(
                label="Case Number"
            ).classes("w-full")
            case_number_input.props("autofocus")

            location_input = ui.input(
                label="Location"
            ).classes("w-full")

            jurisdiction_combo = ui.select(
                options=load_jurisdiction_options(),
                label="Jurisdiction",
                with_input=True,
                new_value_mode="add",
            ).classes("w-full")

            # ── Date/Time Started ──────────────────────────────────
            ui.label("Date/Time Started").classes("text-sm font-medium mb-1")
            with ui.row().classes("w-full gap-2"):
                case_date_begin = ui.date_input(
                    label="Date",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-grow")
                case_time_begin = ui.time_input(
                    label="Time",
                    placeholder="HH:MM",
                ).classes("flex-grow")

            # case_date_time_end_input = ui.input(
            #     label="Date/Time Ended",
            #     placeholder="YYYY-MM-DD HH:MM (optional)",
            # ).classes("w-full")

            # ── Date/Time Ended ────────────────────────────────────
            ui.label(
                "Date/Time Ended (optional)"
            ).classes("text-sm font-medium mb-1 mt-4")
            with ui.row().classes("w-full gap-2"):
                case_date_end = ui.date_input(
                    label="Date",
                    placeholder="YYYY-MM-DD",
                ).classes("flex-grow")
                case_time_end = ui.time_input(
                    label="Time",
                    placeholder="HH:MM",
                ).classes("flex-grow")

            # ── Buttons ─────────────────────────────────────────
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form():
                    case_number_input.value = ""
                    location_input.value = ""
                    jurisdiction_combo.value = None
                    case_date_begin.value = None
                    case_time_begin.value = None
                    case_date_end.value = None
                    case_time_end.value = None
                    ui.notify(
                        "Form cleared",
                        type="info",
                        timeout=NOTIFICATION_TIMEOUT,
                    )

                def on_submit():
                    # ── Required field validation (InputRequired) ──
                    case_number = case_number_input.value
                    if not case_number:
                        ui.notify(
                            "Case Number is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    location = location_input.value
                    if not location:
                        ui.notify(
                            "Location is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    jurisdiction = jurisdiction_combo.value
                    if not jurisdiction:
                        ui.notify(
                            "Jurisdiction is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    date_begin = case_date_begin.value
                    if not date_begin:
                        ui.notify(
                            "Date/Time Started is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    time_begin = case_time_begin.value or "00:00"

                    datetime_begin = f"{date_begin} {time_begin}"

                    # End date/time is optional
                    date_end = case_date_end.value or None
                    time_end = case_time_end.value or None
                    if date_end:
                        datetime_end = f"{date_end} {time_end or '00:00'}"
                    else:
                        datetime_end = None

                    try:
                        with get_session() as session:
                            # Check for duplicate case number
                            existing = (
                                session.query(Cases)
                                .filter_by(case_number=case_number)
                                .first()
                            )
                            if existing:
                                ui.notify(
                                    f"Case '{case_number}' already "
                                    "exists. Please use a unique case "
                                    "number.",
                                    type="negative",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                return

                            new_case = Cases(
                                case_number=case_number,
                                location=location,
                                jurisdiction=jurisdiction,
                                case_date_time_begin=datetime_begin,
                                case_date_time_end=datetime_end,
                            )
                            session.add(new_case)

                        ui.notify(
                            f"Case {case_number} was added successfully",
                            type="positive",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        clear_form()
                        refresh_cases_table()

                    except Exception:
                        ui.notify(
                            "An error occurred while creating the case. "
                            "Please check the information and try again.",
                            type="negative",
                            timeout=NOTIFICATION_TIMEOUT,
                        )

                ui.button(
                    "Clear",
                    on_click=clear_form,
                ).props("outline")
                ui.button(
                    "Open New Case",
                    on_click=on_submit,
                ).props("unelevated")

        # ── Existing Cases Table ─────────────────────────────────
        ui.separator().classes("my-6")
        ui.label(
            "Existing Cases"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_cases_table():
            """Re-renders the cases table from the database."""

            table_container.clear()

            with get_session() as session:
                cases = session.query(Cases).all()

                if not cases:
                    with table_container:
                        ui.label(
                            "No cases in the database yet"
                        ).classes("text-gray-500 italic")
                    return

                # Build row_data INSIDE the session — BEFORE it closes
                row_data = [
                    {
                        "id": r.id,
                        "case_number": r.case_number or "",
                        "location": r.location or "",
                        "jurisdiction": r.jurisdiction or "",
                        "case_date_time_begin": r.case_date_time_begin or "",
                        "case_date_time_end": r.case_date_time_end or "",
                    }
                    for r in cases
                ]

            # Now safe to create the table outside the session
            with table_container:
                column_defs = [
                    {
                        "name": "case_number",
                        "label": "Case Number",
                        "field": "case_number",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "location",
                        "label": "Location",
                        "field": "location",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "jurisdiction",
                        "label": "Jurisdiction",
                        "field": "jurisdiction",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "datetime_begin",
                        "label": "Started",
                        "field": "case_date_time_begin",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "datetime_end",
                        "label": "Ended",
                        "field": "case_date_time_end",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "actions",
                        "label": "Actions",
                        "field": "actions",
                        "sortable": False,
                        "align": "center",
                    },
                ]

                table = ui.table(
                    columns=column_defs,
                    rows=row_data,
                    row_key="id",
                )
                table.props("dense flat")

                # ── Slot: Actions column ──
                table.add_slot(
                    "body-cell-actions",
                    """
                    <q-td :props="props">
                        <div class="row no-wrap gap-1">
                            <q-btn dense flat color="primary"
                                icon="edit" size="sm"
                                @click="$parent.$emit('edit', props.row)" />
                            <q-btn dense flat color="negative"
                                icon="delete" size="sm"
                                @click="$parent.$emit('delete', props.row)" />
                        </div>
                    </q-td>
                """,
                )

                # ── Edit dialog ──────────────────────────────────
                def open_edit_dialog(e):
                    row = e.args
                    with ui.dialog() as edit_dialog, ui.card().classes(
                        "w-full max-w-lg p-6"
                    ):
                        ui.label(
                            f"Edit Case: {row['case_number']}"
                        ).classes("text-lg font-semibold mb-4")

                        edit_case_number = ui.input(
                            label="Case Number",
                            value=row["case_number"],
                        ).classes("w-full")
                        
                        edit_location = ui.input(
                            label="Location",
                            value=row["location"],
                        ).classes("w-full")
                        
                        edit_jurisdiction = ui.select(
                            options=load_jurisdiction_options(),
                            label="Jurisdiction",
                            value=row["jurisdiction"],
                            with_input=True,
                            new_value_mode="add",
                        ).classes("w-full")

                        existing_begin_parts = (
                            row["case_date_time_begin"] or ""
                        ).split(" ")
                        
                        existing_begin_date = (
                            existing_begin_parts[0]
                            if len(existing_begin_parts) >= 1 
                            else None
                        )

                        existing_begin_time = (
                            existing_begin_parts[1]
                            if len(existing_begin_parts) >= 2
                            else None
                        )

                        existing_end_parts = (
                            row["case_date_time_end"] or ""
                        ).split(" ")
                        
                        existing_end_date = (
                            existing_end_parts[0]
                            if len(existing_end_parts) >= 1
                            else None
                        )

                        existing_end_time = (
                            existing_end_parts[1] 
                            if len(existing_end_parts) >= 2
                            else None
                        )

                        ui.label(
                            "Date/Time Started"
                        ).classes("text-sm font-medium mb-1")
                        
                        with ui.row().classes("w-full gap-2"):

                            edit_date_begin = ui.date_input(
                                label="Date",
                                value=existing_begin_date,
                            ).classes("flex-grow")
                            
                            edit_time_begin = ui.time_input(
                                label="Time",
                                value=existing_begin_time,
                            ).classes("flex-grow")

                        ui.label(
                            "Date/Time Ended (optional)"
                        ).classes("text-sm font-medium mb-1 mt-4")
                        
                        with ui.row().classes("w-full gap-2"):

                            edit_date_end = ui.date_input(
                                label="Date",
                                value=existing_end_date,
                            ).classes("flex-grow")
                            
                            edit_time_end = ui.time_input(
                                label="Time",
                                value=existing_end_time,
                            ).classes("flex-grow")

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"
                        ):
                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                            ).props("flat")

                            def on_save_update():
                                with get_session() as session:
                                    case = (
                                        session.query(
                                            Cases
                                        )
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if case:
                                        case.case_number = (
                                            edit_case_number.value or ""
                                        )
                                        case.location = edit_location.value or ""
                                        case.jurisdiction = (
                                            edit_jurisdiction.value or ""
                                        )

                                        # Combine date + time
                                        begin_date = (
                                            edit_date_begin.value 
                                            or ""
                                        )
                                        begin_time = (
                                            edit_time_begin.value
                                            or "00:00"
                                        )
                                        case.case_date_time_begin = (
                                            f"{begin_date} {begin_time}"
                                            if begin_date else ""
                                        )

                                        end_date = (
                                            edit_date_end.value 
                                            or ""
                                        )
                                        if end_date:
                                            end_time = (
                                                edit_time_end.value 
                                                or "00:00"
                                            )
                                            case.case_date_time_end = (
                                                f"{end_date} {end_time}"
                                            )
                                        else:
                                            case.case_date_time_end = ""

                                ui.notify(
                                    f"Case {edit_case_number.value} "
                                    "information was updated successfully",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                edit_dialog.close()
                                refresh_cases_table()

                            ui.button(
                                "Save",
                                on_click=on_save_update,
                            ).props("unelevated")

                    edit_dialog.open()

                # ── Delete confirmation dialog ──────────────────
                def open_delete_dialog(e):
                    row = e.args
                    with ui.dialog() as delete_dialog, ui.card().classes(
                        "max-w-sm p-6"
                    ):
                        ui.label(
                            "Confirm Deletion"
                        ).classes("text-lg font-semibold mb-2")
                        ui.label(
                            f"Are you sure you want to delete "
                            f"case {row['case_number']}?"
                        ).classes("mb-4")

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                            ).props("flat")

                            def on_confirm_delete():
                                with get_session() as session:
                                    case = (
                                        session.query(
                                            Cases
                                        )
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if case:
                                        case_number = case.case_number
                                        session.delete(case)
                                        # session.commit()
                                    else:
                                        case_number = row["case_number"]

                                ui.notify(
                                    f"{case_number} has been deleted "
                                    "successfully",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                delete_dialog.close()
                                refresh_cases_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

    # Initial render
    refresh_cases_table()


# ── Page Registration ────────────────────────────────────────
@ui.page("/cases")
def cases_page():
    build_cases_page()


if __name__ in {"__main__", "__mp_main__"}:
    from models import init_db

    init_db()
    ui.run(title="VECTOR", port=8080)
