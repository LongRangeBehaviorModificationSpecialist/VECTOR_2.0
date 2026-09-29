#!/usr/bin/env python3

"""
utils.py

File containing various functions used throughout the application.
"""
import clock
import settings
from datetime import datetime
from functools import wraps
from inspect import iscoroutinefunction
import json
from nicegui import ui
import mimetypes
import re
from models import (
    check_case_info,
    get_session,
    has_active_case,
    record_audit,
    Agents,
    Cases,
    Evidence,
    Rooms,
    Persons,
    Notes,
    UploadedFiles,
)
from pathlib import Path
from program.inc.agent_role import AGENT_ROLE_LIST
from program.inc.agency_list import AGENCY_LIST
from program.inc.jurisdictions import JURISDICTIONS
from sqlalchemy import exists, inspect
from typing import Optional


WARN_TIMEOUT = 4000
CONFIRM_TIMEOUT = 3500
ZERO_TIMEOUT = 0

AGENTS_JSON_PATH = Path(__file__).parent / "parts/agents.json"


# Allowed MIME types for images, videos, and documents
ALLOWED_MIME_TYPES = {
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/webp",
    "image/svg+xml",
    "image/tiff",
    # Videos
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-ms-wmv",
    "video/webm",
    "video/mpeg",
    "video/x-flv",
    "video/3gpp",
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/rtf",
    "application/rtf",
    # Archives / Containers
    "application/zip",
    "application/x-zip-compressed",
    "application/x-7z-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-gzip",
    "application/vnd.rar",
    "application/x-bzip2",
    "application/x-xz",
}

# Ensure uncommon archive types are recognized
mimetypes.add_type("application/x-7z-compressed", ".7z")
mimetypes.add_type("application/x-tar", ".tar")
mimetypes.add_type("application/gzip", ".gz")
mimetypes.add_type("application/gzip", ".tgz")
mimetypes.add_type("application/vnd.rar", ".rar")
mimetypes.add_type("application/x-bzip2", ".bz2")
mimetypes.add_type("application/x-xz", ".xz")


def get_current_timestamp(format: str = "") -> str:
    """The time now on this machine's clock, with its offset from UTC.

    Both forms used to be UTC, so a note written at 08:45 at the scene read
    12:45. `format` is still accepted from older callers; every stamp now
    has the one form, "09-15-2026 08:45:12 UTC-04:00".
    """
    return clock.stamp()


def get_print_date_time() -> str:
    """When a report is printed, in the date format the rest of it uses."""
    moment = clock.now()
    return f"{moment.strftime('%m-%d-%Y %H:%M')} {clock.zone_label(moment)}"


def required_input(label: str, **kwargs):
    """Creates a ui.input with a red asterisk in the label."""
    req_input = ui.input(**kwargs)
    req_input.props("label-slot")
    req_input.add_slot(
        "label",
        f'{label}<span style="color:#ef4444;"> *</span>'
    )
    return req_input


def required_select(label: str, options: list, **kwargs):
    """Creates a ui.select with a red asterisk in the label."""
    req_select = ui.select(options=options, **kwargs)
    req_select.props("label-slot")
    req_select.add_slot(
        "label",
        f'{label}<span style="color:#ef4444;"> *</span>'
    )
    return req_select


def required_textarea(label: str, **kwargs):
    """Creates a ui.textarea with a red asterisk in the label."""
    req_textarea = ui.textarea(**kwargs)
    req_textarea.props("label-slot")
    req_textarea.add_slot(
        "label",
        f'{label}<span style="color:#ef4444;"> *</span>'
    )
    return req_textarea


def get_case_info() -> dict | None:
    """Returns the single active case info (or None if no case exists)."""
    with get_session() as session:
        case = session.query(Cases).first()

        if not case:
            return None

        return {
            "CASENUMBER": case.CASENUMBER or "",
            "LOCATION": case.LOCATION or "",
            "JURISDICTION": case.JURISDICTION or "",
            "CASEDATETIMEBEGIN": (
                str(case.CASEDATETIMEBEGIN)
                if case.CASEDATETIMEBEGIN else ""
            ),
            "CASEDATETIMEEND": (
                str(case.CASEDATETIMEEND)
                if case.CASEDATETIMEEND else ""
            ),
        }


