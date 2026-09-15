#!/usr/bin/env python3

"""
reports_page.py

Each report renders as formatted HTML that prints exactly like the original
Flask templates. Uses window.print() for native browser printing.


Routes:
    /reports/agents            →  Agent list report
    /reports/evidence_basic    →  Basic evidence inventory (return copy)
    /reports/rooms             →  Room list (pending template)
    /reports/evidence          →  Detailed evidence (pending template)
    /reports/evidence_by_room  →  Evidence by room (pending template)
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

from html import escape
from nicegui import ui
from sqlalchemy import func

from models import get_session, Agents, Cases, Evidence, Notes, Persons, Rooms
from navbar import build_navbar
from auth import is_authenticated, get_current_user_name, get_is_admin
from utils import get_print_date_time, get_case_info


# ----- HTML Escaping -----
def h(value) -> str:
    """Escapes a database value for safe interpolation into report HTML.

    Without this, a description containing "&" or "<" corrupts the
    printed exhibit list, and a "<script>" tag executes in the print
    window.
    """
    return escape("" if value is None else str(value))



# ----- Report Page Wrapper -----
def build_reports_page() -> None:

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("items-center w-full mt-4 mb-4"):

        ui.image(
            "/static/novadc_icac.png",
        ).classes("w-[150px] h-[150px] mb-4")

        ui.label(
            "V·E·C·T·O·R Reports Page"
        ).classes("text-2xl font-normal text-center")

    with ui.column().classes("w-full items-center gap-4"):
        with ui.column().classes("w-full max-w-xs"):

            ui.button(
                "Print Agent List",
                on_click=lambda: ui.navigate.to("/reports/agents"),
                color="#1C69A8",
            ).props("push").classes("w-full py-3")

            ui.button(
                "Print Room List",
                on_click=lambda: ui.navigate.to("/reports/rooms"),
                color="#1C69A8",
            ).props("push").classes("w-full py-3")

            ui.button(
                "Print Evidence List (Full)",
                on_click=lambda: ui.navigate.to("/reports/evidence"),
                color="#1C69A8",
            ).props("push").classes("w-full py-3")

            ui.button(
                "Print Evidence List (By Room)",
                on_click=lambda: ui.navigate.to("/reports/evidence_by_room"),
                color="#1C69A8",
            ).props("push").classes("w-full py-3")

            ui.button(
                "Print Evidence List (Basic)",
                on_click=lambda: ui.navigate.to("/reports/evidence_basic"),
                color="#1C69A8",
            ).props("push").classes("w-full py-3")

            ui.button(
                "Print Persons List",
                on_click=lambda: ui.navigate.to("/reports/persons"),
                color="#1C69A8",
            ).props("push").classes("w-full py-3")

            ui.button(
                "Print Notes List",
                on_click=lambda: ui.navigate.to("/reports/notes"),
                color="#1C69A8",
            ).props("push").classes("w-full py-3")


def render_report_page(html_content: str) -> None:
    """Wraps report HTML with navigation and print button."""
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):

        with ui.element().props("id='report-container'").classes("w-full"):

            ui.button(
                "Print Report",
                on_click=open_report_window,
                color="#1C69A8",
            ).props("push icon=print").classes("mb-4 no-print")

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
        evidence = session.query(Evidence).all()

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

        # Check End Date/Time (required for complete reports)
        if not case.CASEDATETIMEBEGIN:
            errors.append("End Date/Time is required for reports.")

    return (len(errors) == 0, errors)


def show_validation_errors(errors: list[str]) -> None:
    """Displays validation errors as a NiceGUI notification."""
    if len(errors) == 1:
        ui.notify(
            errors[0],
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )
    else:
        error_text = "\n".join(f"• {err}" for err in errors)
        ui.notify(
            f"Cannot generate report — missing information:\n\n{error_text}.",
            type="negative",
            timeout=0,
            position="center",
            close_button="OK",
        )


# ----- Common Print Styles -----
COMMON_STYLES = """
@media print {
    .no-print {
        display: none !important;
    }
    body {
        background: white !important;
        color: black !important;
    }
    .top-table .agentTable thead tr th.agentTableHeader,
    .top-table .noteTable thead tr th.noteTableHeader,
    .top-table .personTable thead tr th.personTableHeader,
    .top-table .roomTable thead tr th.roomTableHeader,
    .top-table .evidTableItemRow {
        border-collapse: collapse;
        font-weight: lighter;
        padding: 0pt 0pt 3pt 5pt;
    }
    .headerTable tr td.data,
    .evidTableRoomNameRow,
    .top-table .evidTable tr td.evidTableData {
        font-family: "Times New Roman", Times, serif;
        font-size: 11pt;
    }

    .evidTableRoomNameRow,
    .top-table .evidTable tr td.evidTableData {
        font-weight: bold;
    }


    .headerTable tr td.header,
    .headerTable tr td.data {
        vertical-align: "bottom";
    }
    .top-table .agentTable tbody tr td.agentTableData,
    .top-table .evidTable tr td.evidTableDataColTwo,
    .top-table .noteTable tbody tr td.noteTableData,
    .top-table .personTable tbody tr td.personTableData,
    .top-table .roomTable tbody tr td.roomTableData {
        font-family: "Times New Roman", Times, serif;
        font-size: 11pt;
        padding: 5px 5px 3px 5px;
        vertical-align: "bottom";
    }
    .top-table .evidTable tr td.evidTableDataColOne,
    .top-table .evidTable tr td.evidTableDataColTwo {
        height: 1.45rem;
    }
    .top-table .evidTable tr td.evidTableDataColOne {
        font-size: 10pt;
    }
    .top-table .evidTable tr td.evidTableDataColTwo {
        font-size: 12pt;
        padding: 0pt 6pt;
    }
    .top-table .headerTable tr td.header {
        font-size: 10pt;
    }
    .reportTitle p.fs-5 {
        font-size: 10pt;
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
    padding: 0pt 6pt;
}

.top-table {
    padding-left: 5%;
    padding-right: 5%;
}

.evidTable {
    border-collapse: collapse;
    margin-left: auto;
    margin-right: auto;
    margin-bottom: 2em;
    width: 100%;
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
    border-bottom: 1px dashed black;
    width: 65%;
    vertical-align: bottom;
}

/* Shared table styles */
.agentTable,
.noteTable,
.roomTable,
.personTable {
    border-collapse: collapse;
    width: 100%;
}

.agentTableHeader,
.noteTableHeader,
.roomTableHeader,
.personTableHeader {
    border-collapse: collapse;
    font-weight: 650;
    padding: 0pt 5pt;
    text-align: left;
}

.agentTable thead tr,
.noteTable thead tr,
.roomTable thead tr,
.personTable thead tr {
    border-top: 0px solid black;
    border-bottom: 1px dashed black;
}

.agentTableData,
.noteTableData,
.roomTableData,
.personTableData {
    border-bottom: 1px dashed black;
    height: 1.85em;
    padding: 0pt 5pt;
    vertical-align: bottom;
}

/* Evidence table styles */
.evidTableItemRow {
    text-align: center;
    font-weight: 700;
}

td.evidTableData {
    border-bottom: 0px solid black;
    height: 1.75em;
    font-size: 11pt;
    padding: 2px 5px;
}

td.evidTableDataColOne {
    height: 1.85em;
    padding: 0px 5px;
    font-weight: normal;
    width: 20%;
    vertical-align: bottom;
}

td.evidTableDataColTwo {
    border-bottom: 1px dashed black;
    height: 1.85em;
    width: 80%;
    vertical-align: bottom;
}

.evidTableRoomNameRow {
    border-bottom: 0px dashed black;
    height: 1.5em;
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


# ----- Case Header Builder -----
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
            timeout=0,
            close_button="OK",
            position="center",
        )
        # Redirect to case creation page
        ui.navigate.to("/cases")
        # Stop here: without this the header below subscripts None and
        # the whole report route returns a 500 instead of redirecting.
        return ""

    print_date_time = get_print_date_time()

    report_header_table = f"""
    <div class="top-table">
        <table class="headerTable">
            <tr>
                <td class="header font-11">Investigation Number:</td>
                <td class="data font-11">{h(active_case["CASENUMBER"])}</td>
            </tr>
            <tr>
                <td class="header font-11">Site Address:</td>
                <td class="data font-11">{h(active_case["LOCATION"])}</td>
            </tr>
            <tr>
                <td class="header font-11">Jurisdiction:</td>
                <td class="data font-11">{h(active_case["JURISDICTION"])}</td>
            </tr>
            <tr>
                <td class="header font-11">Starting Date and Time:</td>
                <td class="data font-11">{h(active_case["CASEDATETIMEBEGIN"])}</td>
            </tr>
            <tr>
                <td class="header font-11">Ending Date and Time:</td>
                <td class="data font-11">{h(active_case["CASEDATETIMEEND"])}</td>
            </tr>
            <tr>
                <td class="header font-11">Report Printed Date:</td>
                <td class="data font-11">{print_date_time}</td>
            </tr>
        </table>
    </div>"""

    return f"""
    <div class="reportTitle">
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


# ----- Agent List Report HTML Template -----
def build_agents_report_html(active_case: dict, agents: list) -> str:
    """Generates the complete HTML for the Agent List report."""

    agent_rows = "".join([f"""
        <tr>
            <td class="agentTableData font-10">{h(a["AGENTNAME"])}</td>
            <td class="agentTableData font-10">{h(a["AGENTPARENTAGENCY"])}</td>
            <td class="agentTableData font-10">{h(a["AGENTPRIMARYROLE"])}</td>
            <td class="agentTableData font-10">{h(a["AGENTPHONE"])}</td>
            <td class="agentTableData font-10">{h(a["AGENTEMAIL"])}</td>
        </tr>"""
        for a in agents]
    )

    header = build_case_header_html(
        active_case,
        page_title="INVESTIGATORS AT SEARCH WARRANT SITE",
        sub_title="(Agent Copy)",
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
        <table class="agentTable">
            <thead>
                <tr>
                    <th class="agentTableHeader font-10">Agent Name</th>
                    <th class="agentTableHeader font-10">Agency</th>
                    <th class="agentTableHeader font-10">Primary Role</th>
                    <th class="agentTableHeader font-10">Phone Number</th>
                    <th class="agentTableHeader font-10">Email</th>
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


# ----- Detailed Evidence Report HTML Template (AGENT COPY) -----
def build_evidence_report_html(active_case: list, evidence: list) -> str:
    """Generates the complete HTML for the detailed Evidence report.

    Each item is displayed as vertical label/value rows with ALL fields.

    This is the "AGENT COPY" version.
    """

    evid_rows = "".join([f"""
            <tr class="evidTableItemRow">
                <td colspan="2" class="evidTableData">
                    Item #:&ensp;{h(e["EVIDNUM"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Quantity:</td>
                <td class="evidTableDataColTwo px-6">{h(e["EVIDQTY"])}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Description:</td>
                <td class="evidTableDataColTwo px-6">{h(e["EVIDDESC"])}</td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Model #:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDMODELNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Serial #:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDSERIALNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Location:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDLOCROOM"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Where Found:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDLOCROOMDETAIL"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Located By:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDFOUNDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Witnessed By:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDFOUNDBYWITNESS"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Photographed:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDPICTAKEN"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Item Triaged:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDTRIAGED"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Item Triaged By:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDTRIAGEDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Notes:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDNOTE"])}
                </td>
            </tr>
            <tr>
                <td colspan="2" style="height: 1.25em;"></td>
            </tr>"""
            for e in evidence
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="FULL EVIDENCE INVENTORY LIST",
        sub_title="(Agent Copy)",
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
        <table class="evidTable">
            {evid_rows}
        </table>
    </div>
    {footer}
</body>
</html>"""


# ----- Evidence By Room Report HTML Template -----
def build_evidence_by_room_report_html(
        active_case: list,
        evidence: list,
        unique_rooms: list
) -> str:
    """Generates the complete HTML for the Evidence By Room report.

    Groups evidence items under dark-background room headers with item counts.

    Uses the same full detail layout as the AGENT COPY evidence report.
    """

    room_tables = ""

    for room in unique_rooms:
        room_name = room[0]
        item_count = room[1]

        # Singular vs plural
        if item_count == 1:
            count_text = f"{h(room_name)}&ensp;:&ensp;({item_count} item)"
        else:
            count_text = f"{h(room_name)}&ensp;:&ensp;({item_count} items)"

        # Filter evidence items for this room
        room_items = [e for e in evidence if e["EVIDLOCROOM"] == room_name]
        evid_rows = "".join([f"""
            <tr>
                <td class="evidTableDataColOne">Item No.:</td>
                <td class="evidTableDataColTwo px-6" style="font-weight:bold">
                    {h(e["EVIDNUM"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Quantity:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDQTY"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Description:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDDESC"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Model #:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDMODELNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Serial #:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDSERIALNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Location:</td>
                <td class="evidTableDataColTwo px-6">
                    Room {h(e["EVIDLOCROOM"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Where Found</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDLOCROOMDETAIL"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Located By:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDFOUNDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Witnessed By:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDFOUNDBYWITNESS"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Photographed:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDPICTAKEN"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Item Triaged:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDTRIAGED"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Item Triaged By:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDTRIAGEDBY"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Notes:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDNOTE"])}
                </td>
            </tr>
            <tr>
                <td colspan="2" style="height: 1.25em;"></td>
            </tr>
            """
            for e in room_items
        ]
    )

        room_tables += f"""
        <div class="top-table">
            <table class="evidTable">
                <thead>
                </thead>
                <tbody>
                    <tr class="evidTableRoomNameRow">
                        <th colspan="2">{h(count_text)}</th>
                    </tr>
                    {evid_rows}
                </tbody>
            </table>
        </div>
        </br />"""

    header = build_case_header_html(
        active_case,
        page_title="EVIDENCE FOUND LIST BY ROOM",
        sub_title="(Agent Copy)",
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


# ----- Basic Evidence Report HTML Template (RETURN COPY) -----
def build_basic_evidence_report_html(
        active_case: list,
        evidence: list
) -> str:
    """Generates the complete HTML for the Basic Evidence report.

    Each item shows only Item#, Quantity, Description, Model#, and Serial#.

    This is the "RETURN COPY" version.
    """

    evid_rows = "".join([f"""
            <tr class="evidTableItemRow">
                <td colspan="2" class="evidTableData">
                    Item #:&ensp;{h(e["EVIDNUM"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Quantity:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDQTY"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Description:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDDESC"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Model #:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDMODELNUMBER"])}
                </td>
            </tr>
            <tr>
                <td class="evidTableDataColOne">Serial #:</td>
                <td class="evidTableDataColTwo px-6">
                    {h(e["EVIDSERIALNUMBER"])}
                </td>
            </tr>
            <tr>
                <td colspan="2" style="height: 1.25em;"></td>
            </tr>"""
            for e in evidence
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="SEARCH INVENTORY AND RETURN",
        sub_title="(Return Copy)",
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
        <table class="evidTable">
            {evid_rows}
        </table>
    </div>
    {footer}
</body>
</html>"""


# ----- Room List Report HTML Template -----
def build_rooms_report_html(active_case: list, rooms: list) -> str:
    """Generates the complete HTML for the Room List report."""

    room_rows = "".join([f"""
            <tr>
                <td class="roomTableData" style="padding-left:25px;">
                    {h(r["ROOMLABEL"])}
                </td>
                <td class="roomTableData font-10">{h(r["ROOMDESC"])}</td>
                <td class="roomTableData font-10">{h(r["ROOMFIRSTAGENT"])}</td>
                <td class="roomTableData font-10">{h(r["ROOMSECONDAGENT"])}</td>
                <td class="roomTableData font-10">{h(r["ROOMNOTE"])}</td>
            </tr>"""
            for r in rooms
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="ROOM LIST",
        sub_title="(Agent Copy)",
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
        <table class="roomTable">
            <thead>
                <tr>
                    <th class="roomTableHeader font-10">Room ID</th>
                    <th class="roomTableHeader font-10">Room Name</th>
                    <th class="roomTableHeader font-10">Searched By (1)</th>
                    <th class="roomTableHeader font-10">Searched By (2)</th>
                    <th class="roomTableHeader font-10">Notes</th>
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


# ----- Person List Report HTML Template -----
def build_persons_report_html(active_case: list, persons: list) -> str:
    """Generates the complete HTML for the Person List report."""

    person_rows = "".join([f"""
        <tr>
            <td class="personTableData font-10">{h(p["PERSONNAME"])}</td>
            <td class="personTableData font-10">{h(p["PERSONDOB"])}</td>
            <td class="personTableData font-10">{h(p["PERSONADDRESS"])}</td>
            <td class="personTableData font-10">{h(p["PERSONPHONE"])}</td>
            <td class="personTableData font-10">{h(p["SUSPECTNOTE"])}</td>
        </tr>"""
        for p in persons
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="PERSONS LIST",
        sub_title="(Agent Copy)",
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
        <table class="personTable">
            <thead>
                <tr>
                    <th class="personTableHeader font-10">Person Name</th>
                    <th class="personTableHeader font-10">DOB</th>
                    <th class="personTableHeader font-10">Address</th>
                    <th class="personTableHeader font-10">Phone #</th>
                    <th class="personTableHeader font-10">Notes</th>
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


# ----- Notes Report HTML Template -----
def build_notes_report_html(active_case: list, notes: list) -> str:
    """Generates the complete HTML for the Notes report."""

    note_rows = "".join([f"""
        <tr>
            <td class="noteTableData font-10">{h(n["NOTEDATETIME"])}</td>
            <td class="noteTableData font-10">{h(n["NOTEDATETIMEUPDATED"])}</td>
            <td class="noteTableData font-10">{h(n["NOTEAUTHOR"])}</td>
            <td class="noteTableData font-10">{h(n["NOTETEXT"])}</td>
        </tr>
        """
        for n in notes
        ]
    )

    header = build_case_header_html(
        active_case,
        page_title="NOTES LIST",
        sub_title="(Agent Copy)",
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
        <table class="noteTable">
            <thead>
                <tr>
                    <th class="noteTableHeader font-10">Date/Time Added</th>
                    <th class="noteTableHeader font-10">Date/Time Updated</th>
                    <th class="noteTableHeader font-10">Author</th>
                    <th class="noteTableHeader font-10">Text</th>
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


# ----- Updated Agents Route -----
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
        agents=agents
    )

    render_report_page(html_content=html)


# ----- Updated Evidence Routes -----
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
                "EVIDMODELNUMBER": e.EVIDMODELNUMBER,
                "EVIDSERIALNUMBER": e.EVIDSERIALNUMBER,
                "EVIDLOCROOM": e.EVIDLOCROOM,
                "EVIDLOCROOMDETAIL": e.EVIDLOCROOMDETAIL,
                "EVIDFOUNDBY": e.EVIDFOUNDBY,
                "EVIDFOUNDBYWITNESS": e.EVIDFOUNDBYWITNESS,
                "EVIDPICTAKEN": e.EVIDPICTAKEN,
                "EVIDTRIAGED": e.EVIDTRIAGED,
                "EVIDTRIAGEDBY": e.EVIDTRIAGEDBY,
                "EVIDNOTE": e.EVIDNOTE,
            }
            for e in session.query(Evidence).order_by(Evidence.EVIDNUM).all()
        ]

    html = build_evidence_report_html(
        active_case=active_case,
        evidence=evidence
    )

    render_report_page(html_content=html)


# ----- Updated Evidence By Room Route -----
@ui.page("/reports/evidence_by_room")
def print_evidence_by_room_report():

    if not is_authenticated():
        ui.navigate.to("/")
        return

    with get_session() as session:
        active_case = get_case_info()

        # Get unique rooms with item counts (matches Flask route query)
        unique_rooms = (
            session.query(
                Evidence.EVIDLOCROOM,
                func.count(Evidence.EVIDLOCROOM),
            )
            .group_by(Evidence.EVIDLOCROOM)
            .all()
        )

        # Convert to list of tuples for the template
        unique_rooms_list = [(r[0], r[1]) for r in unique_rooms]

        evidence = [
            {
                "EVIDNUM": e.EVIDNUM,
                "EVIDQTY": e.EVIDQTY,
                "EVIDDESC": e.EVIDDESC,
                "EVIDMODELNUMBER": e.EVIDMODELNUMBER,
                "EVIDSERIALNUMBER": e.EVIDSERIALNUMBER,
                "EVIDLOCROOM": e.EVIDLOCROOM,
                "EVIDLOCROOMDETAIL": e.EVIDLOCROOMDETAIL,
                "EVIDFOUNDBY": e.EVIDFOUNDBY,
                "EVIDFOUNDBYWITNESS": e.EVIDFOUNDBYWITNESS,
                "EVIDPICTAKEN": e.EVIDPICTAKEN,
                "EVIDTRIAGED": e.EVIDTRIAGED,
                "EVIDTRIAGEDBY": e.EVIDTRIAGEDBY,
                "EVIDNOTE": e.EVIDNOTE,
            }
            for e in session.query(Evidence).order_by(Evidence.EVIDNUM).all()
        ]

    html = build_evidence_by_room_report_html(
        active_case=active_case,
        evidence=evidence,
        unique_rooms=unique_rooms_list,
    )

    render_report_page(html_content=html)


# ----- Updated Basic Evidence Report Route -----
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
                "EVIDMODELNUMBER": e.EVIDMODELNUMBER,
                "EVIDSERIALNUMBER": e.EVIDSERIALNUMBER,
            }
            for e in session.query(Evidence).order_by(Evidence.EVIDNUM).all()
        ]

    html = build_basic_evidence_report_html(
        active_case=active_case,
        evidence=evidence
    )

    render_report_page(html_content=html)


# ----- Updated Rooms Route -----
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
                "ROOMNOTE": r.ROOMNOTE,
            }
            for r in session.query(Rooms).order_by(Rooms.ROOMLABEL).all()
        ]

    html = build_rooms_report_html(
        active_case=active_case,
        rooms=rooms
    )

    render_report_page(html_content=html)


# ----- Updated Persons Route -----
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
                "PERSONDOB": p.PERSONDOB or "",
                "PERSONADDRESS": p.PERSONADDRESS or "",
                "PERSONPHONE": p.PERSONPHONE or "",
                "SUSPECTNOTE": p.SUSPECTNOTE or "",
            }
            for p in session.query(Persons).order_by(Persons.PERSONNAME).all()
        ]

    html = build_persons_report_html(
        active_case=active_case,
        persons=persons
    )

    render_report_page(html_content=html)


# ----- Updated Notes Route -----
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
                "NOTEDATETIMEUPDATED": n.NOTEDATETIMEUPDATED or "",
                "NOTEAUTHOR": n.NOTEAUTHOR,
                "NOTETEXT": n.NOTETEXT or "",
            }
            for n in session.query(Notes).order_by(Notes.NOTEDATETIME).all()
        ]

    html = build_notes_report_html(
        active_case=active_case,
        notes=notes
    )

    render_report_page(html_content=html)


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
        """
    )
