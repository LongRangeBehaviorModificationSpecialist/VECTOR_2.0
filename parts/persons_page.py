#!/usr/bin/env python3

"""
persons_page.py

Suspects and others present at the scene.
"""

from auth import get_current_user_name, get_is_admin
from home_page import confirm_new_case_handler
from models import Persons
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import get_current_timestamp, validate_person_data


def _validate(stage: str, values: dict, row: dict | None) -> bool:
    return validate_person_data(
        stage=stage,
        PERSONNAME=values.get("PERSONNAME", ""),
        SUSPECTNOTE=values.get("SUSPECTNOTE", ""),
        row=row,
    )


SPEC = CrudSpec(
    model=Persons,
    title="Person List",
    entity="person",
    entity_plural="people",
    label_field="PERSONNAME",
    table_title="People Recorded",
    submit_label="Add Person",
    order_by="PERSONNAME",
    validate=_validate,
    fields=[
        Field("PERSONNAME", "Name", required=True, props="autofocus"),
        Field(
            "PERSONDOB",
            "DOB",
            placeholder="MM-DD-YYYY",
            props='mask="##-##-####"',
        ),
        Field("PERSONADDRESS", "Address"),
        Field(
            "PERSONPHONE",
            "Phone Number",
            placeholder="(###) ###-####",
            props='mask="(###) ###-####"',
        ),
        Field("SUSPECTNOTE", "Notes", required=True),
        Field(
            "ENTEREDDATETIME",
            "Entered (UTC)",
            in_form=False,
            in_edit=False,
            default=lambda: get_current_timestamp(format="entry"),
        ),
    ],
)


def build_persons_page() -> None:
    """Builds the full Persons page UI."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )
    build_crud_page(SPEC)
