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

from auth import require_session
from failures import explain, log
from live import refresh_on_change
from models import get_session
from parts.drafts import clear_draft, load_draft, save_draft
from parts.crud_dialogs import (
    delete_all_section,
    open_delete_dialog,
    open_edit_dialog,
)
# Field is re-exported: every page imports it from here.
from parts.crud_widgets import (  # noqa: F401
    Field,
    notify_done,
    notify_problem,
    options_including,
    select_value,
    typed_choice,
    _make_widget,
    _values_from,
)
from utils import require_active_case


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
    on_before_create: hook given the values the add form is about to save,
                    so a page can settle e.g. the next item number when the
                    item is saved rather than when the form was opened
    on_delete:      hook run inside a delete's transaction once the record
                    has gone, given the session and the removed record's
                    values; may return a sentence to add to the message
    delete_note:    gives a sentence for the delete dialog, given the row
    live_defaults:  add-form fields whose default is worked out again when
                    another device changes the case, such as the next item
                    number
    searchable:     whether a search box appears above the table. On for
                    every table that grows; off for the one-row case
    form_hint:      a line under the add form, saying something about how
                    it behaves -- which fields stay filled in, say
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
    on_before_create: Optional[Callable[[dict], None]] = None
    on_delete: Optional[Callable] = None
    delete_note: Optional[Callable[[dict], str]] = None
    live_defaults: tuple = ()
    searchable: bool = True
    form_hint: str = ""

    def __post_init__(self):
        self.entity_plural = self.entity_plural or f"{self.entity}s"
        self.label_field = self.label_field or self.fields[0].name
        self.table_title = self.table_title or f"Current {self.entity_plural}"
        self.submit_label = self.submit_label or f"Add {self.entity.title()}"
        self.order_by = self.order_by or self.row_key
        self.empty_text = (
            self.empty_text or f"No {self.entity_plural} have been entered"
        )


def _asked_for(name: str) -> str:
    """A value from the page's address, such as ?find=..., or ""."""
    try:
        return str(ui.context.client.request.query_params.get(name, ""))[:200]
    except Exception:
        # No page request in scope: a test, or a page being rebuilt.
        return ""


