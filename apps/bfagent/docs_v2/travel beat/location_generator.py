"""
Travel Story - Location Database
================================
Part 3: On-Demand Generator

Generiert Location-Daten via LLM wenn nicht in DB.
"""

import json
from typing import Optional, List
from datetime import datetime

from location_models import (
    BaseLocation, LocationLayer, UserWorld, MergedLocationData,
    LayerType, District, LayerPlace, SensoryDetails, PlaceType,
    PersonalPlace, LocationMemory, StoryCharacter,
)
from location_repository import LocationRepository, DatabaseConfig


# ═══════════════════════════════════════════════════════════════
# GENERATION PROMPTS
# ═══════════════════════════════════════════════════════════════

BASE_LOCATION_PROMPT = """Generiere detaillierte Informationen über {city}, {country} für einen Roman.

Antworte NUR mit validem JSON im folgenden Format:
```json
{{
    "name": "{city}",
    "country": "{country}",
    "region": "Region/Bundesland",
    "coordinates": [latitude, longitude],
    "timezone": "Europe/...",
    "languages": ["Sprache1", "Sprache2"],
    "currency": "EUR",
    "climate": "Kurze Klimabeschreibung",
    "best_seasons": ["Frühling", "Herbst"],
    "districts": [
        {{
            "name": "Viertelname",
            "local_name": "Lokaler Name falls anders",
            "vibe": "Atmosphäre in 3-5 Wörtern",
            "description": "1-2 Sätze Beschreibung"
        }}
    ],
    "population": 1000000,
    "known_for": ["Bekannt für 1", "Bekannt für 2", "Bekannt für 3"]
}}
```

Liefere 4-6 interessante Stadtviertel mit authentischen lokalen Namen.
"""


LOCATION_LAYER_PROMPT = """Generiere {genre}-spezifische Details für {city} für einen Roman.

GENRE: {genre}
{genre_description}

Antworte NUR mit validem JSON:
```json
{{
    "atmospheres": {{
        "morning": "Atmosphäre morgens (2-3 Sätze, sinnlich)",
        "afternoon": "Atmosphäre nachmittags",
        "evening": "Atmosphäre abends",
        "night": "Atmosphäre nachts"
    }},
    "places": [
        {{
            "name": "Echter Ortsname",
            "place_type": "restaurant|bar|cafe|museum|landmark|viewpoint|park|beach|street|plaza|market|church|hidden_gem|danger_spot",
            "district": "Viertelname",
            "relevance_score": 5,
            "description": "Beschreibung des Ortes",
            "atmosphere": "Spezifische Atmosphäre hier",
            "story_potential": "Wie kann dieser Ort in einer {genre}-Story verwendet werden?"
        }}
    ],
    "sensory": {{
        "smells": ["Geruch1", "Geruch2", "Geruch3", "Geruch4", "Geruch5"],
        "sounds": ["Geräusch1", "Geräusch2", "Geräusch3", "Geräusch4", "Geräusch5"],
        "textures": ["Textur1", "Textur2", "Textur3"],
        "tastes": ["Geschmack1", "Geschmack2", "Geschmack3"],
        "visuals": ["Visuell1", "Visuell2", "Visuell3", "Visuell4", "Visuell5"]
    }},
    "story_hooks": [
        "Story-Hook 1: Eine Idee für eine Szene",
        "Story-Hook 2: Eine weitere Idee",
        "Story-Hook 3: Noch eine Idee"
    ],
    "scene_settings": [
        "Setting 1: Beschreibung einer typischen Szene",
        "Setting 2: Weitere Szene"
    ],
    "potential_conflicts": [
        "Konflikt 1: Möglicher Konflikt für dieses Genre",
        "Konflikt 2: Weiterer Konflikt"
    ]
}}
```

Liefere 8-12 authentische Orte mit echten Namen, sortiert nach Relevanz für {genre}.
"""


