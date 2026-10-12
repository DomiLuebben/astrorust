//! Orts-Atlas: ~320 kuratierte Städte (DACH ausführlich) plus alle Zonen-Referenzorte der
//! System-tzdata (`zone1970.tab`). Jeder Ort trägt seine IANA-Zeitzone, sodass Sommerzeit und
//! historische Zeitzonen automatisch aufgelöst werden.

use crate::astrology::tz;
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;

const CURATED: &str = include_str!("atlas_data.txt");

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CityEntry {
    pub name: String,
    pub country: String,
    pub latitude: f64,
    pub longitude: f64,
    /// Heutige Standardzeit (Januar) – nur als Anhaltspunkt; maßgeblich ist `timezone`
    pub default_tz: f64,
    /// IANA-Zone, z. B. "Europe/Berlin"
    #[serde(default)]
    pub timezone: String,
}

fn parse_curated() -> Vec<CityEntry> {
    CURATED
        .lines()
        .filter(|l| !l.trim().is_empty() && !l.starts_with('#'))
        .filter_map(|l| {
            let p: Vec<&str> = l.trim().split('|').collect();
            if p.len() != 5 {
                return None;
            }
            Some(CityEntry {
                name: p[0].to_string(),
                country: p[1].to_string(),
                latitude: p[2].parse().ok()?,
                longitude: p[3].parse().ok()?,
                default_tz: 0.0,
                timezone: p[4].to_string(),
            })
        })
        .collect()
}

/// "+4852+01107" bzw. "+485230+0110730" → (lat, lon)
fn parse_iso6709(s: &str) -> Option<(f64, f64)> {
    let split = s[1..].find(['+', '-'])? + 1;
    let (lat_s, lon_s) = s.split_at(split);
    let conv = |t: &str, deg_digits: usize| -> Option<f64> {
        let sign = if t.starts_with('-') { -1.0 } else { 1.0 };
        let d = &t[1..];
        let deg: f64 = d.get(..deg_digits)?.parse().ok()?;
        let min: f64 = d.get(deg_digits..deg_digits + 2)?.parse().ok()?;
        let sec: f64 = d.get(deg_digits + 2..).filter(|x| !x.is_empty()).map(|x| x.parse().unwrap_or(0.0)).unwrap_or(0.0);
        Some(sign * (deg + min / 60.0 + sec / 3600.0))
    };
    Some((conv(lat_s, 2)?, conv(lon_s, 3)?))
}

fn country_name_de(code: &str, english: &str) -> String {
    match code {
        "DE" => "Deutschland",
        "AT" => "Österreich",
        "CH" => "Schweiz",
        "US" => "USA",
        "GB" => "Großbritannien",
        "FR" => "Frankreich",
        "IT" => "Italien",
        "ES" => "Spanien",
        "RU" => "Russland",
        "CN" => "China",
        "JP" => "Japan",
        "IN" => "Indien",
        "BR" => "Brasilien",
        "CA" => "Kanada",
        "AU" => "Australien",
        "MX" => "Mexiko",
        "AR" => "Argentinien",
        "ZA" => "Südafrika",
        "EG" => "Ägypten",
        "TR" => "Türkei",
        "GR" => "Griechenland",
        "NL" => "Niederlande",
        "BE" => "Belgien",
        "PL" => "Polen",
        "CZ" => "Tschechien",
        "HU" => "Ungarn",
        "DK" => "Dänemark",
        "SE" => "Schweden",
        "NO" => "Norwegen",
        "FI" => "Finnland",
        "PT" => "Portugal",
        "IE" => "Irland",
        "UA" => "Ukraine",
        "ID" => "Indonesien",
        "NZ" => "Neuseeland",
        _ => english,
    }
    .to_string()
}

