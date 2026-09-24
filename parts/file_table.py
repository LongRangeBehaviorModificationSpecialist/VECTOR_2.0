#!/usr/bin/env python3

"""
file_table.py

The list of everything attached to the case: each file with its size,
type, fingerprint and when it arrived, a download for each, a delete
that asks first, and Delete All Files.

It was the back three hundred lines of the Files page builder. The one
change on the way out: the refresh it returns also settles the
delete-all button, which the page used to do by hand in a second
function.

parts/files_page.py draws it; nothing else does.
"""

from typing import Callable

import clock
from nicegui import ui

from failures import explain, log
from models import get_session, has_active_case, UploadedFiles
from utils import confirm_delete_all, format_file_size, require_active_case


def files_table() -> Callable[[], None]:
    """Draws the list, and returns the function that redraws it.

    The returned function also settles the delete-all button, which is
    disabled while no case is open.
    """
    ui.separator().classes("my-6")

    ui.label("Files List").classes("text-xl font-bold mb-1")

    # A scene's photographs run to hundreds; the name of the one
    # being asked about should not need scrolling for.
    search_box = ui.input(
        placeholder="Search the files below",
    ).props("dense outlined clearable").classes("w-full max-w-md mb-2")

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
                    # Stored in UTC; shown in this machine's zone.
                    "FILEUPLOADDATE": (
                        clock.show_utc(f.FILEUPLOADDATE)
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
                    "label": "Uploaded At",
                    "field": "FILEUPLOADDATE",
                    # Newest first already; as text the dates would
                    # sort by month, not by when.
                    "sortable": False,
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

            table.bind_filter_from(
                search_box, "value", backward=lambda typed: typed or ""
            )

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
                # Served by /attachments above, straight from the
                # database, so no copy of the file is written to disk.
                ui.download.from_url(f"/attachments/{e.args['Z_PK']}")

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
                        "The following file will be removed from the "
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

    def refresh_everything() -> None:
        refresh_files_table()
        delete_all_button.set_enabled(has_active_case())

    return refresh_everything
