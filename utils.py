#!/usr/bin/env python3

"""
utils.py

File containing various functions used throughout the application.
"""
from datetime import datetime, timezone
import json
from nicegui import ui
import mimetypes
from models import (
    get_session,
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


NOTIFICATION_TIMEOUT = 0
POSITIVE_NOTIFICATION_TIMEOUT = 2000

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
    """Gets the current date and time.

    Returns:
        [str] current UTC date/time formatted as MM-DD-YYYY HH:MM:SS."""
    if format == "entry":
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    else:
        return datetime.now(timezone.utc).strftime("%m-%d-%Y %H:%M:%S")


def get_print_date_time() -> str:
    """Returns date and time separately for template compatibility."""
    now = datetime.now()
    print_date_time = now.strftime("%Y-%m-%d %H:%M")
    return print_date_time


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
                str(case.CASEDATETIMEBEGIN) if case.CASEDATETIMEBEGIN else ""
            ),
            "CASEDATETIMEEND": (
                str(case.CASEDATETIMEEND) if case.CASEDATETIMEEND else ""
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
    with open(AGENTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(agents, f, indent=4, ensure_ascii=False)


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

    agents = load_agents_from_json()

    name_lower = AGENTNAME.strip().lower()
    phone_clean = (
        AGENTPHONE.strip()
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
    )

    for AGENTNAME in agents:
        # Check name match
        if AGENTNAME.get("AGENTNAME", "").strip().lower() == name_lower:
            return True

        # Check phone match (normalize format first)
        existing_phone = AGENTNAME.get("AGENTPHONE", "").strip()
        existing_phone_clean = (
            existing_phone.replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace(" ", "")
        )

        if (
            existing_phone_clean
            and phone_clean
            and existing_phone_clean == phone_clean
        ):
            return True

        # Check email match (if applicable)
        if AGENTEMAIL:
            email_lower = AGENTEMAIL.strip().lower()
            existing_email = AGENTNAME.get("AGENTEMAIL", "").strip().lower()
            if email_lower and existing_email and existing_email == email_lower:
                return True

    return False


def confirm_delete_all(action: str, callback):
    """Shows a confirmation dialog before executing a destructive action."""
    with ui.dialog() as dialog, ui.card().classes("max-w-sm p-6"):

        ui.label(f"Warning!").classes("text-lg font-bold mb-2 text-[#1C69A8]")

        ui.label(
            f"This will permanently delete ALL {action} from the database. "
            "This action cannot be undone."
        ).classes("mb-4 text-base text-[#D4D4D8]")

        with ui.row().classes("w-full justify-end gap-2"):

            ui.button("Cancel", on_click=dialog.close).props("flat")

            def on_confirm():
                callback()
                dialog.close()

            ui.button(
                "Delete All",
                on_click=on_confirm,
                color="#1C69A8",
            ).props("negative unelevated")

    dialog.open()


def load_room_labels() -> list[str]:
    """Returns a list of all room labels from the Rooms table."""
    with get_session() as session:
        rows = (
            session.query(Rooms.ROOMLABEL, Rooms.ROOMDESC)
            .order_by(Rooms.ROOMLABEL)
            .all()
        )
        return [f"Room {r[0]} ({r[1]})" for r in rows]


def get_next_evid_num() -> str:
    """Gets the highest evidence number from the database and
    increments it.

    Returns:
        "1" if no evidence exists yet.
    """
    with get_session() as session:
        evid_query = (
            session.query(Evidence)
            .order_by(Evidence.EVIDNUM)
            .all()
        )

        if evid_query:
            last_evid = evid_query[-1]
            try:
                last_id = int(last_evid.EVIDNUM)
                next_id = last_id + 1
                return str(next_id)
            except ValueError:
                return "1"
        else:
            return "1"


def load_agent_names() -> list[str]:
    """Returns a list of all agent names from the Agents table."""
    with get_session() as session:
        rows = (
            session.query(Agents.AGENTNAME)
            .order_by(Agents.AGENTNAME)
            .all()
        )
        return [r[0] for r in rows]


def get_next_room_ltr() -> str:
    """Gets the label of the last room in the database and
    increments it to the next letter.

    Returns:
        "A" if no rooms exist yet.
    """
    with get_session() as session:
        rooms = session.query(Rooms).order_by(Rooms.ROOMLABEL).all()
        if rooms:
            last_label = rooms[-1].ROOMLABEL
            # Increment the ASCII value by 1, then convert back to char
            return chr(ord(last_label) + 1)
        else:
            return "A"


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
    """Delete all data from the app_data.db file."""
    with get_session() as session:
        try:
            session.query(Cases).delete()
            session.query(Agents).delete()
            session.query(Rooms).delete()
            session.query(Evidence).delete()
            session.query(Persons).delete()
            session.query(Notes).delete()
            session.query(UploadedFiles).delete()

            session.commit()

        except Exception as err:
            ui.notify(
                f"An error occured while trying to delete the data → {err}",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )


def value_in_use(session, model, column_name, value, exclude_pk=None) -> bool:
    """Return True if `value` already exists in `model.column_name`.

    Args:
        model:         the mapped class, e.g. Agents
        column_name:   name of the attribute to check, e.g. "agent_name"
        value:         the proposed value
        exclude_pk:    primary key of the row being updated (None on insert)

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


def validate_case_entry(
        stage: str,
        CASENUMBER: str,
        LOCATION: str,
        JURISDICTION: str,
        CASEDATETIMEBEGIN: str,
        row: Optional[dict] = None,
) -> bool:

    number = CASENUMBER.strip()
    location = LOCATION.strip()
    jurisdiction = JURISDICTION.strip()
    begin = CASEDATETIMEBEGIN.strip()

    for field_label, value in [
        ("Case Number", number),
        ("Location", location),
        ("Jurisdiction", jurisdiction),
        ("Date/Time Started", begin),
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning", timeout=0, position="center", close_button="OK",
            )
            return True

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
                timeout=0,
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

    name = AGENTNAME.strip()
    agency = AGENTPARENTAGENCY.strip()
    primary = AGENTPRIMARYROLE.strip()
    secondary = AGENTROLESECONDARY.strip()

    for field_label, value in [
        ("Agent Name", name),
        ("Agency", agency),
        ("Agent Role", primary),
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return True

    if primary and primary == secondary:
        ui.notify(
                f"The 'Primary Role' field and the 'Secondary Role' "
                f"field for {name} cannot be the same.",
                type="warning",
                timeout=0,
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
                timeout=0,
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

    item_num = EVIDNUM.strip()
    qty = EVIDQTY.strip()
    desc = EVIDDESC.strip()

    if EVIDLOCROOM:
        room = EVIDLOCROOM.strip()
    if EVIDLOCROOMDETAIL:
        loc_detail = EVIDLOCROOMDETAIL.strip()
    found_by = EVIDFOUNDBY.strip()
    witness = EVIDFOUNDBYWITNESS.strip()
    triaged = EVIDTRIAGED.strip()
    triaged_by = EVIDTRIAGEDBY.strip()

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
                timeout=0,
                position="center",
                close_button="OK",
            )
            return True

    if found_by == witness:
        ui.notify(
            "The same agent cannot be listed in the 'Found By' and the "
            "'Witnessed By' fields.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return True

    if triaged == "Yes" and not triaged_by:
        ui.notify(
            "The 'Triaged By' field is required if the 'Item Triaged?' "
            "field is set to 'Yes'.",
            type="warning",
            timeout=0,
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
                timeout=0,
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
        - Agents: on initial entry, both or neither; on update, both required
        - The same agent may not occupy both agent fields
        - Room label must be unique (excluding the row being updated)
    """

    label = ROOMLABEL.strip()
    desc = ROOMDESC.strip()
    first = ROOMFIRSTAGENT.strip()
    second = ROOMSECONDAGENT.strip()

    for field_label, value in [
        ("Room Label", label),
        ("Room Description", desc)
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning", timeout=0, position="center", close_button="OK",
            )
            return True

    if stage == "update":
        # Both agents are mandatory on update
        for field_label, value in [
            ("First Agent Name", first),
            ("Second Agent Name", second),
        ]:
            if not value:
                ui.notify(
                    f"The '{field_label}' field is required.",
                    type="warning",
                    timeout=0,
                    position="center",
                    close_button="OK",
                )
                return True
    else:
        # On initial entry: both or neither
        if bool(first) != bool(second):
            ui.notify(
                "Agents must be entered as a pair: fill both 'First Agent "
                "Name' and 'Second Agent Name', or leave both blank.",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return True

    # ----- Same agent checks -----
    if first and first == second:
        ui.notify(
            "The same agent cannot be listed in both the 'First Agent Name' "
            "and 'Second Agent Name' fields.",
            type="warning", timeout=0, position="center", close_button="OK",
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
                type="warning", timeout=0, position="center", close_button="OK",
            )
            return True

    return False


def validate_person_data(
        stage: str,
        PERSONNAME: str = "",
        SUSPECTNOTE: str = "",
        row: Optional[dict] = None,
) -> bool:

    suspect = PERSONNAME.strip()
    if SUSPECTNOTE:
        note = SUSPECTNOTE.strip()

    for field_label, value in [
        ("Name", suspect),
        ("Note", note)
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning", timeout=0, position="center", close_button="OK",
            )
            return True

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
                type="warning", timeout=0, position="center", close_button="OK",
            )
            return True

    return False


def validate_note_data(
        NOTEAUTHOR: str,
        NOTETEXT: str,
) -> bool:

    author = NOTEAUTHOR.strip()
    text = NOTETEXT.strip()

    for field_label, value in [
        ("Agent Name", author),
        ("Note Text", text)
    ]:
        if not value:
            ui.notify(
                f"The '{field_label}' field is required.",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return True

    return False