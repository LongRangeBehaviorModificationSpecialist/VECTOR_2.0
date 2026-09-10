#!/usr/bin/env python3

"""
models.py

Dependencies:
    pip install sqlalchemy marshmallow bcrypt
"""

import bcrypt
from contextlib import contextmanager
from datetime import datetime, timezone
import json
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
from sqlalchemy.orm import declarative_base, sessionmaker
from marshmallow import Schema, fields

from program.config import APP_DB_PATH, DB_DIR, USERS_DB_PATH


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


# ----- Main database -----
DATABASE_URL = _sqlite_url(APP_DB_PATH)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False}
)
event.listen(engine, "connect", _enable_wal)

Session = sessionmaker(bind=engine)

# ----- Users database -----
USERS_DATABASE_URL = _sqlite_url(USERS_DB_PATH)

users_engine = create_engine(
    USERS_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
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

    Z_PK = Column(Integer(), primary_key=True)
    CASENUMBER = Column(String(), nullable=False)
    LOCATION = Column(String(), nullable=False)
    JURISDICTION = Column(String(), nullable=False)
    CASEDATETIMEBEGIN = Column(String(), nullable=False)
    CASEDATETIMEEND = Column(String())

    def __repr__(self):
        return f"Case Number: {self.CASENUMBER}"

    def __str__(self):
        return f"Case Number: {self.CASENUMBER}"


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

    Z_PK = Column(Integer(), primary_key=True)
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
        return f"Agent {self.Z_PK}: {self.AGENTNAME}"

    def __str__(self):
        return f"Agent {self.Z_PK}: {self.AGENTNAME}"


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

    Z_PK = Column(Integer(), primary_key=True)
    ROOMLABEL = Column(String(), nullable=False, unique=True)
    # Not unique: a house with two bedrooms is ordinary.
    ROOMDESC = Column(String(), nullable=False)
    ROOMFIRSTAGENT = Column(String(), nullable=False)
    ROOMSECONDAGENT = Column(String(), nullable=False)
    ROOMNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Room {self.ROOMLABEL}: {self.ROOMDESC}"

    def __str__(self):
        return f"Room {self.ROOMLABEL}: {self.ROOMDESC}"


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

    Z_PK = Column(Integer(), primary_key=True)
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

    Z_PK = Column(Integer(), primary_key=True)
    SUSPECTNAME = Column(String(), nullable=False, unique=True)
    SUSPECTDOB = Column(String())
    SUSPECTADDRESS = Column(String())
    SUSPECTPHONE = Column(String())
    SUSPECTNOTE = Column(Text())
    ENTEREDDATETIME = Column(String())

    def __repr__(self):
        return f"Person {self.Z_PK}: {self.SUSPECTNAME}"

    def __str__(self):
        return f"Person {self.Z_PK}: {self.SUSPECTNAME}"


class PersonSchema(Schema):
    """Person schema."""

    SUSPECTNAME = fields.Str()
    SUSPECTDOB = fields.Str()
    SUSPECTADDRESS = fields.Str()
    SUSPECTPHONE = fields.Str()
    SUSPECTNOTE = fields.Str()
    ENTEREDDATETIME = fields.Str()


person_schema = PersonSchema(many=True)


class Notes(Base):
    """Notes table — stores general case/agent notes."""

    __tablename__ = "NOTES"

    Z_PK = Column(Integer(), primary_key=True)
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

    __tablename__ = "files"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    file_name = Column(String(), nullable=False)
    file_size = Column(Integer(), nullable=False)
    file_mime_type = Column(String(50))
    upload_date = Column(DateTime(), default=datetime.utcnow)
    # Not unique: the same photograph may legitimately be attached
    # twice, and enforcing it made SQLite index every byte of every
    # attachment. Duplicate detection belongs on sha256 below.
    file_data = Column(LargeBinary(), nullable=False)
    # Computed when the file is received, not when it is exported, so
    # the recorded hash certifies the file as collected.
    sha256 = Column(String(64), index=True)
    hashed_at = Column(String())
    uploaded_by = Column(String(100), nullable=False)

    def __repr__(self):
        return f"File Name: {self.file_name}, Uploaded at: {self.upload_date}"

    def __str__(self):
        return f"File Name: {self.file_name}, Uploaded at: {self.upload_date}"


class FileSchema(Schema):
    """File schema."""

    file_name = fields.Str()
    file_size = fields.Int()
    file_mime_type = fields.Str()
    file_note = fields.Str()
    upload_date = fields.Str()
    uploaded_by = fields.Str()

file_schema = FileSchema(many=True)


class Users(UsersBase):
    """Users table — authentication and user management."""

    __tablename__ = "users"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    user_name = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean(), default=False)
    is_active = Column(Boolean(), default=True)
    must_change_password = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"User Name: {self.user_name}"

    def __str__(self):
        return f"User {self.id}: {self.user_name}"

    def set_password(self, password: str):
        """Hashes a plaintext password and stores it."""
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(
            password_bytes, salt
        ).decode("utf-8")

    def check_password_correction(self, attempted_password: str) -> bool:
        """Checks a plaintext password against the stored bcrypt hash."""
        try:
            return bcrypt.checkpw(
                attempted_password.encode("utf-8"),
                self.password_hash.encode("utf-8"),
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

    def __repr__(self):
        return f"Audit {self.id}: {self.action} {self.table_name}"


# ----- Audit plumbing -----
# Columns never worth recording: file_data would put every byte of every
# attachment into the log.
_AUDIT_SKIP_COLUMNS = {"file_data"}

# Tables the listener watches. AUDIT itself is excluded -- it is
# append-only and must never audit its own writes.
_AUDITED_TABLES = {
    "CASES": "CASENUMBER",
    "AGENTS": "AGENTNAME",
    "ROOMS": "ROOMLABEL",
    "EVIDENCE": "EVIDNUM",
    "PERSONS": "SUSPECTNAME",
    "NOTES": "NOTEAUTHOR",
    "files": "file_name",
}


def audit_timestamp() -> str:
    """UTC, ISO-8601, explicitly marked. Never local time."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def current_actor() -> str:
    """The signed-in user, or a marker when there is no web session.

    Never raises: an audit record with an uncertain actor is worth far
    more than a failed save.
    """
    try:
        from nicegui import app
        name = app.storage.user.get("user_name", "")
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
        AuditLog(
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
            AuditLog(
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


DEFAULT_USER_PASSWORD = "Vector2026!"


# ----- Schema Migration -----
# Columns that used to carry UNIQUE and no longer should. SQLite cannot
# drop an implicit unique index, so the table has to be rebuilt.
_UNIQUE_DROPPED = {
    "AGENTS": {"AGENTPHONE", "AGENTEMAIL"},
    "ROOMS": {"ROOMDESC"},
    "files": {"file_data"},
}


def _stale_unique_columns(connection, table_name: str) -> set:
    """Returns the columns on `table_name` still carrying UNIQUE."""
    from sqlalchemy import text

    exists = connection.execute(
        text(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name=:name"
        ),
        {"name": table_name},
    ).scalar()
    if not exists:
        return set()

    stale = set()
    for row in connection.execute(text(f'PRAGMA index_list("{table_name}")')):
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
        "files": [
            ("sha256", "VARCHAR(64)"),
            ("hashed_at", "VARCHAR"),
        ],
    }

    with engine.begin() as connection:
        for table_name, columns in additions.items():
            exists = connection.execute(
                text(
                    "SELECT 1 FROM sqlite_master "
                    "WHERE type='table' AND name=:name"
                ),
                {"name": table_name},
            ).scalar()
            if not exists:
                continue

            present = {
                row[1]
                for row in connection.execute(
                    text(f'PRAGMA table_info("{table_name}")')
                )
            }
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
    import shutil
    from sqlalchemy import text

    with engine.connect() as connection:
        pending = {
            name: _stale_unique_columns(connection, name)
            for name in _UNIQUE_DROPPED
        }
    pending = {name: cols for name, cols in pending.items() if cols}

    if not pending:
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = APP_DB_PATH.with_suffix(f".db.bak-{stamp}")
    shutil.copy2(APP_DB_PATH, backup)
    print(f"Schema migration: backed up case database to {backup.name}")

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


# ----- Table Creation -----
def init_db():
    """Initialize both databases."""
    Base.metadata.create_all(engine)

    # Create ONLY the Users table in users.db
    UsersBase.metadata.create_all(users_engine)

    # Bring an existing case database up to the current schema.
    _add_missing_columns()
    migrate_schema()


# ----- Convenience Context Manager -----
from contextlib import contextmanager

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
