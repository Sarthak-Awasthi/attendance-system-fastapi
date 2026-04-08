from __future__ import annotations

import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from core.config import get_public_dir, settings
from models import SubmitAttendanceRequest
from services.excel_service import mark_attendance
from services.session_manager import get_session, record_submission, validate_submission

router = APIRouter()
logger = logging.getLogger(__name__)
ROLL_PATTERN = re.compile(r"^[A-Z0-9]{4,15}$", re.IGNORECASE)


@router.get("/attend")
async def attend_page() -> FileResponse:
    file_path = get_public_dir() / "student" / "scan.html"
    return FileResponse(file_path)


@router.post("/api/student/submit")
async def submit_attendance(payload: SubmitAttendanceRequest, request: Request) -> dict:
    if not ROLL_PATTERN.match(payload.rollNumber):
        logger.warning("Rejected submission with invalid roll format")
        raise HTTPException(status_code=400, detail="Invalid roll number format")

    ip = request.client.host if request.client else "unknown"
    session = get_session(payload.sessionId)
    if not session:
        logger.warning("Rejected submission: session %s not found", payload.sessionId)
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")

    effective_dev_mode = bool(
        settings.allow_student_dev_mode
        and session.get("dev_mode_enabled", False)
    )
    validation = validate_submission(payload.sessionId, payload.token, ip, allow_repeat=effective_dev_mode)

    if validation == "SESSION_NOT_FOUND":
        logger.warning("Rejected submission: session %s not found", payload.sessionId)
        raise HTTPException(status_code=404, detail=validation)
    if validation == "SESSION_EXPIRED":
        logger.warning("Rejected submission: session %s expired", payload.sessionId)
        raise HTTPException(status_code=410, detail=validation)
    if validation in {"TOKEN_INVALID", "IP_ALREADY_USED"}:
        logger.warning("Rejected submission for session %s: %s", payload.sessionId, validation)
        raise HTTPException(status_code=409, detail=validation)

    now = datetime.now().astimezone()
    try:
        await mark_attendance(
            session["course_code"],
            session["worksheet_name"],
            payload.rollNumber.upper(),
            attendance_date=now.date().isoformat(),
            present=1,
        )
    except Exception:
        logger.exception("Excel write failed for session %s", payload.sessionId)
        raise HTTPException(status_code=500, detail="ATTENDANCE_WRITE_FAILED")

    record_submission(payload.sessionId, ip, payload.token)
    logger.info("Recorded attendance for roll %s in session %s", payload.rollNumber.upper(), payload.sessionId)

    return {"ok": True, "message": "Attendance marked"}

