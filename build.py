from __future__ import annotations

import platform

import PyInstaller.__main__

os_name = platform.system().lower()
data_sep = ";" if os_name == "windows" else ":"

PyInstaller.__main__.run(
    [
        "main.py",
        "--name=AttendanceSystem",
        "--onefile",
        f"--add-data=public{data_sep}public",
        f"--add-data=config{data_sep}config",
        "--clean",
        "--noconfirm",
    ]
)
