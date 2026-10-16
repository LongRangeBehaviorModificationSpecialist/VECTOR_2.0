"""
test_reports.py

Report rendering.

Every report shares one case header, so a single stale key took all
seven down with KeyError: 'case_number'. These tests exist to make that
class of failure loud.
"""

import hashlib
from datetime import datetime

import pytest

from models import (
    Agents,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
    get_session,
)
from utils import get_case_info
import parts.reports_page as reports


def _rows(model):
    with get_session() as session:
        return [
            {column.name: getattr(row, column.name)
            for column in model.__table__.columns}
            for row in session.query(model).all()
        ]


def _build(name):
    """Renders one report from whatever is currently in the database."""
    active_case = get_case_info()
    evidence = _rows(Evidence)
    builders = {
        "agents": lambda: reports.build_agents_report_html(
            active_case, _rows(Agents)),
        "evidence": lambda: reports.build_evidence_report_html(
            active_case, evidence),
        "evidence_by_room": lambda: (
            reports.build_evidence_by_room_report_html(
                active_case,
                evidence,
                [(item["EVIDLOCROOM"], 1) for item in evidence],
            )
        ),
        "evidence_basic": lambda: reports.build_basic_evidence_report_html(
            active_case, evidence),
        "rooms": lambda: reports.build_rooms_report_html(
            active_case, _rows(Rooms)),
        "persons": lambda: reports.build_persons_report_html(
            active_case, _rows(Persons)),
        "notes": lambda: reports.build_notes_report_html(
            active_case, _rows(Notes)),
        "files": lambda: reports.build_files_report_html(
            active_case, _file_rows()),
    }
    return builders[name]()


def _file_rows():
    with get_session() as session:
        return reports.files_report_rows(session)


REPORT_NAMES = [
    "agents",
    "evidence",
    "evidence_by_room",
    "evidence_basic",
    "rooms",
    "persons",
    "notes",
    "files",
]


@pytest.mark.parametrize("report_name", REPORT_NAMES)
def test_report_renders(populated, report_name):
    """Each report produces HTML rather than raising."""
    html = _build(report_name)
    assert isinstance(html, str)
    assert len(html) > 200


@pytest.mark.parametrize("report_name", REPORT_NAMES)
def test_report_carries_the_case_number(populated, report_name):
    """The case header is what broke; assert it actually rendered."""
    assert populated in _build(report_name)


@pytest.mark.parametrize("report_name", REPORT_NAMES)
def test_report_header_fields_present(populated, report_name):
    """Location and jurisdiction come from the same stale-key block."""
    html = _build(report_name)
    assert "14 Elm Street, Apt 3" in html
    assert "Fairfax County" in html


def test_evidence_values_are_html_escaped(populated):
    """A description with & or < must not reach the page raw."""
    html = _build("evidence")
    assert "Smith &amp; Wesson" in html
    assert "&lt;item 1&gt;" in html
    assert "<item 1>" not in html


def test_script_tag_cannot_execute(case):
    """Stored values must never render as live markup."""
    with get_session() as session:
        session.add(
            Evidence(
                EVIDNUM="1",
                EVIDQTY="1",
                EVIDDESC="<script>alert('xss')</script>",
                EVIDLOCROOM="Room A",
                EVIDLOCROOMDETAIL="floor",
                EVIDFOUNDBY="Doe, John",
                EVIDFOUNDBYWITNESS="Roe, Jane",
            )
        )
    html = _build("evidence")
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_evidence_by_room_groups_items(populated):
    """The room filter used a stale key and silently matched nothing."""
    html = _build("evidence_by_room")
    assert "Room A (Bedroom)" in html
    # All twelve items live in that room, so each number should appear.
    assert "12" in html


