use crate::astrology::calculator::calculate_chart;
use crate::astrology::models::{
    AspectType, ChartRequest, TransitRequest, TransitResponse, TransitToNatalAspect,
};

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
    };
    let transit_chart = calculate_chart(&transit_chart_req)?;

    // Calculate Transit-to-Natal aspects
    let aspect_types = [
        AspectType::Conjunction,
        AspectType::Opposition,
        AspectType::Trine,
        AspectType::Square,
        AspectType::Sextile,
        AspectType::Quincunx,
    ];

    let mut transit_aspects = Vec::new();

    for t_planet in &transit_chart.planets {
        for n_planet in &natal_chart.planets {
            let mut diff = (t_planet.longitude - n_planet.longitude).abs();
            if diff > 180.0 {
                diff = 360.0 - diff;
            }

            for &asp in &aspect_types {
                let target = asp.target_angle();
                let orb = (diff - target).abs();

                // Transit aspects typically have an orb of 2.0° - 3.0°
                if orb <= 2.5 {
                    let deg = orb.floor() as u32;
                    let min = ((orb - orb.floor()) * 60.0).round() as u32;
                    let formatted_orb = format!("{:02}°{:02}'", deg, min);

                    transit_aspects.push(TransitToNatalAspect {
                        transit_point: t_planet.id,
                        transit_name: t_planet.name.clone(),
                        transit_glyph: t_planet.glyph.clone(),
                        natal_point: n_planet.id,
                        natal_name: n_planet.name.clone(),
                        natal_glyph: n_planet.glyph.clone(),
                        aspect_type: asp,
                        aspect_name: asp.name_de().to_string(),
                        aspect_glyph: asp.glyph().to_string(),
                        orb,
                        formatted_orb,
                        color_hex: asp.color_hex().to_string(),
                    });
                    break;
                }
            }
        }
    }

    transit_aspects.sort_by(|a, b| a.orb.partial_cmp(&b.orb).unwrap_or(std::cmp::Ordering::Equal));

    Ok(TransitResponse {
        natal_chart,
        transit_chart,
        transit_aspects,
    })
}
