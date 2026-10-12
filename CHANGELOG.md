# Änderungen

## 1.1.0 — 12.10.2026

Claudes unterbrochenen Ausbau abgeschlossen. Enthält den bereits eingecheckten Rust-Ausbau aus `c4e1905` und `78aff75` sowie die bisher ungespeicherte neue modulare Qt-Oberfläche.

- Historische Zeitzonen, Offline-Atlas, Berechnungseinstellungen, Asteroiden und Fixsterne in die Oberfläche integriert.
- Analyse, Prognosen, Synastrie/Composite/Davison, vedische Tafeln und Astrokartografie bedienbar; unabhängige Horoskop-Tabs, Datenbank, Berichte und KI-Streaming eingebunden.
- Englische Bedienoberfläche ausgefüllt; deutsche und englische KI-Ausgabe. Regelbasierte Langtexte und einige Engine-Texte bleiben deutsch.
- AAF-Geburtsdatenimport/-export ergänzt (DST, doppelte Sommerzeit, LMT, JD-Vorrang, Sekunden, Kommentare). CSV erhält Sekunden; ungültige Importe verändern keine Profile. Profilumbenennung erhält die Identität; Datenbankfilter verlieren keine Notizen.
- Topozentrik aktiviert (vorher leere Option) und äquatoriale Mondpositionen konsistent berechnet. Relokierte topozentrische Returns rechnen am gewählten Ort.
- Veraltete Prognose-/Synastrie-/Karten-/vedische Ergebnisse und KI-Texte bei Radixwechsel verworfen. Weitere Berechnungen synchronisieren zuvor geänderte Eingabedaten.
- Ungültige Datumstexte werden überall abgewiesen. Julianische Schalttage auch in der Oberfläche; Prognosezeiten runden über Mitternacht und nutzen den richtigen Kalender.
- Einstellungsabbruch verändert keine gespeicherten Werte; Ayanamsa-ID 0 bleibt erhalten. Getippte Zeitzonen überstimmen den zuvor ausgewählten Kombobox-Eintrag.
- Lokale KI-CLIs streamen auch ohne Zeilenumbruch. Große stderr-Ausgaben blockieren nicht; Abbruch beendet die gestartete Prozessgruppe. Auslaufende Netzwerk-Threads bleiben beim Schließen referenziert.
- PDF-Rad zeigt das Radix passend zu den Tabellen, unabhängig von der gewählten Composite-Anzeige; Glyphen in Druckauflösung lesbar skaliert.
- Paketierung auf alle GUI-Module, Weltkarte, Ephemeridendateien, tzdata-Abhängigkeit, Dokumentation und Original-Lizenzhinweise erweitert. Version 1.1.0 an allen Versionsstellen.

Prüfstand: 53 Rust-Tests einschließlich JPL-Referenzen, Zeit-/Geometrie-/Prognose-Tests und neuer Topozentrik-/Datums-Gegenproben; 16 zusätzliche Python/Qt-Integrationstests; Clippy ohne Warnungen; Python-Syntaxprüfung; vollständiger GUI-Durchlauf mit lokalem KI-Testserver und PDF-Sichtprüfung. Das fertige Arch-Paket ist separat mit seinen enthaltenen Modulen, Bibliotheken und Ressourcen geprüft. Kostenpflichtige KI-APIs und eine systemweite Installation sind nicht Bestandteil dieser Prüfung.

Aus der ursprünglichen Ideenliste verbleiben die als später bezeichneten Primärdirektionen, Profektionen und Firdaria. Der GeoNames-Download wurde in Claudes Sitzung nicht ausgewählt; der vorhandene kuratierte Atlas bleibt erhalten.

## 1.0.1 — 12.10.2026

Rechenaudit: JPL-Chiron-Fallback, julianischer Kalender, sichere JSON-/SVG-Ausgabe, Eingabeprüfung, Polarkreis-Fallback und erste GUI-/KI-Korrekturen (`ffd3491`).
