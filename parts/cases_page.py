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

from main import get_current_user_name, get_is_admin
from models import get_session, Cases
from navbar import build_navbar
from utils import (
    required_input,
    required_select,
    load_jurisdiction_options,
    validate_case_entry,
)


# ----- Main Page Builder -----
def build_cases_page() -> None:
    """Builds the full Cases page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):

        ui.label("Case Management").classes("text-2xl font-bold mb-4")

        # ----- Input Form -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            CASENUMBER_input = required_input(label="Case Number"
            ).classes("w-full")

            CASENUMBER_input.props("autofocus")

            LOCATION_input =required_input(label="Location"
            ).classes("w-full")

            JURISDICTION_combo = required_select(
                options=load_jurisdiction_options(),
                label="Jurisdiction",
                with_input=True,
                new_value_mode="add",
            ).classes("w-full")

            # ----- Date/Time Started -----
            CASEDATETIMEBEGIN_input = required_input(
                label="Date/Time Started",
                placeholder="MM-DD-YYYY HH:MM",
                ).props('mask="##-##-#### ##:##"'
            ).classes("w-full")

            # ----- Date/Time Ended -----
            CASEDATETIMEEND_input = ui.input(
                label="Date/Time Ended",
                placeholder="MM-DD-YYYY HH:MM"
                ).props('mask="##-##-#### ##:##"'
            ).classes("w-full")

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form() -> None:
                    CASENUMBER_input.value = ""
                    LOCATION_input.value = ""
                    JURISDICTION_combo.value = None
                    CASEDATETIMEBEGIN_input.value = ""
                    CASEDATETIMEEND_input.value = ""

                def on_submit() -> None:
                    CASENUMBER = CASENUMBER_input.value
                    LOCATION = LOCATION_input.value
                    JURISDICTION = JURISDICTION_combo.value
                    CASEDATETIMEBEGIN = CASEDATETIMEBEGIN_input.value
                    CASEDATETIMEEND = CASEDATETIMEEND_input.value

                    # ----- Required field validation -----
                    if validate_case_entry(
                        stage="initial",
                        CASENUMBER=CASENUMBER,
                        LOCATION=LOCATION,
                        JURISDICTION=JURISDICTION,
                        CASEDATETIMEBEGIN=CASEDATETIMEBEGIN,
                    ):
                        return

                    try:
                        with get_session() as session:
                            # ----- Save to database -----
                            new_case = Cases(
                                CASENUMBER=CASENUMBER,
                                LOCATION=LOCATION,
                                JURISDICTION=JURISDICTION,
                                CASEDATETIMEBEGIN=CASEDATETIMEBEGIN,
                                CASEDATETIMEEND=CASEDATETIMEEND,
                            )
                            session.add(new_case)

                        ui.notify(
                            f"Case {CASENUMBER} was added.",
                            timeout=4000,
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
                        import traceback
                        traceback.print_exc()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                    color="transparent").props("flat"
                ).classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Open New Case",
                    on_click=on_submit,
                    color="var(--vsp-blue)").props("push"
                ).classes("text-[var(--vsp-white)]")

        # ----- Existing Cases Table -----
        ui.separator().classes("my-6")

        ui.label("Current Case").classes("text-xl font-bold mb-1")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2")

        def refresh_cases_table() -> None:
            """Re-renders the cases table from the database."""

            table_container.clear()

            with get_session() as session:
                cases = session.query(Cases).all()
                if not cases:
                    with table_container:
                        ui.label(
                            "No current active case"
                        ).classes("text-red italic")
                    return

                # Build row_data INSIDE the session — BEFORE it closes
                row_data = [
                    {
                        "Z_PK": r.Z_PK,
                        "CASENUMBER": r.CASENUMBER or "",
                        "LOCATION": r.LOCATION or "",
                        "JURISDICTION": r.JURISDICTION or "",
                        "CASEDATETIMEBEGIN": r.CASEDATETIMEBEGIN or "",
                        "CASEDATETIMEEND": r.CASEDATETIMEEND or "",
                    }
                    for r in cases
                ]

            # Now safe to create the table outside the session
            with table_container:
                column_defs = [
                    {
                        "name": "Z_PK",
                        "label": "ID #",
                        "field": "Z_PK",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "CASENUMBER",
                        "label": "Case Number",
                        "field": "CASENUMBER",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "LOCATION",
                        "label": "Location",
                        "field": "LOCATION",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "JURISDICTION",
                        "label": "Jurisdiction",
                        "field": "JURISDICTION",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "CASEDATETIMEBEGIN",
                        "label": "Started",
                        "field": "CASEDATETIMEBEGIN",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "CASEDATETIMEEND",
                        "label": "Ended",
                        "field": "CASEDATETIMEEND",
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
                    row_key="Z_PK",
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
                    with ui.dialog() as edit_dialog, ui.card(
                    ).classes("w-full max-w-lg p-6"):

                        ui.label(
                            f"Edit Case: {row['CASENUMBER']}"
                        ).classes("text-lg font-semibold mb-4")

                        CASENUMBER_input = required_input(
                            label="Case Number",
                            value=row["CASENUMBER"],
                        ).classes("w-full")

                        LOCATION_input = required_input(
                            label="Location",
                            value=row["LOCATION"],
                        ).classes("w-full")

                        JURISDICTION_input = required_select(
                            options=load_jurisdiction_options(),
                            label="Jurisdiction",
                            value=row["JURISDICTION"],
                            with_input=True,
                            new_value_mode="add",
                        ).classes("w-full")

                        CASEDATETIMEBEGIN_input = (
                            required_input(
                                label="Begin Date/Time",
                                value=row["CASEDATETIMEBEGIN"],
                                placeholder="MM-DD-YYYY HH:MM",
                            ).props('mask="##-##-#### ##:##"'
                        ).classes("w-full"))

                        CASEDATETIMEEND_input = (
                            ui.input(
                                label="End Date/Time",
                                value=row["CASEDATETIMEEND"],
                                placeholder="MM-DD-YYYY HH:MM",
                            ).props('mask="##-##-#### ##:##"'
                        ).classes("w-full"))

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"):

                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                                color="transparent").props("flat"
                            ).classes("text-[var(--vsp-blue)]")

                            def on_save_update() -> None:
                                CASENUMBER = CASENUMBER_input.value or ""
                                LOCATION = LOCATION_input.value or ""
                                JURISDICTION = (
                                    JURISDICTION_input.value or ""
                                )
                                CASEDATETIMEBEGIN = (
                                    CASEDATETIMEBEGIN_input.value or ""
                                )
                                CASEDATETIMEEND = (
                                    CASEDATETIMEEND_input.value or ""
                                )

                                if validate_case_entry(
                                    stage="update",
                                    CASENUMBER=CASENUMBER,
                                    LOCATION=LOCATION,
                                    JURISDICTION=JURISDICTION,
                                    CASEDATETIMEBEGIN=CASEDATETIMEBEGIN,
                                    row=row,
                                ):
                                    return

                                with get_session() as session:
                                    case = (
                                        session.query(Cases)
                                        .filter_by(Z_PK=row["Z_PK"])
                                        .first()
                                    )
                                    if case:
                                        case.CASENUMBER = CASENUMBER
                                        case.LOCATION = LOCATION
                                        case.JURISDICTION = JURISDICTION
                                        case.CASEDATETIMEBEGIN = (
                                            CASEDATETIMEBEGIN
                                        )
                                        case.CASEDATETIMEEND = CASEDATETIMEEND

                                ui.notify(
                                    f"Case {CASENUMBER} was updated.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                edit_dialog.close()
                                refresh_cases_table()

                            ui.button(
                                "Update",
                                on_click=on_save_update,
                                color="var(--vsp-blue)").props("push"
                            ).classes("text-[var(--vsp-white)]")

                    edit_dialog.open()

                # ----- Delete confirmation dialog -----
                def open_delete_dialog(e) -> None:
                    row = e.args
                    with ui.dialog() as delete_dialog, ui.card(
                        ).classes("max-w-sm p-6"
                    ):
                        ui.label(
                            "Confirm Deletion").classes(
                            "mb-3 text-lg font-bold text-[var(--vsp-blue)]"
                        )
                        ui.label(
                            f"Are you sure you want to delete "
                            f"case {row['CASENUMBER']}?"
                        ).classes("mb-4")

                        with ui.row().classes("w-full justify-end gap-2"):

                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                                color="transparent").props("flat"
                            ).classes("text-[var(--vsp-blue)]")

                            def on_confirm_delete() -> None:
                                with get_session() as session:
                                    case = (
                                        session.query(Cases)
                                        .filter_by(Z_PK=row["Z_PK"])
                                        .first()
                                    )
                                    if case:
                                        CASENUMBER = case.CASENUMBER
                                        session.delete(case)
                                    else:
                                        CASENUMBER = row["CASENUMBER"]

                                ui.notify(
                                    f"Case {CASENUMBER} has been deleted.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                delete_dialog.close()
                                refresh_cases_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#EF4444").props("push"
                            ).classes("text-[var(--vsp-white)]")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

    # ----- Initial render -----
    refresh_cases_table()
