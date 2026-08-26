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
from datetime import datetime

from models import get_session, Notes, Agents
from navbar import build_navbar
from main_page import (
    is_authenticated,
    get_current_user_name,
    get_is_admin,
    confirm_new_case_handler,
)


NOTIFICATION_TIMEOUT = 1500


# ── Helpers ─────────────────────────────────────────────────
def load_agent_names() -> list[str]:
    """Returns a list of all agent names from the Agents table."""
    with get_session() as session:
        rows = session.query(
            Agents.agent_name
        ).order_by(Agents.agent_name).all()
        return [r[0] for r in rows]


def get_current_timestamp() -> str:
    """Returns current date/time formatted as MM-DD-YYYY HH:MM:SS."""
    return datetime.now().strftime("%m-%d-%Y %H:%M:%S")


# ── Main Page Builder ────────────────────────────────────────
def build_notes_page():
    """Builds the full Notes page UI."""

    # ── Header / Navbar ──────────────────────────────────────
    build_navbar(
        is_admin=get_is_admin(),
        username=get_current_user_name(),
        on_new_case=confirm_new_case_handler,
    )

    with ui.column().classes("w-full items-center"):

        ui.label(
            "Notes Management"
        ).classes("text-2xl font-bold m-4")

        # ── Add Note Form ────────────────────────────────────────
        with ui.card().classes("w-full max-w-lg mx-auto p-6"):
            ui.label(
                "Add Note"
            ).classes("text-lg font-semibold mb-4")

            agent_options = load_agent_names()
            current_time = get_current_timestamp()

            # note_date_time — auto-populated, read-only
            note_date_time_input = ui.input(
                label="Date/Time Added",
                value=current_time,
            ).classes("w-full")
            note_date_time_input.props("readonly")

            # note_date_time_updated — hidden/auto, not shown on add form
            # (will be set when the note is updated via the edit dialog)

            # note_author — SelectField (required), populated from Agents
            note_author_combo = ui.select(
                options=agent_options,
                label="Agent Name",
                with_input=True,
            ).classes("w-full")

            # note_text — TextAreaField
            note_text_input = ui.textarea(
                label="Note"
            ).classes("w-full")

            # ── Buttons ────────────────────────────────────────
            with ui.row().classes("w-full justify-end gap-2 mt-4"):

                def clear_form():
                    note_date_time_input.value = get_current_timestamp()
                    note_author_combo.value = None
                    note_text_input.value = ""
                    ui.notify(
                        "Form cleared",
                        type="info",
                        timeout=NOTIFICATION_TIMEOUT
                    )

                def on_submit():
                    # ── Required field validation ──
                    note_author = note_author_combo.value
                    if not note_author:
                        ui.notify(
                            "Agent Name is required",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    note_text = note_text_input.value or ""
                    if not note_text:
                        ui.notify(
                            "Note text is required.",
                            type="warning",
                            timeout=NOTIFICATION_TIMEOUT,
                        )
                        return

                    note_date_time = (
                        note_date_time_input.value or 
                        get_current_timestamp()
                    )

                    # ── Save to database ──
                    with get_session() as session:
                        new_note = Notes(
                            note_date_time=note_date_time,
                            note_date_time_updated="",
                            note_author=note_author,
                            note_text=note_text,
                        )
                        session.add(new_note)

                    ui.notify(
                        f"Note from {note_author} was added successfully",
                        type="positive",
                        timeout=NOTIFICATION_TIMEOUT,
                    )
                    clear_form()
                    refresh_notes_table()

                ui.button(
                    "Clear",
                    on_click=clear_form,
                ).props("outline")

                ui.button(
                    "Add Note",
                    on_click=on_submit,
                ).props("unelevated")

        # ── Existing Notes Table ─────────────────────────────────
        ui.separator().classes("my-6")

        ui.label(
            "Current Notes"
        ).classes("text-xl font-bold mb-3")

        table_container = ui.column().classes(
            "w-full max-w-5xl mx-auto items-center gap-2"
        )

        def refresh_notes_table():
            """Re-renders the notes table from the database."""
            table_container.clear()

            with get_session() as session:
                notes = session.query(
                    Notes
                ).order_by(Notes.id.desc()).all()

                if not notes:
                    with table_container:
                        ui.label(
                            "No notes in the database yet"
                        ).classes("text-gray-500 italic")
                    return

                row_data = [
                    {
                        "id": r.id,
                        "note_date_time": r.note_date_time or "",
                        "note_date_time_updated": r.note_date_time_updated or "",
                        "note_author": r.note_author or "",
                        "note_text": r.note_text or "",
                    }
                    for r in notes
                ]

            with table_container:
                column_defs = [
                    {
                        "name": "note_date_time",
                        "label": "Date Added",
                        "field": "note_date_time",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "note_updated",
                        "label": "Date Updated",
                        "field": "note_date_time_updated",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "note_author",
                        "label": "Author",
                        "field": "note_author",
                        "sortable": True,
                        "align": "left",
                    },
                    {
                        "name": "note_text",
                        "label": "Note",
                        "field": "note_text",
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
                    row_key="id",
                )
                table.props("dense flat")

                # ── Slot: Actions column ──
                table.add_slot(
                    "body-cell-actions",
                    """
                    <q-td :props="props">
                        <div class="row no-wrap gap-1">
                            <q-btn dense flat color="primary"
                                icon="edit" size="sm"
                                @click="$parent.$emit('edit', props.row)" />
                            <q-btn dense flat color="negative"
                                icon="delete" size="sm"
                                @click="$parent.$emit('delete', props.row)" />
                        </div>
                    </q-td>
                """,
                )

                # ── Edit dialog ──────────────────────────────────
                def open_edit_dialog(e):
                    row = e.args
                    current_agents = load_agent_names()

                    with ui.dialog() as edit_dialog, ui.card().classes(
                        "w-full max-w-lg p-6"
                    ):
                        ui.label(
                            f"Edit Note #{row['id']}"
                        ).classes("text-lg font-semibold mb-4")

                        # Original date/time
                        edit_date_added = ui.input(
                            label="Date/Time Added",
                            value=row["note_date_time"],
                        ).classes("w-full")
                        edit_date_added.props("readonly")

                        # Updated date/time — auto-set to now
                        edit_date_updated = ui.input(
                            label="Date/Time Updated",
                            value=get_current_timestamp(),
                        ).classes("w-full")
                        edit_date_updated.props("readonly")

                        # Author — editable
                        edit_author = ui.select(
                            options=current_agents,
                            label="Agent Name",
                            value=row["note_author"] or None,
                            with_input=True,
                        ).classes("w-full")

                        # Note text — editable
                        edit_text = ui.textarea(
                            label="Note",
                            value=row["note_text"],
                        ).classes("w-full")

                        with ui.row().classes(
                            "w-full justify-end gap-2 mt-4"
                        ):
                            ui.button(
                                "Cancel",
                                on_click=edit_dialog.close,
                            ).props("flat")

                            def on_save_update():
                                new_author = edit_author.value or ""
                                if not new_author:
                                    ui.notify(
                                        "Agent Name is required",
                                        type="warning",
                                        timeout=NOTIFICATION_TIMEOUT,
                                    )
                                    return

                                new_text = edit_text.value or ""
                                
                                if not new_text:
                                    ui.notify(
                                        "Note text is required",
                                        type="warning",
                                        timeout=NOTIFICATION_TIMEOUT,
                                    )
                                    return

                                with get_session() as session:
                                    note = (
                                        session.query(
                                            Notes
                                        )
                                        .filter_by(id=row["id"])
                                        .first()
                                    )
                                    
                                    if note:
                                        # Only update these fields
                                        note.note_date_time_updated = (
                                            edit_date_updated.value
                                        )
                                        note.note_author = new_author
                                        note.note_text = new_text
                                        # session.commit()

                                ui.notify(
                                    f"Note from {new_author} was updated " 
                                    "successfully.",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )
                                edit_dialog.close()
                                refresh_notes_table()

                            ui.button(
                                "Update Note", 
                                on_click=on_save_update,
                            ).props("unelevated")

                    edit_dialog.open()

                # ── Delete confirmation dialog ──────────────────
                def open_delete_dialog(e):
                    row = e.args
                    with ui.dialog() as delete_dialog, ui.card().classes(
                        "max-w-sm p-6"
                    ):
                        ui.label(
                            "Confirm Deletion"
                        ).classes("text-lg font-semibold mb-2")
                        
                        ui.label(
                            f"Are you sure you want to delete "
                            "Note #{row['id']}?"
                        ).classes("mb-4")

                        # Show a preview of the note text (truncated)
                        preview = (
                            row["note_text"][:100] + "..."
                            if len(row["note_text"]) > 100
                            else row["note_text"]
                        )
                        ui.label(f"'{preview}'").classes(
                            "text-sm text-gray-500 italic mb-4"
                        )

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Cancel",
                                on_click=delete_dialog.close,
                            ).props("flat")

                            def on_confirm_delete():
                                with get_session() as session:
                                    note = (
                                        session.query(
                                            Notes
                                        )
                                        .filter_by(id=row["id"])
                                        .first()
                                    )

                                    if note:
                                        note_id = note.id
                                        session.delete(note)
                                    else:
                                        note_id = row["id"]

                                ui.notify(
                                    f"Note {note_id} was successfully "
                                    "deleted.",
                                    type="positive",
                                    timeout=NOTIFICATION_TIMEOUT,
                                )

                                delete_dialog.close()
                                refresh_notes_table()

                            ui.button(
                                "Delete",
                                on_click=on_confirm_delete
                            ).props("negative unelevated")

                    delete_dialog.open()

                table.on("edit", open_edit_dialog)

                table.on("delete", open_delete_dialog)

    # Initial render
    refresh_notes_table()


# ── Page Registration ────────────────────────────────────────
@ui.page("/notes")
def notes_page():
    if not is_authenticated():
        ui.navigate.to("/")
        return
    build_notes_page()