GENRE_DESCRIPTIONS = {
    LayerType.ROMANCE: """
Fokus auf: Romantische Orte, intime Settings, Orte für erste Begegnungen,
Plätze für Geständnisse, versteckte Ecken für Küsse, Restaurants für Dates.
Atmosphäre: Warm, einladend, sinnlich, magisch.""",
    
    LayerType.THRILLER: """
Fokus auf: Gefährliche Orte, dunkle Gassen, verlassene Plätze, Orte für Verfolgungen,
Verstecke, Treffpunkte für geheime Übergaben, Orte mit Fluchtmöglichkeiten.
Atmosphäre: Bedrohlich, urban, schattig, spannungsgeladen.""",
    
    LayerType.MYSTERY: """
Fokus auf: Geheimnisvolle Orte, alte Gebäude mit Geschichte, Archive, Bibliotheken,
Orte mit Legenden, versteckte Räume, Friedhöfe, historische Stätten.
Atmosphäre: Rätselhaft, neblig, historisch, mit verborgenen Geschichten.""",
    
    LayerType.FOODIE: """
Fokus auf: Beste Restaurants, authentische Lokale, Märkte, Street Food,
lokale Spezialitäten, Weinbars, Traditionslokale, Food-Touren.
Atmosphäre: Kulinarisch, authentisch, gesellig, aromatisch.""",
    
    LayerType.ART: """
Fokus auf: Museen, Galerien, Street Art, Architektur-Highlights,
Künstlerviertel, Ateliers, historische Kunstorte, moderne Installationen.
Atmosphäre: Kreativ, inspirierend, kulturell, ästhetisch.""",
    
    LayerType.HISTORY: """
Fokus auf: Historische Stätten, Denkmäler, alte Viertel, Museen,
Orte bedeutender Ereignisse, Ruinen, Paläste, Kirchen.
Atmosphäre: Ehrwürdig, zeitlos, geschichtsträchtig, nachdenklich.""",
    
    LayerType.ADVENTURE: """
Fokus auf: Aussichtspunkte, Wanderwege, sportliche Aktivitäten,
Adrenalin-Orte, Naturwunder, Kletter-Spots, Wassersport.
Atmosphäre: Aufregend, naturverbunden, herausfordernd, frei.""",
    
    LayerType.NIGHTLIFE: """
Fokus auf: Clubs, Bars, Rooftop-Lounges, Live-Musik-Venues,
Geheimtipps, Late-Night-Lokale, Szene-Treffpunkte.
Atmosphäre: Pulsierend, neonbeleuchtet, laut, exzessiv.""",
}


# ═══════════════════════════════════════════════════════════════
# LLM CLIENTS
# ═══════════════════════════════════════════════════════════════

class BaseLLMClient:
    """Base class for LLM clients"""
    
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class AnthropicLocationLLM(BaseLLMClient):
    """
    Echter Anthropic Claude Client für Location-Generierung.
    
    Benötigt: ANTHROPIC_API_KEY environment variable
    """
    
    def __init__(
        self, 
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ):
        import os
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY nicht gesetzt")
        
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic nicht installiert. Run: pip install anthropic")
        return self._client
    
    def generate(self, prompt: str) -> str:
        """Generiere Location-Daten via Claude API"""
        
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            system="""Du bist ein Experte für Reiseziele und kreatives Schreiben.
Deine Aufgabe ist es, detaillierte, atmosphärische Location-Daten für Romane zu generieren.

WICHTIG:
- Antworte NUR mit validem JSON, keine Erklärungen davor oder danach
- Verwende echte, existierende Orte mit korrekten Namen
- Schreibe atmosphärische, sinnliche Beschreibungen
- Fokussiere auf Details, die für Storytelling relevant sind
- Alle Texte auf Deutsch"""
        )
        
        # Extract text from response
        text = response.content[0].text.strip()
        
        # Clean up: Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return text.strip()


