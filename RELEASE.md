# Release Guide (Windows/macOS/Linux)

This guide is for end-users running the packaged binary.

## What to include in your release package

Minimum:

- `AttendanceSystem` (Linux/macOS) or `AttendanceSystem.exe` (Windows)

Recommended:

- `.env` (optional)
- `config/courses.json` (optional)
- empty `data/` folder (optional)

Notes:

- If `.env` is missing, app still starts with defaults.
- If no teacher secret is configured, first visit to `/teacher` prompts one-time bootstrap setup.

## First-run checklist

1. Start the executable.
2. Open `http://127.0.0.1:3000/teacher` (or your configured host/port).
3. If prompted, set initial teacher secret (one-time bootstrap).
4. Open teacher config page and verify:
   - courses
   - data folder path
   - base URL
   - session defaults

## Run on each OS

## Windows

- Double-click `AttendanceSystem.exe`
- If SmartScreen appears, choose **More info -> Run anyway**.

## macOS

- In Terminal:

```bash
cd /path/to/release
chmod +x AttendanceSystem
./AttendanceSystem
```

- If Gatekeeper blocks first run, right-click binary -> **Open**.

## Linux

```bash
cd /path/to/release
chmod +x AttendanceSystem
./AttendanceSystem
```

## Runtime file locations

When running packaged binary, user-editable files are read/written near the executable location:

- `.env`
- `config/courses.json`
- `config/app_settings.json`
- `data/*.xlsx` (or configured custom data directory)

## Attendance workbook layout

Attendance sheets use a matrix layout:

- Column `A` header is `RollNo.`
- Date columns (`YYYY-MM-DD`) are added over time as attendance is taken
- Each student roll number has one row
- Values are `1` (present) or `0` (absent/not marked)

## Quick troubleshooting

- App starts but teacher actions fail with invalid secret:
  - set/verify teacher secret in bootstrap or teacher config.
- QR link not opening from student devices:
  - check `BASE_URL` in teacher config.
- No course shown on teacher setup page:
  - add course from teacher config page.
- Excel files not appearing where expected:
  - verify configured data folder in teacher config.

