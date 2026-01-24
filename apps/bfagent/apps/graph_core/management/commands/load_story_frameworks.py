"""
Management command to load built-in story frameworks into the database.

Usage:
    python manage.py load_story_frameworks
    python manage.py load_story_frameworks --clear  # Clear existing first
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from apps.graph_core.models import Framework, FrameworkPhase, FrameworkStep, NodeType, EdgeType


class Command(BaseCommand):
    help = 'Load built-in story frameworks (Save the Cat, Hero\'s Journey, Three-Act)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing story frameworks before loading',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing story frameworks...')
            Framework.objects.filter(domain='story').delete()
            NodeType.objects.filter(domain='story').delete()
            EdgeType.objects.filter(domain='story').delete()

        self.load_node_types()
        self.load_edge_types()
        self.load_save_the_cat()
        self.load_heros_journey()
        self.load_three_act()

        self.stdout.write(self.style.SUCCESS('Successfully loaded story frameworks!'))

    def load_node_types(self):
        """Load story-related node types"""
        node_types = [
            {'name': 'character', 'display_name': 'Character', 'icon': 'person', 'color': '#3B82F6', 'shape': 'ellipse'},
            {'name': 'location', 'display_name': 'Location', 'icon': 'geo-alt', 'color': '#10B981', 'shape': 'round-rectangle'},
            {'name': 'event', 'display_name': 'Event', 'icon': 'calendar-event', 'color': '#F59E0B', 'shape': 'diamond'},
            {'name': 'object', 'display_name': 'Object/Item', 'icon': 'box', 'color': '#8B5CF6', 'shape': 'rectangle'},
            {'name': 'faction', 'display_name': 'Faction/Group', 'icon': 'people', 'color': '#EC4899', 'shape': 'hexagon'},
            {'name': 'concept', 'display_name': 'Concept/Theme', 'icon': 'lightbulb', 'color': '#6366F1', 'shape': 'octagon'},
        ]
        
        for nt_data in node_types:
            NodeType.objects.update_or_create(
                name=nt_data['name'],
                defaults={
                    'display_name': nt_data['display_name'],
                    'domain': 'story',
                    'icon': nt_data['icon'],
                    'color': nt_data['color'],
                    'shape': nt_data['shape'],
                }
            )
        self.stdout.write(f'  Created {len(node_types)} node types')

    def load_edge_types(self):
        """Load story-related edge types"""
        edge_types = [
            {'name': 'loves', 'display_name': 'Loves', 'color': '#EC4899', 'directed': True},
            {'name': 'hates', 'display_name': 'Hates', 'color': '#EF4444', 'directed': True},
            {'name': 'knows', 'display_name': 'Knows', 'color': '#6B7280', 'directed': False},
            {'name': 'related_to', 'display_name': 'Related To', 'color': '#8B5CF6', 'directed': False},
            {'name': 'located_at', 'display_name': 'Located At', 'color': '#10B981', 'directed': True},
            {'name': 'owns', 'display_name': 'Owns', 'color': '#F59E0B', 'directed': True},
            {'name': 'causes', 'display_name': 'Causes', 'color': '#3B82F6', 'directed': True},
            {'name': 'member_of', 'display_name': 'Member Of', 'color': '#EC4899', 'directed': True},
            {'name': 'opposes', 'display_name': 'Opposes', 'color': '#EF4444', 'directed': False},
            {'name': 'allies_with', 'display_name': 'Allies With', 'color': '#10B981', 'directed': False},
        ]
        
        for et_data in edge_types:
            EdgeType.objects.update_or_create(
                name=et_data['name'],
                defaults={
                    'display_name': et_data['display_name'],
                    'domain': 'story',
                    'color': et_data['color'],
                    'is_directed': et_data['directed'],
                }
            )
        self.stdout.write(f'  Created {len(edge_types)} edge types')

    def load_save_the_cat(self):
        """Load Save the Cat Beat Sheet framework"""
        fw, created = Framework.objects.update_or_create(
            slug='save-the-cat',
            defaults={
                'name': 'Save the Cat',
                'display_name': 'Save the Cat Beat Sheet',
                'description': 'Blake Snyder\'s 15-beat story structure, the most widely used story framework in Hollywood.',
                'domain': 'story',
                'icon': 'film',
                'color': 'warning',
                'is_default': True,
            }
        )
        
        # Define phases and steps
        phases_data = [
            {
                'name': 'Act 1 - Setup',
                'order': 0,
                'position_start': 0.0,
                'position_end': 0.25,
                'color': '#3B82F6',
                'guidance': 'Establish the world, introduce the hero, show what\'s missing.',
                'steps': [
                    {'name': 'Opening Image', 'order': 0, 'position': 0.0, 'chapters': 1, 'guidance': 'A visual that represents the starting point. Sets tone and mood.'},
                    {'name': 'Theme Stated', 'order': 1, 'position': 0.05, 'chapters': 1, 'guidance': 'Someone (usually not the hero) states the theme or moral.'},
                    {'name': 'Set-Up', 'order': 2, 'position': 0.10, 'chapters': 2, 'guidance': 'Introduce hero, their world, and "6 things that need fixing".'},
                    {'name': 'Catalyst', 'order': 3, 'position': 0.12, 'chapters': 1, 'guidance': 'The inciting incident. Life will never be the same.'},
                    {'name': 'Debate', 'order': 4, 'position': 0.17, 'chapters': 2, 'guidance': 'Hero debates: should I go? Can I do it? What about...?'},
                ]
            },
            {
                'name': 'Act 2A - Fun & Games',
                'order': 1,
                'position_start': 0.25,
                'position_end': 0.50,
                'color': '#10B981',
                'guidance': 'The promise of the premise. What the audience came to see.',
                'steps': [
                    {'name': 'Break into Two', 'order': 0, 'position': 0.25, 'chapters': 1, 'guidance': 'Hero makes a choice and enters the "upside-down" world of Act 2.'},
                    {'name': 'B Story', 'order': 1, 'position': 0.30, 'chapters': 1, 'guidance': 'The love story or friendship. Often carries the theme.'},
                    {'name': 'Fun and Games', 'order': 2, 'position': 0.35, 'chapters': 3, 'guidance': 'The heart of the movie. Deliver on the premise!'},
                ]
            },
            {
                'name': 'Act 2B - Bad Guys Close In',
                'order': 2,
                'position_start': 0.50,
                'position_end': 0.75,
                'color': '#F59E0B',
                'guidance': 'Internal and external pressures mount. Things get worse.',
                'steps': [
                    {'name': 'Midpoint', 'order': 0, 'position': 0.50, 'chapters': 1, 'guidance': 'False victory or false defeat. Stakes are raised. No going back.'},
                    {'name': 'Bad Guys Close In', 'order': 1, 'position': 0.55, 'chapters': 3, 'guidance': 'External: bad guys regroup. Internal: team fractures.'},
                    {'name': 'All Is Lost', 'order': 2, 'position': 0.70, 'chapters': 1, 'guidance': 'The opposite of the midpoint. The lowest point. "Whiff of death".'},
                    {'name': 'Dark Night of the Soul', 'order': 3, 'position': 0.72, 'chapters': 2, 'guidance': 'Hero processes the loss. Mourns. Beats himself up.'},
                ]
            },
            {
                'name': 'Act 3 - Resolution',
                'order': 3,
                'position_start': 0.75,
                'position_end': 1.0,
                'color': '#EC4899',
                'guidance': 'Hero synthesizes what they\'ve learned and wins.',
                'steps': [
                    {'name': 'Break into Three', 'order': 0, 'position': 0.75, 'chapters': 1, 'guidance': 'Eureka! The A and B stories combine. Hero has the solution.'},
                    {'name': 'Finale', 'order': 1, 'position': 0.80, 'chapters': 3, 'guidance': 'Execution of the new plan. Hero proves change. Bad guys defeated.'},
                    {'name': 'Final Image', 'order': 2, 'position': 0.99, 'chapters': 1, 'guidance': 'Opposite of Opening Image. Proof of change. The new world.'},
                ]
            },
        ]
        
        self._create_phases_and_steps(fw, phases_data)
        self.stdout.write(f'  {"Created" if created else "Updated"} Save the Cat framework')

    def load_heros_journey(self):
        """Load Hero's Journey framework"""
        fw, created = Framework.objects.update_or_create(
            slug='heros-journey',
            defaults={
                'name': 'Hero\'s Journey',
                'display_name': 'Hero\'s Journey (Monomyth)',
                'description': 'Joseph Campbell\'s 12-stage monomyth structure found in myths across cultures.',
                'domain': 'story',
                'icon': 'compass',
                'color': 'primary',
            }
        )
        
        phases_data = [
            {
                'name': 'Departure',
                'order': 0,
                'position_start': 0.0,
                'position_end': 0.33,
                'color': '#3B82F6',
                'guidance': 'The hero leaves the ordinary world.',
                'steps': [
                    {'name': 'Ordinary World', 'order': 0, 'position': 0.0, 'chapters': 1, 'guidance': 'Hero\'s normal life before the adventure begins.'},
                    {'name': 'Call to Adventure', 'order': 1, 'position': 0.08, 'chapters': 1, 'guidance': 'Hero is presented with a problem or challenge.'},
                    {'name': 'Refusal of the Call', 'order': 2, 'position': 0.12, 'chapters': 1, 'guidance': 'Hero hesitates or refuses the call due to fear.'},
                    {'name': 'Meeting the Mentor', 'order': 3, 'position': 0.17, 'chapters': 1, 'guidance': 'Hero meets a guide who provides advice or tools.'},
                    {'name': 'Crossing the Threshold', 'order': 4, 'position': 0.25, 'chapters': 1, 'guidance': 'Hero commits to the adventure and enters the special world.'},
                ]
            },
            {
                'name': 'Initiation',
                'order': 1,
                'position_start': 0.33,
                'position_end': 0.66,
                'color': '#F59E0B',
                'guidance': 'The hero faces tests and transforms.',
                'steps': [
                    {'name': 'Tests, Allies, Enemies', 'order': 0, 'position': 0.35, 'chapters': 3, 'guidance': 'Hero learns the rules of the special world.'},
                    {'name': 'Approach to the Inmost Cave', 'order': 1, 'position': 0.45, 'chapters': 1, 'guidance': 'Hero prepares for the major challenge.'},
                    {'name': 'Ordeal', 'order': 2, 'position': 0.50, 'chapters': 2, 'guidance': 'Hero faces their greatest fear or enemy.'},
                    {'name': 'Reward', 'order': 3, 'position': 0.60, 'chapters': 1, 'guidance': 'Hero survives and receives the treasure.'},
                ]
            },
            {
                'name': 'Return',
                'order': 2,
                'position_start': 0.66,
                'position_end': 1.0,
                'color': '#10B981',
                'guidance': 'The hero returns home transformed.',
                'steps': [
                    {'name': 'The Road Back', 'order': 0, 'position': 0.70, 'chapters': 1, 'guidance': 'Hero begins the journey back to the ordinary world.'},
                    {'name': 'Resurrection', 'order': 1, 'position': 0.85, 'chapters': 2, 'guidance': 'Final battle. Hero must use everything learned.'},
                    {'name': 'Return with the Elixir', 'order': 2, 'position': 0.95, 'chapters': 1, 'guidance': 'Hero returns home with the "treasure" to share.'},
                ]
            },
        ]
        
        self._create_phases_and_steps(fw, phases_data)
        self.stdout.write(f'  {"Created" if created else "Updated"} Hero\'s Journey framework')

    def load_three_act(self):
        """Load Three-Act Structure framework"""
        fw, created = Framework.objects.update_or_create(
            slug='three-act-structure',
            defaults={
                'name': 'Three-Act Structure',
                'display_name': 'Three-Act Structure',
                'description': 'The classic beginning-middle-end structure used since Aristotle.',
                'domain': 'story',
                'icon': 'list-ol',
                'color': 'info',
            }
        )
        
        phases_data = [
            {
                'name': 'Act 1 - Setup',
                'order': 0,
                'position_start': 0.0,
                'position_end': 0.25,
                'color': '#3B82F6',
                'guidance': 'Introduce characters, setting, and the central conflict.',
                'steps': [
                    {'name': 'Exposition', 'order': 0, 'position': 0.0, 'chapters': 2, 'guidance': 'Introduce the world, characters, and status quo.'},
                    {'name': 'Inciting Incident', 'order': 1, 'position': 0.10, 'chapters': 1, 'guidance': 'The event that disrupts the status quo.'},
                    {'name': 'Plot Point 1', 'order': 2, 'position': 0.22, 'chapters': 1, 'guidance': 'The turning point that launches into Act 2.'},
                ]
            },
            {
                'name': 'Act 2 - Confrontation',
                'order': 1,
                'position_start': 0.25,
                'position_end': 0.75,
                'color': '#F59E0B',
                'guidance': 'Rising action. Obstacles and complications.',
                'steps': [
                    {'name': 'Rising Action', 'order': 0, 'position': 0.30, 'chapters': 3, 'guidance': 'Hero faces obstacles and complications.'},
                    {'name': 'Midpoint', 'order': 1, 'position': 0.50, 'chapters': 1, 'guidance': 'Major revelation or reversal. Stakes increase.'},
                    {'name': 'Crisis', 'order': 2, 'position': 0.65, 'chapters': 2, 'guidance': 'Things get worse. Hero at lowest point.'},
                    {'name': 'Plot Point 2', 'order': 3, 'position': 0.72, 'chapters': 1, 'guidance': 'The turning point into Act 3.'},
                ]
            },
            {
                'name': 'Act 3 - Resolution',
                'order': 2,
                'position_start': 0.75,
                'position_end': 1.0,
                'color': '#10B981',
                'guidance': 'Climax and resolution of the story.',
                'steps': [
                    {'name': 'Climax', 'order': 0, 'position': 0.85, 'chapters': 2, 'guidance': 'The final confrontation. Maximum tension.'},
                    {'name': 'Denouement', 'order': 1, 'position': 0.95, 'chapters': 1, 'guidance': 'Resolution. New normal established.'},
                ]
            },
        ]
        
        self._create_phases_and_steps(fw, phases_data)
        self.stdout.write(f'  {"Created" if created else "Updated"} Three-Act Structure framework')

    def _create_phases_and_steps(self, framework, phases_data):
        """Helper to create phases and steps for a framework"""
        for phase_data in phases_data:
            phase, _ = FrameworkPhase.objects.update_or_create(
                framework=framework,
                slug=slugify(phase_data['name']),
                defaults={
                    'name': phase_data['name'],
                    'order': phase_data['order'],
                    'position_start': phase_data['position_start'],
                    'position_end': phase_data['position_end'],
                    'color': phase_data['color'],
                    'guidance': phase_data.get('guidance', ''),
                }
            )
            
            for step_data in phase_data['steps']:
                FrameworkStep.objects.update_or_create(
                    phase=phase,
                    slug=slugify(step_data['name']),
                    defaults={
                        'name': step_data['name'],
                        'order': step_data['order'],
                        'typical_position': step_data['position'],
                        'estimated_chapters': step_data.get('chapters', 1),
                        'chapter_guidance': step_data.get('guidance', ''),
                    }
                )
