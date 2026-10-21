"""
test_scene_usability.py

The October usability batch: the things that make a search day quicker.

- Room Located, Found By and Witnessed By stay filled in after an item.
- The evidence form is one column on a phone.
- A person's phone number can be typed any way, as an agent's can.
- What is typed into an add form and not saved comes back.
- A QR code on Connect a Device.
- Light mode, from the account menu.
- One search over the whole case.
- A summary of the case, and what to check before leaving, on Home.
- Print All: the reports a search ends with, one button, one window.
- A demo case for training, from the Admin Panel.
- The Tools page's iPhone Wiki link, which had gone dead.
"""

import asyncio
import base64
import hashlib
import inspect
import json
import sys
from pathlib import Path

import pytest

import settings
from models import (
    AuditLog,
    Cases,
    Evidence,
    Notes,
    Rooms,
    UploadedFiles,
    Users,
    get_session,
    get_users_session,
    record_audit,
)

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def machine_settings(tmp_path, monkeypatch):
    """This machine's settings file, in a folder of the test's own."""
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    return tmp_path / "settings.json"


# ----- Room, Found By and Witnessed By stay -----

def test_the_three_fields_an_item_shares_with_the_next_stay_filled_in():
    from parts.evidence_page import SPEC
    kept = {field.name for field in SPEC.fields if field.keep_after_add}
    assert kept == {"EVIDLOCROOM", "EVIDFOUNDBY", "EVIDFOUNDBYWITNESS"}
    assert "stay filled in for the next item" in SPEC.form_hint


def test_only_a_saved_item_keeps_them_and_clear_empties_them():
    import parts.crud as crud
    source = inspect.getsource(crud.build_crud_page)
    assert "_clear_form(after_add=True)" in source
    assert "if after_add and spec_field.keep_after_add:" in source
    # The Clear button empties everything.
    assert 'on_click=lambda: _clear_form(),' in source


# ----- One column on a phone -----

def test_the_evidence_form_stacks_on_a_narrow_screen():
    import parts.crud as crud
    # The code, not the commented-out earlier version above it.
    source = "\n".join(
        line for line in inspect.getsource(crud.build_crud_page).splitlines()
        if not line.strip().startswith("#")
    )
    assert "grid-cols-1 md:grid-cols-2" in source
    assert "ui.grid(columns=2)" not in source


# ----- A person's phone number -----

def test_a_persons_phone_is_typed_any_way_and_saved_the_one_way():
    from parts.persons_page import SPEC
    from utils import format_phone
    phone = next(field for field in SPEC.fields if field.name == "PERSONPHONE")
    assert "mask" not in phone.props
    assert phone.tidy is format_phone
    assert phone.tidy("703.555.0199 ext 4") == "(703) 555-0199 x4"
    assert phone.tidy("+44 20 7946 0958") == "+44 20 7946 0958"


# ----- What was typed and not saved -----

@pytest.fixture
def browser_store(monkeypatch):
    import parts.drafts as drafts
    import auth
    store = {}
    who = {"name": "agent"}
    monkeypatch.setattr(drafts, "_store", lambda: store)
    monkeypatch.setattr(auth, "get_current_user_name", lambda: who["name"])
    return store, who


def test_a_draft_is_kept_and_given_back(browser_store):
    from parts.drafts import load_draft, save_draft
    save_draft("Evidence Management", {"EVIDDESC": "Laptop, silver"})
    assert load_draft("Evidence Management") == {"EVIDDESC": "Laptop, silver"}
    assert load_draft("Notes") == {}


def test_a_draft_belongs_to_the_account_that_typed_it(browser_store):
    """A tablet passed to a colleague does not show them your draft."""
    from parts.drafts import load_draft, save_draft
    _store, who = browser_store
    save_draft("Notes", {"NOTETEXT": "Half a note"})
    who["name"] = "someone.else"
    assert load_draft("Notes") == {}


