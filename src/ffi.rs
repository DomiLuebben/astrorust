use crate::astrology::atlas::search_cities;
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

#[no_mangle]
pub extern "C" fn astrorust_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = CString::from_raw(s);
        }
    }
}
