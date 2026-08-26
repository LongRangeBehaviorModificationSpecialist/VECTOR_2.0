#!/usr/bin/env python3

"""
rooms_page.py

Consolidates four Flask routes into one interactive page:
    /room_list      →  table display + delete
    /room_add_page  →  add form (auto-generates next room letter, agent dropdowns)
    /room_update    →  inline edit dialog
    /room_delete    →  delete with confirmation
"""

from nicegui import ui

from models import get_session, Agents, Rooms
from navbar import build_navbar, confirm_new_case_dialog
from main_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler
)


NOTIFICATION_TIMEOUT = 1500


# ── Helpers ─────────────────────────────────────────────────
def load_agent_names() -> list[str]:
    """Returns a list of all agent names from the Agents table."""
    with get_session() as session:
        rows = (
            session.query(
                Agents.agent_name
            )
            .order_by(Agents.agent_name)
            .all()
        )
        return [r[0] for r in rows]


def get_next_room_ltr() -> str:
    """Gets the label of the last room in the database and 
    increments it to the next letter.

    Returns "A" if no rooms exist yet.
    """
    with get_session() as session:
        rooms = (
            session.query(
                Rooms
            )
            .order_by(Rooms.room_label)
            .all()
        )
        if rooms:
            last_label = rooms[-1].room_label
            # Increment the ASCII value by 1, 
            # then convert back to char
            return chr(ord(last_label) + 1)
        else:
            return "A"


