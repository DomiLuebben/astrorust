use crate::astrology::calculator::{
    assemble_chart, build_chart, calculate_chart, resolve_time, ChartInput, ChartMeta, HouseSet, PointPos,
};
use crate::astrology::engine;
use crate::astrology::models::{
    AspectType, CelestialPoint, ChartRequest, ChartResponse, HouseSystemChoice,
    InterpretationSection, SynastryRequest, SynastryResponse, TransitToNatalAspect,
};
use crate::astrology::transits::{chart_points, cross_aspects, light_settings, PointRef, MAJOR_ASPECTS};
use crate::astrology::util::{angle_diff, normalize_deg, signed_diff};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OverlayEntry {
    pub planet: String,
    pub glyph: String,
    pub sign_name: String,
    /// Haus im Horoskop der anderen Person
    pub house: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GridCell {
    pub aspect_name: String,
    pub aspect_glyph: String,
    pub color_hex: String,
    pub formatted_orb: String,
    pub orb: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AspectGrid {
    /// Zeilen: Punkte von Person A, Spalten: Punkte von Person B
    pub rows: Vec<String>,
    pub row_glyphs: Vec<String>,
    pub cols: Vec<String>,
    pub col_glyphs: Vec<String>,
    pub cells: Vec<Vec<Option<GridCell>>>,
}

pub fn calculate_synastry(req: &SynastryRequest) -> Result<SynastryResponse, String> {
    let chart_a = calculate_chart(&req.person_a)?;
    let chart_b = calculate_chart(&req.person_b)?;

    let pts_a = chart_points(&chart_a, true);
    let pts_b = chart_points(&chart_b, true);
    let cross = cross_aspects(&pts_a, &pts_b, &MAJOR_ASPECTS, 4.0);

    let grid = build_grid(&pts_a, &pts_b, &cross);
    let overlay_a_in_b = overlay(&chart_a, &chart_b);
    let overlay_b_in_a = overlay(&chart_b, &chart_a);

    let composite = composite_chart(&req.person_a, &req.person_b, &chart_a, &chart_b).ok();
    let davison = davison_chart(&req.person_a, &req.person_b).ok();

    let compatibility_notes = compatibility_notes(&chart_a, &chart_b, &cross);

    Ok(SynastryResponse {
        chart_a,
        chart_b,
        cross_aspects: cross,
        compatibility_notes,
        composite_chart: composite,
        davison_chart: davison,
        overlay_a_in_b,
        overlay_b_in_a,
        grid,
    })
}

fn overlay(from: &ChartResponse, into: &ChartResponse) -> Vec<OverlayEntry> {
    let cusps: Vec<f64> = into.houses.iter().map(|h| h.longitude).collect();
    let mut cusp_arr = [0.0; 12];
    for (i, c) in cusps.iter().enumerate().take(12) {
        cusp_arr[i] = *c;
    }
    from.planets
        .iter()
        .filter(|p| p.id != CelestialPoint::SouthNode)
        .map(|p| OverlayEntry {
            planet: p.name.clone(),
            glyph: p.glyph.clone(),
            sign_name: p.sign_name.clone(),
            house: crate::astrology::calculator::determine_house(p.longitude, &cusp_arr),
        })
        .collect()
}

fn build_grid(a: &[PointRef], b: &[PointRef], cross: &[TransitToNatalAspect]) -> AspectGrid {
    let mut cells = vec![vec![None; b.len()]; a.len()];
    for asp in cross {
        let (Some(i), Some(j)) = (
            a.iter().position(|p| p.id == asp.transit_point),
            b.iter().position(|p| p.id == asp.natal_point),
        ) else {
            continue;
        };
        cells[i][j] = Some(GridCell {
            aspect_name: asp.aspect_name.clone(),
            aspect_glyph: asp.aspect_glyph.clone(),
            color_hex: asp.color_hex.clone(),
            formatted_orb: asp.formatted_orb.clone(),
            orb: asp.orb,
        });
    }
    AspectGrid {
        rows: a.iter().map(|p| p.name.clone()).collect(),
        row_glyphs: a.iter().map(|p| p.glyph.clone()).collect(),
        cols: b.iter().map(|p| p.name.clone()).collect(),
        col_glyphs: b.iter().map(|p| p.glyph.clone()).collect(),
        cells,
    }
}

/// Mittelpunkt zweier Längen auf dem kürzeren Bogen.
pub fn midpoint_lon(a: f64, b: f64) -> f64 {
    normalize_deg(a + signed_diff(b, a) / 2.0)
}

/// Composite-Horoskop (Halbsummen-Methode). Häuser: MC als Mittelpunkt der MCs, Aszendent
/// daraus abgeleitet für die mittlere geografische Breite (Hand/„derived Ascendant“).
pub fn composite_chart(
    ra: &ChartRequest,
    rb: &ChartRequest,
    a: &ChartResponse,
    b: &ChartResponse,
) -> Result<ChartResponse, String> {
    let settings = light_settings(ra);
    let _g = engine::lock();

    let mut points = Vec::new();
    for pa in &a.planets {
        let Some(pb) = b.planets.iter().find(|p| p.id == pa.id) else { continue };
        let lon = if pa.id == CelestialPoint::SouthNode {
            normalize_deg(midpoint_lon(
                a.planets.iter().find(|p| p.id == CelestialPoint::TrueNode).map(|p| p.longitude).unwrap_or(pa.longitude),
                b.planets.iter().find(|p| p.id == CelestialPoint::TrueNode).map(|p| p.longitude).unwrap_or(pb.longitude),
            ) + 180.0)
        } else {
            midpoint_lon(pa.longitude, pb.longitude)
        };
        let speed = (pa.speed + pb.speed) / 2.0;
        points.push(PointPos {
            id: pa.id,
            lon,
            lat: (pa.latitude + pb.latitude) / 2.0,
            dist: (pa.distance + pb.distance) / 2.0,
            speed,
            retro: speed < 0.0,
            decl: (pa.declination + pb.declination) / 2.0,
        });
    }

    let mc = midpoint_lon(a.angles.midheaven, b.angles.midheaven);
    let lat = (ra.latitude + rb.latitude) / 2.0;
    let jd_mid = (a.julian_day + b.julian_day) / 2.0;
    let eps = engine::true_obliquity(jd_mid);
    // MC → Rektaszension (Ekliptikbreite 0)
    let armc = (mc.to_radians().sin() * eps.to_radians().cos()).atan2(mc.to_radians().cos()).to_degrees().rem_euclid(360.0);
    let system = ra.house_system.unwrap_or(HouseSystemChoice::Placidus);
    let (cusps, asc, mc_calc, vertex) = engine::houses_from_armc(armc, lat, eps, system.code());

    let meta = ChartMeta {
        name: format!("Composite {} & {}", a.name, b.name),
        date_time: "Halbsummen-Horoskop".into(),
        location_name: format!("{:.2}°, {:.2}° (Mittel)", lat, (ra.longitude + rb.longitude) / 2.0),
        latitude: lat,
        longitude: (ra.longitude + rb.longitude) / 2.0,
        julian_day: jd_mid,
        house_system_label: format!("{} (abgeleitet aus Composite-MC)", system.name_de()),
        timezone_info: None,
        ayanamsa_name: a.ayanamsa_name.clone(),
        ayanamsa_value: a.ayanamsa_value,
        ephemeris_files: a.ephemeris_files,
    };
    let houses = HouseSet { cusps, ascendant: asc, midheaven: mc_calc, vertex };
    let mut comp_settings = settings.clone();
    comp_settings.analysis = true;
    comp_settings.fixed_stars = false;
    Ok(assemble_chart(&meta, points, &houses, &comp_settings))
}

/// Davison-Horoskop (Zeit- und Ortsmittelpunkt).
pub fn davison_chart(ra: &ChartRequest, rb: &ChartRequest) -> Result<ChartResponse, String> {
    let (jd_a, _, _) = resolve_time(ra)?;
    let (jd_b, _, _) = resolve_time(rb)?;
    let jd_mid = (jd_a + jd_b) / 2.0;
    let lat = (ra.latitude + rb.latitude) / 2.0;
    // Längenmittel über Einheitsvektoren (wegen ±180°)
    let (x, y) = (
        ra.longitude.to_radians().cos() + rb.longitude.to_radians().cos(),
        ra.longitude.to_radians().sin() + rb.longitude.to_radians().sin(),
    );
    let lon = if x.abs() < 1e-12 && y.abs() < 1e-12 { ra.longitude } else { y.atan2(x).to_degrees() };

    let mut settings = light_settings(ra);
    settings.analysis = true;
    let date = sweph::date_from_julian_day(jd_mid);
    build_chart(&ChartInput {
        name: format!("Davison {} & {}", ra.name, rb.name),
        jd_ut: jd_mid,
        latitude: lat,
        longitude: lon,
        house_system: ra.house_system.unwrap_or(HouseSystemChoice::Placidus),
        settings: &settings,
        date_time_label: format!(
            "{:04}-{:02}-{:02} {:02}:{:02} UTC (Zeitmittel)",
            date.year,
            date.month,
            date.day,
            date.hour.floor() as u32,
            ((date.hour - date.hour.floor()) * 60.0).floor() as u32
        ),
        location_name: format!("{:.2}°, {:.2}° (Mittel)", lat, lon),
        timezone_info: None,
    })
}

fn has<'a>(cross: &'a [TransitToNatalAspect], p: CelestialPoint, q: CelestialPoint, kinds: &[AspectType]) -> Option<&'a TransitToNatalAspect> {
    cross.iter().find(|a| {
        ((a.transit_point == p && a.natal_point == q) || (a.transit_point == q && a.natal_point == p))
            && kinds.contains(&a.aspect_type)
    })
}

