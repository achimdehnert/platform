"""
Management command to set up Idea Generation System.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.writing_hub.models import ContentType, IdeaGenerationStep


class Command(BaseCommand):
    help = 'Set up Idea Generation System with ContentTypes and Steps'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete existing steps')

    def handle(self, *args, **options):
        self.stdout.write('\n🎯 Setting up Idea Generation System...\n')
        
        with transaction.atomic():
            content_types = self._create_content_types()
            
            if options['reset']:
                IdeaGenerationStep.objects.all().delete()
            
            for ct in content_types:
                self._create_steps_for_content_type(ct)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Setup complete!\n'))

    def _create_content_types(self):
        """Create ContentTypes for different project types"""
        data = [
            {'slug': 'fairy_tale', 'name': 'Fairy Tale', 'name_de': 'Märchen', 'icon': 'bi-stars',
             'default_word_count': 5000, 'default_section_count': 7, 'section_label': 'Szene', 'sort_order': 10},
            {'slug': 'short_story', 'name': 'Short Story', 'name_de': 'Kurzgeschichte', 'icon': 'bi-journal-text',
             'default_word_count': 8000, 'default_section_count': 5, 'section_label': 'Abschnitt', 'sort_order': 20},
            {'slug': 'novel', 'name': 'Novel', 'name_de': 'Roman', 'icon': 'bi-book',
             'default_word_count': 60000, 'default_section_count': 20, 'has_world_building': True, 'sort_order': 30},
            {'slug': 'complex_novel', 'name': 'Complex Novel', 'name_de': 'Komplexer Roman', 'icon': 'bi-diagram-3',
             'default_word_count': 120000, 'default_section_count': 40, 'has_world_building': True, 'sort_order': 40},
            {'slug': 'essay', 'name': 'Essay', 'name_de': 'Essay', 'icon': 'bi-file-text',
             'default_word_count': 5000, 'has_characters': False, 'has_citations': True, 'sort_order': 50},
        ]
        
        created = []
        for d in data:
            ct, new = ContentType.objects.update_or_create(slug=d['slug'], defaults=d)
            self.stdout.write(f"  {'Created' if new else 'Updated'}: {ct.name_de}")
            created.append(ct)
        return created

    def _create_steps_for_content_type(self, ct):
        """Create IdeaGenerationSteps for a ContentType"""
        steps_map = {
            'fairy_tale': self._fairy_tale_steps(),
            'short_story': self._short_story_steps(),
            'novel': self._novel_steps(),
            'complex_novel': self._novel_steps() + self._complex_additions(),
            'essay': self._essay_steps(),
        }
        
        steps = steps_map.get(ct.slug, [])
        self.stdout.write(f"\n  📝 {len(steps)} steps for {ct.name_de}:")
        
        for s in steps:
            s['content_type'] = ct
            obj, new = IdeaGenerationStep.objects.update_or_create(
                content_type=ct, name=s['name'], defaults=s)
            self.stdout.write(f"    {'✓' if new else '↻'} {s['step_number']}. {s['name_de']}")

    def _fairy_tale_steps(self):
        return [
            {'step_number': 1, 'name': 'moral', 'name_de': 'Moral/Lehre', 'sort_order': 10,
             'question_de': 'Welche Lebenslehre soll vermittelt werden?', 'question': 'What lesson?',
             'help_text_short': 'Jedes Märchen hat eine zeitlose Botschaft.',
             'help_examples': ['Ehrlichkeit währt am längsten', 'Gier führt ins Verderben'],
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 2, 'name': 'protagonist', 'name_de': 'Held/Heldin', 'sort_order': 20,
             'question_de': 'Wer ist die Hauptfigur?', 'question': 'Who is the hero?',
             'help_text_short': 'Typisch: Kinder, einfache Leute, Tiere.',
             'help_examples': ['Ein armes, gutherziges Mädchen', 'Der jüngste von drei Brüdern'],
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 3, 'name': 'antagonist', 'name_de': 'Gegenspieler', 'sort_order': 30,
             'question_de': 'Wer ist das Böse?', 'question': 'Who is the villain?',
             'help_text_short': 'Klassisch: Hexen, Wölfe, böse Stiefmütter.',
             'help_examples': ['Eine neidische Hexe', 'Der große böse Wolf'],
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 4, 'name': 'magic', 'name_de': 'Magisches Element', 'sort_order': 40,
             'question_de': 'Welche Magie kommt vor?', 'question': 'What magic?',
             'help_text_short': 'Wünsche, Verwandlungen, sprechende Tiere.',
             'help_examples': ['Drei Wünsche', 'Ein Zauberspiegel'],
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 5, 'name': 'trials', 'name_de': 'Prüfungen', 'sort_order': 50,
             'question_de': 'Welche drei Prüfungen muss der Held bestehen?', 'question': 'What trials?',
             'help_text_short': 'Dreizahl ist magisch: Drei Aufgaben.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 6, 'name': 'reward', 'name_de': 'Belohnung', 'sort_order': 60,
             'question_de': 'Was gewinnt der Held am Ende?', 'question': 'What reward?',
             'help_text_short': 'Das verdiente Happy End.',
             'help_examples': ['Heirat mit dem Prinzen', 'Ein eigenes Königreich'],
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
        ]

    def _short_story_steps(self):
        return [
            {'step_number': 1, 'name': 'core_conflict', 'name_de': 'Kernkonflikt', 'sort_order': 10,
             'question_de': 'Was ist der zentrale Konflikt in einem Satz?', 'question': 'Core conflict?',
             'help_text_short': 'EIN zentrales Problem.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 2, 'name': 'protagonist', 'name_de': 'Protagonist', 'sort_order': 20,
             'question_de': 'Wer erlebt die Geschichte?', 'question': 'Who experiences it?',
             'help_text_short': 'Wenige, gut gezeichnete Charaktere.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 3, 'name': 'setting', 'name_de': 'Setting', 'sort_order': 30,
             'question_de': 'Wo und wann spielt die Geschichte?', 'question': 'Where/when?',
             'help_text_short': 'Ein konkreter Ort, eine konkrete Zeit.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 4, 'name': 'turning_point', 'name_de': 'Wendepunkt', 'sort_order': 40,
             'question_de': 'Was verändert alles?', 'question': 'What changes everything?',
             'help_text_short': 'Der Moment ohne Zurück.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 5, 'name': 'ending', 'name_de': 'Ende', 'sort_order': 50,
             'question_de': 'Wie endet die Geschichte?', 'question': 'How does it end?',
             'input_type': 'select', 'input_options': {'options': [
                 {'value': 'open', 'label': 'Offen'}, {'value': 'twist', 'label': 'Twist'},
                 {'value': 'tragic', 'label': 'Tragisch'}, {'value': 'hopeful', 'label': 'Hoffnungsvoll'}
             ]}, 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 6, 'name': 'emotion', 'name_de': 'Emotionaler Kern', 'sort_order': 60,
             'question_de': 'Welches Gefühl soll der Leser haben?', 'question': 'What feeling?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
        ]

    def _novel_steps(self):
        return [
            {'step_number': 1, 'name': 'premise', 'name_de': 'Prämisse', 'sort_order': 10,
             'question_de': 'Worum geht es in einem Satz?', 'question': 'What is it about?',
             'help_text_short': 'Der Elevator Pitch.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 2, 'name': 'genre', 'name_de': 'Genre & Ton', 'sort_order': 20,
             'question_de': 'Welches Genre und welcher Ton?', 'question': 'Genre and tone?',
             'input_type': 'multiselect', 'input_options': {'options': [
                 {'value': 'fantasy', 'label': 'Fantasy'}, {'value': 'scifi', 'label': 'Sci-Fi'},
                 {'value': 'romance', 'label': 'Romance'}, {'value': 'thriller', 'label': 'Thriller'},
                 {'value': 'crime', 'label': 'Krimi'}, {'value': 'literary', 'label': 'Literarisch'}
             ]}, 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 3, 'name': 'protagonist', 'name_de': 'Hauptfigur', 'sort_order': 30,
             'question_de': 'Wer ist deine Hauptfigur?', 'question': 'Who is the protagonist?',
             'help_text_short': 'Ziel, innerer Konflikt, Stärken, Schwächen.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 4, 'name': 'conflict', 'name_de': 'Zentraler Konflikt', 'sort_order': 40,
             'question_de': 'Extern und intern?', 'question': 'External and internal conflict?',
             'help_text_short': 'Äußeres Problem + innerer Kampf.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 5, 'name': 'supporting', 'name_de': 'Nebenfiguren', 'sort_order': 50,
             'question_de': 'Wichtige Nebenfiguren?', 'question': 'Supporting characters?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 6, 'name': 'themes', 'name_de': 'Themen', 'sort_order': 60,
             'question_de': 'Welche Themen behandelt der Roman?', 'question': 'What themes?',
             'input_type': 'tags', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 7, 'name': 'setting', 'name_de': 'Setting/Welt', 'sort_order': 70,
             'question_de': 'Wo und wann spielt die Geschichte?', 'question': 'Setting?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 8, 'name': 'structure', 'name_de': 'Handlungsbögen', 'sort_order': 80,
             'question_de': 'Grobe Struktur (3 Akte)?', 'question': 'Story structure?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 9, 'name': 'subplots', 'name_de': 'Nebenhandlungen', 'sort_order': 90,
             'question_de': 'Welche Subplots bereichern die Geschichte?', 'question': 'Subplots?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': False},
        ]

    def _complex_additions(self):
        return [
            {'step_number': 10, 'name': 'pov', 'name_de': 'POV-Strategie', 'sort_order': 100,
             'question_de': 'Wer erzählt aus welcher Perspektive?', 'question': 'POV strategy?',
             'help_text_short': 'Multiple POVs für komplexe Erzählungen.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 11, 'name': 'worldbuilding', 'name_de': 'Weltenbau-Details', 'sort_order': 110,
             'question_de': 'Magie, Politik, Religion, Geschichte?', 'question': 'World systems?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 12, 'name': 'factions', 'name_de': 'Fraktionen', 'sort_order': 120,
             'question_de': 'Welche Gruppen gibt es?', 'question': 'What factions?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 13, 'name': 'timeline', 'name_de': 'Timeline', 'sort_order': 130,
             'question_de': 'Chronologie vs. Erzählstruktur?', 'question': 'Timeline structure?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 14, 'name': 'secrets', 'name_de': 'Verborgene Zusammenhänge', 'sort_order': 140,
             'question_de': 'Was wird erst später enthüllt?', 'question': 'Hidden connections?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': False},
            {'step_number': 15, 'name': 'symbolism', 'name_de': 'Symbolik & Motive', 'sort_order': 150,
             'question_de': 'Wiederkehrende Symbole?', 'question': 'Recurring symbols?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': False},
        ]

    def _essay_steps(self):
        return [
            {'step_number': 1, 'name': 'thesis', 'name_de': 'These', 'sort_order': 10,
             'question_de': 'Was ist deine Hauptaussage?', 'question': 'What is your thesis?',
             'help_text_short': 'Eine klare, vertretbare Position.',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 2, 'name': 'counterpoint', 'name_de': 'Gegenposition', 'sort_order': 20,
             'question_de': 'Was sagen Kritiker?', 'question': 'What do critics say?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 3, 'name': 'arguments', 'name_de': 'Argumente', 'sort_order': 30,
             'question_de': 'Welche 3-5 Argumente stützen deine These?', 'question': 'Arguments?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 4, 'name': 'evidence', 'name_de': 'Beweise', 'sort_order': 40,
             'question_de': 'Quellen, Studien, Beispiele?', 'question': 'Evidence?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 5, 'name': 'structure', 'name_de': 'Struktur', 'sort_order': 50,
             'question_de': 'Wie baust du die Argumentation auf?', 'question': 'Structure?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
            {'step_number': 6, 'name': 'cta', 'name_de': 'Call to Action', 'sort_order': 60,
             'question_de': 'Was soll der Leser tun/denken?', 'question': 'Call to action?',
             'input_type': 'textarea', 'can_generate_with_ai': True, 'is_required': True},
        ]
