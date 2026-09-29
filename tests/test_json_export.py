"""
test_json_export.py

JSON export and import.

A second format alongside the CSV archive: one self-contained file with
attachments embedded, for handing a case to another tool.

Held to the same bar as the CSV path -- a round trip must preserve every
row and every attachment byte for byte, tampering must be detected, and
the import must reach the audit trail.
"""

import base64
import hashlib
import json
import tempfile
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
def out_dir(tmp_path, monkeypatch):
    """Where the finished export is written. Staging goes in a private
    temp folder, so a test never touches the real one.
    """
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
    destination = tmp_path / "exports"
    destination.mkdir()
    return destination


@pytest.fixture
def with_attachment(populated):
    with get_session() as session:
        session.add(
            UploadedFiles(
                FILENAME="scene_photo.jpg",
                FILESIZE=len(PAYLOAD),
                FILEMIMETYPE="image/jpeg",
                FILEUPLOADEDBY="Roe, Jane",
                FILEDATA=PAYLOAD,
                FILESHA256=hashlib.sha256(PAYLOAD).hexdigest(),
                FILEHASHEDDATETIME="2026-09-10T08:10:00Z",
            )
        )
    return populated


def _counts():
    with get_session() as session:
        return {
            model.__name__: session.query(model).count()
            for model in (
                Cases,
                Agents,
                Rooms,
                Evidence,
                Persons,
                Notes,
                UploadedFiles,
            )
        }


# ----- Export -----

def test_export_writes_one_json_file(with_attachment, out_dir):
    import_export.export_vector_to_json(destination=out_dir)
    files = list(out_dir.glob("*.json"))
    assert len(files) == 1
    assert with_attachment in files[0].name


def test_export_leaves_nothing_staged(with_attachment, out_dir):
    exported = import_export.export_vector_to_json(destination=out_dir)
    assert [p.name for p in out_dir.iterdir()] == [exported.name]
    assert list(Path(tempfile.gettempdir()).iterdir()) == []


def test_the_file_is_valid_json_with_the_expected_shape(
        with_attachment,
        out_dir
):
    import_export.export_vector_to_json(destination=out_dir)
    payload = json.loads(
        next(out_dir.glob("*.json")).read_text(encoding="utf-8")
    )
    assert payload["export_metadata"]["application"] == "VECTOR"
    assert payload["export_metadata"]["format_version"] == "1.1"
    assert "tables" in payload
    assert payload["tables"]["EVIDENCE"]["record_count"] == 12
    assert payload["files"]["record_count"] == 1


def test_the_audit_trail_is_included(with_attachment, out_dir):
    """A case handed on without its history cannot answer what changed."""
    import_export.export_vector_to_json(destination=out_dir)
    payload = json.loads(
        next(out_dir.glob("*.json")).read_text(encoding="utf-8")
    )
    assert "AUDIT" in payload["tables"]