fn zone_references() -> Vec<CityEntry> {
    let mut countries = std::collections::HashMap::new();
    for dir in ["/usr/share/zoneinfo", "/usr/lib/zoneinfo"] {
        if let Ok(t) = std::fs::read_to_string(format!("{dir}/iso3166.tab")) {
            for l in t.lines().filter(|l| !l.starts_with('#')) {
                if let Some((code, name)) = l.split_once('\t') {
                    countries.insert(code.to_string(), name.trim().to_string());
                }
            }
            break;
        }
    }
    let mut out = Vec::new();
    for dir in ["/usr/share/zoneinfo", "/usr/lib/zoneinfo"] {
        let Ok(t) = std::fs::read_to_string(format!("{dir}/zone1970.tab")) else { continue };
        for l in t.lines().filter(|l| !l.starts_with('#') && !l.trim().is_empty()) {
            let f: Vec<&str> = l.split('\t').collect();
            if f.len() < 3 {
                continue;
            }
            let code = f[0].split(',').next().unwrap_or("");
            let Some((lat, lon)) = parse_iso6709(f[1]) else { continue };
            let zone = f[2];
            let city = zone.rsplit('/').next().unwrap_or(zone).replace('_', " ");
            let english = countries.get(code).cloned().unwrap_or_else(|| code.to_string());
            out.push(CityEntry {
                name: city,
                country: country_name_de(code, &english),
                latitude: lat,
                longitude: lon,
                default_tz: 0.0,
                timezone: zone.to_string(),
            });
        }
        break;
    }
    out
}

fn haversine_deg(a: (f64, f64), b: (f64, f64)) -> f64 {
    let (la1, lo1, la2, lo2) = (a.0.to_radians(), a.1.to_radians(), b.0.to_radians(), b.1.to_radians());
    let h = ((la2 - la1) / 2.0).sin().powi(2) + la1.cos() * la2.cos() * ((lo2 - lo1) / 2.0).sin().powi(2);
    (2.0 * h.sqrt().asin()).to_degrees()
}

fn build_atlas() -> Vec<CityEntry> {
    let mut atlas = parse_curated();
    // Zonenreferenzen nur ergänzen, wenn nicht schon ein kuratierter Ort mit derselben Zone ≤ 1° entfernt liegt
    for z in zone_references() {
        let dup = atlas
            .iter()
            .any(|c| c.timezone == z.timezone && haversine_deg((c.latitude, c.longitude), (z.latitude, z.longitude)) < 1.0)
            || atlas.iter().any(|c| c.name.eq_ignore_ascii_case(&z.name) && c.timezone == z.timezone);
        if !dup {
            atlas.push(z);
        }
    }
    // Standardzeit im Januar des laufenden Jahres als Anhaltspunkt
    let jan1 = days_since_epoch_jan1_this_year();
    for c in &mut atlas {
        c.default_tz = tz::offset_at_utc(&c.timezone, jan1).unwrap_or(0.0);
    }
    atlas
}

fn days_since_epoch_jan1_this_year() -> i64 {
    let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map(|d| d.as_secs() as i64).unwrap_or(0);
    // grob: Jahr berechnen und auf den 1.1. 12:00 UTC runden
    let days = now / 86400;
    let year = 1970 + (days as f64 / 365.2425) as i64;
    let y = year - 1;
    let leap_days = y / 4 - y / 100 + y / 400 - (1969 / 4 - 1969 / 100 + 1969 / 400);
    ((year - 1970) * 365 + leap_days) * 86400 + 43200
}

pub fn get_atlas() -> Vec<CityEntry> {
    static ATLAS: OnceLock<Vec<CityEntry>> = OnceLock::new();
    ATLAS.get_or_init(build_atlas).clone()
}

/// Kleinschreibung, Umlaute und Akzente vereinheitlichen („Zürich“ findet „zurich“).
pub fn fold(s: &str) -> String {
    fold_with(s, true)
}

/// `expand`: ä→ae (deutsche Schreibung) oder ä→a (nur Grundbuchstabe, wie ohne Umlaut getippt).
fn fold_with(s: &str, expand: bool) -> String {
    s.chars()
        .map(|c| match c {
            'ä' | 'Ä' => (if expand { "ae" } else { "a" }).to_string(),
            'ö' | 'Ö' => (if expand { "oe" } else { "o" }).to_string(),
            'ü' | 'Ü' => (if expand { "ue" } else { "u" }).to_string(),
            'ß' => "ss".to_string(),
            'à' | 'á' | 'â' | 'ã' | 'å' | 'À' | 'Á' | 'Â' => "a".to_string(),
            'è' | 'é' | 'ê' | 'ë' | 'È' | 'É' | 'Ê' => "e".to_string(),
            'ì' | 'í' | 'î' | 'ï' => "i".to_string(),
            'ò' | 'ó' | 'ô' | 'õ' | 'ø' => "o".to_string(),
            'ù' | 'ú' | 'û' => "u".to_string(),
            'ç' => "c".to_string(),
            'ñ' => "n".to_string(),
            'ý' | 'ÿ' => "y".to_string(),
            other => other.to_lowercase().collect::<String>(),
        })
        .collect()
}

