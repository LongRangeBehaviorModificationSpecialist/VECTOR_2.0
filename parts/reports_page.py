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
    /reports/print-all         →  Print All's reports, for its print window


WORKFLOW FOR REPORT CREATION:

    (1) `print_<type>_report() function is called from the navbar button ->
    (2) That function calls `get_case_info()` ->
    (3) `build_<type>_report_html(active_case=active_case,
            <type>=<type>)` compiles the html string for report ->
        (a) `build_case_header_html(active_case and page_title)`
        (b) `build_report_footer_html()`
    (4) `render_report_page()` is run with the output from step 3 (html_content)

"""

from html import escape
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from nicegui import app, ui
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
from live import refresh_on_change
from navbar import build_navbar, unit_logo
from auth import (
    get_current_user_name,
    get_is_admin,
    is_authenticated,
    require_session,
)
from utils import (
    CASE_TIME_FORMAT,
    CONFIRM_TIMEOUT,
    WARN_TIMEOUT,
    ZERO_TIMEOUT,
    evidence_number_key,
    get_case_info,
    get_print_date_time,
    parse_entered_date,
    set_print_all,
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

    # ----- One button for the reports a search ends with -----
    _print_all_section()

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


COPIES_CHOICES = {
    0: "Leave out",
    1: "1 copy",
    2: "2 copies",
    3: "3 copies",
}


def _print_all_section() -> None:
    """One button for the reports a search normally ends with.

    Printing them meant opening each report and printing it in turn --
    the return copy twice. The button opens one print window with all of
    them, each starting on a new sheet. What it prints is chosen below
    it, and kept for this machine.
    """
    case_number = (get_case_info() or {}).get("CASENUMBER", "")
    is_valid, errors = validate_case_for_report()

    with ui.card().classes("w-full max-w-2xl mx-auto p-6 mb-4 items-center"):
        button = ui.button(
            "Print All",
            color="#1C69A8",
        ).props("push icon=print").classes("w-70 p-6 hover-border-white")

        if is_valid:
            # Opened by the click itself; see render_report_page().
            button.on("click", js_handler=print_all_script(case_number))
        else:
            button.on_click(lambda: show_validation_errors(errors))

        summary = ui.label().classes(
            "text-sm text-center text-[var(--vsp-gray)] mt-2"
        )
        rooms_note = ui.label().classes(
            "text-sm text-center text-[#F5B027] mt-1"
        )

        def settle() -> None:
            """The summary, the warning and the button, as things stand."""
            copies = settings.print_all_copies()
            chosen = print_all_summary(copies)
            summary.set_text(
                f"Prints, each starting on a new page: {chosen}." if chosen
                else "Nothing is chosen for Print All yet. Choose below."
            )
            button.set_enabled(bool(chosen))
            missing = rooms_missing_agents() if copies.get("rooms") else []
            rooms_note.set_text(
                "Room" + ("s " if len(missing) > 1 else " ")
                + ", ".join(missing[:10])
                + (" have" if len(missing) > 1 else " has")
                + " no agent named, printed as [NOT RECORDED]."
                if missing else ""
            )
            rooms_note.set_visibility(bool(missing))

        settle()
        # Rooms given their agents on another device.
        refresh_on_change(settle)

        with ui.expansion(
            "Choose what Print All prints",
            icon="tune",
        ).classes("w-full mt-2"):
            ui.label(
                "Kept for this machine. In this order, each report "
                "starting on a new sheet."
            ).classes("text-xs text-gray-400 mb-2")

            copies = settings.print_all_copies()
            for key, name, _build in PRINT_ALL_REPORTS:

                @require_session
                def choose(event, key=key) -> None:
                    try:
                        set_print_all(
                            {key: int(event.value)}, get_current_user_name()
                        )
                    except Exception as err:
                        log.exception("Could not change what Print All prints")
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
                    settle()

                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(name).classes("text-sm")
                    ui.select(
                        COPIES_CHOICES,
                        value=copies.get(key, 0),
                        on_change=choose,
                    ).props("dense outlined").classes("w-36")


def _printed_date_switch() -> None:
    """Whether each report says when it was printed.

    Off by default; it is this machine's choice, kept with its other settings,
    and every change is in the audit trail.
    """

    @require_session
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

    @require_session
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
        "Some rooms are missing agent names.\n\n"
        "Enter the names on the Rooms page, or print the list with those "
        "names marked '[NOT RECORDED]'.\n\n"
        f"Rooms missing an agent => {shown}.\n\n"
    )


def rooms_missing_agents_banner(message: str) -> None:
    """Renders the missing-agents warning banner."""
    with ui.column().classes("items-center w-full"):
        unit_logo("novadc_icac.png", "w-[150px] h-[150px] mb-4")
        with ui.row().classes("text-2xl font-normal text-center"):
            ui.label("V·E·C·T·O·R")
            ui.label("|").classes("font-bold text-[var(--vsp-blue)]")
            ui.label("Reports Page")
        # Put the message INSIDE the column, via a real widget:
        ui.markdown(message).classes("text-center text-lg py-12")


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


# ----- Report Styles -----
#
# Order matters here. Rules of equal weight are decided by whichever comes
# last, so the sheet runs: tokens -> utilities -> page frame -> components
# -> @media print. Print is last on purpose: it only has to say what is
# DIFFERENT on paper, and it wins over the screen rules above it.
#
# Class naming:
#   report-*        the frame shared by every report (wrapper, titles, footer)
#   header-*        the case-information table at the top of every report
#   item-bar*       the dark "Item #" / room-name bar above a detail table
#   detail-*        the label/value tables (evidence reports and file list)
#   <name>-table*   the column-style list tables (agent, note, room, person)
COMMON_STYLES = """
@page {
    margin: 0.65in 0.5in 0.75in 0.5in;

    @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        color: #000;
        font-family: "Arial", sans-serif;
        font-size: 10pt;
        font-weight: bold;
        margin-bottom: 0.5in;
    }
}

:root {
    --report-gray: #D1D5DC;
    --report-dark: #1E293B;
    --report-dark-text: #CBD5E1;
    --default-padding: 2pt 8pt 2pt 8pt;
}

body {
    box-sizing: border-box;
    color: black;
    font-family: "Arial", sans-serif;
    margin: 0;
    padding: 1em;
}

/* ----- Utilities (before the components, so a component's own size wins) */
.font-10 { font-size: 10pt; }
.font-11 { font-size: 11pt; }

/* ----- Page frame ----- */
.report-wrap {
    padding-left: 5%;
    padding-right: 5%;
}

.report-heading {
    text-align: center;
}

.report-title {
    font-size: 11pt;
    font-weight: bold;
    margin: 0 auto 2em auto;
    text-align: center;
}

.report-end {
    font-size: 11pt;
    font-weight: 600;
    margin-top: 2rem;
    text-align: center;
}

/* ----- Case information block ----- */
.header-table {
    border-collapse: collapse;
    line-height: 1.5em;
    margin: 0 auto 2em auto;
    table-layout: fixed;
    width: 100%;
}

.header-label {
    font-size: 11pt;
    padding: var(--default-padding);
    vertical-align: bottom;
    width: 30%;
}

td.header-value {
    border-bottom: 1px dotted black;
    font-family: "Times New Roman", Times, serif;
    padding: var(--default-padding);
    vertical-align: bottom;
    width: 70%;
}


/* ----- List tables: agent, note, room, person ----- */
.agent-table,
.note-table,
.room-table,
.person-table {
    border-collapse: collapse;
    width: 100%;
}

.agent-table thead tr,
.note-table thead tr,
.room-table thead tr,
.person-table thead tr {
    border-bottom: 1px solid black;
}

.agent-table-header,
.note-table-header,
.room-table-header,
.person-table-header {
    border-collapse: collapse;
    font-size: 10pt;
    font-weight: 650;
    text-align: left;
    white-space: nowrap;
}

.agent-table-data,
.note-table-data,
.room-table-data,
.person-table-data {
    border-bottom: 1px dotted black;
    font-size: 10pt;
    height: 1.85em;
    padding: 0pt 5pt;
    vertical-align: middle;
}

.no-data {
    border-bottom: 1px dotted black;
    font-weight: bold;
    height: 6em;
    padding: 0pt;
    text-align: center;
    vertical-align: middle;
}

/* ----- Item bar: the dark "Item #" / room-name strip above a table ----- */
.item-bar,
.detail-table {
    border-collapse: collapse;
    margin: 0 auto;
    table-layout: fixed;
    width: 100%;
}

.item-bar-cell {
    background-color: var(--report-dark);
    color: var(--report-dark-text);
    font-size: 10pt;
    font-weight: bold;
    height: 1.65em;
    padding: 2pt 8pt;
    text-align: left;
    vertical-align: middle;
}

/* ----- Detail tables: one label column, one value column ----- */
.detail-table {
    margin-bottom: 1.5em;
}

.detail-table col.col-label { width: 30%; }
.detail-table col.col-value { width: 70%; }

.detail-table {
    border: 1px solid black;
}

.detail-table td.detail-label {
    height: 1.5em;
}

.detail-label {
    border-bottom: 1px dotted black;
    border-right: 1px dotted black;
    font-size: 10pt;
    font-weight: normal;
    padding: var(--default-padding);
    vertical-align: middle;
}

.detail-value {
    border-bottom: 1px dotted black;
    font-family: "Times New Roman", Times, serif;
    font-size: 11pt;
    overflow-wrap: break-word;
    padding: var(--default-padding);
    vertical-align: middle;
    word-wrap: break-word;
}

/* The shaded "Item No." / "File No." row that opens each item. */
.detail-title-row {
    background-color: var(--report-gray);
    border-top: 1px solid black
}

.detail-title-row .detail-label,
.detail-title-row .detail-value {
    font-weight: bold;
}

/* A gap row between items. The td. prefix is needed to outweigh the
   border set on every .detail-table td above. */
.detail-table td.detail-spacer {
    border-left: 1px solid transparent;
    border-right: 1px solid transparent;
}

/* ----- Paper only: what differs from the screen ----- */
@media print {
    .no-print {
        display: none !important;
    }

    body {
        background: white !important;
        color: black !important;
    }

    .header-label {
        font-size: 10pt;
        vertical-align: middle;
    }

    .header-value {
        font-size: 11pt;
        vertical-align: middle;
    }

    /* Repeat the column headings on every printed page. */
    .agent-table thead,
    .note-table thead,
    .room-table thead,
    .person-table thead {
        display: table-header-group;
    }

    .agent-table-header,
    .note-table-header,
    .room-table-header,
    .person-table-header {
        break-inside: avoid;
        page-break-inside: avoid;
        padding: 5px 5px 3px 5px;
    }

    .agent-table-data,
    .note-table-data,
    .room-table-data,
    .person-table-data {
        font-family: "Times New Roman", Times, serif;
        padding: 5px 5px 3px 5px;
    }

    /* Ink-friendly: the dark bar prints as plain black text. */
    .item-bar-cell {
        background-color: #FFFFFF;
        border: 1px solid transparent;
        color: #000000;
        padding: 2px 0px;
    }

    .detail-value {
        padding: var(--default-padding);
    }

    .detail-table td.detail-spacer {
        border-top: 1px solid transparent;
    }
}
"""


def build_case_header_html(
        active_case: dict | None,
        page_title: str,
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
                <td class="header-label">Report Printed Date:</td>
                <td class="header-value">{get_print_date_time()}</td>
            </tr>"""

    report_header_table = f"""
    <div class="report-wrap">
        <table class="header-table">
            <tr>
                <td class="header-label">Investigation Number:</td>
                <td class="header-value">{h(active_case["CASENUMBER"])}</td>
            </tr>
            <tr>
                <td class="header-label">Site Address:</td>
                <td class="header-value">{h(active_case["LOCATION"])}</td>
            </tr>
            <tr>
                <td class="header-label">Jurisdiction:</td>
                <td class="header-value">{h(active_case["JURISDICTION"])}</td>
            </tr>
            <tr>
                <td class="header-label">Starting Date and Time:</td>
                <td class="header-value">
                    {h(active_case["CASEDATETIMEBEGIN"])}
                </td>
            </tr>
            <tr>
                <td class="header-label">Ending Date and Time:</td>
                <td class="header-value">
                    {h(active_case["CASEDATETIMEEND"])}
                </td>
            </tr>
            {printed_row}
        </table>
    </div>"""

    return f"""
    <div class="report-heading">
        <p class="report-title">{page_title}</p>
    </div>
    {report_header_table}
    """


def build_report_footer_html() -> str:
    """Generates the standard END OF REPORT footer."""

    return """
    <p class="report-end">
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
            <td class="agent-table-data">{h(a["AGENTNAME"])}</td>
            <td class="agent-table-data">{h(a["AGENTPARENTAGENCY"])}</td>
            <td class="agent-table-data">{h(a["AGENTPRIMARYROLE"])}</td>
            <td class="agent-table-data">{contact(a["AGENTPHONE"])}</td>
            <td class="agent-table-data">{contact(a["AGENTEMAIL"])}</td>
        </tr>"""
        for a in agents]
    )

    header = build_case_header_html(
        active_case,
        page_title="INVESTIGATORS AT SEARCH WARRANT SITE",
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
    <div class="report-wrap">
        <table class="agent-table">
            <thead>
                <tr>
                    <th class="agent-table-header">Agent Name</th>
                    <th class="agent-table-header">Agency</th>
                    <th class="agent-table-header">Primary Role</th>
                    <th class="agent-table-header">Phone Number</th>
                    <th class="agent-table-header">Email</th>
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

# The label/value rows of an evidence item, in print order. The label is
# what is printed; the key is the field in the evidence dict.
EVIDENCE_FIELDS = [
    ("Quantity:", "EVIDQTY"),
    ("Description:", "EVIDDESC"),
    ("Model #:", "EVIDMODELNUMBER"),
    ("Serial #:", "EVIDSERIALNUMBER"),
    ("Location:", "EVIDLOCROOM"),
    ("Where Found:", "EVIDLOCROOMDETAIL"),
    ("Located By:", "EVIDFOUNDBY"),
    ("Witnessed By:", "EVIDFOUNDBYWITNESS"),
    ("Photographed:", "EVIDPICTAKEN"),
    ("Item Triaged:", "EVIDTRIAGED"),
    ("Item Triaged By:", "EVIDTRIAGEDBY"),
    ("Notes:", "EVIDNOTE"),
]

# The return copy shows only these, in the same order as above.
_BASIC_EVIDENCE_KEYS = ("EVIDDESC", "EVIDMODELNUMBER", "EVIDSERIALNUMBER")
BASIC_EVIDENCE_FIELDS = [
    field for field in EVIDENCE_FIELDS if field[1] in _BASIC_EVIDENCE_KEYS
]

# Sets the 30/70 split for every .detail-table. It has to be a colgroup:
# see the note above .detail-table in COMMON_STYLES.
DETAIL_COLGROUP = (
    '<colgroup><col class="col-label"><col class="col-value"></colgroup>'
)


def detail_rows(item: dict, fields: list[tuple[str, str]]) -> str:
    """The label/value <tr> rows for one item. Values are escaped here."""
    return "".join(
        f"""
            <tr>
                <td class="detail-label">{label}</td>
                <td class="detail-value">{h(item[key])}</td>
            </tr>"""
        for label, key in fields
    )


def item_bar_html(text_html: str) -> str:
    """The dark bar above an item's table.

    text_html goes in as written, so escape database values with h()
    before passing them.
    """
    return f"""
        <table class="item-bar">
            <tr>
                <td class="item-bar-cell">{text_html}</td>
            </tr>
        </table>"""


def report_document_html(
        title: str,
        header: str,
        body: str,
        footer: str
) -> str:
    """Wraps a report's pieces in the complete HTML page."""
    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | {title}</title>
    <style>
        {COMMON_STYLES}
    </style>
</head>
<body>
    {header}
    {body}
    {footer}
</body>
</html>"""


def build_evidence_report_html(active_case: list, evidence: list) -> str:
    """Generates the complete HTML for the detailed Evidence report.

    Each item is displayed as vertical label/value rows with ALL fields.

    This is the AGENT COPY.
    """

    evid_tables = "".join(
        item_bar_html(f"Item #:&ensp;{h(e['EVIDNUM'])}")
        + f"""
        <table class="detail-table">
            {DETAIL_COLGROUP}
            {detail_rows(e, EVIDENCE_FIELDS)}
        </table>"""
        for e in evidence
    )

    header = build_case_header_html(
        active_case,
        page_title="FULL EVIDENCE INVENTORY LIST",
    )

    return report_document_html(
        title="Evidence Inventory List",
        header=header,
        body=f'<div class="report-wrap">{evid_tables}</div>',
        footer=build_report_footer_html(),
    )


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

        # Each item: a spacer row, the shaded "Item No." row, then its
        # label/value rows, all in the one table for the room.
        item_rows = "".join(
            f"""
            <tr>
                <td class="detail-spacer"></td>
                <td class="detail-spacer"></td>
            </tr>
            <tr class="detail-title-row">
                <td class="detail-label">Item No.:</td>
                <td class="detail-value">{h(e["EVIDNUM"])}</td>
            </tr>{detail_rows(e, EVIDENCE_FIELDS)}"""
            for e in evidence
            if e["EVIDLOCROOM"] == room_name
        )

        room_tables += f"""
        <div class="report-wrap">
            {item_bar_html(h(label))}
            <table class="detail-table">
                {DETAIL_COLGROUP}
                {item_rows}
            </table>
        </div>
        <br />"""

    header = build_case_header_html(
        active_case,
        page_title="EVIDENCE FOUND LIST BY ROOM",
    )

    return report_document_html(
        title="Evidence Found By Room",
        header=header,
        body=room_tables,
        footer=build_report_footer_html(),
    )


def build_basic_evidence_report_html(
        active_case: list,
        evidence: list
) -> str:
    """Generates the complete HTML for the Basic Evidence report.

    Each item shows only Item#, Quantity, Description, Model#, and Serial#.

    This is the "RETURN COPY" version.
    """

    evid_tables = "".join(
        item_bar_html(f"Item #:&ensp;{h(e['EVIDNUM'])}")
        + f"""
        <table class="detail-table">
            {DETAIL_COLGROUP}
            {detail_rows(e, BASIC_EVIDENCE_FIELDS)}
        </table>"""
        for e in evidence
    )

    header = build_case_header_html(
        active_case,
        page_title="SEARCH INVENTORY AND RETURN",
    )

    return report_document_html(
        title="Basic Evidence Inventory List",
        header=header,
        body=f'<div class="report-wrap">{evid_tables}</div>',
        footer=build_report_footer_html(),
    )


def build_rooms_report_html(active_case: list, rooms: list) -> str:
    """Generates the complete HTML for the Room List report."""

    room_rows = "".join([f"""
            <tr>
                <td class="room-table-data">
                    {h(r["ROOMLABEL"])}
                </td>
                <td class="room-table-data">
                    {h(r["ROOMDESC"])}
                </td>
                <td class="room-table-data">
                    {recorded(r["ROOMFIRSTAGENT"])}
                </td>
                <td class="room-table-data">
                    {recorded(r["ROOMSECONDAGENT"])}
                </td>
                <td class="room-table-data">
                    {h(r["ROOMNOTE"])}
                </td>
            </tr>
            """
            for r in rooms
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="ROOM LIST",
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
    <div class="report-wrap">
        <table class="room-table">
            <thead>
                <tr>
                    <th class="room-table-header">Room ID</th>
                    <th class="room-table-header">Room Name</th>
                    <th class="room-table-header">Searched By (1)</th>
                    <th class="room-table-header">Searched By (2)</th>
                    <th class="room-table-header">Notes</th>
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
            <td class="person-table-data">{h(p["PERSONNAME"])}</td>
            <td class="person-table-data">{h(p["PERSONDOB"])}</td>
            <td class="person-table-data">{h(p["PERSONADDRESS"])}</td>
            <td class="person-table-data">{h(p["PERSONPHONE"])}</td>
            <td class="person-table-data">{h(p["PERSONNOTE"])}</td>
        </tr>
        """
            for p in persons
            ]
        )

    header = build_case_header_html(
        active_case,
        page_title="PERSONS LIST",
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
    <div class="report-wrap">
        <table class="person-table">
            <thead>
                <tr>
                    <th class="person-table-header">Person Name</th>
                    <th class="person-table-header">DOB</th>
                    <th class="person-table-header">Address</th>
                    <th class="person-table-header">Phone #</th>
                    <th class="person-table-header">Notes</th>
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
            <td class="note-table-data">{h(n["NOTEDATETIME"])}</td>
            <td class="note-table-data">{h(n["NOTEDATETIMEUPDATED"])}</td>
            <td class="note-table-data">{h(n["NOTEAUTHOR"])}</td>
            <td class="note-table-data">{h(n["NOTETEXT"])}</td>
        </tr>
        """
            for n in notes
            ]
        )

    header = build_case_header_html(
        active_case,
        page_title="NOTES LIST",
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
    <div class="report-wrap">
        <table class="note-table">
            <thead>
                <tr>
                    <th class="note-table-header">Date/Time Added</th>
                    <th class="note-table-header">Date/Time Updated</th>
                    <th class="note-table-header">Author</th>
                    <th class="note-table-header">Text</th>
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

    file_fields = [
        ("File Name:", "FILENAME"),
        ("File Type:", "FILEMIMETYPE"),
        ("Uploaded Date/Time:", "FILEUPLOADDATE"),
        ("Uploaded By:", "FILEUPLOADEDBY"),
        ("File Hash (SHA256):", "FILESHA256"),
    ]

    file_tables = "".join(
        item_bar_html(f"File #:&ensp;{h(f['Z_PK'])}")
        + f"""
        <table class="detail-table">
            {DETAIL_COLGROUP}
            {detail_rows(f, file_fields)}
        </table>"""
        for f in files
    )

    header = build_case_header_html(
        active_case,
        page_title="ATTACHED FILES LIST",
    )

    return report_document_html(
        title="Attached Files List",
        header=header,
        body=f'<div class="report-wrap">{file_tables}</div>',
        footer=build_report_footer_html(),
    )


# ----- Each report, built from the case -----
# One function per report, apart from its page, so Print All can put the
# same reports one after another in a single print window.
def _evidence_rows(session, basic: bool = False) -> list[dict]:
    """The evidence as the evidence reports print it, in item order."""
    rows = []
    for e in evidence_in_order(session):
        row = {
            "EVIDNUM": e.EVIDNUM,
            "EVIDQTY": e.EVIDQTY,
            "EVIDDESC": e.EVIDDESC,
            "EVIDMODELNUMBER": e.EVIDMODELNUMBER or "[NOT RECORDED]",
            "EVIDSERIALNUMBER": e.EVIDSERIALNUMBER or "[NOT RECORDED]",
        }
        if not basic:
            row.update({
                "EVIDLOCROOM": e.EVIDLOCROOM,
                "EVIDLOCROOMDETAIL": e.EVIDLOCROOMDETAIL,
                "EVIDFOUNDBY": e.EVIDFOUNDBY,
                "EVIDFOUNDBYWITNESS": e.EVIDFOUNDBYWITNESS,
                "EVIDPICTAKEN": e.EVIDPICTAKEN,
                "EVIDTRIAGED": e.EVIDTRIAGED,
                "EVIDTRIAGEDBY": e.EVIDTRIAGEDBY or "N/A",
                "EVIDNOTE": e.EVIDNOTE or "[NOT RECORDED]",
            })
        rows.append(row)
    return rows


def agents_report_html() -> str:
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
    return build_agents_report_html(
        active_case=active_case,
        agents=agents,
        redact_contacts=settings.redact_agent_report(),
    )


def evidence_report_html() -> str:
    with get_session() as session:
        active_case = get_case_info()
        evidence = _evidence_rows(session)
    return build_evidence_report_html(
        active_case=active_case,
        evidence=evidence,
    )


def evidence_by_room_report_html() -> str:
    with get_session() as session:
        active_case = get_case_info()
        unique_rooms_list = rooms_with_item_counts(session)
        evidence = _evidence_rows(session)
    return build_evidence_by_room_report_html(
        active_case=active_case,
        evidence=evidence,
        unique_rooms=unique_rooms_list,
    )


def basic_evidence_report_html() -> str:
    with get_session() as session:
        active_case = get_case_info()
        evidence = _evidence_rows(session, basic=True)
    return build_basic_evidence_report_html(
        active_case=active_case,
        evidence=evidence,
    )


def rooms_report_html() -> str:
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
    return build_rooms_report_html(
        active_case=active_case,
        rooms=rooms,
    )


def persons_report_html() -> str:
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
    return build_persons_report_html(
        active_case=active_case,
        persons=persons,
    )


def notes_report_html() -> str:
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
    return build_notes_report_html(
        active_case=active_case,
        notes=notes,
    )


def files_report_html() -> str:
    with get_session() as session:
        active_case = get_case_info()
        files = files_report_rows(session)
        return build_files_report_html(
            active_case=active_case,
            files=files,
        )


# ----- The report pages -----
@ui.page("/reports/agents")
def print_agents_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    render_report_page(
        html_content=agents_report_html(), report_name="Agent List"
    )


@ui.page("/reports/evidence")
def print_evidence_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    render_report_page(
        html_content=evidence_report_html(),
        report_name="Evidence List (Full)",
    )


@ui.page("/reports/evidence_by_room")
def print_evidence_by_room_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    render_report_page(
        html_content=evidence_by_room_report_html(),
        report_name="Evidence List (By Room)",
    )


@ui.page("/reports/evidence_basic")
def print_basic_evidence_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    render_report_page(
        html_content=basic_evidence_report_html(),
        report_name="Evidence List (Basic)",
    )


@ui.page("/reports/check_rooms_agents")
def check_rooms_agents():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    missing_labels = rooms_missing_agents()
    if missing_labels:
        build_navbar(
            is_admin=get_is_admin(),
            username=get_current_user_name(),
        )
        with ui.column().classes("items-center w-full mt-4 mb-4"):
            message = rooms_missing_agents_message(labels=missing_labels)
            if message:
                rooms_missing_agents_banner(message=message)

        with ui.row().classes(
            "flex justify-center items-center gap-12 my-6 w-full"):
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

    ui.add_head_html(
        "<title>V·E·C·T·O·R | Room List Report</title>",
        shared=True,
    )

    render_report_page(
        html_content=rooms_report_html(), report_name="Room List"
    )


@ui.page("/reports/persons")
def print_persons_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    render_report_page(
        html_content=persons_report_html(), report_name="Persons List"
    )


@ui.page("/reports/notes")
def print_notes_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    render_report_page(
        html_content=notes_report_html(), report_name="Notes List"
    )


@ui.page("/reports/files")
def print_files_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    render_report_page(
        html_content=files_report_html(), report_name="File List"
    )


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


# ----- Print All -----
# The reports a search normally ends with, printed by one button into one
# print window, each starting on a new sheet. In the order the Reports
# page lists them; settings.print_all_copies() says how many copies of
# each, set on the Reports page.
PRINT_ALL_REPORTS = [
    ("agents", "Agent List", agents_report_html),
    ("rooms", "Room List", rooms_report_html),
    ("evidence", "Evidence List (Full)", evidence_report_html),
    ("evidence_by_room", "Evidence List (By Room)",
     evidence_by_room_report_html),
    ("evidence_basic", "Inventory and Return", basic_evidence_report_html),
    ("persons", "Persons List", persons_report_html),
    ("notes", "Notes List", notes_report_html),
    ("files", "File List", files_report_html),
]

PRINT_ALL_NAMES = {key: name for key, name, _build in PRINT_ALL_REPORTS}

# Added to the print window's styles for Print All.
PRINT_ALL_STYLES = """
/* Each report starts on a new sheet. */
.print-all-part + .print-all-part {
    break-before: page;
}

/*
No page numbers. The count runs on across every report in the window, so
the second report's first page would read "Page 4 of 11".
*/
@page {
    @bottom-center {
        content: none;
    }
}
"""

_BODY = re.compile(r"<body[^>]*>(.*)</body>", re.S | re.I)


def _report_body(html: str) -> str:
    """What is inside a report's <body>; its styles come from the window."""
    match = _BODY.search(html)
    return match.group(1) if match else html


def print_all_html(copies: dict | None = None) -> str:
    """Every report Print All prints, one after another.

    Each report is built once however many copies are asked for, so the
    copies cannot differ.
    """
    copies = settings.print_all_copies() if copies is None else copies
    parts = []
    for key, _name, build in PRINT_ALL_REPORTS:
        count = copies.get(key, 0)
        if not count:
            continue
        body = _report_body(build())
        parts += [f'<section class="print-all-part">{body}</section>'] * count
    return "\n".join(parts)


def print_all_summary(copies: dict | None = None) -> str:
    """What Print All prints, as the Reports page says it."""
    copies = settings.print_all_copies() if copies is None else copies
    chosen = []
    for key, name, _build in PRINT_ALL_REPORTS:
        count = copies.get(key, 0)
        if count == 1:
            chosen.append(name)
        elif count > 1:
            chosen.append(f"{name} ({count} copies)")
    return ", ".join(chosen)


@app.get("/reports/print-all")
async def print_all_document():
    """The reports for Print All, fetched by its print window.

    Signed-in users only, like every report. Not kept by the browser: it
    is the case.
    """
    if not is_authenticated():
        return Response(status_code=403)

    is_valid, errors = validate_case_for_report()
    if not is_valid:
        return PlainTextResponse(
            "Cannot print yet -- missing information:\n\n"
            + "\n".join(f"- {error}" for error in errors),
            status_code=409,
        )

    html = print_all_html()
    if not html:
        return PlainTextResponse(
            "Print All has no reports chosen. Choose some on the Reports "
            "page.",
            status_code=409,
        )
    return HTMLResponse(html, headers={"Cache-Control": "no-store"})


def print_all_script(case_number: str = "") -> str:
    """The browser-side handler behind Print All.

    The window is opened by the click itself, as for a single report, so
    a pop-up blocker lets it through; the reports are fetched into it
    afterwards, so they are as the case is at that moment.
    """
    title = " · ".join(h(part) for part in ("Print All", case_number) if part)
    values = {
        "STYLES": json.dumps(
            COMMON_STYLES + PRINT_WINDOW_STYLES + PRINT_ALL_STYLES
        ),
        "TITLE": json.dumps(title, ensure_ascii=False),
        "TOOLBAR": json.dumps(
            print_toolbar_html("Print All", case_number), ensure_ascii=False
        ),
    }
    return re.sub(
        r"__(STYLES|TITLE|TOOLBAR)__",
        lambda match: values[match.group(1)],
        _PRINT_ALL_JS,
    )


_PRINT_ALL_JS = """() => {
        const printWindow = window.open('', '_blank');
        if (!printWindow) {
            alert('The browser blocked the print window. Allow pop-ups '
                + 'for this address, and press Print All again.');
            return;
        }
        printWindow.document.write(
            '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            + '<title>' + __TITLE__ + '</title></head>'
            + '<body style="font: 16px -apple-system, Segoe UI, Arial, '
            + 'sans-serif; padding: 24px;">Getting the reports ready...'
            + '</body></html>'
        );
        printWindow.document.close();

        const say = (text) => {
            printWindow.document.body.textContent = text;
            printWindow.document.body.style.whiteSpace = 'pre-line';
        };

        fetch('/reports/print-all', {credentials: 'same-origin', cache: 'no-store'})
            .then((response) => response.text().then(
                (text) => ({ok: response.ok, text: text})))
            .then((answer) => {
                if (!answer.ok) {
                    say(answer.text || 'The reports could not be prepared.');
                    return;
                }
                printWindow.document.open();
                printWindow.document.write(
                    '<!DOCTYPE html><html lang="en"><head>'
                    + '<meta charset="UTF-8">'
                    + '<meta name="viewport" content="width=device-width, '
                    + 'initial-scale=1.0">'
                    + '<title>' + __TITLE__ + '</title>'
                    + '<style>' + __STYLES__ + '</style></head><body>'
                    + __TOOLBAR__
                    + '<div class="report-body">' + answer.text + '</div>'
                    + '<scr' + 'ipt>setTimeout(() => window.print(), 500);'
                    + '</scr' + 'ipt></body></html>'
                );
                printWindow.document.close();
            })
            .catch(() => say(
                'The reports could not be loaded. Close this window and '
                + 'press Print All again.'));
    }"""


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
    align-items: center;
    background: #1E293B;
    color: #FFFFFF;
    display: flex;
    flex-wrap: wrap;
    font-family: -apple-system, "Segoe UI", system-ui, Arial, sans-serif;
    gap: 12px;
    margin: 0 0 16px;
    padding: 10px 16px;
    position: sticky;
    top: 0;
    z-index: 10;
}

.print-toolbar .tb-title {
    flex: 1 1 220px;
    font-size: 16px;
    font-weight: 600;
    line-height: 1.3;
}

.print-toolbar .tb-title small {
    color: #CBD5E1;
    display: block;
    font-size: 12px;
    font-weight: 400;
}

/* 44 px tall: the smallest target Apple recommends for a finger. */
.print-toolbar button {
    align-items: center;
    appearance: none;
    border-radius: 8px;
    cursor: pointer;
    display: inline-flex;
    font: 600 16px/1.2 -apple-system, "Segoe UI", system-ui, Arial, sans-serif;
    gap: 8px;
    justify-content: center;
    min-height: 44px;
    min-width: 150px;
    padding: 0 20px;
    -webkit-appearance: none;
}

.print-toolbar .print-btn {
    background: #2984D1;
    border: 2px solid #2984D1;
    color: #FFFFFF;
}

.print-toolbar .print-btn:hover {
    border: 2px dashed white;
    inset: 3px;
}

.print-toolbar .close-btn {
    background: transparent;
    border: 1px solid #94A3B8;
    color: #FFFFFF;
}

.print-toolbar .close-btn:hover {
    border: 2px dashed #2984D1;
    inset: 3px;
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
