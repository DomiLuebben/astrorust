use crate::astrology::models::ChartRequest;

/// Erster Tag des Gregorianischen Kalenders. Davor gilt der Julianische Kalender.
const GREGORIAN_START: (i32, i32, i32) = (1582, 10, 15);

fn is_gregorian(year: i32, month: i32, day: i32) -> bool {
    (year, month, day) >= GREGORIAN_START
}

fn is_leap_year(year: i32, month: i32, day: i32) -> bool {
    if is_gregorian(year, month, day) {
        (year % 4 == 0 && year % 100 != 0) || year % 400 == 0
    } else {
        year.rem_euclid(4) == 0
    }
}

fn days_in_month(year: i32, month: i32, day: i32) -> i32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        _ => {
            if is_leap_year(year, month, day) {
                29
            } else {
                28
            }
        }
    }
}

/// Julianischer Tag (UT) für Kalenderdatum und Dezimalstunde.
/// Vor dem 15.10.1582 wird – wie historisch üblich – der Julianische Kalender
/// angenommen, danach der Gregorianische.
pub fn julian_day_ut(year: i32, month: i32, day: i32, hour: f64) -> f64 {
    if is_gregorian(year, month, day) {
        return sweph::julian_day(year, month, day, hour);
    }
    let a = (14 - month).div_euclid(12);
    let y = year + 4800 - a;
    let m = month + 12 * a - 3;
    let jdn = day + (153 * m + 2).div_euclid(5) + 365 * y + y.div_euclid(4) - 32083;
    jdn as f64 - 0.5 + hour / 24.0
}

/// Julianischer Tag (UT) → Sekunden seit 1970-01-01 00:00 (UT).
pub fn days_to_epoch_secs(jd: f64) -> i64 {
    ((jd - 2440587.5) * 86400.0).round() as i64
}

/// Prüft eine Horoskop-Anfrage und liefert eine verständliche Fehlermeldung.
pub fn validate_request(req: &ChartRequest) -> Result<(), String> {
    if !(-3000..=3000).contains(&req.year) {
        return Err(format!("Jahr {} liegt außerhalb des berechenbaren Bereichs (-3000 bis 3000).", req.year));
    }
    if !(1..=12).contains(&req.month) {
        return Err(format!("Ungültiger Monat: {}.", req.month));
    }
    let max_day = days_in_month(req.year, req.month, 1);
    if req.day < 1 || req.day > max_day {
        return Err(format!(
            "Ungültiger Tag: {}.{}.{} (der Monat hat {} Tage).",
            req.day, req.month, req.year, max_day
        ));
    }
    if req.hour > 23 || req.minute > 59 || req.second.unwrap_or(0) > 59 {
        return Err("Ungültige Uhrzeit.".into());
    }
    if !req.latitude.is_finite() || !(-90.0..=90.0).contains(&req.latitude) {
        return Err(format!("Ungültiger Breitengrad: {}.", req.latitude));
    }
    if !req.longitude.is_finite() || !(-180.0..=180.0).contains(&req.longitude) {
        return Err(format!("Ungültiger Längengrad: {}.", req.longitude));
    }
    if !req.timezone_offset.is_finite() || !(-14.0..=14.0).contains(&req.timezone_offset) {
        return Err(format!("Ungültiger Zeitzonen-Offset: {}.", req.timezone_offset));
    }
    Ok(())
}

/// Zerlegt Grad innerhalb eines Zeichens (0 ≤ x < 30) in Grad/Minute/Sekunde.
/// Auf ganze Sekunden gerundet, mit Übertrag – nie "60'" oder "30°".
pub fn split_dms(sign_deg: f64) -> (u32, u32, u32) {
    let total = ((sign_deg * 3600.0).round() as i64).clamp(0, 30 * 3600 - 1);
    ((total / 3600) as u32, ((total % 3600) / 60) as u32, (total % 60) as u32)
}

/// Wie `split_dms`, aber auf ganze Minuten gerundet (mit Übertrag).
pub fn split_dm(sign_deg: f64) -> (u32, u32) {
    let total = ((sign_deg * 60.0).round() as i64).clamp(0, 30 * 60 - 1);
    ((total / 60) as u32, (total % 60) as u32)
}

/// Orbis als `GG°MM'` (auf Minuten gerundet, mit Übertrag).
pub fn format_orb(orb: f64) -> String {
    let total = (orb.abs() * 60.0).round() as i64;
    format!("{:02}°{:02}'", total / 60, total % 60)
}

/// `UTC+01:00`, `UTC-03:30`, `UTC+05:45`.
pub fn format_utc_offset(offset_hours: f64) -> String {
    let total_min = (offset_hours.abs() * 60.0).round() as i64;
    let sign = if offset_hours < 0.0 && total_min != 0 { '-' } else { '+' };
    format!("UTC{}{:02}:{:02}", sign, total_min / 60, total_min % 60)
}

/// Winkel in [0, 360).
pub fn normalize_deg(x: f64) -> f64 {
    x.rem_euclid(360.0)
}

/// Kleinster Abstand zweier Längen (0–180°).
pub fn angle_diff(a: f64, b: f64) -> f64 {
    let d = (a - b).rem_euclid(360.0);
    if d > 180.0 { 360.0 - d } else { d }
}

/// Vorzeichenbehafteter Abstand a − b im Bereich (−180, 180].
pub fn signed_diff(a: f64, b: f64) -> f64 {
    let d = (a - b + 540.0).rem_euclid(360.0) - 180.0;
    if d == -180.0 { 180.0 } else { d }
}

/// Maskiert Text für die Verwendung in XML/SVG.
pub fn xml_escape(text: &str) -> String {
    text.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&apos;")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dms_carries_instead_of_showing_60() {
        assert_eq!(split_dms(4.9999999), (5, 0, 0));
        assert_eq!(split_dms(29.9999999), (29, 59, 59));
        assert_eq!(split_dm(10.9999), (11, 0));
        assert_eq!(format_orb(0.99999), "01°00'");
    }

    #[test]
    fn utc_offset_formats_fractions() {
        assert_eq!(format_utc_offset(1.0), "UTC+01:00");
        assert_eq!(format_utc_offset(-3.5), "UTC-03:30");
        assert_eq!(format_utc_offset(5.75), "UTC+05:45");
    }

    #[test]
    fn julian_calendar_before_1582() {
        // 4.10.1582 (jul.) und 15.10.1582 (greg.) sind aufeinanderfolgende Tage.
        let a = julian_day_ut(1582, 10, 4, 12.0);
        let b = julian_day_ut(1582, 10, 15, 12.0);
        assert!((b - a - 1.0).abs() < 1e-9);
        // J2000 und eine bekannte julianische Zahl: 1.1.-4712 12:00 = JD 0 (jul.)
        assert!((julian_day_ut(-4712, 1, 1, 12.0)).abs() < 1e-9);
        assert!((julian_day_ut(2000, 1, 1, 12.0) - 2451545.0).abs() < 1e-9);
    }

    #[test]
    fn xml_is_escaped() {
        assert_eq!(xml_escape("A & <B>"), "A &amp; &lt;B&gt;");
    }
}
