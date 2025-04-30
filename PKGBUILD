# Maintainer: Vuk Knežević <kuvk.me@gmail.com>
pkgname=frame-checker
pkgver=1.0
pkgrel=1
pkgdesc="Frame Checker is a PySide6 application for checking video frames using ffmpeg filters."
arch=('x86_64')
url="https://github.com/kuvk/frame-checker"
license=('GPL-3.0')
options=('!debug')
depends=(
    'python>=3.10'
    'ffmpeg'
    'xdg-utils'
    'xcb-util-cursor'
)
makedepends=(
    'python-setuptools'
    'python-wheel'
    'python-virtualenv'
    'imagemagick'
    'rsync'
)
install=frame-checker.install
source=()

prepare() {
    # Create the destination directory
    mkdir -p "$srcdir/$pkgname"

    # Read the .gitignore file to create rsync exclude patterns
    rsync_exclude=()
    while IFS= read -r line; do
        [[ "$line" =~ ^#.*$ ]] && continue
        [[ -z "$line" ]] && continue
        rsync_exclude+=("--exclude=$line")
    done <"$startdir/.gitignore"
    rsync_exclude+=("--exclude=makeondeb")
    rsync_exclude+=("--exclude=makeonmac")
    rsync_exclude+=("--exclude=makeonwindows.py")
    rsync_exclude+=("--exclude=macos/")
    rsync_exclude+=("--exclude=windows/")
    rsync_exclude+=("--exclude=debian/")
    rsync_exclude+=("--exclude=resources/icon.icns")
    rsync_exclude+=("--exclude=resources/icon.ico")
    rsync_exclude+=("--exclude=resources/logfile.gif")
    rsync_exclude+=("--exclude=resources/screenshot*")
    rsync_exclude+=("--exclude=resources/LICENSE.txt")
    rsync_exclude+=("--exclude=resources/version.txt")

    # Copy the contents of the project directory to the src directory, excluding patterns from .gitignore
    rsync -a "${rsync_exclude[@]}" "$startdir/" "$srcdir/$pkgname/"
}

build() {
    cd "$srcdir/$pkgname"

    python -m venv venv
    source venv/bin/activate

    pip install --upgrade pip setuptools wheel
    pip install .
}

package() {
    cd "$srcdir/$pkgname"

    # Copy virtualenv contents to /opt/frame-checker
    install -d "$pkgdir/opt/$pkgname"
    cp -a venv/* "$pkgdir/opt/$pkgname/"

    # Remove __pycache__
    find "$pkgdir/opt/$pkgname" -name '__pycache__' -exec rm -rf {} +

    # Fix shebangs to be relocatable
    for bin in "$pkgdir/opt/$pkgname/bin/"*; do
        if head -n1 "$bin" | grep -qE '^#!.*/bin/python'; then
            sed -i "1 s|^#!.*|#!/opt/$pkgname/bin/python|" "$bin"
        fi
    done

    # Install resources, icons, .desktop, license, readme
    install -d "$pkgdir/usr/share/$pkgname/resources"
    cp -r resources/icon.png resources/frame-checker.desktop "$pkgdir/usr/share/$pkgname/resources"
    cp frame_checker/default_settings.ini "$pkgdir/usr/share/$pkgname/"
    cp -r assets "$pkgdir/usr/share/$pkgname/"

    for size in 512 256 128 64 48 32 16; do
        install -d "$pkgdir/usr/share/icons/hicolor/${size}x${size}/apps"
        magick "resources/icon.png" -resize ${size}x${size} \
            "$pkgdir/usr/share/icons/hicolor/${size}x${size}/apps/$pkgname.png"
    done

    install -Dm644 "resources/frame-checker.desktop" \
        "$pkgdir/usr/share/applications/frame-checker.desktop"

    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    install -Dm644 COPYING "$pkgdir/usr/share/licenses/$pkgname/COPYING"
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
}
