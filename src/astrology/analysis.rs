//! Zusatzanalysen zu einem berechneten Horoskop: klassische Würden und Herrscherketten,
//! Aspektfiguren, Halbsummen / 90°-Scheibe, arabische Lose, Fixsterne, Parallelen,
//! Hemisphären-/Quadrantenverteilung und Horoskopform.

use crate::astrology::engine;
use crate::astrology::models::*;
use crate::astrology::util::{angle_diff, normalize_deg, split_dm};
use serde::{Deserialize, Serialize};

// ──────────────────────────────────────────────────────────────────────────
// Ausgabetypen
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AnalysisData {
    pub is_diurnal: bool,
    pub dignities: Vec<EssentialDignity>,
    pub receptions: Vec<Reception>,
    pub dispositors: Vec<DispositorEntry>,
    pub final_dispositor: Option<String>,
    pub patterns: Vec<AspectPattern>,
    pub chart_shape: Option<ChartShape>,
    pub distribution: Distribution,
    pub midpoints: Vec<MidpointData>,
    pub midpoint_hits: Vec<MidpointHit>,
    pub dial90: Vec<DialEntry>,
    pub lots: Vec<LotData>,
    pub fixed_stars: Vec<FixedStarContact>,
    pub parallels: Vec<ParallelData>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EssentialDignity {
    pub planet: CelestialPoint,
    pub planet_name: String,
    pub glyph: String,
    pub sign_name: String,
    /// Domizil-Herrscher des Zeichens
    pub domicile_ruler: String,
    pub exaltation_ruler: Option<String>,
    pub triplicity_day: String,
    pub triplicity_night: String,
    pub triplicity_participating: String,
    pub term_ruler: String,
    pub face_ruler: String,
    pub in_domicile: bool,
    pub in_exaltation: bool,
    pub in_triplicity: bool,
    pub in_term: bool,
    pub in_face: bool,
    pub in_detriment: bool,
    pub in_fall: bool,
    pub peregrine: bool,
    /// Summe nach William Lilly (+5/+4/+3/+2/+1, −5/−4, peregrin −5)
    pub score: i32,
    pub summary: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Reception {
    pub planet_a: String,
    pub planet_b: String,
    pub kind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DispositorEntry {
    pub planet: String,
    pub glyph: String,
    pub sign_name: String,
    pub ruler: String,
    /// Kette bis zum Endpunkt oder Zyklus, z. B. "Mars → Sonne → Venus ↻"
    pub chain: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AspectPattern {
    pub kind: String,
    pub name: String,
    pub points: Vec<String>,
    pub glyphs: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChartShape {
    pub name: String,
    pub description: String,
    pub span_degrees: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Distribution {
    /// Planeten (Sonne–Pluto) über dem Horizont (Häuser 7–12) / darunter (1–6)
    pub above_horizon: u32,
    pub below_horizon: u32,
    /// Östliche Hälfte (Häuser 10–12, 1–3) / westliche (4–9)
    pub eastern: u32,
    pub western: u32,
    /// Quadranten I–IV (Häuser 1–3, 4–6, 7–9, 10–12)
    pub quadrants: [u32; 4],
    pub dominant_house_group: String,
    /// Planeten je Haus 1–12
    pub per_house: [u32; 12],
    /// Tradition: Anzahl Planeten je Zeichen
    pub per_sign: [u32; 12],
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MidpointData {
    pub a: String,
    pub b: String,
    pub label: String,
    pub longitude: f64,
    pub formatted: String,
    pub sign_name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MidpointHit {
    pub point: String,
    pub point_glyph: String,
    pub a: String,
    pub b: String,
    pub label: String,
    /// 0, 90 oder 180: Winkel zwischen Punkt und Halbsumme (90°-Scheibe)
    pub relation_degrees: u32,
    pub orb: f64,
    pub formatted_orb: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DialEntry {
    pub name: String,
    pub glyph: String,
    /// Position in der 90°-Scheibe (0–90)
    pub position: f64,
    pub longitude: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LotData {
    pub key: String,
    pub name: String,
    pub formula: String,
    pub longitude: f64,
    pub formatted: String,
    pub sign_name: String,
    pub house: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FixedStarContact {
    pub star: String,
    pub star_longitude: f64,
    pub star_formatted: String,
    pub contact: String,
    pub contact_glyph: String,
    pub orb: f64,
    pub formatted_orb: String,
    pub nature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelData {
    pub planet_a: String,
    pub planet_b: String,
    pub kind: String,
    pub orb: f64,
    pub formatted_orb: String,
}

// ──────────────────────────────────────────────────────────────────────────
// Klassische Tabellen
// ──────────────────────────────────────────────────────────────────────────

use CelestialPoint as P;
use ZodiacSign as Z;

pub const TRADITIONAL: [CelestialPoint; 7] = [P::Sun, P::Moon, P::Mercury, P::Venus, P::Mars, P::Jupiter, P::Saturn];

fn sign_index(s: ZodiacSign) -> usize {
    s as usize
}

/// Domizil-Herrscher (traditionell).
pub fn domicile_ruler(s: ZodiacSign) -> CelestialPoint {
    match s {
        Z::Aries | Z::Scorpio => P::Mars,
        Z::Taurus | Z::Libra => P::Venus,
        Z::Gemini | Z::Virgo => P::Mercury,
        Z::Cancer => P::Moon,
        Z::Leo => P::Sun,
        Z::Sagittarius | Z::Pisces => P::Jupiter,
        Z::Capricorn | Z::Aquarius => P::Saturn,
    }
}

/// Moderner Herrscher (Uranus/Neptun/Pluto für Wassermann/Fische/Skorpion).
pub fn modern_ruler(s: ZodiacSign) -> CelestialPoint {
    match s {
        Z::Scorpio => P::Pluto,
        Z::Aquarius => P::Uranus,
        Z::Pisces => P::Neptune,
        other => domicile_ruler(other),
    }
}

pub fn exaltation_ruler(s: ZodiacSign) -> Option<CelestialPoint> {
    match s {
        Z::Aries => Some(P::Sun),
        Z::Taurus => Some(P::Moon),
        Z::Virgo => Some(P::Mercury),
        Z::Pisces => Some(P::Venus),
        Z::Capricorn => Some(P::Mars),
        Z::Cancer => Some(P::Jupiter),
        Z::Libra => Some(P::Saturn),
        _ => None,
    }
}

fn detriment_signs(p: CelestialPoint) -> &'static [ZodiacSign] {
    match p {
        P::Sun => &[Z::Aquarius],
        P::Moon => &[Z::Capricorn],
        P::Mercury => &[Z::Sagittarius, Z::Pisces],
        P::Venus => &[Z::Aries, Z::Scorpio],
        P::Mars => &[Z::Taurus, Z::Libra],
        P::Jupiter => &[Z::Gemini, Z::Virgo],
        P::Saturn => &[Z::Cancer, Z::Leo],
        _ => &[],
    }
}

fn fall_sign(p: CelestialPoint) -> Option<ZodiacSign> {
    match p {
        P::Sun => Some(Z::Libra),
        P::Moon => Some(Z::Scorpio),
        P::Mercury => Some(Z::Pisces),
        P::Venus => Some(Z::Virgo),
        P::Mars => Some(Z::Cancer),
        P::Jupiter => Some(Z::Capricorn),
        P::Saturn => Some(Z::Aries),
        _ => None,
    }
}

/// Triplizitätsherrscher (Dorotheus): (Tag, Nacht, beteiligt)
fn triplicity(s: ZodiacSign) -> (CelestialPoint, CelestialPoint, CelestialPoint) {
    match s.element() {
        Element::Fire => (P::Sun, P::Jupiter, P::Saturn),
        Element::Earth => (P::Venus, P::Moon, P::Mars),
        Element::Air => (P::Saturn, P::Mercury, P::Jupiter),
        Element::Water => (P::Venus, P::Mars, P::Moon),
    }
}

/// Ägyptische Grenzen: (obere Gradgrenze, Herrscher) je Zeichen
const TERMS: [[(f64, CelestialPoint); 5]; 12] = [
    [(6.0, P::Jupiter), (12.0, P::Venus), (20.0, P::Mercury), (25.0, P::Mars), (30.0, P::Saturn)],
    [(8.0, P::Venus), (14.0, P::Mercury), (22.0, P::Jupiter), (27.0, P::Saturn), (30.0, P::Mars)],
    [(6.0, P::Mercury), (12.0, P::Jupiter), (17.0, P::Venus), (24.0, P::Mars), (30.0, P::Saturn)],
    [(7.0, P::Mars), (13.0, P::Venus), (19.0, P::Mercury), (26.0, P::Jupiter), (30.0, P::Saturn)],
    [(6.0, P::Jupiter), (11.0, P::Venus), (18.0, P::Saturn), (24.0, P::Mercury), (30.0, P::Mars)],
    [(7.0, P::Mercury), (17.0, P::Venus), (21.0, P::Jupiter), (28.0, P::Mars), (30.0, P::Saturn)],
    [(6.0, P::Saturn), (14.0, P::Mercury), (21.0, P::Jupiter), (28.0, P::Venus), (30.0, P::Mars)],
    [(7.0, P::Mars), (11.0, P::Venus), (19.0, P::Mercury), (24.0, P::Jupiter), (30.0, P::Saturn)],
    [(12.0, P::Jupiter), (17.0, P::Venus), (21.0, P::Mercury), (26.0, P::Saturn), (30.0, P::Mars)],
    [(7.0, P::Mercury), (14.0, P::Jupiter), (22.0, P::Venus), (26.0, P::Saturn), (30.0, P::Mars)],
    [(7.0, P::Mercury), (13.0, P::Venus), (20.0, P::Jupiter), (25.0, P::Mars), (30.0, P::Saturn)],
    [(12.0, P::Venus), (16.0, P::Jupiter), (19.0, P::Mercury), (28.0, P::Mars), (30.0, P::Saturn)],
];

pub fn term_ruler(s: ZodiacSign, sign_deg: f64) -> CelestialPoint {
    for (limit, ruler) in TERMS[sign_index(s)] {
        if sign_deg < limit {
            return ruler;
        }
    }
    TERMS[sign_index(s)][4].1
}

/// Chaldäische Dekanate: Mars, Sonne, Venus, Merkur, Mond, Saturn, Jupiter (ab 0° Widder)
pub fn face_ruler(s: ZodiacSign, sign_deg: f64) -> CelestialPoint {
    const SEQ: [CelestialPoint; 7] = [P::Mars, P::Sun, P::Venus, P::Mercury, P::Moon, P::Saturn, P::Jupiter];
    let decan = (sign_index(s) * 3 + (sign_deg / 10.0).floor().min(2.0) as usize) % 7;
    SEQ[decan]
}

fn name_of(p: CelestialPoint) -> String {
    p.name_de().to_string()
}

fn compute_dignities(planets: &[PlanetData], diurnal: bool) -> Vec<EssentialDignity> {
    let mut out = Vec::new();
    for &tp in TRADITIONAL.iter() {
        let Some(pl) = planets.iter().find(|p| p.id == tp) else { continue };
        let (sign, deg) = (pl.sign, pl.sign_deg);
        let (td, tn, tpart) = triplicity(sign);
        let term = term_ruler(sign, deg);
        let face = face_ruler(sign, deg);
        let dom = domicile_ruler(sign);
        let exalt = exaltation_ruler(sign);

        let in_domicile = dom == tp;
        let in_exaltation = exalt == Some(tp);
        let triplicity_ruler = if diurnal { td } else { tn };
        let in_triplicity = triplicity_ruler == tp;
        let in_term = term == tp;
        let in_face = face == tp;
        let in_detriment = detriment_signs(tp).contains(&sign);
        let in_fall = fall_sign(tp) == Some(sign);

        let mut score = 0;
        if in_domicile {
            score += 5;
        }
        if in_exaltation {
            score += 4;
        }
        if in_triplicity {
            score += 3;
        }
        if in_term {
            score += 2;
        }
        if in_face {
            score += 1;
        }
        if in_detriment {
            score -= 5;
        }
        if in_fall {
            score -= 4;
        }
        let peregrine = !(in_domicile || in_exaltation || in_triplicity || in_term || in_face);
        if peregrine {
            score -= 5;
        }

        let mut parts = Vec::new();
        if in_domicile {
            parts.push("Domizil (+5)");
        }
        if in_exaltation {
            parts.push("Erhöhung (+4)");
        }
        if in_triplicity {
            parts.push("Triplizität (+3)");
        }
        if in_term {
            parts.push("Grenze (+2)");
        }
        if in_face {
            parts.push("Dekanat (+1)");
        }
        if in_detriment {
            parts.push("Exil (−5)");
        }
        if in_fall {
            parts.push("Fall (−4)");
        }
        if peregrine {
            parts.push("peregrin (−5)");
        }

        out.push(EssentialDignity {
            planet: tp,
            planet_name: name_of(tp),
            glyph: tp.glyph().to_string(),
            sign_name: sign.name_de().to_string(),
            domicile_ruler: name_of(dom),
            exaltation_ruler: exalt.map(name_of),
            triplicity_day: name_of(td),
            triplicity_night: name_of(tn),
            triplicity_participating: name_of(tpart),
            term_ruler: name_of(term),
            face_ruler: name_of(face),
            in_domicile,
            in_exaltation,
            in_triplicity,
            in_term,
            in_face,
            in_detriment,
            in_fall,
            peregrine,
            score,
            summary: parts.join(", "),
        });
    }
    out
}

fn compute_receptions(planets: &[PlanetData]) -> Vec<Reception> {
    let mut out = Vec::new();
    for (i, &a) in TRADITIONAL.iter().enumerate() {
        for &b in TRADITIONAL.iter().skip(i + 1) {
            let (Some(pa), Some(pb)) = (planets.iter().find(|p| p.id == a), planets.iter().find(|p| p.id == b)) else {
                continue;
            };
            if domicile_ruler(pa.sign) == b && domicile_ruler(pb.sign) == a {
                out.push(Reception {
                    planet_a: name_of(a),
                    planet_b: name_of(b),
                    kind: "Gegenseitige Rezeption durch Domizil".into(),
                });
            } else if exaltation_ruler(pa.sign) == Some(b) && exaltation_ruler(pb.sign) == Some(a) {
                out.push(Reception {
                    planet_a: name_of(a),
                    planet_b: name_of(b),
                    kind: "Gegenseitige Rezeption durch Erhöhung".into(),
                });
            } else if (domicile_ruler(pa.sign) == b && exaltation_ruler(pb.sign) == Some(a))
                || (domicile_ruler(pb.sign) == a && exaltation_ruler(pa.sign) == Some(b))
            {
                out.push(Reception {
                    planet_a: name_of(a),
                    planet_b: name_of(b),
                    kind: "Gemischte Rezeption (Domizil/Erhöhung)".into(),
                });
            }
        }
    }
    out
}

fn compute_dispositors(planets: &[PlanetData], modern: bool) -> (Vec<DispositorEntry>, Option<String>) {
    let ruler_of = |s: ZodiacSign| if modern { modern_ruler(s) } else { domicile_ruler(s) };
    let classical: Vec<&PlanetData> = planets.iter().filter(|p| CelestialPoint::classical().contains(&p.id)).collect();
    let mut entries = Vec::new();
    let mut finals: Vec<CelestialPoint> = Vec::new();
    for pl in &classical {
        let mut chain = vec![pl.id];
        let mut cur = pl.id;
        let mut loop_note = "";
        for _ in 0..12 {
            let Some(c) = classical.iter().find(|p| p.id == cur) else { break };
            let r = ruler_of(c.sign);
            if r == cur {
                loop_note = " ⊙"; // herrscht über sich selbst
                break;
            }
            if chain.contains(&r) {
                chain.push(r);
                loop_note = " ↻";
                break;
            }
            chain.push(r);
            cur = r;
        }
        if loop_note == " ⊙" {
            finals.push(cur);
        }
        let text: Vec<String> = chain.iter().map(|p| name_of(*p)).collect();
        entries.push(DispositorEntry {
            planet: name_of(pl.id),
            glyph: pl.id.glyph().to_string(),
            sign_name: pl.sign.name_de().to_string(),
            ruler: name_of(ruler_of(pl.sign)),
            chain: format!("{}{}", text.join(" → "), loop_note),
        });
    }
    finals.sort();
    finals.dedup();
    // Endpunkt nur, wenn alle Ketten im selben Selbstherrscher enden
    let all_end_same = finals.len() == 1
        && entries.iter().all(|e| e.chain.ends_with(" ⊙") && e.chain.contains(&name_of(finals[0])));
    (entries, if all_end_same { Some(name_of(finals[0])) } else { None })
}

// ──────────────────────────────────────────────────────────────────────────
// Aspektfiguren
// ──────────────────────────────────────────────────────────────────────────

fn aspect_between(aspects: &[AspectData], a: CelestialPoint, b: CelestialPoint, kinds: &[AspectType]) -> bool {
    aspects.iter().any(|x| {
        ((x.point_a == a && x.point_b == b) || (x.point_a == b && x.point_b == a)) && kinds.contains(&x.aspect_type)
    })
}

fn make_pattern(kind: &str, name: &str, pts: &[CelestialPoint], description: &str) -> AspectPattern {
    AspectPattern {
        kind: kind.into(),
        name: name.into(),
        points: pts.iter().map(|p| name_of(*p)).collect(),
        glyphs: pts.iter().map(|p| p.glyph()).collect::<Vec<_>>().join(" "),
        description: description.into(),
    }
}

fn detect_patterns(planets: &[PlanetData], aspects: &[AspectData]) -> Vec<AspectPattern> {
    let ids: Vec<CelestialPoint> = planets
        .iter()
        .map(|p| p.id)
        .filter(|id| CelestialPoint::classical().contains(id))
        .collect();
    let n = ids.len();
    let tri = [AspectType::Trine];
    let sq = [AspectType::Square];
    let opp = [AspectType::Opposition];
    let sex = [AspectType::Sextile];
    let qnx = [AspectType::Quincunx];
    let trine_or_sextile = [AspectType::Trine, AspectType::Sextile];

    let mut out = Vec::new();

    // Großes Trigon + Drachen
    let mut grand_trines: Vec<[usize; 3]> = Vec::new();
    for a in 0..n {
        for b in a + 1..n {
            for c in b + 1..n {
                if aspect_between(aspects, ids[a], ids[b], &tri)
                    && aspect_between(aspects, ids[b], ids[c], &tri)
                    && aspect_between(aspects, ids[a], ids[c], &tri)
                {
                    grand_trines.push([a, b, c]);
                    let element = planets.iter().find(|p| p.id == ids[a]).map(|p| p.sign.element().name_de()).unwrap_or("");
                    out.push(make_pattern(
                        "grand_trine",
                        "Großes Trigon",
                        &[ids[a], ids[b], ids[c]],
                        &format!("Dreieck aus drei Trigonen ({}): leichter Energiefluss, Begabung, aber auch Bequemlichkeit.", element),
                    ));
                }
            }
        }
    }
    for gt in &grand_trines {
        for d in 0..n {
            if gt.contains(&d) {
                continue;
            }
            for k in 0..3 {
                let opp_vertex = gt[k];
                let others = [gt[(k + 1) % 3], gt[(k + 2) % 3]];
                if aspect_between(aspects, ids[d], ids[opp_vertex], &opp)
                    && aspect_between(aspects, ids[d], ids[others[0]], &sex)
                    && aspect_between(aspects, ids[d], ids[others[1]], &sex)
                {
                    out.push(make_pattern(
                        "kite",
                        "Drachen",
                        &[ids[gt[0]], ids[gt[1]], ids[gt[2]], ids[d]],
                        "Großes Trigon mit einem Planeten in Opposition zu einer Spitze und Sextilen zu den anderen beiden: die Energie bekommt ein Ziel.",
                    ));
                }
            }
        }
    }

    // T-Quadrat
    for apex in 0..n {
        for a in 0..n {
            for b in a + 1..n {
                if a == apex || b == apex {
                    continue;
                }
                if aspect_between(aspects, ids[a], ids[b], &opp)
                    && aspect_between(aspects, ids[apex], ids[a], &sq)
                    && aspect_between(aspects, ids[apex], ids[b], &sq)
                {
                    out.push(make_pattern(
                        "t_square",
                        "T-Quadrat",
                        &[ids[a], ids[b], ids[apex]],
                        &format!(
                            "Opposition {}–{} mit Quadraten zum Scheitelpunkt {}: Spannung, die über den Scheitelpunkt entladen wird.",
                            ids[a].name_de(),
                            ids[b].name_de(),
                            ids[apex].name_de()
                        ),
                    ));
                }
            }
        }
    }

    // Großes Kreuz
    for a in 0..n {
        for b in a + 1..n {
            for c in b + 1..n {
                for d in c + 1..n {
                    let quad = [a, b, c, d];
                    // zwei Oppositionen + vier Quadrate, in irgendeiner Paarung
                    for (p, q, r, s) in [(0, 1, 2, 3), (0, 2, 1, 3), (0, 3, 1, 2)] {
                        let (pa, qa, ra, sa) = (quad[p], quad[q], quad[r], quad[s]);
                        if aspect_between(aspects, ids[pa], ids[qa], &opp)
                            && aspect_between(aspects, ids[ra], ids[sa], &opp)
                            && aspect_between(aspects, ids[pa], ids[ra], &sq)
                            && aspect_between(aspects, ids[pa], ids[sa], &sq)
                            && aspect_between(aspects, ids[qa], ids[ra], &sq)
                            && aspect_between(aspects, ids[qa], ids[sa], &sq)
                        {
                            out.push(make_pattern(
                                "grand_cross",
                                "Großes Kreuz",
                                &[ids[a], ids[b], ids[c], ids[d]],
                                "Zwei Oppositionen, die sich im Quadrat kreuzen: hohe Spannung, aber auch große Durchhaltekraft.",
                            ));
                            break;
                        }
                    }
                }
            }
        }
    }

    // Yod
    for apex in 0..n {
        for a in 0..n {
            for b in a + 1..n {
                if a == apex || b == apex {
                    continue;
                }
                if aspect_between(aspects, ids[a], ids[b], &sex)
                    && aspect_between(aspects, ids[apex], ids[a], &qnx)
                    && aspect_between(aspects, ids[apex], ids[b], &qnx)
                {
                    out.push(make_pattern(
                        "yod",
                        "Yod (Finger Gottes)",
                        &[ids[a], ids[b], ids[apex]],
                        &format!(
                            "Sextil {}–{} mit Quinkunxen zum Spitzenplaneten {}: Anpassungsdruck, ein Gefühl besonderer Aufgabe.",
                            ids[a].name_de(),
                            ids[b].name_de(),
                            ids[apex].name_de()
                        ),
                    ));
                }
            }
        }
    }

    // Mystisches Rechteck: zwei Oppositionen, verbunden durch Trigone und Sextile
    for a in 0..n {
        for b in a + 1..n {
            for c in b + 1..n {
                for d in c + 1..n {
                    let quad = [a, b, c, d];
                    for (p, q, r, s) in [(0, 1, 2, 3), (0, 2, 1, 3), (0, 3, 1, 2)] {
                        let (pa, qa, ra, sa) = (quad[p], quad[q], quad[r], quad[s]);
                        if aspect_between(aspects, ids[pa], ids[qa], &opp)
                            && aspect_between(aspects, ids[ra], ids[sa], &opp)
                            && ((aspect_between(aspects, ids[pa], ids[ra], &tri)
                                && aspect_between(aspects, ids[qa], ids[sa], &tri)
                                && aspect_between(aspects, ids[pa], ids[sa], &sex)
                                && aspect_between(aspects, ids[qa], ids[ra], &sex))
                                || (aspect_between(aspects, ids[pa], ids[sa], &tri)
                                    && aspect_between(aspects, ids[qa], ids[ra], &tri)
                                    && aspect_between(aspects, ids[pa], ids[ra], &sex)
                                    && aspect_between(aspects, ids[qa], ids[sa], &sex)))
                        {
                            out.push(make_pattern(
                                "mystic_rectangle",
                                "Mystisches Rechteck",
                                &[ids[a], ids[b], ids[c], ids[d]],
                                "Zwei Oppositionen, durch Trigone und Sextile verbunden: Spannung mit einem Ventil.",
                            ));
                            break;
                        }
                    }
                }
            }
        }
    }

    // Stellium: ≥ 3 Planeten im selben Zeichen oder innerhalb 10°
    for sign_i in 0..12usize {
        let in_sign: Vec<&PlanetData> = planets
            .iter()
            .filter(|p| CelestialPoint::classical().contains(&p.id) && p.sign as usize == sign_i)
            .collect();
        if in_sign.len() >= 3 {
            let pts: Vec<CelestialPoint> = in_sign.iter().map(|p| p.id).collect();
            out.push(make_pattern(
                "stellium",
                "Stellium",
                &pts,
                &format!("{} Planeten im Zeichen {}: starke Betonung dieses Themas.", pts.len(), in_sign[0].sign.name_de()),
            ));
        }
    }
    // Zeichenübergreifende Häufung (≥ 3 Planeten in 10°) – nur wenn nicht schon als Zeichen-Stellium erfasst
    let mut sorted: Vec<&PlanetData> =
        planets.iter().filter(|p| CelestialPoint::classical().contains(&p.id)).collect();
    sorted.sort_by(|a, b| a.longitude.partial_cmp(&b.longitude).unwrap_or(std::cmp::Ordering::Equal));
    let m = sorted.len();
    for i in 0..m {
        let mut group = vec![sorted[i]];
        for k in 1..m {
            let nxt = sorted[(i + k) % m];
            if angle_diff(nxt.longitude, sorted[i].longitude) <= 10.0
                && normalize_deg(nxt.longitude - sorted[i].longitude) <= 10.0
            {
                group.push(nxt);
            } else {
                break;
            }
        }
        let signs_differ = group.iter().any(|p| p.sign != group[0].sign);
        if group.len() >= 3 && signs_differ {
            let pts: Vec<CelestialPoint> = group.iter().map(|p| p.id).collect();
            if !out.iter().any(|p| p.kind == "stellium_wide" && p.points == pts.iter().map(|x| name_of(*x)).collect::<Vec<_>>()) {
                out.push(make_pattern(
                    "stellium_wide",
                    "Stellium (zeichenübergreifend)",
                    &pts,
                    "Drei oder mehr Planeten innerhalb von 10° über eine Zeichengrenze hinweg.",
                ));
            }
        }
    }

    // Duplikate (gleiche Art + gleiche Punktmenge) entfernen
    let mut seen: Vec<(String, Vec<String>)> = Vec::new();
    out.retain(|p| {
        let mut pts = p.points.clone();
        pts.sort();
        let key = (p.kind.clone(), pts);
        if seen.contains(&key) {
            false
        } else {
            seen.push(key);
            true
        }
    });
    let _ = trine_or_sextile;
    out
}

fn chart_shape(planets: &[PlanetData]) -> Option<ChartShape> {
    let mut lons: Vec<f64> = planets
        .iter()
        .filter(|p| CelestialPoint::classical().contains(&p.id))
        .map(|p| p.longitude)
        .collect();
    if lons.len() < 10 {
        return None;
    }
    lons.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = lons.len();
    // gaps[i] = Lücke zwischen lons[i] und dem nächsten (zyklisch)
    let gaps: Vec<f64> = (0..n).map(|i| normalize_deg(lons[(i + 1) % n] - lons[i])).collect();
    let max_gap = gaps.iter().cloned().fold(0.0, f64::max);
    let span = 360.0 - max_gap;

    // Gruppen: Planeten, die durch Lücken ≥ 60° getrennt sind
    let split_at: Vec<usize> = gaps.iter().enumerate().filter(|(_, g)| **g >= 60.0).map(|(i, _)| i).collect();
    let mut group_sizes: Vec<usize> = Vec::new();
    if split_at.is_empty() {
        group_sizes.push(n);
    } else {
        for w in 0..split_at.len() {
            let start = split_at[w];
            let end = split_at[(w + 1) % split_at.len()];
            group_sizes.push(if end > start { end - start } else { end + n - start });
        }
    }

    let (name, desc): (&str, &str) = if span <= 120.0 {
        ("Bündel (Bundle)", "Alle Planeten innerhalb von 120°: starke Konzentration, Spezialisierung, aber auch Einseitigkeit.")
    } else if span <= 180.0 {
        // Eimer: ein einzelner Planet (Henkel) mit ≥ 60° Abstand zu beiden Seiten, Rest in einer Hälfte
        let handle = group_sizes.len() == 2 && group_sizes.contains(&1);
        if handle {
            ("Eimer (Bucket)", "Eine Halbkugel gefüllt, ein einzelner Planet als Henkel: dieser Planet bündelt die Energie des Horoskops.")
        } else {
            ("Schüssel (Bowl)", "Alle Planeten in einer Hälfte (180°): Selbstgenügsamkeit, ein Thema des Gebens und Empfangens.")
        }
    } else if group_sizes.len() == 2 && group_sizes.iter().all(|s| *s >= 2) {
        ("Wippe (Seesaw)", "Zwei Planetengruppen stehen sich gegenüber: Pendeln zwischen zwei Positionen, Abwägen.")
    } else if max_gap >= 120.0 && group_sizes.len() <= 2 {
        ("Lokomotive (Locomotive)", "Planeten über 240° verteilt, ein Drittel leer: Antrieb, Zielstrebigkeit.")
    } else if split_at.is_empty() && covered_signs(&lons) >= 9 {
        ("Streuung (Splash)", "Planeten gleichmäßig über das ganze Rad: vielseitige Interessen, Zersplitterungsgefahr.")
    } else {
        ("Unregelmäßig (Splay)", "Unregelmäßige Verteilung in mehreren Gruppen: ausgeprägte Individualität.")
    };
    Some(ChartShape { name: name.into(), description: desc.into(), span_degrees: span })
}

fn covered_signs(lons: &[f64]) -> usize {
    let mut seen = [false; 12];
    for l in lons {
        seen[((l / 30.0).floor() as usize).min(11)] = true;
    }
    seen.iter().filter(|b| **b).count()
}

fn compute_distribution(planets: &[PlanetData]) -> Distribution {
    let mut d = Distribution::default();
    for p in planets.iter().filter(|p| CelestialPoint::classical().contains(&p.id)) {
        let h = p.house.clamp(1, 12) as usize;
        d.per_house[h - 1] += 1;
        d.per_sign[p.sign as usize] += 1;
        if h >= 7 {
            d.above_horizon += 1;
        } else {
            d.below_horizon += 1;
        }
        if h >= 10 || h <= 3 {
            d.eastern += 1;
        } else {
            d.western += 1;
        }
        let q = match h {
            1..=3 => 0,
            4..=6 => 1,
            7..=9 => 2,
            _ => 3,
        };
        d.quadrants[q] += 1;
    }
    let groups = [
        ("Angular (1/4/7/10)", [1usize, 4, 7, 10]),
        ("Sukzedent (2/5/8/11)", [2, 5, 8, 11]),
        ("Kadent (3/6/9/12)", [3, 6, 9, 12]),
    ];
    let mut best = ("", 0u32);
    for (label, hs) in groups {
        let c: u32 = hs.iter().map(|h| d.per_house[h - 1]).sum();
        if c > best.1 {
            best = (label, c);
        }
    }
    d.dominant_house_group = best.0.to_string();
    d
}

// ──────────────────────────────────────────────────────────────────────────
// Halbsummen
// ──────────────────────────────────────────────────────────────────────────

fn midpoint(a: f64, b: f64) -> f64 {
    let diff = ((b - a + 540.0).rem_euclid(360.0)) - 180.0;
    normalize_deg(a + diff / 2.0)
}

struct NamedPoint {
    name: String,
    glyph: String,
    lon: f64,
}

fn points_for_midpoints(chart: &ChartResponse) -> Vec<NamedPoint> {
    let mut v: Vec<NamedPoint> = chart
        .planets
        .iter()
        .filter(|p| CelestialPoint::classical().contains(&p.id) || p.id == CelestialPoint::TrueNode)
        .map(|p| NamedPoint { name: p.name.clone(), glyph: p.glyph.clone(), lon: p.longitude })
        .collect();
    v.push(NamedPoint { name: "Aszendent".into(), glyph: "AC".into(), lon: chart.angles.ascendant });
    v.push(NamedPoint { name: "Medium Coeli".into(), glyph: "MC".into(), lon: chart.angles.midheaven });
    v
}

fn compute_midpoints(chart: &ChartResponse, orb: f64) -> (Vec<MidpointData>, Vec<MidpointHit>, Vec<DialEntry>) {
    let pts = points_for_midpoints(chart);
    let mut mids = Vec::new();
    let mut mid_values: Vec<(usize, usize, f64)> = Vec::new();
    for i in 0..pts.len() {
        for j in i + 1..pts.len() {
            let m = midpoint(pts[i].lon, pts[j].lon);
            let (sign, sd) = ZodiacSign::from_degrees(m);
            let (d, mi) = split_dm(sd);
            mids.push(MidpointData {
                a: pts[i].name.clone(),
                b: pts[j].name.clone(),
                label: format!("{}/{}", pts[i].glyph, pts[j].glyph),
                longitude: m,
                formatted: format!("{} {:02}° {:02}'", sign.glyph(), d, mi),
                sign_name: sign.name_de().to_string(),
            });
            mid_values.push((i, j, m));
        }
    }
    let mut hits = Vec::new();
    for (c_idx, c) in pts.iter().enumerate() {
        for &(i, j, m) in &mid_values {
            if i == c_idx || j == c_idx {
                continue;
            }
            // Abstand auf der 90°-Scheibe
            let d = (c.lon - m).rem_euclid(90.0);
            let dd = d.min(90.0 - d);
            if dd <= orb {
                // tatsächliche Beziehung 0/90/180 zur Halbsumme
                let raw = angle_diff(c.lon, m);
                let relation = if raw < 45.0 {
                    0
                } else if raw < 135.0 {
                    90
                } else {
                    180
                };
                let total = (dd * 60.0).round() as i64;
                hits.push(MidpointHit {
                    point: c.name.clone(),
                    point_glyph: c.glyph.clone(),
                    a: pts[i].name.clone(),
                    b: pts[j].name.clone(),
                    label: format!("{} = {}/{}", c.glyph, pts[i].glyph, pts[j].glyph),
                    relation_degrees: relation,
                    orb: dd,
                    formatted_orb: format!("{:02}°{:02}'", total / 60, total % 60),
                });
            }
        }
    }
    hits.sort_by(|a, b| a.orb.partial_cmp(&b.orb).unwrap_or(std::cmp::Ordering::Equal));

    let mut dial: Vec<DialEntry> = pts
        .iter()
        .map(|p| DialEntry { name: p.name.clone(), glyph: p.glyph.clone(), position: p.lon.rem_euclid(90.0), longitude: p.lon })
        .collect();
    dial.sort_by(|a, b| a.position.partial_cmp(&b.position).unwrap_or(std::cmp::Ordering::Equal));
    (mids, hits, dial)
}

// ──────────────────────────────────────────────────────────────────────────
// Arabische Lose (hellenistisch, mit Sektenumkehr)
// ──────────────────────────────────────────────────────────────────────────

fn compute_lots(chart: &ChartResponse, diurnal: bool) -> Vec<LotData> {
    let lon = |id: CelestialPoint| chart.planets.iter().find(|p| p.id == id).map(|p| p.longitude);
    let asc = chart.angles.ascendant;
    let (Some(sun), Some(moon)) = (lon(P::Sun), lon(P::Moon)) else { return Vec::new() };
    let (Some(merc), Some(ven), Some(mars), Some(jup), Some(sat)) =
        (lon(P::Mercury), lon(P::Venus), lon(P::Mars), lon(P::Jupiter), lon(P::Saturn))
    else {
        return Vec::new();
    };

    let fortune = if diurnal { asc + moon - sun } else { asc + sun - moon };
    let spirit = if diurnal { asc + sun - moon } else { asc + moon - sun };
    let fortune = normalize_deg(fortune);
    let spirit = normalize_deg(spirit);

    // (Schlüssel, Name, Formel, Länge, sektenabhängig umgekehrt?) – Formeln für den Tag; nachts Summanden vertauscht
    let reversible = |day_plus: f64, day_minus: f64| {
        if diurnal { asc + day_plus - day_minus } else { asc + day_minus - day_plus }
    };
    let fixed = |plus: f64, minus: f64| asc + plus - minus;

    let defs: Vec<(&str, &str, String, f64)> = vec![
        ("fortune", "Glückspunkt (Pars Fortunae)", if diurnal { "AC + Mond − Sonne".into() } else { "AC + Sonne − Mond (nachts)".into() }, fortune),
        ("spirit", "Geistpunkt (Pars Spiritus)", if diurnal { "AC + Sonne − Mond".into() } else { "AC + Mond − Sonne (nachts)".into() }, spirit),
        ("eros", "Eros", "AC + Venus − Geistpunkt".into(), reversible(ven, spirit)),
        ("necessity", "Notwendigkeit (Ananke)", "AC + Glückspunkt − Merkur".into(), reversible(fortune, merc)),
        ("courage", "Mut (Tolma)", "AC + Glückspunkt − Mars".into(), reversible(fortune, mars)),
        ("victory", "Sieg (Nike)", "AC + Jupiter − Geistpunkt".into(), reversible(jup, spirit)),
        ("nemesis", "Nemesis", "AC + Glückspunkt − Saturn".into(), reversible(fortune, sat)),
        ("marriage", "Ehe", "AC + Venus − Saturn".into(), fixed(ven, sat)),
        ("children", "Kinder", "AC + Jupiter − Saturn".into(), fixed(jup, sat)),
        ("father", "Vater", "AC + Saturn − Sonne".into(), fixed(sat, sun)),
        ("mother", "Mutter", "AC + Mond − Venus".into(), fixed(moon, ven)),
    ];

    let cusps: Vec<f64> = chart.houses.iter().map(|h| h.longitude).collect();
    defs.into_iter()
        .map(|(key, name, formula, l)| {
            let l = normalize_deg(l);
            let (sign, sd) = ZodiacSign::from_degrees(l);
            let (d, m) = split_dm(sd);
            LotData {
                key: key.into(),
                name: name.into(),
                formula,
                longitude: l,
                formatted: format!("{} {:02}° {:02}'", sign.glyph(), d, m),
                sign_name: sign.name_de().to_string(),
                house: house_of(l, &cusps),
            }
        })
        .collect()
}

fn house_of(lon: f64, cusps: &[f64]) -> u8 {
    if cusps.len() < 12 {
        return 1;
    }
    for i in 0..12 {
        let cur = normalize_deg(cusps[i]);
        let next = normalize_deg(cusps[(i + 1) % 12]);
        let width = normalize_deg(next - cur);
        if normalize_deg(lon - cur) < width {
            return (i + 1) as u8;
        }
    }
    1
}

// ──────────────────────────────────────────────────────────────────────────
// Fixsterne
// ──────────────────────────────────────────────────────────────────────────

/// (Name in sefstars.txt, Natur nach der Tradition)
const STARS: &[(&str, &str)] = &[
    ("Algol", "Saturn/Jupiter – Unheil, Gewalt, Intensität"),
    ("Alcyone", "Mond/Mars – Pleiaden, Sehkraft, Tränen"),
    ("Aldebaran", "Mars – Königsstern: Ehre, Integrität"),
    ("Rigel", "Jupiter/Saturn – Lehre, Erfolg"),
    ("Bellatrix", "Mars/Merkur – Kriegerin, Ruhm"),
    ("Capella", "Mars/Merkur – Neugier, Ehre"),
    ("Betelgeuse", "Mars/Merkur – Erfolg, Glück"),
    ("Sirius", "Jupiter/Mars – Ruhm, Hingabe, Brennen"),
    ("Canopus", "Saturn/Jupiter – Reisen, Wissen"),
    ("Castor", "Merkur – Intellekt, plötzlicher Wandel"),
    ("Pollux", "Mars – Mut, Streitlust"),
    ("Procyon", "Merkur/Mars – Aktivität, Schnelligkeit"),
    ("Regulus", "Mars/Jupiter – Königsstern: Macht, Erfolg"),
    ("Alphard", "Saturn/Venus – Leidenschaft, Gift"),
    ("Denebola", "Saturn/Venus – Unglück, Edelmut"),
    ("Vindemiatrix", "Saturn/Merkur – Witwenstern, Trauer"),
    ("Spica", "Venus/Mars – größtes Glück, Begabung"),
    ("Arcturus", "Mars/Jupiter – Pfadfinder, Wohlstand"),
    ("Zubenelgenubi", "Mars/Saturn – Karma, Gerechtigkeit"),
    ("Zubeneschamali", "Jupiter/Merkur – Glück, Ehre"),
    ("Antares", "Mars/Jupiter – Königsstern: Mut, Zerstörung"),
    ("Alphecca", "Venus/Merkur – Würde, Kunst"),
    ("Vega", "Venus/Merkur – Charisma, Idealismus"),
    ("Altair", "Mars/Jupiter – Kühnheit, Ehrgeiz"),
    ("Deneb Algedi", "Saturn/Jupiter – Gesetz, Gerechtigkeit"),
    ("Fomalhaut", "Venus/Merkur – Königsstern: Idealismus, Ruhm"),
    ("Achernar", "Jupiter – Erfolg, Ehre"),
    ("Markab", "Mars/Merkur – Ehre, Gefahr von Messern"),
    ("Scheat", "Mars/Merkur – Ertrinken, Unglück"),
    ("Hamal", "Mars/Saturn – Gewalt, Mut"),
    ("Mirach", "Venus – Schönheit, Liebe"),
    ("Menkar", "Saturn – Krankheit, Verlust"),
    ("Gal. Center", "Zentrum der Milchstraße – Umbruch, Weite"),
];

fn compute_fixed_stars(chart: &ChartResponse, settings: &ChartSettings) -> Vec<FixedStarContact> {
    let sidereal = settings.zodiac == Zodiac::Sidereal;
    let mut contacts: Vec<FixedStarContact> = Vec::new();
    let mut targets: Vec<(String, String, f64)> = chart
        .planets
        .iter()
        .filter(|p| !matches!(p.id, P::SouthNode))
        .map(|p| (p.name.clone(), p.glyph.clone(), p.longitude))
        .collect();
    targets.push(("Aszendent".into(), "AC".into(), chart.angles.ascendant));
    targets.push(("Medium Coeli".into(), "MC".into(), chart.angles.midheaven));

    if sidereal {
        engine::set_sidereal(settings.ayanamsa);
    }
    for (star_name, nature) in STARS {
        let Some(star) = engine::fixed_star(star_name, chart.julian_day, sidereal) else { continue };
        for (name, glyph, lon) in &targets {
            let orb = angle_diff(star.longitude, *lon);
            if orb <= settings.fixed_star_orb {
                let (sign, sd) = ZodiacSign::from_degrees(star.longitude);
                let (d, m) = split_dm(sd);
                let total = (orb * 60.0).round() as i64;
                contacts.push(FixedStarContact {
                    star: star.name.clone(),
                    star_longitude: star.longitude,
                    star_formatted: format!("{} {:02}° {:02}'", sign.glyph(), d, m),
                    contact: name.clone(),
                    contact_glyph: glyph.clone(),
                    orb,
                    formatted_orb: format!("{:02}°{:02}'", total / 60, total % 60),
                    nature: (*nature).to_string(),
                });
            }
        }
    }
    contacts.sort_by(|a, b| a.orb.partial_cmp(&b.orb).unwrap_or(std::cmp::Ordering::Equal));
    contacts
}

// ──────────────────────────────────────────────────────────────────────────
// Parallelen (Deklination)
// ──────────────────────────────────────────────────────────────────────────

fn compute_parallels(planets: &[PlanetData]) -> Vec<ParallelData> {
    let pts: Vec<&PlanetData> = planets.iter().filter(|p| CelestialPoint::classical().contains(&p.id)).collect();
    let mut out = Vec::new();
    for i in 0..pts.len() {
        for j in i + 1..pts.len() {
            let (a, b) = (pts[i], pts[j]);
            let par = (a.declination - b.declination).abs();
            let contra = (a.declination + b.declination).abs();
            let (kind, orb) = if par <= 1.0 && par <= contra {
                ("Parallel", par)
            } else if contra <= 1.0 {
                ("Kontraparallel", contra)
            } else {
                continue;
            };
            let total = (orb * 60.0).round() as i64;
            out.push(ParallelData {
                planet_a: a.name.clone(),
                planet_b: b.name.clone(),
                kind: kind.into(),
                orb,
                formatted_orb: format!("{:02}°{:02}'", total / 60, total % 60),
            });
        }
    }
    out.sort_by(|a, b| a.orb.partial_cmp(&b.orb).unwrap_or(std::cmp::Ordering::Equal));
    out
}

// ──────────────────────────────────────────────────────────────────────────

/// Alle Zusatzanalysen eines Horoskops.
pub fn analyze(chart: &ChartResponse, settings: &ChartSettings) -> AnalysisData {
    let diurnal = chart.is_diurnal;
    let (mids, hits, dial) = compute_midpoints(chart, 1.0);
    let (dispositors, final_dispositor) = compute_dispositors(&chart.planets, false);
    AnalysisData {
        is_diurnal: diurnal,
        dignities: compute_dignities(&chart.planets, diurnal),
        receptions: compute_receptions(&chart.planets),
        dispositors,
        final_dispositor,
        patterns: detect_patterns(&chart.planets, &chart.aspects),
        chart_shape: chart_shape(&chart.planets),
        distribution: compute_distribution(&chart.planets),
        midpoints: mids,
        midpoint_hits: hits,
        dial90: dial,
        lots: compute_lots(chart, diurnal),
        fixed_stars: if settings.fixed_stars { compute_fixed_stars(chart, settings) } else { Vec::new() },
        parallels: compute_parallels(&chart.planets),
    }
}
