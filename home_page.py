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

from datetime import datetime
from nicegui import ui
import shutil
import time
from pathlib import Path

from failures import explain, log
from import_export import (
    ExportResult,
    export_vector_to_csv,
    export_vector_to_json,
    import_vector_from_csv,
    import_vector_from_json,
    looks_like_json_export,
    needs_password,
    new_staging_dir,
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
from models import (
    get_session,
    get_users_session,
    has_active_case,
    record_audit,
)
from navbar import build_navbar, unit_logo
from program.config import Config
from utils import delete_all_data, CONFIRM_TIMEOUT, WARN_TIMEOUT


style = {
    "color": "var(--vsp-blue)",
    "props": "push",
    "classes": "flex-shrink-0 min-w-56 py-3 hover-border-white"
}

home_page_buttons = {
    "0": {
        "text": "Start New Case",
        "action": "confirm_new_case_handler()",
    },
    "1": {
        "text": "Add Agent",
        "page_url": "/agents",
    },
    "2": {
        "text": "Add Room",
        "page_url": "/rooms",
        },
    "3": {
        "text": "Add Evidence",
        "page_url": "/evidence",
        },
    "4": {
        "text": "Add Person",
        "page_url": "/persons",
        },
    "5": {
        "text": "Add Note",
        "page_url": "/notes",
        },
    "6": {
        "text": "Add File",
        "page_url": "/uploads",
        },
    "7": {
        "text": "Useful Links",
        "page_url": "/links",
        },
    "8": {
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
            on_click=lambda: confirm_new_case_handler(),
            color="var(--vsp-blue)",
        ).props("push").classes(
            "flex-shrink-0 min-w-56 py-3 hover-border-white"
        )

        for k, v in list(home_page_buttons.items())[1:3]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: ui.navigate.to(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])


    # ----- Action Buttons ROW 2: Add Evidence | Add Person | Add Note -----

    with ui.row().classes(
        "flex justify-center items-center gap-6 py-1 w-full"):

        for k, v in list(home_page_buttons.items())[3:6]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: ui.navigate.to(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])


    # ----- Action Buttons ROW 3: Add File | Useful Links -----

    with ui.row().classes(
        "flex justify-center items-center gap-6 py-1 w-full"):

        for k, v in list(home_page_buttons.items())[6:]:
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
        with ui.row().classes("flex justify-center items-center gap-6 w-full"):

            # ----- EXPORT Button -----
            def open_export_dialog():

                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

                    ui.label(
                        "Export Data..."
                    ).classes("text-lg font-bold text-[var(--vsp-blue)]")

                    ui.label(
                        "Downloads the whole case -- every table, every "
                        "attachment, and the audit trail -- through your "
                        "browser, on whichever device you are using."
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    ui.label("The file will be named :").classes(
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

                    ui.label(
                        "CSV opens in Excel. JSON is one self-contained "
                        "file with the attachments embedded, for handing "
                        "the case to another system."
                    ).classes("text-xs text-gray-400")

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
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return

                        dialog.close()

                        # ----- Run the selected exports -----
                        # Each results file goes to the browser, so it
                        # arrives on the device the export was asked from.
                        results = []
                        if format_radio.value in ("csv", "both"):
                            result = export_vector_to_csv(password=pwd)
                            if result is not None:
                                results.append(result)

                        if format_radio.value in ("json", "both"):
                            result = export_vector_to_json(password=pwd)
                            if result is not None:
                                results.append(result)

                        # Pass each file path to the browser to it can be
                        # downloaded to a location choosen by the user.
                        for result in results:
                            ui.download.file(result.zip_path)

                        for result in results:
                            ui.notify(
                                result.message,
                                multi_line=True,
                                classes="multi-line-notification",
                                timeout=CONFIRM_TIMEOUT,
                                position="bottom",
                                close_button="OK",
                            )

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent",
                        ).props("flat").classes("hover-border-blue")

                        ui.button(
                            "Export Now",
                            on_click=do_export,
                            color="var(--vsp-blue)",
                        ).props("push").classes("hover-border-white")

                dialog.open()

            # ----- IMPORT Button -----
            def open_import_dialog():

                with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

                    ui.label("Import Data...").classes(
                        "text-lg font-bold text-[var(--vsp-blue)]"
                    )

                    # No format to choose. The CSV archive and the JSON
                    # export are told apart from the file itself, so
                    # picking the wrong one cannot fail an import.
                    ui.label(
                        "Select a file previously exported from VECTOR -- "
                        "either the ZIP archive or the JSON file. The "
                        "format is detected from the file itself."
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    ui.label(
                        "WARNING :"
                    ).classes("text-sm font-bold text-[#EF4444]")

                    ui.label("This will REPLACE ALL existing data!").classes(
                        "text-base text-[var(--vsp-gray)]"
                    )

                    picked = {"path": None, "folder": None, "locked": False}

                    def discard_picked() -> None:
                        if picked["folder"] is not None:
                            shutil.rmtree(picked["folder"], ignore_errors=True)
                        picked["path"] = picked["folder"] = None
                        picked["locked"] = False

                    async def on_file_picked(e) -> None:
                        # Kept under the name it arrived with: the suffix is
                        # part of how the format is recognised.
                        discard_picked()
                        folder = new_staging_dir("vector_import_upload_")
                        name = Path(e.file.name).name or "import.zip"
                        target = folder / name
                        await e.file.save(target)
                        picked["path"], picked["folder"] = target, folder
                        picked_label.set_text(f"Chosen: {name}")
                        # Whether it needs a password is read from the file
                        # itself, so nobody has to remember to say so.
                        locked = needs_password(target)
                        picked["locked"] = locked
                        password_note.set_visibility(locked)
                        password_input.set_visibility(locked)
                        import_button.enable()

                    ui.upload(
                        label="Choose the exported file (.zip or .json)",
                        on_upload=on_file_picked,
                        auto_upload=True,
                        max_files=1,
                        max_file_size=Config.MAX_IMPORT_BYTES,
                    ).props('accept=".zip,.json" flat bordered').classes(
                        "w-full"
                    )

                    picked_label = ui.label(
                        "No file chosen yet."
                    ).classes("text-sm text-[var(--vsp-gray)]")

                    password_note = ui.label(
                        "This file is protected with a password."
                    ).classes("text-sm text-[#F5B027]")

                    password_input = ui.input(
                        label="ENTER THE FILE'S PASSWORD :",
                        password=True,
                    ).classes("w-full yellow-label text-sm")

                    # Shown once a file that needs one has been chosen.
                    password_note.set_visibility(False)
                    password_input.set_visibility(False)

                    def do_import():
                        path = picked["path"]
                        if path is None:
                            ui.notify(
                                "Choose the exported file first.",
                                type="warning",
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return

                        pwd = password_input.value if picked["locked"] else None

                        if picked["locked"] and not pwd:
                            ui.notify(
                                "This file is protected with a password. "
                                "Enter it to import the file.",
                                type="warning",
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return

                        dialog.close()

                        # A .json, or a .zip holding one, goes through
                        # the JSON reader; the CSV archive is also a
                        # .zip, so the contents decide, not the suffix
                        # alone.
                        try:
                            if looks_like_json_export(path):
                                import_vector_from_json(
                                    str(path), password=pwd
                                )
                            else:
                                import_vector_from_csv(
                                    str(path), password=pwd
                                )
                        finally:
                            discard_picked()

                    def cancel_import() -> None:
                        discard_picked()
                        dialog.close()

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=cancel_import,
                            color="transparent",
                        ).props("flat").classes("hover-border-blue")

                        import_button = ui.button(
                            "Import Now",
                            on_click=do_import,
                            color="var(--vsp-blue)",
                        ).props("push").classes("hover-border-white")

                        import_button.disable()

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
                            label="AFFIRM BY TYPING 'DELETE' BELOW",
                            password=False,
                        )
                        .classes("w-full yellow-label mb-3")
                    )

                    affirm_input.bind_visibility_from(
                        affirm_checkbox,
                        "value",
                    )

                    def do_delete():
                        if not affirm_checkbox.value:
                            ui.notify(
                                "Tick the box to confirm you understand "
                                "the data cannot be recovered.",
                                type="warning",
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return

                        if (affirm_input.value or "").strip() != "DELETE":
                            ui.notify(
                                "Type DELETE, in capital letters, to confirm.",
                                type="warning",
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return

                        dialog.close()

                        try:
                            delete_all_data()
                        except Exception as err:
                            log.exception("Data deletion failed")
                            ui.notify(
                                "No data was deleted, and the case is "
                                f"unchanged.\n\n{explain(err)}",
                                multi_line=True,
                                classes="multi-line-notification",
                                type="warning",
                                timeout=WARN_TIMEOUT,
                                position="center",
                                close_button="OK",
                            )
                            return

                    with ui.row().classes("w-full justify-end gap-2 mt-4"):

                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent",
                        ).props("flat").classes("hover-border-blue")

                        ui.button(
                            "Delete all data",
                            on_click=do_delete,
                            color="#EF4444",
                        ).props("push").classes("hover-border-white")

                dialog.open()

            ui.button(
                "📤 EXPORT CASE DATA",
                on_click=open_export_dialog,
                color="#379161",
            ).props("push").classes("w-56 py-3 hover-border-white")

            ui.button(
                "📥 IMPORT CASE DATA",
                on_click=open_import_dialog,
                color="#379161",
            ).props("push").classes("w-56 py-3 hover-border-white")

            ui.button(
                "DELETE ALL DATA",
                on_click=open_delete_all_dialog,
                color="#EF4444",
            ).props("push").classes("w-56 py-3 hover-border-white")


def build_login_home():
    """Login page for unauthenticated users."""

    with ui.column().classes("items-center w-full mt-12"):

        ui.image(
            "/static/novadc_icac.png",
        ).classes("w-[150px] h-[150px] mb-2")

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
        ).props("push").classes("mt-4 px-8 py-3")


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
   The case number now shows at the top of every page.
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
8. **Reports** — seven printable lists, including the inventory used as
   the return copy. If the case is missing a detail a report needs, the
   page says which, and if it has no end time yet the page offers to fill
   it in from this machine's clock.

Until a case is open, the top bar shows **No Active Case** and the other
pages will not save.

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
  passwords and clear a sign-in lock; **Audit Trail**, a record of every
  change; and **Shutdown**, which stops VECTOR for everyone.
- After {LOCK_AFTER_FAILURES} wrong passwords an account is locked for
  {LOCKOUT_MINUTES} minutes. An administrator can clear the lock sooner.
- Passwords an administrator issues are shown once. Write them down before
  closing the message.

#### Other pages

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
            ).props("flat").classes("hover-border-blue")

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
                        timeout=WARN_TIMEOUT,
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
                "Proceed (Delete All Data)",
                on_click=on_proceed,
                color="#EF4444",
            ).props("push").classes("hover-border-white")

    warn_dialog.open()


@ui.page("/logout")
def logout_page():
    """Logs out the current user."""
    from nicegui import app

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
