#!/usr/bin/env python3

"""
agents_page.py — NiceGUI conversion of Flask agents blueprint routes.

Consolidates five Flask routes into one interactive page:
    /agent_list      →  table display + delete buttons
    /agent_add_page   →  add form (auto-fill from agents.json)
    /agent_new_add    →  add form (brand new agent)
    /agent_update     →  inline edit dialog
    /agent_delete     →  delete with confirmation
"""

from nicegui import ui
from sqlalchemy import inspect as sa_inspect
import json
from pathlib import Path

from models import get_session, Agents
from program.inc.agent_role import AGENT_ROLE_LIST
from program.inc.agency_list import AGENCY_LIST

from main_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler,
)
from navbar import build_navbar, confirm_new_case_dialog


NOTIFICATION_TIMEOUT = 1500


# ── JSON File Path ───────────────────────────────────────
AGENTS_JSON_PATH = Path(__file__).parent / "agents.json"


def load_agents_from_json() -> list[dict]:
    """Load agent list from agents.json."""
    if not AGENTS_JSON_PATH.exists():
        return []
    try:
        with open(AGENTS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("agent_list", [])
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_agent_to_json(
        name: str,
        initials: str,
        agency: str,
        phone: str
) -> None:
    """Append a new agent to agents.json."""
    agents = load_agents_from_json()

    # Check if agent already exists in JSON (by name)
    if any(a["name"].lower() == name.lower() for a in agents):
        return  # Don't duplicate

    new_entry = {
        "name": name,
        "initials": initials,
        "agency": agency,
        "phone": phone
    }
    agents.append(new_entry)

    with open(AGENTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"agent_list": agents}, f, indent=4)


# ── Helper: Load agent dict from agents.json ──────────────
def get_agent_dict() -> list[dict]:
    """Loads agent data from agents.json file.

    Returns rows as dicts for auto-population.
    """
    return [
        {
            "name": a["name"],
            "initials": a.get("initials", "") or "",
            "agency": a.get("agency", "") or "",
            "phone": a.get("phone", "") or "",
        }
        for a in load_agents_from_json()
    ]


def load_agent_names() -> list[str]:
    """Returns sorted list of unique names from agents.json."""

    all_agents = get_agent_dict()
    seen = set()
    unique_names = []
    for a in all_agents:
        if a["name"] not in seen:
            seen.add(a["name"])
            unique_names.append(a["name"])
    return sorted(unique_names)


def load_role_options() -> list[str]:
    """Flattens AGENT_ROLE_LIST for NiceGUI select components."""

    if AGENT_ROLE_LIST:
        return [
            role[1] if isinstance(role, tuple) else role for role in AGENT_ROLE_LIST
        ]
    return []


def load_agency_options() -> list[str]:
    """Returns AGENCY_LIST for the agency select component."""

    if AGENCY_LIST:
        if isinstance(AGENCY_LIST[0], tuple):
            return [a[1] for a in AGENCY_LIST]
        return list(AGENCY_LIST)
    return []


