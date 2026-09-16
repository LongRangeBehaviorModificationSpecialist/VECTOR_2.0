"""Schema migration.

An existing database has to reach the current schema without losing a
row: old column names renamed in place, columns added since, and the
unique indexes that blocked ordinary scenes rebuilt away. These build
databases on the old schemas and run the real upgrade over them.
"""

import sqlite3

import bcrypt
import pytest
from sqlalchemy.orm import Session as OrmSession

import models


OLD_SCHEMA = """
CREATE TABLE "AGENTS" (
    "Z_PK" INTEGER NOT NULL PRIMARY KEY,
    "AGENTNAME" VARCHAR NOT NULL UNIQUE,
    "AGENTPARENTAGENCY" VARCHAR NOT NULL,
    "AGENTPRIMARYROLE" VARCHAR NOT NULL,
    "AGENTROLESECONDARY" VARCHAR,
    "AGENTPHONE" VARCHAR NOT NULL UNIQUE,
    "AGENTEMAIL" VARCHAR UNIQUE,
    "AGENTNOTE" TEXT,
    "ENTEREDDATETIME" VARCHAR
);
CREATE TABLE "ROOMS" (
    "Z_PK" INTEGER NOT NULL PRIMARY KEY,
    "ROOMLABEL" VARCHAR NOT NULL UNIQUE,
    "ROOMDESC" VARCHAR NOT NULL UNIQUE,
    "ROOMFIRSTAGENT" VARCHAR NOT NULL,
    "ROOMSECONDAGENT" VARCHAR NOT NULL,
    "ROOMNOTE" TEXT,
    "ENTEREDDATETIME" VARCHAR
);
CREATE TABLE "PERSONS" (
    "Z_PK" INTEGER NOT NULL PRIMARY KEY,
    "SUSPECTNAME" VARCHAR NOT NULL UNIQUE,
    "SUSPECTDOB" VARCHAR,
    "SUSPECTADDRESS" VARCHAR,
    "SUSPECTPHONE" VARCHAR,
    "SUSPECTNOTE" TEXT,
    "ENTEREDDATETIME" VARCHAR
);
CREATE TABLE "files" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "file_name" VARCHAR NOT NULL,
    "file_size" INTEGER NOT NULL,
    "file_mime_type" VARCHAR(50),
    "upload_date" DATETIME,
    "file_data" BLOB NOT NULL UNIQUE,
    "uploaded_by" VARCHAR(100) NOT NULL
);
"""

OLD_USERS_SCHEMA = """
CREATE TABLE "users" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "user_name" VARCHAR(100) NOT NULL UNIQUE,
    "password_hash" VARCHAR(255) NOT NULL,
    "is_admin" BOOLEAN,
    "is_active" BOOLEAN,
    "must_change_password" BOOLEAN,
    "created_at" DATETIME
);
"""

LEGACY_PASSWORD = "password-set-before-the-upgrade"


def _unique_columns(path, table):
    connection = sqlite3.connect(path)
    found = set()
    for row in connection.execute(f'PRAGMA index_list("{table}")'):
        if row[2]:
            found |= {
                info[2]
                for info in connection.execute(
                    f'PRAGMA index_info("{row[1]}")'
                )
            }
    connection.close()
    return found


def _columns(path, table):
    connection = sqlite3.connect(path)
    names = {row[1] for row in connection.execute(
        f'PRAGMA table_info("{table}")')}
    connection.close()
    return names


def _table_names(path):
    connection = sqlite3.connect(path)
    names = {row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    connection.close()
    return names


def _engine_for(path):
    return models.create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False},
    )


