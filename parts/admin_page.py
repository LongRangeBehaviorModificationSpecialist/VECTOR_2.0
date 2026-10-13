#!/usr/bin/env python3

"""
admin_page.py

Admin panel for user management.

Only accessible to admin accounts. Manages users stored in
the separate users.db database file.
"""

from nicegui import ui

from auth import get_current_user_name, get_is_admin
from navbar import build_navbar
from parts.admin_users import (
    add_user_card,
    network_access_card,
    session_controls,
    users_table,
)

# ----- PAGE BUILDER -----
def build_admin_page():
    """Builds the Admin user management page.

    Re-checks admin status rather than trusting the caller: the route
    guard and this check must both fail before a non-admin sees the
    panel.
    """

    if not get_is_admin():
        ui.navigate.to("/")
        return

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "User Administration"
        ).classes("text-2xl font-bold m-4")

        # The card is drawn above the table it refreshes, so the table's
        # own refresh is handed to it once both exist.
        refresh = {"users": lambda: None}

        add_user_card(lambda: refresh["users"]())
        refresh["users"] = users_table()
        session_controls()
        network_access_card()

    # Initial render
    refresh["users"]()
