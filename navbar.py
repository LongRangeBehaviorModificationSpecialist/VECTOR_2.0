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


# ----- Modal Dialog Builders -----
def confirm_new_case_dialog(on_confirm: callable) -> None:
    """Replacement for _new_case_confirm.html.

    Shows a confirmation dialog before creating a new case file.

    Call the returned function to open it.
    """

    def open_dialog() -> None:
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


def confirm_delete_dialog(on_confirm: callable, item_name: str = "this item"):
    """Replacement for _confirm_data_delete.html.

    Shows a confirmation dialog before deleting data.
    """

    def open_dialog() -> None:
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
def build_navbar(
    is_admin: bool = False,
    username: str = "Guest",
    on_new_case: callable = None,
) -> None:
    """Builds the top navigation bar for authenticated users.

    Args:
        is_admin: Whether to show the Admin Panel link.
        username: The current user's display name.
        on_new_case: Callback for the "Make New Case File" action.
            If None, navigates to /cases/new.
    """

    with ui.header().classes("items-center bg-dark no-print"):

        # ----- Logo + Brand -----
        ui.image(
            "/static/novadc_icac.ico",
        ).classes("w-[32px] h-[32px]")

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
        new_case_handler = on_new_case or (
            lambda: ui.navigate.to("/cases/new")
        )
        _nav_dropdown(
            "Help",
            [
                ("About App", lambda: ui.navigate.to("/about")),
                ("Help", lambda: ui.navigate.to("/help")),
                ("---", None),
                ("Make New Case File", new_case_handler),
            ],
        )

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
