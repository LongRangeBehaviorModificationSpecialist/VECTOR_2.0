#!/usr/bin/env python3

"""
decrypt_database.py

Converts the case databases back to plaintext SQLite.

    .venv/bin/python tools/decrypt_database.py            (macOS / Linux)
    .venv\\Scripts\\python tools\\decrypt_database.py       (Windows)

The reverse of encrypt_database.py, and it exists for a reason: a case
that can only be opened by one build of one tool is a liability. Use it
to hand a case to an examiner without the SQLCipher driver, to run
another tool against the file, or to step back if encryption turns out
not to suit how the unit works.

It verifies the result before replacing anything, and leaves the
encrypted original as a timestamped backup.

The output is readable by anyone with the file. Decrypt onto an
encrypted volume, or delete the plaintext copy once you are finished
with it.
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import crypto  # noqa: E402
from program.config import APP_DB_PATH, USERS_DB_PATH  # noqa: E402


def row_counts(connection) -> dict:
    names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ]
    return {
        name: connection.execute(
            f'SELECT count(*) FROM "{name}"'
        ).fetchone()[0]
        for name in names
        if not name.startswith("sqlite_")
    }


def decrypt_one(path: Path, passphrase: str, stamp: str) -> bool:
    """Decrypts one database in place. Returns True on success."""
    import sqlite3

    crypto.require_sqlcipher()

    if not path.exists():
        print(f"  {path.name}: not present, skipping")
        return True

    if not crypto.is_encrypted(path):
        print(f"  {path.name}: already plaintext, skipping")
        return True

    backup = path.with_name(f"{path.name}.encrypted-backup-{stamp}")
    plain = path.with_name(f"{path.name}.decrypting")
    plain.unlink(missing_ok=True)

    try:
        source = crypto.open_encrypted(path, passphrase)
    except crypto.WrongKey:
        print(f"  {path.name}: that passphrase did not open it")
        return False

    before = row_counts(source)

    source.execute(f"ATTACH DATABASE '{plain}' AS plaintext KEY ''")
    source.execute("SELECT sqlcipher_export('plaintext')")
    source.execute("DETACH DATABASE plaintext")
    source.close()

    try:
        check = sqlite3.connect(str(plain))
        after = row_counts(check)
        check.close()
    except Exception as err:
        plain.unlink(missing_ok=True)
        print(f"  {path.name}: FAILED to verify -- {err}")
        return False

    if before != after:
        plain.unlink(missing_ok=True)
        print(f"  {path.name}: FAILED -- row counts differ")
        print(f"    before: {before}")
        print(f"    after : {after}")
        return False

    shutil.copy2(path, backup)
    for suffix in ("-wal", "-shm"):
        path.with_name(path.name + suffix).unlink(missing_ok=True)
    path.unlink()
    plain.rename(path)

    print(
        f"  {path.name}: decrypted, {sum(before.values())} rows verified "
        f"(encrypted copy kept as {backup.name})"
    )
    return True


def main() -> None:
    if not crypto.sqlcipher_available():
        print(
            "The SQLCipher driver is not installed, so an encrypted "
            "database cannot be read.\n\n"
            "    pip install -r requirements-encryption.txt\n"
        )
        sys.exit(1)

    databases = [APP_DB_PATH, USERS_DB_PATH]

    if not any(crypto.is_encrypted(p) for p in databases if p.exists()):
        print("Neither database is encrypted. Nothing to do.")
        return

    print("  " + "=" * 68)
    print("  DECRYPT THE CASE DATABASE")
    print("  " + "=" * 68)
    print("  The result is an ordinary SQLite file. A suspect's name,")
    print("  address and date of birth will be readable by anyone with")
    print("  the file, and photographs can be extracted from it.")
    print()
    print("  Decrypt onto an encrypted volume, or delete the plaintext")
    print("  copy when you are finished with it.")
    print("  " + "=" * 68)
    print()

    if input("  Type DECRYPT to continue: ").strip() != "DECRYPT":
        print("  Cancelled. Nothing was changed.")
        return

    import getpass

    passphrase = getpass.getpass("\n  Passphrase: ")
    if not passphrase:
        print("  No passphrase given. Cancelled.")
        return

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    print("\n  Working...")

    ok = True
    for path in databases:
        if not decrypt_one(path, passphrase, stamp):
            ok = False
            break

    print()
    if not ok:
        print("  Decryption failed. Your databases were not replaced.")
        sys.exit(1)

    print("  Done. The case databases are plaintext again.")
    print("  Unset VECTOR_DB_KEY / VECTOR_DB_KEY_FILE before starting.")


if __name__ == "__main__":
    main()
