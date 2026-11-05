"""
test_case_integrity.py

The November scene review's six release blockers, and its printing note.

Nothing still showing one case writes into another: a page, an edit or
delete dialog, an upload, a download or Print All belongs to the case it
was opened on, and to the record it was opened on. And nothing replaces
the case with less than it had: the demo case is loaded all or nothing,
and an import file is checked before anything is cleared.

Each problem was reproduced on the branch before it was fixed.
"""

import ast
import asyncio
import base64
import hashlib
import inspect
import json
import tempfile
import zipfile
from pathlib import Path

import pytest

import import_export
import settings
from models import (
    Cases,
    Evidence,
    Notes,
    UploadedFiles,
    case_generation,
    get_session,
)
from utils import delete_all_data, require_same_case

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = b"\xff\xd8\xff\xe0" + b"photo-bytes" * 64


@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
    destination = tmp_path / "exports"
    destination.mkdir()
    return destination


@pytest.fixture
def with_attachment(populated):
    with get_session() as session:
        session.add(UploadedFiles(
            FILENAME="scene_photo.jpg", FILESIZE=len(PAYLOAD),
            FILEMIMETYPE="image/jpeg", FILEUPLOADEDBY="Roe, Jane",
            FILEDATA=PAYLOAD, FILESHA256=hashlib.sha256(PAYLOAD).hexdigest(),
            FILEHASHEDDATETIME="2026-09-10T08:10:00Z",
        ))
    return populated


@pytest.fixture
def notices(monkeypatch):
    said = []
    monkeypatch.setattr(import_export.ui, "notify",
                        lambda message, **kw: said.append(str(message)))
    return said


def _counts():
    with get_session() as session:
        return {
            "cases": session.query(Cases).count(),
            "evidence": session.query(Evidence).count(),
            "notes": session.query(Notes).count(),
            "files": session.query(UploadedFiles).count(),
        }


def _next_case(number="26-999999", note=None):
    """What Start New Case does on another tablet, then a first entry."""
    delete_all_data()
    with get_session() as session:
        session.add(Cases(CASENUMBER=number, LOCATION="2 Other Road",
                          JURISDICTION="Arlington County",
                          CASEDATETIMEBEGIN="11-05-2026 09:00"))
        if note:
            session.add(Notes(NOTEDATETIME="11-05-2026 09:05:00 UTC-05:00",
                              NOTEAUTHOR="admin", NOTETEXT=note))


# ----- P1 01: a page belongs to the case it was opened on -----

def test_a_page_opened_on_one_case_cannot_write_into_the_next(case):
    opened_on = case_generation()
    saved = []

    @require_same_case(opened_on)
    def save():
        saved.append("note")

    save()
    _next_case()
    assert save() is None
    assert saved == ["note"]


def test_an_upload_finishing_after_the_case_changed_is_refused(case, monkeypatch):
    import utils
    # Said on the page in the app; there is no page here.
    monkeypatch.setattr(utils.ui, "notify", lambda *args, **kwargs: None)
    opened_on = case_generation()
    stored = []

    @require_same_case(opened_on)
    async def upload():
        stored.append("photo")

    _next_case()
    asyncio.run(upload())
    assert stored == []


def test_only_a_new_case_changes_which_case_this_is(populated):
    """Entries, edits and deletes within the case leave it the same case."""
    opened_on = case_generation()
    with get_session() as session:
        session.add(Notes(NOTEDATETIME="now", NOTEAUTHOR="admin", NOTETEXT="more"))
    with get_session() as session:
        session.delete(session.query(Notes).first())
    assert case_generation() == opened_on


def _decorated_with(path, function):
    """The names of what a function is decorated with, calls included."""
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
            node.name == function
        ):
            for decorator in node.decorator_list:
                target = decorator.func if isinstance(decorator, ast.Call) else decorator
                names.add(getattr(target, "id", getattr(target, "attr", "")))
    return names


@pytest.mark.parametrize("path, handler, check", [
    ("parts/file_upload.py", "handle_upload", "require_same_case"),
    ("parts/file_table.py", "on_download", "same_case"),
    ("parts/file_table.py", "open_delete_dialog", "same_case"),
    ("parts/file_table.py", "on_confirm_delete", "same_case"),
    ("parts/file_table.py", "delete_all_files", "same_case"),
    ("parts/crud_dialogs.py", "on_save_update", "guard"),
    ("parts/crud_dialogs.py", "on_confirm_delete", "guard"),
    ("parts/crud_dialogs.py", "on_confirm_delete_all", "guard"),
])
def test_every_write_on_a_case_page_checks_the_case(path, handler, check):
    assert check in _decorated_with(path, handler), f"{path}: {handler}"