# ── Main Page Builder ────────────────────────────────────────
def build_rooms_page():
    """Builds the full Rooms page UI."""

    # ── Header / Navbar ──────────────────────────────────────
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Room Management"
        ).classes("text-2xl font-bold m-4")

        # ── Add Room Form ────────────────────────────────────────
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            ui.label(
                "Add Room"
            ).classes("text-lg font-semibold mb-4")

            next_letter = get_next_room_ltr()
            agent_options = load_agent_names()

            # room_label — pre-populated with next letter
            room_label_input = ui.input(
                label="Room Label",
                value=next_letter,
            ).classes("w-full")

            # room_desc — (required, autofocused)
            room_desc_input = ui.input(
                label="Room Description",
            ).classes("w-full")

            room_desc_input.props("autofocus")

            # room_first_agent —  populated from Agents
            room_first_agent_combo = ui.select(
                options=agent_options,
                label="First Agent Name",
                with_input=True,
            ).classes("w-full")

            # room_second_agent — populated from Agents
            room_second_agent_combo = ui.select(
                options=agent_options,
                label="Second Agent Name",
                with_input=True,
            ).classes("w-full")

            # ── Buttons ────────────────────────────────────────
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form():
                    room_label_input.value = get_next_room_ltr()
                    room_desc_input.value = ""
                    room_first_agent_combo.value = None
                    room_second_agent_combo.value = None
                    ui.notify(
                        "Form cleared",
                        type="info",
                        timeout=NOTIFICATION_TIMEOUT,
                    )

                def on_submit():
                    # ── Required field validation ──
                    room_label = room_label_input.value
                    if not room_label:
                        ui.notify(
                            "Room Label is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    room_desc = room_desc_input.value
                    if not room_desc:
                        ui.notify(
                            "A room description is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    first_agent = room_first_agent_combo.value or ""
                    second_agent = room_second_agent_combo.value or ""

                    # ── Duplicate label validation ──
                    with get_session() as session:
                        existing_label = (
                            session.query(
                                Rooms
                            )
                            .filter_by(room_label=room_label)
                            .first()
                        )

                        if existing_label:
                            ui.notify(
                                "That label is currently assigned "
                                "to another room",
                                type="negative",
                                timeout=NOTIFICATION_TIMEOUT,
                            )
                            return

                        # ── Duplicate description validation ──
                        existing_desc = (
                            session.query(
                                Rooms
                            )
                            .filter_by(room_desc=room_desc)
                            .first()
                        )

                        if existing_desc:
                            ui.notify(
                                "That room description is already "
                                "assigned to another room",
                                type="negative",
                                timeout=NOTIFICATION_TIMEOUT,
                            )
                            return

                        # ── Same agent checks
                        if (
                            first_agent and 
                            second_agent and 
                            first_agent == second_agent
                        ):
                            ui.notify(
                                "You cannot have the same agent "
                                "listed as both the 'First Agent "
                                "Name' and 'Second Agent Name'.",
                                type="warning",
                                timeout=NOTIFICATION_TIMEOUT,
                            )
                            return

                        # ── Save to database ──
                        new_room = Rooms(
                            room_label=room_label,
                            room_desc=room_desc,
                            room_first_agent=first_agent,
                            room_second_agent=second_agent,
                        )
                        session.add(new_room)

                    ui.notify(
                        f"Room {room_label} was added to the case file "
                        "successfully",
                        type="positive",
                        timeout=NOTIFICATION_TIMEOUT,
                    )

                    clear_form()
                    refresh_rooms_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                ).props("outline")

                ui.button(
                    "Add Room", 
                    on_click=on_submit,
                ).props("unelevated")

        # ── Existing Rooms Table ────────────────────────────────
        ui.separator().classes("my-6")

        ui.label(
            "Current Rooms"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_rooms_table():
            """Re-renders the rooms table from the database."""
            table_container.clear()

            with get_session() as session:
                rooms = (
                    session.query(
                        Rooms
                    )
                    .order_by(Rooms.room_label)
                    .all()
                )

                if not rooms:
                    with table_container:
                        ui.label(
                            "No rooms in the database yet"
                        ).classes("text-gray-500 italic")
                    return

                row_data = [
                    {
                        "id": r.id,
                        "room_label": r.room_label or "",
                        "room_desc": r.room_desc or "",
                        "room_first_agent": r.room_first_agent or "",
                        "room_second_agent": r.room_second_agent or "",
                    }
                    for r in rooms
                ]

            with table_container:
                column_defs = [
                    {
                        "name": "room_label",
                        "label": "Label",
                        "field": "room_label",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "room_desc",
                        "label": "Description",
                        "field": "room_desc",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "room_first_agent",
                        "label": "Agent 1",
                        "field": "room_first_agent",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "room_second_agent",
                        "label": "Agent 2",
                        "field": "room_second_agent",
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
                    # Reload agent options in case new agents were added
                    current_agents = load_agent_names()

                    with ui.dialog() as edit_dialog, ui.card().classes(
                        "w-full max-w-lg p-6"
                    ):
                        ui.label(
                            f"Edit Room: {row['room_label']}"
                        ).classes("text-lg font-semibold mb-4")

                        edit_label = ui.input(
                            label="Room Label",
                            value=row["room_label"],
                        ).classes("w-full")

                        edit_desc = ui.input(
                            label="Room Description",
                            value=row["room_desc"],
                        ).classes("w-full")

                        edit_first_agent = ui.select(
                            options=current_agents,
                            label="First Agent Name",
                            value=row["room_first_agent"] or None,
                            with_input=True,
                        ).classes("w-full")

                        edit_second_agent = ui.select(
                            options=current_agents,
                            label="Second Agent Name",
                            value=row["room_second_agent"] or None,
                            with_input=True,
                        ).classes("w-full")

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"
                        ):
                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                            ).props("flat")

                            def on_save_update():
                                # Validate uniqueness 
                                # (excluding current record)
                                new_label = edit_label.value or ""
                                new_desc = edit_desc.value or ""

                                with get_session() as session:
                                    # Check duplicate label (exclude self)
                                    dup_label = (
                                        session.query(
                                            Rooms
                                        )
                                        .filter(
                                            Rooms.room_label == new_label,
                                            Rooms.id != row["id"]
                                        ).first()
                                    )

                                    if dup_label:
                                        ui.notify(
                                            "That label is currently "
                                            "assigned to another room",
                                            type="negative",
                                            timeout=NOTIFICATION_TIMEOUT,
                                        )
                                        return

                                    # Check duplicate description 
                                    # (exclude self)
                                    dup_desc = (
                                        session.query(
                                            Rooms
                                        )
                                        .filter(
                                            Rooms.room_desc == new_desc,
                                            Rooms.id != row["id"],
                                        ).first()
                                    )

                                    if dup_desc:
                                        ui.notify(
                                            "That room description is "
                                            "already assigned to another "
                                            "room",
                                            type="negative",
                                            timeout=NOTIFICATION_TIMEOUT,
                                        )
                                        return

                                    # Check same agent
                                    a1 = edit_first_agent.value or ""
                                    a2 = edit_second_agent.value or ""
                                    if a1 and a2 and a1 == a2:
                                        ui.notify(
                                            "You cannot have the same "
                                            "agent listed as both the "
                                            "First and Second Agent",
                                            type="warning",
                                            timeout=NOTIFICATION_TIMEOUT,
                                        )
                                        return

                                    # Save changes
                                    room = (
                                        session.query(
                                            Rooms
                                        )
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if room:
                                        room.room_label = new_label
                                        room.room_desc = new_desc
                                        room.room_first_agent = a1
                                        room.room_second_agent = a2

                                ui.notify(
                                    f"Room {new_label} was updated "
                                    "successfully",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )

                                edit_dialog.close()
                                refresh_rooms_table()

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
                            f"Room {row['room_label']} -- "
                            f"{row['room_desc']} from the case file?"
                        ).classes("mb-4")

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                            ).props("flat")

                            def on_confirm_delete():
                                with get_session() as session:
                                    room = (
                                        session.query(
                                            Rooms
                                        )
                                        .filter_by(id=row["id"])
                                        .first()
                                    )

                                    if room:
                                        room_label = room.room_label
                                        room_desc = room.room_desc
                                        session.delete(room)
                                    else:
                                        room_label = row["room_label"]
                                        room_desc = row["room_desc"]

                                ui.notify(
                                    f"Room {room_label} -- {room_desc} "
                                    "has been removed from the case file",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )

                                delete_dialog.close()
                                refresh_rooms_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)

                table.on("delete", open_delete_dialog)

    # Initial render
    refresh_rooms_table()

# ── Page Registration ────────────────────────────────────────
@ui.page("/rooms")
def rooms_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return
    build_rooms_page()
