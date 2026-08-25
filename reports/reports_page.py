"""
reports_page.py — NiceGUI conversion of Flask reports with print-ready HTML templates.

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


NOTIFICATION_TIMEOUT = 1500


# ── Helpers ─────────────────────────────────────────────────
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


def get_case_info() -> list[dict]:
    """Returns case info for report headers."""
    with get_session() as session:
        cases = session.query(Cases).all()
        return [
            {
                "case_number": c.case_number,
                "location": c.location,
                "jurisdiction": c.jurisdiction,
                "case_date_time_begin": c.case_date_time_begin,
                "case_date_time_end": c.case_date_time_end or "",
            }
            for c in cases
        ]


# ── Report Page Wrapper ─────────────────────────────────────
def render_report_page(html_content: str):
    """Wraps report HTML with navigation and print button."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("items-center w-full p-4 no-print"):
        ui.button("Print", on_click=lambda: ui.run_javascript("window.print()")).props(
            "unelevated icon=print"
        ).classes("mb-4")

    ui.html(html_content)


# ── Common Print Styles ──────────────────────────────────────
COMMON_STYLES = """
<style>
@media print {
    .no-print { display: none !important; }
    body { background: white !important; color: black !important; }
}

body {
    box-sizing: border-box;
    color: black;
    font-family: "Arial", sans-serif;
    margin: 0;
    padding: 1em;
}

.reportTitle { text-align: center; margin-bottom: 1em; }
.font-09 { font-size: 9pt; }
.font-10 { font-size: 10pt; }
.font-11 { font-size: 11pt; }
.font-12 { font-size: 12pt; }
.font-16 { font-size: 16pt; }
.fs-3 { font-weight: 700; margin: 0.25em auto 0 auto; text-align: center; }
.fs-5 { margin: 0 auto 2em auto; text-align: center; }

.headerTable {
    border-collapse: collapse;
    margin-bottom: 2em;
    width: 100%;
}
td.header {
    background-color: lightgray;
    font-size: 11pt;
    padding: 1px 10px;
    border: 1px solid black;
    width: 30%;
}
td.data {
    font-family: "Courier New", Courier, monospace;
    font-size: 11pt;
    padding: 3px 20px;
    border: 1px solid black;
    width: 70%;
}

/* Shared table styles */
.agentTable, .noteTable, .roomTable, .personTable, .evidTable {
    border: 2px solid black;
    border-collapse: collapse;
    width: 100%;
}
.agentTableHeader, .noteTableHeader, .roomTableHeader, .personTableHeader {
    background-color: lightgray;
    border-collapse: collapse;
    font-weight: bold;
    padding: 5px;
    text-align: left;
}
.agentTable thead tr, .noteTable thead tr,
.roomTable thead tr, .personTable thead tr {
    border: 2px solid black;
}
.agentTableData, .noteTableData, .roomTableData, .personTableData {
    border-bottom: 1px dotted black;
    height: 1.25em;
    padding: 5px;
}

/* Evidence table styles */
.evidTableItemRow {
    text-align: center;
    border: 2px solid gray;
    font-weight: 700;
}
td.evidTableData {
    border-bottom: 1px dotted gray;
    border-left: 1px solid gray;
    height: 1.15em;
    padding: 5px;
}
td.evidTableDataColOne {
    border-bottom: 1px dotted gray;
    border-left: 1px solid gray;
    height: 1.15em;
    padding: 5px;
    font-weight: bold;
    width: 30%;
}
td.evidTableDataColTwo {
    border-bottom: 1px dotted gray;
    border-left: 1px solid gray;
    height: 1.15em;
    padding: 5px;
    width: 70%;
}
.evidTableRoomNameRow {
    background-color: #515151;
    border: 2px solid gray;
    text-align: center;
}
.evidTableRoomNameRow th {
    background-color: #515151;
    border-bottom: 1pt solid gray;
    border-top: 1px solid gray;
    font-weight: 700;
    padding: 5px;
}

.end {
    font-weight: 600;
    margin-top: 2rem;
    text-align: center;
}
</style>
"""


