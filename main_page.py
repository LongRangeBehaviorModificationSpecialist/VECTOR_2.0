#!/usr/bin/env python3

"""
main_page.py

Handles:
    /               →  Home/Login page
    /about          →  About page
    /help           →  Help page
    /export_db      →  Database export
    /make_new_case  →  Clear all data (dangerous!)
    /error_check    →  Data integrity checks
    /saved_output   →  Save output viewer
"""

from nicegui import ui
from pathlib import Path
from datetime import datetime
import shutil

from models import (
    get_session,
    Agents,
    Cases,
    Evidence,
    Notes,
    Persons,
    Rooms,
)
from navbar import build_navbar, confirm_new_case_dialog
from program.config import Config


# ── Auth Helpers ──────────────────────────────────────────────
def is_authenticated() -> bool:
    """Stub — wire up to your session/auth logic."""
    from nicegui import app
    return app.storage.user.get("authenticated", False)


def get_current_user_name() -> str:
    """Stub — returns username or 'Guest'."""
    from nicegui import app
    return app.storage.user.get("user_name", "Guest")


def get_is_admin() -> bool:
    """Stub — returns True if user is admin."""
    from nicegui import app
    return app.storage.user.get("is_admin", False)


# ── Home Page ─────────────────────────────────────────────────
def build_home_page():
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
    """Main menu for logged-in users."""

    with ui.column().classes("items-center w-full mt-8 mb-6"):
        ui.label(
            "V·E·C·T·O·R Home Page"
        ).classes("text-2xl font-normal text-center")

    with ui.column().classes("items-center w-full"):
        ui.label(
            "Main Menu"
        ).classes("text-xl font-semibold mb-6")

    with ui.row().classes(
        "flex justify-center items-center gap-6 mb-4 w-full"
    ):
        ui.button(
            "Start New Case",
            on_click=lambda: ui.navigate.to("/cases"),
        ).props(
            "unelevated"
        ).classes("flex-shrink-0 min-w-48 py-3")

        ui.button(
            "Add Agent",
            on_click=lambda: ui.navigate.to("/agents"),
        ).props(
            "unelevated"
        ).classes("flex-shrink-0 min-w-48 py-3")

        ui.button(
            "Add Room",
            on_click=lambda: ui.navigate.to("/rooms"),
        ).props(
            "unelevated"
        ).classes("flex-shrink-0 min-w-48 py-3")

    # Row 2: Add Evidence | Add Person | Add Note
    with ui.row().classes(
        "flex justify-center items-center gap-6 mb-4 w-full"
    ):
        ui.button(
            "Add Evidence",
            on_click=lambda: ui.navigate.to("/evidence"),
        ).props(
            "unelevated"
        ).classes("flex-shrink-0 min-w-48 py-3")

        ui.button(
            "Add Person",
            on_click=lambda: ui.navigate.to("/persons"),
        ).props(
            "unelevated"
        ).classes("flex-shrink-0 min-w-48 py-3")

        ui.button(
            "Add Note",
            on_click=lambda: ui.navigate.to("/notes"),
        ).props(
            "unelevated"
        ).classes("flex-shrink-0 min-w-48 py-3")


def build_login_home():
    """Login page for unauthenticated users."""

    with ui.column().classes("items-center w-full mt-12"):
        ui.icon(
            "shield",
            size="80px",
        ).classes("text-purple-600 mb-4")

        ui.label(
            "-- V·E·C·T·O·R --"
        ).classes("text-3xl font-bold tracking-widest mb-6")

        ui.label(
            "The Virginia Evidence Collection, Tracking, "
            "Organization, & Recording Program"
        ).classes("text-base text-gray-400 text-center max-w-xl mb-2")

        ui.label(
            "Please log in below"
        ).classes("text-lg mb-6")

        username_input = ui.input(
            label="Username"
        ).classes("w-full max-w-xs")
        
        password_input = ui.input(
            label="Password",
            password=True,
            password_toggle_button=True,
        ).classes("w-full max-w-xs")

        def attempt_login():
            # Wire this to your Users model authentication
            from models import get_session, Users

            user_name = username_input.value
            user_pass = password_input.value

            with get_session() as session:
                user = session.query(
                    Users
                ).filter_by(user_name=user_name).first()

                if user and user.check_password_correction(user_pass):
                    from nicegui import app

                    app.storage.user["authenticated"] = True
                    app.storage.user["user_name"] = user.user_name
                    app.storage.user["is_admin"] = user.is_admin
                    ui.notify(
                        f"Welcome, {user.user_name}!",
                        type="positive",
                    )
                    ui.navigate.to("/")
                else:
                    ui.notify(
                        "Invalid credentials",
                        type="negative",
                    )

        ui.button(
            "Login",
            on_click=attempt_login,
        ).props("unelevated").classes("mt-4 px-8 py-3")


