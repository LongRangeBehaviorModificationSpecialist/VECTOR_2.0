"""JSON export and import.

A second format alongside the CSV archive: one self-contained file with
attachments embedded, for handing a case to another tool.

Held to the same bar as the CSV path -- a round trip must preserve every
row and every attachment byte for byte, tampering must be detected, and
the import must reach the audit trail.
"""

import base64
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

import import_export
from models import (
    Agents,
    AuditLog,
    Cases,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
    get_session,
)
from utils import delete_all_data


PAYLOAD = b"\xff\xd8\xff\xe0" + b"scene-photo-bytes" * 128


@pytest.fixture
def desktop(tmp_path, monkeypatch):
    """Keeps the export away from the real Desktop."""
    home = tmp_path / "home"
    (home / "Desktop").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home / "Desktop"


@pytest.fixture
def with_attachment(populated):
    with get_session() as session:
        session.add(
            UploadedFiles(
                file_name="scene_photo.jpg",
                file_size=len(PAYLOAD),
                file_mime_type="image/jpeg",
                uploaded_by="Roe, Jane",
                file_data=PAYLOAD,
                sha256=hashlib.sha256(PAYLOAD).hexdigest(),
                hashed_at="2026-09-10T08:10:00Z",
            )
        )
    return populated


def _counts():
    with get_session() as session:
        return {
            model.__name__: session.query(model).count()
            for model in (Cases, Agents, Rooms, Evidence, Persons, Notes,
                          UploadedFiles)
        }


# ----- Export -----

def test_export_writes_one_json_file(with_attachment, desktop):
    import_export.export_database_json()
    files = list(desktop.glob("*.json"))
    assert len(files) == 1
    assert with_attachment in files[0].name


def test_export_leaves_nothing_staged_on_the_desktop(with_attachment,
                                                     desktop):
    import_export.export_database_json()
    assert [p.name for p in desktop.iterdir() if p.is_dir()] == []


def test_the_file_is_valid_json_with_the_expected_shape(with_attachment,
                                                        desktop):
    import_export.export_database_json()
    payload = json.loads(
        next(desktop.glob("*.json")).read_text(encoding="utf-8")
    )
    assert payload["export_metadata"]["application"] == "VECTOR"
    assert payload["export_metadata"]["format_version"] == "1.0"
    assert "tables" in payload
    assert payload["tables"]["evidence"]["record_count"] == 12


def test_the_audit_trail_is_included(with_attachment, desktop):
    """A case handed on without its history cannot answer what changed."""
    import_export.export_database_json()
    payload = json.loads(
        next(desktop.glob("*.json")).read_text(encoding="utf-8")
    )
    assert "audit" in payload["tables"]


