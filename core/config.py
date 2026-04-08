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


@dataclass(frozen=True)
class Settings:
    port: int
    teacher_secret: str
    qr_rotate_interval_sec: int
    default_session_duration_minutes: int
    base_url: str
    excel_data_dir: Path


settings = Settings(
    port=int(os.getenv("PORT", "3000")),
    teacher_secret=os.getenv("TEACHER_SECRET", ""),
    qr_rotate_interval_sec=int(os.getenv("QR_ROTATE_INTERVAL_SEC", "5")),
    default_session_duration_minutes=int(os.getenv("DEFAULT_SESSION_DURATION_MINUTES", "10")),
    base_url=os.getenv("BASE_URL", "http://127.0.0.1:3000").rstrip("/"),
    excel_data_dir=(get_user_data_dir() / os.getenv("EXCEL_DATA_DIR", "./data")).resolve(),
)


def get_public_dir() -> Path:
    return get_base_dir() / "public"


def get_courses_config_path() -> Path:
    user_path = get_user_data_dir() / "config" / "courses.json"
    if user_path.exists():
        return user_path
    return get_base_dir() / "config" / "courses.json"


def load_courses() -> list[dict[str, Any]]:
    courses_path = get_courses_config_path()
    if not courses_path.exists():
        return []
    with courses_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, list) else []


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