# ── About Page ───────────────────────────────────────────────
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
            "About VECTOR"
        ).classes("text-2xl font-bold mb-6")

        with ui.card().classes("max-w-md p-6"):
            ui.label(f"Version: {Config.version}").classes("mb-2")
            ui.label(f"Author: {Config.author}").classes("mb-2")
            ui.label(f"Department: {Config.dept}").classes("mb-2")
            ui.label(
                f"Last Updated: {Config.updated}"
            ).classes("text-sm text-gray-500")


# ── Help Page ────────────────────────────────────────────────
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

    with ui.column().classes("items-center w-full mt-8 max-w-3xl"):
        ui.label(
            "Help"
        ).classes("text-2xl font-bold mb-6")

        with ui.card().classes("p-6"):
            ui.markdown("""
                ### VECTOR Help Documentation

                This application helps you manage evidence collection,
                tracking, organization, and recording for law
                enforcement cases.

                #### Quick Start

                1. **Start New Case** — Begin a fresh case file
                2. **Add Agent** — Register agents who will work on cases
                3. **Add Room** — Define storage rooms for evidence
                4. **Add Evidence** — Record evidence items
                5. **Add Person** — Document suspects/witnesses
                6. **Add Notes** — Write case notes

                #### Navigation

                Use the top menu to access different sections:
                - **Case Info** — View/edit case details
                - **Agents** — Manage agent roster
                - **Rooms** — Manage storage locations
                - **Evidence** — Track evidence chain of custody
                - **People** — Document persons of interest
                - **Notes** — Write case documentation
                - **Reports** — Print various reports
            """)


# ── Export Database Page ─────────────────────────────────────
@ui.page("/export_db")
def export_db_page():
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
            "Export Database"
        ).classes("text-2xl font-bold mb-6")

        ui.label(
            "This will create a backup copy of the current case "
            "database in your user profile folder."
        ).classes("text-sm text-gray-400 mb-4")

        db_path_label = ui.label("").classes("text-sm text-green-400")

        def on_export():
            try:
                with get_session() as session:
                    first_case = session.query(Cases).first()
                    case_number = (
                        first_case.case_number
                        if first_case
                        else "UNKNOWN"
                    )

                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                new_dir = f"{timestamp}_Case_File_Folder"
                save_to_path = Path(Config.USERPROFILE) / new_dir
                save_to_path.mkdir(parents=True, exist_ok=True)

                db_file = Path.cwd() / "program" / "_VECTOR.db"

                if not db_file.exists():
                    ui.notify(
                        "Database file not found",
                        type="negative",
                    )
                    return

                dest_file = save_to_path / f"{case_number}_VECTOR.db"
                shutil.copy(db_file, dest_file)

                db_path_label.set_text(f"Saved to: {dest_file}")
                ui.notify(
                    f"A copy of the case's database folder was saved "
                    f"to the '{save_to_path}' directory.",
                    type="positive",
                )

            except Exception as e:
                ui.notify(
                    f"Export failed: {str(e)}",
                    type="negative",
                )

        ui.button(
            "Export Database",
            on_click=on_export,
        ).props("unelevated")

        with ui.card().classes("mt-4 p-4 bg-gray-800"):
            ui.label("Export Location:").classes("text-sm font-mono")
            ui.label(str(
                Path(Config.USERPROFILE))
            ).classes("text-sm text-gray-500")


# ── Confirm New Case Handler ─────────────────────────────────
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
            "- Agents\n- Cases\n- Evidence\n- Notes\n- Persons\n"
            "- Rooms\n\n. This action CANNOT be undone. Are you "
            "absolutely sure?"
        ).classes("text-sm mb-4")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(
                "Cancel",
                on_click=dialog.close,
            ).props("flat")

            def on_confirm_delete_all():
                try:
                    with get_session() as session:
                        # Delete in order to avoid foreign key issues
                        session.query(Evidence).delete()
                        session.query(Notes).delete()
                        session.query(Persons).delete()
                        session.query(Rooms).delete()
                        session.query(Agents).delete()
                        session.query(Cases).delete()
                        session.commit()

                    ui.notify(
                        "All data in all database tables has "
                        "been successfully deleted",
                        type="info",
                    )
                    ui.navigate.to("/")

                except Exception as e:
                    session.rollback()
                    ui.notify(
                        "Database information was rolled back "
                        "successfully",
                        type="warning",
                    )
                finally:
                    dialog.close()

            ui.button(
                "DELETE ALL",
                on_click=on_confirm_delete_all,
            ).props("negative unelevated")

    dialog.open()


