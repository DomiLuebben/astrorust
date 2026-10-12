use astrorust::astrology::calculator::calculate_chart;
use astrorust::astrology::models::{ChartRequest, HouseSystemChoice};
use clap::Parser;
use std::process::Command;

#[derive(Parser, Debug)]
#[command(name = "astrorust")]
#[command(author = "Astrorust Desktop")]
#[command(version = "1.0.0")]
#[command(about = "Professionelle Astrologie- und Horoskop-Software in Rust & Qt6", long_about = None)]
pub struct CliArgs {
    /// Native Qt6 GUI starten (Standard)
    #[arg(long)]
    pub gui: bool,

    /// Horoskop direkt im Terminal als CLI ausgeben
    #[arg(long)]
    pub cli: bool,

    /// Name der Person für CLI-Berechnung
    #[arg(long, default_value = "Geburtshoroskop")]
    pub name: String,

    /// Datum im Format JJJJ-MM-TT (z.B. 1990-05-15)
    #[arg(long, default_value = "1990-05-15")]
    pub date: String,

    /// Uhrzeit im Format HH:MM (z.B. 14:30)
    #[arg(long, default_value = "12:00")]
    pub time: String,

    /// Breitengrad (Latitude, z.B. 52.52 für Berlin)
    #[arg(long, default_value_t = 52.52)]
    pub lat: f64,

    /// Längengrad (Longitude, z.B. 13.405 für Berlin)
    #[arg(long, default_value_t = 13.405)]
    pub lon: f64,

    /// Zeitzonen-Offset in Stunden (z.B. 1.0 für MEZ, 2.0 für MESZ)
    #[arg(long, default_value_t = 1.0)]
    pub tz: f64,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = CliArgs::parse();

    if args.cli {
        run_terminal_mode(&args)?;
        return Ok(());
    }

    // Default: Start native Qt6 GUI
    start_native_qt_gui()?;
    Ok(())
}

fn start_native_qt_gui() -> Result<(), Box<dyn std::error::Error>> {
    let mut candidates = vec![
        "/usr/share/astrorust/gui/main.py".to_string(),
        format!("{}/gui/main.py", env!("CARGO_MANIFEST_DIR")),
        "gui/main.py".to_string(),
    ];

    if let Ok(exe_path) = std::env::current_exe() {
        if let Some(parent) = exe_path.parent() {
            candidates.push(parent.join("../share/astrorust/gui/main.py").to_string_lossy().to_string());
            candidates.push(parent.join("../../gui/main.py").to_string_lossy().to_string());
        }
    }

    let gui_script = candidates
        .into_iter()
        .find(|p| std::path::Path::new(p).exists())
        .unwrap_or_else(|| "/usr/share/astrorust/gui/main.py".to_string());

    println!("\x1b[38;2;61;174;233m");
    println!("  ╔══════════════════════════════════════════════════════════════════════════╗");
    println!("  ║                                                                          ║");
    println!("  ║                        ✨  A S T R O R U S T  ✨                         ║");
    println!("  ║             Native Qt6 Astrologie • Swiss Ephemeris 2.10 Core            ║");
    println!("  ║                                                                          ║");
    println!("  ╚══════════════════════════════════════════════════════════════════════════╝");
    println!("\x1b[0m");
    println!("  \x1b[32m✔\x1b[0m Starte native Qt6-Oberfläche (KDE Breeze Dark / LME Design)...");

    let status = Command::new("python3")
        .arg(&gui_script)
        .status()?;

    if !status.success() {
        eprintln!("Qt-GUI beendet mit Status: {:?}", status.code());
    }

    Ok(())
}

fn run_terminal_mode(args: &CliArgs) -> Result<(), Box<dyn std::error::Error>> {
    let date_parts: Vec<&str> = args.date.split('-').collect();
    let time_parts: Vec<&str> = args.time.split(':').collect();

    if date_parts.len() < 3 || time_parts.len() < 2 {
        eprintln!("Fehler: Ungültiges Datums- oder Zeitformat.");
        return Ok(());
    }

    let year: i32 = date_parts[0].parse()?;
    let month: i32 = date_parts[1].parse()?;
    let day: i32 = date_parts[2].parse()?;
    let hour: u32 = time_parts[0].parse()?;
    let minute: u32 = time_parts[1].parse()?;

    let req = ChartRequest {
        name: args.name.clone(),
        year,
        month,
        day,
        hour,
        minute,
        second: Some(0),
        timezone_offset: args.tz,
        latitude: args.lat,
        longitude: args.lon,
        location_name: Some(format!("{:.2}°, {:.2}°", args.lat, args.lon)),
        house_system: Some(HouseSystemChoice::Placidus),
    };

    let chart = calculate_chart(&req).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;

    println!("\n\x1b[1;36m=== ASTRORUST HOROSKOP: {} ===\x1b[0m", chart.name);
    println!("Datum/Zeit: {} | Ort: {}", chart.date_time, chart.location_name);
    println!("AC: {} | MC: {}\n", chart.angles.ascendant_formatted, chart.angles.midheaven_formatted);

    println!("\x1b[1m{:<4} {:<12} {:<18} {:<6} {:<12} {:<4}\x1b[0m", "Pt", "Planet", "Position", "Haus", "Würde", "Rx");
    println!("{}", "-".repeat(60));
    for p in &chart.planets {
        let retro = if p.is_retrograde { "\x1b[31mRx\x1b[0m" } else { "  " };
        let dignity = p.dignity.as_deref().unwrap_or("-");
        println!("{:<4} {:<12} {:<18} {:<6} {:<12} {:<4}", p.glyph, p.name, format!("{} {}", p.formatted_deg, p.sign_glyph), p.house, dignity, retro);
    }

    println!("\n\x1b[1m=== BEDEUTENDE ASPEKTE ===\x1b[0m");
    for asp in chart.aspects.iter().take(8) {
        println!("  {} {:<10} {} {:<16} {} (Orb: {})", asp.point_a_glyph, asp.point_a_name, asp.aspect_glyph, asp.aspect_name, asp.point_b_name, asp.formatted_orb);
    }
    println!();

    Ok(())
}
