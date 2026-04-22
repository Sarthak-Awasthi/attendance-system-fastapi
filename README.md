# Attendance System (FastAPI)

Classroom attendance system with rotating QR codes, dual-timer token validation, and pluggable storage backends (Excel and Google Sheets).

## Features

- **Dual-timer QR rotation** — QR display rotates every N seconds, while scanned tokens remain valid for a configurable grace period
- Teacher session setup and live dashboard with real-time QR countdown
- Teacher configuration page for:
  - course management (add/update/remove)
  - runtime settings (data directory, defaults, base URL)
  - storage backend toggle (Excel / Google Sheets / Both)
  - token grace period and QR rotation interval
  - teacher secret rotation
  - password prompt on save for protected actions
- First-run bootstrap when no teacher secret is configured
- Student one-touch attendance using saved roll number on device
- Teacher-controlled dev mode (global + per-session)
- Dark/light theme with system preference detection
- Storage backends: local Excel (.xlsx) and/or Google Sheets (cloud)

## Quick Start

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
cd /home/sarthak/Projects/attendance-system-fastapi
uv sync          # Install dependencies
uv run python main.py   # Start on port 3000
```

Open in browser:

- Teacher setup: `http://127.0.0.1:3000/teacher`
- Teacher config: `http://127.0.0.1:3000/teacher/config`
- Google Sheets setup guide: `http://127.0.0.1:3000/static/docs/google_sheets_setup.html`
- Student page comes from QR URL: `/attend?...`

## Configuration

You can run the app with or without `.env`.

- Recommended: copy `.env.example` to `.env` and edit values.
- If `.env` is missing (or `TEACHER_SECRET` is empty), first visit to `/teacher` shows a one-time bootstrap form to set initial teacher secret.

Runtime settings and course edits are stored in user-writable files:

- `config/app_settings.json`
- `config/courses.json`

**Config hierarchy (highest to lowest priority):**

1. `config/app_settings.json` (runtime overrides via teacher UI)
2. `.env` file or environment variables
3. Hardcoded defaults in `core/config.py`

If `BASE_URL` is `127.0.0.1`/`localhost`, QR links auto-switch to detected LAN IP.

## Storage Backends

### Excel (default)

Each course gets one `.xlsx` file. Each worksheet stores attendance as a matrix:

| RollNo. | 2026-04-07 | 2026-04-08 | 2026-04-09 |
|---|---:|---:|---:|
| 21CS1001 | 1 | 0 | 1 |
| 21CS1002 | 1 | 0 | 0 |

- First column header is `RollNo.`
- Additional headers are dates in `YYYY-MM-DD` format
- Cell value `1` = present, `0` = absent/not marked
- Date columns are created automatically on first submission for that day

### Google Sheets

Uses the same matrix format as Excel, stored in Google Sheets for cloud access. Requires a Google Cloud service account (free). See the [setup guide](docs/google_sheets_setup.md) or access it in-app at `/static/docs/google_sheets_setup.html`.

Configure via teacher config page:
- **Storage Backend**: Excel / Google Sheets / Both
- **Service Account JSON Path**: path to downloaded credentials file
- **Spreadsheet Key**: single ID or per-course mapping (`CS301=ID1,MA101=ID2`)

## Dual-Timer QR Rotation

| Setting | Default | Range | Purpose |
|---------|---------|-------|---------|
| `qr_rotate_interval_sec` | 5 | 1–120 | How often the QR image changes on the dashboard |
| `token_grace_period_sec` | 30 | 5–120 | How long a scanned token remains valid for submission |

Students see a new QR every 5 seconds, but have 30 seconds to submit after scanning — eliminating failed submissions from slow scans.

## Dev Mode

- Dev mode is teacher-controlled only.
- Global switch: teacher config page.
- Per-session switch: teacher dashboard.
- Student page does not expose dev mode controls.
- When enabled: skips IP and token uniqueness checks, allowing repeat submissions.

## Tests

Run from repository root using uv:

```bash
uv run pytest tests/ -v                    # Run all 95 tests
uv run pytest tests/test_session_manager.py -v  # Run specific test file
uv run pytest tests/ -k "test_token"       # Run tests matching pattern
```

### Test files

| File | Coverage |
|------|----------|
| `test_session_manager.py` | Session CRUD, token rotation, sliding window, validation, expiration, dev mode |
| `test_excel_service.py` | Worksheet init, attendance marking, dedup, concurrent writes |
| `test_config_service.py` | Course CRUD, settings persistence, secret management |
| `test_teacher_api.py` | Bootstrap, session lifecycle, QR, courses, settings, secret |
| `test_student_api.py` | Submission validation, token/IP/session checks, dev mode |
| `test_qr_generator.py` | QR data URI format, PNG validity, uniqueness |

Legacy standalone tests are still available but not pytest-discoverable:

```bash
PYTHONPATH=. uv run python tests/smoke_test.py
PYTHONPATH=. uv run python tests/phase8_concurrency_test.py
PYTHONPATH=. uv run python tests/dev_mode_api_test.py
PYTHONPATH=. uv run python tests/bootstrap_secret_test.py
```

## Build Local Binary

```bash
uv run python build.py    # Creates dist/AttendanceSystem
```

Output is generated in `dist/`.

## Build Binaries for Windows, macOS, Linux

Use GitHub Actions workflow:

- File: `.github/workflows/package-all-os.yml`
- Workflow name: `Build Binaries (Windows/macOS/Linux)`
- Artifacts:
  - `AttendanceSystem-Windows`
  - `AttendanceSystem-macOS`
  - `AttendanceSystem-Linux`

## Distribution Notes

For binary distribution, provide alongside executable:

- `.env` (optional if bootstrap flow is used for first secret)
- `config/courses.json` (optional if courses are configured in UI)
- writable `data/` directory (or set custom path in teacher config)

For end-user packaging and run instructions, see `RELEASE.md`.

## Isolated Binary Run Check (Linux example)

```bash
cd /tmp
rm -rf attendance_binary_test
mkdir -p attendance_binary_test/config
cp dist/AttendanceSystem attendance_binary_test/
cp .env attendance_binary_test/.env
cp config/courses.json attendance_binary_test/config/courses.json
cd attendance_binary_test
./AttendanceSystem
```
