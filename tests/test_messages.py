"""test_messages.py

Which messages fade and which stay.

Upstream's four-second timeout suits a prompt to fill a field in or a
confirmation. A message saying that something did not happen -- nothing
was saved, deleted, imported or exported -- has to be read, so it stays
until OK is pressed.
"""

import re
from pathlib import Path

import pytest

import import_export
import utils
from parts import crud_widgets

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def said(monkeypatch):
    """Every ui.notify call, as (message, keyword arguments)."""
    calls = []

    def notify(message, **kwargs):
        calls.append((message, kwargs))

    for module in (crud_widgets, import_export, utils):
        monkeypatch.setattr(module.ui, "notify", notify)
    return calls


def test_a_save_that_failed_stays_until_acknowledged(said):
    crud_widgets.notify_problem("Could not save this evidence.")
    (_, kwargs), = said
    assert kwargs["timeout"] == 0
    assert kwargs["close_button"] == "OK"


def test_a_confirmation_still_fades(said):
    crud_widgets.notify_done("Evidence saved.")
    (_, kwargs), = said
    assert kwargs["timeout"] > 0


def test_an_export_or_import_that_failed_stays(said):
    import_export._report_failure(
        "Nothing was imported, and the case is unchanged.", OSError("disk")
    )
    (message, kwargs), = said
    assert "Nothing was imported" in message
    assert kwargs["timeout"] == 0


def test_the_wipe_itself_says_nothing(said, populated):
    """Delete All Data and Start New Case both wipe through this, and
    each says its own thing after it; the wipe saying something too put
    two messages on the screen for one Start New Case."""
    utils.delete_all_data()
    assert said == []


def test_no_debugging_note_is_left_in_a_message():
    """"(ln 1354)" reached a message users would see."""
    sources = [ROOT / name for name in ("import_export.py", "utils.py",
                                        "home_page.py", "main.py")]
    sources += sorted((ROOT / "parts").glob("*.py"))
    found = [
        f"{path.name}: {line.strip()}"
        for path in sources
        for line in path.read_text(encoding="utf-8").splitlines()
        if re.search(r"\(ln \d+\)", line)
    ]
    assert not found, found
