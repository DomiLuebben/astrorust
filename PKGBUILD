# Maintainer: Dominik Lübben <dominikluebben@googlemail.com>
pkgname=astrorust
pkgver=1.1.0
pkgrel=1
pkgdesc="Professionelle Astrologie- und Ephemeriden-Software in Rust und Qt6"
arch=('x86_64')
url="https://github.com/DomiLuebben/astrorust"
license=('AGPL-3.0-only')
depends=('glibc' 'gcc-libs' 'python' 'python-pyqt6' 'tzdata')
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
    for f in gui/*.py gui/*.svg gui/*.geojson; do
        install -Dm644 "$f" "$appdir/${f##*/}"
    done
    for f in ephe/*.se1 ephe/sefstars.txt; do
        install -Dm644 "$f" "$pkgdir/usr/share/astrorust/$f"
    done
    install -Dm644 "DATA_SOURCES.md" "$pkgdir/usr/share/doc/$pkgname/DATA_SOURCES.md"
    install -Dm644 "CHANGELOG.md" "$pkgdir/usr/share/doc/$pkgname/CHANGELOG.md"
    chmod +x "$appdir/main.py"

    for f in licenses/*; do
        install -Dm644 "$f" "$pkgdir/usr/share/licenses/$pkgname/${f##*/}"
    done

    # 4. Desktop-Starter & App-Icon
    install -Dm644 "astrorust.desktop" "$pkgdir/usr/share/applications/astrorust.desktop"
    install -Dm644 "gui/astrorust.svg" "$pkgdir/usr/share/icons/hicolor/scalable/apps/astrorust.svg"

    # 5. Dokumentation
    install -Dm644 "README.md" "$pkgdir/usr/share/doc/$pkgname/README.md"
}
