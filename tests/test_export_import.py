"""Export and import.

The export is the only way a case leaves the machine, so a round trip
has to preserve every row and every attachment byte-for-byte.

These run the real functions, which call ui.notify. Outside a browser
session that is a no-op, so nothing needs stubbing.
"""

import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

import import_export
from models import (
    Agents,
    Cases,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
    get_session,
)


PAYLOAD = b"\xff\xd8\xff\xe0" + b"photo-bytes" * 64


@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    """Where the finished export is written. Staging goes in a private
    temp folder, so a test never touches the real one."""
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
                FILEHASHEDAT="2026-09-10T08:10:00Z",
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


def test_export_produces_an_archive(with_attachment, out_dir):
    import_export.export_vector_to_csv(destination=out_dir)
    archives = list(out_dir.glob("*.zip"))
    assert len(archives) == 1
    assert with_attachment.replace("-", "-") in archives[0].name


def test_export_cleans_up_its_staging_directory(with_attachment, out_dir):
    """The unzipped case must not be left behind anywhere."""
    archive = import_export.export_vector_to_csv(destination=out_dir)
    assert [p.name for p in out_dir.iterdir()] == [archive.name]
    assert list(Path(tempfile.gettempdir()).iterdir()) == []


def test_export_without_a_destination_stages_for_download(with_attachment,
                                                          out_dir):
    """What the Export button does: build the file in a private staging
    folder for the browser to download, never on the host's Desktop."""
    archive = import_export.export_vector_to_csv()
    assert archive.exists()
    assert archive.parent.parent == Path(tempfile.gettempdir())
    assert archive.parent.name.startswith("vector_export_")


def test_manifest_records_the_ingest_hash(with_attachment, out_dir):
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))

    with zipfile.ZipFile(archive) as zf:
        manifest = json.loads(zf.read("export_manifest.json"))

    entry = manifest["files"][0]
    assert entry["FILENAME"] == "scene_photo.jpg"
    assert entry["FILESHA256"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert entry["FILEHASH"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert entry["FILEHASHMATCHES"] is True
    assert manifest["integrity_failures"] == []


def test_audit_trail_travels_with_the_export(with_attachment, out_dir):
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))
    with zipfile.ZipFile(archive) as zf:
        assert "AUDIT.csv" in zf.namelist()


def test_round_trip_preserves_every_row(with_attachment, out_dir):
    before = _counts()
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))

    from utils import delete_all_data
    delete_all_data()
    assert _counts()["Evidence"] == 0

    import_export.import_vector_from_csv(str(archive))
    assert _counts() == before


def test_round_trip_preserves_attachment_bytes(with_attachment, out_dir):
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))

    from utils import delete_all_data
    delete_all_data()
    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        restored = session.query(UploadedFiles).one()
        assert restored.FILEDATA == PAYLOAD
        assert hashlib.sha256(restored.FILEDATA).hexdigest() == \
            hashlib.sha256(PAYLOAD).hexdigest()


def test_import_restores_provenance(with_attachment, out_dir):
    """Files used to come back as octet-stream, uploaded by "import"."""
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))

    from utils import delete_all_data
    delete_all_data()
    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        restored = session.query(UploadedFiles).one()
        assert restored.FILEMIMETYPE == "image/jpeg"
        assert restored.FILEUPLOADEDBY == "Roe, Jane"
        assert restored.FILESHA256 == hashlib.sha256(PAYLOAD).hexdigest()


def test_encrypted_round_trip(with_attachment, out_dir):
    before = _counts()
    import_export.export_vector_to_csv(
        destination=out_dir, password="correct horse battery")
    archive = next(out_dir.glob("*.zip"))

    # The archive must genuinely be encrypted.
    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(RuntimeError):
            zf.read("export_manifest.json")

    from utils import delete_all_data
    delete_all_data()
    import_export.import_vector_from_csv(
        str(archive), password="correct horse battery")
    assert _counts() == before


def test_import_detects_a_tampered_attachment(with_attachment, out_dir,
                                              tmp_path):
    """A file whose bytes no longer match the manifest must be flagged."""
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))

    # Rebuild the archive with one attachment altered.
    staging = tmp_path / "tampered"
    staging.mkdir()
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(staging)
    (staging / "files" / "scene_photo.jpg").write_bytes(b"swapped content")

    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(tampered, "w") as zf:
        for path in staging.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(staging))

    notices = []
    original_notify = import_export.ui.notify
    import_export.ui.notify = lambda message, **kw: notices.append(str(message))
    try:
        from utils import delete_all_data
        delete_all_data()
        import_export.import_vector_from_csv(str(tampered))
    finally:
        import_export.ui.notify = original_notify

    assert any("integrity checks" in text for text in notices)
    assert any("scene_photo.jpg" in text for text in notices)


def test_import_is_recorded_in_the_audit_trail(with_attachment, out_dir):
    import_export.export_vector_to_csv(destination=out_dir)
    archive = next(out_dir.glob("*.zip"))

    from utils import delete_all_data
    from models import AuditLog
    delete_all_data()
    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        assert session.query(AuditLog).filter_by(action="IMPORT").count() == 1


# ----- Archives written by other versions -----

