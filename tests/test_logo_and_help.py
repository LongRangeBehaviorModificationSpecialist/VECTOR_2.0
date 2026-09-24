"""The logo fallback and the Help page.

Both used to go stale without anyone noticing: the logo files are unit
branding that a checkout does not include, so every page showed a
broken-image icon, and the Help page still named buttons -- "Case Info"
-- that had since been renamed.
"""

import re
from pathlib import Path

import pytest

import home_page
import navbar

ROOT = Path(__file__).resolve().parent.parent


# ----- Logo -----
def test_a_missing_logo_has_no_address(tmp_path, monkeypatch):
    monkeypatch.setattr(navbar, "STATIC_DIR", tmp_path)
    assert navbar.static_url("novadc_icac.png") is None


def test_a_present_logo_is_served_from_static(tmp_path, monkeypatch):
    (tmp_path / "novadc_icac.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(navbar, "STATIC_DIR", tmp_path)
    assert navbar.static_url("novadc_icac.png") == "/static/novadc_icac.png"


def test_a_folder_is_not_taken_for_a_logo(tmp_path, monkeypatch):
    (tmp_path / "novadc_icac.png").mkdir()
    monkeypatch.setattr(navbar, "STATIC_DIR", tmp_path)
    assert navbar.static_url("novadc_icac.png") is None


def test_a_logo_named_by_its_static_address_is_found(tmp_path, monkeypatch):
    """/static/x.png is what a page would write by hand, so unit_logo()
    takes that as well as the bare file name. Taking it literally is how
    a logo that is present gets dropped."""
    (tmp_path / "novadc_icac.png").write_bytes(b"pretend this is a png")
    monkeypatch.setattr(navbar, "STATIC_DIR", tmp_path)

    for named in ("novadc_icac.png",
                  "static/novadc_icac.png",
                  "/static/novadc_icac.png"):
        assert navbar.static_url(named) == "/static/novadc_icac.png", named


def test_a_missing_logo_is_still_left_out_whichever_way_it_is_named(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(navbar, "STATIC_DIR", tmp_path)

    for named in ("novadc_icac.png", "/static/novadc_icac.png"):
        assert navbar.static_url(named) is None, named


def test_no_page_points_at_a_static_image_directly():
    """Every logo goes through unit_logo(), which checks the file is there."""
    pages = [ROOT / "home_page.py", ROOT / "navbar.py",
             *sorted((ROOT / "parts").glob("*.py"))]
    offenders = [
        str(path.relative_to(ROOT))
        for path in pages
        if re.search(r"ui\.image\(\s*[\"']/static/",
                     path.read_text(encoding="utf-8"))
    ]
    assert not offenders, offenders


# ----- Help -----
def _on_screen_text() -> str:
    """Source of everything that labels a button or menu, minus the help."""
    sources = [(ROOT / "navbar.py").read_text(encoding="utf-8")]
    sources += [path.read_text(encoding="utf-8")
                for path in sorted((ROOT / "parts").glob("*.py"))]
    home_source = (ROOT / "home_page.py").read_text(encoding="utf-8")
    sources.append(home_source.split("HELP_TEXT = ")[0])
    return "\n".join(sources).lower()


def test_every_button_the_help_names_exists():
    named = re.findall(r"\*\*(.+?)\*\*", home_page.HELP_TEXT)
    assert len(named) > 10, named
    on_screen = _on_screen_text()
    missing = sorted({name for name in named
                      if name.lower() not in on_screen})
    assert not missing, f"the Help page names buttons that do not exist: {missing}"


def test_the_help_does_not_use_old_names():
    assert "Case Info" not in home_page.HELP_TEXT


@pytest.mark.parametrize("topic", [
    "one case at a time",
    "Start New Case",
    "Export Case Data",
    "Import Case Data",
    "Delete All Data",
])
def test_the_help_covers(topic):
    assert topic.lower() in home_page.HELP_TEXT.lower()


def test_the_help_states_the_real_lockout_rule():
    from auth import LOCK_AFTER_FAILURES, LOCKOUT_MINUTES

    assert f"After {LOCK_AFTER_FAILURES} wrong passwords" in home_page.HELP_TEXT
    assert f"{LOCKOUT_MINUTES} minutes" in home_page.HELP_TEXT