# ── Case Header Builder ─────────────────────────────────────
def build_case_header_html(cases: list[dict], page_title: str, sub_title: str) -> str:
    """Generates the standard report title + case info header HTML."""
    print_date, print_time = get_print_date_time()

    case_tables = "".join([f"""<table class="headerTable">
            <tr>
                <td class="header font-11">Investigation Number:</td>
                <td class="data font-11">{c["case_number"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Site Address:</td>
                <td class="data font-11">{c["location"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Jurisdiction:</td>
                <td class="data font-11">{c["jurisdiction"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Starting Date and Time:</td>
                <td class="data font-11">{c["case_date_time_begin"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Ending Date and Time:</td>
                <td class="data font-11">{c["case_date_time_end"]}</td>
            </tr>
            <tr>
                <td class="header font-11">Report Printed Date:</td>
                <td class="data font-11">{print_date} at {print_time}</td>
            </tr>
        </table>""" for c in cases])

    return f"""
    <div class="reportTitle">
        <p class="fs-3 font-16">{page_title}</p>
        <p class="fs-5 font-12">{sub_title}</p>
    </div>
    {case_tables}
    """


def build_report_footer_html() -> str:
    """Generates the standard END OF REPORT footer."""
    return """
    <p class="end font-11">
        &ndash;&ensp;&ndash;&ensp;END OF REPORT&ensp;&ndash;&ensp;&ndash;
    </p>
    """


