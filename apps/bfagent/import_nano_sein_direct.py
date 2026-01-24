#!/usr/bin/env python
"""
Direct Import Script for NANO-SEIN Book Project
Bypasses Django management command discovery issues
"""
import os
import sys
import yaml
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

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


def load_yaml(filename):
    """Load a YAML file"""
    filepath = YAML_DIR / filename
    if not filepath.exists():
        print(f'File not found: {filepath}')
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_framework():
    """Create the Vier-Schichten-Architektur framework"""
    print('Creating Framework: Vier-Schichten-Architektur...')
    
    structure = load_yaml('book_1_structure.yaml')
    if not structure:
        return None
    
    layers = structure.get('book_1', {}).get('layer_architecture', {})
    
    framework, created = Framework.objects.update_or_create(
        slug='vier-schichten-architektur',
        defaults={
            'name': 'vier-schichten-architektur',
            'display_name': 'Vier-Schichten-Architektur',
            'description': 'Multi-Layer Story Framework: Thriller + Romance + Soft-SciFi + Mystik.',
            'domain': 'story',
            'icon': 'layers',
            'color': '#6366f1',
            'is_active': True,
            'config': {
                'source': 'NANO-SEIN',
                'layers': list(layers.keys())
            }
        }
    )
    
    print(f'  {"Created" if created else "Updated"} Framework: {framework.display_name}')
    
    # Create Phases for each layer
    phase_data = [
        ('thriller', 'Thriller-Schicht', layers.get('thriller', {}).get('focus', ''), 1, '#ef4444'),
        ('romance', 'Romance-Schicht', layers.get('romance', {}).get('focus', ''), 2, '#ec4899'),
        ('soft-scifi', 'Soft-SciFi-Schicht', layers.get('soft_scifi', {}).get('focus', ''), 3, '#3b82f6'),
        ('mystik', 'Mystik-Schicht', layers.get('mystik', {}).get('focus', ''), 4, '#8b5cf6'),
    ]
    
    for slug, name, desc, order, color in phase_data:
        phase, _ = FrameworkPhase.objects.update_or_create(
            framework=framework,
            slug=slug,
            defaults={
                'name': name,
                'description': desc,
                'order': order,
                'color': color,
            }
        )
        print(f'    Phase: {phase.name}')
        
        # Create steps from layer elements
        layer_key = slug.replace('-', '_')
        layer_info = layers.get(layer_key, {})
        elements = layer_info.get('elements', [])
        
        for i, element in enumerate(elements, 1):
            step_slug = slugify(element[:50]) or f'step-{i}'
            step, _ = FrameworkStep.objects.update_or_create(
                phase=phase,
                slug=step_slug,
                defaults={
                    'name': element[:100],
                    'description': element,
                    'order': i,
                }
            )
    
    # Add Act Structure phases
    acts = structure.get('book_1', {})
    act_phases = [
        ('act-1', 'Akt 1: RISSE', 5, '#22c55e'),
        ('act-2', 'Akt 2: SPALTUNG', 6, '#eab308'),
        ('act-3', 'Akt 3: SYNTHESE', 7, '#f97316'),
    ]
    
    for slug, name, order, color in act_phases:
        act_key = slug.replace('-', '_')
        act_data = acts.get(act_key, {})
        goals = act_data.get('goals', [])
        
        phase, _ = FrameworkPhase.objects.update_or_create(
            framework=framework,
            slug=slug,
            defaults={
                'name': name,
                'description': goals[0] if goals else '',
                'order': order,
                'color': color,
            }
        )
        print(f'    Phase: {phase.name}')
        
        for i, goal in enumerate(goals, 1):
            goal_slug = slugify(goal[:50]) or f'goal-{i}'
            step, _ = FrameworkStep.objects.update_or_create(
                phase=phase,
                slug=goal_slug,
                defaults={
                    'name': goal[:100],
                    'description': goal,
                    'order': i,
                }
            )
    
    return framework


