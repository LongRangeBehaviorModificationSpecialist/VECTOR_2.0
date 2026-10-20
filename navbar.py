#!/usr/bin/env python3

"""
navbar.py

Provides build_navbar() to be called at the top of every authenticated
page. Uses Quasar's button + menu pattern for dropdown navigation items.

The two dialog builders that used to live here -- confirm_new_case_dialog
and confirm_delete_dialog -- were written as shared helpers and never
adopted by any page. parts/crud.py now provides the real shared dialogs,
so they have been removed rather than left as a second, dead answer to
the same question.
"""

from nicegui import ui

from auth import is_authenticated
from idle import leave_when_signed_out, sign_out_when_idle
from live import refresh_on_change
from models import check_case_info
from program.config import STATIC_DIR


# ----- Dropdown Helper -----
def _nav_dropdown(
        label: str,
        items: list[tuple[str, callable]],
        icon: str | None = None,
        classes: str = "",
        props: str = "",
) -> None:
    """Creates a dropdown button in the navbar.

    Each item is a (label, callback) tuple.
    """
    with ui.button(
        label,
        icon=icon
    ).props(f"flat color=white {props}").classes(classes):
        with ui.menu():
            for item_label, callback in items:
                if item_label == "---":
                    ui.separator()
                else:
                    ui.menu_item(item_label, on_click=callback)


# ----- Unit logo -----
def static_url(filename: str) -> str | None:
    """The /static address of a file that is present, or None.

    The logo files are unit branding and are not distributed with the
    source, so a fresh checkout has none of them.

    A leading "/static/" or "static/" is accepted and ignored. That is
    the address a page writes by hand, and taking it literally would
    look for a file of that name inside static/, find nothing, and drop
    a logo that is sitting right there.
    """
    name = filename.lstrip("/")
    if name.startswith("static/"):
        name = name[len("static/"):]
    if (STATIC_DIR / name).is_file():
        return f"/static/{name}"
    return None


def unit_logo(filename: str, classes: str) -> None:
    """Shows a logo from static/, or nothing when the file is missing.

    Every logo sits beside a title, so leaving it out still leaves the
    page named -- where a missing file used to show a broken-image icon.
    """
    url = static_url(filename)
    if url:
        ui.image(url).classes(classes)


# ----- Main Navbar -----
# The pages, in the order they appear. One list serves the row of buttons
# on a wide screen and the menu button on a narrow one, so the two cannot
# drift apart.
NAV_PAGES = [
    ("Home", "/"),
    ("Case", "/cases"),
    ("Agents", "/agents"),
    ("Rooms", "/rooms"),
    ("Evidence", "/evidence"),
    ("People", "/persons"),
    ("Notes", "/notes"),
    ("Files", "/uploads"),
    ("Tools", "/links"),
    ("Reports", "/reports"),
]

HELP_PAGES = [
    ("Connect a Device", "/connect"),
    ("About App", "/about"),
    ("Help", "/help"),
]

# The row of page buttons wrapped onto as many as five lines on a phone,
# covering a fifth of the screen on every page, and onto two on a laptop.
# Below NAV_ROW_MIN_WIDTH the pages fold into one menu button instead. On
# a phone the badge shows just the case number and the account menu just
# its icon, so the whole bar stays on one line.
#
# Measured in a browser with the case badge, the account menu and a short
# name: the row needs 1,564 px with the roomy buttons below, and about
# 1,300 px once their padding is tightened. So the padding is tightened
# between NAV_ROW_MIN_WIDTH and NAV_ROW_ROOMY_WIDTH -- a laptop keeps the
# whole row rather than folding it away, and a wide screen keeps the
# roomier buttons.
#
# Everything is shown or hidden with VECTOR's own classes and !important:
# Quasar's utilities -- .block, .row -- are !important themselves, and sit
# in a layer that outranks this CSS.
NAV_ROW_MIN_WIDTH = 1320
NAV_ROW_ROOMY_WIDTH = 1600

_NAV_CSS = f"""
@media (max-width: {NAV_ROW_MIN_WIDTH - 0.02}px) {{
    .nav-wide {{ display: none !important; }}
}}
@media (min-width: {NAV_ROW_MIN_WIDTH}px) {{
    .nav-narrow {{ display: none !important; }}
}}
@media (min-width: {NAV_ROW_MIN_WIDTH}px) and (max-width: {NAV_ROW_ROOMY_WIDTH - 0.02}px) {{
    .nav-wide .q-btn {{
        padding-left: 8px !important;
        padding-right: 8px !important;
    }}
}}
@media (max-width: 599.98px) {{
    .nav-not-phone {{ display: none !important; }}
    .case-badge {{ padding: 4px 8px !important; font-size: 11px !important; }}
    .nav-brand {{ margin-right: 0 !important; }}
    .q-header {{
        column-gap: 4px !important;
        padding-left: 8px !important;
        padding-right: 8px !important;
    }}
}}
@media (min-width: 600px) {{
    .nav-phone {{ display: none !important; }}
}}
"""


