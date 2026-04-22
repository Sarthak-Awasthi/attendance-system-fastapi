"""Tests for student API endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core.config import settings
from services.session_manager import create_session, sessions, end_session
from services.excel_service import initialize_worksheet
from tests.conftest import TEST_COURSE_CODE, TEST_SECRET


@pytest.fixture(autouse=True)
def _clear_sessions():
    sessions.clear()
    yield
    sessions.clear()


@pytest.fixture()
def active_session(set_secret, setup_test_course):
    """Create an active session and return its details."""
    import asyncio

    async def _create():
        session = await create_session(TEST_COURSE_CODE, 10)
        await initialize_worksheet(session["course_code"], session["worksheet_name"])
        return session

    session = asyncio.get_event_loop().run_until_complete(_create())
    sid = session["session_id"]
    live = sessions[sid]
    return {"session_id": sid, "token": live["current_token"]}


class TestSubmitAttendance:
    def test_success(self, client, active_session):
        resp = client.post("/api/student/submit", json={
            "rollNumber": "21CS1001",
            "token": active_session["token"],
            "sessionId": active_session["session_id"],
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_invalid_roll_number_format(self, client, active_session):
        resp = client.post("/api/student/submit", json={
            "rollNumber": "ab",  # too short
            "token": active_session["token"],
            "sessionId": active_session["session_id"],
        })
        assert resp.status_code in (400, 422)  # pydantic or manual validation

    def test_session_not_found(self, client, set_secret):
        resp = client.post("/api/student/submit", json={
            "rollNumber": "21CS1001",
            "token": "some_token",
            "sessionId": "nonexistent_session",
        })
        assert resp.status_code == 404

    def test_expired_session(self, client, active_session):
        sid = active_session["session_id"]
        sessions[sid]["start_time"] = datetime.now().astimezone() - timedelta(minutes=20)
        resp = client.post("/api/student/submit", json={
            "rollNumber": "21CS1001",
            "token": active_session["token"],
            "sessionId": sid,
        })
        assert resp.status_code == 410

    def test_invalid_token(self, client, active_session):
        resp = client.post("/api/student/submit", json={
            "rollNumber": "21CS1001",
            "token": "completely_wrong_token",
            "sessionId": active_session["session_id"],
        })
        assert resp.status_code == 409

    def test_ip_already_used(self, client, active_session):
        payload = {
            "rollNumber": "21CS1001",
            "token": active_session["token"],
            "sessionId": active_session["session_id"],
        }
        first = client.post("/api/student/submit", json=payload)
        assert first.status_code == 200
        # Second submit from same IP
        payload["rollNumber"] = "21CS1002"
        second = client.post("/api/student/submit", json=payload)
        assert second.status_code == 409


class TestDevModeRepeatSubmission:
    def test_repeat_allowed_when_dev_mode_on(self, client, set_secret, setup_test_course):
        import asyncio

        settings.allow_student_dev_mode = True

        async def _create():
            session = await create_session(TEST_COURSE_CODE, 10, dev_mode_enabled=True)
            await initialize_worksheet(session["course_code"], session["worksheet_name"])
            return session

        session = asyncio.get_event_loop().run_until_complete(_create())
        sid = session["session_id"]
        token = sessions[sid]["current_token"]

        payload = {
            "rollNumber": "21CS1001",
            "token": token,
            "sessionId": sid,
        }
        first = client.post("/api/student/submit", json=payload)
        assert first.status_code == 200
        second = client.post("/api/student/submit", json=payload)
        assert second.status_code == 200

    def test_repeat_blocked_when_global_off(self, client, set_secret, setup_test_course):
        import asyncio

        settings.allow_student_dev_mode = False

        async def _create():
            session = await create_session(TEST_COURSE_CODE, 10, dev_mode_enabled=True)
            await initialize_worksheet(session["course_code"], session["worksheet_name"])
            return session

        session = asyncio.get_event_loop().run_until_complete(_create())
        sid = session["session_id"]
        token = sessions[sid]["current_token"]

        payload = {
            "rollNumber": "21CS1001",
            "token": token,
            "sessionId": sid,
        }
        first = client.post("/api/student/submit", json=payload)
        assert first.status_code == 200
        second = client.post("/api/student/submit", json=payload)
        assert second.status_code == 409


class TestAttendPage:
    def test_attend_page_serves(self, client):
        resp = client.get("/attend")
        assert resp.status_code == 200
