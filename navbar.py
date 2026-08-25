#!/usr/bin/env python3

"""
navbar.py

Provides build_navbar() to be called at the top of every authenticated page.
Uses Quasar's button + menu pattern for dropdown navigation items.

Also registers the two modal dialogs from the original includes:
    - _new_case_confirm.html     →  confirm_new_case_dialog()
    - _confirm_data_delete.html  →  confirm_delete_dialog()
"""

from nicegui import ui


# ── Modal Dialog Builders ───────────────────────────────────
def confirm_new_case_dialog(on_confirm: callable):
    """Replacement for _new_case_confirm.html.

    Shows a confirmation dialog before creating a new case file.

    Call the returned function to open it.
    """

    def open_dialog():
        with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):
            ui.label(
                "Create New Case File"
            ).classes("text-lg font-semibold mb-2")
            ui.label(
                "This will archive the current case and start a new one. "
                "Are you sure you want to proceed?"
            ).classes("text-sm text-gray-500 mb-4")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button(
                    "Cancel",
                    on_click=dialog.close,
                ).props("flat")

                ui.button(
                    "Confirm",
                    on_click=lambda: (on_confirm(), dialog.close()),
                ).props("unelevated")
        dialog.open()

    return open_dialog


def confirm_delete_dialog(
        on_confirm: callable,
        item_name: str = "this item"
):
    """Replacement for _confirm_data_delete.html.

    Shows a confirmation dialog before deleting data.
    """

    def open_dialog():
        with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

            ui.label(
                "Confirm Deletion"
            ).classes("text-lg font-semibold mb-2")

            ui.label(
                f"Are you sure you want to delete {item_name}? "
                "This action cannot be undone."
            ).classes("text-sm text-gray-500 mb-4")

            with ui.row().classes("w-full justify-end gap-2"):

                ui.button(
                    "Cancel",
                    on_click=dialog.close,
                ).props("flat")

                ui.button(
                    "Delete",
                    on_click=lambda: (on_confirm(), dialog.close()),
                ).props("negative unelevated")

        dialog.open()

    return open_dialog


# ── Dropdown Helper ─────────────────────────────────────────
def _nav_dropdown(label: str, items: list[tuple[str, callable]]):
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


# ── Main Navbar ─────────────────────────────────────────────
def build_navbar(
        is_admin: bool = False,
        username: str = "Guest",
        on_new_case: callable = None,
):
    """Builds the top navigation bar for authenticated users.

    Args:
        is_admin: Whether to show the Admin Panel link.
        username: The current user's display name.
        on_new_case: Callback for the "Make New Case File" action.
            If None, navigates to /cases/new.
    """

    with ui.header().classes("items-center bg-dark"):

        # ── Logo + Brand ────────────────────────────────────
        ui.icon("shield", size="32px").classes("text-white mr-2")

        ui.link(
            "V·E·C·T·O·R", "https://www.novadcicac.org/"
        ).classes(
            "text-white font-bold mr-6 no-underline"
        ).props("target=_blank")

        # ── Home Dropdown ───────────────────────────────────
        new_case_handler = on_new_case or (
            lambda: ui.navigate.to("/cases/new")
        )
        _nav_dropdown(
            "Home",
            [
                ("Home Page", lambda: ui.navigate.to("/")),
                ("About App", lambda: ui.navigate.to("/about")),
                ("Help", lambda: ui.navigate.to("/help")),
                ("---", None),
                ("View JSON Data", lambda: ui.navigate.to("/api/json")),
                ("Make New Case File", new_case_handler),
            ],
        )

        # ── Case Info (direct link — no dropdown) ───────────
        ui.button(
            "Case Info",
            on_click=lambda: ui.navigate.to("/cases"),
        ).props("flat color=white")

        # ── Agents Dropdown ─────────────────────────────────
        _nav_dropdown(
            "Agents",
            [
                (
                    "Agent List",
                    lambda: ui.navigate.to("/agents")
                ),
                (
                    "Add Agent",
                    lambda: ui.navigate.to("/agents")
                ),
            ],
        )

        # ── Rooms Dropdown ──────────────────────────────────
        _nav_dropdown(
            "Rooms",
            [
                (
                    "Room List",
                    lambda: ui.navigate.to("/rooms")
                ),
                (
                    "Add Room",
                    lambda: ui.navigate.to("/rooms")
                ),
            ],
        )

        # ── Evidence Dropdown ───────────────────────────────
        _nav_dropdown(
            "Evidence",
            [
                (
                    "Evidence List",
                    lambda: ui.navigate.to("/evidence")
                ),
                (
                    "Add Evidence",
                    lambda: ui.navigate.to("/evidence")
                ),
            ],
        )

        # ── People Dropdown ─────────────────────────────────
        _nav_dropdown(
            "People",
            [
                (
                    "Person List",
                    lambda: ui.navigate.to("/persons")
                ),
                (
                    "Add Person",
                    lambda: ui.navigate.to("/persons")
                ),
            ],
        )

        # ── Notes Dropdown ──────────────────────────────────
        _nav_dropdown(
            "Notes",
            [
                (
                    "Note List",
                    lambda: ui.navigate.to("/notes")
                ),
                (
                    "Add Note",
                    lambda: ui.navigate.to("/notes")
                ),
            ],
        )

        # ── Tools Dropdown ──────────────────────────────────
        _nav_dropdown(
            "Tools",
            [
                (
                    "Useful Links",
                    lambda: ui.navigate.to("/links")
                ),
            ],
        )

        # ── Reports Dropdown ────────────────────────────────
        _nav_dropdown(
            "Reports",
            [
                (
                    "Print Agent List", 
                    lambda: ui.navigate.to("/reports/agents")
                ),
                (
                    "Print Room List",
                    lambda: ui.navigate.to("/reports/rooms")
                ),
                (
                    "Print Evidence List (Detailed)",
                    lambda: ui.navigate.to("/reports/evidence"),
                ),
                (
                    "Print Evidence List (By Room)",
                    lambda: ui.navigate.to("/reports/evidence-by-room"),
                ),
                (
                    "Print Person List",
                    lambda: ui.navigate.to("/reports/persons")
                ),
                (
                    "Print Notes List", 
                    lambda: ui.navigate.to("/reports/notes")
                ),
                ("---", None),
                (
                    "Print Evidence List (Basic)",
                    lambda: ui.navigate.to("/reports/evidence-basic"),
                ),
            ],
        )

        # ── Spacer ──────────────────────────────────────────
        ui.space()

        # ── Welcome Dropdown ────────────────────────────────
        welcome_items = []
        if is_admin:
            welcome_items.append(
                (
                    "Admin Panel",
                    lambda: ui.navigate.to("/admin")
                )
            )
            welcome_items.append(("---", None))
        welcome_items.append(
            (
                "Logout",
                lambda: ui.navigate.to("/logout")
            )
        )

        _nav_dropdown(f"Welcome, {username}", welcome_items)