def test_saving_or_clearing_forgets_the_draft(browser_store):
    from parts.drafts import clear_draft, load_draft, save_draft
    save_draft("Notes", {"NOTETEXT": "Half a note"})
    clear_draft("Notes")
    assert load_draft("Notes") == {}
    save_draft("Notes", {"NOTETEXT": "Again"})
    save_draft("Notes", {})          # everything typed was deleted
    assert load_draft("Notes") == {}


def test_drafts_never_break_a_page_outside_a_browser():
    from parts.drafts import clear_draft, load_draft, save_draft
    assert load_draft("Notes") == {}
    save_draft("Notes", {"NOTETEXT": "x"})
    clear_draft("Notes")


def test_every_add_form_keeps_its_draft_but_not_the_numbers_vector_hands_out():
    import parts.crud as crud
    source = inspect.getsource(crud.build_crud_page)
    assert "typed_fields = [f for f in form_fields if not f.readonly]" in source
    assert "_restore_draft()" in source
    assert "clear_draft(spec.title)" in source


# ----- QR code -----

def test_connect_a_device_draws_a_qr_code_of_the_address():
    from parts.connect_page import qr_code_image
    image = qr_code_image("http://192.168.1.23:8080")
    assert image.startswith("data:image/png;base64,")
    assert base64.b64decode(image.split(",", 1)[1])[:8] == b"\x89PNG\r\n\x1a\n"


def test_without_the_qr_package_the_page_is_as_it_was(monkeypatch):
    from parts.connect_page import qr_code_image
    monkeypatch.setitem(sys.modules, "segno", None)
    assert qr_code_image("http://192.168.1.23:8080") == ""


def test_the_qr_package_is_a_requirement():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "segno~=" in requirements


# ----- Light mode -----

def test_light_mode_is_in_the_account_menu_not_the_bar():
    import navbar
    source = inspect.getsource(navbar.build_navbar)
    assert "(THEME_ITEM, lambda: flip_theme(dark))" in source
    assert navbar.THEME_ITEM == "Light or dark page"


def test_the_switch_flips_and_is_kept_for_the_browser(monkeypatch):
    import navbar

    class Switch:
        value = True

    stored = {}

    class Storage:
        user = stored

    monkeypatch.setattr(navbar.app, "storage", Storage)
    dark = Switch()
    navbar.flip_theme(dark)
    assert dark.value is False and stored[navbar.THEME] == "light"
    assert navbar.prefers_light()
    navbar.flip_theme(dark)
    assert dark.value is True and stored[navbar.THEME] == "dark"


def test_vector_is_dark_unless_a_browser_chose_light():
    import navbar
    assert navbar.prefers_light() is False


@pytest.mark.parametrize(
    "rule",
    [
        "body.body--light {\n    --vsp-gray:",
        "body.body--light .text-gray-400",
        "body.body--light .text-\\[\\#F5B027\\]",
        "body.body--light .text-green-500",
        "body.body--light .text-red-400",
        "body.body--light .border-\\[\\#3a3a3a\\]",
    ],
)
def test_the_colours_drawn_for_a_dark_page_are_put_right_on_a_light_one(rule):
    """Checked in the CSS as Python hands it to the browser, which is
    where a backslash in the wrong place would show."""
    import ast
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    css = next(
        node.value for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and "body.body--light" in node.value
    )
    assert rule in css


def test_main_compiles_without_a_warning():
    """An unknown escape such as "\\[" in a Python string is a warning
    today and an error in a later Python."""
    import warnings
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        compile(source, "main.py", "exec")


def test_the_top_bar_keeps_to_one_line_at_the_widths_measured():
    """Measured in a browser, with the search button, from 360 to 1,920
    px: the row of pages from 1,344, the phone layout below 720, and no
    name beside the logo below 375."""
    import navbar
    assert navbar.NAV_ROW_MIN_WIDTH == 1344
    assert navbar.NAV_PHONE_MAX_WIDTH == 720
    assert "@media (max-width: 374.98px)" in navbar._NAV_CSS
    assert "@media (max-width: 719.98px)" in navbar._NAV_CSS


