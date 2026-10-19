#!/usr/bin/env python3

"""
make_shortcut.py — puts a VECTOR shortcut, with VECTOR's icon, on the
desktop, made the way each system makes its own.

    Windows   VECTOR.lnk, made with Windows' own shortcut maker
              (WScript.Shell, through PowerShell), using vector.ico.
    macOS     VECTOR.app: a small app that opens "Start VECTOR.command"
              in Terminal, using vector.icns. It is made on the Mac
              itself, so it is not a downloaded app.
    Linux     vector.desktop, on the desktop and in the applications
              menu, using vector-256.png.

The launchers offer this the first time they start; it can also be run
on its own, from the VECTOR folder:

    .venv\\Scripts\\python tools\\make_shortcut.py        (Windows)
    .venv/bin/python tools/make_shortcut.py             (macOS, Linux)

A shortcut holds the folder VECTOR was in when it was made, which is why
one cannot simply be shipped with VECTOR. Move the folder, and run this
again.

    --dest DIR   put the shortcut in DIR instead of on the desktop
"""

import argparse
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "static" / "icons"
NAME = "VECTOR"


class ShortcutError(Exception):
    """A shortcut could not be made; the message says what to do instead."""


# ----- Windows -----

# Paths reach PowerShell through the environment, never through the
# command line, so a folder name with quotes or spaces cannot break it.
_WINDOWS_SCRIPT = (
    "$ErrorActionPreference = 'Stop';"
    "$dest = $env:VECTOR_SHORTCUT_DEST;"
    "if (-not $dest) { $dest = [Environment]::GetFolderPath('Desktop') };"
    "$path = Join-Path $dest 'VECTOR.lnk';"
    "$link = (New-Object -ComObject WScript.Shell).CreateShortcut($path);"
    "$link.TargetPath = $env:VECTOR_SHORTCUT_TARGET;"
    "$link.WorkingDirectory = $env:VECTOR_SHORTCUT_FOLDER;"
    "$link.IconLocation = $env:VECTOR_SHORTCUT_ICON + ',0';"
    "$link.Description = 'Start VECTOR';"
    "$link.Save();"
    "Write-Output $path"
)

WINDOWS_BY_HAND = (
    'Make it by hand instead: right-click "Start VECTOR.bat", then Show more '
    "options, then Send to, Desktop (create shortcut). To give it VECTOR's "
    "icon, right-click the new shortcut, Properties, Change Icon, and choose "
    "static\\icons\\vector.ico in the VECTOR folder."
)


def make_windows_shortcut(dest: Path | None = None) -> Path:
    env = dict(os.environ)
    env.update({
        "VECTOR_SHORTCUT_TARGET": str(ROOT / "Start VECTOR.bat"),
        "VECTOR_SHORTCUT_FOLDER": str(ROOT),
        "VECTOR_SHORTCUT_ICON": str(ICONS / "vector.ico"),
        "VECTOR_SHORTCUT_DEST": str(dest) if dest else "",
    })
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", _WINDOWS_SCRIPT],
            env=env, capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise ShortcutError(f"Windows did not make the shortcut ({err}). {WINDOWS_BY_HAND}")
    if result.returncode != 0:
        # An agency laptop may block PowerShell from making shortcuts.
        reason = (result.stderr or result.stdout).strip().splitlines()
        raise ShortcutError(
            "Windows did not make the shortcut"
            + (f" ({reason[0]})" if reason else "")
            + f". {WINDOWS_BY_HAND}"
        )
    return Path(result.stdout.strip().splitlines()[-1])


# ----- macOS -----

MAC_BY_HAND = (
    'Make it by hand instead: right-click "Start VECTOR.command", then Make '
    "Alias, and drag the alias to the Desktop."
)


def mac_launcher_script(folder: Path) -> str:
    """What the app runs: open the launcher in Terminal, as a double-click
    on it does, so the VECTOR window appears as usual."""
    command = shlex.quote(str(folder / "Start VECTOR.command"))
    return (
        "#!/bin/bash\n"
        "# Made by tools/make_shortcut.py. Opens VECTOR in Terminal, as\n"
        "# double-clicking \"Start VECTOR.command\" does. If the VECTOR folder\n"
        "# moves, run tools/make_shortcut.py again.\n"
        f"exec open -a Terminal {command}\n"
    )


BUNDLE_ID = "local.vector.launcher"


def _made_by_us(app: Path) -> bool:
    """Whether an existing VECTOR.app is one this script made, and so
    one it may replace. Anything else of that name is left alone."""
    try:
        with open(app / "Contents" / "Info.plist", "rb") as plist:
            return plistlib.load(plist).get("CFBundleIdentifier") == BUNDLE_ID
    except (OSError, plistlib.InvalidFileException, ValueError):
        return False


