//! Prognose: Sekundärprogression, Solarbogen, Returns (Solar/Lunar/Planeten),
//! Transitsuche mit exakten Zeitpunkten, Himmelsereignisse (Ingresse, Stationen,
//! Mondphasen, Finsternisse) und grafische Ephemeride.

use crate::astrology::calculator::{
    assemble_chart, build_chart, calculate_chart, point_position, resolve_time, ChartInput, ChartMeta, HouseSet,
    PointPos,
};
use crate::astrology::engine;
use crate::astrology::models::*;
use crate::astrology::transits::{chart_points, cross_aspects, light_settings, MAJOR_ASPECTS};
use crate::astrology::tz;
use crate::astrology::util::{days_to_epoch_secs, format_orb, julian_day_ut, normalize_deg, signed_diff, split_dm};
use serde::{Deserialize, Serialize};

/// Länge eines tropischen Jahres in Tagen (Tag-für-Jahr-Schlüssel der Sekundärprogression).
const TROPICAL_YEAR: f64 = 365.242189;

// ──────────────────────────────────────────────────────────────────────────
// Zeit-Hilfen
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimePoint {
    pub year: i32,
    pub month: i32,
    pub day: i32,
    #[serde(default)]
    pub hour: u32,
    #[serde(default)]
    pub minute: u32,
    /// Offset der Eingabezeit zu UTC (Stunden); Standard 0 = UTC
    #[serde(default)]
    pub timezone_offset: f64,
}

impl TimePoint {
    pub fn jd_ut(&self) -> f64 {
        julian_day_ut(self.year, self.month, self.day, self.hour as f64 + self.minute as f64 / 60.0 - self.timezone_offset)
    }
}

/// Formatiert einen UT-JD als Ortszeit der Anzeigezone (oder UTC).
pub fn format_jd(jd_ut: f64, zone: Option<&str>) -> String {
    let mut offset = 0.0;
    let mut tag = "UTC".to_string();
    if let Some(z) = zone {
        if let Ok(o) = tz::offset_at_utc(z, days_to_epoch_secs(jd_ut)) {
            offset = o;
            tag = format!("UTC{}{:02}:{:02}", if o < 0.0 { '-' } else { '+' }, o.abs().floor() as i32, ((o.abs() - o.abs().floor()) * 60.0).round() as i32);
        }
    }
    let d = sweph::date_from_julian_day(jd_ut + offset / 24.0);
    let h = d.hour.floor();
    let m = ((d.hour - h) * 60.0).round() as u32;
    let (h, m) = if m == 60 { (h as u32 + 1, 0) } else { (h as u32, m) };
    format!("{:04}-{:02}-{:02} {:02}:{:02} {}", d.year, d.month, d.day, h, m, tag)
}

fn settings_of(req: &ChartRequest) -> ChartSettings {
    light_settings(req)
}

fn lon_at(pt: CelestialPoint, jd: f64, settings: &ChartSettings) -> Result<(f64, f64), String> {
    let p = point_position(pt, jd, settings)?;
    Ok((p.lon, p.speed))
}

/// Setzt den Sidereal-Modus für die Dauer einer Prognoserechnung.
fn prepare(settings: &ChartSettings) {
    if settings.zodiac == Zodiac::Sidereal {
        engine::set_sidereal(settings.ayanamsa);
    }
}

fn bisect<F: Fn(f64) -> Result<f64, String>>(mut lo: f64, mut hi: f64, f: F) -> Result<f64, String> {
    let mut flo = f(lo)?;
    for _ in 0..48 {
        let mid = (lo + hi) / 2.0;
        let fm = f(mid)?;
        if (fm < 0.0) == (flo < 0.0) {
            lo = mid;
            flo = fm;
        } else {
            hi = mid;
        }
    }
    Ok((lo + hi) / 2.0)
}

