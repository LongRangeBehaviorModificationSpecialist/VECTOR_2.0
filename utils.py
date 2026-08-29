#!/usr/bin/env python3

"""
utils.py
"""
from datetime import datetime
import json
from nicegui import ui
import mimetypes
from models import get_session, Agents, Cases, Evidence, Rooms
from pathlib import Path
from program.inc.agent_role import AGENT_ROLE_LIST
from program.inc.agency_list import AGENCY_LIST
from program.inc.jurisdictions import JURISDICTIONS

NOTIFICATION_TIMEOUT = 0
POSITIVE_NOTIFICATION_TIMEOUT = 4000

AGENTS_JSON_PATH = Path(__file__).parent / "agents.json"

MESSAGES = {
    "agent_1": "The 'Agent's Name' field is required",
    "agent_2": "The 'Agent's Role' field is required.",
    "agent_3": "That Agent's Name is already in the case database. Please "
        "check the name and try again.",
    "agent_4": "Those initials are already used for another agent. Please "
        "change the initials and re-submit.",
    "agent_5": "That phone number is already assigned to another agent.",

    "case_1": "The 'Case Number' field is required.",
    "case_2": "The 'Location' field is required.",
    "case_3": "The 'Jurisdiction' field is required.",
    "case_4": "The 'Date/Time Started' field is required.",
    "case_err": "An error occurred while creating the case. Please check "
        "the information and try again.",

    "evid_1": "The 'Triaged By' field is required if the 'Item Triaged?' "
        "field is set to 'Yes'.",
    "evid_2": "The same agent cannot be listed in the 'Found By' and "
        "'Witnessed By' fields.",
    "evid_3": "The 'Evidence Item Number' field is required.",
    "evid_4": "The 'Quantity' field is required.",
    "evid_5": "The 'Evidence Description' field is required.",
    "evid_6": "The 'Room Located' field is required.",
    "evid_7": "The 'Where Located' field is required.",
    "evid_8": "The 'Found By' field is required.",
    "evid_9": "The 'Witnessed By' field is required.",

    "note_1": "The 'Agent Name' field is required.",
    "note_2": "The 'Note Text' field is required.",

    "room_1": "A Room Label is required.",
    "room_2": "The 'Room Description' field is required.",
    "room_3": "That label is currently assigned to another room.",
    "room_4": "That room description is already assigned to another room.",
    "room_5": "The same agent cannot be listed in the 'First Agent Name' and "
        "'Second Agent Name' fields.",

    "person_1": "The 'Name' field is required.",
}

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

def get_current_timestamp() -> str:
    """Returns current date/time formatted as MM-DD-YYYY HH:MM:SS."""
    return datetime.now().strftime("%m-%d-%Y %H:%M:%S")


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
            "case_number": case.case_number or "",
            "location": case.location or "",
            "jurisdiction": case.jurisdiction or "",
            "case_date_time_begin": (
                str(case.case_date_time_begin)
                if case.case_date_time_begin
                else ""
            ),
            "case_date_time_end": (
                str(case.case_date_time_end)
                if case.case_date_time_end
                else ""
            ),
        }


def load_jurisdiction_options() -> list[str]:
    """Returns jurisdiction choices from JURISDICTIONS.

    Handles both plain-string and (value, label) tuple formats.
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

    Returns rows as dicts for auto-population.
    """
    data = load_agents_from_json()

    # If the JSON file is a dict instead of a list, wrap it in a list
    if isinstance(data, dict):
        data = [data]

    return [
        {
            "name": a.get("name", ""),
            "agency": a.get("agency", "") or "",
            "phone": a.get("phone", "") or "",
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
        if a["name"] not in seen:
            seen.add(a["name"])
            unique_names.append(a["name"])
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


def check_agent_dup_role(agent: str, role: str, role_secondary: str) -> bool:
    if role and role_secondary:
        if role.strip().lower() == role_secondary.strip().lower():
            ui.notify(
                f"The 'Primary Role' field and the 'Secondary Role' field "
                f"for {agent} cannot be the same.",
                type="warning",
                timeout=NOTIFICATION_TIMEOUT,
                close_button="OK",
                position="center",
                )
            return True
        return False


def confirm_delete_all(action: str, callback):
    """Shows a confirmation dialog before executing a destructive action."""
    with ui.dialog() as dialog, ui.card().classes("max-w-sm p-6"):

        ui.label(f"Warning!").classes("text-lg font-bold mb-2 text-red-500")

        ui.label(
            f"This will permanently delete ALL {action} from the database. "
            "This action cannot be undone."
        ).classes("mb-4")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")

            def on_confirm():
                callback()
                dialog.close()

            ui.button(
                "Delete All",
                on_click=on_confirm
            ).props("negative unelevated")

    dialog.open()


def load_agent_names() -> list[str]:
    """Returns a list of all agent names from the Agents table."""
    with get_session() as session:
        rows = (
            session.query(Agents.agent_name)
            .order_by(Agents.agent_name)
            .all()
        )
        return [r[0] for r in rows]


def load_room_labels() -> list[str]:
    """Returns a list of all room labels from the Rooms table."""
    with get_session() as session:
        rows = (
            session.query(Rooms.room_label, Rooms.room_desc)
            .order_by(Rooms.room_label)
            .all()
        )
        return [f"Room {r[0]} ({r[1]})" for r in rows]


def get_next_evid_num() -> str:
    """Gets the highest evidence number from the database and
    increments it.

    Returns "1" if no evidence exists yet.
    """
    with get_session() as session:
        evid_query = (
            session.query(Evidence)
            .order_by(Evidence.evid_num)
            .all()
        )

        if evid_query:
            last_evid = evid_query[-1]
            try:
                last_id = int(last_evid.evid_num)
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
            session.query(Agents.agent_name)
            .order_by(Agents.agent_name)
            .all()
        )
        return [r[0] for r in rows]


def get_next_room_ltr() -> str:
    """Gets the label of the last room in the database and
    increments it to the next letter.

    Returns "A" if no rooms exist yet.
    """
    with get_session() as session:
        rooms = session.query(Rooms).order_by(Rooms.room_label).all()
        if rooms:
            last_label = rooms[-1].room_label
            # Increment the ASCII value by 1,
            # then convert back to char
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
