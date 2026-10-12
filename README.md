# ✨ Astrorust

> **Open-Source Astrologie- und Ephemeriden-Software inspiriert von Astroplus, umgesetzt in Rust und nativem Qt6.**
>
> Entwickelt mit modernem KDE Breeze Dark Design, hochpräziser Swiss Ephemeris 2.10 Engine und integrierter KI-Deutungssynthese (lokale LLMs & APIs).

---

## 🌟 Highlights & Features

Astrorust kombiniert die Zuverlässigkeit und Geschwindigkeit von **Rust** mit einer nativen Linux-Desktop-Oberfläche (**Qt6 / QPainter**) und einem modularen **KI-Deutungssystem**:

* **🪐 Swiss Ephemeris 2.10.03 Core (`sweph`):**
  * Auf Bogensekunden genaue Planetenpositionen und Häuserspitzen.
  * Alle 10 klassischen Planeten (☉ Sonne, ☽ Mond, ☿ Merkur, ♀ Venus, ♂ Mars, ♃ Jupiter, ♄ Saturn, ♅ Uranus, ♆ Neptun, ♇ Pluto).
  * ☊ Wahrer Mondknoten, ⚷ Chiron (Kepler-Orbitalmodell) und ⚸ Lilith (Mittleres Apogäum).
  * 8 Häusersysteme: Placidus, Koch, Regiomontanus, Campanus, Ganzzeichen (Whole Sign), Äqual, Topozentrisch, Porphyrius.
  * 10 Aspektarten mit konfigurierbaren Orben und Applikativ/Separativ-Status.
  * Klassische Würden-Matrix (Domizil, Erhöhung, Fall, Exil).
  * Bi-Wheel-Berechnungen für **Transite** und **Synastrie** (Partnervergleich).
  * Vollständig in Rust implementiert und als C-ABI Shared Library (`libastrorust.so`) exportiert.

* **🎨 Native Qt6 Desktop-Oberfläche:**
  * **KDE Breeze Dark Design:** Gestaltet nach der Designsprache des Linux Media Encoders (AME-Layout, `#1a1d20` Window, `#232629` Surface, `#3daee9` Breeze-Blau).
  * **Vektor-Horoskoprad (`QPainter`):** Gestochen scharfe Vektorgrafik mit Anti-Aliasing, 360°-Skala, Elementarfarben, Anti-Kollisions-Zeigern bei Stellien und interaktiven Tooltips beim Hovern über Planeten und Aspekte.
  * **⏳ Zeitschieber / Time Travel:** Scrubber-Regler, Sprung-Tasten (`±10m`, `±1h`, `±1T`, `±1M`, `±1J`) und animierter Play-Modus zur visuellen Beobachtung von Planetenwanderungen in Echtzeit.
  * **SVG-Export:** Export des aktuellen Radixrades als Vektorgrafik auf Knopfdruck.
  * **Integrierter Orts-Atlas:** Koordinaten- und Zeitzonensuche für über 100 Städte weltweit.

* **🔮 Multi-Provider KI-Deutungsengine (Astroplus-Parität):**
  * **Lokale KIs & CLIs:** Automatische Erkennung von Claude Code CLI (`claude`), Codex CLI (`codex`), lokalem Ollama (`http://127.0.0.1:11434`) oder LM Studio / vLLM.
  * **API-Keys & GenOffice-Import:** 1-Klick-Import hinterlegter Schlüssel (Anthropic, OpenAI, Google Gemini, DeepSeek, OpenRouter, Mistral) aus `~/.config/GenOffice/ai-settings.json`.
  * **7 tiefenpsychologische Deutungsmodule (Jungianisch / Liz Greene):**
    1. 🌟 *Großes Radix-Persönlichkeitsprofil*
    2. 🏛️ *Berufung, Karriere & Lebensziel* (MC & 10. Haus)
    3. 💖 *Partnerschaft, Liebe & Beziehung* (Venus/Mars/7. Haus)
    4. 🌙 *Seelenleben & emotionale Wurzeln* (Mond & 4. Haus IC)
    5. 🪐 *Karma, Seelenplan & Schattenarbeit* (Saturn, Chiron, Lilith, Mondknoten)
    6. ⏳ *Aktuelle Transite & Zeitqualität* (Jahresvorschau)
    7. 👥 *Partnervergleich & Beziehungsdynamik* (Synastrie)

---

## 🛠️ Systemvoraussetzungen

* **Linux** (x86_64, aarch64)
* **Rust & Cargo** (1.75+ empfohlen)
* **Python 3.10+** mit **PyQt6** (`python3 -m pip install PyQt6` oder `sudo pacman -S python-pyqt6` / `sudo apt install python3-pyqt6`)
* C-Compiler (`gcc` oder `clang`) für das Bauen der C-Bibliothek von Swiss Ephemeris.

---

## 🚀 Installation & Start

### 1. Repository klonen

```bash
git clone https://github.com/DomiLuebben/astrorust.git
cd astrorust
```

### 2. Rust-Bibliothek bauen

```bash
cargo build --release
```

*(Oder `cargo build` für den Debug-Build).*

### 3. Native Desktop-App starten

Entweder direkt über das Shell-Skript:
```bash
./run_gui.sh
```

Oder über Cargo:
```bash
cargo run
```

---

## 💻 CLI-Modus (Reine Terminal-Berechnung)

Astrorust kann Horoskope auch rein im Terminal ohne grafische Oberfläche auf Bogensekunden genau ausgeben:

```bash
cargo run -- --cli \
  --name "Johann Wolfgang von Goethe" \
  --date "1749-08-28" \
  --time "12:00" \
  --lat 50.1109 \
  --lon 8.6821 \
  --tz 0.58
```

---

## 📁 Projektstruktur

```
astrorust/
├── Cargo.toml            # Rust Manifest
├── run_gui.sh            # One-Click Starter für die Desktop-GUI
├── astrorust.desktop     # Desktop-Starter für KDE Plasma / GNOME
├── src/                  # Rust Swiss-Ephemeris Core & FFI
│   ├── lib.rs            # Rust Library Root
│   ├── main.rs           # CLI Launcher & Terminal-Deutung
│   ├── ffi.rs            # C-ABI Export (libastrorust.so)
│   └── astrology/        # Berechnungsmodule (Planeten, Würden, Aspekte, Atlas...)
└── gui/                  # Native Qt6 Desktop-Oberfläche
    ├── main.py           # GUI Einstiegspunkt
    ├── rust_backend.py   # ctypes FFI Bridge zu libastrorust.so
    ├── chart_wheel.py    # Interaktives Radixrad (QPainter Vektor-Engine)
    ├── mainwindow.py     # Hauptfenster (Breeze Dark, Splitter, Tabs)
    ├── styles.py         # KDE Breeze Dark QSS & Theme Tokens
    ├── ai_engine.py      # Multi-Provider KI Engine (Claude, Codex, Ollama, APIs)
    └── ai_dialog.py      # Einstellungsdialog inkl. GenOffice-Import
```

---

## 📜 Lizenz & Danksagung

* **Astrorust** steht unter der **GPL-3.0-or-later** Lizenz.
* Berechnungen basieren auf der **Swiss Ephemeris** (Copyright © Astrodienst AG).
* Inspiriert von der deutschen Astrologie-Referenzsoftware **Astroplus**.
