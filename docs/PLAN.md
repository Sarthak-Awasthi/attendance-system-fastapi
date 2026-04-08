Here is the updated **Full Development Plan** modified specifically for a **Python-based application** using **FastAPI**. It includes instructions on how to compile the entire system into a standalone, double-clickable executable (for Windows `.exe`, macOS `.app`/binary, or Linux) using **PyInstaller**. 

This completely removes the need for Node.js, NPM, or any installation on the teacher's end once compiled.

--- START OF FILE PLAN.md ---

# Classroom Attendance System — Full Development Plan (Python / Executable Version)
> This document is intended for a localized AI coding agent. Follow every section in order. Do not skip ahead. Each phase builds on the previous one.

---

## 0. Project Overview

Build a **web-based classroom attendance system** using a **Dynamic Rotating QR Code** approach, packaged as a **standalone compiled executable**. A teacher starts a session from a dashboard; a QR code is projected and refreshes every 5 seconds. Students scan it, land on a form, enter their Roll Number, and submit. Attendance is written to a **local Excel file (.xlsx)** stored on the teacher's machine. Fraud is prevented via one-time tokens, IP-based deduplication, and session duration enforcement.

### Core Principles
- No internet required — fully offline after the server (executable) starts on the teacher's laptop.
- No installation required for the teacher (just run the compiled `.exe` / binary).
- No mobile app installation required for students (uses native phone camera + browser).
- Works via the local WiFi network.
- Excel (.xlsx) files are the only persistent storage — no database, no cloud.
- Each course has its own `.xlsx` file auto-created in a local `data/` folder.
- Every session generates a new, unique classroom code.
- QR tokens are single-use and time-bound.

---

## 1. Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend Server | **Python + FastAPI** | High performance, async-native, built-in validation. |
| Server Gateway | **Uvicorn** | Fast ASGI server to run the FastAPI app. |
| Frontend | Vanilla HTML + CSS + JS | No build tools needed, works on all phones, easily served by FastAPI. |
| QR Generation | `qrcode` (Python library) | Generates QR codes as base64 images entirely offline. |
| Excel Read/Write | `openpyxl` (Python library) | Native Excel file manipulation (reads/writes real .xlsx). |
| Session Storage | In-memory Python `dict` | Tokens are ephemeral, no DB needed. |
| Unique IDs | `uuid` (Python stdlib) | For session IDs and one-time tokens. |
| Environment Config | `python-dotenv` | For local dev (compiled apps will read a local `.env` or `config.ini`). |
| Compilation | **PyInstaller** | Bundles Python, libraries, and static files into ONE executable. |

### Do NOT use:
- Any frontend framework (React, Vue, etc.) — overkill for this.
- Any cloud API (Google, Microsoft) — everything is local.
- Any authentication library — teacher link security is handled via a secret token in the URL.
- Any SQL/NoSQL database — Excel files are the database.

---

## 2. Project Folder Structure

```
attendance-system/
├── main.py                    # Main FastAPI server — entry point
├── build.py                   # PyInstaller compile script
├── .env                       # Config values — NEVER commit this
├── .env.example               # Template for .env — commit this
├── .gitignore                 # Ignore venv/, __pycache__/, data/, dist/, build/
├── requirements.txt           # Python dependencies
│
├── config/
│   └── courses.json           # Maps course codes to Excel filenames + metadata
│
├── data/                      # All Excel attendance files live here (auto-created)
│   └── (Excel files will appear here during runtime)
│
├── routers/
│   ├── teacher.py             # All teacher-facing API routes
│   └── student.py             # All student-facing API routes
│
├── services/
│   ├── session_manager.py     # In-memory session + token store
│   ├── qr_generator.py        # QR code generation logic
│   └── excel_service.py       # All Excel file read/write logic using openpyxl
│
├── core/
│   ├── config.py              # Loads ENV vars and handles paths (PyInstaller aware)
│   └── security.py            # Validates teacher secret
│
└── public/
    ├── teacher/
    │   ├── index.html         # Teacher setup page
    │   └── dashboard.html     # Teacher live dashboard (QR display + timer)
    └── student/
        ├── scan.html          # Landing page after QR scan (attendance form)
        └── result.html        # Success or failure confirmation page
```

---

## 3. Excel File Setup

