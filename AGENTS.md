# AGENTS.md - Attendance System FastAPI

AI agents working on this codebase should understand the following:

## Architecture Overview

**Core Components:**
- **FastAPI app** (`main.py`): Entry point with lifespan management, mounts routers, serves static files via `/static`
- **Teacher router** (`routers/teacher.py`): Dashboard, configuration endpoints, session management (start/end/QR)
- **Student router** (`routers/student.py`): Attendance submission with token/IP validation
- **Session manager** (`services/session_manager.py`): In-memory session store with async token rotation, sliding window grace period, and expiration
- **Storage factory** (`services/storage_factory.py`): Protocol-based backend router — dispatches to Excel, Google Sheets, or both
- **Excel service** (`services/excel_service.py`): Async worksheet management with per-course locking
- **Google Sheets service** (`services/google_sheets_service.py`): `gspread`-based cloud storage with per-course locking
- **Config service** (`services/config_service.py`): Course CRUD, settings persistence, teacher secret management

**Data Flow:**
1. Teacher starts session → storage factory determines backend → session created with rotating token loop → QR generated with current token
2. QR display rotates every `qr_rotate_interval_sec` (1-120s, default 5s)
3. Scanned tokens remain valid for `token_grace_period_sec` (5-120s, default 30s) via sliding window
4. Student scans QR → validates token (grace period window), session, IP → records via storage factory to configured backend
5. Session expires after `default_session_duration_minutes` (default 10m)

**Key Design Decisions:**
- Sessions are **in-memory** (lost on restart) — intentional for classroom use
- Attendance stored as **roll/date matrix**: `RollNo.` column + date columns (YYYY-MM-DD) with 1/0 values
- One course = one file/spreadsheet, multiple worksheets per day (`{date}_S1`, `{date}_S2`, etc.)
- Config/state split: `.env` + `config/app_settings.json` (runtime) + `config/courses.json`
- Bootstrap mode: if `TEACHER_SECRET` empty, teacher must set initial secret before use
- **Storage backends are pluggable** via `storage_factory.get_storage()` — routers never import Excel/Sheets directly
- Teacher secret stored in `sessionStorage` (not URL params) for security

## Package Management

This project uses **uv** for dependency management and virtual environments.

```bash
uv sync              # Install all dependencies
uv run python main.py   # Run the app
uv run pytest tests/ -v  # Run tests
uv lock              # Regenerate lockfile
```

Dependencies are declared in `pyproject.toml` (not `requirements.txt`).

## Critical Workflows

**Running the app:**
```bash
uv run python main.py  # Runs on port 3000 (or $PORT env var)
# Opens teacher UI at http://127.0.0.1:3000/teacher
```

**Running tests:**
```bash
uv run pytest tests/ -v                         # All 95 tests (~4s)
uv run pytest tests/test_session_manager.py -v   # Session manager only
uv run pytest tests/ -k "test_token"             # Pattern matching
```

Legacy standalone tests (not pytest-discoverable):
```bash
PYTHONPATH=. uv run python tests/smoke_test.py
PYTHONPATH=. uv run python tests/phase8_concurrency_test.py
PYTHONPATH=. uv run python tests/dev_mode_api_test.py
PYTHONPATH=. uv run python tests/bootstrap_secret_test.py
```

**Building binary:**
```bash
uv run python build.py  # Creates dist/AttendanceSystem
```

**Config hierarchy (highest to lowest priority):**
1. `config/app_settings.json` (runtime overrides via teacher UI)
2. `.env` file or environment variables
3. Hardcoded defaults in `core/config.py`

## Project Conventions

**Settings and configuration:**
- `Settings` dataclass in `core/config.py` is mutable singleton; use `refresh_runtime_settings()` to reload from files
- App settings stored in `config/app_settings.json`, loaded at startup
- Teacher secret validation in `core/security.is_teacher_secret_valid()` — **all protected endpoints check this**
- New settings fields: `token_grace_period_sec`, `storage_backend`, `google_credentials_path`, `google_spreadsheet_key`

**Session validation (dual-timer model):**
- Sessions validate via `validate_submission()`: checks token (sliding window grace period), IP, expiration, dev mode state
- Token is valid if it exists in `valid_tokens` list AND was created within `token_grace_period_sec`, OR equals `current_token`/`previous_token`
- `_prune_expired_tokens()` removes tokens outside grace window on each rotation
- Dev mode allows repeat submissions from same IP/token; disabled globally in config, per-session via dashboard
- Session status tracked by `is_active` flag and expiration check

**Storage backend pattern:**
- `storage_factory.get_storage()` returns the active backend based on `settings.storage_backend`
- Three backends: `ExcelBackend`, `GoogleSheetsBackend`, `DualBackend` (writes to both)
- All implement the `StorageBackend` Protocol: `get_next_worksheet_name()`, `initialize_worksheet()`, `mark_attendance()`
- Routers import only `get_storage()` — never direct Excel/Sheets services

**Excel concurrency:**
- Each course has per-file `asyncio.Lock` in `course_locks` dict to prevent race conditions
- `mark_attendance()` awaits lock before read/write
- Worksheets created on-demand; auto-creates date column when first submission for that day

**Google Sheets concurrency:**
- Same pattern as Excel: per-course `asyncio.Lock` in `_gsheets_locks`
- Uses `asyncio.to_thread()` to run blocking `gspread` calls off the event loop
- Cached `gspread` client; call `invalidate_client()` after credentials change

