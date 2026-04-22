from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)

ROLL_HEADER = "RollNo."

# Per-course locks to prevent concurrent write races
_gsheets_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

# Cached gspread client
_gspread_client = None


def _get_client():
    """Get or create a gspread client using service account credentials."""
    global _gspread_client
    if _gspread_client is not None:
        return _gspread_client

    import gspread
    from google.oauth2.service_account import Credentials

    creds_path = settings.google_credentials_path
    if not creds_path:
        raise ValueError(
            "Google credentials path not configured. "
            "Set google_credentials_path in teacher configuration."
        )

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
    _gspread_client = gspread.authorize(credentials)
    return _gspread_client


def invalidate_client() -> None:
    """Force re-authentication on next call (e.g. after changing credentials path)."""
    global _gspread_client
    _gspread_client = None


def _get_spreadsheet(course_code: str):
    """Open the spreadsheet for a given course.

    Uses the google_spreadsheet_key from settings.
    If the key contains a comma-separated mapping like "CS301=abc123,MA101=def456",
    it looks up the course-specific spreadsheet. Otherwise uses a single key for all courses.
    """
    client = _get_client()
    key = settings.google_spreadsheet_key

    if not key:
        raise ValueError(
            "Google Spreadsheet key not configured. "
            "Set google_spreadsheet_key in teacher configuration."
        )

    # Support per-course mapping: "CS301=key1,MA101=key2"
    if "=" in key:
        mappings = {}
        for part in key.split(","):
            part = part.strip()
            if "=" in part:
                code, spreadsheet_id = part.split("=", 1)
                mappings[code.strip().upper()] = spreadsheet_id.strip()
        course_key = mappings.get(course_code.upper())
        if not course_key:
            raise ValueError(
                f"No Google Spreadsheet configured for course {course_code}. "
                f"Add {course_code}=SPREADSHEET_ID to google_spreadsheet_key."
            )
        return client.open_by_key(course_key)

    return client.open_by_key(key)


def _get_next_worksheet_name_sync(course_code: str) -> str:
    """Determine the next worksheet name for today's sessions."""
    import re

    date_prefix = datetime.now().strftime("%Y-%m-%d")
    pattern = re.compile(rf"^{re.escape(date_prefix)}_S(\d+)$")
    highest = 0

    try:
        spreadsheet = _get_spreadsheet(course_code)
        for ws in spreadsheet.worksheets():
            match = pattern.match(ws.title)
            if match:
                highest = max(highest, int(match.group(1)))
    except Exception as exc:
        logger.warning("Could not read existing worksheets from Google Sheets: %s", exc)

    return f"{date_prefix}_S{highest + 1}"


async def get_next_worksheet_name(course_code: str) -> str:
    lock = _gsheets_locks[course_code]
    async with lock:
        return await asyncio.to_thread(_get_next_worksheet_name_sync, course_code)


def _initialize_worksheet_sync(course_code: str, worksheet_name: str) -> None:
    """Create a worksheet in the Google Spreadsheet if it doesn't exist."""
    spreadsheet = _get_spreadsheet(course_code)

    # Check if worksheet already exists
    existing_titles = [ws.title for ws in spreadsheet.worksheets()]
    if worksheet_name in existing_titles:
        ws = spreadsheet.worksheet(worksheet_name)
    else:
        ws = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=26)

    # Ensure header row
    header = ws.row_values(1)
    if not header or header[0] != ROLL_HEADER:
        ws.update_cell(1, 1, ROLL_HEADER)
    # Bold header formatting
    ws.format("A1", {"textFormat": {"bold": True}})


async def initialize_worksheet(course_code: str, worksheet_name: str) -> None:
    lock = _gsheets_locks[course_code]
    async with lock:
        await asyncio.to_thread(_initialize_worksheet_sync, course_code, worksheet_name)


def _mark_attendance_sync(
    course_code: str,
    worksheet_name: str,
    roll_number: str,
    attendance_date: str,
    present: int,
) -> None:
    """Mark attendance in Google Sheets.

    Uses the same roll/date matrix format as the Excel service:
    - Column A: Roll numbers
    - Row 1: Headers (RollNo., date1, date2, ...)
    - Cell values: 1 for present, 0 for absent
    """
    spreadsheet = _get_spreadsheet(course_code)

    try:
        ws = spreadsheet.worksheet(worksheet_name)
    except Exception:
        raise ValueError(f"Worksheet does not exist: {worksheet_name}")

    # Get all values to work with
    all_values = ws.get_all_values()
    if not all_values:
        ws.update_cell(1, 1, ROLL_HEADER)
        all_values = [[ROLL_HEADER]]

    header_row = all_values[0]
    normalized_roll = roll_number.upper().strip()

    # Find or create date column
    date_col = None
    for col_idx, header in enumerate(header_row):
        if header == attendance_date:
            date_col = col_idx + 1  # 1-indexed
            break

    if date_col is None:
        date_col = len(header_row) + 1
        ws.update_cell(1, date_col, attendance_date)
        ws.format(
            f"{_col_letter(date_col)}1",
            {"textFormat": {"bold": True}},
        )
        # Fill existing rows with 0 for new date column
        if len(all_values) > 1:
            cells = []
            for row_idx in range(2, len(all_values) + 1):
                cells.append(gspread_cell(row_idx, date_col, 0))
            if cells:
                ws.update_cells(cells)

    # Find or create roll number row
    roll_row = None
    for row_idx, row in enumerate(all_values[1:], start=2):
        if row and row[0].upper().strip() == normalized_roll:
            roll_row = row_idx
            break

    if roll_row is None:
        roll_row = len(all_values) + 1
        ws.update_cell(roll_row, 1, normalized_roll)
        # Fill all date columns with 0 for new student
        current_header = ws.row_values(1)
        for col_idx in range(2, len(current_header) + 1):
            if col_idx != date_col:
                ws.update_cell(roll_row, col_idx, 0)

    # Set attendance value
    ws.update_cell(roll_row, date_col, 1 if present else 0)


def gspread_cell(row: int, col: int, value: Any):
    """Create a gspread Cell object for batch updates."""
    import gspread

    cell = gspread.Cell(row, col)
    cell.value = value
    return cell


def _col_letter(col_num: int) -> str:
    """Convert 1-indexed column number to letter (1=A, 2=B, 27=AA, etc.)."""
    result = ""
    while col_num > 0:
        col_num, remainder = divmod(col_num - 1, 26)
        result = chr(65 + remainder) + result
    return result


async def mark_attendance(
    course_code: str,
    worksheet_name: str,
    roll_number: str,
    attendance_date: str | None = None,
    present: int = 1,
) -> None:
    """Mark attendance for a student in Google Sheets.

    This function is thread-safe using per-course locks.

    Args:
        course_code: Course code (used to find spreadsheet)
        worksheet_name: Sheet name within spreadsheet
        roll_number: Student's roll number
        attendance_date: Date in YYYY-MM-DD format; defaults to today
        present: 1 for present, 0 for absent (default: 1)
    """
    lock = _gsheets_locks[course_code]
    async with lock:
        await asyncio.to_thread(
            _mark_attendance_sync,
            course_code,
            worksheet_name,
            roll_number,
            attendance_date or date.today().isoformat(),
            1 if present else 0,
        )
