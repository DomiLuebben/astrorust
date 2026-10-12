# Astrorust 1.1.0

Astrologie- und Ephemeridenprogramm für Linux mit Rust-Rechenkern, Swiss Ephemeris 2.10.03 und nativer PyQt6-Oberfläche.

## Funktionen

- Beliebig viele Horoskope in unabhängigen Tabs, interaktives Rad, Radix-SVG und PDF-Berichte mit Tabellen, Analyse und KI-Deutung.
- Historische IANA-Zeitzonen einschließlich Sommerzeit aus der installierten `tzdata`. Vor Einführung der Zonenzeit: mittlere Ortszeit des Geburtsorts (Länge/15). Mehrdeutige oder übersprungene Ortszeiten werden angezeigt; ein manueller UTC-Offset ist möglich.
- Offline-Atlas: rund 320 kuratierte Orte plus Referenzorte der System-Zeitzonendatenbank. Keine GeoNames-Daten. Freie Koordinaten und freie IANA-Zone sind möglich. Die Zone zu freien Koordinaten ist ein Vorschlag anhand des nächsten Atlasorts, keine Ermittlung politischer Zeitzonengrenzen.
- Sonne bis Pluto, Chiron, wahrer/mittlerer Mondknoten, Südknoten, mittlere/osculierende Lilith, optional Ceres, Pallas, Juno und Vesta. Fixsternkonjunktionen. Tropischer oder siderischer Tierkreis mit Ayanamsa-Wahl; optionale topozentrische Positionen am Geburtsort.
- Acht Häusersysteme: Placidus, Koch, Regiomontanus, Campanus, Ganzzeichen, Äqual, Topozentrisch und Porphyrius. Quadrantensysteme am Polarkreis weichen mit Hinweis auf Porphyrius aus.
- Zehn Aspektarten mit einstellbaren Orben, Zuschlag für Sonne/Mond und Abschlag für Nebenpunkte.
- Klassische Würden einschließlich Triplizitäten, Grenzen, Dekanaten, Rezeptionen, Dispositoren und Sekte; Aspektfiguren, Verteilung, Halbsummen mit 90°-Scheibe, arabische Lose und Deklinationsparallelen.
- Prognose: Sekundär-, Tertiär- und Minorprogression, Solarbogen, Sonnen-/Mond-/Planetenreturns einschließlich Relokation, Transitsuche mit exakten Zeitpunkten und Zeitleiste, Ingresse, Stationen, Mondphasen, Finsternisse und grafische Ephemeride.
- Synastrie mit Aspektgitter, Häuserüberlagerung, Composite und Davison.
- Vedische Tafeln (nord-/südindisch), Nakshatras, Pada, Vimshottari-Dasha mit Unterperioden und Teilungshoroskope einschließlich Navamsa.
- Astrokartografie mit MC/IC/AC/DC-Linien, zoombarer Weltkarte und Orten nahe den Linien.
- Horoskop-Datenbank mit Suche, Gruppen, Stichwörtern und Notizen. JSON-, CSV- und AAF-Import/Export. Ein fehlerhafter Import verändert die Datenbank nicht.
- Elf KI-Themen: Radix, Beruf, Partnerschaft, Seelenleben, Karma, Transite, Progression, Return, Synastrie, Vedisch und Astrokartografie. Streaming, Kopieren, Speichern und automatischer Verlauf; Deutsch/Englisch als Antwortsprache. Lokale Claude-/Codex-CLIs, Ollama, OpenAI-kompatible Server (LM Studio/vLLM) sowie Anthropic, Gemini, OpenAI, DeepSeek und OpenRouter mit eigenen Schlüsseln.
- Deutsche und englische Bedienoberfläche (Neustart nach Sprachwechsel). Regelbasierte längere Deutungen, einige berechnete Fachtexte und Fehlermeldungen bleiben deutsch.

## Installation und Start

Benötigt werden Python 3.10+, PyQt6 und `tzdata`; zum Bauen Rust/Cargo (geprüft mit 1.94) und ein C-Compiler.

```sh
git clone https://github.com/DomiLuebben/astrorust.git
cd astrorust
cargo build --release --locked
./run_gui.sh
```

Arch Linux: `makepkg -f` baut das Installationspaket. Es enthält sämtliche GUI-Module, die Weltkarte, Ephemeridendateien, Dokumentation und Lizenzhinweise. Die fertige Datei lässt sich mit `sudo pacman -U astrorust-1.1.0-1-x86_64.pkg.tar.zst` installieren.

## Rechengenauigkeit und Grenzen

