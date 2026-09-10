#!/usr/bin/env python3

"""
rooms_page.py

The premises divided into lettered areas, with the two agents assigned
to search each one.
"""

from auth import get_current_user_name, get_is_admin
from home_page import confirm_new_case_handler
from models import Rooms
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import (
    get_current_timestamp,
    get_next_room_ltr,
    load_agent_names,
    validate_room_entry,
)


def _validate(stage: str, values: dict, row: dict | None) -> bool:
    return validate_room_entry(
        stage=stage,
        ROOMLABEL=values.get("ROOMLABEL", ""),
        ROOMDESC=values.get("ROOMDESC", ""),
        ROOMFIRSTAGENT=values.get("ROOMFIRSTAGENT", ""),
        ROOMSECONDAGENT=values.get("ROOMSECONDAGENT", ""),
        row=row,
    )


SPEC = CrudSpec(
    model=Rooms,
    title="Rooms",
    entity="room",
    label_field="ROOMLABEL",
    table_title="Rooms Defined",
    submit_label="Add Room",
    order_by="ROOMLABEL",
    validate=_validate,
    fields=[
        # Assigned automatically: the next unused letter, continuing
        # past Z as AA rather than running off the end of the alphabet.
        Field(
            "ROOMLABEL",
            "Room Label",
            readonly=True,
            default=get_next_room_ltr,
        ),
        Field(
            "ROOMDESC",
            "Room Description",
            required=True,
            props="autofocus",
        ),
        Field(
            "ROOMFIRSTAGENT",
            "First Agent Name",
            kind="select",
            options=load_agent_names,
        ),
        Field(
            "ROOMSECONDAGENT",
            "Second Agent Name",
            kind="select",
            options=load_agent_names,
        ),
        Field("ROOMNOTE", "Notes"),
        Field(
            "ENTEREDDATETIME",
            "Entered (UTC)",
            in_form=False,
            in_edit=False,
            default=lambda: get_current_timestamp(format="entry"),
        ),
    ],
)


def build_rooms_page() -> None:
    """Builds the full Rooms page UI."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )
    build_crud_page(SPEC)
