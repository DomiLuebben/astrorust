use crate::astrology::astrocarto::{astro_map, AstroMapRequest};
use crate::astrology::atlas::{nearest_city, search_cities, zone_names};
use crate::astrology::forecast::{
    calculate_progression, calculate_return, graphic_ephemeris, search_transits, sky_events, GraphicEphemerisRequest,
    ProgressionRequest, ReturnRequest, SkyEventsRequest, TransitSearchRequest,
};
use crate::astrology::vedic::{calculate_vedic, VedicRequest};
use crate::astrology::calculator::calculate_chart;
use crate::astrology::models::{ChartRequest, SynastryRequest, TransitRequest};
use crate::astrology::profiles::get_preset_profiles;
use crate::astrology::svg_export::generate_chart_svg;
use crate::astrology::synastry::calculate_synastry;
use crate::astrology::transits::calculate_transits;
use serde::de::DeserializeOwned;
use serde::Serialize;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::panic::{catch_unwind, AssertUnwindSafe};

fn str_from_c(ptr: *const c_char) -> Option<String> {
    if ptr.is_null() {
        return None;
    }
    unsafe { CStr::from_ptr(ptr).to_str().ok().map(|s| s.to_string()) }
}

fn c_from_str(s: &str) -> *mut c_char {
    // Ein NUL-Byte im Text würde den String abschneiden; lieber entfernen als leer zurückgeben.
    CString::new(s.replace('\0', ""))
        .unwrap_or_default()
        .into_raw()
}

/// Fehlerantwort als gültiges JSON (Anführungszeichen in Meldungen werden maskiert).
fn error_json(message: &str) -> String {
    serde_json::json!({ "error": message }).to_string()
}

/// Gemeinsamer Rahmen: JSON lesen, rechnen, JSON schreiben – und keinen Panic über
/// die C-Grenze lassen (das würde den ganzen Python-Prozess abbrechen).
fn json_call<Req, Resp, F>(json_req: *const c_char, label: &str, f: F) -> *mut c_char
where
    Req: DeserializeOwned,
    Resp: Serialize,
    F: FnOnce(&Req) -> Result<Resp, String>,
{
    let req_str = match str_from_c(json_req) {
        Some(s) => s,
        None => return c_from_str(&error_json("Null pointer passed")),
    };

    let result = catch_unwind(AssertUnwindSafe(|| -> String {
        let req: Req = match serde_json::from_str(&req_str) {
            Ok(r) => r,
            Err(e) => return error_json(&format!("JSON Parse Error: {}", e)),
        };
        match f(&req) {
            Ok(resp) => serde_json::to_string(&resp)
                .unwrap_or_else(|e| error_json(&format!("Serialisierungsfehler: {}", e))),
            Err(e) => error_json(&format!("{}: {}", label, e)),
        }
    }));

    c_from_str(&result.unwrap_or_else(|_| error_json("Interner Fehler bei der Berechnung")))
}

#[no_mangle]
pub extern "C" fn astrorust_calculate_chart(json_req: *const c_char) -> *mut c_char {
    json_call(json_req, "Calculation Error", |r: &ChartRequest| calculate_chart(r))
}

#[no_mangle]
pub extern "C" fn astrorust_calculate_transit(json_req: *const c_char) -> *mut c_char {
    json_call(json_req, "Transit Error", |r: &TransitRequest| calculate_transits(r))
}

#[no_mangle]
pub extern "C" fn astrorust_calculate_synastry(json_req: *const c_char) -> *mut c_char {
    json_call(json_req, "Synastry Error", |r: &SynastryRequest| calculate_synastry(r))
}

#[no_mangle]
pub extern "C" fn astrorust_get_profiles() -> *mut c_char {
    let profiles = get_preset_profiles();
    c_from_str(&serde_json::to_string(&profiles).unwrap_or_default())
}

#[no_mangle]
pub extern "C" fn astrorust_search_cities(query: *const c_char) -> *mut c_char {
    let q = str_from_c(query).unwrap_or_default();
    let cities = search_cities(&q);
    c_from_str(&serde_json::to_string(&cities).unwrap_or_default())
}

/// Liefert bei Erfolg das SVG, bei Fehler `{"error": ...}`.
#[no_mangle]
pub extern "C" fn astrorust_export_svg(json_req: *const c_char) -> *mut c_char {
    json_call(json_req, "Calculation Error", |r: &ChartRequest| {
        calculate_chart(r).map(|chart| generate_chart_svg(&chart))
    })
    // Hinweis: json_call serialisiert das SVG als JSON-String; die Python-Seite entpackt es.
}

