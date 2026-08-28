#!/usr/bin/env python3

"""
utils.py
"""

from nicegui import ui


NOTIFICATION_TIMEOUT = 0

MESSAGES = {
    "agent_1": "The 'Agent's Name' field is required",
    "agent_2": "The 'Agent's Role' field is required.",
    "agent_3": "That Agent's Name is already in the case database. Please check the name and try again.",
    "agent_4": "Those initials are already used for another agent. Please change the initials and re-submit.",
    "agent_5": "That phone number is already assigned to another agent.",

    "case_1": "The 'Case Number' field is required.",
    "case_2": "The 'Location' field is required.",
    "case_3": "The 'Jurisdiction' field is required.",
    "case_4": "The 'Date/Time Started' field is required.",
    "case_err": "An error occurred while creating the case. Please check the information and try again.",

    "evid_1": "The 'Triaged By' field is required if the 'Item Triaged?' field is set to 'Yes'.",
    "evid_2": "The same agent cannot be listed in the 'Found By' and 'Witnessed By' fields.",
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
    "room_5": "The same agent cannot be listed in the 'First Agent Name' and 'Second Agent Name' fields.",

    "person_1": "The 'Name' field is required.",
}

def required_input(label: str, **kwargs):
    """Creates a ui.input with a red asterisk in the label."""
    req_input = ui.input(**kwargs)
    req_input.props("label-slot")
    req_input.add_slot("label", f'{label}<span style="color:#ef4444;"> *</span>')
    return req_input

def required_select(label: str, options: list, **kwargs):
    """Creates a ui.select with a red asterisk in the label."""
    req_select = ui.select(options=options, **kwargs)
    req_select.props("label-slot")
    req_select.add_slot("label", f'{label}<span style="color:#ef4444;"> *</span>')
    return req_select

def required_textarea(label: str, **kwargs):
    """Creates a ui.textarea with a red asterisk in the label."""
    req_textarea = ui.textarea(**kwargs)
    req_textarea.props("label-slot")
    req_textarea.add_slot("label", f'{label}<span style="color:#ef4444;"> *</span>')
    return req_textarea

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

            ui.button("Delete All", on_click=on_confirm).props("negative unelevated")

    dialog.open()
