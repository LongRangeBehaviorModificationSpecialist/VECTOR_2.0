#!/usr/bin/env python3

"""
crypto.py

At-rest encryption for the case database, via SQLCipher.

Without this the database is ordinary SQLite: a suspect's name, address
and date of birth are readable in a text editor, and a photograph can be
carved straight out of the file. Encryption is opt-in -- an existing
install keeps working untouched until someone runs
tools/encrypt_database.py.

WHAT IT PROTECTS. A laptop that is lost, stolen, or handed in for
repair, and a backup copied somewhere it should not have gone. The
database is unreadable without the passphrase.

WHAT IT DOES NOT PROTECT. Anything while VECTOR is running and unlocked:
the passphrase is in memory, reports render in the browser, exports are
written in the clear unless you also encrypt them. It is not a substitute
for full-disk encryption, and it does not protect a machine someone is
sitting in front of.

THE PASSPHRASE CANNOT BE RECOVERED. There is no reset, no backdoor and
no key escrow. A forgotten passphrase means the case is gone. Record it
somewhere your unit already trusts with credentials, before you encrypt
anything.
"""

import os
import sys
from pathlib import Path

# An unencrypted SQLite file starts with this. An encrypted one starts
# with its random salt, so the header is the reliable way to tell them
# apart without a passphrase.
SQLITE_MAGIC = b"SQLite format 3\x00"

MIN_PASSPHRASE_LENGTH = 12


class EncryptionUnavailable(RuntimeError):
    """SQLCipher is needed but not installed."""


class KeyRequired(RuntimeError):
    """The database is encrypted and no passphrase was supplied."""


class WrongKey(RuntimeError):
    """The passphrase did not open the database."""


def sqlcipher_available() -> bool:
    """True when the sqlcipher3 driver can be imported."""
    try:
        import sqlcipher3  # noqa: F401
        return True
    except ImportError:
        return False


def require_sqlcipher():
    """Returns the sqlcipher3 module, or explains how to install it."""
    try:
        import sqlcipher3
        return sqlcipher3
    except ImportError as err:
        raise EncryptionUnavailable(
            "This database is encrypted, but the SQLCipher driver is not "
            "installed.\n\n"
            "    pip install -r requirements-encryption.txt\n\n"
            "Prebuilt packages exist for Windows and Apple Silicon. On "
            "Intel Mac or Linux it is built from source and needs a C "
            "compiler and the OpenSSL headers."
        ) from err


def is_encrypted(path) -> bool:
    """Whether a database file is encrypted.

    A missing or empty file is not encrypted -- it does not exist yet.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return False
    with open(path, "rb") as handle:
        return handle.read(16) != SQLITE_MAGIC


def key_pragma(passphrase: str) -> str:
    """Builds the PRAGMA that unlocks a database.

    PRAGMA does not accept bound parameters, so the passphrase goes in
    as a SQL string literal with single quotes doubled -- the complete
    escape for SQLite. The passphrase form is used deliberately: a raw
    hex key would skip SQLCipher's key derivation, and a short
    passphrase would become a short key with no stretching.
    """
    return "PRAGMA key = '" + passphrase.replace("'", "''") + "'"


def resolve_passphrase(prompt: str = "Case database passphrase: ") -> str:
    """Finds the passphrase, in order of preference.

    1. VECTOR_DB_KEY           -- convenient, but it ends up in whatever
                                  script or shortcut sets it
    2. VECTOR_DB_KEY_FILE      -- a file, ideally on removable media that
                                  travels separately from the laptop
    3. an interactive prompt   -- nothing is stored, but it needs someone
                                  at a console when the app starts

    Returns "" when none is available; the caller decides whether that
    is fatal.
    """
    from_env = os.environ.get("VECTOR_DB_KEY")
    if from_env:
        return from_env

    key_file = os.environ.get("VECTOR_DB_KEY_FILE")
    if key_file:
        candidate = Path(key_file).expanduser()
        if not candidate.exists():
            raise KeyRequired(
                f"VECTOR_DB_KEY_FILE points at {candidate}, which does "
                "not exist.\nIf the key is on removable media, check it "
                "is connected."
            )
        passphrase = candidate.read_text(encoding="utf-8").strip()
        if not passphrase:
            raise KeyRequired(f"The key file {candidate} is empty.")
        return passphrase

    if can_prompt():
        import getpass
        return getpass.getpass(prompt)

    return ""


def can_prompt() -> bool:
    """Whether it is safe to ask for the passphrase interactively.

    On Windows getpass reads the console handle directly rather than
    stdin, so redirecting stdin does not stop it blocking. A launch with
    no console -- a desktop shortcut, a scheduled task, a service --
    would hang forever with nothing on screen to explain why.

    VECTOR_NO_PROMPT=1 disables prompting outright, which is what such a
    launcher should set; the passphrase then has to come from
    VECTOR_DB_KEY or VECTOR_DB_KEY_FILE.
    """
    if os.environ.get("VECTOR_NO_PROMPT", "").strip().lower() in (
        "1", "true", "yes", "on"
    ):
        return False

    try:
        return bool(
            sys.stdin is not None
            and sys.stdin.isatty()
            and sys.stdout is not None
            and sys.stdout.isatty()
        )
    except Exception:
        return False


def open_encrypted(path, passphrase: str):
    """Opens an encrypted database, or says clearly why it could not."""
    sqlcipher3 = require_sqlcipher()

    connection = sqlcipher3.connect(str(path), check_same_thread=False)
    connection.execute(key_pragma(passphrase))
    try:
        # Any read forces SQLCipher to derive the key and verify the
        # page HMAC. Until something is read, a wrong passphrase looks
        # like success.
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except Exception as err:
        connection.close()
        raise WrongKey(
            "That passphrase did not open the case database.\n"
            "SQLCipher prints its own decryption errors above; they mean "
            "the same thing."
        ) from err
    return connection


def verify_passphrase(path, passphrase: str) -> bool:
    """True when the passphrase opens the database."""
    try:
        connection = open_encrypted(path, passphrase)
        connection.close()
        return True
    except (WrongKey, EncryptionUnavailable):
        return False


def describe_passphrase_problem(passphrase: str) -> str:
    """Returns a reason the passphrase is unsuitable, or ""."""
    if len(passphrase) < MIN_PASSPHRASE_LENGTH:
        return (
            f"Too short. Use at least {MIN_PASSPHRASE_LENGTH} characters; "
            "a few unrelated words are easier to remember and harder to "
            "guess than one mangled word."
        )
    if passphrase.strip() != passphrase:
        return (
            "Leading or trailing spaces are too easy to lose when this is "
            "written down or copied. Remove them."
        )
    return ""
