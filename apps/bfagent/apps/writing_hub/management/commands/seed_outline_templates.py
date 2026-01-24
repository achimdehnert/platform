"""
Management command to seed outline templates for the Import Framework V2.

Usage:
    python manage.py seed_outline_templates
    python manage.py seed_outline_templates --clear  # Clear existing first
"""

from django.core.management.base import BaseCommand
from apps.writing_hub.models_import_framework import OutlineCategory, OutlineTemplate


CATEGORIES = [
    {
        'code': 'classic',
        'name': 'Classic Structures',
        'name_de': 'Klassische Strukturen',
        'description': 'Time-tested narrative frameworks used across media',
        'icon': '📚',
        'order': 1,
    },
    {
        'code': 'author_methods',
        'name': 'Author Methods',
        'name_de': 'Autoren-Methoden',
        'description': 'Structures developed by successful authors',
        'icon': '✍️',
        'order': 2,
    },
    {
        'code': 'genre_specific',
        'name': 'Genre-Specific',
        'name_de': 'Genre-spezifisch',
        'description': 'Structures optimized for specific genres',
        'icon': '🎭',
        'order': 3,
    },
    {
        'code': 'experimental',
        'name': 'Experimental',
        'name_de': 'Experimentell',
        'description': 'Non-traditional and innovative structures',
        'icon': '🔬',
        'order': 4,
    },
]

