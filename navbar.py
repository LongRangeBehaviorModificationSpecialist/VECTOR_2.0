#!/usr/bin/env python3

"""
navbar.py

Provides build_navbar() to be called at the top of every authenticated
page. Uses Quasar's button + menu pattern for dropdown navigation items.

The two dialog builders that used to live here -- confirm_new_case_dialog
and confirm_delete_dialog -- were written as shared helpers and never
adopted by any page. parts/crud.py now provides the real shared dialogs,
so they have been removed rather than left as a second, dead answer to
the same question.
"""

from nicegui import ui

from auth import is_authenticated
from models import check_case_info
from program.config import STATIC_DIR


# ----- Dropdown Helper -----
def _nav_dropdown(label: str, items: list[tuple[str, callable]]) -> None:
    """Creates a dropdown button in the navbar.

    Each item is a (label, callback) tuple.
    """
    with ui.button(label).props("flat color=white"):
        with ui.menu() as menu:
            for item_label, callback in items:
                if item_label == "---":
                    ui.separator()
                else:
                    ui.menu_item(item_label, on_click=callback)


# ----- Unit logo -----
def static_url(filename: str) -> str | None:
    """The /static address of a file that is present, or None.

    The logo files are unit branding and are not distributed with the
    source, so a fresh checkout has none of them.
    """
    if (STATIC_DIR / filename).is_file():
        return f"/static/{filename}"
    return None


def unit_logo(filename: str, classes: str) -> None:
    """Shows a logo from static/, or nothing when the file is missing.

    Every logo sits beside a title, so leaving it out still leaves the
    page named -- where a missing file used to show a broken-image icon.
    """
    url = static_url(filename)
    if url:
        ui.image(url).classes(classes)


# ----- Main Navbar -----
def build_navbar(is_admin: bool = False, username: str = "Guest") -> None:
    """Builds the top navigation bar for authenticated users.

    Args:
        is_admin: Whether to show the Admin Panel link.
        username: The current user's display name.
    """

    with ui.header().classes("items-center bg-dark no-print"):

        # ----- Logo + Brand -----
        unit_logo("novadc_icac.ico", "w-[32px] h-[32px]")

        ui.link(
            "V·E·C·T·O·R",
            "https://novadcicac.vsp.virginia.gov/"
            ).classes("text-white font-bold mr-6 no-underline"
        ).props("target=_blank")

        # ----- Home Button -----
        ui.button(
            "Home",
            on_click=lambda: ui.navigate.to("/"),
        ).props("flat color=white")

        # ----- Case Info Button -----
        ui.button(
            "Case",
            on_click=lambda: ui.navigate.to("/cases"),
        ).props("flat color=white")

        # ----- Agents Button -----
        ui.button(
            "Agents",
            on_click=lambda: ui.navigate.to("/agents"),
        ).props("flat color=white")

        # ----- Rooms Button -----
        ui.button(
            "Rooms",
            on_click=lambda: ui.navigate.to("/rooms"),
        ).props("flat color=white")

        # ----- Evidence Button -----
        ui.button(
            "Evidence",
            on_click=lambda: ui.navigate.to("/evidence"),
        ).props("flat color=white")

        # ----- People Button -----
        ui.button(
            "People",
            on_click= lambda: ui.navigate.to("/persons"),
        ).props("flat color=white")

        # ----- Notes Button -----
        ui.button(
            "Notes",
            on_click=lambda: ui.navigate.to("/notes")
        ).props("flat color=white")

        # ----- Files Button -----
        ui.button(
            "Files",
            on_click=lambda: ui.navigate.to("/uploads")
        ).props("flat color=white")

        # ----- Tools Button -----
        ui.button(
            "Tools",
            on_click=lambda: ui.navigate.to("/links")
        ).props("flat color=white")

        # ----- Reports Button -----
        ui.button(
            "Reports",
            on_click=lambda: ui.navigate.to("/reports")
        ).props("flat color=white")

        # ----- Help Button -----
        _nav_dropdown(
            "Help",
            [
                ("About App", lambda: ui.navigate.to("/about")),
                ("Help", lambda: ui.navigate.to("/help")),
            ],
        )

        # ----- Active case -----
        # Centred between the menus, so an agent can see at a glance which
        # case an entry is going into. Only once signed in: the login page
        # answers anyone who can reach the port, and a case number is not
        # theirs to read.
        ui.space()

        if is_authenticated():
            case_info = check_case_info()
            if case_info:
                ui.badge(
                    f"Case No.: {case_info['CASENUMBER']}",
                    color="positive",
                ).classes("py-3 px-5")
            else:
                ui.badge(
                    "No Active Case",
                    color="#ef4444",
                ).classes("py-3 px-5")

        # ----- Spacer -----
        ui.space()

        # ----- Welcome Dropdown -----
        welcome_items = []
        if is_admin:
            welcome_items.append(
                (
                    "Admin Panel",
                    lambda: ui.navigate.to("/admin")
                )
            )
            welcome_items.append(
                (
                    "Audit Trail",
                    lambda: ui.navigate.to("/audit")
                )
            )
            welcome_items.append(("---", None))
        welcome_items.append(
            (
                "Logout",
                lambda: ui.navigate.to("/logout")
            )
        )
        welcome_items.append(
            (
                "Shutdown",
                lambda: ui.navigate.to("/shutdown")
            )
        )

        _nav_dropdown(
            f"Welcome, {username}",
            welcome_items
        )
