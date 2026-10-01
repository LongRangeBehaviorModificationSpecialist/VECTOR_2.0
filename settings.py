#!/usr/bin/env python3

"""
settings.py

Settings that belong to this machine rather than to the case: whether
VECTOR listens on the network, and whether reports print the date and
time they were printed.

They are kept in db/settings.json rather than in the case database,
because they describe this installation. A database copied to another
machine should not carry that machine's network posture with it.

The file is read once at startup. The address a server listens on is
fixed when the socket opens, so changing this takes a restart -- which
is why the Admin Panel says so rather than pretending otherwise. When
network access is off, the port is not on the network at all: the
operating system refuses the connection, rather than VECTOR accepting
it and deciding.

Imports nothing from the rest of the application.
"""

import json
import socket

from program.config import Config, DB_DIR


SETTINGS_PATH = DB_DIR / "settings.json"

NETWORK_ACCESS = "network_access"
REPORT_PRINT_DATE = "report_print_date"
DEFAULTS = {NETWORK_ACCESS: False, REPORT_PRINT_DATE: False}

# Set at startup from what VECTOR actually bound to, so a page can say
# what is true now rather than what the setting says for next time.
_running_host = ""


def read() -> dict:
    """Every setting, with defaults for anything missing.

    A file that is missing, empty or damaged reads as the defaults: the
    safe end of each setting, and never a reason to refuse to start.
    """
    values = dict(DEFAULTS)
    try:
        stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return values
    if isinstance(stored, dict):
        for name in DEFAULTS:
            if name in stored:
                values[name] = stored[name]
    return values


def write(values: dict) -> None:
    """Saves the settings, leaving the old file alone until it works."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    nearly = SETTINGS_PATH.with_suffix(".json.writing")
    nearly.write_text(json.dumps(values, indent=2) + "\n", encoding="utf-8")
    nearly.replace(SETTINGS_PATH)


def network_access() -> bool:
    """Whether other devices are allowed to reach this machine."""
    return bool(read().get(NETWORK_ACCESS, False))


def set_network_access(allowed: bool) -> None:
    """Turns network access on or off for the next start."""
    values = read()
    values[NETWORK_ACCESS] = bool(allowed)
    write(values)


def report_print_date() -> bool:
    """Whether reports carry a "Report Printed Date" line. Off unless
    someone turns it on, on the Reports page."""
    return bool(read().get(REPORT_PRINT_DATE, False))


def set_report_print_date(on: bool) -> None:
    """Turns the "Report Printed Date" line on or off for every report."""
    values = read()
    values[REPORT_PRINT_DATE] = bool(on)
    write(values)


def host_to_bind(lan_flag: bool = False) -> str:
    """The address to listen on: every interface, or this machine only.

    The --lan flag still wins, so a shortcut or a launcher can open it
    for one run without changing what the machine does from then on.
    """
    if lan_flag or network_access():
        return "0.0.0.0"
    return Config.HOST


def note_running_host(host: str) -> None:
    """Records what VECTOR actually bound to, for the pages to report."""
    global _running_host
    _running_host = host


def reachable_now() -> bool:
    """Whether this run is actually reachable from other devices."""
    return _running_host == "0.0.0.0"


def machine_addresses() -> list:
    """This machine's addresses on the network, best guess first.

    Loopback and the 169.254 addresses Windows invents when there is no
    network are left out: neither is any use to a tablet.
    """
    found = set()

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None,
                                       socket.AF_INET):
            found.add(info[4][0])
    except OSError:
        pass

    # The address a route off this machine would leave from, which is
    # the one another device on the same network will reach. Connecting
    # a UDP socket sends nothing; the address is documentation-only.
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        found.add(probe.getsockname()[0])
    except OSError:
        pass
    finally:
        probe.close()

    return sorted(
        address for address in found
        if not address.startswith("127.")
        and not address.startswith("169.254.")
    )


def addresses_for_other_devices() -> list:
    """The whole address to type on a tablet, one per network address."""
    return [
        f"http://{address}:{Config.PORT}"
        for address in machine_addresses()
    ]
