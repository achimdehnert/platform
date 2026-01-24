"""
Management Command to Test Pipeline Handler System

Usage:
    python manage.py test_pipeline_handlers
"""

from django.core.management.base import BaseCommand
from apps.bfagent.services.handlers.registries import (
    InputHandlerRegistry,
    ProcessingHandlerRegistry,
    OutputHandlerRegistry,
    get_all_handlers,
)
from apps.bfagent.models import BookProjects
import json


class Command(BaseCommand):
    help = "Test Pipeline Handler System"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='Project ID for testing (default: first project)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )
    
    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*60))
        self.stdout.write(self.style.SUCCESS("🧪 PIPELINE HANDLER SYSTEM TEST"))
        self.stdout.write(self.style.SUCCESS("="*60 + "\n"))
        
        # Test 1: Registry Discovery
        self.test_registries(verbose)
        
        # Test 2: Handler Creation
        self.test_handler_creation(verbose)
        
        # Test 3: Handler Execution
        project_id = options.get('project_id')
        self.test_handler_execution(project_id, verbose)
        
        self.stdout.write(self.style.SUCCESS("\n" + "="*60))
        self.stdout.write(self.style.SUCCESS("✅ ALL TESTS COMPLETE!"))
        self.stdout.write(self.style.SUCCESS("="*60 + "\n"))
    
    def test_registries(self, verbose):
        """Test handler registries."""
        self.stdout.write("\n📋 TEST 1: Handler Registries")
        self.stdout.write("-" * 60)
        
        all_handlers = get_all_handlers()
        
        # Count handlers
        input_count = len(all_handlers['input'])
        processing_count = len(all_handlers['processing'])
        output_count = len(all_handlers['output'])
        total = input_count + processing_count + output_count
        
        self.stdout.write(f"✅ Input Handlers: {input_count}")
        for handler in all_handlers['input']:
            self.stdout.write(f"   • {handler['name']}: {handler['description']}")
        
        self.stdout.write(f"✅ Processing Handlers: {processing_count}")
        for handler in all_handlers['processing']:
            self.stdout.write(f"   • {handler['name']}: {handler['description']}")
        
        self.stdout.write(f"✅ Output Handlers: {output_count}")
        for handler in all_handlers['output']:
            self.stdout.write(f"   • {handler['name']}: {handler['description']}")
        
        self.stdout.write(f"\n📊 Total Handlers Registered: {total}")
        
        if verbose:
            self.stdout.write("\n📄 Complete Registry Info:")
            self.stdout.write(json.dumps(all_handlers, indent=2))
    
    def test_handler_creation(self, verbose):
        """Test creating handler instances."""
        self.stdout.write("\n🔨 TEST 2: Handler Creation")
        self.stdout.write("-" * 60)
        
        tests = [
            (
                "Input: ProjectFieldsInputHandler",
                InputHandlerRegistry,
                "project_fields",
                {"fields": ["title", "genre"]}
            ),
            (
                "Input: UserInputHandler",
                InputHandlerRegistry,
                "user_input",
                {}
            ),
            (
                "Processing: TemplateRendererHandler",
                ProcessingHandlerRegistry,
                "template_renderer",
                {"template": "Title: {{ title }}"}
            ),
            (
                "Output: SimpleTextFieldHandler",
                OutputHandlerRegistry,
                "simple_text_field",
                {
                    "target_model": "BookProjects",
                    "target_field": "synopsis",
                    "target_instance": "current"
                }
            ),
        ]
        
        for test_name, registry, handler_name, config in tests:
            try:
                HandlerClass = registry.get(handler_name)
                handler = HandlerClass(config)
                self.stdout.write(f"✅ {test_name}")
                if verbose:
                    self.stdout.write(f"   {handler}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {test_name}: {e}"))
    
    def test_handler_execution(self, project_id, verbose):
        """Test executing handlers with real data."""
        self.stdout.write("\n🚀 TEST 3: Handler Execution")
        self.stdout.write("-" * 60)
        
        # Get test project
        if project_id:
            try:
                project = BookProjects.objects.get(pk=project_id)
            except BookProjects.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Project {project_id} not found"))
                return
        else:
            project = BookProjects.objects.first()
            if not project:
                self.stdout.write(self.style.WARNING("⚠️  No projects found. Skipping execution test."))
                return
        
        self.stdout.write(f"📚 Using Project: {project.title} (ID: {project.pk})")
        
        # Test 3.1: ProjectFieldsInputHandler
        self.stdout.write("\n🔹 Test 3.1: ProjectFieldsInputHandler")
        try:
            HandlerClass = InputHandlerRegistry.get("project_fields")
            handler = HandlerClass({"fields": ["title", "genre", "synopsis"]})
            
            context = {"project": project}
            data = handler.collect(context)
            
            self.stdout.write("✅ Data collected:")
            for key, value in data.items():
                preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                self.stdout.write(f"   • {key}: {preview}")
            
            if verbose:
                self.stdout.write("\n   Full Data:")
                self.stdout.write(f"   {json.dumps(data, indent=4)}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
        
        # Test 3.2: UserInputHandler
        self.stdout.write("\n🔹 Test 3.2: UserInputHandler")
        try:
            HandlerClass = InputHandlerRegistry.get("user_input")
            handler = HandlerClass({})
            
            context = {
                "user_context": "Test context from command",
                "user_requirements": "Generate diverse characters"
            }
            data = handler.collect(context)
            
            self.stdout.write("✅ User input collected:")
            for key, value in data.items():
                self.stdout.write(f"   • {key}: {value}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
        
        # Test 3.3: TemplateRendererHandler
        self.stdout.write("\n🔹 Test 3.3: TemplateRendererHandler")
        try:
            HandlerClass = ProcessingHandlerRegistry.get("template_renderer")
            handler = HandlerClass({
                "template": "Title: {{ title }}\nGenre: {{ genre }}\nUser: {{ user_context }}"
            })
            
            input_data = {
                "title": project.title,
                "genre": project.genre or "Unknown",
                "user_context": "Test context"
            }
            
            rendered = handler.process(input_data, {})
            
            self.stdout.write("✅ Template rendered:")
            self.stdout.write(f"\n{rendered}\n")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
        
        # Test 3.4: SimpleTextFieldHandler (parse only, no DB write)
        self.stdout.write("\n🔹 Test 3.4: SimpleTextFieldHandler (parse)")
        try:
            HandlerClass = OutputHandlerRegistry.get("simple_text_field")
            handler = HandlerClass({
                "target_model": "BookProjects",
                "target_field": "ai_suggestions",
                "target_instance": "current"
            })
            
            test_text = "This is a test synopsis generated by the pipeline."
            parsed = handler.parse(test_text)
            validation = handler.validate(parsed)
            
            self.stdout.write("✅ Parsed:")
            self.stdout.write(f"   {parsed}")
            self.stdout.write("✅ Validation:")
            self.stdout.write(f"   Valid: {validation['valid']}")
            self.stdout.write(f"   Length: {validation.get('length', 0)} characters")
            if validation['errors']:
                self.stdout.write(f"   Errors: {validation['errors']}")
            if validation['warnings']:
                self.stdout.write(f"   Warnings: {validation['warnings']}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))
