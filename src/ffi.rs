use crate::astrology::atlas::search_cities;
use crate::astrology::calculator::calculate_chart;
use crate::astrology::models::{ChartRequest, SynastryRequest, TransitRequest};
use crate::astrology::profiles::get_preset_profiles;
use crate::astrology::svg_export::generate_chart_svg;
use crate::astrology::synastry::calculate_synastry;
use crate::astrology::transits::calculate_transits;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

fn str_from_c(ptr: *const c_char) -> Option<String> {
    if ptr.is_null() {
        return None;
    }
    unsafe { CStr::from_ptr(ptr).to_str().ok().map(|s| s.to_string()) }
}

fn c_from_str(s: &str) -> *mut c_char {
    CString::new(s).unwrap_or_default().into_raw()
}

#[no_mangle]
pub extern "C" fn astrorust_calculate_chart(json_req: *const c_char) -> *mut c_char {
    let req_str = match str_from_c(json_req) {
        Some(s) => s,
        None => return c_from_str(r#"{"error":"Null pointer passed"}"#),
    };

    let req: ChartRequest = match serde_json::from_str(&req_str) {
        Ok(r) => r,
        Err(e) => return c_from_str(&format!(r#"{{"error":"JSON Parse Error: {}"}}"#, e)),
    };

    match calculate_chart(&req) {
        Ok(chart) => c_from_str(&serde_json::to_string(&chart).unwrap_or_default()),
        Err(e) => c_from_str(&format!(r#"{{"error":"Calculation Error: {}"}}"#, e)),
    }
}

#[no_mangle]
pub extern "C" fn astrorust_calculate_transit(json_req: *const c_char) -> *mut c_char {
    let req_str = match str_from_c(json_req) {
        Some(s) => s,
        None => return c_from_str(r#"{"error":"Null pointer passed"}"#),
    };

    let req: TransitRequest = match serde_json::from_str(&req_str) {
        Ok(r) => r,
        Err(e) => return c_from_str(&format!(r#"{{"error":"JSON Parse Error: {}"}}"#, e)),
    };

    match calculate_transits(&req) {
        Ok(resp) => c_from_str(&serde_json::to_string(&resp).unwrap_or_default()),
        Err(e) => c_from_str(&format!(r#"{{"error":"Transit Error: {}"}}"#, e)),
    }
}

#[no_mangle]
pub extern "C" fn astrorust_calculate_synastry(json_req: *const c_char) -> *mut c_char {
    let req_str = match str_from_c(json_req) {
        Some(s) => s,
        None => return c_from_str(r#"{"error":"Null pointer passed"}"#),
    };

    let req: SynastryRequest = match serde_json::from_str(&req_str) {
        Ok(r) => r,
        Err(e) => return c_from_str(&format!(r#"{{"error":"JSON Parse Error: {}"}}"#, e)),
    };

    match calculate_synastry(&req) {
        Ok(resp) => c_from_str(&serde_json::to_string(&resp).unwrap_or_default()),
        Err(e) => c_from_str(&format!(r#"{{"error":"Synastry Error: {}"}}"#, e)),
    }
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

#[no_mangle]
pub extern "C" fn astrorust_export_svg(json_req: *const c_char) -> *mut c_char {
    let req_str = match str_from_c(json_req) {
        Some(s) => s,
        None => return c_from_str(r#"{"error":"Null pointer passed"}"#),
    };

    let req: ChartRequest = match serde_json::from_str(&req_str) {
        Ok(r) => r,
        Err(e) => return c_from_str(&format!(r#"{{"error":"JSON Parse Error: {}"}}"#, e)),
    };

    match calculate_chart(&req) {
        Ok(chart) => {
            let svg = generate_chart_svg(&chart);
            c_from_str(&svg)
        }
        Err(e) => c_from_str(&format!(r#"{{"error":"Calculation Error: {}"}}"#, e)),
    }
}

#[no_mangle]
pub extern "C" fn astrorust_free_string(s: *mut c_char) {
    if !s.is_null() {
        unsafe {
            let _ = CString::from_raw(s);
        }
    }
}