def account_menu(is_admin: bool) -> list[tuple[str, str | None]]:
    """The account menu's (label, route) items; "---" is a separator."""
    items = []
    if is_admin:
        items += [
            ("Admin Panel", "/admin"),
            ("Audit Trail", "/audit"),
            ("---", None),
        ]
    items.append(("Logout", "/logout"))
    if is_admin:
        # The route refuses anyone else, so nobody else is offered a button
        # that does nothing. Stopping VECTOR ends every session.
        items.append(("Shutdown", "/shutdown"))
    return items


def _go(route: str | None):
    return (lambda: ui.navigate.to(route)) if route else None


def build_navbar(is_admin: bool = False, username: str = "Guest") -> None:
    """Builds the top navigation bar.

    Before sign-in it shows only the logo and the name. The buttons used to
    appear on the login page too, where every one of them led back to the
    login form, beside an account menu with nobody's name in it.

    Args:
        is_admin: Whether to show the administrator's items.
        username: The current user's display name.
    """
    ui.add_css(_NAV_CSS)

    with ui.header().classes("items-center bg-dark no-print"):

        # ----- Logo + Brand -----
        unit_logo("novadc_icac.ico", "w-[32px] h-[32px]")

        ui.link(
            "V·E·C·T·O·R",
            "https://novadcicac.vsp.virginia.gov/"
            ).classes("nav-brand text-white font-bold mr-6 no-underline"
        ).props("target=_blank")

        if not is_authenticated():
            return

        # Every signed-in page draws this bar, so this is the one place
        # that has to watch for a device nobody is using -- and for a
        # session ended from another device.
        sign_out_when_idle(username)
        leave_when_signed_out()

        # ----- Pages: a row of buttons on a wide screen... -----
        with ui.row().classes("nav-wide items-center gap-0 no-wrap"):
            for label, route in NAV_PAGES:
                ui.button(label, on_click=_go(route)).props(
                    "flat color=white"
                ).classes("py-3 px-5 hover-border-blue")
            _nav_dropdown(
                "Help",
                [(label, _go(route)) for label, route in HELP_PAGES],
                classes="p-3 hover-border-blue"
            )

        # ----- ...and one menu button on a narrow one -----
        _nav_dropdown(
            "",
            [(label, _go(route)) for label, route in NAV_PAGES]
            + [("---", None)]
            + [(label, _go(route)) for label, route in HELP_PAGES],
            icon="menu",
            classes="p-3 nav-narrow hover-border-blue",
            props='round dense aria-label="Menu"',
        )

        # ----- Active case -----
        # Centred between the menus, so an agent can see at a glance which
        # case an entry is going into. Only once signed in: the login page
        # answers anyone who can reach the port, and a case number is not
        # theirs to read.
        ui.space()

        @ui.refreshable
        def case_badge() -> None:
            case_info = check_case_info()
            if case_info:
                number = case_info["CASENUMBER"]
                ui.badge(
                    f"Case No.: {number}",
                    color="positive",
                ).classes("p-3 case-badge nav-not-phone")
                # Just the number on a phone, so the bar keeps to one line.
                ui.badge(
                    number,
                    color="positive"
                ).classes("p-3 case-badge nav-phone")
            else:
                ui.badge(
                    "No Active Case",
                    color="#ef4444",
                ).classes("p-3 case-badge")

        case_badge()
        # Follows a case opened or cleared on another device.
        refresh_on_change(case_badge.refresh)

        # ----- Spacer -----
        ui.space()

        # ----- Account menu -----
        # With the name on a wider screen, and just the icon on a phone.
        account_items = [
            (label, _go(route)) for label, route in account_menu(is_admin)
        ]
        _nav_dropdown(
            f"Welcome, {username}",
            account_items,
            icon="account_circle",
            classes="p-3 account-menu nav-not-phone hover-border-blue",
        )
        spoken_name = (username or "").replace('"', "")
        _nav_dropdown(
            "",
            account_items,
            icon="account_circle",
            props=f'round dense aria-label="Account menu for {spoken_name}"',
            classes="p-3 account-menu nav-phone hover-border-blue",
        )
