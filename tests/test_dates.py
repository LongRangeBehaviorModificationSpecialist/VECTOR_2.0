"""Date format.

Case times and dates of birth are entered as MM-DD-YYYY. A value stored
earlier as YYYY-MM-DD would be scrambled by the input mask the first time
someone edited it, so such values are rewritten once -- and only values
in exactly that old format.
"""

import json

import pytest

import models
import parts.cases_page as cases_page
from models import AuditLog, Cases, Persons, get_session


def _add_case(begin, end=None):
    with get_session() as session:
        session.add(
            Cases(
                CASENUMBER="26-1",
                LOCATION="14 Elm Street",
                JURISDICTION="Fairfax County",
                CASEDATETIMEBEGIN=begin,
                CASEDATETIMEEND=end,
            )
        )


def _stored_case_times():
    with get_session() as session:
        case = session.query(Cases).one()
        return case.CASEDATETIMEBEGIN, case.CASEDATETIMEEND


def test_case_times_are_entered_month_first():
    for name in ("CASEDATETIMEBEGIN", "CASEDATETIMEEND"):
        field = next(f for f in cases_page.SPEC.fields if f.name == name)
        assert field.placeholder == "MM-DD-YYYY HH:MM"
        assert 'mask="##-##-#### ##:##"' in field.props


def test_old_case_times_are_rewritten():
    _add_case("2026-09-10 08:00", "2026-09-10 16:30")
    assert models.normalise_legacy_dates() == 2
    assert _stored_case_times() == ("09-10-2026 08:00", "09-10-2026 16:30")


def test_old_birth_dates_are_rewritten():
    with get_session() as session:
        session.add(
            Persons(PERSONNAME="O'Brien, Sean", PERSONDOB="1984-03-02")
        )
    assert models.normalise_legacy_dates() == 1
    with get_session() as session:
        assert session.query(Persons).one().PERSONDOB == "03-02-1984"


@pytest.mark.parametrize(
    "value",
    [
        "09-10-2026 16:30",
        "2026-09-10T16:30",
        "2026-09-10",
        "10 Sept 2026 16:30",
        "",
        None,
    ],
)
def test_anything_else_is_left_alone(value):
    _add_case("09-10-2026 08:00", value)
    assert models.normalise_legacy_dates() == 0
    assert _stored_case_times() == ("09-10-2026 08:00", value)


def test_the_rewrite_happens_once():
    _add_case("2026-09-10 08:00")
    models.normalise_legacy_dates()
    assert models.normalise_legacy_dates() == 0


def test_each_rewrite_reaches_the_audit_trail():
    _add_case("2026-09-10 08:00")
    models.normalise_legacy_dates()

    with get_session() as session:
        updates = session.query(AuditLog).filter_by(action="UPDATE").all()
        assert len(updates) == 1
        assert json.loads(updates[0].before) == {
            "CASEDATETIMEBEGIN": "2026-09-10 08:00"
        }
        assert json.loads(updates[0].after) == {
            "CASEDATETIMEBEGIN": "09-10-2026 08:00"
        }
