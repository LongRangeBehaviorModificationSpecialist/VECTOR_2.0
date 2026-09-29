"""
test_constraints.py

Database constraints.

Three unique constraints used to reject situations that occur on most
warrants. Four others are real identity rules and must stay.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from models import (
    Agents,
    Evidence,
    Persons,
    Rooms,
    UploadedFiles,
    get_session,
)


def _agent(name, phone="", email=""):
    return Agents(
        AGENTNAME=name,
        AGENTPARENTAGENCY="Virginia State Police",
        AGENTPRIMARYROLE="Searcher",
        AGENTPHONE=phone,
        AGENTEMAIL=email,
    )


def _room(label, desc):
    return Rooms(
        ROOMLABEL=label,
        ROOMDESC=desc,
        ROOMFIRSTAGENT="Doe, John",
        ROOMSECONDAGENT="Roe, Jane",
    )


# ----- constraints that had to go -----

def test_two_agents_can_share_a_blank_email():
    with get_session() as session:
        session.add_all([_agent("Doe, John"), _agent("Roe, Jane")])

    with get_session() as session:
        assert session.query(Agents).count() == 2


def test_two_agents_can_share_a_blank_phone():
    with get_session() as session:
        session.add_all(
            [
                _agent("Doe, John", email="a@b.gov"),
                _agent("Roe, Jane", email="c@d.gov"),
            ]
        )
    with get_session() as session:
        assert session.query(Agents).count() == 2


def test_a_house_can_have_two_bedrooms():
    with get_session() as session:
        session.add_all([_room("A", "Bedroom"), _room("B", "Bedroom")])

    with get_session() as session:
        assert session.query(Rooms).count() == 2


def test_the_same_photograph_can_be_attached_twice():
    payload = b"\xff\xd8\xff\xe0identical-bytes"
    with get_session() as session:
        for name in ("front.jpg", "back.jpg"):
            session.add(
                UploadedFiles(
                    FILENAME=name,
                    FILESIZE=len(payload),
                    FILEMIMETYPE="image/jpeg",
                    FILEUPLOADEDBY="Doe, John",
                    FILEDATA=payload,
                )
            )
    with get_session() as session:
        assert session.query(UploadedFiles).count() == 2


# ----- constraints that must stay -----

def test_agent_names_stay_unique():
    with get_session() as session:
        session.add(_agent("Doe, John"))

    with pytest.raises(IntegrityError):
        with get_session() as session:
            session.add(_agent("Doe, John", email="other@vsp.gov"))


def test_room_labels_stay_unique():
    with get_session() as session:
        session.add(_room("A", "Bedroom"))

    with pytest.raises(IntegrityError):
        with get_session() as session:
            session.add(_room("A", "Kitchen"))


def test_evidence_numbers_stay_unique():
    def item(number, desc):
        return Evidence(
            EVIDNUM=number,
            EVIDQTY="1",
            EVIDDESC=desc,
            EVIDLOCROOM="Room A",
            EVIDLOCROOMDETAIL="shelf",
            EVIDFOUNDBY="Doe, John",
            EVIDFOUNDBYWITNESS="Roe, Jane",
        )

    with get_session() as session:
        session.add(item("1", "Laptop"))

    with pytest.raises(IntegrityError):
        with get_session() as session:
            session.add(item("1", "Phone"))


def test_person_names_stay_unique():
    with get_session() as session:
        session.add(Persons(PERSONNAME="O'Brien, Sean"))

    with pytest.raises(IntegrityError):
        with get_session() as session:
            session.add(Persons(PERSONNAME="O'Brien, Sean"))
