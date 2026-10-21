#!/usr/bin/env python3

"""
evidence_page.py

The evidence log: what was seized, from where, by whom, witnessed by
whom.

Item numbers are assigned automatically and compared numerically, so a
case does not stop counting correctly at item ten.
"""

from auth import get_current_user_name, get_is_admin
from models import Evidence, get_session
from navbar import build_navbar
from parts.crud import CrudSpec, Field, build_crud_page
from utils import evidence_number_key
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


# ----- Item numbers that never skip -----
def _plain_number(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _later_items(session, removed: int) -> list:
    """(number, item) for every plainly numbered item above `removed`,
    lowest first."""
    later = []
    for item in session.query(Evidence).all():
        number = _plain_number(item.EVIDNUM)
        if number is not None and number > removed:
            later.append((number, item))
    return sorted(later, key=lambda pair: pair[0])


def _renumber_sentence(numbers: list, done: bool) -> str:
    if not numbers:
        return ""
    first, last = numbers[0], numbers[-1]
    if len(numbers) == 1:
        if done:
            return f"Item {first} is now item {first - 1}."
        return f"Item {first} will become item {first - 1}, so the numbers do not skip."
    if done:
        return (
            f"The {len(numbers)} later items each moved down one number: "
            f"{first} is now {first - 1}, and {last} is now {last - 1}."
        )
    return (
        f"The {len(numbers)} later items will each move down one number -- "
        f"{first} becomes {first - 1} and {last} becomes {last - 1} -- so "
        "the numbers do not skip."
    )


def _close_the_gap(session, removed: dict) -> str:
    """Moves every later item down one number, so the list never skips.

    Removing item 4 of 7 -- an item that was not seized after all -- left
    1, 2, 3, 5, 6, 7. Items 5 to 7 now become 4 to 6, in the same
    transaction as the deletion, and each change reaches the audit trail.
    A hand-entered number such as 12A is left as it is.
    """
    gone = _plain_number(removed.get("EVIDNUM"))
    if gone is None:
        return ""
    later = _later_items(session, gone)
    # Lowest first, one at a time: item numbers are unique, so 6 can only
    # become 5 once 5 has become 4.
    for number, item in later:
        item.EVIDNUM = str(number - 1)
        session.flush()
    return _renumber_sentence([number for number, _item in later], done=True)


def _renumber_warning(row: dict) -> str:
    """What deleting this item will do to the numbers after it."""
    gone = _plain_number(row.get("EVIDNUM"))
    if gone is None:
        return ""
    with get_session() as session:
        numbers = [number for number, _item in _later_items(session, gone)]
    return _renumber_sentence(numbers, done=False)


def _take_next_number(values: dict) -> None:
    """Settles the item number when the item is saved, not when the form
    opened: another device may have added or removed an item meanwhile."""
    values["EVIDNUM"] = get_next_evid_num()


SPEC = CrudSpec(
    model=Evidence,
    title="Evidence Management",
    entity="item",
    entity_plural="evidence items",
    label_field="EVIDNUM",
    table_title="Evidence List",
    submit_label="Add Evidence",
    order_by="Z_PK",
    # By item number as a person reads it: item 10 after item 9.
    sort_key=lambda row: evidence_number_key(row["EVIDNUM"]),
    on_before_create=_take_next_number,
    on_delete=_close_the_gap,
    delete_note=_renumber_warning,
    live_defaults=("EVIDNUM",),
    validate=_validate,
    on_form_ready=_wire_triage_toggle,
    form_columns=2,
    card_width="max-w-6xl",
    # A room is searched by the same two agents, item after item, and
    # choosing all three again for every one was most of the typing.
    form_hint=(
        "Room Located, Found By and Witnessed By stay filled in for the "
        "next item. Clear empties them."
    ),
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
            keep_after_add=True,
        ),
        Field("EVIDLOCROOMDETAIL", "Where Located", table_label="Where",
              required=True),
        Field(
            "EVIDFOUNDBY",
            "Found By",
            kind="select",
            required=True,
            options=load_agent_names,
            keep_after_add=True,
        ),
        Field(
            "EVIDFOUNDBYWITNESS",
            "Witnessed By",
            kind="select",
            required=True,
            options=load_agent_names,
            keep_after_add=True,
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
            "Entered",
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
