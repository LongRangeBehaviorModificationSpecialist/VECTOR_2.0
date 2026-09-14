#!/usr/bin/env python3

"""
files_page.py — File upload and management page.

Stores files as BLOBs in the SQLite database with download and delete capability.
"""

from nicegui import ui
import os
import tempfile

from models import (
    require_active_case,
    has_active_case,
    get_session,
    UploadedFiles,
)
from navbar import build_navbar
from main import get_current_user_name, get_is_admin
from utils import (
    get_mime_type,
    is_allowed_file,
    format_file_size,
    confirm_delete_all,
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

        ui.label("File Upload & Management").classes("text-2xl font-bold m-4")

        # ----- Upload Section -----
        with ui.card().classes("w-full max-w-3xl mx-auto p-6"):

            ui.label("Upload New File").classes("text-lg font-semibold mb-2")

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
                            FILENAME=file_name,
                            FILEDATA=file_data,
                            FILESIZE=file_size,
                            FILEMIMETYPE=file_mime_type,
                            FILEUPLOADEDBY=uploader,
                        )
                        session.add(new_file)

                    ui.notify(
                        f"'{file_name}' uploaded successfully ("
                        f"{file_size:,} bytes), {file_mime_type}.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )

                    refresh_files_table()

                except Exception as err:
                    ui.notify(
                        f"Error uploading file → {str(err)}",
                        multi_line=True,
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

        ui.label("Files List").classes("text-xl font-bold mb-1")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_files_table() -> None:
            """Re-renders the files table from the database."""

            table_container.clear()

            with get_session() as session:
                files = (
                    session.query(UploadedFiles)
                    .order_by(UploadedFiles.FILEUPLOADDATE.desc())
                    .all()
                )

                if not files:
                    with table_container:
                        ui.label(
                            "No files have been uploaded"
                        ).classes("text-red italic")
                    return

                row_data = [
                    {
                        "Z_PK": f.Z_PK,
                        "FILENAME": f.FILENAME or "",
                        "FILESIZE": format_file_size(f.FILESIZE or 0),
                        "file_size_bytes": f.FILESIZE or 0,
                        "FILEMIMETYPE": f.FILEMIMETYPE or "unknown",
                        "FILEUPLOADEDBY": f.FILEUPLOADEDBY or "",
                        "FILEUPLOADDATE": (
                            f.FILEUPLOADDATE.strftime("%Y-%m-%d %H:%M:%S")
                            if f.FILEUPLOADDATE
                            else ""
                        ),
                    }
                    for f in files
                ]

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
                @require_active_case
                def on_download(e) -> None:
                    row = e.args
                    with get_session() as session:
                        file_record = (
                            session.query(UploadedFiles)
                            .filter_by(Z_PK=row["Z_PK"])
                            .first()
                        )

                        if file_record:
                            temp_dir = tempfile.gettempdir()
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
                                color="transparent").props("flat"
                            ).classes("text-[var(--vsp-blue)]")

                            def on_confirm_delete() -> None:
                                with get_session() as session:
                                    file_record = (
                                        session.query(UploadedFiles)
                                        .filter_by(Z_PK=row["Z_PK"])
                                        .first()
                                    )

                                    if file_record:
                                        session.delete(file_record)

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
                                color="#EF4444").props("push"
                            ).classes("text-[var(--vsp-white)]")

                    delete_dialog.open()

                table.on("download", on_download)
                table.on("delete", open_delete_dialog)

        with ui.row().classes("w-full justify-center my-2"):

            # ----- DELETE ALL BUTTON -----
            @require_active_case
            def delete_all_files() -> None:
                with get_session() as session:
                    session.query(UploadedFiles).delete()
                    session.commit()

                ui.notify(
                    "All Files has been deleted.",
                    timeout=4000,
                    position="bottom",
                    close_button="OK",
                )

                refresh_files_table()

            case_exists = has_active_case()

            ui.button(
                "Delete All Files",
                on_click=lambda: confirm_delete_all(
                    "files",
                    delete_all_files,
                ), color="#EF4444",).props("push"
            ).classes("mb-2 items-center").set_enabled(case_exists)

    # ----- Initial render -----
    refresh_files_table()
