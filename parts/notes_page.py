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
from home_page import confirm_new_case_handler
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
    table_title="Case Notes",
    submit_label="Add Note",
    order_by="NOTEDATETIME",
    validate=_validate,
    on_before_update=_stamp_edit,
    fields=[
        Field(
            "NOTEDATETIME",
            "Date/Time Added (UTC)",
            table_label="Added (UTC)",
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
            "Last Edited (UTC)",
            table_label="Edited (UTC)",
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
        on_new_case=confirm_new_case_handler,
    )
    build_crud_page(SPEC)
