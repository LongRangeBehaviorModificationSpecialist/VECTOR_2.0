"""Page specifications.

Each entity page is now a CrudSpec rather than 500 lines of hand-written
scaffold. That makes the pages checkable without a browser: every field
must name a real column, every validator must accept the shape the
builder passes it, and every default must actually produce a value.

This is the guard against the failure that started all of this -- a
rename that reached the models but not everything that referenced them.
Here it fails a test instead of reaching a search warrant.
"""

import pytest

from parts.crud import CrudSpec, Field
import parts.agents_page as agents_page
import parts.cases_page as cases_page
import parts.evidence_page as evidence_page
import parts.notes_page as notes_page
import parts.persons_page as persons_page
import parts.rooms_page as rooms_page


SPECS = {
    "agents": agents_page.SPEC,
    "cases": cases_page.SPEC,
    "evidence": evidence_page.SPEC,
    "notes": notes_page.SPEC,
    "persons": persons_page.SPEC,
    "rooms": rooms_page.SPEC,
}

ALL_SPECS = list(SPECS.items())


@pytest.mark.parametrize("name,spec", ALL_SPECS)
def test_every_field_names_a_real_column(name, spec):
    """A renamed column must not be able to reach a page unnoticed."""
    columns = {column.name for column in spec.model.__table__.columns}
    declared = {spec_field.name for spec_field in spec.fields}
    unknown = declared - columns
    assert not unknown, (
        f"{name} declares fields that do not exist on "
        f"{spec.model.__name__}: {sorted(unknown)}"
    )


@pytest.mark.parametrize("name,spec", ALL_SPECS)
def test_required_columns_are_all_on_the_form(name, spec):
    """A NOT NULL column with no form field can never be filled in."""
    required_columns = {
        column.name
        for column in spec.model.__table__.columns
        if not column.nullable and not column.primary_key
    }
    provided = {
        spec_field.name
        for spec_field in spec.fields
        if spec_field.in_form or spec_field.default
    }
    missing = required_columns - provided
    assert not missing, (
        f"{name} cannot supply required columns: {sorted(missing)}"
    )


@pytest.mark.parametrize("name,spec", ALL_SPECS)
def test_label_field_and_order_by_are_real(name, spec):
    columns = {column.name for column in spec.model.__table__.columns}
    assert spec.label_field in columns
    assert spec.order_by in columns
    assert spec.row_key in columns


@pytest.mark.parametrize("name,spec", ALL_SPECS)
def test_defaults_produce_a_value(name, spec):
    """Auto-assigned fields -- item numbers, room labels -- must work."""
    for spec_field in spec.fields:
        if spec_field.default is None:
            continue
        value = spec_field.default()
        assert value is not None, f"{name}.{spec_field.name} default is None"
        assert str(value) != "", f"{name}.{spec_field.name} default is blank"


@pytest.mark.parametrize("name,spec", ALL_SPECS)
def test_select_options_are_callable_and_return_lists(name, spec):
    for spec_field in spec.fields:
        if spec_field.kind != "select":
            continue
        assert spec_field.options is not None, (
            f"{name}.{spec_field.name} is a select with no options"
        )
        assert isinstance(spec_field.options(), list)


@pytest.mark.parametrize("name,spec", ALL_SPECS)
def test_validator_accepts_an_empty_submission(name, spec):
    """The builder always passes (stage, values, row); an empty form
    must be reported as invalid rather than raising."""
    values = {f.name: "" for f in spec.fields}
    assert spec.validate(stage="initial", values=values, row=None) is True


@pytest.mark.parametrize("name,spec", ALL_SPECS)
def test_validator_accepts_missing_keys(name, spec):
    """A field absent from the form must not produce a KeyError."""
    assert spec.validate(stage="initial", values={}, row=None) is True


def test_evidence_form_is_two_columns():
    """Fourteen fields in one column makes an agent scroll mid-item."""
    assert evidence_page.SPEC.form_columns == 2


def test_notes_author_is_not_editable():
    """Authorship is fixed at creation; the trail records later edits."""
    author = next(
        f for f in notes_page.SPEC.fields if f.name == "NOTEAUTHOR"
    )
    assert author.readonly is True


def test_notes_author_defaults_to_the_session_user():
    author = next(
        f for f in notes_page.SPEC.fields if f.name == "NOTEAUTHOR"
    )
    # No web session in the tests, so this is the documented fallback.
    assert author.default() == "unknown"


def test_evidence_number_is_not_user_editable():
    """A typed-over item number defeats the uniqueness guarantee."""
    number = next(
        f for f in evidence_page.SPEC.fields if f.name == "EVIDNUM"
    )
    assert number.readonly is True


def test_cases_page_has_no_delete_all():
    """Clearing the case goes through Make New Case File, which wipes
    attachments too."""
    assert cases_page.SPEC.show_delete_all is False


def test_spec_defaults_fill_themselves_in():
    """__post_init__ derives the labels a page did not spell out."""
    spec = CrudSpec(
        model=persons_page.Persons,
        title="T",
        entity="person",
        fields=[Field("SUSPECTNAME", "Name")],
        validate=lambda **kwargs: False,
    )
    assert spec.entity_plural == "persons"
    assert spec.label_field == "SUSPECTNAME"
    assert spec.submit_label == "Add Person"
