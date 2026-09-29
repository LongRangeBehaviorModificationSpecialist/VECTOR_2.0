"""
test_failures_and_live.py

Failures that explain themselves, imports that cannot half-happen, and
the change signal that keeps other devices' pages current.

A failed save used to show the SQL statement with the reason buried in
it. A failed import left a case that was half the old one and half the
new, and an export whose attachments could not be read still said it was
complete. And a page on a second tablet never showed a new entry until
someone reloaded it.
"""

import hashlib
import json
import sqlite3
import tempfile
import zipfile

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

import import_export
import models
from failures import explain
from models import (
    Agents,
    AuditLog,
    Evidence,
    UploadedFiles,
    get_session,
    record_audit,
)
from utils import delete_all_data


PAYLOAD = b"\x89PNG\r\n\x1a\n" + b"attachment" * 64


@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    """Where exports are written; staging goes in a private temp folder."""
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
    destination = tmp_path / "exports"
    destination.mkdir()
    return destination


@pytest.fixture
def notices(monkeypatch):
    """What export and import put on screen."""
    shown = []
    monkeypatch.setattr(
        import_export.ui, "notify",
        lambda message, **_kwargs: shown.append(str(message)),
    )
    return shown


def _agent(name):
    return Agents(
        AGENTNAME=name,
        AGENTPARENTAGENCY="Virginia State Police",
        AGENTPRIMARYROLE="Searcher",
        AGENTPHONE="",
        AGENTEMAIL="",
    )


def _add_attachment(name="scene_photo.jpg"):
    with get_session() as session:
        session.add(
            UploadedFiles(
                FILENAME=name,
                FILESIZE=len(PAYLOAD),
                FILEMIMETYPE="image/png",
                FILEUPLOADEDBY="Roe, Jane",
                FILEDATA=PAYLOAD,
                FILESHA256=hashlib.sha256(PAYLOAD).hexdigest(),
            )
        )


def _duplicate_evidence():
    """Adds an evidence item whose number is already taken."""
    with get_session() as session:
        session.add(
            Evidence(
                EVIDNUM="1",
                EVIDQTY="1",
                EVIDDESC="duplicate",
                EVIDLOCROOM="Room A (Bedroom)",
                EVIDLOCROOMDETAIL="floor",
                EVIDFOUNDBY="Doe, John",
                EVIDFOUNDBYWITNESS="Roe, Jane",
            )
        )


def _snapshot():
    with get_session() as session:
        return {
            "agents": sorted(a.AGENTNAME for a in session.query(Agents)),
            "evidence": session.query(Evidence).count(),
            "files": session.query(UploadedFiles).count(),
        }


def _rewrite_zip(archive, name, transform):
    """Rewrites one member of a ZIP archive in place."""
    with zipfile.ZipFile(archive) as source:
        members = {item: source.read(item) for item in source.namelist()}
    members[name] = transform(members[name])
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as target:
        for item, data in members.items():
            target.writestr(item, data)


# ----- Explaining a failure -----
def test_a_clash_on_a_unique_column_names_the_field(populated):
    with pytest.raises(IntegrityError) as caught:
        _duplicate_evidence()

    message = explain(caught.value, {"EVIDNUM": "Evidence Number"})

    assert "Evidence Number" in message
    assert "INSERT" not in message and "[SQL" not in message


def test_a_missing_required_value_names_the_field():
    with pytest.raises(IntegrityError) as caught:
        with get_session() as session:
            session.add(Agents(AGENTNAME="No, Agency"))
    message = explain(caught.value, {"AGENTPARENTAGENCY": "Parent Agency"})
    assert message == "Parent Agency cannot be left empty."


def test_a_locked_database_is_explained_as_busy():
    err = OperationalError(
        "INSERT ...",
        {},
        sqlite3.OperationalError("database is locked")
    )
    assert "busy" in explain(err)


def test_a_file_that_is_not_a_zip_is_explained(tmp_path):
    import pyzipper

    bogus = tmp_path / "case.zip"
    bogus.write_text("not a zip")
    with pytest.raises(Exception) as caught:
        with pyzipper.AESZipFile(bogus, "r"):
            pass
    assert "not a ZIP archive" in explain(caught.value)


def test_an_unexpected_failure_still_says_what_it_was():
    assert explain(ValueError("odd value")) == "ValueError: odd value"


# ----- Edit dialogs open for values no longer on the list -----
# Opening the edit dialog for an agent missing from this machine's roster
# raised inside NiceGUI and showed nothing, so the edit button appeared to
# do nothing at all.
def test_a_stored_value_missing_from_the_options_is_offered():
    from parts.crud import options_including

    assert options_including(
        ["Doe, John"],
        "Demo, Alex",
    ) == ["Doe, John", "Demo, Alex"]


def test_options_are_left_alone_when_the_value_is_listed_or_blank():
    from parts.crud import options_including

    assert options_including(["A", "B"], "A") == ["A", "B"]
    assert options_including(["A"], "") == ["A"]
    assert options_including(["A"], None) == ["A"]


def test_labelled_options_gain_the_value_too():
    from parts.crud import options_including

    assert options_including({"y": "Yes"}, "maybe") == {
        "y": "Yes", "maybe": "maybe"
    }


