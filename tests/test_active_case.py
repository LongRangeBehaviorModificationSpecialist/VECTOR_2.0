"""
test_active_case.py

The active case.

Agents, rooms, evidence and the rest belong to a case, so the pages that
record them refuse to until one has been opened. Ported from upstream,
where the same guard sits on every add, edit and delete.
"""

import asyncio
import inspect

import pytest

import models
import utils
import parts.agents_page as agents_page
import parts.cases_page as cases_page
import parts.evidence_page as evidence_page
import parts.notes_page as notes_page
import parts.persons_page as persons_page
import parts.rooms_page as rooms_page


@pytest.fixture
def notices(monkeypatch):
    captured = []
    monkeypatch.setattr(
        utils.ui,
        "notify",
        lambda message,
        **kw: captured.append(str(message))
    )
    return captured


# ----- Detecting a case -----

def test_an_empty_database_has_no_active_case():
    assert models.has_active_case() is False
    assert models.check_case_info() is None


def test_an_opened_case_is_active(case):
    assert models.has_active_case() is True
    assert models.check_case_info()["CASENUMBER"] == case


# ----- The guard -----

def test_the_guard_stops_an_action_without_a_case(notices):
    calls = []

    @utils.require_active_case
    def add_item():
        calls.append("ran")
        return "saved"

    assert add_item() is None
    assert calls == []
    assert any("No active case" in text for text in notices)


def test_the_guard_lets_an_action_through_with_a_case(case, notices):
    @utils.require_active_case
    def add_item(value):
        return value

    assert add_item("saved") == "saved"
    assert notices == []


def test_an_async_handler_stays_async(case):
    """The file upload handler is async. Wrapping it must not leave a
    coroutine that nothing awaits.
    """

    @utils.require_active_case
    async def upload(event):
        return event

    assert inspect.iscoroutinefunction(upload)
    assert asyncio.run(upload("file")) == "file"


def test_an_async_handler_is_stopped_without_a_case(notices):
    @utils.require_active_case
    async def upload(event):
        raise AssertionError("must not run")

    assert asyncio.run(upload("file")) is None
    assert any("No active case" in text for text in notices)


def test_the_guard_keeps_the_handler_signature():
    """NiceGUI reads a handler's parameters to decide whether to pass the
    event, so the wrapper has to still look like the original.
    """

    @utils.require_active_case
    def on_edit(event):
        return event

    assert list(inspect.signature(on_edit).parameters) == ["event"]


# ----- Which pages use it -----

@pytest.mark.parametrize(
    "spec",
    [
        agents_page.SPEC,
        evidence_page.SPEC,
        notes_page.SPEC,
        persons_page.SPEC,
        rooms_page.SPEC,
    ],
    ids=lambda spec: spec.title,
)
def test_entity_pages_require_a_case(spec):
    assert spec.requires_case is True


def test_the_cases_page_works_without_a_case():
    """It is where a case gets opened."""
    assert cases_page.SPEC.requires_case is False
