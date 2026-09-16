#!/usr/bin/env python3

"""
encrypt_database.py

Converts the case databases from plaintext SQLite to SQLCipher.

    .venv/bin/python tools/encrypt_database.py            (macOS / Linux)
    .venv\\Scripts\\python tools\\encrypt_database.py       (Windows)

READ THIS FIRST. There is no recovery. No reset, no backdoor, no key
escrow. If the passphrase is lost the case is lost -- not delayed,
lost. Record it somewhere your unit already trusts with credentials
before you run this.

What it does, in order:

  1. refuses to run while VECTOR is open, or on an already-encrypted
     database
  2. takes the passphrase twice and checks it is not trivially weak
  3. copies each database to a timestamped .plaintext-backup
  4. writes an encrypted copy with SQLCipher's sqlcipher_export()
  5. verifies the encrypted copy opens and holds the same row counts
  6. only then replaces the original

If any step fails, nothing is replaced and the backup is left in place.
The backups are unencrypted copies of the case -- delete them once you
have confirmed the encrypted database opens and looks right.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import crypto  # noqa: E402
from program.config import APP_DB_PATH, USERS_DB_PATH  # noqa: E402

TABLES_TO_COUNT = [
    "CASES", "AGENTS", "ROOMS", "EVIDENCE", "PERSONS", "NOTES", "FILES",
    "AUDIT",
]


def row_counts(connection) -> dict:
    """Counts every table present, for before/after comparison."""
    names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    counts = {}
    for name in names:
        if name.startswith("sqlite_"):
            continue
        counts[name] = connection.execute(
            f'SELECT count(*) FROM "{name}"'
        ).fetchone()[0]
    return counts


def wal_files(path: Path) -> list:
    return [
        path.with_name(path.name + suffix) for suffix in ("-wal", "-shm")
    ]


def encrypt_one(path: Path, passphrase: str, stamp: str) -> bool:
    """Encrypts one database in place. Returns True on success."""
    import sqlite3

    sqlcipher3 = crypto.require_sqlcipher()

    if not path.exists():
        print(f"  {path.name}: not present, skipping")
        return True

    if crypto.is_encrypted(path):
        print(f"  {path.name}: already encrypted, skipping")
        return True

    backup = path.with_name(f"{path.name}.plaintext-backup-{stamp}")
    encrypted = path.with_name(f"{path.name}.encrypting")
    encrypted.unlink(missing_ok=True)

    # Checkpoint first: recent writes may still be sitting in the -wal
    # file, and sqlcipher_export() would not carry them over.
    plain = sqlite3.connect(str(path))
    plain.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    before = row_counts(plain)
    plain.close()

    shutil.copy2(path, backup)
    print(f"  {path.name}: backed up to {backup.name}")

    # No PRAGMA key on the source: it is plaintext, and SQLCipher
    # rejects an empty key rather than treating it as "none".
    source = sqlcipher3.connect(str(path))
    escaped = passphrase.replace("'", "''")
    source.execute(f"ATTACH DATABASE '{encrypted}' AS encrypted KEY '{escaped}'")
    source.execute("SELECT sqlcipher_export('encrypted')")
    source.execute("DETACH DATABASE encrypted")
    source.close()

    # Verify before replacing anything.
    try:
        check = crypto.open_encrypted(encrypted, passphrase)
        after = row_counts(check)
        check.close()
    except Exception as err:
        encrypted.unlink(missing_ok=True)
        print(f"  {path.name}: FAILED to verify -- {err}")
        print(f"  {path.name}: nothing replaced, original untouched")
        return False

    if before != after:
        encrypted.unlink(missing_ok=True)
        print(f"  {path.name}: FAILED -- row counts differ")
        print(f"    before: {before}")
        print(f"    after : {after}")
        print(f"  {path.name}: nothing replaced, original untouched")
        return False

    for leftover in wal_files(path):
        leftover.unlink(missing_ok=True)
    path.unlink()
    encrypted.rename(path)

    total = sum(before.values())
    print(f"  {path.name}: encrypted, {total} rows verified")
    return True


def main() -> None:
    if not crypto.sqlcipher_available():
        print(
            "The SQLCipher driver is not installed.\n\n"
            "    pip install -r requirements-encryption.txt\n"
        )
        sys.exit(1)

    databases = [APP_DB_PATH, USERS_DB_PATH]

    if all(crypto.is_encrypted(p) for p in databases if p.exists()):
        print("Both databases are already encrypted. Nothing to do.")
        return

    for path in databases:
        for leftover in wal_files(path):
            if leftover.exists() and leftover.stat().st_size > 0:
                print(
                    f"{leftover.name} is present and not empty, which "
                    "usually means VECTOR is still running or was not "
                    "closed cleanly.\nClose it and try again."
                )
                sys.exit(1)

    print("=" * 68)
    print("  ENCRYPT THE CASE DATABASE")
    print("=" * 68)
    print("  There is no way to recover a lost passphrase. No reset, no")
    print("  backdoor, no key escrow. If it is lost, so is the case.")
    print()
    print("  Record it somewhere your unit already trusts with")
    print("  credentials BEFORE continuing.")
    print("=" * 68)
    print()

    if input("  Type ENCRYPT to continue: ").strip() != "ENCRYPT":
        print("  Cancelled. Nothing was changed.")
        return

    import getpass

    passphrase = getpass.getpass("\n  Passphrase: ")
    problem = crypto.describe_passphrase_problem(passphrase)
    if problem:
        print(f"\n  {problem}")
        print("  Cancelled. Nothing was changed.")
        return

    if getpass.getpass("  Passphrase again: ") != passphrase:
        print("\n  The two passphrases do not match.")
        print("  Cancelled. Nothing was changed.")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    print("\n  Working...")

    ok = True
    for path in databases:
        if not encrypt_one(path, passphrase, stamp):
            ok = False
            break

    print()
    if not ok:
        print("  Encryption failed. Your databases were not replaced.")
        print("  The .plaintext-backup files are beside them.")
        sys.exit(1)

    print("=" * 68)
    print("  Done. The case databases are encrypted.")
    print("=" * 68)
    print("  VECTOR will now ask for the passphrase at every start.")
    print("  Supply it with VECTOR_DB_KEY, VECTOR_DB_KEY_FILE, or by")
    print("  starting from a terminal.")
    print()
    print("  Start VECTOR and confirm the case looks right, then delete")
    print(f"  db/*.plaintext-backup-{stamp} -- those are unencrypted")
    print("  copies of the case.")
    print("=" * 68)


if __name__ == "__main__":
    main()
