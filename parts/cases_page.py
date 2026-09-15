#!/usr/bin/env python3

"""
cases_page.py

The single active case: number, address, jurisdiction and the times the
search began and ended.
"""

from auth import get_current_user_name, get_is_admin
from models import Cases
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import load_jurisdiction_options, validate_case_entry


def _validate(stage: str, values: dict, row: dict | None) -> bool:
    return validate_case_entry(
        stage=stage,
        CASENUMBER=values.get("CASENUMBER", ""),
        LOCATION=values.get("LOCATION", ""),
        JURISDICTION=values.get("JURISDICTION", ""),
        CASEDATETIMEBEGIN=values.get("CASEDATETIMEBEGIN", ""),
        row=row,
    )


SPEC = CrudSpec(
    model=Cases,
    title="Case Management",
    entity="case",
    label_field="CASENUMBER",
    table_title="Current Case",
    empty_text="No current active case",
    id_label="ID #",
    submit_label="Open New Case",
    order_by="CASENUMBER",
    validate=_validate,
    # Where a case is opened, so it has to work before one exists.
    requires_case=False,
    # A case is cleared through Start New Case on the home page, which
    # removes everything recorded against it rather than this table alone.
    show_delete_all=False,
    fields=[
        Field("CASENUMBER", "Case Number", required=True, props="autofocus"),
        Field("LOCATION", "Location", required=True),
        Field(
            "JURISDICTION",
            "Jurisdiction",
            kind="select",
            required=True,
            options=load_jurisdiction_options,
            new_values=True,
        ),
        Field(
            "CASEDATETIMEBEGIN",
            "Date/Time Started",
            table_label="Started",
            required=True,
            placeholder="MM-DD-YYYY HH:MM",
            props='mask="##-##-#### ##:##"',
        ),
        Field(
            "CASEDATETIMEEND",
            "Date/Time Ended",
            table_label="Ended",
            placeholder="MM-DD-YYYY HH:MM",
            props='mask="##-##-#### ##:##"',
        ),
    ],
)


def build_cases_page() -> None:
    """Builds the full Cases page UI."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )
    build_crud_page(SPEC)
