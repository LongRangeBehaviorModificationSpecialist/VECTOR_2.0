#!/usr/bin/env python3

"""
crud.py

One table-driven builder for the entity pages.

Cases, agents, rooms, evidence, people and notes each hand-rolled the
same scaffold: a form, a table with an actions column, an edit dialog, a
delete dialog and a delete-all button. Around 3,500 near-duplicate
lines, with the Quasar actions slot pasted verbatim six times.

That duplication is why a rename could land in the models and half the
pages and go unnoticed: a change had six landing sites and nothing
checked it reached all of them. Declaring an entity once means a fix
happens once.

A page describes itself as a CrudSpec and gets the whole scaffold
back. Behaviour genuinely particular to one page -- evidence's triage
toggle, the agent roster auto-filling contact details -- is wired up
through the on_form_ready hook rather than by forking the builder.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from nicegui import ui

from failures import explain, log
from live import refresh_on_change
from models import get_session, has_active_case
from utils import (
    require_active_case,
    required_input,
    required_select,
    required_textarea,
)


# ----- Field description -----
@dataclass
class Field:
    """One column, and how it should be presented.

    name:        the model column
    label:       what the user sees
    kind:        input | select | textarea
    required:    renders with the red asterisk
    options:     callable returning select options, evaluated per render
                 so a newly added agent appears without a restart
    props:       extra Quasar props, e.g. an input mask
    placeholder: shown in the empty field
    readonly:    displayed but not editable
    in_form:     include in the add form
    in_edit:     include in the edit dialog
    in_table:    include as a table column
    table_label: column heading, when it should differ from `label`
    default:     callable producing the value for a fresh form
    new_values:  let a select accept a value that is not in its options
    """

    name: str
    label: str
    kind: str = "input"
    required: bool = False
    options: Optional[Callable[[], list]] = None
    props: str = ""
    placeholder: str = ""
    readonly: bool = False
    in_form: bool = True
    in_edit: bool = True
    in_table: bool = True
    table_label: Optional[str] = None
    default: Optional[Callable[[], str]] = None
    new_values: bool = False


@dataclass
class CrudSpec:
    """Everything the builder needs to render an entity page.

    model:          the SQLAlchemy class
    title:          page heading
    entity:         singular noun used in messages ("agent", "room")
    entity_plural:  used on the delete-all button
    fields:         the Field list
    validate:       (stage, values, row) -> True when INVALID
    row_key:        primary key column
    label_field:    column used to name a row in dialogs and messages
    table_title:    heading above the table
    submit_label:   text on the create button
    order_by:       column to sort the table by
    on_created:     hook run after a successful create, given the values
    on_before_update: hook given the values about to be written by an
                    edit, so a page can stamp e.g. a last-edited time
    on_form_ready:  hook run once the add-form widgets exist, given the
                    {name: widget} dict -- for behaviour that spans
                    fields, such as one field auto-filling others
    form_columns:   1 for a single column, 2 for a side-by-side grid
    card_width:     Tailwind max-width class for the form card
    show_delete_all: whether to offer the delete-all button
    requires_case:  whether adding, editing and deleting need an open case
    empty_text:     shown in place of the table when there are no rows
    id_label:       heading for an ID column; no ID column when blank
    max_records:    most rows the table may hold, 0 for no limit. The add
                    form closes once it is reached; the validator should
                    refuse the extra row as well
    limit_message:  shown on the add form while it is closed
    allow_delete:   whether each row offers a delete button
    sort_key:       orders the table's rows when the column's own order is
                    wrong for people -- item 10 after item 9, room AA after
                    room Z. Given a row dict; applied after order_by
    on_update:      hook run inside an edit's transaction, given the
                    session, the record's values before the edit and the
                    values being written -- for changes that must happen
                    with it, such as renaming a room's evidence
    """

    model: type
    title: str
    entity: str
    fields: list
    validate: Callable
    entity_plural: str = ""
    row_key: str = "Z_PK"
    label_field: str = ""
    table_title: str = ""
    submit_label: str = ""
    order_by: str = ""
    on_created: Optional[Callable[[dict], None]] = None
    on_before_update: Optional[Callable[[dict], None]] = None
    on_form_ready: Optional[Callable[[dict], None]] = None
    form_columns: int = 1
    card_width: str = "max-w-lg"
    show_delete_all: bool = True
    requires_case: bool = True
    empty_text: str = ""
    id_label: str = ""
    max_records: int = 0
    limit_message: str = ""
    allow_delete: bool = True
    sort_key: Optional[Callable[[dict], object]] = None
    on_update: Optional[Callable] = None

    def __post_init__(self):
        self.entity_plural = self.entity_plural or f"{self.entity}s"
        self.label_field = self.label_field or self.fields[0].name
        self.table_title = self.table_title or f"Current {self.entity_plural}"
        self.submit_label = self.submit_label or f"Add {self.entity.title()}"
        self.order_by = self.order_by or self.row_key
        self.empty_text = (
            self.empty_text or f"No {self.entity_plural} have been entered"
        )


# ----- Notification helpers -----
def notify_problem(message: str) -> None:
    """A problem the user has to acknowledge."""
    ui.notify(
        message,
        type="negative",
        timeout=0,
        position="center",
        close_button="OK",
    )


def notify_done(message: str) -> None:
    """A confirmation that can fade."""
    ui.notify(
        message,
        timeout=4000,
        position="bottom",
        close_button="OK",
    )


# ----- Widget construction -----
def options_including(options, value):
    """A dropdown's options, with the record's own value among them.

    A stored value need not be on today's list: an agent from an imported
    case is not on this machine's roster, and a room can be relabelled or
    an agent deleted after evidence was logged against them. NiceGUI
    refuses a value missing from the options, so the edit dialog failed to
    open, with nothing on screen to say why.
    """
    if value in (None, ""):
        return options
    if isinstance(options, dict):
        return options if value in options else {**options, value: value}
    options = list(options)
    return options if value in options else options + [value]


def select_value(value):
    """The value a dropdown opens with.

    A dropdown left blank is saved as "", which is never one of its
    options. NiceGUI refuses a value that is not an option, so the edit
    dialog for any record with a blank dropdown -- a room with no agents
    yet, an item nobody triaged -- failed to open, with nothing on screen.
    """
    return None if value == "" else value


def _make_widget(spec_field: Field, value=None):
    """Builds the input for one field."""
    factory_required = {
        "input": required_input,
        "select": required_select,
        "textarea": required_textarea,
    }
    factory_optional = {
        "input": ui.input,
        "select": ui.select,
        "textarea": ui.textarea,
    }

    if spec_field.kind == "select":
        value = select_value(value)

    kwargs = {}
    if value is not None:
        kwargs["value"] = value
    if spec_field.placeholder:
        kwargs["placeholder"] = spec_field.placeholder

    if spec_field.kind == "select":
        options = options_including(
            spec_field.options() if spec_field.options else [], value
        )
        kwargs["with_input"] = True
        if spec_field.new_values:
            kwargs["new_value_mode"] = "add"
        if spec_field.required:
            widget = factory_required["select"](
                label=spec_field.label, options=options, **kwargs
            )
        else:
            widget = factory_optional["select"](
                options=options, label=spec_field.label, **kwargs
            )
    else:
        if spec_field.required:
            widget = factory_required[spec_field.kind](
                label=spec_field.label, **kwargs
            )
        else:
            widget = factory_optional[spec_field.kind](
                label=spec_field.label, **kwargs
            )

    widget.classes("w-full")
    if spec_field.props:
        widget.props(spec_field.props)
    if spec_field.readonly:
        widget.props("readonly")
    return widget


def _values_from(widgets: dict) -> dict:
    """Reads the current value of every widget, normalised to str."""
    return {
        name: ("" if widget.value is None else widget.value)
        for name, widget in widgets.items()
    }


# ----- The builder -----
def build_crud_page(spec: CrudSpec) -> None:
    """Renders the complete page for one entity."""

    # Records belong to a case. The Cases page is the exception: it is
    # where a case is opened, so it has to work before one exists.
    guard = require_active_case if spec.requires_case else (lambda f: f)

    # Column names as the page shows them, for explaining a failed save.
    labels = {f.name: f.label for f in spec.fields}

    with ui.column().classes("w-full items-center"):

        ui.label(spec.title).classes("text-2xl font-bold m-4")

        # ----- Add form -----
        form_widgets: dict = {}

        form_fields = [f for f in spec.fields if f.in_form]

        with ui.card().classes(f"w-full {spec.card_width} mx-auto p-6"):

            def _render_fields(fields) -> None:
                for spec_field in fields:
                    default = (
                        spec_field.default() if spec_field.default else None
                    )
                    form_widgets[spec_field.name] = _make_widget(
                        spec_field, default
                    )

            if spec.form_columns == 2:
                # Evidence has fourteen fields; one column makes the
                # agent scroll while logging an item.
                half = (len(form_fields) + 1) // 2
                with ui.grid(columns=2).classes("w-full gap-6 items-start"):
                    with ui.column().classes("gap-4"):
                        _render_fields(form_fields[:half])
                    with ui.column().classes("gap-4"):
                        _render_fields(form_fields[half:])
            else:
                _render_fields(form_fields)

            if spec.on_form_ready:
                spec.on_form_ready(form_widgets)

            limit_note = ui.label(spec.limit_message).classes(
                "w-full text-sm text-[#F5B027]"
            )
            limit_note.set_visibility(False)

            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button(
                    "Clear",
                    on_click=lambda: _clear_form(),
                    color="transparent",
                ).props("flat").classes("text-[var(--vsp-blue)]")

                submit_button = ui.button(
                    spec.submit_label,
                    on_click=lambda: _submit(),
                    color="var(--vsp-blue)",
                ).props("push").classes("text-[var(--vsp-white)]")

        def _clear_form() -> None:
            for spec_field in spec.fields:
                widget = form_widgets.get(spec_field.name)
                if widget is None:
                    continue
                if spec_field.default:
                    widget.value = spec_field.default()
                elif spec_field.kind == "select":
                    widget.value = None
                else:
                    widget.value = ""

        def _submit() -> None:
            values = _values_from(form_widgets)

            if spec.validate(stage="initial", values=values, row=None):
                return

            # Server-set columns -- entry timestamps and the like -- are
            # declared with a default but kept out of the form, so they
            # are filled in here rather than by the user.
            for spec_field in spec.fields:
                if spec_field.name not in values and spec_field.default:
                    values[spec_field.name] = spec_field.default()

            try:
                with get_session() as session:
                    session.add(spec.model(**values))
            except Exception as err:
                log.exception("Could not save a new %s", spec.entity)
                notify_problem(
                    f"Could not save this {spec.entity}.\n\n"
                    f"{explain(err, labels)}"
                )
                return

            if spec.on_created:
                spec.on_created(values)

            notify_done(
                f"{spec.entity.title()} "
                f"{values.get(spec.label_field, '')} was added."
            )
            _clear_form()
            refresh_table()

        _submit = guard(_submit)

        # ----- Table -----
        ui.separator().classes("my-6")
        ui.label(spec.table_title).classes("text-xl font-bold mb-1")

        table_container = ui.column().classes(
            "w-full max-w-6xl mx-auto items-center gap-2"
        )

        def _row_dict(record) -> dict:
            row = {spec.row_key: getattr(record, spec.row_key)}
            for spec_field in spec.fields:
                row[spec_field.name] = (
                    getattr(record, spec_field.name, "") or ""
                )
            return row

        def _apply_record_limit(count: int) -> None:
            """Closes the add form while the table holds all it may."""
            if not spec.max_records:
                return
            full = count >= spec.max_records
            submit_button.set_enabled(not full)
            limit_note.set_visibility(full)

        shown = {"table": None}

        def refresh_table() -> None:
            """Re-reads the table from the database."""
            with get_session() as session:
                records = (
                    session.query(spec.model)
                    .order_by(getattr(spec.model, spec.order_by))
                    .all()
                )
                # Built inside the session, before it closes.
                rows = [_row_dict(record) for record in records]

            if spec.sort_key:
                rows.sort(key=spec.sort_key)

            _apply_record_limit(len(rows))

            # Rows are swapped in place when the table is already showing,
            # so a refresh keeps the sort order the user picked.
            table = shown["table"]
            if rows and table is not None and not table.is_deleted:
                table.rows = rows
                table.update()
                return

            table_container.clear()
            shown["table"] = None

            with table_container:
                if not rows:
                    ui.label(spec.empty_text).classes("text-red italic")
                    return

                columns = [
                    {
                        "name": spec_field.name,
                        "label": spec_field.table_label or spec_field.label,
                        "field": spec_field.name,
                        "sortable": True,
                        "align": "left",
                    }
                    for spec_field in spec.fields
                    if spec_field.in_table
                ]
                if spec.id_label:
                    columns.insert(
                        0,
                        {
                            "name": spec.row_key,
                            "label": spec.id_label,
                            "field": spec.row_key,
                            "sortable": True,
                            "align": "left",
                        },
                    )
                columns.append(
                    {
                        "name": "actions",
                        "label": "Actions",
                        "field": "actions",
                        "sortable": False,
                        "align": "center",
                    }
                )

                table = ui.table(
                    columns=columns,
                    rows=rows,
                    row_key=spec.row_key,
                )
                table.props("dense flat")
                shown["table"] = table

                # Defined once here, not pasted into six page modules.
                delete_button = (
                    """
                            <q-btn dense flat color="negative"
                                icon="delete" size="sm"
                                @click="$parent.$emit('delete', props.row)" />"""
                    if spec.allow_delete
                    else ""
                )
                table.add_slot(
                    "body-cell-actions",
                    f"""
                    <q-td :props="props">
                        <div class="row no-wrap gap-1">
                            <q-btn dense flat color="primary"
                                icon="edit" size="sm"
                                @click="$parent.$emit('edit', props.row)" />{delete_button}
                        </div>
                    </q-td>
                    """,
                )

                table.on("edit", _open_edit_dialog)
                if spec.allow_delete:
                    table.on("delete", _open_delete_dialog)

        # ----- Edit -----
        def _open_edit_dialog(event) -> None:
            row = event.args
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
                    ).props("flat").classes("text-[var(--vsp-blue)]")

                    def on_save_update() -> None:
                        values = _values_from(edit_widgets)

                        if spec.validate(
                            stage="update", values=values, row=row
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
                                        f"That {spec.entity} no longer "
                                        "exists. It may have been deleted "
                                        "on another device."
                                    )
                                    edit_dialog.close()
                                    refresh_table()
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
                        refresh_table()

                    ui.button(
                        "Update",
                        on_click=on_save_update,
                        color="var(--vsp-blue)",
                    ).props("push").classes("text-[var(--vsp-white)]")

            edit_dialog.open()

        _open_edit_dialog = guard(_open_edit_dialog)

        # ----- Delete one -----
        def _open_delete_dialog(event) -> None:
            # No button is drawn when deletes are off, but a crafted
            # event could still arrive, so refuse it here as well.
            if not spec.allow_delete:
                return
            row = event.args
            label = row.get(spec.label_field, "")

            with ui.dialog() as delete_dialog, ui.card().classes(
                "max-w-sm p-6"
            ):
                ui.label("Confirm Deletion").classes(
                    "mb-3 text-lg font-bold text-[var(--vsp-blue)]"
                )
                ui.label(
                    f"Delete {spec.entity} {label}?"
                ).classes("mb-2")
                ui.label(
                    "The record is removed, but the deletion and its "
                    "contents are kept in the audit trail."
                ).classes("mb-4 text-xs text-gray-400")

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button(
                        "Cancel",
                        on_click=delete_dialog.close,
                        color="transparent",
                    ).props("flat").classes("text-[var(--vsp-blue)]")

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
                                if record is not None:
                                    session.delete(record)
                        except Exception as err:
                            log.exception("Could not delete a %s", spec.entity)
                            notify_problem(
                                f"Could not delete this {spec.entity}.\n\n"
                                f"{explain(err, labels)}"
                            )
                            return

                        notify_done(
                            f"{spec.entity.title()} {label} was deleted."
                        )
                        delete_dialog.close()
                        refresh_table()

                    ui.button(
                        "Delete",
                        on_click=on_confirm_delete,
                        color="#ef4444",
                    ).props("push").classes("text-[var(--vsp-white)]")

            delete_dialog.open()

        _open_delete_dialog = guard(_open_delete_dialog)

        # ----- Delete all -----
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
                            f"This permanently deletes every "
                            f"{spec.entity} in this case. The deletions "
                            f"are kept in the audit trail, but the "
                            f"records are gone."
                        ).classes("mb-4 text-[var(--vsp-gray)]")

                        with ui.row().classes("w-full justify-end gap-2"):
                            ui.button(
                                "Cancel",
                                on_click=dialog.close,
                                color="transparent",
                            ).props("flat").classes(
                                "text-[var(--vsp-blue)]"
                            )

                            def on_confirm_delete_all() -> None:
                                try:
                                    with get_session() as session:
                                        # Loaded and deleted individually
                                        # so each removal reaches the
                                        # audit trail; a bulk delete
                                        # raises no ORM events.
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
                                refresh_table()

                            ui.button(
                                "Delete All",
                                on_click=on_confirm_delete_all,
                                color="#ef4444",
                            ).props("push").classes(
                                "text-[var(--vsp-white)]"
                            )

                    dialog.open()

                _open_delete_all_dialog = guard(_open_delete_all_dialog)

                delete_all_button = ui.button(
                    f"Delete All {spec.entity_plural.title()}",
                    on_click=_open_delete_all_dialog,
                    color="#ef4444",
                ).props("push")
                if spec.requires_case:
                    delete_all_button.set_enabled(has_active_case())

        refresh_table()

        # Entries made on another device appear without a reload.
        def _live_refresh() -> None:
            refresh_table()
            if spec.show_delete_all and spec.requires_case:
                delete_all_button.set_enabled(has_active_case())

        refresh_on_change(_live_refresh)
