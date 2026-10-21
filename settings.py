#!/usr/bin/env python3

"""
settings.py

Settings that belong to this machine rather than to the case: whether
VECTOR listens on the network, whether reports print the date and time
they were printed, whether the Agent List hides contact details, and
what Print All prints.

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
from dataclasses import dataclass

try:
    # Installed with NiceGUI, which uses it to list addresses at start-up.
    import ifaddr
except ImportError:  # pragma: no cover - only without NiceGUI's extras
    ifaddr = None

from program.config import Config, DB_DIR


SETTINGS_PATH = DB_DIR / "settings.json"

NETWORK_ACCESS = "network_access"
REPORT_PRINT_DATE = "report_print_date"
REDACT_AGENT_REPORT = "redact_agent_report"
PRINT_ALL = "print_all"

# What Print All on the Reports page prints, and how many copies of each:
# the reports a search normally ends with, the return copy twice -- one
# left at the premises, one kept. The keys are the reports' names in
# parts/reports_page.PRINT_ALL_REPORTS.
PRINT_ALL_DEFAULT = {
    "agents": 1,
    "rooms": 1,
    "evidence": 1,
    "evidence_by_room": 0,
    "evidence_basic": 2,
    "persons": 1,
    "notes": 0,
    "files": 0,
}
MAX_COPIES = 3

DEFAULTS = {
    NETWORK_ACCESS: False,
    REPORT_PRINT_DATE: False,
    REDACT_AGENT_REPORT: False,
    PRINT_ALL: PRINT_ALL_DEFAULT,
    }

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
    """Whether reports carry a "Report Printed Date" line.

    Off unless someone turns it on, on the Reports page.
    """
    return bool(read().get(REPORT_PRINT_DATE, False))


def set_report_print_date(on: bool) -> None:
    """Turns the "Report Printed Date" line on or off for every report."""
    values = read()
    values[REPORT_PRINT_DATE] = bool(on)
    write(values)


def redact_agent_report() -> bool:
    """Whether the Agent List report hides each agent's phone and email.

    Off unless someone turns it on, on the Reports page.
    """
    return bool(read().get(REDACT_AGENT_REPORT, False))


def set_redact_agent_report(on: bool) -> None:
    """Turns redaction of the Agent List report on or off."""
    values = read()
    values[REDACT_AGENT_REPORT] = bool(on)
    write(values)


def _copies(value) -> int | None:
    """A number of copies, or None when it is not one."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if 0 <= value <= MAX_COPIES else None


def print_all_copies() -> dict[str, int]:
    """How many copies of each report Print All prints; 0 leaves it out.

    Anything unreadable in the file falls back to the default for that
    report, so a damaged setting never stops the printing.
    """
    stored = read().get(PRINT_ALL)
    copies = dict(PRINT_ALL_DEFAULT)
    if isinstance(stored, dict):
        for name in copies:
            number = _copies(stored.get(name))
            if number is not None:
                copies[name] = number
    return copies


def set_print_all_copies(copies: dict[str, int]) -> None:
    """Saves what Print All prints. Unknown reports are ignored."""
    current = print_all_copies()
    for name, number in copies.items():
        number = _copies(number)
        if name in current and number is not None:
            current[name] = number
    values = read()
    values[PRINT_ALL] = current
    write(values)


