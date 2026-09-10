#!/usr/bin/env python3

"""
cases_page.py

The single active case: number, address, jurisdiction and the times the
search began and ended.
"""

from auth import get_current_user_name, get_is_admin
from home_page import confirm_new_case_handler
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
    submit_label="Open New Case",
    order_by="CASENUMBER",
    validate=_validate,
    # The case is deleted through "Make New Case File" on the navbar,
    # which clears the whole case rather than this table alone.
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
            placeholder="YYYY-MM-DD HH:MM",
            props='mask="####-##-## ##:##"',
        ),
        Field(
            "CASEDATETIMEEND",
            "Date/Time Ended",
            table_label="Ended",
            placeholder="YYYY-MM-DD HH:MM",
            props='mask="####-##-## ##:##"',
        ),
    ],
)


def build_cases_page() -> None:
    """Builds the full Cases page UI."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )
    build_crud_page(SPEC)