# ----- Search the whole case -----

def test_a_search_finds_an_item_by_its_serial_number(populated):
    from parts.case_search import search_case
    with get_session() as session:
        session.query(Evidence).filter_by(EVIDNUM="7").one().EVIDSERIALNUMBER = "C02XK1ZZ"
    hits = search_case("c02xk1")
    assert [(hit.kind, hit.title.split(":")[0]) for hit in hits] == [("Item", "Item 7")]
    assert hits[0].found == "Serial #: C02XK1ZZ"
    assert hits[0].route == "/evidence?find=c02xk1"


def test_a_name_is_found_everywhere_it_appears(populated):
    from parts.case_search import search_case
    kinds = {hit.kind for hit in search_case("Doe, John")}
    assert {"Agent", "Room", "Item", "Note"} <= kinds


def test_a_search_needs_two_characters(populated):
    from parts.case_search import search_case
    assert search_case("a") == []
    assert search_case("  ") == []


def test_percent_and_underscore_are_searched_for_as_typed(populated):
    from parts.case_search import search_case
    assert search_case("%%") == []
    assert search_case("_x") == []


def test_files_are_found_by_name_and_fingerprint(case):
    from parts.case_search import search_case
    data = b"\xff\xd8\xff photograph"
    digest = hashlib.sha256(data).hexdigest().upper()
    with get_session() as session:
        session.add(UploadedFiles(
            FILENAME="IMG_0042.jpg", FILEDATA=data, FILESIZE=len(data),
            FILEMIMETYPE="image/jpeg", FILEUPLOADEDBY="Roe, Jane",
            FILESHA256=digest,
        ))
    assert [hit.kind for hit in search_case("img_0042")] == ["File"]
    assert [hit.kind for hit in search_case(digest[:12].lower())] == ["File"]


def test_a_result_opens_its_page_filtered_to_what_was_searched_for():
    import parts.crud as crud
    source = inspect.getsource(crud.build_crud_page)
    assert '_asked_for("find")' in source


def test_the_search_is_in_the_top_bar():
    import navbar
    assert "search_button()" in inspect.getsource(navbar.build_navbar)


# ----- The summary and the checklist on Home -----

def test_the_counts_on_home(populated):
    from parts.case_summary import case_counts
    counts = {label: count for label, count, _route in case_counts()}
    assert counts == {"Items": 12, "Rooms": 2, "Agents": 2, "People": 1,
                      "Notes": 1, "Files": 0}


def test_nothing_to_check_before_a_case_is_open():
    from parts.case_summary import scene_checks
    assert scene_checks() == []


def _texts(checks, ok=False):
    return [check.text for check in checks if check.ok == ok]


def test_the_checklist_says_what_is_missing(populated):
    from parts.case_summary import scene_checks
    with get_session() as session:
        session.query(Rooms).filter_by(ROOMLABEL="B").one().ROOMSECONDAGENT = ""
        session.query(Cases).one().CASEDATETIMEEND = ""
        for item in session.query(Evidence):
            item.EVIDPICTAKEN = "Yes"
            item.EVIDTRIAGED = "No"
        session.query(Evidence).filter_by(EVIDNUM="3").one().EVIDPICTAKEN = "No"
        session.query(Evidence).filter_by(EVIDNUM="10").one().EVIDTRIAGED = ""
    problems = _texts(scene_checks())
    assert "The case has no end date and time yet. Every report prints them." in problems
    assert "Room B has fewer than two agents named." in problems
    assert "Item 3 is not marked as photographed." in problems
    assert "Item 10 has no answer for Item Triaged." in problems
    assert any("not been exported" in text for text in problems)


def test_a_long_list_is_shortened(populated):
    from parts.case_summary import scene_checks
    problems = _texts(scene_checks())
    assert ("Items 1, 2, 3, 4, 5, 6, 7, 8 and 4 more are not marked as "
            "photographed.") in problems


