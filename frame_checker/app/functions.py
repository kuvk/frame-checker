# Frame Checker - A tool for checking video frames using ffmpeg filters.
# Copyright (C) 2025 Vuk Knežević
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import shutil
import sys
import time


def ffmpeg_binaries() -> tuple | None:
    """Gets system available ffmpeg binaries.

    Gets binaries that may have been bundled with pyinstaller, in case they are
    not available on the system.(Not used, since I do not include ffmpeg binaries)

    Returns:
        tuple | None: Tuple of strings representing ffmpeg and ffprobe binaries.

    Example: ("/usr/bin/ffmpeg", "/usr/bin/ffprobe")
    """

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        ffmpeg = os.path.join(sys._MEIPASS, "ffmpeg")
        ffprobe = os.path.join(sys._MEIPASS, "ffprobe")
        if os.path.exists(ffmpeg) and os.path.exists(ffprobe):
            return ffmpeg, ffprobe

    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return shutil.which("ffmpeg"), shutil.which("ffprobe")

    return None


def load_stylesheet(app, styles: str, font_family: str, monofont_family: str) -> None:
    """Loads the QSS stylesheet for QApplication with modified font placeholders.

    Excpects stylesheet to have placeholders ("Custom Font" and "Custom Mono Font")
    for font-family values and replaces them with font_family and monofont_family.

    Args:
        app (class): QApplication instance to load stylesheet for.
        styles (str): String specifying path to stylesheet. 
        font_family (str): String specifying font family to replace "Custom Font".
        monofont_family (str): String specifying font family to replace "Custom Mono Font".

    Example: 
        {font-family: "Custom Font";} => {font-family: "SF Pro Display"}
        {font-family: "Custom Mono Font";} => {font-family: "FiraCode Nerd Font"}
    """
    with open(styles, "r") as f:
        stylesheet = f.read()
        if font_family:
            stylesheet = stylesheet.replace("Custom Font", font_family)
        if monofont_family:
            stylesheet = stylesheet.replace("Custom Mono Font", monofont_family)
        app.setStyleSheet(stylesheet)


def convert_seconds(sec: float, fps: float) -> str:
    """Convert seconds to SMPTE timecode (hour:minute:second:frame).

    Args:
        sec (float): Float to specify total number of seconds.
        fps (float): Float to specify frame rate.

    Returns:
        str: String representing converted seconds in SMPTE timecode.

        Example: "00:52:12:11"
    """

    hours = int(sec / 3600)
    if hours >= 1:
        sec = sec % 3600
    minutes = int(sec / 60)
    if minutes >= 1:
        sec = sec % 60
    seconds = int(sec)
    if seconds >= 1:
        sec = sec % 1
    frames = round(sec * fps)

    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"


def get_time() -> str:
    """Returns formatted current date and time as a string.

    Example: "[2024-11-27 15:53:06]"
    """
    return time.strftime("[%Y-%m-%d %H:%M:%S]")


def get_xdg_config_dir():
    """Returns user XDG_CONFIG_HOME directory or user home directory."""
    return os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~")


def trim_log_file(filepath, max_size=10 * 1024 * 1024, keep_last_n_lines=20_000):
    """Trims the log file to the last N lines if it exceeds max_size bytes."""
    if not os.path.isfile(filepath):
        return

    if os.path.getsize(filepath) <= max_size:
        return

    try:
        with open(filepath, 'rb') as f:
            # Read from the end, going backward
            f.seek(-min(max_size, os.path.getsize(filepath)), os.SEEK_END)
            data = f.read().decode("utf-8", errors="ignore")

        # Get last N lines
        lines = data.splitlines()[-keep_last_n_lines:]

        # Overwrite the file with trimmed lines
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("Log trimmed due to size limit.\n")
            f.write('\n'.join(lines) + '\n')

    except Exception as e:
        return
