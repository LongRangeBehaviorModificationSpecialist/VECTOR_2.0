#!/usr/bin/env python3

"""
main.py

V·E·C·T·O·R —
Virginia Evidence Collection, Tracking, Organization, & Reporting Program

Usage:
    python main.py
    Open browser to http://localhost:8080
"""

import ast
import json
from nicegui import ui, app
import os
from pathlib import Path
import sys


DEBUG_MODE = "--dev" in sys.argv

# Explicitly tell NiceGUI where the static folder is
app.add_static_files(
    "/static",
    os.path.join(os.path.dirname(__file__), "static")
)


# ----- Initialize Database -----
from models import init_db, get_session, Users
init_db()


# ----- Seed Default User -----
def seed_default_user():
    """Reads user credentials from users.json and upserts into the
    Users table.

    The JSON stores hashes as Python byte-string literals.
    """
    json_path = Path(__file__).parent / f"parts\\users.json"
    if not json_path.exists():
        print("WARNING → 'users.json' not found — no user seeded.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        user_data = json.load(f)

    # Extract the password hash from the byte-string representation
    raw_hash = user_data.get("password_hash", "")

    # The JSON stores it as "b'$2b$12$...'"
    # parse it back to bytes, then decode to str
    try:
        hash_bytes = ast.literal_eval(raw_hash)
        if isinstance(hash_bytes, bytes):
            clean_hash = hash_bytes.decode("utf-8")
        else:
            clean_hash = str(hash_bytes)
    except (ValueError, SyntaxError):
        # If ast.literal_eval fails, try stripping the b'' wrapper manually
        clean_hash = raw_hash
        if clean_hash.startswith("b'") and clean_hash.endswith("'"):
            clean_hash = clean_hash[2:-1]

    user_name = user_data.get("user_name", "")
    is_admin = user_data.get("is_admin", False)

    with get_session() as session:
        existing = (
            session.query(Users)
            .filter_by(user_name=user_name)
            .first()
        )
        if existing:
            # Update existing user with latest hash from JSON
            existing.password_hash = clean_hash
            existing.is_admin = is_admin
            existing.is_active = True
            print(f"✓ Updated user '{user_name}' from users.json")
        else:
            # Create new user
            new_user = Users(
                user_name=user_name,
                password_hash=clean_hash,
                is_admin=is_admin,
                is_active=True,
            )
            session.add(new_user)
            print(f"✓ Created user '{user_name}' from users.json")

seed_default_user()


# ----- Theme Configuration -----
# Shrinks all textarea heights to match input/select field heights
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

# ----- Import All Page Modules -----
# Each module registers its own @ui.page routes on import.
# Order matters: shared utilities first, then pages.

# Core infrastructure
import home_page  # (/, /home, /about, /help, /export_db, /logout)

# ----- Page Registrations -----
# Some page modules define their own @ui.page decorators internally.
# The ones below are registered here for centralized control.


@ui.page("/agents")
def agents_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.agents_page import build_agents_page
    build_agents_page()


@ui.page("/cases")
def cases_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.cases_page import build_cases_page
    build_cases_page()


@ui.page("/rooms")
def rooms_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.rooms_page import build_rooms_page
    build_rooms_page()


@ui.page("/evidence")
def evidence_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.evidence_page import build_evidence_page
    build_evidence_page()


@ui.page("/persons")
def persons_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.persons_page import build_persons_page
    build_persons_page()


@ui.page("/notes")
def notes_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.notes_page import build_notes_page
    build_notes_page()


@ui.page("/uploads")
def uploads_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.files_page import build_uploads_page
    build_uploads_page()


@ui.page("/links")
def links_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.links_page import build_links_page
    build_links_page()


@ui.page("/reports")
def reports_route():
    if not home_page.is_authenticated():
        ui.navigate.to("/")
        return
    from parts.reports_page import build_reports_page
    build_reports_page()


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
        return app.storage.user.get("user_name", "")
    except Exception:
        return ""

def get_is_admin() -> bool:
    """Checks if current user is admin (defaults to False)."""
    try:
        return app.storage.user.get("is_admin", False)
    except Exception:
        return False


# ----- Run -----
if __name__ in {"__main__", "__mp_main__"}:

    ui.add_head_html(
        '<link rel="icon" type="image/x-icon" href="/static/favicon.ico">',
        shared=True
    )

    ui.run(
        title="V·E·C·T·O·R",
        port=8080,
        reload=DEBUG_MODE,
        dark=True,
        storage_secret="vector-secret-key-change-in-production-2024",
    )
