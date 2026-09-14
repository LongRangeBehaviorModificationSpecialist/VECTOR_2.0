#!/usr/bin/env python3

"""
main.py

V·E·C·T·O·R —
Virginia Evidence Collection, Tracking, Organization, & Reporting Program

Usage:
    python main.py [--dev]
    Open browser to http://localhost:8080
"""

import ast
import json
from nicegui import ui, app
import os
from pathlib import Path
import secrets
import sys

from models import get_users_session

DEBUG_MODE = "--dev" in sys.argv


# ----- Startup Configuration -----
def is_authenticated() -> bool:
    """Checks if user is authenticated (defaults to False)."""
    try:
        return app.storage.user.get("authenticated", False)
    except Exception:
        return False


def get_current_user_name() -> str:
    """Gets current username (defaults to empty)."""
    try:
        return app.storage.user.get("USERNAME", "")
    except Exception:
        return ""


def get_is_admin() -> bool:
    """Checks if current user is admin (defaults to False)."""
    try:
        return app.storage.user.get("ISADMIN", False)
    except Exception:
        return False


def get_storage_secret() -> str:
    """Loads the storage secret from a hidden file.

    Generates a new secret and saves it if the file doesn't exist.
    """

    secret_file = Path(__file__).parent / ".secret"

    if secret_file.exists():
        secret = secret_file.read_text(encoding="utf-8").strip()
        if secret:
            return secret

    # ----- Generate a new secret and save it -----
    secret = secrets.token_hex(32)
    secret_file.write_text(secret, encoding="utf-8")
    return secret


# Explicitly tell NiceGUI where the static folder is
app.add_static_files(
    "/static",
    os.path.join(os.path.dirname(__file__), "static"),
)


# ----- Initialize Database -----
from models import init_db, Users

init_db()


# ----- Seed Default User -----
def seed_default_user() -> None:
    """Reads user credentials from users.json and upserts into the
    Users table.

    The JSON stores hashes as Python byte-string literals.
    """
    json_path = Path(__file__).parent / f"db/users.json"

    if not json_path.exists():
        ui.notify(
            "WARNING → 'users.json' not found — no user seeded.",
            type="warning",
            timeout=0,
            position="center",
            close_button="OK",
        )
        return

    with open(json_path, "r", encoding="utf-8") as f:
        user_data = json.load(f)

    raw_hash = user_data.get("PASSWORDHASH", "")

    try:
        hash_bytes = ast.literal_eval(raw_hash)
        if isinstance(hash_bytes, bytes):
            clean_hash = hash_bytes.decode("utf-8")
        else:
            clean_hash = str(hash_bytes)

    except (ValueError, SyntaxError):
        clean_hash = raw_hash
        if clean_hash.startswith("b'") and clean_hash.endswith("'"):
            clean_hash = clean_hash[2:-1]

    user_name = user_data.get("USERNAME", "")
    is_admin = user_data.get("ISADMIN", False)

    with get_users_session() as session:
        existing = (
            session.query(Users)
            .filter_by(USERNAME="novaicac")
            .first()
        )
        if existing:
            # Update existing user with latest hash from JSON
            existing.PASSWORDHASH = clean_hash
            existing.ISADMIN = is_admin
            existing.ISACTIVE = True
        else:
            # Create new user
            new_user = Users(
                USERNAME=user_name,
                PASSWORDHASH=clean_hash,
                ISADMIN=is_admin,
                ISACTIVE=True,
            )
            session.add(new_user)
            ui.notify(
                f"✓ Created user '{user_name}' from users.json",
                timeout=4000,
                position="bottom",
                close_button="OK",
            )

seed_default_user()


