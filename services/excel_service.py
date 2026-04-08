from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import re
from typing import Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font

from core.config import settings

HEADERS = ["Roll Number", "Timestamp", "Session ID", "IP Address", "Present", "Classroom Code"]
course_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


async def get_next_worksheet_name(course_code: str) -> str:
    lock = course_locks[course_code]
    async with lock:
        return await asyncio.to_thread(_get_next_worksheet_name_sync, course_code)


def _get_next_worksheet_name_sync(course_code: str) -> str:
    file_path = _course_file_path(course_code)
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    pattern = re.compile(rf"^{re.escape(date_prefix)}_S(\d+)$")

    highest = 0
    if file_path.exists():
        workbook = load_workbook(file_path)
        for name in workbook.sheetnames:
            match = pattern.match(name)
            if match:
                highest = max(highest, int(match.group(1)))

    return f"{date_prefix}_S{highest + 1}"


def _course_file_path(course_code: str) -> Path:
    settings.excel_data_dir.mkdir(parents=True, exist_ok=True)
    return settings.excel_data_dir / f"{course_code}.xlsx"


def _setup_sheet(sheet) -> None:
    if sheet.max_row == 1 and sheet.max_column == 1 and sheet["A1"].value is None:
        sheet.delete_rows(1)
    sheet.append(HEADERS)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.freeze_panes = "A2"
    sheet.column_dimensions["A"].width = 18
    sheet.column_dimensions["B"].width = 28
    sheet.column_dimensions["C"].width = 40
    sheet.column_dimensions["D"].width = 18
    sheet.column_dimensions["E"].width = 10
    sheet.column_dimensions["F"].width = 18


async def initialize_worksheet(course_code: str, worksheet_name: str) -> None:
    lock = course_locks[course_code]
    async with lock:
        await asyncio.to_thread(_initialize_worksheet_sync, course_code, worksheet_name)


def _initialize_worksheet_sync(course_code: str, worksheet_name: str) -> None:
    file_path = _course_file_path(course_code)
    if file_path.exists():
        workbook = load_workbook(file_path)
    else:
        workbook = Workbook()

    if worksheet_name not in workbook.sheetnames:
        sheet = workbook.create_sheet(title=worksheet_name)
        _setup_sheet(sheet)

    if "Sheet" in workbook.sheetnames and len(workbook.sheetnames) > 1:
        default_sheet = workbook["Sheet"]
        if default_sheet.max_row == 1 and default_sheet["A1"].value is None:
            workbook.remove(default_sheet)

    workbook.save(file_path)


async def append_attendance_row(course_code: str, worksheet_name: str, row_data: Iterable) -> None:
    lock = course_locks[course_code]
    async with lock:
        await asyncio.to_thread(_append_attendance_row_sync, course_code, worksheet_name, list(row_data))


def _append_attendance_row_sync(course_code: str, worksheet_name: str, row_data: list) -> None:
    file_path = _course_file_path(course_code)
    if not file_path.exists():
        raise FileNotFoundError(f"Course workbook does not exist: {file_path}")

    workbook = load_workbook(file_path)
    if worksheet_name not in workbook.sheetnames:
        raise ValueError(f"Worksheet does not exist: {worksheet_name}")

    sheet = workbook[worksheet_name]
    sheet.append(row_data)
    workbook.save(file_path)

