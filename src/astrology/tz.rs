//! Historische Zeitzonen aus der System-tzdata (`/usr/share/zoneinfo`, TZif v2+).
//!
//! Liefert für Zone + Ortszeit den damals gültigen UTC-Offset samt Sommerzeit,
//! erkennt übersprungene bzw. doppelte Ortszeiten bei der Umstellung und fällt
//! vor Einführung der Zonenzeit auf die mittlere Ortszeit (LMT) zurück.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};

#[derive(Debug, Clone)]
struct TType {
    utoff: i32,
    is_dst: bool,
    abbr: String,
}

#[derive(Debug, Clone)]
struct PosixRule {
    std: TType,
    dst: Option<(TType, RuleDate, RuleDate)>,
}

/// Mm.w.d/time (Sekunden ab Mitternacht Ortszeit)
#[derive(Debug, Clone, Copy)]
struct RuleDate {
    month: u32,
    week: u32,
    dow: u32,
    time: i32,
}

#[derive(Debug, Clone)]
pub struct Zone {
    transitions: Vec<i64>,
    idx: Vec<u8>,
    types: Vec<TType>,
    footer: Option<PosixRule>,
}

/// Ergebnis der Auflösung Ortszeit → Offset.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TzInfo {
    pub zone: String,
    /// Offset zu UTC in Stunden (Ost positiv), inkl. Sommerzeit
    pub offset_hours: f64,
    pub abbreviation: String,
    pub is_dst: bool,
    /// Mittlere Ortszeit (vor Einführung der Zonenzeit)
    pub is_lmt: bool,
    /// Ortszeit fiel in eine Lücke (Uhr wurde vorgestellt) bzw. kommt doppelt vor
    pub ambiguity: Option<String>,
    /// Lesbarer Hinweis für die Oberfläche
    pub note: String,
}

fn zoneinfo_dirs() -> Vec<String> {
    let mut v = Vec::new();
    if let Ok(d) = std::env::var("ZONEINFO") {
        v.push(d);
    }
    v.push("/usr/share/zoneinfo".into());
    v.push("/usr/lib/zoneinfo".into());
    v.push("/usr/share/lib/zoneinfo".into());
    v
}

fn be_i32(b: &[u8], p: usize) -> i32 {
    i32::from_be_bytes([b[p], b[p + 1], b[p + 2], b[p + 3]])
}
fn be_i64(b: &[u8], p: usize) -> i64 {
    let mut a = [0u8; 8];
    a.copy_from_slice(&b[p..p + 8]);
    i64::from_be_bytes(a)
}

fn parse_tzif(data: &[u8]) -> Result<Zone, String> {
    if data.len() < 44 || &data[0..4] != b"TZif" {
        return Err("keine TZif-Datei".into());
    }
    let version = data[4];
    let counts = |p: usize| -> [usize; 6] {
        let mut c = [0usize; 6];
        for (i, slot) in c.iter_mut().enumerate() {
            *slot = be_i32(data, p + 20 + i * 4) as usize;
        }
        c
    };
    // [isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt]
    let c1 = counts(0);
    let v1_len = c1[3] * 4 + c1[3] + c1[4] * 6 + c1[5] + c1[2] * 8 + c1[1] + c1[0];
    let (base, tsize) = if version >= b'2' {
        (44 + v1_len, 8usize)
    } else {
        (0, 4usize)
    };
    if base + 44 > data.len() {
        return Err("TZif abgeschnitten".into());
    }
    let c = counts(base);
    let (isut, isstd, leap, timecnt, typecnt, charcnt) = (c[0], c[1], c[2], c[3], c[4], c[5]);
    let mut p = base + 44;
    let mut transitions = Vec::with_capacity(timecnt);
    for i in 0..timecnt {
        transitions.push(if tsize == 8 { be_i64(data, p + i * 8) } else { be_i32(data, p + i * 4) as i64 });
    }
    p += timecnt * tsize;
    let idx = data[p..p + timecnt].to_vec();
    p += timecnt;
    let type_bytes = &data[p..p + typecnt * 6];
    p += typecnt * 6;
    let chars = &data[p..p + charcnt];
    p += charcnt + leap * (tsize + 4) + isstd + isut;

    let mut types = Vec::with_capacity(typecnt);
    for t in 0..typecnt {
        let utoff = be_i32(type_bytes, t * 6);
        let is_dst = type_bytes[t * 6 + 4] != 0;
        let ai = type_bytes[t * 6 + 5] as usize;
        let end = chars[ai..].iter().position(|&b| b == 0).map(|e| ai + e).unwrap_or(chars.len());
        types.push(TType { utoff, is_dst, abbr: String::from_utf8_lossy(&chars[ai..end]).to_string() });
    }

    let mut footer = None;
    if version >= b'2' && p < data.len() && data[p] == b'\n' {
        if let Some(end) = data[p + 1..].iter().position(|&b| b == b'\n') {
            let s = String::from_utf8_lossy(&data[p + 1..p + 1 + end]).to_string();
            footer = parse_posix(&s);
        }
    }
    Ok(Zone { transitions, idx, types, footer })
}

