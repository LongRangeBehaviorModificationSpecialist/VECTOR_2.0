#!/usr/bin/env python3

"""
crud_widgets.py

What a page's field description is, and how one becomes something on
screen: the Field dataclass, the two notifications every page uses, and
the widget builders -- including the dropdown that keeps what was typed
into it when the field is left.

Split out of crud.py so that the builder and its dialogs can both use
these without importing each other.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from nicegui import ui

import clock
from utils import (
    CONFIRM_TIMEOUT,
    WARN_TIMEOUT,
    required_input,
    required_select,
    required_textarea,
)


# ----- Field description -----
@dataclass
class Field:
    """One column, and how it should be presented.

    name:        the model column
    label:       what the user sees
    kind:        input | select | textarea
    required:    renders with the red asterisk
    options:     callable returning select options, evaluated per render
                 so a newly added agent appears without a restart
    props:       extra Quasar props, e.g. an input mask
    placeholder: shown in the empty field
    readonly:    displayed but not editable
    in_form:     include in the add form
    in_edit:     include in the edit dialog
    in_table:    include as a table column
    table_label: column heading, when it should differ from `label`
    default:     callable producing the value for a fresh form
    new_values:  let a select accept a value that is not in its options
    now_button:  offer a button that fills the field with this machine's
                 current date and time
    """

    name: str
    label: str
    kind: str = "input"
    required: bool = False
    options: Optional[Callable[[], list]] = None
    props: str = ""
    placeholder: str = ""
    readonly: bool = False
    in_form: bool = True
    in_edit: bool = True
    in_table: bool = True
    table_label: Optional[str] = None
    default: Optional[Callable[[], str]] = None
    new_values: bool = False
    now_button: bool = False

# ----- Notification helpers -----
def notify_problem(message: str) -> None:
    """A problem the user has to acknowledge."""
    ui.notify(
        message,
        type="warning",
        timeout=WARN_TIMEOUT,
        position="center",
        close_button="OK",
    )


def notify_done(message: str) -> None:
    """A confirmation that can fade."""
    ui.notify(
        message,
        timeout=CONFIRM_TIMEOUT,
        position="bottom",
        close_button="OK",
    )


# ----- Widget construction -----
def options_including(options, value):
    """A dropdown's options, with the record's own value among them.

    A stored value need not be on today's list: an agent from an imported
    case is not on this machine's roster, and a room can be relabelled or
    an agent deleted after evidence was logged against them. NiceGUI
    refuses a value missing from the options, so the edit dialog failed to
    open, with nothing on screen to say why.
    """
    if value in (None, ""):
        return options
    if isinstance(options, dict):
        return options if value in options else {**options, value: value}
    options = list(options)
    return options if value in options else options + [value]


def select_value(value):
    """The value a dropdown opens with.

    A dropdown left blank is saved as "", which is never one of its
    options. NiceGUI refuses a value that is not an option, so the edit
    dialog for any record with a blank dropdown -- a room with no agents
    yet, an item nobody triaged -- failed to open, with nothing on screen.
    """
    return None if value == "" else value


def typed_choice(text, options, current, allow_new: bool):
    """What text typed into a dropdown becomes when the field is left.

    An option matching the text, ignoring case -- or, where new values are
    allowed, the text itself. None leaves the dropdown as it is.
    """
    text = (text or "").strip()
    if not text or text == str(current or ""):
        return None
    choices = list(options.keys()) if isinstance(options, dict) else list(options)
    for choice in choices:
        if str(choice).lower() == text.lower():
            return None if choice == current else choice
    return text if allow_new else None


def _keep_typed_text(select, allow_new: bool) -> None:
    """Keeps what was typed into a dropdown when the field is left.

    Quasar turns typed text into a value only on Enter. Clicking or tabbing
    out of the field threw it away, so an agent's name that was not on the
    roster had to be confirmed with Enter or it was lost.
    """
    typed = {"text": ""}

    def remember(event) -> None:
        typed["text"] = str(event.args or "")

    def forget(_event=None) -> None:
        # A choice picked from the list replaces whatever was typed.
        typed["text"] = ""

    def commit(_event=None) -> None:
        text, typed["text"] = typed["text"], ""
        choice = typed_choice(text, select.options, select.value, allow_new)
        if choice is None:
            return
        options = select.options
        present = options.keys() if isinstance(options, dict) else options
        if choice not in present:
            if isinstance(options, dict):
                options = {**options, choice: choice}
            else:
                options = [*options, choice]
        select.set_options(options, value=choice)

    select.on("input-value", remember)
    select.on_value_change(forget)
    select.on("blur", commit)


def _build_widget(spec_field: Field, value=None):
    """Builds the input for one field."""
    factory_required = {
        "input": required_input,
        "select": required_select,
        "textarea": required_textarea,
    }
    factory_optional = {
        "input": ui.input,
        "select": ui.select,
        "textarea": ui.textarea,
    }

    if spec_field.kind == "select":
        value = select_value(value)

    kwargs = {}
    if value is not None:
        kwargs["value"] = value
    if spec_field.placeholder:
        kwargs["placeholder"] = spec_field.placeholder

    if spec_field.kind == "select":
        options = options_including(
            spec_field.options() if spec_field.options else [], value
        )
        kwargs["with_input"] = True
        if spec_field.new_values:
            kwargs["new_value_mode"] = "add"
        if spec_field.required:
            widget = factory_required["select"](
                label=spec_field.label, options=options, **kwargs
            )
        else:
            widget = factory_optional["select"](
                options=options, label=spec_field.label, **kwargs
            )
    else:
        if spec_field.required:
            widget = factory_required[spec_field.kind](
                label=spec_field.label, **kwargs
            )
        else:
            widget = factory_optional[spec_field.kind](
                label=spec_field.label, **kwargs
            )

    widget.classes("w-full")
    if spec_field.props:
        widget.props(spec_field.props)
    if spec_field.readonly:
        widget.props("readonly")
    if spec_field.kind == "select" and not spec_field.readonly:
        _keep_typed_text(widget, allow_new=spec_field.new_values)
    return widget


def _make_widget(spec_field: Field, value=None):
    """Builds the input for one field, with its fill button if it has one."""
    if not spec_field.now_button:
        return _build_widget(spec_field, value)

    with ui.column().classes("w-full gap-0"):
        widget = _build_widget(spec_field, value)
        widget.props(f'hint="Times are this machine\'s: {clock.zone_label()}"')
        ui.button(
            "Fill with current date/time",
            icon="schedule",
            on_click=lambda: widget.set_value(clock.case_time_now()),
        ).props("flat dense no-caps").classes(
            "self-end hover-border-blue"
        )
    return widget


def _values_from(widgets: dict) -> dict:
    """Reads the current value of every widget, normalised to str."""
    return {
        name: ("" if widget.value is None else widget.value)
        for name, widget in widgets.items()
    }