def test_an_export_after_the_last_change_is_ticked_off(populated):
    from parts.case_summary import scene_checks

    def export_check():
        return next(c for c in scene_checks() if "export" in c.text.lower())

    with get_session() as session:
        record_audit(session, action="EXPORT", table_name="(all case tables)")
    assert export_check().ok

    with get_session() as session:
        session.add(Notes(NOTEDATETIME="now", NOTEAUTHOR="Doe, John",
                          NOTETEXT="One more thing"))
    check = export_check()
    assert not check.ok
    assert check.text.startswith("The case has changed since it was last exported.")


def test_home_draws_them():
    import home_page
    assert "case_overview()" in inspect.getsource(home_page.build_authenticated_home)


# ----- Print All -----

def test_print_all_prints_what_a_search_ends_with_by_default(machine_settings):
    assert settings.print_all_copies() == {
        "agents": 1, "rooms": 1, "evidence": 1, "evidence_by_room": 0,
        "evidence_basic": 2, "persons": 1, "notes": 0, "files": 0,
    }


def test_what_print_all_prints_is_kept_and_checked(machine_settings):
    settings.set_print_all_copies({"notes": 1, "files": 9, "nonsense": 1,
                                   "agents": "two", "rooms": True})
    copies = settings.print_all_copies()
    assert copies["notes"] == 1
    assert copies["files"] == 0          # more than three is refused
    assert copies["agents"] == 1         # not a number: unchanged
    assert copies["rooms"] == 1          # a yes/no is not a number
    assert "nonsense" not in copies
    stored = json.loads(machine_settings.read_text(encoding="utf-8"))
    assert stored["print_all"]["notes"] == 1


def test_a_damaged_setting_falls_back_to_the_default(machine_settings):
    machine_settings.write_text('{"print_all": "everything"}', encoding="utf-8")
    assert settings.print_all_copies()["evidence_basic"] == 2


def test_print_all_puts_the_reports_in_order_with_two_return_copies(
        populated, machine_settings):
    from parts.reports_page import print_all_html
    html = print_all_html()
    titles = ["INVESTIGATORS AT SEARCH WARRANT SITE", "ROOM LIST",
              "FULL EVIDENCE INVENTORY LIST", "SEARCH INVENTORY AND RETURN",
              "PERSONS LIST"]
    positions = [html.index(title) for title in titles]
    assert positions == sorted(positions)
    assert html.count("SEARCH INVENTORY AND RETURN") == 2
    assert html.count('<section class="print-all-part">') == 6
    assert "NOTES LIST" not in html and "ATTACHED FILES LIST" not in html
    # Bodies only: the print window carries the styles once.
    assert "<!DOCTYPE" not in html and "<style>" not in html


def test_each_report_starts_a_new_sheet_and_no_page_numbers():
    from parts.reports_page import PRINT_ALL_STYLES
    assert ".print-all-part + .print-all-part {\n    break-before: page;" in PRINT_ALL_STYLES
    assert "content: none;" in PRINT_ALL_STYLES


def test_print_all_says_what_it_prints(machine_settings):
    from parts.reports_page import print_all_summary
    assert print_all_summary() == (
        "Agent List, Room List, Evidence List (Full), "
        "Inventory and Return (2 copies), Persons List"
    )
    assert print_all_summary({key: 0 for key in settings.PRINT_ALL_DEFAULT}) == ""


def test_every_report_print_all_knows_has_a_default():
    from parts.reports_page import PRINT_ALL_REPORTS
    assert [key for key, _name, _build in PRINT_ALL_REPORTS] == list(
        settings.PRINT_ALL_DEFAULT
    )


def _document(monkeypatch, signed_in: bool):
    import parts.reports_page as reports
    monkeypatch.setattr(reports, "is_authenticated", lambda: signed_in)
    return asyncio.run(reports.print_all_document())


def test_print_all_is_for_signed_in_users_only(monkeypatch, populated):
    assert _document(monkeypatch, signed_in=False).status_code == 403


def test_print_all_says_what_is_missing_before_a_case_can_print(monkeypatch):
    response = _document(monkeypatch, signed_in=True)
    assert response.status_code == 409
    assert b"No case exists" in response.body


