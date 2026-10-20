"""
test_accounts_and_sessions.py

Temporary passwords, sessions ended from elsewhere, the sign-in pause,
and account events in the audit trail.

Each of these was found in the October review by trying it, not by a
test: a temporary password was a full sign-in once the Change Password
page was skipped; a page left open after its account was deleted kept
saving; a wrong password paused every connected device; and creating,
resetting or deleting an account left no trace in the trail.

The browser's session is a plain dict here, and the generation counters
are in memory, as in test_auth.py.
"""

import ast
import asyncio
import inspect
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import auth
import idle
import models
from models import AuditLog, Users, get_session

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def browser(monkeypatch):
    """One browser's session, and the counters that end sessions."""
    store = {}
    counters = {"all": 0, "users": {}}
    monkeypatch.setattr(auth, "_session_store", lambda: store)
    monkeypatch.setattr(auth, "global_generation", lambda: counters["all"])
    monkeypatch.setattr(
        auth, "user_generation",
        lambda name: counters["users"].get(name, 0),
    )

    def end_one(name):
        counters["users"][name] = counters["users"].get(name, 0) + 1
        return True

    def end_all():
        counters["all"] += 1
        return True

    monkeypatch.setattr(auth, "invalidate_user_sessions", end_one)
    monkeypatch.setattr(auth, "invalidate_all_sessions", end_all)
    return store


@pytest.fixture
def went_to(monkeypatch):
    """Where the page was sent, in order."""
    places = []
    monkeypatch.setattr(auth.ui.navigate, "to", places.append)
    monkeypatch.setattr(auth.ui, "notify", lambda *_a, **_k: None)
    return places


# ----- A temporary password -----

def test_a_temporary_password_is_not_a_sign_in(browser):
    auth.sign_in("agent", False, must_change_password=True)
    assert not auth.is_authenticated()
    assert auth.signed_in_with_temporary_password()
    assert auth.where_to_sign_in() == "/change-password"


def test_an_ordinary_sign_in_is_one(browser):
    auth.sign_in("agent", False)
    assert auth.is_authenticated()
    assert not auth.signed_in_with_temporary_password()
    assert auth.where_to_sign_in() == "/"


@pytest.mark.parametrize("guard", [auth.require_login, auth.require_admin])
def test_every_page_sends_a_temporary_password_back_to_change_it(
        browser, went_to, guard):
    """Typing /notes, or pressing Home, used to carry on without it."""
    drawn = []
    page = guard(lambda: drawn.append("page"))

    auth.sign_in("admin", True, must_change_password=True)
    page()

    assert drawn == []
    assert went_to == ["/change-password"]


def test_a_temporary_admin_password_is_not_an_admin(browser):
    auth.sign_in("admin", True, must_change_password=True)
    assert auth.get_is_admin() is False


def test_replacing_it_makes_a_full_sign_in(browser):
    auth.sign_in("agent", False, must_change_password=True)
    assert auth.finish_password_change("agent", False)
    assert auth.is_authenticated()
    assert not auth.password_change_pending()


def test_replacing_it_ends_every_other_session_of_the_account(browser):
    """Another device signed in with the same temporary password could
    otherwise set a password of its own over this one."""
    auth.sign_in("agent", False, must_change_password=True)
    other_device = dict(browser)

    auth.finish_password_change("agent", False)
    assert auth.is_authenticated()

    browser.clear()
    browser.update(other_device)
    assert not auth.is_authenticated()
    assert not auth.signed_in_with_temporary_password()


def test_signing_out_clears_a_pending_change(browser):
    auth.sign_in("agent", False, must_change_password=True)
    auth.sign_out()
    assert not auth.signed_in_with_temporary_password()
    assert auth.where_to_sign_in() == "/"


# ----- A session ended from another device -----

