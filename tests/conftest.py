"""Shared fixtures for the attendance system test suite."""
from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import Any, Generator

import pytest
from fastapi.testclient import TestClient

from core.config import (
    get_app_settings_path,
    get_user_config_dir,
    refresh_runtime_settings,
    settings,
)
from main import app


TEST_SECRET = "test_secret_1234"
TEST_COURSE_CODE = "TEST101"
TEST_COURSE_NAME = "Test Course"


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_settings() -> Generator[None, None, None]:
    """Backup and restore app_settings.json and teacher secret around each test."""
    app_settings_path = get_app_settings_path()
    backup_text: str | None = None
    had_file = app_settings_path.exists()
    original_secret = settings.teacher_secret
    original_dev_mode = settings.allow_student_dev_mode

    if had_file:
        backup_text = app_settings_path.read_text(encoding="utf-8")

    yield

    # Restore
    app_settings_path.parent.mkdir(parents=True, exist_ok=True)
    if had_file and backup_text is not None:
        app_settings_path.write_text(backup_text, encoding="utf-8")
    elif app_settings_path.exists():
        app_settings_path.unlink()
    settings.teacher_secret = original_secret
    settings.allow_student_dev_mode = original_dev_mode


@pytest.fixture()
def set_secret() -> Generator[None, None, None]:
    """Set a known teacher secret for tests that need authentication."""
    original = settings.teacher_secret
    settings.teacher_secret = TEST_SECRET
    yield
    settings.teacher_secret = original


@pytest.fixture()
def setup_test_course(set_secret: None) -> Generator[dict[str, str], None, None]:
    """Set up a test course and clean it up after."""
    from services.config_service import upsert_course, delete_course

    courses = upsert_course(None, TEST_COURSE_CODE, TEST_COURSE_NAME)
    yield {"code": TEST_COURSE_CODE, "name": TEST_COURSE_NAME}
    try:
        delete_course(TEST_COURSE_CODE)
    except Exception:
        pass


@pytest.fixture()
def clean_excel_data() -> Generator[Path, None, None]:
    """Provide a clean temporary excel data directory for tests."""
    test_data_dir = settings.excel_data_dir / "_test_data"
    test_data_dir.mkdir(parents=True, exist_ok=True)

    original_dir = settings.excel_data_dir
    settings.excel_data_dir = test_data_dir
    yield test_data_dir

    settings.excel_data_dir = original_dir
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir, ignore_errors=True)


@pytest.fixture()
def session_factory(set_secret: None, setup_test_course: dict[str, str]):
    """Factory fixture that creates sessions with sensible defaults."""

    async def _create(
        course_code: str | None = None,
        duration_minutes: int = 5,
        dev_mode_enabled: bool = False,
    ) -> dict[str, Any]:
        from services.session_manager import create_session
        from services.excel_service import initialize_worksheet

        code = course_code or TEST_COURSE_CODE
        session = await create_session(code, duration_minutes, dev_mode_enabled=dev_mode_enabled)
        await initialize_worksheet(session["course_code"], session["worksheet_name"])
        return session

    return _create
