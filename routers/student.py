from __future__ import annotations

import logging
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from core.config import get_public_dir
from models import SubmitAttendanceRequest
from services.excel_service import append_attendance_row
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
    validation = validate_submission(payload.sessionId, payload.token, ip)

    if validation == "SESSION_NOT_FOUND":
        logger.warning("Rejected submission: session %s not found", payload.sessionId)
        raise HTTPException(status_code=404, detail=validation)
    if validation == "SESSION_EXPIRED":
        logger.warning("Rejected submission: session %s expired", payload.sessionId)
        raise HTTPException(status_code=410, detail=validation)
    if validation in {"TOKEN_INVALID", "IP_ALREADY_USED"}:
        logger.warning("Rejected submission for session %s: %s", payload.sessionId, validation)
        raise HTTPException(status_code=409, detail=validation)

    session = get_session(payload.sessionId)
    if not session:
        raise HTTPException(status_code=404, detail="SESSION_NOT_FOUND")

    now = datetime.now().astimezone().isoformat()
    row_data = [
        payload.rollNumber.upper(),
        now,
        payload.sessionId,
        ip,
        1,
        session["classroom_code"],
    ]

    try:
        await append_attendance_row(session["course_code"], session["worksheet_name"], row_data)
    except Exception:
        logger.exception("Excel write failed for session %s", payload.sessionId)
        raise HTTPException(status_code=500, detail="ATTENDANCE_WRITE_FAILED")

    record_submission(payload.sessionId, ip, payload.token)
    logger.info("Recorded attendance for roll %s in session %s", payload.rollNumber.upper(), payload.sessionId)

    return {"ok": True, "message": "Attendance marked"}

