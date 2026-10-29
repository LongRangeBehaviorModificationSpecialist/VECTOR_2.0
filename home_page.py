#!/usr/bin/env python3

"""
home_page.py

Handles:
    /                →   Home/Login page
    /about           →   About page
    /help            →   Help page
    /logout          →   Sign out
    /shutdown        →   Stop the app (admins only)
"""

import asyncio

from nicegui import run, ui

from failures import explain, log
from auth import (
    clear_login_failures,
    failure_delay_seconds,
    get_current_user_name,
    get_is_admin,
    is_authenticated,
    lockout_seconds_remaining,
    record_login_failure,
    require_session,
    sign_in,
    sign_out,
    signed_in_with_temporary_password,
    session_ended_notice,
    LOCK_AFTER_FAILURES,
    LOCKOUT_MINUTES,
)
from models import (
    get_session,
    get_users_session,
    has_active_case,
    password_matches,
    record_account_event,
    record_audit,
)
from navbar import build_navbar, unit_logo
from parts.case_summary import case_overview
from parts.help_page import build_help_page
from parts.case_transfer import (
    open_delete_all_dialog,
    open_export_dialog,
    open_import_dialog,
)
from program.config import Config
from utils import (
    CONFIRM_TIMEOUT,
    WARN_TIMEOUT,
    ZERO_TIMEOUT,
    delete_all_data,
)


style = {
    "color": "var(--vsp-blue)",
    "props": "push",
    "classes": "w-70 p-6 hover-border-white",
}

home_page_buttons = {
    "0": {
        "text": "Add Agent",
        "page_url": "/agents",
    },
    "1": {
        "text": "Add Room",
        "page_url": "/rooms",
        },
    "2": {
        "text": "Add Evidence",
        "page_url": "/evidence",
        },
    "3": {
        "text": "Add Person",
        "page_url": "/persons",
        },
    "4": {
        "text": "Add Note",
        "page_url": "/notes",
        },
    "5": {
        "text": "Add File",
        "page_url": "/uploads",
        },
    "6": {
        "text": "Useful Links",
        "page_url": "/links",
        },
    "7": {
        "text": "Reports",
        "page_url": "/reports",
        },
}


# ----- Home Page Registration -----
@ui.page("/")
@ui.page("/home")
def home():
    """Home/login page — shows menu if authenticated, login
    form otherwise.
    """
    # A temporary password opens Change Password and nothing else.
    if signed_in_with_temporary_password():
        ui.navigate.to("/change-password")
        return

    authenticated = is_authenticated()

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    if authenticated:
        build_authenticated_home()
    else:
        build_login_home()


