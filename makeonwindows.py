# Frame Checker - Build Automation Script for Windows
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
import subprocess
import sys

# Check python requirement
required_version = (3, 10)
if sys.version_info < required_version:
    print(f"Python 3.10 or higher is required. You are running Python {sys.version}.")
    sys.exit(1)
print(f"Using Python: {sys.version}")

# Set PYTHONPATH to the current directory
os.environ["PYTHONPATH"] = os.getcwd()

# Create and/or activate virtual environment
venv_activation_script = r".\venv\Scripts\Activate.ps1"
activate = (
    f"powershell -ExecutionPolicy ByPass -NoProfile -Command {venv_activation_script};"
)
if not os.path.isfile(venv_activation_script):
    print("Virtual enviroment not found. Creating...")
    subprocess.run("python -m venv venv", shell=True, check=True)
    print("Virtual enviroment created.")
subprocess.run(
    f"{activate} echo 'Virtual environment activated.'", shell=True, check=True
)

# Upgrade pip and install requirements
print("Installing requirements...")
subprocess.run("python.exe -m pip install --upgrade pip", shell=True, check=True)
subprocess.run("pip install -r frame_checker/requirements.txt", shell=True, check=True)
subprocess.run("pip install pyinstaller", shell=True, check=True)

# Build app with pyinstaller
print("Building Frame Checker with pyinstaller...")
subprocess.run("pyinstaller windows/windows.spec", shell=True, check=True)

# Get environment variables for signing executables
with open(".env") as f:
    for line in f:
        key, value = line.strip().split("=", 1)
        os.environ[key] = value
password = os.environ["PASSWORD"] or sys.exit("PASSWORD not found in .env.")
cert_path = os.path.abspath(os.environ["CERT_PATH"]) or sys.exit(
    "CERT_PATH not found in .env."
)
timestamp_url = os.environ["TIMESTAMP_URL"] or "http://timestamp.digicert.com"

# Check if pyinstaller built app executable exists
exe = os.path.abspath(r"dist\main\Frame Checker.exe")
if not os.path.isfile(exe):
    sys.exit(f"{exe} not found.")
exe = os.path.abspath(exe)


# Sign app executable
print(f"Signing {exe}...")
command = [
    "signtool",
    "sign",
    "/f",
    cert_path,
    "/p",
    password,
    "/fd",
    "SHA256",
    "/tr",
    timestamp_url,
    "/td",
    "SHA256",
    "/v",
    exe,
]
subprocess.run(command, check=True)

# Create installer executable with InnoSetup
print("Creating installer with Inno Setup...")
innosetup_path = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
iss_script = r"windows\frame-checker-innosetup.iss"
if os.path.isfile(innosetup_path) and os.path.isfile(iss_script):
    iss_script = os.path.abspath(iss_script)
    try:
        subprocess.run([innosetup_path, iss_script], check=True)
        print("Inno Setup script compiled successfully.")
    except subprocess.CalledProcessError as e:
        sys.exit(f"Error during Inno Setup compilation:\n{e}")

installer_exe = r"windows\Output\frame-checker-1.0.0-win_x64.exe"
if not os.path.isfile(installer_exe):
    sys.exit(f"{installer_exe} not found.")
installer_exe = os.path.abspath(installer_exe)

# Sign installer executable
print(f"Signing {installer_exe}...")
command = [
    "signtool",
    "sign",
    "/f",
    cert_path,
    "/p",
    password,
    "/fd",
    "SHA256",
    "/tr",
    timestamp_url,
    "/td",
    "SHA256",
    "/v",
    installer_exe,
]
subprocess.run(command, check=True)

print("DONE")
sys.exit(0)