class MockLocationLLM(BaseLLMClient):
    """Mock LLM für Tests ohne API"""
    
    def generate(self, prompt: str) -> str:
        """Generiere Mock-Response basierend auf Prompt"""
        
        if "Barcelona" in prompt or "barcelona" in prompt:
            return self._barcelona_response(prompt)
        elif "Rom" in prompt or "rom" in prompt.lower() or "Rome" in prompt:
            return self._rom_response(prompt)
        else:
            return self._generic_response(prompt)
    
    def _barcelona_response(self, prompt: str) -> str:
        if "romance" in prompt.lower() or "ROMANCE" in prompt:
            return json.dumps(MOCK_BARCELONA_ROMANCE)
        elif "thriller" in prompt.lower() or "THRILLER" in prompt:
            return json.dumps(MOCK_BARCELONA_THRILLER)
        elif "Informationen über" in prompt:
            return json.dumps(MOCK_BARCELONA_BASE)
        else:
            return json.dumps(MOCK_BARCELONA_ROMANCE)
    
    def _rom_response(self, prompt: str) -> str:
        if "romance" in prompt.lower():
            return json.dumps(MOCK_ROM_ROMANCE)
        elif "Informationen über" in prompt:
            return json.dumps(MOCK_ROM_BASE)
        else:
            return json.dumps(MOCK_ROM_ROMANCE)
    
    def _generic_response(self, prompt: str) -> str:
        return json.dumps({"error": "Unknown city"})


# ═══════════════════════════════════════════════════════════════
# MOCK DATA
# ═══════════════════════════════════════════════════════════════

MOCK_BARCELONA_BASE = {
    "name": "Barcelona",
    "country": "Spanien",
    "region": "Katalonien",
    "coordinates": [41.3851, 2.1734],
    "timezone": "Europe/Madrid",
    "languages": ["Spanisch", "Katalanisch"],
    "currency": "EUR",
    "climate": "Mediterranes Klima mit milden Wintern und warmen Sommern",
    "best_seasons": ["Frühling", "Herbst"],
    "districts": [
        {"name": "Barri Gòtic", "local_name": "Barri Gòtic", "vibe": "historisch, verwinkelt, atmosphärisch", "description": "Das gotische Viertel mit engen Gassen, versteckten Plazas und mittelalterlicher Architektur."},
        {"name": "El Born", "local_name": "El Born", "vibe": "trendy, künstlerisch, lebendig", "description": "Hippes Viertel mit Boutiquen, Cocktailbars und dem Picasso-Museum."},
        {"name": "Barceloneta", "local_name": "La Barceloneta", "vibe": "maritim, entspannt, lokal", "description": "Das alte Fischerviertel am Strand mit Seafood-Restaurants und Strandpromenade."},
        {"name": "Gràcia", "local_name": "Gràcia", "vibe": "alternativ, bohemian, gemütlich", "description": "Ehemals eigenständiges Dorf mit charmanten Plazas und unabhängigen Läden."},
        {"name": "Eixample", "local_name": "L'Eixample", "vibe": "elegant, modernistisch, urban", "description": "Schachbrettmuster-Viertel mit Gaudí-Architektur und gehobenen Restaurants."},
    ],
    "population": 1620000,
    "known_for": ["Gaudí-Architektur", "Strand und Meer", "Tapas-Kultur", "FC Barcelona", "Lebendiges Nachtleben"],
}

