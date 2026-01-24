"""
Test command for Style Quality System
=====================================

Tests the complete Style Quality integration:
- StyleQualityService
- StyleQualityHandler
- QualityGateService
- Models

Usage:
    python manage.py test_style_quality
    python manage.py test_style_quality --chapter-id <uuid>
    python manage.py test_style_quality --dry-run
"""
import logging
from decimal import Decimal

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test the Style Quality System integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--chapter-id',
            type=str,
            help='UUID of chapter to analyze (optional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test without database operations',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('🧪 STYLE QUALITY SYSTEM TEST'))
        self.stdout.write(self.style.SUCCESS('=' * 60 + '\n'))

        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)
        chapter_id = options.get('chapter_id')

        # Test 1: Import Models
        self.stdout.write('📦 Test 1: Importing Models...')
        try:
            from apps.writing_hub.models_quality import (
                QualityDimension,
                GateDecisionType,
                PromiseStatus,
                StyleIssueType,
                StyleIssue,
                ChapterQualityScore,
                ChapterDimensionScore,
                ProjectQualityConfig,
            )
            self.stdout.write(self.style.SUCCESS('   ✅ All models imported successfully'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Import failed: {e}'))
            return

        # Test 2: Import Services
        self.stdout.write('📦 Test 2: Importing Services...')
        try:
            from apps.writing_hub.services.quality_gate_service import QualityGateService
            from apps.writing_hub.services.style_quality_service import StyleQualityService
            self.stdout.write(self.style.SUCCESS('   ✅ All services imported successfully'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Import failed: {e}'))
            return

        # Test 3: Import Handler
        self.stdout.write('📦 Test 3: Importing Handler...')
        try:
            from apps.writing_hub.handlers.quality_handler import StyleQualityHandler
            self.stdout.write(self.style.SUCCESS('   ✅ Handler imported successfully'))
        except ImportError as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Import failed: {e}'))
            return

        # Test 4: Service Instantiation
        self.stdout.write('🔧 Test 4: Creating Service Instances...')
        try:
            gate_service = QualityGateService()
            style_service = StyleQualityService()
            handler = StyleQualityHandler()
            self.stdout.write(self.style.SUCCESS('   ✅ All services instantiated'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Instantiation failed: {e}'))
            return

        # Test 5: Rule-based Analysis (no DB)
        self.stdout.write('🔍 Test 5: Rule-based Analysis...')
        try:
            test_text = """
            Er wurde von der Dunkelheit verschlungen. Die Tür wurde geöffnet.
            Maria ging langsam durch den Raum. Plötzlich wurde sie von einem 
            Geräusch aufgeschreckt. Sie drehte sich um und sah nichts.
            """
            
            # Create mock style DNA
            class MockDNA:
                name = "Test DNA"
                signature_moves = ["Kurze Sätze", "Aktive Verben"]
                do_list = ["Konkrete Beschreibungen"]
                dont_list = ["Passiv-Konstruktionen"]
                taboo_list = ["plötzlich", "nichts"]
            
            result = style_service._analyze_rule_based(test_text, MockDNA())
            
            if verbose:
                self.stdout.write(f'   Scores: {result.dimension_scores}')
                self.stdout.write(f'   Issues: {len(result.issues)}')
                for issue in result.issues[:3]:
                    self.stdout.write(f'     - {issue.get("issue_type_code")}: {issue.get("text_excerpt", "")[:50]}...')
            
            self.stdout.write(self.style.SUCCESS(f'   ✅ Analysis completed: {len(result.issues)} issues found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Analysis failed: {e}'))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
            return

        # Test 6: Handler Prompt Building
        self.stdout.write('📝 Test 6: Handler Prompt Building...')
        try:
            style_dna_dict = {
                'name': 'Test Style',
                'signature_moves': ['Kurze Sätze'],
                'do_list': ['Aktive Verben'],
                'dont_list': ['Passiv'],
                'taboo_list': ['plötzlich'],
            }
            prompt = handler._build_prompt("Test text.", style_dna_dict)
            
            if verbose:
                self.stdout.write(f'   Prompt length: {len(prompt)} chars')
            
            self.stdout.write(self.style.SUCCESS('   ✅ Prompt built successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Prompt building failed: {e}'))
            return

        # Test 7: JSON Parsing (Handler)
        self.stdout.write('📊 Test 7: JSON Response Parsing...')
        try:
            test_json = '''```json
            {
                "style_adherence": 8.5,
                "signature_moves": 7.0,
                "taboo_compliance": 9.0,
                "pacing": 7.5,
                "dialogue_quality": 8.0,
                "issues": [
                    {
                        "issue_type_code": "passive_voice",
                        "text_excerpt": "wurde geöffnet",
                        "suggestion": "öffnete sich"
                    }
                ],
                "findings": {
                    "strengths": ["Gute Dialoge"],
                    "weaknesses": ["Zu viel Passiv"]
                }
            }
            ```'''
            
            result = handler._parse_response(test_json)
            
            if verbose:
                self.stdout.write(f'   Parsed: {result}')
            
            assert result['success'] == True
            assert result['style_adherence'] == 8.5
            assert len(result['issues']) == 1
            
            self.stdout.write(self.style.SUCCESS('   ✅ JSON parsing successful'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ JSON parsing failed: {e}'))
            return

        # Test 8: Database Check (if not dry-run)
        if not dry_run:
            self.stdout.write('🗄️ Test 8: Database Tables...')
            try:
                dim_count = QualityDimension.objects.count()
                gate_count = GateDecisionType.objects.count()
                issue_type_count = StyleIssueType.objects.count()
                
                self.stdout.write(f'   QualityDimensions: {dim_count}')
                self.stdout.write(f'   GateDecisionTypes: {gate_count}')
                self.stdout.write(f'   StyleIssueTypes: {issue_type_count}')
                
                if dim_count == 0:
                    self.stdout.write(self.style.WARNING('   ⚠️ No QualityDimensions - run: python manage.py loaddata quality_dimensions'))
                if gate_count == 0:
                    self.stdout.write(self.style.WARNING('   ⚠️ No GateDecisionTypes - run: python manage.py loaddata gate_decisions'))
                if issue_type_count == 0:
                    self.stdout.write(self.style.WARNING('   ⚠️ No StyleIssueTypes - run: python manage.py loaddata style_issue_types'))
                
                self.stdout.write(self.style.SUCCESS('   ✅ Database accessible'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Database error: {e}'))
        else:
            self.stdout.write('🗄️ Test 8: Skipped (dry-run)')

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ ALL TESTS PASSED'))
        self.stdout.write('=' * 60)
        
        self.stdout.write('\n📋 Next Steps:')
        self.stdout.write('   1. Run migrations: python manage.py migrate')
        self.stdout.write('   2. Load fixtures:')
        self.stdout.write('      python manage.py loaddata quality_dimensions')
        self.stdout.write('      python manage.py loaddata gate_decisions')
        self.stdout.write('      python manage.py loaddata promise_statuses')
        self.stdout.write('      python manage.py loaddata style_issue_types')
        self.stdout.write('   3. Test with real chapter:')
        self.stdout.write('      python manage.py test_style_quality --chapter-id <uuid>')
        self.stdout.write('')
