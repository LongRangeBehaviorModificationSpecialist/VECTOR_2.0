"""The audit trail.

Hooked into the session flush rather than each page's save handler, so
a new page or a forgotten call site cannot skip it.
"""

import json

from models import (
    AuditLog,
    Cases,
    Evidence,
    Persons,
    UploadedFiles,
    get_session,
)
import utils


def _entries(action=None):
    with get_session() as session:
        query = session.query(AuditLog)
        if action:
            query = query.filter(AuditLog.action == action)
        return [
            {
                "action": row.action,
                "table_name": row.table_name,
                "summary": row.summary,
                "actor": row.actor,
                "before": json.loads(row.before) if row.before else None,
                "after": json.loads(row.after) if row.after else None,
                "ts_utc": row.ts_utc,
            }
            for row in query.order_by(AuditLog.id).all()
        ]


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


def test_creating_a_record_is_logged():
    _add_evidence()
    entries = _entries("CREATE")
    assert len(entries) == 1
    assert entries[0]["table_name"] == "EVIDENCE"
    assert entries[0]["summary"] == "1"
    assert entries[0]["after"]["EVIDDESC"] == "Laptop"


def test_updating_records_only_the_changed_fields():
    _add_evidence()
    with get_session() as session:
        item = session.query(Evidence).one()
        item.EVIDDESC = "Laptop, Dell Latitude"

    update = _entries("UPDATE")[0]
    assert update["after"] == {"EVIDDESC": "Laptop, Dell Latitude"}
    assert update["before"] == {"EVIDDESC": "Laptop"}
    # Untouched columns must not appear.
    assert "EVIDQTY" not in update["after"]


def test_deleting_keeps_the_whole_row_for_recovery():
    with get_session() as session:
        session.add(
            Persons(
                SUSPECTNAME="O'Brien, Sean",
                SUSPECTDOB="1984-03-02",
                SUSPECTADDRESS="14 Elm Street",
            )
        )
    with get_session() as session:
        session.delete(session.query(Persons).one())

    deleted = _entries("DELETE")[0]
    assert deleted["before"]["SUSPECTNAME"] == "O'Brien, Sean"
    assert deleted["before"]["SUSPECTDOB"] == "1984-03-02"
    assert deleted["before"]["SUSPECTADDRESS"] == "14 Elm Street"


def test_a_no_op_save_writes_nothing():
    _add_evidence()
    before = len(_entries())
    with get_session() as session:
        item = session.query(Evidence).one()
        item.EVIDDESC = item.EVIDDESC  # unchanged
    assert len(_entries()) == before


def test_bulk_wipe_is_recorded_with_counts(populated):
    """query().delete() raises no ORM events, so this is explicit."""
    utils.delete_all_data()

    wipe = _entries("DELETE_ALL")
    assert len(wipe) == 1
    assert wipe[0]["before"]["EVIDENCE"] == 12
    assert wipe[0]["before"]["CASES"] == 1


def test_audit_survives_a_wipe(populated):
    """The trail is append-only; a wipe is what it exists to record."""
    utils.delete_all_data()
    with get_session() as session:
        assert session.query(Cases).count() == 0
        assert session.query(AuditLog).count() > 0


def test_file_blobs_are_never_copied_into_the_log():
    """file_data would put every byte of every attachment in the trail."""
    with get_session() as session:
        session.add(
            UploadedFiles(
                file_name="photo.jpg",
                file_size=10,
                file_mime_type="image/jpeg",
                uploaded_by="Doe, John",
                file_data=b"SECRETPIXELBYTES",
                sha256="a" * 64,
            )
        )
    entry = _entries("CREATE")[0]
    assert "file_data" not in (entry["after"] or {})
    assert "SECRETPIXELBYTES" not in json.dumps(entry["after"])
    assert entry["after"]["sha256"] == "a" * 64


def test_timestamps_are_utc_and_marked():
    _add_evidence()
    stamp = _entries()[0]["ts_utc"]
    assert stamp.endswith("Z")
    assert "T" in stamp


def test_every_entry_names_an_actor():
    _add_evidence()
    assert all(entry["actor"] for entry in _entries())
