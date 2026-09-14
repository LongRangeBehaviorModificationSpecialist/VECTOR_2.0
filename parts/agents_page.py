#!/usr/bin/env python3

"""
agents_page.py

Consolidates five Flask routes into one interactive page:
    /agent_list       →  table display + delete buttons
    /agent_add_page   →  add form (auto-fill from agents.json)
    /agent_new_add    →  add form (brand new agent)
    /agent_update     →  inline edit dialog
    /agent_delete     →  delete with confirmation
"""

from nicegui import ui
from models import require_active_case, has_active_case, get_session, Agents

from main import get_current_user_name, get_is_admin
from navbar import build_navbar
from utils import (
    load_agents_from_json,
    is_duplicate_agent_in_json,
    save_agent_to_json,
    get_agent_dict,
    load_agent_names_for_page,
    load_role_options,
    load_agency_options,
    get_current_timestamp,
    required_input,
    required_select,
    confirm_delete_all,
    validate_agent_entry,
)


# ----- Main Page Builder -----
def build_agents_page() -> None:
    """Builds the Agents page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):

        ui.label("Agents").classes("text-2xl font-bold m-4")

        # ----- Add Agent Section -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            AGENTNAME_input = required_select(
                options=load_agent_names_for_page(),
                label="Agent Name",
                with_input=True,
                new_value_mode="add",
            ).classes("w-full")

            AGENTNAME_input.props("autofocus")

            AGENTPARENTAGENCY_input = required_select(
                options=load_agency_options(),
                label="Parent Agency",
                with_input=True,
                new_value_mode="add",
            ).classes("w-full")

            AGENTPRIMARYROLE_input = required_select(
                options=load_role_options(),
                label="Agent Role",
                with_input=True,
            ).classes("w-full")

            AGENTROLESECONDARY_input = ui.select(
                options=load_role_options(),
                label="Agent Secondary Role (if applicable)",
                with_input=True,
            ).classes("w-full")

            AGENTPHONE_input = ui.input(
                label="Agent Phone Number"
            ).classes("w-full")

            AGENTEMAIL_input = ui.input(
                label="Agent Email"
            ).classes("w-full")

            AGENTNOTE_input = ui.input(
                label="Notes"
            ).classes("w-full")

            # ----- Auto-populate on name selection -----
            def on_name_change(e) -> None:
                selected = e.value
                if not selected:
                    return

                agents_list = get_agent_dict()
                agent_lookup = {a["AGENTNAME"]: a for a in agents_list}

                if selected in agent_lookup:
                    info = agent_lookup[selected]
                    AGENTPARENTAGENCY_input.value = info.get(
                        "AGENTPARENTAGENCY", ""
                    ) or ""
                    AGENTPHONE_input.value = info.get("AGENTPHONE", "") or ""
                    AGENTEMAIL_input.value = info.get("AGENTEMAIL", "") or ""
                else:
                    AGENTPARENTAGENCY_input.value = None

            AGENTNAME_input.on_value_change(on_name_change)

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_agent_form() -> None:
                    AGENTNAME_input.value = None
                    AGENTPARENTAGENCY_input.value = None
                    AGENTPRIMARYROLE_input.value = None
                    AGENTROLESECONDARY_input.value = None
                    AGENTPHONE_input.value = ""
                    AGENTEMAIL_input.value = ""
                    AGENTNOTE_input.value = ""

                @require_active_case
                def on_submit() -> None:
                    """Handles form submission for new agents."""
                    AGENTNAME = AGENTNAME_input.value or ""
                    AGENTPARENTAGENCY = AGENTPARENTAGENCY_input.value or ""
                    AGENTPRIMARYROLE = AGENTPRIMARYROLE_input.value
                    AGENTROLESECONDARY = AGENTROLESECONDARY_input.value or ""
                    AGENTPHONE = AGENTPHONE_input.value or ""
                    AGENTEMAIL = AGENTEMAIL_input.value or ""
                    AGENTNOTE = AGENTNOTE_input.value or ""

                    if validate_agent_entry(
                        stage="initial",
                        AGENTNAME=AGENTNAME,
                        AGENTPARENTAGENCY=AGENTPARENTAGENCY,
                        AGENTPRIMARYROLE=AGENTPRIMARYROLE,
                        AGENTROLESECONDARY=AGENTROLESECONDARY,
                    ):
                        return

                    try:
                        with get_session() as session:
                            new_agent = Agents(
                                AGENTNAME=AGENTNAME,
                                AGENTPARENTAGENCY=AGENTPARENTAGENCY,
                                AGENTPRIMARYROLE=AGENTPRIMARYROLE,
                                AGENTROLESECONDARY=AGENTROLESECONDARY,
                                AGENTPHONE=AGENTPHONE,
                                AGENTEMAIL=AGENTEMAIL,
                                AGENTNOTE=AGENTNOTE,
                                ENTEREDDATETIME=(
                                    get_current_timestamp(format="entry")
                                ),
                            )
                            session.add(new_agent)

                        if not is_duplicate_agent_in_json(
                            AGENTNAME=AGENTNAME,
                            AGENTPHONE=AGENTPHONE,
                            AGENTEMAIL=AGENTEMAIL,
                        ):
                            agents = load_agents_from_json()
                            agents.append(
                                {
                                    "AGENTNAME": AGENTNAME,
                                    "AGENTPARENTAGENCY": AGENTPARENTAGENCY,
                                    "AGENTPHONE": AGENTPHONE,
                                    "AGENTEMAIL": AGENTEMAIL,
                                }
                            )
                            save_agent_to_json(agents=agents)
                            ui.notify(
                                "New agent saved to the JSON file.",
                                timeout=4000,
                                position="bottom",
                                close_button="OK",
                            )
                        else:
                            ui.notify(
                                f"{AGENTNAME} was added.",
                                timeout=4000,
                                position="bottom",
                                close_button="OK",
                            )

                        clear_agent_form()
                        refresh_agent_table()

                    except Exception:
                        ui.notify(
                            "Please check the data you just tried to "
                            "enter — an unknown error occured. "
                            "No changes were made.",
                            type="negative",
                            timeout=0,
                            position="center",
                            close_button="OK",
                        )
                        import traceback
                        traceback.print_exc()

                ui.button(
                    "Clear",
                    on_click=clear_agent_form,
                    color="transparent",).props("flat"
                ).classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Agent",
                    on_click=on_submit,
                    color="var(--vsp-blue)").props("push"
                ).classes("text-[var(--vsp-white)]")

        # ----- Agent List Table -----
        ui.separator().classes("mt-6 mb-3")

        with ui.column().classes("w-full items-center"):

            ui.label("Agents List").classes("text-xl font-bold mb-1")

            with ui.row().classes("w-full max-w-6xl items-center"):

                table_container = ui.column().classes(
                    "w-full max-w-5xl mx-auto items-center gap-2"
                )

                def refresh_agent_table() -> None:
                    """Re-renders the agents table from the database."""
                    table_container.clear()

                    with get_session() as session:
                        agents = (
                            session.query(Agents)
                            .order_by(Agents.AGENTNAME)
                            .all()
                        )

                        if not agents:
                            with table_container:
                                ui.label(
                                    "No agents have been entered"
                                ).classes("text-red italic")
                            return

                        row_data = [
                            {
                                "Z_PK": r.Z_PK,
                                "AGENTNAME": r.AGENTNAME or "",
                                "AGENTPARENTAGENCY": (
                                    r.AGENTPARENTAGENCY or ""
                                ),
                                "AGENTPRIMARYROLE": r.AGENTPRIMARYROLE or "",
                                "AGENTROLESECONDARY": (
                                    r.AGENTROLESECONDARY or ""
                                ),
                                "AGENTPHONE": r.AGENTPHONE or "",
                                "AGENTEMAIL": r.AGENTEMAIL or "",
                                "AGENTNOTE": r.AGENTNOTE or "",
                            }
                            for r in agents
                        ]

                    with table_container:
                        column_defs = [
                            {
                                "name": "Z_PK",
                                "label": "Agent #",
                                "field": "Z_PK",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "AGENTNAME",
                                "label": "Name",
                                "field": "AGENTNAME",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "AGENTPARENTAGENCY",
                                "label": "Agency",
                                "field": "AGENTPARENTAGENCY",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "AGENTPRIMARYROLE",
                                "label": "Role",
                                "field": "AGENTPRIMARYROLE",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "AGENTROLESECONDARY",
                                "label": "Sec. Role",
                                "field": "AGENTROLESECONDARY",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "AGENTPHONE",
                                "label": "Phone",
                                "field": "AGENTPHONE",
                                "sortable": True,
                                "align": "left",
                            },
                            {
                                "name": "AGENTEMAIL",
                                "label": "Email",
                                "field": "AGENTEMAIL",
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

                        # ----- Slot: Actions column (Update / Delete) -----
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
                            """,
                        )

                        # ----- Edit dialog -----
                        @require_active_case
                        def open_edit_dialog(e) -> None:
                            row = e.args
                            with ui.dialog() as edit_dialog, ui.card(
                                ).classes("w-full max-w-lg p-6"
                            ):

                                ui.label(
                                    f"Edit Agent ({row['AGENTNAME']})"
                                    ).classes(
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                AGENTNAME_input = required_input(
                                    label="Agent's Name",
                                    value=row["AGENTNAME"],
                                ).classes("w-full")

                                AGENTPARENTAGENCY_input = required_select(
                                    options=load_agency_options(),
                                    label="Parent Agency",
                                    value=row["AGENTPARENTAGENCY"],
                                    with_input=True,
                                    new_value_mode="add",
                                ).classes("w-full")

                                AGENTPRIMARYROLE_input = required_select(
                                    options=load_role_options(),
                                    label="Agent's Role",
                                    value=row["AGENTPRIMARYROLE"],
                                    with_input=True,
                                ).classes("w-full")

                                AGENTROLESECONDARY_input = ui.select(
                                    options=load_role_options(),
                                    label="Agent's Secondary Role",
                                    value=row["AGENTROLESECONDARY"] or None,
                                    with_input=True,
                                ).classes("w-full")

                                AGENTPHONE_input = required_input(
                                    label="Agent's Phone Number",
                                    value=row["AGENTPHONE"],
                                ).classes("w-full")

                                AGENTEMAIL_input = ui.input(
                                    label="Agent's Email",
                                    value=row["AGENTEMAIL"],
                                ).classes("w-full")

                                AGENTNOTE_input = ui.input(
                                    label="Notes",
                                    value=row["AGENTNOTE"],
                                ).classes("w-full")

                                with ui.row().classes(
                                    "w-full justify-end gap-2 mt-4"
                                ):

                                    ui.button(
                                        "Cancel",
                                        on_click=edit_dialog.close,
                                        color="transparent").props("flat"
                                    ).classes("text-[var(--vsp-blue)]")

                                    def on_save_update() -> None:
                                        """Handles form submission for
                                        updating existing agents.
                                        """
                                        AGENTNAME = AGENTNAME_input.value or ""
                                        AGENTPARENTAGENCY = (
                                            AGENTPARENTAGENCY_input.value or ""
                                        )
                                        AGENTPRIMARYROLE = (
                                            AGENTPRIMARYROLE_input.value or ""
                                        )
                                        AGENTROLESECONDARY = (
                                            AGENTROLESECONDARY_input.value or ""
                                        )
                                        AGENTPHONE = (
                                            AGENTPHONE_input.value or ""
                                        )
                                        AGENTEMAIL = (
                                            AGENTEMAIL_input.value or ""
                                        )
                                        AGENTNOTE = (
                                            AGENTNOTE_input.value or ""
                                        )

                                        if validate_agent_entry(
                                            stage="update",
                                            AGENTNAME=AGENTNAME,
                                            AGENTPARENTAGENCY=(
                                                AGENTPARENTAGENCY
                                            ),
                                            AGENTPRIMARYROLE=(
                                                AGENTPRIMARYROLE
                                            ),
                                            AGENTROLESECONDARY=(
                                                AGENTROLESECONDARY
                                            ),
                                            row=row,
                                        ):
                                            return

                                        with get_session() as session:

                                            agent = (
                                                session.query(Agents)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )

                                            if agent:
                                                agent.AGENTNAME = AGENTNAME
                                                agent.AGENTPARENTAGENCY = (
                                                    AGENTPARENTAGENCY
                                                )
                                                agent.AGENTPRIMARYROLE = (
                                                    AGENTPRIMARYROLE
                                                )
                                                agent.AGENTROLESECONDARY = (
                                                    AGENTROLESECONDARY
                                                )
                                                agent.AGENTPHONE = AGENTPHONE
                                                agent.AGENTEMAIL = AGENTEMAIL
                                                agent.AGENTNOTE = AGENTNOTE

                                        ui.notify(
                                            f"'{AGENTNAME}' was updated ",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        edit_dialog.close()
                                        refresh_agent_table()

                                    ui.button(
                                        "Update",
                                        on_click=on_save_update,
                                        color="var(--vsp-blue)").props("push"
                                    ).classes("text-[var(--vsp-white)]")

                            edit_dialog.open()

                        # ----- Delete confirmation dialog -----
                        @require_active_case
                        def open_delete_dialog(e) -> None:
                            row = e.args
                            with ui.dialog() as delete_dialog, ui.card(
                                ).classes("max-w-sm p-6"
                            ):

                                ui.label(
                                    "Delete Agent?"
                                    ).classes(
                                    "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                                )

                                ui.label(
                                    f"The following Agent will be removed "
                                    "from the case file :"
                                    ).classes(
                                    "mb-3 text-base text-[var(--vsp-gray)]"
                                )

                                ui.label(
                                    f"\"{row['AGENTNAME']}\"").classes(
                                    "mb-3 text-base font-semibold text-[var(--vsp-blue)]"
                                )

                                with ui.row().classes(
                                    "w-full justify-end gap-2"
                                ):

                                    ui.button(
                                        "Cancel",
                                        on_click=delete_dialog.close,
                                        color="transparent").props("flat"
                                    ).classes("text-[var(--vsp-blue)]")

                                    def confirm_agent_delete() -> None:
                                        with get_session() as session:
                                            agent = (
                                                session.query(Agents)
                                                .filter_by(Z_PK=row["Z_PK"])
                                                .first()
                                            )

                                            if agent:
                                                AGENTNAME = agent.AGENTNAME
                                                session.delete(agent)
                                            else:
                                                AGENTNAME = row["AGENTNAME"]

                                        ui.notify(
                                            f"{AGENTNAME} has been removed.",
                                            timeout=4000,
                                            position="bottom",
                                            close_button="OK",
                                        )

                                        delete_dialog.close()
                                        refresh_agent_table()

                                    ui.button(
                                        "Delete",
                                        on_click=confirm_agent_delete,
                                        color="#EF4444").props("push"
                                    ).classes("text-[var(--vsp-white)]")

                            delete_dialog.open()

                        table.on("edit", open_edit_dialog)
                        table.on("delete", open_delete_dialog)

            with ui.row().classes("w-full justify-center my-2"):

                # ----- DELETE ALL BUTTON -----
                @require_active_case
                def delete_all_agents() -> None:
                    with get_session() as session:
                        session.query(Agents).delete()
                        session.commit()

                    ui.notify(
                        "All Agents have been deleted.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )

                    refresh_agent_table()

                case_exists = has_active_case()

                ui.button(
                    "Delete All Agents",
                    on_click=lambda: confirm_delete_all(
                        "agents",
                        delete_all_agents
                    ), color="#EF4444").props("push"
                ).classes("mb-2 items-center").set_enabled(case_exists)

    # ----- Initial render -----
    refresh_agent_table()
