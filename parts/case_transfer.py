#!/usr/bin/env python3

"""
case_transfer.py

The three dialogs that move or destroy a whole case: Export, Import and
Delete All Data.

They were written inside build_authenticated_home(), which ran to five
hundred lines with these three nested in the middle of it. Nothing about
them belongs to the home page in particular -- they are about the case as
a whole -- and out here each one can be read and changed without
scrolling past the other two.

The home page calls them; nothing else does.
"""

import shutil
from pathlib import Path

from nicegui import ui

from failures import explain, log
from import_export import (
    export_vector_to_csv,
    export_vector_to_json,
    import_vector_from_csv,
    import_vector_from_json,
    looks_like_json_export,
    needs_password,
    new_staging_dir,
)
from program.config import Config
from utils import delete_all_data, CONFIRM_TIMEOUT, WARN_TIMEOUT


# ----- Export -----
def open_export_dialog() -> None:
    """Offers the whole case as a download -- CSV, JSON or both, sealed
    with a password if one is asked for."""
    with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

        ui.label(
            "Export Data..."
        ).classes("text-lg font-bold text-[var(--vsp-blue)]")

        ui.label(
            "Downloads the whole case -- every table, every "
            "attachment, and the audit trail -- through your "
            "browser, on whichever device you are using."
        ).classes("text-sm text-[var(--vsp-gray)]")

        ui.label("The file will be named :").classes(
            "text-sm text-[var(--vsp-gray)]"
        )

        ui.label(
            "'<case-number>_<datetime>_saved_results'"
        ).classes("text-base text-[var(--vsp-blue)]")

        # ----- Export format selection -----
        ui.label("Export format:").classes(
            "mt-2 text-sm font-semibold text-[var(--vsp-gray)]"
        )

        format_radio = ui.radio(
            {
                "csv": "CSV — one file per database table",
                "json": "JSON — all data in a single file",
                "both": "Both — export CSV ZIP and JSON together",
            },
            value="csv",
        ).classes("text-sm text-[var(--vsp-gray)]")

        ui.label(
            "CSV opens in Excel. JSON is one self-contained "
            "file with the attachments embedded, for handing "
            "the case to another system."
        ).classes("text-xs text-gray-400")

        # ----- Password option -----
        encrypt_checkbox = ui.checkbox(
            "Encrypt with password (AES-256)"
        ).classes("text-sm text-[var(--vsp-gray)]")

        password_input = ui.input(
            label="ENTER PASSWORD :",
            password=True,
        ).classes("w-full yellow-label text-sm")

        password_input.bind_visibility_from(
            encrypt_checkbox,
            "value",
        )

        def do_export():
            pwd = (
                password_input.value
                if encrypt_checkbox.value
                else None
            )

            if encrypt_checkbox.value and not pwd:
                ui.notify(
                    "Please enter a password or uncheck "
                    "encryption.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

            dialog.close()

            # ----- Run the selected exports -----
            # Each results file goes to the browser, so it
            # arrives on the device the export was asked from.
            results = []
            if format_radio.value in ("csv", "both"):
                result = export_vector_to_csv(password=pwd)
                if result is not None:
                    results.append(result)

            if format_radio.value in ("json", "both"):
                result = export_vector_to_json(password=pwd)
                if result is not None:
                    results.append(result)

            # Pass each file path to the browser to it can be
            # downloaded to a location choosen by the user.
            for result in results:
                ui.download.file(result.zip_path)

            for result in results:
                ui.notify(
                    result.message,
                    multi_line=True,
                    classes="multi-line-notification",
                    timeout=CONFIRM_TIMEOUT,
                    position="bottom",
                    close_button="OK",
                )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):

            ui.button(
                "Cancel",
                on_click=dialog.close,
                color="transparent",
            ).props("flat").classes("p-3 hover-border-blue")

            ui.button(
                "Export Now",
                on_click=do_export,
                color="var(--vsp-blue)",
            ).props("push").classes("p-3 hover-border-white")

    dialog.open()


