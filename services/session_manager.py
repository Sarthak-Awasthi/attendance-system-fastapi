from __future__ import annotations

import asyncio
import logging
import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Any

from core.config import settings

sessions: dict[str, dict[str, Any]] = {}
_session_lock = asyncio.Lock()
_session_sequence: dict[tuple[str, str], int] = {}
logger = logging.getLogger(__name__)


def _random_classroom_code(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def _new_token() -> str:
    return uuid.uuid4().hex


def _is_expired(session: dict[str, Any]) -> bool:
    start_time = session["start_time"]
    expires_at = start_time + timedelta(minutes=session["duration_minutes"])
    return datetime.now().astimezone() >= expires_at


def _next_worksheet_name(course_code: str) -> str:
    date_part = datetime.now().astimezone().date().isoformat()
    key = (course_code, date_part)
    _session_sequence[key] = _session_sequence.get(key, 0) + 1
    return f"{date_part}_S{_session_sequence[key]}"


async def create_session(
    course_code: str,
    duration_minutes: int,
    worksheet_name: str | None = None,
    dev_mode_enabled: bool = False,
) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    token = _new_token()
    session = {
        "session_id": session_id,
        "course_code": course_code,
        "worksheet_name": worksheet_name or _next_worksheet_name(course_code),
        "classroom_code": _random_classroom_code(),
        "start_time": datetime.now().astimezone(),
        "duration_minutes": duration_minutes,
        "dev_mode_enabled": dev_mode_enabled,
        "is_active": True,
        "rotation_task": None,
        "current_token": token,
        "previous_token": None,
        "used_tokens": set(),
        "used_ips": set(),
        "submission_count": 0,
    }
    async with _session_lock:
        sessions[session_id] = session
    task = asyncio.create_task(_rotate_loop(session_id))
    session["rotation_task"] = task
    logger.info(
        "Created session %s course=%s worksheet=%s duration=%s",
        session_id,
        course_code,
        session["worksheet_name"],
        duration_minutes,
    )
    return _serialize_session(session)


async def _rotate_loop(session_id: str) -> None:
    while True:
        await asyncio.sleep(settings.qr_rotate_interval_sec)
        session = sessions.get(session_id)
        if not session or not session.get("is_active", False) or _is_expired(session):
            if session:
                session["is_active"] = False
                logger.info("Stopped token rotation for session %s", session_id)
            break
        old_current = session.get("current_token")
        if old_current:
            session["used_tokens"].add(old_current)
            session["previous_token"] = old_current
        session["current_token"] = _new_token()


def validate_submission(session_id: str, token: str, ip: str, allow_repeat: bool = False) -> str:
    session = sessions.get(session_id)
    if not session:
        return "SESSION_NOT_FOUND"
    if not session.get("is_active", False) or _is_expired(session):
        session["is_active"] = False
        return "SESSION_EXPIRED"
    if token not in {session.get("current_token"), session.get("previous_token")}:
        return "TOKEN_INVALID"
    if not allow_repeat:
        if token in session["used_tokens"]:
            return "TOKEN_INVALID"
        if ip in session["used_ips"]:
            return "IP_ALREADY_USED"
    return "VALID"


def record_submission(session_id: str, ip: str, token: str) -> None:
    session = sessions.get(session_id)
    if not session:
        return
    session["submission_count"] += 1
    session["used_ips"].add(ip)
    session["used_tokens"].add(token)


def get_session(session_id: str) -> dict[str, Any] | None:
    session = sessions.get(session_id)
    if not session:
        return None
    if session.get("is_active", False) and _is_expired(session):
        session["is_active"] = False
        logger.info("Session %s expired", session_id)
    return session


def get_session_payload(session_id: str) -> dict[str, Any] | None:
    session = get_session(session_id)
    if not session:
        return None
    return _serialize_session(session)


def get_time_remaining_seconds(session_id: str) -> int:
    session = get_session(session_id)
    if not session:
        return 0
    expires_at = session["start_time"] + timedelta(minutes=session["duration_minutes"])
    diff = (expires_at - datetime.now().astimezone()).total_seconds()
    return max(0, int(diff))


def end_session(session_id: str) -> bool:
    session = sessions.get(session_id)
    if not session:
        return False
    session["is_active"] = False
    task = session.get("rotation_task")
    if task and not task.done():
        task.cancel()
    logger.info("Session %s marked as ended", session_id)
    return True


def set_session_dev_mode(session_id: str, enabled: bool) -> bool:
    session = sessions.get(session_id)
    if not session:
        return False
    session["dev_mode_enabled"] = bool(enabled)
    return True


def _serialize_session(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session["session_id"],
        "course_code": session["course_code"],
        "worksheet_name": session["worksheet_name"],
        "classroom_code": session["classroom_code"],
        "start_time": session["start_time"].isoformat(),
        "duration_minutes": session["duration_minutes"],
        "dev_mode_enabled": session.get("dev_mode_enabled", False),
        "is_active": session["is_active"],
        "current_token": session["current_token"],
        "submission_count": session["submission_count"],
    }
