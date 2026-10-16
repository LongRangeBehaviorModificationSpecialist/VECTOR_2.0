#!/usr/bin/env python3

"""
config.py

Holds basic configuration information for the app.

All filesystem paths are derived from this file's location, so VECTOR
behaves identically no matter which directory it is launched from --
a desktop shortcut, a scheduled task or a terminal.
"""

import os
from pathlib import Path


# ----- Project layout -----
# config.py lives in <project>/program/, so the root is two levels up.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# VECTOR_DB_DIR relocates the case database. Point it at an encrypted
# volume (BitLocker, FileVault, VeraCrypt) to protect case data at rest
# -- the database itself is plain SQLite. The test suite uses it to work
# against a temporary directory.
DB_DIR = Path(os.environ["VECTOR_DB_DIR"]).expanduser() \
    if os.environ.get("VECTOR_DB_DIR") else PROJECT_ROOT / "db"
STATIC_DIR = PROJECT_ROOT / "static"
SECRET_FILE = PROJECT_ROOT / ".secret"

APP_DB_PATH = DB_DIR / "app_data.db"
USERS_DB_PATH = DB_DIR / "users.db"
USERS_SEED_PATH = DB_DIR / "users.json"
AGENTS_JSON_PATH = PROJECT_ROOT / "parts" / "agents.json"


def _env_flag(name: str, default: bool = False) -> bool:
    """Reads a boolean from the environment ("1", "true", "yes")."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    """Reads an integer from the environment, falling back on bad input."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    """Application metadata and runtime settings."""

    version = "0.96"
    authors = "SSA M. Sponheimer & SuSA M. Brown"
    dept = "Virginia State Police -- NOVA/DC ICAC"
    url = "github.com/LongRangeBehaviorModificationSpecialist/VECTOR_2.0"
    updated = "15-Oct-2026"

    # ----- Network -----
    # Loopback by default: the app is not reachable from the network
    # unless someone deliberately opts in. See README "Access from
    # another device".
    #   VECTOR_HOST=0.0.0.0  (or --lan) exposes it to the local network.
    HOST = os.environ.get("VECTOR_HOST", "127.0.0.1")
    PORT = _env_int("VECTOR_PORT", 8080)

    # Open a browser window on start. Set VECTOR_NO_BROWSER=1 for
    # headless or always-on machines.
    SHOW_BROWSER = not _env_flag("VECTOR_NO_BROWSER")

    # ----- Encryption -----
    # Refuse to start on a plaintext case database. For units whose
    # policy requires encryption, so a machine cannot quietly run
    # unencrypted after a restore or a fresh checkout.
    REQUIRE_ENCRYPTION = _env_flag("VECTOR_REQUIRE_ENCRYPTION")

    # ----- Uploads -----
    # Rejected in the browser before any bytes reach the server.
    MAX_UPLOAD_BYTES = _env_int("VECTOR_MAX_UPLOAD_MB", 512) * 1024 * 1024

    # Largest export accepted back in through Import. Higher than an
    # attachment, since an export carries every attachment in the case.
    MAX_IMPORT_BYTES = _env_int("VECTOR_MAX_IMPORT_MB", 2048) * 1024 * 1024

    # ----- Sessions -----
    # A tablet left on a kitchen counter at a scene stays signed in to
    # the case until somebody closes the browser. A device nobody has
    # touched for this many minutes signs out, after a warning. Set
    # VECTOR_SESSION_IDLE_MINUTES=0 for a unit whose devices never leave
    # a hand and whose scenes run long.
    SESSION_IDLE_MINUTES = _env_int("VECTOR_SESSION_IDLE_MINUTES", 60)

    # ----- Paths (re-exported for convenience) -----
    PROJECT_ROOT = PROJECT_ROOT
    DB_DIR = DB_DIR
    STATIC_DIR = STATIC_DIR
