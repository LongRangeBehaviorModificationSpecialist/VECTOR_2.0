"""
reports_page.py

Each report renders as formatted HTML that prints exactly like the original
Flask templates. Uses window.print() for native browser printing.


Routes:
    /reports/json              →  JSON data viewer
    /reports/agents            →  Agent list report
    /reports/evidence-basic    →  Basic evidence inventory (return copy)
    /reports/rooms             →  Room list (pending template)
    /reports/evidence          →  Detailed evidence (pending template)
    /reports/evidence-by-room  →  Evidence by room (pending template)
    /reports/persons           →  Person list (pending template)
    /reports/notes             →  Notes list (pending template)


Workflow for report creation:
    (1) `print_<type>_report() function is called from the navbar button ->
    (2) That function calls `get_case_info()` ->
    (3) `build_<type>_report_html(active_case=active_case,
            <type>=<type>)` compiles the html string for report ->
        (a) `build_case_header_html(active_case, page_title, sub_title)`
        (b) `build_report_footer_html()`
    (4) `render_report_page()` is run with the output from step 3 (html_content)

"""

from nicegui import ui
from datetime import datetime
from sqlalchemy import func
import json

from models import get_session, Agents, Cases, Evidence, Notes, Persons, Rooms
from navbar import build_navbar
from main_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler,
)


NOTIFICATION_TIMEOUT = 4000


# ── Helpers
def has_active_case() -> bool:
    """Quick check if any case exits in the database"""
    with get_session() as session:
        return session.query(Cases).count() > 0

def get_date_time() -> str:
    """Gets the current date and time for report headers."""
    now = datetime.now()
    date = now.strftime("%a, %b %d, %Y")
    time = now.strftime("%H:%M %p")
    return f"{date} at {time}"

def get_print_date_time() -> tuple[str, str]:
    """Returns date and time separately for template compatibility."""
    now = datetime.now()
    print_date = now.strftime("%m/%d/%Y")
    print_time = now.strftime("%H:%M")
    return print_date, print_time

def get_case_info() -> dict | None:
    """Returns the single active case info (or None if no case exists)."""

    with get_session() as session:

        case = session.query(Cases).first()

        if not case:
            return None

        return {
            "case_number": case.case_number or "",
            "location": case.location or "",
            "jurisdiction": case.jurisdiction or "",
            "case_date_time_begin": (
                str(case.case_date_time_begin) if case.case_date_time_begin else ""
            ),
            "case_date_time_end": (
                str(case.case_date_time_end) if case.case_date_time_end else ""
            ),
        }

# ── Report Page Wrapper
def render_report_page(html_content: str):
    """Wraps report HTML with navigation and print button."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):
        # with ui.column().classes("items-center w-full p-4 no-print"):
        with ui.element().props("id='report-container'").classes("w-full"):
            ui.button(
                "Print Report",
                on_click=open_report_window,
            ).props(
                "unelevated icon=print"
            ).classes("mb-4 no-print")
            # ui.label("Case Report").classes("text-2xl font-bold")

            ui.html(html_content)


def validate_case_for_report() -> tuple[bool, list[str]]:
    """Validates that the single active case has all required fields
    for reporting.

    Returns:
        (is_valid, list_of_error_messages).
    """

    errors = []

    with get_session() as session:

        case = session.query(Cases).first()  # Only one case at a time
        evidence = session.query(Evidence).all()

        if not case:
            errors.append(
                "No case exists in the database. Create a case first."
            )
            return False, errors

        # Check Case Number
        if not case.case_number or not str(case.case_number).strip():
            errors.append("Case Number is required.")

        # Check Location
        if not case.location or not str(case.location).strip():
            errors.append("Location is required.")

        # Check Jurisdiction
        if not case.jurisdiction or not str(case.jurisdiction).strip():
            errors.append("Jurisdiction is required.")

        # Check End Date/Time (required for complete reports)
        if not case.case_date_time_end:
            errors.append("End Date/Time is required for reports.")

        

    return (len(errors) == 0, errors)

def show_validation_errors(errors: list[str]):
    """Displays validation errors as a NiceGUI notification."""
    if len(errors) == 1:
        ui.notify(errors[0], type="negative", timeout=5000)
    else:
        error_text = "\n".join(f"• {err}" for err in errors)
        ui.notify(
            f"Cannot generate report — missing information:\n\n{error_text}",
            type="negative",
            timeout=7000,
        )


# ── Common Print Styles
COMMON_STYLES = """
@media print {
    .no-print {
        display: none !important;
    }
    body {
        background: white !important;
        color: black !important;
    }
    .agentTable thead tr th.agentTableHeader,
    .noteTable thead tr th.noteTableHeader,
    .personTable thead tr th.personTableHeader,
    .roomTable thead tr th.roomTableHeader,
    .evidTableItemRow {
        border-collapse: collapse;
        font-weight: lighter;
    }
    .headerTable tr td.data,
    .evidTableRoomNameRow {
        font-family: "Times New Roman", Times, serif;
        font-size: 11pt;
    }
    .agentTable tbody tr td.agentTableData,
    .evidTable tr td.evidTableDataColTwo,
    .noteTable tbody tr td.noteTableData,
    .personTable tbody tr td.personTableData,
    .roomTable tbody tr td.roomTableData {
        font-family: "Times New Roman", Times, serif;
    }
    .evidTableDataColOne,
    .evidTableDataColTwo {
        font-size: 11pt;
    }
}

