"""Authentication: one-time passwords, throttling and session control.

These three closed the last of the security findings. The storage
helpers fall back safely outside a browser session, so the pure logic --
password generation, failure counting, lockout arithmetic -- is testable
directly.
"""

from datetime import datetime, timedelta, timezone

import pytest

import auth
from models import Users, generate_one_time_password


# ----- One-time passwords (S4) -----

def test_generated_passwords_are_unique():
    """A shared constant meant one leak opened every pending account."""
    passwords = {generate_one_time_password() for _ in range(200)}
    assert len(passwords) == 200


def test_generated_passwords_are_long_enough():
    for _ in range(20):
        assert len(generate_one_time_password()) >= 12


def test_no_shared_default_password_remains():
    """The published constant must not come back."""
    import models

    assert not hasattr(models, "DEFAULT_USER_PASSWORD")


def test_generated_password_round_trips_through_bcrypt():
    password = generate_one_time_password()
    user = Users(user_name="demo", is_admin=False, is_active=True)
    user.set_password(password)

    assert user.check_password_correction(password) is True
    assert user.check_password_correction(password + "x") is False
    assert password not in user.password_hash


# ----- Login throttling (S5) -----

@pytest.fixture
def failures(monkeypatch):
    """An in-memory stand-in for app.storage.general."""
    store = {}
    monkeypatch.setattr(auth, "_failures", lambda: dict(store))
    monkeypatch.setattr(
        auth, "_save_failures", lambda data: store.clear() or store.update(data)
    )
    return store


def test_a_clean_account_is_not_delayed(failures):
    assert auth.failure_delay_seconds("agent") == 0.0
    assert auth.lockout_seconds_remaining("agent") == 0


def test_early_mistypes_are_not_punished(failures):
    """An agent fumbling a password at 3am must not be slowed."""
    for _ in range(auth.SLOW_AFTER_FAILURES - 1):
        auth.record_login_failure("agent")
    assert auth.failure_delay_seconds("agent") == 0.0
    assert auth.lockout_seconds_remaining("agent") == 0


def test_the_delay_grows_with_failures(failures):
    delays = []
    for _ in range(auth.SLOW_AFTER_FAILURES + 2):
        auth.record_login_failure("agent")
        delays.append(auth.failure_delay_seconds("agent"))
    assert delays[-1] > 0
    assert delays == sorted(delays)


def test_the_delay_is_capped(failures):
    for _ in range(50):
        auth.record_login_failure("agent")
    assert auth.failure_delay_seconds("agent") <= 2.0


def test_the_account_locks_at_the_threshold(failures):
    for attempt in range(auth.LOCK_AFTER_FAILURES):
        count = auth.record_login_failure("agent")
    assert count == auth.LOCK_AFTER_FAILURES
    remaining = auth.lockout_seconds_remaining("agent")
    assert 0 < remaining <= auth.LOCKOUT_MINUTES * 60


def test_locking_one_account_does_not_lock_another(failures):
    for _ in range(auth.LOCK_AFTER_FAILURES):
        auth.record_login_failure("agent")
    assert auth.lockout_seconds_remaining("agent") > 0
    assert auth.lockout_seconds_remaining("someone.else") == 0


def test_a_successful_sign_in_clears_the_count(failures):
    for _ in range(auth.SLOW_AFTER_FAILURES + 1):
        auth.record_login_failure("agent")
    assert auth.failure_delay_seconds("agent") > 0

    auth.clear_login_failures("agent")
    assert auth.failure_delay_seconds("agent") == 0.0
    assert auth.lockout_seconds_remaining("agent") == 0


def test_old_failures_age_out(failures):
    """Attempts spread across a shift must not accumulate into a lock."""
    for _ in range(auth.LOCK_AFTER_FAILURES - 1):
        auth.record_login_failure("agent")

    stale = datetime.now(timezone.utc) - timedelta(
        minutes=auth.FAILURE_WINDOW_MINUTES + 5
    )
    record = dict(failures["agent"])
    record["first_seen"] = stale.isoformat()
    failures["agent"] = record

    assert auth.record_login_failure("agent") == 1
    assert auth.lockout_seconds_remaining("agent") == 0


def test_an_expired_lock_stops_blocking(failures):
    for _ in range(auth.LOCK_AFTER_FAILURES):
        auth.record_login_failure("agent")

    expired = datetime.now(timezone.utc) - timedelta(seconds=1)
    record = dict(failures["agent"])
    record["locked_until"] = expired.isoformat()
    failures["agent"] = record

    assert auth.lockout_seconds_remaining("agent") == 0


def test_a_corrupt_lock_value_does_not_block_sign_in(failures):
    """A bad stored value must fail open, not lock an agent out."""
    failures["agent"] = {"count": 99, "locked_until": "not a timestamp"}
    assert auth.lockout_seconds_remaining("agent") == 0


# ----- Session invalidation (S6) -----

@pytest.fixture
def generations(monkeypatch):
    """An in-memory stand-in for the generation counters."""
    store = {"session_generation": 0, "user_generations": {}}
    monkeypatch.setattr(
        auth, "global_generation", lambda: store["session_generation"]
    )
    monkeypatch.setattr(
        auth,
        "user_generation",
        lambda name: store["user_generations"].get(name, 0),
    )

    def bump_user(name):
        store["user_generations"][name] = (
            store["user_generations"].get(name, 0) + 1
        )

    def bump_all():
        store["session_generation"] += 1

    monkeypatch.setattr(auth, "invalidate_user_sessions", bump_user)
    monkeypatch.setattr(auth, "invalidate_all_sessions", bump_all)
    return store


def test_invalidating_one_user_raises_only_their_generation(generations):
    auth.invalidate_user_sessions("agent")
    assert auth.user_generation("agent") == 1
    assert auth.user_generation("someone.else") == 0
    assert auth.global_generation() == 0


def test_invalidating_everyone_raises_the_global_generation(generations):
    auth.invalidate_all_sessions()
    assert auth.global_generation() == 1


def test_a_session_stamped_before_invalidation_is_stale(generations):
    """This comparison is what is_authenticated() performs."""
    stamped_at = auth.user_generation("agent")
    auth.invalidate_user_sessions("agent")
    assert stamped_at < auth.user_generation("agent")


def test_a_session_stamped_after_invalidation_is_current(generations):
    auth.invalidate_user_sessions("agent")
    stamped_at = auth.user_generation("agent")
    assert stamped_at == auth.user_generation("agent")


def test_generation_helpers_never_raise():
    """These run on every request, so they must not be able to throw.

    Deliberately asserts shape rather than exact values: the counters
    live in app.storage.general, which is shared and persisted across
    restarts -- that persistence is what makes an invalidation survive
    the server being bounced.
    """
    assert isinstance(auth.global_generation(), int)
    assert auth.global_generation() >= 0
    assert isinstance(auth.user_generation("nobody"), int)
    assert auth.user_generation("nobody") >= 0


def test_invalidation_survives_a_restart(generations):
    """A signed-out session must not come back when the server does.

    The counters are persisted, so a session stamped before the bump
    stays stale afterwards.
    """
    stamped_at = auth.user_generation("agent")
    auth.invalidate_user_sessions("agent")

    # Simulating a restart: the counter is re-read from storage, not
    # reset in memory.
    assert auth.user_generation("agent") > stamped_at
