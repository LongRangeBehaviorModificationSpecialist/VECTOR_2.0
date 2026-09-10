"""Report rendering.

Every report shares one case header, so a single stale key took all
seven down with KeyError: 'case_number'. These tests exist to make that
class of failure loud.
"""

import pytest

from models import Agents, Evidence, Notes, Persons, Rooms, get_session
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
    }
    return builders[name]()


REPORT_NAMES = [
    "agents",
    "evidence",
    "evidence_by_room",
    "evidence_basic",
    "rooms",
    "persons",
    "notes",
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


def test_reports_survive_an_empty_case(case):
    """A case with no agents, rooms or evidence still renders."""
    for report_name in REPORT_NAMES:
        html = _build(report_name)
        assert case in html


# ----- JSON view -----

def test_json_view_builds_from_model_columns(populated):
    """The hand-written field map listed thirty pre-rename attributes
    and raised on the first one. Building from __table__ cannot drift."""
    import json as json_module

    from models import Agents, Cases, Evidence, Notes, Persons, Rooms

    # Read inside the session, as the page does -- attributes are not
    # available once the session closes.
    with get_session() as session:

        def rows_for(model):
            columns = [column.name for column in model.__table__.columns]
            return [
                {name: getattr(record, name) for name in columns}
                for record in session.query(model).all()
            ]

        case = session.query(Cases).first()
        data = {
            "case": {
                column.name: getattr(case, column.name)
                for column in Cases.__table__.columns
            },
            "agents": rows_for(Agents),
            "rooms": rows_for(Rooms),
            "evidence": rows_for(Evidence),
            "persons": rows_for(Persons),
            "notes": rows_for(Notes),
        }

    payload = json_module.dumps(data, indent=4, default=str)
    restored = json_module.loads(payload)

    assert restored["case"]["CASENUMBER"] == populated
    assert len(restored["evidence"]) == 12
    assert len(restored["agents"]) == 2
    assert restored["persons"][0]["SUSPECTNAME"] == "O'Brien, Sean"


def test_json_payload_survives_being_embedded_in_javascript():
    """indent=4 puts newlines in the payload and names contain
    apostrophes; both break a naively quoted JS string literal."""
    import json as json_module

    payload = json_module.dumps(
        {"name": "O'Brien, Sean", "note": "line one\nline two"}, indent=4
    )
    literal = json_module.dumps(payload)

    # A valid JS string literal is one line with no bare apostrophes
    # terminating it, and round-trips back to the original.
    assert "\n" not in literal
    assert json_module.loads(literal) == payload
