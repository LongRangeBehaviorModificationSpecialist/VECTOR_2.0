#!/usr/bin/env python3

"""
evidence_page.py

Consolidates four Flask routes into one interactive page:
    /evidence_list       →  table display + delete
    /evidence_add_page   →  add form (auto-generates next evidence number)
    /evidence_update     →  inline edit dialog
    /evidence_delete     →  delete with confirmation
"""

from nicegui import ui

from main_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler,
)
from models import get_session, Agents, Evidence, Rooms
from navbar import build_navbar, confirm_new_case_dialog
from utils import required_input, required_select, MESSAGES

NOTIFICATION_TIMEOUT = 0
POSITIVE_NOTIFICATION_TIMEOUT = 4000


# ── Helpers ─────────────────────────────────────────────────
def load_agent_names() -> list[str]:
    """Returns a list of all agent names from the Agents table."""
    with get_session() as session:
        rows = (
            session.query(Agents.agent_name)
            .order_by(Agents.agent_name)
            .all()
        )
        return [r[0] for r in rows]


def load_room_labels() -> list[str]:
    """Returns a list of all room labels from the Rooms table."""
    with get_session() as session:
        rows = (
            session.query(Rooms.room_label)
            .order_by(Rooms.room_label)
            .all()
        )
        return [r[0] for r in rows]


def get_next_evid_num() -> str:
    """Gets the highest evidence number from the database and
    increments it.

    Returns "1" if no evidence exists yet.
    """
    with get_session() as session:
        evid_query = (
            session.query(Evidence)
            .order_by(Evidence.evid_num)
            .all()
        )

        if evid_query:
            last_evid = evid_query[-1]
            try:
                last_id = int(last_evid.evid_num)
                next_id = last_id + 1
                return str(next_id)
            except ValueError:
                return "1"
        else:
            return "1"