// ──────────────────────────────────────────────────────────────────────────
// Progressionen
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProgressionRequest {
    pub natal: ChartRequest,
    pub target: TimePoint,
    /// "secondary" (Tag = Jahr), "solar_arc", "tertiary" (Tag = Mondumlauf) oder "minor" (Mondumlauf = Jahr)
    #[serde(default = "default_prog_kind")]
    pub kind: String,
    /// Orbis für Aspekte zum Radix (Standard 1°)
    #[serde(default = "default_prog_orb")]
    pub orb: f64,
}
fn default_prog_kind() -> String {
    "secondary".into()
}
fn default_prog_orb() -> f64 {
    1.0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProgressionResponse {
    pub kind: String,
    pub kind_label: String,
    pub age_years: f64,
    pub natal_chart: ChartResponse,
    pub progressed_chart: ChartResponse,
    /// Gelaufener Bogen der Sonne (Solarbogen) in Grad
    pub solar_arc: f64,
    pub aspects_to_natal: Vec<TransitToNatalAspect>,
    pub moon_phase: Option<String>,
}

fn arc_shift_chart(natal: &ChartResponse, arc: f64, label: &str, settings: &ChartSettings) -> ChartResponse {
    let points: Vec<PointPos> = natal
        .planets
        .iter()
        .map(|p| PointPos {
            id: p.id,
            lon: normalize_deg(p.longitude + arc),
            lat: p.latitude,
            dist: p.distance,
            speed: 0.0,
            retro: p.is_retrograde,
            decl: p.declination,
        })
        .collect();
    let mut cusps = [0.0; 12];
    for (i, h) in natal.houses.iter().enumerate().take(12) {
        cusps[i] = normalize_deg(h.longitude + arc);
    }
    let meta = ChartMeta {
        name: format!("{} – {}", natal.name, label),
        date_time: label.to_string(),
        location_name: natal.location_name.clone(),
        latitude: natal.latitude,
        longitude: natal.longitude,
        julian_day: natal.julian_day,
        house_system_label: natal.house_system.clone(),
        timezone_info: None,
        ayanamsa_name: natal.ayanamsa_name.clone(),
        ayanamsa_value: natal.ayanamsa_value,
        ephemeris_files: natal.ephemeris_files,
    };
    let houses = HouseSet {
        cusps,
        ascendant: normalize_deg(natal.angles.ascendant + arc),
        midheaven: normalize_deg(natal.angles.midheaven + arc),
        vertex: normalize_deg(natal.angles.vertex + arc),
    };
    let mut s = settings.clone();
    s.fixed_stars = false;
    assemble_chart(&meta, points, &houses, &s)
}

pub fn calculate_progression(req: &ProgressionRequest) -> Result<ProgressionResponse, String> {
    let natal = calculate_chart(&req.natal)?;
    let (natal_jd, _, _) = resolve_time(&req.natal)?;
    let settings = settings_of(&req.natal);
    let target_jd = req.target.jd_ut();
    if target_jd < natal_jd {
        return Err("Der Prognosezeitpunkt liegt vor der Geburt.".into());
    }
    let age_days = target_jd - natal_jd;
    let age_years = age_days / TROPICAL_YEAR;
    let _g = engine::lock();
    prepare(&settings);

    // Sekundärprogression: ein Tag nach der Geburt = ein Jahr
    let sec_jd = natal_jd + age_years;
    let sec_sun = lon_at(CelestialPoint::Sun, sec_jd, &settings)?.0;
    let nat_sun = natal.planets.iter().find(|p| p.id == CelestialPoint::Sun).map(|p| p.longitude).unwrap_or(0.0);
    let solar_arc = normalize_deg(sec_sun - nat_sun);

    let (kind_label, chart) = match req.kind.as_str() {
        "solar_arc" => {
            let label = format!("Solarbogen {:.2}° (Alter {:.1})", solar_arc, age_years);
            ("Solarbogen-Direktionen".to_string(), arc_shift_chart(&natal, solar_arc, &label, &settings))
        }
        "tertiary" => {
            // Tertiär I: ein Tag = ein Mondumlauf (27,321582 Tage)
            let jd = natal_jd + age_days / 27.321582;
            ("Tertiärprogression".to_string(), progressed_chart(&req.natal, &natal, jd, &settings, "Tertiärprogression", target_jd)?)
        }
        "minor" => {
            // Sekundäre Minorprogression: ein Mondumlauf = ein Jahr
            let jd = natal_jd + age_years * 27.321582;
            ("Minorprogression".to_string(), progressed_chart(&req.natal, &natal, jd, &settings, "Minorprogression", target_jd)?)
        }
        _ => ("Sekundärprogression".to_string(), progressed_chart(&req.natal, &natal, sec_jd, &settings, "Sekundärprogression", target_jd)?),
    };

    let aspects = cross_aspects(&chart_points(&chart, true), &chart_points(&natal, true), &MAJOR_ASPECTS, req.orb);

    // Progressive Mondphase (Elongation Mond–Sonne im progredierten Horoskop)
    let phase = {
        let sun = chart.planets.iter().find(|p| p.id == CelestialPoint::Sun);
        let moon = chart.planets.iter().find(|p| p.id == CelestialPoint::Moon);
        match (sun, moon) {
            (Some(s), Some(m)) => Some(moon_phase_name(normalize_deg(m.longitude - s.longitude)).to_string()),
            _ => None,
        }
    };

    Ok(ProgressionResponse {
        kind: req.kind.clone(),
        kind_label,
        age_years,
        natal_chart: natal,
        progressed_chart: chart,
        solar_arc,
        aspects_to_natal: aspects,
        moon_phase: phase,
    })
}

fn progressed_chart(
    req: &ChartRequest,
    natal: &ChartResponse,
    jd: f64,
    settings: &ChartSettings,
    label: &str,
    target_jd: f64,
) -> Result<ChartResponse, String> {
    let mut s = settings.clone();
    s.analysis = true;
    s.fixed_stars = false;
    let mut c = build_chart(&ChartInput {
        name: format!("{} – {}", natal.name, label),
        jd_ut: jd,
        latitude: req.latitude,
        longitude: req.longitude,
        house_system: req.house_system.unwrap_or(HouseSystemChoice::Placidus),
        settings: &s,
        date_time_label: format!("{} für {}", label, format_jd(target_jd, None)),
        location_name: natal.location_name.clone(),
        timezone_info: None,
    })?;
    c.date_time = format!("{} (Ephemeridenzeit {})", label, format_jd(jd, None));
    Ok(c)
}

pub fn moon_phase_name(elongation: f64) -> &'static str {
    match elongation {
        e if e < 22.5 || e >= 337.5 => "Neumond",
        e if e < 67.5 => "Zunehmende Sichel",
        e if e < 112.5 => "Zunehmender Halbmond (erstes Viertel)",
        e if e < 157.5 => "Zunehmender Mond (Dreiviertel)",
        e if e < 202.5 => "Vollmond",
        e if e < 247.5 => "Abnehmender Mond (Dreiviertel)",
        e if e < 292.5 => "Abnehmender Halbmond (letztes Viertel)",
        _ => "Abnehmende Sichel",
    }
}

