use astrorust::astrology::calculator::calculate_chart;
use astrorust::astrology::forecast::*;
use astrorust::astrology::models::*;

fn natal() -> ChartRequest {
    ChartRequest {
        name: "Test".into(),
        year: 1990,
        month: 5,
        day: 15,
        hour: 14,
        minute: 30,
        second: Some(0),
        timezone_offset: 0.0,
        latitude: 52.52,
        longitude: 13.405,
        location_name: Some("Berlin".into()),
        house_system: Some(HouseSystemChoice::Placidus),
        timezone: Some("Europe/Berlin".into()),
        settings: None,
    }
}

fn tp(y: i32, m: i32, d: i32) -> TimePoint {
    TimePoint { year: y, month: m, day: d, hour: 0, minute: 0, timezone_offset: 0.0 }
}

fn lon(chart: &ChartResponse, id: CelestialPoint) -> f64 {
    chart.planets.iter().find(|p| p.id == id).unwrap().longitude
}

fn diff(a: f64, b: f64) -> f64 {
    ((a - b + 540.0).rem_euclid(360.0) - 180.0).abs()
}

#[test]
fn solar_return_has_the_natal_sun_longitude() {
    let n = natal();
    let natal_chart = calculate_chart(&n).unwrap();
    let r = calculate_return(&ReturnRequest {
        natal: n,
        body: "Sun".into(),
        start: tp(2024, 1, 1),
        count: 1,
        latitude: None,
        longitude: None,
        location_name: None,
        display_timezone: Some("Europe/Berlin".into()),
    })
    .unwrap();
    assert!(diff(lon(&r.chart, CelestialPoint::Sun), lon(&natal_chart, CelestialPoint::Sun)) < 1e-4);
    // 15. Mai 2024, nachmittags
    let first = &r.returns[0];
    assert!(first.label.starts_with("2024-05-1"), "{}", first.label);
}

#[test]
fn lunar_returns_come_every_27_days() {
    let r = calculate_return(&ReturnRequest {
        natal: natal(),
        body: "Moon".into(),
        start: tp(2024, 1, 1),
        count: 3,
        latitude: None,
        longitude: None,
        location_name: None,
        display_timezone: None,
    })
    .unwrap();
    assert_eq!(r.returns.len(), 3);
    for w in r.returns.windows(2) {
        let d = w[1].jd - w[0].jd;
        assert!((26.5..28.0).contains(&d), "{d}");
    }
}

#[test]
fn saturn_return_is_found_near_age_29() {
    let r = calculate_return(&ReturnRequest {
        natal: natal(),
        body: "Saturn".into(),
        start: tp(2018, 1, 1),
        count: 1,
        latitude: None,
        longitude: None,
        location_name: None,
        display_timezone: None,
    })
    .unwrap();
    let year: i32 = r.returns[0].label[0..4].parse().unwrap();
    assert!((2019..=2021).contains(&year), "{}", r.returns[0].label);
}

#[test]
fn secondary_progression_moves_the_sun_about_one_degree_per_year() {
    let p = calculate_progression(&ProgressionRequest {
        natal: natal(),
        target: tp(2020, 5, 15),
        kind: "secondary".into(),
        orb: 1.0,
    })
    .unwrap();
    assert!((p.age_years - 30.0).abs() < 0.05);
    assert!((p.solar_arc - 28.8).abs() < 0.5, "{}", p.solar_arc); // Mitte Mai–Juni läuft die Sonne langsam (~0,96°/Tag)
    let natal_sun = lon(&p.natal_chart, CelestialPoint::Sun);
    assert!(diff(lon(&p.progressed_chart, CelestialPoint::Sun), natal_sun + p.solar_arc) < 1e-6);
}

