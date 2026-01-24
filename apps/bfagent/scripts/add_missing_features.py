"""
Add missing features to Feature Planning Registry
Run: python manage.py shell < scripts/add_missing_features.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.bfagent.models import ComponentRegistry, ComponentType, ComponentStatus
from django.utils import timezone

# Define all missing features
MISSING_FEATURES = [
    {
        "name": "DomainModel",
        "component_type": ComponentType.MODEL,
        "description": "Database-driven Domain model to replace free-text domain field. Includes code, name, description, color, icon for consistent domain management across the system.",
        "priority": "high",
        "domain": "shared",
        "benefits": "Consistent naming, validation, dropdown selection, color-coding in UI, domain statistics",
    },
    {
        "name": "QuickStatusChangeDropdown",
        "component_type": ComponentType.UI_COMPONENT,
        "description": "Inline status change dropdown in feature list for quick status updates without opening edit modal. HTMX-driven partial update.",
        "priority": "medium",
        "domain": "book",
        "benefits": "Faster workflow, less clicks, better UX",
    },
    {
        "name": "FeatureDependencyTracking",
        "component_type": ComponentType.MODEL,
        "description": "Track dependencies between features (requires/blocks relationships). M2M model for feature dependencies with validation to prevent circular dependencies.",
        "priority": "medium",
        "domain": "shared",
        "benefits": "Better planning, clear relationships, dependency graph visualization",
    },
    {
        "name": "FeatureTaggingSystem",
        "component_type": ComponentType.MODEL,
        "description": "Flexible tagging system for features (e.g., 'ui', 'backend', 'api', 'urgent', 'refactoring'). Many-to-many relationship with autocomplete.",
        "priority": "low",
        "domain": "shared",
        "benefits": "Better organization, advanced filtering, tag clouds",
    },
    {
        "name": "FeatureStatisticsCharts",
        "component_type": ComponentType.UI_COMPONENT,
        "description": "Interactive charts for feature statistics: timeline, status distribution, priority breakdown, domain overview. Use Chart.js or similar.",
        "priority": "medium",
        "domain": "shared",
        "benefits": "Visual insights, trend analysis, management overview",
    },
    {
        "name": "FeatureExportImport",
        "component_type": ComponentType.UTILITY,
        "description": "Export features to CSV/JSON for backup and sharing. Import features from external sources. Validation and duplicate detection.",
        "priority": "low",
        "domain": "shared",
        "benefits": "Data portability, backup, integration with external tools",
    },
    {
        "name": "FeatureAuditTrail",
        "component_type": ComponentType.MODEL,
        "description": "Complete audit trail for all feature changes. Track who changed what and when. Uses django-simple-history or custom solution.",
        "priority": "medium",
        "domain": "shared",
        "benefits": "Accountability, debugging, compliance, rollback capability",
    },
    {
        "name": "FeatureNotificationSystem",
        "component_type": ComponentType.INTEGRATION,
        "description": "Notify stakeholders on status changes, assignments, comments. Email, Slack, or in-app notifications. Configurable per user.",
        "priority": "low",
        "domain": "shared",
        "benefits": "Better communication, timely updates, team coordination",
    },
    {
        "name": "AdvancedFeatureSearch",
        "component_type": ComponentType.UI_COMPONENT,
        "description": "Full-text search with PostgreSQL full-text search or Elasticsearch. Combined filters, saved searches, search history.",
        "priority": "medium",
        "domain": "shared",
        "benefits": "Find features quickly, complex queries, power user features",
    },
    {
        "name": "DomainSpecificViewsMedTrans",
        "component_type": ComponentType.VIEW,
        "description": "Domain-specific feature planning view for Medical Translation app. Filter by 'medtrans' domain, integrate into medtrans navigation.",
        "priority": "medium",
        "domain": "medtrans",
        "benefits": "Domain isolation, focused workflow, clear ownership",
    },
    {
        "name": "DomainSpecificViewsExplosion",
        "component_type": ComponentType.VIEW,
        "description": "Domain-specific feature planning view for Explosion app. Filter by 'explosion' domain, integrate into explosion navigation.",
        "priority": "low",
        "domain": "explosion",
        "benefits": "Domain isolation, focused workflow, clear ownership",
    },
    {
        "name": "DynamicURLPatternRollout",
        "component_type": ComponentType.REFACTORING,
        "description": "Apply dynamic URL pattern (from feature_planning_views) to all CRUD views. Reduces template code by 75%, improves maintainability.",
        "priority": "high",
        "domain": "shared",
        "benefits": "DRY principle, less code, easier maintenance, namespace-agnostic",
    },
    {
        "name": "AccessibilityImprovements",
        "component_type": ComponentType.REFACTORING,
        "description": "Fix all accessibility warnings: add aria-labels, titles to buttons/selects, proper form labels, keyboard navigation support.",
        "priority": "medium",
        "domain": "shared",
        "benefits": "Better accessibility, WCAG compliance, screen reader support",
    },
    {
        "name": "CodeQualityCleanup",
        "component_type": ComponentType.REFACTORING,
        "description": "Fix linting warnings: remove unused imports (Count, messages), fix module-level imports, remove trailing whitespace, clean up blank lines.",
        "priority": "low",
        "domain": "shared",
        "benefits": "Cleaner code, better maintainability, reduced technical debt",
    },
    {
        "name": "FeatureBulkOperations",
        "component_type": ComponentType.UI_COMPONENT,
        "description": "Bulk operations for features: multi-select checkboxes, bulk status change, bulk delete, bulk tag assignment. Improves efficiency for power users.",
        "priority": "medium",
        "domain": "shared",
        "benefits": "Batch processing, efficiency, admin convenience",
    },
    {
        "name": "FeatureCommentSystem",
        "component_type": ComponentType.MODEL,
        "description": "Add comments/discussion threads to features. Users can discuss implementation details, blockers, questions. Real-time updates with HTMX.",
        "priority": "medium",
        "domain": "shared",
        "benefits": "Collaboration, documentation, context preservation",
    },
    {
        "name": "FeatureEstimationTracking",
        "component_type": ComponentType.MODEL,
        "description": "Track effort estimates (story points, hours), actual time spent, velocity metrics. Integration with time tracking tools.",
        "priority": "low",
        "domain": "shared",
        "benefits": "Project planning, capacity planning, velocity tracking",
    },
    {
        "name": "FeatureMilestones",
        "component_type": ComponentType.MODEL,
        "description": "Group features into milestones/releases. Roadmap view, milestone progress tracking, deadline management.",
        "priority": "high",
        "domain": "shared",
        "benefits": "Release planning, roadmap visibility, deadline tracking",
    },
]

print("=" * 80)
print("ADDING MISSING FEATURES TO REGISTRY")
print("=" * 80)

created_count = 0
skipped_count = 0

for feature_data in MISSING_FEATURES:
    name = feature_data["name"]
    
    # Check if exists
    identifier = f"proposed.{feature_data['component_type']}.{name.lower()}"
    
    if ComponentRegistry.objects.filter(identifier=identifier).exists():
        print(f"⏭️  SKIP: {name} (already exists)")
        skipped_count += 1
        continue
    
    # Create feature
    feature = ComponentRegistry.objects.create(
        identifier=identifier,
        name=name,
        component_type=feature_data["component_type"],
        description=feature_data["description"],
        priority=feature_data["priority"],
        domain=feature_data["domain"],
        status=ComponentStatus.PROPOSED,
        proposed_at=timezone.now(),
        module_path='',
        file_path='',
    )
    
    print(f"✅ CREATED: {name} [{feature_data['component_type']}] - {feature_data['priority']} priority")
    created_count += 1

print("=" * 80)
print(f"SUMMARY: {created_count} created, {skipped_count} skipped")
print("=" * 80)
