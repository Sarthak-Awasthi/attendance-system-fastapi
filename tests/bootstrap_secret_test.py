from __future__ import annotations

from fastapi.testclient import TestClient

from core.config import get_app_settings_path, refresh_runtime_settings, settings
from main import app


def main() -> None:
    app_settings_path = get_app_settings_path()
    backup_text: str | None = None
    had_file = app_settings_path.exists()

    if had_file:
        backup_text = app_settings_path.read_text(encoding="utf-8")

    try:
        if app_settings_path.exists():
            app_settings_path.unlink()
        settings.teacher_secret = ""

        client = TestClient(app)

        status = client.get("/api/teacher/bootstrap/status")
        assert status.status_code == 200
        assert status.json().get("requiresBootstrap") is True

        mismatch = client.post(
            "/api/teacher/bootstrap",
            json={"newSecret": "secret123", "confirmNewSecret": "secret999"},
        )
        assert mismatch.status_code == 400

        created = client.post(
            "/api/teacher/bootstrap",
            json={"newSecret": "secret123", "confirmNewSecret": "secret123"},
        )
        assert created.status_code == 200

        status_after = client.get("/api/teacher/bootstrap/status")
        assert status_after.status_code == 200
        assert status_after.json().get("requiresBootstrap") is False

        second_try = client.post(
            "/api/teacher/bootstrap",
            json={"newSecret": "another123", "confirmNewSecret": "another123"},
        )
        assert second_try.status_code == 409

        print("bootstrap_secret_test.py passed")
    finally:
        app_settings_path.parent.mkdir(parents=True, exist_ok=True)
        if had_file and backup_text is not None:
            app_settings_path.write_text(backup_text, encoding="utf-8")
        elif app_settings_path.exists():
            app_settings_path.unlink()
        refresh_runtime_settings()


if __name__ == "__main__":
    main()


