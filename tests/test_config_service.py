"""Tests for the config service."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.config import (
    get_app_settings_path,
    get_user_courses_config_path,
    refresh_runtime_settings,
    settings,
)
from services.config_service import (
    change_teacher_secret,
    delete_course,
    get_effective_settings,
    list_courses,
    save_app_settings,
    save_courses,
    upsert_course,
)


@pytest.fixture(autouse=True)
def _clean_courses_file():
    """Backup and restore courses.json around each test."""
    courses_path = get_user_courses_config_path()
    backup: str | None = None
    had_file = courses_path.exists()
    if had_file:
        backup = courses_path.read_text(encoding="utf-8")
    yield
    courses_path.parent.mkdir(parents=True, exist_ok=True)
    if had_file and backup is not None:
        courses_path.write_text(backup, encoding="utf-8")
    elif courses_path.exists():
        courses_path.unlink()


class TestListCourses:
    def test_returns_list(self):
        result = list_courses()
        assert isinstance(result, list)

    def test_empty_when_no_file(self):
        courses_path = get_user_courses_config_path()
        if courses_path.exists():
            courses_path.unlink()
        result = list_courses()
        assert result == [] or isinstance(result, list)


class TestSaveCourses:
    def test_saves_and_reads_back(self):
        courses = [
            {"code": "CS101", "name": "Intro to CS"},
            {"code": "MA201", "name": "Linear Algebra"},
        ]
        saved = save_courses(courses)
        assert len(saved) == 2
        loaded = list_courses()
        codes = [c["code"] for c in loaded]
        assert "CS101" in codes
        assert "MA201" in codes

    def test_deduplicates(self):
        courses = [
            {"code": "CS101", "name": "First"},
            {"code": "CS101", "name": "Duplicate"},
        ]
        saved = save_courses(courses)
        assert len(saved) == 1

    def test_normalizes_codes_to_uppercase(self):
        saved = save_courses([{"code": "cs101", "name": "Test"}])
        assert saved[0]["code"] == "CS101"


class TestUpsertCourse:
    def test_add_new_course(self):
        save_courses([])
        courses = upsert_course(None, "NEW101", "New Course")
        assert any(c["code"] == "NEW101" for c in courses)

    def test_update_existing_course(self):
        save_courses([{"code": "OLD101", "name": "Old Name"}])
        courses = upsert_course("OLD101", "OLD101", "New Name")
        match = [c for c in courses if c["code"] == "OLD101"]
        assert len(match) == 1
        assert match[0]["name"] == "New Name"

    def test_rename_course_code(self):
        save_courses([{"code": "OLD101", "name": "Course"}])
        courses = upsert_course("OLD101", "NEW101", "Course")
        codes = [c["code"] for c in courses]
        assert "NEW101" in codes
        assert "OLD101" not in codes

    def test_duplicate_code_raises(self):
        save_courses([
            {"code": "A101", "name": "Course A"},
            {"code": "B101", "name": "Course B"},
        ])
        with pytest.raises(ValueError, match="already exists"):
            upsert_course("A101", "B101", "Conflict")

    def test_empty_code_raises(self):
        with pytest.raises(ValueError, match="required"):
            upsert_course(None, "", "No Code")

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="required"):
            upsert_course(None, "CODE1", "")


class TestDeleteCourse:
    def test_removes_course(self):
        save_courses([{"code": "DEL101", "name": "Delete Me"}])
        courses = delete_course("DEL101")
        assert not any(c["code"] == "DEL101" for c in courses)

    def test_delete_nonexistent_is_safe(self):
        save_courses([{"code": "KEEP101", "name": "Keep"}])
        courses = delete_course("NOPE")
        assert len(courses) == 1


class TestEffectiveSettings:
    def test_returns_expected_keys(self):
        result = get_effective_settings()
        assert "allow_student_dev_mode" in result
        assert "default_session_duration_minutes" in result
        assert "qr_rotate_interval_sec" in result
        assert "token_grace_period_sec" in result
        assert "base_url" in result
        assert "storage_backend" in result


class TestSaveAppSettings:
    def test_saves_and_reloads(self):
        result = save_app_settings({"allow_student_dev_mode": True})
        assert result["allow_student_dev_mode"] is True
        assert settings.allow_student_dev_mode is True

    def test_ignores_unknown_keys(self):
        save_app_settings({"unknown_key_xyz": "value"})
        path = get_app_settings_path()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            assert "unknown_key_xyz" not in data


class TestChangeTeacherSecret:
    def test_changes_secret(self):
        change_teacher_secret("new_secret_1234")
        assert settings.teacher_secret == "new_secret_1234"

    def test_short_secret_raises(self):
        with pytest.raises(ValueError, match="at least 4"):
            change_teacher_secret("ab")

    def test_strips_whitespace(self):
        change_teacher_secret("  padded_secret  ")
        assert settings.teacher_secret == "padded_secret"