def test_the_files_report_prints_local_time_and_the_hash(case):
    """Upload times are stored in UTC. Printed as stored, 03:05 on the
    29th read as a local time for a file uploaded at 23:05 on the 28th."""
    photo = b"scene photograph"
    with get_session() as session:
        session.add(
            UploadedFiles(
                FILENAME="<scene>.jpg",
                FILEDATA=photo,
                FILESIZE=len(photo),
                FILEMIMETYPE="image/jpeg",
                FILEUPLOADEDBY="Doe, John",
                FILEUPLOADDATE=datetime(2026, 9, 29, 3, 5, 35),
                # Recorded in lower case, as attachments before now were.
                FILESHA256=hashlib.sha256(photo).hexdigest(),
            )
        )
    html = _build("files")
    assert "2026-09-29 03:05:35" not in html
    assert "UTC" in html
    assert hashlib.sha256(photo).hexdigest().upper() in html
    assert "&lt;scene&gt;.jpg" in html and "<scene>" not in html


def test_a_room_heading_prints_its_apostrophe_and_ampersand(case):
    """The Evidence by Room heading escaped the room's name twice, so
    "Kid's Room & Closet" printed as "Kid&#x27;s Room &amp; Closet"."""
    room = "Room B (Kid's Room & Closet)"
    with get_session() as session:
        session.add(
            Evidence(
                EVIDNUM="1",
                EVIDQTY="1",
                EVIDDESC="Tablet",
                EVIDLOCROOM=room,
                EVIDLOCROOMDETAIL="under the bed",
                EVIDFOUNDBY="Doe, John",
                EVIDFOUNDBYWITNESS="Roe, Jane",
            )
        )
    html = _build("evidence_by_room")
    assert "Kid&#x27;s Room &amp; Closet) :" in html
    assert "&amp;#x27;" not in html and "&amp;amp;" not in html


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    import settings
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    return settings


def test_reports_leave_out_when_they_were_printed_by_default(
        populated, settings_file):
    for report_name in REPORT_NAMES:
        assert "Report Printed Date" not in _build(report_name), report_name


def test_the_printed_date_appears_once_asked_for(populated, settings_file):
    settings_file.set_report_print_date(True)
    for report_name in REPORT_NAMES:
        assert "Report Printed Date" in _build(report_name), report_name


def test_turning_the_printed_date_on_is_recorded(case, settings_file):
    from models import AuditLog
    from utils import set_report_print_date

    set_report_print_date(True, actor="Doe, John")

    assert settings_file.report_print_date() is True
    with get_session() as session:
        entry = (
            session.query(AuditLog)
            .filter(AuditLog.action == "SETTING_CHANGED")
            .one()
        )
        assert entry.actor == "Doe, John"
        assert "report printed date turned on" in entry.summary


def test_the_print_window_copies_the_report_and_not_the_page():
    """The window is opened by the click, in the browser, and copies only
    #report-container -- which no longer holds the Print button."""
    script = reports.print_window_script()
    assert "window.open(" in script
    assert "report-container" in script
    assert "🖨️ Print Report" in script and "✕ Close" in script
    script.encode("utf-8")  # no lone surrogates for the websocket


def test_the_print_window_names_its_report_and_case():
    script = reports.print_window_script("Agent List", "26-DEMO-001")
    assert "Agent List · 26-DEMO-001" in script
    assert "This bar is not printed" in script
    assert 'class=\\"print-toolbar no-print\\"' in script


def test_a_case_number_cannot_break_the_print_window():
    """The case number is typed in by an agent; in the window it is text."""
    script = reports.print_window_script("Agent List", '<b>"26"</b>__STYLES__')
    assert "<b>" not in script
    assert "&lt;b&gt;" in script
    assert "__STYLES__" in script  # left as typed, not filled in


def test_the_print_window_has_a_white_page_of_its_own():
    """Chrome opens the window dark when the computer is in dark mode, and
    the report's text is black. The white page belongs to the window only:
    the same report styles are drawn inside VECTOR's dark pages."""
    assert "background: #FFFFFF" in reports.PRINT_WINDOW_STYLES
    assert "html, body" not in reports.COMMON_STYLES
    assert "PRINT_WINDOW_STYLES" not in reports.COMMON_STYLES
    script = reports.print_window_script()
    assert "background: #FFFFFF" in script


def test_reports_survive_an_empty_case(case):
    """A case with no agents, rooms or evidence still renders."""
    for report_name in REPORT_NAMES:
        html = _build(report_name)
        assert case in html
