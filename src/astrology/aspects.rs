use crate::astrology::models::{AspectData, AspectType, CelestialPoint, ChartSettings, PlanetData};
use crate::astrology::util::format_orb;

pub fn calculate_aspects(planets: &[PlanetData]) -> Vec<AspectData> {
    calculate_aspects_with(planets, &ChartSettings::default())
}

pub fn calculate_aspects_with(planets: &[PlanetData], settings: &ChartSettings) -> Vec<AspectData> {
    // Reihenfolge der Prüfung (Hauptaspekte zuerst); nur die eingeschalteten Aspekte
    let order = [
        AspectType::Conjunction,
        AspectType::Opposition,
        AspectType::Trine,
        AspectType::Square,
        AspectType::Sextile,
        AspectType::Quincunx,
        AspectType::SemiSquare,
        AspectType::Sesquiquadrate,
        AspectType::SemiSextile,
        AspectType::Quintile,
    ];
    let aspect_types: Vec<AspectType> = order.iter().copied().filter(|t| settings.aspects.contains(t)).collect();

    let mut results = Vec::new();

    for i in 0..planets.len() {
        for j in (i + 1)..planets.len() {
            let p1 = &planets[i];
            let p2 = &planets[j];
            // Der Südknoten steht immer genau gegenüber dem Nordknoten und bringt keine eigenen Aspekte
            if p1.id == CelestialPoint::SouthNode || p2.id == CelestialPoint::SouthNode {
                continue;
            }

            let mut diff = (p1.longitude - p2.longitude).abs();
            if diff > 180.0 {
                diff = 360.0 - diff;
            }

            for &asp in aspect_types.iter() {
                let target = asp.target_angle();
                let orb = (diff - target).abs();

                // Orbis: Sonne/Mond bekommen einen Zuschlag; Knoten, Chiron, Lilith und Asteroiden
                // (ohne Sonne/Mond) werden enger gefasst, mindestens aber 1°.
                let is_luminary = |id: CelestialPoint| matches!(id, CelestialPoint::Sun | CelestialPoint::Moon);
                let mut max_orb = settings.orb_for(asp);
                if is_luminary(p1.id) || is_luminary(p2.id) {
                    max_orb += settings.luminary_bonus;
                } else if p1.id.is_sensitive_point() || p2.id.is_sensitive_point() {
                    max_orb = (max_orb - settings.minor_point_reduction).max(1.0);
                }

                if orb <= max_orb {
                    let formatted_orb = format_orb(orb);

                    // Determine applying vs separating:
                    // If p1 is faster than p2, check if distance to exact is decreasing
                    let is_applying = {
                        // longitudinal order
                        let raw_dist = (p1.longitude - p2.longitude).rem_euclid(360.0);
                        let rel_speed = p1.speed - p2.speed;
                        if raw_dist <= 180.0 {
                            if raw_dist < target {
                                rel_speed > 0.0
                            } else {
                                rel_speed < 0.0
                            }
                        } else {
                            let inv_dist = 360.0 - raw_dist;
                            if inv_dist < target {
                                rel_speed < 0.0
                            } else {
                                rel_speed > 0.0
                            }
                        }
                    };

                    results.push(AspectData {
                        point_a: p1.id,
                        point_a_name: p1.name.clone(),
                        point_a_glyph: p1.glyph.clone(),
                        point_b: p2.id,
                        point_b_name: p2.name.clone(),
                        point_b_glyph: p2.glyph.clone(),
                        aspect_type: asp,
                        aspect_name: asp.name_de().to_string(),
                        aspect_glyph: asp.glyph().to_string(),
                        actual_angle: diff,
                        target_angle: target,
                        orb,
                        formatted_orb,
                        is_applying,
                        color_hex: asp.color_hex().to_string(),
                    });
                    break; // Pick the best matching aspect for this pair
                }
            }
        }
    }

    // Sort by tightest orb first
    results.sort_by(|a, b| a.orb.partial_cmp(&b.orb).unwrap_or(std::cmp::Ordering::Equal));
    results
}
