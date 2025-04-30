#!/bin/bash
# Frame Checker - Install FFmpeg Script - MacOS
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

FFMPEG_PATH=$(which ffmpeg)
if [[ -x "$FFMPEG_PATH" ]]; then
    echo "✅ FFmpeg is already installed at: $FFMPEG_PATH"
    exit 0
fi

# Set the correct Homebrew paths
if sysctl -n machdep.cpu.brand_string | grep -q "Apple"; then
    BREW_PREFIX="/opt/homebrew" # Apple Silicon
    BREW_BIN="$BREW_PREFIX/bin/brew"
else
    BREW_PREFIX="/usr/local" # Intel (x86_64)
    BREW_BIN="$BREW_PREFIX/bin/brew"
fi

if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Ensure Homebrew's path is available for the user
    if ! echo "$PATH" | grep -q "$BREW_PREFIX/bin"; then
        echo "Adding Homebrew to PATH..."
        echo "eval \"$($BREW_BIN shellenv)\"" >>~/.zprofile
        eval "$($BREW_BIN shellenv)"
        export PATH="$BREW_BIN:$PATH"
    fi
else
    echo "Homebrew is already installed."
fi

# Update curl
$BREW_BIN install curl
export HOMEBREW_FORCE_BREWED_CURL=1

echo "Installing FFmpeg..."
$BREW_BIN install ffmpeg

# Check if FFmpeg installation was a success.
FFMPEG_PATH=$(which ffmpeg)

if [[ -x "$FFMPEG_PATH" ]]; then
    echo "✅ FFmpeg installed successfully at: $FFMPEG_PATH"
    exit 0
else
    echo "❌ FFmpeg installation failed! Please check manually."
    exit 1
fi
