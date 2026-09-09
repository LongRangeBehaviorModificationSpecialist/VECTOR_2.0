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

            SUSPECTNAME_input = required_input(
                label="Name"
            ).classes("w-full")

            SUSPECTNAME_input.props("autofocus")

            SUSPECTDOB_input = ui.input(
                label="DOB"
            ).classes("w-full")

            SUSPECTADDRESS_input = ui.input(
                label="Address"
            ).classes("w-full")

            SUSPECTPHONE_input = ui.input(
                label="Phone Number"
            ).classes("w-full")

            SUSPECTNOTE_input = required_input(
                label="Notes"
            ).classes("w-full")

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form() -> None:
                    SUSPECTNAME_input.value = ""
                    SUSPECTDOB_input.value = ""
                    SUSPECTADDRESS_input.value = ""
                    SUSPECTPHONE_input.value = ""
                    SUSPECTNOTE_input.value = ""

                def on_submit() -> None:
                    SUSPECTNAME = SUSPECTNAME_input.value
                    SUSPECTDOB = SUSPECTDOB_input.value or ""
                    SUSPECTADDRESS = SUSPECTADDRESS_input.value or ""
                    SUSPECTPHONE = SUSPECTPHONE_input.value or ""
                    SUSPECTNOTE = SUSPECTNOTE_input.value or ""

                    if validate_person_data(
                        stage="initial",
                        SUSPECTNAME=SUSPECTNAME,
                        SUSPECTNOTE=SUSPECTNOTE,
                    ):
                        return

                    # ----- Duplicate name check (SUSPECTNAME is unique) -----
                    with get_session() as session:
                        # existing = (
                        #     session.query(Persons)
                        #     .filter_by(SUSPECTNAME=SUSPECTNAME)
                        #     .first()
                        # )
                        # if existing:
                        #     ui.notify(
                        #         f"'{SUSPECTNAME}' is already in the "
                        #         "database. Person names must be unique.",
                        #         type="warning",
                        #         timeout=0,
                        #         position="center",
                        #         close_button="OK",
                        #     )
                        #     return

                        # ----- Save to database -----
                        new_person = Persons(
                            SUSPECTNAME=SUSPECTNAME,
                            SUSPECTDOB=SUSPECTDOB,
                            SUSPECTADDRESS=SUSPECTADDRESS,
                            SUSPECTPHONE=SUSPECTPHONE,
                            SUSPECTNOTE=SUSPECTNOTE,
                            ENTEREDDATETIME=get_current_timestamp(format="entry"),
                        )
                        session.add(new_person)

                    ui.notify(
                        f"'{SUSPECTNAME}' was added.",
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
                ).props(
                    "flat"
                ).classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Person",
                    on_click=on_submit,
                    color="var(--vsp-blue)",
                ).props("unelevated").classes("text-[var(--vsp-white)]")

        # ----- Existing Persons Table -----
        ui.separator().classes("my-6")

        ui.label(
            "Current Persons").classes("text-xl font-bold mb-3"
        )

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_persons_table() -> None:
            """Re-renders the persons table from the database."""
            table_container.clear()

            with get_session() as session:
                persons = (
                    session.query(Persons)
                    .order_by(Persons.SUSPECTNAME)
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
                        "SUSPECTNAME": r.SUSPECTNAME or "",
                        "SUSPECTDOB": r.SUSPECTDOB or "",
                        "SUSPECTADDRESS": r.SUSPECTADDRESS or "",
                        "SUSPECTPHONE": r.SUSPECTPHONE or "",
                        "SUSPECTNOTE": r.SUSPECTNOTE or "",
                    }
                    for r in persons
                ]

            with table_container:
                column_defs = [
                    {
                        "name": "SUSPECTNAME",
                        "label": "Name",
                        "field": "SUSPECTNAME",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "SUSPECTDOB",
                        "label": "DOB",
                        "field": "SUSPECTDOB",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "SUSPECTADDRESS",
                        "label": "Address",
                        "field": "SUSPECTADDRESS",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "SUSPECTPHONE",
                        "label": "Phone",
                        "field": "SUSPECTPHONE",
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
                            f"Edit Person ({row['SUSPECTNAME']})"
                        ).classes(
                            "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                        )

                        SUSPECTNAME_input = required_input(
                            label="Name",
                            value=row["SUSPECTNAME"],
                        ).classes("w-full")

                        SUSPECTDOB_input = ui.input(
                            label="DOB",
                            value=row["SUSPECTDOB"],
                        ).classes("w-full")

                        SUSPECTADDRESS_input = ui.input(
                            label="Address",
                            value=row["SUSPECTADDRESS"],
                        ).classes("w-full")

                        SUSPECTPHONE_input = ui.input(
                            label="Phone Number",
                            value=row["SUSPECTPHONE"],
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
                                SUSPECTNAME = SUSPECTNAME_input.value or ""
                                SUSPECTDOB = SUSPECTDOB_input or ""
                                SUSPECTADDRESS = SUSPECTADDRESS_input or ""
                                SUSPECTPHONE = SUSPECTPHONE_input or ""
                                SUSPECTNOTE = SUSPECTNOTE_input or ""

                                if validate_person_data(
                                    stage="update",
                                    SUSPECTNAME=SUSPECTNAME,
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
                                        person.SUSPECTNAME = SUSPECTNAME
                                        person.SUSPECTDOB = (
                                            SUSPECTDOB.value or ""
                                        )
                                        person.SUSPECTADDRESS = (
                                            SUSPECTADDRESS.value or ""
                                        )
                                        person.SUSPECTPHONE = (
                                            SUSPECTPHONE.value or ""
                                        )
                                        person.SUSPECTNOTE = (
                                            SUSPECTNOTE.value or ""
                                        )

                                ui.notify(
                                    f"'{SUSPECTNAME}' was updated.",
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
                            f"\'{row['SUSPECTNAME']}\'"
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
                                        SUSPECTNAME = person.SUSPECTNAME
                                        session.delete(person)
                                    else:
                                        SUSPECTNAME = row["SUSPECTNAME"]

                                ui.notify(
                                    f"'{SUSPECTNAME}' was removed.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                delete_dialog.close()
                                refresh_persons_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#ef4444",
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
                color="#ef4444",
            ).props("unelevated").classes("mb-2 items-center")

    # -----Initial render -----
    refresh_persons_table()