TEMPLATES = [
    # === CLASSIC STRUCTURES ===
    {
        'code': 'three_act',
        'category_code': 'classic',
        'name': 'Three-Act Structure',
        'name_de': 'Drei-Akt-Struktur',
        'description': 'The foundational narrative structure used in most Western storytelling. Divides story into Setup, Confrontation, and Resolution.',
        'description_de': 'Die grundlegende Erzählstruktur der westlichen Erzähltradition. Teilt die Geschichte in Aufstellung, Konfrontation und Auflösung.',
        'structure_json': {
            'acts': [
                {
                    'number': 1,
                    'name': 'Setup',
                    'name_de': 'Aufstellung',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Opening', 'name_de': 'Eröffnung', 'description': 'Hook the reader, establish tone'},
                        {'name': 'Exposition', 'name_de': 'Exposition', 'description': 'World and character introduction'},
                        {'name': 'Inciting Incident', 'name_de': 'Auslösendes Ereignis', 'description': 'Event that starts the story'},
                        {'name': 'First Plot Point', 'name_de': 'Erster Wendepunkt', 'description': 'Hero commits to the journey'},
                    ]
                },
                {
                    'number': 2,
                    'name': 'Confrontation',
                    'name_de': 'Konfrontation',
                    'percentage': 50,
                    'beats': [
                        {'name': 'Rising Action', 'name_de': 'Steigende Handlung', 'description': 'Obstacles and complications'},
                        {'name': 'Midpoint', 'name_de': 'Mittelpunkt', 'description': 'Major revelation or shift'},
                        {'name': 'Complications', 'name_de': 'Komplikationen', 'description': 'Stakes increase'},
                        {'name': 'Second Plot Point', 'name_de': 'Zweiter Wendepunkt', 'description': 'Crisis point'},
                    ]
                },
                {
                    'number': 3,
                    'name': 'Resolution',
                    'name_de': 'Auflösung',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Climax', 'name_de': 'Höhepunkt', 'description': 'Final confrontation'},
                        {'name': 'Falling Action', 'name_de': 'Fallende Handlung', 'description': 'Aftermath'},
                        {'name': 'Resolution', 'name_de': 'Auflösung', 'description': 'New equilibrium'},
                        {'name': 'Ending', 'name_de': 'Ende', 'description': 'Final image/thought'},
                    ]
                }
            ],
            'total_beats': 12
        },
        'genre_tags': ['thriller', 'romance', 'fantasy', 'literary', 'mystery', 'sci-fi'],
        'theme_tags': [],
        'pov_tags': ['first_person', 'third_limited', 'multiple', 'omniscient'],
        'word_count_min': 60000,
        'word_count_max': 150000,
        'difficulty_level': 'beginner',
        'example_books': 'Most Hollywood films, The Hunger Games, Gone Girl',
        'pros': 'Universally understood, clear structure, flexible within beats',
        'cons': 'Can feel formulaic, requires strong midpoint',
        'is_featured': True,
    },
    {
        'code': 'heroes_journey',
        'category_code': 'classic',
        'name': "Hero's Journey (Monomyth)",
        'name_de': 'Heldenreise (Monomythos)',
        'description': "Joseph Campbell's mythological structure. The hero leaves the ordinary world, faces trials, and returns transformed.",
        'description_de': 'Joseph Campbells mythologische Struktur. Der Held verlässt die gewöhnliche Welt, stellt sich Prüfungen und kehrt verwandelt zurück.',
        'structure_json': {
            'acts': [
                {
                    'number': 1,
                    'name': 'Departure',
                    'name_de': 'Aufbruch',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Ordinary World', 'name_de': 'Gewöhnliche Welt', 'description': "Hero's normal life"},
                        {'name': 'Call to Adventure', 'name_de': 'Ruf des Abenteuers', 'description': 'Challenge presented'},
                        {'name': 'Refusal of the Call', 'name_de': 'Weigerung', 'description': 'Hero hesitates'},
                        {'name': 'Meeting the Mentor', 'name_de': 'Treffen mit dem Mentor', 'description': 'Guidance received'},
                        {'name': 'Crossing the Threshold', 'name_de': 'Überschreiten der Schwelle', 'description': 'Enter special world'},
                    ]
                },
                {
                    'number': 2,
                    'name': 'Initiation',
                    'name_de': 'Initiation',
                    'percentage': 50,
                    'beats': [
                        {'name': 'Tests, Allies, Enemies', 'name_de': 'Prüfungen, Verbündete, Feinde', 'description': 'Learning the rules'},
                        {'name': 'Approach to Inmost Cave', 'name_de': 'Annäherung an die innerste Höhle', 'description': 'Preparation for ordeal'},
                        {'name': 'Ordeal', 'name_de': 'Prüfung', 'description': 'Greatest challenge'},
                        {'name': 'Reward', 'name_de': 'Belohnung', 'description': 'Seizing the prize'},
                    ]
                },
                {
                    'number': 3,
                    'name': 'Return',
                    'name_de': 'Rückkehr',
                    'percentage': 25,
                    'beats': [
                        {'name': 'The Road Back', 'name_de': 'Der Weg zurück', 'description': 'Commitment to return'},
                        {'name': 'Resurrection', 'name_de': 'Auferstehung', 'description': 'Final test, transformation'},
                        {'name': 'Return with Elixir', 'name_de': 'Rückkehr mit dem Elixier', 'description': 'Hero brings gift to world'},
                    ]
                }
            ],
            'total_beats': 12
        },
        'genre_tags': ['fantasy', 'adventure', 'epic', 'sci-fi', 'coming-of-age'],
        'theme_tags': ['transformation', 'growth', 'destiny', 'courage'],
        'pov_tags': ['third_limited', 'first_person'],
        'word_count_min': 80000,
        'word_count_max': 200000,
        'difficulty_level': 'intermediate',
        'example_books': 'Star Wars, Harry Potter, The Lord of the Rings, The Matrix',
        'pros': 'Deep mythological resonance, strong character arc, universal appeal',
        'cons': 'Can be predictable, requires strong mentor figure, may feel dated',
        'is_featured': True,
    },
    
    # === AUTHOR METHODS ===
    {
        'code': 'save_the_cat',
        'category_code': 'author_methods',
        'name': 'Save the Cat Beat Sheet',
        'name_de': 'Save the Cat Beatsheet',
        'description': "Blake Snyder's 15-beat structure for emotionally engaging storytelling. Originally for screenwriting, now popular for novels.",
        'description_de': 'Blake Snyders 15-Beat-Struktur für emotional ansprechendes Storytelling. Ursprünglich für Drehbücher, jetzt populär für Romane.',
        'structure_json': {
            'acts': [
                {
                    'number': 1,
                    'name': 'Thesis',
                    'name_de': 'These',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Opening Image', 'name_de': 'Eröffnungsbild', 'description': 'Visual of life before', 'page_target': '1%'},
                        {'name': 'Theme Stated', 'name_de': 'Thema angedeutet', 'description': 'Theme hinted (often by secondary character)', 'page_target': '5%'},
                        {'name': 'Set-Up', 'name_de': 'Einrichtung', 'description': 'Introduce hero, flaws, world', 'page_target': '1-10%'},
                        {'name': 'Catalyst', 'name_de': 'Katalysator', 'description': 'Life-changing event', 'page_target': '10%'},
                        {'name': 'Debate', 'name_de': 'Debatte', 'description': 'Hero questions the journey', 'page_target': '10-20%'},
                    ]
                },
                {
                    'number': 2,
                    'name': 'Antithesis',
                    'name_de': 'Antithese',
                    'percentage': 50,
                    'beats': [
                        {'name': 'Break into Two', 'name_de': 'Übergang zu Akt 2', 'description': 'Hero enters new world', 'page_target': '20%'},
                        {'name': 'B Story', 'name_de': 'B-Handlung', 'description': 'Love story / theme carrier', 'page_target': '22%'},
                        {'name': 'Fun and Games', 'name_de': 'Spaß und Spiele', 'description': 'Promise of the premise', 'page_target': '20-50%'},
                        {'name': 'Midpoint', 'name_de': 'Mittelpunkt', 'description': 'False victory or defeat', 'page_target': '50%'},
                        {'name': 'Bad Guys Close In', 'name_de': 'Die Bösen rücken näher', 'description': 'External/internal pressure', 'page_target': '50-75%'},
                        {'name': 'All Is Lost', 'name_de': 'Alles ist verloren', 'description': 'Lowest point, often a death', 'page_target': '75%'},
                        {'name': 'Dark Night of the Soul', 'name_de': 'Dunkle Nacht der Seele', 'description': 'Hero processes loss', 'page_target': '75-80%'},
                    ]
                },
                {
                    'number': 3,
                    'name': 'Synthesis',
                    'name_de': 'Synthese',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Break into Three', 'name_de': 'Übergang zu Akt 3', 'description': 'Solution found (A + B stories)', 'page_target': '80%'},
                        {'name': 'Finale', 'name_de': 'Finale', 'description': 'Hero proves transformation', 'page_target': '80-99%'},
                        {'name': 'Final Image', 'name_de': 'Schlussbild', 'description': 'Opposite of opening', 'page_target': '100%'},
                    ]
                }
            ],
            'total_beats': 15
        },
        'genre_tags': ['romance', 'thriller', 'comedy', 'drama', 'contemporary'],
        'theme_tags': ['redemption', 'love', 'transformation', 'self-discovery'],
        'pov_tags': ['first_person', 'third_limited', 'dual_pov'],
        'word_count_min': 70000,
        'word_count_max': 100000,
        'difficulty_level': 'beginner',
        'example_books': 'Legally Blonde, Miss Congeniality, The Proposal',
        'pros': 'Very prescriptive timing, emotional beats, commercial appeal',
        'cons': 'Can feel rigid, Hollywood-centric',
        'is_featured': True,
    },
    {
        'code': 'seven_point',
        'category_code': 'author_methods',
        'name': 'Seven-Point Story Structure',
        'name_de': 'Sieben-Punkte-Struktur',
        'description': "Dan Wells' compact structure focusing on key turning points. Work backwards from Resolution to Hook.",
        'description_de': 'Dan Wells kompakte Struktur mit Fokus auf Wendepunkte. Arbeite rückwärts von der Auflösung zum Hook.',
        'structure_json': {
            'acts': [
                {
                    'number': 1,
                    'name': 'Beginning',
                    'name_de': 'Anfang',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Hook', 'name_de': 'Hook', 'description': 'Opposite state of Resolution'},
                        {'name': 'Plot Turn 1', 'name_de': 'Wendepunkt 1', 'description': 'Call to action, new world/conflict'},
                    ]
                },
                {
                    'number': 2,
                    'name': 'Middle',
                    'name_de': 'Mitte',
                    'percentage': 50,
                    'beats': [
                        {'name': 'Pinch 1', 'name_de': 'Zwickmühle 1', 'description': 'Apply pressure, force action'},
                        {'name': 'Midpoint', 'name_de': 'Mittelpunkt', 'description': 'Move from reaction to action'},
                        {'name': 'Pinch 2', 'name_de': 'Zwickmühle 2', 'description': 'Apply more pressure, remove options'},
                    ]
                },
                {
                    'number': 3,
                    'name': 'End',
                    'name_de': 'Ende',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Plot Turn 2', 'name_de': 'Wendepunkt 2', 'description': 'Final piece of puzzle'},
                        {'name': 'Resolution', 'name_de': 'Auflösung', 'description': 'Hero achieves goal'},
                    ]
                }
            ],
            'total_beats': 7
        },
        'genre_tags': ['thriller', 'mystery', 'horror', 'fantasy', 'sci-fi'],
        'theme_tags': ['mystery', 'revelation', 'discovery', 'justice'],
        'pov_tags': ['first_person', 'third_limited'],
        'word_count_min': 60000,
        'word_count_max': 120000,
        'difficulty_level': 'intermediate',
        'example_books': 'I Am Not A Serial Killer, most thriller novels',
        'pros': 'Simple, flexible, works well for plotters and pantsers',
        'cons': 'Less guidance on emotional beats, requires strong instincts',
        'is_featured': False,
    },
    
    # === GENRE SPECIFIC ===
    {
        'code': 'romance_arc',
        'category_code': 'genre_specific',
        'name': 'Romance Arc (HEA)',
        'name_de': 'Romance-Bogen (HEA)',
        'description': 'Structure optimized for romance novels with guaranteed Happy Ever After. Dual POV friendly.',
        'description_de': 'Für Romance-Romane optimierte Struktur mit garantiertem Happy End. Dual-POV-freundlich.',
        'structure_json': {
            'acts': [
                {
                    'number': 1,
                    'name': 'Meeting',
                    'name_de': 'Begegnung',
                    'percentage': 20,
                    'beats': [
                        {'name': 'Setup', 'name_de': 'Einrichtung', 'description': 'Introduce both protagonists separately'},
                        {'name': 'Meet-Cute', 'name_de': 'Erste Begegnung', 'description': 'First meeting, chemistry established'},
                        {'name': 'External Conflict Setup', 'name_de': 'Externer Konflikt', 'description': 'Why they cannot be together'},
                    ]
                },
                {
                    'number': 2,
                    'name': 'Falling',
                    'name_de': 'Verliebtheit',
                    'percentage': 30,
                    'beats': [
                        {'name': 'Forced Proximity', 'name_de': 'Erzwungene Nähe', 'description': 'Circumstances keep them together'},
                        {'name': 'Growing Attraction', 'name_de': 'Wachsende Anziehung', 'description': 'Resist but fail'},
                        {'name': 'First Kiss/Intimacy', 'name_de': 'Erster Kuss/Intimität', 'description': 'Physical milestone'},
                        {'name': 'Midpoint Shift', 'name_de': 'Wendepunkt', 'description': 'Acknowledge feelings (internally or to each other)'},
                    ]
                },
                {
                    'number': 3,
                    'name': 'Crisis',
                    'name_de': 'Krise',
                    'percentage': 30,
                    'beats': [
                        {'name': 'Deepening', 'name_de': 'Vertiefung', 'description': 'Emotional intimacy grows'},
                        {'name': 'Black Moment Setup', 'name_de': 'Schwarzer Moment Vorbereitung', 'description': 'Seeds of conflict bloom'},
                        {'name': 'Black Moment', 'name_de': 'Schwarzer Moment', 'description': 'Breakup/separation'},
                        {'name': 'Dark Night', 'name_de': 'Dunkle Nacht', 'description': 'Both realize what they lost'},
                    ]
                },
                {
                    'number': 4,
                    'name': 'Resolution',
                    'name_de': 'Auflösung',
                    'percentage': 20,
                    'beats': [
                        {'name': 'Grand Gesture', 'name_de': 'Große Geste', 'description': 'One or both make amends'},
                        {'name': 'Declaration', 'name_de': 'Liebeserklärung', 'description': 'Love declared'},
                        {'name': 'HEA/HFN', 'name_de': 'Happy End', 'description': 'Happy Ever After / Happy For Now'},
                        {'name': 'Epilogue', 'name_de': 'Epilog', 'description': 'Future glimpse (optional)'},
                    ]
                }
            ],
            'total_beats': 16
        },
        'genre_tags': ['romance', 'contemporary_romance', 'historical_romance', 'paranormal_romance'],
        'theme_tags': ['love', 'trust', 'healing', 'second_chance', 'forbidden'],
        'pov_tags': ['dual_pov', 'first_person', 'third_limited'],
        'word_count_min': 50000,
        'word_count_max': 100000,
        'difficulty_level': 'beginner',
        'example_books': 'The Hating Game, Beach Read, It Ends with Us',
        'pros': 'Genre expectations met, emotional payoff, dual POV supported',
        'cons': 'Formulaic if not executed well, HEA required',
        'is_featured': True,
    },
    {
        'code': 'dark_romance',
        'category_code': 'genre_specific',
        'name': 'Dark Romance Arc',
        'name_de': 'Dark Romance Bogen',
        'description': 'Modified romance structure for darker themes. Includes morally grey heroes and trauma healing arcs.',
        'description_de': 'Modifizierte Romance-Struktur für dunklere Themen. Enthält moralisch graue Helden und Trauma-Heilungs-Bögen.',
        'structure_json': {
            'acts': [
                {
                    'number': 1,
                    'name': 'Descent',
                    'name_de': 'Abstieg',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Dark World Setup', 'name_de': 'Dunkle Welt', 'description': 'Establish dark setting/circumstances'},
                        {'name': 'Power Dynamic Introduction', 'name_de': 'Machtdynamik', 'description': 'Hero has power over heroine (or vice versa)'},
                        {'name': 'Forced Situation', 'name_de': 'Erzwungene Situation', 'description': 'Why she cannot leave'},
                        {'name': 'First Dark Moment', 'name_de': 'Erster dunkler Moment', 'description': 'Hero shows his darkness'},
                    ]
                },
                {
                    'number': 2,
                    'name': 'Entanglement',
                    'name_de': 'Verstrickung',
                    'percentage': 30,
                    'beats': [
                        {'name': 'Glimpse of Humanity', 'name_de': 'Blick auf Menschlichkeit', 'description': 'Hero shows vulnerability'},
                        {'name': 'Forbidden Attraction', 'name_de': 'Verbotene Anziehung', 'description': 'Against better judgment'},
                        {'name': 'First Surrender', 'name_de': 'Erste Hingabe', 'description': 'Physical intimacy (often intense)'},
                        {'name': 'Backstory Reveal', 'name_de': 'Hintergrund enthüllt', 'description': 'Why hero is damaged'},
                    ]
                },
                {
                    'number': 3,
                    'name': 'Breaking Point',
                    'name_de': 'Bruchpunkt',
                    'percentage': 25,
                    'beats': [
                        {'name': 'Possession vs Freedom', 'name_de': 'Besitz vs Freiheit', 'description': 'Internal conflict peaks'},
                        {'name': 'Ultimate Dark Act', 'name_de': 'Ultimativer dunkler Akt', 'description': 'Hero crosses a line'},
                        {'name': 'Separation', 'name_de': 'Trennung', 'description': 'Heroine escapes or is released'},
                        {'name': 'Hero Redemption Arc', 'name_de': 'Helden-Erlösung', 'description': 'Hero faces his demons'},
                    ]
                },
                {
                    'number': 4,
                    'name': 'Redemption',
                    'name_de': 'Erlösung',
                    'percentage': 20,
                    'beats': [
                        {'name': 'Choice', 'name_de': 'Wahl', 'description': 'Heroine chooses to return (or not)'},
                        {'name': 'Sacrifice', 'name_de': 'Opfer', 'description': 'Hero proves change'},
                        {'name': 'Acceptance', 'name_de': 'Akzeptanz', 'description': 'Love declared with open eyes'},
                        {'name': 'Dark HEA', 'name_de': 'Dunkles Happy End', 'description': 'Happy but not conventional'},
                    ]
                }
            ],
            'total_beats': 16
        },
        'genre_tags': ['dark_romance', 'mafia_romance', 'bully_romance', 'captive_romance'],
        'theme_tags': ['redemption', 'trauma', 'obsession', 'healing', 'power'],
        'pov_tags': ['dual_pov', 'first_person'],
        'word_count_min': 60000,
        'word_count_max': 120000,
        'difficulty_level': 'advanced',
        'example_books': 'Twisted series, Corrupt, Den of Vipers',
        'pros': 'Intense emotional journey, complex characters',
        'cons': 'Requires careful handling of dark themes, content warnings needed',
        'is_featured': True,
    },
    {
        'code': 'thriller_suspense',
        'category_code': 'genre_specific',
        'name': 'Thriller/Suspense Structure',
        'name_de': 'Thriller/Suspense-Struktur',
        'description': 'Optimized for page-turning suspense with ticking clocks and rising stakes.',
        'description_de': 'Optimiert für seitenumblätternde Spannung mit tickenden Uhren und steigenden Einsätzen.',
        'structure_json': {
            'acts': [
                {
                    'number': 1,
                    'name': 'Setup',
                    'name_de': 'Einrichtung',
                    'percentage': 20,
                    'beats': [
                        {'name': 'Hook', 'name_de': 'Hook', 'description': 'Gripping opening (often a crime or threat)'},
                        {'name': 'Protagonist Intro', 'name_de': 'Protagonist Intro', 'description': 'Show expertise and flaw'},
                        {'name': 'Inciting Crime/Threat', 'name_de': 'Auslösendes Verbrechen', 'description': 'The case/threat presented'},
                        {'name': 'Ticking Clock Established', 'name_de': 'Tickende Uhr etabliert', 'description': 'Deadline or urgency'},
                    ]
                },
                {
                    'number': 2,
                    'name': 'Investigation',
                    'name_de': 'Untersuchung',
                    'percentage': 35,
                    'beats': [
                        {'name': 'First Clue/Lead', 'name_de': 'Erster Hinweis', 'description': 'Initial direction'},
                        {'name': 'Red Herring', 'name_de': 'Falsche Fährte', 'description': 'Misleading information'},
                        {'name': 'Stakes Raised', 'name_de': 'Einsätze erhöht', 'description': 'Another victim or threat escalates'},
                        {'name': 'Midpoint Revelation', 'name_de': 'Mittelpunkt-Enthüllung', 'description': 'Major discovery changes direction'},
                        {'name': 'Personal Stakes', 'name_de': 'Persönliche Einsätze', 'description': 'It becomes personal for protagonist'},
                    ]
                },
                {
                    'number': 3,
                    'name': 'Confrontation',
                    'name_de': 'Konfrontation',
                    'percentage': 30,
                    'beats': [
                        {'name': 'Closing In', 'name_de': 'Einkreisen', 'description': 'Pieces come together'},
                        {'name': 'Twist', 'name_de': 'Twist', 'description': 'Surprise revelation'},
                        {'name': 'All Is Lost', 'name_de': 'Alles verloren', 'description': 'Villain gains upper hand'},
                        {'name': 'Final Clue', 'name_de': 'Letzter Hinweis', 'description': 'Protagonist sees the truth'},
                    ]
                },
                {
                    'number': 4,
                    'name': 'Resolution',
                    'name_de': 'Auflösung',
                    'percentage': 15,
                    'beats': [
                        {'name': 'Climactic Confrontation', 'name_de': 'Klimaktische Konfrontation', 'description': 'Face-to-face with antagonist'},
                        {'name': 'Resolution', 'name_de': 'Auflösung', 'description': 'Justice served (or not)'},
                        {'name': 'New Status Quo', 'name_de': 'Neuer Status Quo', 'description': 'How has protagonist changed'},
                    ]
                }
            ],
            'total_beats': 16
        },
        'genre_tags': ['thriller', 'mystery', 'crime', 'suspense', 'police_procedural'],
        'theme_tags': ['justice', 'obsession', 'truth', 'revenge'],
        'pov_tags': ['first_person', 'third_limited', 'multiple'],
        'word_count_min': 70000,
        'word_count_max': 120000,
        'difficulty_level': 'intermediate',
        'example_books': 'Gone Girl, The Girl on the Train, The Silent Patient',
        'pros': 'Page-turning structure, clear escalation, satisfying reveals',
        'cons': 'Requires careful plotting of clues, twist must be earned',
        'is_featured': True,
    },
]


class Command(BaseCommand):
    help = 'Seed outline templates and categories for Import Framework V2'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing templates before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing templates...')
            OutlineTemplate.objects.all().delete()
            OutlineCategory.objects.all().delete()

        # Create categories
        self.stdout.write('Creating categories...')
        categories = {}
        for cat_data in CATEGORIES:
            cat, created = OutlineCategory.objects.update_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            categories[cat.code] = cat
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status}: {cat.name}')

        # Create templates
        self.stdout.write('Creating templates...')
        for tpl_data in TEMPLATES:
            category_code = tpl_data.pop('category_code')
            category = categories.get(category_code)
            
            tpl, created = OutlineTemplate.objects.update_or_create(
                code=tpl_data['code'],
                defaults={**tpl_data, 'category': category}
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'  {status}: {tpl.name}')

        self.stdout.write(self.style.SUCCESS(
            f'Done! Created {len(CATEGORIES)} categories and {len(TEMPLATES)} templates.'
        ))
