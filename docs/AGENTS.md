# AGENTS Guide

## Current repo reality (read first)
- This repository is currently **spec-first**: `Plan.md` is the primary artifact and `main.py` is empty.
- Treat `Plan.md` as the source of truth for implementation intent; do not infer undocumented runtime behavior from absent code.
- If adding code, align naming and module boundaries to the structure defined in `Plan.md` Section 2.

## Big-picture architecture (target design from `Plan.md`)
- Single-process FastAPI app (`main.py`) serves both teacher and student flows over LAN, fully offline.
- Persistent storage is **Excel only** (`data/<COURSE>.xlsx`), no DB and no cloud integrations.
- Service boundaries are explicit:
  - `routers/teacher.py` and `routers/student.py` for HTTP endpoints
  - `services/session_manager.py` for in-memory session/token lifecycle
  - `services/excel_service.py` for all `.xlsx` I/O
  - `services/qr_generator.py` for QR payload/image generation
  - `core/config.py` and `core/security.py` for env/path/secret handling
- Data flow (Plan Section 13): teacher starts session -> rotating QR token issued -> student submit validated -> row appended to worksheet -> submission recorded in memory.

## Critical implementation patterns to preserve
- Token security model (Plan Section 5/11): accept only current/previous token, reject reused tokens via `used_tokens`, enforce one submission per IP via `used_ips`.
- Concurrency model for Excel writes (Plan Section 7): per-course `asyncio.Lock` + `await asyncio.to_thread(...)` around `openpyxl` operations.
- Session lifecycle (Plan Section 5): background `asyncio.create_task` rotates token every `QR_ROTATE_INTERVAL_SEC`; `end_session` must cancel task.
- Worksheet schema is fixed (Plan Section 3):
  `Roll Number | Timestamp | Session ID | IP Address | Present | Classroom Code`.
- Static frontend is vanilla files under `public/`; do not introduce template engines or frontend build tooling.

## Developer workflows (from plan)
- Local run target (after implementation): `python main.py` (Uvicorn startup inside `if __name__ == "__main__"`).
- Build target (after implementation): `python build.py` using PyInstaller one-file bundle with `public/` and `config/` data.
- Configuration contract: `.env` keys include `PORT`, `TEACHER_SECRET`, `QR_ROTATE_INTERVAL_SEC`, `BASE_URL`, `EXCEL_DATA_DIR`.
- Deployment expectation: executable + `.env` + `config/courses.json` colocated; runtime writes `data/` next to executable.

## File-level priorities for new agents
- Read `Plan.md` Sections **2, 4, 5, 7, 8, 10, 11, 12, 15** before coding.
- Implement in phase order from `Plan.md` Section 15; later phases assume earlier contracts.
- Keep API and model names consistent with plan examples (`StartSessionRequest`, `SubmitAttendanceRequest`, `/api/teacher/session/start`, `/api/student/submit`).
- When uncertain, prefer strict adherence to documented behavior over introducing new abstractions.

