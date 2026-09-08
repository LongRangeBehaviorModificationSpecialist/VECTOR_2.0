#!/usr/bin/env python3

"""
rooms_page.py

Consolidates four Flask routes into one interactive page:
    /room_list      →  table display + delete
    /room_add_page  →  add form (auto-generates next room letter,
        agent dropdowns)
    /room_update    →  inline edit dialog
    /room_delete    →  delete with confirmation
"""

from nicegui import ui

from models import get_session, Rooms
from navbar import build_navbar
from home_page import confirm_new_case_handler
from main import get_current_user_name, get_is_admin
from utils import (
    required_input,
    load_agent_names,
    get_next_room_ltr,
    validate_room_data,
    confirm_delete_all,
    get_current_timestamp,
)

# ----- Main Page Builder -----
def build_rooms_page() -> None:
    """Builds the full Rooms page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Rooms"
        ).classes("text-2xl font-bold m-4")

        # ----- Add Room Form -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            next_letter = get_next_room_ltr()
            agent_options = load_agent_names()

            ROOMLABEL_input = ui.input(
                label="Room Label",
                value=next_letter,
            ).classes("w-full")

            ROOMLABEL_input.props("readonly")

            ROOMDESC_input = required_input(
                label="Room Description",
            ).classes("w-full")

            ROOMDESC_input.props("autofocus")

            ROOMFIRSTAGENT_combo = ui.select(
                options=agent_options,
                label="First Agent Name",
                with_input=True,
            ).classes("w-full")

            ROOMSECONDAGENT_combo = ui.select(
                options=agent_options,
                label="Second Agent Name",
                with_input=True,
            ).classes("w-full")

            ROOMNOTE_input = ui.input(label="Notes").classes("w-full")

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form() -> None:
                    ROOMLABEL_input.value = get_next_room_ltr()
                    ROOMDESC_input.value = ""
                    ROOMFIRSTAGENT_combo.value = None
                    ROOMSECONDAGENT_combo.value = None
                    ROOMNOTE_input.value = ""

                def on_submit() -> None:
                    """Handles form submission for new rooms."""
                    ROOMLABEL = ROOMLABEL_input.value
                    ROOMDESC = ROOMDESC_input.value
                    ROOMFIRSTAGENT = ROOMFIRSTAGENT_combo.value or ""
                    ROOMSECONDAGENT = ROOMSECONDAGENT_combo.value or ""
                    ROOMNOTE = ROOMNOTE_input.value or ""

                    # ----- Required field validation -----
                    if not validate_room_data(
                        ROOMLABEL=ROOMLABEL,
                        ROOMDESC=ROOMDESC,
                    ):
                        return

                    # ----- Duplicate label validation -----
                    with get_session() as session:
                        # ----- Same agent checks -----
                        if (
                            ROOMFIRSTAGENT and ROOMSECONDAGENT and
                            ROOMFIRSTAGENT == ROOMSECONDAGENT
                        ):
                            ui.notify(
                                "The same agent cannot be listed in the "
                                "'First Agent Name' and 'Second Agent "
                                "Name' fields.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        # ----- Save to database -----
                        new_room = Rooms(
                            ROOMLABEL=ROOMLABEL,
                            ROOMDESC=ROOMDESC,
                            ROOMFIRSTAGENT=ROOMFIRSTAGENT,
                            ROOMSECONDAGENT=ROOMSECONDAGENT,
                            ROOMNOTE=ROOMNOTE,
                            ENTEREDDATETIME=get_current_timestamp(format="entry"),
                        )
                        session.add(new_room)

                    ui.notify(
                        f"Room {ROOMLABEL} was added.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )

                    clear_form()
                    refresh_rooms_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                    color="transparent",
                ).props(
                    "flat"
                ).classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Room",
                    on_click=on_submit,
                    color="var(--vsp-blue)",
                ).props("unelevated").classes("text-[var(--vsp-white)]")

        # ----- Existing Rooms Table -----
        ui.separator().classes("my-6")

        with ui.column().classes("w-full items-center"):

            ui.label(
                "Current Rooms"
            ).classes("text-xl font-bold mb-3")

            with ui.row().classes("w-full max-w-6xl items-center"):

                table_container = ui.column().classes(
                    "w-full max-w-5xl mx-auto items-center gap-2"
                )

                def refresh_rooms_table() -> None:
                    """Re-renders the rooms table from the database."""
                    table_container.clear()

                    with get_session() as session:
                        rooms = (
                            session.query(Rooms)
                            .order_by(Rooms.ROOMLABEL)
                            .all()
                        )
                        if not rooms:
                            with table_container:
                                ui.label(
                                    "No rooms in the database yet."
                                ).classes("text-gray-500 italic")
                            return

                        row_data = [
                            {
                                "Z_PK": r.Z_PK,
                                "ROOMLABEL": r.ROOMLABEL or "",
                                "ROOMDESC": r.ROOMDESC or "",
                                "ROOMFIRSTAGENT": r.ROOMFIRSTAGENT or "",
                                "ROOMSECONDAGENT": r.ROOMSECONDAGENT or "",
                                "ROOMNOTE": r.ROOMNOTE or "",
                            }
                            for r in rooms
                        ]

                    with table_container:
                        column_defs = [
                            {
                                "name": "ROOMLABEL",
                                "label": "Label",
                                "field": "ROOMLABEL",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "ROOMDESC",
                                "label": "Description",
                                "field": "ROOMDESC",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "ROOMFIRSTAGENT",
                                "label": "Agent 1",
                                "field": "ROOMFIRSTAGENT",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "ROOMSECONDAGENT",
                                "label": "Agent 2",
                                "field": "ROOMSECONDAGENT",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "ROOMNOTE",
                                "label": "Note",
                                "field": "ROOMNOTE",
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
                                    <q-btn dense flat
                                        icon="edit" size="sm"
                                        style="color: #2984D1;"
                                        @click="$parent.$emit('edit', \
                                        props.row)" />
                                    <q-btn dense flat color="negative"
                                        icon="delete" size="sm"
                                        @click="$parent.$emit('delete', \
                                        props.row)" />
                                </div>
                            </q-td>
                            """
                        )

                        # ----- Edit dialog -----
                        def open_edit_dialog(e) -> None:
                            row = e.args
                            current_agents = load_agent_names()

                            with ui.dialog() as edit_dialog, ui.card(
                                ).classes("w-full max-w-lg p-6"
                            ):

                                ui.label(
                                    f"Edit Room ({row['ROOMLABEL']} - "
                                    f"{row['ROOMDESC']})"
                                ).classes(
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                edit_label = required_input(
                                    label="Room Label",
                                    value=row["ROOMLABEL"],
                                ).classes("w-full")

                                edit_desc = required_input(
                                    label="Room Description",
                                    value=row["ROOMDESC"],
                                ).classes("w-full")

                                edit_first_agent = ui.select(
                                    options=current_agents,
                                    label="First Agent Name",
                                    value=row["ROOMFIRSTAGENT"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                edit_second_agent = ui.select(
                                    options=current_agents,
                                    label="Second Agent Name",
                                    value=row["ROOMSECONDAGENT"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                edit_note = ui.input(
                                    label="Notes",
                                    value=row["ROOMNOTE"],
                                ).classes("w-full")

                                with ui.row().classes(
                                    "w-full justify-end gap-2 mt-4"):

                                    ui.button(
                                        "Cancel",
                                        on_click=edit_dialog.close,
                                        color="transparent",
                                    ).props("flat").classes(
                                        "text-[var(--vsp-blue)]"
                                    )

                                    def on_save_update() -> None:
                                        # ----- Validate uniqueness -----
                                        # (excluding current record)
                                        new_label = edit_label.value or ""
                                        new_desc = edit_desc.value or ""
                                        new_note = edit_note.value or ""

                                        with get_session() as session:
                                            dup_label = (
                                                session.query(Rooms)
                                                .filter(
                                                    Rooms.ROOMLABEL == (
                                                        new_label
                                                    ),
                                                    Rooms.Z_PK != row["Z_PK"]
                                                )
                                                .first()
                                            )
                                            if dup_label:
                                                ui.notify(
                                                    "That label is currently "
                                                    "assigned to another room.",
                                                    type="warning",
                                                    timeout=0,
                                                    position="center",
                                                    close_button="OK",
                                                )
                                                return

                                            # Check duplicate description
                                            # (exclude self)
                                            dup_desc = (
                                                session.query(Rooms)
                                                .filter(
                                                    Rooms.ROOMDESC == new_desc,
                                                    Rooms.Z_PK != row["Z_PK"],
                                                )
                                                .first()
                                            )
                                            if dup_desc:
                                                ui.notify(
                                                    "That room description "
                                                    "is already assigned to "
                                                    "another room.",
                                                    type="warning",
                                                    timeout=0,
                                                    position="center",
                                                    close_button="OK",
                                                )
                                                return

                                            # Check if same agent listed in both
                                            a1 = edit_first_agent.value or ""
                                            a2 = edit_second_agent.value or ""

                                            if a1 and a2 and a1 == a2:
                                                ui.notify(
                                                    "The same agent cannot "
                                                    "be listed in the 'First "
                                                    "Agent Name' and "
                                                    "'Second Agent Name' "
                                                    "fields.",
                                                    type="warning",
                                                    timeout=0,
                                                    position="center",
                                                    close_button="OK",
                                                    )
                                                return

                                            # ----- Save changes -----
                                            room = (
                                                session.query(Rooms)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )
                                            if room:
                                                room.ROOMLABEL = new_label
                                                room.ROOMDESC = new_desc
                                                room.ROOMFIRSTAGENT = a1
                                                room.ROOMSECONDAGENT = a2
                                                room.ROOMNOTE = new_note

                                        ui.notify(
                                            f"Room {new_label} was updated.",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        edit_dialog.close()
                                        refresh_rooms_table()

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
                                ).classes("max-w-sm p-6"):

                                ui.label(
                                    f"Delete Room?"
                                ).classes(
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                ui.label(
                                    f"The following Room ID will be removed "
                                    "from the case file :"
                                ).classes(
                                    "mb-3 text-base text-[var(--vsp-gray)]"
                                )

                                ui.label(
                                    f"'Room {row['ROOMLABEL']} -- "
                                    f"{row['ROOMDESC']}'"
                                ).classes(
                                    "mb-3 text-base font-semibold text-[var(--vsp-blue)]"
                                )

                                with ui.row().classes(
                                    "w-full justify-end gap-2"
                                ):

                                    ui.button(
                                        "Cancel",
                                        on_click=delete_dialog.close,
                                        color="transparent",
                                    ).props("flat").classes(
                                        "text-[var(--vsp-blue)]"
                                    )

                                    def on_confirm_delete() -> None:
                                        with get_session() as session:
                                            room = (
                                                session.query(Rooms)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )
                                            if room:
                                                ROOMLABEL = room.ROOMLABEL
                                                ROOMDESC = room.ROOMDESC
                                                session.delete(room)
                                            else:
                                                ROOMLABEL = row["ROOMLABEL"]
                                                ROOMDESC = row["ROOMDESC"]

                                        ui.notify(
                                            f"Room {ROOMLABEL} ({ROOMDESC}) "
                                            "has been removed from the case "
                                            "file.",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        delete_dialog.close()
                                        refresh_rooms_table()

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

                def delete_all_rooms() -> None:
                    with get_session() as session:
                        session.query(Rooms).delete()
                        session.commit()
                    ui.notify(
                        "All rooms have been deleted.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )
                    refresh_rooms_table()

                ui.button(
                    "Delete All Rooms",
                    on_click=lambda: confirm_delete_all(
                        "rooms",
                        delete_all_rooms
                    ),
                    color="#ef4444",
                ).props("unelevated").classes("mb-2 items-center")

    # ----- Initial render -----
    refresh_rooms_table()
