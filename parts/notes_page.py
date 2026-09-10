#!/usr/bin/env python3

"""
notes_page.py

Consolidates four Flask routes into one interactive page:
    /notes_list   →  table display + delete
    /note_add     →  add form (auto-populates date/time, agent dropdown)
    /note_update  →  inline edit dialog
    /note_delete  →  delete with confirmation
"""

from nicegui import ui

from models import get_session, Notes
from navbar import build_navbar
from home_page import confirm_new_case_handler
from main import get_current_user_name, get_is_admin
from utils import (
    required_select,
    required_input,
    get_current_timestamp,
    confirm_delete_all,
    validate_note_data,
)

# ----- Main Page Builder -----
def build_notes_page() -> None:
    """Builds the full Notes page UI."""

    # ----- Header / Navbar -----
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Notes"
        ).classes("text-2xl font-bold m-4")

        # ----- Add Note Form -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            current_time = get_current_timestamp()

            NOTEDATETIME_input = ui.input(
                label="Date/Time Added",
                value=current_time,
            ).classes("w-full")

            NOTEDATETIME_input.props("readonly")

            NOTEDATETIMEUPDATED_input = ui.input(
                label="Date/Time Updated",
            ).classes("w-full")

            NOTEDATETIMEUPDATED_input.props("readonly")

            # Authorship comes from the signed-in user, not a dropdown.
            # Choosing it meant anyone could write, or later rewrite, a
            # note under a colleague's name.
            NOTEAUTHOR = get_current_user_name() or "unknown"

            NOTEAUTHOR_input = ui.input(
                label="Author",
                value=NOTEAUTHOR,
            ).classes("w-full")

            NOTEAUTHOR_input.props("readonly")

            NOTETEXT_input = required_input(
                label="Note"
            ).classes("w-full")

            NOTETEXT_input.props("autofocus")

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form() -> None:

                    NOTEDATETIME_input.value = get_current_timestamp()
                    NOTETEXT_input.value = ""

                def on_submit() -> None:

                    NOTEDATETIME = (
                        NOTEDATETIME_input.value or
                        get_current_timestamp()
                    )
                    NOTEAUTHOR = get_current_user_name() or "unknown"
                    NOTETEXT = NOTETEXT_input.value or ""

                    if validate_note_data(
                        NOTEAUTHOR=NOTEAUTHOR,
                        NOTETEXT=NOTETEXT,
                    ):
                        return

                    with get_session() as session:
                        new_note = Notes(
                            NOTEDATETIME=NOTEDATETIME,
                            NOTEDATETIMEUPDATED="",
                            NOTEAUTHOR=NOTEAUTHOR,
                            NOTETEXT=NOTETEXT,
                        )
                        session.add(new_note)

                    ui.notify(
                        f"Note from {NOTEAUTHOR} was added.",
                        timeout=4000,
                        position="bottom",
                        close_button="OK",
                    )

                    clear_form()
                    refresh_notes_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                    color="transparent",
                    ).props("flat"
                ).classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Note",
                    on_click=on_submit,
                    color="var(--vsp-blue)",
                ).props("unelevated").classes("text-[var(--vsp-white)]")

        # ----- Existing Notes Table -----
        ui.separator().classes("my-6")

        ui.label(
            "Current Notes"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_notes_table() -> None:
            """Re-renders the notes table from the database."""
            table_container.clear()

            with get_session() as session:

                notes = (
                    session.query(Notes)
                    .order_by(Notes.Z_PK)
                    .all()
                )

                if not notes:
                    with table_container:
                        ui.label(
                            "No notes in the database yet"
                        ).classes("text-gray-500 italic")
                    return

                row_data = [
                    {
                        "Z_PK": r.Z_PK,
                        "NOTEDATETIME": r.NOTEDATETIME or "",
                        "NOTEDATETIMEUPDATED": r.NOTEDATETIMEUPDATED or "",
                        "NOTEAUTHOR": r.NOTEAUTHOR or "",
                        "NOTETEXT": r.NOTETEXT or "",
                    }
                    for r in notes
                ]

            with table_container:
                column_defs = [
                    {
                        "name": "NOTEDATETIME",
                        "label": "Date Added",
                        "field": "NOTEDATETIME",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "NOTEDATETIMEUPDATED",
                        "label": "Date Updated",
                        "field": "NOTEDATETIMEUPDATED",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "NOTEAUTHOR",
                        "label": "Author",
                        "field": "NOTEAUTHOR",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "NOTETEXT",
                        "label": "Note",
                        "field": "NOTETEXT",
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

                # ----- Slot: Actions column -----
                table.add_slot(
                    "body-cell-actions",
                    """
                    <q-td :props="props">
                        <div class="row no-wrap gap-1">
                            <q-btn dense flat
                                icon="edit" size="sm"
                                style="color: #2984D1;"
                                @click="$parent.$emit('edit', props.row)" />
                            <q-btn dense flat color="negative"
                                icon="delete" size="sm"
                                @click="$parent.$emit('delete', props.row)" />
                        </div>
                    </q-td>
                    """,
                )

                # ----- Edit dialog -----
                def open_edit_dialog(e) -> None:

                    row = e.args


                    with ui.dialog() as edit_dialog, ui.card(
                        ).classes("w-full max-w-lg p-6"
                    ):

                        ui.label(
                            f"Edit Note #{row['Z_PK']}"
                            ).classes(
                            "mb-3 text-lg font-semibold text-[var(--vsp-blue)]"
                        )

                        NOTEDATETIME_input = ui.input(
                            label="Date/Time Added",
                            value=row["NOTEDATETIME"],
                        ).classes("w-full")

                        NOTEDATETIME_input.props("readonly")

                        NOTEDATETIMEUPDATED_input = ui.input(
                            label="Date/Time Updated",
                            value=get_current_timestamp(),
                        ).classes("w-full")

                        NOTEDATETIMEUPDATED_input.props("readonly")

                        # The original author is fixed. Reassigning it
                        # after the fact is exactly the rewrite the audit
                        # trail exists to prevent.
                        NOTEAUTHOR_input = ui.input(
                            label="Original Author",
                            value=row["NOTEAUTHOR"] or "",
                        ).classes("w-full")

                        NOTEAUTHOR_input.props("readonly")

                        ui.label(
                            f"Edited by {get_current_user_name() or 'unknown'}"
                        ).classes("text-xs text-gray-400 -mt-2 mb-2")

                        NOTETEXT_input = required_input(
                            label="Note",
                            value=row["NOTETEXT"],
                        ).classes("w-full")

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"
                        ):

                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                                color="transparent",
                            ).props("flat").classes("text-[var(--vsp-blue)]")

                            def on_save_update() -> None:
                                NOTEDATETIMEUPDATED = (
                                    NOTEDATETIMEUPDATED_input.value or ""
                                )
                                NOTEAUTHOR = row["NOTEAUTHOR"] or ""
                                NOTETEXT = NOTETEXT_input.value or ""

                                if validate_note_data(
                                    NOTEAUTHOR=NOTEAUTHOR,
                                    NOTETEXT=NOTETEXT,
                                ):
                                    return

                                with get_session() as session:

                                    note = (
                                        session.query(Notes)
                                        .filter_by(Z_PK=row["Z_PK"])
                                        .first()
                                    )

                                    if note:
                                        note.NOTEDATETIMEUPDATED = (
                                            NOTEDATETIMEUPDATED
                                        )
                                        # NOTEAUTHOR is deliberately not
                                        # reassigned; the audit trail
                                        # records who made this edit.
                                        note.NOTETEXT = NOTETEXT

                                ui.notify(
                                    f"Note from {NOTEAUTHOR} was updated.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                edit_dialog.close()
                                refresh_notes_table()

                            ui.button(
                                "Update",
                                on_click=on_save_update,
                                color="var(--vsp-blue)",
                                ).props("unelevated").classes(
                                "text-[var(--vsp-white)]"
                            )

                    edit_dialog.open()

                # ----- Delete confirmation dialog -----
                def open_delete_dialog(e) -> None:

                    row = e.args

                    with ui.dialog() as delete_dialog, ui.card(
                        ).classes("max-w-sm p-6"
                    ):

                        ui.label(
                            f"Delete Note #{row['Z_PK']}?"
                            ).classes(
                            "text-lg font-semibold mb-3 text-[var(--vsp-blue)]"
                        )

                        ui.label(
                            f"Are you sure you want to delete this note?"
                        ).classes("mb-3 text-base text-[var(--vsp-gray)]")

                        # Show a preview of the note text (truncated)
                        preview = (
                            row["NOTETEXT"][:100] + "..."
                            if len(row["NOTETEXT"]) > 100
                            else row["NOTETEXT"]
                        )

                        ui.label(
                            "Note content:"
                            ).classes(
                            "mb-3 text-base font-semibold text-[var(--vsp-blue)]"
                        )

                        ui.label(f"'{preview}'").classes(
                            "text-sm text-gray-500 italic mb-4"
                        )

                        with ui.row().classes("w-full justify-end gap-2"):

                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                                color="transparent",
                            ).props("flat").classes("text-[var(--vsp-blue)]")

                            def on_confirm_delete() -> None:

                                with get_session() as session:

                                    note = (
                                        session.query(Notes)
                                        .filter_by(Z_PK=row["Z_PK"])
                                        .first()
                                    )

                                    if note:
                                        note_id = note.Z_PK
                                        session.delete(note)
                                    else:
                                        note_id = row["Z_PK"]

                                ui.notify(
                                    f"Note {note_id} was deleted.",
                                    timeout=4000,
                                    position="bottom",
                                    close_button="OK",
                                )

                                delete_dialog.close()
                                refresh_notes_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete,
                                color="#ef4444",
                                ).props("unelevated").classes(
                                "text-[var(--vsp-white)]"
                            )

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

        with ui.row().classes("w-full justify-center my-2"):

            def delete_all_notes() -> None:

                with get_session() as session:

                    session.query(Notes).delete()
                    session.commit()

                ui.notify(
                    "All Notes has been deleted.",
                    timeout=4000,
                    position="bottom",
                    close_button="OK",
                )

                refresh_notes_table()

            ui.button(
                "Delete All Notes",
                on_click=lambda: confirm_delete_all(
                    "notes",
                    delete_all_notes,
                ),
                color="#ef4444",
            ).props("unelevated").classes("mb-2 items-center")

    # ----- Initial render -----
    refresh_notes_table()
