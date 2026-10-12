use crate::astrology::models::{CelestialPoint, ZodiacSign};

pub fn calculate_dignity(point: CelestialPoint, sign: ZodiacSign) -> Option<String> {
    // Check Domicile (Domizil / Herrscher)
    let is_domicile = match (point, sign) {
        (CelestialPoint::Sun, ZodiacSign::Leo) => true,
        (CelestialPoint::Moon, ZodiacSign::Cancer) => true,
        (CelestialPoint::Mercury, ZodiacSign::Gemini | ZodiacSign::Virgo) => true,
        (CelestialPoint::Venus, ZodiacSign::Taurus | ZodiacSign::Libra) => true,
        (CelestialPoint::Mars, ZodiacSign::Aries | ZodiacSign::Scorpio) => true,
        (CelestialPoint::Jupiter, ZodiacSign::Sagittarius | ZodiacSign::Pisces) => true,
        (CelestialPoint::Saturn, ZodiacSign::Capricorn | ZodiacSign::Aquarius) => true,
        (CelestialPoint::Uranus, ZodiacSign::Aquarius) => true,
        (CelestialPoint::Neptune, ZodiacSign::Pisces) => true,
        (CelestialPoint::Pluto, ZodiacSign::Scorpio) => true,
        _ => false,
    };
    if is_domicile {
        return Some("Domizil".to_string());
    }

    // Check Detriment (Exil)
    let is_detriment = match (point, sign) {
        (CelestialPoint::Sun, ZodiacSign::Aquarius) => true,
        (CelestialPoint::Moon, ZodiacSign::Capricorn) => true,
        (CelestialPoint::Mercury, ZodiacSign::Sagittarius | ZodiacSign::Pisces) => true,
        (CelestialPoint::Venus, ZodiacSign::Aries | ZodiacSign::Scorpio) => true,
        (CelestialPoint::Mars, ZodiacSign::Taurus | ZodiacSign::Libra) => true,
        (CelestialPoint::Jupiter, ZodiacSign::Gemini | ZodiacSign::Virgo) => true,
        (CelestialPoint::Saturn, ZodiacSign::Cancer | ZodiacSign::Leo) => true,
        (CelestialPoint::Uranus, ZodiacSign::Leo) => true,
        (CelestialPoint::Neptune, ZodiacSign::Virgo) => true,
        (CelestialPoint::Pluto, ZodiacSign::Taurus) => true,
        _ => false,
    };
    if is_detriment {
        return Some("Exil".to_string());
    }

    // Check Exaltation (Erhöhung)
    let is_exaltation = match (point, sign) {
        (CelestialPoint::Sun, ZodiacSign::Aries) => true,
        (CelestialPoint::Moon, ZodiacSign::Taurus) => true,
        (CelestialPoint::Mercury, ZodiacSign::Virgo) => true,
        (CelestialPoint::Venus, ZodiacSign::Pisces) => true,
        (CelestialPoint::Mars, ZodiacSign::Capricorn) => true,
        (CelestialPoint::Jupiter, ZodiacSign::Cancer) => true,
        (CelestialPoint::Saturn, ZodiacSign::Libra) => true,
        (CelestialPoint::Uranus, ZodiacSign::Scorpio) => true,
        _ => false,
    };
    if is_exaltation {
        return Some("Erhöhung".to_string());
    }

    // Check Fall (Fall)
    let is_fall = match (point, sign) {
        (CelestialPoint::Sun, ZodiacSign::Libra) => true,
        (CelestialPoint::Moon, ZodiacSign::Scorpio) => true,
        (CelestialPoint::Mercury, ZodiacSign::Pisces) => true,
        (CelestialPoint::Venus, ZodiacSign::Virgo) => true,
        (CelestialPoint::Mars, ZodiacSign::Cancer) => true,
        (CelestialPoint::Jupiter, ZodiacSign::Capricorn) => true,
        (CelestialPoint::Saturn, ZodiacSign::Aries) => true,
        (CelestialPoint::Uranus, ZodiacSign::Taurus) => true,
        _ => false,
    };
    if is_fall {
        return Some("Fall".to_string());
    }

    None
}
