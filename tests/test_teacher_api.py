"""Tests for teacher API endpoints."""
from __future__ import annotations

import pytest

from core.config import get_app_settings_path, settings
from services.config_service import save_courses
from services.session_manager import sessions
from tests.conftest import TEST_COURSE_CODE, TEST_COURSE_NAME, TEST_SECRET


@pytest.fixture(autouse=True)
def _clear_sessions():
    sessions.clear()
    yield
    sessions.clear()


class TestBootstrapFlow:
    def test_status_requires_bootstrap_when_no_secret(self, client):
        settings.teacher_secret = ""
        resp = client.get("/api/teacher/bootstrap/status")
        assert resp.status_code == 200
        assert resp.json()["requiresBootstrap"] is True

    def test_status_no_bootstrap_when_configured(self, client, set_secret):
        resp = client.get("/api/teacher/bootstrap/status")
        assert resp.status_code == 200
        assert resp.json()["requiresBootstrap"] is False

    def test_bootstrap_creates_secret(self, client):
        settings.teacher_secret = ""
        app_settings = get_app_settings_path()
        if app_settings.exists():
            app_settings.unlink()

        resp = client.post("/api/teacher/bootstrap", json={
            "newSecret": "bootstrap_test_secret",
            "confirmNewSecret": "bootstrap_test_secret",
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_bootstrap_rejects_mismatch(self, client):
        settings.teacher_secret = ""
        resp = client.post("/api/teacher/bootstrap", json={
            "newSecret": "secret_a",
            "confirmNewSecret": "secret_b",
        })
        assert resp.status_code == 400

    def test_bootstrap_rejects_when_already_configured(self, client, set_secret):
        resp = client.post("/api/teacher/bootstrap", json={
            "newSecret": "another_secret",
            "confirmNewSecret": "another_secret",
        })
        assert resp.status_code == 409


class TestSessionLifecycle:
    def test_start_session(self, client, set_secret, setup_test_course):
        resp = client.post("/api/teacher/session/start", json={
            "courseCode": TEST_COURSE_CODE,
            "durationMinutes": 5,
            "secret": TEST_SECRET,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "sessionId" in data
        assert data["courseCode"] == TEST_COURSE_CODE

    def test_start_session_invalid_secret(self, client, set_secret, setup_test_course):
        resp = client.post("/api/teacher/session/start", json={
            "courseCode": TEST_COURSE_CODE,
            "durationMinutes": 5,
            "secret": "wrong_secret",
        })
        assert resp.status_code == 401

    def test_start_session_unknown_course(self, client, set_secret):
        resp = client.post("/api/teacher/session/start", json={
            "courseCode": "NOSUCHCOURSE",
            "durationMinutes": 5,
            "secret": TEST_SECRET,
        })
        assert resp.status_code == 400

    def test_end_session(self, client, set_secret, setup_test_course):
        start = client.post("/api/teacher/session/start", json={
            "courseCode": TEST_COURSE_CODE,
            "durationMinutes": 5,
            "secret": TEST_SECRET,
        })
        session_id = start.json()["sessionId"]
        resp = client.post(f"/api/teacher/session/{session_id}/end", json={
            "secret": TEST_SECRET,
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_end_nonexistent_session(self, client, set_secret):
        resp = client.post("/api/teacher/session/nonexistent/end", json={
            "secret": TEST_SECRET,
        })
        assert resp.status_code == 404


class TestQREndpoint:
    def test_get_qr(self, client, set_secret, setup_test_course):
        start = client.post("/api/teacher/session/start", json={
            "courseCode": TEST_COURSE_CODE,
            "durationMinutes": 5,
            "secret": TEST_SECRET,
        })
        session_id = start.json()["sessionId"]
        resp = client.get(f"/api/teacher/session/{session_id}/qr?secret={TEST_SECRET}")
        assert resp.status_code == 200
        data = resp.json()
        assert "qrBase64" in data
        assert data["qrBase64"].startswith("data:image/png;base64,")
        assert "timeRemainingSeconds" in data
        assert "submissionCount" in data
        assert "qrRotateIntervalSec" in data
        assert "tokenGracePeriodSec" in data

    def test_get_qr_invalid_secret(self, client, set_secret, setup_test_course):
        start = client.post("/api/teacher/session/start", json={
            "courseCode": TEST_COURSE_CODE,
            "durationMinutes": 5,
            "secret": TEST_SECRET,
        })
        session_id = start.json()["sessionId"]
        resp = client.get(f"/api/teacher/session/{session_id}/qr?secret=wrong")
        assert resp.status_code == 401

    def test_get_qr_nonexistent_session(self, client, set_secret):
        resp = client.get(f"/api/teacher/session/nonexistent/qr?secret={TEST_SECRET}")
        assert resp.status_code == 404


class TestCourseCRUD:
    def test_add_course(self, client, set_secret):
        # Use a unique code to avoid collision with existing courses
        resp = client.post("/api/teacher/config/courses", json={
            "code": "ZCRUD01",
            "name": "CRUD Test Course",
            "secret": TEST_SECRET,
        })
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Cleanup
        client.request("DELETE", "/api/teacher/config/courses/ZCRUD01",
            json={"secret": TEST_SECRET},
        )

    def test_delete_course(self, client, set_secret, setup_test_course):
        resp = client.request("DELETE", f"/api/teacher/config/courses/{TEST_COURSE_CODE}",
            json={"secret": TEST_SECRET},
        )
        assert resp.status_code == 200

    def test_add_course_invalid_secret(self, client, set_secret):
        resp = client.post("/api/teacher/config/courses", json={
            "code": "X101",
            "name": "Test",
            "secret": "wrong",
        })
        assert resp.status_code == 401


class TestSettingsUpdate:
    def test_update_settings(self, client, set_secret):
        resp = client.put("/api/teacher/config/settings", json={
            "secret": TEST_SECRET,
            "allowStudentDevMode": True,
            "excelDataDir": "./data",
            "defaultSessionDurationMinutes": 15,
            "qrRotateIntervalSec": 10,
            "tokenGracePeriodSec": 45,
            "baseUrl": "http://localhost:3000",
            "storageBackend": "excel",
            "googleCredentialsPath": "",
            "googleSpreadsheetKey": "",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["settings"]["default_session_duration_minutes"] == 15

    def test_update_settings_invalid_secret(self, client, set_secret):
        resp = client.put("/api/teacher/config/settings", json={
            "secret": "wrong",
            "allowStudentDevMode": False,
            "excelDataDir": "./data",
            "defaultSessionDurationMinutes": 10,
            "qrRotateIntervalSec": 5,
            "tokenGracePeriodSec": 30,
            "baseUrl": "http://localhost:3000",
            "storageBackend": "excel",
            "googleCredentialsPath": "",
            "googleSpreadsheetKey": "",
        })
        assert resp.status_code == 401


class TestSecretChange:
    def test_change_secret(self, client, set_secret):
        resp = client.put("/api/teacher/config/secret", json={
            "oldSecret": TEST_SECRET,
            "newSecret": "new_secret_5678",
            "confirmNewSecret": "new_secret_5678",
        })
        assert resp.status_code == 200

    def test_change_secret_wrong_old(self, client, set_secret):
        resp = client.put("/api/teacher/config/secret", json={
            "oldSecret": "wrong_old",
            "newSecret": "new_secret",
            "confirmNewSecret": "new_secret",
        })
        assert resp.status_code == 401

    def test_change_secret_mismatch(self, client, set_secret):
        resp = client.put("/api/teacher/config/secret", json={
            "oldSecret": TEST_SECRET,
            "newSecret": "new_a",
            "confirmNewSecret": "new_b",
        })
        assert resp.status_code == 400


class TestDevModeToggle:
    def test_toggle_session_dev_mode(self, client, set_secret, setup_test_course):
        settings.allow_student_dev_mode = True
        start = client.post("/api/teacher/session/start", json={
            "courseCode": TEST_COURSE_CODE,
            "durationMinutes": 5,
            "secret": TEST_SECRET,
        })
        session_id = start.json()["sessionId"]
        resp = client.put(f"/api/teacher/session/{session_id}/dev-mode", json={
            "secret": TEST_SECRET,
            "enabled": True,
        })
        assert resp.status_code == 200
        assert resp.json()["devModeEnabled"] is True

    def test_toggle_fails_when_global_off(self, client, set_secret, setup_test_course):
        settings.allow_student_dev_mode = False
        start = client.post("/api/teacher/session/start", json={
            "courseCode": TEST_COURSE_CODE,
            "durationMinutes": 5,
            "secret": TEST_SECRET,
        })
        session_id = start.json()["sessionId"]
        resp = client.put(f"/api/teacher/session/{session_id}/dev-mode", json={
            "secret": TEST_SECRET,
            "enabled": True,
        })
        assert resp.status_code == 400