fn parse_posix_name(s: &[u8], i: &mut usize) -> Option<String> {
    if *i >= s.len() {
        return None;
    }
    if s[*i] == b'<' {
        let end = s[*i..].iter().position(|&b| b == b'>')? + *i;
        let n = String::from_utf8_lossy(&s[*i + 1..end]).to_string();
        *i = end + 1;
        Some(n)
    } else {
        let st = *i;
        while *i < s.len() && s[*i].is_ascii_alphabetic() {
            *i += 1;
        }
        if *i == st { None } else { Some(String::from_utf8_lossy(&s[st..*i]).to_string()) }
    }
}

fn parse_posix_time(s: &[u8], i: &mut usize) -> Option<i32> {
    let mut sign = 1;
    if *i < s.len() && (s[*i] == b'+' || s[*i] == b'-') {
        if s[*i] == b'-' {
            sign = -1;
        }
        *i += 1;
    }
    let mut parts = [0i32; 3];
    let mut n = 0;
    let mut any = false;
    while n < 3 {
        let st = *i;
        while *i < s.len() && s[*i].is_ascii_digit() {
            *i += 1;
        }
        if *i == st {
            break;
        }
        any = true;
        parts[n] = String::from_utf8_lossy(&s[st..*i]).parse().ok()?;
        n += 1;
        if *i < s.len() && s[*i] == b':' {
            *i += 1;
        } else {
            break;
        }
    }
    if !any {
        return None;
    }
    Some(sign * (parts[0] * 3600 + parts[1] * 60 + parts[2]))
}

fn parse_rule_date(s: &[u8], i: &mut usize) -> Option<RuleDate> {
    if *i >= s.len() || s[*i] != b'M' {
        return None;
    }
    *i += 1;
    let mut nums = [0u32; 3];
    for (k, slot) in nums.iter_mut().enumerate() {
        let st = *i;
        while *i < s.len() && s[*i].is_ascii_digit() {
            *i += 1;
        }
        *slot = String::from_utf8_lossy(&s[st..*i]).parse().ok()?;
        if k < 2 {
            if *i >= s.len() || s[*i] != b'.' {
                return None;
            }
            *i += 1;
        }
    }
    let mut time = 7200;
    if *i < s.len() && s[*i] == b'/' {
        *i += 1;
        time = parse_posix_time(s, i)?;
    }
    Some(RuleDate { month: nums[0], week: nums[1], dow: nums[2], time })
}

fn parse_posix(text: &str) -> Option<PosixRule> {
    let s = text.as_bytes();
    let mut i = 0;
    let std_name = parse_posix_name(s, &mut i)?;
    let std_off = -parse_posix_time(s, &mut i)?;
    let std = TType { utoff: std_off, is_dst: false, abbr: std_name };
    if i >= s.len() {
        return Some(PosixRule { std, dst: None });
    }
    let dst_name = parse_posix_name(s, &mut i)?;
    let mut dst_off = std_off + 3600;
    if i < s.len() && s[i] != b',' {
        dst_off = -parse_posix_time(s, &mut i)?;
    }
    if i >= s.len() || s[i] != b',' {
        return Some(PosixRule { std, dst: None });
    }
    i += 1;
    let start = parse_rule_date(s, &mut i)?;
    if i >= s.len() || s[i] != b',' {
        return None;
    }
    i += 1;
    let end = parse_rule_date(s, &mut i)?;
    Some(PosixRule { std, dst: Some((TType { utoff: dst_off, is_dst: true, abbr: dst_name }, start, end)) })
}

fn days_from_civil(y: i64, m: i64, d: i64) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = y.div_euclid(400);
    let yoe = y - era * 400;
    let mp = (m + 9) % 12;
    let doy = (153 * mp + 2) / 5 + d - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}

fn civil_from_days(z: i64) -> (i64, i64, i64) {
    let z = z + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    (if m <= 2 { y + 1 } else { y }, m, d)
}

fn is_leap(y: i64) -> bool {
    (y % 4 == 0 && y % 100 != 0) || y % 400 == 0
}

fn month_len(y: i64, m: u32) -> i64 {
    match m {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        _ => {
            if is_leap(y) {
                29
            } else {
                28
            }
        }
    }
}

