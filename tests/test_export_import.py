"""Export and import.

The export is the only way a case leaves the machine, so a round trip
has to preserve every row and every attachment byte-for-byte.

These run the real functions, which call ui.notify. Outside a browser
session that is a no-op, so nothing needs stubbing.
"""

import hashlib
import json
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
def desktop(tmp_path, monkeypatch):
    """Redirects the export away from the real Desktop."""
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


def test_export_produces_an_archive(with_attachment, desktop):
    import_export.export_database()
    archives = list(desktop.glob("*.zip"))
    assert len(archives) == 1
    assert with_attachment.replace("-", "-") in archives[0].name


def test_export_cleans_up_its_staging_directory(with_attachment, desktop):
    """The unzipped case must not be left sitting on the Desktop."""
    import_export.export_database()
    assert [p.name for p in desktop.iterdir()
            if p.is_dir()] == []


def test_manifest_records_the_ingest_hash(with_attachment, desktop):
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))

    with zipfile.ZipFile(archive) as zf:
        manifest = json.loads(zf.read("export_manifest.json"))

    entry = manifest["files"][0]
    assert entry["file_name"] == "scene_photo.jpg"
    assert entry["hash_at_ingest"] == hashlib.sha256(PAYLOAD).hexdigest()
    assert entry["matches_ingest_hash"] is True
    assert manifest["integrity_failures"] == []


def test_audit_trail_travels_with_the_export(with_attachment, desktop):
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))
    with zipfile.ZipFile(archive) as zf:
        assert "audit.csv" in zf.namelist()


def test_round_trip_preserves_every_row(with_attachment, desktop):
    before = _counts()
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))

    from utils import delete_all_data
    delete_all_data()
    assert _counts()["Evidence"] == 0

    import_export.import_database(str(archive))
    assert _counts() == before


def test_round_trip_preserves_attachment_bytes(with_attachment, desktop):
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))

    from utils import delete_all_data
    delete_all_data()
    import_export.import_database(str(archive))

    with get_session() as session:
        restored = session.query(UploadedFiles).one()
        assert restored.file_data == PAYLOAD
        assert hashlib.sha256(restored.file_data).hexdigest() == \
            hashlib.sha256(PAYLOAD).hexdigest()


def test_import_restores_provenance(with_attachment, desktop):
    """Files used to come back as octet-stream, uploaded by "import"."""
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))

    from utils import delete_all_data
    delete_all_data()
    import_export.import_database(str(archive))

    with get_session() as session:
        restored = session.query(UploadedFiles).one()
        assert restored.file_mime_type == "image/jpeg"
        assert restored.uploaded_by == "Roe, Jane"
        assert restored.sha256 == hashlib.sha256(PAYLOAD).hexdigest()


def test_encrypted_round_trip(with_attachment, desktop):
    before = _counts()
    import_export.export_database(password="correct horse battery")
    archive = next(desktop.glob("*.zip"))

    # The archive must genuinely be encrypted.
    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(RuntimeError):
            zf.read("export_manifest.json")

    from utils import delete_all_data
    delete_all_data()
    import_export.import_database(
        str(archive), password="correct horse battery")
    assert _counts() == before


def test_import_detects_a_tampered_attachment(with_attachment, desktop,
                                              tmp_path):
    """A file whose bytes no longer match the manifest must be flagged."""
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))

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
        import_export.import_database(str(tampered))
    finally:
        import_export.ui.notify = original_notify

    assert any("integrity checks" in text for text in notices)
    assert any("scene_photo.jpg" in text for text in notices)


def test_import_is_recorded_in_the_audit_trail(with_attachment, desktop):
    import_export.export_database()
    archive = next(desktop.glob("*.zip"))

    from utils import delete_all_data
    from models import AuditLog
    delete_all_data()
    import_export.import_database(str(archive))

    with get_session() as session:
        assert session.query(AuditLog).filter_by(action="IMPORT").count() == 1
