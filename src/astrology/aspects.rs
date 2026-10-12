use crate::astrology::models::{AspectData, AspectType, CelestialPoint, PlanetData};
use crate::astrology::util::format_orb;

pub fn calculate_aspects(planets: &[PlanetData]) -> Vec<AspectData> {
    let aspect_types = [
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

    let mut results = Vec::new();

    for i in 0..planets.len() {
        for j in (i + 1)..planets.len() {
            let p1 = &planets[i];
            let p2 = &planets[j];

            let mut diff = (p1.longitude - p2.longitude).abs();
            if diff > 180.0 {
                diff = 360.0 - diff;
            }

            for &asp in &aspect_types {
                let target = asp.target_angle();
                let orb = (diff - target).abs();

                // Orbis: Sonne und Mond bekommen +1,5°; Mondknoten, Chiron und Lilith
                // (ohne Sonne/Mond) werden um 1,5° enger gefasst, mindestens aber 1°.
                let is_luminary = |id: CelestialPoint| matches!(id, CelestialPoint::Sun | CelestialPoint::Moon);
                let is_minor = |id: CelestialPoint| {
                    matches!(id, CelestialPoint::TrueNode | CelestialPoint::Chiron | CelestialPoint::Lilith)
                };
                let mut max_orb = asp.default_orb();
                if is_luminary(p1.id) || is_luminary(p2.id) {
                    max_orb += 1.5;
                } else if is_minor(p1.id) || is_minor(p2.id) {
                    max_orb = (max_orb - 1.5).max(1.0);
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