# ----- Import -----
def open_import_dialog() -> None:
    """Replaces the case with a file exported earlier.

    The format, and whether the file needs a password, are read from
    the file itself rather than asked for."""
    with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

        ui.label("Import Data...").classes(
            "text-lg font-bold text-[var(--vsp-blue)]"
        )

        # No format to choose. The CSV archive and the JSON
        # export are told apart from the file itself, so
        # picking the wrong one cannot fail an import.
        ui.label(
            "Select a file previously exported from VECTOR -- "
            "either the ZIP archive or the JSON file. The "
            "format is detected from the file itself."
        ).classes("text-sm text-[var(--vsp-gray)]")

        ui.label(
            "WARNING :"
        ).classes("text-sm font-bold text-[#EF4444]")

        ui.label("This will REPLACE ALL existing data!").classes(
            "text-base text-[var(--vsp-gray)]"
        )

        picked = {"path": None, "folder": None, "locked": False}

        def discard_picked() -> None:
            if picked["folder"] is not None:
                shutil.rmtree(picked["folder"], ignore_errors=True)
            picked["path"] = picked["folder"] = None
            picked["locked"] = False

        async def on_file_picked(e) -> None:
            # Kept under the name it arrived with: the suffix is
            # part of how the format is recognised.
            discard_picked()
            folder = new_staging_dir("vector_import_upload_")
            name = Path(e.file.name).name or "import.zip"
            target = folder / name
            await e.file.save(target)
            picked["path"], picked["folder"] = target, folder
            picked_label.set_text(f"Chosen: {name}")
            # Whether it needs a password is read from the file
            # itself, so nobody has to remember to say so.
            locked = needs_password(target)
            picked["locked"] = locked
            password_note.set_visibility(locked)
            password_input.set_visibility(locked)
            import_button.enable()

        ui.upload(
            label="Choose the exported file (.zip or .json)",
            on_upload=on_file_picked,
            auto_upload=True,
            max_files=1,
            max_file_size=Config.MAX_IMPORT_BYTES,
        ).props('accept=".zip,.json" flat bordered').classes(
            "w-full"
        )

        picked_label = ui.label(
            "No file chosen yet."
        ).classes("text-sm text-[var(--vsp-gray)]")

        password_note = ui.label(
            "This file is protected with a password."
        ).classes("text-sm text-[#F5B027]")

        password_input = ui.input(
            label="ENTER THE FILE'S PASSWORD :",
            password=True,
        ).classes("w-full yellow-label text-sm")

        # Shown once a file that needs one has been chosen.
        password_note.set_visibility(False)
        password_input.set_visibility(False)

        def do_import():
            path = picked["path"]
            if path is None:
                ui.notify(
                    "Choose the exported file first.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

            pwd = password_input.value if picked["locked"] else None

            if picked["locked"] and not pwd:
                ui.notify(
                    "This file is protected with a password. "
                    "Enter it to import the file.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

            dialog.close()

            # A .json, or a .zip holding one, goes through
            # the JSON reader; the CSV archive is also a
            # .zip, so the contents decide, not the suffix
            # alone.
            try:
                if looks_like_json_export(path):
                    import_vector_from_json(
                        str(path), password=pwd
                    )
                else:
                    import_vector_from_csv(
                        str(path), password=pwd
                    )
            finally:
                discard_picked()

        def cancel_import() -> None:
            discard_picked()
            dialog.close()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):

            ui.button(
                "Cancel",
                on_click=cancel_import,
                color="transparent",
            ).props("flat").classes("p-3 hover-border-blue")

            import_button = ui.button(
                "Import Now",
                on_click=do_import,
                color="var(--vsp-blue)",
            ).props("push").classes("p-3 hover-border-white")

            import_button.disable()

    dialog.open()


# ----- Delete all -----
def open_delete_all_dialog() -> None:
    """Empties the case, once the box is ticked and DELETE is typed.

    Accounts and the audit trail are kept: a wipe is exactly the
    event the trail exists to record."""
    with ui.dialog() as dialog, ui.card().classes("max-w-md p-6"):

        ui.label("Delete All Data?").classes(
            "mb-3 text-lg font-bold text-[var(--vsp-blue)]"
        )

        ui.label(
            "Are you sure you want to delete all case "
            "data for this case? This CANNOT be undone!"
        ).classes(
            "mb-3 text-base text-[var(--vsp-gray)]"
        )

        # ----- User verification of destructive activity -----
        affirm_checkbox = ui.checkbox(
            "I understand the current data cannot be recovered.",
            value=False,
        ).classes("mb-3 text-base text-[var(--vsp-gray)]")

        affirm_input = (
            ui.input(
                label="AFFIRM BY TYPING 'DELETE' BELOW",
                password=False,
            )
            .classes("w-full yellow-label mb-3")
        )

        affirm_input.bind_visibility_from(
            affirm_checkbox,
            "value",
        )

        def do_delete():
            if not affirm_checkbox.value:
                ui.notify(
                    "Tick the box to confirm you understand "
                    "the data cannot be recovered.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

            if (affirm_input.value or "").strip() != "DELETE":
                ui.notify(
                    "Type DELETE, in capital letters, to confirm.",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

            dialog.close()

            try:
                delete_all_data()
            except Exception as err:
                log.exception("Data deletion failed")
                ui.notify(
                    "No data was deleted, and the case is "
                    f"unchanged.\n\n{explain(err)}",
                    multi_line=True,
                    classes="multi-line-notification",
                    type="warning",
                    timeout=WARN_TIMEOUT,
                    position="center",
                    close_button="OK",
                )
                return

        with ui.row().classes("w-full justify-end gap-2 mt-4"):

            ui.button(
                "Cancel",
                on_click=dialog.close,
                color="transparent",
            ).props("flat").classes("p-3 hover-border-blue")

            ui.button(
                "Delete all data",
                on_click=do_delete,
                color="#EF4444",
            ).props("push").classes("p-3 hover-border-white")

    dialog.open()