# ── Error Check Page ─────────────────────────────────────────
@ui.page("/error_check")
def error_check_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes(
        "items-start w-full mt-8 max-w-4xl gap-6"
    ):
        ui.label(
            "Data Integrity Check"
        ).classes("text-2xl font-bold mb-4")

        with ui.row().classes("gap-4 w-full"):
            # Case End Time Issues
            with ui.card().classes("flex-1"):
                ui.label(
                    "Cases Without End Times"
                ).classes("text-lg font-semibold mb-3 text-yellow-400")
                with get_session() as session:
                    queryCaseEndTime = (
                        session.query(
                            Cases.case_number,
                            Cases.case_date_time_end,
                        )
                        .filter(Cases.case_date_time_end == "")
                        .all()
                    )

                if not queryCaseEndTime:
                    ui.label(
                        "✓ No issues found"
                    ).classes("text-sm text-green-400")
                else:
                    with ui.table(
                        columns=[
                            {
                                "name": "case_number",
                                "label": "Case #",
                                "field": "case_number",
                            },
                            {
                                "name": "end_time",
                                "label": "End Time",
                                "field": "case_date_time_end",
                            },
                        ],
                        rows=[
                            {
                                "case_number": r.case_number,
                                "end_time": r.case_date_time_end,
                            }
                            for r in queryCaseEndTime
                        ],
                        row_key="case_number",
                    ).props("dense"):
                        pass

            # Rooms with Missing Agents
            with ui.card().classes("flex-1"):
                ui.label(
                    "Rooms with Missing Agents"
                ).classes("text-lg font-semibold mb-3 text-orange-400")
                
                with get_session() as session:
                    queryTwoAgentsRooms = (
                        session.query(
                            Rooms.room_label,
                            Rooms.room_desc,
                            Rooms.room_first_agent,
                            Rooms.room_second_agent,
                        )
                        .filter(
                            (Rooms.room_first_agent == "")
                            | (Rooms.room_second_agent == "")
                        )
                        .all()
                    )

                if not queryTwoAgentsRooms:
                    ui.label(
                        "✓ No issues found."
                    ).classes("text-sm text-green-400")
                else:
                    with ui.table(
                        columns=[
                            {
                                "name": "room_label",
                                "label": "Room",
                                "field": "room_label",
                            },
                            {
                                "name": "desc",
                                "label": "Description",
                                "field": "room_desc",
                            },
                            {
                                "name": "agent1",
                                "label": "Agent 1",
                                "field": "room_first_agent",
                            },
                            {
                                "name": "agent2",
                                "label": "Agent 2",
                                "field": "room_second_agent",
                            },
                        ],
                        rows=[
                            {
                                "room_label": r.room_label,
                                "desc": r.room_desc,
                                "agent1": r.room_first_agent,
                                "agent2": r.room_second_agent,
                            }
                            for r in queryTwoAgentsRooms
                        ],
                        row_key="room_label",
                    ).props("dense"):
                        pass

        # Evidence with Missing Witnesses
        with ui.card().classes("w-full"):
            ui.label(
                "Evidence without Witness Information"
            ).classes("text-lg font-semibold mb-3 text-orange-400")
            
            with get_session() as session:
                queryTwoAgentsEvid = (
                    session.query(
                        Evidence.evid_num,
                        Evidence.evid_found_by,
                        Evidence.evid_found_by_witness,
                    )
                    .filter(
                        (Evidence.evid_found_by == "")
                        | (Evidence.evid_found_by_witness == "")
                    )
                    .all()
                )

            if not queryTwoAgentsEvid:
                ui.label(
                    "✓ No issues found."
                ).classes("text-sm text-green-400")
            else:
                with ui.table(
                    columns=[
                        {
                            "name": "evid_num",
                            "label": "Evidence #",
                            "field": "evid_num",
                        },
                        {
                            "name": "found_by",
                            "label": "Found By",
                            "field": "evid_found_by",
                        },
                        {
                            "name": "witness",
                            "label": "Witness",
                            "field": "evid_found_by_witness",
                        },
                    ],
                    rows=[
                        {
                            "evid_num": r.evid_num,
                            "found_by": r.evid_found_by,
                            "witness": r.evid_found_by_witness,
                        }
                        for r in queryTwoAgentsEvid
                    ],
                    row_key="evid_num",
                ).props("dense"):
                    pass


# ── Saved Output Page ────────────────────────────────────────
@ui.page("/saved_output")
def saved_output_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("items-center w-full mt-8 max-w-3xl"):
        ui.label("Saved Output").classes("text-2xl font-bold mb-6")

        ui.label(
            "Browse previously exported case files and database "
            "backups"
        ).classes("text-sm text-gray-400 mb-4")

        with ui.card().classes("p-6 w-full"):
            ui.label(
                "Output Directory"
            ).classes("text-base font-semibold mb-2")
            
            ui.label(str(Path(Config.USERPROFILE))).classes(
                "text-sm text-gray-500 font-mono mb-4"
            )

            # List exported folders (placeholder)
            ui.label(
                "No recent exports found"
            ).classes("text-sm text-gray-400")


# ── Page Registration ────────────────────────────────────────
@ui.page("/")
@ui.page("/home")
def home():
    build_home_page()


@ui.page("/logout")
def logout_page():
    """Logs out the current user."""
    from nicegui import app

    app.storage.user.clear()
    ui.notify(
        "Logged out successfully",
        type="info",
    )
    ui.navigate.to("/")
