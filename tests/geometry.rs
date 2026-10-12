//! Geometrische Gegenprobe der Astrokartografie, Composite- und Houses-Kette
use astrorust::astrology::astrocarto::*;
use astrorust::astrology::calculator::calculate_chart;
use astrorust::astrology::models::*;
use astrorust::astrology::synastry::calculate_synastry;

fn req(lat: f64, lon: f64) -> ChartRequest {
    ChartRequest {
        name: "T".into(),
        year: 1985,
        month: 8,
        day: 20,
        hour: 9,
        minute: 15,
        second: Some(0),
        timezone_offset: 0.0,
        latitude: lat,
        longitude: lon,
        location_name: None,
        house_system: Some(HouseSystemChoice::Placidus),
        timezone: None,
        settings: None,
    }
}

fn diff(a: f64, b: f64) -> f64 {
    ((a - b + 540.0).rem_euclid(360.0) - 180.0).abs()
}

#[test]
fn sun_lines_match_charts_cast_on_the_line() {
    let map = astro_map(&AstroMapRequest { natal: req(52.0, 13.0), bodies: vec!["Sun".into()], city_orb: None, lat_step: Some(5.0) }).unwrap();
    let sun_lon = map.natal_chart.planets.iter().find(|p| p.id == CelestialPoint::Sun).unwrap().longitude;

    let mc = map.lines.iter().find(|l| l.kind == "MC").unwrap();
    let lon_mc = mc.segments[0][0][1];
    let chart = calculate_chart(&req(50.0, lon_mc)).unwrap();
    assert!(diff(chart.angles.midheaven, sun_lon) < 0.02, "MC {} vs Sonne {}", chart.angles.midheaven, sun_lon);

    // Die AC-Linie bei ~50° Breite: dort steht die Sonne am Aszendenten
    let ac = map.lines.iter().find(|l| l.kind == "AC").unwrap();
    let pt = ac.segments.iter().flatten().find(|p| (p[0] - 50.0).abs() < 0.01 || (p[0] - 45.0).abs() < 0.01).unwrap();
    let chart = calculate_chart(&req(pt[0], pt[1])).unwrap();
    assert!(diff(chart.angles.ascendant, sun_lon) < 0.1, "AC {} vs Sonne {} bei {:?}", chart.angles.ascendant, sun_lon, pt);
}

#[test]
fn composite_of_a_person_with_themselves_is_the_person() {
    let r = req(48.4, 9.99);
    let syn = calculate_synastry(&SynastryRequest { person_a: r.clone(), person_b: r.clone() }).unwrap();
    let comp = syn.composite_chart.expect("Composite");
    let natal = calculate_chart(&r).unwrap();
    for p in natal.planets.iter().take(10) {
        let c = comp.planets.iter().find(|x| x.id == p.id).unwrap();
        assert!(diff(c.longitude, p.longitude) < 1e-6, "{}", p.name);
    }
    assert!(diff(comp.angles.midheaven, natal.angles.midheaven) < 0.01);
    assert!(diff(comp.angles.ascendant, natal.angles.ascendant) < 0.05);
    let dav = syn.davison_chart.expect("Davison");
    assert!(diff(dav.angles.ascendant, natal.angles.ascendant) < 0.05);
}

#[test]
fn synastry_grid_matches_cross_aspects() {
    let a = req(48.4, 9.99);
    let mut b = req(52.5, 13.4);
    b.year = 1988;
    let syn = calculate_synastry(&SynastryRequest { person_a: a, person_b: b }).unwrap();
    let filled = syn.grid.cells.iter().flatten().filter(|c| c.is_some()).count();
    assert_eq!(filled, syn.cross_aspects.len());
    assert_eq!(syn.overlay_a_in_b.len(), syn.overlay_b_in_a.len());
}
