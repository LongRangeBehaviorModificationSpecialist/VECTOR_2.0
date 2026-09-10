#!/usr/bin/env python3

"""
persons_page.py

Consolidates four Flask routes into one interactive page:
    /person_list       →  table display + delete
    /person_add_page   →  add form
    /person_update     →  inline edit dialog
    /person_delete     →  delete with confirmation
"""

from nicegui import ui

from models import get_session, Persons
from navbar import build_navbar
from home_page import confirm_new_case_handler
from main import get_current_user_name, get_is_admin
from utils import (
    required_input,
    confirm_delete_all,
    get_current_timestamp,
    validate_person_data,
)

# ----- Main Page Builder -----
def build_persons_page() -> None:
    """Builds the full Persons page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Person List"
        ).classes("text-2xl font-bold m-4")

        # ----- Add Person Form -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            PERSONNAME_input = required_input(
                label="Name"
            ).classes("w-full")

            PERSONNAME_input.props("autofocus")

            PERSONDOB_input = ui.input(
                label="DOB",
                placeholder="MM-DD-YYYY",
            ).props('mask="##-##-####"').classes("w-full")

            PERSONADDRESS_input = ui.input(
                label="Address"
            ).classes("w-full")

            PERSONPHONE_input = ui.input(
                label="Phone Number",
                placeholder="(###) ###-####"
            ).props('mask="(###) ###-####"').classes("w-full")

            SUSPECTNOTE_input = required_input(
                label="Notes"
            ).classes("w-full")

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form() -> None:

                    PERSONNAME_input.value = ""
                    PERSONDOB_input.value = ""
                    PERSONADDRESS_input.value = ""
                    PERSONPHONE_input.value = ""
                    SUSPECTNOTE_input.value = ""

                def on_submit() -> None:

                    PERSONNAME = PERSONNAME_input.value
                    PERSONDOB = PERSONDOB_input.value or ""
                    PERSONADDRESS = PERSONADDRESS_input.value or ""
                    PERSONPHONE = PERSONPHONE_input.value or ""
                    SUSPECTNOTE = SUSPECTNOTE_input.value or ""

                    if validate_person_data(
                        stage="initial",
                        PERSONNAME=PERSONNAME,
                        SUSPECTNOTE=SUSPECTNOTE,
                    ):
                        return

                    with get_session() as session:

                        new_person = Persons(
                            PERSONNAME=PERSONNAME,
                            PERSONDOB=PERSONDOB,
                            PERSONADDRESS=PERSONADDRESS,
                            PERSONPHONE=PERSONPHONE,
                            SUSPECTNOTE=SUSPECTNOTE,
                            ENTEREDDATETIME=get_current_timestamp(format="entry"),
                        )
                        session.add(new_person)

                    ui.notify(
                        f"'{PERSONNAME}' was added.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )

                    clear_form()
                    refresh_persons_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                    color="transparent",
                ).props("flat").classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Person",
                    on_click=on_submit,
                    color="var(--vsp-blue)",
                ).props("unelevated").classes("text-[var(--vsp-white)]")

        # ----- Existing Persons Table -----
        ui.separator().classes("my-6")

        ui.label(
            "Persons List"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_persons_table() -> None:
            """Re-renders the persons table from the database."""
            table_container.clear()

            with get_session() as session:

                persons = (
                    session.query(Persons)
                    .order_by(Persons.PERSONNAME)
                    .all()
                )

                if not persons:
                    with table_container:
                        ui.label(
                            "No persons in the database yet"
                        ).classes("text-gray-500 italic")
                    return

                row_data = [
                    {
                        "Z_PK": r.Z_PK,
                        "PERSONNAME": r.PERSONNAME or "",
                        "PERSONDOB": r.PERSONDOB or "",
                        "PERSONADDRESS": r.PERSONADDRESS or "",
                        "PERSONPHONE": r.PERSONPHONE or "",
                        "SUSPECTNOTE": r.SUSPECTNOTE or "",
                    }
                    for r in persons
                ]

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
                        "name": "PERSONNAME",
                        "label": "Name",
                        "field": "PERSONNAME",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "PERSONDOB",
                        "label": "DOB",
                        "field": "PERSONDOB",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "PERSONADDRESS",
                        "label": "Address",
                        "field": "PERSONADDRESS",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "PERSONPHONE",
                        "label": "Phone",
                        "field": "PERSONPHONE",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "SUSPECTNOTE",
                        "label": "Notes",
                        "field": "SUSPECTNOTE",
                        "sortable": False,
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
                            <q-btn dense flat
                                icon="edit" size="sm"
                                style="color: #2984D1;"
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
                        ).classes("w-full max-w-lg p-6"
                    ):

                        ui.label(
                            f"Edit Person ({row['PERSONNAME']})"
                            ).classes(
                            "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                        )

                        PERSONNAME_input = required_input(
                            label="Name",
                            value=row["PERSONNAME"],
                        ).classes("w-full")

                        PERSONDOB_input = ui.input(
                            label="DOB",
                            value=row["PERSONDOB"],
                        ).classes("w-full")

                        PERSONADDRESS_input = ui.input(
                            label="Address",
                            value=row["PERSONADDRESS"],
                        ).classes("w-full")

                        PERSONPHONE_input = ui.input(
                            label="Phone Number",
                            value=row["PERSONPHONE"],
                            ).classes("w-full")

                        SUSPECTNOTE_input = required_input(
                            label="Notes",
                            value=row["SUSPECTNOTE"],
                        ).classes("w-full")

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"
                        ):

                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                                color="transparent",
                            ).props("flat").classes("text-[var(--vsp-blue)]")

                            def on_save_update() -> None:
                                PERSONNAME = PERSONNAME_input.value or ""
                                PERSONDOB = PERSONDOB_input.value or ""
                                PERSONADDRESS = (
                                    PERSONADDRESS_input.value or ""
                                )
                                PERSONPHONE = PERSONPHONE_input.value or ""
                                SUSPECTNOTE = SUSPECTNOTE_input.value or ""

                                if validate_person_data(
                                    stage="update",
                                    PERSONNAME=PERSONNAME,
                                    SUSPECTNOTE=SUSPECTNOTE,
                                    row=row,
                                ):
                                    return

                                with get_session() as session:

                                    person = (
                                        session.query(Persons)
                                        .filter_by(Z_PK=row["Z_PK"])
                                        .first()
                                    )

                                    if person:
                                        person.PERSONNAME = PERSONNAME
                                        person.PERSONDOB = (
                                            PERSONDOB or ""
                                        )
                                        person.PERSONADDRESS = (
                                            PERSONADDRESS or ""
                                        )
                                        person.PERSONPHONE = (
                                            PERSONPHONE or ""
                                        )
                                        person.SUSPECTNOTE = (
                                            SUSPECTNOTE or ""
                                        )

                                ui.notify(
                                    f"'{PERSONNAME}' was updated.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                edit_dialog.close()
                                refresh_persons_table()

                            ui.button(
                                "Update",
                                on_click=on_save_update,
                                color="var(--vsp-blue)",
                                ).props("unelevated").classes(
                                "text-[var(--vsp-white)]"
                            )

                    edit_dialog.open()

                # ----- Delete confirmation dialog -----
                def open_delete_dialog(e) -> None:

                    row = e.args

                    with ui.dialog() as delete_dialog, ui.card(
                        ).classes("max-w-sm p-6"
                    ):

                        ui.label(
                            "Delete Person?"
                            ).classes(
                            "text-lg font-semibold mb-1 text-[var(--vsp-blue)]"
                        )

                        ui.label(
                            f"The following Person will be removed from the "
                            "case file :").classes(
                            "mb-3 text-base text-[var(--vsp-gray)]"
                        )

                        ui.label(
                            f"\"{row['PERSONNAME']}\""
                        ).classes(
                            "mb-3 text-base font-semibold text-[var(--vsp-blue)]")

                        with ui.row().classes("w-full justify-end gap-2"):

                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                                color="transparent",
                            ).props("flat").classes("text-[var(--vsp-blue)]")

                            def on_confirm_delete() -> None:

                                with get_session() as session:

                                    person = (
                                        session.query(Persons)
                                        .filter_by(Z_PK=row["Z_PK"])
                                        .first()
                                    )

                                    if person:
                                        PERSONNAME = person.PERSONNAME
                                        session.delete(person)
                                    else:
                                        PERSONNAME = row["PERSONNAME"]

                                ui.notify(
                                    f"'{PERSONNAME}' was removed.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                delete_dialog.close()
                                refresh_persons_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#EF4444",
                                ).props("unelevated").classes(
                                "text-[var(--vsp-white)]"
                            )

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

        with ui.row().classes("w-full justify-center my-2"):

            def delete_all_persons() -> None:

                with get_session() as session:

                    session.query(Persons).delete()
                    session.commit()

                ui.notify(
                    "All Persons has been deleted.",
                    timeout=4000,
                    position="bottom",
                    close_button="OK",
                )

                refresh_persons_table()

            ui.button(
                "Delete All Persons",
                on_click=lambda: confirm_delete_all(
                    "persons",
                    delete_all_persons,
                ),
                color="#EF4444",
            ).props("unelevated").classes("mb-2 items-center")

    # -----Initial render -----
    refresh_persons_table()
