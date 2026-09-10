"""Schema migration.

An existing case database keeps its old unique indexes until the table
is rebuilt, so migrate_schema() has to do that without losing a row.
This builds a database with the pre-migration schema and runs the real
migration over it.
"""

import sqlite3

import pytest

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


@pytest.fixture
def legacy_database(tmp_path, monkeypatch):
    """A database on the pre-migration schema, with rows in it."""
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
        'INSERT INTO "files" ("file_name", "file_size", "file_mime_type", '
        '"file_data", "uploaded_by") VALUES (?, ?, ?, ?, ?)',
        ("photo.jpg", 5, "image/jpeg", b"bytes", "Doe, John"),
    )
    connection.commit()
    connection.close()

    # Point the module's engine at this database for the test.
    engine = models.create_engine(
        f"sqlite:///{path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(models, "engine", engine)
    monkeypatch.setattr(models, "APP_DB_PATH", path)
    return path


def test_legacy_database_starts_with_the_old_constraints(legacy_database):
    assert "AGENTEMAIL" in _unique_columns(legacy_database, "AGENTS")
    assert "ROOMDESC" in _unique_columns(legacy_database, "ROOMS")
    assert "file_data" in _unique_columns(legacy_database, "files")


def test_migration_drops_only_the_intended_constraints(legacy_database):
    models.migrate_schema()

    agents = _unique_columns(legacy_database, "AGENTS")
    rooms = _unique_columns(legacy_database, "ROOMS")
    files = _unique_columns(legacy_database, "files")

    assert "AGENTEMAIL" not in agents
    assert "AGENTPHONE" not in agents
    assert "ROOMDESC" not in rooms
    assert "file_data" not in files

    # Identity constraints must survive.
    assert "AGENTNAME" in agents
    assert "ROOMLABEL" in rooms


def test_migration_preserves_every_row(legacy_database):
    models.migrate_schema()

    connection = sqlite3.connect(legacy_database)
    agents = connection.execute(
        'SELECT "AGENTNAME", "AGENTEMAIL" FROM "AGENTS" ORDER BY "AGENTNAME"'
    ).fetchall()
    rooms = connection.execute(
        'SELECT "ROOMLABEL", "ROOMDESC" FROM "ROOMS" ORDER BY "ROOMLABEL"'
    ).fetchall()
    files = connection.execute(
        'SELECT "file_name", "file_data" FROM "files"'
    ).fetchall()
    connection.close()

    assert agents == [
        ("Doe, John", "jd@vsp.gov"),
        ("Roe, Jane", "jr@fcpd.gov"),
    ]
    assert rooms == [("A", "Bedroom"), ("B", "Kitchen")]
    assert files == [("photo.jpg", b"bytes")]


def test_migration_writes_a_backup(legacy_database):
    models.migrate_schema()
    backups = list(legacy_database.parent.glob("legacy.db.bak-*"))
    assert len(backups) == 1
    assert backups[0].stat().st_size > 0


def test_migration_is_a_no_op_second_time(legacy_database):
    models.migrate_schema()
    first = set(legacy_database.parent.glob("legacy.db.bak-*"))

    models.migrate_schema()
    second = set(legacy_database.parent.glob("legacy.db.bak-*"))

    # No second backup means no second rebuild.
    assert first == second


def test_new_columns_are_added_to_an_old_files_table(legacy_database):
    assert "sha256" not in _columns(legacy_database, "files")
    models._add_missing_columns()
    assert "sha256" in _columns(legacy_database, "files")
    assert "hashed_at" in _columns(legacy_database, "files")
