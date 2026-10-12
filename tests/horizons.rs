//! Unabhängige Gegenprobe: alle Körper an 8 Zeitpunkten (1850–2100) gegen JPL Horizons
//! (geozentrisch, scheinbar, Äquinoktium des Datums).

use astrorust::astrology::calculator::point_position;
use astrorust::astrology::engine;
use astrorust::astrology::models::{CelestialPoint, ChartSettings};

const REF: &str = include_str!("data/horizons_reference.csv");

fn point(name: &str) -> CelestialPoint {
    match name {
        "Sun" => CelestialPoint::Sun,
        "Moon" => CelestialPoint::Moon,
        "Mercury" => CelestialPoint::Mercury,
        "Venus" => CelestialPoint::Venus,
        "Mars" => CelestialPoint::Mars,
        "Jupiter" => CelestialPoint::Jupiter,
        "Saturn" => CelestialPoint::Saturn,
        "Uranus" => CelestialPoint::Uranus,
        "Neptune" => CelestialPoint::Neptune,
        "Pluto" => CelestialPoint::Pluto,
        "Ceres" => CelestialPoint::Ceres,
        "Pallas" => CelestialPoint::Pallas,
        "Juno" => CelestialPoint::Juno,
        "Vesta" => CelestialPoint::Vesta,
        "Chiron" => CelestialPoint::Chiron,
        other => panic!("{other}"),
    }
}

#[test]
fn all_bodies_match_jpl_horizons() {
    let settings = ChartSettings::default();
    let _g = engine::lock();
    let (dir, _, _) = engine::ephemeris_status();
    assert!(dir.is_some(), "Swiss-Ephemeris-Dateien nicht gefunden (ephe/)");

    let mut worst = (0.0f64, String::new());
    let mut n = 0;
    for line in REF.lines().filter(|l| !l.starts_with('#') && !l.trim().is_empty()) {
        let f: Vec<&str> = line.split(',').collect();
        let (name, jd, lon, lat): (&str, f64, f64, f64) = (f[0], f[1].parse().unwrap(), f[2].parse().unwrap(), f[3].parse().unwrap());
        let p = point_position(point(name), jd, &settings).unwrap_or_else(|e| panic!("{name} @ {jd}: {e}"));
        let dlon = ((p.lon - lon + 540.0).rem_euclid(360.0) - 180.0).abs();
        let dlat = (p.lat - lat).abs();
        let err = dlon.max(dlat);
        // Der Mond reagiert auf die ΔT-Annahme (Extrapolation nach 2050 ist Modellsache, ~0,5″ je Sekunde)
        if std::env::var("HORIZONS_VERBOSE").is_ok() {
            eprintln!("{name:8} JD {jd:.2}  ΔL {:.5}°  ΔB {:.5}°", dlon, dlat);
        }
        n += 1;
        if jd > 2470000.0 && name == "Moon" {
            assert!(err < 0.01, "{name} @ {jd}: {err}");
            continue;
        }
        if err > worst.0 {
            worst = (err, format!("{name} @ JD {jd}: Länge {:.6} statt {:.6}, Breite {:.6} statt {:.6}", p.lon, lon, p.lat, lat));
        }
    }
    assert_eq!(n, 120);
    eprintln!("größte Abweichung: {:.5}° ({})", worst.0, worst.1);
    // 0,002° = 7": das ist bereits strenger als jede gedruckte Ephemeride
    assert!(worst.0 < 0.002, "größte Abweichung {:.5}°: {}", worst.0, worst.1);
}
