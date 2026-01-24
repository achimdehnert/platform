import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import BookTypePhase, BookTypes, WorkflowPhase

# BookType ID 25 (Short Story)
booktype_id = 25
bt = BookTypes.objects.get(pk=booktype_id)
print(f"BookType: {bt.name} (ID: {bt.id})")
print(f"Is active: {bt.is_active}")
print()

# Assigned phases
assigned_configs = BookTypePhase.objects.filter(book_type=bt).select_related("phase")
print(f"Assigned Phases: {assigned_configs.count()}")
for config in assigned_configs:
    print(f"  - {config.phase.name} (ID: {config.phase.id})")
print()

# All active phases
phases = WorkflowPhase.objects.filter(is_active=True)
print(f"Total Active Phases: {phases.count()}")
print()

# Unassigned phases
assigned_phase_ids = [config.phase_id for config in assigned_configs]
unassigned = phases.exclude(id__in=assigned_phase_ids)
print(f"Unassigned Phases: {unassigned.count()}")
for phase in unassigned[:10]:
    print(f"  - {phase.name} (ID: {phase.id})")