body {
    box-sizing: border-box;
    color: black;
    font-family: "Arial", sans-serif;
    margin: 0;
    padding: 1em;
}

.reportTitle {
    text-align: center;
    margin-bottom: 1em;
}
.font-09 { font-size: 9pt; }
.font-10 { font-size: 10pt; }
.font-11 { font-size: 11pt; }
.font-12 { font-size: 12pt; }
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

.top-table {
    padding-left: 5%;
    padding-right: 5%;
}

.headerTable {
    border-collapse: collapse;
    margin-bottom: 2em;
    width: 100%;
    margin-left: auto;
    margin-right: auto;
}

td.header {
    font-size: 11pt;
    padding: 5px 10px;
    width: 35%;
}

td.data {
    font-family: "Courier New", Courier, monospace;
    padding: 0px 10px;
    border-bottom: 1px dotted gray;
    width: 65%;
    vertical-align: bottom;
}

/* Shared table styles */
.agentTable,
.noteTable,
.roomTable,
.personTable,
.evidTable {
    border-collapse: collapse;
    width: 100%;
}

.agentTableHeader,
.noteTableHeader,
.roomTableHeader,
.personTableHeader {
    border-collapse: collapse;
    font-weight: 650;
    padding: 5px;
    text-align: left;
}

.agentTable thead tr,
.noteTable thead tr,
.roomTable thead tr,
.personTable thead tr {
    border-top: 0px solid black;
    border-bottom: 1px solid black;
}

.agentTableData,
.noteTableData,
.roomTableData,
.personTableData {
    border-bottom: 1px dotted gray;
    height: 1.85em;
    padding: 0px 5px;
    vertical-align: bottom;
}

/* Evidence table styles */
.evidTableItemRow {
    text-align: center;
    font-weight: 700;
}

td.evidTableData {
    border-bottom: 1px solid black;
    height: 1.75em;
    font-size: 11pt;
    padding: 2px 5px;
}

td.evidTableDataColOne {
    height: 1.85em;
    padding: 0px 5px;
    font-size: 11pt;
    font-weight: normal;
    width: 30%;
    vertical-align: bottom;
}

td.evidTableDataColTwo {
    border-bottom: 1px dotted gray;
    height: 1.85em;
    padding: 0 px 5px;
    width: 70%;
    vertical-align: bottom;
}

.evidTableRoomNameRow {
    border-bottom: 1px solid black;
    height: 1.75em;
    text-align: center;
    font-size: 11 pt;
    padding: 2px 5px;
}

