# PLAN Status Checklist

This file tracks implementation progress against `Docs/PLAN.md`.

## Phase 1 - Scaffold
- [x] Folder structure created
- [x] `requirements.txt` added
- [x] `.env`, `.env.example`, `config/courses.json` created
- [x] PyInstaller-aware path logic in `core/config.py`

## Phase 2 - Excel Service
- [x] `services/excel_service.py` implemented with `asyncio.Lock` per course
- [x] Blocking Excel writes moved to `asyncio.to_thread(...)`
- [x] Temporary `test_excel.py` executed and removed

## Phase 3 - Session Manager
- [x] `services/session_manager.py` implemented with token rotation task
- [x] Temporary `test_session.py` executed and removed

## Phase 4 - QR Generator
- [x] `services/qr_generator.py` implemented

## Phase 5 - API Routes and FastAPI
- [x] `routers/teacher.py` implemented
- [x] `routers/student.py` implemented
- [x] `main.py` entrypoint implemented

## Phase 6 - Frontend
- [x] `public/teacher/index.html`
- [x] `public/teacher/dashboard.html`
- [x] `public/student/scan.html`
- [x] `public/student/result.html`

## Phase 7 - Standalone Compilation
- [x] `build.py` implemented
- [x] Linux binary build verified locally
- [x] Binary tested from isolated folder with local `.env` and `config/courses.json`
- [x] Cross-platform packaging workflow added (`.github/workflows/package-all-os.yml`)

## Phase 8 - End-to-End and Polish
- [x] Concurrency write harness added (`phase8_concurrency_test.py`)
- [x] Logging improved in API/session lifecycle paths
- [ ] Manual browser testing (teacher + student full loop)
- [ ] Manual classroom-LAN validation

## Next action
- Run manual test checklist, then create base commit of current working state.