### 3.1 How Files Are Organized
- Every course has exactly one `.xlsx` file in the `data/` folder.
- The filename matches the course code exactly: `CS301.xlsx`, `MA101.xlsx`, etc.
- Each file contains one worksheet per class session, named by date and session number: e.g., `2026-04-08_S1`, `2026-04-08_S2`.
- If two sessions happen on the same day for the same course, they each get their own worksheet tab.

### 3.2 Worksheet Structure
Each worksheet (one per session) has the following header row in Row 1:

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Roll Number | Timestamp | Session ID | IP Address | Present | Classroom Code |

- Row 1 is always the header — written once when the worksheet is created.
- Row 2 onwards are attendance records appended as students submit.
- Column E (Present) is always `1` (integer) — only students who submitted get a row.

### 3.3 Auto-Creation Logic
The `excel_service.py` must handle this automatically:
- If `data/CS301.xlsx` does not exist → create it with no default worksheets (remove default 'Sheet').
- When a new session starts → add a new worksheet tab named `{DATE}_{SESSION_NUMBER}` and write the header row.
- When a student submits → append one row to the correct worksheet.
- The agent must NEVER delete or overwrite existing worksheets.

---

## 4. Environment Variables & Paths (.env)

```ini
PORT=3000
TEACHER_SECRET=some_long_random_string_here
QR_ROTATE_INTERVAL_SEC=5
DEFAULT_SESSION_DURATION_MINUTES=10
BASE_URL=http://192.168.1.100:3000
EXCEL_DATA_DIR=./data
```

### PyInstaller Path Handling (`core/config.py`)
When bundled into an executable, Python extracts static files (`public/`) to a temporary folder (`sys._MEIPASS`). `config.py` MUST resolve paths dynamically:
```python
import sys
import os

def get_base_dir():
    # If running as a PyInstaller bundle
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    # If running as a normal Python script
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# User data should ALWAYS be relative to the executable's actual location, 
# NOT the temp MEIPASS folder.
def get_user_data_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
```
All Excel files and config reads (like `courses.json` and `.env`) should use `get_user_data_dir()`. Static HTML files should use `get_base_dir()`.

---

## 5. In-Memory Session Manager (`session_manager.py`)

### 5.1 Concurrency & Background Tasks
Use Python's `asyncio`. The session rotation is an `asyncio.Task` that loops in the background.

### 5.2 Session Dictionary Structure
```python
sessions = {
  "SESSION_UUID": {
    "session_id": "SESSION_UUID",
    "course_code": "CS301",
    "worksheet_name": "2026-04-08_S1",
    "classroom_code": "X7K2PQ",           # random 6-char code
    "start_time": datetime.now(),         # datetime object
    "duration_minutes": 10,
    "is_active": True,
    "rotation_task": "<asyncio.Task>",      # Task reference to cancel later
    "current_token": "32-char-uuid",
    "previous_token": "32-char-uuid",
    "used_tokens": set(),                 # ALL tokens ever issued
    "used_ips": set(),                    # IPs that submitted
    "submission_count": 0
  }
}
```

### 5.3 Required Functions

**`create_session(course_code, duration_minutes)`**
- Generates UUID for `session_id` and random 6-char `classroom_code`.
- Generates `worksheet_name` (`YYYY-MM-DD_SN`).
- Creates `rotation_task` via `asyncio.create_task(_rotate_loop(session_id))`.

**`_rotate_loop(session_id)` (Internal Async Coroutine)**
- `while True:` loop. `await asyncio.sleep(QR_ROTATE_INTERVAL_SEC)`.
- Moves `current_token` to `previous_token`.
- Adds old token to `used_tokens`.
- Generates new `current_token`.
- Breaks if `is_active` becomes False.

**`validate_submission(session_id, token, ip)`**
- Strict order: Session exists? -> Active/Not Expired? -> Token matches current/previous? -> Token not in used_tokens? -> IP not in used_ips?
- Returns Enum/String: `"VALID"`, `"SESSION_NOT_FOUND"`, `"SESSION_EXPIRED"`, `"TOKEN_INVALID"`, `"IP_ALREADY_USED"`.

**`record_submission(session_id, ip, token)`**
- Increments count, adds to sets. Called only after successful Excel write.

**`end_session(session_id)`**
- Sets `is_active = False`. Cancels the `rotation_task`.

---

## 6. QR Generator Service (`qr_generator.py`)

**`generate_qr_base64(token, session_id)`**
- Builds the URL: `{BASE_URL}/attend?token={token}&session={session_id}`
- Uses the `qrcode` library to build the image in memory.
- Uses `base64.b64encode` to return a `data:image/png;base64,...` string.

