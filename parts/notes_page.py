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

from models import require_active_case, has_active_case, get_session, Notes
from navbar import build_navbar
from main import get_current_user_name, get_is_admin
from utils import (
    required_select,
    required_input,
    load_agent_names,
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
    )

    with ui.column().classes("w-full items-center"):

        ui.label("Notes").classes("text-2xl font-bold m-4")

        # ----- Add Note Form -----
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):

            agent_options = load_agent_names()
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

            NOTEAUTHOR_combo = required_select(
                options=agent_options,
                label="Agent Name",
                with_input=True,
            ).classes("w-full")

            NOTEAUTHOR_combo.props("autofocus")

            NOTETEXT_input = required_input(
                label="Note"
            ).classes("w-full")

            # ----- Buttons -----
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_notes_form() -> None:
                    NOTEDATETIME_input.value = get_current_timestamp()
                    NOTEAUTHOR_combo.value = None
                    NOTETEXT_input.value = ""

                @require_active_case
                def on_submit() -> None:
                    NOTEDATETIME = (
                        NOTEDATETIME_input.value or
                        get_current_timestamp()
                    )
                    NOTEAUTHOR = NOTEAUTHOR_combo.value
                    NOTETEXT = NOTETEXT_input.value or ""

                    if validate_note_data(
                        NOTEAUTHOR=NOTEAUTHOR,
                        NOTETEXT=NOTETEXT,
                    ):
                        return

                    try:
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

                        clear_notes_form()
                        refresh_notes_table()

                    except Exception:
                        ui.notify(
                            "Please check the data you just tried to "
                            "enter — an unknown error occured. "
                            "No changes were made.",
                            type="negative",
                            timeout=0,
                            position="center",
                            close_button="OK",
                        )
                        import traceback
                        traceback.print_exc()

                ui.button(
                    "Clear",
                    on_click=clear_notes_form,
                    color="transparent").props("flat"
                ).classes("text-[var(--vsp-blue)]")

                ui.button(
                    "Add Note",
                    on_click=on_submit,
                    color="var(--vsp-blue)").props("push"
                ).classes("text-[var(--vsp-white)]")

        # ----- Existing Notes Table -----
        ui.separator().classes("my-6")

        ui.label("Notes List").classes("text-xl font-bold mb-1")

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
                            "No notes have been entered"
                        ).classes("text-red italic")
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
                        "name": "Z_PK",
                        "label": "ID #",
                        "field": "Z_PK",
                        "sortable": True,
                        "align": "left",
                    },
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
                @require_active_case
                def open_edit_dialog(e) -> None:
                    row = e.args
                    current_agents = load_agent_names()

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

                        NOTEAUTHOR_combo = ui.select(
                            options=current_agents,
                            label="Agent Name",
                            value=row["NOTEAUTHOR"] or None,
                            with_input=True,
                        ).classes("w-full")

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
                                color="transparent").props("flat"
                            ).classes("text-[var(--vsp-blue)]")

                            def on_save_update() -> None:
                                NOTEDATETIMEUPDATED = (
                                    NOTEDATETIMEUPDATED_input.value or ""
                                )
                                NOTEAUTHOR = NOTEAUTHOR_combo.value or ""
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
                                        note.NOTEAUTHOR = NOTEAUTHOR
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
                                color="var(--vsp-blue)").props("push"
                            ).classes("text-[var(--vsp-white)]")

                    edit_dialog.open()

                # ----- Delete confirmation dialog -----
                @require_active_case
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
                                color="transparent").props("flat"
                            ).classes("text-[var(--vsp-blue)]")

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
                                color="#EF4444").props("push"
                            ).classes("text-[var(--vsp-white)]")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)
                table.on("delete", open_delete_dialog)

        with ui.row().classes("w-full justify-center my-2"):

            # ----- DELETE ALL BUTTON -----
            @require_active_case
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

            case_exists = has_active_case()

            ui.button(
                "Delete All Notes",
                on_click=lambda: confirm_delete_all(
                    "notes",
                    delete_all_notes,
                ), color="#EF4444").props("push"
            ).classes("mb-2 items-center").set_enabled(case_exists)

    # ----- Initial render -----
    refresh_notes_table()