def load_jurisdiction_options() -> list[str]:
    """Reads values from the JURISDICTIONS list.

    Handles both plain-string and (value, label) tuple formats.

    Returns:
        jurisdiction choices from JURISDICTIONS.
    """
    if not JURISDICTIONS:
        return []
    if isinstance(JURISDICTIONS[0], tuple):
        return [j[1] for j in JURISDICTIONS]
    return list(JURISDICTIONS)


def load_agents_from_json() -> list[dict]:
    """Loads the agents list from agents.json."""
    if not AGENTS_JSON_PATH.exists():
        return []
    try:
        with open(AGENTS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_agent_to_json(agents: list) -> None:
    """Saves the agents list to agents.json with proper formatting."""
    with open(AGENTS_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(
            agents,
            file,
            indent=4,
            ensure_ascii=False)


def get_agent_dict() -> list[dict]:
    """Loads agent data from agents.json file.

    Returns:
        rows as dicts for auto-population.
    """
    data = load_agents_from_json()

    # If the JSON file is a dict instead of a list, wrap it in a list
    if isinstance(data, dict):
        data = [data]

    return [
        {
            "AGENTNAME": a.get("AGENTNAME", ""),
            "AGENTPARENTAGENCY": a.get("AGENTPARENTAGENCY", "") or "",
            "AGENTPHONE": a.get("AGENTPHONE", "") or "",
            "AGENTEMAIL": a.get("AGENTEMAIL", "") or "",
        }
        for a in data
        if isinstance(a, dict)
    ]


def load_agent_names_for_page() -> list[str]:
    """Returns sorted list of unique names from agents.json."""
    all_agents = get_agent_dict()
    seen = set()
    unique_names = []
    for a in all_agents:
        if a["AGENTNAME"] not in seen:
            seen.add(a["AGENTNAME"])
            unique_names.append(a["AGENTNAME"])
    return sorted(unique_names)


def load_role_options() -> list[str]:
    """Flattens AGENT_ROLE_LIST for NiceGUI select components."""
    if AGENT_ROLE_LIST:
        return (
            [
                role[1]
                if isinstance(role, tuple)
                else role for role in AGENT_ROLE_LIST
            ]
        )
    return []


def load_agency_options() -> list[str]:
    """Returns AGENCY_LIST for the agency select component."""
    if AGENCY_LIST:
        if isinstance(AGENCY_LIST[0], tuple):
            return [a[1] for a in AGENCY_LIST]
        return list(AGENCY_LIST)
    return []


def is_duplicate_agent_in_json(
        AGENTNAME: str,
        AGENTPHONE: str,
        AGENTEMAIL: str = ""
) -> bool:
    """Checks if an agent with the same name, phone, or email already
    exists in agents.json.

    Returns:
        True if duplicate found, False otherwise.
    """

    def digits_only(value: str) -> str:
        return "".join(ch for ch in (value or "") if ch.isdigit())

    agents = load_agents_from_json()

    name_lower = (AGENTNAME or "").strip().lower()
    phone_clean = digits_only(AGENTPHONE)
    email_lower = (AGENTEMAIL or "").strip().lower()

    # The loop variable used to be named AGENTNAME as well, shadowing the
    # argument. It happened to work because name_lower is computed first,
    # but any later use of the parameter inside the loop read a dict.
    for existing in agents:
        if (existing.get("AGENTNAME") or "").strip().lower() == name_lower:
            return True

        existing_phone = digits_only(existing.get("AGENTPHONE"))
        if existing_phone and phone_clean and existing_phone == phone_clean:
            return True

        existing_email = (existing.get("AGENTEMAIL") or "").strip().lower()
        if email_lower and existing_email and existing_email == email_lower:
            return True

    return False


def _case_is_open() -> bool:
    """True when a case is open; otherwise says so and returns False."""
    if has_active_case():
        return True

    ui.notify(
        "No active case!  Start a case before proceeding.",
        type="warning",
        timeout=WARN_TIMEOUT,
        position="center",
        close_button="OK",
    )

    return False


def require_active_case(func):
    """Stops an add, edit or delete when no case has been opened.

    Agents, rooms, evidence and the rest belong to a case, and every
    report is headed by one. An async handler -- the file upload -- stays
    async, so NiceGUI still awaits it.
    """
    if iscoroutinefunction(func):
        @wraps(func)
        async def async_guarded(*args, **kwargs):
            if not _case_is_open():
                return None
            return await func(*args, **kwargs)

        return async_guarded

    @wraps(func)
    def guarded(*args, **kwargs):
        if not _case_is_open():
            return None
        return func(*args, **kwargs)

    return guarded


@require_active_case
def confirm_delete_all(action: str, callback):
    """Shows a confirmation dialog before executing a destructive action."""
    with ui.dialog() as dialog, ui.card().classes("max-w-sm p-6"):

        ui.label("Warning!").classes("text-lg font-bold mb-2 text-[#1C69A8]")

        ui.label(
            f"This will permanently delete ALL {action} from the database. "
            "This action cannot be undone."
        ).classes("mb-4 text-base text-[#D4D4D8]")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(
                "Cancel",
                on_click=dialog.close
            ).props("flat").classes("p-3 hover-border-blue")

            def on_confirm():
                callback()
                dialog.close()

            ui.button(
                "Delete All",
                on_click=on_confirm,
                color="#ef4444",
            ).props("push").classes("p-3 hover-border-white")

    dialog.open()


# ----- Order -----
# Item numbers and room labels are stored as text, and sorted as text the
# return copy listed items 1, 10, 11, 12, 2 -- and room AA came between A
# and B.
def natural_key(value) -> tuple:
    """Sorts text the way a person reads the numbers in it.

    2 comes before 10, and a hand-entered 12A straight after 12.
    """
    parts = re.split(r"(\d+)", str(value or "").strip().lower())
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in parts
        if part
    )


evidence_number_key = natural_key


def room_label_key(label) -> tuple:
    """Orders room labels A to Z, then AA, AB -- as they are handed out."""
    text = str(label or "").strip().upper()
    if text.isalpha():
        return (0, len(text), text)
    return (1, natural_key(text))


def room_display(label, description) -> str:
    """A room as the evidence form shows it, and as evidence records it."""
    return f"Room {label} ({description})"


_ROOM_DISPLAY = re.compile(r"^Room (\S+) \(")


def room_display_key(display) -> tuple:
    """Orders "Room A (Hall)" style names by their room label."""
    match = _ROOM_DISPLAY.match(str(display or ""))
    if match:
        return room_label_key(match.group(1))
    return (2, natural_key(display))


def load_room_labels() -> list[str]:
    """Returns every room as the evidence form shows it, in label order."""
    with get_session() as session:
        rows = session.query(Rooms.ROOMLABEL, Rooms.ROOMDESC).all()
    rows.sort(key=lambda row: room_label_key(row[0]))
    return [room_display(row[0], row[1]) for row in rows]


def get_next_evid_num() -> str:
    """Gets the highest evidence number in use and increments it.

    EVIDNUM is a text column, so it must be compared numerically rather
    than by sort order: sorted as text, "9" comes after "10", which made
    this hand back a number already in use as soon as a case reached ten
    items. EVIDNUM is unique, so the save then failed with nothing to
    explain why.

    Values that are not plain integers -- a hand-entered "12A", say --
    are skipped rather than resetting the count.

    Returns:
        "1" if no numeric evidence numbers exist yet.
    """
    with get_session() as session:
        raw_numbers = [
            row[0] for row in session.query(Evidence.EVIDNUM).all()
        ]

    highest = 0
    for value in raw_numbers:
        try:
            highest = max(highest, int(str(value).strip()))
        except (TypeError, ValueError):
            continue

    return str(highest + 1)


def load_agent_names() -> list[str]:
    """Returns a list of all agent names from the Agents table."""
    with get_session() as session:
        rows = (
            session.query(Agents.AGENTNAME)
            .order_by(Agents.AGENTNAME)
            .all()
        )
        return [r[0] for r in rows]


def label_for_position(position: int) -> str:
    """Converts a 1-based position into a spreadsheet-style label.

    1 -> "A", 26 -> "Z", 27 -> "AA". Incrementing the last label's
    character code instead produced "[" after "Z", and raised TypeError
    on any label that had been edited to more than one character.
    """
    label = ""
    while position > 0:
        position, remainder = divmod(position - 1, 26)
        label = chr(ord("A") + remainder) + label
    return label


def get_next_room_ltr() -> str:
    """Suggests the next unused room label.

    Returns:
        "A" if no rooms exist yet.
    """
    with get_session() as session:
        used = {
            (row[0] or "").strip().upper()
            for row in session.query(Rooms.ROOMLABEL).all()
        }

    position = 1
    while label_for_position(position) in used:
        position += 1
    return label_for_position(position)


def get_mime_type(file_name: str, browser_type: str) -> str:
    """Determines MIME type using browser hint, then mimetypes fallback."""
    if browser_type and browser_type != "application/octet-stream":
        return browser_type
    guessed, _ = mimetypes.guess_type(file_name)
    return guessed or "application/octet-stream"


def is_allowed_file(mime_type: str) -> bool:
    """Checks if the MIME type is in the allowed set."""
    return mime_type in ALLOWED_MIME_TYPES


def format_file_size(size_bytes: int) -> str:
    """Formats file size into human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def delete_all_data() -> None:
    """Deletes every row of case data from app_data.db.

    This is the single wipe path -- both "Delete All Data" and "Make New
    Case File" go through it, so the table list cannot drift between
    them and leave attachments behind.

    Raises on failure rather than reporting it here, so the caller can
    decide what the user sees. The session context manager rolls back,
    so a failure leaves the case intact.

    The audit trail is deliberately NOT cleared -- it is append-only,
    and a wipe is exactly the event it exists to record.
    """
    tables = [
        (Cases, "CASES"),
        (Agents, "AGENTS"),
        (Rooms, "ROOMS"),
        (Evidence, "EVIDENCE"),
        (Persons, "PERSONS"),
        (Notes, "NOTES"),
        (UploadedFiles, "FILES"),
    ]

    with get_session() as session:
        # query().delete() is a bulk statement and does not raise ORM
        # events, so the flush listener never sees these. Count first,
        # then record the wipe explicitly.
        counts = {
            name: session.query(model).count() for model, name in tables
        }

        for model, _name in tables:
            session.query(model).delete()

        record_audit(
            session,
            action="DELETE_ALL",
            table_name="(all case tables)",
            summary=f"{sum(counts.values())} rows deleted",
            before=counts,
        )


def set_network_access(allowed: bool, actor: str = "") -> None:
    """Turns network access on or off, and records who did it.

    The address a server listens on is fixed when the socket opens, so
    this takes effect at the next start; the page offering it says so.
    """
    was = settings.network_access()
    settings.set_network_access(allowed)

    state = "on" if allowed else "off"
    with get_session() as session:
        record_audit(
            session,
            action="SETTING_CHANGED",
            table_name="(settings)",
            summary=(
                f"network access turned {state}; "
                "takes effect at the next start"
            ),
            before={"network_access": was},
            after={"network_access": bool(allowed)},
            actor=actor or None,
        )


def value_in_use(session, model, column_name, value, exclude_pk=None) -> bool:
    """Return True if `value` already exists in `model.column_name`.

    Args:
        model:       the mapped class, e.g. Agents
        column_name: name of the attribute to check, e.g. "agent_name"
        value:       the proposed value
        exclude_pk:  primary key of the row being updated (None on insert)

    Returns:
        [bool] True if the value exists in the database, else returns False
    """
    column = getattr(model, column_name)  # raises AttributeError if misspelled

    q = exists().where(column == value)

    if exclude_pk is not None:
        # Find the model's primary key column automatically
        pk_column = inspect(model).primary_key[0]
        q = q.where(pk_column != exclude_pk)

    return session.query(q).scalar()


# ----- Real dates -----
# The input masks only put digits in the right places, so a half-typed or
# impossible date -- 19-45-2026 25:99 -- was saved and printed as typed.
CASE_TIME_FORMAT = "%m-%d-%Y %H:%M"
DATE_FORMAT = "%m-%d-%Y"


def parse_entered_date(value, fmt: str) -> Optional[datetime]:
    """The date typed into a masked field, or None if it is not a real one."""
    try:
        parsed = datetime.strptime((value or "").strip(), fmt)
    except ValueError:
        return None
    # A year before 1900 is a slip of the finger, not a date anyone means.
    return parsed if parsed.year >= 1900 else None


def _refuse(message: str) -> bool:
    ui.notify(
        message,
        type="warning",
        timeout=WARN_TIMEOUT,
        position="center",
        close_button="OK",
    )
    return True


def validate_case_entry(
        stage: str,
        CASENUMBER: str,
        LOCATION: str,
        JURISDICTION: str,
        CASEDATETIMEBEGIN: str,
        row: Optional[dict] = None,
        CASEDATETIMEEND: str = "",
) -> bool:

    # One case per database. Every report reads the first case, so a
    # second would be recorded but never printed. Starting a different
    # case goes through Start New Case, which clears this one first.
    if stage == "initial":
        open_case = check_case_info()
        if open_case:
            ui.notify(
                f"Case {open_case['CASENUMBER']} is already open. To start "
                "a different case, use Start New Case on the home page — "
                "it clears the current case after a warning.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    number = (CASENUMBER or "").strip()
    location = (LOCATION or "").strip()
    jurisdiction = (JURISDICTION or "").strip()
    begin = (CASEDATETIMEBEGIN or "").strip()

    for field_label, value in [
        ("Case Number", number),
        ("Location", location),
        ("Jurisdiction", jurisdiction),
        ("Date/Time Started", begin),
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    started = parse_entered_date(begin, CASE_TIME_FORMAT)
    if started is None:
        return _refuse(
            "'Date/Time Started' is not a real date and time. Enter it as "
            "MM-DD-YYYY HH:MM, for example '09-15-2026 07:30'."
        )

    end = (CASEDATETIMEEND or "").strip()
    if end:
        ended = parse_entered_date(end, CASE_TIME_FORMAT)
        if ended is None:
            return _refuse(
                "'Date/Time Ended' is not a real date and time. Enter it as "
                "MM-DD-YYYY HH:MM, or leave it blank."
            )
        if ended < started:
            return _refuse(
                "'Date/Time Ended' is earlier than 'Date/Time Started'."
            )

    exclude_pk = (
        row["Z_PK"] if (stage == "update" and row is not None) else None
    )

    with get_session() as session:
        if value_in_use(session,
                        Cases,
                        "CASENUMBER",
                        number,
                        exclude_pk=exclude_pk,
        ):
            ui.notify(
                f"Case '{number}' already exists. Please use a unique case "
                "number.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    return False


def validate_agent_entry(
        stage: str,
        AGENTNAME: str = "",
        AGENTPARENTAGENCY: str ="",
        AGENTPRIMARYROLE: str ="",
        AGENTROLESECONDARY: str = "",
        row: Optional[dict] = None,
) -> bool:

    name = (AGENTNAME or "").strip()
    agency = (AGENTPARENTAGENCY or "").strip()
    primary = (AGENTPRIMARYROLE or "").strip()
    secondary = (AGENTROLESECONDARY or "").strip()

    for field_label, value in [
        ("Agent Name", name),
        ("Agency", agency),
        ("Agent Role", primary),
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    if primary and primary == secondary:
        ui.notify(
                f"The 'Primary Role' field and the 'Secondary Role' "
                f"field for {name} cannot be the same.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
        return True

    exclude_pk = (
        row["Z_PK"] if (stage == "update" and row is not None) else None
    )

    with get_session() as session:
        if value_in_use(session,
                        Agents,
                        "AGENTNAME",
                        name,
                        exclude_pk=exclude_pk
        ):
            ui.notify(
                f"'{name}' is already in the case database. Please "
                "check the name and try again.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    return False


def validate_evid_entry(
        stage: str,
        EVIDNUM: str,
        EVIDQTY: str,
        EVIDDESC: str,
        EVIDLOCROOM: str,
        EVIDLOCROOMDETAIL: str,
        EVIDFOUNDBY: str,
        EVIDFOUNDBYWITNESS: str,
        EVIDTRIAGED: str = "",
        EVIDTRIAGEDBY: str = "",
        row: Optional[dict] = None,
) -> bool:

    # Normalise first, then validate. Assigning inside "if" guards left
    # these unbound when a field was empty, so leaving the room dropdown
    # untouched raised UnboundLocalError instead of reporting a missing
    # required field. ui.select hands back None, not "", when untouched.
    item_num = (EVIDNUM or "").strip()
    qty = (EVIDQTY or "").strip()
    desc = (EVIDDESC or "").strip()
    room = (EVIDLOCROOM or "").strip()
    loc_detail = (EVIDLOCROOMDETAIL or "").strip()
    found_by = (EVIDFOUNDBY or "").strip()
    witness = (EVIDFOUNDBYWITNESS or "").strip()
    triaged = (EVIDTRIAGED or "").strip()
    triaged_by = (EVIDTRIAGEDBY or "").strip()

    for field_label, value in [
        ("Evidence Item Number", item_num),
        ("Quantity", qty),
        ("Evidence Description", desc),
        ("Room Located", room),
        ("Where Located", loc_detail),
        ("Found By", found_by),
        ("Witnessed By", witness)
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    if found_by == witness:
        ui.notify(
            "The same agent cannot be listed in the 'Found By' and the "
            "'Witnessed By' fields.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return True

    if triaged == "Yes" and not triaged_by:
        ui.notify(
            "The 'Triaged By' field is required if the 'Item Triaged?' "
            "field is set to 'Yes'.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return True

    exclude_pk = (
        row["Z_PK"] if (stage == "update" and row is not None) else None
    )

    with get_session() as session:
        if value_in_use(session,
                        Evidence,
                        "EVIDNUM",
                        item_num,
                        exclude_pk=exclude_pk
        ):
            ui.notify(
                f"Evidence Item Number '{item_num}' is already in use.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    return False


def validate_room_entry(
        stage: str,
        ROOMLABEL: str = "",
        ROOMDESC: str = "",
        ROOMFIRSTAGENT: str = "",
        ROOMSECONDAGENT: str = "",
        row: Optional[dict] = None,
) -> bool:
    """Return True if the entry is INVALID (i.e., submission should abort).

    Rules:
        - Room Label and Room Description: always required
        - Agents: both or neither, when the room is added and when edited
        - The same agent may not occupy both agent fields
        - Room label must be unique (excluding the row being updated)
    """

    label = (ROOMLABEL or "").strip()
    desc = (ROOMDESC or "").strip()
    first = (ROOMFIRSTAGENT or "").strip()
    second = (ROOMSECONDAGENT or "").strip()

    for field_label, value in [
        ("Room Label", label),
        ("Room Description", desc)
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    # Both agents or neither, whether the room is new or being edited. A
    # room can be recorded before anyone is assigned to it, and demanding
    # both agents on an edit meant a room saved without them could not have
    # so much as its description corrected.
    if bool(first) != bool(second):
        ui.notify(
            "Agents must be entered as a pair -- fill both 'First Agent "
            "Name' and 'Second Agent Name' or leave both blank.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return True

    # ----- Same agent checks -----
    if first and first == second:
        ui.notify(
            "The same agent cannot be listed in both the 'First Agent Name' "
            "and 'Second Agent Name' fields.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
        return True

    exclude_pk = (
        row["Z_PK"] if (stage == "update" and row is not None) else None
    )

    with get_session() as session:
        if value_in_use(session,
                        Rooms,
                        "ROOMLABEL",
                        label,
                        exclude_pk=exclude_pk
        ):
            ui.notify(
                "That label is currently assigned to another room.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    return False


def validate_person_data(
        stage: str,
        PERSONNAME: str = "",
        PERSONNOTE: str = "",
        row: Optional[dict] = None,
        PERSONDOB: str = "",
) -> bool:

    suspect = (PERSONNAME or "").strip()
    note = (PERSONNOTE or "").strip()

    for field_label, value in [
        ("Name", suspect),
        ("Note", note)
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    dob = (PERSONDOB or "").strip()
    if dob:
        born = parse_entered_date(dob, DATE_FORMAT)
        if born is None or born > datetime.now():
            return _refuse(
                "'DOB' is not a real date of birth. Enter it as MM-DD-YYYY, "
                "or leave it blank."
            )

    exclude_pk = (
            row["Z_PK"] if (stage == "update" and row is not None) else None
        )

    with get_session() as session:
        if value_in_use(session,
                        Persons,
                        "PERSONNAME",
                        suspect,
                        exclude_pk=exclude_pk,
        ):
            ui.notify(
                f"'{suspect}' is already in the database. Person names "
                "must be unique.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    return False


def validate_note_data(
        NOTEAUTHOR: str,
        NOTETEXT: str,
) -> bool:

    author = (NOTEAUTHOR or "").strip()
    text = (NOTETEXT or "").strip()

    for field_label, value in [
        ("Agent Name", author),
        ("Note Text", text)
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return True

    return False