# ── Agent List Report HTML Template ─────────────────────────
def build_agents_report_html(cases: list, agents: list) -> str:
    """Generates the complete HTML for the Agent List report."""

    agent_rows = "".join([f"""<tr>
            <td class="agentTableData font-12">{a["agent_name"]}</td>
            <td class="agentTableData font-12">{a["agent_initials"]}</td>
            <td class="agentTableData font-12">{a["agent_parent_agency"]}</td>
            <td class="agentTableData font-12">{a["agent_role"]}</td>
            <td class="agentTableData font-12">{a["agent_phone"]}</td>
            <td class="agentTableData font-12">{a["agent_notes"] or ""}</td>
        </tr>""" for a in agents])

    header = build_case_header_html(
        cases,
        page_title="Investigators At Search Warrant Site",
        sub_title="( AGENT COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>VECTOR | Agent List Report</title>
    {COMMON_STYLES}
</head>
<body>
    {header}
    <table class="agentTable">
        <thead>
            <tr>
                <th class="agentTableHeader font-12">Agent Name</th>
                <th class="agentTableHeader font-12">Initials</th>
                <th class="agentTableHeader font-12">Agency</th>
                <th class="agentTableHeader font-12">Primary Role</th>
                <th class="agentTableHeader font-12">Primary Phone Number</th>
                <th class="agentTableHeader font-12">Notes</th>
            </tr>
        </thead>
        <tbody>
            {agent_rows}
        </tbody>
    </table>
    {footer}
</body>
</html>"""


# ── Detailed Evidence Report HTML Template (AGENT COPY) ─────
def build_evidence_report_html(cases: list, evidence: list) -> str:
    """
    Generates the complete HTML for the detailed Evidence report.
    Each item is displayed as vertical label/value rows with ALL fields.
    This is the "AGENT COPY" version.
    """

    evid_rows = "".join([f"""<tr class="evidTableItemRow">
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
            <td class="evidTableDataColOne">Witness:</td>
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
        </tr>""" for e in evidence])

    header = build_case_header_html(
        cases,
        page_title="Items Seized at Search Warrant Site",
        sub_title="( AGENT COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>VECTOR | Evidence Inventory List</title>
    {COMMON_STYLES}
</head>
<body>
    {header}
    <table class="evidTable">
        {evid_rows}
    </table>
    {footer}
</body>
</html>"""


# ── Evidence By Room Report HTML Template ───────────────────
def build_evidence_by_room_report_html(
    cases: list, evidence: list, unique_rooms: list
) -> str:
    """
    Generates the complete HTML for the Evidence By Room report.
    Groups evidence items under dark-background room headers with item counts.
    Uses the same full detail layout as the AGENT COPY evidence report.
    """

    room_tables = ""

    for room in unique_rooms:
        room_name = room[0]
        item_count = room[1]

        # Singular vs plural
        if item_count == 1:
            count_text = f"{room_name}&ensp;({item_count} item)"
        else:
            count_text = f"{room_name}&ensp;({item_count} items)"

        # Filter evidence items for this room
        room_items = [e for e in evidence if e["evid_loc_room"] == room_name]

        evid_rows = "".join([f"""<tr class="evidTableItemRow">
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
                <td class="evidTableDataColOne">Witness:</td>
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
            </tr>""" for e in room_items])

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
        cases,
        page_title="Items Seized at Search Warrant Site (By Room)",
        sub_title="( AGENT COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>VECTOR | Evidence Found By Room</title>
    {COMMON_STYLES}
</head>
<body>
    {header}
    {room_tables}
    {footer}
</body>
</html>"""


# ── Basic Evidence Report HTML Template (RETURN COPY) ───────
def build_basic_evidence_report_html(cases: list, evidence: list) -> str:
    """
    Generates the complete HTML for the Basic Evidence report.
    Each item shows only Item#, Quantity, Description, Model#, and Serial#.
    This is the "RETURN COPY" version.
    """

    evid_rows = "".join([f"""<tr class="evidTableItemRow">
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
        cases,
        page_title="Items Seized at Search Warrant Site",
        sub_title="( RETURN COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>VECTOR | Basic Evidence Inventory List</title>
    {COMMON_STYLES}
</head>
<body>
    {header}
    <table class="evidTable">
        {evid_rows}
    </table>
    {footer}
</body>
</html>"""


# ── Room List Report HTML Template ──────────────────────────
def build_rooms_report_html(cases: list, rooms: list) -> str:
    """Generates the complete HTML for the Room List report."""

    room_rows = "".join([f"""<tr>
            <td class="roomTableData" style="padding-left:25px;">{r["room_label"]}</td>
            <td class="roomTableData">{r["room_desc"]}</td>
            <td class="roomTableData">{r["room_first_agent"]}</td>
            <td class="roomTableData">{r["room_second_agent"]}</td>
        </tr>""" for r in rooms])

    header = build_case_header_html(
        cases,
        page_title="Rooms at Search Warrant Site",
        sub_title="( AGENT COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>VECTOR | Room List Report</title>
    {COMMON_STYLES}
</head>
<body>
    {header}
    <table class="roomTable">
        <thead>
            <tr>
                <th class="roomTableHeader">Room ID</th>
                <th class="roomTableHeader">Room Name</th>
                <th class="roomTableHeader">Searched By (1)</th>
                <th class="roomTableHeader">Searched By (2)</th>
            </tr>
        </thead>
        <tbody>
            {room_rows}
        </tbody>
    </table>
    {footer}
</body>
</html>"""


# ── Person List Report HTML Template ────────────────────────
def build_persons_report_html(cases: list, persons: list) -> str:
    """Generates the complete HTML for the Person List report."""

    person_rows = "".join([f"""<tr>
            <td class="personTableData">{p["sus_name"]}</td>
            <td class="personTableData">{p["sus_dob"]}</td>
            <td class="personTableData">{p["sus_address"]}</td>
            <td class="personTableData">{p["sus_phone"]}</td>
            <td class="personTableData">{p["sus_notes"]}</td>
        </tr>""" for p in persons])

    header = build_case_header_html(
        cases,
        page_title="Persons List",
        sub_title="( AGENT COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>VECTOR | Person List</title>
    {COMMON_STYLES}
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


# ── Notes Report HTML Template ──────────────────────────────
def build_notes_report_html(cases: list, notes: list) -> str:
    """Generates the complete HTML for the Notes report."""

    note_rows = "".join([f"""<tr>
            <td class="noteTableData">{n["note_date_time"]}</td>
            <td class="noteTableData">{n["note_date_time_updated"]}</td>
            <td class="noteTableData">{n["note_author"]}</td>
            <td class="noteTableData">{n["note_text"]}</td>
        </tr>""" for n in notes])

    header = build_case_header_html(
        cases,
        page_title="Search Warrant Notes",
        sub_title="( AGENT COPY )",
    )
    footer = build_report_footer_html()

    return f"""<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="utf-8" />
    <title>VECTOR | Search Warrant Notes</title>
    {COMMON_STYLES}
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


# ── Updated Route ───────────────────────────────────────────
@ui.page("/reports/agents")
def print_agents_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        cases = get_case_info()
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

    html = build_agents_report_html(cases, agents)
    render_report_page(html)


# ── Updated Routes ─────────────────────────────────────────
@ui.page("/reports/evidence")
def print_evidence_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        cases = get_case_info()
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

    html = build_evidence_report_html(cases, evidence)
    render_report_page(html)


# ── Updated Route ───────────────────────────────────────────
@ui.page("/reports/evidence-by-room")
def print_evidence_by_room_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        cases = get_case_info()

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

    html = build_evidence_by_room_report_html(cases, evidence, unique_rooms_list)
    render_report_page(html)


# ── Updated Route ───────────────────────────────────────────
@ui.page("/reports/evidence-basic")
def print_basic_evidence_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        cases = get_case_info()
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

    html = build_basic_evidence_report_html(cases, evidence)
    render_report_page(html)


# ── Updated Route ───────────────────────────────────────────
@ui.page("/reports/rooms")
def print_rooms_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        cases = get_case_info()
        rooms = [
            {
                "room_label": r.room_label,
                "room_desc": r.room_desc,
                "room_first_agent": r.room_first_agent,
                "room_second_agent": r.room_second_agent,
            }
            for r in session.query(Rooms).order_by(Rooms.room_label).all()
        ]

    html = build_rooms_report_html(cases, rooms)
    render_report_page(html)


# ── Updated Route ───────────────────────────────────────────
@ui.page("/reports/persons")
def print_persons_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        cases = get_case_info()
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

    html = build_persons_report_html(cases, persons)
    render_report_page(html)


# ── Updated Route ───────────────────────────────────────────
@ui.page("/reports/notes")
def print_notes_report():
    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        cases = get_case_info()
        notes = [
            {
                "note_date_time": n.note_date_time,
                "note_date_time_updated": n.note_date_time_updated or "",
                "note_author": n.note_author,
                "note_text": n.note_text or "",
            }
            for n in session.query(Notes).order_by(Notes.note_date_time).all()
        ]

    html = build_notes_report_html(cases, notes)
    render_report_page(html)


# ── JSON Output ─────────────────────────────────────────────
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
        data = {
            "case": [
                {
                    "case_number": c.case_number,
                    "location": c.location,
                    "jurisdiction": c.jurisdiction,
                    "case_date_time_begin": c.case_date_time_begin,
                    "case_date_time_end": c.case_date_time_end,
                }
                for c in session.query(Cases).all()
            ],
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

    json_str = json.dumps(data, indent=2)

    with ui.column().classes("w-full max-w-4xl mx-auto p-4"):
        ui.button(
            "Copy JSON",
            on_click=lambda: ui.run_javascript(
                f"navigator.clipboard.writeText(`{json_str}`)"
            ),
        ).props("outline icon=content_copy").classes("mb-4")

        ui.code(json_str, language="json").classes("w-full")