@pytest.fixture
def legacy_database(tmp_path, monkeypatch):
    """Case and users databases on the pre-migration schemas, with rows."""
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.executescript(OLD_SCHEMA)
    connection.executemany(
        'INSERT INTO "AGENTS" ("AGENTNAME", "AGENTPARENTAGENCY", '
        '"AGENTPRIMARYROLE", "AGENTPHONE", "AGENTEMAIL") '
        "VALUES (?, ?, ?, ?, ?)",
        [
            ("Doe, John", "VSP", "Searcher", "555-0100", "jd@vsp.gov"),
            ("Roe, Jane", "FCPD", "Photographer", "555-0101", "jr@fcpd.gov"),
        ],
    )
    connection.executemany(
        'INSERT INTO "ROOMS" ("ROOMLABEL", "ROOMDESC", "ROOMFIRSTAGENT", '
        '"ROOMSECONDAGENT") VALUES (?, ?, ?, ?)',
        [
            ("A", "Bedroom", "Doe, John", "Roe, Jane"),
            ("B", "Kitchen", "Doe, John", "Roe, Jane"),
        ],
    )
    connection.execute(
        'INSERT INTO "PERSONS" ("SUSPECTNAME", "SUSPECTDOB", '
        '"SUSPECTADDRESS", "SUSPECTNOTE") VALUES (?, ?, ?, ?)',
        ("O'Brien, Sean", "03-02-1984", "14 Elm Street", "Present"),
    )
    connection.execute(
        'INSERT INTO "files" ("file_name", "file_size", "file_mime_type", '
        '"file_data", "uploaded_by") VALUES (?, ?, ?, ?, ?)',
        ("photo.jpg", 5, "image/jpeg", b"bytes", "Doe, John"),
    )
    connection.commit()
    connection.close()

    users_path = tmp_path / "legacy_users.db"
    connection = sqlite3.connect(users_path)
    connection.executescript(OLD_USERS_SCHEMA)
    connection.execute(
        'INSERT INTO "users" ("user_name", "password_hash", "is_admin", '
        '"is_active", "must_change_password") VALUES (?, ?, 1, 1, 0)',
        (
            "legacy.admin",
            bcrypt.hashpw(
                LEGACY_PASSWORD.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8"),
        ),
    )
    connection.commit()
    connection.close()

    # Point the module's engines at these databases for the test.
    engine = _engine_for(path)
    users_engine = _engine_for(users_path)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "APP_DB_PATH", path)
    monkeypatch.setattr(models, "users_engine", users_engine)
    monkeypatch.setattr(models, "USERS_DB_PATH", users_path)

    yield path

    engine.dispose()
    users_engine.dispose()


# ----- The starting point -----

def test_legacy_database_starts_with_the_old_schema(legacy_database):
    assert "AGENTEMAIL" in _unique_columns(legacy_database, "AGENTS")
    assert "ROOMDESC" in _unique_columns(legacy_database, "ROOMS")
    assert "file_data" in _unique_columns(legacy_database, "files")
    assert "SUSPECTNAME" in _columns(legacy_database, "PERSONS")


# ----- Renames -----

def test_person_columns_are_renamed(legacy_database):
    models.upgrade_database()

    columns = _columns(legacy_database, "PERSONS")
    assert {"PERSONNAME", "PERSONDOB", "PERSONADDRESS",
            "PERSONPHONE"} <= columns
    assert not {c for c in columns if c.startswith("SUSPECT")} - {
        "SUSPECTNOTE"
    }

    connection = sqlite3.connect(legacy_database)
    row = connection.execute(
        'SELECT "PERSONNAME", "PERSONDOB", "SUSPECTNOTE" FROM "PERSONS"'
    ).fetchone()
    connection.close()
    assert row == ("O'Brien, Sean", "03-02-1984", "Present")


def test_the_files_table_and_its_columns_are_renamed(legacy_database):
    models.upgrade_database()

    tables = _table_names(legacy_database)
    assert "FILES" in tables
    assert "files" not in tables

    columns = _columns(legacy_database, "FILES")
    assert {"Z_PK", "FILENAME", "FILESIZE", "FILEMIMETYPE",
            "FILEUPLOADDATE", "FILEUPLOADEDBY", "FILEDATA"} <= columns
    assert "file_name" not in columns


def test_user_columns_are_renamed_and_passwords_still_work(legacy_database):
    models.upgrade_database()

    users_path = models.USERS_DB_PATH
    columns = _columns(users_path, "users")
    assert {"Z_PK", "USERNAME", "PASSWORDHASH", "ISADMIN", "ISACTIVE",
            "MUSTCHANGEPASSWORD", "ENTEREDDATETIME"} <= columns

    with OrmSession(models.users_engine) as session:
        user = session.query(models.Users).one()
        assert user.USERNAME == "legacy.admin"
        assert user.ISADMIN is True
        assert user.check_password_correction(LEGACY_PASSWORD) is True


def test_new_columns_are_added_to_an_old_files_table(legacy_database):
    models.upgrade_database()
    columns = _columns(legacy_database, "FILES")
    assert {"FILESHA256", "FILEHASHEDAT", "FILENOTE"} <= columns


