"""The double-click launchers.

"Start VECTOR.command" was renamed to "Start VECTOR.sh", which quietly
took the macOS launcher away: Finder opens a .command file in Terminal
when it is double-clicked, and does not open a .sh file at all. The
line endings matter just as much -- bash stops at the first carriage
return with "$'\\r': command not found" -- and they are pinned in
.gitattributes, which a rename leaves behind.
"""

from pathlib import Path

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
