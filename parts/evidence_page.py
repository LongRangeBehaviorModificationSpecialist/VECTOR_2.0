#!/usr/bin/env python3

"""
evidence_page.py

The evidence log: what was seized, from where, by whom, witnessed by
whom.

Item numbers are assigned automatically and compared numerically, so a
case does not stop counting correctly at item ten.
"""

from auth import get_current_user_name, get_is_admin
from models import Evidence
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import (
    get_current_timestamp,
    get_next_evid_num,
    load_agent_names,
    load_room_labels,
    validate_evid_entry,
)


YES_NO = ["", "Yes", "No"]
CONTRABAND = ["", "Yes", "No", "Unknown", "N/A"]


def _validate(stage: str, values: dict, row: dict | None) -> bool:
    return validate_evid_entry(
        stage=stage,
        EVIDNUM=values.get("EVIDNUM", ""),
        EVIDQTY=values.get("EVIDQTY", ""),
        EVIDDESC=values.get("EVIDDESC", ""),
        EVIDLOCROOM=values.get("EVIDLOCROOM", ""),
        EVIDLOCROOMDETAIL=values.get("EVIDLOCROOMDETAIL", ""),
        EVIDFOUNDBY=values.get("EVIDFOUNDBY", ""),
        EVIDFOUNDBYWITNESS=values.get("EVIDFOUNDBYWITNESS", ""),
        EVIDTRIAGED=values.get("EVIDTRIAGED", ""),
        EVIDTRIAGEDBY=values.get("EVIDTRIAGEDBY", ""),
        row=row,
    )


def _wire_triage_toggle(widgets: dict) -> None:
    """"Triaged By" only accepts a name once the item is marked triaged."""
    triaged = widgets.get("EVIDTRIAGED")
    triaged_by = widgets.get("EVIDTRIAGEDBY")
    if triaged is None or triaged_by is None:
        return

    triaged_by.disable()

    def on_triage_change(event) -> None:
        if event.value == "Yes":
            triaged_by.enable()
        else:
            triaged_by.disable()
            triaged_by.value = None

    triaged.on_value_change(on_triage_change)


SPEC = CrudSpec(
    model=Evidence,
    title="Evidence Management",
    entity="item",
    entity_plural="evidence items",
    label_field="EVIDNUM",
    table_title="Evidence List",
    submit_label="Add Evidence",
    order_by="Z_PK",
    validate=_validate,
    on_form_ready=_wire_triage_toggle,
    form_columns=2,
    card_width="max-w-6xl",
    fields=[
        Field(
            "EVIDNUM",
            "Evidence Item Number",
            table_label="Item No.",
            required=True,
            readonly=True,
            default=get_next_evid_num,
        ),
        Field("EVIDQTY", "Quantity", table_label="Qty", required=True),
        Field("EVIDDESC", "Evidence Description", table_label="Description",
              required=True),
        Field("EVIDMODELNUMBER", "Model Number", table_label="Model #"),
        Field("EVIDSERIALNUMBER", "Serial Number", table_label="Serial #"),
        Field(
            "EVIDLOCROOM",
            "Room Located",
            table_label="Room",
            kind="select",
            required=True,
            options=load_room_labels,
        ),
        Field("EVIDLOCROOMDETAIL", "Where Located", table_label="Where",
              required=True),
        Field(
            "EVIDFOUNDBY",
            "Found By",
            kind="select",
            required=True,
            options=load_agent_names,
        ),
        Field(
            "EVIDFOUNDBYWITNESS",
            "Witnessed By",
            kind="select",
            required=True,
            options=load_agent_names,
        ),
        Field("EVIDPICTAKEN", "Item Photographed", table_label="Photo",
              kind="select", options=lambda: YES_NO),
        Field("EVIDTRIAGED", "Item Triaged?", table_label="Triaged",
              kind="select", options=lambda: YES_NO),
        Field(
            "EVIDTRIAGEDBY",
            "Triaged By",
            kind="select",
            options=load_agent_names,
        ),
        Field("EVIDISCONTRABAND", "Contains Contraband?",
              table_label="Contraband", kind="select",
              options=lambda: CONTRABAND),
        Field("EVIDNOTE", "Notes"),
        Field(
            "ENTEREDDATETIME",
            "Entered (UTC)",
            in_form=False,
            in_edit=False,
            in_table=False,
            default=lambda: get_current_timestamp(format="entry"),
        ),
    ],
)


def build_evidence_page() -> None:
    """Builds the full Evidence page UI."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )
    build_crud_page(SPEC)