MOCK_BARCELONA_ROMANCE = {
    "atmospheres": {
        "morning": "Goldenes Licht fällt durch die engen Gassen des Gotischen Viertels. Der Duft von frischem Café con leche mischt sich mit dem Geruch von warmem Stein. Die Stadt erwacht langsam, noch intim und ruhig.",
        "afternoon": "Die Sonne steht hoch über den Dachterrassen. In schattigen Innenhöfen plätschern Brunnen. Paare teilen Tapas in versteckten Bodegas, während das mediterrane Licht alles in warme Farben taucht.",
        "evening": "Die Stadt verwandelt sich. Straßenmusiker spielen Flamenco-Gitarre. Kerzen flackern auf den Tischen der Plazas. Der warme Wind trägt Gelächter und das Klirren von Cava-Gläsern.",
        "night": "Barcelona pulsiert. Versteckte Rooftop-Bars bieten Blicke über die illuminierte Stadt. Am Strand rauschen die Wellen. In dunklen Ecken des Gotischen Viertels finden sich geheime Momente.",
    },
    "places": [
        {"name": "Bunkers del Carmel", "place_type": "viewpoint", "district": "Gràcia", "relevance_score": 5, "description": "Alte Bunker-Ruinen mit dem besten Panoramablick über Barcelona. Locals kommen zum Sonnenuntergang mit Wein und Decken.", "atmosphere": "Magisch bei Sonnenuntergang, intim trotz anderer Besucher", "story_potential": "Perfekt für ein erstes Geständnis oder einen romantischen Wendepunkt. Die Stadt liegt einem zu Füßen."},
        {"name": "El Xampanyet", "place_type": "bar", "district": "El Born", "relevance_score": 5, "description": "Winzige Cava-Bar seit 1929. Blaue Kacheln, enge Räume, authentischster Cava der Stadt.", "atmosphere": "Laut, eng, authentisch - erzwingt körperliche Nähe", "story_potential": "Zufällige Begegnung in der Enge. Angestoßene Ellbogen führen zu Gesprächen."},
        {"name": "Plaça Sant Felip Neri", "place_type": "plaza", "district": "Barri Gòtic", "relevance_score": 5, "description": "Versteckter Platz mit tragischer Geschichte (Bürgerkrieg). Barock-Kirche, Brunnen, Tauben.", "atmosphere": "Melancholisch-schön, zeitlos, wie aus der Zeit gefallen", "story_potential": "Ort für tiefe Gespräche über Vergangenheit und Verlust. Emotionaler Wendepunkt."},
        {"name": "Barceloneta Strand bei Nacht", "place_type": "beach", "district": "Barceloneta", "relevance_score": 5, "description": "Der Stadtstrand nach Mitternacht. Warmer Sand, Wellenrauschen, Lichter der Stadt im Hintergrund.", "atmosphere": "Romantisch, wild, befreiend", "story_potential": "Mitternachtsschwimmen, Geheimnisse teilen, der erste Kuss unter Sternen."},
        {"name": "Jardins de Laribal", "place_type": "park", "district": "Montjuïc", "relevance_score": 4, "description": "Versteckte Gärten am Montjuïc mit maurischen Elementen, Wasserspielen und Aussicht.", "atmosphere": "Verzaubert, ruhig, wie ein geheimer Garten", "story_potential": "Geheimes Treffen, Flucht aus dem Alltag, Ort der Versöhnung."},
        {"name": "La Vinya del Senyor", "place_type": "bar", "district": "El Born", "relevance_score": 4, "description": "Weinbar direkt gegenüber Santa Maria del Mar. Terrasse mit Kirchenblick.", "atmosphere": "Kultiviert, romantisch, mit historischem Flair", "story_potential": "Erstes Date, Gespräche über Kunst und Leben, Sonnenuntergang über der Kirche."},
        {"name": "Palau de la Música Catalana", "place_type": "landmark", "district": "Sant Pere", "relevance_score": 4, "description": "Jugendstil-Konzertsaal von Domènech i Montaner. Überwältigende Glasdecke.", "atmosphere": "Überwältigend schön, emotional, erhaben", "story_potential": "Konzertbesuch wird zum emotionalen Durchbruch. Musik als Katalysator."},
        {"name": "Mirablau", "place_type": "bar", "district": "Tibidabo", "relevance_score": 4, "description": "Lounge-Bar am Tibidabo mit Panoramafenstern über die gesamte Stadt bis zum Meer.", "atmosphere": "Sophisticated, atemberaubend, wie über der Welt schwebend", "story_potential": "Exklusives Date, wichtiges Gespräch mit dramatischem Hintergrund."},
    ],
    "sensory": {
        "smells": ["Meer und Salz", "Jasmin in der Nacht", "Café con leche", "gegrillte Sardinen", "warmer Sandstein"],
        "sounds": ["Flamenco-Gitarre", "Möwengeschrei", "Katalanische Gespräche", "Wellenrauschen", "Kirchenglocken"],
        "textures": ["glatter Marmor", "raue Sandsteinmauern", "warmer Sand zwischen den Zehen", "kühle Mosaikfliesen"],
        "tastes": ["herber Cava", "salzige Sardinen", "süße Crema Catalana", "bitterer Café solo"],
        "visuals": ["Gaudís geschwungene Linien", "blaues Mittelmeer", "goldenes Abendlicht auf Fassaden", "bunte Mosaikbänke"],
    },
    "story_hooks": [
        "Ein mysteriöser Brief führt sie zu einem versteckten Innenhof im Gotischen Viertel",
        "Sie sehen sich jeden Tag zur gleichen Zeit im selben Café - wer spricht zuerst?",
        "Eine Verwechslung im Picasso-Museum bringt zwei Fremde zusammen",
        "Der Regen zwingt sie, unter demselben Balkon Schutz zu suchen",
        "Ein verlorenes Notizbuch mit Zeichnungen von Barcelona führt zu seinem Besitzer",
    ],
    "scene_settings": [
        "Frühstück auf einer sonnigen Dachterrasse mit Blick auf die Sagrada Familia",
        "Verlorengehen in den Gassen des Gotischen Viertels bei Vollmond",
        "Tapas-Hopping durch El Born, von Bar zu Bar",
        "Sonnenuntergang an den Bunkers mit einer Flasche Cava",
    ],
    "potential_conflicts": [
        "Einer muss Barcelona verlassen - letzte gemeinsame Nacht",
        "Geheimnis aus der Vergangenheit wird an einem bedeutsamen Ort enthüllt",
        "Missverständnis trennt sie - Wiedersehen am Strand",
    ],
}