fn note(notes: &mut Vec<InterpretationSection>, title: String, subtitle: &str, text: String, keywords: &[&str]) {
    notes.push(InterpretationSection {
        title,
        subtitle: subtitle.into(),
        text,
        keywords: keywords.iter().map(|s| s.to_string()).collect(),
    });
}

fn compatibility_notes(a: &ChartResponse, b: &ChartResponse, cross: &[TransitToNatalAspect]) -> Vec<InterpretationSection> {
    use CelestialPoint as P;
    let soft = [AspectType::Conjunction, AspectType::Trine, AspectType::Sextile];
    let hard = [AspectType::Square, AspectType::Opposition];
    let any = [AspectType::Conjunction, AspectType::Trine, AspectType::Sextile, AspectType::Square, AspectType::Opposition];
    let mut notes = Vec::new();


    // Sonne–Mond (beide Richtungen)
    if let Some(asp) = has(cross, P::Sun, P::Moon, &any) {
        let harmonious = soft.contains(&asp.aspect_type);
        note(&mut notes, 
            format!("Sonne–Mond ({})", asp.aspect_name),
            "Klassischer Partnerschafts-Schlüssel",
            if harmonious {
                format!("Die Wesensenergie von {} und die Gefühlswelt von {} stützen einander: Man fühlt sich verstanden und gesehen.", a.name, b.name)
            } else {
                format!("Die Wesensenergie und die Gefühlswelt von {} und {} reiben sich: Das Verhältnis von Handeln und Fühlen muss immer wieder ausgehandelt werden.", a.name, b.name)
            },
            &["Seelenverwandtschaft", "Verständnis", "Grundbedürfnisse"],
        );
    }
    if let Some(asp) = has(cross, P::Venus, P::Mars, &any) {
        note(&mut notes, 
            format!("Venus–Mars ({})", asp.aspect_name),
            "Anziehung und Leidenschaft",
            if soft.contains(&asp.aspect_type) {
                "Spürbare Anziehung; die weibliche und männliche Seite ergänzen sich lebendig.".into()
            } else {
                "Starke Funken, aber auch Reibung: Anziehung und Konkurrenz liegen nah beieinander.".into()
            },
            &["Leidenschaft", "Anziehung", "Dynamik"],
        );
    }
    if let Some(asp) = has(cross, P::Venus, P::Jupiter, &soft) {
        note(&mut notes, 
            format!("Venus–Jupiter ({})", asp.aspect_name),
            "Wohlwollen und Großzügigkeit",
            "Ein Aspekt von Wärme, Großzügigkeit und gemeinsamer Lebensfreude.".into(),
            &["Wohlwollen", "Freude", "Wachstum"],
        );
    }
    if let Some(asp) = has(cross, P::Moon, P::Moon, &any) {
        note(&mut notes, 
            format!("Mond–Mond ({})", asp.aspect_name),
            "Gefühlsrhythmus",
            if soft.contains(&asp.aspect_type) {
                "Ähnliche emotionale Rhythmen: Stimmungen und Bedürfnisse werden intuitiv geteilt.".into()
            } else {
                "Unterschiedliche emotionale Rhythmen: Nähe- und Rückzugsbedürfnis müssen abgestimmt werden.".into()
            },
            &["Gefühle", "Alltag", "Geborgenheit"],
        );
    }
    for (p, label) in [(P::Sun, "Sonne"), (P::Moon, "Mond"), (P::Venus, "Venus")] {
        if let Some(asp) = has(cross, P::Saturn, p, &any) {
            note(&mut notes, 
                format!("Saturn–{} ({})", label, asp.aspect_name),
                "Bindung und Verantwortung",
                if soft.contains(&asp.aspect_type) {
                    format!("Saturn stützt hier die {}-Themen des anderen: Verlässlichkeit, Beständigkeit, gemeinsamer Aufbau.", label)
                } else {
                    format!("Saturn fordert und begrenzt die {}-Themen des anderen: Prüfungen, aber auch tiefe Verbindlichkeit.", label)
                },
                &["Verbindlichkeit", "Beständigkeit", "Prüfung"],
            );
            break;
        }
    }
    let asc_hits: Vec<&TransitToNatalAspect> = cross
        .iter()
        .filter(|x| x.aspect_type == AspectType::Conjunction && x.orb <= 3.0)
        .filter(|x| matches!(x.transit_point, P::Ascendant | P::Midheaven) || matches!(x.natal_point, P::Ascendant | P::Midheaven))
        .collect();
    for asp in asc_hits.iter().take(2) {
        note(&mut notes, 
            format!("{} ☌ {}", asp.transit_name, asp.natal_name),
            "Kontakt mit einer Achse",
            "Planetenkontakt mit Aszendent oder MC des anderen: starker Wiedererkennungseffekt, die Person wird direkt „gespürt“.".into(),
            &["Resonanz", "Wiedererkennung"],
        );
    }
    let _ = (hard, angle_diff(0.0, 0.0));
    if notes.is_empty() {
        note(&mut notes, 
            "Individuelle Begegnung".into(),
            "Vielschichtige Beziehungsdynamik",
            "Die Horoskope zeigen ein nuanciertes Zusammenspiel mit vielen individuellen Anknüpfungspunkten.".into(),
            &["Partnerschaft", "Wachstum"],
        );
    }
    notes
}
