#!/usr/bin/env python3

"""
file_upload.py

The card that puts a photograph or a document into the case: the file
picker, the camera button beside it on a tablet, and what happens to the
bytes when they arrive -- the size and type checks, the SHA-256 taken at
that moment, and the row written to the database.

It was the first two hundred lines of a 432-line page builder, above the
list it refreshes. The refresh is handed in now rather than reached for.

parts/files_page.py draws it; nothing else does.
"""

import hashlib
from typing import Callable

from nicegui import ui

from failures import explain, log
from models import (
    audit_timestamp,
    get_session,
    UploadedFiles,
)
from program.config import Config
from auth import get_current_user_name, require_session
from utils import (
    WARN_TIMEOUT,
    ZERO_TIMEOUT,
    derive_mime_type,
    is_allowed_file,
    require_active_case,
    require_same_case,
)


def upload_card(refresh_files: Callable[[], None], opened_on: str) -> None:
    """Draws the upload card. refresh_files redraws the list below it;
    opened_on is the case the page was opened on, which a file finishing
    its upload after Start New Case on another tablet must not land in."""
    with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

        ui.label(
            "Upload New File"
        ).classes("text-lg font-semibold mb-2")

        ui.label(
            "Allowed file types → (1) Images, (2) Videos, (3) Documents, "
            "and (4) Archive files."
        ).classes("text-sm text-gray-400 mb-2")

        @require_session
        @require_active_case
        @require_same_case(opened_on)
        async def handle_upload(e) -> None:
            """Handles file upload from ui.upload component."""

            try:
                uploaded_file = e.file
                file_name = uploaded_file.name
                # read() is the public API and works for both the
                # in-memory and spooled-to-disk cases. The private
                # _data attribute only exists on small uploads, so
                # reading it failed for anything over ~1 MB.
                file_data = await uploaded_file.read()
                file_size = len(file_data)
                # From the file's own content, never from what the
                # browser says it is.
                file_mime_type = derive_mime_type(file_name, file_data)

                # Validate file type
                if not is_allowed_file(file_mime_type):
                    ui.notify(
                        f"'{file_name}' is not an allowed file type "
                        f"({file_mime_type}). "
                        f"Only images, videos, documents, and archives "
                        "are permitted.",
                        type="warning",
                        timeout=WARN_TIMEOUT,
                        position="center",
                        close_button="OK",
                    )
                    return

                uploader = get_current_user_name()

                # Hashed on arrival, not at export time: the stored
                # digest then certifies the file as collected rather
                # than whatever the database holds later.
                digest = hashlib.sha256(file_data).hexdigest().upper()
                hashed_at = audit_timestamp()

                with get_session() as session:
                    new_file = UploadedFiles(
                        FILENAME=file_name,
                        FILEDATA=file_data,
                        FILESIZE=file_size,
                        FILEMIMETYPE=file_mime_type,
                        FILEUPLOADEDBY=uploader,
                        FILESHA256=digest,
                        FILEHASHEDDATETIME=hashed_at,
                    )
                    session.add(new_file)

                ui.notify(
                    f"'{file_name}' uploaded ({file_size:,} bytes, "
                    f"{file_mime_type}).\n"
                    f"SHA-256: {digest}",
                    timeout=WARN_TIMEOUT,
                    position="bottom",
                    close_button="OK",
                )

                refresh_files()

            except Exception as err:
                name = getattr(e.file, "name", "") or "the file"
                log.exception("Could not upload %s", name)
                ui.notify(
                    f"Could not upload {name}.\n\n{explain(err)}",
                    multi_line=True,
                    classes="multi-line-notification",
                    type="warning",
                    timeout=ZERO_TIMEOUT,
                    position="center",
                    close_button="OK",
                )

        ui.upload(
            on_upload=handle_upload,
            auto_upload=True,
            label="Drag files here or click to browse",
            multiple=True,
            max_file_size=Config.MAX_UPLOAD_BYTES,
            ).props("accept=image/*, video/*,"
                ".pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt, .rtf,"
                ".zip, .7z, .tar, .tgz, .gz, .tar.gz, .rar, .bz2, .xz"
        ).classes("w-full")

        # On a phone or tablet this opens the camera itself, instead
        # of the file picker with the camera one more tap behind it.
        # A desktop browser ignores "capture" and would show the
        # picker again, so the button appears only where the pointer
        # is a finger -- see .touch-only in main.py.
        ui.upload(
            on_upload=handle_upload,
            auto_upload=True,
            label="Take a photograph",
            multiple=False,
            max_file_size=Config.MAX_UPLOAD_BYTES,
        ).props(
            'accept="image/*,video/*" capture="environment"'
        ).classes("w-full touch-only mt-2")
