"""
Management command to run the book writing workflow
"""
import json
from django.core.management.base import BaseCommand, CommandError
from apps.bfagent.models import BookProjects
from apps.bfagent.domains.book_writing.handlers.workflow_orchestrator import (
    BookWorkflowOrchestrator,
    WorkflowPhase
)


class Command(BaseCommand):
    help = 'Run the complete book writing workflow for a project'

    def add_arguments(self, parser):
        parser.add_argument(
            'project_id',
            type=int,
            help='ID of the BookProject to process'
        )
        parser.add_argument(
            '--use-ai',
            action='store_true',
            default=False,
            help='Use AI for content generation (requires API key)'
        )
        parser.add_argument(
            '--skip-phases',
            type=str,
            default='',
            help='Comma-separated list of phases to skip (planning,characters,world_building,outline,chapters)'
        )
        parser.add_argument(
            '--phase',
            type=str,
            default='',
            help='Run only a specific phase'
        )
        parser.add_argument(
            '--output',
            type=str,
            default='',
            help='Output file for results (JSON)'
        )

    def handle(self, *args, **options):
        project_id = options['project_id']
        use_ai = options['use_ai']
        skip_phases = [p.strip() for p in options['skip_phases'].split(',') if p.strip()]
        single_phase = options['phase']
        output_file = options['output']

        # Verify project exists
        try:
            project = BookProjects.objects.get(id=project_id)
            self.stdout.write(f"\n📚 Project: {project.title}")
            self.stdout.write(f"   Genre: {project.genre or 'Not set'}")
            self.stdout.write(f"   Type: {project.book_type.name if project.book_type else 'Not set'}\n")
        except BookProjects.DoesNotExist:
            raise CommandError(f'Project {project_id} not found')

        # Initialize orchestrator
        self.stdout.write(self.style.HTTP_INFO(f"🚀 Initializing workflow orchestrator..."))
        self.stdout.write(f"   AI Mode: {'Enabled' if use_ai else 'Mock Mode'}")
        
        try:
            orchestrator = BookWorkflowOrchestrator(
                project_id=project_id,
                use_ai=use_ai
            )
        except Exception as e:
            raise CommandError(f'Failed to initialize orchestrator: {e}')

        # Run single phase or full workflow
        if single_phase:
            self.stdout.write(f"\n📍 Running single phase: {single_phase}")
            result = self._run_single_phase(orchestrator, single_phase)
        else:
            self.stdout.write(f"\n📍 Running full workflow...")
            if skip_phases:
                self.stdout.write(f"   Skipping: {', '.join(skip_phases)}")
            result = orchestrator.run_full_workflow(skip_phases=skip_phases)

        # Display results
        self._display_results(result)

        # Save output if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            self.stdout.write(f"\n💾 Results saved to: {output_file}")

        if result.get('success'):
            self.stdout.write(self.style.SUCCESS('\n✅ Workflow completed successfully!'))
        else:
            self.stdout.write(self.style.ERROR(f'\n❌ Workflow failed: {result.get("error")}'))

    def _run_single_phase(self, orchestrator, phase_name):
        """Run a single workflow phase"""
        phase_handlers = {
            'planning': orchestrator.run_planning_phase,
            'characters': orchestrator.run_characters_phase,
            'world_building': orchestrator.run_world_building_phase,
            'outline': orchestrator.run_outline_phase,
            'chapters': orchestrator.run_chapters_phase,
        }

        handler = phase_handlers.get(phase_name)
        if not handler:
            return {
                'success': False,
                'error': f'Unknown phase: {phase_name}. Valid: {list(phase_handlers.keys())}'
            }

        result = handler()
        return {
            'success': result.success,
            'phase': phase_name,
            'data': result.data,
            'error': result.error,
            'cost': result.cost
        }

    def _display_results(self, result):
        """Display workflow results"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 WORKFLOW RESULTS")
        self.stdout.write("=" * 60)

        if 'results' in result:
            for phase_name, phase_result in result['results'].items():
                if hasattr(phase_result, 'success'):
                    status = '✅' if phase_result.success else '❌'
                    self.stdout.write(f"\n{status} {phase_name.upper()}")
                    if phase_result.data:
                        for key, value in phase_result.data.items():
                            if isinstance(value, list):
                                self.stdout.write(f"   {key}: {len(value)} items")
                            elif isinstance(value, dict):
                                self.stdout.write(f"   {key}: {len(value)} fields")
                            elif isinstance(value, str) and len(value) > 100:
                                self.stdout.write(f"   {key}: {value[:100]}...")
                            else:
                                self.stdout.write(f"   {key}: {value}")
                    if phase_result.cost > 0:
                        self.stdout.write(f"   💰 Cost: ${phase_result.cost:.4f}")

        if 'context' in result:
            ctx = result['context']
            self.stdout.write("\n📋 CONTEXT SUMMARY:")
            self.stdout.write(f"   Characters: {ctx.get('character_count', 0)}")
            self.stdout.write(f"   Chapters: {ctx.get('chapter_count', 0)}")
            self.stdout.write(f"   World: {ctx.get('world_name', 'None')}")

        if result.get('total_cost', 0) > 0:
            self.stdout.write(f"\n💰 TOTAL COST: ${result['total_cost']:.4f}")
            self.stdout.write(f"📊 TOTAL TOKENS: {result.get('total_tokens', 0)}")
