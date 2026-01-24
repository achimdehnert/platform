#!/usr/bin/env python
"""
Fix NANO-SEIN Import:
1. Fix phase/step ordering (start at 0 for proper display)
2. Create StepProgress entries for checklists
3. Import richer content from YAML
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import yaml
from pathlib import Path
from django.contrib.auth import get_user_model
from apps.graph_core.models import (
    Framework, FrameworkPhase, FrameworkStep,
    ProjectFramework, PhaseProgress, StepProgress
)
from apps.bfagent.models import BookProjects

User = get_user_model()
YAML_DIR = Path('docs/graphen/books/erwachen')


def load_yaml(filename):
    """Load YAML file"""
    filepath = YAML_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


def fix_framework_ordering():
    """Fix phase and step ordering to start at 0"""
    print("Fixing Framework ordering...")
    
    try:
        fw = Framework.objects.get(slug='vier-schichten-architektur')
    except Framework.DoesNotExist:
        print("  Framework not found!")
        return None
    
    # Fix phase ordering - start at 0
    for idx, phase in enumerate(fw.phases.all().order_by('id')):
        if phase.order != idx:
            phase.order = idx
            phase.save()
            print(f"  Fixed Phase {idx}: {phase.name}")
        
        # Fix step ordering - start at 0
        for step_idx, step in enumerate(phase.steps.all().order_by('id')):
            if step.order != step_idx:
                step.order = step_idx
                step.save()
                print(f"    Fixed Step {step_idx}: {step.name}")
    
    return fw


def create_step_progress():
    """Create StepProgress entries for project framework"""
    print("\nCreating StepProgress entries...")
    
    try:
        project = BookProjects.objects.get(title='NANO-SEIN: Erwachen')
    except BookProjects.DoesNotExist:
        print("  Project not found!")
        return
    
    try:
        pf = ProjectFramework.objects.get(project=project)
    except ProjectFramework.DoesNotExist:
        print("  ProjectFramework not found!")
        return
    
    fw = pf.framework
    
    # Create PhaseProgress for each phase
    for phase in fw.phases.all():
        phase_progress, created = PhaseProgress.objects.get_or_create(
            project_framework=pf,
            phase=phase,
            defaults={
                'is_complete': False,
            }
        )
        if created:
            print(f"  Created PhaseProgress: {phase.name}")
        
        # Create StepProgress for each step (links to project_framework, not phase_progress)
        for step in phase.steps.all():
            step_progress, created = StepProgress.objects.get_or_create(
                project_framework=pf,
                step=step,
                defaults={
                    'is_complete': False,
                }
            )
            if created:
                print(f"    Created StepProgress: {step.name}")
    
    print(f"\n  Total StepProgress entries: {StepProgress.objects.filter(project_framework=pf).count()}")


def enrich_framework_content():
    """Add richer content from YAML to framework steps"""
    print("\nEnriching Framework content...")
    
    structure = load_yaml('book_1_structure.yaml')
    if not structure:
        print("  Could not load structure YAML")
        return
    
    try:
        fw = Framework.objects.get(slug='vier-schichten-architektur')
    except Framework.DoesNotExist:
        return
    
    book_info = structure.get('book_1', {})
    layers = book_info.get('layer_architecture', {})
    
    # Map layer names to phases
    layer_mapping = {
        'thriller': 'Thriller-Schicht',
        'romance': 'Romance-Schicht',
        'soft_scifi': 'Soft-SciFi-Schicht',
        'mystik': 'Mystik-Schicht',
    }
    
    for layer_key, phase_name in layer_mapping.items():
        layer_data = layers.get(layer_key, {})
        try:
            phase = fw.phases.get(name=phase_name)
            
            # Update phase description
            focus = layer_data.get('focus', '')
            tone = layer_data.get('tone', '')
            percentage = layer_data.get('percentage', 0)
            
            phase.description = f"{focus}\n\nTon: {tone}\nAnteil: {percentage}%"
            phase.story_percentage = percentage / 100.0
            phase.save()
            print(f"  Updated Phase: {phase_name}")
            
            # Update steps with subplot/arc/progression info
            extra_content = layer_data.get('subplot') or layer_data.get('arc') or layer_data.get('progression') or ''
            if extra_content and phase.steps.exists():
                first_step = phase.steps.first()
                first_step.chapter_guidance = extra_content.strip()
                first_step.save()
                print(f"    Added guidance to: {first_step.name}")
                
        except FrameworkPhase.DoesNotExist:
            pass
    
    # Enrich act phases with three-act structure
    acts = book_info.get('three_act_structure', {})
    act_mapping = {
        'act_1': 'Akt 1: RISSE',
        'act_2': 'Akt 2: SPALTUNG', 
        'act_3': 'Akt 3: SYNTHESE',
    }
    
    for act_key, phase_name in act_mapping.items():
        act_data = acts.get(act_key, {})
        try:
            phase = fw.phases.get(name=phase_name)
            
            chapters = act_data.get('chapters', '')
            theme = act_data.get('theme', '')
            
            phase.description = f"Kapitel: {chapters}\nThema: {theme}"
            phase.save()
            print(f"  Updated Act: {phase_name}")
            
        except FrameworkPhase.DoesNotExist:
            pass


def main():
    print("=" * 60)
    print("NANO-SEIN Import Fix")
    print("=" * 60)
    
    # 1. Fix ordering
    fw = fix_framework_ordering()
    
    # 2. Create step progress entries
    create_step_progress()
    
    # 3. Enrich content
    enrich_framework_content()
    
    print("\n" + "=" * 60)
    print("Fix completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