def test_attachments_carry_their_collection_hash(with_attachment, desktop):
    import_export.export_database_json()
    payload = json.loads(
        next(desktop.glob("*.json")).read_text(encoding="utf-8")
    )
    entry = payload["files"][0]
    assert entry["file_name"] == "scene_photo.jpg"
    assert entry["hash_at_ingest"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert entry["matches_ingest_hash"] is True
    assert base64.b64decode(entry["data_base64"]) == PAYLOAD


def test_an_encrypted_export_is_really_encrypted(with_attachment, desktop):
    import_export.export_database_json(password="correct horse battery")
    archive = next(desktop.glob("*.json.zip"))
    assert not list(desktop.glob("*.json"))  # no plaintext left beside it

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(RuntimeError):
            zf.read(zf.namelist()[0])


# ----- Round trip -----

def test_round_trip_preserves_every_row(with_attachment, desktop):
    before = _counts()
    import_export.export_database_json()
    exported = next(desktop.glob("*.json"))

    delete_all_data()
    assert _counts()["Evidence"] == 0

    import_export.import_database_json(str(exported))
    assert _counts() == before


def test_round_trip_preserves_attachment_bytes(with_attachment, desktop):
    import_export.export_database_json()
    exported = next(desktop.glob("*.json"))

    delete_all_data()
    import_export.import_database_json(str(exported))

    with get_session() as session:
        restored = session.query(UploadedFiles).one()
        assert restored.file_data == PAYLOAD
        assert restored.file_mime_type == "image/jpeg"
        assert restored.uploaded_by == "Roe, Jane"
        assert restored.sha256 == hashlib.sha256(PAYLOAD).hexdigest()


def test_round_trip_preserves_field_values(with_attachment, desktop):
    """Values that break naive serialisation must survive."""
    import_export.export_database_json()
    exported = next(desktop.glob("*.json"))

    delete_all_data()
    import_export.import_database_json(str(exported))

    with get_session() as session:
        person = session.query(Persons).one()
        assert person.SUSPECTNAME == "O'Brien, Sean"
        note = session.query(Notes).one()
        assert "&" in note.NOTETEXT and "<" in note.NOTETEXT


def test_encrypted_round_trip(with_attachment, desktop):
    before = _counts()
    import_export.export_database_json(password="correct horse battery")
    archive = next(desktop.glob("*.json.zip"))

    delete_all_data()
    import_export.import_database_json(
        str(archive), password="correct horse battery"
    )
    assert _counts() == before


# ----- Integrity and safety -----

def test_a_tampered_attachment_is_detected(with_attachment, desktop):
    import_export.export_database_json()
    exported = next(desktop.glob("*.json"))

    payload = json.loads(exported.read_text(encoding="utf-8"))
    payload["files"][0]["data_base64"] = base64.b64encode(
        b"swapped content"
    ).decode("ascii")
    exported.write_text(json.dumps(payload), encoding="utf-8")

    notices = []
    original = import_export.ui.notify
    import_export.ui.notify = lambda message, **kw: notices.append(str(message))
    try:
        delete_all_data()
        import_export.import_database_json(str(exported))
    finally:
        import_export.ui.notify = original

    assert any("scene_photo.jpg" in text for text in notices)
    assert any("do not match" in text for text in notices)


def test_the_local_audit_trail_is_not_overwritten(with_attachment, desktop):
    """An import appends a record; it does not import someone else's
    history over the receiving machine's own."""
    import_export.export_database_json()
    exported = next(desktop.glob("*.json"))

    delete_all_data()
    import_export.import_database_json(str(exported))

    with get_session() as session:
        assert session.query(AuditLog).filter_by(action="IMPORT").count() == 1


def test_a_file_that_is_not_an_export_is_refused(tmp_path):
    stray = tmp_path / "notes.json"
    stray.write_text('{"hello": "world"}', encoding="utf-8")

    notices = []
    original = import_export.ui.notify
    import_export.ui.notify = lambda message, **kw: notices.append(str(message))
    try:
        import_export.import_database_json(str(stray))
    finally:
        import_export.ui.notify = original

    assert any("not a VECTOR JSON export" in text for text in notices)
    assert _counts()["Cases"] == 0


def test_a_missing_file_is_refused(tmp_path):
    notices = []
    original = import_export.ui.notify
    import_export.ui.notify = lambda message, **kw: notices.append(str(message))
    try:
        import_export.import_database_json(str(tmp_path / "absent.json"))
    finally:
        import_export.ui.notify = original
    assert any("not found" in text for text in notices)


# ----- Format detection -----

def test_a_json_file_is_recognised(tmp_path):
    path = tmp_path / "case.json"
    path.write_text("{}", encoding="utf-8")
    assert import_export.looks_like_json_export(str(path)) is True


def test_the_csv_archive_is_not_mistaken_for_json(with_attachment, desktop):
    """The CSV archive also contains export_manifest.json, so the
    detection has to look at more than 'is there a .json in here'."""
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))
    assert import_export.looks_like_json_export(str(archive)) is False


def test_a_json_zip_is_recognised(with_attachment, desktop):
    import_export.export_database_json(password="correct horse battery")
    archive = next(desktop.glob("*.json.zip"))
    assert import_export.looks_like_json_export(str(archive)) is True


def test_quoted_paths_are_handled(tmp_path):
    """Windows "Copy as path" wraps the path in quotes."""
    path = tmp_path / "case.json"
    path.write_text("{}", encoding="utf-8")
    assert import_export.looks_like_json_export(f'"{path}"') is True


def test_an_unreadable_file_does_not_raise(tmp_path):
    path = tmp_path / "broken.zip"
    path.write_bytes(b"not really a zip")
    assert import_export.looks_like_json_export(str(path)) is False