MOCK_BARCELONA_THRILLER = {
    "atmospheres": {
        "morning": "Nebel hängt in den engen Gassen. Die Stadt ist noch still, aber jemand beobachtet aus einem Fenster. Schatten bewegen sich in Hauseingängen.",
        "afternoon": "Die Menschenmassen auf den Ramblas bieten perfekte Deckung. Zu viele Gesichter, zu viele Möglichkeiten. Paranoia kriecht hoch.",
        "evening": "Die Touristen verschwinden, die Stadt zeigt ihr anderes Gesicht. Deals in dunklen Ecken. Wer ist Freund, wer Feind?",
        "night": "Das Gotische Viertel wird zum Labyrinth. Schritte hallen, aber niemand ist zu sehen. Jede Gasse könnte eine Falle sein.",
    },
    "places": [
        {"name": "Raval-Gassen", "place_type": "danger_spot", "district": "El Raval", "relevance_score": 5, "description": "Enge, dunkle Gassen des ehemaligen Rotlichtviertels. Noch immer zwielichtig nach Einbruch der Dunkelheit.", "atmosphere": "Bedrohlich, urban, unberechenbar", "story_potential": "Verfolgungsjagd, geheime Übergabe, Hinterhalt."},
        {"name": "Alter Hafen - Port Vell", "place_type": "danger_spot", "district": "Barceloneta", "relevance_score": 5, "description": "Verlassene Lagerhallen und Kais. Nachts kaum beleuchtet, nur das Klatschen der Wellen.", "atmosphere": "Isoliert, gefährlich, perfekt für Konfrontationen", "story_potential": "Geheimes Treffen, Leichenfund, Flucht übers Wasser."},
        {"name": "Untergrund-Parkhaus Plaça Catalunya", "place_type": "danger_spot", "district": "Zentrum", "relevance_score": 4, "description": "Labyrinthisches Parkhaus unter dem Hauptplatz. Echo, Betonpfeiler, wenig Licht.", "atmosphere": "Klaustrophobisch, hallendes Echo, Paranoia", "story_potential": "Verfolgung zwischen Autos, geheime Übergabe, Entführung."},
    ],
    "sensory": {
        "smells": ["Abgase", "feuchter Beton", "Müll in Gassen", "Meer bei Nacht", "Zigarettenrauch"],
        "sounds": ["hallende Schritte", "quietschende Bremsen", "fernes Sirenengeheul", "Stille, die zu laut ist"],
        "textures": ["kalter Beton", "rostiges Metall", "feuchte Mauern", "das Gewicht einer Waffe"],
        "tastes": ["Adrenalin - metallisch", "bitterer Kaffee", "Blut auf der Lippe"],
        "visuals": ["Schatten in Hauseingängen", "flackernde Neonlichter", "Überwachungskameras", "leere Gassen"],
    },
    "story_hooks": [
        "Eine verschlüsselte Nachricht führt ins Labyrinth des Gotischen Viertels",
        "Der Informant erscheint nicht zum Treffen - stattdessen liegt eine Warnung",
        "Jemand kennt jeden ihrer Schritte - wer hat ihr Handy gehackt?",
    ],
    "scene_settings": [
        "Verfolgungsjagd durch die Gassen des Raval bei Nacht",
        "Geheimes Treffen in einer verlassenen Fabrik in Poblenou",
        "Observation von einer Dachterrasse aus",
    ],
    "potential_conflicts": [
        "Der Kontaktmann ist tot - jetzt ist sie die Hauptverdächtige",
        "Die Polizei und die Verbrecher sind beide hinter ihr her",
        "Der einzige Verbündete könnte ein Doppelagent sein",
    ],
}

