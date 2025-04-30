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

import configparser
import logging
import os
import platform
import sys

from frame_checker.app.functions import get_xdg_config_dir, trim_log_file

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
os_name = platform.system()

# Fonts to load from assets
font_name = "SFProDisplay-Regular.otf"
monofont_name = "FiraCodeNerdFont-Medium.ttf"

# Define and create necessary directories
win = "Documents\\Frame Checker"
mac = "Documents/Frame Checker"
linux = "frame-checker"
linux_share = "/usr/share/frame-checker"
if os_name == "Windows":
    config_dir = os.path.abspath(os.path.join(get_xdg_config_dir(), win))
if os_name == "Darwin":
    config_dir = os.path.abspath(os.path.join(get_xdg_config_dir(), mac))
if os_name == "Linux":
    config_dir = os.path.abspath(os.path.join(get_xdg_config_dir(), linux))

logs_dir = os.path.abspath(os.path.join(config_dir, "logs"))
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Setup logger
logger = logging.getLogger()
app_log = os.path.join(logs_dir, "frame-checker.log")
trim_log_file(app_log) # trim log to 20000 lines if 10MB size is exceeded
log_handler = logging.FileHandler(app_log, mode="a", encoding="utf-8")
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
)
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)


class SettingsConfig:
    """Defines app default config, initializes settings.ini."""

    STYLESHEET = os.path.join(basedir, "..", "assets", "styles.qss")
    FONT = os.path.join(basedir, "..", "assets", font_name)
    MONOFONT = os.path.join(basedir, "..", "assets", monofont_name)
    ICON = os.path.join(basedir, "..", "resources", "icon.png")
    DEFAULT_SETTINGS = os.path.join(basedir, "default_settings.ini")
    SETTINGS_DIR = config_dir
    # Tested input extensions
    FILE_FILTER = "Video (*.mxf *.mov *.mp4 *.avi *.mkv *.m2ts *.webm \
    *.mpg *.mpeg *.3gp *.3g2 *.ogv *.ogg *.m2v *.m4v *.wmv)"
    FILETYPES = (
        ".mxf",
        ".mov",
        ".mp4",
        ".avi",
        ".mkv",
        ".m2ts",  # not tested
        ".webm",
        ".mpg",
        ".mpeg",
        ".3gp",
        ".3g2",  # not tested
        ".ogv",
        ".ogg",
        ".m2v",
        ".m4v",
        ".wmv",
    )

    # Windows and MacOS application is built with pyinstaller
    if os_name in ("Windows", "Darwin"):
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            STYLESHEET = os.path.join(sys._MEIPASS, "assets", "styles.qss")
            FONT = os.path.join(sys._MEIPASS, "assets", font_name)
            MONOFONT = os.path.join(sys._MEIPASS, "assets", monofont_name)
            ICON = os.path.join(sys._MEIPASS, "resources", "icon.ico")
            DEFAULT_SETTINGS = os.path.join(sys._MEIPASS, "default_settings.ini")

    # Update PATH on MacOS to include '/usr/local/bin' and '/opt/homebrew/bin'
    if os_name == "Darwin":
        # Default PATH where app will look for ffmpeg binaries on macos:
        # PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/homebrew/bin
        os.environ["PATH"] += (
            os.pathsep + "/usr/local/bin" + os.pathsep + "/opt/homebrew/bin"
        )

    # Linux application is not built with pyinstaller because of GLIBC errors
    if os_name == "Linux":
        if os.path.isfile(os.path.join(linux_share, "resources", "icon.png")):
            ICON = os.path.join(linux_share, "resources", "icon.png")
        if os.path.isdir(os.path.join(linux_share, "assets")):
            STYLESHEET = os.path.join(linux_share, "assets", "styles.qss")
            FONT = os.path.join(linux_share, "assets", font_name)
            MONOFONT = os.path.join(linux_share, "assets", monofont_name)

    def __init__(self):
        """Initialize configparser to read and/or generate settings.ini."""

        self.settings_file = os.path.join(self.SETTINGS_DIR, "settings.ini")
        self.settings = configparser.ConfigParser()
        try:
            self.settings.read(self.settings_file)
            if len(self.settings.sections()) == 0:
                self.default_settings()
        except FileNotFoundError as e:
            logger.error("Caught an error: %s", e, exc_info=True)
            self.default_settings()

        self.settings.read(self.settings_file)

    def default_settings(self):
        """Generates settings.ini from default_settings.ini."""

        self.settings.read(self.DEFAULT_SETTINGS)
        self.settings.set("app", "logdir", os.path.join(self.SETTINGS_DIR, "logs"))
        self.settings.set("app", "mediadir", get_xdg_config_dir())
        with open(self.settings_file, "w") as defaults:
            self.settings.write(defaults)

    def get_settings(self, section, key):
        """Gets value for key in config section."""

        return self.settings.get(section, key)

    def get_settings_section(self, section):
        """Gets all keys and values in a config section."""

        return self.settings[section]

    def update_settings(self, section, key, value):
        """Updates config value."""

        self.settings.set(section, key, value)
        with open(self.settings_file, "w") as f:
            self.settings.write(f)
