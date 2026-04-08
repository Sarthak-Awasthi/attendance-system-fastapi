from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from core.config import get_public_dir, get_runtime_base_url, load_courses
from core.security import is_teacher_secret_valid
from models import EndSessionRequest, StartSessionRequest
from services.excel_service import get_next_worksheet_name, initialize_worksheet
from services.qr_generator import generate_qr_base64
from services.session_manager import (
    create_session,
    end_session,
    get_session,
    get_time_remaining_seconds,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _is_known_course(course_code: str) -> bool:
    return any(course.get("code", "").upper() == course_code for course in load_courses())


@router.get("/teacher")
async def teacher_home() -> FileResponse:
    file_path = get_public_dir() / "teacher" / "index.html"
    return FileResponse(file_path)


@router.get("/teacher/dashboard")
async def teacher_dashboard() -> FileResponse:
    file_path = get_public_dir() / "teacher" / "dashboard.html"
    return FileResponse(file_path)


@router.get("/api/teacher/courses")
async def get_courses() -> dict:
    return {"courses": load_courses()}


@router.post("/api/teacher/session/start")
async def start_session(payload: StartSessionRequest) -> dict:
    if not is_teacher_secret_valid(payload.secret):
        logger.warning("Rejected session start due to invalid teacher secret")
        raise HTTPException(status_code=401, detail="Invalid teacher secret")

    course_code = payload.courseCode.upper()
    if not _is_known_course(course_code):
        logger.warning("Rejected session start for unknown course %s", course_code)
        raise HTTPException(status_code=400, detail="Unknown course code")

    worksheet_name = await get_next_worksheet_name(course_code)
    session = await create_session(
        course_code,
        payload.durationMinutes,
        worksheet_name=worksheet_name,
    )
    await initialize_worksheet(session["course_code"], session["worksheet_name"])
    logger.info("Started session %s for %s", session["session_id"], course_code)

    return {
        "sessionId": session["session_id"],
        "courseCode": session["course_code"],
        "worksheetName": session["worksheet_name"],
        "classroomCode": session["classroom_code"],
        "durationMinutes": session["duration_minutes"],
    }


@router.get("/api/teacher/session/{session_id}/qr")
async def get_live_qr(session_id: str, secret: str = Query(default="")) -> dict:
    if not is_teacher_secret_valid(secret):
        logger.warning("Rejected QR poll for session %s due to invalid secret", session_id)
        raise HTTPException(status_code=401, detail="Invalid teacher secret")

    session = get_session(session_id)
    if not session:
        logger.warning("QR poll requested for missing session %s", session_id)
        raise HTTPException(status_code=404, detail="Session not found")

    token = session.get("current_token", "")
    url = f"{get_runtime_base_url()}/attend?token={token}&session={session_id}"

    return {
        "qrBase64": generate_qr_base64(url),
        "attendUrl": url,
        "timeRemainingSeconds": get_time_remaining_seconds(session_id),
        "submissionCount": session["submission_count"],
        "classroomCode": session["classroom_code"],
        "isActive": session["is_active"],
    }


@router.post("/api/teacher/session/{session_id}/end")
async def stop_session(session_id: str, payload: EndSessionRequest) -> dict:
    if not is_teacher_secret_valid(payload.secret):
        logger.warning("Rejected session end for %s due to invalid secret", session_id)
        raise HTTPException(status_code=401, detail="Invalid teacher secret")

    if not end_session(session_id):
        logger.warning("Requested end for missing session %s", session_id)
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info("Ended session %s", session_id)

    return {"ok": True}
