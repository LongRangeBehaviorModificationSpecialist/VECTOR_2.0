"""test_entry_edges.py

Small things about how an entry arrives: the spaces a tablet keyboard
leaves behind, the photograph format an iPhone saves in, and an agent
roster that cannot be written.
"""

from types import SimpleNamespace

import pytest

import utils
from models import Agents, get_session
from parts import agents_page
from parts.crud_widgets import _values_from


def _widgets(**values):
    return {name: SimpleNamespace(value=value) for name, value in values.items()}


# ----- Spaces around what was typed -----

def test_text_is_saved_without_the_spaces_around_it():
    """A tablet keyboard adds a space after every word it completes."""
    values = _values_from(_widgets(
        AGENTNAME="Doe, John ",
        AGENTNOTE="  searched the garage  ",
    ))
    assert values == {"AGENTNAME": "Doe, John", "AGENTNOTE": "searched the garage"}


def test_an_empty_field_is_saved_as_empty_text():
    assert _values_from(_widgets(EVIDTRIAGEDBY=None)) == {"EVIDTRIAGEDBY": ""}


def test_a_value_that_is_not_text_is_left_alone():
    assert _values_from(_widgets(FILESIZE=12)) == {"FILESIZE": 12}


# ----- Phone numbers -----

@pytest.mark.parametrize("typed, saved", [
    ("7035551234", "(703) 555-1234"),
    ("703-555-1234", "(703) 555-1234"),
    ("703.555.1234", "(703) 555-1234"),
    ("(703) 555-1234", "(703) 555-1234"),
    ("1-703-555-1234", "(703) 555-1234"),
    ("+1 703 555 1234", "(703) 555-1234"),
    ("703-555-1234 x12", "(703) 555-1234 x12"),
    ("703 555 1234 ext. 4021", "(703) 555-1234 x4021"),
    ("(703) 555-1234 extension 7", "(703) 555-1234 x7"),
])
def test_a_us_number_is_saved_one_way(typed, saved):
    assert utils.format_phone(typed) == saved


@pytest.mark.parametrize("typed", [
    "555-0101",              # seven digits: saved before the mask existed
    "+44 20 7946 0958",      # a foreign number
    "4021",                  # an internal line
    "703-555-CALL",          # letters
    "see dispatch",
])
def test_anything_else_is_kept_as_typed(typed):
    assert utils.format_phone(typed) == typed


def test_the_phone_field_takes_any_number_and_tidies_it_on_save():
    """A mask forced exactly ten digits: no extensions, no foreign
    numbers, and 555-0101 shown as "(555) 010-1" in the edit dialog."""
    phone = next(f for f in agents_page.SPEC.fields if f.name == "AGENTPHONE")
    assert "mask" not in phone.props
    assert phone.tidy is utils.format_phone
    values = _values_from(
        _widgets(AGENTPHONE=" 703 555 1234 x12 ", AGENTNAME="Doe, John"),
        agents_page.SPEC.fields,
    )
    assert values == {"AGENTPHONE": "(703) 555-1234 x12", "AGENTNAME": "Doe, John"}


def test_an_empty_phone_stays_empty():
    values = _values_from(_widgets(AGENTPHONE=""), agents_page.SPEC.fields)
    assert values == {"AGENTPHONE": ""}


def test_a_trailing_space_no_longer_makes_a_second_agent(case):
    """"Doe, John " passed the duplicate check beside "Doe, John", because
    the check trimmed and the save did not."""
    with get_session() as session:
        session.add(Agents(
            AGENTNAME="Doe, John",
            AGENTPARENTAGENCY="Virginia State Police",
            AGENTPRIMARYROLE="Searcher",
        ))

    values = _values_from(_widgets(
        AGENTNAME="Doe, John ",
        AGENTPARENTAGENCY="Virginia State Police",
        AGENTPRIMARYROLE="Searcher",
        AGENTROLESECONDARY="",
    ))
    refused = agents_page._validate(stage="initial", values=values, row=None)
    assert refused
    assert values["AGENTNAME"] == "Doe, John"


# ----- Photographs from an iPhone -----

@pytest.mark.parametrize("name, sent", [
    ("IMG_0412.HEIC", "image/heic"),
    ("IMG_0412.heic", ""),
    ("IMG_0412.HEIC", "application/octet-stream"),
    ("IMG_0413.heif", ""),
])
def test_an_iphone_photograph_is_accepted(name, sent):
    """HEIC, as the phone saves it, whether or not the browser names the
    type."""
    mime_type = utils.get_mime_type(name, sent)
    assert mime_type in ("image/heic", "image/heif")
    assert utils.is_allowed_file(mime_type)


def test_a_program_is_still_refused():
    assert not utils.is_allowed_file(utils.get_mime_type("setup.exe", ""))


# ----- The agent roster -----

def test_an_agent_roster_that_cannot_be_written_is_not_a_failed_save(
        monkeypatch):
    """The agent is already in the case when the roster is written. A
    read-only program folder raised here, which skipped the "added"
    message and left the form filled in, as though the save had failed."""
    def refuse(**_kwargs):
        raise PermissionError("read-only folder")

    monkeypatch.setattr(agents_page, "is_duplicate_agent_in_json",
                        lambda **_kwargs: False)
    monkeypatch.setattr(agents_page, "load_agents_from_json", lambda: [])
    monkeypatch.setattr(agents_page, "save_agent_to_json", refuse)

    agents_page._remember_agent({"AGENTNAME": "Doe, John"})
