use crate::astrology::calculator::calculate_chart;
use crate::astrology::models::{
    AspectType, CelestialPoint, ChartRequest, ChartResponse, ChartSettings, TransitRequest, TransitResponse,
    TransitToNatalAspect,
};
use crate::astrology::util::{angle_diff, format_orb};

/// Punkt eines Horoskops als Aspektpartner (Planet oder Achse).
#[derive(Debug, Clone)]
pub struct PointRef {
    pub id: CelestialPoint,
    pub name: String,
    pub glyph: String,
    pub lon: f64,
    pub speed: f64,
}

/// Planeten (ohne Südknoten) und – wenn gewünscht – Aszendent und Medium Coeli.
pub fn chart_points(chart: &ChartResponse, with_angles: bool) -> Vec<PointRef> {
    let mut v: Vec<PointRef> = chart
        .planets
        .iter()
        .filter(|p| p.id != CelestialPoint::SouthNode)
        .map(|p| PointRef { id: p.id, name: p.name.clone(), glyph: p.glyph.clone(), lon: p.longitude, speed: p.speed })
        .collect();
    if with_angles {
        v.push(PointRef {
            id: CelestialPoint::Ascendant,
            name: "Aszendent".into(),
            glyph: "AC".into(),
            lon: chart.angles.ascendant,
            speed: 0.0,
        });
        v.push(PointRef {
            id: CelestialPoint::Midheaven,
            name: "Medium Coeli".into(),
            glyph: "MC".into(),
            lon: chart.angles.midheaven,
            speed: 0.0,
        });
    }
    v
}

pub const MAJOR_ASPECTS: [AspectType; 6] = [
    AspectType::Conjunction,
    AspectType::Opposition,
    AspectType::Trine,
    AspectType::Square,
    AspectType::Sextile,
    AspectType::Quincunx,
];

/// Aspekte zwischen zwei Punktmengen (Transit→Radix, Partner A→B, Progression→Radix …).
/// `first` ist der bewegte Partner (liefert `transit_*`), `second` der Bezugspunkt.
pub fn cross_aspects(
    first: &[PointRef],
    second: &[PointRef],
    aspect_types: &[AspectType],
    max_orb: f64,
) -> Vec<TransitToNatalAspect> {
    let mut out = Vec::new();
    for a in first {
        for b in second {
            let diff = angle_diff(a.lon, b.lon);
            for &asp in aspect_types {
                let target = asp.target_angle();
                let orb = (diff - target).abs();
                if orb > max_orb {
                    continue;
                }
                // Annäherung? Kleine Vorausrechnung mit den Tagesgeschwindigkeiten.
                let after = angle_diff(a.lon + a.speed * 0.01, b.lon + b.speed * 0.01);
                let applying = (after - target).abs() < orb;
                out.push(TransitToNatalAspect {
                    transit_point: a.id,
                    transit_name: a.name.clone(),
                    transit_glyph: a.glyph.clone(),
                    natal_point: b.id,
                    natal_name: b.name.clone(),
                    natal_glyph: b.glyph.clone(),
                    aspect_type: asp,
                    aspect_name: asp.name_de().to_string(),
                    aspect_glyph: asp.glyph().to_string(),
                    orb,
                    formatted_orb: format_orb(orb),
                    color_hex: asp.color_hex().to_string(),
                    is_applying: applying,
                });
                break;
            }
        }
    }
    out.sort_by(|x, y| x.orb.partial_cmp(&y.orb).unwrap_or(std::cmp::Ordering::Equal));
    out
}

/// Einstellungen des Radix, aber ohne die teuren Zusatzanalysen (das Transitrad wird oft neu berechnet).
pub fn light_settings(natal: &ChartRequest) -> ChartSettings {
    let mut s = natal.settings.clone().unwrap_or_default();
    s.analysis = false;
    s.fixed_stars = false;
    s
}

pub fn calculate_transits(req: &TransitRequest) -> Result<TransitResponse, String> {
    let natal_chart = calculate_chart(&req.natal)?;

    let transit_chart_req = ChartRequest {
        name: format!("Transite für {}", req.natal.name),
        year: req.transit_year,
        month: req.transit_month,
        day: req.transit_day,
        hour: req.transit_hour,
        minute: req.transit_minute,
        second: Some(0),
        timezone_offset: req.transit_timezone_offset,
        latitude: req.natal.latitude,
        longitude: req.natal.longitude,
        location_name: req.natal.location_name.clone(),
        house_system: req.natal.house_system,
        timezone: None,
        settings: Some(light_settings(&req.natal)),
    };
    let transit_chart = calculate_chart(&transit_chart_req)?;

    // Transit → Radix, inklusive Aszendent und MC des Radix
    let transit_aspects = cross_aspects(
        &chart_points(&transit_chart, false),
        &chart_points(&natal_chart, true),
        &MAJOR_ASPECTS,
        2.5,
    );

    Ok(TransitResponse { natal_chart, transit_chart, transit_aspects })
}
