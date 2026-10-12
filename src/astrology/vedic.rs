//! Vedische Astrologie (Jyotish): siderische Rashi, Nakshatras mit Padas, Vimshottari-Dasha,
//! Vargas (D3, D4, D7, D9, D10, D12), planetare Würden. Häuser nach Ganzzeichen-Art ab dem Lagna.

use crate::astrology::calculator::{calculate_chart, resolve_time};
use crate::astrology::models::*;
use crate::astrology::util::split_dms;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VedicRequest {
    pub natal: ChartRequest,
    /// Stichtag für die laufende Dasha (UTC); Standard: jetzt
    #[serde(default)]
    pub as_of_jd: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VedicPlanet {
    pub id: CelestialPoint,
    pub name: String,
    pub sanskrit: String,
    pub glyph: String,
    pub longitude: f64,
    pub formatted: String,
    pub rashi: String,
    pub rashi_sanskrit: String,
    pub rashi_index: u8,
    /// Haus ab Lagna (Ganzzeichen)
    pub house: u8,
    pub nakshatra: String,
    pub nakshatra_lord: String,
    pub pada: u8,
    pub retrograde: bool,
    pub dignity: String,
    pub navamsa_rashi: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VargaPlacement {
    pub point: String,
    pub glyph: String,
    pub rashi_index: u8,
    pub rashi: String,
    pub house: u8,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VargaChart {
    pub key: String,
    pub name: String,
    pub meaning: String,
    pub lagna_rashi_index: u8,
    pub placements: Vec<VargaPlacement>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DashaPeriod {
    pub lord: String,
    pub start_jd: f64,
    pub end_jd: f64,
    pub start: String,
    pub end: String,
    pub years: f64,
    pub current: bool,
    pub sub_periods: Vec<DashaPeriod>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VedicResponse {
    pub chart: ChartResponse,
    pub ayanamsa_name: String,
    pub ayanamsa_value: f64,
    pub lagna: String,
    pub lagna_rashi_index: u8,
    pub moon_nakshatra: String,
    pub planets: Vec<VedicPlanet>,
    pub vargas: Vec<VargaChart>,
    pub dasha: Vec<DashaPeriod>,
    pub dasha_system: String,
}

const RASHI_SANSKRIT: [&str; 12] =
    ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"];

const NAKSHATRAS: [&str; 27] = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati",
];

/// Vimshottari-Reihenfolge der Herren und ihre Jahre
const DASHA_ORDER: [(&str, f64); 9] = [
    ("Ketu", 7.0),
    ("Venus", 20.0),
    ("Sonne", 6.0),
    ("Mond", 10.0),
    ("Mars", 7.0),
    ("Rahu", 18.0),
    ("Jupiter", 16.0),
    ("Saturn", 19.0),
    ("Merkur", 17.0),
];

fn sanskrit_planet(p: CelestialPoint) -> &'static str {
    use CelestialPoint as P;
    match p {
        P::Sun => "Surya",
        P::Moon => "Chandra",
        P::Mars => "Mangala",
        P::Mercury => "Budha",
        P::Jupiter => "Guru",
        P::Venus => "Shukra",
        P::Saturn => "Shani",
        P::TrueNode => "Rahu",
        P::SouthNode => "Ketu",
        P::Uranus => "Uranus",
        P::Neptune => "Neptun",
        P::Pluto => "Pluto",
        _ => "",
    }
}

fn nakshatra_lord(index: usize) -> &'static str {
    DASHA_ORDER[index % 9].0
}

fn dignity(p: CelestialPoint, sign: usize, deg_in_sign: f64) -> String {
    use CelestialPoint as P;
    // (Erhöhungszeichen, Grad) / Schwächung ist das Gegenzeichen
    let exalt: Option<(usize, f64)> = match p {
        P::Sun => Some((0, 10.0)),
        P::Moon => Some((1, 3.0)),
        P::Mars => Some((9, 28.0)),
        P::Mercury => Some((5, 15.0)),
        P::Jupiter => Some((3, 5.0)),
        P::Venus => Some((11, 27.0)),
        P::Saturn => Some((6, 20.0)),
        _ => None,
    };
    let own: &[usize] = match p {
        P::Sun => &[4],
        P::Moon => &[3],
        P::Mars => &[0, 7],
        P::Mercury => &[2, 5],
        P::Jupiter => &[8, 11],
        P::Venus => &[1, 6],
        P::Saturn => &[9, 10],
        _ => &[],
    };
    if let Some((es, _)) = exalt {
        if sign == es {
            return "Uccha (erhöht)".into();
        }
        if sign == (es + 6) % 12 {
            return "Neecha (geschwächt)".into();
        }
    }
    if own.contains(&sign) {
        return "Swakshetra (eigenes Zeichen)".into();
    }
    let _ = deg_in_sign;
    "—".into()
}

/// Rashi-Index der Varga-Teilung für eine Länge.
fn varga_sign(division: u32, lon: f64) -> usize {
    let lon = lon.rem_euclid(360.0);
    let sign = (lon / 30.0).floor() as usize % 12;
    let d = lon - sign as f64 * 30.0;
    let odd = sign.is_multiple_of(2); // Widder (0) ist ein ungerades Zeichen
    match division {
        1 => sign,
        3 => {
            let part = (d / 10.0).floor() as usize % 3;
            (sign + part * 4) % 12
        }
        4 => {
            let part = (d / 7.5).floor() as usize % 4;
            (sign + part * 3) % 12
        }
        7 => {
            let part = (d / (30.0 / 7.0)).floor() as usize % 7;
            let start = if odd { sign } else { (sign + 6) % 12 };
            (start + part) % 12
        }
        9 => {
            let part = (d / (30.0 / 9.0)).floor() as usize % 9;
            let start = match sign % 4 {
                0 => 0, // Feuer → Widder
                1 => 9, // Erde → Steinbock
                2 => 6, // Luft → Waage
                _ => 3, // Wasser → Krebs
            };
            (start + part) % 12
        }
        10 => {
            let part = (d / 3.0).floor() as usize % 10;
            let start = if odd { sign } else { (sign + 8) % 12 };
            (start + part) % 12
        }
        12 => {
            let part = (d / 2.5).floor() as usize % 12;
            (sign + part) % 12
        }
        _ => sign,
    }
}

fn rashi_name(i: usize) -> String {
    ZodiacSign::from_degrees(i as f64 * 30.0 + 1.0).0.name_de().to_string()
}

fn jd_label(jd: f64) -> String {
    let d = sweph::date_from_julian_day(jd);
    format!("{:04}-{:02}-{:02}", d.year, d.month, d.day)
}

const YEAR_DAYS: f64 = 365.25;

fn build_dasha(birth_jd: f64, moon_lon: f64, as_of: f64) -> Vec<DashaPeriod> {
    let nak_len = 360.0 / 27.0;
    let idx = (moon_lon / nak_len).floor() as usize % 27;
    let frac_elapsed = (moon_lon - idx as f64 * nak_len) / nak_len;
    let first_lord = idx % 9;
    let first_years = DASHA_ORDER[first_lord].1;
    // Beginn der ersten Dasha liegt vor der Geburt
    let mut cursor = birth_jd - frac_elapsed * first_years * YEAR_DAYS;
    let mut out = Vec::new();
    for k in 0..10 {
        let (lord, years) = DASHA_ORDER[(first_lord + k) % 9];
        let start = cursor;
        let end = start + years * YEAR_DAYS;
        // Unterperioden (Antardasha): Anteil des Gesamtzyklus von 120 Jahren
        let mut sub = Vec::new();
        let mut sc = start;
        let lord_pos = (first_lord + k) % 9;
        for s in 0..9 {
            let (slord, syears) = DASHA_ORDER[(lord_pos + s) % 9];
            let dur = years * syears / 120.0 * YEAR_DAYS;
            sub.push(DashaPeriod {
                lord: slord.to_string(),
                start_jd: sc,
                end_jd: sc + dur,
                start: jd_label(sc),
                end: jd_label(sc + dur),
                years: years * syears / 120.0,
                current: as_of >= sc && as_of < sc + dur,
                sub_periods: Vec::new(),
            });
            sc += dur;
        }
        out.push(DashaPeriod {
            lord: lord.to_string(),
            start_jd: start,
            end_jd: end,
            start: jd_label(start),
            end: jd_label(end),
            years,
            current: as_of >= start && as_of < end,
            sub_periods: sub,
        });
        cursor = end;
    }
    out
}

pub fn calculate_vedic(req: &VedicRequest) -> Result<VedicResponse, String> {
    let mut natal = req.natal.clone();
    let mut s = natal.settings.clone().unwrap_or_else(|| ChartSettings {
        node: NodeType::Mean, // Rahu/Ketu traditionell als mittlere Knoten
        ..ChartSettings::default()
    });
    s.zodiac = Zodiac::Sidereal;
    s.fixed_stars = false;
    s.south_node = true;
    if natal.settings.is_none() {
        s.ayanamsa = 1; // Lahiri
    }
    natal.settings = Some(s);
    natal.house_system = Some(HouseSystemChoice::WholeSign);
    let chart = calculate_chart(&natal)?;
    let (birth_jd, _, _) = resolve_time(&natal)?;

    let lagna_idx = (chart.angles.ascendant / 30.0).floor() as usize % 12;
    let house_of = |sign_idx: usize| ((sign_idx + 12 - lagna_idx) % 12 + 1) as u8;

    let mut planets = Vec::new();
    for pl in &chart.planets {
        use CelestialPoint as P;
        if !matches!(pl.id, P::Sun | P::Moon | P::Mars | P::Mercury | P::Jupiter | P::Venus | P::Saturn | P::TrueNode | P::SouthNode | P::Uranus | P::Neptune | P::Pluto) {
            continue;
        }
        let idx = (pl.longitude / 30.0).floor() as usize % 12;
        let nak_len = 360.0 / 27.0;
        let nk = (pl.longitude / nak_len).floor() as usize % 27;
        let pada = (((pl.longitude - nk as f64 * nak_len) / (nak_len / 4.0)).floor() as u8 + 1).min(4);
        let (d, m, sec) = split_dms(pl.sign_deg);
        planets.push(VedicPlanet {
            id: pl.id,
            name: pl.name.clone(),
            sanskrit: sanskrit_planet(pl.id).to_string(),
            glyph: pl.glyph.clone(),
            longitude: pl.longitude,
            formatted: format!("{:02}° {:02}' {:02}\"", d, m, sec),
            rashi: pl.sign_name.clone(),
            rashi_sanskrit: RASHI_SANSKRIT[idx].to_string(),
            rashi_index: idx as u8,
            house: house_of(idx),
            nakshatra: NAKSHATRAS[nk].to_string(),
            nakshatra_lord: nakshatra_lord(nk).to_string(),
            pada,
            retrograde: pl.is_retrograde || matches!(pl.id, P::TrueNode | P::SouthNode),
            dignity: dignity(pl.id, idx, pl.sign_deg),
            navamsa_rashi: rashi_name(varga_sign(9, pl.longitude)),
        });
    }

    let divisions = [
        (1u32, "D1", "Rashi", "Körper, Gesamtbild des Lebens"),
        (3, "D3", "Drekkana", "Geschwister, Mut"),
        (4, "D4", "Chaturthamsha", "Besitz, Wohnstätte"),
        (7, "D7", "Saptamsha", "Kinder, Nachkommen"),
        (9, "D9", "Navamsha", "Ehe, Dharma, innere Stärke"),
        (10, "D10", "Dashamsha", "Beruf, Karriere"),
        (12, "D12", "Dvadashamsha", "Eltern, Herkunft"),
    ];
    let mut vargas = Vec::new();
    for (div, key, name, meaning) in divisions {
        let lag = varga_sign(div, chart.angles.ascendant);
        let mut pl = Vec::new();
        for p in &chart.planets {
            use CelestialPoint as P;
            if !matches!(p.id, P::Sun | P::Moon | P::Mars | P::Mercury | P::Jupiter | P::Venus | P::Saturn | P::TrueNode | P::SouthNode) {
                continue;
            }
            let sign = varga_sign(div, p.longitude);
            pl.push(VargaPlacement {
                point: p.name.clone(),
                glyph: p.glyph.clone(),
                rashi_index: sign as u8,
                rashi: rashi_name(sign),
                house: ((sign + 12 - lag) % 12 + 1) as u8,
            });
        }
        vargas.push(VargaChart {
            key: key.into(),
            name: name.into(),
            meaning: meaning.into(),
            lagna_rashi_index: lag as u8,
            placements: pl,
        });
    }

    let moon = chart.planets.iter().find(|p| p.id == CelestialPoint::Moon).map(|p| p.longitude).unwrap_or(0.0);
    let moon_nak = NAKSHATRAS[(moon / (360.0 / 27.0)).floor() as usize % 27];
    let as_of = req.as_of_jd.unwrap_or_else(|| {
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0);
        now / 86400.0 + 2440587.5
    });
    let dasha = build_dasha(birth_jd, moon, as_of);

    Ok(VedicResponse {
        ayanamsa_name: chart.ayanamsa_name.clone().unwrap_or_default(),
        ayanamsa_value: chart.ayanamsa_value.unwrap_or(0.0),
        lagna: format!("{} ({})", ZodiacSign::from_degrees(chart.angles.ascendant).0.name_de(), RASHI_SANSKRIT[lagna_idx]),
        lagna_rashi_index: lagna_idx as u8,
        moon_nakshatra: moon_nak.to_string(),
        planets,
        vargas,
        dasha,
        dasha_system: "Vimshottari (120 Jahre, Jahr = 365,25 Tage)".into(),
        chart,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn navamsa_of_zero_aries_is_aries_and_last_part_is_sagittarius() {
        assert_eq!(varga_sign(9, 0.5), 0);
        assert_eq!(varga_sign(9, 29.5), 8); // 9. Navamsa des Widders = Schütze
        assert_eq!(varga_sign(9, 30.5), 9); // Stier beginnt mit Steinbock
        assert_eq!(varga_sign(9, 60.5), 6); // Zwillinge beginnt mit Waage
        assert_eq!(varga_sign(9, 90.5), 3); // Krebs beginnt mit Krebs
    }

    #[test]
    fn dashamsa_even_signs_start_at_ninth() {
        assert_eq!(varga_sign(10, 1.0), 0); // Widder ungerade: Widder
        assert_eq!(varga_sign(10, 31.0), 9); // Stier gerade: ab 9. Zeichen (Steinbock)
    }

    #[test]
    fn dasha_lengths_sum_to_120() {
        let total: f64 = DASHA_ORDER.iter().map(|(_, y)| y).sum();
        assert_eq!(total, 120.0);
    }

    #[test]
    fn dasha_first_balance() {
        // Mond bei 0° Widder: Beginn von Ashwini (Ketu), nichts abgelaufen
        let d = build_dasha(2451545.0, 0.0, 2451545.0);
        assert_eq!(d[0].lord, "Ketu");
        assert!((d[0].start_jd - 2451545.0).abs() < 1e-6);
        // Mond in der Mitte von Ashwini: halbe Ketu-Dasha verbleibt
        let d = build_dasha(2451545.0, 360.0 / 27.0 / 2.0, 2451545.0);
        assert!((d[0].end_jd - 2451545.0 - 3.5 * YEAR_DAYS).abs() < 1e-6);
    }
}