#[derive(serde::Deserialize)]
struct ZoneQuery {
    zone: String,
    year: i32,
    month: i32,
    day: i32,
    #[serde(default)]
    hour: u32,
    #[serde(default)]
    minute: u32,
    #[serde(default)]
    longitude: f64,
}

#[derive(serde::Deserialize)]
struct Coords {
    latitude: f64,
    longitude: f64,
}

#[derive(serde::Deserialize)]
struct Query {
    #[serde(default)]
    query: String,
}

#[derive(serde::Deserialize)]
struct JulianDate {
    jd: f64,
}

/// Allgemeiner Einstieg: `method` wählt die Funktion, `json_req` ist die Anfrage (oder `{}`).
/// Die Antwort ist JSON; Fehler als `{"error": "..."}`.
#[no_mangle]
pub extern "C" fn astrorust_call(method: *const c_char, json_req: *const c_char) -> *mut c_char {
    let Some(method) = str_from_c(method) else { return c_from_str(&error_json("Null pointer passed")) };
    let json_req = if json_req.is_null() { c"{}".as_ptr() } else { json_req };
    match method.as_str() {
        "calendar_date" => json_call(json_req, "Date Error", |r: &JulianDate| {
            if !r.jd.is_finite() || !(625000.0..=2818000.0).contains(&r.jd) {
                return Err("Julianischer Tag außerhalb des unterstützten Bereichs".into());
            }
            let d = crate::astrology::engine::calendar_date((r.jd * 86400.0).round() / 86400.0);
            let seconds = (d.hour * 3600.0).round() as u32;
            Ok(serde_json::json!({"year": d.year, "month": d.month, "day": d.day,
                "hour": seconds / 3600, "minute": seconds / 60 % 60, "second": seconds % 60}))
        }),
        "chart" => json_call(json_req, "Calculation Error", |r: &ChartRequest| calculate_chart(r)),
        "transit" => json_call(json_req, "Transit Error", |r: &TransitRequest| calculate_transits(r)),
        "synastry" => json_call(json_req, "Synastry Error", |r: &SynastryRequest| calculate_synastry(r)),
        "progression" => json_call(json_req, "Progression Error", |r: &ProgressionRequest| calculate_progression(r)),
        "return" => json_call(json_req, "Return Error", |r: &ReturnRequest| calculate_return(r)),
        "transit_search" => json_call(json_req, "Transit Search Error", |r: &TransitSearchRequest| search_transits(r)),
        "sky_events" => json_call(json_req, "Sky Events Error", |r: &SkyEventsRequest| sky_events(r)),
        "graphic_ephemeris" => json_call(json_req, "Ephemeris Error", |r: &GraphicEphemerisRequest| graphic_ephemeris(r)),
        "vedic" => json_call(json_req, "Vedic Error", |r: &VedicRequest| calculate_vedic(r)),
        "astro_map" => json_call(json_req, "Astro Map Error", |r: &AstroMapRequest| astro_map(r)),
        "svg" => json_call(json_req, "Calculation Error", |r: &ChartRequest| {
            calculate_chart(r).map(|chart| generate_chart_svg(&chart))
        }),
        "atlas_search" => json_call(json_req, "Atlas Error", |r: &Query| Ok(search_cities(&r.query))),
        "atlas_nearest" => json_call(json_req, "Atlas Error", |r: &Coords| {
            nearest_city(r.latitude, r.longitude).ok_or_else(|| "Atlas leer".to_string())
        }),
        "zones" => json_call(json_req, "Zone Error", |_r: &serde_json::Value| Ok(zone_names())),
        "resolve_timezone" => json_call(json_req, "Zone Error", |r: &ZoneQuery| {
            crate::astrology::calculator::resolve_zone(
                &r.zone,
                r.year,
                r.month,
                r.day,
                r.hour as f64 + r.minute as f64 / 60.0,
                r.longitude,
            )
        }),
        "ayanamsas" => json_call(json_req, "Error", |_r: &serde_json::Value| {
            Ok(crate::astrology::engine::AYANAMSAS.iter().map(|(id, n)| serde_json::json!({"id": id, "name": n})).collect::<Vec<_>>())
        }),
        "engine_status" => json_call(json_req, "Error", |_r: &serde_json::Value| {
            let (dir, asteroids, stars) = crate::astrology::engine::ephemeris_status();
            Ok(serde_json::json!({"ephemeris_dir": dir, "asteroids_chiron": asteroids, "fixed_stars": stars, "version": sweph::version()}))
        }),
        other => c_from_str(&error_json(&format!("Unbekannte Methode: {other}"))),
    }
}

#[no_mangle]
/// # Safety
/// `s` must be null or a live string returned by this library, freed exactly once.
pub unsafe extern "C" fn astrorust_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = CString::from_raw(s);
        }
    }
}
