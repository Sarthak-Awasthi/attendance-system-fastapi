from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from services.excel_service import initialize_worksheet, mark_attendance
from services.session_manager import (
    create_session,
    get_session,
    get_time_remaining_seconds,
    record_submission,
    validate_submission,
)


async def main() -> None:
    session = await create_session("CS301", 1)
    session_id = session["session_id"]

    await initialize_worksheet(session["course_code"], session["worksheet_name"])

    live = get_session(session_id)
    assert live is not None

    token = live["current_token"]
    ip = "192.168.0.10"
    result = validate_submission(session_id, token, ip)
    assert result == "VALID", result

    now = datetime.now(timezone.utc)
    await mark_attendance(
        live["course_code"],
        live["worksheet_name"],
        "21CS1001",
        attendance_date=now.date().isoformat(),
        present=1,
    )
    record_submission(session_id, ip, token)

    print("Smoke test passed")
    print(f"Session ID: {session_id}")
    print(f"Time remaining: {get_time_remaining_seconds(session_id)} sec")


if __name__ == "__main__":
    asyncio.run(main())

