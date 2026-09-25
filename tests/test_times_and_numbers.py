"""
test_time_and_numbers.py

Times in the machine's time zone, fill-in buttons for case times, the
end-time reminder, dropdowns that keep what was typed, and evidence
numbers that never skip.

Notes and entry times were stamped in UTC, so a note written at 08:45 at a
scene read 12:45. A case time had to be typed out. A report printed a
blank end time without a word. An agent's name typed into its box was lost
unless Enter was pressed. And removing an item left a gap in the numbers.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import clock
import models
import parts.agents_page as agents_page
import parts.cases_page as cases_page
import parts.evidence_page as evidence_page
import parts.notes_page as notes_page
import parts.persons_page as persons_page
import parts.reports_page as reports_page
import parts.rooms_page as rooms_page
import utils
from models import AuditLog, Cases, Evidence, Notes, get_session
from parts.crud import typed_choice

ROOT = Path(__file__).resolve().parent.parent
STAMP = re.compile(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2} UTC[+-]\d{2}:\d{2}$")


def _local(*parts) -> str:
    """The local stamp for a UTC time."""
    return clock.stamp(datetime(*parts, tzinfo=timezone.utc).astimezone())


# ----- The machine's time zone -----
def test_stamps_are_local_with_their_offset():
    for stamped in (
        utils.get_current_timestamp(),
        utils.get_current_timestamp(format="entry")
    ):
        assert STAMP.match(stamped), stamped
        assert stamped.endswith(clock.zone_label())


def test_the_offset_is_this_machines():
    moment = datetime.now().astimezone()
    offset = moment.utcoffset()
    sign = "-" if offset < timedelta(0) else "+"
    minutes = abs(int(offset.total_seconds())) // 60
    assert clock.zone_label(moment) == (
        f"UTC{sign}{minutes // 60:02d}:{minutes % 60:02d}"
    )


def test_offsets_are_written_the_same_way_everywhere():
    eastern = datetime(
        2026, 9, 15, 8, 45, 12,
        tzinfo=timezone(timedelta(hours=-4))
    )
    india = datetime(
        2026, 9, 15, 8, 45,
        tzinfo=timezone(timedelta(hours=5, minutes=30))
    )

    assert clock.stamp(eastern) == "09-15-2026 08:45:12 UTC-04:00"
    assert clock.zone_label(india) == "UTC+05:30"


def test_stored_utc_times_are_shown_in_local_time():
    expected = _local(2026, 9, 15, 12, 45, 12)
    assert clock.show_utc(datetime(2026, 9, 15, 12, 45, 12)) == expected
    assert clock.show_utc("2026-09-15T12:45:12Z") == expected
    assert clock.show_utc("not a time") == "not a time"
    assert clock.show_utc(None) == ""


def test_the_fill_in_time_is_now_as_a_case_time():
    filled = clock.case_time_now()
    parsed = utils.parse_entered_date(filled, utils.CASE_TIME_FORMAT)
    assert parsed is not None

    now = datetime.now().replace(second=0, microsecond=0)
    assert abs(parsed - now) <= timedelta(minutes=1)


def test_utc_stamps_already_saved_are_rewritten_once(populated):
    with get_session() as session:
        session.add(
            Notes(
                NOTEDATETIME="09-01-2026 11:32:00",
                NOTEDATETIMEUPDATED="",
                NOTEAUTHOR="Doe, John",
                NOTETEXT="Written before the change"
            )
        )
        session.query(models.Agents).filter_by(
            AGENTNAME="Doe, John"
        ).one().ENTEREDDATETIME = "2026-09-01 11:35:00"

    models.normalise_legacy_dates()

    with get_session() as session:
        note = session.query(Notes).filter_by(
            NOTETEXT="Written before the change"
        ).one()
        agent = session.query(models.Agents).filter_by(
            AGENTNAME="Doe, John"
        ).one()
        assert note.NOTEDATETIME == _local(2026, 9, 1, 11, 32)
        assert agent.ENTEREDDATETIME == _local(2026, 9, 1, 11, 35)

    assert models.normalise_legacy_dates() == 0


def test_a_local_stamp_is_left_alone(case):
    with get_session() as session:
        session.add(
            Notes(
                NOTEDATETIME=clock.stamp(),
                NOTEAUTHOR="Doe, John",
                NOTETEXT="Written after the change"
            )
        )
    assert models.normalise_legacy_dates() == 0


def test_no_page_labels_its_times_utc():
    for spec in (
        agents_page.SPEC,
        cases_page.SPEC,
        evidence_page.SPEC,
        notes_page.SPEC,
        persons_page.SPEC,
        rooms_page.SPEC
    ):
        for field in spec.fields:
            assert "UTC" not in field.label, (spec.title, field.label)
            assert "UTC" not in (field.table_label or ""), field.table_label
    for page in ("files_page.py", "audit_page.py"):
        assert "(UTC)" not in (
            ROOT / "parts" / page
        ).read_text(encoding="utf-8")


# ----- Filling in a case time -----
def test_both_case_times_offer_the_fill_button():
    for name in ("CASEDATETIMEBEGIN", "CASEDATETIMEEND"):
        assert next(
            f for f in cases_page.SPEC.fields if f.name == name
        ).now_button


def _case_without_an_end(begin="09-15-2026 07:30"):
    with get_session() as session:
        session.add(
            Cases(
                CASENUMBER="26-2",
                LOCATION="1 Test Road",
                JURISDICTION="Fairfax County",
                CASEDATETIMEBEGIN=begin,
                CASEDATETIMEEND=""
            )
        )


def _stored_end():
    with get_session() as session:
        return session.query(Cases).one().CASEDATETIMEEND


def test_the_reminder_fills_in_the_end_time():
    _case_without_an_end()
    saved, message = reports_page.fill_case_end_time("09-15-2026 16:45")
    assert saved and "09-15-2026 16:45" in message
    assert _stored_end() == "09-15-2026 16:45"


def test_an_end_time_before_the_start_is_not_filled_in():
    _case_without_an_end("09-15-2026 18:00")
    saved, message = reports_page.fill_case_end_time("09-15-2026 16:45")
    assert not saved and "Check the start time" in message
    assert _stored_end() == ""


def test_an_end_time_already_entered_is_kept(case):
    saved, _message = reports_page.fill_case_end_time("09-15-2026 16:45")
    assert not saved
    assert _stored_end() == "09-10-2026 16:30"


# ----- Dropdowns keep what was typed -----
def test_a_new_name_typed_and_left_is_kept():
    assert typed_choice(
        "Brand, New",
        ["Doe, John"],
        None,
        allow_new=True,
    ) == "Brand, New"


def test_typed_text_matching_an_option_selects_it():
    assert typed_choice(
        "doe, john",
        ["Doe, John"],
        None,
        allow_new=False,
    ) == "Doe, John"


def test_new_text_is_ignored_where_new_values_are_not_allowed():
    assert typed_choice(
        "Somebody Else",
        ["Doe, John"],
        None,
        allow_new=False,
    ) is None


@pytest.mark.parametrize("text", ["", "   ", "Doe, John", "doe, john"])
def test_blank_or_unchanged_text_changes_nothing(text):
    assert typed_choice(
        text,
        ["Doe, John"],
        "Doe, John",
        allow_new=True
    ) is None


# ----- Item numbers that never skip -----
def _delete_item(number) -> str:
    with get_session() as session:
        item = session.query(Evidence).filter_by(EVIDNUM=number).one()
        removed = {"EVIDNUM": item.EVIDNUM}
        session.delete(item)
        session.flush()
        return evidence_page._close_the_gap(session, removed)


def _numbers():
    with get_session() as session:
        return sorted(
            (item.EVIDNUM for item in session.query(Evidence)),
            key=utils.evidence_number_key
        )


def _count(action):
    with get_session() as session:
        return session.query(AuditLog).filter_by(
            action=action, table_name="EVIDENCE").count()


def test_removing_an_item_moves_the_later_ones_down(populated):
    message = _delete_item("4")
    assert _numbers() == [str(n) for n in range(1, 12)]
    assert "8 later items" in message


def test_each_renumbering_reaches_the_audit_trail(populated):
    updates, deletes = _count("UPDATE"), _count("DELETE")
    _delete_item("4")
    assert _count("UPDATE") == updates + 8
    assert _count("DELETE") == deletes + 1


def test_removing_the_last_item_moves_nothing(populated):
    assert _delete_item("12") == ""
    assert _numbers() == [str(n) for n in range(1, 12)]


def test_a_hand_entered_number_is_left_as_it_is(populated):
    with get_session() as session:
        session.add(Evidence(
            EVIDNUM="12A",
            EVIDQTY="1",
            EVIDDESC="extra",
            EVIDLOCROOM="Room A (Bedroom)",
            EVIDLOCROOMDETAIL="shelf",
            EVIDFOUNDBY="Doe, John",
            EVIDFOUNDBYWITNESS="Roe, Jane"),
        )
    _delete_item("3")
    assert _numbers() == [str(n) for n in range(1, 12)] + ["12A"]


def test_the_delete_dialog_says_what_will_move(populated):
    warning = evidence_page._renumber_warning({"EVIDNUM": "4"})
    assert "5 becomes 4" in warning and "12 becomes 11" in warning
    assert evidence_page._renumber_warning({"EVIDNUM": "12"}) == ""


def test_the_item_number_is_settled_when_the_item_is_saved(populated):
    values = {"EVIDNUM": "99"}
    evidence_page._take_next_number(values)
    assert values["EVIDNUM"] == "13"