def create_graph_types():
    """Create NodeTypes and EdgeTypes"""
    print('Creating Graph Types...')
    
    # NodeType uses 'name' as unique key, 'display_name' as human-readable
    node_types_data = [
        ('character', 'Charakter', 'bi-person', '#3b82f6'),
        ('location', 'Ort', 'bi-geo-alt', '#22c55e'),
        ('theme', 'Thema', 'bi-lightbulb', '#eab308'),
        ('plotthread', 'Handlungsstrang', 'bi-diagram-3', '#8b5cf6'),
        ('bloodline', 'Blutlinie', 'bi-tree', '#ef4444'),
        ('faction', 'Fraktion', 'bi-people', '#ec4899'),
    ]
    
    node_types = {}
    for name, display_name, icon, color in node_types_data:
        nt, _ = NodeType.objects.update_or_create(
            name=name,
            defaults={'display_name': display_name, 'icon': icon, 'color': color}
        )
        node_types[name] = nt
        print(f'  NodeType: {nt.display_name}')
    
    # EdgeType uses 'name' as unique key, 'display_name' as human-readable
    edge_types_data = [
        ('loves', 'liebt', '#ec4899'),
        ('mentors', 'mentor von', '#22c55e'),
        ('conflicts_with', 'Konflikt mit', '#f97316'),
        ('bloodline_to', 'Blutlinie zu', '#8b5cf6'),
        ('belongs_to', 'gehört zu', '#64748b'),
    ]
    
    edge_types = {}
    for name, display_name, color in edge_types_data:
        et, _ = EdgeType.objects.update_or_create(
            name=name,
            defaults={'display_name': display_name, 'color': color}
        )
        edge_types[name] = et
        print(f'  EdgeType: {et.display_name}')
    
    return node_types, edge_types


def create_book_project():
    """Create BookProject for NANO-SEIN"""
    print('Creating BookProject...')
    
    structure = load_yaml('book_1_structure.yaml')
    if not structure:
        return None
    
    book_info = structure.get('book_1', {})
    
    # Check if project already exists
    try:
        project = BookProjects.objects.get(title='NANO-SEIN: Erwachen')
        print(f'  Found existing BookProject: {project.title}')
        return project
    except BookProjects.DoesNotExist:
        pass
    
    # Get a default book_type to satisfy the model's save() method
    from apps.bfagent.models import BookTypes
    book_type = BookTypes.objects.first()
    
    # Get the user
    user = User.objects.first()
    
    # Create new project
    project = BookProjects(
        title='NANO-SEIN: Erwachen',
        description=f"Buch 1 der NANO-SEIN Serie. {book_info.get('estimated_length', '85.000-95.000 Wörter')}, {book_info.get('chapters', 32)} Kapitel.",
        genre='Speculative Fiction',
        target_audience='Erwachsene 25-55',
        status='planning',
        user=user,
        book_type=book_type,
        target_word_count=90000,  # ~85.000-95.000 words
    )
    project.save()
    
    print(f'  Created BookProject: {project.title}')
    return project


def create_chapters(project):
    """Create chapters from YAML files"""
    print('Creating Chapters...')
    
    try:
        from apps.writing_hub.models import Chapter
    except ImportError:
        print('Could not import Chapter model')
        return
    
    chapter_files = [
        'book_1_chapters_01_08.yaml',
        'book_1_chapters_09_16.yaml',
        'book_1_chapters_17_24.yaml',
        'book_1_chapters_25_32.yaml',
    ]
    
    chapter_count = 0
    for filename in chapter_files:
        data = load_yaml(filename)
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
            
            layer_focus = chapter_data.get('layer_focus', {})
            notes = f"POV: {pov}\nWord Count: {word_count}\n"
            notes += f"Primary Layer: {layer_focus.get('primary', 'N/A')}\n"
            notes += f"Secondary Layer: {layer_focus.get('secondary', 'N/A')}"
            
            chapter, _ = Chapter.objects.update_or_create(
                project=project,
                chapter_number=chapter_num,
                defaults={
                    'title': title,
                    'content': content,
                    'notes': notes,
                    'status': 'outline',
                }
            )
            chapter_count += 1
            print(f'  Chapter {chapter_num}: {title}')
    
    print(f'  Created/Updated {chapter_count} chapters')