# ── Main Page Builder
def build_evidence_page():
    """Builds the full Evidence page UI."""

    # ── Header / Navbar

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Evidence Management"
        ).classes("text-2xl font-bold m-4")

        # ── Add Evidence Form
        with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

            ui.label(
                "Add Evidence Item"
            ).classes("text-lg font-semibold mb-4")

            next_evid = get_next_evid_num()
            agent_options = load_agent_names()
            room_options = load_room_labels()

            # evid_num — StringField, pre-populated with next number
            evid_num_input = required_input(
                label="Evidence Item Number",
                value=next_evid,
            ).classes("w-full")
            evid_num_input.props("readonly")

            # evid_qty — StringField (required, autofocused)
            evid_qty_input = required_input(
                label="Quantity"
            ).classes("w-full")
            evid_qty_input.props("autofocus")

            # evid_desc — StringField (required)
            evid_desc_input = required_input(
                label="Evidence Description"
            ).classes("w-full")

            # evid_model_num — StringField
            evid_model_input = ui.input(
                label="Model Number"
            ).classes("w-full")

            # evid_serial_num — StringField
            evid_serial_input = ui.input(
                label="Serial Number"
            ).classes("w-full")

            # evid_loc_room — (required), populated from Rooms
            evid_room_combo = required_select(
                options=room_options,
                label="Room Located",
                with_input=True,
            ).classes("w-full")

            # evid_loc_room_detail — (required)
            evid_room_detail_input = required_input(
                label="Where Located"
            ).classes("w-full")

            # evid_found_by — (required), populated from Agents
            evid_found_by_combo = required_select(
                options=agent_options,
                label="Found By",
                with_input=True,
            ).classes("w-full")

            # evid_found_by_witness — (required), populated from Agents
            evid_witness_combo = required_select(
                options=agent_options,
                label="Witnessed By",
                with_input=True,
            ).classes("w-full")

            # evid_pic_taken — (Yes/No)
            evid_pic_combo = ui.select(
                options=["Yes", "No"],
                label="Item Photographed",
            ).classes("w-full")

            # evid_triaged — (empty/Yes/No)
            evid_triaged_combo = ui.select(
                options=["", "Yes", "No"],
                label="Item Triaged?",
            ).classes("w-full")

            # evid_triaged_by — disabled until triaged = Yes
            evid_triaged_by_combo = ui.select(
                options=agent_options,
                label="Triaged By",
                with_input=True,
            ).classes("w-full")
            evid_triaged_by_combo.disable()

            # evid_contains_contraband
            evid_contraband_combo = ui.select(
                options=["", "Yes", "No", "Unknown", "N/A"],
                label="Contains Contraband?",
            ).classes("w-full")

            # evid_notes — TextAreaField
            evid_notes_input = ui.textarea(
                label="Notes"
            ).classes("w-full")

            # ── Triaged toggle logic ─────────────────────────────
            def on_triage_change(e):

                if e.value == "Yes":
                    evid_triaged_by_combo.enable()
                else:
                    evid_triaged_by_combo.disable()
                    evid_triaged_by_combo.value = None

            evid_triaged_combo.on_value_change(on_triage_change)

            # ── Buttons ────────────────────────────────────────
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form():
                    evid_num_input.value = get_next_evid_num()
                    evid_qty_input.value = ""
                    evid_desc_input.value = ""
                    evid_model_input.value = ""
                    evid_serial_input.value = ""
                    evid_room_combo.value = None
                    evid_room_detail_input.value = ""
                    evid_found_by_combo.value = None
                    evid_witness_combo.value = None
                    evid_pic_combo.value = None
                    evid_triaged_combo.value = None
                    evid_triaged_by_combo.value = None
                    evid_triaged_by_combo.disable()
                    evid_contraband_combo.value = None
                    evid_notes_input.value = ""

                def on_submit():
                    # ── Required field validation ──
                    evid_num = evid_num_input.value

                    if not evid_num:
                        ui.notify(
                            MESSAGES["evid_3"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    evid_qty = evid_qty_input.value

                    if not evid_qty:
                        ui.notify(
                            MESSAGES["evid_4"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    evid_desc = evid_desc_input.value

                    if not evid_desc:
                        ui.notify(
                            MESSAGES["evid_5"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    evid_loc_room = evid_room_combo.value

                    if not evid_loc_room:
                        ui.notify(
                            MESSAGES["evid_6"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    evid_room_detail = evid_room_detail_input.value

                    if not evid_room_detail:
                        ui.notify(
                            MESSAGES["evid_7"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    evid_found_by = evid_found_by_combo.value

                    if not evid_found_by:
                        ui.notify(
                            MESSAGES["evid_8"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    evid_witness = evid_witness_combo.value

                    if not evid_witness:
                        ui.notify(
                            MESSAGES["evid_9"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    # ── Cross-field validation ──
                    # Same agent check
                    if evid_found_by == evid_witness:
                        ui.notify(
                            MESSAGES["evid_2"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    # Triaged validation
                    evid_triaged = evid_triaged_combo.value or ""
                    evid_triaged_by = evid_triaged_by_combo.value or ""
                    if evid_triaged == "Yes" and not evid_triaged_by:
                        ui.notify(
                            MESSAGES["evid_1"],
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                            close_button="OK",
                            position="center",
                        )
                        return

                    # ── Duplicate evidence number check ──
                    with get_session() as session:
                        existing = (
                            session.query(Evidence)
                            .filter_by(evid_num=evid_num)
                            .first()
                        )

                        if existing:
                            ui.notify(
                                f"Evidence Item Number '{evid_num}' is "
                                "already used.",
                                type="negative",
                                timeout=NOTIFICATION_TIMEOUT,
                                close_button="OK",
                                position="center",
                            )
                            return

                        # ── Save to database ──
                        new_evid = Evidence(
                            evid_num=evid_num,
                            evid_qty=evid_qty,
                            evid_desc=evid_desc,
                            evid_model_num=evid_model_input.value or "",
                            evid_serial_num=evid_serial_input.value or "",
                            evid_loc_room=evid_loc_room,
                            evid_loc_room_detail=evid_room_detail,
                            evid_found_by=evid_found_by,
                            evid_found_by_witness=evid_witness,
                            evid_pic_taken=evid_pic_combo.value or "",
                            evid_triaged=evid_triaged,
                            evid_triaged_by=evid_triaged_by,
                            evid_contains_contraband=evid_contraband_combo.value or "",
                            evid_notes=evid_notes_input.value or "",
                        )
                        session.add(new_evid)

                    ui.notify(
                        f"Evidence Item {evid_num} ({evid_desc}) has been "
                        "added to the case file.",
                        timeout=POSITIVE_NOTIFICATION_TIMEOUT,
                        close_button="OK",
                        position="bottom",
                    )

                    clear_form()
                    refresh_evidence_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                ).props("outline")

                ui.button(
                    "Add Evidence Item",
                    on_click=on_submit,
                ).props("unelevated")

        # ── Existing Evidence Table ──────────────────────────────
        ui.separator().classes("my-6")
        ui.label(
            "Current Evidence Items"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_evidence_table():
            """Re-renders the evidence table from the database."""
            table_container.clear()

            with get_session() as session:

                evidence = (
                    session.query(Evidence)
                    .order_by(Evidence.evid_num)
                    .all()
                )

                if not evidence:
                    with table_container:
                        ui.label(
                            "No evidence items in the database yet."
                        ).classes("text-gray-500 italic")
                    return

                row_data = [
                    {
                        "id": r.id,
                        "evid_num": r.evid_num or "",
                        "evid_qty": r.evid_qty or "",
                        "evid_desc": r.evid_desc or "",
                        "evid_model_num": r.evid_model_num or "",
                        "evid_serial_num": r.evid_serial_num or "",
                        "evid_loc_room": r.evid_loc_room or "",
                        "evid_loc_room_detail": r.evid_loc_room_detail or "",
                        "evid_found_by": r.evid_found_by or "",
                        "evid_found_by_witness": r.evid_found_by_witness or "",
                        "evid_pic_taken": r.evid_pic_taken or "",
                        "evid_triaged": r.evid_triaged or "",
                        "evid_triaged_by": r.evid_triaged_by or "",
                        "evid_contains_contraband": r.evid_contains_contraband or "",
                        "evid_notes": r.evid_notes or "",
                    }
                    for r in evidence
                ]

            with table_container:
                column_defs = [
                    {
                        "name": "evid_num",
                        "label": "Evid #",
                        "field": "evid_num",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "evid_qty",
                        "label": "Qty",
                        "field": "evid_qty",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "evid_desc",
                        "label": "Description",
                        "field": "evid_desc",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "evid_loc_room",
                        "label": "Room",
                        "field": "evid_loc_room",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "evid_found_by",
                        "label": "Found By",
                        "field": "evid_found_by",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "evid_found_by_witness",
                        "label": "Witness",
                        "field": "evid_found_by_witness",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "evid_triaged",
                        "label": "Triaged",
                        "field": "evid_triaged",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "evid_contraband",
                        "label": "Contraband",
                        "field": "evid_contains_contraband",
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
                    current_agents = load_agent_names()
                    current_rooms = load_room_labels()

                    with ui.dialog() as edit_dialog, ui.card().classes(
                        "w-full max-w-3xl p-6"
                    ):
                        ui.label(
                            f"Edit Evidence: {row['evid_num']}"
                        ).classes("text-lg font-semibold mb-4")

                        edit_num = required_input(
                            label="Evidence Item Number",
                            value=row["evid_num"],
                        ).classes("w-full")

                        edit_qty = required_input(
                            label="Quantity",
                            value=row["evid_qty"],
                        ).classes("w-full")

                        edit_desc = required_input(
                            label="Evidence Description",
                            value=row["evid_desc"],
                        ).classes("w-full")

                        edit_model = ui.input(
                            label="Model Number",
                            value=row["evid_model_num"],
                        ).classes("w-full")

                        edit_serial = ui.input(
                            label="Serial Number",
                            value=row["evid_serial_num"],
                        ).classes("w-full")

                        edit_room = required_select(
                            options=current_rooms,
                            label="Room Located",
                            value=row["evid_loc_room"] or None,
                            with_input=True,
                        ).classes("w-full")

                        edit_room_detail = required_input(
                            label="Where Located",
                            value=row["evid_loc_room_detail"],
                        ).classes("w-full")

                        edit_found_by = required_select(
                            options=current_agents,
                            label="Found By",
                            value=row["evid_found_by"] or None,
                            with_input=True,
                        ).classes("w-full")

                        edit_witness = required_select(
                            options=current_agents,
                            label="Witnessed By",
                            value=row["evid_found_by_witness"] or None,
                            with_input=True,
                        ).classes("w-full")

                        edit_pic = ui.select(
                            options=["Yes", "No"],
                            label="Item Photographed",
                            value=row["evid_pic_taken"] or None,
                        ).classes("w-full")

                        edit_triaged = ui.select(
                            options=["", "Yes", "No"],
                            label="Item Triaged?",
                            value=row["evid_triaged"] or None,
                        ).classes("w-full")

                        edit_triaged_by = ui.select(
                            options=current_agents,
                            label="Triaged By",
                            value=row["evid_triaged_by"] or None,
                            with_input=True,
                        ).classes("w-full")

                        # Enable/disable triaged_by based on
                        # current triaged value
                        if row["evid_triaged"] != "Yes":
                            edit_triaged_by.disable()

                        def on_edit_triage_change(ev):
                            if ev.value == "Yes":
                                edit_triaged_by.enable()
                            else:
                                edit_triaged_by.disable()
                                edit_triaged_by.value = None

                        edit_triaged.on_value_change(on_edit_triage_change)

                        edit_contraband = ui.select(
                            options=["", "Yes", "No", "Unknown", "N/A"],
                            label="Contains Contraband?",
                            value=row["evid_contains_contraband"] or None,
                        ).classes("w-full")

                        edit_notes = ui.textarea(
                            label="Notes",
                            value=row["evid_notes"],
                        ).classes("w-full")

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"
                        ):
                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                            ).props("flat")

                            def on_save_update():
                                # Cross-field validation
                                new_found_by = edit_found_by.value or ""
                                new_witness = edit_witness.value or ""

                                if (
                                    new_found_by
                                    and new_witness
                                    and new_found_by == new_witness
                                ):
                                    ui.notify(
                                        MESSAGES["evid_2"],
                                        type="warning",
                                        timeout=NOTIFICATION_TIMEOUT,
                                        close_button="OK",
                                        position="center",
                                    )
                                    return

                                new_triaged = edit_triaged.value or ""
                                new_triaged_by = edit_triaged_by.value or ""

                                if new_triaged == "Yes" and not new_triaged_by:

                                    ui.notify(
                                        MESSAGES["evid_1"],
                                        type="warning",
                                        timeout=NOTIFICATION_TIMEOUT,
                                        close_button="OK",
                                        position="center",
                                    )
                                    return

                                # Duplicate evidence number check
                                # (exclude self)
                                new_num = edit_num.value or ""
                                with get_session() as session:
                                    dup = (
                                        session.query(Evidence)
                                        .filter(
                                            Evidence.evid_num == new_num,
                                            Evidence.id != row["id"],
                                        )
                                        .first()
                                    )

                                    if dup:
                                        ui.notify(
                                            f"Evidence number {new_num} is "
                                            "already used",
                                            type="warning",
                                            timeout=NOTIFICATION_TIMEOUT,
                                            close_button="OK",
                                            position="center",
                                        )
                                        return

                                    evid = (
                                        session.query(Evidence)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if evid:
                                        evid.evid_num = new_num
                                        evid.evid_qty = (
                                            edit_qty.value or ""
                                        )
                                        evid.evid_desc = (
                                            edit_desc.value or ""
                                        )
                                        evid.evid_model_num = (
                                            edit_model.value or ""
                                        )
                                        evid.evid_serial_num = (
                                            edit_serial.value or ""
                                        )
                                        evid.evid_loc_room = (
                                            edit_room.value or ""
                                        )
                                        evid.evid_loc_room_detail = (
                                            edit_room_detail.value or ""
                                        )
                                        evid.evid_found_by = (
                                            new_found_by
                                        )
                                        evid.evid_found_by_witness = (
                                            new_witness
                                        )
                                        evid.evid_pic_taken = (
                                            edit_pic.value or ""
                                        )
                                        evid.evid_triaged = new_triaged
                                        evid.evid_triaged_by = (
                                            new_triaged_by
                                        )
                                        evid.evid_contains_contraband = (
                                            edit_contraband.value or ""
                                        )
                                        evid.evid_notes = (
                                            edit_notes.value or ""
                                        )

                                ui.notify(
                                    f"Item {new_num} was successfully " "updated.",
                                    timeout=POSITIVE_NOTIFICATION_TIMEOUT,
                                    close_button="OK",
                                    position="bottom",
                                )

                                edit_dialog.close()
                                refresh_evidence_table()

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
                            f"Item {row['evid_num']} -- "
                            f"{row['evid_desc']}?"
                        ).classes("mb-4")

                        with ui.row().classes(
                            "w-full justify-end gap-2"
                        ):
                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                            ).props("flat")

                            def on_confirm_delete():
                                with get_session() as session:

                                    evid = (
                                        session.query(Evidence)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if evid:
                                        evid_num = evid.evid_num
                                        evid_desc = evid.evid_desc
                                        session.delete(evid)
                                    else:
                                        evid_num = row["evid_num"]
                                        evid_desc = row["evid_desc"]

                                ui.notify(
                                    f"Item {evid_num} ({evid_desc}) was "
                                    "deleted successfully.",
                                    timeout=POSITIVE_NOTIFICATION_TIMEOUT,
                                    close_button="OK",
                                    position="bottom",
                                )
                                delete_dialog.close()
                                refresh_evidence_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#FF0000",
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)

                table.on("delete", open_delete_dialog)

    # Initial render
    refresh_evidence_table()


# ── Page Registration ────────────────────────────────────────
@ui.page("/evidence")
def evidence_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return
    build_evidence_page()
