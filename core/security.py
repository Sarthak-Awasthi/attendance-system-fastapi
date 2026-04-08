from __future__ import annotations

import hmac

from core.config import settings


def is_teacher_secret_valid(secret: str) -> bool:
    expected = settings.teacher_secret or ""
    provided = secret or ""
    return bool(expected) and hmac.compare_digest(provided, expected)

