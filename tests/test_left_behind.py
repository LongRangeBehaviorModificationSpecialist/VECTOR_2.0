"""
test_left_behind.py

What VECTOR, and its own tests, leave in the temp folder.

An import unpacks the whole case -- notes, photographs -- into the temp
folder, unencrypted even when the export was not. It used to remove that
copy only on the paths it expected: a damaged manifest, a damaged JSON
archive, or anything else unforeseen stopped the import with nothing on
screen and the copy left behind for good, under a name the start-up
clean-up did not recognise. And every run of this suite left its own
database folder there: about three hundred of them by October.
"""

import os
import subprocess
import sys
import tempfile
import time
import zipfile

import pytest

import import_export
from models import Notes, get_session


@pytest.fixture
def temp_root(tmp_path, monkeypatch):
    """A private temp folder, so what is left in it can be seen."""
    root = tmp_path / "temp"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    return root


@pytest.fixture
def notices(monkeypatch):
    shown = []
    monkeypatch.setattr(
        import_export.ui, "notify",
        lambda message, **_kwargs: shown.append(str(message)),
    )
    return shown


def _left_behind(root):
    return sorted(
        entry.name for entry in root.iterdir()
        if entry.name.startswith(("vector_import_", "vector_json_import_"))
    )


def _archive(tmp_path, manifest="{}"):
    path = tmp_path / "case.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("case/export_manifest.json", manifest)
        archive.writestr(
            "case/CASES.csv",
            "Z_PK,CASENUMBER,LOCATION,JURISDICTION,CASEDATETIMEBEGIN\n"
            '1,26-004711,"1 Elm Street",Fairfax County,09-10-2026 08:00\n',
        )
        archive.writestr(
            "case/NOTES.csv",
            "Z_PK,NOTEDATETIME,NOTEAUTHOR,NOTETEXT\n"
            '1,09-10-2026 08:05,"Doe, John",from the archive\n',
        )
        archive.writestr("case/files/photo.jpg", b"\xff\xd8\xff a photograph")
    return path


def test_a_damaged_manifest_is_explained_and_cleaned_up(
        tmp_path, temp_root, notices, populated):
    archive = _archive(tmp_path, manifest="{ not json")

    import_export.import_vector_from_csv(str(archive))

    assert _left_behind(temp_root) == []
    assert any("could not be read" in message for message in notices)
    with get_session() as session:
        assert session.query(Notes).count() == 1   # the case is unchanged


def test_a_manifest_that_is_not_vectors_is_refused(
        tmp_path, temp_root, notices):
    archive = _archive(tmp_path, manifest="[1, 2, 3]")
    import_export.import_vector_from_csv(str(archive))
    assert _left_behind(temp_root) == []
    assert any("could not be read" in message for message in notices)


def test_the_unpacked_case_goes_even_when_something_unforeseen_stops_it(
        tmp_path, temp_root, notices, monkeypatch):
    def unforeseen():
        raise MemoryError("something nobody planned for")

    monkeypatch.setattr(import_export, "get_all_models", unforeseen)

    with pytest.raises(MemoryError):
        import_export.import_vector_from_csv(str(_archive(tmp_path)))

    assert _left_behind(temp_root) == []


def test_a_successful_import_leaves_nothing_either(
        tmp_path, temp_root, notices):
    import_export.import_vector_from_csv(str(_archive(tmp_path)))
    assert _left_behind(temp_root) == []
    with get_session() as session:
        assert session.query(Notes).one().NOTETEXT == "from the archive"


def test_a_damaged_json_archive_is_explained_and_cleaned_up(
        tmp_path, temp_root, notices):
    """A bad checksum inside the archive is not a wrong password."""
    path = tmp_path / "case.json.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("case.json", '{"tables": {}}' + " " * 64)
    data = bytearray(path.read_bytes())
    data[data.index(b'{"tables"') + 2] ^= 0xFF   # damage one byte
    path.write_bytes(bytes(data))

    import_export.import_vector_from_json(str(path))

    assert _left_behind(temp_root) == []
    assert any("may be damaged" in message for message in notices)


def test_the_json_staging_goes_when_something_unforeseen_stops_it(
        tmp_path, temp_root, notices, monkeypatch):
    path = tmp_path / "case.json.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("case.json", '{"tables": {"CASES": {"records": []}}}')

    def unforeseen():
        raise MemoryError("something nobody planned for")

    monkeypatch.setattr(import_export, "get_all_models", unforeseen)

    with pytest.raises(MemoryError):
        import_export.import_vector_from_json(str(path))

    assert _left_behind(temp_root) == []


@pytest.mark.parametrize(
    "name",
    ["vector_import_ab12cd", "vector_json_import_ab12cd", "vector_import_upload_ab12cd"],
)
def test_the_start_up_clean_up_recognises_an_import_left_behind(
        temp_root, name):
    """For one left by a VECTOR older than this fix, or by a power cut."""
    folder = temp_root / name
    folder.mkdir()
    (folder / "NOTES.csv").write_text("a case", encoding="utf-8")
    an_hour_and_more = time.time() - 2 * 60 * 60
    os.utime(folder, (an_hour_and_more, an_hour_and_more))

    assert import_export.remove_stale_staging() == 1
    assert not folder.exists()


def test_the_import_dialog_explains_a_failure_the_importers_did_not_expect():
    """It used to end with nothing on screen at all."""
    from pathlib import Path
    source = (
        Path(import_export.__file__).parent / "parts" / "case_transfer.py"
    ).read_text(encoding="utf-8")
    body = source[source.index("def do_import"):source.index("def cancel_import")]
    assert "except Exception as err:" in body
    assert "did not" in body and "expect" in body


def test_a_run_of_the_tests_removes_its_own_database_folder(tmp_path):
    """Run a few tests in a separate pytest, with a temp folder of its
    own, and look in it afterwards."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    temp = tmp_path / "temp"
    temp.mkdir()
    env = {**os.environ, "TEMP": str(temp), "TMP": str(temp), "TMPDIR": str(temp)}
    env.pop("VECTOR_DB_DIR", None)
    env.pop("PYTEST_CURRENT_TEST", None)
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "tests/test_auth.py", "-k", "generated_passwords"],
        cwd=root, env=env, capture_output=True, text=True, timeout=300,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert [p.name for p in temp.iterdir() if p.name.startswith("vector_tests_")] == []