MOCK_ROM_BASE = {
    "name": "Rom",
    "country": "Italien",
    "region": "Latium",
    "coordinates": [41.9028, 12.4964],
    "timezone": "Europe/Rome",
    "languages": ["Italienisch"],
    "currency": "EUR",
    "climate": "Mediterranes Klima, heiße Sommer, milde Winter",
    "best_seasons": ["Frühling", "Herbst"],
    "districts": [
        {"name": "Trastevere", "local_name": "Trastevere", "vibe": "bohemian, authentisch, romantisch", "description": "Kopfsteinpflaster, Efeu-bewachsene Fassaden, das echte römische Leben."},
        {"name": "Centro Storico", "local_name": "Centro Storico", "vibe": "monumental, touristisch, geschichtsträchtig", "description": "Das historische Zentrum mit Pantheon, Piazza Navona und zahllosen Kirchen."},
        {"name": "Testaccio", "local_name": "Testaccio", "vibe": "lokal, kulinarisch, unentdeckt", "description": "Arbeiterklasse-Viertel mit den besten Trattorien und dem alten Schlachthof."},
        {"name": "Monti", "local_name": "Monti", "vibe": "hip, vintage, künstlerisch", "description": "Trendiges Viertel mit Vintage-Läden, Bars und jungem Publikum."},
    ],
    "population": 2870000,
    "known_for": ["Kolosseum", "Vatikan", "Italienische Küche", "Dolce Vita", "Ewige Stadt"],
}