/// Lokale Sekunden (seit 1970, in Ortszeit gezählt) des Regel-Datums im Jahr `year`.
fn rule_local_secs(year: i64, r: &RuleDate) -> i64 {
    let first = days_from_civil(year, r.month as i64, 1);
    let dow_first = (first + 4).rem_euclid(7); // 1970-01-01 war Donnerstag (4)
    let mut day = 1 + (r.dow as i64 - dow_first).rem_euclid(7) + (r.week as i64 - 1) * 7;
    let ml = month_len(year, r.month);
    while day > ml {
        day -= 7;
    }
    (first + day - 1) * 86400 + r.time as i64
}

impl PosixRule {
    fn type_at_utc(&self, utc: i64) -> &TType {
        match &self.dst {
            None => &self.std,
            Some((dst, start, end)) => {
                let (y, _, _) = civil_from_days((utc + self.std.utoff as i64).div_euclid(86400));
                let start_utc = rule_local_secs(y, start) - self.std.utoff as i64;
                let end_utc = rule_local_secs(y, end) - dst.utoff as i64;
                let in_dst = if start_utc < end_utc {
                    utc >= start_utc && utc < end_utc
                } else {
                    utc >= start_utc || utc < end_utc
                };
                if in_dst { dst } else { &self.std }
            }
        }
    }
}

impl Zone {
    fn type_at_utc(&self, utc: i64) -> &TType {
        if self.transitions.is_empty() || utc < self.transitions[0] {
            // Vor der ersten Umstellung: mittlere Ortszeit (erster Typ, sonst erster Nicht-DST-Typ)
            return self
                .types
                .iter()
                .find(|t| !t.is_dst)
                .unwrap_or(&self.types[0]);
        }
        let last = *self.transitions.last().unwrap();
        if utc >= last {
            if let Some(f) = &self.footer {
                return f.type_at_utc(utc);
            }
            return &self.types[*self.idx.last().unwrap() as usize];
        }
        let pos = match self.transitions.binary_search(&utc) {
            Ok(i) => i,
            Err(i) => i - 1,
        };
        &self.types[self.idx[pos] as usize]
    }

    fn is_lmt_at_utc(&self, utc: i64) -> bool {
        self.transitions.is_empty() || utc < self.transitions[0]
    }
}

fn cache() -> &'static Mutex<HashMap<String, Option<Zone>>> {
    static CACHE: OnceLock<Mutex<HashMap<String, Option<Zone>>>> = OnceLock::new();
    CACHE.get_or_init(|| Mutex::new(HashMap::new()))
}

fn load_zone(name: &str) -> Result<Zone, String> {
    if name.is_empty() || name.contains("..") || name.starts_with('/') || name.contains('\0') {
        return Err(format!("Ungültiger Zonenname: {name}"));
    }
    {
        let c = cache().lock().unwrap();
        if let Some(entry) = c.get(name) {
            return entry.clone().ok_or_else(|| format!("Zeitzone nicht gefunden: {name}"));
        }
    }
    let mut result = None;
    for dir in zoneinfo_dirs() {
        let path = std::path::Path::new(&dir).join(name);
        if let Ok(bytes) = std::fs::read(&path) {
            if let Ok(z) = parse_tzif(&bytes) {
                result = Some(z);
                break;
            }
        }
    }
    cache().lock().unwrap().insert(name.to_string(), result.clone());
    result.ok_or_else(|| format!("Zeitzone nicht gefunden: {name} (Paket tzdata installiert?)"))
}

/// Ob die Zone im System vorhanden ist.
pub fn zone_exists(name: &str) -> bool {
    load_zone(name).is_ok()
}

fn hours(secs: i32) -> f64 {
    secs as f64 / 3600.0
}

fn describe(zone: &str, t: &TType, lmt: bool, ambiguity: Option<String>) -> TzInfo {
    let total_min = (t.utoff.abs() as f64 / 60.0).round() as i32;
    let off = format!("UTC{}{:02}:{:02}", if t.utoff < 0 { '-' } else { '+' }, total_min / 60, total_min % 60);
    let mut note = if lmt {
        format!("Mittlere Ortszeit (LMT), {off} – vor Einführung der Zonenzeit")
    } else if t.is_dst {
        format!("{} (Sommerzeit), {off}", t.abbr)
    } else {
        format!("{} (Normalzeit), {off}", t.abbr)
    };
    if let Some(a) = &ambiguity {
        note.push_str(&format!(" – Achtung: {a}"));
    }
    TzInfo {
        zone: zone.to_string(),
        offset_hours: hours(t.utoff),
        abbreviation: if lmt { "LMT".into() } else { t.abbr.clone() },
        is_dst: t.is_dst,
        is_lmt: lmt,
        ambiguity,
        note,
    }
}

