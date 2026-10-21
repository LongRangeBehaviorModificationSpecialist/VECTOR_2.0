#!/usr/bin/env python3

"""
persons_page.py

Suspects and others present at the scene.
"""

from auth import get_current_user_name, get_is_admin
from models import Persons
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import format_phone, get_current_timestamp, validate_person_data


def _validate(stage: str, values: dict, row: dict | None) -> bool:
    return validate_person_data(
        stage=stage,
        PERSONNAME=values.get("PERSONNAME", ""),
        PERSONDOB=values.get("PERSONDOB", ""),
        PERSONNOTE=values.get("PERSONNOTE", ""),
        row=row,
    )


SPEC = CrudSpec(
    model=Persons,
    title="Person List",
    entity="person",
    entity_plural="people",
    label_field="PERSONNAME",
    table_title="Persons List",
    empty_text="No persons have been entered",
    id_label="ID #",
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
        # As on the Agents page: typed any way, a US number is saved as
        # (703) 555-1234, with any extension; anything else as typed. The
        # mask here forced exactly ten digits, so a foreign number or an
        # extension could not be entered for anyone at the scene.
        Field(
            "PERSONPHONE",
            "Phone Number",
            placeholder="(703) 555-1234 x12",
            tidy=format_phone,
        ),
        Field("PERSONNOTE", "Notes", required=True),
        Field(
            "ENTEREDDATETIME",
            "Entered",
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
    )
    build_crud_page(SPEC)
