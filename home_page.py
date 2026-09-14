#!/usr/bin/env python3

"""
home_page.py

Handles:
    /                →   Home/Login page
    /about           →   About page
    /help            →   Help page
    /make_new_case   →   Clear all data (dangerous!)
"""

from nicegui import ui
from pathlib import Path

from import_export import (
    export_vector_to_csv,
    export_vector_to_json,
    import_vector_from_csv,
    import_vector_from_json,
)
from main import is_authenticated, get_current_user_name, get_is_admin
from models import get_users_session, has_active_case, clear_all_case_data
from navbar import build_navbar
from program.config import Config
from utils import delete_all_data


# ----- Home Page Registration -----
@ui.page("/")
@ui.page("/home")
def home() -> None:
    """Home/login page — shows menu if authenticated,
    login form otherwise.
    """
    authenticated = is_authenticated()

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    if authenticated:
        build_authenticated_home()
    else:
        build_login_home()


def build_authenticated_home() -> None:
    """Main menu shown to logged-in users."""

    with ui.column().classes("items-center w-full mt-8 py-2"):

        # ----- Page Title and Header -----

        ui.image("/static/novadc_icac.png").classes("w-[150px] h-[150px] mb-2")

        ui.label(
            "V·E·C·T·O·R Home"
        ).classes("text-2xl font-bold text-center mx-2")

        ui.label(
            "The Virginia Evidence Collection, Tracking, "
            "Organization, & Reporting Program"
        ).classes("text-base text-gray-400 text-center max-w-xl")

    with ui.row().classes("flex justify-center items-center gap-6 w-full"):

        ui.label("Main Menu").classes("text-xl items-center font-semibold py-1")

    # ----- Action Buttons ROW 1: Start New Case | Add Agent | Add Room -----

    with ui.row().classes(
        "flex justify-center items-center gap-6 py-1 w-full"):

        ui.button(
            "Start New Case",
            on_click=lambda _: confirm_new_case_handler(),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

        # on_click=lambda: ui.navigate.to("/cases"),

        ui.button(
            "Add Agent",
            on_click=lambda: ui.navigate.to("/agents"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

        ui.button(
            "Add Room",
            on_click=lambda: ui.navigate.to("/rooms"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

    # ----- Action Buttons ROW 2: Add Evidence | Add Person | Add Note -----

    with ui.row().classes("flex justify-center items-center gap-6 py-1 w-full"):

        ui.button(
            "Add Evidence",
            on_click=lambda: ui.navigate.to("/evidence"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

        ui.button(
            "Add Person",
            on_click=lambda: ui.navigate.to("/persons"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

        ui.button(
            "Add Note",
            on_click=lambda: ui.navigate.to("/notes"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

    # ----- Action Buttons ROW 3: Add File | Useful Links -----

    with ui.row().classes(
        "flex justify-center items-center gap-6 py-1 w-full"):

        ui.button(
            "Add File",
            on_click=lambda: ui.navigate.to("/uploads"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

        ui.button(
            "Useful Links",
            on_click=lambda: ui.navigate.to("/links"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

        ui.button(
            "Reports",
            on_click=lambda: ui.navigate.to("/reports"),
            color="var(--vsp-blue)").props("push"
        ).classes("flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]")

    # ----- Import / Export ROW -----

    with ui.column().classes("items-center w-full py-2"):

        with ui.row().classes("flex justify-center items-center gap-6 w-full"):

            ui.label("Data Management").classes("text-lg font-bold py-1")

        # ----- Row to hold the Data Management buttons -----
        with ui.row().classes("flex justify-center items-center gap-6 w-full"):

            # ----- EXPORT Button -----
            def open_export_dialog() -> None:

                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

                    ui.label(
                        "Export Data..."
                    ).classes("text-lg font-bold text-[var(--vsp-blue)]")

                    ui.label(
                        "Export all database tables and uploaded files "
                        "into a single compressed ZIP archive saved to "
                        "your /Desktop/ directory."
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    ui.label("The ZIP file will be named :").classes(
                        "text-sm text-[var(--vsp-gray)]"
                    )

                    ui.label(
                        "'<case-number>_<datetime>_saved_results'"
                    ).classes("text-base text-[var(--vsp-blue)]")

                    # ----- Export format selection -----
                    ui.label("Export format:").classes(
                        "mt-2 text-sm font-semibold text-[var(--vsp-gray)]"
                    )

                    format_radio = ui.radio(
                        {
                            "csv": "CSV — one file per database table",
                            "json": "JSON — all data in a single file",
                            "both": "Both — export CSV ZIP and JSON together",
                        },
                        value="csv",
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    # ----- Password option -----
                    encrypt_checkbox = ui.checkbox(
                        "Encrypt with password (AES-256)"
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    password_input = ui.input(
                        label="ENTER PASSWORD :",
                        password=True,
                    ).classes("w-full yellow-label text-sm")

                    password_input.bind_visibility_from(
                        encrypt_checkbox,
                        "value",
                    )

                    def do_export() -> None:
                        #  ----- Password validation -----
                        pwd = (
                            password_input.value
                            if encrypt_checkbox.value
                            else None
                        )

                        if encrypt_checkbox.value and not pwd:
                            ui.notify(
                                "Please enter a password or uncheck "
                                "encryption.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        dialog.close()

                        # ----- Run the selected exports -----
                        if format_radio.value in ("csv", "both"):
                            export_vector_to_csv(password=pwd)

                        if format_radio.value in ("json", "both"):
                            export_vector_to_json(password=pwd)

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent").props("flat"
                        ).classes("text-[var(--vsp-blue)]")

                        ui.button(
                            "Export Now",
                            on_click=do_export,
                            color="var(--vsp-blue)").props("push"
                        ).classes("text-[var(--vsp-white)]")

                dialog.open()

            # ----- IMPORT Button -----
            def open_import_dialog() -> None:

                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

                    ui.label("Import Data...").classes(
                        "text-lg font-bold text-[var(--vsp-blue)]"
                    )

                    ui.label(
                        "Select a file previously exported from VECTOR."
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    # ----- Import format selection -----
                    ui.label(
                        "Select file format :"
                    ).classes("text-sm text-[var(--vsp-blue)]")

                    format_radio = ui.radio(
                        {
                            "csv": "CSV ZIP — archive with one .csv per table",
                            "json": "JSON — single .json file (or encrypted .json.zip)",
                        },
                        value="csv",
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    ui.label(
                        "WARNING :"
                    ).classes("text-sm font-bold text-[#EF4444]")

                    ui.label(text="This will REPLACE ALL existing data!").classes(
                        "close"
                    )

                    file_path_input = ui.input(
                        label="PATH TO FILE :"
                    ).classes("w-full text-sm yellow-label")

                    def update_path_label() -> None:
                        """Adapts the path input to the selected format."""
                        if format_radio.value == "csv":
                            file_path_input._props["label"] = "ZIP File Path"
                        else:
                            file_path_input._props["label"] = "JSON File Path"
                        file_path_input.update()

                    format_radio.on_value_change(update_path_label)

                    encrypt_checkbox = ui.checkbox(
                        "ZIP is encrypted (requires password)"
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    password_input = ui.input(
                        label="ENTER PASSWORD :",
                        password=True,
                    ).classes("w-full yellow-label text-sm")

                    password_input.bind_visibility_from(
                        encrypt_checkbox,
                        "value",
                    )

                    def do_import() -> None:
                        # ----- Path validation -----
                        path = file_path_input.value.strip("\"'").strip()

                        if not path:
                            ui.notify(
                                "Please enter file path.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        if not Path(path).exists():
                            ui.notify(
                                f"File at '{path}' not found.",
                                type="negative",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        # ----- Extension sanity check -----
                        suffix = Path(path).suffix.lower()

                        if format_radio.value == "csv" and suffix != ".zip":
                            ui.notify(
                                "Selected CSV import, but the file is "
                                "not a ZIP archive.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        if format_radio.value == "json" and suffix not in (
                            ".json", ".zip"
                        ):
                            ui.notify(
                                "Selected JSON import, but the file is "
                                "neither a JSON nor a ZIP file.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        pwd = (
                            password_input.value
                            if encrypt_checkbox.value
                            else None
                        )

                        if encrypt_checkbox.value and not pwd:
                            ui.notify(
                                "Please enter the password to decrypt "
                                "the file.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        dialog.close()

                        # ----- Run the selected import -----
                        if format_radio.value == "csv":
                            import_vector_from_csv(path, password=pwd)
                        else:
                            import_vector_from_json(path, password=pwd)

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent",).props("flat"
                        ).classes("text-[var(--vsp-blue)]")

                        ui.button(
                            "Import Now",
                            on_click=do_import,
                            color="var(--vsp-blue)").props("push"
                        ).classes("text-[var(--vsp-white)]")

                dialog.open()

            # ----- DELETE ALL Button -----
            def open_delete_all_dialog() -> None:
                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):
                    ui.label("Delete All Data?").classes(
                        "mb-3 text-lg font-bold text-[var(--vsp-blue)]"
                    )

                    ui.label(
                        "Are you sure you want to delete all case "
                        "data for this case? This CANNOT be undone!"
                    ).classes("mb-3 text-base text-[var(--vsp-gray)]")

                    # ----- User verification of destructive activity -----
                    affirm_checkbox = ui.checkbox(
                        "I understand the current data cannot be recovered.",
                        value=False,
                    ).classes("mb-3 text-base text-[var(--vsp-gray)]")

                    affirm_input = (
                        ui.input(
                            label="AFFIRM BY TYPING 'DELETE' BELOW",
                            password=False,
                    ).classes("w-full yellow-label mb-3"))

                    affirm_input.bind_visibility_from(
                        affirm_checkbox,
                        "value",
                    )

                    def do_delete() -> None:
                        if not affirm_checkbox.value:
                            ui.notify(
                                "Is it really that much trouble to click "
                                "one simple box?  Let's try this again.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        if affirm_input.value != "DELETE":
                            ui.notify(
                                "Seriously, how difficult is it to type "
                                "the word 'DELETE'?  You absolute noob!",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        affirm = (
                            affirm_input.value
                            if affirm_checkbox.value
                            else None
                        )

                        if affirm_checkbox.value and not affirm:
                            ui.notify(
                                "Please indicate you understand...",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        dialog.close()
                        delete_all_data()

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent").props("flat"
                        ).classes("text-[var(--vsp-blue)]")

                        ui.button(
                            "Delete all data",
                            on_click=do_delete,
                            color="#EF4444").props("push"
                        ).classes("text-[var(--vsp-white)]")

                dialog.open()

            ui.button(
                "📤 EXPORT CASE DATA",
                on_click=open_export_dialog,
                color="#379161").props("push"
            ).classes("w-56 py-3 text-[var(--vsp-white)]")

            ui.button(
                "📥 IMPORT CASE DATA",
                on_click=open_import_dialog,
                color="#379161").props("push"
            ).classes("w-56 py-3 text-[var(--vsp-white)]")

            ui.button(
                "DELETE ALL DATA",
                on_click=open_delete_all_dialog,
                color="#EF4444").props("push"
            ).classes("w-56 py-3 text-[var(--vsp-white)]")


def build_login_home() -> None:
    """Login page for unauthenticated users."""

    with ui.column().classes("items-center w-full mt-12"):

        ui.image(
            "/static/novadc_icac.png",
        ).classes("w-[150px] h-[150px] mb-4")

        ui.label(
            "-- V·E·C·T·O·R --"
        ).classes("text-3xl font-bold tracking-widest mb-6")

        ui.label(
            "The Virginia Evidence Collection, Tracking, "
            "Organization, & Reporting Program"
        ).classes("text-base text-gray-400 text-center max-w-xl mb-2")

        ui.label(
            "Please log in below"
        ).classes("text-lg mb-6")

        username_input = ui.input(
            label="Username"
        ).classes("w-full max-w-xs")

        username_input.props("autofocus")

        password_input = ui.input(
            label="Password",
            password=True,
            password_toggle_button=True,
        ).classes("w-full max-w-xs")

        def attempt_login() -> None:
            from models import Users

            entered_user = username_input.value.strip()
            entered_pass = password_input.value

            if not entered_user or not entered_pass:
                ui.notify(
                    "Both a username and password are required.",
                    type="warning",
                    timeout=0,
                    position="center",
                    close_button="OK",
                )
                return

            with get_users_session() as session:
                user = (
                    session.query(Users)
                    .filter_by(
                        USERNAME=entered_user,
                        ISACTIVE=True,
                    )
                    .first()
                )

                if user and user.check_password_correction(entered_pass):
                    from nicegui import app
                    app.storage.user["authenticated"] = True
                    app.storage.user["USERNAME"] = user.USERNAME
                    app.storage.user["ISADMIN"] = user.ISADMIN
                    app.storage.user["session_generation"] = (
                        app.storage.general.get("session_generation", 0)
                    )

                    if user.MUSTCHANGEPASSWORD:
                        ui.navigate.to("/change-password")
                    else:
                        ui.notify(
                            f"Welcome, {user.USERNAME}!",
                            timeout=4000,
                            position="bottom",
                            close_button="OK",
                        )
                        ui.navigate.to("/")
                else:
                    ui.notify(
                        "Invalid username or password.",
                        type="warning",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )
                    password_input.value = ""

        # Submit on Enter key
        password_input.on("keydown.enter", attempt_login)

        ui.button(
            "Login",
            on_click=attempt_login).props("push"
        ).classes("mt-4 px-8 py-3")


# ----- About Page -----
@ui.page("/about")
def about_page() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("items-center w-full mt-8"):

        ui.label("About V·E·C·T·O·R").classes("text-2xl font-bold mb-6")

        with ui.card().classes("p-6"):
            ui.label(f"Version  :  {Config.version}").classes("mb-2")
            ui.label(f"Author  :  {Config.author}").classes("mb-2")
            ui.label(f"Department  :  {Config.dept}").classes("mb-2")
            ui.label(f"URL : {Config.url}").classes("mb-2")
            ui.label(f"Last Updated  :  {Config.updated}").classes("mb-2")


# ----- Help Page -----
@ui.page("/help")
def help_page() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):
        with ui.column().classes("items-center w-full mt-8 max-w-3xl"):

            ui.label(
                "Help"
            ).classes("text-2xl font-bold mb-6")

            with ui.card().classes("p-6"):

                ui.markdown("""
### V·E·C·T·O·R Help Documentation

---

This application helps you manage evidence collection,
tracking, organization, and reporting for law
enforcement cases.

#### Quick Start

1.&ensp;**Start New Case**&ensp;→&ensp;Begin a fresh case file\n
2.&ensp;**Add Agent**&ensp;→&ensp;Register agents who will work on cases\n
3.&ensp;**Add Room**&ensp;→&ensp;Define rooms at search location\n
4.&ensp;**Add Evidence**&ensp;→&ensp;Record evidence items\n
5.&ensp;**Add Person**&ensp;→&ensp;Document suspects/witnesses\n
6.&ensp;**Add Notes**&ensp;→&ensp;Write case notes\n
7.&ensp;**Add Files**&ensp;→&ensp;Upload files to the case database\n

#### Navigation

Use the top menu to access different sections:\n
1.&ensp;**Case Info**&ensp;→&ensp;View/edit case details\n
2.&ensp;**Agents**&ensp;→&ensp;Manage agent roster\n
3.&ensp;**Rooms**&ensp;→&ensp;Manage defined rooms\n
4.&ensp;**Evidence**&ensp;→&ensp;Track evidence information\n
5.&ensp;**People**&ensp;→&ensp;Document persons of interest\n
6.&ensp;**Notes**&ensp;→&ensp;Write case documentation\n
7.&ensp;**Files**&ensp;→&ensp;Upload a file to case\n
8.&ensp;**Reports**&ensp;→&ensp;Print various reports\n
"""
                ).classes("text-sm")


# ----- Confirm New Case Handler -----
def confirm_new_case_handler() -> None:
    """Called when user initiates a NEW CASE.

    Prompts for confirmation if a case already exists, then clears data.
    """

    if has_active_case():
        # Show warning dialog
        with ui.dialog() as warn_dialog, ui.card().classes("max-w-md p-6"):

            ui.label(
                "⚠️ New Case Warning"
            ).classes("text-red-400 text-lg font-bold mb-2")

            ui.label(
                "The existing case will be REMOVED and all associated data "
                "(agents, rooms, evidence, persons, notes, and files) WILL "
                "BE DELETED."
            ).classes("text-sm mb-4")

            ui.label(
                "This action cannot be undone.  Please export the current "
                "case data before proceeding if you need to preserve it."
            ).classes("mb-4 text-sm")

            with ui.row().classes("w-full justify-end gap-2"):

                ui.button("Cancel", on_click=warn_dialog.close).props("flat")

                def on_proceed():
                    warn_dialog.close()
                    clear_all_case_data()

                ui.button(
                    "Proceed (Delete All Data)",
                    on_click=lambda: on_proceed(),
                    color="#EF4444").props("push"
                ).classes("text-[var(--vsp-white)]")

        warn_dialog.open()
    else:
        ui.navigate.to("/cases")


@ui.page("/logout")
def logout_page() -> None:
    """Logs out the current user."""
    from nicegui import app

    app.storage.user["authenticated"] = False
    app.storage.user["USERNAME"] = ""
    app.storage.user["ISADMIN"] = False

    ui.notify(
        "You have been logged out successfully.",
        timeout=4000,
        position="bottom",
        close_button="OK",
    )

    ui.navigate.to("/")


@ui.page("/shutdown")
def shutdown_page() -> None:
    """Shuts down the application."""
    from nicegui import app

    app.storage.user["authenticated"] = False
    app.storage.user["USERNAME"] = ""
    app.storage.user["ISADMIN"] = False

    ui.notify("Shutting down...", type="positive", timeout=2000)

    app.shutdown()
    ui.run(reload=False)
