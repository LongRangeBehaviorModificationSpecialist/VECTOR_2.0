"""The idle sign-out, and the search box above each table.

Neither needs a browser to be checked: what to do about a session idle
for a given time is a function of its own, and which pages offer a
search box is part of their spec.
"""

import re
from pathlib import Path

import pytest

import idle
from models import AuditLog, get_session
from parts import audit_page
from parts.agents_page import SPEC as AGENTS
from parts.cases_page import SPEC as CASES
from parts.evidence_page import SPEC as EVIDENCE
from parts.notes_page import SPEC as NOTES
from parts.persons_page import SPEC as PERSONS
from parts.rooms_page import SPEC as ROOMS
from program.config import Config


LIMIT = 30 * 60


# ----- The idle rule -----

@pytest.mark.parametrize("idle_seconds, expected", [
    (0, "wait"),
    (60, "wait"),
    (LIMIT - idle.WARN_BEFORE_SECONDS - 1, "wait"),
    (LIMIT - idle.WARN_BEFORE_SECONDS, "warn"),
    (LIMIT - 1, "warn"),
    (LIMIT, "end"),
    (3 * LIMIT, "end"),
])
def test_what_to_do_about_a_session_idle_this_long(idle_seconds, expected):
    assert idle.decide(idle_seconds, LIMIT) == expected


def test_a_timeout_of_zero_never_signs_anyone_out():
    """Some units will not want a scene tool signing itself out."""
    for idle_seconds in (0, 60, 60 * 60, 24 * 60 * 60):
        assert idle.decide(idle_seconds, 0) == "wait"


def test_the_limit_comes_from_the_setting(monkeypatch):
    monkeypatch.setattr(Config, "SESSION_IDLE_MINUTES", 45)
    assert idle.idle_limit_seconds() == 45 * 60

    monkeypatch.setattr(Config, "SESSION_IDLE_MINUTES", 0)
    assert idle.idle_limit_seconds() == 0

    # A negative setting is a typo, not an invitation to sign out at once.
    monkeypatch.setattr(Config, "SESSION_IDLE_MINUTES", -5)
    assert idle.idle_limit_seconds() == 0


def test_nothing_is_watched_when_the_timeout_is_off(monkeypatch):
    monkeypatch.setattr(Config, "SESSION_IDLE_MINUTES", 0)
    assert idle.sign_out_when_idle("admin") is None


def test_an_idle_sign_out_reaches_the_audit_trail():
    """A device left alone at a scene is worth knowing about."""
    idle.record_idle_sign_out("Doe, John")

    with get_session() as session:
        entry = (
            session.query(AuditLog)
            .filter(AuditLog.action == "LOGOUT_IDLE")
            .one()
        )
        assert entry.actor == "Doe, John"
        assert "without activity" in entry.summary


def test_an_idle_sign_out_can_be_filtered_for_on_the_audit_page():
    """A filter that cannot name the action hides it from whoever is
    looking for the device that was left."""
    assert "LOGOUT_IDLE" in audit_page.ACTION_CHOICES


def test_every_action_vector_records_can_be_filtered_for():
    """The filter list is typed out by hand, and a merge once dropped
    UPDATE from it -- the commonest entry after CREATE. Every action the
    application writes is looked for in its source and must be offered."""
    root = Path(audit_page.__file__).resolve().parent.parent
    recorded = {"CREATE", "UPDATE", "DELETE"}  # written by the flush listener
    for source in root.glob("*.py"):
        recorded |= set(re.findall(r'action="([A-Z_]+)"', source.read_text("utf-8")))
    for source in (root / "parts").glob("*.py"):
        recorded |= set(re.findall(r'action="([A-Z_]+)"', source.read_text("utf-8")))
    missing = recorded - set(audit_page.ACTION_CHOICES)
    assert not missing, f"Not in the Audit Trail filter: {sorted(missing)}"


# ----- The search box -----

@pytest.mark.parametrize(
    "spec",
    [AGENTS, ROOMS, EVIDENCE, PERSONS, NOTES],
    ids=lambda spec: spec.title,
)
def test_every_table_that_grows_offers_a_search(spec):
    assert spec.searchable, spec.title


def test_the_case_page_does_not_offer_one():
    """It holds one case, and a search box over a single row is noise."""
    assert not CASES.searchable
