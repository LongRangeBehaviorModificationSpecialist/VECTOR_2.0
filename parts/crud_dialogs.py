#!/usr/bin/env python3

"""
crud_dialogs.py

The three dialogs every entity page shares: edit one record, delete one
record, and delete every record of that kind.

They were written inside build_crud_page(), which ran to 514 lines. Each
takes what it needs -- the page's spec, the row, the column labels for
explaining a failure, and the function that redraws the table -- rather
than closing over a builder's locals.

parts/crud.py wires them to the table; the case guard stays there, on
the handlers it hands to the table.
"""

from typing import Callable

from nicegui import ui

from failures import explain, log
from models import get_session, has_active_case
from parts.crud_widgets import (
    notify_done,
    notify_problem,
    _make_widget,
    _values_from,
)


def open_edit_dialog(
        spec,
        row: dict,
        labels: dict,
        refresh: Callable[[], None]
) -> None:
    """Edits one record, and redraws the table once it is saved."""
    with ui.dialog() as edit_dialog, ui.card().classes(
        "w-full max-w-lg p-6"
    ):
        ui.label(
            f"Edit {spec.entity}: {row.get(spec.label_field, '')}"
        ).classes("text-lg font-semibold mb-4")

        edit_widgets = {}
        for spec_field in spec.fields:
            if not spec_field.in_edit:
                continue
            edit_widgets[spec_field.name] = _make_widget(
                spec_field, row.get(spec_field.name, "")
            )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button(
                "Cancel",
                on_click=edit_dialog.close,
                color="transparent",
            ).props("flat").classes("p-3 hover-border-blue")

            def on_save_update() -> None:
                values = _values_from(edit_widgets)

                if spec.validate(
                    stage="update",
                    values=values,
                    row=row,
                ):
                    return

                if spec.on_before_update:
                    spec.on_before_update(values)

                try:
                    with get_session() as session:
                        record = (
                            session.query(spec.model)
                            .filter_by(
                                **{spec.row_key: row[spec.row_key]}
                            )
                            .first()
                        )
                        if record is None:
                            notify_problem(
                                f"That {spec.entity} no longer exists. It may "
                                "have been deleted on another device."
                            )
                            edit_dialog.close()
                            refresh()
                            return

                        before = {
                            name: getattr(record, name)
                            for name in values
                        }
                        for name, value in values.items():
                            setattr(record, name, value)

                        if spec.on_update:
                            spec.on_update(session, before, values)

                except Exception as err:
                    log.exception("Could not update a %s", spec.entity)
                    notify_problem(
                        f"Could not update this {spec.entity}.\n\n"
                        f"{explain(err, labels)}"
                    )
                    return

                notify_done(
                    f"{spec.entity.title()} "
                    f"{values.get(spec.label_field, '')} was updated."
                )
                edit_dialog.close()
                refresh()

            ui.button(
                f"Update {spec.entity}",
                on_click=on_save_update,
                color="var(--vsp-blue)",
            ).props("push").classes("p-3 hover-border-white")

    edit_dialog.open()