def test_attachments_carry_their_collection_hash(with_attachment, out_dir):
    import_export.export_vector_to_json(destination=out_dir)
    payload = json.loads(
        next(out_dir.glob("*.json")).read_text(encoding="utf-8")
    )
    entry = payload["files"]["records"][0]
    assert entry["FILENAME"] == "scene_photo.jpg"
    assert entry["FILESHA256"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert entry["FILEHASHMATCHES"] is True
    assert base64.b64decode(entry["FILEDATA_b64"]) == PAYLOAD


def test_an_encrypted_export_is_really_encrypted(with_attachment, out_dir):
    import_export.export_vector_to_json(
        destination=out_dir,
        password="correct horse battery"
    )
    archive = next(out_dir.glob("*.json.zip"))
    assert not list(out_dir.glob("*.json"))  # no plaintext left beside it

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(RuntimeError):
            zf.read(zf.namelist()[0])


# ----- Round trip -----

def test_round_trip_preserves_every_row(with_attachment, out_dir):
    before = _counts()
    import_export.export_vector_to_json(destination=out_dir)
    exported = next(out_dir.glob("*.json"))

    delete_all_data()
    assert _counts()["Evidence"] == 0

    import_export.import_vector_from_json(str(exported))
    assert _counts() == before


def test_round_trip_preserves_attachment_bytes(with_attachment, out_dir):
    import_export.export_vector_to_json(destination=out_dir)
    exported = next(out_dir.glob("*.json"))

    delete_all_data()
    import_export.import_vector_from_json(str(exported))

    with get_session() as session:
        restored = session.query(UploadedFiles).one()
        assert restored.FILEDATA == PAYLOAD
        assert restored.FILEMIMETYPE == "image/jpeg"
        assert restored.FILEUPLOADEDBY == "Roe, Jane"
        assert restored.FILESHA256 == hashlib.sha256(PAYLOAD).hexdigest()


def test_round_trip_preserves_field_values(with_attachment, out_dir):
    """Values that break naive serialisation must survive."""
    import_export.export_vector_to_json(destination=out_dir)
    exported = next(out_dir.glob("*.json"))

    delete_all_data()
    import_export.import_vector_from_json(str(exported))

    with get_session() as session:
        person = session.query(Persons).one()
        assert person.PERSONNAME == "O'Brien, Sean"
        note = session.query(Notes).one()
        assert "&" in note.NOTETEXT and "<" in note.NOTETEXT


def test_encrypted_round_trip(with_attachment, out_dir):
    before = _counts()
    import_export.export_vector_to_json(
        destination=out_dir,
        password="correct horse battery"
    )
    archive = next(out_dir.glob("*.json.zip"))

    delete_all_data()
    import_export.import_vector_from_json(
        str(archive), password="correct horse battery"
    )
    assert _counts() == before


# ----- Integrity and safety -----

def test_a_tampered_attachment_is_detected(with_attachment, out_dir):
    import_export.export_vector_to_json(destination=out_dir)
    exported = next(out_dir.glob("*.json"))

    payload = json.loads(exported.read_text(encoding="utf-8"))
    payload["files"]["records"][0]["FILEDATA_b64"] = base64.b64encode(
        b"swapped content"
    ).decode("ascii")
    exported.write_text(json.dumps(payload), encoding="utf-8")

    notices = []
    original = import_export.ui.notify
    import_export.ui.notify = lambda message, **kw: notices.append(str(message))
    try:
        delete_all_data()
        import_export.import_vector_from_json(str(exported))
    finally:
        import_export.ui.notify = original

    assert any("scene_photo.jpg" in text for text in notices)
    assert any("do not match" in text for text in notices)


def test_the_local_audit_trail_is_not_overwritten(with_attachment, out_dir):
    """An import appends a record; it does not import someone else's
    history over the receiving machine's own.
    """
    import_export.export_vector_to_json(destination=out_dir)
    exported = next(out_dir.glob("*.json"))

    delete_all_data()
    import_export.import_vector_from_json(str(exported))

    with get_session() as session:
        assert session.query(AuditLog).filter_by(action="IMPORT").count() == 1


def test_a_file_that_is_not_an_export_is_refused(tmp_path):
    stray = tmp_path / "notes.json"
    stray.write_text('{"hello": "world"}', encoding="utf-8")

    notices = []
    original = import_export.ui.notify
    import_export.ui.notify = lambda message, **kw: notices.append(str(message))
    try:
        import_export.import_vector_from_json(str(stray))
    finally:
        import_export.ui.notify = original

    assert any("not a VECTOR JSON export" in text for text in notices)
    assert _counts()["Cases"] == 0


def test_a_missing_file_is_refused(tmp_path):
    notices = []
    original = import_export.ui.notify
    import_export.ui.notify = lambda message, **kw: notices.append(str(message))
    try:
        import_export.import_vector_from_json(str(tmp_path / "absent.json"))
    finally:
        import_export.ui.notify = original
    assert any("not found" in text for text in notices)


# ----- Files written by other versions -----

def test_a_1_0_export_still_imports(tmp_path):
    """This branch's first layout: lowercase tables, SUSPECT* columns and
    a bare list of attachments with lowercase keys.
    """
    photo = b"version-one-photo"
    digest = hashlib.sha256(photo).hexdigest()
    payload = {
        "export_metadata": {
            "format_version": "1.0",
            "application": "VECTOR"
        },
        "tables": {
            "cases": {
                "records": [{
                    "Z_PK": 1,
                    "CASENUMBER": "26-V1",
                    "LOCATION": "1 Old Road",
                    "JURISDICTION": "Fairfax County",
                    "CASEDATETIMEBEGIN": "2026-09-01 08:00",
                }]
            },
            "persons": {
                "records": [{
                    "Z_PK": 1,
                    "SUSPECTNAME": "O'Brien, Sean",
                    "SUSPECTDOB": "03-02-1984",
                    "SUSPECTNOTE": "Present at entry",
                }]
            },
        },
        "files": [{
            "file_name": "old.jpg",
            "file_mime_type": "image/jpeg",
            "uploaded_by": "Doe, John",
            "hash_at_ingest": digest,
            "file_hash": digest,
            "data_base64": base64.b64encode(photo).decode("ascii"),
        }],
    }
    path = tmp_path / "v1.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    import_export.import_vector_from_json(str(path))

    with get_session() as session:
        case = session.query(Cases).one()
        assert case.CASENUMBER == "26-V1"
        # Stored before the date format changed; rewritten on the way in.
        assert case.CASEDATETIMEBEGIN == "09-01-2026 08:00"
        person = session.query(Persons).one()
        assert person.PERSONNAME == "O'Brien, Sean"
        assert person.PERSONNOTE == "Present at entry"
        restored = session.query(UploadedFiles).one()
        assert restored.FILEDATA == photo
        assert restored.FILEUPLOADEDBY == "Doe, John"
        assert restored.FILESHA256 == digest


def test_an_upstream_export_imports(tmp_path):
    """Upstream's layout: EVIDENDCE for the evidence table, attachments
    under files.records with the bytes in FILEDATA_b64."""
    photo = b"upstream-photo"
    payload = {
        "export_metadata": {
            "format_version": "1.0"
        },
        "tables": {
            "CASES": {
                "record_count": 1,
                "records": [{
                    "Z_PK": 1,
                    "CASENUMBER": "26-UPSTREAM",
                    "LOCATION": "2 New Road",
                    "JURISDICTION": "Fairfax County",
                    "CASEDATETIMEBEGIN": "09-01-2026 08:00",
                }]
            },
            "EVIDENDCE": {
                "record_count": 1,
                "records": [{
                    "Z_PK": 1,
                    "EVIDNUM": "1",
                    "EVIDQTY": "1",
                    "EVIDDESC": "Laptop",
                    "EVIDLOCROOM": "Room A (Bedroom)",
                    "EVIDLOCROOMDETAIL": "shelf",
                    "EVIDFOUNDBY": "Doe, John",
                    "EVIDFOUNDBYWITNESS": "Roe, Jane",
                }]
            },
        },
        "files": {
            "record_count": 1,
            "records": [{
                "FILENAME": "a.jpg",
                "FILESIZE": len(photo),
                "FILEMIMETYPE": "image/jpeg",
                "FILEDATA_b64": base64.b64encode(photo).decode("ascii"),
            }]
        },
    }
    path = tmp_path / "upstream.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    import_export.import_vector_from_json(str(path))

    with get_session() as session:
        assert session.query(Evidence).one().EVIDDESC == "Laptop"
        restored = session.query(UploadedFiles).one()
        assert restored.FILEDATA == photo
        assert restored.FILEMIMETYPE == "image/jpeg"


def test_attachments_sharing_a_name_all_survive_json(case, out_dir):
    attachments = [
        ("photo.jpg", b"FRONT"),
        ("photo.jpg", b"BACK")
    ]
    with get_session() as session:
        for name, payload in attachments:
            session.add(
                UploadedFiles(
                    FILENAME=name,
                    FILESIZE=len(payload),
                    FILEDATA=payload,
                    FILEUPLOADEDBY="Doe, John",
                )
            )

    exported = import_export.export_vector_to_json(destination=out_dir)
    delete_all_data()
    import_export.import_vector_from_json(str(exported))

    with get_session() as session:
        restored = sorted(
            (f.FILENAME, bytes(f.FILEDATA))
            for f in session.query(UploadedFiles).all()
        )
    assert restored == sorted(attachments)


# ----- Format detection -----

def test_a_json_file_is_recognised(tmp_path):
    path = tmp_path / "case.json"
    path.write_text("{}", encoding="utf-8")
    assert import_export.looks_like_json_export(str(path)) is True


def test_the_csv_archive_is_not_mistaken_for_json(with_attachment, out_dir):
    """The CSV archive also contains export_manifest.json, so the
    detection has to look at more than 'is there a .json in here'.
    """
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))
    assert import_export.looks_like_json_export(str(archive)) is False


def test_a_json_zip_is_recognised(with_attachment, out_dir):
    import_export.export_vector_to_json(
        destination=out_dir, password="correct horse battery")
    archive = next(out_dir.glob("*.json.zip"))
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
