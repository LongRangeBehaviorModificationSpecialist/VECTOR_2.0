#!/usr/bin/env python3

"""
navbar.py

Provides build_navbar() to be called at the top of every authenticated page.
Uses Quasar's button + menu pattern for dropdown navigation items.

"""

from nicegui import ui
from models import check_case_info


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


# ----- Main Navbar -----
def build_navbar(is_admin: bool = False, username: str = "Guest") -> None:
    """Builds the top navigation bar for authenticated users.

    Args:
        is_admin: Whether to show the Admin Panel link.
        username: The current user's display name.
        on_new_case: Callback for the "Make New Case File" action.
            If None, navigates to /cases/new.
    """

    with ui.header().classes("items-center bg-dark no-print"):

        # ----- Logo + Brand -----
        ui.image("/static/novadc_icac.ico").classes("w-[32px] h-[32px]")

        ui.link(
            "V·E·C·T·O·R",
            "https://novadcicac.vsp.virginia.gov/"
            ).classes("text-white font-bold mr-6 no-underline"
        ).props("target=_blank")

        ui.button("Home", on_click=lambda: ui.navigate.to("/"),
        ).props("flat color=white")

        ui.button("Case", on_click=lambda: ui.navigate.to("/cases"),
        ).props("flat color=white")

        ui.button("Agents", on_click=lambda: ui.navigate.to("/agents"),
        ).props("flat color=white")

        ui.button("Rooms", on_click=lambda: ui.navigate.to("/rooms"),
        ).props("flat color=white")

        ui.button("Evidence", on_click=lambda: ui.navigate.to("/evidence"),
        ).props("flat color=white")

        ui.button("People", on_click=lambda: ui.navigate.to("/persons"),
        ).props("flat color=white")

        ui.button("Notes", on_click=lambda: ui.navigate.to("/notes")
        ).props("flat color=white")

        ui.button("Files", on_click=lambda: ui.navigate.to("/uploads")
        ).props("flat color=white")

        ui.button("Tools", on_click=lambda: ui.navigate.to("/links")
        ).props("flat color=white")

        ui.button("Reports", on_click=lambda: ui.navigate.to("/reports")
        ).props("flat color=white")

        _nav_dropdown(
            "Help",
            [
                ("About App", lambda: ui.navigate.to("/about")),
                ("Help", lambda: ui.navigate.to("/help")),
                ("---", None),
            ],
        )

        ui.space()

        with ui.row().classes("items-center gap-2 ml-auto mr-4"):
            case_info = check_case_info()

            if case_info:
                ui.badge(
                    f"Case No.: {case_info['CASENUMBER']}",
                    color="positive"
                ).classes("mr-2 py-3 px-5")
            else:
                ui.badge(
                    "No Active Case",
                    color="#ef4444"
                ).classes("mr-2 py-3 px-5")

        # ----- Spacer -----
        ui.space()

        # ----- Welcome Dropdown -----
        welcome_items = []
        if is_admin:
            welcome_items.append(
                ("Admin Panel", lambda: ui.navigate.to("/admin"))
            )
            welcome_items.append(("---", None))
        welcome_items.append(
            ("Logout", lambda: ui.navigate.to("/logout"))
        )
        welcome_items.append(
            ("Shutdown", lambda: ui.navigate.to("/shutdown"))
        )

        _nav_dropdown(f"Welcome, {username}", welcome_items)