```python
import qrcode
import base64
from io import BytesIO

def generate_qr_base64(url: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"
```

---

## 7. Excel Service (`excel_service.py`)

Uses `openpyxl`. 

### Critical Rule on Concurrent Writes
Multiple students may submit via FastAPI async endpoints. `openpyxl` is synchronous and not thread-safe for the same file. 
Implement a per-course lock dictionary in Python:
```python
import asyncio
course_locks = defaultdict(asyncio.Lock)
```
Every operation (initialize, append) MUST acquire the specific course lock before reading/writing the file. Use `await asyncio.to_thread(...)` to run the blocking Excel save operations without freezing FastAPI's async event loop.

### Functions to Export

**`initialize_worksheet(course_code, worksheet_name)`**
- Acquires lock.
- If file missing, creates `openpyxl.Workbook()`.
- Creates sheet, writes header, applies bold styles, sets column dimensions, freezes row 1.
- Saves file via thread. Releases lock.

**`append_attendance_row(course_code, worksheet_name, row_data)`**
- Acquires lock.
- Loads workbook, finds sheet. Appends row `[roll, timestamp, session_id, ip, 1, classroom_code]`.
- Saves file via thread. Releases lock.

---

## 8. API Routes (FastAPI)

### Pydantic Models (`models.py` or inline)
Define request bodies securely:
```python
from pydantic import BaseModel
class StartSessionRequest(BaseModel):
    courseCode: str
    durationMinutes: int
    secret: str

class SubmitAttendanceRequest(BaseModel):
    rollNumber: str
    token: str
    sessionId: str
```

### 8.1 Teacher Routes (`routers/teacher.py`)

- **`GET /teacher`**: Serves `public/teacher/index.html` via `FileResponse`.
- **`GET /api/teacher/courses`**: Returns list of courses from JSON.
- **`POST /api/teacher/session/start`**: Validates secret. Calls SessionManager and ExcelService. Returns session details.
- **`GET /api/teacher/session/{session_id}/qr`**: Validates secret. Calculates `timeRemainingSeconds`. Returns `{ qrBase64, timeRemainingSeconds, submissionCount, classroomCode, isActive }`.
- **`POST /api/teacher/session/{session_id}/end`**: Validates secret. Calls `end_session`.

### 8.2 Student Routes (`routers/student.py`)

- **`GET /attend`**: Serves `public/student/scan.html`. URL parameters are handled by frontend JS.
- **`POST /api/student/submit`**: 
  - Extracts IP via `request.client.host`.
  - Validates `rollNumber` regex `/^[A-Z0-9]{4,15}$/i`.
  - Calls `validate_submission`. 
  - If valid: calls `append_attendance_row`. If successful, calls `record_submission`.

---

## 9. Frontend Pages (HTML/JS/CSS)