Die mitgelieferten `_18.se1`-Dateien decken ungefähr 1800–2399 ab. Außerhalb dieses Bereichs nutzt die Swiss Ephemeris für die großen Planeten das Moshier-Modell. Für Chiron gibt es zusätzlich einen JPL-Bahnelemente-Fallback (1700–2150 gegen Horizons geprüft, maximale Abweichung etwa 0,03°). Asteroiden benötigen passende Datendateien; außerhalb deren Abdeckung gibt es eine Fehlermeldung. Das Diagnosemenü zeigt die vorhandenen Dateien.

Suchreihenfolge: `$ASTRORUST_EPHE`, `~/.local/share/astrorust/ephe`, `/usr/share/astrorust/ephe`, Projektverzeichnis `ephe/`, systemweite Swiss-Ephemeris-Verzeichnisse. Eigene zusätzliche `.se1`-Dateien können dort abgelegt werden.

Daten vor dem 15.10.1582 werden julianisch gelesen, danach gregorianisch. Das Datumsfeld und der Kalender beachten auch julianische Schalttage. Die GUI unterstützt Jahre 100–3000, der Rust-Kern -3000–3000; praktisch verfügbare Ephemeriden begrenzen die jeweils berechenbaren Körper.

AAF unterstützt Geburtsdaten mit `#A93`, `#B93`, `#ZNAM` und `#COM`, einschließlich Standard-/Sommer-/doppelter Sommerzeit, Ortszeit, Sekunden und Vorrang eines angegebenen Julianischen Tags. Zusatzdaten für Astrorust stehen in einem optionalen `#ASTRORUST`-Block. Unbekannte Geburtszeiten oder fehlende Koordinaten werden nicht erfunden. Abweichende explizite Kalender benötigen einen Julianischen Tag. Berechnete AAF-Positionen werden nicht übernommen, sondern neu berechnet. JSON ist das bevorzugte vollständige Sicherungsformat.

Primärdirektionen, Profektionen und Firdaria waren in der ursprünglichen Ideenliste als spätere Erweiterungen genannt und gehören nicht zu Version 1.1.0. Ein großer GeoNames-Atlas wurde in der vorherigen Sitzung nicht zum Download ausgewählt.

## Bedienung

Geburtsdaten eingeben und **Berechnen** wählen. Die IANA-Zone bestimmt den historischen Offset; für einen eigenen Offset die Zone auf **manueller UTC-Offset** setzen. Person B wird für Synastrie links eingeblendet. Prognosen, Composite und Davison erscheinen über die Auswahl **Radanzeige** im Rad. PDF-Berichte zeigen stets das Radix passend zu den Radix-Tabellen; Synastrie-Daten werden als eigener Abschnitt ergänzt. SVG exportiert das eingegebene Radix.

**Strg+T**: neuer Tab · **Strg+W**: Tab schließen · **F5**: berechnen · **F6**: jetzt · **Strg+D**: Datenbank · **Strg+S**: Profil speichern · **Strg+E**: SVG · **Strg+P**: PDF · **Strg+G**: KI-Deutung.

Einstellungen und Profile: `~/.config/astrorust/`. Gespeicherte KI-Deutungen: `~/.local/share/astrorust/readings/`. API-Schlüssel werden lokal in einer Datei mit Modus 0600 gespeichert. Die ausgewählte KI erhält die Horoskopdaten bei einer aktiv gestarteten Deutung.

## Terminalmodus

```sh
cargo run -- --cli --name "Berlin Beispiel" --date 1990-07-15 \
  --time 14:30 --lat 52.52 --lon 13.405 --zone Europe/Berlin
```

Weitere Optionen: `--tz` für manuelle UTC-Abweichung, `--sidereal`, `--ayanamsa`, `--asteroids`; `--help` zeigt alle Optionen.

## Prüfungen

```sh
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
python -m compileall -q gui
python tests/test_gui.py
```

Die GUI-Tests arbeiten mit einem eigenen temporären HOME unter `work/`, einem unsichtbaren Qt-Fenster und lokalen Testprozessen. Sie verändern keine Nutzerprofile und rufen keine kostenpflichtigen KI-Dienste auf. Referenztests gegen gespeicherte JPL-Horizons-Werte benötigen kein Netz. Release-Prüfstand und Änderungen: [CHANGELOG.md](CHANGELOG.md).

## Quellen und Lizenz

Eigener Astrorust-Quelltext: GPL-3.0-or-later. Die eingebundenen `sweph`-/`sweph-sys`-Crates und Swiss Ephemeris sind AGPL-3.0-only; das kombinierte Arch-Paket trägt deshalb AGPL-3.0-only. Originalhinweise und Lizenztext sind unter `licenses/` enthalten. Datenquellen, Dateihashes und Hinweise zur Weltkarte: [DATA_SOURCES.md](DATA_SOURCES.md).
