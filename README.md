# Attendance System (FastAPI)

Local classroom attendance app with rotating QR codes and Excel-only storage.

## Plan status

- Phases 1-6: implemented and verified.
- Phase 7: executable build flow implemented and validated locally on Linux.
- Phase 8: concurrency write check added and passing (`phase8_concurrency_test.py`).
- Manual testing + base commit: pending (next step).

## Quick start

```bash
cd /home/sarthak/Projects/Attendance-Python
python -m pip install -r requirements.txt
python main.py
```

Open:
- Teacher setup: `http://127.0.0.1:3000/teacher`
- Teacher configuration: `http://127.0.0.1:3000/teacher/config`
- Student scan page comes from the QR code (`/attend?...`)

## Config files

- Copy `.env.example` to `.env` and adjust values (`TEACHER_SECRET`, `BASE_URL`, `PORT`).
- Use the teacher configuration page to manage courses and runtime settings.
- Teacher secret can be rotated in the teacher configuration page using old/new/confirm secret flow.
- Runtime overrides are stored in `config/app_settings.json` (under the executable/user data directory).
- Course changes are stored in `config/courses.json` (under the executable/user data directory).
- If `BASE_URL` uses `127.0.0.1` / `localhost`, the app auto-detects LAN IP for QR links.

## Smoke test

```bash
cd /home/sarthak/Projects/Attendance-Python
python smoke_test.py
```

This creates a session, initializes an Excel worksheet, and appends one attendance row.

## Concurrency check

```bash
cd /home/sarthak/Projects/Attendance-Python
python phase8_concurrency_test.py
```

This runs parallel attendance writes to validate per-course Excel locking.

## Build executable

```bash
cd /home/sarthak/Projects/Attendance-Python
python build.py
```

Binary output appears in `dist/`.

## Build packages for Windows/macOS/Linux

- Use the GitHub Actions workflow in `.github/workflows/package-all-os.yml`.
- Run **"Build Binaries (Windows/macOS/Linux)"** from the Actions tab.
- Download artifacts:
  - `AttendanceSystem-Windows`
  - `AttendanceSystem-macOS`
  - `AttendanceSystem-Linux`

## Isolated binary run check

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
