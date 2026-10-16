#!/usr/bin/env python3

"""
models.py

Dependencies:
    pip install sqlalchemy marshmallow bcrypt
"""

import bcrypt
import clock
from contextlib import contextmanager
import hashlib
import itertools
import secrets
from datetime import datetime, timezone
import json
import re
from sqlalchemy import (
    create_engine,
    event,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    LargeBinary,
)
from sqlalchemy.orm import declarative_base, deferred, sessionmaker
from marshmallow import Schema, fields

import crypto
from program.config import (
    APP_DB_PATH,
    Config,
    DB_DIR,
    USERS_DB_PATH,
)


# ----- Database Setup -----
# Paths are absolute (see program/config.py) so the app always opens the
# same database regardless of the current working directory. A relative
# path would silently create an empty database next to wherever the
# process happened to start.
DB_DIR.mkdir(parents=True, exist_ok=True)


def _sqlite_url(path) -> str:
    """Builds a SQLAlchemy URL from an absolute path, cross-platform."""
    return f"sqlite:///{path.as_posix()}"


def _enable_wal(dbapi_connection, _connection_record) -> None:
    """Puts SQLite in WAL mode so readers never block the writer.

    Without this, two agents working the same case over the network
    trip "database is locked" as soon as their writes overlap.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


# ----- Encryption -----
# Opt-in. An install with plaintext databases keeps working exactly as
# before; encryption starts when someone runs tools/encrypt_database.py.
# The passphrase is resolved once, here, and held only in memory.
ENCRYPTED = crypto.is_encrypted(APP_DB_PATH) or crypto.is_encrypted(
    USERS_DB_PATH
)
PASSPHRASE = ""

if ENCRYPTED:
    PASSPHRASE = crypto.resolve_passphrase()
    if not PASSPHRASE:
        raise crypto.KeyRequired(
            "The case database is encrypted and no passphrase was given.\n\n"
            "Supply one of:\n"
            "  VECTOR_DB_KEY=...         the passphrase itself\n"
            "  VECTOR_DB_KEY_FILE=...    a file holding it, e.g. on a USB "
            "stick\n"
            "  or start VECTOR from a terminal, which will prompt.\n"
        )
elif Config.REQUIRE_ENCRYPTION:
    raise crypto.KeyRequired(
        "VECTOR_REQUIRE_ENCRYPTION is set, but the case database is not "
        "encrypted.\nRun tools/encrypt_database.py, or unset the variable."
    )


def _make_engine(path, **kwargs):
    """Builds an engine for one database, encrypted or not."""
    if not ENCRYPTED:
        return create_engine(
            _sqlite_url(path),
            connect_args={"check_same_thread": False},
            **kwargs,
        )

    sqlcipher3 = crypto.require_sqlcipher()

    def creator():
        connection = sqlcipher3.connect(str(path), check_same_thread=False)
        connection.execute(crypto.key_pragma(PASSPHRASE))
        return connection

    # The plain sqlite dialect with the sqlcipher driver, rather than
    # sqlite+pysqlcipher: that dialect runs its own "pragma key=" from
    # the URL on connect, which would overwrite the one set here and
    # would also mean URL-escaping the passphrase.
    return create_engine(
        "sqlite://",
        module=sqlcipher3.dbapi2,
        creator=creator,
        **kwargs,
    )


# ----- Main database -----
DATABASE_URL = _sqlite_url(APP_DB_PATH)

engine = _make_engine(APP_DB_PATH, echo=False, future=True)
event.listen(engine, "connect", _enable_wal)

Session = sessionmaker(bind=engine)


# ----- Users database -----
USERS_DATABASE_URL = _sqlite_url(USERS_DB_PATH)

users_engine = _make_engine(USERS_DB_PATH)
event.listen(users_engine, "connect", _enable_wal)

UsersSession = sessionmaker(bind=users_engine)


# Main modles -> app_data.db
Base = declarative_base()

# Users model -> users.db
UsersBase = declarative_base()


# ----- MODELS -----

class Cases(Base):
    """Cases table — stores case details."""

    __tablename__ = "CASES"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    CASENUMBER = Column(String(), nullable=False)
    LOCATION = Column(String(), nullable=False)
    JURISDICTION = Column(String(), nullable=False)
    CASEDATETIMEBEGIN = Column(String(), nullable=False)
    CASEDATETIMEEND = Column(String())

    def __repr__(self):
        return f"Case Number: {self.CASENUMBER}; Location: {self.LOCATION}"

    def __str__(self):
        return f"Case Number: {self.CASENUMBER}; Location: {self.LOCATION}"


class CaseSchema(Schema):
    """Case schema."""

    CASENUMBER = fields.Str()
    LOCATION = fields.Str()
    JURISDICTION = fields.Str()
    CASEDATETIMEBEGIN = fields.Str()
    CASEDATETIMEEND = fields.Str()


case_schema = CaseSchema(many=True)


class Agents(Base):
    """Agents table — stores agent details."""

    __tablename__ = "AGENTS"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    AGENTNAME = Column(String(), nullable=False, unique=True)
    AGENTPARENTAGENCY = Column(String(), nullable=False)
    AGENTPRIMARYROLE = Column(String(), nullable=False)
    AGENTROLESECONDARY = Column(String())
    # Not unique: several agents legitimately have no direct number,
    # and blank values collided with each other.
    AGENTPHONE = Column(String())
    AGENTEMAIL = Column(String())
    AGENTNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Agent ID: {self.Z_PK}; Name: {self.AGENTNAME}"

    def __str__(self):
        return f"Agent ID: {self.Z_PK}; Name: {self.AGENTNAME}"


class AgentsSchema(Schema):
    """Agent schema."""

    AGENTNAME = fields.Str()
    AGENTPARENTAGENCY = fields.Str()
    AGENTPRIMARYROLE = fields.Str()
    AGENTROLESECONDARY = fields.Str()
    AGENTPHONE = fields.Str()
    AGENTEMAIL = fields.Str()
    AGENTNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


agents_schema = AgentsSchema(many=True)


class Rooms(Base):
    """Rooms table — stores room/area details."""

    __tablename__ = "ROOMS"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    ROOMLABEL = Column(String(), nullable=False, unique=True)
    ROOMDESC = Column(String(), nullable=False)
    ROOMFIRSTAGENT = Column(String(), nullable=False)
    ROOMSECONDAGENT = Column(String(), nullable=False)
    ROOMNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Room {self.ROOMLABEL} ({self.ROOMDESC})"

    def __str__(self):
        return f"Room {self.ROOMLABEL} ({self.ROOMDESC})"


class RoomsSchema(Schema):
    """Room schema."""

    ROOMLABEL = fields.Str()
    ROOMDESC = fields.Str()
    ROOMFIRSTAGENT = fields.Str()
    ROOMSECONDAGENT = fields.Str()
    ROOMNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


rooms_schema = RoomsSchema(many=True)


class Evidence(Base):
    """Evidence table — stores evidence item details."""

    __tablename__ = "EVIDENCE"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    EVIDNUM = Column(String(), nullable=False, unique=True)
    EVIDQTY = Column(String(), nullable=False)
    EVIDDESC = Column(String(), nullable=False)
    EVIDMODELNUMBER = Column(String())
    EVIDSERIALNUMBER = Column(String())
    EVIDLOCROOM = Column(String(), nullable=False)
    EVIDLOCROOMDETAIL = Column(String(), nullable=False)
    EVIDFOUNDBY = Column(String(), nullable=False)
    EVIDFOUNDBYWITNESS = Column(String(), nullable=False)
    EVIDPICTAKEN = Column(String())
    EVIDTRIAGED = Column(String())
    EVIDTRIAGEDBY = Column(String())
    EVIDISCONTRABAND = Column(String())
    EVIDNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Item {self.Z_PK}: {self.EVIDDESC}"

    def __str__(self):
        return f"Item {self.Z_PK}: {self.EVIDDESC}"


class EvidenceSchema(Schema):
    """Evidence schema."""

    EVIDNUM = fields.Str()
    EVIDQTY = fields.Str()
    EVIDDESC = fields.Str()
    EVIDMODELNUMBER = fields.Str()
    EVIDSERIALNUMBER = fields.Str()
    EVIDLOCROOM = fields.Str()
    EVIDLOCROOMDETAIL = fields.Str()
    EVIDFOUNDBY = fields.Str()
    EVIDFOUNDBYWITNESS = fields.Str()
    EVIDPICTAKEN = fields.Str()
    EVIDTRIAGED = fields.Str()
    EVIDTRIAGEDBY = fields.Str()
    EVIDISCONTRABAND = fields.Str()
    EVIDNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


evid_schema = EvidenceSchema(many=True)


class Persons(Base):
    """Persons table — stores suspect/person details."""

    __tablename__ = "PERSONS"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    PERSONNAME = Column(String(), nullable=False, unique=True)
    PERSONDOB = Column(String())
    PERSONADDRESS = Column(String())
    PERSONPHONE = Column(String())
    PERSONNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Person {self.Z_PK}: {self.PERSONNAME}"

    def __str__(self):
        return f"Person {self.Z_PK}: {self.PERSONNAME}"


class PersonSchema(Schema):
    """Person schema."""

    PERSONNAME = fields.Str()
    PERSONDOB = fields.Str()
    PERSONADDRESS = fields.Str()
    PERSONPHONE = fields.Str()
    PERSONNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


person_schema = PersonSchema(many=True)


class Notes(Base):
    """Notes table — stores general case/agent notes."""

    __tablename__ = "NOTES"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    NOTEDATETIME = Column(String(), nullable=False)
    NOTEDATETIMEUPDATED = Column(String())
    NOTEAUTHOR = Column(String(), nullable=False)
    NOTETEXT = Column(Text(), nullable=False)

    def __repr__(self):
        return f"Note {self.Z_PK}: {self.NOTETEXT}"

    def __str__(self):
        return f"Note {self.Z_PK}: {self.NOTETEXT}"


class NotesSchema(Schema):
    """Notes schema."""

    NOTEDATETIME = fields.Str()
    NOTEDATETIMEUPDATED = fields.Str()
    NOTEAUTHOR = fields.Str()
    NOTETEXT = fields.Str()


note_schema = NotesSchema(many=True)


class UploadedFiles(Base):
    """Uploaded files table."""

    __tablename__ = "FILES"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    FILENAME = Column(String(), nullable=False)
    FILESIZE = Column(Integer(), nullable=False)
    FILEMIMETYPE = Column(String(50))
    FILEUPLOADDATE = Column(DateTime(), default=datetime.utcnow)
    FILEUPLOADEDBY = Column(String(100), nullable=False)
    # Not unique: the same photograph may legitimately be attached
    # twice, and enforcing it made SQLite index every byte of every
    # attachment. Duplicate detection belongs on FILESHA256 below.
    # Deferred: loaded only when the bytes themselves are read. The Files
    # page lists names and sizes, and it refreshes whenever another device
    # saves -- loading every attachment each time read the whole case from
    # disk to show a table of file names.
    FILEDATA = deferred(Column(LargeBinary(), nullable=False))
    FILENOTE = Column(String())
    # Computed when the file is received, not when it is exported, so
    # the recorded hash certifies the file as collected.
    FILESHA256 = Column(String(64), index=True)
    FILEHASHEDDATETIME = Column(String())

    def __repr__(self):
        return f"File: {self.FILENAME}, Uploaded at: {self.FILEUPLOADDATE}"

    def __str__(self):
        return f"File: {self.FILENAME}, Uploaded at: {self.FILEUPLOADDATE}"


class FileSchema(Schema):
    """File schema."""

    FILENAME = fields.Str()
    FILESIZE = fields.Int()
    FILEMIMETYPE = fields.Str()
    FILEUPLOADDATE = fields.Str()
    FILEUPLOADEDBY = fields.Str()
    FILENOTE = fields.Str()
    FILESHA256 = fields.Str()
    FILEHASHEDDATETIME = fields.Str()


file_schema = FileSchema(many=True)


class Users(UsersBase):
    """Users table — authentication and user management."""

    __tablename__ = "users"

    Z_PK = Column(Integer(), primary_key=True, autoincrement=True)
    USERNAME = Column(String(100), unique=True, nullable=False)
    PASSWORDHASH = Column(String(255), nullable=False)
    ISADMIN = Column(Boolean(), default=False)
    ISACTIVE = Column(Boolean(), default=True)
    MUSTCHANGEPASSWORD = Column(Boolean, default=True)
    ENTEREDDATETIME = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"User Name: {self.USERNAME}"

    def __str__(self):
        return f"User {self.Z_PK}: {self.USERNAME}"

    def set_password(self, password: str):
        """Hashes a plaintext password and stores the hash."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        self.PASSWORDHASH = bcrypt.hashpw(
            password_bytes, salt
        ).decode("utf-8")

    def check_password_correction(self, attempted_password: str) -> bool:
        """Checks a plaintext password against the stored bcrypt hash."""
        try:
            return bcrypt.checkpw(
                attempted_password.encode("utf-8"),
                self.PASSWORDHASH.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False


class AuditLog(Base):
    """Append-only record of every change to case data.

    Never updated and never deleted. A tool whose purpose is
    documenting a seizure has to be able to answer "was this record
    changed after it was written, by whom, and from what?" -- so every
    insert, update and delete lands here with the values on both sides.

    Deletions store the complete row in `before`, which is what makes a
    deleted item recoverable without soft-delete columns on every table.
    """

    __tablename__ = "AUDIT"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    ts_utc = Column(String(), nullable=False, index=True)
    actor = Column(String(), nullable=False)
    action = Column(String(), nullable=False)      # CREATE/UPDATE/DELETE/...
    table_name = Column(String(), nullable=False, index=True)
    row_pk = Column(Integer())
    summary = Column(String())                     # human-readable label
    before = Column(Text())                        # JSON, changed fields only
    after = Column(Text())
    # A fingerprint of this entry and of the one before it, which makes
    # the trail a chain. See audit_fingerprint().
    chain = Column(String(64))

    def __repr__(self):
        return f"Audit {self.id}: {self.action} {self.table_name}"


# ----- Audit plumbing -----
# Columns never worth recording: FILEDATA would put every byte of every
# attachment into the log.
_AUDIT_SKIP_COLUMNS = {"FILEDATA"}

# Tables the listener watches. AUDIT itself is excluded -- it is
# append-only and must never audit its own writes.
_AUDITED_TABLES = {
    "CASES": "CASENUMBER",
    "AGENTS": "AGENTNAME",
    "ROOMS": "ROOMLABEL",
    "EVIDENCE": "EVIDNUM",
    "PERSONS": "PERSONNAME",
    "NOTES": "NOTEAUTHOR",
    "FILES": "FILENAME",
}


def audit_timestamp() -> str:
    """UTC, ISO-8601, explicitly marked. Never local time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----- Tamper-evidence -----
# Each entry carries a SHA-256 of its own contents and of the entry
# before it, so the entries form a chain. Change one in a database
# browser, or take one out, and every entry after it stops matching --
# which is the difference between an alteration somebody notices and one
# nobody does.
#
# This is evidence of tampering, not protection from it: anyone who can
# write to the database could recompute the whole chain. An export taken
# while the trail was whole is the outside copy to check against.
AUDIT_CHAIN_START = "0" * 64

# The order entries were written in. Their ids are not assigned until the
# flush, and the chain has to follow the order they happened in.
_audit_sequence = itertools.count()


def audit_fingerprint(previous: str, entry) -> str:
    """The fingerprint of one entry, given the one before it."""
    fields = [
        previous or AUDIT_CHAIN_START,
        entry.ts_utc or "",
        entry.actor or "",
        entry.action or "",
        entry.table_name or "",
        "" if entry.row_pk is None else str(entry.row_pk),
        entry.summary or "",
        entry.before or "",
        entry.after or "",
    ]
    # A unit separator between the fields, so no value can fake a field
    # boundary: JSON escapes control characters, and it is not a
    # character a username or a table name can hold.
    joined = "\x1f".join(fields)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _new_audit_entry(**fields):
    """An audit entry, stamped with its place in the order written."""
    entry = AuditLog(**fields)
    entry._sequence = next(_audit_sequence)
    return entry


def current_actor() -> str:
    """The signed-in user, or a marker when there is no web session.

    Never raises: an audit record with an uncertain actor is worth far
    more than a failed save.
    """
    try:
        from nicegui import app
        name = app.storage.user.get("USERNAME", "")
        return name or "unauthenticated"
    except Exception:
        return "system"


def _serialise(value):
    """Makes a column value JSON-safe."""
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(bytes(value))} bytes>"
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _row_dict(obj) -> dict:
    """Every auditable column of a mapped object."""
    return {
        column.name: _serialise(getattr(obj, column.name, None))
        for column in obj.__table__.columns
        if column.name not in _AUDIT_SKIP_COLUMNS
    }


def _changed_fields(obj) -> tuple[dict, dict]:
    """Returns (before, after) limited to columns that actually changed."""
    from sqlalchemy import inspect as sa_inspect

    before, after = {}, {}
    state = sa_inspect(obj)
    for column in obj.__table__.columns:
        if column.name in _AUDIT_SKIP_COLUMNS:
            continue
        history = state.attrs[column.name].history
        if not history.has_changes():
            continue
        before[column.name] = _serialise(
            history.deleted[0] if history.deleted else None
        )
        after[column.name] = _serialise(
            history.added[0] if history.added else None
        )
    return before, after


def record_audit(
        session,
        action: str,
        table_name: str,
        row_pk=None,
        summary: str = "",
        before=None,
        after=None,
        actor: str | None = None,
) -> None:
    """Writes one audit row.

    Used directly for events the ORM listener cannot see -- logins, and
    bulk deletes issued as query().delete(), which bypass ORM events
    entirely.
    """
    session.add(
        _new_audit_entry(
            ts_utc=audit_timestamp(),
            actor=actor or current_actor(),
            action=action,
            table_name=table_name,
            row_pk=row_pk,
            summary=summary or "",
            before=json.dumps(before, default=str) if before else None,
            after=json.dumps(after, default=str) if after else None,
        )
    )


# Bound to the app_data sessionmaker specifically, not to Session as a
# class: users.db has no AUDIT table, so auditing its writes would
# fail every login.
@event.listens_for(Session, "before_flush")
def _audit_before_flush(session, _flush_context, _instances) -> None:
    """Captures every ORM insert, update and delete as it is flushed.

    Hooking the flush rather than each page's save handler means a new
    page, or a forgotten call site, cannot silently skip the audit
    trail.
    """
    entries = []

    for obj in session.new:
        table = getattr(obj, "__tablename__", None)
        if table not in _AUDITED_TABLES:
            continue
        entries.append(("CREATE", obj, None, _row_dict(obj)))

    for obj in session.dirty:
        table = getattr(obj, "__tablename__", None)
        if table not in _AUDITED_TABLES or not session.is_modified(obj):
            continue
        before, after = _changed_fields(obj)
        if not after:
            continue
        entries.append(("UPDATE", obj, before, after))

    for obj in session.deleted:
        table = getattr(obj, "__tablename__", None)
        if table not in _AUDITED_TABLES:
            continue
        entries.append(("DELETE", obj, _row_dict(obj), None))

    if not entries:
        return

    actor = current_actor()
    for action, obj, before, after in entries:
        label_column = _AUDITED_TABLES[obj.__tablename__]
        session.add(
            _new_audit_entry(
                ts_utc=audit_timestamp(),
                actor=actor,
                action=action,
                table_name=obj.__tablename__,
                row_pk=getattr(obj, "Z_PK", None) or getattr(obj, "id", None),
                summary=str(getattr(obj, label_column, "") or ""),
                before=json.dumps(before, default=str) if before else None,
                after=json.dumps(after, default=str) if after else None,
            )
        )


@event.listens_for(Session, "before_flush")
def _chain_audit_entries(session, _flush_context, _instances) -> None:
    """Fingerprints each new entry onto the one before it.

    Registered after the listener above, so the entries it has just
    added are chained in the same flush -- and before anything reaches
    the database, so a rolled-back transaction leaves no gap.
    """
    pending = sorted(
        (obj for obj in session.new if isinstance(obj, AuditLog)),
        key=lambda entry: getattr(entry, "_sequence", 0),
    )
    if not pending:
        return

    with session.no_autoflush:
        previous = (
            session.query(AuditLog.chain)
            .order_by(AuditLog.id.desc())
            .limit(1)
            .scalar()
        )

    for entry in pending:
        if entry.chain:
            continue
        entry.chain = audit_fingerprint(previous, entry)
        previous = entry.chain


def verify_audit_chain() -> tuple[bool, str]:
    """Walks the trail, checking each entry against its fingerprint.

    Returns whether everything matches, and a sentence saying what was
    found -- the first entry that does not match, if any, because every
    entry after it is chained onto a value that has changed.
    """
    previous = AUDIT_CHAIN_START
    checked = unchained = 0

    with get_session() as session:
        entries = (
            session.query(AuditLog).order_by(AuditLog.id).yield_per(500)
        )
        for entry in entries:
            checked += 1
            if not entry.chain:
                # Written before fingerprints existed, and not yet
                # filled in. The next entry was chained onto nothing.
                unchained += 1
                previous = AUDIT_CHAIN_START
                continue
            if entry.chain != audit_fingerprint(previous, entry):
                return (
                    False,
                    f"Entry {entry.id} does not match its fingerprint: a "
                    f"{entry.action} on {entry.table_name}, recorded at "
                    f"{clock.show_utc(entry.ts_utc)} by "
                    f"{entry.actor or 'someone unrecorded'}. It was "
                    "changed or the entry before it was removed. "
                    f"The {checked - 1} entries before it match.",
                )
            previous = entry.chain

    if not checked:
        return (True, "The trail has no entries yet.")

    message = f"All {checked} entries match their fingerprints."
    if unchained:
        message += (
            f" {unchained} of them could not be checked: they were "
            "written before fingerprints were added."
        )
    return (True, message)


def chain_existing_audit_entries() -> int:
    """Fingerprints entries written before the chain existed.

    They are chained in the order they were written, which says nothing
    about what happened to them before this ran -- only that nothing has
    changed since. Returns how many were filled in.

    Only entries after the last fingerprinted one are filled in. An
    unfingerprinted entry with a fingerprinted one after it was already
    passed over when that one was written -- it was chained onto the
    start -- and filling it in now would break the chain there rather
    than extend it. It is left as it is, and the check reports it as
    one that could not be checked, which is the truth.

    Raw SQL rather than the ORM: this runs during the schema upgrade,
    and updating the trail is not itself an event worth recording.
    """
    from sqlalchemy import text

    with engine.connect() as connection:
        if _stored_table_name(connection, "AUDIT") is None:
            return 0
        rows = connection.execute(
            text(
                'SELECT id, ts_utc, actor, action, table_name, row_pk, '
                'summary, "before", "after", chain FROM "AUDIT" ORDER BY id'
            )
        ).all()

    last_chained = max(
        (index for index, row in enumerate(rows) if row.chain),
        default=-1,
    )
    previous = rows[last_chained].chain if last_chained >= 0 else (
        AUDIT_CHAIN_START
    )
    filled = []
    for row in rows[last_chained + 1:]:
        fingerprint = audit_fingerprint(previous, row)
        filled.append((row.id, fingerprint))
        previous = fingerprint

    if not filled:
        return 0

    with engine.begin() as connection:
        for row_id, fingerprint in filled:
            connection.execute(
                text('UPDATE "AUDIT" SET chain = :chain WHERE id = :id'),
                {"chain": fingerprint, "id": row_id},
            )

    print(
        f"Schema migration: fingerprinted {len(filled)} existing audit "
        "entries"
    )
    return len(filled)


# ----- Change signal -----
# Open pages on other devices watch these numbers and reload what they
# show when one moves, so an entry made on one tablet appears on the
# others without anyone pressing reload. They count commits made by this
# process, which is the only one writing to app_data.db while VECTOR
# runs.
#
# Case data and the audit trail are counted apart. A sign-in writes
# nothing but an audit entry: no table on screen changes, so the pages
# showing case data must not reload -- and the Audit Trail page, which
# exists to show exactly those entries, must.
_data_version = 0
_audit_version = 0


def data_version() -> int:
    """Goes up by one each time a change to case data is committed."""
    return _data_version


def audit_version() -> int:
    """Goes up by one each time audit entries are committed."""
    return _audit_version


@event.listens_for(Session, "before_flush")
def _note_case_change(session, _flush_context, _instances) -> None:
    for group in (session.new, session.dirty, session.deleted):
        for obj in group:
            if isinstance(obj, AuditLog):
                session.info["vector_audited"] = True
            else:
                session.info["vector_changed"] = True


@event.listens_for(Session, "do_orm_execute")
def _note_bulk_change(orm_execute_state) -> None:
    # query().delete() never flushes objects, so a wipe or an import is
    # caught here instead.
    if not orm_execute_state.is_select:
        orm_execute_state.session.info["vector_changed"] = True


@event.listens_for(Session, "after_commit")
def _count_committed_change(session) -> None:
    global _data_version, _audit_version
    if session.info.pop("vector_changed", False):
        _data_version += 1
    if session.info.pop("vector_audited", False):
        _audit_version += 1


@event.listens_for(Session, "after_rollback")
def _forget_rolled_back_change(session) -> None:
    session.info.pop("vector_changed", None)
    session.info.pop("vector_audited", None)


def generate_one_time_password() -> str:
    """Makes a fresh password for a new or reset account.

    Replaces a shared DEFAULT_USER_PASSWORD constant that was published
    in this repository. Every account whose owner had not yet signed in
    was open to anyone who had read models.py -- and combined with the
    unguarded admin panel, that was the whole exploit chain.

    Shown to the administrator once, never stored in plaintext, and
    paired with MUSTCHANGEPASSWORD so it survives only until first use.
    """
    return secrets.token_urlsafe(9)


# ----- Schema Migration -----
# Columns that used to carry UNIQUE and no longer should. SQLite cannot
# drop an implicit unique index, so the table has to be rebuilt.
_UNIQUE_DROPPED = {
    "AGENTS": {"AGENTPHONE", "AGENTEMAIL"},
    "ROOMS": {"ROOMDESC"},
    "FILES": {"FILEDATA"},
}

# Names from before the upstream project brought PERSONS, FILES and users
# into line with the TABLE+FIELD capitals used everywhere else, and from
# before PERSONS.SUSPECTNOTE became PERSONNOTE and FILES.FILEHASHEDAT
# became FILEHASHEDDATETIME. Databases and exports made earlier still
# carry them. The migration and both importers read this one map, so they
# cannot disagree about what an old name means.
LEGACY_TABLE_NAMES = {
    "files": "FILES",
    "uploaded_files": "FILES",
}

LEGACY_COLUMN_NAMES = {
    "PERSONS": {
        "SUSPECTNAME": "PERSONNAME",
        "SUSPECTDOB": "PERSONDOB",
        "SUSPECTADDRESS": "PERSONADDRESS",
        "SUSPECTPHONE": "PERSONPHONE",
        "SUSPECTNOTE": "PERSONNOTE",
    },
    "FILES": {
        "id": "Z_PK",
        "file_name": "FILENAME",
        "file_size": "FILESIZE",
        "file_mime_type": "FILEMIMETYPE",
        "upload_date": "FILEUPLOADDATE",
        "uploaded_by": "FILEUPLOADEDBY",
        "file_data": "FILEDATA",
        "file_note": "FILENOTE",
        "sha256": "FILESHA256",
        "hashed_at": "FILEHASHEDDATETIME",
        "FILEHASHEDAT": "FILEHASHEDDATETIME",
    },
    "users": {
        "id": "Z_PK",
        "user_name": "USERNAME",
        "password_hash": "PASSWORDHASH",
        "is_admin": "ISADMIN",
        "is_active": "ISACTIVE",
        "must_change_password": "MUSTCHANGEPASSWORD",
        "created_at": "ENTEREDDATETIME",
    },
}


def _stored_table_name(connection, table_name: str):
    """The name a table is actually stored under, or None if absent.

    SQLite matches table names without regard to case, but sqlite_master
    keeps the spelling the table was created with -- so an older database
    answers to "FILES" while still listing itself as "files".
    """
    from sqlalchemy import text

    return connection.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name = :name COLLATE NOCASE"
        ),
        {"name": table_name},
    ).scalar()


def _column_names(connection, table_name: str) -> set:
    """The columns a table currently has, as stored."""
    from sqlalchemy import text

    return {
        row[1]
        for row in connection.execute(
            text(f'PRAGMA table_info("{table_name}")')
        )
    }


def _backup_database(target_engine, path):
    """Copies a database aside before a migration rewrites it.

    The write-ahead log is folded in first. In WAL mode the most recent
    writes live in the -wal file rather than the .db, so copying the .db
    alone would quietly leave them out of the backup.
    """
    import shutil
    from sqlalchemy import text

    with target_engine.connect() as connection:
        connection.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_suffix(f".db.bak-{stamp}")
    counter = 1
    while backup.exists():
        backup = path.with_suffix(f".db.bak-{stamp}-{counter}")
        counter += 1

    shutil.copy2(path, backup)
    print(f"Schema migration: backed up {path.name} to {backup.name}")
    return backup


def _rename_legacy_schema() -> None:
    """Renames old table and column names in place.

    ALTER TABLE ... RENAME COLUMN keeps every row, index and constraint,
    so no rebuild is needed. Idempotent: a column is renamed only while
    its old spelling is present and its new one is not.

    Where both spellings are present -- a database opened by a version
    that added the new column, empty, beside the old one -- the old
    values are copied into the gaps in the new column instead, and the
    old column is left where it is.
    """
    from sqlalchemy import text

    targets = (
        (engine, APP_DB_PATH, Base.metadata),
        (users_engine, USERS_DB_PATH, UsersBase.metadata),
    )

    for target_engine, path, metadata in targets:
        plan = []
        with target_engine.connect() as connection:
            for table_name, renames in LEGACY_COLUMN_NAMES.items():
                if table_name not in metadata.tables:
                    continue
                stored = _stored_table_name(connection, table_name)
                if stored is None:
                    continue
                present = _column_names(connection, stored)
                columns = [
                    (old, new)
                    for old, new in renames.items()
                    if old in present and new not in present
                ]
                gaps = [
                    (old, new)
                    for old, new in renames.items()
                    if old in present and new in present
                    and connection.execute(
                        text(
                            f'SELECT COUNT(*) FROM "{stored}" '
                            f'WHERE "{new}" IS NULL AND "{old}" IS NOT NULL'
                        )
                    ).scalar()
                ]
                if columns or gaps or stored != table_name:
                    plan.append((table_name, stored, columns, gaps))

        if not plan:
            continue

        _backup_database(target_engine, path)

        with target_engine.begin() as connection:
            for table_name, stored, columns, gaps in plan:
                for old, new in columns:
                    connection.execute(
                        text(
                            f'ALTER TABLE "{stored}" '
                            f'RENAME COLUMN "{old}" TO "{new}"'
                        )
                    )
                for old, new in gaps:
                    connection.execute(
                        text(
                            f'UPDATE "{stored}" SET "{new}" = "{old}" '
                            f'WHERE "{new}" IS NULL AND "{old}" IS NOT NULL'
                        )
                    )
                    print(
                        f"Schema migration: {stored}.{old} copied into "
                        f"{stored}.{new}"
                    )
                if stored != table_name:
                    # SQLite refuses a rename that differs only in case,
                    # so it goes by way of a temporary name.
                    interim = f"{table_name}__renaming"
                    connection.execute(
                        text(f'ALTER TABLE "{stored}" RENAME TO "{interim}"')
                    )
                    connection.execute(
                        text(
                            f'ALTER TABLE "{interim}" RENAME TO "{table_name}"'
                        )
                    )
                print(
                    f"Schema migration: {stored} -> {table_name}, "
                    f"{len(columns)} column(s) renamed"
                )


def _stale_unique_columns(connection, table_name: str) -> set:
    """Returns the columns on `table_name` still carrying UNIQUE."""
    from sqlalchemy import text

    stored = _stored_table_name(connection, table_name)
    if stored is None:
        return set()

    stale = set()
    for row in connection.execute(text(f'PRAGMA index_list("{stored}")')):
        index_name, is_unique = row[1], row[2]
        if not is_unique:
            continue
        columns = {
            info[2]
            for info in connection.execute(
                text(f'PRAGMA index_info("{index_name}")')
            )
        }
        stale |= columns & _UNIQUE_DROPPED[table_name]
    return stale


def _add_missing_columns() -> None:
    """Adds columns introduced after a database was first created.

    SQLite supports ALTER TABLE ADD COLUMN, so unlike the unique-index
    work below this needs no table rebuild.
    """
    from sqlalchemy import text

    additions = {
        "FILES": [
            ("FILENOTE", "VARCHAR"),
            ("FILESHA256", "VARCHAR(64)"),
            ("FILEHASHEDDATETIME", "VARCHAR"),
        ],
        "AUDIT": [
            ("chain", "VARCHAR(64)"),
        ],
    }

    with engine.begin() as connection:
        for table_name, columns in additions.items():
            stored = _stored_table_name(connection, table_name)
            if stored is None:
                continue

            present = _column_names(connection, stored)
            for column_name, column_type in columns:
                if column_name in present:
                    continue
                connection.execute(
                    text(
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{column_name}" {column_type}'
                    )
                )
                print(
                    f"Schema migration: added {table_name}.{column_name}"
                )


def migrate_schema() -> None:
    """Rebuilds any table still carrying a UNIQUE we have since dropped.

    Those constraints blocked ordinary scenes: a second agent with no
    email address, a house with two bedrooms, the same photograph
    attached twice. Existing databases keep the old indexes until the
    table is rebuilt, so this runs at startup and is a no-op once done.

    The database is copied to a timestamped .bak alongside itself before
    anything is rewritten.
    """
    from sqlalchemy import text

    with engine.connect() as connection:
        pending = {
            name: _stale_unique_columns(connection, name)
            for name in _UNIQUE_DROPPED
        }
    pending = {name: cols for name, cols in pending.items() if cols}

    if not pending:
        return

    _backup_database(engine, APP_DB_PATH)

    for table_name, columns in pending.items():
        table = Base.metadata.tables[table_name]
        column_list = ", ".join(f'"{c.name}"' for c in table.columns)
        temp_name = f"{table_name}__premigrate"

        with engine.begin() as connection:
            connection.execute(
                text(f'ALTER TABLE "{table_name}" RENAME TO "{temp_name}"')
            )
            table.create(bind=connection)
            connection.execute(
                text(
                    f'INSERT INTO "{table_name}" ({column_list}) '
                    f'SELECT {column_list} FROM "{temp_name}"'
                )
            )
            connection.execute(text(f'DROP TABLE "{temp_name}"'))

        print(
            f"Schema migration: dropped UNIQUE on "
            f"{table_name}.{', '.join(sorted(columns))}"
        )


# ----- Date format -----
# Case times and dates of birth are entered as MM-DD-YYYY, the format the
# upstream project settled on. A value stored earlier as YYYY-MM-DD would
# be scrambled by the input mask the first time someone edited it, so it
# is rewritten once -- through the ORM, which puts each change in the
# audit trail.
_ISO_DATETIME = re.compile(r"^(\d{4})-(\d{2})-(\d{2})( \d{2}:\d{2})$")
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})()$")
_ISO_TIMESTAMP = re.compile(r"^(\d{4})-(\d{2})-(\d{2})( \d{2}:\d{2}:\d{2})$")


def _month_first(value, pattern):
    """Rewrites one value if it matches `pattern` exactly."""
    match = pattern.match(value or "")
    if not match:
        return value
    year, month, day, time_part = match.groups()
    return f"{month}-{day}-{year}{time_part}"


_BARE_STAMP = re.compile(r"^\d{2,4}-\d{2}-\d{2,4} \d{2}:\d{2}:\d{2}$")
_UTC_STAMP_FORMATS = ("%m-%d-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S")


def _utc_stamp_to_local(value):
    """Rewrites a stamp VECTOR wrote in UTC as a local one, with its offset.

    Only a complete stamp with no offset qualifies. One that already
    carries its offset -- which is what marks it as done -- and anything a
    person typed are left as they are.
    """
    text = value or ""
    if not _BARE_STAMP.match(text):
        return value
    for fmt in _UTC_STAMP_FORMATS:
        try:
            moment = datetime.strptime(text, fmt)
        except ValueError:
            continue
        return clock.stamp(clock.from_utc(moment))
    return value


def normalise_legacy_dates() -> int:
    """Brings stored dates and times into today's formats.

    YYYY-MM-DD case times, birth dates and note times become MM-DD-YYYY,
    and stamps VECTOR wrote in UTC become local time with their offset.
    Anything not in exactly an old format is left alone. Returns how many
    values changed.
    """
    changed = 0
    with get_session() as session:
        for case in session.query(Cases).all():
            for column in ("CASEDATETIMEBEGIN", "CASEDATETIMEEND"):
                old = getattr(case, column)
                new = _month_first(old, _ISO_DATETIME)
                if new != old:
                    setattr(case, column, new)
                    changed += 1

        for person in session.query(Persons).all():
            new = _month_first(person.PERSONDOB, _ISO_DATE)
            if new != person.PERSONDOB:
                person.PERSONDOB = new
                changed += 1

        # Notes and entry times were stamped in UTC, with no offset: notes
        # as MM-DD-YYYY HH:MM:SS (older ones the other way round), entry
        # times as YYYY-MM-DD HH:MM:SS. Each is rewritten once in this
        # machine's time zone, with the offset.
        for note in session.query(Notes).all():
            for column in ("NOTEDATETIME", "NOTEDATETIMEUPDATED"):
                old = getattr(note, column)
                new = _utc_stamp_to_local(_month_first(old, _ISO_TIMESTAMP))
                if new != old:
                    setattr(note, column, new)
                    changed += 1

        for model in (Agents, Rooms, Evidence, Persons):
            for record in session.query(model).all():
                old = record.ENTEREDDATETIME
                new = _utc_stamp_to_local(old)
                if new != old:
                    record.ENTEREDDATETIME = new
                    changed += 1

    if changed:
        print(
            f"Schema migration: {changed} date(s) and time(s) brought "
            "up to date"
        )
    return changed


def upgrade_database() -> None:
    """Brings existing databases up to the current schema.

    Order matters: names first, so the later steps see today's columns;
    then columns added since; then the table rebuilds, which copy rows by
    the current column list; then the audit fingerprints for entries
    written before there were any; and last the stored dates.

    The fingerprints have to come before anything that writes to the
    trail. Rewriting a date writes an audit entry, and a new entry is
    chained onto the one before it -- which, before the old entries are
    fingerprinted, has none, so the new one was chained onto the start.
    Fingerprinting the old ones afterwards then left it chained onto the
    wrong thing, and the trail failed its own check from that entry on.
    """
    _rename_legacy_schema()
    _add_missing_columns()
    migrate_schema()
    chain_existing_audit_entries()
    normalise_legacy_dates()


# ----- Table Creation -----
def init_db():
    """Initialize both databases."""
    Base.metadata.create_all(engine)

    # Create ONLY the Users table in users.db
    UsersBase.metadata.create_all(users_engine)

    # Bring existing databases up to the current schema.
    upgrade_database()


# ----- Convenience Context Manager -----
@contextmanager
def get_session():
    """Provides a transactional session scope.

    Usage:
        with get_session() as session:
            session.add(new_record)
            # commit happens automatically on exit
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_users_session():
    """Provides a transactional session scope for the users database.

    Usage:
        with get_users_session() as session:
            session.add(new_user)
            # commit happens automatically on exit
    """
    session = UsersSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ----- Active case -----
def has_active_case() -> bool:
    """Whether a case has been opened."""
    with get_session() as session:
        return session.query(Cases).count() > 0


def check_case_info() -> dict | None:
    """The open case's number and start time, or None if there is none."""
    with get_session() as session:
        case = session.query(Cases).order_by(Cases.Z_PK).first()
        if not case:
            return None
        return {
            "Z_PK": case.Z_PK,
            "CASENUMBER": case.CASENUMBER,
            "CASEDATETIMEBEGIN": case.CASEDATETIMEBEGIN or None,
        }