def test_a_page_says_when_its_case_has_been_replaced():
    import parts.crud as crud
    import parts.files_page as files_page
    for source in (inspect.getsource(crud.build_crud_page),
                   inspect.getsource(files_page.build_uploads_page)):
        assert "case_changed_banner(page_case)" in source
        assert "settle_case_banner()" in source


# ----- P1 02: a dialog acts on the record it was opened on -----

def _note_row():
    from parts.crud_widgets import table_row
    from parts.notes_page import SPEC
    with get_session() as session:
        return table_row(SPEC, session.query(Notes).one())


def test_a_dialog_on_an_unchanged_record_goes_ahead(case):
    from parts.crud_dialogs import _changed_since
    from parts.notes_page import SPEC
    with get_session() as session:
        session.add(Notes(NOTEDATETIME="now", NOTEAUTHOR="admin", NOTETEXT="first"))
    row = _note_row()
    # Whatever else the browser sends back with the row.
    assert not _changed_since(SPEC, dict(row, extra="from the table"), lambda: None)


def test_a_dialog_from_the_last_case_does_not_touch_the_next_cases_record(case):
    """Row numbers start again once a table is emptied: the next case's
    first note is note 1 too."""
    from parts.crud_dialogs import _changed_since
    from parts.notes_page import SPEC
    with get_session() as session:
        session.add(Notes(NOTEDATETIME="now", NOTEAUTHOR="admin", NOTETEXT="first"))
    row = _note_row()
    _next_case(note="the next case's own note")
    assert _note_row()["Z_PK"] == row["Z_PK"]
    redrawn = []
    assert _changed_since(SPEC, row, lambda: redrawn.append(True))
    assert redrawn == [True]


def test_a_dialog_on_a_record_edited_elsewhere_does_not_overwrite_it(case):
    from parts.crud_dialogs import _changed_since
    from parts.notes_page import SPEC
    with get_session() as session:
        session.add(Notes(NOTEDATETIME="now", NOTEAUTHOR="admin", NOTETEXT="first"))
    row = _note_row()
    with get_session() as session:
        session.query(Notes).one().NOTETEXT = "changed on another tablet"
    assert _changed_since(SPEC, row, lambda: None)


def test_a_file_replaced_since_the_list_was_drawn_is_not_handed_out(case):
    from parts.file_table import _file_now
    with get_session() as session:
        session.add(UploadedFiles(FILENAME="a.jpg", FILEDATA=PAYLOAD,
                                  FILESIZE=len(PAYLOAD), FILEUPLOADEDBY="admin",
                                  FILESHA256=hashlib.sha256(PAYLOAD).hexdigest()))
    with get_session() as session:
        record = session.query(UploadedFiles).one()
        row = {"Z_PK": record.Z_PK, "FILENAME": "a.jpg",
               "FILESHA256": record.FILESHA256.upper()}
    assert _file_now(row)
    _next_case()
    with get_session() as session:
        session.add(UploadedFiles(FILENAME="b.jpg", FILEDATA=b"other",
                                  FILESIZE=5, FILEUPLOADEDBY="admin",
                                  FILESHA256=hashlib.sha256(b"other").hexdigest()))
    assert not _file_now(row)


# ----- P1 03: the demo case is loaded all or nothing -----

def test_a_failed_demo_load_leaves_the_case_as_it_was(populated, monkeypatch):
    from parts.admin_users import load_demo_case
    from tools import make_demo_case
    before = _counts()
    # A note the database refuses: a note's text may not be empty.
    monkeypatch.setattr(make_demo_case, "DEMO_NOTES",
                        [("09-01-2026 07:32:00", "Demo, Alex", None)])
    with pytest.raises(Exception):
        load_demo_case("admin")
    assert _counts() == before
    with get_session() as session:
        assert session.query(Cases).one().CASENUMBER == populated


# ----- P1 04: a JSON file is checked before anything is cleared -----

def _write_json(tmp_path, payload):
    path = tmp_path / "case.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_an_empty_json_file_leaves_the_case_as_it_was(populated, tmp_path, notices):
    before = _counts()
    import_export.import_vector_from_json(str(_write_json(tmp_path, {"tables": {}})))
    assert _counts() == before
    assert any("Nothing was imported" in n and "holds no case" in n for n in notices)


def test_a_json_file_without_a_case_leaves_the_case_as_it_was(
        populated, tmp_path, notices):
    before = _counts()
    import_export.import_vector_from_json(str(_write_json(tmp_path, {"tables": {
        "NOTES": {"records": [{"NOTEDATETIME": "x", "NOTEAUTHOR": "y",
                               "NOTETEXT": "z"}]},
    }})))
    assert _counts() == before


def test_a_json_file_with_two_cases_is_refused(populated, tmp_path, notices):
    case = {"CASENUMBER": "A", "LOCATION": "x", "JURISDICTION": "y",
            "CASEDATETIMEBEGIN": "09-01-2026 08:00"}
    before = _counts()
    import_export.import_vector_from_json(str(_write_json(tmp_path, {"tables": {
        "CASES": {"records": [case, dict(case, CASENUMBER="B")]},
    }})))
    assert _counts() == before
    assert any("holds 2 cases" in n for n in notices)