def build_authenticated_home():
    """Main menu shown to logged-in users."""

    with ui.column().classes("items-center w-full mt-8 py-2"):

        # ----- Page Title and Header -----

        unit_logo("novadc_icac.png", "w-[150px] h-[150px] mb-2")

        ui.label(
            "V·E·C·T·O·R Home"
        ).classes("text-2xl font-bold text-center mx-2")

        ui.label(
            "The Virginia Evidence Collection, Tracking, "
            "Organization, & Reporting Program"
        ).classes("text-base text-gray-400 text-center max-w-xl")

    # ----- How much is recorded, and what to check before leaving -----
    case_overview()

    with ui.row().classes(
        "flex justify-center items-center gap-6 w-full"):

        ui.label(
            "Main Menu"
        ).classes("text-xl items-center font-semibold py-1")

    # ----- Action Buttons ROW 1: Start New Case | Add Agent | Add Room -----

    with ui.row().classes(
        "flex justify-center items-center gap-8 py-1 w-full"):

        ui.button(
            "Start New Case",
            on_click=confirm_new_case_handler,
            color=style["color"],
        ).props(style["props"]).classes(style["classes"])

        for k, v in list(home_page_buttons.items())[0:2]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: ui.navigate.to(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])


    # ----- Action Buttons ROW 2: Add Evidence | Add Person | Add Note -----

    with ui.row().classes(
        "flex justify-center items-center gap-8 py-1 w-full"):

        for k, v in list(home_page_buttons.items())[2:5]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: ui.navigate.to(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])


    # ----- Action Buttons ROW 3: Add File | Useful Links -----

    with ui.row().classes(
        "flex justify-center items-center gap-8 py-1 w-full"):

        for k, v in list(home_page_buttons.items())[5:]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: ui.navigate.to(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])


    # ----- Import / Export ROW -----

    with ui.column().classes("items-center w-full py-2"):

        with ui.row().classes(
                "flex justify-center items-center gap-6 w-full"):

            ui.label(
                "Data Management"
            ).classes("text-lg font-bold py-1")

        # ----- Row to hold the Data Management buttons -----
        with ui.row().classes(
            "flex justify-center items-center gap-8 py-1 w-full"):

            action_buttons = {
                "0": {
                    "text":"📤 EXPORT CASE DATA",
                    "color": "#379161",
                    "command":open_export_dialog,
                },
                "1": {
                    "text":"📥 IMPORT CASE DATA",
                    "color": "#379161",
                    "command":open_import_dialog,
                },
                "2": {
                    "text":"DELETE ALL DATA",
                    "color": "#EF4444",
                    "command":open_delete_all_dialog,
                }
            }

            for _, v in action_buttons.items():
                ui.button(
                    v["text"],
                    on_click=v["command"],
                    color=v["color"],
                ).props("push").classes("w-70 p-6 hover-border-white")


def build_login_home():
    """Login page for unauthenticated users."""

    with ui.column().classes("items-center w-full mt-12"):

        unit_logo("novadc_icac.png", "w-[150px] h-[150px] mb-2")

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

        # A page whose session was ended -- by an administrator, by Sign
        # Everyone Out, by the password being changed on another device
        # -- comes here by itself, so say why.
        if session_ended_notice():
            ui.label(
                "This device was signed out. Sign in again to carry on."
            ).classes("text-sm text-[#F5B027] mb-4 text-center")

        username_input = ui.input(label="Username").classes("w-full max-w-xs")

        username_input.props("autofocus")

        password_input = ui.input(
            label="Password",
            password=True,
            password_toggle_button=True,
        ).classes("w-full max-w-xs")

        async def attempt_login():
            # Async so that the two slow parts of a sign-in -- the
            # password check, and the pause after repeated failures --
            # hold up this sign-in only. Done on VECTOR's own loop, as
            # they were, every connected device stopped while they ran.
            from models import Users

            entered_user = (username_input.value or "").strip()
            entered_pass = password_input.value or ""

            if not entered_user or not entered_pass:
                ui.notify(
                    "Both a username and password are required.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
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
                    f"for {minutes} more minute"
                    f"{'s' if minutes != 1 else ''}.\n"
                    "An administrator can clear the lock from the Admin "
                    "Panel.",
                    type="negative",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                password_input.value = ""
                return

            # What the check needs, read before the session closes.
            with get_users_session() as session:
                user = (
                    session.query(Users)
                    .filter_by(
                        USERNAME=entered_user,
                        ISACTIVE=True,
                    )
                    .first()
                )
                account = None if user is None else {
                    "Z_PK": user.Z_PK,
                    "USERNAME": user.USERNAME,
                    "ISADMIN": bool(user.ISADMIN),
                    "MUSTCHANGEPASSWORD": bool(user.MUSTCHANGEPASSWORD),
                    "PASSWORDHASH": user.PASSWORDHASH,
                }

            # bcrypt takes a quarter of a second by design. In a thread,
            # that quarter second is this sign-in's alone.
            correct = account is not None and await run.io_bound(
                password_matches,
                entered_pass,
                account["PASSWORDHASH"],
            )

            if correct:
                with get_session() as audit_session:
                    record_audit(
                        audit_session,
                        action="LOGIN",
                        table_name="users",
                        row_pk=account["Z_PK"],
                        summary=account["USERNAME"],
                        actor=account["USERNAME"],
                    )

                clear_login_failures(entered_user)
                sign_in(
                    account["USERNAME"],
                    account["ISADMIN"],
                    must_change_password=account["MUSTCHANGEPASSWORD"],
                )

                if account["MUSTCHANGEPASSWORD"]:
                    ui.navigate.to("/change-password")
                else:
                    ui.notify(
                        f"Welcome, {account['USERNAME']}!",
                        timeout=CONFIRM_TIMEOUT,
                        position="bottom",
                        close_button="OK",
                    )
                    ui.navigate.to("/")
                return

            # A pause that grows with the failure count. Slow enough to
            # make scripted guessing impractical, short enough not to
            # punish a mistype -- and awaited, so it pauses this sign-in
            # and not every device at the scene.
            delay = failure_delay_seconds(entered_user)
            if delay:
                await asyncio.sleep(delay)

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
                timeout=WARN_TIMEOUT,
                position="center",
                close_button="OK",
            )
            password_input.value = ""

        # Submit on Enter key
        password_input.on("keydown.enter", attempt_login)

        ui.button(
            "Login",
            on_click=attempt_login,
        ).props("push").classes("mt-4 px-8 p-3")


