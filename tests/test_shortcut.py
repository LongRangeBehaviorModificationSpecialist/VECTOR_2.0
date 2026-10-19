"""The desktop shortcut and its icon.

A shortcut holds the folder VECTOR is in, so it cannot be shipped; it is
made on each computer by tools/make_shortcut.py, which the launchers
offer the first time they start. These tests build each system's kind in
a temporary folder: a Windows .lnk for real where Windows is running, and
the macOS app and the Linux entry anywhere, since both are ordinary files.
"""

import plistlib
import shlex
import struct
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "static" / "icons"
sys.path.insert(0, str(ROOT / "tools"))

import make_shortcut  # noqa: E402


# ----- The icon files -----

def _ico_sizes(data: bytes) -> list[int]:
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1)
    sizes = []
    for i in range(count):
        width = data[6 + 16 * i]
        sizes.append(width or 256)
    return sizes


def test_the_windows_icon_has_every_size_windows_asks_for():
    sizes = _ico_sizes((ICONS / "vector.ico").read_bytes())
    assert {16, 24, 32, 48, 256} <= set(sizes), sizes


def test_the_windows_icon_keeps_png_for_the_large_size_only():
    """Every part of Windows reads bitmaps; only the 256 px image is PNG,
    as Microsoft recommends. An all-PNG icon could not be read by
    System.Drawing."""
    data = (ICONS / "vector.ico").read_bytes()
    count = struct.unpack("<H", data[4:6])[0]
    for i in range(count):
        width, _h, _c, _r, _p, _bpp, size, offset = struct.unpack(
            "<BBBBHHII", data[6 + 16 * i:22 + 16 * i])
        is_png = data[offset:offset + 8] == b"\x89PNG\r\n\x1a\n"
        assert is_png == (width == 0), (width or 256, is_png)


def test_the_mac_icon_holds_every_retina_size():
    data = (ICONS / "vector.icns").read_bytes()
    assert data[:4] == b"icns"
    assert struct.unpack(">I", data[4:8])[0] == len(data)
    kinds, pos = set(), 8
    while pos < len(data):
        kind, length = data[pos:pos + 4], struct.unpack(">I", data[pos + 4:pos + 8])[0]
        assert data[pos + 8:pos + 16] == b"\x89PNG\r\n\x1a\n", kind
        kinds.add(kind)
        pos += length
    assert {b"icp4", b"icp5", b"ic07", b"ic08", b"ic09", b"ic10"} <= kinds


def test_the_linux_icon_is_a_256_px_png():
    data = (ICONS / "vector-256.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", data[16:24]) == (256, 256)


# ----- macOS -----

def test_the_mac_app_is_a_complete_bundle(tmp_path):
    app = make_shortcut.make_mac_app(tmp_path)
    contents = app / "Contents"
    assert app.name == "VECTOR.app"
    info = plistlib.loads((contents / "Info.plist").read_bytes())
    assert info["CFBundleExecutable"] == "VECTOR"
    assert info["CFBundlePackageType"] == "APPL"
    assert (contents / "Resources" / f"{info['CFBundleIconFile']}.icns").read_bytes() == \
        (ICONS / "vector.icns").read_bytes()
    script = (contents / "MacOS" / "VECTOR").read_text(encoding="utf-8")
    assert script.startswith("#!/bin/bash\n")
    assert "\r" not in script


def test_the_mac_app_opens_the_launcher_in_terminal(tmp_path):
    """So the VECTOR window appears, as a double-click on the launcher
    gives -- and a folder name with spaces or quotes still works."""
    folder = tmp_path / "Agent's VECTOR folder"
    script = make_shortcut.mac_launcher_script(folder)
    command = script.strip().splitlines()[-1]
    assert command.startswith("exec open -a Terminal ")
    assert shlex.split(command)[-1] == str(folder / "Start VECTOR.command")


@pytest.mark.skipif(sys.platform.startswith("win"), reason="no execute bit on Windows")
def test_the_mac_app_can_run(tmp_path):
    executable = make_shortcut.make_mac_app(tmp_path) / "Contents" / "MacOS" / "VECTOR"
    assert executable.stat().st_mode & 0o111


def test_making_the_mac_app_again_replaces_it(tmp_path):
    make_shortcut.make_mac_app(tmp_path)
    app = make_shortcut.make_mac_app(tmp_path)
    assert (app / "Contents" / "Info.plist").is_file()


# ----- Linux -----

def test_the_linux_entry_starts_vector_in_a_terminal(tmp_path):
    made = make_shortcut.make_linux_entry(tmp_path)
    entry = made.read_text(encoding="utf-8")
    assert entry.startswith("[Desktop Entry]\n")
    assert f'Exec="{ROOT / "Start VECTOR.sh"}"' in entry
    assert f"Icon={ICONS / 'vector-256.png'}" in entry
    assert "Terminal=true" in entry


# ----- Windows -----

@pytest.mark.skipif(not sys.platform.startswith("win"), reason="needs Windows")
def test_the_windows_shortcut_points_at_the_launcher_with_the_icon(tmp_path):
    made = make_shortcut.make_windows_shortcut(tmp_path)
    assert made == tmp_path / "VECTOR.lnk" and made.is_file()
    read = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
         "Write-Output $s.TargetPath; Write-Output $s.WorkingDirectory;"
         "Write-Output $s.IconLocation"],
        env={**__import__("os").environ, "LNK": str(made)},
        capture_output=True, text=True, timeout=60,
    ).stdout.splitlines()
    assert read[0] == str(ROOT / "Start VECTOR.bat")
    assert read[1] == str(ROOT)
    assert read[2] == f"{ICONS / 'vector.ico'},0"


def test_a_blocked_windows_shortcut_says_how_to_make_one_by_hand(monkeypatch):
    """An agency laptop may stop PowerShell making shortcuts."""
    def refuse(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 1, "", "Access is denied.")
    monkeypatch.setattr(make_shortcut.subprocess, "run", refuse)
    with pytest.raises(make_shortcut.ShortcutError) as caught:
        make_shortcut.make_windows_shortcut()
    message = str(caught.value)
    assert "Access is denied" in message
    assert "Send to" in message and "vector.ico" in message


def test_each_system_gets_its_own_kind(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(make_shortcut, "make_windows_shortcut", lambda d: calls.append("win"))
    monkeypatch.setattr(make_shortcut, "make_mac_app", lambda d: calls.append("mac"))
    monkeypatch.setattr(make_shortcut, "make_linux_entry", lambda d: calls.append("linux"))
    for platform in ("win32", "darwin", "linux"):
        make_shortcut.make_shortcut(tmp_path, platform=platform)
    assert calls == ["win", "mac", "linux"]
