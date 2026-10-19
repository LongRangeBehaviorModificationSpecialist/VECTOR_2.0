#!/usr/bin/env python3

"""
reports_page.py

Each report renders as formatted HTML that prints exactly like the original
Flask templates. Uses window.print() for native browser printing.


Routes:
    /reports/agents            →  Agent list report
    /reports/rooms             →  Room report
    /reports/evidence          →  Detailed evidence report
    /reports/evidence_by_room  →  Evidence listed by room report
    /reports/evidence_basic    →  Basic evidence inventory (return copy) report
    /reports/persons           →  Person report
    /reports/notes             →  Notes report
    /reports/files             →  Files report


WORKFLOW FOR REPORT CREATION:

    (1) `print_<type>_report() function is called from the navbar button ->
    (2) That function calls `get_case_info()` ->
    (3) `build_<type>_report_html(active_case=active_case,
            <type>=<type>)` compiles the html string for report ->
        (a) `build_case_header_html(active_case, page_title, sub_title)`
        (b) `build_report_footer_html()`
    (4) `render_report_page()` is run with the output from step 3 (html_content)

"""

from html import escape
from nicegui import ui
import json
import re

from sqlalchemy import func

import clock
from failures import explain, log
import settings
from models import (
    get_session,
    Agents,
    Cases,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
)
from navbar import build_navbar, unit_logo
from auth import is_authenticated, get_current_user_name, get_is_admin
from utils import (
    CASE_TIME_FORMAT,
    CONFIRM_TIMEOUT,
    WARN_TIMEOUT,
    ZERO_TIMEOUT,
    evidence_number_key,
    get_case_info,
    get_print_date_time,
    parse_entered_date,
    set_redact_agent_report,
    set_report_print_date,
    room_display_key,
    room_label_key,
)

style = {
    "color": "#1C69A8",
    "props": "push",
    "classes": "w-70 p-6 hover-border-white"
}
report_buttons = {
    "0": {
        "text": "Print Agent List",
        "page_url": "/reports/agents",
    },
    "1": {
        "text": "Print Room List",
        "page_url": "/reports/check_rooms_agents",
    },
    "2": {
        "text": "Print Evidence List (Full)",
        "page_url": "/reports/evidence",
    },
    "3": {
        "text": "Print Evidence List (By Room)",
        "page_url": "/reports/evidence_by_room",
    },
    "4": {
        "text": "Print Evidence List (Basic)",
        "page_url": "/reports/evidence_basic",
    },
    "5": {
        "text": "Print Persons List",
        "page_url": "/reports/persons",
    },
    "6": {
        "text": "Print Notes List",
        "page_url": "/reports/notes",
    },
    "7": {
        "text": "Print File List",
        "page_url": "/reports/files",
    },
}

REDACTED = "[REDACTED]"
NOT_RECORDED = "[NOT RECORDED]"

# ----- HTML Escaping -----
def h(value) -> str:
    """Escapes a database value for safe interpolation into report HTML.

    Without this, a description containing "&" or "<" corrupts the
    printed exhibit list, and a "<script>" tag executes in the print
    window.
    """
    return escape("" if value is None else str(value))


def recorded(value) -> str:
    """Escaped text for a report cell, or a marker if nothing is recorded."""
    text = "" if value is None else str(value).strip()
    return h(value) if text else NOT_RECORDED


def open_report(url: str) -> None:
    """Opens a report."""
    ui.navigate.to(url)


