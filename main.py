#!/usr/bin/env python3

# ==============================================================================

"""
main.py — VECTOR Application Bootstrap
NiceGUI conversion of the original Flask VECTOR application.

V·E·C·T·O·R —
Virginia Evidence Collection, Tracking, Organization, & Recording Program

Usage:
    python main.py
    Open browser to http://localhost:8080
"""

from nicegui import ui, app

# ── Initialize Database ─────────────────────────────────────
from models import init_db, get_session, Users
init_db()


# ── Seed Default User ───────────────────────────────────────
def seed_default_user():
    """Creates the default 'novaicac' user if it doesn't exist."""
    with get_session() as session:
        existing = session.query(Users).filter_by(user_name="novaicac").first()
        if not existing:
            default_user = Users(
                user_name="novaicac",
                is_admin=False,
                is_active=True,
            )
            # Set the default password — CHANGE THIS before deploying!
            default_user.set_password("ChangeMe123!")
            session.add(default_user)


seed_default_user()


# ── Theme Configuration ─────────────────────────────────────

# ── Import All Page Modules ─────────────────────────────────
# Each module registers its own @ui.page routes on import.
# Order matters: shared utilities first, then pages.

# Core infrastructure
import navbar
import main_page  # (/, /home, /about, /help, /export_db, /logout)

# Reports (self-registers all /reports/* routes on import)
import reports.reports_page

# ── Page Registrations ─────────────────────────────────────
# Some page modules define their own @ui.page decorators internally.
# The ones below are registered here for centralized control.


@ui.page("/agents")
def agents_route():
    if not main_page.is_authenticated():
        ui.navigate.to("/")
        return 
    from agents.agents_page import build_agents_page
    build_agents_page()


@ui.page("/cases")
def cases_route():
    if not main_page.is_authenticated():
        ui.navigate.to("/")
        return
    from cases.cases_page import build_cases_page
    build_cases_page()


@ui.page("/rooms")
def rooms_route():
    if not main_page.is_authenticated():
        ui.navigate.to("/")
        return
    from rooms.rooms_page import build_rooms_page
    build_rooms_page()


@ui.page("/evidence")
def evidence_route():
    if not main_page.is_authenticated():
        ui.navigate.to("/")
        return
    from evidence.evidence_page import build_evidence_page
    build_evidence_page()


@ui.page("/persons")
def persons_route():
    if not main_page.is_authenticated():
        ui.navigate.to("/")
        return
    from persons.persons_page import build_persons_page
    build_persons_page()


@ui.page("/notes")
def notes_route():
    if not main_page.is_authenticated():
        ui.navigate.to("/")
        return
    from notes.notes_page import build_notes_page
    build_notes_page()


@ui.page("/links")
def links_route():
    if not main_page.is_authenticated():
        ui.navigate.to("/")
        return
    from links.links_page import build_links_page
    build_links_page()


# ── Startup Configuration ──────────────────────────────────
@app.on_startup
async def initialize_app():
    """Initialize app storage and verify database."""
    # Matches the original Flask app's dark theme (#212121 background)
    ui.colors(
        primary="#6d4aff",
        secondary="#264653",
        accent="#2a9d8f",
        dark="#1a1a1a",
        dark_page="#212121",
        positive="#22c55e",
        negative="#ef4444",
        warning="#f59e0b",
        info="#3b82f6",
    )
    # Ensure storage keys exist
    if "authenticated" not in app.storage.user:
        app.storage.user["authenticated"] = False
    if "user_name" not in app.storage.user:
        app.storage.user["user_name"] = ""
    if "is_admin" not in app.storage.user:
        app.storage.user["is_admin"] = False


# ── Run ─────────────────────────────────────────────────────
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="V·E·C·T·O·R",
        port=8080,
        reload=False,
        dark=True,
        storage_secret="vector-secret-key-change-in-production-2024",
        favicon="🛡️",
    )
