from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from core.config import get_public_dir, get_runtime_base_url, load_courses, settings
from routers.student import router as student_router
from routers.teacher import router as teacher_router


class _ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[35m",
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"


def _configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    handler.setFormatter(_ColorFormatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))

    root.handlers.clear()
    root.addHandler(handler)


_configure_logging()
logger = logging.getLogger(__name__)


async def _startup() -> None:
    """Application startup handler."""
    try:
        settings.excel_data_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.error("Failed to create excel data directory: %s", exc)
        raise

    try:
        courses = load_courses()
    except Exception as exc:
        logger.warning("Failed to load courses: %s", exc)
        courses = []

    try:
        runtime_base_url = get_runtime_base_url()
    except Exception as exc:
        logger.warning("Failed to determine runtime base URL: %s", exc)
        runtime_base_url = settings.base_url

    local_base_url = f"http://localhost:{settings.port}"
    logger.info("=" * 64)
    logger.info("Classroom Attendance System")
    logger.info("Teacher UI (local): %s/teacher", local_base_url)
    logger.info("Teacher UI (network): %s/teacher", runtime_base_url)
    logger.info("Student URL base: %s/attend", runtime_base_url)
    logger.info("Courses loaded: %s", len(courses))
    logger.info("Excel data dir: %s", settings.excel_data_dir)
    logger.info("=" * 64)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Manage application lifespan (startup/shutdown)."""
    await _startup()
    yield


app = FastAPI(title="Classroom Attendance System", lifespan=lifespan)
app.include_router(teacher_router)
app.include_router(student_router)
app.mount("/static", StaticFiles(directory=get_public_dir()), name="static")


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/teacher")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "3000")), log_level="warning")