*(Keep logic identical to original plan. Do NOT use Python templates like Jinja2. Keep it strictly Vanilla JS fetching JSON from the FastAPI backend. This ensures the frontend logic executes cleanly on the student's phone browser.)*

### Files:
- `public/teacher/index.html`
- `public/teacher/dashboard.html`
- `public/student/scan.html`
- `public/student/result.html`

*The frontend paths should be mounted in FastAPI using `app.mount("/static", StaticFiles(directory="public"), name="static")`.*

---

## 10. `main.py` — Main Entry Point

### Responsibilities
- Load environment variables.
- Initialize FastAPI app (`app = FastAPI()`).
- Mount static files. Include Routers.
- Add an `@app.on_event("startup")` lifecycle hook:
  1. Ensure `data/` folder exists using `get_user_data_dir()`.
  2. Load and parse `courses.json`.
  3. Print startup ASCII banner and URL links to the console.
- Run via Uvicorn programmatically if executed directly:
  ```python
  if __name__ == "__main__":
      import uvicorn
      uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3000)))
  ```

---

## 11. Security Rules — Enforce All of These

| Threat | Mitigation |
|---|---|
| Student accessing dashboard | All teacher endpoints check `secret` against `.env` value. |
| Student reusing QR token | `used_tokens` set. Reusing returns `TOKEN_INVALID`. |
| Screenshot fraud | QR rotates every 5s. |
| Two-phone fraud | `used_ips` set. One submission per IP. |
| Roll number XSS | Validated via Pydantic/Regex server-side. |
| Concurrent Excel writes | Controlled via `asyncio.Lock` per course. |

---

## 12. Executable Build Script (`build.py`)

This phase handles compiling the app into a standalone desktop application.

Use **PyInstaller**. Write a script `build.py` to automate compilation so the teacher only needs one file.

```python
# build.py
import PyInstaller.__main__
import platform

# Identify OS to name the output binary correctly
os_name = platform.system().lower()
ext = ".exe" if os_name == "windows" else ""

PyInstaller.__main__.run([
    'main.py',
    '--name=%s' % f"AttendanceSystem{ext}",
    '--onefile',
    '--add-data=public:public',       # Bundle HTML/CSS/JS
    '--add-data=config:config',       # Bundle default config
    '--clean',
    '--noconfirm'
])
```
*Note: The generated executable will unpack `public` into a temp folder at runtime, which is why `core/config.py` handling `sys._MEIPASS` is mandatory.*

---

## 13. Data Flow — Step by Step
*(Same logic as the original Node.js flow, mapped to Python functions.)*
Teacher opens dashboard -> FastAPI validates secret -> Session initialized in memory loop -> QR polled -> Student scans -> FastAPI evaluates via `asyncio` -> `openpyxl` locks and writes row -> returns success.

---

## 14. `requirements.txt` Dependencies

```text
fastapi>=0.103.0
uvicorn>=0.23.2
qrcode>=7.4.2
Pillow>=10.0.0
openpyxl>=3.1.2
pydantic>=2.3.0
python-dotenv>=1.0.0
pyinstaller>=6.0.0
```

---

## 15. Build Order for the Agent

Execute phases strictly in this order. Do not proceed until confirmed working.

### Phase 1 — Scaffold
- [ ] Create folder structure.
- [ ] Create `requirements.txt` and install locally.
- [ ] Create `.env`, `.env.example`, and `config/courses.json`.
- [ ] Implement `core/config.py` with PyInstaller `sys._MEIPASS` pathing logic.

### Phase 2 — Excel Service
- [ ] Implement `excel_service.py` with `openpyxl`, `asyncio.Lock`, and `asyncio.to_thread`.
- [ ] Write `test_excel.py`: test initialization, append 3 rows, confirm file saves without freezing. Delete test after passing.

### Phase 3 — Session Manager
- [ ] Implement `session_manager.py` with `asyncio.create_task` looping interval.
- [ ] Write `test_session.py`: create session, await 6 seconds to verify token rotation, test validations. Delete test after passing.

### Phase 4 — QR Generator
- [ ] Implement `qr_generator.py`. Test base64 output.

### Phase 5 — API Routes & FastAPI
- [ ] Implement `routers/teacher.py` and `routers/student.py` using Pydantic schemas.
- [ ] Implement `main.py` entry point.
- [ ] Run `python main.py` and verify all endpoints via cURL or Postman.

### Phase 6 — Frontend (Teacher & Student)
- [ ] Create HTML/JS/CSS files in `public/`.
- [ ] Test the full local browser loop (Start Session -> Dashboard -> Scan QR -> Form -> Submit -> Success).

### Phase 7 — Standalone Compilation
- [ ] Create `build.py`.
- [ ] Run `python build.py`.
- [ ] Locate the generated `.exe` (or binary) in the `dist/` folder.
- [ ] Move the `.exe` to a completely new, empty folder.
- [ ] Create a `.env` and `config/courses.json` in that new folder.
- [ ] Double click the `.exe`. Verify the server starts and serves HTML properly without crashing.

### Phase 8 — End-to-End & Polish
- [ ] Run final concurrency tests (multiple browsers submitting simultaneously) against the compiled binary to ensure `openpyxl` thread-safety holds.
- [ ] Ensure terminal outputs clear, colorful logs (using standard library `logging` or print statements).

---

## 16. Running on the Classroom LAN (For the Teacher)

Instead of dealing with npm or Node.js, the workflow for the teacher is now trivial:

1. **Download** the compiled `AttendanceSystem.exe` (or Mac/Linux binary) to their laptop.
2. Ensure `.env` and `config/courses.json` exist in the same folder as the executable.
3. Find their laptop's LAN IP (e.g., `192.168.1.100`) and set `BASE_URL=http://192.168.1.100:3000` in the `.env`.
4. **Double click** the executable. A terminal window will open showing the server is running.
5. Open the provided Teacher Link in their browser.
6. When class is over, close the terminal window to shut down the server. Excel files are safely saved in the local `data/` directory next to the executable.

*End of Python/Executable plan. The agent should now begin with Phase 1 of Section 15 and work strictly in order.*