/// Sucht Orte; Treffer am Namensanfang kommen zuerst. Leere Suche liefert alle Orte.
pub fn search_cities(query: &str) -> Vec<CityEntry> {
    let atlas = get_atlas();
    if query.trim().is_empty() {
        return atlas;
    }
    let q_exp = fold_with(query.trim(), true);
    let q_base = fold_with(query.trim(), false);
    let split = |q: &str| match q.split_once(',') {
        Some((n, c)) => (n.trim().to_string(), Some(c.trim().to_string())),
        None => (q.to_string(), None),
    };
    let (name_exp, country_exp) = split(&q_exp);
    let (name_base, country_base) = split(&q_base);

    let mut starts: Vec<CityEntry> = Vec::new();
    let mut contains: Vec<CityEntry> = Vec::new();
    for c in atlas {
        let n_exp = fold_with(&c.name, true);
        let n_base = fold_with(&c.name, false);
        let c_exp = fold_with(&c.country, true);
        let c_base = fold_with(&c.country, false);
        if let (Some(ce), Some(cb)) = (&country_exp, &country_base) {
            if !(c_exp.contains(ce.as_str()) || c_base.contains(cb.as_str())) {
                continue;
            }
        }
        if n_exp.starts_with(&name_exp) || n_base.starts_with(&name_base) {
            starts.push(c);
        } else if n_exp.contains(&name_exp)
            || n_base.contains(&name_base)
            || (country_exp.is_none() && (c_exp.contains(&name_exp) || c_base.contains(&name_base)))
        {
            contains.push(c);
        }
    }
    starts.extend(contains);
    starts
}

/// Ort aus dem Atlas, der den Koordinaten am nächsten liegt (für die Zonenvorgabe bei freien Koordinaten).
pub fn nearest_city(lat: f64, lon: f64) -> Option<CityEntry> {
    get_atlas()
        .into_iter()
        .min_by(|a, b| {
            haversine_deg((a.latitude, a.longitude), (lat, lon))
                .partial_cmp(&haversine_deg((b.latitude, b.longitude), (lat, lon)))
                .unwrap_or(std::cmp::Ordering::Equal)
        })
}

/// Alle verfügbaren IANA-Zonen (aus `zone1970.tab` + Atlas) für die Auswahlliste.
pub fn zone_names() -> Vec<String> {
    let mut v: Vec<String> = get_atlas().into_iter().map(|c| c.timezone).collect();
    v.sort();
    v.dedup();
    v
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn atlas_has_many_entries_with_valid_zones() {
        let a = get_atlas();
        assert!(a.len() > 400, "{}", a.len());
        for c in a.iter().take(2000) {
            assert!(tz::zone_exists(&c.timezone), "{} → {}", c.name, c.timezone);
        }
    }

    #[test]
    fn search_ignores_umlauts_and_finds_country() {
        assert!(search_cities("zurich").iter().any(|c| c.name == "Zürich"));
        assert!(search_cities("Köln").iter().any(|c| c.name == "Köln"));
        assert!(search_cities("Ulm, Deutschland").iter().any(|c| c.name == "Ulm"));
        assert!(search_cities("schweiz").iter().any(|c| c.name == "Bern"));
    }

    #[test]
    fn nearest_city_maps_coordinates_to_zone() {
        assert_eq!(nearest_city(48.0, 9.9).unwrap().timezone, "Europe/Berlin");
        assert_eq!(nearest_city(-33.0, 151.0).unwrap().timezone, "Australia/Sydney");
    }

    #[test]
    fn iso6709_parsing() {
        let (la, lo) = parse_iso6709("+5230+01322").unwrap();
        assert!((la - 52.5).abs() < 1e-9 && (lo - 13.3667).abs() < 1e-3);
        let (la, lo) = parse_iso6709("-3352+15113").unwrap();
        assert!(la < 0.0 && lo > 0.0);
    }
}
