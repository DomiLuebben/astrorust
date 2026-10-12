use crate::astrology::calculator::calculate_chart;
use crate::astrology::util::format_orb;
use crate::astrology::models::{
    AspectType, CelestialPoint, InterpretationSection, SynastryRequest, SynastryResponse,
    TransitToNatalAspect,
};

pub fn calculate_synastry(req: &SynastryRequest) -> Result<SynastryResponse, String> {
    let chart_a = calculate_chart(&req.person_a)?;
    let chart_b = calculate_chart(&req.person_b)?;

    let aspect_types = [
        AspectType::Conjunction,
        AspectType::Opposition,
        AspectType::Trine,
        AspectType::Square,
        AspectType::Sextile,
        AspectType::Quincunx,
    ];

    let mut cross_aspects = Vec::new();

    for pa in &chart_a.planets {
        for pb in &chart_b.planets {
            let mut diff = (pa.longitude - pb.longitude).abs();
            if diff > 180.0 {
                diff = 360.0 - diff;
            }

            for &asp in &aspect_types {
                let target = asp.target_angle();
                let orb = (diff - target).abs();

                if orb <= 4.0 {
                    let formatted_orb = format_orb(orb);

                    cross_aspects.push(TransitToNatalAspect {
                        transit_point: pa.id,
                        transit_name: pa.name.clone(),
                        transit_glyph: pa.glyph.clone(),
                        natal_point: pb.id,
                        natal_name: pb.name.clone(),
                        natal_glyph: pb.glyph.clone(),
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

    cross_aspects.sort_by(|a, b| a.orb.partial_cmp(&b.orb).unwrap_or(std::cmp::Ordering::Equal));

    // Generate synastry compatibility notes
    let mut compatibility_notes = Vec::new();

    // Check Sun - Moon connections
    for asp in &cross_aspects {
        if (asp.transit_point == CelestialPoint::Sun && asp.natal_point == CelestialPoint::Moon)
            || (asp.transit_point == CelestialPoint::Moon && asp.natal_point == CelestialPoint::Sun)
        {
            compatibility_notes.push(InterpretationSection {
                title: format!("Sonne-Mond Resonanz ({})", asp.aspect_name),
                subtitle: "Klassischer Partnerschafts-Schlüssel".into(),
                text: format!(
                    "Eine tiefe seelische Verbindung: Die Wesensenergie von {} harmoniert unmittelbar mit der emotionalen Gefühlswelt von {}.",
                    chart_a.name, chart_b.name
                ),
                keywords: vec!["Seelenverwandtschaft".into(), "Harmonie".into(), "Verständnis".into()],
            });
            break;
        }
    }

    // Check Venus - Mars connections
    for asp in &cross_aspects {
        if (asp.transit_point == CelestialPoint::Venus && asp.natal_point == CelestialPoint::Mars)
            || (asp.transit_point == CelestialPoint::Mars && asp.natal_point == CelestialPoint::Venus)
        {
            compatibility_notes.push(InterpretationSection {
                title: format!("Venus-Mars Anziehung ({})", asp.aspect_name),
                subtitle: "Erotische & leidenschaftliche Chemie".into(),
                text: "Starke magnetische Anziehungskraft und spürbare Funken zwischen den Partnern. Die weiblichen und männlichen Pole ergänzen sich dynamisch.".into(),
                keywords: vec!["Leidenschaft".into(), "Anziehung".into(), "Dynamik".into()],
            });
            break;
        }
    }

    if compatibility_notes.is_empty() {
        compatibility_notes.push(InterpretationSection {
            title: "Individuelle Begegnung".into(),
            subtitle: "Vielschichtige Beziehungsdynamik".into(),
            text: "Die Horoskope zeigen ein nuanciertes Zusammenspiel verschiedener Lebensbereiche mit vielen individuellen Anknüpfungspunkten.".into(),
            keywords: vec!["Partnerschaft".into(), "Wachstum".into()],
        });
    }

    Ok(SynastryResponse {
        chart_a,
        chart_b,
        cross_aspects,
        compatibility_notes,
    })
}
