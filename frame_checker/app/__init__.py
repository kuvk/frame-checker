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

import platform
import socket
import sys
import traceback

import qtmodern.styles
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication

from frame_checker.app.functions import load_stylesheet
from frame_checker.app.mainwindow import MainWindow
from frame_checker.config import SettingsConfig, logger


class SingleInstanceSocket:
    """Single instance lock mechanism for application.

    Binds application to port 57389 on localhost to prevent opening another
    application instance.
    """

    def __init__(self, host="127.0.0.1", port=57389):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __enter__(self):
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen(1)
            logger.info("Frame Checker startup")
            logger.info(f"Single instance lock on {self.host}:{self.port}")
            return self
        except socket.error:
            logger.info("Another instance of Frame Checker is already running")
            sys.exit(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            error_msg = "".join(
                traceback.format_exception(exc_type, exc_val, exc_tb)
            ).rstrip()
            logger.error("Exception occurred:\n%s", error_msg)
        logger.info("Frame Checker shutdown")
        logger.info(f"Single instance lock removed {self.host}:{self.port}")
        self.sock.close()


def create_app():
    """Function to create application. Returns application and mainwindow.

    For more on theme source, see here: https://github.com/gmarull/qtmodern
    """

    app = QApplication(sys.argv)
    app_config = SettingsConfig()
    app.setApplicationName("Frame Checker")
    app.setApplicationDisplayName("Frame Checker")
    app.setWindowIcon(QIcon(app_config.ICON))

    # Set theme - default dark
    if app_config.get_settings("app", "theme").lower() == "light":
        qtmodern.styles.light(app)
    else:
        qtmodern.styles.dark(app)

    # Load custom font for Linux and MacOS
    font_id = QFontDatabase.addApplicationFont(app_config.FONT)
    monofont_id = QFontDatabase.addApplicationFont(app_config.MONOFONT)

    # Font
    font_family = "Tahoma"  # Windows
    if font_id != -1 and platform.system() in ("Linux", "Darwin"):
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

    # Mono Font
    monofont_family = None # Windows - should load FiraCode Nerd Font
    if monofont_id != -1:
        monofont_family = QFontDatabase.applicationFontFamilies(monofont_id)[0]

    load_stylesheet(app, app_config.STYLESHEET, font_family, monofont_family)

    mainwindow = MainWindow(app_config)
    return app, mainwindow