MOCK_ROM_ROMANCE = {
    "atmospheres": {
        "morning": "Rosa Morgenlicht auf Travertin-Fassaden. Der Duft von frischem Cornetto und Cappuccino. Rom erwacht mit dem Plätschern barocker Brunnen.",
        "evening": "Die Stadt glüht golden. Auf der Spanischen Treppe sitzen Verliebte. In Trastevere füllen sich die Trattorien, Gelächter hallt durch enge Gassen.",
        "night": "Rom bei Nacht ist magisch. Beleuchtete Monumente, leere Piazzas, der Geruch von Jasmin. Die Stadt gehört den Liebenden.",
    },
    "places": [
        {"name": "Spanische Treppe bei Nacht", "place_type": "landmark", "district": "Centro", "relevance_score": 5, "description": "Die berühmten Stufen, nachts beleuchtet und weniger überlaufen. Blick über Rom.", "atmosphere": "Ikonisch, romantisch, filmreif", "story_potential": "Das klassische Rom-Setting für Geständnisse und Wiedersehen."},
        {"name": "Gianicolo-Hügel", "place_type": "viewpoint", "district": "Trastevere", "relevance_score": 5, "description": "Aussichtspunkt über die ewige Stadt. Kuppeln, Dächer, die Berge am Horizont.", "atmosphere": "Erhaben, romantisch, zeitlos", "story_potential": "Sonnenuntergang mit Panorama - perfekt für wichtige Momente."},
        {"name": "Trastevere-Gassen", "place_type": "street", "district": "Trastevere", "relevance_score": 5, "description": "Verwinkelte Kopfsteinpflaster-Gassen mit Efeu, Wäscheleinen und versteckten Piazzas.", "atmosphere": "Authentisch, intim, das echte Rom", "story_potential": "Sich verlaufen und finden, zufällige Entdeckungen, das wahre Italien erleben."},
    ],
    "sensory": {
        "smells": ["frisches Basilikum", "Espresso", "alte Steine nach Regen", "Orangenblüten", "Holzofenpizza"],
        "sounds": ["Vespas", "Kirchenglocken", "italienische Gespräche", "plätschernde Brunnen", "Opern aus offenen Fenstern"],
        "textures": ["warmes Kopfsteinpflaster", "kühler Marmor", "knuspriges Brot", "samtige Pasta"],
        "tastes": ["Cacio e Pepe", "Gelato", "bitterer Espresso", "süßer Limoncello"],
        "visuals": ["Kuppeln gegen den Himmel", "Efeu an ockerfarbenen Mauern", "Brunnen im Abendlicht", "Priester in Schwarz"],
    },
    "story_hooks": [
        "Sie treffen sich jeden Tag 'zufällig' am selben Brunnen",
        "Ein antiker Schlüssel führt zu einem geheimen Garten",
        "La Dolce Vita - eine Nacht, die alles verändert",
    ],
    "scene_settings": [
        "Mitternachts-Gelato an der Fontana di Trevi",
        "Verstecktes Dinner in einer Kellerwein-Bar in Trastevere",
        "Vespa-Fahrt durch die nächtliche Stadt",
    ],
    "potential_conflicts": [
        "Rom ist zu schön - keiner will zur Realität zurück",
        "Ein Geheimnis aus der Vergangenheit wartet an der Spanischen Treppe",
    ],
}


# ═══════════════════════════════════════════════════════════════
# ON-DEMAND GENERATOR
# ═══════════════════════════════════════════════════════════════