def test_a_json_file_cut_short_is_refused(with_attachment, out_dir, notices):
    exported = import_export.export_vector_to_json(destination=out_dir).zip_path
    payload = json.loads(exported.read_text(encoding="utf-8"))
    payload["tables"]["EVIDENCE"]["records"].pop()
    exported.write_text(json.dumps(payload), encoding="utf-8")
    before = _counts()
    import_export.import_vector_from_json(str(exported))
    assert _counts() == before
    assert any("EVIDENCE table should hold 12 records and holds 11" in n
               for n in notices)


def test_a_json_file_with_an_altered_photo_leaves_the_case_as_it_was(
        with_attachment, out_dir, notices):
    exported = import_export.export_vector_to_json(destination=out_dir).zip_path
    payload = json.loads(exported.read_text(encoding="utf-8"))
    payload["files"]["records"][0]["FILEDATA_b64"] = base64.b64encode(
        b"swapped content").decode("ascii")
    exported.write_text(json.dumps(payload), encoding="utf-8")
    import_export.import_vector_from_json(str(exported))
    with get_session() as session:
        assert session.query(UploadedFiles).one().FILEDATA == PAYLOAD
    assert any("scene_photo.jpg" in n for n in notices)


# ----- P1 05: an archive is checked against its manifest -----

def _rewrite(archive, tmp_path, drop=(), add=None, change=None):
    """A copy of an archive with members dropped, added or changed."""
    copy = tmp_path / "copy.zip"
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(copy, "w") as target:
        for item in source.infolist():
            if item.filename in drop:
                continue
            data = source.read(item.filename)
            if change and item.filename in change:
                data = change[item.filename](data)
            target.writestr(item.filename, data)
        for name, data in (add or {}).items():
            target.writestr(name, data)
    return copy


def _csv_export(out_dir):
    import_export.export_vector_to_csv(destination=out_dir)
    return next(out_dir.glob("*.zip"))


def test_an_archive_missing_a_listed_photo_leaves_the_case_as_it_was(
        with_attachment, out_dir, tmp_path, notices):
    short = _rewrite(_csv_export(out_dir), tmp_path, drop={"files/scene_photo.jpg"})
    before = _counts()
    import_export.import_vector_from_csv(str(short))
    assert _counts() == before
    with get_session() as session:
        assert session.query(UploadedFiles).one().FILEDATA == PAYLOAD
    assert any("not in the archive" in n and "scene_photo.jpg" in n for n in notices)


def test_an_archive_with_an_altered_photo_leaves_the_case_as_it_was(
        with_attachment, out_dir, tmp_path, notices):
    altered = _rewrite(_csv_export(out_dir), tmp_path,
                       change={"files/scene_photo.jpg": lambda data: b"swapped"})
    before = _counts()
    import_export.import_vector_from_csv(str(altered))
    assert _counts() == before
    with get_session() as session:
        assert session.query(UploadedFiles).one().FILEDATA == PAYLOAD


def test_an_archive_with_a_file_its_manifest_does_not_list_is_refused(
        with_attachment, out_dir, tmp_path, notices):
    extra = _rewrite(_csv_export(out_dir), tmp_path,
                     add={"files/added_later.jpg": b"\xff\xd8\xff not ours"})
    before = _counts()
    import_export.import_vector_from_csv(str(extra))
    assert _counts() == before
    assert any("does not list" in n and "added_later.jpg" in n for n in notices)


def test_an_archive_with_a_table_cut_short_is_refused(
        with_attachment, out_dir, tmp_path, notices):
    def drop_last_row(data):
        lines = data.decode("utf-8").splitlines(keepends=True)
        return "".join(lines[:-1]).encode("utf-8")

    short = _rewrite(_csv_export(out_dir), tmp_path,
                     change={"EVIDENCE.csv": drop_last_row})
    before = _counts()
    import_export.import_vector_from_csv(str(short))
    assert _counts() == before
    assert any("EVIDENCE table should hold 12 rows and holds 11" in n for n in notices)


def test_a_whole_archive_still_imports(with_attachment, out_dir):
    archive = _csv_export(out_dir)
    before = _counts()
    delete_all_data()
    import_export.import_vector_from_csv(str(archive))
    assert _counts() == before


# ----- P1 06: Print All prints one case at one moment -----

@pytest.fixture
def print_all(populated, tmp_path, monkeypatch):
    import parts.reports_page as reports
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    monkeypatch.setattr(reports, "is_authenticated", lambda: True)
    return reports