.end {
    font-weight: 600;
    margin-top: 2rem;
    text-align: center;
}
"""

# ── Case Header Builder
def build_case_header_html(active_case: dict | None, page_title: str, sub_title: str) -> str:
    """Generates the standard report title + case info header HTML."""
    active_case = get_case_info()

    if not active_case:
        ui.notify(
            "No active case — please create a case first",
            type="warning"
        )
        # Redirect to case creation page
        ui.navigate.to("/cases")

    print_date, print_time = get_print_date_time()

    report_header_table = f"""
    <div class="top-table">
        <table class="headerTable">
            <tr>
                <td class="header font-11">Investigation Number:</td>
                <td class="data font-11">{active_case["case_number"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Site Address:</td>
                <td class="data font-11">{active_case["location"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Jurisdiction:</td>
                <td class="data font-11">{active_case["jurisdiction"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Starting Date and Time:</td>
                <td class="data font-11">{active_case["case_date_time_begin"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Ending Date and Time:</td>
                <td class="data font-11">{active_case["case_date_time_end"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Report Printed Date:</td>
                <td class="data font-11">{print_date} at {print_time}</td>
            </tr>
        </table>
    </div>"""

    return f"""
    <div class="reportTitle">
        <p class="fs-3 font-14">{page_title}</p>
        <p class="fs-5 font-10">{sub_title}</p>
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

# ── Agent List Report HTML Template
def build_agents_report_html(active_case: dict, agents: list) -> str:
    """Generates the complete HTML for the Agent List report."""

    agent_rows = "".join([f"""
    <tr>
        <td class="agentTableData font-10">{a["agent_name"]}</td>
        <td class="agentTableData font-10">{a["agent_parent_agency"]}</td>
        <td class="agentTableData font-10">{a["agent_role"]}</td>
        <td class="agentTableData font-10">{a["agent_phone"]}</td>
    </tr>""" for a in agents])

    header = build_case_header_html(
        active_case,
        page_title="Investigators At Search Warrant Site",
        sub_title="( AGENT COPY )",
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
    <table class="agentTable">
        <thead>
            <tr>
                <th class="agentTableHeader font-10">Agent Name</th>
                <th class="agentTableHeader font-10">Agency</th>
                <th class="agentTableHeader font-10">Primary Role</th>
                <th class="agentTableHeader font-10">Phone Number</th>
            </tr>
        </thead>
        <tbody>
            {agent_rows}
        </tbody>
    </table>
    {footer}
</body>
</html>"""

# ── Detailed Evidence Report HTML Template (AGENT COPY)
def build_evidence_report_html(active_case: list, evidence: list) -> str:
    """Generates the complete HTML for the detailed Evidence report.

    Each item is displayed as vertical label/value rows with ALL fields.

    This is the "AGENT COPY" version.
    """

    evid_rows = "".join([f"""
        <tr class="evidTableItemRow">
            <td colspan="2" class="evidTableData">Item #:&ensp;{e["evid_num"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Quantity:</td>
            <td class="evidTableDataColTwo">{e["evid_qty"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Description:</td>
            <td class="evidTableDataColTwo">{e["evid_desc"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Model #:</td>
            <td class="evidTableDataColTwo">{e["evid_model_num"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Serial #:</td>
            <td class="evidTableDataColTwo">{e["evid_serial_num"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Location:</td>
            <td class="evidTableDataColTwo">{e["evid_loc_room"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Where Found:</td>
            <td class="evidTableDataColTwo">{e["evid_loc_room_detail"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Located By:</td>
            <td class="evidTableDataColTwo">{e["evid_found_by"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Witnessed By:</td>
            <td class="evidTableDataColTwo">{e["evid_found_by_witness"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Photographed:</td>
            <td class="evidTableDataColTwo">{e["evid_pic_taken"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Item Triaged:</td>
            <td class="evidTableDataColTwo">{e["evid_triaged"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Item Triaged By:</td>
            <td class="evidTableDataColTwo">{e["evid_triaged_by"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Notes:</td>
            <td class="evidTableDataColTwo">{e["evid_notes"]}</td>
        </tr>
        <tr>
            <td colspan="2" style="height: 1.5em;"></td>
        </tr>""" for e in evidence])

    header = build_case_header_html(
        active_case,
        page_title="Items Seized at Search Warrant Site",
        sub_title="( AGENT COPY )",
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
    <table class="evidTable">
        {evid_rows}
    </table>
    {footer}
</body>
</html>"""

# ── Evidence By Room Report HTML Template
def build_evidence_by_room_report_html(active_case: list, evidence: list, unique_rooms: list) -> str:
    """Generates the complete HTML for the Evidence By Room report.

    Groups evidence items under dark-background room headers with item counts.

    Uses the same full detail layout as the AGENT COPY evidence report.
    """

    room_tables = ""

    print(f"DEBUG: unique_room = {unique_rooms}")

    for room in unique_rooms:
        room_name = room[0]
        print(f"DEBUG: room_name = {room_name}")
        item_count = room[1]
        print(f"DEBUG: item_count = {item_count}")

        # Singular vs plural
        if item_count == 1:
            count_text = f"Room {room_name}&ensp;:&ensp;({item_count} item)"
        else:
            count_text = f"Room {room_name}&ensp;:&ensp;({item_count} items)"

        # Filter evidence items for this room
        room_items = [e for e in evidence if e["evid_loc_room"] == room_name]
        print(f"DEBUG: room_items = {room_items}")

        evid_rows = "".join([f"""
            <tr>
                <td class="evidTableDataColOne">Item No.:</td>
                <td class="evidTableDataColTwo" style="font-weight:bold">
                    {e["evid_num"]}
                </td>
            </tr>

            <tr>
                <td class="evidTableDataColOne">Quantity:</td>
                <td class="evidTableDataColTwo">{e["evid_qty"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Description:</td>
                <td class="evidTableDataColTwo">{e["evid_desc"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Model #:</td>
                <td class="evidTableDataColTwo">{e["evid_model_num"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Serial #:</td>
                <td class="evidTableDataColTwo">{e["evid_serial_num"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Location:</td>
                <td class="evidTableDataColTwo">Room {e["evid_loc_room"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Where Found</td>
                <td class="evidTableDataColTwo">{e["evid_loc_room_detail"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Located By:</td>
                <td class="evidTableDataColTwo">{e["evid_found_by"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Witnessed By:</td>
                <td class="evidTableDataColTwo">
                    {e["evid_found_by_witness"]}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Photographed:</td>
                <td class="evidTableDataColTwo">{e["evid_pic_taken"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Item Triaged:</td>
                <td class="evidTableDataColTwo">{e["evid_triaged"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Item Triaged By:</td>
                <td class="evidTableDataColTwo">{e["evid_triaged_by"]}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Notes:</td>
                <td class="evidTableDataColTwo">{e["evid_notes"]}</td>
            </tr>
            <tr>
                <td colspan="2" style="height: 1.5em;"></td>
            </tr>
            """ for e in room_items])

        room_tables += f"""
        <table class="evidTable">
            <thead>
            </thead>
            <tbody>
                <tr class="evidTableRoomNameRow">
                    <th colspan="2">{count_text}</th>
                </tr>
                {evid_rows}
            </tbody>
        </table>
        </br />"""

    header = build_case_header_html(
        active_case,
        page_title="Items Seized at Search Warrant Site (By Room)",
        sub_title="( AGENT COPY )",
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

# ── Basic Evidence Report HTML Template (RETURN COPY)
def build_basic_evidence_report_html(active_case: list, evidence: list) -> str:
    """Generates the complete HTML for the Basic Evidence report.

    Each item shows only Item#, Quantity, Description, Model#, and Serial#.

    This is the "RETURN COPY" version.
    """

    evid_rows = "".join([f"""
        <tr class="evidTableItemRow">
            <td colspan="2" class="evidTableData">Item #:&ensp;&ensp;{e["evid_num"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Quantity:</td>
            <td class="evidTableDataColTwo">{e["evid_qty"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Description:</td>
            <td class="evidTableDataColTwo">{e["evid_desc"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Model #:</td>
            <td class="evidTableDataColTwo">{e["evid_model_num"]}</td>
        </tr>
        <tr>
            <td class="evidTableDataColOne">Serial #:</td>
            <td class="evidTableDataColTwo">{e["evid_serial_num"]}</td>
        </tr>""" for e in evidence])

    header = build_case_header_html(
        active_case,
        page_title="Items Seized at Search Warrant Site",
        sub_title="( RETURN COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>V·E·C·T·O·R | Basic Evidence Inventory List</title>
    <style>
        {COMMON_STYLES}
    <style>
</head>
<body>
    {header}
    <table class="evidTable">
        {evid_rows}
    </table>
    {footer}
</body>
</html>"""

# ── Room List Report HTML Template
def build_rooms_report_html(active_case: list, rooms: list) -> str:
    """Generates the complete HTML for the Room List report."""

    room_rows = "".join([f"""
        <tr>
            <td class="roomTableData" style="padding-left:25px;">{r["room_label"]}</td>
            <td class="roomTableData">{r["room_desc"]}</td>
            <td class="roomTableData">{r["room_first_agent"]}</td>
            <td class="roomTableData">{r["room_second_agent"]}</td>
        </tr>""" for r in rooms])

    header = build_case_header_html(
        active_case,
        page_title="Rooms at Search Warrant Site",
        sub_title="( AGENT COPY )",
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
    <table class="roomTable">
        <thead>
            <tr>
                <th class="roomTableHeader font-10">Room ID</th>
                <th class="roomTableHeader font-10">Room Name</th>
                <th class="roomTableHeader font-10">Searched By (1)</th>
                <th class="roomTableHeader font-10">Searched By (2)</th>
            </tr>
        </thead>
        <tbody>
            {room_rows}
        </tbody>
    </table>
    {footer}
</body>
</html>"""

# ── Person List Report HTML Template
def build_persons_report_html(active_case: list, persons: list) -> str:
    """Generates the complete HTML for the Person List report."""

    person_rows = "".join([f"""
        <tr>
            <td class="personTableData">{p["sus_name"]}</td>
            <td class="personTableData">{p["sus_dob"]}</td>
            <td class="personTableData">{p["sus_address"]}</td>
            <td class="personTableData">{p["sus_phone"]}</td>
            <td class="personTableData">{p["sus_notes"]}</td>
        </tr>""" for p in persons])

    header = build_case_header_html(
        active_case,
        page_title="Persons List",
        sub_title="( AGENT COPY )",
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
    <table class="personTable">
        <thead>
            <tr>
                <th class="personTableHeader">Person Name</th>
                <th class="personTableHeader">DOB</th>
                <th class="personTableHeader">Address</th>
                <th class="personTableHeader">Phone #</th>
                <th class="personTableHeader">Notes</th>
            </tr>
        </thead>
        <tbody>
            {person_rows}
        </tbody>
    </table>
    {footer}
</body>
</html>"""

# ── Notes Report HTML Template
def build_notes_report_html(active_case: list, notes: list) -> str:
    """Generates the complete HTML for the Notes report."""

    note_rows = "".join([f"""
        <tr>
            <td class="noteTableData">{n["note_date_time"]}</td>
            <td class="noteTableData">{n["note_date_time_updated"]}</td>
            <td class="noteTableData">{n["note_author"]}</td>
            <td class="noteTableData">{n["note_text"]}</td>
        </tr>""" for n in notes])

    header = build_case_header_html(
        active_case,
        page_title="Search Warrant Notes",
        sub_title="( AGENT COPY )",
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
    <table class="noteTable">
        <thead>
            <tr>
                <th class="noteTableHeader">Date/Time Added</th>
                <th class="noteTableHeader">Date/Time Updated</th>
                <th class="noteTableHeader">Author</th>
                <th class="noteTableHeader">Text</th>
            </tr>
        </thead>
        <tbody>
            {note_rows}
        </tbody>
    </table>
    {footer}
</body>
</html>"""

# ── Updated Agents Route
@ui.page("/reports/agents")
def print_agents_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:

        active_case = get_case_info()

        agents = [
            {
                "agent_name": a.agent_name,
                "agent_initials": a.agent_initials,
                "agent_parent_agency": a.agent_parent_agency,
                "agent_role": a.agent_role,
                "agent_phone": a.agent_phone,
                "agent_notes": a.agent_notes or "",
            }
            for a in session.query(Agents).all()
        ]

    html = build_agents_report_html(
        active_case=active_case,
        agents=agents
    )

    render_report_page(html_content=html)

# ── Updated Evidence Routes
@ui.page("/reports/evidence")
def print_evidence_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:

        active_case = get_case_info()

        evidence = [
            {
                "evid_num": e.evid_num,
                "evid_qty": e.evid_qty,
                "evid_desc": e.evid_desc,
                "evid_model_num": e.evid_model_num,
                "evid_serial_num": e.evid_serial_num,
                "evid_loc_room": e.evid_loc_room,
                "evid_loc_room_detail": e.evid_loc_room_detail,
                "evid_found_by": e.evid_found_by,
                "evid_found_by_witness": e.evid_found_by_witness,
                "evid_pic_taken": e.evid_pic_taken,
                "evid_triaged": e.evid_triaged,
                "evid_triaged_by": e.evid_triaged_by,
                "evid_notes": e.evid_notes,
            }
            for e in session.query(Evidence).order_by(Evidence.evid_num).all()
        ]

    html = build_evidence_report_html(
        active_case=active_case,
        evidence=evidence
    )

    render_report_page(html_content=html)

# ── Updated Evidence By Room Route
@ui.page("/reports/evidence-by-room")
def print_evidence_by_room_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()

        # Get unique rooms with item counts (matches Flask route query)
        unique_rooms = (
            session.query(
                Evidence.evid_loc_room,
                func.count(Evidence.evid_loc_room),
            )
            .group_by(Evidence.evid_loc_room)
            .all()
        )

        # Convert to list of tuples for the template
        unique_rooms_list = [(r[0], r[1]) for r in unique_rooms]

        evidence = [
            {
                "evid_num": e.evid_num,
                "evid_qty": e.evid_qty,
                "evid_desc": e.evid_desc,
                "evid_model_num": e.evid_model_num,
                "evid_serial_num": e.evid_serial_num,
                "evid_loc_room": e.evid_loc_room,
                "evid_loc_room_detail": e.evid_loc_room_detail,
                "evid_found_by": e.evid_found_by,
                "evid_found_by_witness": e.evid_found_by_witness,
                "evid_pic_taken": e.evid_pic_taken,
                "evid_triaged": e.evid_triaged,
                "evid_triaged_by": e.evid_triaged_by,
                "evid_notes": e.evid_notes,
            }
            for e in session.query(Evidence).order_by(Evidence.evid_num).all()
        ]

    html = build_evidence_by_room_report_html(
        active_case=active_case,
        evidence=evidence,
        unique_rooms=unique_rooms_list,
    )

    render_report_page(html_content=html)

# ── Updated Basic Evidence Report Route
@ui.page("/reports/evidence-basic")
def print_basic_evidence_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        evidence = [
            {
                "evid_num": e.evid_num,
                "evid_qty": e.evid_qty,
                "evid_desc": e.evid_desc,
                "evid_model_num": e.evid_model_num,
                "evid_serial_num": e.evid_serial_num,
            }
            for e in session.query(Evidence).order_by(Evidence.evid_num).all()
        ]

    html = build_basic_evidence_report_html(
        active_case=active_case,
        evidence=evidence
    )

    render_report_page(html_content=html)

# ── Updated Rooms Route
@ui.page("/reports/rooms")
def print_rooms_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        rooms = [
            {
                "room_label": r.room_label,
                "room_desc": r.room_desc,
                "room_first_agent": r.room_first_agent,
                "room_second_agent": r.room_second_agent,
            }
            for r in session.query(Rooms).order_by(Rooms.room_label).all()
        ]

    html = build_rooms_report_html(
        active_case=active_case,
        rooms=rooms
    )

    render_report_page(html_content=html)

# ── Updated Persons Route
@ui.page("/reports/persons")
def print_persons_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        persons = [
            {
                "sus_name": p.sus_name,
                "sus_dob": p.sus_dob or "",
                "sus_address": p.sus_address or "",
                "sus_phone": p.sus_phone or "",
                "sus_notes": p.sus_notes or "",
            }
            for p in session.query(Persons).order_by(Persons.sus_name).all()
        ]

    html = build_persons_report_html(
        active_case=active_case,
        persons=persons
    )

    render_report_page(html_content=html)

# ── Updated Notes Route
@ui.page("/reports/notes")
def print_notes_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()
        notes = [
            {
                "note_date_time": n.note_date_time,
                "note_date_time_updated": n.note_date_time_updated or "",
                "note_author": n.note_author,
                "note_text": n.note_text or "",
            }
            for n in session.query(Notes).order_by(Notes.note_date_time).all()
        ]

    html = build_notes_report_html(
        active_case=active_case,
        notes=notes
    )

    render_report_page(html_content=html)

# ── JSON Output
@ui.page("/reports/json")
def json_output_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    ui.label("JSON Data Output").classes("text-2xl font-bold m-4")

    with get_session() as session:

        case = session.query(Cases).first()

        data = {
            "case": {
                    "case_number": case.case_number,
                    "location": case.location,
                    "jurisdiction": case.jurisdiction,
                    "case_date_time_begin": case.case_date_time_begin,
                    "case_date_time_end": case.case_date_time_end,
                },
            "agents": [
                {
                    "agent_name": a.agent_name,
                    "agent_initials": a.agent_initials,
                    "agent_parent_agency": a.agent_parent_agency,
                    "agent_role": a.agent_role,
                    "agent_role_secondary": a.agent_role_secondary or "",
                    "agent_phone": a.agent_phone,
                    "agent_notes": a.agent_notes or "",
                }
                for a in session.query(Agents).all()
            ],
            "evidence": [
                {
                    "evid_num": e.evid_num,
                    "evid_qty": e.evid_qty,
                    "evid_desc": e.evid_desc,
                    "evid_model_num": e.evid_model_num,
                    "evid_serial_num": e.evid_serial_num,
                    "evid_loc_room": e.evid_loc_room,
                    "evid_loc_room_detail": e.evid_loc_room_detail,
                    "evid_found_by": e.evid_found_by,
                    "evid_found_by_witness": e.evid_found_by_witness,
                    "evid_pic_taken": e.evid_pic_taken,
                    "evid_triaged": e.evid_triaged,
                    "evid_triaged_by": e.evid_triaged_by,
                    "evid_contains_contraband": e.evid_contains_contraband,
                    "evid_notes": e.evid_notes,
                }
                for e in session.query(Evidence).all()
            ],
            "rooms": [
                {
                    "room_label": r.room_label,
                    "room_desc": r.room_desc,
                    "room_first_agent": r.room_first_agent,
                    "room_second_agent": r.room_second_agent,
                }
                for r in session.query(Rooms).all()
            ],
            "persons": [
                {
                    "sus_name": p.sus_name,
                    "sus_dob": p.sus_dob or "",
                    "sus_address": p.sus_address or "",
                    "sus_phone": p.sus_phone or "",
                    "sus_notes": p.sus_notes or "",
                }
                for p in session.query(Persons).all()
            ],
            "notes": [
                {
                    "note_date_time": n.note_date_time,
                    "note_date_time_updated": n.note_date_time_updated or "",
                    "note_author": n.note_author,
                    "note_text": n.note_text,
                }
                for n in session.query(Notes).all()
            ],
        }

    json_str = json.dumps(data, indent=4)

    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        ui.button(
            "Copy JSON",
            on_click=lambda: ui.run_javascript(
                f"navigator.clipboard.writeText('{json_str}')"
            ),
        ).props("outline icon=content_copy").classes("mb-4")

        ui.code(json_str, language="json").classes("w-full")

def open_report_window():
    """Extracts the report innerHTML and opens it in a clean new tab.

    The report can be printed after validation has occured.
    """

    # Validate all of the requirements are met before opening the report
    is_valid, errors = validate_case_for_report()
    if not is_valid:
        show_validation_errors(errors)
        return

    REPORT_PRINT_STYLES = COMMON_STYLES.replace('"', '\\"')

    ui.run_javascript(f"""
        const reportContent = document.getElementById('report-container');
        if (!reportContent) {{
            alert('No report content found to print.');
            return;
        }}

        const html = reportContent.innerHTML;

        const newWindow = window.open('', '_blank');
        if (!newWindow) {{
            alert('Pop-up blocked. Please allow pop-ups for this site.');
            return;
        }}

        const fullHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>V·E·C·T·O·R</title>
    <style>
        {REPORT_PRINT_STYLES}
    </style>
</head>
<body>
    <div class="print-toolbar no-print">
        <button class="print-btn" onclick="window.print()">🖨️ Print Report</button>
        <button class="close-btn" onclick="window.close()">✕ Close</button>
    </div>
    <div class="report-body">
        ${{html}}
    </div>
    <script>
        // Auto-trigger print dialog after a short delay
        setTimeout(() => {{ window.print(); }}, 500);
    </script>
</body>
</html>`;

        newWindow.document.write(fullHtml);
        newWindow.document.close();
    """)
