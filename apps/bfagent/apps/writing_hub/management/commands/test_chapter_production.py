"""
Test Chapter Production Pipeline
================================

Management command to test the chapter production pipeline.

Usage:
    python manage.py test_chapter_production --project-id <uuid> --chapter-id <uuid>
    python manage.py test_chapter_production --project-id <uuid> --chapter-number 1
    python manage.py test_chapter_production --list-projects
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Test the chapter production pipeline'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=str,
            help='Project UUID',
        )
        parser.add_argument(
            '--chapter-id',
            type=str,
            help='Chapter UUID',
        )
        parser.add_argument(
            '--chapter-number',
            type=int,
            help='Chapter number (alternative to chapter-id)',
        )
        parser.add_argument(
            '--list-projects',
            action='store_true',
            help='List available projects',
        )
        parser.add_argument(
            '--list-chapters',
            action='store_true',
            help='List chapters for project',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without LLM calls',
        )
        parser.add_argument(
            '--stage',
            type=str,
            choices=['brief', 'write', 'analyze', 'gate', 'full'],
            default='full',
            help='Run specific stage or full pipeline',
        )
    
    def handle(self, *args, **options):
        from uuid import UUID
        from apps.writing_hub.models import BookProject, Chapter
        
        # List projects
        if options['list_projects']:
            self.stdout.write("\n📚 Verfügbare Projekte:\n")
            projects = BookProject.objects.all()[:20]
            for p in projects:
                chapters = Chapter.objects.filter(project=p).count()
                self.stdout.write(f"  • {p.project_id} - {p.title} ({chapters} Kapitel)")
            return
        
        # Need project-id for other operations
        if not options['project_id']:
            self.stderr.write(self.style.ERROR('--project-id required'))
            return
        
        try:
            project_id = UUID(options['project_id'])
            project = BookProject.objects.get(project_id=project_id)
        except (ValueError, BookProject.DoesNotExist) as e:
            self.stderr.write(self.style.ERROR(f'Project not found: {e}'))
            return
        
        self.stdout.write(f"\n📖 Projekt: {project.title}")
        
        # List chapters
        if options['list_chapters']:
            self.stdout.write("\n📑 Kapitel:\n")
            chapters = Chapter.objects.filter(project=project).order_by('chapter_number')
            for ch in chapters:
                status = ch.status or 'draft'
                words = ch.word_count or 0
                self.stdout.write(f"  {ch.chapter_number}. {ch.title or 'Untitled'} [{status}] ({words} Wörter)")
                self.stdout.write(f"     ID: {ch.chapter_id}")
            return
        
        # Get chapter
        chapter = None
        if options['chapter_id']:
            try:
                chapter_id = UUID(options['chapter_id'])
                chapter = Chapter.objects.get(chapter_id=chapter_id)
            except (ValueError, Chapter.DoesNotExist):
                self.stderr.write(self.style.ERROR(f'Chapter not found'))
                return
        elif options['chapter_number']:
            chapter = Chapter.objects.filter(
                project=project,
                chapter_number=options['chapter_number']
            ).first()
            if not chapter:
                self.stderr.write(self.style.ERROR(f'Chapter {options["chapter_number"]} not found'))
                return
        else:
            self.stderr.write(self.style.ERROR('--chapter-id or --chapter-number required'))
            return
        
        self.stdout.write(f"📝 Kapitel: {chapter.chapter_number}. {chapter.title or 'Untitled'}\n")
        
        # Run pipeline
        from apps.writing_hub.services.chapter_production_service import (
            get_chapter_production_service,
            ProductionStage
        )
        
        service = get_chapter_production_service(project.project_id)
        stage = options['stage']
        
        if stage == 'brief':
            self.stdout.write("🎯 Stage: BRIEF\n")
            result = service.generate_brief(chapter)
            self._print_brief_result(result)
            
        elif stage == 'analyze':
            self.stdout.write("🔍 Stage: ANALYZE\n")
            content = chapter.content or "Test content for analysis."
            result = service.analyze_chapter(chapter, content)
            self._print_analyze_result(result)
            
        elif stage == 'gate':
            self.stdout.write("🚦 Stage: GATE\n")
            content = chapter.content or "Test content."
            analyze = service.analyze_chapter(chapter, content)
            result = service.evaluate_gate(chapter, analyze)
            self._print_gate_result(result)
            
        elif stage == 'full':
            self.stdout.write("🚀 Stage: FULL PIPELINE\n")
            if options['dry_run']:
                self.stdout.write("  (Dry Run - keine LLM Calls)\n")
            result = service.produce_chapter(
                chapter.chapter_id,
                max_iterations=2,
                auto_commit=False
            )
            self._print_production_result(result)
    
    def _print_brief_result(self, result):
        if result.success:
            self.stdout.write(self.style.SUCCESS("✅ Brief generiert:\n"))
            self.stdout.write(f"\n{result.brief}\n")
            self.stdout.write(f"\n📋 Produktionsziele: {len(result.production_goals)}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Fehler: {result.error}"))
    
    def _print_analyze_result(self, result):
        if result.success:
            self.stdout.write(self.style.SUCCESS(f"✅ Analyse abgeschlossen\n"))
            self.stdout.write(f"📊 Overall Score: {result.overall_score:.1f}/10\n")
            self.stdout.write("\nDimension Scores:")
            for dim, score in result.dimension_scores.items():
                bar = "█" * int(score) + "░" * (10 - int(score))
                self.stdout.write(f"  {dim:15} [{bar}] {score:.1f}")
            if result.strengths:
                self.stdout.write(f"\n✨ Stärken: {', '.join(result.strengths)}")
            if result.issues:
                self.stdout.write(f"\n⚠️  Issues: {len(result.issues)}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Fehler: {result.error}"))
    
    def _print_gate_result(self, result):
        decision_colors = {
            'approve': self.style.SUCCESS,
            'review': self.style.WARNING,
            'revise': self.style.WARNING,
            'reject': self.style.ERROR,
        }
        color = decision_colors.get(result.decision, self.style.NOTICE)
        
        self.stdout.write(f"\n🚦 Gate Decision: {color(result.decision.upper())}")
        self.stdout.write(f"   Reason: {result.reason}")
        self.stdout.write(f"   Commit erlaubt: {'✅' if result.allows_commit else '❌'}")
        
        if result.required_fixes:
            self.stdout.write("\n   Required Fixes:")
            for fix in result.required_fixes:
                self.stdout.write(f"     - {fix}")
    
    def _print_production_result(self, result):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"📊 PRODUCTION RESULT")
        self.stdout.write(f"{'='*60}\n")
        
        status = self.style.SUCCESS("✅ SUCCESS") if result.success else self.style.ERROR("❌ FAILED")
        self.stdout.write(f"Status: {status}")
        self.stdout.write(f"Stage: {result.stage.value}")
        self.stdout.write(f"Iterations: {result.iterations}")
        self.stdout.write(f"Duration: {result.duration_seconds:.1f}s")
        self.stdout.write(f"Total Tokens: {result.total_tokens}")
        self.stdout.write(f"Total Cost: ${result.total_cost:.4f}")
        
        if result.error:
            self.stdout.write(self.style.ERROR(f"\nError: {result.error}"))
        
        if result.brief:
            self.stdout.write(f"\n📋 BRIEF: {'✅' if result.brief.success else '❌'}")
            self.stdout.write(f"   Goals: {len(result.brief.production_goals)}")
        
        if result.write:
            self.stdout.write(f"\n✍️  WRITE: {'✅' if result.write.success else '❌'}")
            self.stdout.write(f"   Words: {result.write.word_count}")
            self.stdout.write(f"   Tokens: {result.write.tokens_used}")
        
        if result.analyze:
            self.stdout.write(f"\n🔍 ANALYZE: {'✅' if result.analyze.success else '❌'}")
            self.stdout.write(f"   Overall: {result.analyze.overall_score:.1f}/10")
        
        if result.gate:
            self._print_gate_result(result.gate)
        
        self.stdout.write(f"\n{'='*60}\n")
