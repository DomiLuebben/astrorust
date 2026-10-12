//! Gemeinsame Schicht über der Swiss Ephemeris: Sperre, Datenpfad, Fixsterne,
//! Sternzeit, Ayanamsa-Katalog.
//!
//! Die C-Bibliothek hält globalen Zustand (Pfad, Sidereal-Modus, Topozentrik). Jede
//! Berechnung läuft deshalb unter [`lock`]; die Sperre ist pro Thread wiedereintrittsfähig,
//! damit z. B. `forecast` Horoskope berechnen kann, während es die Sperre schon hält.

use std::cell::Cell;
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_int};
use std::sync::{Mutex, MutexGuard, Once};

static ENGINE_LOCK: Mutex<()> = Mutex::new(());
static EPHE_INIT: Once = Once::new();

thread_local! {
    static DEPTH: Cell<u32> = const { Cell::new(0) };
}

pub struct EngineGuard {
    guard: Option<MutexGuard<'static, ()>>,
}

impl Drop for EngineGuard {
    fn drop(&mut self) {
        DEPTH.with(|d| d.set(d.get() - 1));
        self.guard.take();
    }
}

/// Sperre für Berechnungen (wiedereintrittsfähig innerhalb eines Threads).
pub fn lock() -> EngineGuard {
    let outer = DEPTH.with(|d| {
        let first = d.get() == 0;
        d.set(d.get() + 1);
        first
    });
    let guard = if outer {
        Some(ENGINE_LOCK.lock().unwrap_or_else(|p| p.into_inner()))
    } else {
        None
    };
    let g = EngineGuard { guard };
    init_ephemeris();
    g
}

extern "C" {
    fn swe_fixstar2_ut(star: *mut c_char, tjd_ut: c_double, iflag: c_int, xx: *mut c_double, serr: *mut c_char) -> c_int;
    fn swe_sidtime(tjd_ut: c_double) -> c_double;
    fn swe_cotrans(xpo: *mut c_double, xpn: *mut c_double, eps: c_double);
    fn swe_set_sid_mode(sid_mode: c_int, t0: c_double, ayan_t0: c_double);
    fn swe_get_ayanamsa_ex_ut(tjd_ut: c_double, iflag: c_int, daya: *mut c_double, serr: *mut c_char) -> c_int;
    fn swe_houses_armc(armc: c_double, geolat: c_double, eps: c_double, hsys: c_int, cusps: *mut c_double, ascmc: *mut c_double) -> c_int;
    fn swe_calc_ut(tjd_ut: c_double, ipl: c_int, iflag: c_int, xx: *mut c_double, serr: *mut c_char) -> c_int;
}

const SEFLG_SWIEPH: c_int = 2;
const SEFLG_SPEED: c_int = 256;
const SE_ECL_NUT: c_int = -1;

/// Verzeichnisse, in denen nach `*.se1` gesucht wird (in dieser Reihenfolge).
pub fn ephemeris_search_dirs() -> Vec<String> {
    let mut c: Vec<String> = Vec::new();
    if let Ok(p) = std::env::var("ASTRORUST_EPHE") {
        c.push(p);
    }
    if let Ok(home) = std::env::var("HOME") {
        c.push(format!("{}/.local/share/astrorust/ephe", home));
    }
    c.push("/usr/share/astrorust/ephe".into());
    // Entwicklungsstand: neben dem Quelltext
    c.push(format!("{}/ephe", env!("CARGO_MANIFEST_DIR")));
    c.push("/usr/share/swisseph".into());
    c.push("/usr/share/sweph/ephe".into());
    c
}

/// Welche Datendateien gefunden wurden (für die Statuszeile / Diagnose).
pub fn ephemeris_status() -> (Option<String>, bool, bool) {
    let dir = ephemeris_search_dirs().into_iter().find(|d| has_se1(d));
    match &dir {
        Some(d) => {
            let p = std::path::Path::new(d);
            (Some(d.clone()), p.join("seas_18.se1").exists(), p.join("sefstars.txt").exists())
        }
        None => (None, false, false),
    }
}

fn has_se1(dir: &str) -> bool {
    std::fs::read_dir(dir)
        .map(|rd| rd.flatten().any(|e| e.path().extension().map_or(false, |x| x == "se1")))
        .unwrap_or(false)
}

fn init_ephemeris() {
    EPHE_INIT.call_once(|| {
        for dir in ephemeris_search_dirs() {
            if has_se1(&dir) && !dir.contains('\0') {
                sweph::set_ephe_path(&dir);
                // sefstars.txt liegt im selben Verzeichnis (wird von der Bibliothek dort gesucht)
                break;
            }
        }
    });
}

/// Setzt den Sidereal-Modus (Ayanamsa-ID der Swiss Ephemeris).
pub fn set_sidereal(ayanamsa_id: i32) {
    let _g = lock();
    unsafe { swe_set_sid_mode(ayanamsa_id, 0.0, 0.0) };
}

/// Ayanamsa in Grad für eine Ayanamsa-ID.
pub fn ayanamsa_value(jd_ut: f64, ayanamsa_id: i32) -> Result<f64, String> {
    let _g = lock();
    let mut daya = 0.0;
    let mut serr = [0 as c_char; 256];
    unsafe {
        swe_set_sid_mode(ayanamsa_id, 0.0, 0.0);
        let r = swe_get_ayanamsa_ex_ut(jd_ut, SEFLG_SWIEPH, &mut daya, serr.as_mut_ptr());
        if r < 0 {
            return Err(CStr::from_ptr(serr.as_ptr()).to_string_lossy().to_string());
        }
    }
    Ok(daya)
}

