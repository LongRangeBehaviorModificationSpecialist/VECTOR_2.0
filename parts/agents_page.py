#!/usr/bin/env python3

"""
agents_page.py

Everyone working the scene.

Agents are also kept in parts/agents.json, so the same team
auto-populates at the next warrant rather than being retyped.
"""

from auth import get_current_user_name, get_is_admin
from failures import log
from models import Agents
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import (
    get_agent_dict,
    get_current_timestamp,
    is_duplicate_agent_in_json,
    load_agency_options,
    load_agent_names_for_page,
    load_agents_from_json,
    load_role_options,
    save_agent_to_json,
    validate_agent_entry,
)


def _validate(stage: str, values: dict, row: dict | None) -> bool:
    return validate_agent_entry(
        stage=stage,
        AGENTNAME=values.get("AGENTNAME", ""),
        AGENTPARENTAGENCY=values.get("AGENTPARENTAGENCY", ""),
        AGENTPRIMARYROLE=values.get("AGENTPRIMARYROLE", ""),
        AGENTROLESECONDARY=values.get("AGENTROLESECONDARY", ""),
        row=row,
    )


def _remember_agent(values: dict) -> None:
    """Adds a newly entered agent to the reusable roster.

    The agent is already saved to the case when this runs. A roster that
    cannot be written -- the program folder is read-only, say -- is noted
    in the console and nothing more: raising here skipped the "added"
    message and left the form filled in, as if the save had failed.
    """
    try:
        _add_to_roster(values)
    except OSError:
        log.warning("Could not add %s to the agent roster",
                    values.get("AGENTNAME", ""), exc_info=True)


def _add_to_roster(values: dict) -> None:
    if is_duplicate_agent_in_json(
        AGENTNAME=values.get("AGENTNAME", ""),
        AGENTPHONE=values.get("AGENTPHONE", ""),
        AGENTEMAIL=values.get("AGENTEMAIL", ""),
    ):
        return

    roster = load_agents_from_json()
    roster.append(
        {
            "AGENTNAME": values.get("AGENTNAME", ""),
            "AGENTPARENTAGENCY": values.get("AGENTPARENTAGENCY", ""),
            "AGENTPHONE": values.get("AGENTPHONE", ""),
            "AGENTEMAIL": values.get("AGENTEMAIL", ""),
        }
    )
    save_agent_to_json(agents=roster)


def _autofill_from_roster(widgets: dict) -> None:
    """Fills agency, phone and email when a known name is picked."""

    def on_name_change(event) -> None:
        selected = event.value
        if not selected:
            return

        known = {a["AGENTNAME"]: a for a in get_agent_dict()}
        details = known.get(selected)

        if details:
            widgets["AGENTPARENTAGENCY"].value = (
                details.get("AGENTPARENTAGENCY") or ""
            )
            widgets["AGENTPHONE"].value = details.get("AGENTPHONE") or ""
            widgets["AGENTEMAIL"].value = details.get("AGENTEMAIL") or ""
        else:
            # A name typed in fresh: clear rather than leave the previous
            # agent's contact details attached to it.
            widgets["AGENTPARENTAGENCY"].value = None
            widgets["AGENTPHONE"].value = ""
            widgets["AGENTEMAIL"].value = ""

    widgets["AGENTNAME"].on_value_change(on_name_change)


SPEC = CrudSpec(
    model=Agents,
    title="Agents",
    entity="agent",
    label_field="AGENTNAME",
    table_title="Agents List",
    id_label="Agent #",
    submit_label="Add Agent",
    order_by="AGENTNAME",
    validate=_validate,
    on_created=_remember_agent,
    on_form_ready=_autofill_from_roster,
    fields=[
        Field(
            "AGENTNAME",
            "Agent Name",
            kind="select",
            required=True,
            options=load_agent_names_for_page,
            new_values=True,
            props="autofocus",
        ),
        Field(
            "AGENTPARENTAGENCY",
            "Agency",
            table_label="Agency",
            kind="select",
            required=True,
            options=load_agency_options,
            new_values=True,
        ),
        Field(
            "AGENTPRIMARYROLE",
            "Primary Role",
            kind="select",
            required=True,
            options=load_role_options,
        ),
        Field(
            "AGENTROLESECONDARY",
            "Secondary Role",
            kind="select",
            options=load_role_options,
        ),
        Field("AGENTPHONE", "Phone Number"),
        Field("AGENTEMAIL", "Email"),
        Field("AGENTNOTE", "Notes"),
        Field(
            "ENTEREDDATETIME",
            "Entered",
            in_form=False,
            in_edit=False,
            default=lambda: get_current_timestamp(format="entry"),
        ),
    ],
)


def build_agents_page() -> None:
    """Builds the full Agents page UI."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )
    build_crud_page(SPEC)
