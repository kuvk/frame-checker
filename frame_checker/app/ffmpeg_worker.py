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
import platform
import re
import subprocess
import time

import ffmpeg_progress_yield as fpy
from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from tabulate import tabulate

from frame_checker.app.functions import convert_seconds, ffmpeg_binaries
from frame_checker.config import app_log, logger

# Regular expressions for blackdetect, freezedetect and silencedetect.
BLACK_REG = r"^.+blackdetect.+black_start:(\d+\.?\d*) black_end:(\d+\.?\d*) black_duration:(\d+\.?\d*)$"
FSTART_REG = r"^.+freezedetect.+lavfi.freezedetect.freeze_start: (\d+\.?\d*).*$"
FDURATION_REG = r"^.+freezedetect.+lavfi.freezedetect.freeze_duration: (\d+\.?\d*).*$"
FEND_REG = r"^.+freezedetect.+lavfi.freezedetect.freeze_end: (\d+\.?\d*).*$"
SSTART_REG = r"^.+silencedetect.+silence_start: -?(\d+\.?\d*).*$"
SDUREND_REG = (
    r"^.+silencedetect.+silence_end: (\d+\.?\d*).+silence_duration: (\d+\.?\d*).*$"
)


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread.

    Signals:
        finished: No data
        status (str): string returned from processing
        progress (int): int indicating % progress

    See also:
        :class:`Worker`
        :func:`app.mainwindow.MainWindow.start_checker`
        :func:`app.mainwindow.MainWindow.thread_complete`
        :func:`app.mainwindow.MainWindow.proccess_status`
        :func:`app.mainwindow.MainWindow.update_progress`

    """

    finished = Signal()
    status = Signal(str)
    progress = Signal(int)


class Worker(QRunnable):
    """Worker thread that runs ffmpeg commands.

    Inherits from QRunnable and is designed to be executed in a threadpool, during
    :func:`app.mainwindow.MainWindow.start_checker`. It provides a way to collect
    metadata, run ffmpeg commands, process output and create a log file in a
    non-blocking manner, preventing the GUI from freezing.

    Attributes:
        files (list[str]): List of files to be passed to ffprobe and ffmpeg command.
        filters (dict[str: list]): Dictionary with string keys representing filters and
        lists of ints and floats as values or None representing filter options to be
        used.
        directory (str): String to specify files parent directory.
        log_directory (str): String to specify directory where log files will be saved.
        signals (class): :class:`WorkerSignals` for inter-thread communication.
        canceled (bool): Boolean to cancel Worker.
        ffmpeg_binaries (tuple): Tuple to specify ffmpeg and ffprobe binaries.

    Methods:
        __init__(files, filters, directory, log_directory): Initialize Worker.
        run(): Runs ffmpeg and processes output.
        get_metadata(file): Retrieves input metadata via ffprobe.
        ffmpeg_build_command(file): Builds ffmpeg command.
        parse_ffmpeg_result(result, fps): Parses ffmpeg output for detections.
        create_log(file, detections, metadata): Creates a log file.

    See also: :class:`app.mainwindow.MainWindow`
    """

    def __init__(self, files: list, filters: dict, directory: str, log_directory):
        """Initialize Worker."""
        super(Worker, self).__init__()
        self.files = files
        self.filters = filters
        self.directory = directory
        self.log_directory = log_directory
        self.signals = WorkerSignals()
        self.canceled = False
        self.ffmpeg_binaries = ffmpeg_binaries()

    @Slot()
    def run(self):
        """Runs ffmpeg and processes output.

        Collects metadata, builds ffmpeg command with filters, runs ffmpeg
        while capturing progress using ffmpeg-progress-yield, parses the result
        and creates a log file.

        Emits status, progress and finished signals.

        See also: :func:`ffmpeg_progress_yield.FfmpegProgress.run_command_with_progress`
        More on ffmpeg-progress-yield: https://github.com/slhck/ffmpeg-progress-yield
        """

        # In case ffmpeg binaries are not available on the system
        if not self.ffmpeg_binaries:
            self.signals.status.emit("ffmpeg binaries unavailable. Aborting ...")
            self.signals.status.emit(
                "Please install ffmpeg and add to PATH before trying again."
            )
            return self.signals.finished.emit()
        else:
            ffmpeg, ffprobe = self.ffmpeg_binaries

        # Define variables to help calculate total progress
        total_files = len(self.files)
        progress = 0

        for index, file in enumerate(self.files):
            self.signals.status.emit(f'Checking file: "{file}"')

            try:
                # Collect metadata
                self.signals.status.emit("Retrieving metadata ...")
                metadata = self.get_metadata(file, ffprobe)

                # Build ffmpeg command of media input
                self.signals.status.emit("Running ffmpeg ...")
                cmd = self.ffmpeg_build_command(file, ffmpeg)

                # Use ffmpeg-progress-yeild for running ffmpeg command
                ff = fpy.FfmpegProgress(cmd)

                # Without creationflags Windows opens terminal during subprocess
                args = {"shell": False}
                if platform.system() == "Windows":
                    args["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore

                # Run ffmpeg with progress
                for input_progress in ff.run_command_with_progress(args):
                    # User canceled
                    if self.canceled:
                        ff.quit_gracefully()
                        self.signals.progress.emit(0)
                        self.signals.status.emit("Canceled.")
                        return self.signals.finished.emit()
                    # Calculate total progress
                    if input_progress == 0:
                        total = progress / total_files
                    else:
                        total = (progress + (input_progress / 100)) / total_files

                    self.signals.progress.emit(total * 100)
                progress = index + 1  # Keep track of total progress

            except Exception as e:
                self.signals.status.emit(f'Error encountered. Omitting file: "{file}"')
                self.signals.status.emit(f'Error logged in: "{app_log}"')
                logger.error("%s", str(e).rstrip())
                progress = index + 1  # Keep track of total progress
                if progress == len(self.files):
                    self.signals.progress.emit(100)
                continue

            # May be triggered if user cancels after ffmpeg is done
            if self.canceled:
                self.signals.progress.emit(0)
                self.signals.status.emit("Canceled.")
                return self.signals.finished.emit()

            # Parse result and create log file
            if ff.stderr:
                detections = self.parse_ffmpeg_result(
                    ff.stderr.rstrip().splitlines(),
                    float(metadata["fps"] if metadata["fps"] != "N/A" else 25.0),
                )
                for i, detection in enumerate(detections.keys()):
                    try:
                        if detections[detection]:
                            log_file = self.create_log(file, detections, metadata)
                            self.signals.status.emit(
                                f'Created log file: "{os.path.basename(log_file)}"'
                            )
                            break
                        if i == len(detections.keys()) - 1:
                            self.signals.status.emit("No detections made.")
                    # Concerened about PermissionError mainly, but not sure which
                    # other error might be raised
                    except Exception as e:
                        self.signals.status.emit(f'Error: "{e}"')
                        self.signals.status.emit(f'Error logged in: "{app_log}"')
                        logger.error("%s", e, exc_info=True)
                        return self.signals.finished.emit()

        self.signals.status.emit("Done.")
        self.signals.finished.emit()

    # Collect metadata
    def get_metadata(self, file: str, ffprobe: str) -> dict:
        """Retrieves input metadata via ffprobe.

        Runs ffprobe to get input resolution, fps and duration, parses the result 
        and returns a dictionary containing the metadata. 
        
        Emits status signal.
        
        Command:
            ffprobe -v error -select_streams v:0 -show_entries \
            stream=r_frame_rate,height,width:format=duration -of \
            default=noprint_wrappers=1:nokey=1 <input> -ignore_chapters 1

        Args:
            file (str): String to specify input.
            ffprobe (str): String to specify ffprobe binary.

        Returns:
            metadata[dict]: Dictionary containing input resolution, fps, and duration.

        TODO: Modify function to return all metadata values as json.
        """

        metadata = dict()
        cmd = [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate,height,width:format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            os.path.join(self.directory, file),
            "-ignore_chapters",
            "1",
        ]

        # Without creation_flags Windows opens terminal during suprocess
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore
        process = subprocess.Popen(
            cmd,  # type: ignore
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        result = process.communicate()[0].decode("UTF-8").splitlines()

        # Resolution: width and height values
        try:
            metadata["resolution"] = f"{int(result[0])}x{int(result[1])}"

        except (IndexError, ValueError):
            self.signals.status.emit("Cannot determine media resolution.")
            metadata["resolution"] = "N/A"

        # Frame rate value:
        try:
            metadata["fps"] = (
                f"{(float(result[2].split('/')[0]) / float(result[2].split('/')[1]))}"
            )
        except (IndexError, ValueError):
            self.signals.status.emit("Cannot determine media frame rate.")
            metadata["fps"] = "N/A"

        # Duration value
        try:
            metadata["duration"] = convert_seconds(
                float(result[3]), float(metadata["fps"])
            )
        except (IndexError, ValueError):
            self.signals.status.emit("Cannot determine media duration.")
            metadata["duration"] = "N/A"

        return metadata

    # Build ffmpeg command
    def ffmpeg_build_command(self, file: str, ffmpeg: str) -> list:
        """Builds ffmpeg command for input with available filters.

        For example, command is:
            ffmpeg -i <input> -an -vf "freezedetect=n=-60dB:d=2" -f null -

        Args:
            file (str): String to specify input.
            ffmpeg (str): String to specify ffmpeg binary.

        Returns:
            cmd [list[str]]: A list of ffmpeg commands, e.g. ["ffmpeg", "-i", ...]
        """

        # ffmpeg input
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-i",
            os.path.join(self.directory, file),
        ]

        # Ignore audio stream if user didn't select silencedetect filter
        if not self.filters["silencedetect"]:
            cmd.append("-an")

        # User selected blackdetect and freezedetect filters
        if self.filters["blackdetect"] and self.filters["freezedetect"]:
            bd = self.filters["blackdetect"][0]
            pic_th = self.filters["blackdetect"][1]
            pix_th = self.filters["blackdetect"][2]
            n = self.filters["freezedetect"][0]
            fd = self.filters["freezedetect"][1]
            cmd += [
                "-vf",
                f"freezedetect=n=-{n}dB:d={fd},blackdetect=d={bd}:pic_th={pic_th}:pix_th={pix_th}",
            ]
        # User selected blackdetect filter
        elif self.filters["blackdetect"]:
            d = self.filters["blackdetect"][0]
            pic_th = self.filters["blackdetect"][1]
            pix_th = self.filters["blackdetect"][2]
            cmd += [
                "-vf",
                f"blackdetect=d={d}:pic_th={pic_th}:pix_th={pix_th}",
            ]
        # User selected freezedetect filter
        elif self.filters["freezedetect"]:
            n = self.filters["freezedetect"][0]
            d = self.filters["freezedetect"][1]
            cmd += [
                "-vf",
                f"freezedetect=n=-{n}dB:d={d}",
            ]
        # Ignore video stream if user didn't select freezedetect and blackdetect
        else:
            cmd.append("-vn")

        # User selected silencedetect filter
        if self.filters["silencedetect"]:
            n = self.filters["silencedetect"][0]
            d = self.filters["silencedetect"][1]
            cmd.append("-af")
            if self.filters["silencedetect"][2]:
                cmd += [
                    f"silencedetect=n=-{n}dB:d={d}:m=1",
                ]
            else:
                cmd += [
                    f"silencedetect=n=-{n}dB:d={d}",
                ]

        # ffmpeg output to null
        cmd += ["-f", "null", "-"]
        return cmd

    # Parse ffmpeg result
    def parse_ffmpeg_result(self, result: list, fps: float) -> dict:
        """Parses ffmpeg output for detections.

        Parses ffmpeg output, extracts start, duration and end number of seconds
        with regular expressions, converts those seconds to SMPTE timecode (h:m:s:f)
        and appends them as dicts representing detections(start-duration-end sequence)
        to the corresponding filter list.

        Args:
            result (list[str]): List of strings representing ffmpeg output as lines.
            fps (float): Float to specify input frame rate.

        Returns:
            detections[dict]: Dictionary with filters as keys and detections as
            lists of dictionaries each representing one filter detection.

            Example:
                detections = {
                    "blackdetect": [
                        {
                            "start": "00:00:15:10",
                            "duration": "00:00:01:10",
                            "end": "00:00:16:20"
                        },
                        {
                            "start": "00:20:15:01",
                            "duration": "00:00:00:12",
                            "end": "00:20:15:13"
                        },
                        ...
                    ],
                    "freezedetect": [
                        ...
                    ],
                    "silencedetect": [
                        ...
                    ]
                }

        Example of expected ffmpeg output representing one detection for each filter:

        [blackdetect @ 000001eb612ed440] black_start:4.52 black_end:7.72 black_duration:3.2

        [freezedetect @ 000002671a0613c0] lavfi.freezedetect.freeze_start: 4.526
        [freezedetect @ 000002671a0613c0] lavfi.freezedetect.freeze_duration: 3.2
        [freezedetect @ 000002671a0613c0] lavfi.freezedetect.freeze_end: 7.72

        [silencedetect @ 00000135014f0300] silence_start: 119.397146
        [silencedetect @ 00000135014f0300] silence_end: 121.6 | silence_duration: 2.202854

        Notes:
        Silencedetect silence_start output may have '-' before value (indicating
        a negative value?), which is accounted for in SSTART_REG regular expression,
        by ingoring '-' before value. This will not be the final solution, since
        in such cases converted time for silence_start is slightly inaccurate.
        In my experience these values where always below 1 second duration and at 
        the start of input.

        Freezedetect will not output freeze_duration and freeze_end if detection
        duration lasts from freeze_start to the end of input total duration. This 
        will result in a dictionary with last detection in detections["freezedetect"] 
        only having a "start" value. 
        Such cases have an unwanted effect on :func:`create_log` which will write
        and tabulate only the "start" value.

        TODO
        Correctly handle silencedetect silence_start output with '-' before value.
        Not sure how to handle this, since I do not fully understand why it occurs.

        Handle freezedetect not outputting freeze_duration and freeze_end for last
        detection. This may be done by passing full metadata dictionary instead of 
        just fps value from :func:`get_metadata` which uses ffprobe to get input 
        duration value. In cases where duration was not determined, :func:`get_metadata`
        should be updated to extract "out_time" or "out_time_ms" value with regular
        expression near the end of ffmpeg output, since result is already available.
        Converting this value to float number of seconds would make it easy to
        calculate and add "duration" and "end" to detections["freezedetect"] last
        detection.
        Regardless, :func:`get_metadata` should be updated to get all input metadata.
        """

        # Counters to keep track of 'start, duration, end' sequences.
        # Blackdetect counter is excluded, since its output is on a single line.
        freeze_counter = 0
        silence_counter = 0

        # Parse each line in result and populate detections dictionary
        detections: dict = {"blackdetect": [], "freezedetect": [], "silencedetect": []}
        for line in result:
            # Blackdetect
            if matches := re.search(BLACK_REG, line):
                detections["blackdetect"] += [
                    {
                        "start": convert_seconds(float(matches.group(1)), fps),
                        "duration": convert_seconds(float(matches.group(3)), fps),
                        "end": convert_seconds(float(matches.group(2)), fps),
                    }
                ]

            # Freezedetect
            if matches := re.search(FSTART_REG, line):
                detections["freezedetect"] += [
                    {
                        "start": convert_seconds(float(matches.group(1)), fps),
                    }
                ]
            if matches := re.search(FDURATION_REG, line):
                detections["freezedetect"][freeze_counter].update(
                    {"duration": convert_seconds(float(matches.group(1)), fps)}
                )
            if matches := re.search(FEND_REG, line):
                detections["freezedetect"][freeze_counter].update(
                    {"end": convert_seconds(float(matches.group(1)), fps)}
                )
                freeze_counter += 1  # Keep count

            # Silencedetect
            if matches := re.search(SSTART_REG, line):
                detections["silencedetect"] += [
                    {
                        "start": convert_seconds(float(matches.group(1)), fps),
                    }
                ]
            if matches := re.search(SDUREND_REG, line):
                detections["silencedetect"][silence_counter].update(
                    {"duration": convert_seconds(float(matches.group(2)), fps)}
                )
                detections["silencedetect"][silence_counter].update(
                    {"end": convert_seconds(float(matches.group(1)), fps)}
                )
                silence_counter += 1  # Keep count

        return detections

    # Create a log file
    def create_log(self, file: str, detections: dict, metadata: dict) -> str:
        """Creates a log containing input metadata and filters detections.

        Creates a timestamped text log file with considerations to input filename,
        then writes file metadata and tabulated ffmpeg filters detections.

        For more on created logs, see here: https://github.com/kuvk/frame-checker

        Args:
            file (str): String to specify input filename, used to create log filename.
            detections (dict): Dictionary containing input ffmpeg filters detections.
            metadata (dict): Dictionary containing input metadata information.

        Returns:
            str: Created log file path as a string.

        TODO: Expand File information section. Depends on extracting full metadata.
        """

        log_name = f"{file[:-4]}_{file[-3:]}_{time.strftime('%y%m%d_%H%M%S')}.txt"
        log_file = os.path.join(self.log_directory, log_name)

        # Determine how frame rate will be displayed in log file
        if metadata["fps"] != "N/A":
            if float(metadata["fps"]) % 1 > 0:
                fps = f"{float(metadata['fps']):.3f}"
            else:
                fps = f"{int(float(metadata['fps']))}"
        else:
            # Cases where frame rate could not be determined. Haven't triggered
            # this part yet.
            self.signals.status.emit("Filter detections might be inaccurate.")
            self.signals.status.emit(f'Error logged in: "{app_log}"')
            logger.error(f"ffprobe could not determine frame rate for file: {file}")
            fps = "25"

        # Write metadata and detections to log file
        with open(log_file, "w") as o:
            title = 12 * "-"
            section = 6 * "-"

            # Start section
            o.write(f"{title} Frame Checker Log {title}\n")
            o.write(f"{11 * '-'} {time.strftime('%d-%m-%Y %H:%M:%S')} {11 * '-'}\n\n\n")

            # File information section
            o.write(f"{section} File information\n\n")
            o.write(f"Name: {file}\n")
            o.write(f"Location: {self.directory}\n")
            o.write(f"Duration: {metadata['duration']}\n")
            o.write(f"Resolution: {metadata['resolution']}\n")
            o.write(f"FPS: {fps}\n\n\n")

            # Filters section
            o.write(f"{section} Filter detections\n\n")
            # Blackdetect
            if detections["blackdetect"]:
                o.write("-- Blackdetect\n\n")
                # Options used
                o.write("- Options\n")
                o.write(f"Minimum black duration: {self.filters['blackdetect'][0]}s\n")
                o.write(f"Picture black threshold: {self.filters['blackdetect'][1]}\n")
                o.write(f"Pixel black threshold: {self.filters['blackdetect'][2]}\n\n")
                # Tabulated detections
                o.write("- Black frames detected\n")
                o.write(
                    tabulate(detections["blackdetect"], headers="keys", tablefmt="psql")
                )
                o.write("\n\n")
            # Freezedetect
            if detections["freezedetect"]:
                o.write("-- Freezedetect\n\n")
                # Options
                o.write("- Options\n")
                o.write(f"Noise tolerance: -{self.filters['freezedetect'][0]}dB\n")
                o.write(
                    f"Minimum freeze duration: {self.filters['freezedetect'][1]}s\n\n"
                )
                # Tabulated detections
                o.write("- Frozen frames detected\n")
                o.write(
                    tabulate(
                        detections["freezedetect"], headers="keys", tablefmt="psql"
                    )
                )
                o.write("\n\n")
            # Silencedetect
            if detections["silencedetect"]:
                o.write("-- Silentdetect\n\n")
                # Options used
                o.write("- Options\n")
                o.write(f"Noise tolerance: -{self.filters['silencedetect'][0]}dB\n")
                o.write(
                    f"Minimum silence duration: {self.filters['silencedetect'][1]}s\n"
                )
                o.write(
                    f"Mono: {'Enabled' if self.filters['silencedetect'][2] else 'Disabled'}\n\n"
                )
                # Tabulated detections
                o.write("- Silent frames detected\n")
                o.write(
                    tabulate(
                        detections["silencedetect"], headers="keys", tablefmt="psql"
                    )
                )
                o.write("\n\n")

            # End section
            o.write(f"\n{19 * '-'} END {19 * '-'}\n")
            o.write(f"{43 * '-'}")

        return log_file