def build_reports_page() -> None:
    """Report Page wrapper."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("items-center w-full mt-4 mb-4"):

        unit_logo("novadc_icac.png", "w-[150px] h-[150px] mb-4")

        with ui.row().classes("text-2xl font-normal text-center"):
            ui.label("V·E·C·T·O·R")
            ui.label("|").classes("font-bold text-[var(--vsp-blue)]")
            ui.label("Reports Page")

        _printed_date_switch()
        _redact_agent_report()

    _remind_about_end_time()

    # ----- First row of buttons -----
    # Contains buttons for the following reports :
    # (1) Print Agent List
    # (2) Print Room List
    # (3) Print Evidence List (Full)
    with ui.row().classes(
            "flex justify-center items-center gap-8 my-1 py-1 w-full"):

        for k, v in list(report_buttons.items())[0:3]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: open_report(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])

    # ----- Second row of buttons -----
    # Contains buttons for the following reports :
    # (1) Print Evidence List (By Room)
    # (2) Print Evidence List (Basic)
    # (3) Print Persons List
    with ui.row().classes(
            "flex justify-center items-center gap-8 my-1 py-1 w-full"):

        for k, v in list(report_buttons.items())[3:6]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: open_report(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])

    # ----- Third row of buttons -----
    # Contains buttons for the following reports :
    # (1) Print Notes List
    # (2) Print File List
    with ui.row().classes(
                "flex justify-center items-center gap-8 my-1 py-1 w-full"):

        for k, v in list(report_buttons.items())[6:]:
            ui.button(
                v["text"],
                on_click=lambda url=v["page_url"]: open_report(url),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])


def _printed_date_switch() -> None:
    """Whether each report says when it was printed.

    Off by default; it is this machine's choice, kept with its other settings,
    and every change is in the audit trail.
    """

    def on_change(event) -> None:
        try:
            set_report_print_date(bool(event.value), get_current_user_name())
        except Exception as err:
            log.exception("Could not change the printed-date setting")
            ui.notify(
                f"The setting was not changed.\n\n{explain(err)}",
                multi_line=True,
                classes="multi-line-notification",
                type="warning",
                timeout=ZERO_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return
        ui.notify(
            "Reports now show when they were printed."
            if event.value else
            "Reports no longer show when they were printed.",
            timeout=CONFIRM_TIMEOUT,
            position="bottom",
            close_button="OK",
        )

    ui.switch(
        "Show the date and time each report is printed",
        value=settings.report_print_date(),
        on_change=on_change,
    ).classes("text-sm text-[var(--vsp-gray)] mt-2")


def _redact_agent_report() -> None:
    """Whether the Agent List report hides agents' phone numbers and emails.

    Off by default; it is this machine's choice, kept with its other
    settings, and every change is in the audit trail.
    """

    def on_change(event) -> None:
        try:
            set_redact_agent_report(bool(event.value), get_current_user_name())
        except Exception as err:
            log.exception("Could not change the agent redaction setting")
            ui.notify(
                f"The setting was not changed.\n\n{explain(err)}",
                multi_line=True,
                classes="multi-line-notification",
                type="warning",
                timeout=ZERO_TIMEOUT,
                position="center",
                close_button="OK",
            )
            return
        ui.notify(
            "The Agent List now hides phone numbers and emails."
            if event.value else
            "The Agent List now shows phone numbers and emails.",
            timeout=CONFIRM_TIMEOUT,
            position="bottom",
            close_button="OK",
        )

    ui.switch(
        "Redact agent phone numbers and emails on the Agent List",
        value=settings.redact_agent_report(),
        on_change=on_change,
    ).classes("text-sm text-[var(--vsp-gray)]")


# ----- Order -----
# Item numbers and room labels are text. Ordered by the database, the
# return copy listed items 1, 10, 11, 12, 2, and room AA came between A
# and B.
def evidence_in_order(session) -> list:
    """Every evidence item, by item number as a person reads it."""
    return sorted(
        session.query(Evidence).all(),
        key=lambda item: evidence_number_key(item.EVIDNUM),
    )


def rooms_missing_agents() -> list[str]:
    """Labels of rooms where either agent field is blank.

    Returns:
        List of rooms where no Agent name is listed.
    """
    with get_session() as session:
        return [
            room.ROOMLABEL
            for room in rooms_in_order(session)
            if not (room.ROOMFIRSTAGENT or "").strip()
            or not (room.ROOMSECONDAGENT or "").strip()
        ]


def rooms_missing_agents_message(labels: list[str]) -> str:
    """Tells the user what to fix, without listing every room."""
    shown = ", ".join(labels[:10])
    if len(labels) > 10:
        shown += f", and {len(labels) - 10} more"
    return (
        "The Room List cannot be printed until a first and second agent "
        "are entered for every room.\n\n"
        f"Rooms missing an agent => {shown}.\n\n"
        "Open the Rooms page and enter both agent names for each."
    )


def rooms_in_order(session) -> list:
    """Every room, A to Z and then AA."""
    return sorted(
        session.query(Rooms).all(),
        key=lambda room: room_label_key(room.ROOMLABEL),
    )


def rooms_with_item_counts(session) -> list[tuple[str, int]]:
    """Each room evidence was found in, with its item count, in label order."""
    counts = (
        session.query(
            Evidence.EVIDLOCROOM,
            func.count(Evidence.EVIDLOCROOM)
        )
        .group_by(Evidence.EVIDLOCROOM)
        .all()
    )
    return sorted(
        ((room, count) for room, count in counts),
        key=lambda pair: room_display_key(pair[0]),
    )


def fill_case_end_time(now_text: str | None = None) -> tuple[bool, str]:
    """Sets the open case's end time to now, unless that would be wrong.

    Returns (saved, message). Leaves the case alone when it already has an
    end time -- another device may have filled it in -- and when its start
    time is later than now, which means the start time needs checking.
    """
    now_text = now_text or clock.case_time_now()
    with get_session() as session:
        case = session.query(Cases).order_by(Cases.Z_PK).first()
        if case is None:
            return False, "There is no open case."
        if (case.CASEDATETIMEEND or "").strip():
            return False, (
                f"The case already has an end date/time: "
                f"{case.CASEDATETIMEEND}."
            )
        started = parse_entered_date(
            case.CASEDATETIMEBEGIN,
            CASE_TIME_FORMAT
        )
        ended = parse_entered_date(now_text, CASE_TIME_FORMAT)
        if started is not None and ended is not None and ended < started:
            return False, (
                f"The case starts at {case.CASEDATETIMEBEGIN}, which "
                f"is later than the time now on this machine ({now_text}), "
                "so the end time was not filled in. Check the start time "
                "on the Case page."
            )
        case.CASEDATETIMEEND = now_text
    return True, f"The case's end date/time is now {now_text}."


def _remind_about_end_time() -> None:
    """Asks about the case's end time when it has none.

    Every report's header prints when the search began and ended, and a
    case with no end time printed that line blank. Fill it in from this
    machine's clock, or carry on without it.
    """
    with get_session() as session:
        case = session.query(Cases).order_by(Cases.Z_PK).first()
        if case is None or (case.CASEDATETIMEEND or "").strip():
            return
        number = case.CASENUMBER
        begin = case.CASEDATETIMEBEGIN or "at a time not recorded"

    with ui.dialog() as reminder, ui.card().classes("max-w-md p-6"):
        ui.label("This case has no end date/time yet").classes(
            "text-lg font-bold text-[var(--vsp-blue)]"
        )
        ui.label(
            f"Case {number} started {begin}. Every report prints the ending "
            "date and time, and that line stays blank until one is entered."
        ).classes("text-sm text-[var(--vsp-gray)]")

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(
                "Continue without it",
                on_click=reminder.close,
                color="transparent",
            ).props("flat").classes("p-3 hover-border-blue")

            def fill_in_now() -> None:
                try:
                    saved, message = fill_case_end_time()
                except Exception as err:
                    log.exception("Could not fill in the case's end time")
                    ui.notify(
                        f"Could not save the end time.\n\n{explain(err)}",
                        multi_line=True,
                        type="warning",
                        timeout=ZERO_TIMEOUT,
                        position="center",
                        close_button="OK",
                    )
                    return

                reminder.close()
                ui.notify(
                    message,
                    multi_line=True,
                    type="" if saved else "warning",
                    timeout=CONFIRM_TIMEOUT if saved else 0,
                    position="bottom" if saved else "center",
                    close_button="OK",
                )

            ui.button(
                "Fill in with current date/time",
                icon="schedule",
                on_click=fill_in_now,
                color="var(--vsp-blue)",
            ).props("push").classes("p-3 hover-border-white")

    reminder.open()


def render_report_page(html_content: str, report_name: str = "") -> None:
    """Wraps report HTML with navigation and print button.

    The button sits outside the report: the print window copies
    everything inside #report-container, and with the button in there it
    showed a second "Print Report" -- as "printPrint Report", its icon's
    name standing in for an icon the print window has no font for.
    """
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):

        with ui.row().classes(
            "w-full no-print items-center justify-center py-3"):
            print_button = ui.button(
                "Print Report",
                color="#1C69A8").props("push icon=print"
            ).classes("w-70 p-6 hover-border-white")
                    # p-3 mb-4 no-print hover-border-white

        is_valid, errors = validate_case_for_report()
        if is_valid:
            # Opened in the browser by the click itself. Opened from the
            # server after the click had made the round trip, the window
            # was not the click's any more, and pop-up blockers -- Safari
            # on an iPad by default -- stopped it.
            case_number = (get_case_info() or {}).get("CASENUMBER", "")
            print_button.on(
                "click",
                js_handler=print_window_script(report_name, case_number),
            )
        else:
            print_button.on_click(lambda: show_validation_errors(errors))

        with ui.element().props("id='report-container'").classes("w-full max-w-2xl my-12"):
            ui.html(html_content)


def validate_case_for_report() -> tuple[bool, list[str]]:
    """Validates that the single active case has all required fields
    for reporting.

    Returns:
        (is_valid, list_of_error_messages).
    """

    errors = []

    with get_session() as session:

        case = session.query(Cases).first()

        if not case:
            errors.append(
                "No case exists in the database. Create a case first."
            )
            return False, errors

        # Check Case Number
        if not case.CASENUMBER or not str(case.CASENUMBER).strip():
            errors.append("Case Number is required.")

        # Check Location
        if not case.LOCATION or not str(case.LOCATION).strip():
            errors.append("Location is required.")

        # Check Jurisdiction
        if not case.JURISDICTION or not str(case.JURISDICTION).strip():
            errors.append("Jurisdiction is required.")

        # Check Start Date/Time (required for complete reports)
        if not case.CASEDATETIMEBEGIN:
            errors.append("Start Date/Time is required for reports.")

    return (len(errors) == 0, errors)


def show_validation_errors(errors: list[str]) -> None:
    """Displays validation errors as a NiceGUI notification."""
    if len(errors) == 1:
        ui.notify(
            errors[0],
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )
    else:
        error_text = "\n".join(f"• {err}" for err in errors)
        ui.notify(
            f"Cannot generate report — missing information:\n\n{error_text}.",
            type="warning",
            timeout=WARN_TIMEOUT,
            position="center",
            close_button="OK",
        )


# ----- Common Print Styles -----
COMMON_STYLES = """
@page {
    margin-top: 0.65in;
    margin-right: 0.5in;
    margin-bottom: 0.75in;
    margin-left: 0.5in;

    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        color: #000;
        font-family: "Arial", sans-serif;
        font-size: 10pt;
        font-weight: bold;
        margin-bottom: 0.5in;
    }
    /*
    @bottom-left {
        content: "Confidential";
        font-family: "Arial", sans-serif;
        font-size: 9pt;
        font-weight: bold;
        color: #FF0000;
    }
    */
        }

        @media print {
    .no-print {
        display: none !important;
    }
    body {
        background: white !important;
        color: black !important;
    }
    .top-table .agent-table thead tr th.agent-table-header,
    .top-table .note-table thead tr th.note-table-header,
    .top-table .person-table thead tr th.person-table-header,
    .top-table .room-table thead tr th.room-table-header {
        border-collapse: collapse;
        break-inside: avoid !important;
        page-break-inside: avoid !important;
    }


    .top-table .agent-table thead tr th.agent-table-header,
    .top-table .note-table thead tr th.note-table-header,
    .top-table .person-table thead tr th.person-table-header,
    .top-table .room-table thead tr th.room-table-header {
        padding: 5px 5px 3px 5px;
    }


    .header-table tr td.header-data-value,
    .evid-table-room-row-label,
    .top-table .evid-table tr td.evid-table-item-label {
        font-family: "Times New Roman", Times, serif;
        font-size: 11pt;
    }

    .header-table tr td.header-data-label,
    .header-table tr td.header-data-value {
        vertical-align: "bottom";
    }

    .agent-table thead,
    .note-table thead,
    .room-table thead,
    .person-table thead {
        display: table-header-group; /* repeads <thead> on each printed page */
    }

    .top-table .agent-table tbody tr td.agent-table-data,
    .top-table .evid-table tr td.evid-data-value,
    .top-table .file-table tr td.file-data-value,
    .top-table .note-table tbody tr td.note-table-data,
    .top-table .person-table tbody tr td.person-table-data,
    .top-table .room-table tbody tr td.room-table-data {
        font-family: "Times New Roman", Times, serif;
        font-size: 11pt;
        padding: 5px 5px 3px 5px;
        vertical-align: "center";
    }

    .top-table .evid-table-top tr td.evid-table-item-row {
        background-color: #FFFFFF;
        color: #000000;
        font-size: 10pt;
    }

    .top-table .evid-table tr,
    .top-table .file-table tr {
        height: 1.45rem;
    }

    .top-table .header-table tr td.header-data-label,
    .report-title p.fs-5,
    .top-table .evid-table tr td.evid-data-label,
    .top-table .file-table tr td.file-data-label {
        font-size: 10pt;
    }

    .top-table .evid-table tr td.evid-data-label-header {
        font-size: 10pt;
        font-weight: bold;
        padding: 0px 10px;
        width: 30%
    }

    .top-table .evid-table tr td.evid-data-value,
    .top-table .evid-table tr td.file-data-value {
        font-size: 12pt;
        padding: 0pt 6pt;
    }

    .top-table .evid-table tr td.spacer-row {
        border-left: 1px solid transparent;
        border-right: 1px solid transparent;
    }

    .bold {
        font-weight: bold;
    }
}