# ----- Imports are all or nothing -----
def test_a_failed_csv_import_leaves_the_case_unchanged(
        populated,
        out_dir,
        notices
):
    archive = import_export.export_vector_to_csv(destination=out_dir)

    # EVIDENCE.csv gains a second item 1. The tables before it in the
    # archive -- AGENTS and CASES -- used to be replaced before this failed.
    def duplicate_first_row(data):
        lines = data.decode("utf-8").splitlines(keepends=True)
        return "".join(lines + [lines[1]]).encode("utf-8")

    _rewrite_zip(archive, "EVIDENCE.csv", duplicate_first_row)

    with get_session() as session:
        session.add(_agent("Local, Only"))
    _add_attachment()
    before = _snapshot()

    import_export.import_vector_from_csv(str(archive))

    assert _snapshot() == before
    assert any(
        "Nothing was imported"
        in n and "EVIDENCE" in n
        for n in notices
    ), notices
    assert not any("[SQL" in n for n in notices)


def test_a_failed_json_import_leaves_the_case_unchanged(
        populated,
        out_dir,
        notices
):
    exported = import_export.export_vector_to_json(destination=out_dir)
    payload = json.loads(exported.read_text(encoding="utf-8"))
    records = payload["tables"]["EVIDENCE"]["records"]
    records.append(dict(records[0]))
    exported.write_text(json.dumps(payload), encoding="utf-8")

    with get_session() as session:
        session.add(_agent("Local, Only"))
    before = _snapshot()

    import_export.import_vector_from_json(str(exported))

    assert _snapshot() == before
    assert any(
        "Nothing was imported"
        in n and "EVIDENCE" in n
        for n in notices
    ), notices


def test_importing_a_case_without_attachments_removes_the_old_ones(
        populated,
        out_dir,
        notices
):
    """An archive with no files folder used to leave the previous case's
    attachments in place, and wrote no import record.
    """
    archive = import_export.export_vector_to_csv(destination=out_dir)
    _add_attachment("previous_case.jpg")
    with get_session() as session:
        imports_before = session.query(AuditLog).filter_by(
            action="IMPORT").count()

    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        assert session.query(UploadedFiles).count() == 0
        assert session.query(AuditLog).filter_by(
            action="IMPORT").count() == imports_before + 1


# ----- Exports stop rather than leave things out -----
def test_a_csv_export_that_cannot_copy_attachments_stops(
        populated,
        out_dir,
        notices,
        monkeypatch
):
    _add_attachment()

    def unreadable(*_args, **_kwargs):
        raise PermissionError(13, "Permission denied", "scene_photo.jpg")

    monkeypatch.setattr(import_export, "_unique_archive_name", unreadable)

    assert import_export.export_vector_to_csv(destination=out_dir) is None
    assert list(out_dir.iterdir()) == []
    assert any("Nothing was downloaded" in n for n in notices), notices


def test_a_json_export_that_cannot_embed_attachments_stops(
        populated,
        out_dir,
        notices,
        monkeypatch
):
    _add_attachment()

    def broken(*_args, **_kwargs):
        raise MemoryError("out of memory")

    monkeypatch.setattr(import_export.hashlib, "sha256", broken)

    assert import_export.export_vector_to_json(destination=out_dir) is None
    assert list(out_dir.iterdir()) == []
    assert any("Nothing was downloaded" in n for n in notices), notices


# ----- The change signal -----
def test_saving_a_record_moves_the_version():
    before = models.data_version()
    with get_session() as session:
        session.add(_agent("New, Agent"))
    assert models.data_version() > before


def test_editing_and_deleting_move_the_version(populated):
    before = models.data_version()
    with get_session() as session:
        session.query(Agents).first().AGENTNOTE = "edited"
    after_edit = models.data_version()
    with get_session() as session:
        session.delete(session.query(Agents).first())

    assert after_edit > before
    assert models.data_version() > after_edit


def test_reading_does_not_move_the_version(populated):
    before = models.data_version()
    trail_before = models.audit_version()
    with get_session() as session:
        session.query(Agents).all()
        session.query(Evidence).count()
    assert models.data_version() == before
    assert models.audit_version() == trail_before


def test_a_failed_save_does_not_move_the_version(populated):
    before = models.data_version()
    with pytest.raises(IntegrityError):
        _duplicate_evidence()
    assert models.data_version() == before


def test_a_sign_in_record_does_not_move_the_case_version():
    """No table of case data changes, so those pages must not reload."""
    before = models.data_version()
    with get_session() as session:
        record_audit(
            session,
            action="LOGIN",
            table_name="users",
            summary="agent",
            actor="agent",
        )
    assert models.data_version() == before


def test_a_sign_in_record_moves_the_trail_version():
    """The Audit Trail page exists to show exactly that entry, so it
    watches this signal instead."""
    before = models.audit_version()
    with get_session() as session:
        record_audit(session, action="LOGIN", table_name="users",
                     summary="agent", actor="agent")
    assert models.audit_version() > before


def test_saving_a_record_moves_both_signals():
    """A save writes the record and its audit entry in one commit."""
    case_before = models.data_version()
    trail_before = models.audit_version()
    with get_session() as session:
        session.add(_agent("Both, Signals"))
    assert models.data_version() > case_before
    assert models.audit_version() > trail_before


def test_a_bulk_wipe_moves_the_version(populated):
    before = models.data_version()
    delete_all_data()
    assert models.data_version() > before


def test_an_import_moves_the_version(populated, out_dir, notices):
    archive = import_export.export_vector_to_csv(destination=out_dir)
    before = models.data_version()
    import_export.import_vector_from_csv(str(archive))
    assert models.data_version() > before