// ──────────────────────────────────────────────────────────────────────────
// Returns
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReturnRequest {
    pub natal: ChartRequest,
    /// Planet des Returns: "Sun", "Moon", "Mercury", … "Pluto", "Chiron"
    #[serde(default = "default_return_body")]
    pub body: String,
    /// Suche ab diesem Zeitpunkt (UTC)
    pub start: TimePoint,
    /// Wie viele aufeinanderfolgende Returns aufgelistet werden (Horoskop gibt es nur für den ersten)
    #[serde(default = "default_count")]
    pub count: u32,
    /// Ort des Return-Horoskops (Standard: Geburtsort; für Relokation anderer Ort)
    #[serde(default)]
    pub latitude: Option<f64>,
    #[serde(default)]
    pub longitude: Option<f64>,
    #[serde(default)]
    pub location_name: Option<String>,
    /// Zone zur Anzeige der Ortszeit
    #[serde(default)]
    pub display_timezone: Option<String>,
}
fn default_return_body() -> String {
    "Sun".into()
}
fn default_count() -> u32 {
    1
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReturnEntry {
    pub jd: f64,
    pub label: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReturnResponse {
    pub body: String,
    pub returns: Vec<ReturnEntry>,
    pub chart: ChartResponse,
    pub natal_chart: ChartResponse,
    pub aspects_to_natal: Vec<TransitToNatalAspect>,
}

pub fn point_by_name(name: &str) -> Option<CelestialPoint> {
    use CelestialPoint as P;
    Some(match name.to_lowercase().as_str() {
        "sun" | "sonne" => P::Sun,
        "moon" | "mond" => P::Moon,
        "mercury" | "merkur" => P::Mercury,
        "venus" => P::Venus,
        "mars" => P::Mars,
        "jupiter" => P::Jupiter,
        "saturn" => P::Saturn,
        "uranus" => P::Uranus,
        "neptune" | "neptun" => P::Neptune,
        "pluto" => P::Pluto,
        "chiron" => P::Chiron,
        "truenode" | "node" | "mondknoten" => P::TrueNode,
        "lilith" => P::Lilith,
        "ceres" => P::Ceres,
        "pallas" => P::Pallas,
        "juno" => P::Juno,
        "vesta" => P::Vesta,
        _ => return None,
    })
}

/// Erstes Zusammentreffen (rechtläufig) des Planeten mit `natal_lon` ab `start_jd`.
fn find_return(pt: CelestialPoint, natal_lon: f64, start_jd: f64, settings: &ChartSettings) -> Result<f64, String> {
    let step = match pt {
        CelestialPoint::Moon => 0.25,
        CelestialPoint::Sun | CelestialPoint::Mercury | CelestialPoint::Venus => 1.0,
        CelestialPoint::Mars => 2.0,
        CelestialPoint::Jupiter | CelestialPoint::Saturn => 5.0,
        _ => 20.0,
    };
    let period_days = match pt {
        CelestialPoint::Moon => 30.0,
        CelestialPoint::Sun => 370.0,
        CelestialPoint::Mercury => 400.0,
        CelestialPoint::Venus => 700.0,
        CelestialPoint::Mars => 1000.0,
        CelestialPoint::Jupiter => 4800.0,
        CelestialPoint::Saturn => 11000.0,
        CelestialPoint::Chiron => 19500.0,
        CelestialPoint::Uranus => 31000.0,
        CelestialPoint::Neptune => 61000.0,
        CelestialPoint::Pluto => 91000.0,
        _ => 5000.0,
    };
    let f = |jd: f64| -> Result<f64, String> { Ok(signed_diff(lon_at(pt, jd, settings)?.0, natal_lon)) };
    let mut t = start_jd;
    let mut prev = f(t)?;
    let end = start_jd + period_days;
    while t < end {
        let nt = t + step;
        let cur = f(nt)?;
        // Nulldurchgang von negativ nach positiv = rechtläufiges Überlaufen (Sprung bei ±180° ausschließen)
        if prev < 0.0 && cur >= 0.0 && (cur - prev).abs() < 90.0 {
            return bisect(t, nt, &f);
        }
        prev = cur;
        t = nt;
    }
    Err("Kein Return im Suchzeitraum gefunden.".into())
}

pub fn calculate_return(req: &ReturnRequest) -> Result<ReturnResponse, String> {
    let natal = calculate_chart(&req.natal)?;
    let settings = settings_of(&req.natal);
    let pt = point_by_name(&req.body).ok_or_else(|| format!("Unbekannter Körper: {}", req.body))?;
    let natal_lon = natal
        .planets
        .iter()
        .find(|p| p.id == pt)
        .map(|p| p.longitude)
        .ok_or_else(|| format!("{} ist im Radix nicht berechnet (Einstellungen prüfen).", req.body))?;
    let _g = engine::lock();
    prepare(&settings);

    let count = req.count.clamp(1, 24);
    let mut start = req.start.jd_ut();
    let mut returns = Vec::new();
    let mut first_jd = None;
    for _ in 0..count {
        let jd = find_return(pt, natal_lon, start, &settings)?;
        if first_jd.is_none() {
            first_jd = Some(jd);
        }
        returns.push(ReturnEntry { jd, label: format_jd(jd, req.display_timezone.as_deref()) });
        // nächstes Mal frühestens kurz nach dem jetzigen
        start = jd + match pt {
            CelestialPoint::Moon => 20.0,
            CelestialPoint::Sun => 300.0,
            CelestialPoint::Mercury => 60.0,
            CelestialPoint::Venus => 150.0,
            CelestialPoint::Mars => 400.0,
            _ => 1000.0,
        };
    }
    let jd = first_jd.unwrap();
    let lat = req.latitude.unwrap_or(req.natal.latitude);
    let lon = req.longitude.unwrap_or(req.natal.longitude);
    let mut s = settings.clone();
    s.analysis = true;
    s.fixed_stars = false;
    let label = format!("{}-Return", pt.name_de());
    let mut chart = build_chart(&ChartInput {
        name: format!("{} – {}", natal.name, label),
        jd_ut: jd,
        latitude: lat,
        longitude: lon,
        house_system: req.natal.house_system.unwrap_or(HouseSystemChoice::Placidus),
        settings: &s,
        date_time_label: format_jd(jd, req.display_timezone.as_deref()),
        location_name: req
            .location_name
            .clone()
            .filter(|n| !n.trim().is_empty())
            .unwrap_or_else(|| natal.location_name.clone()),
        timezone_info: None,
    })?;
    chart.name = format!("{} – {}", natal.name, label);

    let aspects = cross_aspects(&chart_points(&chart, true), &chart_points(&natal, true), &MAJOR_ASPECTS, 2.0);
    Ok(ReturnResponse { body: req.body.clone(), returns, chart, natal_chart: natal, aspects_to_natal: aspects })
}

// ──────────────────────────────────────────────────────────────────────────
// Transitsuche
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitSearchRequest {
    pub natal: ChartRequest,
    pub start: TimePoint,
    pub end: TimePoint,
    /// Transitierende Körper; leer = Sonne bis Pluto
    #[serde(default)]
    pub bodies: Vec<String>,
    /// Aspekte; leer = Konjunktion, Sextil, Quadrat, Trigon, Opposition
    #[serde(default)]
    pub aspects: Vec<AspectType>,
    /// Orbis, ab dem ein Transit „beginnt“/„endet“ (Standard 1°)
    #[serde(default = "default_prog_orb")]
    pub orb: f64,
    #[serde(default)]
    pub display_timezone: Option<String>,
    /// Natalpunkte; leer = alle Planeten + AC + MC
    #[serde(default)]
    pub natal_points: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitEvent {
    pub transit_body: String,
    pub transit_glyph: String,
    pub natal_point: String,
    pub natal_glyph: String,
    pub aspect_name: String,
    pub aspect_glyph: String,
    pub color_hex: String,
    pub enter_jd: f64,
    pub leave_jd: f64,
    pub enter_label: String,
    pub leave_label: String,
    pub exact_jds: Vec<f64>,
    pub exact_labels: Vec<String>,
    /// Beginnt schon vor dem Suchzeitraum / dauert über dessen Ende hinaus
    pub starts_before_range: bool,
    pub ends_after_range: bool,
    pub passes: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransitSearchResponse {
    pub natal_chart: ChartResponse,
    pub start_jd: f64,
    pub end_jd: f64,
    pub events: Vec<TransitEvent>,
}

fn default_transit_bodies() -> Vec<CelestialPoint> {
    CelestialPoint::classical().to_vec()
}

pub fn search_transits(req: &TransitSearchRequest) -> Result<TransitSearchResponse, String> {
    let natal = calculate_chart(&req.natal)?;
    let settings = settings_of(&req.natal);
    let start = req.start.jd_ut();
    let end = req.end.jd_ut();
    if end <= start {
        return Err("Das Ende liegt vor dem Beginn.".into());
    }
    if end - start > 3660.0 {
        return Err("Der Suchzeitraum ist auf 10 Jahre begrenzt.".into());
    }
    let bodies: Vec<CelestialPoint> = if req.bodies.is_empty() {
        default_transit_bodies()
    } else {
        req.bodies.iter().filter_map(|b| point_by_name(b)).collect()
    };
    let aspect_list: Vec<AspectType> = if req.aspects.is_empty() {
        vec![AspectType::Conjunction, AspectType::Sextile, AspectType::Square, AspectType::Trine, AspectType::Opposition]
    } else {
        req.aspects.clone()
    };
    // Natalziele
    let all_targets = chart_points(&natal, true);
    let targets: Vec<_> = if req.natal_points.is_empty() {
        all_targets
    } else {
        let wanted: Vec<String> = req.natal_points.iter().map(|s| s.to_lowercase()).collect();
        all_targets
            .into_iter()
            .filter(|t| {
                wanted.contains(&t.name.to_lowercase())
                    || wanted.contains(&t.glyph.to_lowercase())
                    || point_by_name(&wanted.join("")).is_some_and(|x| x == t.id)
            })
            .collect()
    };

    let _g = engine::lock();
    prepare(&settings);
    let orb = req.orb.clamp(0.1, 5.0);
    let mut events: Vec<TransitEvent> = Vec::new();

    for &body in &bodies {
        // Schrittweite: höchstens ein Viertel der Durchlaufzeit des Orbis
        let step = match body {
            CelestialPoint::Moon => 0.1,
            CelestialPoint::Sun | CelestialPoint::Mercury | CelestialPoint::Venus => 0.5,
            CelestialPoint::Mars => 1.0,
            _ => 2.0,
        };
        // Positionen vorab berechnen
        let n = ((end - start) / step).ceil() as usize + 2;
        let mut times = Vec::with_capacity(n);
        let mut lons = Vec::with_capacity(n);
        for i in 0..n {
            let t = start + i as f64 * step;
            times.push(t);
            lons.push(lon_at(body, t, &settings)?.0);
        }

        for tgt in &targets {
            for &asp in &aspect_list {
                let angle = asp.target_angle();
                // Beide Richtungen (vor/hinter dem Natalpunkt), bei 0° und 180° nur eine
                let signs: &[f64] = if angle == 0.0 || angle == 180.0 { &[1.0] } else { &[1.0, -1.0] };
                for &sgn in signs {
                    let f_at = |lon: f64| signed_diff(lon, normalize_deg(tgt.lon + sgn * angle));
                    let f_time = |t: f64| -> Result<f64, String> { Ok(f_at(lon_at(body, t, &settings)?.0)) };

                    let mut i = 0;
                    while i < n {
                        if f_at(lons[i]).abs() <= orb {
                            // Intervall beginnt (ggf. schon vor dem Zeitraum)
                            let begin_idx = i;
                            let mut j = i;
                            while j + 1 < n && f_at(lons[j + 1]).abs() <= orb {
                                j += 1;
                            }
                            // exakte Durchgänge im Intervall
                            let mut exacts = Vec::new();
                            for k in begin_idx..j {
                                let (a, b) = (f_at(lons[k]), f_at(lons[k + 1]));
                                if (a < 0.0) != (b < 0.0) && (a - b).abs() < 90.0 {
                                    exacts.push(bisect(times[k], times[k + 1], &f_time)?);
                                }
                            }
                            // Ränder des Orbis verfeinern
                            let enter = if begin_idx == 0 {
                                start
                            } else {
                                let edge = |t: f64| -> Result<f64, String> { Ok(f_time(t)?.abs() - orb) };
                                bisect(times[begin_idx - 1], times[begin_idx], edge)?
                            };
                            let leave = if j + 1 >= n {
                                end
                            } else {
                                let edge = |t: f64| -> Result<f64, String> { Ok(f_time(t)?.abs() - orb) };
                                bisect(times[j], times[j + 1], edge)?
                            };
                            // nur melden, wenn das Intervall den Zeitraum berührt
                            if leave >= start && enter <= end {
                                let exacts: Vec<f64> = exacts.into_iter().filter(|e| *e >= start && *e <= end).collect();
                                events.push(TransitEvent {
                                    transit_body: body.name_de().to_string(),
                                    transit_glyph: body.glyph().to_string(),
                                    natal_point: tgt.name.clone(),
                                    natal_glyph: tgt.glyph.clone(),
                                    aspect_name: asp.name_de().to_string(),
                                    aspect_glyph: asp.glyph().to_string(),
                                    color_hex: asp.color_hex().to_string(),
                                    enter_jd: enter,
                                    leave_jd: leave,
                                    enter_label: format_jd(enter, req.display_timezone.as_deref()),
                                    leave_label: format_jd(leave, req.display_timezone.as_deref()),
                                    exact_labels: exacts.iter().map(|e| format_jd(*e, req.display_timezone.as_deref())).collect(),
                                    passes: exacts.len() as u32,
                                    exact_jds: exacts,
                                    starts_before_range: begin_idx == 0,
                                    ends_after_range: j + 1 >= n,
                                });
                            }
                            i = j + 1;
                        } else {
                            i += 1;
                        }
                    }
                }
            }
        }
    }

    // Zusammenhängende Durchgänge desselben Transits (Rückläufigkeit) in einen Ereignisblock fassen
    events.sort_by(|a, b| {
        (&a.transit_body, &a.natal_point, &a.aspect_name, a.enter_jd.to_bits())
            .partial_cmp(&(&b.transit_body, &b.natal_point, &b.aspect_name, b.enter_jd.to_bits()))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    events.sort_by(|a, b| {
        let ka = a.exact_jds.first().copied().unwrap_or(a.enter_jd);
        let kb = b.exact_jds.first().copied().unwrap_or(b.enter_jd);
        ka.partial_cmp(&kb).unwrap_or(std::cmp::Ordering::Equal)
    });
    Ok(TransitSearchResponse { natal_chart: natal, start_jd: start, end_jd: end, events })
}

// ──────────────────────────────────────────────────────────────────────────
// Himmelsereignisse
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkyEventsRequest {
    pub start: TimePoint,
    pub end: TimePoint,
    /// Natalbezug für Finsternis-/Phasenkontakte (optional)
    #[serde(default)]
    pub natal: Option<ChartRequest>,
    #[serde(default)]
    pub display_timezone: Option<String>,
    /// Welche Arten: "ingress", "station", "phase", "eclipse"; leer = alle
    #[serde(default)]
    pub kinds: Vec<String>,
    /// Zodiak für Ingresse (Standard tropisch)
    #[serde(default)]
    pub settings: Option<ChartSettings>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkyEvent {
    pub kind: String,
    pub jd: f64,
    pub label: String,
    pub title: String,
    pub detail: String,
    pub glyph: String,
    pub longitude: f64,
    pub formatted: String,
    pub natal_contacts: Vec<String>,
}

pub fn sky_events(req: &SkyEventsRequest) -> Result<Vec<SkyEvent>, String> {
    let start = req.start.jd_ut();
    let end = req.end.jd_ut();
    if end <= start {
        return Err("Das Ende liegt vor dem Beginn.".into());
    }
    if end - start > 3660.0 {
        return Err("Der Zeitraum ist auf 10 Jahre begrenzt.".into());
    }
    let settings = req.settings.clone().unwrap_or_default();
    let want = |k: &str| req.kinds.is_empty() || req.kinds.iter().any(|x| x == k);
    let zone = req.display_timezone.as_deref();

    let natal_points = match &req.natal {
        Some(n) => Some(chart_points(&calculate_chart(n)?, true)),
        None => None,
    };
    let contacts = |lon: f64, orb: f64, axis: bool| -> Vec<String> {
        let Some(pts) = &natal_points else { return Vec::new() };
        pts.iter()
            .filter_map(|p| {
                let d1 = crate::astrology::util::angle_diff(lon, p.lon);
                let d2 = if axis { (d1 - 180.0).abs() } else { 999.0 };
                let (o, kind) = if d1 <= d2 { (d1, "☌") } else { (d2, "☍") };
                if o <= orb {
                    Some(format!("{} {} {} (Orb {})", kind, p.glyph, p.name, format_orb(o)))
                } else {
                    None
                }
            })
            .collect()
    };
    let fmt_lon = |lon: f64| {
        let (sign, sd) = ZodiacSign::from_degrees(lon);
        let (d, m) = split_dm(sd);
        format!("{} {:02}° {:02}'", sign.glyph(), d, m)
    };

    let _g = engine::lock();
    prepare(&settings);
    let mut out: Vec<SkyEvent> = Vec::new();
    let step = 0.5;
    let n = ((end - start) / step).ceil() as usize + 2;

    // Ingresse und Stationen (Sonne bis Pluto, ohne Mond)
    if want("ingress") || want("station") {
        for &body in CelestialPoint::classical().iter().filter(|b| **b != CelestialPoint::Moon) {
            let bstep = if matches!(body, CelestialPoint::Sun | CelestialPoint::Mercury | CelestialPoint::Venus) { 0.5 } else { 1.0 };
            let nb = ((end - start) / bstep).ceil() as usize + 2;
            let mut prev_t = start;
            let mut prev = point_position(body, prev_t, &settings)?;
            for i in 1..nb {
                let t = start + i as f64 * bstep;
                let cur = point_position(body, t, &settings)?;
                if want("ingress") && body != CelestialPoint::Sun || want("ingress") {
                    let s0 = (prev.lon / 30.0).floor() as i32;
                    let s1 = (cur.lon / 30.0).floor() as i32;
                    if s0 != s1 && crate::astrology::util::angle_diff(prev.lon, cur.lon) < 90.0 {
                        // Grenze der betroffenen Zeichen
                        let boundary = (if signed_diff(cur.lon, prev.lon) > 0.0 { s1 } else { s0 } as f64) * 30.0;
                        let boundary = boundary.rem_euclid(360.0);
                        let f = |tt: f64| -> Result<f64, String> {
                            Ok(signed_diff(point_position(body, tt, &settings)?.lon, boundary))
                        };
                        let tx = bisect(prev_t, t, &f)?;
                        let sign = ZodiacSign::from_degrees(cur.lon).0;
                        let retro = cur.speed < 0.0;
                        out.push(SkyEvent {
                            kind: "ingress".into(),
                            jd: tx,
                            label: format_jd(tx, zone),
                            title: format!("{} {} in {}{}", body.glyph(), body.name_de(), sign.name_de(), if retro { " (rückläufig)" } else { "" }),
                            detail: format!("Eintritt in das Zeichen {}", sign.name_de()),
                            glyph: body.glyph().to_string(),
                            longitude: boundary,
                            formatted: fmt_lon(boundary),
                            natal_contacts: Vec::new(),
                        });
                    }
                }
                if want("station") && body != CelestialPoint::Sun {
                    if (prev.speed < 0.0) != (cur.speed < 0.0) {
                        let f = |tt: f64| -> Result<f64, String> { Ok(point_position(body, tt, &settings)?.speed) };
                        let tx = bisect(prev_t, t, &f)?;
                        let pos = point_position(body, tx, &settings)?;
                        let to_retro = cur.speed < 0.0;
                        out.push(SkyEvent {
                            kind: "station".into(),
                            jd: tx,
                            label: format_jd(tx, zone),
                            title: format!("{} {} {}", body.glyph(), body.name_de(), if to_retro { "wird rückläufig" } else { "wird rechtläufig" }),
                            detail: format!("Station bei {}", fmt_lon(pos.lon)),
                            glyph: body.glyph().to_string(),
                            longitude: pos.lon,
                            formatted: fmt_lon(pos.lon),
                            natal_contacts: contacts(pos.lon, 2.0, false),
                        });
                    }
                }
                prev_t = t;
                prev = cur;
            }
        }
    }

    // Mondphasen
    if want("phase") {
        let elong = |t: f64| -> Result<f64, String> {
            let s = point_position(CelestialPoint::Sun, t, &settings)?.lon;
            let m = point_position(CelestialPoint::Moon, t, &settings)?.lon;
            Ok(normalize_deg(m - s))
        };
        let mut prev_t = start;
        let mut prev = elong(prev_t)?;
        let names = ["Neumond", "Erstes Viertel", "Vollmond", "Letztes Viertel"];
        for i in 1..n {
            let t = start + i as f64 * step;
            let cur = elong(t)?;
            let (q0, q1) = ((prev / 90.0).floor() as i32, (cur / 90.0).floor() as i32);
            if q0 != q1 || cur < prev {
                // Welcher Viertelschritt wurde überschritten?
                let crossed = if cur < prev { 0 } else { q1 } as usize % 4;
                let target = crossed as f64 * 90.0;
                let f = |tt: f64| -> Result<f64, String> { Ok(signed_diff(elong(tt)?, target)) };
                let tx = bisect(prev_t, t, &f)?;
                let moon = point_position(CelestialPoint::Moon, tx, &settings)?;
                let glyph = ["🌑", "🌓", "🌕", "🌗"][crossed];
                out.push(SkyEvent {
                    kind: "phase".into(),
                    jd: tx,
                    label: format_jd(tx, zone),
                    title: format!("{} {}", glyph, names[crossed]),
                    detail: format!("Mond bei {}", fmt_lon(moon.lon)),
                    glyph: glyph.to_string(),
                    longitude: moon.lon,
                    formatted: fmt_lon(moon.lon),
                    natal_contacts: contacts(moon.lon, 3.0, crossed == 0 || crossed == 2),
                });
            }
            prev_t = t;
            prev = cur;
        }
    }

    // Finsternisse
    if want("eclipse") {
        let mut cursor = start;
        for solar in [true, false] {
            cursor = start;
            for _ in 0..40 {
                let ecl = if solar { sweph::next_solar_eclipse(cursor) } else { sweph::next_lunar_eclipse(cursor) }
                    .map_err(|e| format!("Finsternissuche: {e}"))?;
                if ecl.maximum_jd > end {
                    break;
                }
                let body = if solar { CelestialPoint::Sun } else { CelestialPoint::Moon };
                let pos = point_position(body, ecl.maximum_jd, &settings)?;
                let kind_de = match ecl.kind {
                    sweph::EclipseKind::Total => "total",
                    sweph::EclipseKind::Annular => "ringförmig",
                    sweph::EclipseKind::Hybrid => "hybrid",
                    sweph::EclipseKind::Partial => "partiell",
                    sweph::EclipseKind::Penumbral => "Halbschatten",
                    sweph::EclipseKind::Unknown => "",
                };
                out.push(SkyEvent {
                    kind: "eclipse".into(),
                    jd: ecl.maximum_jd,
                    label: format_jd(ecl.maximum_jd, zone),
                    title: format!("{} {}finsternis {}", if solar { "☉" } else { "☽" }, if solar { "Sonnen" } else { "Mond" }, kind_de),
                    detail: format!("Maximum bei {}", fmt_lon(pos.lon)),
                    glyph: if solar { "☉" } else { "☽" }.to_string(),
                    longitude: pos.lon,
                    formatted: fmt_lon(pos.lon),
                    natal_contacts: contacts(pos.lon, 3.0, true),
                });
                cursor = ecl.maximum_jd + 20.0;
            }
        }
        let _ = cursor;
    }

    out.sort_by(|a, b| a.jd.partial_cmp(&b.jd).unwrap_or(std::cmp::Ordering::Equal));
    out.dedup_by(|a, b| a.kind == b.kind && a.title == b.title && (a.jd - b.jd).abs() < 0.01);
    Ok(out)
}

// ──────────────────────────────────────────────────────────────────────────
// Grafische Ephemeride (90°-Scheibe)
// ──────────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphicEphemerisRequest {
    pub natal: ChartRequest,
    pub start: TimePoint,
    pub end: TimePoint,
    #[serde(default)]
    pub bodies: Vec<String>,
    /// Abtastung in Tagen (Standard 1)
    #[serde(default)]
    pub step_days: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EphemerisSeries {
    pub body: String,
    pub glyph: String,
    /// Position auf der 90°-Scheibe je Abtastzeit
    pub dial: Vec<f64>,
    pub longitude: Vec<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NatalLine {
    pub name: String,
    pub glyph: String,
    pub dial: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GraphicEphemerisResponse {
    pub times: Vec<f64>,
    pub series: Vec<EphemerisSeries>,
    pub natal_lines: Vec<NatalLine>,
}

pub fn graphic_ephemeris(req: &GraphicEphemerisRequest) -> Result<GraphicEphemerisResponse, String> {
    let natal = calculate_chart(&req.natal)?;
    let settings = settings_of(&req.natal);
    let start = req.start.jd_ut();
    let end = req.end.jd_ut();
    if end <= start {
        return Err("Das Ende liegt vor dem Beginn.".into());
    }
    let step = req.step_days.unwrap_or(1.0).clamp(0.1, 30.0);
    let n = ((end - start) / step).ceil() as usize + 1;
    if n > 20000 {
        return Err("Zu viele Abtastpunkte – Zeitraum verkleinern oder Schrittweite erhöhen.".into());
    }
    let bodies: Vec<CelestialPoint> = if req.bodies.is_empty() {
        CelestialPoint::classical().iter().copied().filter(|b| *b != CelestialPoint::Moon).collect()
    } else {
        req.bodies.iter().filter_map(|b| point_by_name(b)).collect()
    };
    let _g = engine::lock();
    prepare(&settings);
    let times: Vec<f64> = (0..n).map(|i| (start + i as f64 * step).min(end)).collect();
    let mut series = Vec::new();
    for b in bodies {
        let mut lon = Vec::with_capacity(n);
        for &t in &times {
            lon.push(lon_at(b, t, &settings)?.0);
        }
        series.push(EphemerisSeries {
            body: b.name_de().to_string(),
            glyph: b.glyph().to_string(),
            dial: lon.iter().map(|l| l.rem_euclid(90.0)).collect(),
            longitude: lon,
        });
    }
    let natal_lines = chart_points(&natal, true)
        .into_iter()
        .map(|p| NatalLine { name: p.name, glyph: p.glyph, dial: p.lon.rem_euclid(90.0) })
        .collect();
    Ok(GraphicEphemerisResponse { times, series, natal_lines })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn time_point_to_jd() {
        let t = TimePoint { year: 2000, month: 1, day: 1, hour: 12, minute: 0, timezone_offset: 0.0 };
        assert!((t.jd_ut() - 2451545.0).abs() < 1e-9);
    }

    #[test]
    fn moon_phase_names() {
        assert_eq!(moon_phase_name(5.0), "Neumond");
        assert_eq!(moon_phase_name(180.0), "Vollmond");
    }
}
