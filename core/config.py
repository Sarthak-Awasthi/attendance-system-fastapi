from __future__ import annotations

import json
import os
import socket
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_user_data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env_path = get_user_data_dir() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()


_load_env()


@dataclass
class Settings:
    port: int
    teacher_secret: str
    allow_student_dev_mode: bool
    qr_rotate_interval_sec: int
    token_grace_period_sec: int
    default_session_duration_minutes: int
    base_url: str
    excel_data_dir: Path
    storage_backend: str  # "excel", "google_sheets", or "both"
    google_credentials_path: str
    google_spreadsheet_key: str


def get_user_config_dir() -> Path:
    return get_user_data_dir() / "config"


def get_user_courses_config_path() -> Path:
    return get_user_config_dir() / "courses.json"


def get_app_settings_path() -> Path:
    return get_user_config_dir() / "app_settings.json"


def _load_app_settings_overrides() -> dict[str, Any]:
    app_settings_path = get_app_settings_path()
    if not app_settings_path.exists():
        return {}
    try:
        with app_settings_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError, UnicodeDecodeError) as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to load app settings: %s", exc)
        return {}


def _resolve_excel_data_dir(value: str | None) -> Path:
    raw = value if value is not None else os.getenv("EXCEL_DATA_DIR", "./data")
    path = Path(raw)
    if not path.is_absolute():
        path = get_user_data_dir() / path
    return path.resolve()


def _build_settings() -> Settings:
    overrides = _load_app_settings_overrides()

    # Validate and parse PORT
    port = int(os.getenv("PORT", "3000"))
    if not (1 <= port <= 65535):
        raise ValueError(f"PORT must be between 1 and 65535, got {port}")

    # Validate and parse QR_ROTATE_INTERVAL_SEC
    qr_rotate = int(overrides.get("qr_rotate_interval_sec", os.getenv("QR_ROTATE_INTERVAL_SEC", "5")))
    if not (1 <= qr_rotate <= 120):
        raise ValueError(f"QR_ROTATE_INTERVAL_SEC must be between 1 and 120, got {qr_rotate}")

    # Validate and parse TOKEN_GRACE_PERIOD_SEC
    grace_period = int(overrides.get("token_grace_period_sec", os.getenv("TOKEN_GRACE_PERIOD_SEC", "30")))
    if not (5 <= grace_period <= 120):
        raise ValueError(f"TOKEN_GRACE_PERIOD_SEC must be between 5 and 120, got {grace_period}")

    # Validate and parse DEFAULT_SESSION_DURATION_MINUTES
    session_duration = int(overrides.get("default_session_duration_minutes", os.getenv("DEFAULT_SESSION_DURATION_MINUTES", "10")))
    if not (1 <= session_duration <= 360):
        raise ValueError(f"DEFAULT_SESSION_DURATION_MINUTES must be between 1 and 360, got {session_duration}")

    return Settings(
        port=port,
        teacher_secret=str(overrides.get("teacher_secret", os.getenv("TEACHER_SECRET", ""))),
        allow_student_dev_mode=bool(overrides.get("allow_student_dev_mode", False)),
        qr_rotate_interval_sec=qr_rotate,
        token_grace_period_sec=grace_period,
        default_session_duration_minutes=session_duration,
        base_url=str(overrides.get("base_url", os.getenv("BASE_URL", "http://127.0.0.1:3000"))).rstrip("/"),
        excel_data_dir=_resolve_excel_data_dir(overrides.get("excel_data_dir")),
        storage_backend=str(overrides.get("storage_backend", os.getenv("STORAGE_BACKEND", "excel"))),
        google_credentials_path=str(overrides.get("google_credentials_path", os.getenv("GOOGLE_CREDENTIALS_PATH", ""))),
        google_spreadsheet_key=str(overrides.get("google_spreadsheet_key", os.getenv("GOOGLE_SPREADSHEET_KEY", ""))),
    )


settings = _build_settings()


def refresh_runtime_settings() -> Settings:
    fresh = _build_settings()
    settings.port = fresh.port
    settings.teacher_secret = fresh.teacher_secret
    settings.allow_student_dev_mode = fresh.allow_student_dev_mode
    settings.qr_rotate_interval_sec = fresh.qr_rotate_interval_sec
    settings.token_grace_period_sec = fresh.token_grace_period_sec
    settings.default_session_duration_minutes = fresh.default_session_duration_minutes
    settings.base_url = fresh.base_url
    settings.excel_data_dir = fresh.excel_data_dir
    settings.storage_backend = fresh.storage_backend
    settings.google_credentials_path = fresh.google_credentials_path
    settings.google_spreadsheet_key = fresh.google_spreadsheet_key
    return settings


def get_public_dir() -> Path:
    return get_base_dir() / "public"


def get_courses_config_path() -> Path:
    user_path = get_user_courses_config_path()
    if user_path.exists():
        return user_path
    return get_base_dir() / "config" / "courses.json"


def load_courses() -> list[dict[str, Any]]:
    courses_path = get_courses_config_path()
    if not courses_path.exists():
        return []
    try:
        with courses_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, IOError, UnicodeDecodeError) as exc:
        import logging
        logging.getLogger(__name__).warning("Failed to load courses: %s", exc)
        return []


def _detect_lan_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packets are sent; this asks OS routing for the outbound interface address.
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def get_runtime_base_url() -> str:
    parsed = urlparse(settings.base_url)
    host = parsed.hostname or ""
    if host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
        return settings.base_url

    lan_ip = _detect_lan_ip()
    port = parsed.port or settings.port
    scheme = parsed.scheme or "http"
    return f"{scheme}://{lan_ip}:{port}"
