#!/usr/bin/env python3

"""
rooms_page.py

The premises divided into lettered areas, with the two agents assigned
to search each one.
"""

from auth import get_current_user_name, get_is_admin
from models import Evidence, Rooms
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import (
    get_current_timestamp,
    get_next_room_ltr,
    load_agent_names,
    room_display,
    room_label_key,
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


def _carry_rename_to_evidence(session, before: dict, after: dict) -> None:
    """Keeps evidence with its room when the room is renamed.

    Evidence records its room as the text the dropdown showed -- "Room A
    (Living Room)" -- rather than as a link to the room. Renaming a room
    left its items under the old name, so the evidence-by-room report
    listed them under a room that was no longer on the room list. Each
    change is an ordinary edit, so it reaches the audit trail.
    """
    old = room_display(before.get("ROOMLABEL"), before.get("ROOMDESC"))
    new = room_display(
        after.get("ROOMLABEL", before.get("ROOMLABEL")),
        after.get("ROOMDESC", before.get("ROOMDESC")),
    )
    if old == new:
        return
    for item in session.query(Evidence).filter_by(EVIDLOCROOM=old):
        item.EVIDLOCROOM = new


SPEC = CrudSpec(
    model=Rooms,
    title="Rooms",
    entity="room",
    label_field="ROOMLABEL",
    table_title="Rooms List",
    submit_label="Add Room",
    order_by="ROOMLABEL",
    # As text, room AA would be listed between A and B.
    sort_key=lambda row: room_label_key(row["ROOMLABEL"]),
    on_update=_carry_rename_to_evidence,
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
    )
    build_crud_page(SPEC)