# ----- Constraint rebuilds -----

def test_migration_drops_only_the_intended_constraints(legacy_database):
    models.upgrade_database()

    agents = _unique_columns(legacy_database, "AGENTS")
    rooms = _unique_columns(legacy_database, "ROOMS")
    files = _unique_columns(legacy_database, "FILES")

    assert "AGENTEMAIL" not in agents
    assert "AGENTPHONE" not in agents
    assert "ROOMDESC" not in rooms
    assert "FILEDATA" not in files

    # Identity constraints must survive.
    assert "AGENTNAME" in agents
    assert "ROOMLABEL" in rooms
    assert "PERSONNAME" in _unique_columns(legacy_database, "PERSONS")


def test_migration_preserves_every_row(legacy_database):
    models.upgrade_database()

    connection = sqlite3.connect(legacy_database)
    agents = connection.execute(
        'SELECT "AGENTNAME", "AGENTEMAIL" FROM "AGENTS" ORDER BY "AGENTNAME"'
    ).fetchall()
    rooms = connection.execute(
        'SELECT "ROOMLABEL", "ROOMDESC" FROM "ROOMS" ORDER BY "ROOMLABEL"'
    ).fetchall()
    files = connection.execute(
        'SELECT "FILENAME", "FILEDATA", "FILEUPLOADEDBY" FROM "FILES"'
    ).fetchall()
    connection.close()

    assert agents == [
        ("Doe, John", "jd@vsp.gov"),
        ("Roe, Jane", "jr@fcpd.gov"),
    ]
    assert rooms == [("A", "Bedroom"), ("B", "Kitchen")]
    assert files == [("photo.jpg", b"bytes", "Doe, John")]


# ----- Safety -----

def test_the_first_backup_is_of_the_untouched_database(legacy_database):
    models.upgrade_database()

    backups = sorted(legacy_database.parent.glob("legacy.db.bak-*"))
    assert backups
    assert "file_name" in _columns(backups[0], "files")
    assert "SUSPECTNAME" in _columns(backups[0], "PERSONS")

    user_backups = list(
        legacy_database.parent.glob("legacy_users.db.bak-*")
    )
    assert len(user_backups) == 1
    assert "user_name" in _columns(user_backups[0], "users")


def test_upgrade_is_a_no_op_second_time(legacy_database):
    models.upgrade_database()
    first = set(legacy_database.parent.glob("*.bak-*"))

    models.upgrade_database()
    second = set(legacy_database.parent.glob("*.bak-*"))

    # No new backup means nothing was rewritten.
    assert first == second


def test_a_current_database_is_left_alone(tmp_path, monkeypatch):
    path = tmp_path / "current.db"
    engine = _engine_for(path)
    models.Base.metadata.create_all(engine)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "APP_DB_PATH", path)

    try:
        models.upgrade_database()
    finally:
        engine.dispose()

    assert not list(tmp_path.glob("*.bak-*"))


def test_the_backup_includes_writes_still_in_the_wal(tmp_path, monkeypatch):
    """In WAL mode recent writes sit in the -wal file. A backup that
    copied only the .db would silently leave them out."""
    path = tmp_path / "wal.db"
    writer = sqlite3.connect(path)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("PRAGMA wal_autocheckpoint=0")
    writer.execute(
        'CREATE TABLE "PERSONS" ("Z_PK" INTEGER PRIMARY KEY, '
        '"SUSPECTNAME" VARCHAR NOT NULL, "SUSPECTNOTE" TEXT)'
    )
    writer.execute(
        'INSERT INTO "PERSONS" ("SUSPECTNAME") VALUES (?)', ("Late, Entry",)
    )
    writer.commit()
    # Held open, so nothing has folded the log into the database yet.
    assert (tmp_path / "wal.db-wal").stat().st_size > 0

    engine = _engine_for(path)
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "APP_DB_PATH", path)
    try:
        models._rename_legacy_schema()
    finally:
        writer.close()
        engine.dispose()

    backup = next(tmp_path.glob("wal.db.bak-*"))
    connection = sqlite3.connect(backup)
    names = connection.execute(
        'SELECT "SUSPECTNAME" FROM "PERSONS"'
    ).fetchall()
    connection.close()
    assert names == [("Late, Entry",)]
