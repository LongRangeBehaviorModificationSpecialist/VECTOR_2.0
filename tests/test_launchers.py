"""The double-click launchers.

"Start VECTOR.command" was renamed to "Start VECTOR.sh", which quietly
took the macOS launcher away: Finder opens a .command file in Terminal
when it is double-clicked, and does not open a .sh file at all. The
line endings matter just as much -- bash stops at the first carriage
return with "$'\\r': command not found" -- and they are pinned in
.gitattributes, which a rename leaves behind.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

WINDOWS = ROOT / "Start VECTOR.bat"
MAC_CLICKABLE = ROOT / "Start VECTOR.command"
MAC_SCRIPT = ROOT / "Start VECTOR.sh"


def test_every_launcher_is_present():
    missing = [
        path.name
        for path in (WINDOWS, MAC_CLICKABLE, MAC_SCRIPT)
        if not path.is_file()
    ]
    assert not missing, missing


def test_finder_has_a_file_it_will_open():
    """The .command file is what a double-click runs, and it hands over
    to the .sh script rather than repeating it."""
    text = MAC_CLICKABLE.read_text(encoding="utf-8")
    assert MAC_SCRIPT.name in text


def test_the_launchers_pass_their_arguments_on():
    """Without this, "./Start VECTOR.command" --lan starts on loopback
    and the tablets never reach it."""
    assert '"$@"' in MAC_CLICKABLE.read_text(encoding="utf-8")
    assert "%*" in WINDOWS.read_text(encoding="utf-8")


def test_the_mac_launchers_have_unix_line_endings():
    for path in (MAC_CLICKABLE, MAC_SCRIPT):
        assert b"\r\n" not in path.read_bytes(), path.name


def test_the_line_endings_are_pinned_for_every_launcher():
    """A checkout on either system has to produce a file that runs."""
    rules = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.bat" in rules
    for pattern in ("*.command", "*.sh"):
        assert f"{pattern}" in rules, pattern


# ----- The desktop shortcut -----

def test_both_launchers_offer_the_shortcut_once():
    """Asked on the first start, remembered in .venv either way, so it is
    never asked again; tools/make_shortcut.py does the work."""
    for path in (WINDOWS, MAC_SCRIPT):
        text = path.read_text(encoding="utf-8")
        assert "shortcut.offered" in text, path.name
        assert "tools" in text and "make_shortcut.py" in text, path.name
        assert "Put a VECTOR shortcut on the desktop" in text, path.name


def test_the_shortcut_question_cannot_hold_up_a_start():
    """Nobody at the laptop? It goes ahead after 30 seconds."""
    assert "/t 30 /d Y" in WINDOWS.read_text(encoding="utf-8")
    assert "read -r -t 30" in MAC_SCRIPT.read_text(encoding="utf-8")


# ----- 00 START HERE -----

START_HERE = ROOT / "00 START HERE"
START_WINDOWS = START_HERE / "Start VECTOR (Windows).bat"
START_MAC = START_HERE / "Start VECTOR (Mac).command"


def test_the_start_here_folder_has_the_guide_and_both_start_files():
    for path in (START_HERE / "README.md", START_WINDOWS, START_MAC):
        assert path.is_file(), path.name


def test_the_start_files_hand_over_to_the_real_launchers():
    """One copy of the launcher, so the two can never drift apart; the
    arguments go through, as they do from the main folder."""
    windows = START_WINDOWS.read_text(encoding="utf-8")
    assert '"%~dp0..\\Start VECTOR.bat" %*' in windows
    mac = START_MAC.read_text(encoding="utf-8")
    assert '"$(dirname "$0")/../Start VECTOR.sh" "$@"' in mac
    assert b"\r\n" not in START_MAC.read_bytes()


def test_the_start_here_guide_shows_its_pictures():
    """The pictures are in docs/images/install, one folder up from it."""
    import re

    guide = (START_HERE / "README.md").read_text(encoding="utf-8")
    pictures = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", guide)
    assert len(pictures) >= 6, pictures
    missing = [p for p in pictures if not (START_HERE / p).resolve().is_file()]
    assert not missing, missing


def test_the_launchers_point_at_the_start_here_guide_when_they_fail():
    for path in (WINDOWS, MAC_SCRIPT):
        assert "00 START HERE" in path.read_text(encoding="utf-8"), path.name


# ----- The Download ZIP -----

LEFT_OUT = [
    "tests/conftest.py", ".github/workflows/tests.yml",
    "requirements-dev.txt", "ruff.toml", "pytest.ini",
]
KEPT = [
    "main.py", "requirements.txt", "Start VECTOR.bat", "Start VECTOR.sh",
    "Start VECTOR.command", "00 START HERE/README.md",
    "00 START HERE/VECTOR install guide.pdf",
    "00 START HERE/Start VECTOR (Windows).bat",
    "00 START HERE/Start VECTOR (Mac).command", "tools/make_shortcut.py",
    "static/icons/vector.ico", "docs/REFERENCE.md",
    "docs/images/install/sign-in.png", "parts/help_page.py",
]


def test_the_download_zip_leaves_out_only_what_developers_use():
    """GitHub's Download ZIP honours export-ignore. An agent should get
    everything that runs VECTOR and everything the guide shows, and
    none of the tests or the CI setup."""
    if not shutil.which("git") or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(
        ["git", "check-attr", "export-ignore", "--", *LEFT_OUT, *KEPT],
        cwd=ROOT, capture_output=True, text=True,
    ).stdout
    found = {line.split(": ")[0]: line.rsplit(": ", 1)[1] for line in out.splitlines()}
    assert all(found[path] == "set" for path in LEFT_OUT), found
    assert all(found[path] == "unspecified" for path in KEPT), found
