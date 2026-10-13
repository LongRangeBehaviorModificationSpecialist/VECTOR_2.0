#!/usr/bin/env python3

"""
files_page.py — File upload and management page.

Stores files as BLOBs in the SQLite database with download and delete capability.
"""

from urllib.parse import quote

from fastapi import Response
from nicegui import app, ui

from models import (
    audit_timestamp,
    get_session,
    has_active_case,
    record_audit,
    UploadedFiles,
)
from program.config import Config
from failures import explain, log
from live import refresh_on_change
from navbar import build_navbar
from auth import get_current_user_name, get_is_admin, is_authenticated
from utils import (
    derive_mime_type,
    get_mime_type,
    is_allowed_file,
    format_file_size,
    confirm_delete_all,
    require_active_case,
    ALLOWED_MIME_TYPES,
    CONFIRM_TIMEOUT,
    WARN_TIMEOUT,
)

DOWNLOAD_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "sandbox",   # even if opened inline, no scripts run
    "Cache-Control": "no-store",            # don't leave evidence in browser/proxy caches
}

# ----- Downloads -----
def content_disposition(filename: str) -> str:
    """An attachment header that keeps the file's own name, accents and all."""
    fallback = "".join(
        char if 32 <= ord(char) < 127 and char not in '"\\' else "_"
        for char in filename
    ) or "attachment"
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename)}"


@app.get("/attachments/{file_id}")
async def download_attachment(file_id: int) -> Response:
    """Sends one attachment straight from the database to the browser.

    A download used to write the file to the temp folder first and hand
    the browser that copy, and nothing ever removed it -- an unencrypted
    copy of the evidence left on disk even when the database itself is
    encrypted. Signed-in users only, like every page.
    """
    if not is_authenticated():
        return Response(status_code=403)

    with get_session() as session:
        record = session.get(UploadedFiles, file_id)
        if record is None:
            return Response(status_code=404)

        name = (record.FILENAME or f"file_{record.Z_PK}")
        name = name.replace("/", "_").replace("\\", "_")

        stored = record.FILEMIMETYPE or ""
        media_type = (
            stored if stored in ALLOWED_MIME_TYPES
            else "application/octet-stream"
        )

        record_audit(
            session,
            action="DOWNLOAD",
            table_name="FILES",
            row_pk=record.Z_PK,
            summary=f"{name} (SHA-256 {record.FILESHA256 or 'n/a'})",
            actor=get_current_user_name(),
        )

        return Response(
            content=record.FILEDATA,
            media_type=media_type,
            headers={
                "Content-Disposition": content_disposition(name),
                **DOWNLOAD_SECURITY_HEADERS,
            },
        )


# ----- Main Page Builder -----
def build_uploads_page() -> None:
    """Builds the full File Upload page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "File Upload & Management"
        ).classes("text-2xl font-bold m-4")

        # The card is drawn above the list it refreshes, so the list's
        # own refresh is handed to it once both exist.
        refresh = {"files": lambda: None}

        upload_card(lambda: refresh["files"]())
        refresh["files"] = files_table()

    # ----- Initial render -----
    refresh["files"]()

    # Files added or removed on another device appear without a reload.
    refresh_on_change(refresh["files"])
