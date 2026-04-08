from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from core.config import (
    get_app_settings_path,
    get_courses_config_path,
    get_user_config_dir,
    get_user_courses_config_path,
    refresh_runtime_settings,
    settings,
)

ALLOWED_SETTING_KEYS = {
    "teacher_secret",
    "excel_data_dir",
    "default_session_duration_minutes",
    "qr_rotate_interval_sec",
    "base_url",
}


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as temp_file:
        json.dump(payload, temp_file, indent=2)
        temp_file.write("\n")
        temp_path = Path(temp_file.name)
    temp_path.replace(path)


def _normalize_course(course: dict[str, Any]) -> dict[str, str]:
    return {
        "code": str(course.get("code", "")).strip().upper(),
        "name": str(course.get("name", "")).strip(),
    }


def list_courses() -> list[dict[str, str]]:
    source_path = get_courses_config_path()
    if not source_path.exists():
        return []
    with source_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        return []

    courses: list[dict[str, str]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_course(item)
        if normalized["code"]:
            courses.append(normalized)

    courses.sort(key=lambda c: c["code"])
    return courses


def save_courses(courses: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in courses:
        if not isinstance(item, dict):
            continue
        course = _normalize_course(item)
        if not course["code"] or course["code"] in seen:
            continue
        seen.add(course["code"])
        normalized.append(course)

    normalized.sort(key=lambda c: c["code"])
    target_path = get_user_courses_config_path()
    _atomic_write_json(target_path, normalized)
    return normalized


def upsert_course(original_code: str | None, code: str, name: str) -> list[dict[str, str]]:
    target_code = code.strip().upper()
    target_name = name.strip()
    if not target_code:
        raise ValueError("Course code is required")
    if not target_name:
        raise ValueError("Course name is required")

    old_code = (original_code or "").strip().upper()
    courses = list_courses()

    if old_code:
        courses = [c for c in courses if c["code"] != old_code]

    conflict = any(c["code"] == target_code for c in courses)
    if conflict and target_code != old_code:
        raise ValueError("Course code already exists")

    courses.append({"code": target_code, "name": target_name})
    return save_courses(courses)


def delete_course(code: str) -> list[dict[str, str]]:
    target_code = code.strip().upper()
    courses = [c for c in list_courses() if c["code"] != target_code]
    return save_courses(courses)


def get_effective_settings() -> dict[str, Any]:
    return {
        "excel_data_dir": str(settings.excel_data_dir),
        "default_session_duration_minutes": settings.default_session_duration_minutes,
        "qr_rotate_interval_sec": settings.qr_rotate_interval_sec,
        "base_url": settings.base_url,
    }


def save_app_settings(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in ALLOWED_SETTING_KEYS:
            continue
        sanitized[key] = value

    app_settings_path = get_app_settings_path()
    current: dict[str, Any] = {}
    if app_settings_path.exists():
        with app_settings_path.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
            if isinstance(loaded, dict):
                current = loaded

    current.update(sanitized)
    get_user_config_dir().mkdir(parents=True, exist_ok=True)
    _atomic_write_json(app_settings_path, current)
    refresh_runtime_settings()
    settings.excel_data_dir.mkdir(parents=True, exist_ok=True)
    return get_effective_settings()


def change_teacher_secret(new_secret: str) -> None:
    normalized = (new_secret or "").strip()
    if len(normalized) < 4:
        raise ValueError("New teacher secret must be at least 4 characters")
    save_app_settings({"teacher_secret": normalized})