class LocationGenerator:
    """
    Generiert Location-Daten on-demand.
    Prüft erst DB, dann Cache, dann generiert via LLM.
    
    Args:
        repository: LocationRepository instance
        llm_client: LLM client (MockLocationLLM oder AnthropicLocationLLM)
        use_real_llm: Wenn True, versuche echten LLM zu nutzen (mit Fallback auf Mock)
    """
    
    def __init__(
        self, 
        repository: LocationRepository, 
        llm_client: BaseLLMClient = None,
        use_real_llm: bool = False,
    ):
        self.repo = repository
        
        # LLM Client Setup
        if llm_client:
            self.llm = llm_client
        elif use_real_llm:
            try:
                self.llm = AnthropicLocationLLM()
                print("  ✓ Anthropic LLM aktiviert")
            except (ValueError, ImportError) as e:
                print(f"  ⚠ LLM Fallback auf Mock: {e}")
                self.llm = MockLocationLLM()
        else:
            self.llm = MockLocationLLM()
    
    def get_base_location(self, city: str, country: str = "") -> BaseLocation:
        """
        Hole oder generiere BaseLocation.
        
        1. Check DB
        2. Check Cache
        3. Generate via LLM
        """
        location_id = city.lower().replace(" ", "_").replace("-", "_")
        
        # 1. Check DB
        existing = self.repo.get_base_location(location_id)
        if existing:
            return existing
        
        # 2. Check Cache
        cache_key = f"{location_id}:base"
        cached = self.repo.get_cached(cache_key)
        if cached:
            cached["id"] = location_id
            location = BaseLocation.from_dict(cached)
            self.repo.save_base_location(location)
            return location
        
        # 3. Generate via LLM
        print(f"  → Generiere Base Location für '{city}'...")
        prompt = BASE_LOCATION_PROMPT.format(city=city, country=country or "")
        response = self.llm.generate(prompt)
        
        try:
            data = json.loads(response)
            data["id"] = location_id
            data["source"] = "llm_generated"
            data["generated_at"] = datetime.now().isoformat()
            data["quality_score"] = 0.8
            
            location = BaseLocation.from_dict(data)
            
            # Save to DB and Cache
            self.repo.save_base_location(location)
            self.repo.save_cache(cache_key, data)
            
            return location
            
        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON Parse Error: {e}")
            # Fallback: Minimal location
            return BaseLocation(
                id=location_id,
                name=city,
                country=country or "Unknown",
                source="fallback",
            )
    
    def get_location_layer(
        self, 
        location_id: str, 
        layer_type: LayerType,
        city_name: str = ""
    ) -> LocationLayer:
        """
        Hole oder generiere LocationLayer.
        
        1. Check DB
        2. Check Cache  
        3. Generate via LLM
        """
        location_id = location_id.lower()
        
        # 1. Check DB
        existing = self.repo.get_location_layer(location_id, layer_type)
        if existing:
            return existing
        
        # 2. Check Cache
        cache_key = f"{location_id}:{layer_type.value}"
        cached = self.repo.get_cached(cache_key)
        if cached:
            cached["location_id"] = location_id
            cached["layer_type"] = layer_type.value
            layer = LocationLayer.from_dict(cached)
            self.repo.save_location_layer(layer)
            return layer
        
        # 3. Generate via LLM
        print(f"  → Generiere {layer_type.value} Layer für '{city_name or location_id}'...")
        genre_desc = GENRE_DESCRIPTIONS.get(layer_type, "Allgemeine Details")
        prompt = LOCATION_LAYER_PROMPT.format(
            city=city_name or location_id,
            genre=layer_type.value,
            genre_description=genre_desc,
        )
        response = self.llm.generate(prompt)
        
        try:
            data = json.loads(response)
            data["location_id"] = location_id
            data["layer_type"] = layer_type.value
            data["generated_at"] = datetime.now().isoformat()
            data["quality_score"] = 0.8
            
            layer = LocationLayer.from_dict(data)
            
            # Save to DB and Cache
            self.repo.save_location_layer(layer)
            self.repo.save_cache(cache_key, data)
            
            return layer
            
        except json.JSONDecodeError as e:
            print(f"  ⚠ JSON Parse Error: {e}")
            # Fallback: Empty layer
            return LocationLayer(
                location_id=location_id,
                layer_type=layer_type,
            )
    
    def get_merged_location(
        self,
        city: str,
        country: str,
        layer_type: LayerType,
        user_world: Optional[UserWorld] = None,
    ) -> MergedLocationData:
        """
        Hole komplette, gemergete Location-Daten.
        """
        location_id = city.lower().replace(" ", "_")
        
        # Get base
        base = self.get_base_location(city, country)
        
        # Get layer
        layer = self.get_location_layer(location_id, layer_type, city)
        
        # Merge
        merged = MergedLocationData(
            location_id=location_id,
            name=base.name,
            country=base.country,
            districts=base.districts,
            layer_type=layer_type,
            atmospheres=layer.atmospheres,
            places=layer.places,
            sensory=layer.sensory,
            story_hooks=layer.story_hooks,
        )
        
        # Apply user personalization
        if user_world:
            merged.personal_places = user_world.get_personal_places(location_id)
            merged.excluded_places = user_world.get_excluded_places(location_id)
            merged.location_memories = user_world.get_memories_for_location(location_id)
            
            # Filter excluded places from layer places
            merged.places = [
                p for p in merged.places 
                if p.name not in merged.excluded_places
            ]
        
        return merged
