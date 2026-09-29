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
