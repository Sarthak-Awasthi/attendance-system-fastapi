# Release Guide (Windows/macOS/Linux)

This guide is for end-users running the packaged binary.

## What to Include in Your Release Package

Minimum:

- `AttendanceSystem` (Linux/macOS) or `AttendanceSystem.exe` (Windows)

Recommended:

- `.env` (optional)
- `config/courses.json` (optional)
- empty `data/` folder (optional)

Notes:

- If `.env` is missing, app still starts with defaults.
- If no teacher secret is configured, first visit to `/teacher` prompts one-time bootstrap setup.

## First-Run Checklist

1. Start the executable.
2. Open `http://127.0.0.1:3000/teacher` (or your configured host/port).
3. If prompted, set initial teacher secret (one-time bootstrap).
4. Open teacher config page and verify:
   - courses
   - data folder path (for Excel storage)
   - storage backend (Excel, Google Sheets, or Both)
   - base URL
   - QR rotation interval and token grace period
   - session duration defaults

## Google Sheets Setup (Optional)

If the faculty prefers cloud-based attendance storage:

1. Open the in-app setup guide at `http://127.0.0.1:3000/static/docs/google_sheets_setup.html`
2. Follow the 5 steps to create a Google Cloud service account (free)
3. Configure the storage backend to "Google Sheets" in teacher configuration

See also: `docs/google_sheets_setup.md`

## Run on Each OS

### Windows

- Double-click `AttendanceSystem.exe`
- If SmartScreen appears, choose **More info -> Run anyway**.

### macOS

- In Terminal:

```bash
cd /path/to/release
chmod +x AttendanceSystem
./AttendanceSystem
```

- If Gatekeeper blocks first run, right-click binary -> **Open**.

### Linux

```bash
cd /path/to/release
chmod +x AttendanceSystem
./AttendanceSystem
```

## Runtime File Locations

When running packaged binary, user-editable files are read/written near the executable location:

- `.env`
- `config/courses.json`
- `config/app_settings.json`
- `data/*.xlsx` (or configured custom data directory)

## Attendance Data Layout

Attendance sheets (Excel and Google Sheets) use a matrix layout:

- Column `A` header is `RollNo.`
- Date columns (`YYYY-MM-DD`) are added over time as attendance is taken
- Each student roll number has one row
- Values are `1` (present) or `0` (absent/not marked)

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Teacher actions fail with invalid secret | Set/verify teacher secret in bootstrap or teacher config |
| QR link not opening from student devices | Check `BASE_URL` in teacher config — should be your LAN IP |
| No course shown on teacher setup page | Add course from teacher config page |
| Excel files not appearing where expected | Verify configured data folder in teacher config |
| Google Sheets permission denied | Share the spreadsheet with the service account email |
| Google Sheets credentials error | Verify the JSON file path in teacher config |
| Theme not saving | Ensure browser allows localStorage |

## Building From Source

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync                   # Install dependencies
uv run python build.py    # Creates dist/AttendanceSystem
```
