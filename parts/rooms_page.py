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
    validate_room_entry,
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

                def clear_room_form() -> None:

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

                    # ----- Data validation -----
                    if validate_room_entry(
                        stage="initial",
                        ROOMLABEL=ROOMLABEL,
                        ROOMDESC=ROOMDESC,
                        ROOMFIRSTAGENT=ROOMFIRSTAGENT,
                        ROOMSECONDAGENT=ROOMSECONDAGENT,
                    ):
                        return

                    try:
                        with get_session() as session:
                            new_room = Rooms(
                                ROOMLABEL=ROOMLABEL,
                                ROOMDESC=ROOMDESC,
                                ROOMFIRSTAGENT=ROOMFIRSTAGENT,
                                ROOMSECONDAGENT=ROOMSECONDAGENT,
                                ROOMNOTE=ROOMNOTE,
                                ENTEREDDATETIME=(
                                    get_current_timestamp(format="entry")
                                ),
                            )
                            session.add(new_room)

                        ui.notify(
                            f"Room {ROOMLABEL} was added.",
                            timeout=4000,
                            position="bottom",
                            close_button="OK",
                        )

                        refresh_rooms_table()
                        clear_room_form()

                    except Exception:
                        ui.notify(
                            "Please check the Room information you just tried "
                            "to enter/update — You may have entered a "
                            "duplicate value. No changes were made.",
                            type="negative",
                            timeout=0,
                            position="center",
                            close_button="OK",
                        )
                        import traceback
                        traceback.print_exc()

                ui.button(
                    "Clear",
                    on_click=clear_room_form,
                    color="transparent",
                ).props("flat").classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Room",
                    on_click=on_submit,
                    color="var(--vsp-blue)",
                ).props("unelevated").classes("text-[var(--vsp-white)]")

        # ----- Existing Rooms Table -----
        ui.separator().classes("my-6")

        with ui.column().classes("w-full items-center"):

            ui.label("Rooms List").classes("text-xl font-bold mb-3")

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

                                ROOMLABEL_input = required_input(
                                    label="Room Label",
                                    value=row["ROOMLABEL"],
                                ).classes("w-full")

                                ROOMDESC_input = required_input(
                                    label="Room Description",
                                    value=row["ROOMDESC"],
                                ).classes("w-full")

                                ROOMFIRSTAGENT_input = ui.select(
                                    options=current_agents,
                                    label="First Agent Name",
                                    value=row["ROOMFIRSTAGENT"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                ROOMSECONDAGENT_input = ui.select(
                                    options=current_agents,
                                    label="Second Agent Name",
                                    value=row["ROOMSECONDAGENT"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                ROOMNOTE_input = ui.input(
                                    label="Notes",
                                    value=row["ROOMNOTE"],
                                ).classes("w-full")

                                with ui.row().classes(
                                    "w-full justify-end gap-2 mt-4"
                                ):

                                    ui.button(
                                        "Cancel",
                                        on_click=edit_dialog.close,
                                        color="transparent",
                                    ).props("flat").classes(
                                        "text-[var(--vsp-blue)]"
                                    )

                                    def on_save_update() -> None:
                                        ROOMLABEL = ROOMLABEL_input.value or ""
                                        ROOMDESC = ROOMDESC_input.value or ""
                                        ROOMFIRSTAGENT = (
                                            ROOMFIRSTAGENT_input.value or ""
                                        )
                                        ROOMSECONDAGENT = (
                                            ROOMSECONDAGENT_input.value or ""
                                        )
                                        ROOMNOTE = ROOMNOTE_input.value or ""

                                        if validate_room_entry(
                                            stage="update",
                                            ROOMLABEL=ROOMLABEL,
                                            ROOMDESC=ROOMDESC,
                                            ROOMFIRSTAGENT=ROOMFIRSTAGENT,
                                            ROOMSECONDAGENT=ROOMSECONDAGENT,
                                            row=row,
                                        ):
                                            return

                                        with get_session() as session:

                                            a1 = ROOMFIRSTAGENT
                                            a2 = ROOMSECONDAGENT

                                            # ----- Save changes -----
                                            room = (
                                                session.query(Rooms)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )
                                            if room:
                                                room.ROOMLABEL = ROOMLABEL
                                                room.ROOMDESC = ROOMDESC
                                                room.ROOMFIRSTAGENT = a1
                                                room.ROOMSECONDAGENT = a2
                                                room.ROOMNOTE = ROOMNOTE

                                        ui.notify(
                                            f"Room {ROOMLABEL} was updated.",
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
                                ).classes("max-w-sm p-6"
                            ):

                                ui.label(
                                    "Delete Room?"
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
                                            "has been removed.",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        delete_dialog.close()
                                        refresh_rooms_table()

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
                    color="#EF4444",
                ).props("unelevated").classes("mb-2 items-center")

    # ----- Initial render -----
    refresh_rooms_table()
