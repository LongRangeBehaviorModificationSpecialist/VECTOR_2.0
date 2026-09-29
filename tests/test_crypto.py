"""
test_crypto.py

At-rest encryption.

The tests that need SQLCipher skip themselves when the driver is not
installed, so the suite still runs on a machine without it -- which is
the same machine on which encryption is optional.
"""

import sqlite3

import pytest

import crypto


requires_sqlcipher = pytest.mark.skipif(
    not crypto.sqlcipher_available(),
    reason="SQLCipher driver not installed (encryption is optional)",
)


# ----- Detection -----

def test_a_plaintext_database_is_detected(tmp_path):
    path = tmp_path / "plain.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE t (v TEXT)")
    connection.commit()
    connection.close()
    assert crypto.is_encrypted(path) is False


def test_a_missing_database_is_not_encrypted(tmp_path):
    assert crypto.is_encrypted(tmp_path / "absent.db") is False


def test_an_empty_file_is_not_encrypted(tmp_path):
    path = tmp_path / "empty.db"
    path.touch()
    assert crypto.is_encrypted(path) is False


@requires_sqlcipher
def test_an_encrypted_database_is_detected(tmp_path):
    import sqlcipher3

    path = tmp_path / "sealed.db"
    connection = sqlcipher3.connect(str(path))
    connection.execute(crypto.key_pragma("a good long passphrase"))
    connection.execute("CREATE TABLE t (v TEXT)")
    connection.commit()
    connection.close()
    assert crypto.is_encrypted(path) is True


# ----- Passphrase handling -----

@pytest.mark.parametrize(
    "passphrase",
    [
        "it's got an apostrophe",
        "it''s got two",
        'double "quotes" as well',
        "back\\slashes and /slashes",
        "; DROP TABLE CASES; --",
        "unicode: naïve café £20",
    ],
)
@requires_sqlcipher
def test_awkward_passphrases_round_trip(tmp_path, passphrase):
    """PRAGMA takes no bound parameters, so the escaping is ours to get
    right. A passphrase must never need to avoid a character.
    """
    import sqlcipher3

    path = tmp_path / "sealed.db"
    connection = sqlcipher3.connect(str(path))
    connection.execute(crypto.key_pragma(passphrase))
    connection.execute("CREATE TABLE t (v TEXT)")
    connection.execute("INSERT INTO t VALUES ('marker')")
    connection.commit()
    connection.close()

    reopened = crypto.open_encrypted(path, passphrase)
    assert reopened.execute("SELECT v FROM t").fetchone()[0] == "marker"
    reopened.close()


@requires_sqlcipher
def test_a_near_miss_passphrase_is_refused(tmp_path):
    import sqlcipher3

    path = tmp_path / "sealed.db"
    connection = sqlcipher3.connect(str(path))
    connection.execute(crypto.key_pragma("the right passphrase"))
    connection.execute("CREATE TABLE t (v TEXT)")
    connection.commit()
    connection.close()

    assert crypto.verify_passphrase(path, "the right passphras") is False
    assert crypto.verify_passphrase(path, "the right passphrase ") is False
    assert crypto.verify_passphrase(path, "the right passphrase") is True


@requires_sqlcipher
def test_wrong_passphrase_raises_wrongkey(tmp_path):
    import sqlcipher3

    path = tmp_path / "sealed.db"
    connection = sqlcipher3.connect(str(path))
    connection.execute(crypto.key_pragma("the right passphrase"))
    connection.execute("CREATE TABLE t (v TEXT)")
    connection.commit()
    connection.close()

    with pytest.raises(crypto.WrongKey):
        crypto.open_encrypted(path, "something else")


# ----- What encryption actually protects -----

@requires_sqlcipher
def test_case_data_is_not_readable_in_the_raw_file(tmp_path):
    """The whole point: a suspect's details must not be sitting in the
    file in the clear.
    """
    import sqlcipher3

    path = tmp_path / "case.db"
    connection = sqlcipher3.connect(str(path))
    connection.execute(crypto.key_pragma("a good long passphrase"))
    connection.execute("CREATE TABLE PERSONS (name TEXT, dob TEXT)")
    connection.execute(
        "INSERT INTO PERSONS VALUES (?, ?)",
        ("Fictional, Jordan", "1985-04-17"),
    )
    connection.commit()
    connection.close()

    raw = path.read_bytes()
    assert b"Fictional, Jordan" not in raw
    assert b"1985-04-17" not in raw
    assert not raw.startswith(crypto.SQLITE_MAGIC)


@requires_sqlcipher
def test_a_sqlite_browser_cannot_open_it(tmp_path):
    import sqlcipher3

    path = tmp_path / "case.db"
    connection = sqlcipher3.connect(str(path))
    connection.execute(crypto.key_pragma("a good long passphrase"))
    connection.execute("CREATE TABLE PERSONS (name TEXT)")
    connection.commit()
    connection.close()

    with pytest.raises(sqlite3.DatabaseError):
        sqlite3.connect(path).execute("SELECT * FROM PERSONS").fetchall()


# ----- Passphrase quality -----

def test_a_short_passphrase_is_rejected():
    assert crypto.describe_passphrase_problem("short") != ""


def test_padded_passphrase_is_rejected():
    """Trailing spaces vanish when a passphrase is written down."""
    assert crypto.describe_passphrase_problem("a good passphrase ") != ""


def test_a_reasonable_passphrase_is_accepted():
    assert crypto.describe_passphrase_problem(
        "four unrelated words here"
    ) == ""


# ----- Key resolution -----

def test_the_environment_variable_is_preferred(monkeypatch):
    monkeypatch.setenv("VECTOR_DB_KEY", "from the environment")
    assert crypto.resolve_passphrase() == "from the environment"


def test_a_key_file_is_read_and_stripped(tmp_path, monkeypatch):
    key_file = tmp_path / "case.key"
    key_file.write_text("  from the key file  \n", encoding="utf-8")
    monkeypatch.delenv("VECTOR_DB_KEY", raising=False)
    monkeypatch.setenv("VECTOR_DB_KEY_FILE", str(key_file))
    assert crypto.resolve_passphrase() == "from the key file"


def test_a_missing_key_file_says_so(tmp_path, monkeypatch):
    """Most likely the USB stick holding it is not plugged in."""
    monkeypatch.delenv("VECTOR_DB_KEY", raising=False)
    monkeypatch.setenv("VECTOR_DB_KEY_FILE", str(tmp_path / "absent.key"))
    with pytest.raises(crypto.KeyRequired):
        crypto.resolve_passphrase()


def test_an_empty_key_file_says_so(tmp_path, monkeypatch):
    key_file = tmp_path / "case.key"
    key_file.write_text("   \n", encoding="utf-8")
    monkeypatch.delenv("VECTOR_DB_KEY", raising=False)
    monkeypatch.setenv("VECTOR_DB_KEY_FILE", str(key_file))
    with pytest.raises(crypto.KeyRequired):
        crypto.resolve_passphrase()


def test_prompting_can_be_disabled(monkeypatch):
    """A shortcut or scheduled task has no console; getpass on Windows
    reads the console directly, so it would hang with nothing on
    screen.
    """
    monkeypatch.delenv("VECTOR_DB_KEY", raising=False)
    monkeypatch.delenv("VECTOR_DB_KEY_FILE", raising=False)
    monkeypatch.setenv("VECTOR_NO_PROMPT", "1")
    assert crypto.can_prompt() is False
    assert crypto.resolve_passphrase() == ""
