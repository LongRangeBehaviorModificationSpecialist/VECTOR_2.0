"""
conftest.py

Shared test fixtures.

VECTOR_DB_DIR is set before anything imports program.config, so the whole
suite works against a temporary database and never touches db/.
"""

import os
import sys
import tempfile
from pathlib import Path

# Must happen before the first import of program.config, which resolves
# DB_DIR at import time.
_TEST_DB_DIR = Path(tempfile.mkdtemp(prefix="vector_tests_"))
os.environ["VECTOR_DB_DIR"] = str(_TEST_DB_DIR)
os.environ.setdefault("VECTOR_NO_BROWSER", "1")

# Allow "import models" etc. when pytest is run from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402

import models  # noqa: E402
from models import (  # noqa: E402
    Agents,
    AuditLog,
    Cases,
    Evidence,
    Notes,
    Persons,
    Rooms,
    UploadedFiles,
    get_session,
)


ALL_MODELS = (
    Evidence,
    Notes,
    Persons,
    Rooms,
    Agents,
    Cases,
    UploadedFiles,
    AuditLog,
)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Builds the schema once for the whole run."""
    models.Base.metadata.create_all(models.engine)
    models.UsersBase.metadata.create_all(models.users_engine)
    yield


@pytest.fixture(autouse=True)
def clean_database():
    """Empties every table between tests so they cannot leak into each
    other.

    Uses bulk deletes, which do not raise ORM events -- so clearing up
    does not itself write audit rows.
    """
    with get_session() as session:
        for model in ALL_MODELS:
            session.query(model).delete()
    yield
    with get_session() as session:
        for model in ALL_MODELS:
            session.query(model).delete()


@pytest.fixture
def case():
    """A minimal active case, as every report needs one."""
    with get_session() as session:
        session.add(
            Cases(
                CASENUMBER="26-004711",
                LOCATION="14 Elm Street, Apt 3",
                JURISDICTION="Fairfax County",
                CASEDATETIMEBEGIN="09-10-2026 08:00",
                CASEDATETIMEEND="09-10-2026 16:30",
            )
        )
    return "26-004711"


@pytest.fixture
def populated(case):
    """A case with two agents, two rooms, evidence, a person and a note.

    Deliberately includes values that break naive HTML interpolation and
    values that used to hit unique constraints.
    """
    with get_session() as session:
        session.add_all(
            [
                Agents(
                    AGENTNAME="Doe, John",
                    AGENTPARENTAGENCY="Virginia State Police",
                    AGENTPRIMARYROLE="Searcher",
                    AGENTPHONE="",
                    AGENTEMAIL="",
                ),
                Agents(
                    AGENTNAME="Roe, Jane",
                    AGENTPARENTAGENCY="Fairfax County Police",
                    AGENTPRIMARYROLE="Photographer",
                    AGENTPHONE="",
                    AGENTEMAIL="",
                ),
                Rooms(
                    ROOMLABEL="A",
                    ROOMDESC="Bedroom",
                    ROOMFIRSTAGENT="Doe, John",
                    ROOMSECONDAGENT="Roe, Jane",
                ),
                Rooms(
                    ROOMLABEL="B",
                    ROOMDESC="Bedroom",
                    ROOMFIRSTAGENT="Doe, John",
                    ROOMSECONDAGENT="Roe, Jane",
                ),
                Persons(
                    PERSONNAME="O'Brien, Sean",
                    PERSONDOB="03-02-1984",
                    PERSONADDRESS="14 Elm Street",
                ),
                Notes(
                    NOTEDATETIME="2026-09-10 08:05",
                    NOTEAUTHOR="Doe, John",
                    NOTETEXT="Entry made & premises secured <no incident>",
                ),
            ]
        )
        for number in range(1, 13):
            session.add(
                Evidence(
                    EVIDNUM=str(number),
                    EVIDQTY="1",
                    EVIDDESC=f"Smith & Wesson <item {number}>",
                    EVIDLOCROOM="Room A (Bedroom)",
                    EVIDLOCROOMDETAIL="closet shelf",
                    EVIDFOUNDBY="Doe, John",
                    EVIDFOUNDBYWITNESS="Roe, Jane",
                )
            )
    return case