:root {
    --gray: #D1D5DC;
}

body {
    box-sizing: border-box;
    color: black;
    font-family: "Arial", sans-serif;
    margin: 0;
    padding: 1em;
}

.bold { font-weight: bold; }

.top-row {
    background-color: var(--gray);
}

.report-title {
    text-align: center;
    margin-bottom: 1em;
}

.font-08 { font-size: 8pt; }
.font-09 { font-size: 9pt; }
.font-10 { font-size: 10pt; }
.font-11 { font-size: 11pt; }
.font-12 { font-size: 12pt; }
.font-13 { font-size: 13pt; }
.font-16 { font-size: 16pt; }

.fs-3 {
    font-weight: bold;
    margin: 1em auto 0.25em auto;
    text-align: center;
}

.fs-5 {
    margin: 0 auto 2em auto;
    text-align: center;
}

td.px-6 {
    padding: 0px 8px;
}

.top-table {
    padding-left: 5%;
    padding-right: 5%;
}

.header-table {
    border-collapse: collapse;
    margin-bottom: 2em;
    margin-right: auto;
    margin-left: auto;
    table-layout: fixed;
    width: 100%;
}

td.header-data-label {
    font-size: 11pt;
    padding: 5px 10px;
    width: 30%;
}

td.header-data-value {
    border-bottom: 1px dotted black;
    font-family: "Times New Roman", Times, serif;
    padding: 0px 10px;
    vertical-align: bottom;
    width: 70%;
}

