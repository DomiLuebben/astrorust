//! Referenzwerte: JPL Horizons (Chiron, geozentrisch, Äquinoktium des Datums) und
//! veröffentlichte Radixdaten (Albert Einstein, Astro-Databank AA).

use astrorust::astrology::calculator::calculate_chart;
use astrorust::astrology::chiron::chiron_position;
use astrorust::astrology::models::{CelestialPoint, ChartRequest, HouseSystemChoice};

fn angle_diff(a: f64, b: f64) -> f64 {
    ((a - b + 540.0).rem_euclid(360.0) - 180.0).abs()
}

fn request(year: i32, month: i32, day: i32, hour: u32, minute: u32, tz: f64, lat: f64, lon: f64) -> ChartRequest {
    ChartRequest {
        name: "Test".into(),
        year,
        month,
        day,
        hour,
        minute,
        second: Some(0),
        timezone_offset: tz,
        latitude: lat,
        longitude: lon,
        location_name: None,
        house_system: Some(HouseSystemChoice::Placidus),
    }
}

fn planet_lon(chart: &astrorust::astrology::models::ChartResponse, id: CelestialPoint) -> f64 {
    chart.planets.iter().find(|p| p.id == id).unwrap().longitude
}

#[test]
fn chiron_matches_jpl_horizons() {
    // (JD UT, Länge°, Breite°) aus JPL Horizons
    let refs = [
        (2344164.453333333, 264.1788711, 5.3618193),
        (2366078.986666667, 334.8037610, 5.2093485),
        (2387993.520000000, 16.8295145, 1.0181650),
        (2409908.053333333, 72.1634275, -5.3273744),
        (2431822.586666666, 200.2395992, -1.7834995),
        (2453737.120000000, 301.9694167, 6.4897658),
        (2475651.653333333, 346.4759606, 4.4514033),
        (2497566.186666667, 22.6973735, 0.5957978),
    ];
    for (jd, lon, lat) in refs {
        let (l, b, _, _, _) = chiron_position(jd).expect("Chiron");
        assert!(angle_diff(l, lon) < 0.05, "JD {jd}: Länge {l} statt {lon}");
        assert!((b - lat).abs() < 0.05, "JD {jd}: Breite {b} statt {lat}");
    }
}

#[test]
fn einstein_radix() {
    // 14.3.1879 11:30 Ortszeit Ulm (LMT = UTC+0:40)
    let chart = calculate_chart(&request(1879, 3, 14, 11, 30, 0.6656, 48.4011, 9.9876)).unwrap();
    // Sonne 23°30' Fische, Mond 14°32' Schütze, AC 11°Krebs
    assert!(angle_diff(planet_lon(&chart, CelestialPoint::Sun), 353.508) < 0.02);
    assert!(angle_diff(planet_lon(&chart, CelestialPoint::Moon), 254.527) < 0.02);
    assert!((chart.angles.ascendant - 101.65).abs() < 0.1);
    // Chiron (JPL Horizons): 35.5446°
    assert!(angle_diff(planet_lon(&chart, CelestialPoint::Chiron), 35.5446) < 0.05);
}

#[test]
fn old_dates_use_the_julian_calendar() {
    // 15.4.1452 (jul.) = 23.4.1452 (greg.): die Sonne steht dann im frühen Stier.
    let chart = calculate_chart(&request(1452, 4, 15, 21, 40, 0.73, 43.7844, 10.925)).unwrap();
    let sun = planet_lon(&chart, CelestialPoint::Sun);
    assert!((30.0..40.0).contains(&sun), "Sonne bei {sun}°");
}

#[test]
fn invalid_input_is_rejected_with_a_message() {
    assert!(calculate_chart(&request(1990, 13, 1, 12, 0, 1.0, 52.0, 13.0)).is_err());
    assert!(calculate_chart(&request(1990, 2, 30, 12, 0, 1.0, 52.0, 13.0)).is_err());
    assert!(calculate_chart(&request(1990, 2, 28, 24, 0, 1.0, 52.0, 13.0)).is_err());
    assert!(calculate_chart(&request(1990, 2, 28, 12, 0, 1.0, 95.0, 13.0)).is_err());
    assert!(calculate_chart(&request(1990, 2, 28, 12, 0, 1.0, 52.0, 200.0)).is_err());
}

#[test]
fn polar_latitude_falls_back_to_porphyry() {
    let chart = calculate_chart(&request(1990, 6, 21, 12, 0, 1.0, 78.2, 15.6)).unwrap();
    assert!(chart.house_system.contains("Porphyrius"), "{}", chart.house_system);
    assert_eq!(chart.houses.len(), 12);
}

#[test]
fn displayed_degrees_never_show_sixty() {
    for day in 1..=28 {
        let chart = calculate_chart(&request(2024, 2, day, 3, 17, 1.0, 52.52, 13.405)).unwrap();
        for p in &chart.planets {
            assert!(p.min_int < 60 && p.sec_int < 60 && p.deg_int < 30, "{}", p.formatted_deg);
        }
        for h in &chart.houses {
            assert!(h.min_int < 60 && h.deg_int < 30, "{}", h.formatted_deg);
        }
        for a in &chart.aspects {
            assert!(!a.formatted_orb.contains("60'"), "{}", a.formatted_orb);
        }
    }
}

#[test]
fn element_count_uses_ten_planets_plus_ascendant() {
    let chart = calculate_chart(&request(1990, 5, 15, 14, 30, 2.0, 52.52, 13.405)).unwrap();
    let eq = &chart.element_quality;
    assert_eq!(eq.fire + eq.earth + eq.air + eq.water, 11);
    assert_eq!(eq.cardinal + eq.fixed + eq.mutable, 11);
}

#[test]
fn ffi_errors_are_valid_json() {
    use astrorust::ffi::{astrorust_calculate_chart, astrorust_free_string};
    use std::ffi::{CStr, CString};

    let bad = CString::new(r#"{"name": "x", "year": "abc"}"#).unwrap();
    let ptr = astrorust_calculate_chart(bad.as_ptr());
    let text = unsafe { CStr::from_ptr(ptr).to_str().unwrap().to_string() };
    astrorust_free_string(ptr);
    let value: serde_json::Value = serde_json::from_str(&text).expect("Antwort muss gültiges JSON sein");
    assert!(value["error"].as_str().unwrap().contains("JSON Parse Error"));
}

#[test]
fn svg_escapes_user_text() {
    use astrorust::astrology::svg_export::generate_chart_svg;
    let mut req = request(1990, 5, 15, 14, 30, 2.0, 52.52, 13.405);
    req.name = "Ben & <Jerry>".into();
    let svg = generate_chart_svg(&calculate_chart(&req).unwrap());
    assert!(svg.contains("Ben &amp; &lt;Jerry&gt;"));
    assert!(!svg.contains("<Jerry>"));
}
