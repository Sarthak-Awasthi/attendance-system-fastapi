"""Tests for the session manager service."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from core.config import settings
from services.session_manager import (
    _is_expired,
    _is_token_in_grace_period,
    create_session,
    end_session,
    get_session,
    get_time_remaining_seconds,
    record_submission,
    set_session_dev_mode,
    sessions,
    validate_submission,
)


@pytest.fixture(autouse=True)
def _clear_sessions():
    """Ensure sessions dict is clean between tests."""
    sessions.clear()
    yield
    sessions.clear()


class TestCreateSession:
    async def test_creates_session_with_all_fields(self):
        session = await create_session("CS301", 10)
        assert session["session_id"]
        assert session["course_code"] == "CS301"
        assert session["worksheet_name"]
        assert session["classroom_code"]
        assert session["duration_minutes"] == 10
        assert session["is_active"] is True
        assert session["current_token"]
        assert session["submission_count"] == 0

    async def test_session_stored_in_sessions_dict(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        assert sid in sessions
        assert sessions[sid]["course_code"] == "CS301"

    async def test_dev_mode_flag(self):
        session = await create_session("CS301", 5, dev_mode_enabled=True)
        assert session["dev_mode_enabled"] is True

    async def test_custom_worksheet_name(self):
        session = await create_session("CS301", 5, worksheet_name="custom_sheet")
        assert session["worksheet_name"] == "custom_sheet"


class TestTokenRotation:
    async def test_token_rotates_after_interval(self):
        original_interval = settings.qr_rotate_interval_sec
        settings.qr_rotate_interval_sec = 1
        try:
            session = await create_session("CS301", 5)
            sid = session["session_id"]
            original_token = session["current_token"]
            await asyncio.sleep(1.5)
            live = get_session(sid)
            assert live is not None
            assert live["current_token"] != original_token
        finally:
            settings.qr_rotate_interval_sec = original_interval
            end_session(sid)

    async def test_valid_tokens_sliding_window(self):
        original_interval = settings.qr_rotate_interval_sec
        original_grace = settings.token_grace_period_sec
        settings.qr_rotate_interval_sec = 1
        settings.token_grace_period_sec = 10
        try:
            session = await create_session("CS301", 5)
            sid = session["session_id"]
            first_token = session["current_token"]
            await asyncio.sleep(1.5)
            live = get_session(sid)
            second_token = live["current_token"]
            # First token should still be in grace period
            assert _is_token_in_grace_period(live, first_token)
            assert _is_token_in_grace_period(live, second_token)
        finally:
            settings.qr_rotate_interval_sec = original_interval
            settings.token_grace_period_sec = original_grace
            end_session(sid)


class TestValidateSubmission:
    async def test_valid_submission(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        token = sessions[sid]["current_token"]
        result = validate_submission(sid, token, "192.168.1.10")
        assert result == "VALID"
        end_session(sid)

    def test_session_not_found(self):
        result = validate_submission("nonexistent", "token", "192.168.1.10")
        assert result == "SESSION_NOT_FOUND"

    async def test_expired_session(self):
        session = await create_session("CS301", 1)
        sid = session["session_id"]
        live = sessions[sid]
        # Manually expire the session
        live["start_time"] = datetime.now().astimezone() - timedelta(minutes=2)
        token = live["current_token"]
        result = validate_submission(sid, token, "192.168.1.10")
        assert result == "SESSION_EXPIRED"

    async def test_invalid_token(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        result = validate_submission(sid, "totally_wrong_token", "192.168.1.10")
        assert result == "TOKEN_INVALID"
        end_session(sid)

    async def test_ip_already_used(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        token1 = sessions[sid]["current_token"]
        # First submission with token1
        assert validate_submission(sid, token1, "192.168.1.10") == "VALID"
        record_submission(sid, "192.168.1.10", token1)
        # Generate a fresh token for the session so IP check is reached before token check
        import uuid
        new_token = uuid.uuid4().hex
        now = __import__('datetime').datetime.now().astimezone()
        sessions[sid]["current_token"] = new_token
        sessions[sid]["valid_tokens"].append((new_token, now))
        # Second submission from same IP with new (valid) token
        assert validate_submission(sid, new_token, "192.168.1.10") == "IP_ALREADY_USED"
        end_session(sid)

    async def test_used_token_rejected(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        token = sessions[sid]["current_token"]
        assert validate_submission(sid, token, "192.168.1.10") == "VALID"
        record_submission(sid, "192.168.1.10", token)
        # Same token from different IP
        assert validate_submission(sid, token, "192.168.1.20") == "TOKEN_INVALID"
        end_session(sid)

    async def test_dev_mode_allows_repeat(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        token = sessions[sid]["current_token"]
        assert validate_submission(sid, token, "192.168.1.10", allow_repeat=True) == "VALID"
        record_submission(sid, "192.168.1.10", token)
        assert validate_submission(sid, token, "192.168.1.10", allow_repeat=True) == "VALID"
        end_session(sid)


class TestRecordSubmission:
    async def test_increments_count(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        record_submission(sid, "192.168.1.10", "tok1")
        record_submission(sid, "192.168.1.11", "tok2")
        assert sessions[sid]["submission_count"] == 2
        end_session(sid)

    async def test_tracks_ips_and_tokens(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        record_submission(sid, "10.0.0.1", "token_a")
        assert "10.0.0.1" in sessions[sid]["used_ips"]
        assert "token_a" in sessions[sid]["used_tokens"]
        end_session(sid)

    def test_nonexistent_session_no_error(self):
        record_submission("does_not_exist", "ip", "tok")


class TestEndSession:
    async def test_marks_inactive(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        assert end_session(sid) is True
        assert sessions[sid]["is_active"] is False

    def test_nonexistent_session(self):
        assert end_session("does_not_exist") is False

    async def test_cancels_rotation_task(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        task = sessions[sid]["rotation_task"]
        end_session(sid)
        await asyncio.sleep(0.1)
        assert task.done() or task.cancelled()


class TestGetSession:
    async def test_returns_session(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        live = get_session(sid)
        assert live is not None
        assert live["session_id"] == sid
        end_session(sid)

    def test_returns_none_for_missing(self):
        assert get_session("does_not_exist") is None

    async def test_marks_expired_on_access(self):
        session = await create_session("CS301", 1)
        sid = session["session_id"]
        sessions[sid]["start_time"] = datetime.now().astimezone() - timedelta(minutes=2)
        live = get_session(sid)
        assert live is not None
        assert live["is_active"] is False


class TestTimeRemaining:
    async def test_positive_remaining(self):
        session = await create_session("CS301", 10)
        sid = session["session_id"]
        remaining = get_time_remaining_seconds(sid)
        assert remaining > 0
        assert remaining <= 600
        end_session(sid)

    def test_zero_for_missing(self):
        assert get_time_remaining_seconds("does_not_exist") == 0

    async def test_zero_for_expired(self):
        session = await create_session("CS301", 1)
        sid = session["session_id"]
        sessions[sid]["start_time"] = datetime.now().astimezone() - timedelta(minutes=2)
        assert get_time_remaining_seconds(sid) == 0


class TestDevMode:
    async def test_toggle_dev_mode(self):
        session = await create_session("CS301", 5)
        sid = session["session_id"]
        assert set_session_dev_mode(sid, True) is True
        assert sessions[sid]["dev_mode_enabled"] is True
        assert set_session_dev_mode(sid, False) is True
        assert sessions[sid]["dev_mode_enabled"] is False
        end_session(sid)

    def test_nonexistent_session(self):
        assert set_session_dev_mode("does_not_exist", True) is False
