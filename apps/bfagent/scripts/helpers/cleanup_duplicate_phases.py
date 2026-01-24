"""
Management Command: Cleanup Duplicate Phases

Removes duplicate phases keeping only the first occurrence of each unique name.
"""

from django.core.management.base import BaseCommand
from apps.genagent.models import Phase


class Command(BaseCommand):
    help = 'Remove duplicate phases keeping only the first occurrence'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🔍 Scanning for duplicate phases...'))
        
        # Get all phases
        all_phases = Phase.objects.all().order_by('id')
        
        seen_names = set()
        duplicates_to_delete = []
        kept_phases = []
        
        for phase in all_phases:
            if phase.name in seen_names:
                duplicates_to_delete.append(phase)
            else:
                seen_names.add(phase.name)
                kept_phases.append(phase)
        
        if not duplicates_to_delete:
            self.stdout.write(self.style.SUCCESS('✅ No duplicate phases found!'))
            return
        
        self.stdout.write(self.style.WARNING(f'\n📋 Found {len(duplicates_to_delete)} duplicate phases:'))
        for phase in duplicates_to_delete:
            self.stdout.write(f'   - ID {phase.id}: {phase.name}')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Keeping {len(kept_phases)} unique phases:'))
        for phase in kept_phases:
            self.stdout.write(f'   - ID {phase.id}: {phase.name} (Order: {phase.order})')
        
        # Reassign actions first
        self.stdout.write(self.style.WARNING('\n🔄 Reassigning actions from duplicates to kept phases...'))
        
        # Create mapping: phase_name -> kept_phase
        kept_phase_map = {p.name: p for p in kept_phases}
        
        total_reassigned = 0
        for dup_phase in duplicates_to_delete:
            actions = dup_phase.actions.all()
            if actions.count() > 0:
                # Find the kept phase with same name
                target_phase = kept_phase_map.get(dup_phase.name)
                if target_phase:
                    for action in actions:
                        action.phase = target_phase
                        action.save()
                        total_reassigned += 1
                    self.stdout.write(
                        f'   ✅ Reassigned {actions.count()} actions from '
                        f'Phase ID {dup_phase.id} → Phase ID {target_phase.id} "{target_phase.name}"'
                    )
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Reassigned {total_reassigned} actions total'))
        
        # Delete duplicates
        self.stdout.write(self.style.WARNING('\n🗑️  Deleting duplicate phases...'))
        deleted_count = 0
        for phase in duplicates_to_delete:
            phase.delete()
            deleted_count += 1
            self.stdout.write(f'   ✅ Deleted: ID {phase.id} - {phase.name}')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 Cleanup complete!'))
        self.stdout.write(f'   Kept: {len(kept_phases)} phases')
        self.stdout.write(f'   Reassigned: {total_reassigned} actions')
        self.stdout.write(f'   Deleted: {deleted_count} duplicate phases')