def test_an_open_page_cannot_save_once_its_account_is_deleted(
        browser, went_to):
    saved = []
    save = auth.require_session(lambda: saved.append("note"))

    auth.sign_in("agent", False)
    save()
    assert saved == ["note"]

    auth.invalidate_user_sessions("agent")
    save()
    assert saved == ["note"]
    assert went_to == ["/"]


def test_the_check_keeps_an_async_handler_async(browser, went_to):
    """The file upload is async, and NiceGUI must still await it."""
    uploaded = []

    async def upload():
        uploaded.append("photo")

    guarded = auth.require_session(upload)
    assert inspect.iscoroutinefunction(guarded)

    auth.sign_in("agent", False)
    auth.invalidate_all_sessions()
    asyncio.run(guarded())
    assert uploaded == []
    assert went_to == ["/"]


def test_sign_everyone_out_ends_an_open_admin_page(browser):
    """get_is_admin() read the flag stamped at sign-in, so an admin page
    left open could still reset and delete accounts."""
    auth.sign_in("admin", True)
    assert auth.get_is_admin()
    auth.invalidate_all_sessions()
    assert auth.get_is_admin() is False


def test_the_sign_in_page_says_why_the_device_is_back_there(
        browser, went_to):
    auth.sign_in("agent", False)
    auth.invalidate_user_sessions("agent")
    auth.leave_ended_session()

    assert auth.take_session_ended_notice() is True
    assert auth.take_session_ended_notice() is False


def test_pressing_logout_needs_no_explanation(browser, went_to):
    auth.sign_in("agent", False)
    auth.sign_out()
    auth.leave_ended_session()
    assert auth.take_session_ended_notice() is False


def test_an_open_page_notices_within_seconds(browser, went_to, monkeypatch):
    """Every signed-in page runs this through the navbar."""
    timers = []
    monkeypatch.setattr(
        idle.ui, "timer",
        lambda interval, callback: timers.append((interval, callback)),
    )
    idle.leave_when_signed_out()
    (interval, check), = timers
    assert interval <= 10

    auth.sign_in("agent", False)
    check()
    assert went_to == []

    auth.invalidate_user_sessions("agent")
    check()
    assert went_to == ["/"]


def test_the_navbar_starts_the_watch():
    import navbar
    assert "leave_when_signed_out()" in inspect.getsource(navbar.build_navbar)


def _decorators(path: Path) -> dict:
    """Every function in a file, with the names of its decorators."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names = {
                d.id if isinstance(d, ast.Name) else getattr(d, "attr", "")
                for d in node.decorator_list
            }
            found.setdefault(node.name, []).append(names)
    return found


@pytest.mark.parametrize(
    "path, handler",
    [
        ("parts/crud_dialogs.py", "on_save_update"),
        ("parts/crud_dialogs.py", "on_confirm_delete"),
        ("parts/crud_dialogs.py", "on_confirm_delete_all"),
        ("parts/file_upload.py", "handle_upload"),
        ("parts/file_table.py", "open_delete_dialog"),
        ("parts/file_table.py", "on_confirm_delete"),
        ("parts/file_table.py", "delete_all_files"),
        ("parts/case_transfer.py", "do_export"),
        ("parts/case_transfer.py", "do_import"),
        ("parts/case_transfer.py", "do_delete"),
        ("parts/reports_page.py", "on_change"),
        ("home_page.py", "confirm_new_case_handler"),
        ("home_page.py", "on_proceed"),
    ],
)
def test_every_button_that_changes_the_case_checks_the_session(path, handler):
    found = _decorators(ROOT / path)
    assert found.get(handler), f"{handler} is not in {path}"
    for decorators in found[handler]:
        assert "require_session" in decorators, f"{path}: {handler}"


def test_the_entity_pages_check_the_session_too():
    import parts.crud as crud
    assert "require_session(case_guard(handler))" in inspect.getsource(
        crud.build_crud_page
    )


# ----- The pause after failed sign-ins -----

def test_the_sign_in_never_sleeps_on_the_shared_loop():
    """time.sleep() in the sign-in paused every connected device, for up
    to two seconds a try."""
    source = (ROOT / "home_page.py").read_text(encoding="utf-8")
    assert "time.sleep" not in source
    assert "async def attempt_login" in source
    assert "await asyncio.sleep(delay)" in source
    # The password check is a quarter of a second of bcrypt.
    assert "await run.io_bound(" in source


def test_the_password_check_stands_on_its_own():
    """So it can run in a thread, apart from the account's session."""
    user = Users(USERNAME="agent", ISADMIN=False, ISACTIVE=True)
    user.set_password("a-test-password")
    assert models.password_matches("a-test-password", user.PASSWORDHASH)
    assert not models.password_matches("wrong", user.PASSWORDHASH)
    assert not models.password_matches("anything", None)
    assert user.check_password_correction("a-test-password")


