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
import secrets
import sys

from auth import (
    get_current_user_name,
    get_is_admin,
    is_authenticated,
    require_admin,
    require_login,
)
from models import get_users_session
from program.config import (
    Config,
    DB_DIR,
    SECRET_FILE,
    STATIC_DIR,
    USERS_SEED_PATH,
)

DEBUG_MODE = "--dev" in sys.argv

# ----- Network exposure -----
# Loopback unless explicitly opted in, so an install is never reachable
# from the network by accident. See README "Access from another device".
LAN_MODE = "--lan" in sys.argv
HOST = "0.0.0.0" if LAN_MODE else Config.HOST


def get_storage_secret() -> str:
    """Loads the storage secret from a hidden file.

    Generates a new secret and saves it if the file doesn't exist.
    """

    if SECRET_FILE.exists():
        secret = SECRET_FILE.read_text(encoding="utf-8").strip()
        if secret:
            return secret

    # ----- Generate a new secret and save it -----
    secret = secrets.token_hex(32)
    SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret


# Explicitly tell NiceGUI where the static folder is.
# Created if absent: a checkout without the logo files must still boot.
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.add_static_files("/static", str(STATIC_DIR))


# ----- Initialize Database -----
from models import init_db, Users

init_db()


# ----- Seed Default User -----
def bootstrap_first_admin():
    """Creates a starting admin account if no users exist at all.

    A fresh checkout ships no credentials -- db/users.json is not
    tracked -- so without this there would be no way to log in. The
    password is random, shown once on the console, and must be changed
    at first login.
    """
    with get_users_session() as session:
        if session.query(Users).count() > 0:
            return

        password = secrets.token_urlsafe(12)
        admin = Users(
            USERNAME="admin",
            ISADMIN=True,
            ISACTIVE=True,
            MUSTCHANGEPASSWORD=True,
        )
        admin.set_password(password)
        session.add(admin)

    # Also written to a file: a launcher script or a double-clicked
    # shortcut can close or scroll the console before anyone reads it.
    # ASCII only -- the Windows console is not UTF-8 by default.
    note = DB_DIR / "FIRST_RUN_PASSWORD.txt"
    note.write_text(
        "VECTOR first-run administrator account\n"
        "======================================\n\n"
        "  Username:  admin\n"
        f"  Password:  {password}\n\n"
        "You will be asked to change this password at first login.\n"
        "Delete this file once you have done so.\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 62)
    print("  FIRST RUN - an administrator account has been created.")
    print("=" * 62)
    print("    Username:  admin")
    print(f"    Password:  {password}")
    print("\n  You will be asked to change it at first login.")
    print(f"  Also saved to: {note}")
    print("=" * 62 + "\n")


def seed_default_user():
    """Reads user credentials from users.json and upserts into the
    Users table.

    The JSON stores hashes as Python byte-string literals. This path is
    for existing installs that already have a users.json; new installs
    go through bootstrap_first_admin() instead.
    """
    if not USERS_SEED_PATH.exists():
        bootstrap_first_admin()
        return

    with open(USERS_SEED_PATH, "r", encoding="utf-8") as f:
        user_data = json.load(f)

    # Upstream's users.json moved to capitalised keys; older copies still
    # use the lowercase ones.
    raw_hash = user_data.get(
        "PASSWORDHASH", user_data.get("password_hash", "")
    )

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

    user_name = user_data.get("USERNAME", user_data.get("user_name", ""))
    is_admin = user_data.get("ISADMIN", user_data.get("is_admin", False))

    with get_users_session() as session:
        existing = (
            session.query(Users)
            .filter_by(USERNAME=user_name)
            .first()
        )
        if existing:
            # Seed only. Re-applying the hash on every start would undo
            # the user's own password changes each time the app
            # restarts -- which it does on every save under --dev.
            pass
        else:
            # Create new user
            new_user = Users(
                USERNAME=user_name,
                PASSWORDHASH=clean_hash,
                ISADMIN=is_admin,
                ISACTIVE=True,
            )
            session.add(new_user)
            print(f"Created user '{user_name}' from users.json")

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
    --q-vspblue: #2984D1;

    --vsp-blue: #2984D1;
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
# Imported eagerly. These modules were previously imported inside each
# route to dodge the circular dependency on main.py, which meant the
# report sub-routes were not registered until somebody first visited
# /reports -- so a bookmark or a page refresh returned 404. auth.py
# removed the cycle, so the imports can sit where they belong.
import home_page

from parts.admin_page import build_admin_page
from parts.agents_page import build_agents_page
from parts.audit_page import build_audit_page
from parts.cases_page import build_cases_page
from parts.evidence_page import build_evidence_page
from parts.files_page import build_uploads_page
from parts.links_page import build_links_page
from parts.notes_page import build_notes_page
from parts.persons_page import build_persons_page
from parts.reports_page import build_reports_page
from parts.rooms_page import build_rooms_page


# Route -> builder, and whether the page is admin-only. Written once so
# a new page cannot arrive with its guard subtly different from the
# others -- which is how /admin ended up reachable by any signed-in
# user, and /shutdown by anyone at all.
PAGES = [
    ("/cases", build_cases_page, False),
    ("/agents", build_agents_page, False),
    ("/rooms", build_rooms_page, False),
    ("/evidence", build_evidence_page, False),
    ("/persons", build_persons_page, False),
    ("/notes", build_notes_page, False),
    ("/uploads", build_uploads_page, False),
    ("/links", build_links_page, False),
    ("/reports", build_reports_page, False),
    ("/admin", build_admin_page, True),
    ("/audit", build_audit_page, True),
]

for _route, _builder, _admin_only in PAGES:
    _guard = require_admin if _admin_only else require_login
    ui.page(_route)(_guard(_builder))


@ui.page("/change-password")
def change_password_page():

    from models import get_users_session, Users

    if not is_authenticated():
        ui.navigate.to("/")
        return

    username = get_current_user_name()

    with ui.column().classes("items-center w-full mt-12"):

        ui.label(
            "Change Password"
        ).classes("text-2xl font-bold mb-2")

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

            def save_new_password():
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

                # There is no shared default password to exclude any
                # more; every issued password is unique to the account.

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
                on_click=save_new_password,
            ).props("unelevated").classes("w-full mt-4")


# ----- Run -----
if __name__ in {"__main__", "__mp_main__"}:

    ui.add_head_html(
        '<link rel="icon" type="image/x-icon" href="/static/favicon.ico">',
        shared=True,
    )

    if LAN_MODE:
        print(
            "\n  ** LAN MODE ** VECTOR is reachable from other devices on "
            "this network.\n"
            "  Traffic is unencrypted HTTP. Use only on a network you "
            "control.\n"
        )

    ui.run(
        title="V·E·C·T·O·R",
        host=HOST,
        port=Config.PORT,
        reload=DEBUG_MODE,  # or "False"
        show=Config.SHOW_BROWSER,
        dark=True,
        storage_secret=get_storage_secret(),
    )