def create_character_nodes(project, node_types, edge_types):
    """Create graph nodes for characters"""
    print('Creating Character Nodes...')
    
    story_graph = load_yaml('story_graph_export.yaml')
    if not story_graph:
        return
    
    characters = story_graph.get('characters', {})
    character_nt = node_types.get('character')
    faction_nt = node_types.get('faction')
    
    if not character_nt:
        return
    
    created_nodes = {}
    
    # Create protagonist nodes
    for char_key, char_data in characters.get('protagonists', {}).items():
        name = char_key.replace('_', ' ').title()
        node, _ = GraphNode.objects.update_or_create(
            project=project,
            node_type=character_nt,
            name=name,
            defaults={
                'properties': {
                    'profession': char_data.get('profession', ''),
                    'age': char_data.get('age', 0),
                    'role': char_data.get('role', ''),
                    'arc': char_data.get('arc', {}),
                }
            }
        )
        created_nodes[char_key] = node
        print(f'  Character: {node.name}')
    
    # Create antagonist nodes
    for char_key, char_data in characters.get('antagonists', {}).items():
        name = char_data.get('name', char_key.replace('_', ' ').title())
        node, _ = GraphNode.objects.update_or_create(
            project=project,
            node_type=character_nt,
            name=name,
            defaults={
                'properties': {
                    'role': 'Antagonist',
                    'organization': char_data.get('organization', ''),
                }
            }
        )
        created_nodes[char_key] = node
        print(f'  Antagonist: {node.name}')
    
    # Create faction nodes
    mythology = story_graph.get('mythology', {})
    if mythology and faction_nt:
        factions = mythology.get('factions', {})
        for faction_key, faction_data in factions.items():
            node, _ = GraphNode.objects.update_or_create(
                project=project,
                node_type=faction_nt,
                name=faction_key.upper(),
                defaults={
                    'properties': {
                        'principle': faction_data.get('principle', ''),
                        'goal': faction_data.get('goal', ''),
                    }
                }
            )
            created_nodes[faction_key] = node
            print(f'  Faction: {node.name}')
    
    # Create relationships
    loves_et = edge_types.get('loves')
    if 'lena_vogt' in created_nodes and 'david_khouri' in created_nodes and loves_et:
        edge, _ = GraphEdge.objects.update_or_create(
            project=project,
            source=created_nodes['lena_vogt'],
            target=created_nodes['david_khouri'],
            edge_type=loves_et,
            defaults={'properties': {'development': 'slow_burn'}}
        )
        print(f'  Edge: Lena → David (loves)')
    
    print(f'  Created {len(created_nodes)} graph nodes')


def main():
    print('=' * 60)
    print('NANO-SEIN Import Script')
    print('=' * 60)
    
    user = User.objects.first()
    if not user:
        print('ERROR: No users found!')
        return
    
    print(f'Using user: {user.username}')
    print(f'YAML directory: {YAML_DIR}')
    print()
    
    with transaction.atomic():
        # Step 1: Create Framework
        framework = create_framework()
        print()
        
        # Step 2: Create Graph Types
        node_types, edge_types = create_graph_types()
        print()
        
        # Step 3: Create BookProject
        project = create_book_project()
        print()
        
        # Step 4: Link Project to Framework
        if framework and project:
            pf, created = ProjectFramework.objects.update_or_create(
                project=project,
                framework=framework,
                defaults={'is_primary': True}
            )
            if created:
                pf.start()
            print(f'Linked: {project.title} → {framework.display_name}')
            print()
        
        # Step 5: Create Chapters
        if project:
            create_chapters(project)
            print()
        
        # Step 6: Create Character Nodes
        if project and node_types:
            create_character_nodes(project, node_types, edge_types)
    
    print()
    print('=' * 60)
    print('Import completed successfully!')
    print('=' * 60)
    
    if project:
        print(f'\nView project at: http://localhost:8000/graph/workflow/{project.id}/')


if __name__ == '__main__':
    main()
