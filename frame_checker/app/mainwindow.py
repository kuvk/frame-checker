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

import fnmatch
import os
import platform

from PySide6.QtCore import QThreadPool
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import QFileDialog, QWidget

from frame_checker.app.ffmpeg_worker import Worker
from frame_checker.app.functions import get_time
from frame_checker.app.ui_widget import Ui_Widget


class MainWindow(QWidget, Ui_Widget):
    """The main application window.

    This class represents the main window and user interface of the application,
    which inherits from PySide6's QMainWindow and :class:`app.ui_widget.Ui_Widget`
    generated from reading UI file 'widget.ui' created with Qt Designer 6.

    Methods:
        __init__(): Initialize the main window.
        set_user_options(): Sets default filters options from settings.ini.
        file_button_clicked(): Opens file dialog and saves selection.
        folder_button_clicked(): Opens directory dialog and saves selection.
        validate_input: Validates user input.
        validate_filters(checked): Validates if any of the filters are checked.
        add_filter_options(): Populates filters attribute with selected filters.
        update_status(status): Updates main window status log with status.
        clear_status(): Clears main window status log.
        save_status(): Opens dialog and saves status log to a text file.
        open_logs_dir(): Opens file manager in the logs directory.
        start_checker(): Starts worker in a threadpool.
        update_progress(p): Process worker progress signal to update progress bar value.
        proccess_status(s): Process worker status signal to update status log.
        cancel_checker(): Cancels worker.
        thread_complete(): Resets filters, worker and buttons.
    """

    def __init__(self, app_config):
        """Initialize the main window."""

        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Frame Checker")

        # Initialize SettingsConfig and set_user_options from settings.ini
        self.config = app_config
        self.set_user_options()

        # Icon
        self.setWindowIcon(QIcon(self.config.ICON))
        self.setProperty("class", "frame-checker")
        self.setWindowRole("frame-checker")

        # Connect file and folder buttons to open dialogs
        self.file_button.clicked.connect(self.file_button_clicked)
        self.folder_button.clicked.connect(self.folder_button_clicked)

        # Variable to hold files to check - files are added during validate_input
        self.files = []
        self.input_line_edit.textChanged.connect(self.validate_input)

        # Connect filter checkboxes to validation on toggle
        self.use_blackdetect.toggled.connect(self.validate_filters)
        self.use_freezedetect.toggled.connect(self.validate_filters)
        self.use_silencedetect.toggled.connect(self.validate_filters)

        # filters_chosen will be checked during start_checker, it is set to
        # True during validate_filters if any of the checkboxes are checked
        self.filters_chosen = False

        # Set filters to None, add_filter_options will be called
        # during start_checker if filters_chosen is True
        self.filters = {
            "blackdetect": None,
            "freezedetect": None,
            "silencedetect": None,
        }

        # Connect buttons to clear_status, save_status and open_logs_dir
        self.clear_status_button.clicked.connect(self.clear_status)
        self.save_status_button.clicked.connect(self.save_status)
        self.open_logs_button.clicked.connect(self.open_logs_dir)

        # Set worker to None, create threadpool and connect start button
        # to start_checker
        self.worker = None
        self.threadpool = QThreadPool()
        self.start_button.clicked.connect(self.start_checker)

        # Hide cancel button and connect to cancel_checker
        self.cancel_button.hide()
        self.cancel_button.clicked.connect(self.cancel_checker)

        # Inital status
        self.update_status("Ready.")

    # Set user default options
    def set_user_options(self):
        """Sets deafult filters options from settings.ini."""

        self.black_duration.setValue(
            float(self.config.get_settings("blackdetect", "duration"))
        )
        self.pic_th.setValue(float(self.config.get_settings("blackdetect", "pic_th")))
        self.pix_th.setValue(float(self.config.get_settings("blackdetect", "pix_th")))
        self.freeze_noise.setValue(
            int(self.config.get_settings("freezedetect", "noise"))
        )
        self.freeze_duration.setValue(
            float(self.config.get_settings("freezedetect", "duration"))
        )
        self.silence_noise.setValue(
            int(self.config.get_settings("silencedetect", "noise"))
        )
        self.silence_duration.setValue(
            float(self.config.get_settings("silencedetect", "duration"))
        )
        self.enable_mono.setChecked(
            True
            if self.config.get_settings("silencedetect", "mono").lower() == "true"
            else False
        )

    # User choose file as input
    def file_button_clicked(self):
        """Opens file dialog and saves selection as input.

        Triggered on file_button clicked signal.
        """
        mediadir = self.config.get_settings("app", "mediadir")
        if not os.path.isdir(mediadir):
            self.update_status(
                f"Invalid entry for mediadir in settings.ini: {mediadir}"
            )
            self.update_status("Add valid path and restart Frame Checker.")

        dialog = QFileDialog()
        dialog.setDirectory(mediadir)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilter(self.config.FILE_FILTER)

        dialog.setViewMode(QFileDialog.ViewMode.List)
        if dialog.exec():
            filename = dialog.selectedFiles()[0]
            self.input_line_edit.setText(os.path.normpath(filename))

    # User chose folder as input
    def folder_button_clicked(self):
        """Opens directory dialog and saves selection as input.

        Triggered on folder_button clicked signal.
        """
        mediadir = self.config.get_settings("app", "mediadir")
        if not os.path.isdir(mediadir):
            self.update_status(
                f"Invalid entry for mediadir in settings.ini: {mediadir}"
            )
            self.update_status("Add valid path and restart Frame Checker.")
        dialog = QFileDialog()
        dialog.setDirectory(mediadir)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOptions(QFileDialog.Option.ShowDirsOnly)

        if dialog.exec():
            directory = dialog.selectedFiles()[0]
            self.input_line_edit.setText(os.path.normpath(directory))

    # Validate user input
    def validate_input(self):
        """Validates user input.

        Checks file or all files in a directory against supported file extensions
        and updates status log to inform user if file/s can be checked.

        Triggered on input_line_edit textChanged signal.
        """
        path = self.input_line_edit.text()
        # File
        if os.path.isfile(path):
            file = os.path.basename(path)
            if file.lower().endswith(self.config.FILETYPES):
                self.update_status(f'File "{file}" can be checked.')
                self.files = [file]
            else:
                self.update_status(f'Invalid input. "{file}" cannot be checked.')
                self.files = []

        # Folder
        if os.path.isdir(path):
            self.files = []
            for ext in self.config.FILETYPES:
                self.files += fnmatch.filter(os.listdir(path), f"*{ext}")
            if self.files:
                self.update_status(f"{len(self.files)} files can be checked. ")
            else:
                self.update_status("No files to check in this folder.")

    # Filters toggled
    def validate_filters(self, checked: bool):
        """Validates if any of the filters are checked.

        Checks if any of the filter checkboxes are checked and changes filters_chosen
        value to True or False.

        Triggered if any of the filters checkboxes are toggled.
        """
        if checked:
            self.filters_chosen = True
        elif (
            not self.use_blackdetect.isChecked()
            and not self.use_freezedetect.isChecked()
            and not self.use_silencedetect.isChecked()
        ):
            self.filters_chosen = False

    # Add filter options if user checked filter checkbox
    def add_filter_options(self):
        """Populates filters attribute with selected filters.

        Populates filters dictionary with lists of options (int or float) for
        each filter that user checked.

        Called during :func:`start_checker`.
        """
        if self.use_blackdetect.isChecked():
            self.filters["blackdetect"] = [
                self.black_duration.value(),
                self.pic_th.value(),
                self.pix_th.value(),
            ]
        else:
            self.filters["blackdetect"] = None

        if self.use_freezedetect.isChecked():
            self.filters["freezedetect"] = [
                self.freeze_noise.value(),
                self.freeze_duration.value(),
            ]
        else:
            self.filters["freezedetect"] = None

        if self.use_silencedetect.isChecked():
            self.filters["silencedetect"] = [
                self.silence_noise.value(),
                self.silence_duration.value(),
                self.enable_mono.isChecked(),
            ]
        else:
            self.filters["silencedetect"] = None

    # Update status log
    def update_status(self, status: str) -> None:
        """Updates status log with status."""
        self.status.moveCursor(QTextCursor.MoveOperation.End)
        self.status.append(f"{get_time()} => {status}")
        self.status.moveCursor(QTextCursor.MoveOperation.End)
        self.status.moveCursor(QTextCursor.MoveOperation.NextRow)
        self.status.moveCursor(QTextCursor.MoveOperation.StartOfLine)

    # Clear status log
    def clear_status(self) -> None:
        """Clears status log."""
        self.status.clear()
        if self.progress.value() == 100:
            self.progress.setValue(0)

    # Save status log
    def save_status(self) -> None:
        """Opens dialog and saves status log to a text file."""

        home = os.path.expanduser("~")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            home,
            "Text Files (*.txt);",
        )
        if filename:
            if not filename.endswith(".txt"):
                filename = filename + ".txt"
            with open(filename, "w") as o:
                o.write(self.status.toPlainText())

    # Open logs directory
    def open_logs_dir(self) -> None:
        """Opens system file manager in the logs directory.

        Uses os.startfile which will open explorer on Windows.
        Uses open command to open Finder on MacOs.
        Uses xdg-open command to open default file manager for Linux.

        Note: Linux command dependens on xdg-utils package.
        """

        logdir = os.path.abspath(self.config.get_settings("app", "logdir"))
        if os.path.isdir(logdir):
            if platform.system() == "Windows":
                os.startfile(logdir)  # type: ignore
            elif platform.system() == "Darwin":
                os.system(f'open "{logdir}"')
            elif platform.system() == "Linux":
                os.system(f"xdg-open {logdir} > /dev/null 2>&1 &")
        else:
            self.update_status(f"Invalid entry for logdir in setting.ini: {logdir}")
            self.update_status("Add valid path and restart Frame Checker.")

    # Start checker
    def start_checker(self) -> None:
        """Starts worker in a threadpool.

        Checks if conditions are met to start the Worker, updates buttons,
        calls :func:`add_filter_options` to add selected filters options,
        connects Worker signals and starts Worker in a threadpool.

        If conditions to start are not met informs the user with status log update.

        See also: :class:`app.ffmpeg_worker.Worker`
        """

        # Update status to inform user if no files or filters are selected
        if not self.files:
            return self.update_status("Invalid input. Cannot start checker.")
        if not self.filters_chosen:
            return self.update_status("No filters selected. Cannot start checker.")

        self.update_status("Starting checker ...")

        # Enable cancel button and disable others
        self.start_button.setEnabled(False)
        self.start_button.hide()
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        self.clear_status_button.setEnabled(False)
        self.save_status_button.setEnabled(False)
        self.file_button.setEnabled(False)
        self.folder_button.setEnabled(False)

        # Directory containing files
        if os.path.isdir(self.input_line_edit.text()):
            directory = self.input_line_edit.text()
        else:
            directory = os.path.dirname(self.input_line_edit.text())

        # Add filter options and create worker
        self.add_filter_options()
        self.worker = Worker(
            self.files,
            self.filters,
            directory,
            self.config.get_settings("app", "logdir"),
        )

        # Connect status, progress and finished signals
        self.worker.signals.status.connect(self.proccess_status)
        self.worker.signals.finished.connect(self.thread_complete)
        self.worker.signals.progress.connect(self.update_progress)

        # Start worker
        self.threadpool.start(self.worker)

    # Update progress from worker signals
    def update_progress(self, p: int) -> None:
        """Process worker progress signal to update progress bar value.

        Triggered by :class:`app.ffmpeg_worker.Worker` emmiting progress signal.
        """

        self.progress.setValue(p)

    # Update status log from worker signals
    def proccess_status(self, s: str) -> None:
        """Process worker status signal to update status log.

        Triggered by :class:`app.ffmpeg_worker.Worker` emmiting status signal.
        """

        self.update_status(s)

    # Cancel checker
    def cancel_checker(self) -> None:
        """Cancels worker.

        Changes Worker canceled attribute to True, which enables Worker to break
        out of run method before it finishes.
        """

        self.worker.canceled = True
        self.cancel_button.setEnabled(False)

    # Worker finished
    def thread_complete(self) -> None:
        """Resets filters, worker and buttons."""

        self.filters["silencedetect"] = None
        self.filters["freezedetect"] = None
        self.filters["blackdetect"] = None

        self.worker = None
        self.cancel_button.hide()
        self.start_button.setEnabled(True)
        self.start_button.show()
        self.clear_status_button.setEnabled(True)
        self.save_status_button.setEnabled(True)
        self.file_button.setEnabled(True)
        self.folder_button.setEnabled(True)
