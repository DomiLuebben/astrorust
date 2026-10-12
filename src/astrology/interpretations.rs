use crate::astrology::models::{
    AspectData, AspectType, CelestialPoint, ElementQualitySummary, InterpretationSection,
    PlanetData, ZodiacSign,
};

pub fn generate_interpretations(
    planets: &[PlanetData],
    ascendant_sign: ZodiacSign,
    aspects: &[AspectData],
    eq: &ElementQualitySummary,
) -> Vec<InterpretationSection> {
    let mut sections = Vec::new();

    // 1. Aszendent
    let asc_text = match ascendant_sign {
        ZodiacSign::Aries => "Mit dem Aszendenten im Widder begegnen Sie dem Leben mit Mut, Direktheit und Entschlossenheit. Sie handeln impulsiv, ergreifen gerne die Initiative und gehen Herausforderungen offen an.",
        ZodiacSign::Taurus => "Mit dem Aszendenten im Stier zeichnen Sie sich durch Gelassenheit, Verlässlichkeit und ein feines Gespür für materielle und sinnliche Werte aus. Sie bauen Dinge schrittweise und mit Ausdauer auf.",
        ZodiacSign::Gemini => "Mit dem Aszendenten in den Zwillingen strahlen Sie Neugier, Leichtigkeit und Kommunikationsfreude aus. Sie treten rasch mit anderen in Kontakt und betrachten das Leben als Entdeckungsreise.",
        ZodiacSign::Cancer => "Mit dem Aszendenten im Krebs wirken Sie einfühlsam, intuitiv und fürsorglich. Sie schützen Ihre innere Gefühlswelt und suchen emotionale Sicherheit und Geborgenheit.",
        ZodiacSign::Leo => "Mit dem Aszendenten im Löwen besitzen Sie ein natürliches Charisma, Großzügigkeit und Lebensfreude. Sie möchten im Leben sichtbar sein und mit Herzlichkeit führen.",
        ZodiacSign::Virgo => "Mit dem Aszendenten in der Jungfrau begegnen Sie Ihrer Umwelt analytisch, aufmerksam und strukturiert. Sie erkennen Details schnell und streben nach Ordnung und Nützlichkeit.",
        ZodiacSign::Libra => "Mit dem Aszendenten in der Waage verkörpern Sie Harmonie, Ästhetik und Diplomatie. Sie suchen die Begegnung auf Augenhöhe und vermitteln instinktiv zwischen Gegensätzen.",
        ZodiacSign::Scorpio => "Mit dem Aszendenten im Skorpion besitzen Sie eine magnetische Ausstrahlung und Tiefgang. Sie blicken hinter die Fassaden und wandeln Krisen in persönliche Transformation um.",
        ZodiacSign::Sagittarius => "Mit dem Aszendenten im Schützen strahlen Sie Optimismus, Weite und Sinnsuche aus. Ihr Lebensmotto ist geprägt von stetem Erkenntnisdrang und Horizonterweiterung.",
        ZodiacSign::Capricorn => "Mit dem Aszendenten im Steinbock strahlen Sie Ernsthaftigkeit, Reife und Disziplin aus. Sie übernehmen gerne Verantwortung und verfolgen langfristige Ziele mit Ausdauer.",
        ZodiacSign::Aquarius => "Mit dem Aszendenten im Wassermann treten Sie als Freigeist, originell und unkonventionell auf. Sie schätzen Unabhängigkeit, Gleichberechtigung und zukunftsgewandte Ideen.",
        ZodiacSign::Pisces => "Mit dem Aszendenten in den Fischen strahlen Sie Feinfühligkeit, Fantasie und Mitgefühl aus. Sie nehmen subtile Schwingungen wahr und vertrauen auf Ihre Intuition.",
    };
    sections.push(InterpretationSection {
        title: format!("Aszendent in {}", ascendant_sign.name_de()),
        subtitle: "Die Maske, der erste Eindruck & der Lebensweg".to_string(),
        text: asc_text.to_string(),
        keywords: vec!["Persönlichkeit".into(), "Ausstrahlung".into(), "Lebensaufgabe".into()],
    });

    // 2. Sonne
    if let Some(sun) = planets.iter().find(|p| p.id == CelestialPoint::Sun) {
        let sun_text = match sun.sign {
            ZodiacSign::Aries => "Die Sonne im Widder verleiht Ihnen Schaffenskraft, Pioniergeist und Durchsetzungswillen. Ihr Wesenskern strebt danach, Neuland zu betreten.",
            ZodiacSign::Taurus => "Die Sonne im Stier schenkt Ihnen Verwurzelung, Geduld und Schöpferkraft. Sie schätzen Beständigkeit, Treue und handfeste Resultate.",
            ZodiacSign::Gemini => "Die Sonne in den Zwillingen macht Sie vielseitig interessiert, geistig beweglich und vernetzend. Ihr Antrieb ist Wissen und Austausch.",
            ZodiacSign::Cancer => "Die Sonne im Krebs verankert Ihr Wesen in emotionaler Verbundenheit, Empathie und seelischem Reichtum.",
            ZodiacSign::Leo => "Die Sonne im Löwen steht im eigenen Domizil. Sie strahlt Kreativität, Selbstvertrauen, Großmut und Freude am schöpferischen Ausdruck aus.",
            ZodiacSign::Virgo => "Die Sonne in der Jungfrau strebt nach Präzision, Meisterschaft und Sinnhaftigkeit im Alltag. Sie perfektionieren das Vorhandene.",
            ZodiacSign::Libra => "Die Sonne in der Waage sucht nach Balance, Schönheit und wahrer partnerschaftlicher Resonanz.",
            ZodiacSign::Scorpio => "Die Sonne im Skorpion erforscht die verborgenen Tiefen des Seins mit unbändiger Entschlossenheit und Loyalität.",
            ZodiacSign::Sagittarius => "Die Sonne im Schützen ist getrieben von philosophischem Weitblick, Idealismus und Zuversicht.",
            ZodiacSign::Capricorn => "Die Sonne im Steinbock verleiht Ihnen Pflichtbewusstsein, strategische Weitsicht und Meisterschaft über die Zeit.",
            ZodiacSign::Aquarius => "Die Sonne im Wassermann brennt für Innovation, Freiheit und den Dienst an einer humanistischen Gemeinschaft.",
            ZodiacSign::Pisces => "Die Sonne in den Fischen verbindet Sie mit transzendenten Welten, universeller Liebe und künstlerischer Inspiration.",
        };
        sections.push(InterpretationSection {
            title: format!("Sonne in {} (Haus {})", sun.sign.name_de(), sun.house),
            subtitle: "Wesenskern, Lebensenergie & Bewusstsein".to_string(),
            text: format!("{} Im {}. Haus entfaltet sich diese Kraft vor allem in Lebensbereichen, die mit diesem Sektor korrespondieren.", sun_text, sun.house),
            keywords: vec!["Selbstverwirklichung".into(), "Identität".into(), "Vitalität".into()],
        });
    }

    // 3. Mond
    if let Some(moon) = planets.iter().find(|p| p.id == CelestialPoint::Moon) {
        let moon_text = match moon.sign {
            ZodiacSign::Aries => "Ihr Mond im Widder reagiert spontan, feurig und unmittelbar. Sie brauchen Freiheit für Ihre Gefühlsausbrüche und schnelle Klärung.",
            ZodiacSign::Taurus => "Ihr Mond im Stier (Erhöhung) schenkt Ihnen ein tiefes seelisches Ruhepolster, Genussfähigkeit und Verlässlichkeit im Fühlen.",
            ZodiacSign::Gemini => "Ihr Mond in den Zwillingen verarbeitet Emotionen über Kommunikation, Gedanken und sprachliche Einordnung.",
            ZodiacSign::Cancer => "Ihr Mond im Krebs steht im Domizil: Intensive Intuition, seelische Tiefe und großes Bedürfnis nach liebevoller Geborgenheit.",
            ZodiacSign::Leo => "Ihr Mond im Löwen fühlt sich glücklich, wenn Gefühle herzlich, warm und anerkennend zelebriert werden.",
            ZodiacSign::Virgo => "Ihr Mond in der Jungfrau findet Geborgenheit in überschaubarer Ordnung, Fürsorge und praktischem Nutzen.",
            ZodiacSign::Libra => "Ihr Mond in der Waage strebt nach emotionalem Frieden, Harmonie und feinsinnigem Gleichgewicht.",
            ZodiacSign::Scorpio => "Ihr Mond im Skorpion fühlt mit extremer Intensität. Emotionen sind tief, leidenschaftlich und transformativ.",
            ZodiacSign::Sagittarius => "Ihr Mond im Schützen braucht emotionalen Freiraum, Horizonterweiterung und eine Prise Humor in jeder Situation.",
            ZodiacSign::Capricorn => "Ihr Mond im Steinbock drückt Gefühle zurückhaltend und loyal aus. Sicherheit entsteht durch Verlässlichkeit.",
            ZodiacSign::Aquarius => "Ihr Mond im Wassermann schützt die eigene Autonomie und fühlt sich in gleichgesinnten Freundschaften wohl.",
            ZodiacSign::Pisces => "Ihr Mond in den Fischen ist ein feines Seelenbarometer für Stimmungen anderer, grenzenlos empathisch und träumerisch.",
        };
        sections.push(InterpretationSection {
            title: format!("Mond in {} (Haus {})", moon.sign.name_de(), moon.house),
            subtitle: "Emotionale Grundbedürfnisse & Unterbewusstsein".to_string(),
            text: format!("{} Im {}. Haus zeigt der Mond, wo Sie sich am stärksten zu Hause und geborgen fühlen wollen.", moon_text, moon.house),
            keywords: vec!["Gefühlswelt".into(), "Intuition".into(), "Geborgenheit".into()],
        });
    }

    // 4. Bedeutende Aspekte (die engsten Orben)
    let mut tight_aspects = aspects.to_vec();
    tight_aspects.sort_by(|a, b| a.orb.partial_cmp(&b.orb).unwrap_or(std::cmp::Ordering::Equal));

    for asp in tight_aspects.into_iter().take(4) {
        if asp.orb <= 3.5 {
            let desc = match (asp.aspect_type, asp.point_a, asp.point_b) {
                (AspectType::Trine | AspectType::Sextile, _, _) => {
                    format!("Ein harmonischer Energiefluss ({}) zwischen {} und {}. Diese Begabung fällt Ihnen natürlich zu und stärkt Ihre Fähigkeiten.", asp.aspect_name, asp.point_a_name, asp.point_b_name)
                }
                (AspectType::Square | AspectType::Opposition, _, _) => {
                    format!("Ein dynamisches Spannungsverhältnis ({}) zwischen {} und {}. Es fordert Sie heraus, Gegensätze zu integrieren und durch Reibung zu wachsen.", asp.aspect_name, asp.point_a_name, asp.point_b_name)
                }
                (AspectType::Conjunction, _, _) => {
                    format!("Eine kraftvolle Verschmelzung ({}) der Energien von {} und {}. Diese Kräfte wirken als Einheit in Ihrer Persönlichkeit.", asp.aspect_name, asp.point_a_name, asp.point_b_name)
                }
                _ => {
                    format!("Eine Verbindung ({}) zwischen {} und {} mit einem sehr engen Orbis von {}.", asp.aspect_name, asp.point_a_name, asp.point_b_name, asp.formatted_orb)
                }
            };
            sections.push(InterpretationSection {
                title: format!("{} {} {} (Orbis: {})", asp.point_a_name, asp.aspect_name, asp.point_b_name, asp.formatted_orb),
                subtitle: format!("Aspektqualität: {}", asp.aspect_type.nature()),
                text: desc,
                keywords: vec![asp.aspect_name.clone(), "Dynamik".into(), "Charakter".into()],
            });
        }
    }

    // 5. Elementverteilung
    let elem_text = format!(
        "Ihr Horoskop weist eine Betonung des Elements {} auf ({}), kombiniert mit der Qualität {}. Dies verleiht Ihrer Persönlichkeit eine charakteristische Grundschwingung.",
        eq.dominant_element,
        match eq.dominant_element.as_str() {
            "Feuer" => "Tatkraft, Begeisterungsfähigkeit und Enthusiasmus",
            "Erde" => "Pragmatismus, Stabilität und greifbare Realität",
            "Luft" => "Intellektuelle Neugier, Kommunikation und Ideenreichtum",
            "Wasser" => "Seelische Feinfühligkeit, Intuition und Empathie",
            _ => "Ausgewogene Verteilung",
        },
        eq.dominant_quality
    );
    sections.push(InterpretationSection {
        title: format!("Element-Schwerpunkt: {}", eq.dominant_element),
        subtitle: "Energetische Grundverfassung".to_string(),
        text: elem_text,
        keywords: vec!["Elemente".into(), eq.dominant_element.clone(), eq.dominant_quality.clone()],
    });

    sections
}
