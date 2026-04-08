# Attendance System (FastAPI)

Local classroom attendance system with rotating QR codes and Excel-only storage.

## Features

- Teacher session setup and live dashboard
- Teacher configuration page for:
  - course management (add/update/remove)
  - runtime settings (data directory, defaults, base URL)
  - teacher secret rotation
  - password prompt on save for protected actions
- First-run bootstrap when no teacher secret is configured
- Student one-touch attendance using saved roll number on device
- Teacher-controlled dev mode (global + per-session)
- Excel output with fixed attendance schema

## Quick start

```bash
cd /home/sarthak/Projects/Attendance-Python
python -m pip install -r requirements.txt
python main.py
```

Open in browser:

- Teacher setup: `http://127.0.0.1:3000/teacher`
- Teacher config: `http://127.0.0.1:3000/teacher/config`
- Student page comes from QR URL: `/attend?...`

## Configuration

You can run the app with or without `.env`.

- Recommended: copy `.env.example` to `.env` and edit values.
- If `.env` is missing (or `TEACHER_SECRET` is empty), first visit to `/teacher` shows a one-time bootstrap form to set initial teacher secret.

Runtime settings and course edits are stored in user-writable files:

- `config/app_settings.json`
- `config/courses.json`

If `BASE_URL` is `127.0.0.1`/`localhost`, QR links auto-switch to detected LAN IP.

## Attendance data format (Excel)

Each row is written with this schema:

- `Roll. No.`
- `Date` (`YYYY-MM-DD`)
- `Time` (`HH:MM:SS±HH:MM`)
- `Session ID`
- `IP Address`
- `Present`
- `Classroom Code`

## Dev mode behavior

- Dev mode is teacher-controlled only.
- Global switch: teacher config page.
- Per-session switch: teacher dashboard.
- Student page does not expose dev mode controls.

## Tests

Run from repository root:

```bash
cd /home/sarthak/Projects/Attendance-Python
PYTHONPATH=. python tests/smoke_test.py
PYTHONPATH=. python tests/phase8_concurrency_test.py
PYTHONPATH=. python tests/dev_mode_api_test.py
PYTHONPATH=. python tests/bootstrap_secret_test.py
```

## Build local binary

```bash
cd /home/sarthak/Projects/Attendance-Python
python build.py
```

Output is generated in `dist/`.

## Build binaries for Windows, macOS, Linux

Use GitHub Actions workflow:

- File: `.github/workflows/package-all-os.yml`
- Workflow name: `Build Binaries (Windows/macOS/Linux)`
- Artifacts:
  - `AttendanceSystem-Windows`
  - `AttendanceSystem-macOS`
  - `AttendanceSystem-Linux`

## Distribution notes

For binary distribution, provide alongside executable:

- `.env` (optional if bootstrap flow is used for first secret)
- `config/courses.json` (optional if courses are configured in UI)
- writable `data/` directory (or set custom path in teacher config)

For end-user packaging and run instructions, see `RELEASE.md`.

## Isolated binary run check (Linux example)

```bash
cd /tmp
rm -rf attendance_binary_test
mkdir -p attendance_binary_test/config
cp /home/sarthak/Projects/Attendance-Python/dist/AttendanceSystem attendance_binary_test/
cp /home/sarthak/Projects/Attendance-Python/.env attendance_binary_test/.env
cp /home/sarthak/Projects/Attendance-Python/config/courses.json attendance_binary_test/config/courses.json
cd attendance_binary_test
./AttendanceSystem
```
