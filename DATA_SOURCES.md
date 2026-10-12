# Datenquellen

## Swiss Ephemeris

Quelle der vier von Claude am 12.10.2026 bezogenen Dateien: https://github.com/aloistr/swisseph/tree/master/ephe

Projekt und Downloadhinweise: https://www.astro.com/swisseph/swedownload_e.htm

Swiss Ephemeris: Copyright © Astrodienst AG, Dieter Koch und Alois Treindl. Der originale Lizenzhinweis steht in `licenses/Swiss-Ephemeris-NOTICE`, die freie Lizenz in `licenses/AGPL-3.0.txt`. Für die eingebundenen Rust-Crates `sweph` und `sweph-sys` 0.3.0 ist AGPL-3.0-only ausgewiesen. Die Dateien `_18.se1` sind der 600-Jahres-Block ab 1800. Die Dateien werden unverändert ausgeliefert.

| Datei | SHA-256 |
|---|---|
| seas_18.se1 | a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2 |
| sepl_18.se1 | ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66 |
| semo_18.se1 | 1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7 |
| sefstars.txt | 18b0dcafbe5b7240773daba2c038a325f5b3fc4163f61e0a7f4e92abd4f517c6 |

## Zeitzonen und Orts-Atlas

Die System-IANA-tzdata wird lokal gelesen (`/usr/share/zoneinfo/`, einschließlich `zone1970.tab`/`iso3166.tab`). Quelle: https://www.iana.org/time-zones . Dazu kommt Claudes kuratierte Ortsliste in `src/astrology/atlas_data.txt`. Die Zahl zusätzlicher Referenzorte hängt von der installierten tzdata-Version ab. Der Atlas enthält keine GeoNames-Daten. Der nächste Referenzort ist nur ein Zeitzonenvorschlag, kein Grenzpolygon-Test.

## Weltkarte

`gui/coastlines.geojson` wurde von Claude aus Natural Earth **ne_110m_land**, Version 4.1.0, erzeugt: https://www.naturalearthdata.com/downloads/110m-physical-vectors/110m-land/ . Die Koordinaten wurden auf zwei Dezimalstellen reduziert. Natural Earth veröffentlicht die Daten als Public Domain: https://www.naturalearthdata.com/about/terms-of-use/ . Die Darstellung dient der Orientierung und bildet keine politischen Grenzen ab.

## Rechenreferenzen und AAF

JPL Horizons: https://ssd.jpl.nasa.gov/horizons/ . Die gespeicherten Stichproben stehen in `tests/data/horizons_reference.csv`; der Chiron-Fallback und seine Referenzen stammen aus dem Audit vom 12.10.2026.

AAF'97: Beschreibung des Austauschformats mit Auszug der Originaldokumentation bei Astrodienst: https://www.astro.com/astrowiki/en/AAF . Die Implementierung ist eigener Astrorust-Code und übernimmt keine fremde Parser-Implementierung.