#[test]
fn solar_arc_shifts_everything_by_the_same_arc() {
    let p = calculate_progression(&ProgressionRequest {
        natal: natal(),
        target: tp(2020, 5, 15),
        kind: "solar_arc".into(),
        orb: 1.0,
    })
    .unwrap();
    for id in [CelestialPoint::Moon, CelestialPoint::Mars, CelestialPoint::Saturn] {
        let d = (lon(&p.progressed_chart, id) - lon(&p.natal_chart, id)).rem_euclid(360.0);
        assert!((d - p.solar_arc).abs() < 1e-6 || (d - p.solar_arc).abs() > 359.999);
    }
    assert!(diff(p.progressed_chart.angles.midheaven, p.natal_chart.angles.midheaven + p.solar_arc) < 1e-6);
}

#[test]
fn transit_events_are_ordered_and_exact_times_are_exact() {
    let n = natal();
    let res = search_transits(&TransitSearchRequest {
        natal: n.clone(),
        start: tp(2024, 1, 1),
        end: tp(2025, 1, 1),
        bodies: vec![],
        aspects: vec![],
        orb: 1.0,
        display_timezone: None,
        natal_points: vec![],
    })
    .unwrap();
    assert!(res.events.len() > 50, "{}", res.events.len());
    for e in &res.events {
        assert!(e.leave_jd >= e.enter_jd);
        for x in &e.exact_jds {
            assert!(*x >= e.enter_jd - 1e-6 && *x <= e.leave_jd + 1e-6);
        }
    }
    // Probe: der exakte Zeitpunkt wirklich exakt (Sonne ☌ Natal-Sonne ist genau ein Jahr nach der Geburt)
    let sun_return = res
        .events
        .iter()
        .find(|e| e.transit_body == "Sonne" && e.natal_point == "Sonne" && e.aspect_name == "Konjunktion")
        .expect("Sonnenrückkehr");
    let exact = sun_return.exact_jds[0];
    let chart_at = |jd: f64| {
        let d = sweph::date_from_julian_day(jd);
        let mut r = natal();
        r.year = d.year;
        r.month = d.month as i32;
        r.day = d.day as i32;
        r.timezone = None;
        r.timezone_offset = 0.0;
        r.hour = d.hour.floor() as u32;
        r.minute = ((d.hour - d.hour.floor()) * 60.0) as u32;
        r.second = Some((((d.hour * 60.0) - (d.hour * 60.0).floor()) * 60.0) as u32);
        calculate_chart(&r).unwrap()
    };
    let at = chart_at(exact);
    let natal_sun = lon(&calculate_chart(&n).unwrap(), CelestialPoint::Sun);
    assert!(diff(lon(&at, CelestialPoint::Sun), natal_sun) < 0.002);
}

#[test]
fn sun_ingress_into_aries_2024() {
    let ev = sky_events(&SkyEventsRequest {
        start: tp(2024, 3, 1),
        end: tp(2024, 4, 30),
        natal: None,
        display_timezone: None,
        kinds: vec!["ingress".into()],
        settings: None,
    })
    .unwrap();
    let aries = ev
        .iter()
        .find(|e| e.title.contains("Sonne") && e.title.contains("Widder"))
        .expect("Sonne in Widder");
    // 20.3.2024 ca. 03:06 UTC
    assert!(aries.label.starts_with("2024-03-20 03:0") || aries.label.starts_with("2024-03-20 03:1"), "{}", aries.label);
}

#[test]
fn moon_phases_and_eclipse_april_2024() {
    let ev = sky_events(&SkyEventsRequest {
        start: tp(2024, 3, 20),
        end: tp(2024, 4, 20),
        natal: None,
        display_timezone: None,
        kinds: vec!["phase".into(), "eclipse".into()],
        settings: None,
    })
    .unwrap();
    let full = ev.iter().find(|e| e.title.contains("Vollmond")).expect("Vollmond");
    assert!(full.label.starts_with("2024-03-25 07:"), "{}", full.label); // 25.3.2024 07:00 UTC
    let new = ev.iter().find(|e| e.title.contains("Neumond")).expect("Neumond");
    assert!(new.label.starts_with("2024-04-08 18:"), "{}", new.label); // 8.4.2024 18:21 UTC
    let solar = ev.iter().find(|e| e.kind == "eclipse" && e.title.contains("Sonnen")).expect("Sonnenfinsternis");
    assert!(solar.label.starts_with("2024-04-08 18:"), "{}", solar.label);
    assert!(solar.title.contains("total"), "{}", solar.title);
}

