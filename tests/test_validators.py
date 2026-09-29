"""
test_validators.py

Each returns True when the entry is INVALID and submission should stop.
Several used to raise UnboundLocalError instead, because they assigned
inside "if" guards and then read unconditionally -- so an untouched
dropdown crashed the save rather than reporting a missing field.
"""

from models import Cases, get_session
import utils


# ----- the crash paths -----

def test_evidence_missing_room_is_reported_not_raised():
    assert utils.validate_evid_entry(
        stage="initial",
        EVIDNUM="1",
        EVIDQTY="1",
        EVIDDESC="Laptop",
        EVIDLOCROOM=None,
        EVIDLOCROOMDETAIL=None,
        EVIDFOUNDBY="Doe, John",
        EVIDFOUNDBYWITNESS="Roe, Jane",
    ) is True


def test_person_missing_note_is_reported_not_raised():
    assert utils.validate_person_data(
        stage="initial",
        PERSONNAME="Doe, John",
        PERSONNOTE=None,
    ) is True


def test_case_missing_jurisdiction_is_reported_not_raised():
    assert utils.validate_case_entry(
        stage="initial",
        CASENUMBER="26-1",
        LOCATION="14 Elm Street",
        JURISDICTION=None,
        CASEDATETIMEBEGIN="09-10-2026 08:00",
    ) is True


def test_agent_missing_agency_is_reported_not_raised():
    assert utils.validate_agent_entry(
        stage="initial",
        AGENTNAME="Doe, John",
        AGENTPARENTAGENCY=None,
        AGENTPRIMARYROLE="Searcher",
    ) is True


def test_note_missing_text_is_reported_not_raised():
    assert utils.validate_note_data(
        NOTEAUTHOR="Doe, John",
        NOTETEXT=None,
    ) is True


# ----- the rules that should pass -----

def test_complete_case_is_accepted():
    assert utils.validate_case_entry(
        stage="initial",
        CASENUMBER="26-1",
        LOCATION="14 Elm Street",
        JURISDICTION="Fairfax County",
        CASEDATETIMEBEGIN="09-10-2026 08:00",
    ) is False


def test_complete_evidence_is_accepted():
    assert utils.validate_evid_entry(
        stage="initial",
        EVIDNUM="1",
        EVIDQTY="1",
        EVIDDESC="Laptop",
        EVIDLOCROOM="Room A (Bedroom)",
        EVIDLOCROOMDETAIL="closet shelf",
        EVIDFOUNDBY="Doe, John",
        EVIDFOUNDBYWITNESS="Roe, Jane",
    ) is False


def test_room_agents_may_both_be_blank_on_first_entry():
    """Both-or-neither: a room can be defined before it is assigned."""
    assert utils.validate_room_entry(
        stage="initial",
        ROOMLABEL="A",
        ROOMDESC="Bedroom",
        ROOMFIRSTAGENT=None,
        ROOMSECONDAGENT=None,
    ) is False


# ----- the domain rules worth protecting -----

def test_finder_cannot_also_be_the_witness():
    assert utils.validate_evid_entry(
        stage="initial",
        EVIDNUM="1",
        EVIDQTY="1",
        EVIDDESC="Laptop",
        EVIDLOCROOM="Room A",
        EVIDLOCROOMDETAIL="shelf",
        EVIDFOUNDBY="Doe, John",
        EVIDFOUNDBYWITNESS="Doe, John",
    ) is True


def test_one_agent_cannot_hold_both_room_positions():
    assert utils.validate_room_entry(
        stage="initial",
        ROOMLABEL="A",
        ROOMDESC="Bedroom",
        ROOMFIRSTAGENT="Doe, John",
        ROOMSECONDAGENT="Doe, John",
    ) is True


def test_triaged_item_requires_who_triaged_it():
    assert utils.validate_evid_entry(
        stage="initial",
        EVIDNUM="1",
        EVIDQTY="1",
        EVIDDESC="Laptop",
        EVIDLOCROOM="Room A",
        EVIDLOCROOMDETAIL="shelf",
        EVIDFOUNDBY="Doe, John",
        EVIDFOUNDBYWITNESS="Roe, Jane",
        EVIDTRIAGED="Yes",
        EVIDTRIAGEDBY="",
    ) is True


def test_agent_primary_and_secondary_roles_must_differ():
    assert utils.validate_agent_entry(
        stage="initial",
        AGENTNAME="Doe, John",
        AGENTPARENTAGENCY="Virginia State Police",
        AGENTPRIMARYROLE="Searcher",
        AGENTROLESECONDARY="Searcher",
    ) is True


def test_duplicate_case_number_is_rejected(case):
    """Only reachable on a database that already holds two cases, from
    before one case at a time was enforced.
    """
    with get_session() as session:
        second = Cases(
            CASENUMBER="26-000002",
            LOCATION="Somewhere else",
            JURISDICTION="Fairfax County",
            CASEDATETIMEBEGIN="09-11-2026 08:00",
        )
        session.add(second)
        session.flush()
        second_pk = second.Z_PK

    assert utils.validate_case_entry(
        stage="update",
        CASENUMBER=case,
        LOCATION="Somewhere else",
        JURISDICTION="Fairfax County",
        CASEDATETIMEBEGIN="09-11-2026 08:00",
        row={"Z_PK": second_pk},
    ) is True


# ----- one case at a time -----

def test_a_second_case_cannot_be_opened(case, monkeypatch):
    """Reports read the first case only, so a second would be recorded
    and never printed."""
    notices = []
    monkeypatch.setattr(
        utils.ui,
        "notify",
        lambda message,
        **kw: notices.append(str(message))
    )

    assert utils.validate_case_entry(
        stage="initial",
        CASENUMBER="26-999999",
        LOCATION="Somewhere else",
        JURISDICTION="Fairfax County",
        CASEDATETIMEBEGIN="09-11-2026 08:00",
    ) is True
    assert any(case in text and "Start New Case" in text for text in notices)


def test_the_open_case_can_still_be_edited(case):
    with get_session() as session:
        pk = session.query(Cases).one().Z_PK

    assert utils.validate_case_entry(
        stage="update",
        CASENUMBER=case,
        LOCATION="14 Elm Street, Apt 4",
        JURISDICTION="Fairfax County",
        CASEDATETIMEBEGIN="09-10-2026 08:00",
        row={"Z_PK": pk},
    ) is False


def test_duplicate_evidence_number_is_rejected(populated):
    assert utils.validate_evid_entry(
        stage="initial",
        EVIDNUM="1",
        EVIDQTY="1",
        EVIDDESC="Another laptop",
        EVIDLOCROOM="Room A",
        EVIDLOCROOMDETAIL="shelf",
        EVIDFOUNDBY="Doe, John",
        EVIDFOUNDBYWITNESS="Roe, Jane",
    ) is True
