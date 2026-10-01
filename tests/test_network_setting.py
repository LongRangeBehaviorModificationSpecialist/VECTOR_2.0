"""Whether VECTOR listens on the network, and the address to type.

The setting decides what this machine does from the next start onwards;
--lan still opens it for one run. Both answers matter more than most:
with it off, the port is not on the network at all.
"""

import pytest

import settings
import utils
from models import AuditLog, get_session
from program.config import Config


@pytest.fixture(autouse=True)
def settings_file(tmp_path, monkeypatch):
    """Each test gets its own settings file, never the real db/ one."""
    monkeypatch.setattr(settings, "SETTINGS_PATH", tmp_path / "settings.json")
    yield tmp_path / "settings.json"


# ----- Reading and writing -----

def test_network_access_is_off_until_somebody_turns_it_on():
    """A fresh install is not on the network, and a missing file is a
    fresh install."""
    assert settings.network_access() is False


def test_the_setting_survives_being_written(settings_file):
    settings.set_network_access(True)
    assert settings_file.is_file()
    assert settings.network_access() is True

    settings.set_network_access(False)
    assert settings.network_access() is False


def test_a_damaged_settings_file_reads_as_off(settings_file):
    settings_file.write_text("{not json at all", encoding="utf-8")
    assert settings.network_access() is False
    assert settings.read() == settings.DEFAULTS


def test_an_unrelated_setting_is_left_alone(settings_file):
    settings_file.write_text('{"something_else": 42}', encoding="utf-8")
    settings.set_network_access(True)

    import json
    stored = json.loads(settings_file.read_text(encoding="utf-8"))
    assert stored["network_access"] is True


# ----- What it binds to -----

def test_the_flag_opens_it_for_one_run():
    assert settings.network_access() is False
    assert settings.host_to_bind(lan_flag=True) == "0.0.0.0"


def test_the_setting_opens_it_from_then_on():
    settings.set_network_access(True)
    assert settings.host_to_bind(lan_flag=False) == "0.0.0.0"


def test_with_neither_it_listens_to_this_machine_only():
    assert settings.host_to_bind(lan_flag=False) == Config.HOST
    assert Config.HOST != "0.0.0.0"


def test_what_is_true_now_is_what_it_bound_to():
    """The setting says what happens next time; this says what happened."""
    settings.note_running_host("127.0.0.1")
    assert settings.reachable_now() is False

    settings.note_running_host("0.0.0.0")
    assert settings.reachable_now() is True


# ----- The address to type -----

def test_the_address_is_one_a_tablet_could_use():
    for address in settings.machine_addresses():
        assert not address.startswith("127."), address
        assert not address.startswith("169.254."), address
        assert len(address.split(".")) == 4, address


def test_the_address_is_given_whole():
    """A number on its own is something a browser searches for."""
    for url in settings.addresses_for_other_devices():
        assert url.startswith("http://")
        assert url.endswith(f":{Config.PORT}")


# ----- Which of the machine's addresses to give -----
# Adapter names as Windows reports them, and as macOS and Linux do.
WIFI = "Intel(R) Wi-Fi 6 AX201 160MHz"
CABLE = "Realtek PCIe GbE Family Controller"
VMNET8 = "VMware Virtual Ethernet Adapter for VMnet8"
WSL = "vEthernet (WSL (Hyper-V firewall))"
VPN = "Cisco AnyConnect Secure Mobility Client Virtual Miniport Adapter"
HOTSPOT = "Microsoft Wi-Fi Direct Virtual Adapter #2"


def _kinds(found, route):
    return [(a.address, a.kind)
            for a in settings.classify_addresses(found, route)]


def test_the_network_this_computer_is_on_comes_first():
    """A laptop with VMware and WSL has three addresses; one of them is
    on the network a tablet can join. Sorted as text, WSL's 172.x came
    first and the page said the first was usually the one."""
    found = [(VMNET8, "192.168.88.1"), (WSL, "172.20.16.1"),
             (WIFI, "192.168.1.23")]
    assert _kinds(found, route="192.168.1.23") == [
        ("192.168.1.23", "main"),
        ("172.20.16.1", "virtual"),
        ("192.168.88.1", "virtual"),
    ]


def test_virtual_adapters_are_not_offered():
    found = [(VMNET8, "192.168.88.1"), (WIFI, "192.168.1.23")]
    addresses = [a.address for a in settings.classify_addresses(
        found, "192.168.1.23") if a.kind != settings.VIRTUAL]
    assert addresses == ["192.168.1.23"]


