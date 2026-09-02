#!/usr/bin/env python3

"""
files_page.py — File upload and management page.

Stores files as BLOBs in the SQLite database with download and delete capability.
"""

from nicegui import ui
import os
import tempfile

from models import get_session, UploadedFiles
from navbar import build_navbar
from home_page import confirm_new_case_handler
from main import get_current_user_name, get_is_admin
from utils import (
    get_mime_type,
    is_allowed_file,
    format_file_size
)

# ----- Main Page Builder -----
def build_uploads_page():
    """Builds the full File Upload page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "File Upload & Management"
        ).classes("text-2xl font-bold m-4")

        # ----- Upload Section -----
        with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

            ui.label(
                "Upload New File"
            ).classes("text-lg font-semibold mb-4")

            ui.label(
                "Allowed file types → (1) Images, (2) Videos, (3) Documents, "
                "and (4) Archive files."
            ).classes("text-sm text-gray-400 mb-4")

            async def handle_upload(e):
                """Handles file upload from ui.upload component."""

                try:

                    uploaded_file = e.file
                    file_name = uploaded_file.name
                    # SmallFileUpload stores the data as bytes in _data
                    file_data = uploaded_file._data
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

                    with get_session() as session:

                        new_file = UploadedFiles(
                            file_name=file_name,
                            file_data=file_data,
                            file_size=file_size,
                            file_mime_type=file_mime_type,
                            uploaded_by=uploader,
                        )

                        session.add(new_file)

                    ui.notify(
                        f"'{file_name}' uploaded successfully ("
                        f"{file_size:,} bytes), {file_mime_type}.",
                        type="positive",
                        timeout=2000,
                        position="bottom",
                        close_button="OK",
                    )

                    refresh_files_table()

                except Exception as err:

                    ui.notify(
                        f"Error uploading file → {str(err)}.",
                        type="negative",
                        timeout=0,
                        position="center",
                        close_button="OK",
                    )

                    import traceback
                    traceback.print_exc()

            ui.upload(
                on_upload=handle_upload,
                auto_upload=True,
                label="Drag files here or click to browse",
                multiple=True,
                ).props("accept=image/*, video/*,"
                    ".pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt, .rtf,"
                    ".zip, .7z, .tar, .tgz, .gz, .tar.gz, .rar, .bz2, .xz"
            ).classes("w-full")

        # ----- Existing Files Table -----
        ui.separator().classes("my-6")

        ui.label(
            "Uploaded Files"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2")

        def refresh_files_table():
            """Re-renders the files table from the database."""

            table_container.clear()

            with get_session() as session:

                files = (
                    session.query(UploadedFiles)
                    .order_by(UploadedFiles.upload_date.desc())
                    .all()
                )

                if not files:

                    with table_container:

                        ui.label(
                            "No files uploaded yet"
                        ).classes("text-gray-500 italic")

                    return

                row_data = [
                    {
                        "id": f.id,
                        "file_name": f.file_name or "",
                        "file_size": format_file_size(f.file_size or 0),
                        "file_size_bytes": f.file_size or 0,
                        "file_mime_type": f.file_mime_type or "unknown",
                        "uploaded_by": f.uploaded_by or "",
                        "upload_date": (
                            f.upload_date.strftime("%Y-%m-%d %H:%M:%S")
                            if f.upload_date
                            else ""
                        )
                    }
                    for f in files
                ]

            with table_container:

                column_defs = [
                    {
                        "name": "file_name",
                        "label": "file_name",
                        "field": "file_name",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "file_size",
                        "label": "Size",
                        "field": "file_size",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "file_mime_type",
                        "label": "Type",
                        "field": "file_mime_type",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "uploaded_by",
                        "label": "Uploaded By",
                        "field": "uploaded_by",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "upload_date",
                        "label": "Uploaded At (UTC)",
                        "field": "upload_date",
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
                    row_key="id",
                )

                table.props("dense flat")

                table.add_slot(
                    "body-cell-actions",
                    """
                    <q-td :props="props">
                        <div class="row no-wrap gap-1">
                            <q-btn dense flat color="primary"
                                icon="download" size="sm"
                                @click="$parent.$emit('download', \
                                props.row)" />
                            <q-btn dense flat color="negative"
                                icon="delete" size="sm"
                                @click="$parent.$emit('delete', \
                                props.row)" />
                        </div>
                    </q-td>
                    """
                )

                # ----- Download handler -----
                def on_download(e):

                    row = e.args

                    with get_session() as session:

                        file_record = (
                            session.query(UploadedFiles)
                            .filter_by(id=row["id"])
                            .first()
                        )

                        if file_record:

                            temp_dir = tempfile.gettempdir()
                            temp_path = os.join.path(
                                temp_dir,
                                file_record.file_name
                            )

                            with open(temp_path, "wb") as f:

                                f.write(file_record.file_data)

                            ui.download(temp_path)

                # ----- Delete confirmation dialog -----
                def open_delete_dialog(e):
                    """Confirms and deletes a file."""

                    row = e.args

                    with ui.dialog() as delete_dialog, ui.card(
                        ).classes("max-w-sm p-6"
                    ):

                        ui.label("Confirm Deletion"
                            ).classes("text-lg font-semibold mb-2")

                        ui.label(
                            f"Are you sure you want to delete "
                            f"'{row['file_name']}'? This cannot be undone!"
                        ).classes("mb-4")

                        with ui.row().classes("w-full justify-end gap-2"):

                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                            ).props("flat")

                            def on_confirm_delete():

                                with get_session() as session:

                                    file_record = (
                                        session.query(UploadedFiles)
                                        .filter_by(id=row["id"])
                                        .first()
                                    )

                                    if file_record:

                                        session.delete(file_record)

                                ui.notify(
                                    f"File: {row['file_name']} has been "
                                    "deleted.",
                                    type="positive",
                                    timeout=2000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                delete_dialog.close()
                                refresh_files_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#ef4444",
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("download", on_download)
                table.on("delete", open_delete_dialog)

    # ----- Initial render -----
    refresh_files_table()
