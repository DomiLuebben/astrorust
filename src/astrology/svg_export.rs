use crate::astrology::models::ChartResponse;

pub fn generate_chart_svg(chart: &ChartResponse) -> String {
    let size = 900.0;
    let cx = size / 2.0;
    let cy = size / 2.0;
    let r_out = 380.0;
    let r_zodiac_inner = 320.0;
    let r_house_outer = 320.0;
    let r_house_inner = 200.0;
    let r_aspects = 195.0;

    let asc = chart.angles.ascendant;
    let screen_angle = |lon: f64| -> f64 {
        let a = (180.0 - (lon - asc)).rem_euclid(360.0);
        a.to_radians()
    };

    let mut svg = String::new();
    svg.push_str(&format!(
        r##"<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {} {}" width="{}" height="{}" style="background:#0a0d17; font-family:sans-serif;">"##,
        size, size, size, size
    ));

    // Defs: Gradients
    svg.push_str(r##"
    <defs>
      <radialGradient id="bgGlow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="#1e1b4b" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="#0a0d17" stop-opacity="0"/>
      </radialGradient>
    </defs>
    "##);

    // Background circle
    svg.push_str(&format!(
        r##"<circle cx="{}" cy="{}" r="{}" fill="url(#bgGlow)" stroke="#312e81" stroke-width="2"/>"##,
        cx, cy, r_out
    ));

    // Draw Zodiac Signs (12 slices)
    let signs = [
        ("♈", "Widder", "#f87171"),
        ("♉", "Stier", "#4ade80"),
        ("♊", "Zwillinge", "#fbbf24"),
        ("♋", "Krebs", "#60a5fa"),
        ("♌", "Löwe", "#f87171"),
        ("♍", "Jungfrau", "#4ade80"),
        ("♎", "Waage", "#fbbf24"),
        ("♏", "Skorpion", "#60a5fa"),
        ("♐", "Schütze", "#f87171"),
        ("♑", "Steinbock", "#4ade80"),
        ("♒", "Wassermann", "#fbbf24"),
        ("♓", "Fische", "#60a5fa"),
    ];

    for i in 0..12 {
        let start_deg = i as f64 * 30.0;
        let end_deg = (i + 1) as f64 * 30.0;
        let mid_deg = start_deg + 15.0;

        let a_start = screen_angle(start_deg);
        let a_end = screen_angle(end_deg);

        let x1_out = cx + r_out * a_start.cos();
        let y1_out = cy + r_out * a_start.sin();
        let _x2_out = cx + r_out * a_end.cos();
        let _y2_out = cy + r_out * a_end.sin();

        let x1_in = cx + r_zodiac_inner * a_start.cos();
        let y1_in = cy + r_zodiac_inner * a_start.sin();
        let _x2_in = cx + r_zodiac_inner * a_end.cos();
        let _y2_in = cy + r_zodiac_inner * a_end.sin();

        // Sign boundary line
        svg.push_str(&format!(
            r##"<line x1="{:.1}" y1="{:.1}" x2="{:.1}" y2="{:.1}" stroke="#475569" stroke-width="1.5"/>"##,
            x1_in, y1_in, x1_out, y1_out
        ));

        // Sign glyph
        let a_mid = screen_angle(mid_deg);
        let r_glyph = (r_out + r_zodiac_inner) / 2.0;
        let gx = cx + r_glyph * a_mid.cos();
        let gy = cy + r_glyph * a_mid.sin();

        let (glyph, _, color) = signs[i];
        svg.push_str(&format!(
            r##"<text x="{:.1}" y="{:.1}" fill="{}" font-size="20" font-weight="bold" text-anchor="middle" dominant-baseline="central">{}</text>"##,
            gx, gy, color, glyph
        ));
    }

    // Inner ring border
    svg.push_str(&format!(
        r##"<circle cx="{}" cy="{}" r="{}" fill="none" stroke="#475569" stroke-width="2"/>"##,
        cx, cy, r_zodiac_inner
    ));
    svg.push_str(&format!(
        r##"<circle cx="{}" cy="{}" r="{}" fill="none" stroke="#334155" stroke-width="1.5"/>"##,
        cx, cy, r_house_inner
    ));

    // House cusps
    for h in &chart.houses {
        let a = screen_angle(h.longitude);
        let x1 = cx + r_house_inner * a.cos();
        let y1 = cy + r_house_inner * a.sin();
        let x2 = cx + r_house_outer * a.cos();
        let y2 = cy + r_house_outer * a.sin();

        let is_axis = h.house_number == 1 || h.house_number == 4 || h.house_number == 7 || h.house_number == 10;
        let stroke_color = if is_axis { "#fbbf24" } else { "#475569" };
        let stroke_width = if is_axis { "2.5" } else { "1" };

        svg.push_str(&format!(
            r##"<line x1="{:.1}" y1="{:.1}" x2="{:.1}" y2="{:.1}" stroke="{}" stroke-width="{}"/>"##,
            x1, y1, x2, y2, stroke_color, stroke_width
        ));

        // House number
        let next_idx = (h.house_number as usize) % 12;
        let next_lon = chart.houses[next_idx].longitude;
        let h_mid = h.longitude + ((next_lon - h.longitude).rem_euclid(360.0) / 2.0);
        let a_mid = screen_angle(h_mid);
        let r_num = r_house_inner + 25.0;
        let nx = cx + r_num * a_mid.cos();
        let ny = cy + r_num * a_mid.sin();
        svg.push_str(&format!(
            r##"<text x="{:.1}" y="{:.1}" fill="#94a3b8" font-size="12" text-anchor="middle" dominant-baseline="central">{}</text>"##,
            nx, ny, h.house_number
        ));
    }

    // Aspect lines inside central circle
    for asp in &chart.aspects {
        let pa = chart.planets.iter().find(|p| p.id == asp.point_a);
        let pb = chart.planets.iter().find(|p| p.id == asp.point_b);
        if let (Some(p1), Some(p2)) = (pa, pb) {
            let a1 = screen_angle(p1.longitude);
            let a2 = screen_angle(p2.longitude);

            let x1 = cx + r_aspects * a1.cos();
            let y1 = cy + r_aspects * a1.sin();
            let x2 = cx + r_aspects * a2.cos();
            let y2 = cy + r_aspects * a2.sin();

            let stroke_width = if asp.orb <= 1.0 { "2.0" } else { "1.0" };
            let opacity = if asp.orb <= 1.5 { "0.85" } else { "0.5" };

            svg.push_str(&format!(
                r##"<line x1="{:.1}" y1="{:.1}" x2="{:.1}" y2="{:.1}" stroke="{}" stroke-width="{}" stroke-opacity="{}"/>"##,
                x1, y1, x2, y2, asp.color_hex, stroke_width, opacity
            ));
        }
    }

    // Draw Planets
    for p in &chart.planets {
        let a = screen_angle(p.longitude);
        let r_p = r_house_inner + 65.0;
        let px = cx + r_p * a.cos();
        let py = cy + r_p * a.sin();

        // Planet symbol
        svg.push_str(&format!(
            r##"<circle cx="{:.1}" cy="{:.1}" r="11" fill="#0f172a" stroke="#64748b" stroke-width="1"/>"##,
            px, py
        ));
        svg.push_str(&format!(
            r##"<text x="{:.1}" y="{:.1}" fill="#f8fafc" font-size="14" font-weight="bold" text-anchor="middle" dominant-baseline="central">{}</text>"##,
            px, py, p.glyph
        ));

        // Retrograde symbol
        if p.is_retrograde {
            svg.push_str(&format!(
                r##"<text x="{:.1}" y="{:.1}" fill="#ef4444" font-size="9" text-anchor="middle">℞</text>"##,
                px + 10.0,
                py - 8.0
            ));
        }
    }

    // Chart header info
    svg.push_str(&format!(
        r##"<text x="30" y="45" fill="#f8fafc" font-size="22" font-weight="bold">{}</text>"##,
        chart.name
    ));
    svg.push_str(&format!(
        r##"<text x="30" y="70" fill="#94a3b8" font-size="14">{} • {}</text>"##,
        chart.date_time, chart.location_name
    ));
    svg.push_str(&format!(
        r##"<text x="30" y="90" fill="#fbbf24" font-size="13">AC: {} | MC: {} | {}</text>"##,
        chart.angles.ascendant_formatted, chart.angles.midheaven_formatted, chart.house_system
    ));

    svg.push_str("</svg>");
    svg
}
