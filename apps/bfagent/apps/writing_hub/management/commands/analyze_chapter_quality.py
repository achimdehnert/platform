"""
Analyze Chapter Quality
=======================

Management command to analyze a chapter's quality against Style DNA.

Usage:
    python manage.py analyze_chapter_quality --list
    python manage.py analyze_chapter_quality --chapter-id <uuid>
    python manage.py analyze_chapter_quality --project-id <uuid> --chapter-num 1
"""
import logging
from django.core.management.base import BaseCommand
from django.db.models import Q

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Analyze chapter quality against Style DNA'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List available chapters with content',
        )
        parser.add_argument(
            '--chapter-id',
            type=str,
            help='UUID of chapter to analyze',
        )
        parser.add_argument(
            '--project-id',
            type=str,
            help='UUID of project (use with --chapter-num)',
        )
        parser.add_argument(
            '--chapter-num',
            type=int,
            help='Chapter number (use with --project-id)',
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='Save results to database',
        )

    def handle(self, *args, **options):
        from apps.bfagent.models import BookChapters, BookProjects
        
        # List mode
        if options.get('list'):
            self._list_chapters(BookChapters, BookProjects)
            return
        
        # Get chapter
        chapter = self._get_chapter(options, BookChapters)
        if not chapter:
            return
        
        # Analyze
        self._analyze_chapter(chapter, options.get('save', False))

    def _list_chapters(self, BookChapters, BookProjects):
        """List available chapters."""
        self.stdout.write(self.style.SUCCESS('\n📚 AVAILABLE PROJECTS & CHAPTERS'))
        self.stdout.write('=' * 60)
        
        projects = BookProjects.objects.all()[:10]
        self.stdout.write(f'\nProjects: {BookProjects.objects.count()} total')
        
        for project in projects:
            chapters = BookChapters.objects.filter(project=project)
            chapters_with_content = chapters.filter(
                Q(content__isnull=False) & ~Q(content='')
            )
            
            self.stdout.write(f'\n📖 {project.title or "Untitled"} (ID: {project.id})')
            self.stdout.write(f'   Owner: {project.owner or project.user or "Unknown"}')
            self.stdout.write(f'   Chapters: {chapters.count()} ({chapters_with_content.count()} with content)')
            
            for ch in chapters_with_content[:3]:
                content_len = len(ch.content or '')
                self.stdout.write(
                    f'   - Ch.{ch.chapter_number}: {ch.title or "Untitled"} '
                    f'({content_len} chars) ID: {ch.id}'
                )
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('To analyze: python manage.py analyze_chapter_quality --chapter-id <uuid>')

    def _get_chapter(self, options, BookChapters):
        """Get chapter by ID or project+number."""
        chapter_id = options.get('chapter_id')
        project_id = options.get('project_id')
        chapter_num = options.get('chapter_num')
        
        if chapter_id:
            try:
                return BookChapters.objects.get(id=chapter_id)
            except BookChapters.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Chapter not found: {chapter_id}'))
                return None
        
        if project_id and chapter_num:
            try:
                return BookChapters.objects.get(
                    project_id=project_id,
                    chapter_number=chapter_num
                )
            except BookChapters.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'Chapter {chapter_num} not found in project {project_id}'
                ))
                return None
        
        self.stdout.write(self.style.ERROR(
            'Specify --chapter-id or --project-id with --chapter-num'
        ))
        self.stdout.write('Use --list to see available chapters')
        return None

    def _analyze_chapter(self, chapter, save_results):
        """Analyze a single chapter."""
        self.stdout.write(self.style.SUCCESS(f'\n🔍 ANALYZING CHAPTER'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'Title: {chapter.title or "Untitled"}')
        self.stdout.write(f'Project: {chapter.project.title if chapter.project else "Unknown"}')
        self.stdout.write(f'Chapter #: {chapter.chapter_number}')
        self.stdout.write(f'Content: {len(chapter.content or "")} characters')
        
        if not chapter.content:
            self.stdout.write(self.style.ERROR('\n❌ Chapter has no content to analyze'))
            return
        
        # Get Style DNA
        style_dna = self._get_style_dna(chapter)
        
        # Analyze with service
        self.stdout.write('\n📊 Running Analysis...')
        
        try:
            from apps.writing_hub.services.style_quality_service import StyleQualityService
            
            service = StyleQualityService()
            
            # Create a mock DNA object if we have dict
            class MockDNA:
                def __init__(self, data):
                    self.name = data.get('name', 'Default')
                    self.signature_moves = data.get('signature_moves', [])
                    self.do_list = data.get('do_list', [])
                    self.dont_list = data.get('dont_list', [])
                    self.taboo_list = data.get('taboo_list', [])
            
            mock_dna = MockDNA(style_dna) if style_dna else MockDNA({
                'name': 'Default Analysis',
                'taboo_list': ['plötzlich', 'irgendwie', 'eigentlich'],
                'dont_list': ['Passiv-Konstruktionen', 'Füllwörter'],
            })
            
            result = service._analyze_rule_based(chapter.content, mock_dna)
            
            self.stdout.write(self.style.SUCCESS('\n✅ ANALYSIS RESULTS'))
            self.stdout.write('-' * 40)
            
            self.stdout.write('\n📈 Dimension Scores:')
            for dim, score in result.dimension_scores.items():
                bar = '█' * int(float(score)) + '░' * (10 - int(float(score)))
                self.stdout.write(f'   {dim}: {bar} {score}/10')
            
            self.stdout.write(f'\n⚠️ Issues Found: {len(result.issues)}')
            for issue in result.issues[:10]:
                issue_type = issue.get('issue_type_code', 'unknown')
                excerpt = issue.get('text_excerpt', '')[:60]
                self.stdout.write(f'   - [{issue_type}] {excerpt}...')
            
            if len(result.issues) > 10:
                self.stdout.write(f'   ... and {len(result.issues) - 10} more')
            
            # Save if requested
            if save_results:
                self._save_results(chapter, result, style_dna)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Analysis failed: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def _get_style_dna(self, chapter):
        """Get Style DNA for the chapter's author."""
        self.stdout.write('\n🧬 Loading Style DNA...')
        
        try:
            from apps.writing_hub.models import AuthorStyleDNA
            
            # Get author from project
            author = None
            if chapter.project:
                author = chapter.project.owner or chapter.project.user
            
            if not author:
                self.stdout.write('   ⚠️ No author found, using default rules')
                return None
            
            self.stdout.write(f'   Author: {author}')
            
            # Get primary DNA
            dna = AuthorStyleDNA.objects.filter(
                author=author,
                is_primary=True
            ).first()
            
            if not dna:
                dna = AuthorStyleDNA.objects.filter(author=author).first()
            
            if dna:
                self.stdout.write(f'   ✅ Found Style DNA: {dna.name}')
                return {
                    'name': dna.name,
                    'signature_moves': dna.signature_moves or [],
                    'do_list': dna.do_list or [],
                    'dont_list': dna.dont_list or [],
                    'taboo_list': dna.taboo_list or [],
                }
            else:
                self.stdout.write('   ⚠️ No Style DNA found for author')
                return None
                
        except Exception as e:
            self.stdout.write(f'   ⚠️ Error loading DNA: {e}')
            return None

    def _save_results(self, chapter, result, style_dna):
        """Save analysis results to database."""
        self.stdout.write('\n💾 Saving results...')
        
        try:
            from apps.writing_hub.models_quality import (
                ChapterQualityScore,
                ChapterDimensionScore,
                QualityDimension,
                GateDecisionType,
                StyleIssue,
                StyleIssueType,
            )
            from decimal import Decimal
            
            # Calculate overall score
            scores = list(result.dimension_scores.values())
            overall = sum(float(s) for s in scores) / len(scores) if scores else 5.0
            
            # Get gate decision based on score
            if overall >= 8.5:
                gate = GateDecisionType.objects.filter(code='approve').first()
            elif overall >= 7.0:
                gate = GateDecisionType.objects.filter(code='review').first()
            elif overall >= 5.0:
                gate = GateDecisionType.objects.filter(code='revise').first()
            else:
                gate = GateDecisionType.objects.filter(code='reject').first()
            
            if not gate:
                gate = GateDecisionType.objects.first()
            
            # Create quality score
            quality_score = ChapterQualityScore.objects.create(
                chapter=chapter,
                overall_score=Decimal(str(round(overall, 2))),
                gate_decision=gate,
                findings={
                    'style_dna': style_dna.get('name') if style_dna else None,
                    'issues_count': len(result.issues),
                }
            )
            
            self.stdout.write(f'   ✅ Created ChapterQualityScore: {quality_score.id}')
            
            # Create dimension scores
            for dim_code, score in result.dimension_scores.items():
                dimension = QualityDimension.objects.filter(code=dim_code).first()
                if dimension:
                    ChapterDimensionScore.objects.create(
                        quality_score=quality_score,
                        dimension=dimension,
                        score=score
                    )
            
            # Create style issues
            for issue_data in result.issues[:20]:  # Limit to 20
                issue_type = StyleIssueType.objects.filter(
                    code=issue_data.get('issue_type_code')
                ).first()
                
                if issue_type:
                    StyleIssue.objects.create(
                        quality_score=quality_score,
                        issue_type=issue_type,
                        text_excerpt=issue_data.get('text_excerpt', '')[:500],
                        suggestion=issue_data.get('suggestion', ''),
                        explanation=issue_data.get('explanation', ''),
                    )
            
            self.stdout.write(self.style.SUCCESS(f'   ✅ Saved {len(result.issues)} issues'))
            self.stdout.write(f'   Gate Decision: {gate.name_de if gate else "Unknown"}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Save failed: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
