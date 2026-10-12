#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Ensure Rust library is built
if [ ! -f "target/debug/libastrorust.so" ]; then
    echo "Baue Astrorust Rust-Bibliothek..."
    cargo build
fi

# Launch native Qt6 GUI
python3 "$DIR/gui/main.py" "$@"