#[test]
fn mercury_stations_exist_in_a_year() {
    let ev = sky_events(&SkyEventsRequest {
        start: tp(2024, 1, 1),
        end: tp(2025, 1, 1),
        natal: None,
        display_timezone: None,
        kinds: vec!["station".into()],
        settings: None,
    })
    .unwrap();
    let merc = ev.iter().filter(|e| e.title.contains("Merkur")).count();
    assert_eq!(merc, 7); // 2.1. direkt, dann dreimal rückläufig + dreimal rechtläufig
}

#[test]
fn graphic_ephemeris_wraps_on_the_90_degree_dial() {
    let g = graphic_ephemeris(&GraphicEphemerisRequest {
        natal: natal(),
        start: tp(2024, 1, 1),
        end: tp(2024, 2, 1),
        bodies: vec!["Mars".into()],
        step_days: Some(1.0),
    })
    .unwrap();
    assert_eq!(g.series.len(), 1);
    assert!(g.series[0].dial.iter().all(|d| (0.0..90.0).contains(d)));
    assert!(!g.natal_lines.is_empty());
}

#[test]
fn invalid_forecast_dates_are_rejected() {
    let mut bad = tp(2024, 2, 30);
    assert!(bad.checked_jd_ut().is_err());
    bad = tp(2024, 13, 1);
    assert!(calculate_progression(&ProgressionRequest {
        natal: natal(), target: bad, kind: "secondary".into(), orb: 1.0,
    }).is_err());
}

#[test]
fn displayed_event_time_rolls_to_next_day() {
    let jd = astrorust::astrology::util::julian_day_ut(2024, 12, 31, 23.0 + 59.0 / 60.0 + 50.0 / 3600.0);
    assert_eq!(format_jd(jd, None), "2025-01-01 00:00 UTC");
    let historic = astrorust::astrology::util::julian_day_ut(1452, 4, 15, 12.0);
    assert_eq!(format_jd(historic, None), "1452-04-15 12:00 UTC");
}

#[test]
fn topocentric_moon_and_relocated_return_use_the_observer() {
    use astrorust::astrology::engine;
    let mut n = natal();
    let geocentric = calculate_chart(&n).unwrap();
    n.settings = Some(ChartSettings { topocentric: true, ..Default::default() });
    let topocentric = calculate_chart(&n).unwrap();
    assert!(diff(lon(&geocentric, CelestialPoint::Moon), lon(&topocentric, CelestialPoint::Moon)) > 0.05);
    {
        let _guard = engine::lock();
        sweph::set_topocentric(n.longitude, n.latitude, 0.0);
        let expected = sweph::calc_with(topocentric.julian_day, sweph::Body::Moon,
            sweph::Flags::SWISS | sweph::Flags::TOPOCENTRIC | sweph::Flags::EQUATORIAL).unwrap();
        let moon = topocentric.planets.iter().find(|p| p.id == CelestialPoint::Moon).unwrap();
        assert!((moon.declination - expected.latitude).abs() < 1e-8);
    }
    let r = calculate_return(&ReturnRequest {
        natal: n, body: "Moon".into(), start: tp(2024, 1, 1), count: 1,
        latitude: Some(-33.86), longitude: Some(151.21), location_name: Some("Sydney".into()), display_timezone: None,
    }).unwrap();
    assert!(diff(lon(&r.chart, CelestialPoint::Moon), lon(&topocentric, CelestialPoint::Moon)) < 1e-4);
}
