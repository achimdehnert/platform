"""
Quick Test Script for Pipeline Handlers
Run with: python test_handlers_quick.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import BookProjects
from apps.bfagent.services.handlers.input.project_fields import ProjectFieldsInputHandler
from apps.bfagent.services.handlers.processing.template_renderer import TemplateRendererHandler

def test_auto_discovery():
    """Test Mode 'all' - Auto-discovery of all filled fields"""
    print("\n" + "="*70)
    print("🧪 TEST: Auto-Discovery (Mode 'all')")
    print("="*70)
    
    project = BookProjects.objects.get(pk=18)
    
    handler = ProjectFieldsInputHandler({"mode": "all"})
    data = handler.collect({"project": project})
    
    print(f"\n✅ Collected {len(data)} fields from '{project.title}':\n")
    
    for key, value in data.items():
        preview = value[:100] + "..." if isinstance(value, str) and len(value) > 100 else value
        print(f"  📌 {key}:")
        print(f"     {preview}\n")
    
    return data

def test_field_mapping():
    """Test field mapping (user-friendly names)"""
    print("\n" + "="*70)
    print("🧪 TEST: Field Mapping")
    print("="*70)
    
    project = BookProjects.objects.get(pk=18)
    
    handler = ProjectFieldsInputHandler({
        "fields": ["title", "synopsis", "themes", "conflict", "protagonist"]
    })
    data = handler.collect({"project": project})
    
    print(f"\n✅ Collected {len(data)} fields (with mapping):\n")
    
    for key, value in data.items():
        preview = value[:100] + "..." if isinstance(value, str) and len(value) > 100 else value
        print(f"  📌 {key}: {preview}\n")
    
    return data

def test_template_rendering(input_data):
    """Test template rendering with collected data"""
    print("\n" + "="*70)
    print("🧪 TEST: Template Rendering")
    print("="*70)
    
    handler = TemplateRendererHandler({
        "template": """
📚 Project: {{ title }}
🎭 Genre: {{ genre }}
📖 Story: {{ description }}

🎯 Conflict: {{ main_conflict }}
⚡ Stakes: {{ stakes }}

Please generate diverse characters for this story.
"""
    })
    
    rendered = handler.process(input_data, {})
    
    print("\n✅ Rendered Template:\n")
    print(rendered)
    
    return rendered

if __name__ == "__main__":
    print("\n" + "🚀"*35)
    print("PIPELINE HANDLERS - QUICK TEST")
    print("🚀"*35)
    
    # Test 1: Auto-discovery
    data = test_auto_discovery()
    
    # Test 2: Field mapping
    data_mapped = test_field_mapping()
    
    # Test 3: Template rendering
    rendered = test_template_rendering(data)
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETE!")
    print("="*70 + "\n")