# ----- The builder -----
def build_crud_page(spec: CrudSpec) -> None:
    """Renders the complete page for one entity."""

    # Records belong to a case. The Cases page is the exception: it is
    # where a case is opened, so it has to work before one exists.
    case_guard = require_active_case if spec.requires_case else (lambda f: f)

    # And every action needs a session that is still current: a page left
    # open after its account was deleted kept saving under that name.
    def guard(handler):
        return require_session(case_guard(handler))

    # Column names as the page shows them, for explaining a failed save.
    labels = {f.name: f.label for f in spec.fields}

    with ui.column().classes("w-full items-center"):

        ui.label(spec.title).classes("text-2xl font-bold m-4")

        # ----- Add form -----
        form_widgets: dict = {}

        form_fields = [f for f in spec.fields if f.in_form]

        with ui.card().classes(f"w-full {spec.card_width} mx-auto p-6"):

            # Shown in place of the form while the table is full.
            limit_note = ui.html(spec.limit_message).classes(
                "w-full text-base text-[#F5B027]"
            )
            limit_note.set_visibility(False)

            # Everything the user fills in lives here, so it can be hidden
            # as one piece.
            form_body = ui.column().classes("w-full")

            with form_body:

                # Shown when the form opens with what was typed before and
                # not saved -- see parts/drafts.py.
                with ui.row().classes(
                    "w-full items-center gap-2 mb-2 draft-note"
                ) as draft_note:
                    ui.icon("restore", color="warning").classes("text-xl")
                    ui.label(
                        "Filled in from before: this was typed here and not "
                        "saved yet."
                    ).classes("text-sm text-[#F5B027] grow")
                    ui.button(
                        "Discard",
                        on_click=lambda: _clear_form(),
                        color="transparent",
                    ).props("flat dense").classes("hover-border-blue")
                draft_note.set_visibility(False)

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
                    # agent scroll while logging an item. But only where
                    # there is room: on a phone two columns of half a
                    # screen each cut every label short, so below a
                    # tablet's width the halves stack, in the same order.
                    half = (len(form_fields) + 1) // 2
                    with ui.grid().classes(
                        "w-full gap-6 items-start grid-cols-1 md:grid-cols-2"
                    ):
                        with ui.column().classes("gap-4"):
                            _render_fields(form_fields[:half])
                        with ui.column().classes("gap-4"):
                            _render_fields(form_fields[half:])
                else:
                    _render_fields(form_fields)

                if spec.on_form_ready:
                    spec.on_form_ready(form_widgets)

                if spec.form_hint:
                    ui.label(spec.form_hint).classes(
                        "w-full text-sm text-[var(--vsp-gray)] mt-2"
                    )

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button(
                        "Clear",
                        on_click=lambda: _clear_form(),
                        color="transparent").props("flat"
                    ).classes("p-3 hover-border-blue")

                    submit_button = ui.button(
                        spec.submit_label,
                        on_click=lambda: _submit(),
                        color="var(--vsp-blue)").props("push"
                    ).classes("p-3 hover-border-white")

        def _clear_form(after_add: bool = False) -> None:
            """Empties the add form. After a record is saved, the fields
            marked keep_after_add stay as they are, for the next one."""
            drafting["on"] = False
            for spec_field in spec.fields:
                widget = form_widgets.get(spec_field.name)
                if widget is None:
                    continue
                if after_add and spec_field.keep_after_add:
                    continue
                if spec_field.default:
                    widget.value = spec_field.default()
                elif spec_field.kind == "select":
                    widget.value = None
                else:
                    widget.value = ""
            # Saved, or cleared on purpose: nothing left to keep.
            clear_draft(spec.title)
            draft_note.set_visibility(False)
            drafting["on"] = True

        # ----- What was typed and not saved -----
        # Kept as it is typed, and put back when the form next opens, so
        # an idle sign-out or a dropped connection does not lose it. Only
        # what someone typed or chose: not a number VECTOR hands out.
        drafting = {"on": False}
        typed_fields = [f for f in form_fields if not f.readonly]

        def _keep_draft(_event=None) -> None:
            if not drafting["on"]:
                return
            values = {}
            for spec_field in typed_fields:
                value = form_widgets[spec_field.name].value
                if value in (None, ""):
                    continue
                if spec_field.default and value == spec_field.default():
                    continue
                values[spec_field.name] = value
            save_draft(spec.title, values)

        def _restore_draft() -> None:
            saved = load_draft(spec.title)
            restored = False
            for spec_field in typed_fields:
                if spec_field.name not in saved:
                    continue
                widget = form_widgets[spec_field.name]
                value = saved[spec_field.name]
                if spec_field.kind == "select":
                    # A room or agent since deleted is still put back.
                    widget.set_options(
                        options_including(widget.options, value), value=value
                    )
                else:
                    widget.value = value
                restored = True
            draft_note.set_visibility(restored)

        try:
            _restore_draft()
        except Exception:
            # A draft that no longer fits the form is not worth a page
            # that will not open.
            log.exception("Could not restore a draft on %s", spec.title)
            clear_draft(spec.title)
        drafting["on"] = True
        for spec_field in typed_fields:
            form_widgets[spec_field.name].on_value_change(_keep_draft)

        def _submit() -> None:
            values = _values_from(form_widgets, spec.fields)

            if spec.on_before_create:
                spec.on_before_create(values)

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
            _clear_form(after_add=True)
            refresh_table()

        _submit = guard(_submit)

        # ----- Table -----
        ui.separator().classes("my-6")
        ui.label(spec.table_title).classes("text-xl font-bold mb-1")

        # Finding item 47 among 120 by scrolling is how a detail gets
        # missed. Quasar filters the rows the table already holds, so
        # this costs no database work and keeps the sort order.
        search_box = None
        if spec.searchable:
            search_box = ui.input(
                placeholder=f"Search the {spec.entity_plural} below",
            ).props("dense outlined clearable").classes(
                "w-full max-w-md mb-2"
            )
            # Opened from the search in the top bar: the table starts
            # filtered to what was searched for.
            searched_for = _asked_for("find")
            if searched_for:
                search_box.value = searched_for

        # Wide enough for a long evidence row, and never wider than
        # the window: the table scrolls inside itself instead of taking
        # the page with it.
        table_container = ui.column().classes(
            "w-full max-w-[1536px] px-2 mx-auto items-center gap-2"
        )

        def _row_dict(record) -> dict:
            row = {spec.row_key: getattr(record, spec.row_key)}
            for spec_field in spec.fields:
                row[spec_field.name] = (
                    getattr(record, spec_field.name, "") or ""
                )
            return row

        def _apply_record_limit(count: int) -> None:
            """While the table holds all it may, the card shows only the
            limit message; otherwise it shows the form."""
            if not spec.max_records:
                return
            full = count >= spec.max_records
            # A page that sets a limit but no message keeps its form.
            hide_form = full and bool(spec.limit_message)
            form_body.set_visibility(not hide_form)
            limit_note.set_visibility(hide_form)
            submit_button.set_enabled(not full)

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
                # Fills its column rather than growing to fit the widest
                # row, which is what leaves Quasar's own scrolling to do
                # the work.
                table.classes("w-full")
                shown["table"] = table

                if search_box is not None:
                    table.bind_filter_from(
                        search_box,
                        "value",
                        backward=lambda typed: typed or "",
                    )

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
            open_edit_dialog(spec, event.args, labels, refresh_table)

        _open_edit_dialog = guard(_open_edit_dialog)

        # ----- Delete one -----
        def _open_delete_dialog(event) -> None:
            open_delete_dialog(spec, event.args, labels, refresh_table)

        _open_delete_dialog = guard(_open_delete_dialog)

        # ----- Delete all -----
        settle_delete_all = delete_all_section(
            spec, labels, refresh_table, guard
        )

        refresh_table()

        # Entries made on another device appear without a reload.
        def _live_refresh() -> None:
            refresh_table()
            # A number handed out on another device moves the next one on.
            for name in spec.live_defaults:
                spec_field = next(f for f in form_fields if f.name == name)
                form_widgets[name].set_value(spec_field.default())
            settle_delete_all()

        refresh_on_change(_live_refresh)
