#!/usr/bin/env python3

"""
home_page.py

Handles:
    /                →   Home/Login page
    /about           →   About page
    /help            →   Help page
    /make_new_case   →   Clear all data (dangerous!)
"""

from datetime import datetime
from nicegui import ui
import time
from pathlib import Path

from import_export import (
    export_database,
    export_database_json,
    import_database,
    import_database_json,
    looks_like_json_export,
)
from auth import (
    clear_login_failures,
    failure_delay_seconds,
    get_current_user_name,
    get_is_admin,
    is_authenticated,
    lockout_seconds_remaining,
    record_login_failure,
    sign_in,
    sign_out,
    LOCK_AFTER_FAILURES,
    LOCKOUT_MINUTES,
)
from models import get_session, get_users_session, record_audit
from navbar import build_navbar
from program.config import Config
from utils import delete_all_data


# ----- Home Page Registration -----
@ui.page("/")
@ui.page("/home")
def home():
    """Home/login page — shows menu if authenticated, login
    form otherwise.
    """
    authenticated = is_authenticated()

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    if authenticated:
        build_authenticated_home()
    else:
        build_login_home()


def build_authenticated_home():
    """Main menu shown to logged-in users."""

    with ui.column().classes("items-center w-full mt-8 py-2"):

        # ----- Page Title and Header -----

        ui.image(
            "/static/novadc_icac.png",
        ).classes("w-[150px] h-[150px] mb-2")

        ui.label(
            "V·E·C·T·O·R Home"
        ).classes("text-2xl font-bold text-center mx-2")

        ui.label(
            "The Virginia Evidence Collection, Tracking, "
            "Organization, & Reporting Program"
        ).classes("text-base text-gray-400 text-center max-w-xl")

    with ui.row().classes(
        "flex justify-center items-center gap-6 w-full"):

        ui.label(
            "Main Menu"
        ).classes("text-xl items-center font-semibold py-1")

    # ----- Action Buttons ROW 1: Start New Case | Add Agent | Add Room -----

    with ui.row().classes(
        "flex justify-center items-center gap-6 py-1 w-full"):

        ui.button(
            "Start New Case",
            on_click=lambda: ui.navigate.to("/cases"),
            color="#1C69A8",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

        ui.button(
            "Add Agent",
            on_click=lambda: ui.navigate.to("/agents"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

        ui.button(
            "Add Room",
            on_click=lambda: ui.navigate.to("/rooms"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

    # ----- Action Buttons ROW 2: Add Evidence | Add Person | Add Note -----

    with ui.row().classes(
        "flex justify-center items-center gap-6 py-1 w-full"):

        ui.button(
            "Add Evidence",
            on_click=lambda: ui.navigate.to("/evidence"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

        ui.button(
            "Add Person",
            on_click=lambda: ui.navigate.to("/persons"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

        ui.button(
            "Add Note",
            on_click=lambda: ui.navigate.to("/notes"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

    # ----- Action Buttons ROW 3: Add File | Useful Links -----

    with ui.row().classes(
        "flex justify-center items-center gap-6 py-1 w-full"):

        ui.button(
            "Add File",
            on_click=lambda: ui.navigate.to("/uploads"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

        ui.button(
            "Useful Links",
            on_click=lambda: ui.navigate.to("/links"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

        ui.button(
            "Reports",
            on_click=lambda: ui.navigate.to("/reports"),
            color="var(--vsp-blue)",
        ).props("unelevated").classes(
            "flex-shrink-0 min-w-56 py-3 text-[var(--vsp-white)]"
        )

    # ----- Import / Export ROW -----

    # ui.separator().classes("my-2")

    with ui.column().classes("items-center w-full py-2"):

        with ui.row().classes(
                "flex justify-center items-center gap-6 w-full"):

            ui.label(
                "Data Management"
            ).classes("text-lg font-bold py-1")

        # ----- Row to hold the Data Management buttons -----
        with ui.row().classes("flex justify-center items-center gap-6 w-full"):

            # ----- EXPORT Button -----
            def open_export_dialog():

                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

                    ui.label("Export All Data...").classes(
                        "text-lg font-bold mb-1 text-[var(--vsp-blue)]"
                    )

                    ui.label(
                        "Saves the whole case -- every table, every "
                        "attachment, and the audit trail -- to your "
                        "Desktop."
                    ).classes("mb-2 text-base text-[var(--vsp-gray)]")

                    export_format = ui.radio(
                        {
                            "zip": "ZIP archive of CSV files  (spreadsheets)",
                            "json": "Single JSON file  (other tools)",
                        },
                        value="zip",
                    ).props("inline=false").classes("mb-1")

                    ui.label(
                        "CSV opens in Excel. JSON is one self-contained "
                        "file with the attachments embedded, for handing "
                        "the case to another system."
                    ).classes("mb-2 text-xs text-gray-400")

                    ui.label("Named '<case-number>_<datetime>_saved_results'"
                             ).classes(
                        "mb-1 text-xs text-[var(--vsp-gray)]"
                    )

                    # ----- Password option -----

                    encrypt_checkbox = ui.checkbox(
                        "Encrypt with password (AES-256)"
                    ).classes("mb-1 mt-1 text-base text-[var(--vsp-gray)]")

                    password_input = ui.input(
                        label="Password",
                        password=True,
                    ).classes("w-full")

                    password_input.bind_visibility_from(
                        encrypt_checkbox,
                        "value",
                    )

                    def do_export():
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
                        if export_format.value == "json":
                            export_database_json(password=pwd)
                        else:
                            export_database(password=pwd)

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent",
                        ).props("flat").classes("text-[var(--vsp-blue)]")

                        ui.button(
                            "Export Now",
                            on_click=do_export,
                            color="var(--vsp-blue)",
                        ).props("unelevated").classes(
                            "text-[var(--vsp-white)]"
                        )

                dialog.open()

            # ----- IMPORT Button -----
            def open_import_dialog():

                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

                    ui.label("Import Data...").classes(
                        "text-lg font-bold mb-1 text-[var(--vsp-blue)]"
                    )

                    ui.label(
                        "Select a file previously exported from VECTOR -- "
                        "either the ZIP archive or the JSON file. The "
                        "format is detected from the file itself."
                    ).classes("mb-1 text-base text-[var(--vsp-gray)]")

                    ui.label("WARNING :").classes("mb-1 text-base text-[var(--vsp-blue)]")

                    ui.label("This will REPLACE all existing data!").classes(
                        "mb-1 text-base text-[var(--vsp-gray)]"
                    )

                    zip_path_input = ui.input(
                        label="Path to the exported file",
                        placeholder=r"...-1234_saved_results.zip",
                    ).classes("w-full")

                    encrypt_checkbox = ui.checkbox(
                        "ZIP is encrypted (requires password)"
                    ).classes("mb-1 mt-1 text-base text-[var(--vsp-gray)]")

                    password_input = ui.input(
                        label="Password",
                        password=True,
                    ).classes("w-full")

                    password_input.bind_visibility_from(
                        encrypt_checkbox,
                        "value",
                    )

                    def do_import():
                        path = zip_path_input.value.strip("\"'")
                        if not path:
                            ui.notify(
                                "Please enter file path to ZIP file.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        if not Path(path).exists():
                            ui.notify(
                                "ZIP file not found.",
                                type="negative",
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
                                "Please enter the password.",
                                type="warning",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        dialog.close()

                        # A .json, or a .zip holding one, goes through
                        # the JSON reader; the CSV archive is also a
                        # .zip, so the contents decide, not the suffix
                        # alone.
                        if looks_like_json_export(path):
                            import_database_json(path, password=pwd)
                        else:
                            import_database(path, password=pwd)

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent",
                        ).props("flat").classes("text-[var(--vsp-blue)]")

                        ui.button(
                            "Import Now",
                            on_click=do_import,
                            color="var(--vsp-blue)",
                        ).props(
                            "unelevated warning"
                        ).classes("text-[var(--vsp-white)]")

                dialog.open()

            # ----- DELETE ALL Button -----

            def open_delete_all_dialog():

                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

                    ui.label("Delete All Data?").classes(
                        "mb-3 text-lg font-bold text-[var(--vsp-blue)]"
                    )

                    ui.label(
                        "Are you sure you want to delete all case "
                        "data for this case? This CANNOT be undone!"
                    ).classes(
                        "mb-3 text-base text-[var(--vsp-gray)]"
                    )

                    # ----- User verification of destructive activity -----

                    affirm_checkbox = ui.checkbox(
                        "I understand the current data cannot be recovered.",
                        value=False,
                    ).classes("mb-3 text-base text-[var(--vsp-gray)]")

                    affirm_input = (
                        ui.input(
                            label="Affirm by typing 'DELETE' on the line below",
                            password=False,
                        )
                        .classes("w-full mb-3")
                    )

                    affirm_input.bind_visibility_from(
                        affirm_checkbox,
                        "value",
                    )

                    def do_delete():
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
                        try:
                            delete_all_data()
                        except Exception as err:
                            ui.notify(
                                f"Nothing was deleted — the database was "
                                f"rolled back. → {err}",
                                type="negative",
                                timeout=0,
                                position="center",
                                close_button="OK",
                            )
                            return

                        ui.notify(
                            "All case data has been deleted.",
                            timeout=4000,
                            position="bottom",
                            close_button="OK",
                        )
                        ui.navigate.to("/")

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent",
                        ).props("flat").classes("text-[var(--vsp-blue)]")

                        ui.button(
                            "Delete all data",
                            on_click=do_delete,
                            color="#EF4444",
                        ).props("unelevated").classes("text-[var(--vsp-white)]")

                dialog.open()

            ui.button(
                "📤 Export All Data",
                on_click=open_export_dialog,
                color="#2AA63E",
            ).props("unelevated").classes("w-56 py-3 text-[var(--vsp-white)]")

            ui.button(
                "📥 Import Data",
                on_click=open_import_dialog,
                color="#2AA63E",
            ).props("unelevated").classes("w-56 py-3 text-[var(--vsp-white)]")

            ui.button(
                "Delete All Data",
                on_click=open_delete_all_dialog,
                color="#EF4444",
            ).props("unelevated").classes("w-56 py-3 text-[var(--vsp-white)]")


def build_login_home():
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

        def attempt_login():
            # Wire this to your Users model authentication
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

            # Refuse before touching the database, so a locked account
            # costs an attacker nothing to discover and gains them
            # nothing either.
            locked_for = lockout_seconds_remaining(entered_user)
            if locked_for:
                minutes = max(1, round(locked_for / 60))
                ui.notify(
                    f"Too many failed attempts. This account is locked "
                    f"for about {minutes} more minute"
                    f"{'s' if minutes != 1 else ''}.\n"
                    "An administrator can clear the lock from the Admin "
                    "Panel.",
                    type="negative",
                    timeout=0,
                    position="center",
                    close_button="OK",
                )
                password_input.value = ""
                return

            with get_users_session() as session:
                user = (
                    session.query(Users)
                    .filter_by(
                        user_name=entered_user,
                        is_active=True,
                    )
                    .first()
                )

                if user and user.check_password_correction(entered_pass):
                    with get_session() as audit_session:
                        record_audit(
                            audit_session,
                            action="LOGIN",
                            table_name="users",
                            row_pk=user.id,
                            summary=user.user_name,
                            actor=user.user_name,
                        )

                    clear_login_failures(entered_user)
                    sign_in(user.user_name, user.is_admin)

                    if user.must_change_password:
                        ui.navigate.to("/change-password")
                    else:
                        ui.notify(
                            f"Welcome, {user.user_name}!",
                            timeout=4000,
                            position="bottom",
                            close_button="OK",
                        )
                        ui.navigate.to("/")
                else:
                    # A pause that grows with the failure count. Slow
                    # enough to make scripted guessing impractical,
                    # short enough not to punish a mistype.
                    delay = failure_delay_seconds(entered_user)
                    if delay:
                        time.sleep(delay)

                    failures = record_login_failure(entered_user)
                    remaining = LOCK_AFTER_FAILURES - failures

                    with get_session() as audit_session:
                        record_audit(
                            audit_session,
                            action="LOGIN_FAILED",
                            table_name="users",
                            summary=(
                                f"{entered_user} "
                                f"(failure {failures})"
                            ),
                            actor=entered_user or "unknown",
                        )

                    if failures >= LOCK_AFTER_FAILURES:
                        message = (
                            "Too many failed attempts. This account is "
                            f"now locked for {LOCKOUT_MINUTES} minutes."
                        )
                    elif remaining <= 3:
                        message = (
                            "Invalid username or password.\n"
                            f"{remaining} attempt"
                            f"{'s' if remaining != 1 else ''} left before "
                            "this account is locked."
                        )
                    else:
                        message = "Invalid username or password."

                    ui.notify(
                        message,
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
            on_click=attempt_login,
        ).props("unelevated").classes("mt-4 px-8 py-3")


# ----- About Page -----
@ui.page("/about")
def about_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("items-center w-full mt-8"):

        ui.label(
            "About V·E·C·T·O·R"
        ).classes("text-2xl font-bold mb-6")

        with ui.card().classes("p-6"):

            ui.label(f"Version  :  {Config.version}").classes("mb-2")
            ui.label(f"Author  :  {Config.author}").classes("mb-2")
            ui.label(f"Department  :  {Config.dept}").classes("mb-2")
            ui.label(f"URL : {Config.url}").classes("mb-2")
            ui.label(f"Last Updated  :  {Config.updated}").classes("mb-2")


# ----- Help Page -----
@ui.page("/help")
def help_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
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
def confirm_new_case_handler():
    """Called when user clicks "Make New Case File".

    Clears ALL data from all tables (destructive operation!).
    """
    with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

        ui.label(
            "⚠️ WARNING: Delete All Data"
        ).classes("text-red-400 text-lg font-bold mb-2")

        ui.label(
            "This will DELETE ALL DATA from all database tables:\n"
            "- Case\n- Agents\n- Rooms\n- Evidence\n- People\n"
            "- Notes\n- Uploaded files\n\n"
            "Export the case first if you need to keep it. "
            "This action CANNOT be undone. Are you absolutely sure?"
        ).classes("text-sm mb-4 whitespace-pre-line")

        with ui.row().classes("w-full justify-end gap-2"):

            ui.button(
                "Cancel",
                on_click=dialog.close,
            ).props("flat")

            def on_confirm_delete_all():
                # Delegates to delete_all_data() rather than repeating the
                # table list. The inline version here cleared six tables
                # and omitted UploadedFiles, so starting a new case left
                # the previous subject's photographs and documents in the
                # database, to be swept into the next case's export.
                try:
                    delete_all_data()
                    ui.notify(
                        "Data in the app database tables has been deleted.",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )
                    ui.navigate.to("/")
                except Exception as err:
                    ui.notify(
                        f"Nothing was deleted — the database was rolled "
                        f"back. → {err}",
                        type="negative",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )
                finally:
                    dialog.close()

            ui.button(
                "DELETE ALL",
                on_click=on_confirm_delete_all,
            ).props("negative unelevated")

    dialog.open()


@ui.page("/logout")
def logout_page():
    """Logs out the current user."""
    from nicegui import app

    sign_out()

    ui.notify(
        "You have been logged out successfully.",
        timeout=4000,
        position="bottom",
        close_button="OK",
    )

    ui.navigate.to("/")


@ui.page("/shutdown")
def shutdown_page():
    """Shuts down the application. Admins only.

    Without these checks any unauthenticated request -- from any device
    that can reach the port -- terminates evidence logging.
    """
    from nicegui import app

    if not is_authenticated() or not get_is_admin():
        ui.navigate.to("/")
        return

    sign_out()

    ui.notify("Shutting down...", type="positive", timeout=2000)

    app.shutdown()
