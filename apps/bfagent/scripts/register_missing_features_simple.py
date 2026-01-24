"""
Register Missing Features - Simplified Version
Focus on: LLM Integration, Handler Migration, UI Improvements

Run: python manage.py shell
>>> exec(open('scripts/register_missing_features_simple.py', encoding='utf-8').read())
"""

import os
import sys
import django

# Fix Windows UTF-8 encoding
os.environ.setdefault("PYTHONUTF8", "1")
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.models import ComponentRegistry, ComponentType, ComponentStatus
from django.utils import timezone

# Priority features to register
FEATURES = [
    # LLM INTEGRATION - CRITICAL
    ("LLMCharacterGeneration", ComponentType.SERVICE, "critical", "book",
     "LLM-based character generation to replace sample data. Full profiles with personality, backstory, goals, conflicts."),
    
    ("LLMWorldBuilding", ComponentType.SERVICE, "critical", "book",
     "LLM-based world building - settings, cultures, geography, magic systems, technology levels."),
    
    ("LLMOutlineGeneration", ComponentType.SERVICE, "critical", "book",
     "Story outline generation with chapter structure, story arcs, pacing, climaxes."),
    
    ("LLMChapterEnhancement", ComponentType.SERVICE, "high", "book",
     "Enhanced LLM integration for chapters - multiple providers, streaming, context management."),
    
    # HANDLER MIGRATION
    ("BookCreateHandler", ComponentType.HANDLER, "high", "book",
     "Central handler for book creation. Move business logic from views to handler."),
    
    ("ChapterGenerateHandler", ComponentType.HANDLER, "high", "book",
     "Handler for chapter generation workflow. Orchestrate LLM calls, validation, storage."),
    
    ("CharacterEnrichHandler", ComponentType.HANDLER, "high", "book",
     "Handler for character enrichment. Deep development, traits, relationships, arcs."),
    
    # UI IMPROVEMENTS
    ("DomainModel", ComponentType.MODEL, "high", "shared",
     "Database-driven Domain model with code, name, description, color, icon."),
    
    ("QuickStatusChangeDropdown", ComponentType.TEMPLATE, "medium", "shared",
     "Inline status change dropdown without modal. HTMX-driven partial update."),
    
    ("AIGenerationUIIntegration", ComponentType.TEMPLATE, "medium", "book",
     "Real-time AI generation UI with progress tracking and cancel support."),
    
    ("FieldValueHistoryViewer", ComponentType.TEMPLATE, "medium", "book",
     "Modal for field history timeline with diff view and restore capability."),
    
    # GENAGENT CONVERGENCE
    ("PhaseModelIntegration", ComponentType.MODEL, "high", "book",
     "Add Phase model to bfagent for workflow stages. Bridge to genagent architecture."),
    
    ("PhaseManagementUI", ComponentType.TEMPLATE, "medium", "book",
     "UI for phase management - create, assign, track progress, visualize workflow."),
    
    # ADVANCED FEATURES
    ("FeatureDependencyTracking", ComponentType.MODEL, "medium", "shared",
     "M2M model for feature dependencies. Requires/blocks relationships, circular prevention."),
    
    ("FeatureStatisticsCharts", ComponentType.TEMPLATE, "medium", "shared",
     "Interactive charts: timeline, status distribution, priority breakdown using Chart.js."),
    
    ("FeatureMilestones", ComponentType.MODEL, "high", "shared",
     "Group features into milestones/releases. Roadmap view, progress tracking, deadlines."),
    
    ("FeatureAuditTrail", ComponentType.MODEL, "medium", "shared",
     "Complete audit trail for feature changes using django-simple-history."),
    
    ("FeatureBulkOperations", ComponentType.TEMPLATE, "medium", "shared",
     "Multi-select checkboxes, bulk status change, bulk delete, bulk tag assignment."),
    
    ("FeatureCommentSystem", ComponentType.MODEL, "medium", "shared",
     "Discussion threads for features with real-time HTMX updates and mentions."),
    
    # REFACTORING
    ("DynamicURLPatternRollout", ComponentType.UTILITY, "high", "shared",
     "Apply dynamic URL pattern to ALL CRUD views. 75% less template code."),
    
    ("AccessibilityImprovements", ComponentType.UTILITY, "medium", "shared",
     "Fix all accessibility warnings - aria-labels, titles, keyboard navigation."),
    
    ("EnrichmentHandlerRefactoring", ComponentType.UTILITY, "high", "book",
     "Migrate enrichment logic from enrichment_views.py to central handlers."),
    
    # HANDLER SYSTEM - MISSING HANDLERS
    ("LLMCallProcessingHandler", ComponentType.HANDLER, "high", "shared",
     "PROCESSING handler for LLM API calls. Multi-provider, retry logic, streaming."),
    
    ("ChaptersOutputHandler", ComponentType.HANDLER, "high", "book",
     "OUTPUT handler for chapter content. Save generated chapters, versioning, metadata."),
    
    ("CharactersOutputHandler", ComponentType.HANDLER, "medium", "book",
     "OUTPUT handler for character data. Save profiles, relationships, updates."),
    
    # MEDTRANS INTEGRATION
    ("TranslationHandler", ComponentType.HANDLER, "high", "medtrans",
     "Handler for DeepL API translation. PPTX text extraction, translation, reintegration."),
    
    ("DomainSpecificViewsMedTrans", ComponentType.VIEW, "medium", "medtrans",
     "Domain-specific feature planning view for Medical Translation app."),
    
    # CONTROL CENTER
    ("ControlCenterBookWritingSection", ComponentType.VIEW, "medium", "shared",
     "Control Center section for BookWriting master data - templates, types, agents."),
    
    ("MasterDataIdentification", ComponentType.UTILITY, "medium", "shared",
     "Identify and document all master data vs operative data. Create migration plan."),
]

print("=" * 80)
print("REGISTERING MISSING FEATURES")
print("=" * 80)

created = 0
skipped = 0

for name, comp_type, priority, domain, description in FEATURES:
    identifier = f"proposed.{comp_type}.{name.lower()}"
    
    if ComponentRegistry.objects.filter(identifier=identifier).exists():
        print(f"⏭️  SKIP: {name}")
        skipped += 1
        continue
    
    ComponentRegistry.objects.create(
        identifier=identifier,
        name=name,
        component_type=comp_type,
        description=description,
        priority=priority,
        domain=domain,
        status=ComponentStatus.PROPOSED,
        proposed_at=timezone.now(),
        module_path='',
        file_path='',
    )
    
    print(f"✅ {name} [{comp_type}] - {priority}")
    created += 1

print("=" * 80)
print(f"DONE: {created} created, {skipped} skipped")
print(f"Total features in registry: {ComponentRegistry.objects.filter(status=ComponentStatus.PROPOSED).count()}")
print("=" * 80)