# ----- Failed sign-ins for names that are not accounts -----

@pytest.fixture
def failures(monkeypatch):
    store = {}
    monkeypatch.setattr(auth, "_failures", lambda: dict(store))
    monkeypatch.setattr(
        auth, "_save_failures",
        lambda data: store.clear() or store.update(data),
    )
    return store


def _ago(minutes):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def test_made_up_names_do_not_pile_up(failures):
    """A name that was never an account is never cleared by a successful
    sign-in, so every one tried used to stay on the list for good."""
    for number in range(50):
        failures[f"made.up.{number}"] = {"count": 1, "first_seen": _ago(90)}

    auth.record_login_failure("agent")
    assert set(failures) == {"agent"}


def test_a_lock_still_running_is_kept(failures):
    failures["agent"] = {
        "count": auth.LOCK_AFTER_FAILURES,
        "first_seen": _ago(auth.FAILURE_WINDOW_MINUTES + 5),
        "locked_until": (
            datetime.now(timezone.utc) + timedelta(minutes=5)
        ).isoformat(),
    }
    auth.record_login_failure("someone.else")
    assert "agent" in failures
    assert auth.lockout_seconds_remaining("agent") > 0


def test_recent_failures_are_kept(failures):
    failures["agent"] = {"count": 2, "first_seen": _ago(5)}
    auth.record_login_failure("someone.else")
    assert failures["agent"]["count"] == 2


# ----- Account events in the audit trail -----

def test_an_account_event_reaches_the_trail():
    assert models.record_account_event(
        action="USER_CREATED",
        row_pk=7,
        summary="new.agent",
        actor="admin",
    )
    with get_session() as session:
        entry = session.query(AuditLog).order_by(AuditLog.id.desc()).first()
        assert (entry.action, entry.actor, entry.table_name, entry.row_pk) == (
            "USER_CREATED", "admin", "users", 7
        )
        assert entry.chain
    ok, _said = models.verify_audit_chain()
    assert ok


def test_an_unwritable_trail_is_reported_not_raised(monkeypatch):
    """The account change has already been made in users.db by then."""
    def broken():
        raise RuntimeError("the disk is full")

    monkeypatch.setattr(models, "get_session", broken)
    assert models.record_account_event(action="LOGOUT") is False


@pytest.mark.parametrize(
    "path, action",
    [
        ("parts/admin_users.py", "USER_CREATED"),
        ("parts/admin_users.py", "PASSWORD_RESET"),
        ("parts/admin_users.py", "USER_DELETED"),
        ("parts/admin_users.py", "LOCK_CLEARED"),
        ("parts/admin_users.py", "SIGN_OUT_ALL"),
        ("main.py", "PASSWORD_CHANGED"),
        ("home_page.py", "LOGOUT"),
        ("home_page.py", "SHUTDOWN"),
    ],
)
def test_every_account_action_is_recorded(path, action):
    source = (ROOT / path).read_text(encoding="utf-8")
    assert f'action="{action}"' in source
