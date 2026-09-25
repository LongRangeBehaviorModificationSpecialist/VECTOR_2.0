"""
test_order_dates_and_files.py

Report order, room renames, real dates, and attachments that stay in the
database until they are needed.

The return copy listed items 1, 10, 11, 12, 2, because item numbers sorted
as text. Renaming a room left its evidence under the old name. A case time
of 19-45-2026 25:99 was saved as typed. The Files page read every
attachment in full just to list their names, and a download left a copy
of the file in the temp folder.
"""

from pathlib import Path

import pytest
from sqlalchemy import inspect as sa_inspect

import parts.files_page as files_page
import parts.reports_page as reports
import utils
from models import AuditLog, Evidence, Rooms, UploadedFiles, get_session


def _evidence(number, room="Room A (Bedroom)"):
    return Evidence(
        EVIDNUM=number,
        EVIDQTY="1",
        EVIDDESC=f"item {number}",
        EVIDLOCROOM=room,
        EVIDLOCROOMDETAIL="shelf",
        EVIDFOUNDBY="Doe, John",
        EVIDFOUNDBYWITNESS="Roe, Jane",
    )


def _room(label, description):
    return Rooms(
        ROOMLABEL=label,
        ROOMDESC=description,
        ROOMFIRSTAGENT="Doe, John",
        ROOMSECONDAGENT="Roe, Jane",
    )


# ----- Order -----
def test_item_numbers_sort_as_numbers():
    numbers = ["10", "2", "12A", "1", "12", "9"]
    assert sorted(numbers, key=utils.evidence_number_key) == [
        "1", "2", "9", "10", "12", "12A"
    ]


def test_room_labels_continue_past_z():
    labels = ["B", "AA", "Z", "A", "AB"]
    assert sorted(labels, key=utils.room_label_key) == [
        "A", "B", "Z", "AA", "AB"
    ]


def test_the_evidence_reports_list_items_in_number_order(case):
    with get_session() as session:
        for number in ["10", "9", "2", "11", "1"]:
            session.add(_evidence(number))

    with get_session() as session:
        listed = [item.EVIDNUM for item in reports.evidence_in_order(session)]

    assert listed == ["1", "2", "9", "10", "11"]


def test_rooms_follow_label_order_on_every_list(case):
    with get_session() as session:
        session.add_all([
            _room("B", "Kitchen"),
            _room("AA", "Attic"),
            _room("A", "Hall"),
        ])
        session.add_all([
            _evidence("1", "Room AA (Attic)"),
            _evidence("2", "Room B (Kitchen)"),
            _evidence("3", "Room A (Hall)"),
            _evidence("4", "Room A (Hall)"),
        ])

    with get_session() as session:
        assert [
            room.ROOMLABEL for room in reports.rooms_in_order(session)
        ] == ["A", "B", "AA"]
        assert reports.rooms_with_item_counts(session) == [
            ("Room A (Hall)", 2),
            ("Room B (Kitchen)", 1),
            ("Room AA (Attic)", 1),
        ]
    assert utils.load_room_labels() == [
        "Room A (Hall)", "Room B (Kitchen)", "Room AA (Attic)",
    ]


def test_the_on_screen_tables_use_the_same_order():
    from parts.evidence_page import SPEC as evidence_spec
    from parts.rooms_page import SPEC as rooms_spec

    assert sorted(
        [{"EVIDNUM": "10"}, {"EVIDNUM": "2"}],
        key=evidence_spec.sort_key
    ) == [
        {"EVIDNUM": "2"},
        {"EVIDNUM": "10"},
    ]
    assert sorted(
        [{"ROOMLABEL": "AA"}, {"ROOMLABEL": "B"}],
        key=rooms_spec.sort_key
    ) == [
        {"ROOMLABEL": "B"}, {"ROOMLABEL": "AA"}
    ]


# ----- Renaming a room -----
def _rename_room_a(description):
    from parts.rooms_page import _carry_rename_to_evidence

    with get_session() as session:
        _carry_rename_to_evidence(
            session,
            {"ROOMLABEL": "A", "ROOMDESC": "Bedroom"},
            {"ROOMLABEL": "A", "ROOMDESC": description},
        )


def _evidence_updates():
    with get_session() as session:
        return session.query(AuditLog).filter_by(
            action="UPDATE", table_name="EVIDENCE").count()


def test_renaming_a_room_moves_its_evidence_with_it(populated):
    before = _evidence_updates()
    _rename_room_a("Main Bedroom")

    with get_session() as session:
        rooms = {item.EVIDLOCROOM for item in session.query(Evidence)}

    assert rooms == {"Room A (Main Bedroom)"}
    assert _evidence_updates() == before + 12