def test_a_vpn_carrying_the_route_is_not_the_address_to_give():
    """With a VPN connected, traffic leaves through the tunnel -- but a
    tablet on the Wi-Fi still reaches the Wi-Fi address."""
    found = [(VPN, "10.8.0.14"), (WIFI, "192.168.1.23")]
    assert _kinds(found, route="10.8.0.14") == [
        ("192.168.1.23", "other"),
        ("10.8.0.14", "virtual"),
    ]


def test_hyper_v_carrying_the_real_network_is_the_main_address():
    """Hyper-V's external switch moves the real network onto a vEthernet
    adapter. It carries the route, so it is the one to give."""
    found = [("vEthernet (External Switch)", "192.168.1.23")]
    assert _kinds(found, route="192.168.1.23") == [("192.168.1.23", "main")]


@pytest.mark.parametrize("adapter", [
    "PANGP Virtual Ethernet Adapter",
    "Fortinet SSL VPN Virtual Ethernet Adapter",
    "TAP-Windows Adapter V9",
    "WireGuard Tunnel",
])
def test_agency_vpn_clients_are_recognised(adapter):
    found = [(adapter, "10.8.0.14"), (WIFI, "192.168.1.23")]
    assert _kinds(found, route="10.8.0.14")[0] == ("192.168.1.23", "other")


def test_this_laptops_own_hotspot_is_offered_after_the_main_network():
    found = [(HOTSPOT, "192.168.137.1"), (WIFI, "192.168.1.23")]
    assert _kinds(found, route="192.168.1.23") == [
        ("192.168.1.23", "main"),
        ("192.168.137.1", "hotspot"),
    ]


def test_a_second_real_adapter_is_offered_after_the_main_one():
    found = [(CABLE, "10.0.0.5"), (WIFI, "192.168.1.23")]
    assert _kinds(found, route="192.168.1.23") == [
        ("192.168.1.23", "main"),
        ("10.0.0.5", "other"),
    ]


def test_loopback_and_self_assigned_addresses_are_left_out():
    found = [("Software Loopback Interface 1", "127.0.0.1"),
             (CABLE, "169.254.10.20"), (WIFI, "192.168.1.23")]
    assert _kinds(found, route="192.168.1.23") == [("192.168.1.23", "main")]


def test_without_a_route_the_real_adapters_still_come_first():
    """No default route -- a hotspot with no internet, say."""
    found = [(VMNET8, "192.168.88.1"), (WIFI, "192.168.43.7")]
    assert _kinds(found, route="") == [
        ("192.168.43.7", "other"),
        ("192.168.88.1", "virtual"),
    ]


def test_macos_and_linux_interface_names_are_recognised():
    found = [("en0", "192.168.1.23"), ("vmnet8", "172.16.5.1"),
             ("utun3", "10.8.0.2"), ("docker0", "172.17.0.1"),
             ("bridge100", "192.168.2.1")]
    assert _kinds(found, route="192.168.1.23") == [
        ("192.168.1.23", "main"),
        ("192.168.2.1", "hotspot"),
        ("10.8.0.2", "virtual"),
        ("172.16.5.1", "virtual"),
        ("172.17.0.1", "virtual"),
    ]


def test_the_route_address_is_kept_when_no_adapter_lists_it():
    assert _kinds([], route="192.168.1.23") == [("192.168.1.23", "main")]


def test_an_address_listed_twice_appears_once():
    found = [("", "192.168.1.23"), (WIFI, "192.168.1.23")]
    assert _kinds(found, route="192.168.1.23") == [("192.168.1.23", "main")]


# ----- The record of the change -----

def test_turning_it_on_is_recorded_with_who_did_it():
    utils.set_network_access(True, actor="Doe, John")

    with get_session() as session:
        entry = (
            session.query(AuditLog)
            .filter(AuditLog.action == "SETTING_CHANGED")
            .one()
        )
        assert entry.actor == "Doe, John"
        assert "network access turned on" in entry.summary
        assert "next start" in entry.summary
        assert '"network_access": false' in (entry.before or "").lower()
        assert '"network_access": true' in (entry.after or "").lower()


def test_turning_it_off_is_recorded_too():
    utils.set_network_access(True, actor="admin")
    utils.set_network_access(False, actor="admin")

    with get_session() as session:
        summaries = [
            row.summary
            for row in session.query(AuditLog)
            .filter(AuditLog.action == "SETTING_CHANGED")
            .order_by(AuditLog.id)
        ]
    assert len(summaries) == 2
    assert "turned off" in summaries[1]


def test_the_change_reaches_the_setting_itself():
    utils.set_network_access(True, actor="admin")
    assert settings.network_access() is True