**Request models:**
- All teacher actions require `secret` field (validated before processing)
- Pydantic models normalize input: uppercase course codes, strip whitespace, validate field lengths
- Roll number pattern: `[A-Z0-9]{4,15}` (case-insensitive regex)
- `UpdateTeacherSettingsRequest` includes: `storageBackend`, `tokenGracePeriodSec`, `googleCredentialsPath`, `googleSpreadsheetKey`

## Integration Points & Dependencies

**External libraries (managed via uv + pyproject.toml):**
- `fastapi`/`uvicorn`: Web server
- `openpyxl`: Excel read/write (preserves formatting, locks)
- `qrcode`/`pillow`: QR generation (base64 PNG)
- `pydantic`: Request validation
- `python-dotenv`: .env loading
- `pyinstaller`: Binary packaging
- `gspread`: Google Sheets API client
- `google-auth`: Google service account authentication
- `httpx`: Used in legacy tests
- `pytest`/`pytest-asyncio`: Test framework

**File structure:**
- `public/`: Static HTML/JS/CSS served from `/static` route
  - `public/scripts/theme.js`: Dark/light mode toggle
  - `public/styles/main.css`: Design system (CSS custom properties, dark mode, toasts, animations)
  - `public/docs/`: In-app documentation (Google Sheets setup guide)
  - `public/favicon.svg`: App favicon
- `config/`: User-writable course/app settings (priority over defaults)
- `core/`: Settings loading, logging, security helpers, constants
- `services/`: Business logic (session mgmt, storage factory, Excel, Google Sheets, QR, config I/O)
- `routers/`: API endpoints (teacher, student)
- `tests/`: Pytest suite + legacy standalone tests
  - `tests/conftest.py`: Shared fixtures (client, clean_settings, set_secret, setup_test_course, session_factory)

**Bootstrap flow (first run):**
- `/api/teacher/bootstrap/status` → check if secret configured
- `/api/teacher/bootstrap` → POST new secret (requires confirmation match)
- After bootstrap: teacher accesses `/teacher/config` to add courses, adjust settings

## Common Patterns & Gotchas

**Token rotation (dual-timer):**
- Rotation happens in background task `_rotate_loop()` spawned per session
- Each rotation creates a new token and appends `(token, timestamp)` to `valid_tokens` list
- `_prune_expired_tokens()` removes entries older than `token_grace_period_sec`
- `_is_token_in_grace_period()` checks both the sliding window AND current/previous token
- Used tokens tracked in `used_tokens` set; checked during validation if dev mode off

**Expiration rules:**
- Session expires when `datetime.now() >= start_time + timedelta(minutes=duration_minutes)`
- `get_session()` and `get_time_remaining_seconds()` check/set `is_active=False` when expired
- Rotation task self-exits on expiration

**Dev mode behavior:**
- **Global**: `allow_student_dev_mode` in app settings (teacher config page)
- **Per-session**: `dev_mode_enabled` flag set during session start or toggled via dashboard
- **Effect**: If both enabled, `validate_submission()` skips IP/token uniqueness checks, allows repeats
- **Not exposed** to student UI — only teacher dashboard controls

**Frontend patterns:**
- Teacher secret stored in `sessionStorage` (not URL query params) — secure from browser history/server logs
- All user feedback via toast notifications (no `alert()` calls)
- Button loading states via `.loading` CSS class (spinner animation)
- QR countdown timer and progress bar synced to server's `qrRotateIntervalSec`
- Student roll number saved to `localStorage` for quick re-submission

**Multi-platform binary:**
- `get_base_dir()`: Returns PyInstaller bundle root if frozen, else repo root
- `get_user_data_dir()`: Returns executable dir if frozen, else repo root
- Config/data files searched in user data dir first, then app bundle (for distribution)

## Debugging & Common Issues

- **"Teacher secret is already configured" on bootstrap**: Secret already set; use reset endpoints or manually delete `app_settings.json`
- **Session not found**: Session lost (app restart) or wrong session ID in request
- **Token invalid**: Student's QR is outdated (outside grace period window) or from different session
- **IP already used**: Another student from same IP already submitted (disable dev mode to enforce)
- **Excel file locked**: Another process has file open; ensure concurrent `mark_attendance()` calls use the per-course lock
- **Google Sheets 403**: Spreadsheet not shared with service account email
- **Google Sheets credentials error**: Check `google_credentials_path` points to valid JSON file
- **Storage backend not switching**: `storage_factory._backends` cache may need clearing — call `invalidate_cache()` or restart app

## Testing Patterns

Tests use `uv run pytest` with `pythonpath = ["."]` in `pyproject.toml`. Test framework: `pytest` + `pytest-asyncio` with `asyncio_mode = "auto"`.

**Pytest test files (95 tests):**
- `test_session_manager.py`: Session CRUD, token rotation, sliding window, validation, expiration, dev mode
- `test_excel_service.py`: Worksheet init, attendance marking, dedup, concurrent writes, error cases
- `test_config_service.py`: Course CRUD, settings persistence, secret management
- `test_teacher_api.py`: Bootstrap, session lifecycle, QR, courses, settings, secret, dev mode
- `test_student_api.py`: Submission validation, token/IP/session checks, dev mode
- `test_qr_generator.py`: QR data URI format, PNG validity, uniqueness
- `conftest.py`: Shared fixtures — settings backup/restore, course setup, session factory

**Legacy standalone tests:**
- `smoke_test.py`: Basic start/submit/end flow
- `phase8_concurrency_test.py`: Token rotation under concurrent submissions
- `dev_mode_api_test.py`: Dev mode bypass validation
- `bootstrap_secret_test.py`: Bootstrap endpoint and edge cases