def open_delete_dialog(
        spec,
        row: dict,
        labels: dict,
        refresh: Callable[[], None]
) -> None:
    """Deletes one record, after saying what that will do."""
    # No button is drawn when deletes are off, but a crafted
    # event could still arrive, so refuse it here as well.
    if not spec.allow_delete:
        return
    label = row.get(spec.label_field, "")

    with ui.dialog() as delete_dialog, ui.card().classes(
        "max-w-sm p-6"
    ):
        ui.label("Confirm Deletion").classes(
            "mb-3 text-lg font-bold text-[var(--vsp-blue)]"
        )
        ui.label(
            f"Delete {spec.entity} {label}?"
        ).classes("mb-2 text-base")

        note = spec.delete_note(row) if spec.delete_note else ""

        if note:
            ui.label(note).classes("mb-2 text-base text-[#F5B027]")
        ui.label(
            "The record is removed, but the deletion and its "
            "contents are kept in the audit trail."
        ).classes("mb-4 text-sm text-white")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button(
                "Cancel",
                on_click=delete_dialog.close,
                color="transparent",
            ).props("flat").classes("p-3 hover-border-blue")

            def on_confirm_delete() -> None:
                try:
                    with get_session() as session:
                        record = (
                            session.query(spec.model)
                            .filter_by(
                                **{spec.row_key: row[spec.row_key]}
                            )
                            .first()
                        )

                        follow_up = ""

                        if record is not None:
                            removed = {
                                spec_field.name: getattr(
                                    record, spec_field.name, None
                                )
                                for spec_field in spec.fields
                            }

                            session.delete(record)
                            if spec.on_delete:
                                session.flush()
                                follow_up = (
                                    spec.on_delete(session, removed)
                                    or ""
                                )

                except Exception as err:
                    log.exception(f"Could not delete a {spec.entity}")
                    notify_problem(
                        f"Could not delete this {spec.entity}.\n\n"
                        f"{explain(err, labels)}"
                    )
                    return

                notify_done(
                    f"{spec.entity.title()} {label} was deleted."
                    + (f" {follow_up}" if follow_up else "")
                )
                delete_dialog.close()
                refresh()

            ui.button(
                f"Delete {spec.entity}",
                on_click=on_confirm_delete,
                color="#ef4444",
            ).props("push").classes("p-3 hover-border-white")

    delete_dialog.open()


def delete_all_section(
        spec,
        labels: dict,
        refresh: Callable[[], None],
        guard: Callable
) -> Callable[[], None]:
    """Draws Delete All, and returns what settles the button's state.

    The button is disabled while no case is open, which the page's live
    refresh has to put right when a case is opened on another device.
    """
    if spec.show_delete_all:
        with ui.row().classes("w-full justify-center my-4"):

            def _open_delete_all_dialog() -> None:
                with ui.dialog() as dialog, ui.card().classes(
                    "max-w-sm p-6"
                ):
                    ui.label("Warning!").classes(
                        "text-lg font-bold mb-2 text-[var(--vsp-blue)]"
                    )
                    ui.label(
                        f"This permanently deletes every {spec.entity} in "
                        f"this case. The deletions are kept in the audit "
                        f"trail, but the records are gone."
                    ).classes("mb-4 text-[var(--vsp-gray)]")

                    with ui.row().classes("w-full justify-end gap-2"):
                        ui.button(
                            "Cancel",
                            on_click=dialog.close,
                            color="transparent",
                        ).props("flat").classes("p-3 hover-border-blue")

                        def on_confirm_delete_all() -> None:
                            try:
                                with get_session() as session:
                                    # Loaded and deleted individually so each
                                    # removal reaches the audit trail; a bulk
                                    # delete raises no ORM events.
                                    for record in session.query(
                                        spec.model
                                    ).all():
                                        session.delete(record)

                            except Exception as err:
                                log.exception(
                                    "Could not delete every %s",
                                    spec.entity,
                                )
                                notify_problem(
                                    "Nothing was deleted.\n\n"
                                    f"{explain(err, labels)}"
                                )
                                dialog.close()
                                return

                            notify_done(
                                f"All {spec.entity_plural} were deleted."
                            )
                            dialog.close()
                            refresh()

                        ui.button(
                            "Delete All",
                            on_click=on_confirm_delete_all,
                            color="#ef4444",
                        ).props("push").classes("p-3 hover-border-white")

                dialog.open()

            _open_delete_all_dialog = guard(_open_delete_all_dialog)

            delete_all_button = ui.button(
                f"Delete All {spec.entity_plural.title()}",
                on_click=_open_delete_all_dialog,
                color="#ef4444",
            ).props("push").classes("p-3 hover-border-white")

            if spec.requires_case:
                delete_all_button.set_enabled(has_active_case())

    def settle() -> None:
        if spec.show_delete_all and spec.requires_case:
            delete_all_button.set_enabled(has_active_case())

    if not spec.show_delete_all:
        return lambda: None

    return settle
