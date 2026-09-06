#!/usr/bin/env python3

"""
cases_page.py

Consolidates four Flask routes into one interactive page:
    /case_list        →  table display + delete
    /case_add_page    →  add form (with jurisdiction from JURISDICTIONS)
    /case_update      →  inline edit dialog
    /case_delete      →  delete with confirmation
"""

from nicegui import ui

from home_page import confirm_new_case_handler
from main import get_current_user_name, get_is_admin
from models import get_session, Cases
from navbar import build_navbar
from utils import (
    required_input,
    required_select,
    load_jurisdiction_options,
    validate_case_data,
)


# ----- Main Page Builder -----
def build_cases_page() -> None:
    """Builds the full Cases page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Case Management"
        ).classes("text-2xl font-bold mb-4")

        # ----- Input Form -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            case_number_input = required_input(
                label="Case Number"
            ).classes("w-full")

            case_number_input.props("autofocus")

            location_input =required_input(
                label="Location"
            ).classes("w-full")

            jurisdiction_combo = required_select(
                options=load_jurisdiction_options(),
                label="Jurisdiction",
                with_input=True,
                new_value_mode="add",
            ).classes("w-full")

            # ----- Date/Time Started -----
            date_time_start = required_input(
                label="Date/Time Started",
                placeholder="YYYY-MM-DD HH:MM",
                ).props('mask="####-##-## ##:##"'
            ).classes("w-full")

            # ----- Date/Time Ended -----
            date_time_end = ui.input(
                label="Date/Time Ended",
                placeholder="YYYY-MM-DD HH:MM"
                ).props('mask="####-##-## ##:##"'
            ).classes("w-full")

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form() -> None:
                    case_number_input.value = ""
                    location_input.value = ""
                    jurisdiction_combo.value = None
                    date_time_start.value = None
                    date_time_end.value = None

                def on_submit() -> None:
                    case_number = case_number_input.value
                    location = location_input.value
                    jurisdiction = jurisdiction_combo.value
                    datetime_start = date_time_start.value
                    datetime_end = date_time_end.value

                    # ----- Required field validation -----
                    if not validate_case_data(
                        case_number=case_number,
                        location=location,
                        jurisdiction=jurisdiction,
                        datetime_start=datetime_start,
                    ):
                        return

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
                                    f"Case '{case_number}' already exists. "
                                    "Please use a unique case number.",
                                    type="warning",
                                    timeout=0,
                                    position="center",
                                    close_button="OK",
                                )
                                return

                            new_case = Cases(
                                case_number=case_number,
                                location=location,
                                jurisdiction=jurisdiction,
                                case_date_time_begin=datetime_start,
                                case_date_time_end=datetime_end,
                            )
                            session.add(new_case)

                        ui.notify(
                            f"Case {case_number} was added successfully.",
                            type="positive",
                            timeout=2000,
                            position="bottom",
                            close_button="OK",
                        )

                        clear_form()
                        refresh_cases_table()

                    except Exception:
                        ui.notify(
                            "An error occurred while creating the case. "
                            "Please check the information and try again.",
                            type="negative",
                            timeout=0,
                            position="center",
                            close_button="OK",
                        )

                ui.button(
                    "Clear",
                    on_click=clear_form,
                ).props("flat")

                ui.button(
                    "Open New Case",
                    on_click=on_submit,
                ).props("unelevated")

        # ----- Existing Cases Table -----
        ui.separator().classes("my-6")

        ui.label(
            "Current Case"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2")

        def refresh_cases_table() -> None:
            """Re-renders the cases table from the database."""

            table_container.clear()

            with get_session() as session:
                cases = session.query(Cases).all()
                if not cases:
                    with table_container:
                        ui.label("No cases in the database yet."
                            ).classes("text-gray-500 italic")
                    return

                # Build row_data INSIDE the session — BEFORE it closes
                row_data = [
                    {
                        "id": r.id,
                        "case_number": r.case_number or "",
                        "location": r.location or "",
                        "jurisdiction": r.jurisdiction or "",
                        "datetime_start": r.case_date_time_begin or "",
                        "datetime_end": r.case_date_time_end or "",
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
                        "name": "datetime_start",
                        "label": "Started",
                        "field": "datetime_start",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "datetime_end",
                        "label": "Ended",
                        "field": "datetime_end",
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

                # ----- Slot: Actions column -----
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
                    """
                )

                # ----- Edit dialog -----
                def open_edit_dialog(e) -> None:
                    row = e.args
                    with ui.dialog() as edit_dialog, ui.card().classes(
                        "w-full max-w-lg p-6"
                    ):

                        ui.label(f"Edit Case: {row['case_number']}"
                            ).classes("text-lg font-semibold mb-4")

                        edit_case_number = required_input(
                            label="Case Number",
                            value=row["case_number"],
                        ).classes("w-full")

                        edit_location = required_input(
                            label="Location",
                            value=row["location"],
                        ).classes("w-full")

                        edit_jurisdiction = required_select(
                            options=load_jurisdiction_options(),
                            label="Jurisdiction",
                            value=row["jurisdiction"],
                            with_input=True,
                            new_value_mode="add",
                        ).classes("w-full")

                        edit_datetime_begin = (
                            required_input(
                                label="Begin Date/Time",
                                value=row["datetime_start"],
                                placeholder="YYYY-MM-DD HH:MM",
                            )
                            .props('mask="####-##-## ##:##"')
                            .classes("w-full")
                        )

                        edit_datetime_end = (
                            ui.input(
                                label="End Date/Time",
                                value=row["datetime_end"],
                                placeholder="YYYY-MM-DD HH:MM",
                            )
                            .props('mask="####-##-## ##:##"')
                            .classes("w-full")
                        )

                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("Cancel", on_click=edit_dialog.close,
                                ).props("flat")

                            def on_save_update() -> None:

                                with get_session() as session:
                                    case = (
                                        session.query(Cases)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if case:
                                        case.case_number = (
                                            edit_case_number.value or ""
                                        )
                                        case.location = (
                                            edit_location.value or ""
                                        )
                                        case.jurisdiction = (
                                            edit_jurisdiction.value or ""
                                        )
                                        case.case_date_time_begin = (
                                            edit_datetime_begin.value or ""
                                        )
                                        case.case_date_time_end = (
                                            edit_datetime_end.value or ""
                                        )

                                ui.notify(
                                    f"Case {edit_case_number.value} "
                                    "information was updated.",
                                    type="positive",
                                    timeout=2000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                edit_dialog.close()
                                refresh_cases_table()

                            ui.button(
                                "Save",
                                on_click=on_save_update,
                            ).props("unelevated")

                    edit_dialog.open()

                # ----- Delete confirmation dialog -----
                def open_delete_dialog(e) -> None:

                    row = e.args

                    with ui.dialog() as delete_dialog, ui.card(
                        ).classes("max-w-sm p-6"
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

                            def on_confirm_delete() -> None:

                                with get_session() as session:
                                    case = (
                                        session.query(Cases)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if case:
                                        case_number = case.case_number
                                        session.delete(case)
                                    else:
                                        case_number = row["case_number"]

                                ui.notify(
                                    f"Case {case_number} has been deleted.",
                                    type="positive",
                                    timeout=2000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                delete_dialog.close()
                                refresh_cases_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#ef4444",
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

    # ----- Initial render -----
    refresh_cases_table()
