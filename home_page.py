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

from nicegui import ui
import time

from failures import explain, log
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
from models import (
    get_session,
    get_users_session,
    has_active_case,
    record_audit,
)
from navbar import build_navbar, unit_logo
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
    "classes": "w-75 p-6 hover-border-white",
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
                ).props("push").classes("w-75 p-6 hover-border-white")


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

        username_input = ui.input(label="Username").classes("w-full max-w-xs")

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
                    with get_session() as audit_session:
                        record_audit(
                            audit_session,
                            action="LOGIN",
                            table_name="users",
                            row_pk=user.Z_PK,
                            summary=user.USERNAME,
                            actor=user.USERNAME,
                        )

                    clear_login_failures(entered_user)
                    sign_in(user.USERNAME, user.ISADMIN)

                    if user.MUSTCHANGEPASSWORD:
                        ui.navigate.to("/change-password")
                    else:
                        ui.notify(
                            f"Welcome, {user.USERNAME}!",
                            timeout=CONFIRM_TIMEOUT,
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

            ui.label(f"Version  :  {Config.version}").classes("mb-2")
            ui.label(f"Authors  :  {Config.authors}").classes("mb-2")
            ui.label(f"Department  :  {Config.dept}").classes("mb-2")
            ui.label(f"URL : {Config.url}").classes("mb-2")
            ui.label(f"Last Updated  :  {Config.updated}").classes("mb-2")


# ----- Help Page -----
# Names in bold are the buttons and menus as they appear on screen. The
# test suite checks each one still exists, so renaming a button fails a
# test instead of leaving the help out of date.
HELP_TEXT = f"""
#### Working a search

VECTOR holds one case at a time. Work through the pages in this order —
each one feeds the next. On a phone or a small tablet, the pages are under
the menu button (three lines) at the top left.

1. **Start New Case** on the Home page opens the Case page. Enter the case
   number, location, jurisdiction and start time (`MM-DD-YYYY HH:MM`) — or
   press **Fill with current date/time** — then press **Open New Case**.
   The case number now shows at the top of every page, and the Case page
   shows the open case in place of the form.
2. **Agents** — everyone on site.
3. **Rooms** — the next room letter is filled in for you.
4. **Evidence** — the next item number is filled in for you, and rooms and
   agents are picked from the lists you made. Delete an item that was not
   seized after all, and the items after it move down one number, so the
   list never skips.
5. **People** — suspects and others present.
6. **Notes** — timestamped, signed with your account, and listed in the
   order they were written.
7. **Files** — photographs and documents. Each file is fingerprinted
   (SHA-256) when it is added, so a later change to it can be detected.
   VECTOR reads what a file is from its contents, not its name: images,
   videos, documents and archives are accepted, and a program renamed to
   look like a photo is refused. Every download is recorded in the audit
   trail.
8. **Reports** — eight printable lists, including the inventory used as
   the return copy. **Print Report** opens the report in its own window,
   with **Print Report** and **Close** in a bar across the top; the bar
   is not printed. If the case is missing a detail a report needs, the
   page says which, and if it has no end time yet the page offers to fill
   it in from this machine's clock. **Print Room List** waits until every
   room has both agents. Switches on the Reports page add the date and
   time each report was printed, and hide agents' phone numbers and
   emails on the Agent List.

Until a case is open, the top bar shows **No Active Case** and the other
pages will not save.

Every table has a search box above it. Type part of a name, a room, an
item number or a description and the list narrows to the rows that hold
it; clear the box to see them all again.

Times follow this machine's clock and time zone. The times VECTOR records
itself — notes, entries, uploads — carry their offset from UTC, such as
`UTC-04:00`.

#### Getting the case out

- **Export Case Data** on the Home page downloads the whole case to the
  device you are using. CSV opens in Excel; JSON is a single file for other
  systems. Tick the encryption box to protect the file with a password — a
  forgotten password cannot be recovered.
- **Import Case Data** replaces the case with a file exported earlier.
  Choose the .zip or .json file; if it was exported with a password,
  VECTOR asks for it.
- **Delete All Data** empties the case; accounts and the audit trail are
  kept. **Start New Case** does the same, after a warning, when a case is
  already open. Neither can be undone, so export first.

#### Accounts

- Sign out from the **Welcome** menu at the top right, with **Logout**.
- Administrators also see **Admin Panel** there, to add accounts, reset
  passwords, clear a sign-in lock and decide whether other devices may
  reach this machine; **Audit Trail**, a record of every
  change, sign-in and download; and **Shutdown**, which stops VECTOR for
  everyone.
- After {LOCK_AFTER_FAILURES} wrong passwords an account is locked for
  {LOCKOUT_MINUTES} minutes. An administrator can clear the lock sooner.
- Passwords an administrator issues are shown once. Write them down before
  closing the message.
- A device nobody has touched for {Config.SESSION_IDLE_MINUTES} minutes
  signs out on its own, so a tablet left at a scene does not stay open on
  the case. A warning appears first, with **Stay signed in** on it.
  Records already saved are kept; a form filled in but not yet saved is
  lost with the page, so save before walking away.

#### Other pages

- **Connect a Device** under **Help** — the address to type on a tablet
  or a second laptop, and whether VECTOR is reachable from them at all.
- **Tools** (or **Useful Links** on the Home page) — links to forensic
  software, DFIR and OSINT resources.
- **Help** → **About App** — the version, and who wrote VECTOR.
"""


@ui.page("/help")
def help_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):
        with ui.column().classes("items-center w-full mt-8 max-w-3xl"):
            ui.label("Help").classes("text-2xl font-bold mb-6")
            with ui.card().classes("p-6 w-full"):
                ui.markdown(HELP_TEXT).classes("text-sm")


# ----- Confirm New Case Handler -----
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
                on_click=warn_dialog.close
            ).props("flat").classes("p-3 hover-border-blue")

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

    sign_out()

    ui.notify(
        "Shutting down...",
        type="positive",
        timeout=CONFIRM_TIMEOUT,
        position="center",
    )

    app.shutdown()