/// Löst Zone + Ortszeit (als Sekunden seit 1970, in Ortszeit gezählt) auf.
pub fn resolve_local(zone_name: &str, local_secs: i64) -> Result<TzInfo, String> {
    let zone = load_zone(zone_name)?;
    // Kandidaten: alle Offsets, die im Umfeld (±2 Tage) gelten können
    let mut offsets: Vec<i32> = Vec::new();
    for probe in [-172800i64, -86400, 0, 86400, 172800] {
        let t = zone.type_at_utc(local_secs + probe - 0);
        if !offsets.contains(&t.utoff) {
            offsets.push(t.utoff);
        }
    }
    let mut valid: Vec<(i32, &TType)> = Vec::new();
    for &o in &offsets {
        let utc = local_secs - o as i64;
        let t = zone.type_at_utc(utc);
        if t.utoff == o {
            valid.push((o, t));
        }
    }
    match valid.len() {
        1 => {
            let utc = local_secs - valid[0].0 as i64;
            Ok(describe(zone_name, valid[0].1, zone.is_lmt_at_utc(utc), None))
        }
        0 => {
            // Lücke: Uhr wurde vorgestellt. Es gilt die Zeit vor der Umstellung.
            let before = zone.type_at_utc(local_secs - 86400 - offsets[0] as i64);
            Ok(describe(
                zone_name,
                before,
                false,
                Some("Diese Ortszeit gab es nicht (Uhren wurden vorgestellt); es wird der Offset davor verwendet.".into()),
            ))
        }
        _ => {
            // Doppelt: Uhr wurde zurückgestellt. Wir nehmen die Sommerzeit (erstes Vorkommen).
            let pick = valid.iter().find(|(_, t)| t.is_dst).unwrap_or(&valid[0]);
            Ok(describe(
                zone_name,
                pick.1,
                false,
                Some("Diese Ortszeit kam doppelt vor (Umstellung); es wird das erste Vorkommen (Sommerzeit) angenommen.".into()),
            ))
        }
    }
}

/// Offset einer Zone zu einem UTC-Zeitpunkt (Sekunden seit 1970).
pub fn offset_at_utc(zone_name: &str, utc_secs: i64) -> Result<f64, String> {
    let zone = load_zone(zone_name)?;
    Ok(hours(zone.type_at_utc(utc_secs).utoff))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn local(y: i64, m: i64, d: i64, h: i64, mi: i64) -> i64 {
        days_from_civil(y, m, d) * 86400 + h * 3600 + mi * 60
    }

    #[test]
    fn berlin_summer_and_winter() {
        let s = resolve_local("Europe/Berlin", local(1990, 7, 15, 14, 0)).unwrap();
        assert_eq!(s.offset_hours, 2.0);
        assert!(s.is_dst);
        let w = resolve_local("Europe/Berlin", local(1990, 1, 15, 14, 0)).unwrap();
        assert_eq!(w.offset_hours, 1.0);
        assert!(!w.is_dst);
    }

    #[test]
    fn berlin_beyond_last_transition_uses_footer_rule() {
        let s = resolve_local("Europe/Berlin", local(2050, 7, 1, 12, 0)).unwrap();
        assert_eq!(s.offset_hours, 2.0);
        let w = resolve_local("Europe/Berlin", local(2050, 12, 1, 12, 0)).unwrap();
        assert_eq!(w.offset_hours, 1.0);
    }

    #[test]
    fn berlin_double_summer_time_1945() {
        let s = resolve_local("Europe/Berlin", local(1945, 6, 1, 12, 0)).unwrap();
        assert_eq!(s.offset_hours, 3.0);
    }

    #[test]
    fn berlin_before_zone_time_is_lmt() {
        let s = resolve_local("Europe/Berlin", local(1879, 3, 14, 11, 30)).unwrap();
        assert!(s.is_lmt);
        // Berlin LMT = +0:53:28
        assert!((s.offset_hours - 0.8911).abs() < 0.001, "{}", s.offset_hours);
    }

    #[test]
    fn dst_gap_and_overlap_are_reported() {
        // 2024: 31.3. 02:30 gab es nicht, 27.10. 02:30 kam doppelt vor
        let gap = resolve_local("Europe/Berlin", local(2024, 3, 31, 2, 30)).unwrap();
        assert!(gap.ambiguity.is_some());
        let dup = resolve_local("Europe/Berlin", local(2024, 10, 27, 2, 30)).unwrap();
        assert!(dup.ambiguity.is_some());
        assert_eq!(dup.offset_hours, 2.0);
    }

    #[test]
    fn southern_hemisphere_and_fractional_offsets() {
        let s = resolve_local("Australia/Sydney", local(2000, 1, 15, 12, 0)).unwrap();
        assert_eq!(s.offset_hours, 11.0);
        let k = resolve_local("Asia/Kathmandu", local(2000, 1, 15, 12, 0)).unwrap();
        assert!((k.offset_hours - 5.75).abs() < 1e-9);
    }

    #[test]
    fn unknown_zone_is_an_error() {
        assert!(resolve_local("Nirgendwo/Stadt", 0).is_err());
        assert!(resolve_local("../etc/passwd", 0).is_err());
    }
}
