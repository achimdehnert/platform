"""
Management Command: Setup Content Type Frameworks
Populates the database with content types, frameworks, and beats.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.writing_hub.models import ContentType, StructureFramework, FrameworkBeat


class Command(BaseCommand):
    help = 'Setup content types, frameworks, and beats for the Writing Hub'

    # ==========================================================================
    # CONTENT TYPES
    # ==========================================================================
    CONTENT_TYPES = {
        'novel': {
            'name': 'Novel',
            'name_de': 'Roman',
            'description': 'Längere Erzählung mit komplexer Handlung, Charakterentwicklung und Weltenbau.',
            'icon': 'bi-book',
            'section_label': 'Kapitel',
            'section_label_plural': 'Kapitel',
            'default_word_count': 80000,
            'default_section_count': 25,
            'has_characters': True,
            'has_world_building': True,
            'has_citations': False,
            'has_abstract': False,
            'sort_order': 1,
            'llm_system_prompt': '''Du bist ein erfahrener Romanautor und Schreibcoach. 
Du hilfst beim Entwickeln von fesselnden Geschichten mit lebendigen Charakteren.
Dein Stil ist kreativ, inspirierend und praxisorientiert.
Antworte immer auf Deutsch, es sei denn, du wirst um eine andere Sprache gebeten.'''
        },
        'novella': {
            'name': 'Novella',
            'name_de': 'Novelle',
            'description': 'Kürzere Erzählung mit fokussierter Handlung und begrenztem Figurenensemble.',
            'icon': 'bi-journal-text',
            'section_label': 'Kapitel',
            'section_label_plural': 'Kapitel',
            'default_word_count': 30000,
            'default_section_count': 12,
            'has_characters': True,
            'has_world_building': True,
            'has_citations': False,
            'has_abstract': False,
            'sort_order': 2,
            'llm_system_prompt': '''Du bist ein erfahrener Autor für Novellen und kürzere Erzählformen.
Du hilfst beim Entwickeln kompakter, intensiver Geschichten.'''
        },
        'short_story': {
            'name': 'Short Story',
            'name_de': 'Kurzgeschichte',
            'description': 'Kurze Erzählung mit konzentrierter Handlung und wenigen Charakteren.',
            'icon': 'bi-file-earmark-text',
            'section_label': 'Szene',
            'section_label_plural': 'Szenen',
            'default_word_count': 5000,
            'default_section_count': 5,
            'has_characters': True,
            'has_world_building': False,
            'has_citations': False,
            'has_abstract': False,
            'sort_order': 3,
            'llm_system_prompt': '''Du bist ein Meister der Kurzgeschichte.
Du hilfst beim Entwickeln prägnanter, wirkungsvoller Erzählungen.'''
        },
        'essay': {
            'name': 'Essay',
            'name_de': 'Essay',
            'description': 'Argumentativer oder reflektierender Text zu einem Thema.',
            'icon': 'bi-file-text',
            'section_label': 'Abschnitt',
            'section_label_plural': 'Abschnitte',
            'default_word_count': 3000,
            'default_section_count': 7,
            'has_characters': False,
            'has_world_building': False,
            'has_citations': False,
            'has_abstract': False,
            'sort_order': 10,
            'llm_system_prompt': '''Du bist ein erfahrener Essayist und Rhetorik-Experte.
Du hilfst beim Entwickeln überzeugender Argumente und klarer Gedankenführung.
Dein Stil ist präzise, logisch und eloquent.'''
        },
        'scientific': {
            'name': 'Scientific Paper',
            'name_de': 'Wissenschaftliche Arbeit',
            'description': 'Akademische Arbeit mit Forschungsfrage, Methodik und Quellenarbeit.',
            'icon': 'bi-mortarboard',
            'section_label': 'Abschnitt',
            'section_label_plural': 'Abschnitte',
            'default_word_count': 15000,
            'default_section_count': 10,
            'has_characters': False,
            'has_world_building': False,
            'has_citations': True,
            'has_abstract': True,
            'sort_order': 20,
            'llm_system_prompt': '''Du bist ein wissenschaftlicher Schreibcoach mit Expertise in akademischem Schreiben.
Du hilfst bei der Entwicklung klarer Forschungsfragen, methodischer Stringenz und präziser Argumentation.
Dein Stil ist sachlich, präzise und wissenschaftlich fundiert.'''
        },
        'blog': {
            'name': 'Blog Post',
            'name_de': 'Blog-Artikel',
            'description': 'Informativer oder unterhaltsamer Online-Artikel.',
            'icon': 'bi-newspaper',
            'section_label': 'Abschnitt',
            'section_label_plural': 'Abschnitte',
            'default_word_count': 1500,
            'default_section_count': 5,
            'has_characters': False,
            'has_world_building': False,
            'has_citations': False,
            'has_abstract': False,
            'sort_order': 30,
            'llm_system_prompt': '''Du bist ein erfahrener Content Creator und Blogger.
Du hilfst beim Erstellen ansprechender, leserfreundlicher Online-Inhalte.'''
        },
    }

    # ==========================================================================
    # FRAMEWORKS FOR NOVELS
    # ==========================================================================
    NOVEL_FRAMEWORKS = {
        'save_the_cat': {
            'name': 'Save the Cat',
            'name_de': 'Save the Cat (15 Beats)',
            'description': 'Blake Snyders 15-Beat-Struktur für emotionale Spannung und klare Wendepunkte.',
            'icon': 'bi-star',
            'default_section_count': 15,
            'is_default': True,
            'sort_order': 1,
            'llm_system_prompt': '''Verwende die Save the Cat Struktur von Blake Snyder.
Die 15 Beats sorgen für emotionale Resonanz und klare Wendepunkte.
Achte besonders auf den Midpoint und das "All Is Lost" Moment.''',
            'llm_user_template': '''Erstelle einen {beat_name} für die Geschichte "{title}" im Genre {genre}.
Kontext: {context}
Der Beat sollte etwa {word_count} Wörter umfassen.''',
            'beats': [
                {'name': 'Opening Image', 'name_de': 'Eröffnungsbild', 'position': '0%', 'part': 1, 'sort_order': 1,
                 'description': 'Zeigt den Protagonisten in seinem normalen Leben vor der Veränderung.',
                 'llm_prompt': 'Beschreibe die Ausgangssituation des Protagonisten. Zeige sein normales Leben und etabliere den Ton der Geschichte.'},
                {'name': 'Theme Stated', 'name_de': 'Thema genannt', 'position': '5%', 'part': 1, 'sort_order': 2,
                 'description': 'Das zentrale Thema wird subtil eingeführt.',
                 'llm_prompt': 'Führe das zentrale Thema der Geschichte ein - oft durch Dialog einer Nebenfigur.'},
                {'name': 'Set-Up', 'name_de': 'Einführung', 'position': '1-10%', 'part': 1, 'sort_order': 3,
                 'description': 'Etabliert die Welt, Charaktere und den Status Quo.',
                 'llm_prompt': 'Stelle die wichtigsten Charaktere vor und zeige die Welt der Geschichte.'},
                {'name': 'Catalyst', 'name_de': 'Katalysator', 'position': '10%', 'part': 1, 'sort_order': 4,
                 'description': 'Das Ereignis, das alles verändert.',
                 'llm_prompt': 'Das auslösende Ereignis, das die Geschichte in Gang setzt.'},
                {'name': 'Debate', 'name_de': 'Debatte', 'position': '10-25%', 'part': 1, 'sort_order': 5,
                 'description': 'Der Protagonist zögert, die Reise anzutreten.',
                 'llm_prompt': 'Zeige den inneren Konflikt des Protagonisten - soll er/sie sich auf das Abenteuer einlassen?'},
                {'name': 'Break into Two', 'name_de': 'Übergang in Akt 2', 'position': '25%', 'part': 2, 'sort_order': 6,
                 'description': 'Der Protagonist entscheidet sich, die neue Welt zu betreten.',
                 'llm_prompt': 'Der Protagonist trifft eine aktive Entscheidung und betritt die "neue Welt" der Geschichte.'},
                {'name': 'B Story', 'name_de': 'B-Geschichte', 'position': '30%', 'part': 2, 'sort_order': 7,
                 'description': 'Einführung des Love Interest oder Mentors.',
                 'llm_prompt': 'Führe die sekundäre Handlung ein - oft eine Liebesgeschichte oder Mentor-Beziehung.'},
                {'name': 'Fun and Games', 'name_de': 'Spaß und Spiele', 'position': '30-50%', 'part': 2, 'sort_order': 8,
                 'description': 'Die "Promise of the Premise" - was Leser von diesem Genre erwarten.',
                 'llm_prompt': 'Liefere die Szenen, die das Genre-Versprechen einlösen. Der Protagonist erkundet die neue Welt.'},
                {'name': 'Midpoint', 'name_de': 'Mittelpunkt', 'position': '50%', 'part': 2, 'sort_order': 9,
                 'description': 'Falscher Sieg oder falsche Niederlage - die Stakes erhöhen sich.',
                 'llm_prompt': 'Ein scheinbarer Triumph oder Tiefpunkt, der die Stakes erhöht und die Richtung ändert.'},
                {'name': 'Bad Guys Close In', 'name_de': 'Die Bösen rücken näher', 'position': '50-75%', 'part': 2, 'sort_order': 10,
                 'description': 'Die Opposition wird stärker, interne Probleme entstehen.',
                 'llm_prompt': 'Die Gegner werden stärker, interne Konflikte im Team entstehen.'},
                {'name': 'All Is Lost', 'name_de': 'Alles verloren', 'position': '75%', 'part': 2, 'sort_order': 11,
                 'description': 'Der absolute Tiefpunkt - oft mit einem "Whiff of Death".',
                 'llm_prompt': 'Der absolute Tiefpunkt der Geschichte. Der Protagonist scheint alles verloren zu haben.'},
                {'name': 'Dark Night of the Soul', 'name_de': 'Dunkle Nacht der Seele', 'position': '75-80%', 'part': 2, 'sort_order': 12,
                 'description': 'Der Protagonist verarbeitet die Niederlage.',
                 'llm_prompt': 'Der emotionale Tiefpunkt - der Protagonist muss sich seinen Dämonen stellen.'},
                {'name': 'Break into Three', 'name_de': 'Übergang in Akt 3', 'position': '80%', 'part': 3, 'sort_order': 13,
                 'description': 'Eine neue Idee oder Erkenntnis ermöglicht die Lösung.',
                 'llm_prompt': 'Eine Erkenntnis (oft aus der B-Story) zeigt den Weg zur Lösung.'},
                {'name': 'Finale', 'name_de': 'Finale', 'position': '80-99%', 'part': 3, 'sort_order': 14,
                 'description': 'Der Protagonist konfrontiert die Opposition mit dem Gelernten.',
                 'llm_prompt': 'Der finale Konflikt - der Protagonist wendet alles Gelernte an.'},
                {'name': 'Final Image', 'name_de': 'Schlussbild', 'position': '100%', 'part': 3, 'sort_order': 15,
                 'description': 'Zeigt die Transformation - Kontrast zum Opening Image.',
                 'llm_prompt': 'Das Schlussbild zeigt die Veränderung - ein Kontrast zum Eröffnungsbild.'},
            ]
        },
        'heros_journey': {
            'name': "Hero's Journey",
            'name_de': 'Heldenreise (12 Stufen)',
            'description': 'Joseph Campbells mythologische Struktur für transformative Geschichten.',
            'icon': 'bi-compass',
            'default_section_count': 12,
            'is_default': False,
            'sort_order': 2,
            'llm_system_prompt': '''Verwende die Heldenreise nach Joseph Campbell.
Die 12 Stufen führen den Helden durch Trennung, Initiation und Rückkehr.''',
            'beats': [
                {'name': 'Ordinary World', 'name_de': 'Gewöhnliche Welt', 'position': '0-8%', 'part': 1, 'sort_order': 1,
                 'description': 'Die normale Welt des Helden vor dem Abenteuer.'},
                {'name': 'Call to Adventure', 'name_de': 'Ruf zum Abenteuer', 'position': '8-12%', 'part': 1, 'sort_order': 2,
                 'description': 'Etwas ruft den Helden zum Abenteuer.'},
                {'name': 'Refusal of the Call', 'name_de': 'Weigerung', 'position': '12-17%', 'part': 1, 'sort_order': 3,
                 'description': 'Der Held zögert oder weigert sich.'},
                {'name': 'Meeting the Mentor', 'name_de': 'Begegnung mit dem Mentor', 'position': '17-25%', 'part': 1, 'sort_order': 4,
                 'description': 'Ein weiser Führer erscheint.'},
                {'name': 'Crossing the Threshold', 'name_de': 'Überschreiten der Schwelle', 'position': '25%', 'part': 2, 'sort_order': 5,
                 'description': 'Der Held betritt die besondere Welt.'},
                {'name': 'Tests, Allies, Enemies', 'name_de': 'Prüfungen, Verbündete, Feinde', 'position': '25-50%', 'part': 2, 'sort_order': 6,
                 'description': 'Der Held trifft auf Herausforderungen und neue Charaktere.'},
                {'name': 'Approach to the Inmost Cave', 'name_de': 'Annäherung an die Höhle', 'position': '50%', 'part': 2, 'sort_order': 7,
                 'description': 'Vorbereitung auf die größte Prüfung.'},
                {'name': 'Ordeal', 'name_de': 'Entscheidende Prüfung', 'position': '50-60%', 'part': 2, 'sort_order': 8,
                 'description': 'Die zentrale Krise - Tod und Wiedergeburt.'},
                {'name': 'Reward', 'name_de': 'Belohnung', 'position': '60-75%', 'part': 2, 'sort_order': 9,
                 'description': 'Der Held erhält das Elixier oder den Schatz.'},
                {'name': 'The Road Back', 'name_de': 'Rückweg', 'position': '75-85%', 'part': 3, 'sort_order': 10,
                 'description': 'Beginn der Heimreise mit neuen Gefahren.'},
                {'name': 'Resurrection', 'name_de': 'Auferstehung', 'position': '85-95%', 'part': 3, 'sort_order': 11,
                 'description': 'Letzte, größte Prüfung - Transformation vollendet.'},
                {'name': 'Return with the Elixir', 'name_de': 'Rückkehr mit dem Elixier', 'position': '95-100%', 'part': 3, 'sort_order': 12,
                 'description': 'Der Held kehrt verwandelt zurück.'},
            ]
        },
        'three_act': {
            'name': 'Three-Act Structure',
            'name_de': 'Drei-Akt-Struktur',
            'description': 'Die klassische dramatische Struktur: Setup, Konfrontation, Auflösung.',
            'icon': 'bi-collection',
            'default_section_count': 12,
            'is_default': False,
            'sort_order': 3,
            'beats': [
                {'name': 'Hook', 'name_de': 'Hook', 'position': '0-5%', 'part': 1, 'sort_order': 1,
                 'description': 'Fesselt den Leser sofort.'},
                {'name': 'Introduction', 'name_de': 'Einführung', 'position': '5-10%', 'part': 1, 'sort_order': 2,
                 'description': 'Stellt Protagonisten und Welt vor.'},
                {'name': 'Inciting Incident', 'name_de': 'Auslösendes Ereignis', 'position': '10-15%', 'part': 1, 'sort_order': 3,
                 'description': 'Das Ereignis, das die Handlung startet.'},
                {'name': 'First Plot Point', 'name_de': 'Erster Wendepunkt', 'position': '20-25%', 'part': 1, 'sort_order': 4,
                 'description': 'Ende von Akt 1 - keine Rückkehr möglich.'},
                {'name': 'Rising Action', 'name_de': 'Steigende Handlung', 'position': '25-35%', 'part': 2, 'sort_order': 5,
                 'description': 'Konflikte und Hindernisse nehmen zu.'},
                {'name': 'Midpoint', 'name_de': 'Mittelpunkt', 'position': '50%', 'part': 2, 'sort_order': 6,
                 'description': 'Zentrale Wende - alles ändert sich.'},
                {'name': 'Escalation', 'name_de': 'Eskalation', 'position': '50-65%', 'part': 2, 'sort_order': 7,
                 'description': 'Die Lage verschärft sich.'},
                {'name': 'Crisis', 'name_de': 'Krise', 'position': '65-75%', 'part': 2, 'sort_order': 8,
                 'description': 'Der Tiefpunkt vor dem Finale.'},
                {'name': 'Climax Build', 'name_de': 'Aufbau zum Höhepunkt', 'position': '75-80%', 'part': 3, 'sort_order': 9,
                 'description': 'Vorbereitung auf den finalen Konflikt.'},
                {'name': 'Climax', 'name_de': 'Höhepunkt', 'position': '80-90%', 'part': 3, 'sort_order': 10,
                 'description': 'Der finale Konflikt.'},
                {'name': 'Falling Action', 'name_de': 'Fallende Handlung', 'position': '90-95%', 'part': 3, 'sort_order': 11,
                 'description': 'Die Konsequenzen des Höhepunkts.'},
                {'name': 'Resolution', 'name_de': 'Auflösung', 'position': '95-100%', 'part': 3, 'sort_order': 12,
                 'description': 'Das neue Normal.'},
            ]
        },
        'trapped_butterfly': {
            'name': 'Trapped Butterfly',
            'name_de': 'McFadden-Stil (16 Beats)',
            'description': 'Psychologischer Thriller mit unzuverlässigem Erzähler, geschlossenem Setting und 3 Twist-Struktur. Basiert auf Freida McFaddens Thriller-Stil.',
            'icon': 'bi-incognito',
            'default_section_count': 16,
            'is_default': False,
            'sort_order': 4,
            'llm_system_prompt': '''Du schreibst im McFadden-Stil für psychologische Thriller.

DIE 5 SÄULEN:
1. UNZUVERLÄSSIGER ERZÄHLER - Ich-Perspektive, Präsens, Leser sieht nur was Protagonistin sieht
2. GESCHLOSSENES SETTING - Haus/Institution wird zur Falle
3. SCHLEICHENDE BEDROHUNG - Von subtil zu lebensbedrohlich, Gaslighting
4. MULTIPLE TWISTS - Mindestens 3, finale verändert alles rückwirkend
5. HÄUSLICHE GEFAHR - Bedrohung aus engstem Kreis, weibliche Perspektive

STILREGELN:
- Ich-Erzähler, Präsens durchgängig
- Satzlängen-Mix: ~40% kurz (1-8 Wörter), ~40% mittel (9-15), ~20% lang (16+)
- NICHT nur Fragmentsätze! Rhythmus: KURZ. KURZ. MITTEL. KURZ. LÄNGER MIT DETAIL.
- Ausführlicher, sarkastischer innerer Monolog (mind. 30% des Textes)
- Detailreiche Beschreibungen mit Wertung (Klasse, Status)
- Dialog mit Action Beats und inneren Reaktionen
- Micro-Tension auch in Alltagsszenen
- Humor trotz Spannung (Sarkasmus, Selbstironie)
- Kapitellänge: 2.000-3.500 Wörter
- Jedes Kapitel endet mit Hook

PROTAGONISTIN-ARCHETYPEN:
- Die Neue (neue Beziehung, neuer Job, neues Haus)
- Die Rückkehrerin (zurück zu Familie, Heimatort)
- Die Helferin (Pflegerin, Gouvernante, Therapeutin)
- Die Suchende (sucht Wahrheit über Vergangenheit)

ANTAGONIST-ARCHETYPEN:
- Charmeur: Perfekt nach außen, kontrollierend dahinter
- Beschützer: "Ich passe auf dich auf", isoliert durch Fürsorge
- Rächer: Freundlich aber distanziert, hat Grund für Vergeltung
- Opportunist: Hilfsbereit, kalkuliert, will Geld/Status

TWIST-GOLDENE REGEL:
Überraschend, aber im Rückblick unvermeidlich. Alle Hinweise waren da (versteckt).''',
            'llm_user_template': '''Schreibe den Beat "{beat_name}" für den psychologischen Thriller "{title}".

Beat-Beschreibung: {description}
Position im Roman: {position}
Kontext: {context}

Stilanforderungen:
- Ich-Perspektive, Präsens
- Satzlängen variiert (nicht nur kurz!)
- Sarkastischer innerer Monolog
- Details mit Klassenbeobachtung
- Micro-Tension/Unbehagen
- ~{word_count} Wörter
- Ende mit Hook''',
            'beats': [
                # AKT I: DIE FALLE (25%)
                {'name': 'The Hook', 'name_de': 'Der Hook', 'position': '0-2%', 'part': 1, 'sort_order': 1,
                 'description': 'Sofortige Spannung + Frage aufwerfen. In-Medias-Res oder Rückblick-Prolog.',
                 'llm_prompt': 'Beginne mit sofortiger Spannung. Optionen: Gefahr/Geheimnis entdecken ODER Szene der Gefahr mit Sprung zu "X Monate früher". Etabliere Ich-Perspektive und Kernfrage: "Was ist hier wirklich los?"'},
                {'name': 'The Setup', 'name_de': 'Das Setup', 'position': '2-8%', 'part': 1, 'sort_order': 2,
                 'description': 'Protagonistin + Setting + scheinbare Normalität etablieren.',
                 'llm_prompt': 'Stelle die Protagonistin vor: sympathisch, aber mit versteckter Verletzlichkeit. Zeige ihre Situation (Job, Beziehung, Familie). Führe das Setting ein. Säe 3-5 versteckte Hinweise, die erst später Sinn machen.'},
                {'name': 'Entering the Trap', 'name_de': 'Die Falle betreten', 'position': '8-15%', 'part': 1, 'sort_order': 3,
                 'description': 'Protagonistin bindet sich an die gefährliche Situation.',
                 'llm_prompt': 'Die Protagonistin bindet sich: Einzug ins Haus, Beginn einer Beziehung, Annahme eines Jobs. Bindung erscheint FREIWILLIG, ist aber subtil erzwungen (emotional, praktisch, moralisch).'},
                {'name': 'False Security', 'name_de': 'Falsche Sicherheit', 'position': '15-25%', 'part': 1, 'sort_order': 4,
                 'description': 'Scheinbare Idylle mit subtilen Störungen. 70% gut, 30% seltsam.',
                 'llm_prompt': 'Balance: 70% "Alles ist gut" + 30% "Etwas stimmt nicht". Subtile Störungen: Räume die man nicht betreten soll, Themen über die nicht gesprochen wird, übertriebene Freundlichkeit. Erstes Gaslighting: "Habe ich mir das eingebildet?" Akt I endet mit unübersehbarem Zeichen.'},
                # AKT II: DAS ERWACHEN (25%)
                {'name': 'First Warning', 'name_de': 'Erste Warnung', 'position': '25-30%', 'part': 2, 'sort_order': 5,
                 'description': 'Protagonistin erkennt: Etwas ist wirklich falsch.',
                 'llm_prompt': 'Warnung: Jemand warnt sie (wird als verrückt abgetan), sie entdeckt etwas Verstörendes, ein "Unfall" passiert. Reaktion: Unglaube → Rationalisierung → wachsende Unruhe. Sie kann NOCH NICHT gehen.'},
                {'name': 'Twist #1 - Red Herring', 'name_de': 'Twist #1 - Falsche Fährte', 'position': '30-35%', 'part': 2, 'sort_order': 6,
                 'description': 'Erste größere Wendung - lenkt Verdacht in falsche Richtung.',
                 'llm_prompt': 'Der "offensichtliche Bösewicht" wird verdächtigt: unheimlicher Nachbar, mysteriöser Fremder, "verrückte" Ex. Leser denkt: "Ah, ICH weiß wer der Böse ist!" - aber der wahre Antagonist bleibt verborgen.'},
                {'name': 'Doubt & Isolation', 'name_de': 'Zweifel & Isolation', 'position': '35-43%', 'part': 2, 'sort_order': 7,
                 'description': 'Protagonistin wird systematisch isoliert. Gaslighting intensiviert.',
                 'llm_prompt': 'Isolation durch: Entfremdung von Freunden/Familie, kontrollierte Kommunikation, untergrabenene Glaubwürdigkeit, finanzielle Abhängigkeit. Gaslighting: "Das hast du dir eingebildet", "Du bist zu empfindlich", Beweise verschwinden. Protagonistin zweifelt: "Bin ICH das Problem?"'},
                {'name': 'Investigation', 'name_de': 'Die Recherche', 'position': '43-50%', 'part': 2, 'sort_order': 8,
                 'description': 'Protagonistin beginnt nachzuforschen. Potenzieller Ally erscheint.',
                 'llm_prompt': 'Recherche: Durchsuchen von Räumen/Unterlagen, Befragen von Menschen, Internet-Recherche. Ein potenzieller Ally tritt auf (Nachbarin, Kollege, Kind). ABER: Ist diese Person wirklich Ally? Akt II endet mit Entdeckung eines GROSSEN Geheimnisses.'},
                # AKT III: DER KAMPF (25%)
                {'name': 'Point of No Return', 'name_de': 'Point of No Return', 'position': '50-55%', 'part': 3, 'sort_order': 9,
                 'description': 'Protagonistin weiß zu viel - Rückweg unmöglich.',
                 'llm_prompt': 'Sie entdeckt die WAHRE Gefahr, der Antagonist merkt dass sie es weiß. Flucht scheint einzige Option, ABER blockiert: Kinder/Abhängige, kein Geld, "Wer würde mir glauben?", Drohungen, Erpressung mit ihrem eigenen Geheimnis.'},
                {'name': 'Twist #2 - True Threat', 'name_de': 'Twist #2 - Wahre Bedrohung', 'position': '55-65%', 'part': 3, 'sort_order': 10,
                 'description': 'Die ECHTE Identität/Natur der Bedrohung wird enthüllt.',
                 'llm_prompt': 'Twist-Kategorien: A) Identität: Helfer ist Feind, Verdächtiger war unschuldig. B) Beziehung: Partner ist nicht der für den er sich ausgibt. C) Motiv: Geld, Rache, Obsession, Vertuschung. D) Vergangenheit: "Unfall" war Mord, verdrängte Erinnerungen.'},
                {'name': 'Mortal Danger', 'name_de': 'Lebensgefahr', 'position': '65-72%', 'part': 3, 'sort_order': 11,
                 'description': 'All Is Lost - physische Bedrohung wird real.',
                 'llm_prompt': '"All Is Lost" Moment. Die Bedrohung wird physisch real: eingesperrt, angegriffen, jemand stirbt. Protagonistin völlig allein, scheint keine Hoffnung zu geben. Tiefster emotionaler Punkt.'},
                {'name': 'The Plan', 'name_de': 'Der Plan', 'position': '72-75%', 'part': 3, 'sort_order': 12,
                 'description': 'Protagonistin entwickelt Gegenstrategie.',
                 'llm_prompt': 'Aus der Verzweiflung wächst Entschlossenheit. Protagonistin nutzt ihr Wissen über den Antagonisten. Vorbereitung der finalen Konfrontation - sie wird vom Opfer zur Akteurin.'},
                # AKT IV: DIE WAHRHEIT (25%)
                {'name': 'Final Confrontation', 'name_de': 'Finale Konfrontation', 'position': '75-82%', 'part': 4, 'sort_order': 13,
                 'description': 'Face to Face mit dem Antagonisten.',
                 'llm_prompt': 'Direkte Konfrontation. Masken fallen. Antagonist enthüllt wahre Natur. Psychologisches Duell bevor es physisch wird. Höchste Spannung.'},
                {'name': 'Twist #3 - The Big One', 'name_de': 'Twist #3 - DER große Twist', 'position': '82-90%', 'part': 4, 'sort_order': 14,
                 'description': 'DER Twist - verändert ALLES rückwirkend.',
                 'llm_prompt': 'Der finale Twist verändert das gesamte Verständnis der Geschichte. Möglichkeiten: Protagonistin hat manipuliert, ihre Realität war anders, Täter-Opfer vertauscht, gespaltene Persönlichkeit. Im Rückblick waren ALLE Hinweise da.'},
                {'name': 'Resolution', 'name_de': 'Auflösung', 'position': '90-97%', 'part': 4, 'sort_order': 15,
                 'description': 'Konsequenzen des Twists. Wer überlebt? Wer wird bestraft?',
                 'llm_prompt': 'Die Konsequenzen: Wer überlebt? Wer wird bestraft? Gerechtigkeit oder nicht? Die neue Realität der Protagonistin nach der Enthüllung.'},
                {'name': 'Epilog', 'name_de': 'Epilog', 'position': '97-100%', 'part': 4, 'sort_order': 16,
                 'description': 'Letzter Hook - die Geschichte ist vielleicht noch nicht vorbei.',
                 'llm_prompt': 'Kurzer Epilog. Scheinbare Ruhe, aber ein letzter Hook: Ein Detail, das Zweifel säht. War wirklich alles, wie es schien? Lädt zum erneuten Lesen ein.'},
            ]
        },
    }

    # ==========================================================================
    # FRAMEWORKS FOR NOVELLAS (reuse Trapped Butterfly)
    # ==========================================================================
    NOVELLA_FRAMEWORKS = {
        'trapped_butterfly': {
            'name': 'Trapped Butterfly',
            'name_de': 'McFadden-Stil (16 Beats)',
            'description': 'Psychologischer Thriller mit unzuverlässigem Erzähler und 3 Twist-Struktur. Kompakter als Roman.',
            'icon': 'bi-incognito',
            'default_section_count': 16,
            'is_default': False,
            'sort_order': 1,
            'llm_system_prompt': '''Du schreibst im McFadden-Stil für psychologische Thriller (Novella-Format).

DIE 5 SÄULEN:
1. UNZUVERLÄSSIGER ERZÄHLER - Ich-Perspektive, Präsens
2. GESCHLOSSENES SETTING - Haus/Institution wird zur Falle
3. SCHLEICHENDE BEDROHUNG - Von subtil zu lebensbedrohlich
4. MULTIPLE TWISTS - Mindestens 3, finale verändert alles
5. HÄUSLICHE GEFAHR - Bedrohung aus engstem Kreis

STILREGELN (Novella-angepasst):
- Ich-Erzähler, Präsens
- Satzlängen variiert, sarkastischer innerer Monolog
- Kapitellänge: 1.500-2.500 Wörter (kompakter als Roman)
- Jedes Kapitel endet mit Hook''',
            'beats': [
                {'name': 'The Hook', 'name_de': 'Der Hook', 'position': '0-3%', 'part': 1, 'sort_order': 1,
                 'description': 'Sofortige Spannung + Frage aufwerfen.'},
                {'name': 'The Setup', 'name_de': 'Das Setup', 'position': '3-10%', 'part': 1, 'sort_order': 2,
                 'description': 'Protagonistin + Setting etablieren.'},
                {'name': 'Entering the Trap', 'name_de': 'Die Falle betreten', 'position': '10-18%', 'part': 1, 'sort_order': 3,
                 'description': 'Protagonistin bindet sich an die Situation.'},
                {'name': 'False Security', 'name_de': 'Falsche Sicherheit', 'position': '18-25%', 'part': 1, 'sort_order': 4,
                 'description': 'Scheinbare Idylle mit subtilen Störungen.'},
                {'name': 'First Warning', 'name_de': 'Erste Warnung', 'position': '25-32%', 'part': 2, 'sort_order': 5,
                 'description': 'Etwas ist wirklich falsch.'},
                {'name': 'Twist #1', 'name_de': 'Twist #1', 'position': '32-38%', 'part': 2, 'sort_order': 6,
                 'description': 'Falsche Fährte - falscher Verdächtiger.'},
                {'name': 'Isolation', 'name_de': 'Isolation', 'position': '38-45%', 'part': 2, 'sort_order': 7,
                 'description': 'Gaslighting intensiviert.'},
                {'name': 'Investigation', 'name_de': 'Recherche', 'position': '45-50%', 'part': 2, 'sort_order': 8,
                 'description': 'Nachforschungen beginnen.'},
                {'name': 'Point of No Return', 'name_de': 'Kein Zurück', 'position': '50-57%', 'part': 3, 'sort_order': 9,
                 'description': 'Rückweg unmöglich.'},
                {'name': 'Twist #2', 'name_de': 'Twist #2', 'position': '57-65%', 'part': 3, 'sort_order': 10,
                 'description': 'Wahre Bedrohung enthüllt.'},
                {'name': 'Mortal Danger', 'name_de': 'Lebensgefahr', 'position': '65-72%', 'part': 3, 'sort_order': 11,
                 'description': 'All Is Lost.'},
                {'name': 'The Plan', 'name_de': 'Der Plan', 'position': '72-75%', 'part': 3, 'sort_order': 12,
                 'description': 'Gegenstrategie entwickeln.'},
                {'name': 'Confrontation', 'name_de': 'Konfrontation', 'position': '75-82%', 'part': 4, 'sort_order': 13,
                 'description': 'Face to Face.'},
                {'name': 'Twist #3', 'name_de': 'Twist #3', 'position': '82-90%', 'part': 4, 'sort_order': 14,
                 'description': 'DER große Twist.'},
                {'name': 'Resolution', 'name_de': 'Auflösung', 'position': '90-97%', 'part': 4, 'sort_order': 15,
                 'description': 'Konsequenzen.'},
                {'name': 'Epilog', 'name_de': 'Epilog', 'position': '97-100%', 'part': 4, 'sort_order': 16,
                 'description': 'Letzter Hook.'},
            ]
        },
    }

    # ==========================================================================
    # FRAMEWORKS FOR ESSAYS
    # ==========================================================================
    ESSAY_FRAMEWORKS = {
        'argumentative': {
            'name': 'Argumentative Essay',
            'name_de': 'Argumentativer Essay',
            'description': 'Strukturierte Argumentation für eine These mit Belegen und Gegenargumenten.',
            'icon': 'bi-chat-quote',
            'default_section_count': 8,
            'is_default': True,
            'sort_order': 1,
            'llm_system_prompt': '''Erstelle einen überzeugenden argumentativen Essay.
Achte auf klare These, stichhaltige Argumente und faire Behandlung von Gegenargumenten.''',
            'beats': [
                {'name': 'Hook & Introduction', 'name_de': 'Einleitung & Hook', 'position': '0-10%', 'part': 1, 'sort_order': 1,
                 'description': 'Aufmerksamkeit erregen und Thema einführen.'},
                {'name': 'Thesis Statement', 'name_de': 'These', 'position': '10-15%', 'part': 1, 'sort_order': 2,
                 'description': 'Klare Formulierung der Hauptthese.'},
                {'name': 'Background', 'name_de': 'Hintergrund', 'position': '15-25%', 'part': 1, 'sort_order': 3,
                 'description': 'Kontext und notwendige Informationen.'},
                {'name': 'Argument 1', 'name_de': 'Argument 1', 'position': '25-40%', 'part': 2, 'sort_order': 4,
                 'description': 'Erstes Hauptargument mit Belegen.'},
                {'name': 'Argument 2', 'name_de': 'Argument 2', 'position': '40-55%', 'part': 2, 'sort_order': 5,
                 'description': 'Zweites Hauptargument mit Belegen.'},
                {'name': 'Argument 3', 'name_de': 'Argument 3', 'position': '55-70%', 'part': 2, 'sort_order': 6,
                 'description': 'Drittes Hauptargument mit Belegen.'},
                {'name': 'Counterarguments', 'name_de': 'Gegenargumente', 'position': '70-85%', 'part': 2, 'sort_order': 7,
                 'description': 'Anerkennung und Entkräftung von Gegenargumenten.'},
                {'name': 'Conclusion', 'name_de': 'Fazit', 'position': '85-100%', 'part': 3, 'sort_order': 8,
                 'description': 'Zusammenfassung und abschließende Aussage.'},
            ]
        },
        'comparative': {
            'name': 'Comparative Essay',
            'name_de': 'Vergleichender Essay',
            'description': 'Gegenüberstellung und Analyse von zwei oder mehr Positionen.',
            'icon': 'bi-arrows-angle-expand',
            'default_section_count': 7,
            'is_default': False,
            'sort_order': 2,
            'beats': [
                {'name': 'Introduction', 'name_de': 'Einleitung', 'position': '0-10%', 'part': 1, 'sort_order': 1,
                 'description': 'Thema und Vergleichsobjekte vorstellen.'},
                {'name': 'Research Question', 'name_de': 'Fragestellung', 'position': '10-15%', 'part': 1, 'sort_order': 2,
                 'description': 'Klare Vergleichsfrage formulieren.'},
                {'name': 'Position A', 'name_de': 'Position A', 'position': '15-35%', 'part': 2, 'sort_order': 3,
                 'description': 'Darstellung der ersten Position.'},
                {'name': 'Position B', 'name_de': 'Position B', 'position': '35-55%', 'part': 2, 'sort_order': 4,
                 'description': 'Darstellung der zweiten Position.'},
                {'name': 'Comparison', 'name_de': 'Vergleich & Analyse', 'position': '55-75%', 'part': 2, 'sort_order': 5,
                 'description': 'Systematischer Vergleich und Analyse.'},
                {'name': 'Evaluation', 'name_de': 'Bewertung', 'position': '75-90%', 'part': 3, 'sort_order': 6,
                 'description': 'Eigene Bewertung und Einordnung.'},
                {'name': 'Conclusion', 'name_de': 'Schlussfolgerung', 'position': '90-100%', 'part': 3, 'sort_order': 7,
                 'description': 'Zusammenfassung und Schlussfolgerung.'},
            ]
        },
        'analytical': {
            'name': 'Analytical Essay',
            'name_de': 'Analytischer Essay',
            'description': 'Tiefgehende Analyse eines Themas oder Werkes.',
            'icon': 'bi-search',
            'default_section_count': 7,
            'is_default': False,
            'sort_order': 3,
            'beats': [
                {'name': 'Introduction & Context', 'name_de': 'Einleitung & Kontext', 'position': '0-15%', 'part': 1, 'sort_order': 1,
                 'description': 'Thema und Analysegegenstand einführen.'},
                {'name': 'Analysis Question', 'name_de': 'Analysefrage', 'position': '15-20%', 'part': 1, 'sort_order': 2,
                 'description': 'Zentrale Analysefrage formulieren.'},
                {'name': 'Methodology', 'name_de': 'Methodik', 'position': '20-30%', 'part': 2, 'sort_order': 3,
                 'description': 'Analytischer Ansatz und Methode.'},
                {'name': 'Analysis Part 1', 'name_de': 'Analyse Teil 1', 'position': '30-50%', 'part': 2, 'sort_order': 4,
                 'description': 'Erster Analyseabschnitt.'},
                {'name': 'Analysis Part 2', 'name_de': 'Analyse Teil 2', 'position': '50-70%', 'part': 2, 'sort_order': 5,
                 'description': 'Zweiter Analyseabschnitt.'},
                {'name': 'Interpretation', 'name_de': 'Interpretation', 'position': '70-85%', 'part': 3, 'sort_order': 6,
                 'description': 'Deutung der Analyseergebnisse.'},
                {'name': 'Conclusion', 'name_de': 'Schluss', 'position': '85-100%', 'part': 3, 'sort_order': 7,
                 'description': 'Zusammenfassung und Erkenntnisse.'},
            ]
        },
    }

    # ==========================================================================
    # FRAMEWORKS FOR SCIENTIFIC PAPERS
    # ==========================================================================
    SCIENTIFIC_FRAMEWORKS = {
        'imrad': {
            'name': 'IMRaD',
            'name_de': 'IMRaD (Empirisch)',
            'description': 'Introduction, Methods, Results, and Discussion - Standard für empirische Arbeiten.',
            'icon': 'bi-journal-text',
            'default_section_count': 11,
            'is_default': True,
            'sort_order': 1,
            'llm_system_prompt': '''Erstelle eine wissenschaftliche Arbeit nach IMRaD-Struktur.
Achte auf präzise Sprache, methodische Stringenz und korrekte Zitation.''',
            'beats': [
                {'name': 'Abstract', 'name_de': 'Abstract', 'position': '0-5%', 'part': 1, 'sort_order': 1,
                 'description': 'Kurze Zusammenfassung der gesamten Arbeit.'},
                {'name': 'Introduction', 'name_de': 'Einleitung', 'position': '5-15%', 'part': 1, 'sort_order': 2,
                 'description': 'Hintergrund, Problemstellung, Forschungslücke.'},
                {'name': 'Research Question', 'name_de': 'Forschungsfrage & Hypothesen', 'position': '15-20%', 'part': 1, 'sort_order': 3,
                 'description': 'Präzise Forschungsfrage und Hypothesen.'},
                {'name': 'Methods - Design', 'name_de': 'Methodik - Design', 'position': '20-30%', 'part': 2, 'sort_order': 4,
                 'description': 'Forschungsdesign und Stichprobe.'},
                {'name': 'Methods - Data Collection', 'name_de': 'Methodik - Datenerhebung', 'position': '30-40%', 'part': 2, 'sort_order': 5,
                 'description': 'Instrumente und Datenerhebung.'},
                {'name': 'Results - Descriptive', 'name_de': 'Ergebnisse - Deskriptiv', 'position': '40-50%', 'part': 2, 'sort_order': 6,
                 'description': 'Deskriptive Statistiken und Befunde.'},
                {'name': 'Results - Inferential', 'name_de': 'Ergebnisse - Inferenzstatistik', 'position': '50-60%', 'part': 2, 'sort_order': 7,
                 'description': 'Hypothesentests und statistische Analysen.'},
                {'name': 'Discussion - Interpretation', 'name_de': 'Diskussion - Interpretation', 'position': '60-75%', 'part': 3, 'sort_order': 8,
                 'description': 'Interpretation der Ergebnisse.'},
                {'name': 'Discussion - Limitations', 'name_de': 'Diskussion - Limitationen', 'position': '75-85%', 'part': 3, 'sort_order': 9,
                 'description': 'Einschränkungen und kritische Reflexion.'},
                {'name': 'Conclusion', 'name_de': 'Fazit', 'position': '85-95%', 'part': 3, 'sort_order': 10,
                 'description': 'Zusammenfassung und Implikationen.'},
                {'name': 'References', 'name_de': 'Literaturverzeichnis', 'position': '95-100%', 'part': 3, 'sort_order': 11,
                 'description': 'Vollständiges Quellenverzeichnis.'},
            ]
        },
        'literature_review': {
            'name': 'Literature Review',
            'name_de': 'Literaturarbeit',
            'description': 'Systematische Aufarbeitung des Forschungsstands.',
            'icon': 'bi-book',
            'default_section_count': 8,
            'is_default': False,
            'sort_order': 2,
            'beats': [
                {'name': 'Introduction', 'name_de': 'Einleitung', 'position': '0-10%', 'part': 1, 'sort_order': 1,
                 'description': 'Thema und Relevanz.'},
                {'name': 'Research Problem', 'name_de': 'Problemstellung', 'position': '10-15%', 'part': 1, 'sort_order': 2,
                 'description': 'Forschungsproblem und Fragen.'},
                {'name': 'Literature Review', 'name_de': 'Forschungsstand', 'position': '15-40%', 'part': 2, 'sort_order': 3,
                 'description': 'Systematische Literaturübersicht.'},
                {'name': 'Theoretical Framework', 'name_de': 'Theoretischer Rahmen', 'position': '40-55%', 'part': 2, 'sort_order': 4,
                 'description': 'Theoretische Einordnung.'},
                {'name': 'Discussion', 'name_de': 'Diskussion', 'position': '55-75%', 'part': 2, 'sort_order': 5,
                 'description': 'Synthese und Diskussion der Literatur.'},
                {'name': 'Critical Evaluation', 'name_de': 'Kritische Würdigung', 'position': '75-85%', 'part': 3, 'sort_order': 6,
                 'description': 'Kritische Bewertung.'},
                {'name': 'Conclusion', 'name_de': 'Fazit & Ausblick', 'position': '85-95%', 'part': 3, 'sort_order': 7,
                 'description': 'Schlussfolgerungen und Forschungsausblick.'},
                {'name': 'References', 'name_de': 'Literaturverzeichnis', 'position': '95-100%', 'part': 3, 'sort_order': 8,
                 'description': 'Quellenverzeichnis.'},
            ]
        },
        'thesis': {
            'name': 'Thesis Structure',
            'name_de': 'Abschlussarbeit',
            'description': 'Umfassende Struktur für Bachelor- und Masterarbeiten.',
            'icon': 'bi-mortarboard',
            'default_section_count': 11,
            'is_default': False,
            'sort_order': 3,
            'beats': [
                {'name': 'Introduction', 'name_de': 'Einleitung & Motivation', 'position': '0-8%', 'part': 1, 'sort_order': 1,
                 'description': 'Motivation und Relevanz des Themas.'},
                {'name': 'Problem Statement', 'name_de': 'Problemstellung & Zielsetzung', 'position': '8-12%', 'part': 1, 'sort_order': 2,
                 'description': 'Problemdefinition und Forschungsziele.'},
                {'name': 'Theoretical Foundations', 'name_de': 'Theoretische Grundlagen', 'position': '12-25%', 'part': 1, 'sort_order': 3,
                 'description': 'Begriffe und theoretischer Rahmen.'},
                {'name': 'State of Research', 'name_de': 'Stand der Forschung', 'position': '25-35%', 'part': 2, 'sort_order': 4,
                 'description': 'Aktueller Forschungsstand.'},
                {'name': 'Methodology', 'name_de': 'Methodik', 'position': '35-45%', 'part': 2, 'sort_order': 5,
                 'description': 'Forschungsmethodik und Vorgehen.'},
                {'name': 'Implementation', 'name_de': 'Durchführung/Analyse', 'position': '45-60%', 'part': 2, 'sort_order': 6,
                 'description': 'Umsetzung und Analyse.'},
                {'name': 'Results', 'name_de': 'Ergebnisse', 'position': '60-75%', 'part': 2, 'sort_order': 7,
                 'description': 'Darstellung der Ergebnisse.'},
                {'name': 'Discussion', 'name_de': 'Diskussion', 'position': '75-85%', 'part': 3, 'sort_order': 8,
                 'description': 'Interpretation und Einordnung.'},
                {'name': 'Conclusion', 'name_de': 'Fazit', 'position': '85-92%', 'part': 3, 'sort_order': 9,
                 'description': 'Zusammenfassung der Erkenntnisse.'},
                {'name': 'Outlook', 'name_de': 'Ausblick', 'position': '92-95%', 'part': 3, 'sort_order': 10,
                 'description': 'Zukünftige Forschung.'},
                {'name': 'Appendix', 'name_de': 'Anhang & Verzeichnisse', 'position': '95-100%', 'part': 3, 'sort_order': 11,
                 'description': 'Anhänge und Verzeichnisse.'},
            ]
        },
    }

    def handle(self, *args, **options):
        self.stdout.write('Setting up Content Type Frameworks...\n')
        
        with transaction.atomic():
            # Create content types
            content_types = {}
            for slug, data in self.CONTENT_TYPES.items():
                ct, created = ContentType.objects.update_or_create(
                    slug=slug,
                    defaults=data
                )
                content_types[slug] = ct
                status = 'Created' if created else 'Updated'
                self.stdout.write(f'  {status} ContentType: {ct.name_de}')
            
            # Create novel frameworks
            self.stdout.write('\n  Creating Novel Frameworks...')
            self._create_frameworks(content_types['novel'], self.NOVEL_FRAMEWORKS)
            
            # Create novella frameworks
            self.stdout.write('\n  Creating Novella Frameworks...')
            self._create_frameworks(content_types['novella'], self.NOVELLA_FRAMEWORKS)
            
            # Create essay frameworks
            self.stdout.write('\n  Creating Essay Frameworks...')
            self._create_frameworks(content_types['essay'], self.ESSAY_FRAMEWORKS)
            
            # Create scientific frameworks
            self.stdout.write('\n  Creating Scientific Frameworks...')
            self._create_frameworks(content_types['scientific'], self.SCIENTIFIC_FRAMEWORKS)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Framework setup complete!'))
        
        # Summary
        ct_count = ContentType.objects.count()
        fw_count = StructureFramework.objects.count()
        beat_count = FrameworkBeat.objects.count()
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  - {ct_count} Content Types')
        self.stdout.write(f'  - {fw_count} Frameworks')
        self.stdout.write(f'  - {beat_count} Beats/Sections')

    def _create_frameworks(self, content_type, frameworks_data):
        """Create frameworks and their beats for a content type"""
        for slug, fw_data in frameworks_data.items():
            beats_data = fw_data.pop('beats', [])
            
            framework, created = StructureFramework.objects.update_or_create(
                content_type=content_type,
                slug=slug,
                defaults=fw_data
            )
            status = 'Created' if created else 'Updated'
            self.stdout.write(f'    {status} Framework: {framework.name_de or framework.name}')
            
            # Create beats
            for beat_data in beats_data:
                llm_prompt = beat_data.pop('llm_prompt', '')
                FrameworkBeat.objects.update_or_create(
                    framework=framework,
                    name=beat_data['name'],
                    defaults={
                        'name_de': beat_data.get('name_de', ''),
                        'description': beat_data.get('description', ''),
                        'position': beat_data.get('position', '0%'),
                        'part': beat_data.get('part', 1),
                        'sort_order': beat_data.get('sort_order', 0),
                        'llm_prompt_template': llm_prompt,
                    }
                )
