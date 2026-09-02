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

from home_page import confirm_new_case_handler
from main import get_current_user_name, get_is_admin
from models import get_session, Evidence
from navbar import build_navbar
from utils import (
    required_input,
    required_select,
    load_agent_names,
    load_room_labels,
    get_next_evid_num,
    confirm_delete_all,
    validate_initial_evidence,
    validate_update_evidence
)


# ----- Main Page Builder -----
def build_evidence_page():
    """Builds the full Evidence page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
        )

    with ui.column().classes("w-full items-center"):

        ui.label("Evidence Management").classes("text-2xl font-bold m-4")

        # ----- TWO-COLUMN GRID LAYOUT -----
        with ui.card().classes("w-full max-w-6xl mx-auto p-6"):

            with ui.grid(columns=2).classes("w-full gap-6 items-start"):

                # ----- LEFT COLUMN (Fields 1-7) -----
                with ui.column().classes("gap-4"):

                    next_evid = get_next_evid_num()
                    agent_options = load_agent_names()
                    room_options = load_room_labels()

                    evid_num_input = required_input(
                        label="Evidence Item Number",
                        value=next_evid,
                        ).classes("w-full")

                    evid_num_input.props("readonly")

                    evid_qty_input = required_input(
                        label="Quantity"
                        ).classes("w-full")

                    evid_qty_input.props("autofocus")

                    evid_desc_input = required_input(
                        label="Evidence Description"
                        ).classes("w-full")

                    evid_model_input = ui.input(
                        label="Model Number"
                        ).classes("w-full")

                    evid_serial_input = ui.input(
                        label="Serial Number"
                        ).classes("w-full")

                    evid_room_combo = required_select(
                        options=room_options,
                        label="Room Located",
                        with_input=True,
                        ).classes("w-full")

                    evid_room_detail_input = required_input(
                        label="Where Located"
                        ).classes("w-full")

                # ----- RIGHT COLUMN (Fields 8-14) -----
                with ui.column().classes("gap-4"):

                    evid_found_by_combo = required_select(
                        options=agent_options,
                        label="Found By",
                        with_input=True,
                        ).classes("w-full")

                    evid_witness_combo = required_select(
                        options=agent_options,
                        label="Witnessed By",
                        with_input=True,
                        ).classes("w-full")

                    evid_pic_combo = ui.select(
                        options=["Yes", "No"],
                        label="Item Photographed",
                        ).classes("w-full")

                    evid_triaged_combo = ui.select(
                        options=["", "Yes", "No"],
                        label="Item Triaged?",
                        ).classes("w-full")

                    evid_triaged_by_combo = ui.select(
                        options=agent_options,
                        label="Triaged By",
                        with_input=True,
                        ).classes("w-full")

                    evid_triaged_by_combo.disable()

                    evid_contraband_combo = ui.select(
                        options=["", "Yes", "No", "Unknown", "N/A"],
                        label="Contains Contraband?",
                        ).classes("w-full")

                    evid_note_input = ui.input(
                        label="Notes"
                        ).classes("w-full")

            # ----- Triaged toggle logic -----
            def on_triage_change(e):

                if e.value == "Yes":

                    evid_triaged_by_combo.enable()

                else:

                    evid_triaged_by_combo.disable()
                    evid_triaged_by_combo.value = None

            evid_triaged_combo.on_value_change(on_triage_change)

            # ----- Buttons -----
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
                    evid_note_input.value = ""

                def on_submit():
                    """Handles form submission for new evidence items."""
                    evid_num = evid_num_input.value
                    evid_qty = evid_qty_input.value
                    evid_desc = evid_desc_input.value
                    evid_loc_room = evid_room_combo.value
                    evid_room_detail = evid_room_detail_input.value
                    evid_found_by = evid_found_by_combo.value
                    evid_witness = evid_witness_combo.value
                    evid_triaged = evid_triaged_combo.value or ""
                    evid_triaged_by = evid_triaged_by_combo.value or ""

                    # ----- Required field validation -----
                    if not validate_initial_evidence(
                        evid_num=evid_num,
                        evid_qty=evid_qty,
                        evid_desc= evid_desc,
                        evid_loc_room=evid_loc_room,
                        evid_room_detail=evid_room_detail,
                        evid_found_by=evid_found_by,
                        evid_witness=evid_witness,
                        evid_triaged=evid_triaged,
                        evid_triaged_by=evid_triaged_by
                        ):

                        return

                    with get_session() as session:

                        # ----- Save to database -----
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
                            evid_is_contraband=(
                                evid_contraband_combo.value or ""
                                ),
                            evid_note=evid_note_input.value or ""
                            )

                        session.add(new_evid)

                    ui.notify(
                        f"Evidence Item {evid_num} ({evid_desc}) has been "
                        "added to the case file.",
                        type="positive",
                        timeout=2000,
                        position="bottom",
                        close_button="OK",
                        )

                    clear_form()
                    refresh_evidence_table()

                ui.button("Clear", on_click=clear_form
                    ).props("flat")

                ui.button("Add Evidence Item", on_click=on_submit
                    ).props("unelevated")

        # ----- Existing Evidence Table -----
        ui.separator().classes("my-6")

        with ui.column().classes("w-full items-center"):

            ui.label("Evidence Items").classes("text-xl font-bold mb-3")

            with ui.row().classes("w-full max-w-6xl items-center"):

                table_container = ui.column().classes(
                    "w-full max-w-5xl mx-auto items-center gap-2")

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
                                "evid_loc_room_detail": (
                                    r.evid_loc_room_detail or ""),
                                "evid_found_by": r.evid_found_by or "",
                                "evid_found_by_witness": (
                                    r.evid_found_by_witness or ""),
                                "evid_pic_taken": r.evid_pic_taken or "",
                                "evid_triaged": r.evid_triaged or "",
                                "evid_triaged_by": r.evid_triaged_by or "",
                                "evid_is_contraband": (
                                    r.evid_is_contraband or ""),
                                "evid_note": r.evid_note or ""
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
                                "field": "evid_is_contraband",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "actions",
                                "label": "Actions",
                                "field": "actions",
                                "sortable": False,
                                "align": "center",
                            }
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
                                        icon="edit" size="sm" @click=\
                                        "$parent.$emit('edit', \
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
                        def open_edit_dialog(e):

                            row = e.args

                            current_agents = load_agent_names()
                            current_rooms = load_room_labels()

                            with ui.dialog() as edit_dialog, ui.card(
                                ).classes("w-full max-w-3xl p-6"):

                                ui.label(
                                    f"Edit Evidence: {row['evid_num']}"
                                    ).classes("text-lg font-semibold mb-4")

                                new_evid_num = required_input(
                                    label="Evidence Item Number",
                                    value=row["evid_num"],
                                    ).classes("w-full")

                                new_evid_qty = required_input(
                                    label="Quantity",
                                    value=row["evid_qty"],
                                    ).classes("w-full")

                                new_evid_desc = required_input(
                                    label="Evidence Description",
                                    value=row["evid_desc"],
                                    ).classes("w-full")

                                new_evid_model_num = ui.input(
                                    label="Model Number",
                                    value=row["evid_model_num"],
                                    ).classes("w-full")

                                new_evid_serial_num = ui.input(
                                    label="Serial Number",
                                    value=row["evid_serial_num"],
                                    ).classes("w-full")

                                new_evid_loc_room = required_select(
                                    options=current_rooms,
                                    label="Room Located",
                                    value=row["evid_loc_room"] or None,
                                    with_input=True,
                                    ).classes("w-full")

                                new_evid_loc_room_detail = required_input(
                                    label="Where Located",
                                    value=row["evid_loc_room_detail"],
                                    ).classes("w-full")

                                new_evid_found_by = required_select(
                                    options=current_agents,
                                    label="Found By",
                                    value=row["evid_found_by"] or None,
                                    with_input=True,
                                    ).classes("w-full")

                                new_evid_found_by_witness = required_select(
                                    options=current_agents,
                                    label="Witnessed By",
                                    value=row["evid_found_by_witness"] or None,
                                    with_input=True,
                                    ).classes("w-full")

                                new_evid_pic_taken = ui.select(
                                    options=["Yes", "No"],
                                    label="Item Photographed",
                                    value=row["evid_pic_taken"] or None,
                                    ).classes("w-full")

                                new_evid_triaged = ui.select(
                                    options=["", "Yes", "No"],
                                    label="Item Triaged?",
                                    value=row["evid_triaged"] or None,
                                    ).classes("w-full")

                                new_evid_triaged_by = ui.select(
                                    options=current_agents,
                                    label="Triaged By",
                                    value=row["evid_triaged_by"] or None,
                                    with_input=True,
                                    ).classes("w-full")

                                # Enable/disable triaged_by based on
                                # current triaged value
                                if row["evid_triaged"] != "Yes":
                                    new_evid_triaged_by.disable()

                                def on_edit_triage_change(ev):

                                    if ev.value == "Yes":

                                        new_evid_triaged_by.enable()

                                    else:

                                        new_evid_triaged_by.disable()
                                        new_evid_triaged_by.value = None

                                new_evid_triaged.on_value_change(
                                    on_edit_triage_change)

                                new_evid_contraband = ui.select(
                                    options=["","Yes","No","Unknown","N/A"],
                                    label="Contains Contraband?",
                                    value=(
                                        row["evid_is_contraband"] or None
                                        ),
                                    ).classes("w-full")

                                new_evid_note = ui.input(
                                    label="Notes",
                                    value=row["evid_note"],
                                    ).classes("w-full")

                                with ui.row().classes(
                                    "w-full justify-end gap-2 mt-4"
                                    ):

                                    ui.button("Cancel",
                                        on_click=edit_dialog.close,
                                        ).props("flat")

                                    def on_save_update():
                                        """Handles form submission for
                                        updating existing evidence item.
                                        """
                                        with get_session() as session:

                                            evid = (
                                                session.query(Evidence)
                                                .filter_by(id=row["id"])
                                                .first()
                                                )

                                            if evid:
                                                evid.evid_num = new_evid_num
                                                evid.evid_qty = (
                                                    new_evid_qty.value
                                                    or ""
                                                    )
                                                evid.evid_desc = (
                                                    new_evid_desc.value
                                                    or ""
                                                    )
                                                evid.evid_model_num = (
                                                    new_evid_model_num.value
                                                    or ""
                                                    )
                                                evid.evid_serial_num = (
                                                    new_evid_serial_num.value
                                                    or ""
                                                    )
                                                evid.evid_loc_room = (
                                                    new_evid_loc_room.value
                                                    or ""
                                                    )
                                                evid.evid_loc_room_detail = (
                                                    new_evid_loc_room_detail.value
                                                    or ""
                                                    )
                                                evid.evid_found_by = (
                                                    new_evid_found_by.value
                                                    )
                                                evid.evid_found_by_witness = (
                                                    new_evid_found_by_witness.value
                                                    )
                                                evid.evid_pic_taken = (
                                                    new_evid_pic_taken.value
                                                    or ""
                                                    )
                                                evid.evid_triaged = (
                                                    new_evid_triaged.value
                                                    )
                                                evid.evid_triaged_by = (
                                                    new_evid_triaged_by.value
                                                    )
                                                evid.evid_is_contraband = (
                                                    new_evid_contraband.value
                                                    or ""
                                                    )
                                                evid.evid_note = (
                                                    new_evid_note.value
                                                    or ""
                                                    )

                                            # ----- Required field validation -----
                                            if not validate_update_evidence(
                                                new_evid_num=new_evid_num,
                                                new_evid_found_by=new_evid_found_by,
                                                new_evid_found_by_witness=new_evid_found_by_witness,
                                                new_evid_triaged=new_evid_triaged,
                                                new_evid_triaged_by=new_evid_triaged_by,
                                                row=row,
                                                ):

                                                return

                                        ui.notify(
                                            f"Item {new_evid_num} was "
                                            "successfully updated.",
                                            type="positive",
                                            timeout=2000,
                                            position="bottom",
                                            close_button="OK",
                                            )

                                        edit_dialog.close()
                                        refresh_evidence_table()

                                    ui.button("Save",
                                        on_click=on_save_update,
                                        ).props("unelevated")

                            edit_dialog.open()

                        # ----- Delete confirmation dialog -----
                        def open_delete_dialog(e):

                            row = e.args

                            with ui.dialog() as delete_dialog, ui.card(
                                ).classes("max-w-sm p-6"):

                                ui.label("Confirm Deletion"
                                    ).classes("text-lg font-semibold mb-2")

                                ui.label(
                                    f"Are you sure you want to delete "
                                    f"Item {row['evid_num']} -- "
                                    f"{row['evid_desc']}?"
                                    ).classes("mb-4")

                                with ui.row().classes(
                                    "w-full justify-end gap-2"
                                    ):

                                    ui.button("Cancel",
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
                                            f"Item {evid_num} ({evid_desc}) "
                                            "was deleted successfully.",
                                            type="positive",
                                            timeout=2000,
                                            position="bottom",
                                            close_button="OK",
                                            )

                                        delete_dialog.close()
                                        refresh_evidence_table()

                                    ui.button("Delete",
                                        on_click=on_confirm_delete,
                                        color="#ef4444",
                                        ).props("negative unelevated")

                            delete_dialog.open()

                        table.on("edit", open_edit_dialog)
                        table.on("delete", open_delete_dialog)

            with ui.row().classes("w-full justify-center my-2"):

                def delete_all_evidence():

                    with get_session() as session:

                        session.query(Evidence).delete()
                        session.commit()

                    ui.notify(
                        "All evidence has been deleted.",
                        type="positive",
                        timeout=2000,
                        position="bottom",
                        close_button="OK",
                        )

                    refresh_evidence_table()

                ui.button(
                    "Clear All Evidence",
                    on_click=lambda: confirm_delete_all(
                        "evidence",
                        delete_all_evidence,
                        ),
                        color="#ef4444",
                    ).props("unelevated").classes("mb-2 items-center")

    # ----- Initial render -----
    refresh_evidence_table()