/* Shared table styles */
.agent-table,
.note-table,
.room-table,
.person-table {
    border-collapse: collapse;
    width: 100%;
}

.agent-table-header,
.note-table-header,
.room-table-header,
.person-table-header {
    border-collapse: collapse;
    font-weight: 650;
    text-align: left;
    white-space: nowrap;
}

/* The Room ID heading must never wrap; the column shrinks to fit it.
.room-table-header-id {
    white-space: nowrap;
    width: 1%;
    text-align: left;
}*/

/*
.room-table td.room-id-cell {
    padding-right: 25pt;
}
*/

.agent-table thead tr,
.note-table thead tr,
.room-table thead tr,
.person-table thead tr {
    border-top: 0px solid black;
    border-bottom: 1px solid black;
}

.no-data {
    border-bottom: 1px dotted black;
    font-weight: bold;
    height: 6em;
    padding: 0pt;
    text-align: center;
    vertical-align: center;
}

.agent-table-data,
.note-table-data,
.room-table-data,
.person-table-data {
    border-bottom: 1px dotted black;
    height: 1.85em;
    padding: 0pt 5pt;
    vertical-align: center;
}

.evid-table-top,
.evid-table,
.file-table {
    border-collapse: collapse;
    margin-left: auto;
    margin-right: auto;
    table-layout: fixed;
    width: 100%;
}

.evid-table,
.file-table {
    margin-bottom: 1.5em;
}

.evid-table-top td,
.evid-table td,
.file-table td {
    border: 1px solid black;
}

.evid-table-top td {
    background-color: #1E293B;
    color: #CBD5E1;
}

.evid-table td,
.file-table td {
    height: 1.5em;
}

.evid-table-item-row {
    font-size: 10pt;
    font-weight: bold;
    height: 1.65em;
    padding: 2px 10px;
    text-align: left;
}

.top-table .evid-table tr td.spacer-row {
    border-left: 1px solid transparent;
    border-right: 1px solid transparent;
}

td.evid-data-label-header,
td.evid-data-label,
td.file-data-label {
    font-weight: normal;
    padding: 0px 10px;
    width: 30%;
}

td.evid-data-value,
td.file-data-value {
    font-family: "Times New Roman", Times, serif;
    padding: 0px 10px;
    width: 70%;
    word-wrap: break-word;
}

.end {
    font-weight: 600;
    margin-top: 2rem;
    text-align: center;
}
"""


def build_case_header_html(
        active_case: dict | None,
        page_title: str,
        sub_title: str
) -> str:
    """Generates the standard report title + case info header HTML."""
    if not active_case:
        active_case = get_case_info()

    if not active_case:
        ui.notify(
            "No active case — please create a case first.",
            type="warning",
            timeout=WARN_TIMEOUT,
            close_button="OK",
            position="center",
        )
        # Redirect to case creation page if no active case
        ui.navigate.to("/cases")
        # Stop here: without this the header below subscripts None and
        # the whole report route returns a 500 instead of redirecting.
        return ""

    # Off unless asked for on the Reports page: a time on the page that
    # is neither when the search began nor when it ended invites the
    # question of which one it is.
    printed_row = ""
    if settings.report_print_date():
        printed_row = f"""
            <tr>
                <td class="header-data-label font-11">Report Printed Date:</td>
                <td class="header-data-value font-11">{get_print_date_time()}</td>
            </tr>"""

    report_header_table = f"""
    <div class="top-table">
        <table class="header-table">
            <tr>
                <td class="header-data-label font-11">Investigation Number:</td>
                <td class="header-data-value font-11">{h(active_case["CASENUMBER"])}</td>
            </tr>
            <tr>
                <td class="header-data-label font-11">Site Address:</td>
                <td class="header-data-value font-11">{h(active_case["LOCATION"])}</td>
            </tr>
            <tr>
                <td class="header-data-label font-11">Jurisdiction:</td>
                <td class="header-data-value font-11">{h(active_case["JURISDICTION"])}</td>
            </tr>
            <tr>
                <td class="header-data-label font-11">Starting Date and Time:</td>
                <td class="header-data-value font-11">
                    {h(active_case["CASEDATETIMEBEGIN"])}
                </td>
            </tr>
            <tr>
                <td class="header-data-label font-11">Ending Date and Time:</td>
                <td class="header-data-value font-11">
                    {h(active_case["CASEDATETIMEEND"])}
                </td>
            </tr>
            {printed_row}
        </table>
    </div>"""

    return f"""
    <div class="report-title">
        <p class="fs-3 font-11">{page_title}</p>
        <p class="fs-5 font-8">{sub_title}</p>
    </div>
    {report_header_table}
    """


def build_report_footer_html() -> str:
    """Generates the standard END OF REPORT footer."""

    return """
    <p class="end font-11">
        &ndash;&ensp;&ndash;&ensp;END OF REPORT&ensp;&ndash;&ensp;&ndash;
    </p>
    """


def build_agents_report_html(
        active_case: dict,
        agents: list,
        redact_contacts: bool = False) -> str:
    """Generates the complete HTML for the Agent List report.

    With redact_contacts, each agent's phone and email are replaced by a
    marker; the real values are never put into the HTML.
    """

    def contact(value) -> str:
        return REDACTED if redact_contacts else h(value)

    agent_rows = "".join([f"""
        <tr>
            <td class="agent-table-data font-10">{h(a["AGENTNAME"])}</td>
            <td class="agent-table-data font-10">{h(a["AGENTPARENTAGENCY"])}</td>
            <td class="agent-table-data font-10">{h(a["AGENTPRIMARYROLE"])}</td>
            <td class="agent-table-data font-10">{contact(a["AGENTPHONE"])}</td>
            <td class="agent-table-data font-10">{contact(a["AGENTEMAIL"])}</td>
        </tr>"""
        for a in agents]
    )

    header = build_case_header_html(
        active_case,
        page_title="INVESTIGATORS AT SEARCH WARRANT SITE",
        sub_title="",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Agent List Report</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    <div class="top-table">
        <table class="agent-table">
            <thead>
                <tr>
                    <th class="agent-table-header font-10">Agent Name</th>
                    <th class="agent-table-header font-10">Agency</th>
                    <th class="agent-table-header font-10">Primary Role</th>
                    <th class="agent-table-header font-10">Phone Number</th>
                    <th class="agent-table-header font-10">Email</th>
                </tr>
            </thead>
            <tbody>
                {agent_rows}
            </tbody>
        </table>
    </div>
    {footer}
</body>
</html>"""


