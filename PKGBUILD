# Maintainer: Dominik Lübben <dominikluebben@googlemail.com>
pkgname=astrorust
pkgver=1.0.0
pkgrel=1
pkgdesc="Professionelle Astrologie- und Ephemeriden-Software in Rust und Qt6"
arch=('x86_64')
url="https://github.com/DomiLuebben/astrorust"
license=('GPL-3.0-or-later')
depends=('glibc' 'gcc-libs' 'python' 'python-pyqt6')
# Rust und Cargo werden über rustup bereitgestellt (~/.cargo/bin/cargo)
optdepends=('ollama: Lokale LLM-Inferenz für Horoskopdeutungen'
            'claude-code: Anthropic Claude CLI Integration')
options=(!lto)

build() {
    cd "$startdir"
    cargo build --release --locked
}

package() {
    cd "$startdir"

    # 1. Rust CLI Binary in /usr/bin
    install -Dm755 "target/release/astrorust" "$pkgdir/usr/bin/astrorust"

    # 2. Rust C-ABI Shared Library in /usr/lib
    install -Dm755 "target/release/libastrorust.so" "$pkgdir/usr/lib/libastrorust.so"

    # 3. Python Qt6 GUI in /usr/share/astrorust/gui
    local appdir="$pkgdir/usr/share/astrorust/gui"
    install -dm755 "$appdir"
    for f in main.py mainwindow.py chart_wheel.py ai_engine.py ai_dialog.py rust_backend.py styles.py astrorust.svg; do
        install -Dm644 "gui/$f" "$appdir/$f"
    done
    chmod +x "$appdir/main.py"

    # 4. Desktop-Starter & App-Icon
    install -Dm644 "astrorust.desktop" "$pkgdir/usr/share/applications/astrorust.desktop"
    install -Dm644 "gui/astrorust.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/astrorust.svg"

    # 5. Dokumentation
    install -Dm644 "README.md" "$pkgdir/usr/share/doc/$pkgname/README.md"
}
