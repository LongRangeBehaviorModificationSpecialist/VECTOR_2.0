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