# ----- Theme Configuration -----
ui.add_css(
    """
/* ----- Theme Colors (replaces ui.colors) ----- */
:root {
    --q-primary: #6d4aff;
    --q-secondary: #264653;
    --q-accent: #2a9d8f;
    --q-dark: #1a1a1a;
    --q-dark-page: #212121;
    --q-positive: #22c55e;
    --q-negative: #ef4444;
    --q-warning: #f59e0b;
    --q-info: #3b82f6;
    --q-vspblue: #2984d1;

    --vsp-blue: #2984D1;
    --vsp-blue-2: #1C69A8;
    --vsp-gray: #D4D4D8;
    --vsp-red: #FF0000;
    --vsp-green: #31C950;
    --vsp-white: #FFFFFF;
}

.confirm-styled-label .q-field__label {
    color: #ef4444;
}

/* Textarea height */
textarea.q-field__native {
    min-height: 40px !important;
    max-height: 40px !important;
    line-height: 20px;
    padding: 8px 12px;
    resize: none !important;
}

/* Required field asterisk */
.required {
    color: #ef4444 !important;
    margin-left: 2px;
}


.q-field--labeled .q-field__native {
    padding-bottom: 0px;
}


.yellow-label .q-field__label {
    color: #F5B027;
    font-size: 10pt;
    font-weight: normal;
}

/* Print styles */
@media print {
    .no-print {
        display: none !important;
    }

    /* Hide navbar */
    .q-header {
        display: none !important;
    }

    /* Hide all images */
    img {
        display: none !important;
    }

    /* Remove padding/margins so content fills the page */
    main,
    .nicegui-content,
    .q-page {
        padding: 0 !important;
        margin: 0 !important;
    }

    body {
        padding: 0 !important;
    }
}
""",
    shared=True,
)


# ----- Page Registrations -----
# Some page modules define their own @ui.page decorators internally.
# The ones below are registered here for centralized control.
import home_page


@ui.page("/agents")
def agents_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.agents_page import build_agents_page
    build_agents_page()


@ui.page("/cases")
def cases_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.cases_page import build_cases_page
    build_cases_page()


@ui.page("/rooms")
def rooms_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.rooms_page import build_rooms_page
    build_rooms_page()


@ui.page("/evidence")
def evidence_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.evidence_page import build_evidence_page
    build_evidence_page()


@ui.page("/persons")
def persons_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.persons_page import build_persons_page
    build_persons_page()


@ui.page("/notes")
def notes_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.notes_page import build_notes_page
    build_notes_page()


@ui.page("/uploads")
def uploads_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.files_page import build_uploads_page
    build_uploads_page()


@ui.page("/links")
def links_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.links_page import build_links_page
    build_links_page()


@ui.page("/reports")
def reports_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    from parts.reports_page import build_reports_page
    build_reports_page()


@ui.page("/admin")
def admin_route() -> None:
    if not is_authenticated():
        ui.navigate.to("/")
        return

    if not get_is_admin():
        ui.notify(
            "Admin access is required to access this page.",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )

    from parts.admin_page import build_admin_page
    build_admin_page()


@ui.page("/change-password")
def change_password_page() -> None:

    from models import get_users_session, Users, DEFAULT_USER_PASSWORD

    if not is_authenticated():
        ui.navigate.to("/")
        return

    username = get_current_user_name()

    with ui.column().classes("items-center w-full mt-12"):

        ui.label("Change Password").classes("text-2xl font-bold mb-2")

        ui.label(
            "You must set a new password before continuing."
        ).classes("text-gray-400 mb-6")

        with ui.card().classes("w-full max-w-sm p-6"):
            ui.label(
                f"User: {username}"
            ).classes("mb-4 font-semibold")

            new_pass = ui.input(
                label="New Password",
                password=True,
            ).classes("w-full")

            confirm_pass = ui.input(
                label="Confirm Password",
                password=True,
            ).classes("w-full")

            def save_new_password() -> None:
                if not new_pass.value or len(new_pass.value) < 8:
                    ui.notify(
                        "Password must be at least 8 characters.",
                        type="negative",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )
                    return

                if new_pass.value != confirm_pass.value:
                    ui.notify(
                        "Passwords do not match.",
                        type="negative",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )
                    return

                if new_pass.value == DEFAULT_USER_PASSWORD:
                    ui.notify(
                        "You cannot use the default password.",
                        type="negative",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )
                    return

                with get_users_session() as session:
                    user = (
                        session.query(Users)
                        .filter_by(USERNAME=username)
                        .first()
                    )
                    if user:
                        user.set_password(new_pass.value)
                        user.MUSTCHANGEPASSWORD = False
                ui.notify(
                    "Password changed.",
                    timeout=4000,
                    position="bottom",
                    close_button="OK",
                )
                ui.navigate.to("/")

            confirm_pass.on("keydown.enter", save_new_password)

            ui.button(
                "Save Password",
                on_click=save_new_password).props("push"
            ).classes("w-full mt-4")


# ----- Run -----
if __name__ in {"__main__", "__mp_main__"}:

    ui.add_head_html(
        '<link rel="icon" type="image/x-icon" href="/static/favicon.ico">',
        shared=True,
    )

    ui.run(
        title="V·E·C·T·O·R",
        port=8080,
        reload=DEBUG_MODE,  # or "False"
        dark=True,
        storage_secret=get_storage_secret(),
    )