# ── Main Page Builder ────────────────────────────────────────
def build_agents_page():

    # ── Header / Navbar ──────────────────────────────────────

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label("Agent Management").classes("text-2xl font-bold m-4")

        # ── Add Agent Section ───────────────────────────────────
        with ui.card().classes("w-full max-w-3xl mx-auto p-6"):
            ui.label("Add Agent").classes("text-lg font-semibold mb-4")

            full_agent_info = get_agent_dict()

            # Build a lookup dict for auto-population: {name: {initials, agency, phone}}
            agent_lookup = {a["name"]: a for a in full_agent_info}

            # Agent Name — dropdown populated from agents.json
            agent_name_input = ui.select(
                options=load_agent_names(),
                label="Agent's Name",
                with_input=True,
                new_value_mode="add",
            ).classes("w-full")

            agent_initials_input = ui.input(
                label="Agent's Initials",
            ).classes("w-full")

            agent_parent_agency_input = ui.select(
                options=load_agency_options(),
                label="Parent Agency",
                with_input=True,
                new_value_mode="add",
            ).classes("w-full")

            agent_role_input = ui.select(
                options=load_role_options(),
                label="Agent's Role",
                with_input=True,
            ).classes("w-full")

            agent_role_secondary_input = ui.select(
                options=load_role_options(),
                label="Agent's Secondary Role (if applicable)",
                with_input=True,
            ).classes("w-full")

            agent_phone_input = ui.input(label="Agent's Phone Number").classes("w-full")
            agent_notes_input = ui.textarea(label="Notes").classes("w-full")

            # ── Auto-populate on name selection ────────────────
            def on_name_change(e):
                selected = e.value
                if not selected:
                    return

                agents_list = get_agent_dict()
                agent_lookup = {a["name"]: a for a in agents_list}

                if selected in agent_lookup:
                    info = agent_lookup[selected]
                    agent_initials_input.value = info.get("initials", "") or ""
                    agent_parent_agency_input.value = info.get("agency", "") or ""
                    agent_phone_input.value = info.get("phone", "") or ""
                    ui.notify(
                        f"Auto-filled fields for {selected}",
                        type="info",
                        timeout=NOTIFICATION_TIMEOUT,
                    )
                else:
                    # New name typed — clear the fields for manual entry
                    agent_initials_input.value = ""
                    agent_parent_agency_input.value = None
                    agent_phone_input.value = ""

            agent_name_input.on_value_change(on_name_change)

            # ── Buttons ────────────────────────────────────────
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form():
                    agent_name_input.value = None
                    agent_initials_input.value = ""
                    agent_parent_agency_input.value = None
                    agent_role_input.value = None
                    agent_role_secondary_input.value = None
                    agent_phone_input.value = ""
                    agent_notes_input.value = ""
                    ui.notify(
                        "Form cleared",
                        type="info",
                        timeout=NOTIFICATION_TIMEOUT,
                    )

                def on_submit():
                    name = agent_name_input.value
                    if not name:
                        ui.notify(
                            "Agent's Name is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    role = agent_role_input.value
                    if not role:
                        ui.notify(
                            "Agent's Role is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    initials = agent_initials_input.value or ""
                    agency = agent_parent_agency_input.value or ""
                    role_secondary = agent_role_secondary_input.value or ""
                    phone = agent_phone_input.value or ""
                    notes = agent_notes_input.value or ""

                    try:
                        with get_session() as session:
                            # Uniqueness checks
                            if session.query(Agents).filter_by(agent_name=name).first():
                                ui.notify(
                                    "That Agent's Name is already in the case "
                                    "database. Please check the name and try "
                                    "again.",
                                    type="negative",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                return
                            if (
                                initials
                                and session.query(Agents)
                                .filter_by(agent_initials=initials)
                                .first()
                            ):
                                ui.notify(
                                    "Those initials are already used for another "
                                    "agent. Please change the initials and "
                                    "re-submit.",
                                    type="negative",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                return
                            if (
                                phone
                                and session.query(Agents)
                                .filter_by(agent_phone=phone)
                                .first()
                            ):
                                ui.notify(
                                    "That phone number is already assigned to an "
                                    "agent.",
                                    type="negative",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                return

                            new_agent = Agents(
                                agent_name=name,
                                agent_initials=initials,
                                agent_parent_agency=agency,
                                agent_role=role,
                                agent_role_secondary=role_secondary,
                                agent_phone=phone,
                                agent_notes=notes,
                            )
                            session.add(new_agent)

                        # ← ADD THIS: Save to JSON file as well
                        save_agent_to_json(name, initials, agency, phone)

                        ui.notify(
                            f"{name} was added to the case file successfully",
                            type="positive",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        clear_form()
                        refresh_agent_table()

                    except Exception as e:
                        ui.notify(
                            "Please check the Agent Information you just tried "
                            "to enter/update — You may have entered a duplicate "
                            "value. The changes were not successful.",
                            type="negative",
                            timeout=NOTIFICATION_TIMEOUT,
                        )

                ui.button("Clear", on_click=clear_form).props("outline")
                ui.button("Add Agent", on_click=on_submit).props("unelevated")

        # ── Agent List Table ────────────────────────────────────
        ui.separator().classes("my-6")
        ui.label("Current Agents").classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_agent_table():
            """Re-renders the agents table from the database."""
            table_container.clear()

            with get_session() as session:
                agents = session.query(Agents).order_by(Agents.agent_name).all()

                if not agents:
                    with table_container:
                        ui.label(
                            "No agents in the database yet."
                        ).classes("text-gray-500 italic")
                    return

                row_data = [
                    {
                        "id": r.id,
                        "agent_name": r.agent_name or "",
                        "agent_initials": r.agent_initials or "",
                        "agent_parent_agency": r.agent_parent_agency or "",
                        "agent_role": r.agent_role or "",
                        "agent_role_secondary": r.agent_role_secondary or "",
                        "agent_phone": r.agent_phone or "",
                        "agent_notes": r.agent_notes or "",
                    }
                    for r in agents
                ]

            with table_container:
                # Build columns for ui.table
                column_defs = [
                    {
                        "name": "agent_name",
                        "label": "Name",
                        "field": "agent_name",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "agent_initials",
                        "label": "Initials",
                        "field": "agent_initials",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "agent_parent_agency",
                        "label": "Agency",
                        "field": "agent_parent_agency",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "agent_role",
                        "label": "Role",
                        "field": "agent_role",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "agent_role_secondary",
                        "label": "Sec. Role",
                        "field": "agent_role_secondary",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "agent_phone",
                        "label": "Phone",
                        "field": "agent_phone",
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

                # ── Slot: Actions column (Update / Delete buttons) ──
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
                        ui.label(f"Edit Agent: {row['agent_name']}").classes(
                            "text-lg font-semibold mb-4"
                        )

                        edit_name = ui.input(
                            label="Agent's Name",
                            value=row["agent_name"],
                        ).classes("w-full")

                        edit_initials = ui.input(
                            label="Agent's Initials",
                            value=row["agent_initials"],
                        ).classes("w-full")

                        edit_agency = ui.select(
                            options=load_agency_options(),
                            label="Parent Agency",
                            value=row["agent_parent_agency"],
                            with_input=True,
                            new_value_mode="add",
                        ).classes("w-full")

                        edit_role = ui.select(
                            options=load_role_options(),
                            label="Agent's Role",
                            value=row["agent_role"],
                            with_input=True,
                        ).classes("w-full")

                        edit_role_secondary = ui.select(
                            options=load_role_options(),
                            label="Agent's Secondary Role",
                            value=row["agent_role_secondary"] or None,
                            with_input=True,
                        ).classes("w-full")

                        edit_phone = ui.input(
                            label="Agent's Phone Number",
                            value=row["agent_phone"],
                        ).classes("w-full")

                        edit_notes = ui.textarea(
                            label="Notes",
                            value=row["agent_notes"],
                        ).classes("w-full")

                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                            ).props("flat")

                            def on_save_update():
                                with get_session() as session:
                                    agent = (
                                        session.query(Agents)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if agent:
                                        agent.agent_name = edit_name.value or ""
                                        agent.agent_initials = (
                                            edit_initials.value or ""
                                        )
                                        agent.agent_parent_agency = (
                                            edit_agency.value or ""
                                        )
                                        agent.agent_role = edit_role.value or ""
                                        agent.agent_role_secondary = (
                                            edit_role_secondary.value or ""
                                        )
                                        agent.agent_phone = edit_phone.value or ""
                                        agent.agent_notes = edit_notes.value or ""
                                        # session.commit()

                                ui.notify(
                                    f"{edit_name.value} was updated successfully",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                edit_dialog.close()
                                refresh_agent_table()

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
                            f"{row['agent_name']} from the case file?"
                        ).classes("mb-4")

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                            ).props("flat")

                            def on_confirm_delete():
                                with get_session() as session:
                                    agent = (
                                        session.query(Agents)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    if agent:
                                        agent_name = agent.agent_name
                                        session.delete(agent)
                                    else:
                                        agent_name = row["agent_name"]

                                ui.notify(
                                    f"{agent_name} has been removed from the "
                                    "case file",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                delete_dialog.close()
                                refresh_agent_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

    # Initial render
    refresh_agent_table()


# ── Page Registration ────────────────────────────────────────
@ui.page("/agents")
def agents_page():
    build_agents_page()


if __name__ in {"__main__", "__mp_main__"}:
    from models import init_db

    init_db()
    ui.run(title="VECTOR", port=8080)
