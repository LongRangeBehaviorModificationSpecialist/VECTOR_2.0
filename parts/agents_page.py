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
from models import get_session, Agents

from home_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler
)
from navbar import build_navbar
from utils import (
    load_agents_from_json,
    is_duplicate_agent_in_json,
    save_agent_to_json,
    get_agent_dict,
    load_agent_names_for_page,
    load_role_options,
    load_agency_options,
    required_input,
    required_select,
    confirm_delete_all,
    validate_agent_data
)


# ----- Main Page Builder -----
def build_agents_page():
    """Builds the Agents page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler)

    with ui.column().classes("w-full items-center"):

        ui.label("Agents").classes("text-2xl font-bold m-4")

        # ----- Add Agent Section -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            agent_name_input = required_select(
                options=load_agent_names_for_page(),
                label="Agent Name", with_input=True,
                new_value_mode="add").classes("w-full")
            agent_name_input.props("autofocus")

            agent_parent_agency_input = required_select(
                options=load_agency_options(),
                label="Parent Agency",
                with_input=True, new_value_mode="add").classes("w-full")

            agent_role_input = required_select(
                options=load_role_options(),
                label="Agent Role", with_input=True).classes("w-full")

            agent_role_secondary_input = ui.select(
                options=load_role_options(),
                label="Agent Secondary Role (if applicable)",
                with_input=True).classes("w-full")

            agent_phone_input = ui.input(
                label="Agent Phone Number").classes("w-full")

            agent_email_input = ui.input(
                label="Agent Email").classes("w-full")

            agent_note_input = ui.input(label="Notes").classes("w-full")

            # ----- Auto-populate on name selection -----
            def on_name_change(e):

                selected = e.value

                if not selected:

                    return

                agents_list = get_agent_dict()
                agent_lookup = {a["name"]: a for a in agents_list}

                if selected in agent_lookup:

                    info = agent_lookup[selected]
                    agent_parent_agency_input.value = info.get(
                        "agency", "" ) or ""
                    agent_phone_input.value = info.get(
                        "phone", "") or ""
                    agent_email_input.value = info.get(
                        "email", "") or ""

                else:
                    agent_parent_agency_input.value = None
                    agent_phone_input.value = ""
                    agent_email_input.value = ""

            agent_name_input.on_value_change(on_name_change)

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_agent_form():

                    agent_name_input.value = None
                    agent_parent_agency_input.value = None
                    agent_role_input.value = None
                    agent_role_secondary_input.value = None
                    agent_phone_input.value = ""
                    agent_email_input.value = ""
                    agent_note_input.value = ""

                def on_submit():
                    """Handles form submission for new agents."""

                    name = agent_name_input.value
                    agency = agent_parent_agency_input.value or ""
                    role = agent_role_input.value
                    role_secondary = agent_role_secondary_input.value or ""
                    phone = agent_phone_input.value or ""
                    email = agent_email_input.value or ""
                    notes = agent_note_input.value or ""

                    # ----- Required field validation -----
                    if not validate_agent_data(
                        name=name,
                        agency=agency,
                        role=role
                    ):

                        return

                    try:

                        with get_session() as session:

                            # ----- Uniqueness checks for data -----
                            if (
                                session.query(Agents)
                                .filter_by(agent_name=name)
                                .first()
                            ):

                                ui.notify(
                                    "That Agent's Name is already in the case "
                                    "database. Please check the name and try "
                                    "again.",
                                    type="warning",
                                    timeout=0,
                                    close_button="OK",
                                    position="center"
                                )

                                return

                            new_agent = Agents(
                                agent_name=name,
                                agent_parent_agency=agency,
                                agent_role=role,
                                agent_role_secondary=role_secondary,
                                agent_phone=phone,
                                agent_email=email,
                                agent_note=notes
                            )

                            session.add(new_agent)

                        if not is_duplicate_agent_in_json(
                            name=name,
                            phone=phone,
                            email=email
                        ):

                            # RIGHT — Load → Append → Save
                            # Save to JSON file
                            agents = load_agents_from_json()

                            agents.append(
                                {
                                    "name": name,
                                    "agency": agency,
                                    "phone": phone,
                                    "email": email
                                }
                            )

                            save_agent_to_json(agents=agents)

                            ui.notify(
                                "New agent saved to the JSON file.",
                                type="positive",
                                timeout=2000,
                                close_button="OK",
                                position="bottom"
                            )

                        else:

                            ui.notify(
                                f"{name} added to the case dataabse.",
                                type="positive",
                                timeout=2000,
                                close_button="OK",
                                position="bottom"
                            )

                        refresh_agent_table()
                        clear_agent_form()

                    except Exception:

                        ui.notify(
                            "Please check the Agent Information you "
                            "just tried to enter/update — You may "
                            "have entered a duplicate value. The "
                            "changes were not successful.",
                            type="negative",
                            timeout=0,
                            close_button="OK",
                            position="center"
                        )

                ui.button("Clear", on_click=clear_agent_form
                    ).props("flat")

                ui.button("Add Agent", on_click=on_submit
                    ).props("unelevated")

        # ----- Agent List Table -----
        ui.separator().classes("mt-6 mb-3")

        with ui.column().classes("w-full items-center"):

            ui.label("Current Agents").classes("text-xl font-bold mb-3")

            with ui.row().classes("w-full max-w-6xl items-center"):

                table_container = ui.column().classes(
                    "w-full max-w-5xl mx-auto items-center gap-2")

                def refresh_agent_table():
                    """Re-renders the agents table from the database."""

                    table_container.clear()

                    with get_session() as session:

                        agents = (
                            session.query(Agents)
                            .order_by(Agents.agent_name)
                            .all())

                        if not agents:

                            with table_container:

                                ui.label("No agents in the database yet"
                                ).classes("text-gray-500 italic")

                            return

                        row_data = [{
                            "id": r.id,
                            "agent_name": r.agent_name or "",
                            "agent_parent_agency": (
                                r.agent_parent_agency or ""),
                            "agent_role": r.agent_role or "",
                            "agent_role_secondary": (
                                r.agent_role_secondary or ""),
                            "agent_phone": r.agent_phone or "",
                            "agent_email": r.agent_email or "",
                            "agent_note": r.agent_note or ""}
                            for r in agents]

                    with table_container:

                        column_defs = [
                            {
                                "name": "agent_name",
                                "label": "Name",
                                "field": "agent_name",
                                "sortable": True,
                                "align": "left"
                            },
                            {
                                "name": "agent_parent_agency",
                                "label": "Agency",
                                "field": "agent_parent_agency",
                                "sortable": True,
                                "align": "left"
                            },
                            {
                                "name": "agent_role",
                                "label": "Role",
                                "field": "agent_role",
                                "sortable": True,
                                "align": "left"
                            },
                            {
                                "name": "agent_role_secondary",
                                "label": "Sec. Role",
                                "field": "agent_role_secondary",
                                "sortable": True,
                                "align": "left"
                            },
                            {
                                "name": "agent_phone",
                                "label": "Phone",
                                "field": "agent_phone",
                                "sortable": True,
                                "align": "left"
                            },
                            {
                                "name": "agent_email",
                                "label": "Email",
                                "field": "agent_email",
                                "sortable": True,
                                "align": "left"
                            },
                            {
                                "name": "actions",
                                "label": "Actions",
                                "field": "actions",
                                "sortable": False,
                                "align": "center"
                            },
                        ]

                        table = ui.table(
                            columns=column_defs,
                            rows=row_data,
                            row_key="id")

                        table.props("dense flat")

                        # ----- Slot: Actions column (Update / Delete) -----
                        table.add_slot(
                            "body-cell-actions",
                            """
                            <q-td :props="props">
                                <div class="row no-wrap gap-1">
                                    <q-btn dense flat color="primary"
                                        icon="edit" size="sm"
                                        @click="$parent.$emit('edit', \
                                        props.row)" />
                                    <q-btn dense flat color="negative"
                                        icon="delete" size="sm"
                                        @click="$parent.$emit('delete', \
                                        props.row)" />
                                </div>
                            </q-td>
                        """)

                        # ----- Edit dialog -----
                        def open_edit_dialog(e):

                            row = e.args

                            with ui.dialog() as edit_dialog, ui.card(
                                ).classes("w-full max-w-lg p-6"):

                                ui.label(
                                    f"Edit Agent: {row['agent_name']}"
                                ).classes("text-lg font-semibold mb-4")

                                agent_name = required_input(
                                    label="Agent's Name",
                                    value=row["agent_name"]
                                ).classes("w-full")

                                agent_parent_agency = required_select(
                                    options=load_agency_options(),
                                    label="Parent Agency",
                                    value=row["agent_parent_agency"],
                                    with_input=True,
                                    new_value_mode="add"
                                ).classes("w-full")

                                agent_role = required_select(
                                    options=load_role_options(),
                                    label="Agent's Role",
                                    value=row["agent_role"],
                                    with_input=True
                                ).classes("w-full")

                                agent_role_secondary = ui.select(
                                    options=load_role_options(),
                                    label="Agent's Secondary Role",
                                    value=row["agent_role_secondary"] or None,
                                    with_input=True
                                ).classes("w-full")

                                agent_phone = required_input(
                                    label="Agent's Phone Number",
                                    value=row["agent_phone"]
                                ).classes("w-full")

                                agent_email = ui.input(
                                    label="Agent's Email",
                                    value=row["agent_email"]
                                ).classes("w-full")

                                agent_note = ui.input(
                                    label="Notes",
                                    value=row["agent_note"]
                                ).classes("w-full")

                                with ui.row().classes(
                                    "w-full justify-end gap-2 mt-4"):

                                    ui.button(
                                        "Cancel", on_click=edit_dialog.close
                                    ).props("flat")

                                    def on_save_update():
                                        """Handles form submission for
                                        updating existing agents.
                                        """

                                        with get_session() as session:

                                            agent = (session.query(Agents)
                                                .filter_by(id=row["id"])
                                                .first())

                                            if not agent:

                                                ui.notify(
                                                    "Agent not found",
                                                    type="warning", timeout=0,
                                                    position="center",
                                                    close_button="OK")

                                                return

                                            agent.agent_name = agent_name
                                            agent.agent_parent_agency = (
                                                agent_parent_agency)
                                            agent.agent_role = agent_role
                                            agent.agent_role_secondary = (
                                                agent_role_secondary)
                                            agent.agent_phone = agent_phone
                                            agent.agent_email = agent_email
                                            agent.agent_note = agent_note

                                            # ----- Required field
                                            # validation -----
                                            if not validate_agent_data(
                                                name=agent_name,
                                                agency=agent_parent_agency,
                                                role=agent_role):
                                                return

                                        ui.notify(
                                            f"{agent_name.value} was updated "
                                            "successfully.", timeout=2000,
                                            close_button="OK",
                                            position="bottom")

                                        edit_dialog.close()
                                        refresh_agent_table()

                                    ui.button(
                                        "Save", on_click=on_save_update
                                    ).props("unelevated")

                            edit_dialog.open()

                        # ----- Delete confirmation dialog -----
                        def open_delete_dialog(e):

                            row = e.args

                            with ui.dialog() as delete_dialog, ui.card(
                                ).classes("max-w-sm p-6"):

                                ui.label("Confirm Deletion").classes(
                                    "text-lg font-semibold mb-2")

                                ui.label(
                                    f"Are you sure you want to remove "
                                    f"{row['agent_name']} from the case file?"
                                ).classes("mb-4")

                                with ui.row().classes(
                                    "w-full justify-end gap-2"):

                                    ui.button(
                                        "Cancel", on_click=delete_dialog.close,
                                    ).props("flat")

                                    def confirm_agent_delete():

                                        with get_session() as session:

                                            agent = (session.query(Agents)
                                                .filter_by(id=row["id"])
                                                .first())

                                            if agent:

                                                agent_name = agent.agent_name
                                                session.delete(agent)

                                            else:

                                                agent_name = row["agent_name"]

                                        ui.notify(
                                            f"{agent_name} has been removed "
                                            "from the case file.",
                                            timeout=2000, close_button="OK",
                                            position="bottom")

                                        delete_dialog.close()
                                        refresh_agent_table()

                                    ui.button(
                                        "Delete",
                                        on_click=confirm_agent_delete,
                                        color="#ef4444"
                                    ).props("negative unelevated")

                            delete_dialog.open()

                        table.on("edit", open_edit_dialog)
                        table.on("delete", open_delete_dialog)

            with ui.row().classes("w-full justify-center my-2"):

                # ----- CLEAR ALL BUTTON -----
                def delete_all_agents():

                    with get_session() as session:

                        session.query(Agents).delete()
                        session.commit()

                    ui.notify(
                        "All agents have been deleted.",
                        type="positive", timeout=2000,
                        close_button="OK", position="bottom")

                    refresh_agent_table()

                ui.button(
                    "Clear All Agents",
                    on_click=lambda: confirm_delete_all(
                        "agents", delete_all_agents
                    ), color="#ef4444"
                ).props("unelevated").classes("mb-2 items-center")

    # ----- Initial render -----
    refresh_agent_table()


# ----- Page Registration -----
@ui.page("/agents")
def agents_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return
    build_agents_page()


if __name__ in {"__main__", "__mp_main__"}:
    from models import init_db

    init_db()
    ui.run(title="V·E·C·T·O·R", port=8080)