def test_evidence_in_another_room_is_left_alone(populated):
    with get_session() as session:
        session.add(_evidence("99", "Room B (Bedroom)"))

    _rename_room_a("Main Bedroom")

    with get_session() as session:
        assert session.query(Evidence).filter_by(
            EVIDLOCROOM="Room B (Bedroom)").count() == 1


def test_an_edit_that_keeps_the_name_touches_no_evidence(populated):
    before = _evidence_updates()
    _rename_room_a("Bedroom")
    assert _evidence_updates() == before


# ----- Real dates -----
CASE = dict(
    stage="initial",
    CASENUMBER="26-1",
    LOCATION="14 Elm Street",
    JURISDICTION="Fairfax County",
)


@pytest.mark.parametrize("begin", [
    "19-45-2026 25:99",   # no such month, day, hour or minute
    "02-30-2026 08:00",   # no 30 February
    "09-1",               # half typed
    "09-15-2026",         # no time
    "09-15-0026 08:00",   # a slip of the finger
])
def test_a_case_start_that_is_not_a_real_time_is_refused(begin):
    assert utils.validate_case_entry(CASEDATETIMEBEGIN=begin, **CASE) is True


def test_a_case_cannot_end_before_it_starts():
    assert utils.validate_case_entry(
        CASEDATETIMEBEGIN="09-15-2026 08:00",
        CASEDATETIMEEND="09-15-2026 07:59",
        **CASE,
    ) is True


def test_an_impossible_end_time_is_refused():
    assert utils.validate_case_entry(
        CASEDATETIMEBEGIN="09-15-2026 08:00",
        CASEDATETIMEEND="09-15-2026 24:00",
        **CASE,
    ) is True


@pytest.mark.parametrize("end", ["", "09-15-2026 08:00", "09-16-2026 01:15"])
def test_a_real_start_with_a_blank_or_later_end_is_accepted(end):
    assert utils.validate_case_entry(
        CASEDATETIMEBEGIN="09-15-2026 08:00",
        CASEDATETIMEEND=end,
        **CASE,
    ) is False


def test_the_message_says_how_to_enter_the_time(monkeypatch):
    notices = []
    monkeypatch.setattr(
        utils.ui,
        "notify",
        lambda message,
        **_kw: notices.append(str(message))
    )
    utils.validate_case_entry(
        CASEDATETIMEBEGIN="19-45-2026 25:99",
        **CASE
    )
    assert any("MM-DD-YYYY HH:MM" in notice for notice in notices), notices


@pytest.mark.parametrize(
    "dob",
    ["02-30-1984", "13-01-1984", "03-02", "01-01-2999"]
)
def test_a_date_of_birth_that_is_not_real_or_not_yet_passed_is_refused(dob):
    assert utils.validate_person_data(
        stage="initial",
        PERSONNAME="Doe, John",
        PERSONNOTE="Present at entry",
        PERSONDOB=dob,
    ) is True


@pytest.mark.parametrize("dob", ["", "03-02-1984"])
def test_a_blank_or_real_date_of_birth_is_accepted(dob):
    assert utils.validate_person_data(
        stage="initial",
        PERSONNAME="Doe, John",
        PERSONNOTE="Present at entry",
        PERSONDOB=dob,
    ) is False


# ----- Attachments stay in the database until needed -----
PAYLOAD = b"%PDF-1.7 " + b"x" * 4096


def _add_attachment(name="scene photo.pdf"):
    with get_session() as session:
        session.add(
            UploadedFiles(
                FILENAME=name,
                FILESIZE=len(PAYLOAD),
                FILEMIMETYPE="application/pdf",
                FILEUPLOADEDBY="Roe, Jane",
                FILEDATA=PAYLOAD,
            )
        )


def test_listing_attachments_does_not_read_their_contents():
    _add_attachment()
    with get_session() as session:
        record = session.query(UploadedFiles).one()
        assert record.FILENAME == "scene photo.pdf"
        assert "FILEDATA" in sa_inspect(record).unloaded


def test_the_contents_still_load_when_they_are_read():
    _add_attachment()
    with get_session() as session:
        assert session.query(UploadedFiles).one().FILEDATA == PAYLOAD


def test_a_download_keeps_the_file_name_accents_and_all():
    header = files_page.content_disposition("façade photo.jpg")
    assert header.startswith("attachment;")
    assert "filename*=UTF-8''fa%C3%A7ade%20photo.jpg" in header
    assert 'filename="fa_ade photo.jpg"' in header


def test_downloads_no_longer_write_a_temporary_copy():
    source = Path(files_page.__file__).read_text(encoding="utf-8")
    assert "tempfile" not in source
    assert "vector_dl_" not in source
