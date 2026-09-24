"""The audit trail's fingerprint chain.

Every entry carries a fingerprint of itself and of the entry before it.
Change an entry, or take one out, and the entries after it stop matching
-- which is what makes an edit made outside VECTOR, in a database
browser or by a damaged file, something that can be found rather than
something nobody notices.
"""

import pytest
from sqlalchemy import text

import models
from models import (
    AUDIT_CHAIN_START,
    AuditLog,
    Evidence,
    Persons,
    audit_fingerprint,
    chain_existing_audit_entries,
    get_session,
    verify_audit_chain,
)
import utils


def _add_evidence(number="1", desc="Laptop"):
    with get_session() as session:
        session.add(
            Evidence(
                EVIDNUM=number,
                EVIDQTY="1",
                EVIDDESC=desc,
                EVIDLOCROOM="Room A",
                EVIDLOCROOMDETAIL="shelf",
                EVIDFOUNDBY="Doe, John",
                EVIDFOUNDBYWITNESS="Roe, Jane",
            )
        )


def _entries():
    with get_session() as session:
        return [
            (row.id, row.action, row.chain)
            for row in session.query(AuditLog).order_by(AuditLog.id)
        ]


def test_every_entry_is_fingerprinted_as_it_is_written():
    _add_evidence()
    _add_evidence("2", "Telephone")

    chains = [chain for _id, _action, chain in _entries()]
    assert len(chains) == 2
    assert all(chain and len(chain) == 64 for chain in chains)
    # Two entries that differ cannot share a fingerprint.
    assert chains[0] != chains[1]


def test_the_first_entry_chains_onto_the_start():
    _add_evidence()

    with get_session() as session:
        first = session.query(AuditLog).order_by(AuditLog.id).first()
        assert first.chain == audit_fingerprint(AUDIT_CHAIN_START, first)


def test_ordinary_work_leaves_a_trail_that_checks_out(populated):
    with get_session() as session:
        item = session.query(Evidence).filter_by(EVIDNUM="3").one()
        item.EVIDDESC = "Telephone, black"
    with get_session() as session:
        session.delete(session.query(Persons).first())
    utils.delete_all_data()

    intact, message = verify_audit_chain()
    assert intact, message
    assert "match" in message


def test_an_entry_changed_afterwards_is_found(populated):
    """The whole point: an edit made outside VECTOR shows up."""
    with get_session() as session:
        target = session.query(AuditLog).order_by(AuditLog.id).first()
        target_id = target.id
    # Straight SQL, as a database browser would do it -- no ORM events,
    # no new audit entry.
    with models.engine.begin() as connection:
        connection.execute(
            text('UPDATE "AUDIT" SET summary = :summary WHERE id = :id'),
            {"summary": "something else entirely", "id": target_id},
        )

    intact, message = verify_audit_chain()
    assert not intact
    assert str(target_id) in message


def test_an_entry_removed_afterwards_is_found(populated):
    with get_session() as session:
        rows = [row.id for row in session.query(AuditLog).order_by(AuditLog.id)]
    assert len(rows) > 2
    with models.engine.begin() as connection:
        connection.execute(
            text('DELETE FROM "AUDIT" WHERE id = :id'), {"id": rows[1]}
        )

    intact, message = verify_audit_chain()
    assert not intact
    # The entry after the hole is the one that no longer matches.
    assert str(rows[2]) in message


def test_entries_from_before_the_chain_are_fingerprinted_once(populated):
    """An upgraded database has entries written before the column
    existed. They are chained retrospectively -- which says nothing
    about what happened to them before, and the check says so."""
    with models.engine.begin() as connection:
        connection.execute(text('UPDATE "AUDIT" SET chain = NULL'))

    intact, message = verify_audit_chain()
    assert intact
    assert "could not be checked" in message

    filled = chain_existing_audit_entries()
    assert filled == len(_entries())
    assert chain_existing_audit_entries() == 0

    intact, message = verify_audit_chain()
    assert intact
    assert "could not be checked" not in message


def test_a_trail_with_no_entries_checks_out():
    intact, message = verify_audit_chain()
    assert intact
    assert "no entries" in message.lower()


@pytest.mark.parametrize(
    "field, value",
    [
        ("summary", "a different item"),
        ("actor", "somebody else"),
        ("action", "DELETE"),
        ("ts_utc", "2020-01-01T00:00:00Z"),
    ],
)
def test_the_fingerprint_covers_what_the_entry_says(field, value):
    """Each recorded field goes into the fingerprint, so changing any one
    of them is detectable."""
    _add_evidence()
    with get_session() as session:
        entry = session.query(AuditLog).order_by(AuditLog.id).first()
        original = audit_fingerprint(AUDIT_CHAIN_START, entry)
        setattr(entry, field, value)
        assert audit_fingerprint(AUDIT_CHAIN_START, entry) != original
        session.expunge(entry)
