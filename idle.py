#!/usr/bin/env python3

"""
idle.py

Signs a session out after a spell with nobody using it.

A tablet left on a kitchen counter at a scene, or a laptop in an
unattended vehicle, stays signed in to the case until somebody closes
the browser. This watches for the absence of typing, tapping, scrolling
and clicking -- deliberately not for the absence of page loads, since
VECTOR's own refresh timers would then keep a session alive forever.

Activity is recorded in the browser rather than on the server, and in
localStorage rather than in the tab, so every tab of the same browser
counts as one device: a tablet with the evidence list in front and a
report behind it is not signed out because nobody touched the report.

A sign-out changes no case data: every record already saved stays as it
is. What it costs is a form filled in and not yet saved, which goes with
the page -- so the warning says so rather than claiming nothing is lost.
The sign-out is recorded in the audit trail, because a device left alone
at a scene is worth knowing about.

Imports nothing from the pages that use it.
"""

from nicegui import ui

from auth import sign_out
from failures import log
from models import get_session, record_audit
from program.config import Config


# Often enough that a sign-out lands within a few seconds of its time,
# rarely enough to be nothing on the network.
CHECK_EVERY_SECONDS = 15.0

# Long enough to notice the warning and reach for the screen.
WARN_BEFORE_SECONDS = 60

STORAGE_KEY = "vectorLastActivity"

_WATCH_ACTIVITY_JS = f"""
if (!window.__vectorActivityWatched) {{
    window.__vectorActivityWatched = true;
    const note = () => {{
        window.__vectorActivityAt = Date.now();
        try {{
            localStorage.setItem('{STORAGE_KEY}', String(Date.now()));
        }} catch (error) {{
            /* Private browsing refuses storage; this tab still counts. */
        }}
    }};
    for (const event of ['pointerdown', 'keydown', 'wheel', 'touchstart']) {{
        window.addEventListener(event, note, {{passive: true}});
    }}
    note();
}}
"""

_IDLE_SECONDS_JS = f"""
(() => {{
    let last = Number(window.__vectorActivityAt || 0);
    try {{
        const stored = Number(localStorage.getItem('{STORAGE_KEY}') || 0);
        last = Math.max(last, stored);
    }} catch (error) {{
        /* Private browsing: this tab's own record is all there is. */
    }}
    if (!last) {{ return 0; }}
    return Math.round((Date.now() - last) / 1000);
}})()
"""


def idle_limit_seconds() -> int:
    """How long without activity ends a session. 0 turns it off."""
    return max(0, Config.SESSION_IDLE_MINUTES) * 60


def decide(idle_seconds: float, limit_seconds: int) -> str:
    """What to do about a session idle this long.

    Returns "wait", "warn" or "end". Kept apart from the page so the
    rule can be tested without a browser.
    """
    if limit_seconds <= 0:
        return "wait"
    if idle_seconds >= limit_seconds:
        return "end"
    if idle_seconds >= limit_seconds - WARN_BEFORE_SECONDS:
        return "warn"
    return "wait"


def record_idle_sign_out(username: str) -> None:
    """Notes in the trail that a device signed itself out."""
    try:
        with get_session() as session:
            record_audit(
                session,
                action="LOGOUT_IDLE",
                table_name="(session)",
                summary=(
                    f"signed out after {Config.SESSION_IDLE_MINUTES} "
                    "minutes without activity"
                ),
                actor=username or "unknown",
            )
    except Exception:
        # A session is never left open because the trail could not be
        # written. The sign-out is the part that matters here.
        log.exception("Could not record an idle sign-out")


def sign_out_when_idle(username: str = "") -> ui.timer | None:
    """Watches this page, and ends the session once nobody is using it.

    Returns the timer, or None when the timeout is turned off.
    """
    if idle_limit_seconds() <= 0:
        return None

    ui.add_body_html(f"<script>{_WATCH_ACTIVITY_JS}</script>")

    warning = {"dialog": None}

    def close_warning() -> None:
        if warning["dialog"] is not None:
            warning["dialog"].close()
            warning["dialog"] = None

    def stay_signed_in() -> None:
        close_warning()
        ui.run_javascript(
            f"window.__vectorActivityAt = Date.now();"
            f"try {{ localStorage.setItem('{STORAGE_KEY}',"
            f" String(Date.now())); }} catch (error) {{}}"
        )

    def end_session() -> None:
        close_warning()
        record_idle_sign_out(username)
        sign_out()
        ui.navigate.to("/")

    def warn() -> None:
        if warning["dialog"] is not None:
            return

        with ui.dialog().props("persistent") as dialog, ui.card().classes(
            "max-w-sm p-6"
        ):
            warning["dialog"] = dialog

            ui.label("Still there?").classes("text-lg font-bold mb-2")

            ui.label(
                f"Nothing has been touched on this device for "
                f"{Config.SESSION_IDLE_MINUTES} minutes, so VECTOR is "
                "about to sign out."
            ).classes("text-sm mb-2")

            ui.label(
                "Records already saved are kept. Anything typed into a "
                "form and not yet saved will be lost -- stay signed in "
                "and save it first."
            ).classes("text-sm text-[#F5B027] mb-4")

            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Sign out now", on_click=end_session).props("flat")
                ui.button(
                    "Stay signed in",
                    on_click=stay_signed_in,
                    color="var(--vsp-blue)",
                ).props("push").classes("text-[var(--vsp-white)]")

        dialog.open()

    async def check() -> None:
        try:
            idle_seconds = await ui.run_javascript(
                _IDLE_SECONDS_JS, timeout=5.0
            )
        except Exception:
            # A tab that has gone away, or a browser too busy to answer
            # in time. The next tick asks again; a session is never ended
            # because an answer went missing.
            return

        action = decide(idle_seconds or 0, idle_limit_seconds())
        if action == "end":
            end_session()
        elif action == "warn":
            warn()
        else:
            close_warning()

    return ui.timer(CHECK_EVERY_SECONDS, check)
