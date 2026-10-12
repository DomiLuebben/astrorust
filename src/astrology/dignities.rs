use crate::astrology::models::{CelestialPoint, ZodiacSign};

pub fn calculate_dignity(point: CelestialPoint, sign: ZodiacSign) -> Option<String> {
    // Check Domicile (Domizil / Herrscher)
    let is_domicile = matches!((point, sign), (CelestialPoint::Sun, ZodiacSign::Leo) | (CelestialPoint::Moon, ZodiacSign::Cancer) | (CelestialPoint::Mercury, ZodiacSign::Gemini | ZodiacSign::Virgo) | (CelestialPoint::Venus, ZodiacSign::Taurus | ZodiacSign::Libra) | (CelestialPoint::Mars, ZodiacSign::Aries | ZodiacSign::Scorpio) | (CelestialPoint::Jupiter, ZodiacSign::Sagittarius | ZodiacSign::Pisces) | (CelestialPoint::Saturn, ZodiacSign::Capricorn | ZodiacSign::Aquarius) | (CelestialPoint::Uranus, ZodiacSign::Aquarius) | (CelestialPoint::Neptune, ZodiacSign::Pisces) | (CelestialPoint::Pluto, ZodiacSign::Scorpio));
    if is_domicile {
        return Some("Domizil".to_string());
    }

    // Check Detriment (Exil)
    let is_detriment = matches!((point, sign), (CelestialPoint::Sun, ZodiacSign::Aquarius) | (CelestialPoint::Moon, ZodiacSign::Capricorn) | (CelestialPoint::Mercury, ZodiacSign::Sagittarius | ZodiacSign::Pisces) | (CelestialPoint::Venus, ZodiacSign::Aries | ZodiacSign::Scorpio) | (CelestialPoint::Mars, ZodiacSign::Taurus | ZodiacSign::Libra) | (CelestialPoint::Jupiter, ZodiacSign::Gemini | ZodiacSign::Virgo) | (CelestialPoint::Saturn, ZodiacSign::Cancer | ZodiacSign::Leo) | (CelestialPoint::Uranus, ZodiacSign::Leo) | (CelestialPoint::Neptune, ZodiacSign::Virgo) | (CelestialPoint::Pluto, ZodiacSign::Taurus));
    if is_detriment {
        return Some("Exil".to_string());
    }

    // Check Exaltation (Erhöhung)
    let is_exaltation = matches!((point, sign), (CelestialPoint::Sun, ZodiacSign::Aries) | (CelestialPoint::Moon, ZodiacSign::Taurus) | (CelestialPoint::Mercury, ZodiacSign::Virgo) | (CelestialPoint::Venus, ZodiacSign::Pisces) | (CelestialPoint::Mars, ZodiacSign::Capricorn) | (CelestialPoint::Jupiter, ZodiacSign::Cancer) | (CelestialPoint::Saturn, ZodiacSign::Libra) | (CelestialPoint::Uranus, ZodiacSign::Scorpio));
    if is_exaltation {
        return Some("Erhöhung".to_string());
    }

    // Check Fall (Fall)
    let is_fall = matches!((point, sign), (CelestialPoint::Sun, ZodiacSign::Libra) | (CelestialPoint::Moon, ZodiacSign::Scorpio) | (CelestialPoint::Mercury, ZodiacSign::Pisces) | (CelestialPoint::Venus, ZodiacSign::Virgo) | (CelestialPoint::Mars, ZodiacSign::Cancer) | (CelestialPoint::Jupiter, ZodiacSign::Capricorn) | (CelestialPoint::Saturn, ZodiacSign::Aries) | (CelestialPoint::Uranus, ZodiacSign::Taurus));
    if is_fall {
        return Some("Fall".to_string());
    }

    None
}
