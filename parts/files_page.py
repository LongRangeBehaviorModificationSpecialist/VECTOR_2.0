#!/usr/bin/env python3

"""
files_page.py — File upload and management page.

Stores files as BLOBs in the SQLite database with download and delete capability.
"""

import hashlib
from nicegui import ui
import os
import tempfile

from models import (
    get_session,
    has_active_case,
    UploadedFiles,
    audit_timestamp,
)
from program.config import Config
from failures import explain, log
from live import refresh_on_change
from navbar import build_navbar
from auth import get_current_user_name, get_is_admin
from utils import (
    get_mime_type,
    is_allowed_file,
    format_file_size,
    confirm_delete_all,
    require_active_case,
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

        # ----- Upload Section -----
        with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

            ui.label(
                "Upload New File"
            ).classes("text-lg font-semibold mb-2")

            ui.label(
                "Allowed file types → (1) Images, (2) Videos, (3) Documents, "
                "and (4) Archive files."
            ).classes("text-sm text-gray-400 mb-2")

            @require_active_case
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
                    file_mime_type = (
                        uploaded_file.content_type
                        or "application/octet-stream"
                    )
                    # Determine MIME type using fallback
                    file_mime_type = get_mime_type(file_name, file_mime_type)

                    # Validate file type
                    if not is_allowed_file(file_mime_type):
                        ui.notify(
                            f"'{file_name}' is not an allowed file type "
                            f"({file_mime_type}). "
                            f"Only images, videos, documents, and archives "
                            "are permitted.",
                            type="warning",
                            timeout=0,
                            position="center",
                            close_button="OK",
                        )
                        return

                    uploader = get_current_user_name()

                    # Hashed on arrival, not at export time: the stored
                    # digest then certifies the file as collected rather
                    # than whatever the database holds later.
                    digest = hashlib.sha256(file_data).hexdigest()
                    hashed_at = audit_timestamp()

                    with get_session() as session:
                        new_file = UploadedFiles(
                            FILENAME=file_name,
                            FILEDATA=file_data,
                            FILESIZE=file_size,
                            FILEMIMETYPE=file_mime_type,
                            FILEUPLOADEDBY=uploader,
                            FILESHA256=digest,
                            FILEHASHEDAT=hashed_at,
                        )
                        session.add(new_file)

                    ui.notify(
                        f"'{file_name}' uploaded ({file_size:,} bytes, "
                        f"{file_mime_type}).\n"
                        f"SHA-256: {digest}",
                        timeout=0,
                        position="bottom",
                        close_button="OK",
                    )

                    refresh_files_table()

                except Exception as err:
                    name = getattr(e.file, "name", "") or "the file"
                    log.exception("Could not upload %s", name)
                    ui.notify(
                        f"Could not upload {name}.\n\n{explain(err)}",
                        multi_line=True,
                        type="negative",
                        timeout=0,
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

        # ----- Existing Files Table -----
        ui.separator().classes("my-6")

        ui.label("Files List").classes("text-xl font-bold mb-1")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2")

        shown = {"table": None}

        def refresh_files_table() -> None:
            """Re-renders the files table from the database."""

            with get_session() as session:
                files = (
                    session.query(UploadedFiles)
                    .order_by(UploadedFiles.FILEUPLOADDATE.desc())
                    .all()
                )
                row_data = [
                    {
                        "Z_PK": f.Z_PK,
                        "FILENAME": f.FILENAME or "",
                        "FILESIZE": format_file_size(f.FILESIZE or 0),
                        "file_size_bytes": f.FILESIZE or 0,
                        "FILEMIMETYPE": f.FILEMIMETYPE or "unknown",
                        "FILEUPLOADEDBY": f.FILEUPLOADEDBY or "",
                        "FILESHA256": (f.FILESHA256 or "not recorded"),
                        "sha256_short": (
                            f"{f.FILESHA256[:12]}…" if f.FILESHA256
                            else "not recorded"
                        ),
                        "FILEUPLOADDATE": (
                            f.FILEUPLOADDATE.strftime("%Y-%m-%d %H:%M:%S")
                            if f.FILEUPLOADDATE
                            else ""
                        ),
                    }
                    for f in files
                ]

            # Rows are swapped in place when the table is already showing,
            # so a refresh keeps the sort order the user picked.
            table = shown["table"]
            if row_data and table is not None and not table.is_deleted:
                table.rows = row_data
                table.update()
                return

            table_container.clear()
            shown["table"] = None

            if not row_data:
                with table_container:
                    ui.label(
                        "No files have been uploaded"
                    ).classes("text-red italic")
                return

            with table_container:
                column_defs = [
                    {
                        "name": "Z_PK",
                        "label": "ID #",
                        "field": "Z_PK",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "FILENAME",
                        "label": "File Name",
                        "field": "FILENAME",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "FILESIZE",
                        "label": "Size",
                        "field": "FILESIZE",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "FILEMIMETYPE",
                        "label": "Type",
                        "field": "FILEMIMETYPE",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "FILEUPLOADEDBY",
                        "label": "Uploaded By",
                        "field": "FILEUPLOADEDBY",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "sha256_short",
                        "label": "SHA-256",
                        "field": "sha256_short",
                        "sortable": False,
                        "align": "left",
                    },
                    {
                        "name": "FILEUPLOADDATE",
                        "label": "Uploaded At (UTC)",
                        "field": "FILEUPLOADDATE",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "actions",
                        "label": "Actions",
                        "field": "actions",
                        "sortable": False,
                        "align": "center",
                    },
                ]

                table = ui.table(
                    columns=column_defs,
                    rows=row_data,
                    row_key="Z_PK",
                )

                table.props("dense flat")
                shown["table"] = table

                table.add_slot(
                    "body-cell-actions",
                    """
                    <q-td :props="props">
                        <div class="row no-wrap gap-1">
                            <q-btn dense flat
                                icon="download" size="sm"
                                style="color: #2984D1;"
                                @click="$parent.$emit('download', \
                                props.row)" />
                            <q-btn dense flat color="negative"
                                icon="delete" size="sm"
                                @click="$parent.$emit('delete', \
                                props.row)" />
                        </div>
                    </q-td>
                    """,
                )

                # ----- Download handler -----
                def on_download(e) -> None:
                    row = e.args
                    with get_session() as session:
                        file_record = (
                            session.query(UploadedFiles)
                            .filter_by(Z_PK=row["Z_PK"])
                            .first()
                        )

                        if file_record:
                            temp_dir = tempfile.mkdtemp(
                                prefix="vector_dl_"
                            )
                            safe_name = (
                                file_record.FILENAME
                                or f"file_{file_record.Z_PK}"
                            )
                            safe_name = (
                                safe_name.replace("/", "_").replace("\\", "_")
                            )
                            temp_path = os.path.join(temp_dir, safe_name)

                            with open(temp_path, "wb") as f:
                                f.write(file_record.FILEDATA)
                            ui.download(temp_path)

                # ----- Delete confirmation dialog -----
                @require_active_case
                def open_delete_dialog(e) -> None:
                    """Confirms and deletes a file."""
                    row = e.args
                    with ui.dialog() as delete_dialog, ui.card(
                        ).classes("max-w-sm p-6"
                    ):
                        ui.label(
                            "Delete File?"
                        ).classes(
                            "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                        )

                        ui.label(
                            f"The following file will be removed from the "
                            "case file :"
                        ).classes("mb-3 text-sm text-[var(--vsp-gray)]")

                        ui.label(
                            f"{row['FILENAME']}"
                        ).classes(
                            "mb-3 text-sm font-semibold text-[var(--vsp-blue)]"
                        )

                        ui.label("This cannot be undone!").classes(
                            "mb-3 text-sm text-[var(--vsp-gray)]"
                        )

                        with ui.row().classes("w-full justify-end gap-2"):

                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                                color="transparent",
                            ).props("flat").classes("text-[var(--vsp-blue)]")

                            def on_confirm_delete() -> None:
                                try:
                                    with get_session() as session:
                                        file_record = (
                                            session.query(UploadedFiles)
                                            .filter_by(Z_PK=row["Z_PK"])
                                            .first()
                                        )
                                        if file_record:
                                            session.delete(file_record)
                                except Exception as err:
                                    log.exception(
                                        "Could not delete %s", row["FILENAME"]
                                    )
                                    ui.notify(
                                        f"Could not delete {row['FILENAME']}."
                                        f"\n\n{explain(err)}",
                                        multi_line=True,
                                        type="negative",
                                        timeout=0,
                                        position="center",
                                        close_button="OK",
                                    )
                                    delete_dialog.close()
                                    return

                                ui.notify(
                                    f"File: {row['FILENAME']} has been "
                                    "deleted.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                delete_dialog.close()
                                refresh_files_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#ef4444",
                            ).props("push").classes(
                                "text-[var(--vsp-white)]"
                            )

                    delete_dialog.open()

                table.on("download", on_download)
                table.on("delete", open_delete_dialog)

        with ui.row().classes("w-full justify-center my-2"):

            def delete_all_files() -> None:
                try:
                    with get_session() as session:
                        # One at a time, so each removal reaches the audit
                        # trail. A bulk delete raises no ORM events, and the
                        # files vanished without a record.
                        for file_record in session.query(UploadedFiles).all():
                            session.delete(file_record)
                except Exception as err:
                    log.exception("Could not delete every file")
                    ui.notify(
                        f"Nothing was deleted.\n\n{explain(err)}",
                        multi_line=True,
                        type="negative",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )
                    return

                ui.notify(
                    "All files have been deleted.",
                    timeout=4000,
                    position="bottom",
                    close_button="OK",
                )

                refresh_files_table()

            delete_all_button = ui.button(
                "Delete All Files",
                on_click=lambda: confirm_delete_all(
                    "files",
                    delete_all_files,
                ),
                color="#ef4444",
            ).props("push").classes("mb-2 items-center")
            delete_all_button.set_enabled(has_active_case())

    # ----- Initial render -----
    refresh_files_table()

    # Files added or removed on another device appear without a reload.
    def live_refresh() -> None:
        refresh_files_table()
        delete_all_button.set_enabled(has_active_case())

    refresh_on_change(live_refresh)
