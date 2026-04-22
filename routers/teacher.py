from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from core.config import get_public_dir, get_runtime_base_url, settings
from core.security import is_teacher_secret_configured, is_teacher_secret_valid
from models import (
    BootstrapTeacherSecretRequest,
    DeleteCourseRequest,
    EndSessionRequest,
    StartSessionRequest,
    UpdateSessionDevModeRequest,
    UpdateTeacherSecretRequest,
    UpdateTeacherSettingsRequest,
    UpsertCourseRequest,
)
from services.config_service import (
    change_teacher_secret,
    delete_course,
    get_effective_settings,
    list_courses,
    save_app_settings,
    upsert_course,
)
from services.qr_generator import generate_qr_base64
from services.session_manager import (
    create_session,
    end_session,
    get_session,
    get_time_remaining_seconds,
    set_session_dev_mode,
)
from services.storage_factory import get_storage

router = APIRouter()
logger = logging.getLogger(__name__)


def _is_known_course(course_code: str) -> bool:
    return any(course.get("code", "").upper() == course_code for course in list_courses())


@router.get("/teacher")
async def teacher_home() -> FileResponse:
    file_path = get_public_dir() / "teacher" / "index.html"
    return FileResponse(file_path)


@router.get("/teacher/dashboard")
async def teacher_dashboard() -> FileResponse:
    file_path = get_public_dir() / "teacher" / "dashboard.html"
    return FileResponse(file_path)


@router.get("/teacher/config")
async def teacher_config_page() -> FileResponse:
    file_path = get_public_dir() / "teacher" / "config.html"
    return FileResponse(file_path)


@router.get("/api/teacher/courses")
async def get_courses() -> dict:
    return {
        "courses": list_courses(),
        "defaults": {
            "durationMinutes": get_effective_settings()["default_session_duration_minutes"],
        },
    }


@router.get("/api/teacher/bootstrap/status")
async def get_bootstrap_status() -> dict:
    return {"requiresBootstrap": not is_teacher_secret_configured()}


@router.post("/api/teacher/bootstrap")
async def bootstrap_teacher_secret(payload: BootstrapTeacherSecretRequest) -> dict:
    if is_teacher_secret_configured():
        raise HTTPException(status_code=409, detail="Teacher secret is already configured")
    if payload.newSecret != payload.confirmNewSecret:
        raise HTTPException(status_code=400, detail="New secret and confirmation do not match")

    try:
        change_teacher_secret(payload.newSecret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Bootstrap teacher secret configured")
    return {"ok": True}


@router.get("/api/teacher/config")
async def get_teacher_config() -> dict:
    return {
        "courses": list_courses(),
        "settings": get_effective_settings(),
    }


@router.post("/api/teacher/config/courses")
async def upsert_teacher_course(payload: UpsertCourseRequest) -> dict:
    if not is_teacher_secret_valid(payload.secret):
        logger.warning("Rejected course upsert due to invalid teacher secret")
        raise HTTPException(status_code=401, detail="Invalid teacher secret")

    try:
        courses = upsert_course(payload.originalCode, payload.code, payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "courses": courses}


@router.delete("/api/teacher/config/courses/{course_code}")
async def remove_teacher_course(course_code: str, payload: DeleteCourseRequest) -> dict:
    if not is_teacher_secret_valid(payload.secret):
        logger.warning("Rejected course delete due to invalid teacher secret")
        raise HTTPException(status_code=401, detail="Invalid teacher secret")

    courses = delete_course(course_code)
    return {"ok": True, "courses": courses}


@router.put("/api/teacher/config/settings")
async def update_teacher_settings(payload: UpdateTeacherSettingsRequest) -> dict:
    if not is_teacher_secret_valid(payload.secret):
        logger.warning("Rejected settings update due to invalid teacher secret")
        raise HTTPException(status_code=401, detail="Invalid teacher secret")

    settings_data = save_app_settings(
        {
            "allow_student_dev_mode": payload.allowStudentDevMode,
            "excel_data_dir": payload.excelDataDir,
            "default_session_duration_minutes": payload.defaultSessionDurationMinutes,
            "qr_rotate_interval_sec": payload.qrRotateIntervalSec,
            "token_grace_period_sec": payload.tokenGracePeriodSec,
            "base_url": payload.baseUrl,
            "storage_backend": payload.storageBackend,
            "google_credentials_path": payload.googleCredentialsPath,
            "google_spreadsheet_key": payload.googleSpreadsheetKey,
        }
    )
    logger.info("Updated teacher app settings")
    return {"ok": True, "settings": settings_data}


@router.put("/api/teacher/config/secret")
async def update_teacher_secret(payload: UpdateTeacherSecretRequest) -> dict:
    if not is_teacher_secret_valid(payload.oldSecret):
        logger.warning("Rejected teacher secret update due to invalid current secret")
        raise HTTPException(status_code=401, detail="Invalid current teacher secret")
    if payload.newSecret != payload.confirmNewSecret:
        raise HTTPException(status_code=400, detail="New secret and confirmation do not match")

    try:
        change_teacher_secret(payload.newSecret)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("Teacher secret updated")
    return {"ok": True}


@router.post("/api/teacher/session/start")
async def start_session(payload: StartSessionRequest) -> dict:
    if not is_teacher_secret_valid(payload.secret):
        logger.warning("Rejected session start due to invalid teacher secret")
        raise HTTPException(status_code=401, detail="Invalid teacher secret")

    course_code = payload.courseCode.upper()
    if not _is_known_course(course_code):
        logger.warning("Rejected session start for unknown course %s", course_code)
        raise HTTPException(status_code=400, detail="Unknown course code")

    storage = get_storage()
    worksheet_name = await storage.get_next_worksheet_name(course_code)
    session = await create_session(
        course_code,
        payload.durationMinutes,
        worksheet_name=worksheet_name,
        dev_mode_enabled=bool(payload.devMode and settings.allow_student_dev_mode),
    )
    await storage.initialize_worksheet(session["course_code"], session["worksheet_name"])
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
        "globalDevModeEnabled": settings.allow_student_dev_mode,
        "devModeEnabled": bool(session.get("dev_mode_enabled", False) and settings.allow_student_dev_mode),
        "isActive": session["is_active"],
        "qrRotateIntervalSec": settings.qr_rotate_interval_sec,
        "tokenGracePeriodSec": settings.token_grace_period_sec,
    }


@router.put("/api/teacher/session/{session_id}/dev-mode")
async def toggle_session_dev_mode(session_id: str, payload: UpdateSessionDevModeRequest) -> dict:
    if not is_teacher_secret_valid(payload.secret):
        logger.warning("Rejected dev mode toggle for %s due to invalid secret", session_id)
        raise HTTPException(status_code=401, detail="Invalid teacher secret")
    if not settings.allow_student_dev_mode:
        raise HTTPException(status_code=400, detail="Enable global student dev mode in teacher configuration first")
    if not set_session_dev_mode(session_id, payload.enabled):
        raise HTTPException(status_code=404, detail="Session not found")
    logger.info("Set session %s dev mode to %s", session_id, payload.enabled)
    return {"ok": True, "devModeEnabled": payload.enabled}


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
