"""Storage backend factory — routes calls to Excel, Google Sheets, or both."""
from __future__ import annotations

import logging
from typing import Any, Protocol

from core.config import settings

logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    """Common interface that both Excel and Google Sheets services implement."""

    async def get_next_worksheet_name(self, course_code: str) -> str: ...
    async def initialize_worksheet(self, course_code: str, worksheet_name: str) -> None: ...
    async def mark_attendance(
        self,
        course_code: str,
        worksheet_name: str,
        roll_number: str,
        attendance_date: str | None = None,
        present: int = 1,
    ) -> None: ...


class ExcelBackend:
    """Wraps the excel_service module as a StorageBackend."""

    async def get_next_worksheet_name(self, course_code: str) -> str:
        from services.excel_service import get_next_worksheet_name
        return await get_next_worksheet_name(course_code)

    async def initialize_worksheet(self, course_code: str, worksheet_name: str) -> None:
        from services.excel_service import initialize_worksheet
        await initialize_worksheet(course_code, worksheet_name)

    async def mark_attendance(
        self,
        course_code: str,
        worksheet_name: str,
        roll_number: str,
        attendance_date: str | None = None,
        present: int = 1,
    ) -> None:
        from services.excel_service import mark_attendance
        await mark_attendance(course_code, worksheet_name, roll_number, attendance_date, present)


class GoogleSheetsBackend:
    """Wraps the google_sheets_service module as a StorageBackend."""

    async def get_next_worksheet_name(self, course_code: str) -> str:
        from services.google_sheets_service import get_next_worksheet_name
        return await get_next_worksheet_name(course_code)

    async def initialize_worksheet(self, course_code: str, worksheet_name: str) -> None:
        from services.google_sheets_service import initialize_worksheet
        await initialize_worksheet(course_code, worksheet_name)

    async def mark_attendance(
        self,
        course_code: str,
        worksheet_name: str,
        roll_number: str,
        attendance_date: str | None = None,
        present: int = 1,
    ) -> None:
        from services.google_sheets_service import mark_attendance
        await mark_attendance(course_code, worksheet_name, roll_number, attendance_date, present)


class DualBackend:
    """Writes to both Excel and Google Sheets. Reads worksheet names from Excel."""

    def __init__(self) -> None:
        self._excel = ExcelBackend()
        self._gsheets = GoogleSheetsBackend()

    async def get_next_worksheet_name(self, course_code: str) -> str:
        return await self._excel.get_next_worksheet_name(course_code)

    async def initialize_worksheet(self, course_code: str, worksheet_name: str) -> None:
        await self._excel.initialize_worksheet(course_code, worksheet_name)
        try:
            await self._gsheets.initialize_worksheet(course_code, worksheet_name)
        except Exception as exc:
            logger.error("Google Sheets initialize_worksheet failed (Excel succeeded): %s", exc)

    async def mark_attendance(
        self,
        course_code: str,
        worksheet_name: str,
        roll_number: str,
        attendance_date: str | None = None,
        present: int = 1,
    ) -> None:
        await self._excel.mark_attendance(course_code, worksheet_name, roll_number, attendance_date, present)
        try:
            await self._gsheets.mark_attendance(course_code, worksheet_name, roll_number, attendance_date, present)
        except Exception as exc:
            logger.error("Google Sheets mark_attendance failed (Excel succeeded): %s", exc)


# Cached backend instances
_backends: dict[str, Any] = {}


def get_storage() -> StorageBackend:
    """Return the storage backend based on the current settings.storage_backend value."""
    backend_type = settings.storage_backend

    if backend_type not in _backends:
        if backend_type == "google_sheets":
            _backends[backend_type] = GoogleSheetsBackend()
        elif backend_type == "both":
            _backends[backend_type] = DualBackend()
        else:  # default to "excel"
            _backends[backend_type] = ExcelBackend()

    return _backends[backend_type]


def invalidate_cache() -> None:
    """Clear cached backend instances (e.g. after settings change)."""
    _backends.clear()
