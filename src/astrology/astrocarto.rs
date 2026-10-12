//! Astrokartografie: Planetenlinien (MC, IC, AC, DC) auf der Erdkarte und Orte nahe an Linien.
//!
//! Geometrie: Ein Planet mit Rektaszension α und Deklination δ steht am MC, wo die lokale
//! Sternzeit = α ist, also λ = α − GST. Auf- und Untergang bei der Breite φ: Stundenwinkel
//! H₀ = arccos(−tan φ · tan δ), λ_AC = α − H₀ − GST, λ_DC = α + H₀ − GST.

use crate::astrology::atlas::get_atlas;
use crate::astrology::calculator::{calculate_chart, resolve_time};
use crate::astrology::engine;
use crate::astrology::forecast::point_by_name;
use crate::astrology::models::*;
use crate::astrology::util::angle_diff;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AstroMapRequest {
    pub natal: ChartRequest,
    /// leer = Sonne bis Pluto, Chiron, Mondknoten
    #[serde(default)]
    pub bodies: Vec<String>,
    /// Orbis in Längengrad für Ortstreffer (Standard 2°)
    #[serde(default)]
    pub city_orb: Option<f64>,
    /// Breitenschritt der AC/DC-Kurven (Standard 2°)
    #[serde(default)]
    pub lat_step: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MapLine {
    pub body: String,
    pub glyph: String,
    /// "MC", "IC", "AC", "DC"
    pub kind: String,
    pub color_hex: String,
    /// Teilstücke als (Breite, Länge); am Datumswechsel getrennt
    pub segments: Vec<Vec<[f64; 2]>>,
    pub meaning: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CityHit {
    pub body: String,
    pub glyph: String,
    pub kind: String,
    /// Abstand zur Linie in Längengraden
    pub distance_deg: f64,
    pub meaning: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CityLines {
    pub city: String,
    pub country: String,
    pub latitude: f64,
    pub longitude: f64,
    pub hits: Vec<CityHit>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AstroMapResponse {
    pub natal_chart: ChartResponse,
    pub lines: Vec<MapLine>,
    pub cities: Vec<CityLines>,
}

fn planet_color(p: CelestialPoint) -> &'static str {
    use CelestialPoint as P;
    match p {
        P::Sun => "#eab308",
        P::Moon => "#cbd5e1",
        P::Mercury => "#a3e635",
        P::Venus => "#f472b6",
        P::Mars => "#ef4444",
        P::Jupiter => "#fb923c",
        P::Saturn => "#94a3b8",
        P::Uranus => "#22d3ee",
        P::Neptune => "#818cf8",
        P::Pluto => "#a855f7",
        P::Chiron => "#34d399",
        _ => "#e2e8f0",
    }
}

fn planet_theme(p: CelestialPoint) -> &'static str {
    use CelestialPoint as P;
    match p {
        P::Sun => "Vitalität, Selbstausdruck, Anerkennung",
        P::Moon => "Gefühle, Geborgenheit, Zugehörigkeit",
        P::Mercury => "Denken, Lernen, Handel, Austausch",
        P::Venus => "Liebe, Schönheit, Genuss, Harmonie",
        P::Mars => "Tatkraft, Mut, Konflikt, Leidenschaft",
        P::Jupiter => "Wachstum, Glück, Fülle, Weitblick",
        P::Saturn => "Struktur, Pflicht, Prüfung, Reife",
        P::Uranus => "Freiheit, Wandel, Überraschung",
        P::Neptune => "Inspiration, Hingabe, Auflösung, Illusion",
        P::Pluto => "Transformation, Macht, Tiefe",
        P::Chiron => "Wunde und Heilung, Lehre",
        _ => "Entwicklungsrichtung",
    }
}

fn angle_theme(kind: &str) -> &'static str {
    match kind {
        "MC" => "Beruf, Ruf und öffentliches Ansehen",
        "IC" => "Zuhause, Wurzeln, Privatleben",
        "AC" => "Persönlichkeit, Auftreten, Körper",
        _ => "Beziehungen, Partner, Begegnungen",
    }
}

fn meaning(p: CelestialPoint, kind: &str) -> String {
    format!("{} {} – {}: {} ({})", p.glyph(), p.name_de(), kind, angle_theme(kind), planet_theme(p))
}

fn split_segments(points: Vec<[f64; 2]>) -> Vec<Vec<[f64; 2]>> {
    let mut segs: Vec<Vec<[f64; 2]>> = Vec::new();
    let mut cur: Vec<[f64; 2]> = Vec::new();
    for p in points {
        if let Some(last) = cur.last() {
            if (p[1] - last[1]).abs() > 180.0 {
                if cur.len() > 1 {
                    segs.push(std::mem::take(&mut cur));
                } else {
                    cur.clear();
                }
            }
        }
        cur.push(p);
    }
    if cur.len() > 1 {
        segs.push(cur);
    }
    segs
}

fn wrap_lon(l: f64) -> f64 {
    let x = (l + 180.0).rem_euclid(360.0) - 180.0;
    if x == -180.0 { 180.0 } else { x }
}

/// Länge der Aufgangs-/Untergangslinie bei der Breite `lat`, falls der Planet dort auf- und untergeht.
fn rise_set_lon(ra: f64, dec: f64, gst_deg: f64, lat: f64, rising: bool) -> Option<f64> {
    let c = -(lat.to_radians().tan()) * dec.to_radians().tan();
    if !(-1.0..=1.0).contains(&c) {
        return None;
    }
    let h0 = c.acos().to_degrees();
    Some(wrap_lon(if rising { ra - h0 - gst_deg } else { ra + h0 - gst_deg }))
}

pub fn astro_map(req: &AstroMapRequest) -> Result<AstroMapResponse, String> {
    let natal = calculate_chart(&req.natal)?;
    let (jd, _, _) = resolve_time(&req.natal)?;
    let _g = engine::lock();
    let gst = engine::sidereal_time_hours(jd) * 15.0;

    let bodies: Vec<CelestialPoint> = if req.bodies.is_empty() {
        let mut v = CelestialPoint::classical().to_vec();
        v.push(CelestialPoint::Chiron);
        v
    } else {
        req.bodies.iter().filter_map(|b| point_by_name(b)).collect()
    };
    let step = req.lat_step.unwrap_or(2.0).clamp(0.5, 10.0);
    let orb = req.city_orb.unwrap_or(2.0).clamp(0.2, 10.0);

    struct Eq {
        body: CelestialPoint,
        ra: f64,
        dec: f64,
    }
    let mut eq = Vec::new();
    for b in bodies {
        let body = b.sweph_body();
        let pos = sweph::calc_with(jd, body, sweph::Flags::SWISS | sweph::Flags::EQUATORIAL);
        let (ra, dec) = match pos {
            Ok(p) => (p.longitude.rem_euclid(360.0), p.latitude),
            Err(_) => {
                // z. B. Chiron ohne Datei: aus ekliptikaler Länge/Breite des Horoskops umrechnen
                let Some(pl) = natal.planets.iter().find(|p| p.id == b) else { continue };
                let eps = engine::true_obliquity(jd);
                engine::ecliptic_to_equatorial(pl.longitude, pl.latitude, eps)
            }
        };
        eq.push(Eq { body: b, ra, dec });
    }

    let mut lines = Vec::new();
    for e in &eq {
        let mc_lon = wrap_lon(e.ra - gst);
        let ic_lon = wrap_lon(mc_lon + 180.0);
        for (kind, lon) in [("MC", mc_lon), ("IC", ic_lon)] {
            lines.push(MapLine {
                body: e.body.name_de().into(),
                glyph: e.body.glyph().into(),
                kind: kind.into(),
                color_hex: planet_color(e.body).into(),
                segments: vec![vec![[-85.0, lon], [85.0, lon]]],
                meaning: meaning(e.body, kind),
            });
        }
        for (kind, rising) in [("AC", true), ("DC", false)] {
            let mut pts = Vec::new();
            let mut lat = -80.0;
            while lat <= 80.0 + 1e-9 {
                if let Some(l) = rise_set_lon(e.ra, e.dec, gst, lat, rising) {
                    pts.push([lat, l]);
                }
                lat += step;
            }
            lines.push(MapLine {
                body: e.body.name_de().into(),
                glyph: e.body.glyph().into(),
                kind: kind.into(),
                color_hex: planet_color(e.body).into(),
                segments: split_segments(pts),
                meaning: meaning(e.body, kind),
            });
        }
    }

    // Orte nahe an Linien
    let mut cities = Vec::new();
    for c in get_atlas() {
        let mut hits = Vec::new();
        for e in &eq {
            let mc_lon = wrap_lon(e.ra - gst);
            let candidates = [
                ("MC", Some(mc_lon)),
                ("IC", Some(wrap_lon(mc_lon + 180.0))),
                ("AC", rise_set_lon(e.ra, e.dec, gst, c.latitude, true)),
                ("DC", rise_set_lon(e.ra, e.dec, gst, c.latitude, false)),
            ];
            for (kind, lon) in candidates {
                let Some(lon) = lon else { continue };
                let d = angle_diff(c.longitude, lon);
                if d <= orb {
                    hits.push(CityHit {
                        body: e.body.name_de().into(),
                        glyph: e.body.glyph().into(),
                        kind: kind.into(),
                        distance_deg: d,
                        meaning: meaning(e.body, kind),
                    });
                }
            }
        }
        if !hits.is_empty() {
            hits.sort_by(|a, b| a.distance_deg.partial_cmp(&b.distance_deg).unwrap_or(std::cmp::Ordering::Equal));
            cities.push(CityLines { city: c.name, country: c.country, latitude: c.latitude, longitude: c.longitude, hits });
        }
    }
    cities.sort_by(|a, b| {
        b.hits.len().cmp(&a.hits.len()).then(
            a.hits[0].distance_deg.partial_cmp(&b.hits[0].distance_deg).unwrap_or(std::cmp::Ordering::Equal),
        )
    });

    Ok(AstroMapResponse { natal_chart: natal, lines, cities })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rise_set_symmetry_and_circumpolar() {
        // Planet auf dem Himmelsäquator geht bei jeder Breite bei H0 = 90° auf
        let l = rise_set_lon(100.0, 0.0, 10.0, 50.0, true).unwrap();
        assert!((l - wrap_lon(100.0 - 90.0 - 10.0)).abs() < 1e-9);
        // Zirkumpolar: hohe Deklination, hohe Breite
        assert!(rise_set_lon(0.0, 80.0, 0.0, 70.0, true).is_none());
    }

    #[test]
    fn antimeridian_split() {
        let segs = split_segments(vec![[0.0, 170.0], [10.0, 179.0], [20.0, -179.0], [30.0, -170.0]]);
        assert_eq!(segs.len(), 2);
    }
}
