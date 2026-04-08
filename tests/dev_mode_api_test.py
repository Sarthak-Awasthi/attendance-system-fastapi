from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from core.config import settings
from main import app
from services.excel_service import initialize_worksheet
from services.session_manager import create_session, get_session


def _create_session_with_sheet(dev_mode_enabled: bool) -> tuple[str, str]:
    async def _create() -> tuple[str, str]:
        session = await create_session("CS301", 1, dev_mode_enabled=dev_mode_enabled)
        await initialize_worksheet(session["course_code"], session["worksheet_name"])
        return session["session_id"], session["current_token"]

    return asyncio.run(_create())


def _submit_twice(client: TestClient, session_id: str, token: str, dev_mode: bool) -> tuple[int, int]:
    payload = {
        "rollNumber": "21CS1001",
        "token": token,
        "sessionId": session_id,
        "devMode": dev_mode,
    }
    first = client.post("/api/student/submit", json=payload)
    second = client.post("/api/student/submit", json=payload)
    return first.status_code, second.status_code


def main() -> None:
    original_global = settings.allow_student_dev_mode
    client = TestClient(app)

    try:
        settings.allow_student_dev_mode = False
        session_id, token = _create_session_with_sheet(dev_mode_enabled=True)
        first, second = _submit_twice(client, session_id, token, dev_mode=True)
        assert first == 200, f"Expected first submit 200, got {first}"
        assert second == 409, f"Expected second submit 409 with global OFF, got {second}"

        settings.allow_student_dev_mode = True
        session_id, token = _create_session_with_sheet(dev_mode_enabled=False)
        first, second = _submit_twice(client, session_id, token, dev_mode=True)
        assert first == 200, f"Expected first submit 200, got {first}"
        assert second == 409, f"Expected second submit 409 with session OFF, got {second}"

        session_id, token = _create_session_with_sheet(dev_mode_enabled=True)
        # Student payload flag should not control repeat policy anymore.
        first, second = _submit_twice(client, session_id, token, dev_mode=False)
        assert first == 200, f"Expected first submit 200, got {first}"
        assert second == 200, f"Expected second submit 200 with global/session ON, got {second}"

        live = get_session(session_id)
        assert live is not None
        assert live["submission_count"] >= 2
        print("dev_mode_api_test.py passed")
    finally:
        settings.allow_student_dev_mode = original_global


if __name__ == "__main__":
    main()