def host_to_bind(lan_flag: bool = False) -> str:
    """The address to listen on: every interface, or this machine only.

    The `--lan` flag still wins, so a shortcut or a launcher can open it
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


# ----- The address to type -----
# A computer has an address for every network adapter it has, and most
# have more than one: Wi-Fi and a cable, and on a laptop that runs VMware,
# Hyper-V, WSL, Docker or a VPN, a virtual adapter for each of them --
# networks that exist only inside this machine. VECTOR listens on all of
# them, and NiceGUI used to print every one at start-up, so a tablet user
# was handed half a dozen addresses of which one worked. The adapter
# names say which are which.

# Names of adapters no other device can reach. Matched without regard to
# case, anywhere in the adapter's name: on Windows that is the adapter's
# description ("VMware Virtual Ethernet Adapter for VMnet8"), on macOS
# and Linux its interface name ("vmnet8", "utun3", "docker0").
_VIRTUAL_ADAPTERS = (
    "vmware", "vmnet", "virtualbox", "vboxnet", "hyper-v", "vethernet",
    "wsl", "docker", "virbr", "veth", "vnic", "parallels", "tailscale",
    "zerotier", "wireguard", "hamachi", "tap-", "utun", "tun0", "tun1",
    "vpn", "loopback", "npcap", "bluetooth", "br-",
    # The VPN clients agencies issue, whose adapters say who made them
    # rather than that they are VPNs.
    "anyconnect", "pangp", "globalprotect", "fortinet", "juniper",
    "pulse secure", "f5 ", "openvpn", "nordlynx", "virtual miniport",
)

# Tunnels: a VPN can carry the default route, and its address is still no
# use to a tablet. A hypervisor's adapter can carry it too -- Hyper-V's
# external switch puts the real network on "vEthernet (...)" -- and then
# it is the real network, so only tunnels are refused the main place.
_TUNNEL_ADAPTERS = (
    "vpn", "utun", "tun0", "tun1", "tap-", "wireguard", "tailscale",
    "zerotier", "hamachi", "anyconnect", "pangp", "globalprotect",
    "fortinet", "juniper", "pulse secure", "f5 ", "openvpn", "nordlynx",
    "virtual miniport",
)

# This laptop's own hotspot, which tablets join directly: Windows' Mobile
# Hotspot runs on a "Wi-Fi Direct Virtual Adapter" at 192.168.137.1, and
# macOS Internet Sharing on bridge100.
_HOTSPOT_ADAPTERS = ("wi-fi direct", "hosted network", "bridge100")
WINDOWS_HOTSPOT_ADDRESS = "192.168.137.1"

# The kinds of address, in the order they are offered.
MAIN, HOTSPOT, OTHER, VIRTUAL = "main", "hotspot", "other", "virtual"
_ORDER = (MAIN, HOTSPOT, OTHER, VIRTUAL)


@dataclass(frozen=True)
class NetworkAddress:
    address: str
    adapter: str
    kind: str

    @property
    def url(self) -> str:
        return f"http://{self.address}:{Config.PORT}"


def _adapter_addresses() -> list:
    """(adapter name, address) for every IPv4 address on this machine."""
    found = []
    if ifaddr is not None:
        try:
            for adapter in ifaddr.get_adapters():
                for ip in adapter.ips:
                    if ip.is_IPv4:
                        found.append((
                            adapter.nice_name or adapter.name,
                            str(ip.ip)
                        ))
        except Exception:
            found = []
    if not found:
        try:
            for info in socket.getaddrinfo(
                    socket.gethostname(),
                    None,
                    socket.AF_INET):
                found.append(("", info[4][0]))
        except OSError:
            pass
    return found


def _route_address() -> str:
    """The address traffic leaves this machine from, or "" if none.

    That is the adapter carrying the default route -- the network this
    machine is on, which a tablet on the same network can reach.
    Connecting a UDP socket sends nothing; 192.0.2.1 is reserved for
    documentation and never answers.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))
        return probe.getsockname()[0]
    except OSError:
        return ""
    finally:
        probe.close()


def classify_addresses(found: list, route: str) -> list:
    """Sorts (adapter, address) pairs into NetworkAddress, best first.

    Loopback and the 169.254 addresses an adapter gives itself when it
    has no network are left out: neither is any use to a tablet. Kept
    apart from the lookups so the rule can be tested on any machine.
    """
    addresses = {}
    for adapter, address in found:
        if address.startswith("127.") or address.startswith("169.254."):
            continue
        name = (adapter or "").lower()
        if address == route and not any(
            hint in name for hint in _TUNNEL_ADAPTERS
        ):
            kind = MAIN
        elif any(hint in name for hint in _HOTSPOT_ADAPTERS) or (
            address == WINDOWS_HOTSPOT_ADDRESS
        ):
            kind = HOTSPOT
        elif any(hint in name for hint in _VIRTUAL_ADAPTERS):
            kind = VIRTUAL
        else:
            kind = OTHER
        # One entry per address, keeping the most useful reading of it.
        held = addresses.get(address)
        if held is None or _ORDER.index(kind) < _ORDER.index(held.kind):
            addresses[address] = NetworkAddress(address, adapter or "", kind)
    if route and route not in addresses and not route.startswith(
        ("127.", "169.254.")
    ):
        addresses[route] = NetworkAddress(route, "", MAIN)

    return sorted(
        addresses.values(),
        key=lambda item: (_ORDER.index(item.kind), item.address),
    )


def network_addresses() -> list:
    """Every address on this machine, as NetworkAddress, best first."""
    return classify_addresses(_adapter_addresses(), _route_address())


def machine_addresses() -> list:
    """The addresses another device could use, best first: the network
    this machine is on, then its own hotspot, then any other real
    adapter. Virtual adapters are left out."""
    return [
        item.address for item in network_addresses() if item.kind != VIRTUAL
    ]


def addresses_for_other_devices() -> list:
    """The whole address to type on a tablet, best first."""
    return [
        f"http://{address}:{Config.PORT}"
        for address in machine_addresses()
    ]