# ----- About Page -----
@ui.page("/about")
def about_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("items-center w-full mt-8"):

        ui.label(
            "About V·E·C·T·O·R"
        ).classes("text-2xl font-bold mb-6")

        with ui.card().classes("p-6"):

            ui.label(f"Version       :  {Config.version}").classes("mb-2")
            ui.label(f"Authors       :  {Config.authors}").classes("mb-2")
            ui.label(f"Department    :  {Config.dept}").classes("mb-2")
            ui.label(f"URL           :  {Config.url}").classes("mb-2")
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
    )

    build_help_page()


# ----- Confirm New Case Handler -----
@require_session
def confirm_new_case_handler() -> None:
    """Called when the user starts a new case.

    With no case open this goes straight to the Cases page. With one open
    it warns first, because the existing case and everything recorded
    against it are removed.
    """
    if not has_active_case():
        ui.navigate.to("/cases")
        return

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

            ui.button(
                "Cancel",
                on_click=warn_dialog.close,
            ).props("flat").classes("p-3 hover-border-blue")

            @require_session
            def on_proceed() -> None:
                # Through delete_all_data() rather than a table list of its
                # own. An earlier inline list here left out UploadedFiles,
                # so a new case inherited the last one's attachments; this
                # path also records the wipe in the audit trail.
                warn_dialog.close()
                try:
                    delete_all_data()
                except Exception as err:
                    log.exception("Start New Case could not clear the case")
                    ui.notify(
                        "Nothing was deleted, and the case is unchanged."
                        f"\n\n{explain(err)}",
                        multi_line=True,
                        type="warning",
                        timeout=ZERO_TIMEOUT,
                        position="center",
                        close_button="OK",
                    )
                    return

                ui.notify(
                    "Old case data cleared",
                    timeout=CONFIRM_TIMEOUT,
                    position="bottom",
                    close_button="OK",
                )
                ui.navigate.to("/cases")

            ui.button(
                "Delete All Data",
                on_click=on_proceed,
                color="#EF4444",
            ).props("push").classes("p-3 hover-border-white")

    warn_dialog.open()


@ui.page("/logout")
def logout_page():
    """Logs out the current user."""
    if is_authenticated() or signed_in_with_temporary_password():
        record_account_event(
            action="LOGOUT",
            table_name="(session)",
            summary="signed out",
            actor=get_current_user_name(),
        )
    sign_out()

    ui.notify(
        "You have been logged out successfully.",
        timeout=CONFIRM_TIMEOUT,
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

    record_account_event(
        action="SHUTDOWN",
        table_name="(application)",
        summary="VECTOR was shut down from the account menu",
        actor=get_current_user_name(),
    )
    sign_out()

    ui.notify(
        "Shutting down...",
        type="positive",
        timeout=CONFIRM_TIMEOUT,
        position="center",
    )

    app.shutdown()
