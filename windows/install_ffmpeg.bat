:: Frame Checker - Install FFmpeg Script - Windows
:: Copyright (C) 2025 Vuk Knežević
::
:: This program is free software: you can redistribute it and/or modify
:: it under the terms of the GNU General Public License as published by
:: the Free Software Foundation, either version 3 of the License, or
:: (at your option) any later version.
::
:: This program is distributed in the hope that it will be useful,
:: but WITHOUT ANY WARRANTY; without even the implied warranty of
:: MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
:: GNU General Public License for more details.
::
:: You should have received a copy of the GNU General Public License
:: along with this program.  If not, see <https://www.gnu.org/licenses/>.

@echo off
setlocal EnableDelayedExpansion

:: Check if the script is run as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Please run this script as administrator.
    exit /b
)

:: Check if ffmpeg is already installed
where ffmpeg >nul 2>&1
if %errorlevel% == 0 (
    echo FFmpeg is already installed.
    goto end
)

:: Download ffmpeg
echo Downloading FFmpeg...
powershell -Command "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg.zip'"

:: Extract the ffmpeg.zip to C:\ffmpeg
echo Extracting FFmpeg to C:\ffmpeg...
powershell -Command "Expand-Archive -Path 'ffmpeg.zip' -DestinationPath 'C:\'"

:: Rename the extracted folder to 'ffmpeg'
for /d %%i in (C:\ffmpeg-*) do (
    ren "%%i" "ffmpeg"
    goto :rename_done
)
:rename_done

:: Delete the ffmpeg.zip file
echo Deleting extracted ffmpeg.zip...
del /f /q ffmpeg.zip

echo Adding FFmpeg to PATH...

set "ffmpegPath=C:\ffmpeg\bin"

:: Add FFmpeg to PATH
for /f "skip=2 tokens=*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do (
    set "regLine=%%A"
)

for /f "tokens=2,*" %%A in ("!regLine!") do (
    set "currentPath=%%B"
)

echo !currentPath! | findstr /I /C:"%ffmpegPath%" >nul
if !errorlevel! == 0 (
    echo FFmpeg is already in system PATH.
) else (
    reg add "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH /t REG_EXPAND_SZ /f /d "!currentPath!;%ffmpegPath%"
    echo FFmpeg added to system PATH.
    set "PATH=%PATH%;%ffmpegPath%"
    powershell -Command "[Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH', 'Machine'), 'Machine'); $signature='[DllImport(\"user32.dll\",SetLastError=true)]public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);'; Add-Type -MemberDefinition $signature -Name 'Win32SendMessageTimeout' -Namespace Win32; [Win32.Win32SendMessageTimeout]::SendMessageTimeout([intptr]0xffff, 0x1A, [uintptr]0, 'Environment', 0, 1000, [ref]([uintptr]0))"
)


echo FFmpeg installation was successful!

:end
endlocal

