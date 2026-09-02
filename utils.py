#!/usr/bin/env python3

"""
utils.py
"""
from datetime import datetime
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
            "email": a.get("email", "") or "",
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


def is_duplicate_agent_in_json(agent_name: str, phone: str, email: str = "") -> bool:
    """Checks if an agent with the same name, phone, or email already
    exists in agents.json.

    Returns:
        True if duplicate found, False otherwise.
    """

    agents = load_agents_from_json()

    name_lower = agent_name.strip().lower()
    phone_clean = (
        phone.strip()
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
        .replace(" ", "")
    )

    for agent_name in agents:
        # Check name match
        if agent_name.get("name", "").strip().lower() == name_lower:
            return True

        # Check phone match (normalize format first)
        existing_phone = agent_name.get("phone", "").strip()
        existing_phone_clean = (
            existing_phone.replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace(" ", "")
        )

        if existing_phone_clean and phone_clean and existing_phone_clean == phone_clean:
            return True

        # Check email match (if applicable)
        if email:
            email_lower = email.strip().lower()
            existing_email = agent_name.get("email", "").strip().lower()
            if email_lower and existing_email and existing_email == email_lower:
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


def delete_all_data() -> None:
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


def validate_case_data(
        case_number: str,
        location: str,
        jurisdiction: str,
        datetime_start: str
) -> bool:

    if not case_number:
        ui.notify(
            "The 'Case Number' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not location:
        ui.notify(
            "The 'Location' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not jurisdiction:
        ui.notify(
            "The 'Jurisdiction' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not datetime_start:
        ui.notify(
            "The 'Date/Time Started' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    return True


def validate_agent_data(
        agent_name: str | None,
        agency: str | None,
        role: str | None,
        role_secondary: str = ""
) -> bool:

    if not agent_name:
        ui.notify(
            "The 'Agent Name' field is required",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
            )
        return False

    if not agency:
        ui.notify(
            "The 'Agency' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
            )
        return False

    if not role:
        ui.notify(
            "The 'Agent Role' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
            )
        return False

    if role and role_secondary:
        if role.strip().lower() == role_secondary.strip().lower():
            ui.notify(
                    f"The 'Primary Role' field and the 'Secondary Role' field "
                    f"for {agent_name} cannot be the same.",
                    type="warning",
                    timeout=0,
                    position="center",
                    close_button="OK",
                    )
            return False

    return True


def validate_initial_evidence(
        evid_num: str,
        evid_qty: str,
        evid_desc: str,
        evid_loc_room: str,
        evid_loc_room_detail: str,
        evid_found_by: str,
        evid_found_by_witness: str,
        evid_triaged: str = "",
        evid_triaged_by: str = "",
) -> bool:

    if not evid_num:
        ui.notify(
            "The 'Evidence Item Number' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not evid_qty:
        ui.notify(
            "The 'Quantity' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not evid_desc:
        ui.notify(
            "The 'Evidence Description' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not evid_loc_room:
        ui.notify(
            "The 'Room Located' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not evid_loc_room_detail:
        ui.notify(
            "The 'Where Located' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not evid_found_by:
        ui.notify(
            "The 'Found By' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not evid_found_by_witness:
        ui.notify(
            "The 'Witnessed By' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if evid_found_by == evid_found_by_witness:
        ui.notify(
            "The same agent cannot be listed in the 'Found By' and "
            "'Witnessed By' fields.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if evid_triaged == "Yes" and not evid_triaged_by:
        ui.notify(
            "The 'Triaged By' field is required if the 'Item Triaged?' "
            "field is set to 'Yes'.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    with get_session() as session:
        existing = (
            session.query(Evidence)
            .filter_by(evid_num=evid_num)
            .first()
        )

        if existing:
            ui.notify(
                f"Evidence Item Number '{evid_num}' is "
                "already used.",
                type="negative",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return False

    return True


def validate_update_evidence(
        evid_num: str,
        evid_found_by: str,
        evid_found_by_witness: str,
        evid_triaged: str,
        evid_triaged_by: str,
        row
) -> bool:

    if (
        evid_found_by and evid_found_by_witness
        and evid_found_by == evid_found_by_witness
    ):
        ui.notify(
            "The same agent cannot be listed in the 'Found By' and "
            "'Witnessed By' fields.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if evid_triaged == "Yes" and not evid_triaged_by:
        ui.notify(
            "The 'Triaged By' field is required if the 'Item Triaged?' "
            "field is set to 'Yes'.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    with get_session() as session:
        dup = (
            session.query(Evidence)
            .filter(
                Evidence.evid_num == (evid_num),
                Evidence.id != row["id"])
            .first()
        )

        if dup:
            ui.notify(
                f"Evidence number {evid_num} is already used",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return False

    return True


def validate_room_data(
        room_label: str,
        room_desc: str,
        first_agent: str = "",
        second_agent: str = ""
) -> bool:

    if not room_label:

        ui.notify(
            "The 'Room Label' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    if not room_desc:
        ui.notify(
            "The 'Room Description' field is required.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return False

    with get_session() as session:
        if (
            session.query(Rooms)
            .filter_by(room_label=room_label)
            .first()
        ):

            ui.notify(
                "That label is currently assigned to another room.",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return False

        # ----- Duplicate description validation -----
        if (
            session.query(Rooms)
            .filter_by(room_desc=room_desc)
            .first()
        ):
            ui.notify(
                "That room description is already assigned to another room.",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return False

        # ----- Same agent checks -----
        if (
            first_agent and second_agent and
            first_agent == second_agent
        ):

            ui.notify(
                "The same agent cannot be listed in the 'First Agent Name' "
                "and 'Second Agent Name' fields.",
                type="warning",
                timeout=0,
                position="center",
                close_button="OK",
            )
            return False

    return True
