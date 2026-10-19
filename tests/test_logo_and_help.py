"""
test_logo_and_help.py

The logo fallback and the Help page.

Both used to go stale without anyone noticing: the logo files are unit
branding that a checkout does not include, so every page showed a
broken-image icon, and the Help page still named buttons -- "Case Info"
-- that had since been renamed.
"""

import re
from pathlib import Path

import pytest

from parts import help_page
import navbar

ROOT = Path(__file__).resolve().parent.parent


# ----- Buttons -----
def test_the_hover_line_is_for_a_mouse_only():
    """An iPad keeps a tapped button "hovered", so the dashed line stayed
    on it; and the transparent border that made room for the line left a
    ring round every raised button."""
    css = (ROOT / "main.py").read_text(encoding="utf-8")
    start = css.index(".hover-border-white {")
    block = css[start:css.index("/* Print styles */", start)]
    assert "transparent" not in block
    mouse_only = block.index("@media (hover: hover)")
    assert ":hover" not in block[:mouse_only]
    assert ".hover-border-white:hover" in block[mouse_only:]
    assert ".hover-border-blue:hover" in block[mouse_only:]


# ----- Logo -----
def test_a_missing_logo_has_no_address(tmp_path, monkeypatch):
    monkeypatch.setattr(navbar, "STATIC_DIR", tmp_path)
    assert navbar.static_url("novadc_icac.png") is None


def test_a_present_logo_is_served_from_static(tmp_path, monkeypatch):
    (tmp_path / "novadc_icac.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.setattr(navbar, "STATIC_DIR", tmp_path)
    assert (
        navbar.static_url("novadc_icac.png") == "/static/novadc_icac.png"
    )


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
    pages = [
        ROOT / "home_page.py",
        ROOT / "navbar.py",
        *sorted((ROOT / "parts").glob("*.py"))
    ]
    offenders = [
        str(path.relative_to(ROOT))
        for path in pages
        if re.search(
            r"ui\.image\(\s*[\"']/static/",
            path.read_text(encoding="utf-8")
        )
    ]
    assert not offenders, offenders


# ----- Help -----
def _on_screen_text() -> str:
    """Source of everything that labels a button or menu, minus the help."""
    sources = [
        (ROOT / "navbar.py").read_text(encoding="utf-8"),
        (ROOT / "idle.py").read_text(encoding="utf-8"),
    ]
    sources += [
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "parts").glob("*.py"))
        if path.name != "help_page.py"
    ]
    sources.append((ROOT / "home_page.py").read_text(encoding="utf-8"))
    return "\n".join(sources).lower()


def test_every_button_the_help_names_exists():
    named = re.findall(r"\*\*(.+?)\*\*", help_page.HELP_TEXT)
    assert len(named) > 10, named
    on_screen = _on_screen_text()
    missing = sorted(
        {name for name in named if name.lower() not in on_screen}
    )
    assert not missing, (
        f"the Help page names buttons that do not exist: {missing}"
    )


def test_the_help_does_not_use_old_names():
    assert "Case Info" not in help_page.HELP_TEXT


@pytest.mark.parametrize("topic", [
    "one case at a time",
    "Start New Case",
    "Export Case Data",
    "Import Case Data",
    "Delete All Data",
])
def test_the_help_covers(topic):
    assert topic.lower() in help_page.HELP_TEXT.lower()


@pytest.mark.parametrize("topic", [
    "Print Report Without Names",   # the Room List with names missing
    "Connect a Device",              # tablets
    "x12",                           # a phone extension
    "pop-ups",                       # the print window
])
def test_the_help_covers_what_agents_ask(topic):
    assert topic.lower() in help_page.HELP_TEXT.lower()


def test_the_help_no_longer_says_the_room_list_waits():
    """Since the author's 70120de the Room List can be printed with
    names missing; the help said it waited for both agents."""
    assert "waits until every" not in help_page.HELP_TEXT


def test_each_help_topic_has_an_icon_a_title_and_text():
    titles = [title for _icon, title, _text in help_page.HELP_SECTIONS]
    assert len(titles) == len(set(titles)) >= 10
    for icon, title, text in help_page.HELP_SECTIONS:
        assert icon and title and len(text.strip()) > 40, title


def test_the_help_states_the_real_lockout_rule():
    from auth import LOCK_AFTER_FAILURES, LOCKOUT_MINUTES

    assert f"After {LOCK_AFTER_FAILURES} wrong passwords" in help_page.HELP_TEXT
    assert f"{LOCKOUT_MINUTES} minutes" in help_page.HELP_TEXT
