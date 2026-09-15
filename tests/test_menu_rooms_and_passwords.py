"""The top bar, rooms without agents, and imports that know whether a file
needs a password.

The row of page buttons filled a fifth of a phone's screen and appeared on
the login page, where every button led back to the login form; Shutdown
was offered to people the route refuses. A room saved without agents
could not be edited without assigning both. And importing an encrypted
export meant remembering to tick a box first.
"""

import tempfile

import pytest

import import_export
import navbar
import utils
from home_page import HELP_TEXT


@pytest.fixture
def out_dir(tmp_path, monkeypatch):
    """Where exports are written; staging goes in a private temp folder."""
    temp_root = tmp_path / "temp"
    temp_root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
    destination = tmp_path / "exports"
    destination.mkdir()
    return destination


# ----- The top bar -----
def test_the_row_and_the_menu_share_one_list_of_pages():
    routes = [route for _label, route in navbar.NAV_PAGES]
    for page in ["/", "/cases", "/agents", "/rooms", "/evidence",
                 "/persons", "/notes", "/uploads", "/links", "/reports"]:
        assert page in routes


def test_shutdown_is_offered_to_administrators_only():
    admin = [label for label, _route in navbar.account_menu(is_admin=True)]
    agent = [label for label, _route in navbar.account_menu(is_admin=False)]

    assert "Shutdown" in admin
    assert "Shutdown" not in agent
    assert agent == ["Logout"]


def test_administrators_keep_their_own_items():
    labels = [label for label, _route in navbar.account_menu(is_admin=True)]
    assert labels[:2] == ["Admin Panel", "Audit Trail"]


# ----- Rooms without agents -----
def test_a_room_without_agents_can_be_edited():
    assert utils.validate_room_entry(
        stage="update",
        ROOMLABEL="A",
        ROOMDESC="Front hall",
        ROOMFIRSTAGENT=None,
        ROOMSECONDAGENT=None,
    ) is False


def test_a_dropdown_saved_blank_opens_blank():
    """A blank dropdown is saved as "", which is never an option. NiceGUI
    refused it, so the edit dialog of a room without agents -- or of an
    item nobody triaged -- would not open."""
    from parts.crud import select_value

    assert select_value("") is None
    assert select_value(None) is None
    assert select_value("Doe, John") == "Doe, John"


@pytest.mark.parametrize("stage", ["initial", "update"])
def test_agents_are_still_assigned_as_a_pair(stage):
    assert utils.validate_room_entry(
        stage=stage,
        ROOMLABEL="A",
        ROOMDESC="Front hall",
        ROOMFIRSTAGENT="Doe, John",
        ROOMSECONDAGENT="",
    ) is True


# ----- Imports that know whether a file needs a password -----
def test_an_encrypted_csv_export_is_recognised(populated, out_dir):
    archive = import_export.export_vector_to_csv(
        password="correct horse battery", destination=out_dir)
    assert import_export.needs_password(archive) is True


def test_a_plain_csv_export_needs_no_password(populated, out_dir):
    archive = import_export.export_vector_to_csv(destination=out_dir)
    assert import_export.needs_password(archive) is False


def test_json_exports_are_recognised_either_way(populated, out_dir):
    plain = import_export.export_vector_to_json(destination=out_dir)
    sealed = import_export.export_vector_to_json(
        password="correct horse battery", destination=out_dir)

    assert import_export.needs_password(plain) is False
    assert import_export.needs_password(sealed) is True


def test_a_room_without_agents_survives_a_csv_round_trip(case, out_dir):
    """A room saved without agents holds "" in its required agent columns.
    The CSV import turned "" into None, so importing the case failed --
    found while checking the password prompt with such a room in the case."""
    from models import Rooms, get_session

    with get_session() as session:
        session.add(Rooms(ROOMLABEL="A", ROOMDESC="Garden shed",
                          ROOMFIRSTAGENT="", ROOMSECONDAGENT=""))
    archive = import_export.export_vector_to_csv(destination=out_dir)

    # Changed after the export, so a failed import cannot pass unnoticed:
    # imports are all or nothing, and a failure would leave this in place.
    with get_session() as session:
        session.query(Rooms).one().ROOMDESC = "changed since the export"

    import_export.import_vector_from_csv(str(archive))

    with get_session() as session:
        room = session.query(Rooms).one()
        assert (room.ROOMDESC, room.ROOMFIRSTAGENT, room.ROOMSECONDAGENT) \
            == ("Garden shed", "", "")


def test_a_damaged_file_is_left_for_the_importer_to_explain(tmp_path):
    bogus = tmp_path / "case.zip"
    bogus.write_text("not a zip archive")
    assert import_export.needs_password(bogus) is False


def test_the_help_page_matches_the_import_dialog():
    assert "tick the encryption box if it was" not in HELP_TEXT
    assert "VECTOR asks for it" in HELP_TEXT
