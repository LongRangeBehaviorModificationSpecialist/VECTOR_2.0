#!/usr/bin/env python3

"""
notes_page.py

Timestamped narrative entries.

Authorship comes from the signed-in user and cannot be edited
afterwards. Choosing an author from a dropdown meant anyone could write,
or later rewrite, a note under a colleague's name; the audit trail
records who made any subsequent edit.
"""

from auth import get_current_user_name, get_is_admin
from models import Notes
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import get_current_timestamp, validate_note_data


def _stamp_edit(values: dict) -> None:
    """Records when a note was last changed."""
    values["NOTEDATETIMEUPDATED"] = get_current_timestamp()


def _validate(stage: str, values: dict, row: dict | None) -> bool:
    return validate_note_data(
        NOTEAUTHOR=values.get("NOTEAUTHOR", ""),
        NOTETEXT=values.get("NOTETEXT", ""),
    )


SPEC = CrudSpec(
    model=Notes,
    title="Notes",
    entity="note",
    label_field="NOTEAUTHOR",
    table_title="Notes List",
    id_label="ID #",
    submit_label="Add Note",
    # The order the notes were written in. NOTEDATETIME is text, and an
    # upgraded database holds two date formats, so sorting on it put a new
    # note above the older ones.
    order_by="Z_PK",
    validate=_validate,
    on_before_update=_stamp_edit,
    fields=[
        Field(
            "NOTEDATETIME",
            "Date/Time Added",
            table_label="Added",
            readonly=True,
            in_edit=False,
            default=get_current_timestamp,
        ),
        Field(
            "NOTEAUTHOR",
            "Author",
            readonly=True,
            # Fixed at creation. The edit dialog shows it read-only so
            # the original author travels with the note.
            default=lambda: get_current_user_name() or "unknown",
        ),
        Field("NOTETEXT", "Note", required=True, props="autofocus"),
        Field(
            "NOTEDATETIMEUPDATED",
            "Last Edited",
            table_label="Edited",
            readonly=True,
            in_form=False,
        ),
    ],
)


def build_notes_page() -> None:
    """Builds the full Notes page UI."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )
    build_crud_page(SPEC)
