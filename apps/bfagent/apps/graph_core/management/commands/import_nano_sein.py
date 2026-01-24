"""
Management Command: Import NANO-SEIN Book Project from YAML files

Creates:
- Custom Framework "Vier-Schichten-Architektur"
- BookProject with chapters
- Graph nodes for characters and relationships
"""
import os
import yaml
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.db import transaction

from apps.graph_core.models import (
    Framework, FrameworkPhase, FrameworkStep,
    NodeType, EdgeType, GraphNode, GraphEdge,
    ProjectFramework
)
from apps.bfagent.models import BookProjects


User = get_user_model()

YAML_DIR = Path('docs/graphen/books/erwachen')


class Command(BaseCommand):
    help = 'Import NANO-SEIN book project from YAML files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yaml-dir',
            type=str,
            default=str(YAML_DIR),
            help='Directory containing YAML files'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Username for created objects'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without saving'
        )

    def handle(self, *args, **options):
        self.yaml_dir = Path(options['yaml_dir'])
        self.dry_run = options['dry_run']
        self.verbosity = options['verbosity']
        
        # Get or create user
        try:
            self.user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            self.user = User.objects.first()
            if not self.user:
                self.stderr.write(self.style.ERROR('No users found!'))
                return
        
        self.stdout.write(f'Using user: {self.user.username}')
        self.stdout.write(f'YAML directory: {self.yaml_dir}')
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - nothing will be saved'))
        
        with transaction.atomic():
            # Step 1: Create Framework
            framework = self.create_framework()
            
            # Step 2: Create NodeTypes and EdgeTypes
            node_types, edge_types = self.create_graph_types()
            
            # Step 3: Create BookProject
            project = self.create_book_project()
            
            # Step 4: Link Project to Framework
            if framework and project:
                self.link_project_framework(project, framework)
            
            # Step 5: Create Chapters from YAML
            if project:
                self.create_chapters(project)
            
            # Step 6: Create Graph Nodes for Characters
            if project and node_types:
                self.create_character_nodes(project, node_types, edge_types)
            
            if self.dry_run:
                raise Exception('DRY RUN - rolling back')
        
        self.stdout.write(self.style.SUCCESS('Import completed!'))

    def load_yaml(self, filename):
        """Load a YAML file from the yaml_dir"""
        filepath = self.yaml_dir / filename
        if not filepath.exists():
            self.stderr.write(f'File not found: {filepath}')
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def create_framework(self):
        """Create the Vier-Schichten-Architektur framework"""
        self.stdout.write('Creating Framework: Vier-Schichten-Architektur...')
        
        # Load structure for layer info
        structure = self.load_yaml('book_1_structure.yaml')
        if not structure:
            return None
        
        layers = structure.get('book_1', {}).get('layer_architecture', {})
        
        framework, created = Framework.objects.update_or_create(
            slug='vier-schichten-architektur',
            defaults={
                'name': 'vier-schichten-architektur',
                'display_name': 'Vier-Schichten-Architektur',
                'description': 'Multi-Layer Story Framework: Thriller + Romance + Soft-SciFi + Mystik. Jede Schicht trägt zur Gesamterzählung bei.',
                'domain': 'story',
                'icon': 'layers',
                'color': '#6366f1',
                'is_active': True,
                'config': {
                    'source': 'NANO-SEIN',
                    'author': 'Custom',
                    'layers': list(layers.keys())
                }
            }
        )
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'  {action} Framework: {framework.display_name}')
        
        # Create Phases for each layer
        phase_data = [
            {
                'name': 'Thriller-Schicht',
                'slug': 'thriller',
                'description': layers.get('thriller', {}).get('focus', 'Bedrohung, Mystery, Stakes'),
                'order': 1,
                'color': '#ef4444',
                'position_start': 0,
                'position_end': 30,
            },
            {
                'name': 'Romance-Schicht',
                'slug': 'romance',
                'description': layers.get('romance', {}).get('focus', 'Beziehung, Vertrauen, Intimität'),
                'order': 2,
                'color': '#ec4899',
                'position_start': 0,
                'position_end': 25,
            },
            {
                'name': 'Soft-SciFi-Schicht',
                'slug': 'soft-scifi',
                'description': layers.get('soft_scifi', {}).get('focus', 'Gesellschaft, Ethik, Konsequenzen'),
                'order': 3,
                'color': '#3b82f6',
                'position_start': 0,
                'position_end': 30,
            },
            {
                'name': 'Mystik-Schicht',
                'slug': 'mystik',
                'description': layers.get('mystik', {}).get('focus', 'Transzendenz, Staunen, das Numinose'),
                'order': 4,
                'color': '#8b5cf6',
                'position_start': 0,
                'position_end': 25,
            },
        ]
        
        for pd in phase_data:
            phase, created = FrameworkPhase.objects.update_or_create(
                framework=framework,
                slug=pd['slug'],
                defaults={
                    'name': pd['name'],
                    'description': pd['description'],
                    'order': pd['order'],
                    'color': pd['color'],
                    'position_start': pd['position_start'],
                    'position_end': pd['position_end'],
                }
            )
            self.stdout.write(f'    Phase: {phase.name}')
            
            # Create steps for each phase based on layer elements
            layer_key = pd['slug'].replace('-', '_')
            layer_info = layers.get(layer_key, {})
            elements = layer_info.get('elements', [])
            
            for i, element in enumerate(elements, 1):
                step, _ = FrameworkStep.objects.update_or_create(
                    phase=phase,
                    slug=slugify(element[:50]),
                    defaults={
                        'name': element[:100],
                        'description': element,
                        'order': i,
                    }
                )
        
        # Add Act Structure as additional phases
        acts = structure.get('book_1', {})
        act_phases = [
            ('act_1', 'Akt 1: RISSE', 'Etablierung, erste Projektionen, Beobachter', 5, '#22c55e', 0, 30),
            ('act_2', 'Akt 2: SPALTUNG', 'Vertiefung, Eskalation, Midpoint', 6, '#eab308', 30, 70),
            ('act_3', 'Akt 3: SYNTHESE', 'Höhepunkt, Konfrontation, offenes Ende', 7, '#f97316', 70, 100),
        ]
        
        for slug, name, desc, order, color, start, end in act_phases:
            act_data = acts.get(slug, {})
            phase, _ = FrameworkPhase.objects.update_or_create(
                framework=framework,
                slug=slug,
                defaults={
                    'name': name,
                    'description': act_data.get('goals', [desc])[0] if act_data.get('goals') else desc,
                    'order': order,
                    'color': color,
                    'position_start': start,
                    'position_end': end,
                }
            )
            self.stdout.write(f'    Phase: {phase.name}')
            
            # Add goals as steps
            goals = act_data.get('goals', [])
            for i, goal in enumerate(goals, 1):
                step, _ = FrameworkStep.objects.update_or_create(
                    phase=phase,
                    slug=slugify(goal[:50]),
                    defaults={
                        'name': goal[:100],
                        'description': goal,
                        'order': i,
                    }
                )
        
        return framework

    def create_graph_types(self):
        """Create NodeTypes and EdgeTypes for story domain"""
        self.stdout.write('Creating Graph Types...')
        
        node_types_data = [
            ('character', 'Charakter', 'bi-person', '#3b82f6', {'category': 'story'}),
            ('location', 'Ort', 'bi-geo-alt', '#22c55e', {'category': 'story'}),
            ('theme', 'Thema', 'bi-lightbulb', '#eab308', {'category': 'story'}),
            ('plotthread', 'Handlungsstrang', 'bi-diagram-3', '#8b5cf6', {'category': 'story'}),
            ('bloodline', 'Blutlinie', 'bi-tree', '#ef4444', {'category': 'mythology'}),
            ('faction', 'Fraktion', 'bi-people', '#ec4899', {'category': 'mythology'}),
            ('mythology', 'Mythologie', 'bi-stars', '#6366f1', {'category': 'mythology'}),
        ]
        
        node_types = {}
        for code, name, icon, color, config in node_types_data:
            nt, created = NodeType.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'icon': icon,
                    'color': color,
                    'config': config,
                }
            )
            node_types[code] = nt
            self.stdout.write(f'  NodeType: {nt.name}')
        
        edge_types_data = [
            ('loves', 'liebt', '#ec4899', {'category': 'relationship'}),
            ('hates', 'hasst', '#ef4444', {'category': 'relationship'}),
            ('mentors', 'mentor von', '#22c55e', {'category': 'relationship'}),
            ('conflicts_with', 'Konflikt mit', '#f97316', {'category': 'relationship'}),
            ('bloodline_to', 'Blutlinie zu', '#8b5cf6', {'category': 'heritage'}),
            ('foreshadows', 'deutet an', '#6366f1', {'category': 'narrative'}),
            ('mirrors', 'spiegelt', '#3b82f6', {'category': 'narrative'}),
            ('belongs_to', 'gehört zu', '#64748b', {'category': 'membership'}),
        ]
        
        edge_types = {}
        for code, name, color, config in edge_types_data:
            et, created = EdgeType.objects.update_or_create(
                code=code,
                defaults={
                    'name': name,
                    'color': color,
                    'config': config,
                }
            )
            edge_types[code] = et
            self.stdout.write(f'  EdgeType: {et.name}')
        
        return node_types, edge_types

    def create_book_project(self):
        """Create the BookProject for NANO-SEIN: Erwachen"""
        self.stdout.write('Creating BookProject...')
        
        structure = self.load_yaml('book_1_structure.yaml')
        story_graph = self.load_yaml('story_graph_export.yaml')
        
        if not structure:
            return None
        
        book_info = structure.get('book_1', {})
        meta = story_graph.get('meta', {}) if story_graph else {}
        
        project, created = BookProjects.objects.update_or_create(
            title='NANO-SEIN: Erwachen',
            defaults={
                'description': f"Buch 1 der NANO-SEIN Serie. {book_info.get('estimated_length', '85.000-95.000 Wörter')}, {book_info.get('chapters', 32)} Kapitel.",
                'genre': meta.get('genre', {}).get('primary', 'Speculative Fiction'),
                'target_audience': ', '.join(meta.get('target_audience', {}).get('secondary', ['Erwachsene'])),
                'status': 'planning',
            }
        )
        
        action = 'Created' if created else 'Updated'
        self.stdout.write(f'  {action} BookProject: {project.title}')
        
        return project

    def link_project_framework(self, project, framework):
        """Link project to framework"""
        self.stdout.write('Linking Project to Framework...')
        
        pf, created = ProjectFramework.objects.update_or_create(
            project=project,
            framework=framework,
            defaults={
                'is_primary': True,
            }
        )
        if created:
            pf.start()
        
        self.stdout.write(f'  Linked: {project.title} → {framework.display_name}')

    def create_chapters(self, project):
        """Create chapters from YAML files"""
        self.stdout.write('Creating Chapters...')
        
        # Import Chapter model
        try:
            from apps.writing_hub.models import Chapter
        except ImportError:
            self.stderr.write('Could not import Chapter model')
            return
        
        chapter_files = [
            'book_1_chapters_01_08.yaml',
            'book_1_chapters_09_16.yaml',
            'book_1_chapters_17_24.yaml',
            'book_1_chapters_25_32.yaml',
        ]
        
        chapter_count = 0
        for filename in chapter_files:
            data = self.load_yaml(filename)
            if not data:
                continue
            
            for key, chapter_data in data.items():
                if not key.startswith('chapter_'):
                    continue
                
                chapter_num = int(key.split('_')[1])
                title = chapter_data.get('title', f'Kapitel {chapter_num}')
                pov = chapter_data.get('pov', '')
                word_count = chapter_data.get('word_count_target', '2500-3000')
                
                # Build content from scenes
                scenes = chapter_data.get('scenes', {})
                content_parts = []
                for scene_key, scene_data in scenes.items():
                    if isinstance(scene_data, dict):
                        scene_title = scene_data.get('title', scene_key)
                        beats = scene_data.get('beats', [])
                        content_parts.append(f"### {scene_title}\n")
                        for beat in beats:
                            content_parts.append(f"- {beat}")
                        content_parts.append("")
                
                content = '\n'.join(content_parts) if content_parts else ''
                
                # Extract layer focus
                layer_focus = chapter_data.get('layer_focus', {})
                notes = f"POV: {pov}\nWord Count: {word_count}\n"
                notes += f"Primary Layer: {layer_focus.get('primary', 'N/A')}\n"
                notes += f"Secondary Layer: {layer_focus.get('secondary', 'N/A')}"
                
                chapter, created = Chapter.objects.update_or_create(
                    book=project,
                    chapter_number=chapter_num,
                    defaults={
                        'title': title,
                        'content': content,
                        'notes': notes,
                        'status': 'outline',
                        'word_count': 0,  # Will be calculated
                    }
                )
                chapter_count += 1
                
                if self.verbosity >= 2:
                    self.stdout.write(f'  Chapter {chapter_num}: {title}')
        
        self.stdout.write(f'  Created/Updated {chapter_count} chapters')

    def create_character_nodes(self, project, node_types, edge_types):
        """Create graph nodes for characters"""
        self.stdout.write('Creating Character Nodes...')
        
        story_graph = self.load_yaml('story_graph_export.yaml')
        if not story_graph:
            return
        
        characters = story_graph.get('characters', {})
        character_nt = node_types.get('character')
        bloodline_nt = node_types.get('bloodline')
        faction_nt = node_types.get('faction')
        
        if not character_nt:
            return
        
        created_nodes = {}
        
        # Create protagonist nodes
        for char_key, char_data in characters.get('protagonists', {}).items():
            node, created = GraphNode.objects.update_or_create(
                project=project,
                node_type=character_nt,
                name=char_data.get('role', char_key.replace('_', ' ').title()),
                defaults={
                    'properties': {
                        'profession': char_data.get('profession', ''),
                        'age': char_data.get('age', 0),
                        'role': char_data.get('role', ''),
                        'internal_conflict': char_data.get('internal_conflict', ''),
                        'arc': char_data.get('arc', {}),
                    }
                }
            )
            created_nodes[char_key] = node
            self.stdout.write(f'  Character: {node.name}')
        
        # Create antagonist nodes
        for char_key, char_data in characters.get('antagonists', {}).items():
            node, created = GraphNode.objects.update_or_create(
                project=project,
                node_type=character_nt,
                name=char_data.get('name', char_key.replace('_', ' ').title()),
                defaults={
                    'properties': {
                        'role': char_data.get('role', 'Antagonist'),
                        'organization': char_data.get('organization', ''),
                        'motivation': char_data.get('motivation', ''),
                    }
                }
            )
            created_nodes[char_key] = node
            self.stdout.write(f'  Antagonist: {node.name}')
        
        # Create mythology nodes
        mythology = story_graph.get('mythology', {})
        if mythology and faction_nt:
            factions = mythology.get('factions', {})
            for faction_key, faction_data in factions.items():
                node, created = GraphNode.objects.update_or_create(
                    project=project,
                    node_type=faction_nt,
                    name=faction_key.upper(),
                    defaults={
                        'properties': {
                            'principle': faction_data.get('principle', ''),
                            'method': faction_data.get('method', ''),
                            'goal': faction_data.get('goal', ''),
                            'danger': faction_data.get('danger', ''),
                        }
                    }
                )
                created_nodes[faction_key] = node
                self.stdout.write(f'  Faction: {node.name}')
        
        # Create relationships
        loves_et = edge_types.get('loves')
        mentors_et = edge_types.get('mentors')
        conflicts_et = edge_types.get('conflicts_with')
        
        if 'lena_vogt' in created_nodes and 'david_khouri' in created_nodes and loves_et:
            edge, _ = GraphEdge.objects.update_or_create(
                project=project,
                source=created_nodes['lena_vogt'],
                target=created_nodes['david_khouri'],
                edge_type=loves_et,
                defaults={'properties': {'development': 'slow_burn'}}
            )
            self.stdout.write(f'  Edge: Lena → David (loves)')
        
        self.stdout.write(f'  Created {len(created_nodes)} graph nodes')
