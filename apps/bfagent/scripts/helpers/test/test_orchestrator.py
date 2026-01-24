"""
Test Pipeline Orchestrator

Run with: python test_orchestrator.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.bfagent.models import BookProjects, Agents
from apps.bfagent.services.pipeline_orchestrator import PipelineOrchestrator


def test_complete_pipeline():
    """Test complete INPUT → PROCESSING → OUTPUT pipeline"""
    print("\n" + "="*70)
    print("🧪 TEST: Complete Pipeline Execution")
    print("="*70)
    
    # Get test data
    project = BookProjects.objects.get(pk=18)
    agent = Agents.objects.first()
    
    print(f"\n📚 Project: {project.title}")
    print(f"🤖 Agent: {agent.name if agent else 'None'}")
    
    # Configure pipeline
    pipeline_config = {
        "input": [
            {
                "handler": "project_fields",
                "config": {
                    "mode": "all"  # Collect all filled fields
                }
            },
            {
                "handler": "user_input",
                "config": {}
            }
        ],
        "processing": [
            {
                "handler": "template_renderer",
                "config": {
                    "template": """
📚 Project: {{ title }}
🎭 Genre: {{ genre }}
📖 Description: {{ description }}

🎯 Main Conflict: {{ main_conflict }}
⚡ Stakes: {{ stakes }}

👤 User Context: {{ user_context }}

Based on this information, please generate a detailed synopsis.
"""
                }
            }
        ],
        "output": {
            "handler": "simple_text_field",
            "config": {
                "target_model": "BookProjects",
                "target_field": "ai_suggestions",
                "target_instance": "current",
                "action_name": "test_pipeline"
            }
        }
    }
    
    # Create orchestrator
    print("\n🔧 Creating Pipeline Orchestrator...")
    orchestrator = PipelineOrchestrator(pipeline_config)
    
    # Execute pipeline
    print("\n🚀 Executing Pipeline...\n")
    
    context = {
        "project": project,
        "agent": agent,
        "user_context": "Focus on emotional depth and character development"
    }
    
    try:
        results = orchestrator.execute(context)
        
        # Display results
        print("\n" + "="*70)
        print("✅ PIPELINE EXECUTION SUCCESSFUL!")
        print("="*70)
        
        # INPUT Stage Results
        print("\n📥 INPUT STAGE:")
        print(f"   Collected {len(results['input'])} fields:")
        for key in list(results['input'].keys())[:5]:  # Show first 5
            value = results['input'][key]
            preview = str(value)[:60] + "..." if len(str(value)) > 60 else str(value)
            print(f"   • {key}: {preview}")
        if len(results['input']) > 5:
            print(f"   ... and {len(results['input']) - 5} more fields")
        
        # PROCESSING Stage Results
        print("\n⚙️ PROCESSING STAGE:")
        processed = results['processed']
        lines = processed.split('\n')
        print(f"   Rendered template ({len(lines)} lines):")
        for line in lines[:10]:  # Show first 10 lines
            print(f"   {line}")
        if len(lines) > 10:
            print(f"   ... and {len(lines) - 10} more lines")
        
        # OUTPUT Stage Results
        print("\n📤 OUTPUT STAGE:")
        output = results['output']
        print(f"   Handler: {output['handler']}")
        print(f"   Responses Created: {len(output['responses'])}")
        print(f"   Validation: {output['validation']['valid']}")
        if output['validation']['errors']:
            print(f"   Errors: {output['validation']['errors']}")
        if output['validation']['warnings']:
            print(f"   Warnings: {output['validation']['warnings']}")
        
        # Metadata
        print("\n📊 EXECUTION METADATA:")
        metadata = results['metadata']
        print(f"   Stages Completed: {', '.join(metadata['stages_completed'])}")
        
        # Execution Summary
        summary = orchestrator.get_execution_summary()
        print(f"\n📈 EXECUTION SUMMARY:")
        print(f"   Total Handlers: {summary['total_handlers']}")
        print(f"   • Input: {summary['input_handlers']}")
        print(f"   • Processing: {summary['processing_handlers']}")
        print(f"   • Output: {summary['output_handlers']}")
        
        print("\n" + "="*70)
        print("🎉 COMPLETE PIPELINE TEST SUCCESSFUL!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"   Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()


def test_simple_pipeline():
    """Test simplified pipeline"""
    print("\n" + "="*70)
    print("🧪 TEST: Simple Pipeline (Field Mapping)")
    print("="*70)
    
    project = BookProjects.objects.get(pk=18)
    agent = Agents.objects.first()
    
    # Simple pipeline: Project fields → Template → Text field
    pipeline_config = {
        "input": [
            {
                "handler": "project_fields",
                "config": {
                    "fields": ["title", "synopsis", "themes"]
                }
            }
        ],
        "processing": [
            {
                "handler": "template_renderer",
                "config": {
                    "template": "Title: {{ title }}\nSynopsis: {{ synopsis }}\nThemes: {{ themes }}"
                }
            }
        ],
        "output": {
            "handler": "simple_text_field",
            "config": {
                "target_model": "BookProjects",
                "target_field": "ai_suggestions",
                "target_instance": "current",
                "action_name": "simple_test"
            }
        }
    }
    
    orchestrator = PipelineOrchestrator(pipeline_config)
    
    context = {"project": project, "agent": agent}
    
    try:
        results = orchestrator.execute(context)
        
        print(f"\n✅ Simple Pipeline Success!")
        print(f"   Input fields: {list(results['input'].keys())}")
        print(f"   Processed output:\n")
        for line in results['processed'].split('\n'):
            print(f"      {line}")
        print(f"\n   Output validation: {results['output']['validation']['valid']}")
        
    except Exception as e:
        print(f"\n❌ Simple Pipeline Failed: {e}")


if __name__ == "__main__":
    print("\n" + "🚀"*35)
    print("PIPELINE ORCHESTRATOR - COMPLETE TEST")
    print("🚀"*35)
    
    # Test 1: Simple pipeline
    test_simple_pipeline()
    
    # Test 2: Complete pipeline
    test_complete_pipeline()
    
    print("\n" + "="*70)
    print("✅ ALL PIPELINE TESTS COMPLETE!")
    print("="*70 + "\n")