/// Mittlere Sternzeit in Stunden (Greenwich) für einen UT-JD.
pub fn sidereal_time_hours(jd_ut: f64) -> f64 {
    let _g = lock();
    unsafe { swe_sidtime(jd_ut) }
}

/// Neigung der Ekliptik (wahre Schiefe) in Grad zu einem JD.
pub fn true_obliquity(jd_ut: f64) -> f64 {
    let _g = lock();
    let mut xx = [0.0f64; 6];
    let mut serr = [0 as c_char; 256];
    unsafe {
        swe_calc_ut(jd_ut, SE_ECL_NUT, SEFLG_SWIEPH, xx.as_mut_ptr(), serr.as_mut_ptr());
    }
    xx[0]
}

/// Häuser aus dem Sternzeitwinkel (ARMC) – für Composite-Horoskope.
/// Liefert (Spitzen 1–12, Aszendent, MC, Vertex).
pub fn houses_from_armc(armc: f64, lat: f64, eps: f64, system_code: u8) -> ([f64; 12], f64, f64, f64) {
    let _g = lock();
    let mut cusps = [0.0f64; 37];
    let mut ascmc = [0.0f64; 10];
    unsafe {
        swe_houses_armc(armc, lat, eps, system_code as c_int, cusps.as_mut_ptr(), ascmc.as_mut_ptr());
    }
    let mut out = [0.0f64; 12];
    out.copy_from_slice(&cusps[1..13]);
    (out, ascmc[0], ascmc[1], ascmc[3])
}

/// Ekliptikal (lon, lat) → äquatorial (RA, Dekl.), alles in Grad.
pub fn ecliptic_to_equatorial(lon: f64, lat: f64, obliquity: f64) -> (f64, f64) {
    let _g = lock();
    let mut xpo = [lon, lat, 1.0];
    let mut xpn = [0.0f64; 3];
    unsafe { swe_cotrans(xpo.as_mut_ptr(), xpn.as_mut_ptr(), -obliquity) };
    (xpn[0].rem_euclid(360.0), xpn[1])
}

#[derive(Debug, Clone)]
pub struct StarPosition {
    pub name: String,
    pub longitude: f64,
    pub latitude: f64,
    pub magnitude: Option<f64>,
}

/// Position eines Fixsterns (Name wie in `sefstars.txt`, z. B. "Regulus").
/// `sidereal` rechnet in den aktuell gesetzten Sidereal-Modus um.
pub fn fixed_star(name: &str, jd_ut: f64, sidereal: bool) -> Option<StarPosition> {
    let _g = lock();
    let mut buf = [0 as c_char; 64];
    let cname = CString::new(name).ok()?;
    for (i, b) in cname.as_bytes().iter().enumerate().take(40) {
        buf[i] = *b as c_char;
    }
    let mut xx = [0.0f64; 6];
    let mut serr = [0 as c_char; 256];
    let mut flags = SEFLG_SWIEPH | SEFLG_SPEED;
    if sidereal {
        flags |= 65536;
    }
    let r = unsafe { swe_fixstar2_ut(buf.as_mut_ptr(), jd_ut, flags, xx.as_mut_ptr(), serr.as_mut_ptr()) };
    if r < 0 {
        return None;
    }
    let full = unsafe { CStr::from_ptr(buf.as_ptr()) }.to_string_lossy().to_string();
    Some(StarPosition {
        name: full.split(',').next().unwrap_or(name).trim().to_string(),
        longitude: xx[0].rem_euclid(360.0),
        latitude: xx[1],
        magnitude: None,
    })
}

/// Katalog der angebotenen Ayanamsas: (Swiss-Ephemeris-ID, Name).
pub const AYANAMSAS: &[(i32, &str)] = &[
    (1, "Lahiri (Chitrapaksha)"),
    (3, "Raman"),
    (5, "Krishnamurti (KP)"),
    (0, "Fagan/Bradley (westlich-siderisch)"),
    (27, "True Chitra"),
    (29, "True Pushya"),
    (28, "True Revati"),
    (7, "Yukteshwar"),
    (8, "J. N. Bhasin"),
    (21, "Suryasiddhanta"),
    (23, "Aryabhata"),
    (2, "De Luce"),
    (17, "Galaktisches Zentrum 0° Schütze"),
    (14, "Aldebaran 15° Stier"),
    (15, "Hipparchos"),
    (16, "Sassanidisch"),
    (9, "Babylonisch (Kugler 1)"),
    (13, "Babylonisch (Huber)"),
    (18, "J2000"),
    (20, "B1950"),
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lock_is_reentrant() {
        let _a = lock();
        let _b = lock();
        let _c = lock();
    }

    #[test]
    fn lahiri_ayanamsa_2000_is_about_23_85() {
        let a = ayanamsa_value(2451545.0, 1).unwrap();
        assert!((a - 23.857).abs() < 0.02, "{a}");
    }

    #[test]
    fn regulus_around_2000_is_29_leo() {
        let s = fixed_star("Regulus", 2451545.0, false).expect("sefstars.txt gefunden");
        assert!((s.longitude - 149.83).abs() < 0.1, "{}", s.longitude);
    }

    #[test]
    fn sidereal_time_matches_known_value() {
        // GMST am 2000-01-01 12:00 UT ≈ 18h 41m 50.5s = 18.6974 h
        let t = sidereal_time_hours(2451545.0);
        assert!((t - 18.6974).abs() < 0.001, "{t}");
    }
}