def test_print_all_never_mixes_two_cases(print_all, populated, monkeypatch):
    swapped = {"done": False}
    real = print_all.PRINT_ALL_REPORTS

    def swap_then(build):
        def wrapped():
            if not swapped["done"]:
                swapped["done"] = True
                _next_case()
            return build()
        return wrapped

    monkeypatch.setattr(print_all, "PRINT_ALL_REPORTS", [real[0]] + [
        (key, name, swap_then(build) if n == 0 else build)
        for n, (key, name, build) in enumerate(real[1:])
    ])
    response = asyncio.run(print_all.print_all_document(case=populated))
    # Refused, saying why, rather than a packet of the two.
    assert response.status_code == 409
    assert b"END OF REPORT" not in response.body
    assert b"now 26-999999" in response.body


def test_print_all_is_built_again_when_something_is_saved_meanwhile(
        print_all, populated, monkeypatch):
    """An item added on a tablet while the packet is built: the packet is
    built again, so the evidence list and the return copy agree."""
    added = {"done": False}
    real = print_all.PRINT_ALL_REPORTS

    def add_then(build):
        def wrapped():
            if not added["done"]:
                added["done"] = True
                with get_session() as session:
                    session.add(Notes(NOTEDATETIME="now", NOTEAUTHOR="admin",
                                      NOTETEXT="added meanwhile"))
            return build()
        return wrapped

    monkeypatch.setattr(print_all, "PRINT_ALL_REPORTS",
                        [(k, n, add_then(b)) for k, n, b in real])
    response = asyncio.run(print_all.print_all_document(case=populated))
    assert response.status_code == 200
    assert added["done"]


def test_print_all_asks_for_the_case_the_page_showed():
    import parts.reports_page as reports
    script = reports.print_all_script("26-004711")
    assert "fetch('/reports/print-all?case=' + encodeURIComponent(\"26-004711\")" in script


# ----- Printed sheets -----

def test_every_printed_sheet_names_its_case_and_report():
    import parts.reports_page as reports
    single = reports.print_window_script("Evidence List (Full)", "26-004711")
    assert "@top-center" in single and "26-004711" in single
    assert "Evidence List (Full)" in single
    packet = reports.print_all_script("26-004711")
    for key, name, _build in reports.PRINT_ALL_REPORTS:
        assert f"@page vector-{key}" in packet
        assert reports._css_string(name) in packet


def test_print_all_puts_each_report_on_its_own_named_pages(populated, tmp_path, monkeypatch):
    import parts.reports_page as reports
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    html = reports.print_all_html()
    assert html.count('style="page: vector-evidence_basic"') == 2
    assert 'style="page: vector-agents"' in html


def test_a_case_number_cannot_break_out_of_the_running_line():
    import parts.reports_page as reports
    css = reports.running_line_css('26-"1</style><script>', "Room List")
    assert "</style>" not in css and "<script>" not in css
    assert '"26-' in css and '\\22 ' in css


def test_an_item_is_kept_whole_on_a_printed_sheet(populated):
    import parts.reports_page as reports
    styles = reports.COMMON_STYLES
    printing = styles[styles.index("@media print"):]
    assert ".detail-item {" in printing and "break-inside: avoid;" in printing
    assert ".item-bar {" in printing and "break-after: avoid;" in printing
    by_room = reports.evidence_by_room_report_html()
    with get_session() as session:
        items = session.query(Evidence).count()
    assert by_room.count('<tbody class="detail-item">') == items


def test_a_report_ending_at_the_foot_of_a_sheet_leaves_no_blank_sheet():
    """The page's padding under the last line started a sheet of its own
    when a report ended at the foot of one: the demo case's Evidence List
    (By Room) printed on eight sheets, the eighth blank but for the
    running line and its page number."""
    import re
    import parts.reports_page as reports
    printing = reports.COMMON_STYLES[reports.COMMON_STYLES.index("@media print"):]
    body = re.search(r"\n    body \{([^}]*)\}", printing)
    assert body and "padding-bottom: 0;" in body.group(1)
    # Nothing the print windows add puts padding back on paper.
    for extra in (reports.PRINT_WINDOW_STYLES, reports.PRINT_ALL_STYLES):
        assert "padding-bottom" not in extra


# ----- The report on screen -----

def test_the_report_on_screen_keeps_its_styles():
    """NiceGUI 3 cleans what ui.html is given, dropping a document's head
    and the styles in it: the report showed as plain text."""
    import parts.reports_page as reports
    source = inspect.getsource(reports.render_report_page)
    assert "ui.add_css(SCREEN_REPORT_STYLES)" in source
    assert "ui.html(_report_body(html_content))" in source
    screen = reports.SCREEN_REPORT_STYLES
    # Pointed at the sheet, not the page: the rest of the page is left alone.
    assert "\nbody {" not in screen
    assert ".report-sheet {" in screen and "background: #ffffff;" in screen