def test_print_all_hands_the_reports_to_its_window(
        monkeypatch, populated, machine_settings):
    response = _document(monkeypatch, signed_in=True)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.body.count(b"SEARCH INVENTORY AND RETURN") == 2


def test_print_all_with_nothing_chosen_says_so(
        monkeypatch, populated, machine_settings):
    settings.set_print_all_copies({key: 0 for key in settings.PRINT_ALL_DEFAULT})
    response = _document(monkeypatch, signed_in=True)
    assert response.status_code == 409
    assert b"no reports chosen" in response.body


def test_the_window_is_opened_by_the_click_and_filled_after(machine_settings):
    from parts.reports_page import print_all_script
    script = print_all_script('26-"0047"')
    assert script.index("window.open(") < script.index("fetch('/reports/print-all'")
    # A typed case number is text in the window, never markup.
    assert "26-&quot;0047&quot;" in script


def test_a_change_to_what_print_all_prints_is_audited_once(machine_settings):
    from utils import set_print_all
    set_print_all({"notes": 1}, actor="admin")
    set_print_all({"notes": 1}, actor="admin")   # no change, no entry
    with get_session() as session:
        entries = session.query(AuditLog).filter_by(action="SETTING_CHANGED").all()
        assert len(entries) == 1
        assert entries[0].actor == "admin"
        assert "notes 1 copy" in entries[0].summary


def test_the_single_reports_still_work_on_their_own(populated):
    import parts.reports_page as reports
    for build in (reports.agents_report_html, reports.rooms_report_html,
                  reports.evidence_report_html, reports.evidence_by_room_report_html,
                  reports.basic_evidence_report_html, reports.persons_report_html,
                  reports.notes_report_html, reports.files_report_html):
        html = build()
        assert html.startswith("<!DOCTYPE html>") and "END OF REPORT" in html


# ----- The demo case, for training -----

def test_the_demo_case_replaces_the_case_and_nothing_else(populated):
    from parts.admin_users import load_demo_case
    with get_users_session() as session:
        session.add(Users(USERNAME="real.agent", PASSWORDHASH="x", ISADMIN=False,
                          ISACTIVE=True))
    roster = ROOT / "parts" / "agents.json"
    before = roster.read_bytes() if roster.exists() else None

    assert load_demo_case("admin") == "26-DEMO-001"

    with get_session() as session:
        assert session.query(Cases).one().CASENUMBER == "26-DEMO-001"
        assert not session.query(Evidence).filter(
            Evidence.EVIDDESC.like("Smith & Wesson%")).count()
        actions = [entry.action for entry in
                   session.query(AuditLog).order_by(AuditLog.id)]
        seeded = session.query(AuditLog).filter_by(action="DEMO_SEED").one()
        assert seeded.actor == "admin"
    assert actions.index("DELETE_ALL") < actions.index("DEMO_SEED")
    with get_users_session() as session:
        assert session.query(Users).filter_by(USERNAME="real.agent").count() == 1
        session.query(Users).filter_by(USERNAME="real.agent").delete()
    assert (roster.read_bytes() if roster.exists() else None) == before


def test_the_admin_panel_offers_it_and_asks_first():
    import parts.admin_users as admin_users
    import parts.admin_page as admin_page
    assert "training_card()" in inspect.getsource(admin_page.build_admin_page)
    source = inspect.getsource(admin_users.training_card)
    assert "TYPE DEMO TO CONFIRM" in source
    assert "if not get_is_admin():" in source


def test_the_demo_is_a_filter_on_the_audit_trail():
    from parts.audit_page import ACTION_CHOICES
    assert "DEMO_SEED" in ACTION_CHOICES


# ----- The Tools page -----

def test_the_tools_page_has_no_dead_iphone_wiki_link():
    source = (ROOT / "parts" / "links_page.py").read_text(encoding="utf-8")
    assert "theiphonewiki.com" not in source
    assert "https://theapplewiki.com/" in source