def _csv(rows: list) -> str:
    import csv
    import io

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def _zip(path, members: dict) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_an_archive_from_before_the_renames_still_imports(tmp_path):
    """Lowercase table names, SUSPECT* columns and the old manifest keys
    must all land in today's columns, provenance included."""
    photo = b"legacy-photo-bytes"
    digest = hashlib.sha256(photo).hexdigest()
    archive = tmp_path / "legacy.zip"
    _zip(archive, {
        "cases.csv": _csv([{
            "Z_PK": "1",
            "CASENUMBER": "26-LEGACY",
            "LOCATION": "1 Old Road",
            "JURISDICTION": "Fairfax County",
            "CASEDATETIMEBEGIN": "09-01-2026 08:00",
            "CASEDATETIMEEND": "",
        }]),
        "persons.csv": _csv([{
            "Z_PK": "1",
            "SUSPECTNAME": "O'Brien, Sean",
            "SUSPECTDOB": "03-02-1984",
            "SUSPECTADDRESS": "14 Elm Street",
            "SUSPECTPHONE": "",
            "SUSPECTNOTE": "Present at entry",
            "ENTEREDDATETIME": "",
        }]),
        "export_manifest.json": json.dumps({"files": [{
            "file_name": "old.jpg",
            "file_hash": digest,
            "hash_at_ingest": digest,
            "hashed_at": "2026-09-01T08:10:00Z",
            "mime_type": "image/jpeg",
            "uploaded_by": "Doe, John",
        }]}),
        "files/old.jpg": photo,
    })

    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        assert session.query(Cases).one().CASENUMBER == "26-LEGACY"
        person = session.query(Persons).one()
        assert person.PERSONNAME == "O'Brien, Sean"
        assert person.PERSONDOB == "03-02-1984"
        restored = session.query(UploadedFiles).one()
        assert restored.FILEDATA == photo
        assert restored.FILEMIMETYPE == "image/jpeg"
        assert restored.FILEUPLOADEDBY == "Doe, John"
        assert restored.FILEHASHEDAT == "2026-09-01T08:10:00Z"


def test_an_archive_from_upstream_keeps_its_evidence(tmp_path):
    """Upstream writes the evidence table as EVIDENDCE.csv, which its own
    importer then skips. Read here as the table it meant."""
    photo = b"upstream-photo"
    digest = hashlib.sha256(photo).hexdigest()
    archive = tmp_path / "upstream.zip"
    _zip(archive, {
        "CASES.csv": _csv([{
            "Z_PK": "1",
            "CASENUMBER": "26-UPSTREAM",
            "LOCATION": "2 New Road",
            "JURISDICTION": "Fairfax County",
            "CASEDATETIMEBEGIN": "09-01-2026 08:00",
            "CASEDATETIMEEND": "",
        }]),
        "EVIDENDCE.csv": _csv([{
            "Z_PK": "1",
            "EVIDNUM": "1",
            "EVIDQTY": "1",
            "EVIDDESC": "Laptop",
            "EVIDLOCROOM": "Room A (Bedroom)",
            "EVIDLOCROOMDETAIL": "shelf",
            "EVIDFOUNDBY": "Doe, John",
            "EVIDFOUNDBYWITNESS": "Roe, Jane",
        }]),
        "export_manifest.json": json.dumps({"files": [{
            "FILENAME": "a.jpg",
            "FILESIZE": len(photo),
            "FILEHASH": digest,
        }]}),
        "files/a.jpg": photo,
    })

    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        assert session.query(Evidence).one().EVIDDESC == "Laptop"
        restored = session.query(UploadedFiles).one()
        assert restored.FILEDATA == photo
        assert restored.FILESHA256 == digest


# ----- Attachments that share a name -----

def test_attachments_sharing_a_name_all_survive_the_round_trip(case, out_dir):
    """Two files called photo.jpg used to overwrite each other in the
    archive, so one was silently lost. Windows also treats PHOTO.JPG as
    the same file."""
    attachments = [
        ("photo.jpg", b"FRONT"),
        ("photo.jpg", b"BACK"),
        ("PHOTO.JPG", b"SIDE"),
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

    archive = import_export.export_vector_to_csv(destination=out_dir)
    with zipfile.ZipFile(archive) as zf:
        stored = [n for n in zf.namelist() if n.startswith("files/")]
    assert len({name.lower() for name in stored}) == 3

    from utils import delete_all_data
    delete_all_data()
    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        restored = sorted(
            (f.FILENAME, bytes(f.FILEDATA))
            for f in session.query(UploadedFiles).all()
        )
    assert restored == sorted(attachments)


# ----- Staging cleanup -----

def test_stale_staging_is_removed_and_recent_staging_kept(out_dir):
    import os
    import time

    root = Path(tempfile.gettempdir())
    stale = root / "vector_export_stale"
    recent = root / "vector_import_upload_recent"
    unrelated = root / "someone_elses_folder"
    for folder in (stale, recent, unrelated):
        folder.mkdir()

    two_hours_ago = time.time() - 2 * 60 * 60
    os.utime(stale, (two_hours_ago, two_hours_ago))
    os.utime(unrelated, (two_hours_ago, two_hours_ago))

    assert import_export.remove_stale_staging() == 1
    assert not stale.exists()
    assert recent.exists()
    assert unrelated.exists()
