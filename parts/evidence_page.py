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
    validate_evid_entry,
    get_current_timestamp,
)

# ----- Main Page Builder -----
def build_evidence_page() -> None:
    """Builds the full Evidence page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Evidence Management"
        ).classes("text-2xl font-bold m-4")

        # ----- TWO-COLUMN GRID LAYOUT -----
        with ui.card().classes("w-full max-w-6xl mx-auto p-6"):

            with ui.grid(columns=2).classes("w-full gap-6 items-start"):

                # ----- LEFT COLUMN (Fields 1-7) -----
                with ui.column().classes("gap-4"):

                    next_evid = get_next_evid_num()
                    agent_options = load_agent_names()
                    room_options = load_room_labels()

                    EVIDNUM_input = required_input(
                        label="Evidence Item Number",
                        value=next_evid,
                    ).classes("w-full")

                    EVIDNUM_input.props("readonly")

                    EVIDQTY_input = required_input(
                        label="Quantity"
                    ).classes("w-full")

                    EVIDQTY_input.props("autofocus")

                    EVIDDESC_input = required_input(
                        label="Evidence Description"
                    ).classes("w-full")

                    EVIDMODELNUMBER_input = ui.input(
                        label="Model Number"
                    ).classes("w-full")

                    EVIDSERIALNUMBER_input = ui.input(
                        label="Serial Number"
                    ).classes("w-full")

                    EVIDLOCROOM_combo = required_select(
                        options=room_options,
                        label="Room Located",
                        with_input=True,
                    ).classes("w-full")

                    EVIDLOCROOMDETAIL_input = required_input(
                        label="Where Located"
                    ).classes("w-full")

                # ----- RIGHT COLUMN (Fields 8-14) -----
                with ui.column().classes("gap-4"):

                    EVIDFOUNDBY_combo = required_select(
                        options=agent_options,
                        label="Found By",
                        with_input=True,
                    ).classes("w-full")

                    EVIDFOUNDBYWITNESS_combo = required_select(
                        options=agent_options,
                        label="Witnessed By",
                        with_input=True,
                    ).classes("w-full")

                    EVIDPICTAKEN_combo = ui.select(
                        options=["Yes", "No"],
                        label="Item Photographed",
                    ).classes("w-full")

                    EVIDTRIAGED_combo = ui.select(
                        options=["", "Yes", "No"],
                        label="Item Triaged?",
                    ).classes("w-full")

                    EVIDTRIAGEDBY_combo = ui.select(
                        options=agent_options,
                        label="Triaged By",
                        with_input=True,
                    ).classes("w-full")

                    EVIDTRIAGEDBY_combo.disable()

                    EVIDISCONTRABAND_combo = ui.select(
                        options=["", "Yes", "No", "Unknown", "N/A"],
                        label="Contains Contraband?",
                    ).classes("w-full")

                    EVIDNOTE_input = ui.input(
                        label="Notes"
                    ).classes("w-full")

            # ----- Triaged toggle logic -----
            def on_triage_change(e) -> None:

                if e.value == "Yes":
                    EVIDTRIAGEDBY_combo.enable()
                else:
                    EVIDTRIAGEDBY_combo.disable()
                    EVIDTRIAGEDBY_combo.value = None

            EVIDTRIAGED_combo.on_value_change(on_triage_change)

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form() -> None:
                    EVIDNUM_input.value = get_next_evid_num()
                    EVIDQTY_input.value = ""
                    EVIDDESC_input.value = ""
                    EVIDMODELNUMBER_input.value = ""
                    EVIDSERIALNUMBER_input.value = ""
                    EVIDLOCROOM_combo.value = None
                    EVIDLOCROOMDETAIL_input.value = ""
                    EVIDFOUNDBY_combo.value = None
                    EVIDFOUNDBYWITNESS_combo.value = None
                    EVIDPICTAKEN_combo.value = None
                    EVIDTRIAGED_combo.value = None
                    EVIDTRIAGEDBY_combo.value = None
                    EVIDTRIAGEDBY_combo.disable()
                    EVIDISCONTRABAND_combo.value = None
                    EVIDNOTE_input.value = ""

                def on_submit() -> None:
                    """Handles form submission for new evidence items."""
                    EVIDNUM = EVIDNUM_input.value
                    EVIDQTY = EVIDQTY_input.value
                    EVIDDESC = EVIDDESC_input.value
                    EVIDLOCROOM = EVIDLOCROOM_combo.value
                    EVIDLOCROOMDETAIL = EVIDLOCROOMDETAIL_input.value
                    EVIDFOUNDBY = EVIDFOUNDBY_combo.value
                    EVIDFOUNDBYWITNESS = EVIDFOUNDBYWITNESS_combo.value
                    EVIDTRIAGED = EVIDTRIAGED_combo.value or ""
                    EVIDTRIAGEDBY = EVIDTRIAGEDBY_combo.value or ""

                    # ----- Required field validation -----
                    if validate_evid_entry(
                        stage="initial",
                        EVIDNUM=EVIDNUM,
                        EVIDQTY=EVIDQTY,
                        EVIDDESC=EVIDDESC,
                        EVIDLOCROOM=EVIDLOCROOM,
                        EVIDLOCROOMDETAIL=EVIDLOCROOMDETAIL,
                        EVIDFOUNDBY=EVIDFOUNDBY,
                        EVIDFOUNDBYWITNESS=EVIDFOUNDBYWITNESS,
                        EVIDTRIAGED=EVIDTRIAGED,
                        EVIDTRIAGEDBY=EVIDTRIAGEDBY,
                    ):
                        return

                    with get_session() as session:
                        # ----- Save to database -----
                        new_evid = Evidence(
                            EVIDNUM=EVIDNUM,
                            EVIDQTY=EVIDQTY,
                            EVIDDESC=EVIDDESC,
                            EVIDMODELNUMBER=EVIDMODELNUMBER_input.value or "",
                            EVIDSERIALNUMBER=(
                                EVIDSERIALNUMBER_input.value or ""
                            ),
                            EVIDLOCROOM=EVIDLOCROOM,
                            EVIDLOCROOMDETAIL=EVIDLOCROOMDETAIL,
                            EVIDFOUNDBY=EVIDFOUNDBY,
                            EVIDFOUNDBYWITNESS=EVIDFOUNDBYWITNESS,
                            EVIDPICTAKEN=EVIDPICTAKEN_combo.value or "",
                            EVIDTRIAGED=EVIDTRIAGED,
                            EVIDTRIAGEDBY=EVIDTRIAGEDBY,
                            EVIDISCONTRABAND=(
                                EVIDISCONTRABAND_combo.value or ""
                            ),
                            EVIDNOTE=EVIDNOTE_input.value or "",
                            ENTEREDDATETIME=(
                                get_current_timestamp(format="entry")
                            ),
                        )
                        session.add(new_evid)

                    ui.notify(
                        f"Evidence Item {EVIDNUM} ({EVIDDESC}) has been "
                        "added.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )

                    clear_form()
                    refresh_evidence_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                    color="transparent",
                ).props("flat").classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Evidence Item",
                    on_click=on_submit,
                    color="var(--vsp-blue)",
                ).props("unelevated").classes("text-[var(--vsp-white)]")

        # ----- Existing Evidence Table -----
        ui.separator().classes("my-6")

        with ui.column().classes("w-full items-center"):

            ui.label(
                "Evidence Items"
            ).classes("text-xl font-bold mb-3")

            with ui.row().classes("w-full max-w-6xl items-center"):

                table_container = ui.column().classes(
                    "w-full max-w-5xl mx-auto items-center gap-2"
                )

                def refresh_evidence_table() -> None:
                    """Re-renders the evidence table from the database."""
                    table_container.clear()

                    with get_session() as session:

                        evidence = (
                            session.query(Evidence)
                            .order_by(Evidence.EVIDNUM)
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
                                "Z_PK": r.Z_PK,
                                "EVIDNUM": r.EVIDNUM or "",
                                "EVIDQTY": r.EVIDQTY or "",
                                "EVIDDESC": r.EVIDDESC or "",
                                "EVIDMODELNUMBER": r.EVIDMODELNUMBER or "",
                                "EVIDSERIALNUMBER": r.EVIDSERIALNUMBER or "",
                                "EVIDLOCROOM": r.EVIDLOCROOM or "",
                                "EVIDLOCROOMDETAIL": (
                                    r.EVIDLOCROOMDETAIL or ""
                                ),
                                "EVIDFOUNDBY": r.EVIDFOUNDBY or "",
                                "EVIDFOUNDBYWITNESS": (
                                    r.EVIDFOUNDBYWITNESS or ""
                                ),
                                "EVIDPICTAKEN": r.EVIDPICTAKEN or "",
                                "EVIDTRIAGED": r.EVIDTRIAGED or "",
                                "EVIDTRIAGEDBY": r.EVIDTRIAGEDBY or "",
                                "EVIDISCONTRABAND": (
                                    r.EVIDISCONTRABAND or ""
                                ),
                                "EVIDNOTE": r.EVIDNOTE or ""
                            }
                            for r in evidence
                        ]

                    with table_container:
                        column_defs = [
                            {
                                "name": "EVIDNUM",
                                "label": "Evid #",
                                "field": "EVIDNUM",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDQTY",
                                "label": "Qty",
                                "field": "EVIDQTY",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDDESC",
                                "label": "Description",
                                "field": "EVIDDESC",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDLOCROOM",
                                "label": "Room",
                                "field": "EVIDLOCROOM",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDFOUNDBY",
                                "label": "Found By",
                                "field": "EVIDFOUNDBY",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDFOUNDBYWITNESS",
                                "label": "Witness",
                                "field": "EVIDFOUNDBYWITNESS",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDTRIAGED",
                                "label": "Triaged",
                                "field": "EVIDTRIAGED",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDISCONTRABAND",
                                "label": "Contraband",
                                "field": "EVIDISCONTRABAND",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "EVIDNOTE",
                                "label": "Note(s)",
                                "field": "EVIDNOTE",
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
                            current_rooms = load_room_labels()

                            with ui.dialog() as edit_dialog, ui.card(
                                ).classes("w-full max-w-3xl p-6"
                            ):

                                ui.label(
                                    f"Edit Evidence (Item {row['EVIDNUM']} - "
                                    f"{row['EVIDDESC']})"
                                    ).classes(
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                EVIDNUM_input = required_input(
                                    label="Evidence Item Number",
                                    value=row["EVIDNUM"],
                                ).classes("w-full")

                                EVIDQTY_input = required_input(
                                    label="Quantity",
                                    value=row["EVIDQTY"],
                                ).classes("w-full")

                                EVIDDESC_input = required_input(
                                    label="Evidence Description",
                                    value=row["EVIDDESC"],
                                ).classes("w-full")

                                EVIDMODELNUMBER_input = ui.input(
                                    label="Model Number",
                                    value=row["EVIDMODELNUMBER"],
                                ).classes("w-full")

                                EVIDSERIALNUMBER_input = ui.input(
                                    label="Serial Number",
                                    value=row["EVIDSERIALNUMBER"],
                                ).classes("w-full")

                                EVIDLOCROOM_combo = required_select(
                                    options=current_rooms,
                                    label="Room Located",
                                    value=row["EVIDLOCROOM"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                EVIDLOCROOMDETAIL_input = required_input(
                                    label="Where Located",
                                    value=row["EVIDLOCROOMDETAIL"],
                                ).classes("w-full")

                                EVIDFOUNDBY_combo = required_select(
                                    options=current_agents,
                                    label="Found By",
                                    value=row["EVIDFOUNDBY"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                EVIDFOUNDBYWITNESS_combo = required_select(
                                    options=current_agents,
                                    label="Witnessed By",
                                    value=row["EVIDFOUNDBYWITNESS"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                EVIDPICTAKEN_combo = ui.select(
                                    options=["Yes", "No"],
                                    label="Item Photographed",
                                    value=row["EVIDPICTAKEN"] or None,
                                ).classes("w-full")

                                EVIDTRIAGED_combo = ui.select(
                                    options=["", "Yes", "No"],
                                    label="Item Triaged?",
                                    value=row["EVIDTRIAGED"] or None,
                                ).classes("w-full")

                                EVIDTRIAGEDBY_combo = ui.select(
                                    options=current_agents,
                                    label="Triaged By",
                                    value=row["EVIDTRIAGEDBY"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                # Enable/disable triaged_by based on
                                # current triaged value
                                if row["EVIDTRIAGED"] != "Yes":
                                    EVIDTRIAGEDBY_combo.disable()

                                def on_edit_triage_change(ev) -> None:
                                    if ev.value == "Yes":
                                        EVIDTRIAGEDBY_combo.enable()
                                    else:
                                        EVIDTRIAGEDBY_combo.disable()
                                        EVIDTRIAGEDBY_combo.value = None

                                EVIDTRIAGEDBY_combo.on_value_change(
                                    on_edit_triage_change
                                )

                                EVIDISCONTRABAND_combo = ui.select(
                                    options=["","Yes","No","Unknown","N/A"],
                                    label="Contains Contraband?",
                                    value=(
                                        row["EVIDISCONTRABAND"] or None
                                    ),
                                ).classes("w-full")

                                EVIDNOTE_input = ui.input(
                                    label="Notes",
                                    value=row["EVIDNOTE"],
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
                                        """Handles form submission for
                                        updating existing evidence item.
                                        """
                                        EVIDNUM = EVIDNUM_input.value
                                        EVIDQTY = (
                                            EVIDQTY_input.value
                                            or ""
                                        )
                                        EVIDDESC = EVIDDESC_input.value or ""
                                        EVIDMODELNUMBER = (
                                            EVIDMODELNUMBER_input.value or ""
                                        )
                                        EVIDSERIALNUMBER = (
                                            EVIDSERIALNUMBER_input.value or ""
                                        )
                                        EVIDLOCROOM = (
                                            EVIDLOCROOM_combo.value
                                            or ""
                                        )
                                        EVIDLOCROOMDETAIL = (
                                            EVIDLOCROOMDETAIL_input.value or ""
                                        )
                                        EVIDFOUNDBY = (
                                            EVIDFOUNDBY_combo.value
                                        )
                                        EVIDFOUNDBYWITNESS = (
                                            EVIDFOUNDBYWITNESS_combo.value
                                        )
                                        EVIDPICTAKEN = (
                                            EVIDPICTAKEN_combo.value
                                            or ""
                                        )
                                        EVIDTRIAGED = (
                                            EVIDTRIAGED_combo.value
                                        )
                                        EVIDTRIAGEDBY = (
                                            EVIDTRIAGEDBY_combo.value
                                        )
                                        EVIDISCONTRABAND = (
                                            EVIDISCONTRABAND_combo.value
                                            or ""
                                        )
                                        EVIDNOTE = EVIDNOTE_input.value or ""

                                        # ----- Validate req fields -----
                                        if validate_evid_entry(
                                            stage="update",
                                            EVIDNUM=EVIDNUM,
                                            EVIDFOUNDBY=EVIDFOUNDBY,
                                            EVIDFOUNDBYWITNESS=(
                                                EVIDFOUNDBYWITNESS
                                            ),
                                            EVIDTRIAGED=EVIDTRIAGED,
                                            EVIDTRIAGEDBY=EVIDTRIAGEDBY,
                                            row=row,
                                        ):
                                            return

                                        with get_session() as session:

                                            evid = (
                                                session.query(Evidence)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )

                                            if evid:
                                                evid.EVIDNUM = EVIDNUM
                                                evid.EVIDQTY = EVIDQTY
                                                evid.EVIDDESC = EVIDDESC
                                                evid.EVIDMODELNUMBER = (
                                                    EVIDMODELNUMBER
                                                )
                                                evid.EVIDSERIALNUMBER = (
                                                    EVIDSERIALNUMBER
                                                )
                                                evid.EVIDLOCROOM = EVIDLOCROOM
                                                evid.EVIDLOCROOMDETAIL = (
                                                    EVIDLOCROOMDETAIL
                                                )
                                                evid.EVIDFOUNDBY = (
                                                    EVIDFOUNDBY
                                                )
                                                evid.EVIDFOUNDBYWITNESS = (
                                                    EVIDFOUNDBYWITNESS
                                                )
                                                evid.EVIDPICTAKEN = (
                                                    EVIDPICTAKEN
                                                )
                                                evid.EVIDTRIAGED = (
                                                    EVIDTRIAGED
                                                )
                                                evid.EVIDTRIAGEDBY = (
                                                    EVIDTRIAGEDBY
                                                )
                                                evid.EVIDISCONTRABAND = (
                                                    EVIDISCONTRABAND
                                                )
                                                evid.EVIDNOTE = EVIDNOTE

                                        ui.notify(
                                            f"Item {EVIDNUM} was updated.",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        edit_dialog.close()
                                        refresh_evidence_table()

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
                                    "Delete Evidence Item?"
                                    ).classes(
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                ui.label(
                                    f"The following Evidence Item will be "
                                    "removed from the case file : "
                                ).classes(
                                    "mb-3 text-base text-[var(--vsp-gray)]"
                                )

                                ui.label(
                                    f"Item {row['EVIDNUM']} -- "
                                    f"{row['EVIDDESC']}"
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
                                        ).props("flat"
                                    ).classes("text-[var(--vsp-blue)]")

                                    def on_confirm_delete() -> None:

                                        with get_session() as session:

                                            evid = (
                                                session.query(Evidence)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )

                                            if evid:
                                                EVIDNUM = evid.EVIDNUM
                                                EVIDDESC = evid.EVIDDESC
                                                session.delete(evid)
                                            else:
                                                EVIDNUM = row["EVIDNUM"]
                                                EVIDDESC = row["EVIDDESC"]

                                        ui.notify(
                                            f"Item {EVIDNUM} ({EVIDDESC}) "
                                            "has bene removed.",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        delete_dialog.close()
                                        refresh_evidence_table()

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

                # ----- DELETE ALL BUTTON -----
                def delete_all_evidence() -> None:

                    with get_session() as session:
                        session.query(Evidence).delete()
                        session.commit()

                    ui.notify(
                        "All evidence has been deleted.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )

                    refresh_evidence_table()

                ui.button(
                    "Delete All Evidence Items",
                    on_click=lambda: confirm_delete_all(
                        "evidence",
                        delete_all_evidence,
                    ),
                    color="#ef4444",
                ).props("unelevated").classes("mb-2 items-center")

    # ----- Initial render -----
    refresh_evidence_table()
