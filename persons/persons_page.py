#!/usr/bin/env python3

"""
persons_page.pu

Consolidates four Flask routes into one interactive page:
    /person_list       →  table display + delete
    /person_add_page   →  add form
    /person_update     →  inline edit dialog
    /person_delete     →  delete with confirmation
"""

from nicegui import ui

from models import get_session, Persons
from navbar import build_navbar
from main_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler,
)


NOTIFICATION_TIMEOUT = 1500


# ── Main Page Builder ────────────────────────────────────────
def build_persons_page():
    """Builds the full Persons page UI."""

    # ── Header / Navbar ──────────────────────────────────────
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Person Management"
        ).classes("text-2xl font-bold m-4")

        # ── Add Person Form ──────────────────────────────────────
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):
            ui.label(
                "Add Person"
            ).classes("text-lg font-semibold mb-4")

            # sus_name — StringField (required, autofocused)
            sus_name_input = ui.input(
                label="Name"
            ).classes("w-full")
            sus_name_input.props("autofocus")

            # sus_dob — StringField
            sus_dob_input = ui.input(
                label="DOB"
            ).classes("w-full")

            # sus_address — StringField
            sus_address_input = ui.input(
                label="Address"
            ).classes("w-full")

            # sus_phone — StringField
            sus_phone_input = ui.input(
                label="Phone Number"
            ).classes("w-full")

            # sus_notes — TextAreaField
            sus_notes_input = ui.textarea(
                label="Notes"
            ).classes("w-full")

            # ── Buttons ────────────────────────────────────────
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form():
                    sus_name_input.value = ""
                    sus_dob_input.value = ""
                    sus_address_input.value = ""
                    sus_phone_input.value = ""
                    sus_notes_input.value = ""
                    ui.notify(
                        "Form cleared",
                        type="info",
                        timeout=NOTIFICATION_TIMEOUT,
                    )

                def on_submit():
                    # ── Required field validation (DataRequired) ──
                    sus_name = sus_name_input.value
                    if not sus_name:
                        ui.notify(
                            "Name is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    sus_dob = sus_dob_input.value or ""
                    sus_address = sus_address_input.value or ""
                    sus_phone = sus_phone_input.value or ""
                    sus_notes = sus_notes_input.value or ""

                    # ── Duplicate name check (sus_name is unique) ──
                    with get_session() as session:
                        existing = (
                            session.query(
                                Persons
                            )
                            .filter_by(sus_name=sus_name)
                            .first()
                        )

                        if existing:
                            ui.notify(
                                f"'{sus_name}' is already in the "
                                "database. Person names must be unique.",
                                type="negative",
                                timeout=NOTIFICATION_TIMEOUT,
                            )
                            return

                        # ── Save to database ──
                        new_person = Persons(
                            sus_name=sus_name,
                            sus_dob=sus_dob,
                            sus_address=sus_address,
                            sus_phone=sus_phone,
                            sus_notes=sus_notes,
                        )
                        session.add(new_person)

                    ui.notify(
                        f"'{sus_name}' was added successfully",
                        type="positive",
                        timeout=NOTIFICATION_TIMEOUT,
                    )

                    clear_form()
                    refresh_persons_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                ).props("outline")

                ui.button(
                    "Add Person",
                    on_click=on_submit,
                ).props("unelevated")

        # ── Existing Persons Table ───────────────────────────────
        ui.separator().classes("my-6")
        ui.label(
            "Current Persons"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_persons_table():
            """Re-renders the persons table from the database."""
            table_container.clear()

            with get_session() as session:
                persons = session.query(
                    Persons
                ).order_by(Persons.sus_name).all()

                if not persons:
                    with table_container:
                        ui.label(
                            "No persons in the database yet"
                        ).classes("text-gray-500 italic")
                    return

                row_data = [
                    {
                        "id": r.id,
                        "sus_name": r.sus_name or "",
                        "sus_dob": r.sus_dob or "",
                        "sus_address": r.sus_address or "",
                        "sus_phone": r.sus_phone or "",
                        "sus_notes": r.sus_notes or "",
                    }
                    for r in persons
                ]

            with table_container:
                column_defs = [
                    {
                        "name": "sus_name",
                        "label": "Name",
                        "field": "sus_name",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "sus_dob",
                        "label": "DOB",
                        "field": "sus_dob",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "sus_address",
                        "label": "Address",
                        "field": "sus_address",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "sus_phone",
                        "label": "Phone",
                        "field": "sus_phone",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "sus_notes",
                        "label": "Notes",
                        "field": "sus_notes",
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
                            f"Edit Person: {row['sus_name']}"
                        ).classes("text-lg font-semibold mb-4")

                        edit_name = ui.input(
                            label="Name",
                            value=row["sus_name"],
                        ).classes("w-full")
                        edit_dob = ui.input(
                            label="DOB",
                            value=row["sus_dob"],
                        ).classes("w-full")
                        edit_address = ui.input(
                            label="Address",
                            value=row["sus_address"],
                        ).classes("w-full")
                        edit_phone = ui.input(
                            label="Phone Number",
                            value=row["sus_phone"],
                        ).classes("w-full")
                        edit_notes = ui.textarea(
                            label="Notes",
                            value=row["sus_notes"],
                        ).classes("w-full")

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"
                        ):
                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                            ).props("flat")

                            def on_save_update():
                                new_name = edit_name.value or ""
                                if not new_name:
                                    ui.notify(
                                        "Name is required",
                                        type="warning",
                                        timeout=NOTIFICATION_TIMEOUT,
                                    )
                                    return

                                with get_session() as session:
                                    # Check duplicate name (exclude self)
                                    dup = (
                                        session.query(Persons)
                                        .filter(
                                            Persons.sus_name == new_name,
                                            Persons.id != row["id"],
                                        )
                                        .first()
                                    )
                                    if dup:
                                        ui.notify(
                                            f"'{new_name}' is already "
                                            "in the database. Person "
                                            "names must be unique.",
                                            type="negative",
                                            timeout=NOTIFICATION_TIMEOUT,
                                        )
                                        return

                                    person = (
                                        session.query(Persons)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if person:
                                        person.sus_name = new_name
                                        person.sus_dob = (
                                            edit_dob.value or ""
                                        )
                                        person.sus_address = (
                                            edit_address.value or ""
                                        )
                                        person.sus_phone = (
                                            edit_phone.value or ""
                                        )
                                        person.sus_notes = (
                                            edit_notes.value or ""
                                        )

                                ui.notify(
                                    f"{new_name} was updated successfully",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )

                                edit_dialog.close()
                                refresh_persons_table()
                                
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
                            f"Are you sure you want to remove "
                            f"{row['sus_name']} from the case file?"
                        ).classes("mb-4")

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                            ).props("flat")

                            def on_confirm_delete():
                                with get_session() as session:
                                    person = (
                                        session.query(
                                            Persons
                                        )
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if person:
                                        sus_name = person.sus_name
                                        session.delete(person)
                                    else:
                                        sus_name = row["sus_name"]

                                ui.notify(
                                    f"{sus_name} has been successfully "
                                    "removed from the file",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                delete_dialog.close()
                                refresh_persons_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

    # Initial render
    refresh_persons_table()


# ── Page Registration ────────────────────────────────────────
@ui.page("/persons")
def persons_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return
    build_persons_page()
