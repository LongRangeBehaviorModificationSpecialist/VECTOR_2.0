#!/usr/bin/env python3

"""
utils.py
"""

from nicegui import ui


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