def build_evidence_report_html(active_case: list, evidence: list) -> str:
    """Generates the complete HTML for the detailed Evidence report.

    Each item is displayed as vertical label/value rows with ALL fields.

    This is the AGENT COPY.
    """

    evid_rows = "".join([f"""
        <table class="evid-table-top">
            <tr>
                <td class="evid-table-item-row">
                    Item #:&ensp;{h(e["EVIDNUM"])}
                </td>
            </tr>
        </table>
        <table class="evid-table">
            <tr>
                <td class="evid-data-label">Quantity:</td>
                <td class="evid-data-value px-6">{h(e["EVIDQTY"])}</td>
            </tr>
            <tr>
                <td class="evid-data-label">Description:</td>
                <td class="evid-data-value px-6">{h(e["EVIDDESC"])}</td>
            </tr>
            <tr>
                <td class="evid-data-label">Model #:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDMODELNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Serial #:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDSERIALNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Location:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDLOCROOM"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Where Found:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDLOCROOMDETAIL"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Located By:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDFOUNDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Witnessed By:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDFOUNDBYWITNESS"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Photographed:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDPICTAKEN"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Item Triaged:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDTRIAGED"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Item Triaged By:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDTRIAGEDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Notes:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDNOTE"])}
                </td>
            </tr>
        </table>"""
            for e in evidence
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="FULL EVIDENCE INVENTORY LIST",
        sub_title="",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Evidence Inventory List</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    <div class="top-table">
        {evid_rows}
    </div>
    {footer}
</body>
</html>"""


def build_evidence_by_room_report_html(
        active_case: list,
        evidence: list,
        unique_rooms: list
) -> str:
    """Generates the complete HTML for the Evidence By Room report.

    Groups evidence items under room headers with count of items found in
    each room.
    """

    space = " "
    double_space = "  "

    room_tables = ""

    for room in unique_rooms:
        room_name = room[0]
        item_count = room[1]

        # Singular vs plural. Escaped once, where it is printed: escaped
        # here as well, "Kid's Room" printed as "Kid&#x27;s Room".
        label = (
            f"{room_name}{space}:{double_space}({item_count} "
            f"{'item' if item_count == 1 else 'items'})"
        )

        # Filter evidence items for this room
        room_items = [e for e in evidence if e["EVIDLOCROOM"] == room_name]
        evid_rows = "".join([f"""
            <tr>
                <td colspan="2" class="spacer-row"></td>
            </tr>
            <tr class="top-row">
                <td class="evid-data-label-header">Item No.:</td>
                <td class="evid-data-value px-6 bold">
                    {h(e["EVIDNUM"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Quantity:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDQTY"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Description:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDDESC"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Model #:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDMODELNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Serial #:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDSERIALNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Location:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDLOCROOM"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Where Found:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDLOCROOMDETAIL"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Located By:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDFOUNDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Witnessed By:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDFOUNDBYWITNESS"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Photographed:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDPICTAKEN"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Item Triaged:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDTRIAGED"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Item Triaged By:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDTRIAGEDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evid-data-label">Notes:</td>
                <td class="evid-data-value px-6">
                    {h(e["EVIDNOTE"])}
                </td>
            </tr>
            """
            for e in room_items
        ]
    )

        room_tables += f"""
        <div class="top-table">
            <table class="evid-table-top">
                <tr>
                    <td class="evid-table-item-row">
                        {h(label)}
                    </td>
                </tr>
            </table>
            <table class="evid-table">
                {evid_rows}
            </table>
        </div>
        <br />"""

    header = build_case_header_html(
        active_case,
        page_title="EVIDENCE FOUND LIST BY ROOM",
        sub_title="",
    )

    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Evidence Found By Room</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    {room_tables}
    {footer}
</body>
</html>"""


def build_basic_evidence_report_html(
        active_case: list,
        evidence: list
) -> str:
    """Generates the complete HTML for the Basic Evidence report.

    Each item shows only Item#, Quantity, Description, Model#, and Serial#.

    This is the "RETURN COPY" version.
    """

    evid_rows = "".join([f"""
            <table class="evid-table-top">
                <tr>
                    <td class="evid-table-item-row">
                        Item #:&ensp;{h(e["EVIDNUM"])}
                    </td>
                </tr>
            </table>
            <table class="evid-table">
                <tr>
                    <td class="evid-data-label">Description:</td>
                    <td class="evid-data-value px-6">
                        {h(e["EVIDDESC"])}
                    </td>
                </tr>
                <tr>
                    <td class="evid-data-label">Model #:</td>
                    <td class="evid-data-value px-6">
                        {h(e["EVIDMODELNUMBER"])}
                    </td>
                </tr>
                <tr>
                    <td class="evid-data-label">Serial #:</td>
                    <td class="evid-data-value px-6">
                        {h(e["EVIDSERIALNUMBER"])}
                    </td>
                </tr>
            </table>"""
            for e in evidence
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="SEARCH INVENTORY AND RETURN",
        sub_title="",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Basic Evidence Inventory List</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    <div class="top-table">
        {evid_rows}
    </div>
    {footer}
</body>
</html>"""


def build_rooms_report_html(active_case: list, rooms: list) -> str:
    """Generates the complete HTML for the Room List report."""

    room_rows = "".join([f"""
            <tr>
                <td class="room-table-data room-id-cell">
                    {h(r["ROOMLABEL"])}
                </td>
                <td class="room-table-data font-10">{h(r["ROOMDESC"])}</td>
                <td class="room-table-data font-10">{recorded(r["ROOMFIRSTAGENT"])}</td>
                <td class="room-table-data font-10">{recorded(r["ROOMSECONDAGENT"])}</td>
                <td class="room-table-data font-10">{h(r["ROOMNOTE"])}</td>
            </tr>
            """
            for r in rooms
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="ROOM LIST",
        sub_title="",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Room List Report</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    <div class="top-table">
        <table class="room-table">
            <thead>
                <tr>
                    <th class="room-table-header room-table-header-id font-10">Room ID</th>
                    <th class="room-table-header font-10">Room Name</th>
                    <th class="room-table-header font-10">Searched By (1)</th>
                    <th class="room-table-header font-10">Searched By (2)</th>
                    <th class="room-table-header font-10">Notes</th>
                </tr>
            </thead>
            <tbody>
                {room_rows}
            </tbody>
        </table>
    </div>
    {footer}
</body>
</html>"""


def build_persons_report_html(active_case: list, persons: list) -> str:
    """Generates the complete HTML for the Person List report."""

    if not persons:
        person_rows = """
        <tr>
            <td class="no-data font-10" colspan="5">[ NO DATA FOUND ]</td>
        </tr>
        """
    else:
        person_rows = "".join([f"""
        <tr>
            <td class="person-table-data font-10">{h(p["PERSONNAME"])}</td>
            <td class="person-table-data font-10">{h(p["PERSONDOB"])}</td>
            <td class="person-table-data font-10">{h(p["PERSONADDRESS"])}</td>
            <td class="person-table-data font-10">{h(p["PERSONPHONE"])}</td>
            <td class="person-table-data font-10">{h(p["PERSONNOTE"])}</td>
        </tr>
        """
            for p in persons
            ]
        )

    header = build_case_header_html(
        active_case,
        page_title="PERSONS LIST",
        sub_title="",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Person List</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    <div class="top-table">
        <table class="person-table">
            <thead>
                <tr>
                    <th class="person-table-header font-10">Person Name</th>
                    <th class="person-table-header font-10">DOB</th>
                    <th class="person-table-header font-10">Address</th>
                    <th class="person-table-header font-10">Phone #</th>
                    <th class="person-table-header font-10">Notes</th>
                </tr>
            </thead>
            <tbody>
                {person_rows}
            </tbody>
        </table>
    </div>
    {footer}
</body>
</html>"""


def build_notes_report_html(active_case: list, notes: list) -> str:
    """Generates the complete HTML for the Notes report."""

    if not notes:
        note_rows = """
        <tr>
            <td class="no-data font-10" colspan="4">[ NO DATA FOUND ]</td>
        </tr>
        """
    else:
        note_rows = "".join([f"""
        <tr>
            <td class="note-table-data font-10">{h(n["NOTEDATETIME"])}</td>
            <td class="note-table-data font-10">{h(n["NOTEDATETIMEUPDATED"])}</td>
            <td class="note-table-data font-10">{h(n["NOTEAUTHOR"])}</td>
            <td class="note-table-data font-10">{h(n["NOTETEXT"])}</td>
        </tr>
        """
            for n in notes
            ]
        )

    header = build_case_header_html(
        active_case,
        page_title="NOTES LIST",
        sub_title="",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Search Warrant Notes</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    <div class="top-table">
        <table class="note-table">
            <thead>
                <tr>
                    <th class="note-table-header font-10">Date/Time Added</th>
                    <th class="note-table-header font-10">Date/Time Updated</th>
                    <th class="note-table-header font-10">Author</th>
                    <th class="note-table-header font-10">Text</th>
                </tr>
            </thead>
            <tbody>
                {note_rows}
            </tbody>
        </table>
    </div>
    {footer}
</body>
</html>"""


def build_files_report_html(active_case: list, files: list) -> str:
    """Generates the complete HTML for the File List report.

    Each item shows only FILENAME, FILEMIMETYPE, FILEUPLOADDATE,
    FILEUPLOADEDBY, and FILESHA256.
    """

    file_rows = "".join([f"""
        <table class="file-table">
            <tr class="top-row">
                <td class="file-data-label bold">File No.:</td>
                <td class="file-data-value px-6 bold">
                    {h(f["Z_PK"])}
                </td>
            </tr>
            <tr>
                <td class="file-data-label">File Name:</td>
                <td class="file-data-value px-6">
                    {h(f["FILENAME"])}
                </td>
            </tr>
            <tr>
                <td class="file-data-label">File Type:</td>
                <td class="file-data-value px-6">
                    {h(f["FILEMIMETYPE"])}
                </td>
            </tr>
            <tr>
                <td class="file-data-label">Uploaded Date/Time:</td>
                <td class="file-data-value px-6">
                    {h(f["FILEUPLOADDATE"])}
                </td>
            </tr>
            <tr>
                <td class="file-data-label">Uploaded By:</td>
                <td class="file-data-value px-6">
                    {h(f["FILEUPLOADEDBY"])}
                </td>
            </tr>
            <tr>
                <td class="file-data-label">File Hash (SHA256):</td>
                <td class="file-data-value px-6">
                    {h(f["FILESHA256"])}
                </td>
            </tr>
        </table>"""
            for f in files
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="ATTACHED FILES LIST",
        sub_title="",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Attached Files List</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    <div class="top-table">
        {file_rows}
    </div>
    {footer}
</body>
</html>"""


@ui.page("/reports/agents")
def print_agents_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:

        active_case = get_case_info()

        agents = [
            {
                "AGENTNAME": a.AGENTNAME,
                "AGENTPARENTAGENCY": a.AGENTPARENTAGENCY,
                "AGENTPRIMARYROLE": a.AGENTPRIMARYROLE,
                "AGENTPHONE": a.AGENTPHONE,
                "AGENTEMAIL": a.AGENTEMAIL,
                "AGENTNOTE": a.AGENTNOTE or "",
            }
            for a in session.query(Agents).all()
        ]

    html = build_agents_report_html(
        active_case=active_case,
        agents=agents,
        redact_contacts=settings.redact_agent_report(),
    )

    render_report_page(html_content=html, report_name="Agent List")


@ui.page("/reports/evidence")
def print_evidence_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:

        active_case = get_case_info()

        evidence = [
            {
                "EVIDNUM": e.EVIDNUM,
                "EVIDQTY": e.EVIDQTY,
                "EVIDDESC": e.EVIDDESC,
                "EVIDMODELNUMBER": e.EVIDMODELNUMBER or "N/A",
                "EVIDSERIALNUMBER": e.EVIDSERIALNUMBER or "N/A",
                "EVIDLOCROOM": e.EVIDLOCROOM,
                "EVIDLOCROOMDETAIL": e.EVIDLOCROOMDETAIL,
                "EVIDFOUNDBY": e.EVIDFOUNDBY,
                "EVIDFOUNDBYWITNESS": e.EVIDFOUNDBYWITNESS,
                "EVIDPICTAKEN": e.EVIDPICTAKEN,
                "EVIDTRIAGED": e.EVIDTRIAGED,
                "EVIDTRIAGEDBY": e.EVIDTRIAGEDBY or "N/A",
                "EVIDNOTE": e.EVIDNOTE or "N/A",
            }
            for e in evidence_in_order(session)
        ]

    html = build_evidence_report_html(
        active_case=active_case,
        evidence=evidence
    )

    render_report_page(html_content=html, report_name="Evidence List (Full)")


@ui.page("/reports/evidence_by_room")
def print_evidence_by_room_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()

        unique_rooms_list = rooms_with_item_counts(session)

        evidence = [
            {
                "EVIDNUM": e.EVIDNUM,
                "EVIDQTY": e.EVIDQTY,
                "EVIDDESC": e.EVIDDESC,
                "EVIDMODELNUMBER": e.EVIDMODELNUMBER or "N/A",
                "EVIDSERIALNUMBER": e.EVIDSERIALNUMBER or "N/A",
                "EVIDLOCROOM": e.EVIDLOCROOM,
                "EVIDLOCROOMDETAIL": e.EVIDLOCROOMDETAIL,
                "EVIDFOUNDBY": e.EVIDFOUNDBY,
                "EVIDFOUNDBYWITNESS": e.EVIDFOUNDBYWITNESS,
                "EVIDPICTAKEN": e.EVIDPICTAKEN,
                "EVIDTRIAGED": e.EVIDTRIAGED,
                "EVIDTRIAGEDBY": e.EVIDTRIAGEDBY or "N/A",
                "EVIDNOTE": e.EVIDNOTE or "N/A",
            }
            for e in evidence_in_order(session)
        ]

    html = build_evidence_by_room_report_html(
        active_case=active_case,
        evidence=evidence,
        unique_rooms=unique_rooms_list,
    )

    render_report_page(html_content=html, report_name="Evidence List (By Room)")


@ui.page("/reports/evidence_basic")
def print_basic_evidence_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:

        active_case = get_case_info()

        evidence = [
            {
                "EVIDNUM": e.EVIDNUM,
                "EVIDQTY": e.EVIDQTY,
                "EVIDDESC": e.EVIDDESC,
                "EVIDMODELNUMBER": e.EVIDMODELNUMBER or "N/A",
                "EVIDSERIALNUMBER": e.EVIDSERIALNUMBER or "N/A",
            }
            for e in evidence_in_order(session)
        ]

    html = build_basic_evidence_report_html(
        active_case=active_case,
        evidence=evidence
    )

    render_report_page(html_content=html, report_name="Evidence List (Basic)")


@ui.page("/reports/check_rooms_agents")
def check_rooms_agents():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    missing = rooms_missing_agents()
    if missing:
        build_navbar(
            is_admin=get_is_admin(),
            username=get_current_user_name(),
        )
        with ui.column().classes("items-center w-full mt-8 gap-4"):
            ui.label(rooms_missing_agents_message(missing)).classes(
                "text-lg text-center whitespace-pre-line"
            )

        with ui.row().classes(
            "flex justify-center items-center gap-8 my-1 py-12 w-full"):
            ui.button(
                "Print Report Without Names",
                on_click=lambda: ui.navigate.to("/reports/rooms"),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])

            ui.button(
                "Go to Rooms",
                on_click=lambda: ui.navigate.to("/rooms"),
                color=style["color"],
            ).props(style["props"]).classes(style["classes"])
        return
    else:
        ui.navigate.to("/reports/rooms")


@ui.page("/reports/rooms")
def print_rooms_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        rooms = [
            {
                "ROOMLABEL": r.ROOMLABEL,
                "ROOMDESC": r.ROOMDESC,
                "ROOMFIRSTAGENT": r.ROOMFIRSTAGENT,
                "ROOMSECONDAGENT": r.ROOMSECONDAGENT,
                "ROOMNOTE": r.ROOMNOTE or "N/A",
            }
            for r in rooms_in_order(session)
        ]

    ui.add_head_html(
        "<title>V·E·C·T·O·R | Room List Report</title>",
        shared=True,
    )

    html = build_rooms_report_html(
        active_case=active_case,
        rooms=rooms
    )

    render_report_page(html_content=html, report_name="Room List")


@ui.page("/reports/persons")
def print_persons_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        persons = [
            {
                "PERSONNAME": p.PERSONNAME,
                "PERSONDOB": p.PERSONDOB or "N/A",
                "PERSONADDRESS": p.PERSONADDRESS or "N/A",
                "PERSONPHONE": p.PERSONPHONE or "N/A",
                "PERSONNOTE": p.PERSONNOTE or "",
            }
            for p in session.query(Persons).order_by(Persons.PERSONNAME).all()
        ]

    html = build_persons_report_html(
        active_case=active_case,
        persons=persons
    )

    render_report_page(html_content=html, report_name="Persons List")


@ui.page("/reports/notes")
def print_notes_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        notes = [
            {
                "NOTEDATETIME": n.NOTEDATETIME,
                "NOTEDATETIMEUPDATED": n.NOTEDATETIMEUPDATED or "N/A",
                "NOTEAUTHOR": n.NOTEAUTHOR,
                "NOTETEXT": n.NOTETEXT or "",
            }
            # In the order written: see the note on notes_page.SPEC.
            for n in session.query(Notes).order_by(Notes.Z_PK).all()
        ]

    html = build_notes_report_html(
        active_case=active_case,
        notes=notes
    )

    render_report_page(html_content=html, report_name="Notes List")


@ui.page("/reports/files")
def print_files_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        files = files_report_rows(session)

        html = build_files_report_html(
            active_case=active_case,
            files=files,
        )

    render_report_page(html_content=html, report_name="File List")


def files_report_rows(session) -> list[dict]:
    """The attachments as the Files report lists them.

    The attachment itself is not read: FILEDATA is deferred, and nothing
    here touches it.
    """
    return [
        {
            "Z_PK": f.Z_PK,
            "FILENAME": f.FILENAME,
            "FILEMIMETYPE": f.FILEMIMETYPE or "",
            # Stored in UTC. Printed raw it read as a local time four
            # or five hours out; shown in this machine's zone, with its
            # offset, as the Files page shows it.
            "FILEUPLOADDATE": (
                clock.show_utc(f.FILEUPLOADDATE)
                if f.FILEUPLOADDATE else ""
            ),
            "FILEUPLOADEDBY": f.FILEUPLOADEDBY or "",
            "FILESHA256": (f.FILESHA256 or "").upper(),
        }
        for f in session.query(UploadedFiles).order_by(UploadedFiles.Z_PK)
    ]


# The print window's own styles, on top of the report's.
PRINT_WINDOW_STYLES = """
@media screen {
    /*
    Chrome paints a new window dark when the computer is in dark mode,
    and report text is black: without a page of its own the report was
    all but unreadable until it printed. Printing is unaffected.
    */

    html, body {
        background: #FFFFFF;
        color: #000000;
    }
    /*
    The page's padding moves onto the report, so the bar runs edge to edge.
    */
    body {
        margin: 0;
        padding: 0;
    }
    .report-body {
        padding: 0 16px 24px;
    }
}

/*
Stays at the top while a long report is scrolled, so Print and Close buttons
are always in reach. Marked no-print, so it never prints.
*/
.print-toolbar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    margin: 0 0 16px;
    background: #1E293B;
    color: #FFFFFF;
    font-family: -apple-system, "Segoe UI", system-ui, Arial, sans-serif;
}

.print-toolbar .tb-title {
    flex: 1 1 220px;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.3;
}

.print-toolbar .tb-title small {
    display: block;
    font-size: 12px;
    font-weight: 400;
    color: #CBD5E1;
}

/* 44 px tall: the smallest target Apple recommends for a finger. */
.print-toolbar button {
    -webkit-appearance: none;
    appearance: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    min-width: 150px;
    min-height: 44px;
    padding: 0 20px;
    border-radius: 8px;
    font: 600 16px/1.2 -apple-system, "Segoe UI", system-ui, Arial, sans-serif;
    cursor: pointer;
}

.print-toolbar .print-btn {
    background: #2984D1;
    border: 2px solid #2984D1;
    color: #FFFFFF;
}

.print-toolbar .print-btn:hover {
    inset: 3px;
    border: 2px dashed white;
}

.print-toolbar .close-btn {
    background: transparent;
    border: 1px solid #94A3B8;
    color: #FFFFFF;
}

.print-toolbar .close-btn:hover {
    inset: 3px;
    border: 2px dashed #2984D1;
}

.print-toolbar button:focus-visible {
    outline: 3px solid #93C5FD;
    outline-offset: 2px;
}
"""


def print_toolbar_html(
        report_name: str = "",
        case_number: str = ""
) -> str:
    """The bar across the top of the print window: which report and case
    this is, and the Print and Close buttons."""
    title = " · ".join(h(part) for part in (report_name, case_number) if part)
    return (
        '<div class="print-toolbar no-print">'
        f'<div class="tb-title">{title or "Report"}'
        "<small>[ This title bar is not printed ]</small></div>"
        '<button type="button" class="print-btn" onclick="window.print()">'
        "🖨️ Print Report</button>"
        '<button type="button" class="close-btn" onclick="window.close()">'
        "✕ Close</button>"
        "</div>"
    )


def print_window_script(
        report_name: str = "",
        case_number: str = ""
) -> str:
    """The browser-side handler that opens the report in a print window.

    The report's own HTML is copied into a clean page with the report
    styles, a bar naming the report with Print and Close buttons, and the
    print dialog opened after a moment. Run by the click in the browser,
    not from the server: see render_report_page().
    """
    title = " · ".join(h(part) for part in (report_name, case_number) if part)
    values = {
        "STYLES": json.dumps(COMMON_STYLES + PRINT_WINDOW_STYLES),
        "TITLE": json.dumps(title or "V·E·C·T·O·R", ensure_ascii=False),
        "TOOLBAR": json.dumps(
            print_toolbar_html(report_name, case_number), ensure_ascii=False
        ),
    }
    # One pass, so a case number can never be read as a placeholder.
    return re.sub(
        r"__(STYLES|TITLE|TOOLBAR)__",
        lambda match: values[match.group(1)],
        _PRINT_WINDOW_JS,
    )


_PRINT_WINDOW_JS = """() => {
        const report = document.getElementById('report-container');
        if (!report) {
            alert('No report content found to print.');
            return;
        }

        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert('The browser blocked the print window. Allow pop-ups '
                + 'for this address, or press Ctrl + P on this page.');
            return;
        }

        printWindow.document.write(
            '<!DOCTYPE html><html lang="en"><head>'
            + '<meta charset="UTF-8">'
            + '<meta name="viewport" content="width=device-width, '
            + 'initial-scale=1.0">'
            + '<title>' + __TITLE__ + '</title>'
            + '<style>' + __STYLES__ + '</style></head><body>'
            + __TOOLBAR__
            + '<div class="report-body">' + report.innerHTML + '</div>'
            + '<scr' + 'ipt>setTimeout(() => window.print(), 500);</scr'
            + 'ipt></body></html>'
        );
        printWindow.document.close();
    }"""