def make_mac_app(dest: Path | None = None) -> Path:
    dest = dest or Path.home() / "Desktop"
    app = dest / f"{NAME}.app"
    contents = app / "Contents"
    if app.exists() and not _made_by_us(app):
        raise ShortcutError(
            f"There is already a {app.name} in {dest} that VECTOR did not "
            f"make, so it was left alone. {MAC_BY_HAND}"
        )
    try:
        if app.exists():
            shutil.rmtree(app)
        (contents / "MacOS").mkdir(parents=True)
        (contents / "Resources").mkdir()
        shutil.copyfile(ICONS / "vector.icns", contents / "Resources" / "vector.icns")
        executable = contents / "MacOS" / NAME
        executable.write_text(mac_launcher_script(ROOT), encoding="utf-8", newline="\n")
        executable.chmod(0o755)
        with open(contents / "Info.plist", "wb") as plist:
            plistlib.dump({
                "CFBundleName": NAME,
                "CFBundleDisplayName": NAME,
                "CFBundleIdentifier": BUNDLE_ID,
                "CFBundleExecutable": NAME,
                "CFBundleIconFile": "vector",
                "CFBundlePackageType": "APPL",
                "CFBundleInfoDictionaryVersion": "6.0",
                "LSMinimumSystemVersion": "11.0",
            }, plist)
    except OSError as err:
        raise ShortcutError(f"Could not make {app} ({err}). {MAC_BY_HAND}")
    return app


# ----- Linux -----

LINUX_BY_HAND = (
    'Start VECTOR with "Start VECTOR.sh" in the VECTOR folder, or copy '
    "vector.desktop from the applications menu by hand."
)


def _desktop_string(text: str) -> str:
    """A value as a .desktop file writes it: a backslash is doubled."""
    return text.replace("\\", "\\\\")


def _desktop_exec_argument(path: Path) -> str:
    """One quoted argument of an Exec line, by the Desktop Entry spec:
    inside the quotes " ` $ and \\ take a backslash; then the file's own
    string escaping doubles every backslash; and % is written %%. A
    folder named with any of these still starts VECTOR."""
    quoted = "".join("\\" + ch if ch in '"`$\\' else ch for ch in str(path))
    return '"' + _desktop_string(quoted).replace("%", "%%") + '"'


def linux_desktop_entry(folder: Path) -> str:
    launcher = folder / "Start VECTOR.sh"
    icon = folder / "static" / "icons" / "vector-256.png"
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={NAME}\n"
        "Comment=Start VECTOR\n"
        f"Exec={_desktop_exec_argument(launcher)}\n"
        f"Path={_desktop_string(str(folder))}\n"
        f"Icon={_desktop_string(str(icon))}\n"
        "Terminal=true\n"
        "Categories=Office;\n"
    )


def _linux_desktop_dir() -> Path:
    try:
        found = subprocess.run(["xdg-user-dir", "DESKTOP"],
                               capture_output=True, text=True, timeout=10)
        if found.returncode == 0 and found.stdout.strip():
            return Path(found.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return Path.home() / "Desktop"


def make_linux_entry(dest: Path | None = None) -> Path:
    entry = linux_desktop_entry(ROOT)
    targets = (
        [dest / "vector.desktop"] if dest else [
            _linux_desktop_dir() / "vector.desktop",
            Path.home() / ".local" / "share" / "applications" / "vector.desktop",
        ]
    )
    made = None
    for target in targets:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(entry, encoding="utf-8")
            target.chmod(0o755)
            made = made or target
        except OSError:
            continue
    if made is None:
        raise ShortcutError(f"Could not write vector.desktop. {LINUX_BY_HAND}")
    return made


# ----- Any system -----

def make_shortcut(dest: Path | None = None, platform: str = sys.platform) -> Path:
    """Makes the shortcut this system uses, and returns where it is."""
    if platform.startswith("win"):
        return make_windows_shortcut(dest)
    if platform == "darwin":
        return make_mac_app(dest)
    return make_linux_entry(dest)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Put a VECTOR shortcut on the desktop.")
    parser.add_argument("--dest", type=Path, help="folder to put it in, instead of the desktop")
    args = parser.parse_args(argv)
    try:
        made = make_shortcut(args.dest)
    except ShortcutError as err:
        print(f"\n{err}\n")
        return 1
    print(f"\nA VECTOR shortcut is ready: {made}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
