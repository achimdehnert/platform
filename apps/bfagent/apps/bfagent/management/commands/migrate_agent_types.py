"""
Django Management Command: Migrate Agent Types to AgentType Table
Migrates existing agent_type CharField data to new AgentType ForeignKey

Usage:
  python manage.py migrate_agent_types --dry-run  # Preview migration
  python manage.py migrate_agent_types             # Execute migration
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.bfagent.models import Agents, AgentType


class Command(BaseCommand):
    help = "Migrate agent_type CharField to AgentType ForeignKey"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be migrated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🔄 AGENT TYPE MIGRATION"))
        self.stdout.write("=" * 80)

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n⚠️  DRY-RUN MODE - No changes will be made\n")
            )

        # Step 1: Extract unique agent_types from Agents table
        self.stdout.write("\n📊 Step 1: Analyzing existing agent types...")
        
        # Get all unique agent_type values (CharField)
        unique_types = (
            Agents.objects.values_list("agent_type", flat=True)
            .distinct()
            .exclude(agent_type__isnull=True)
            .order_by("agent_type")
        )
        
        unique_types_list = list(unique_types)
        self.stdout.write(f"Found {len(unique_types_list)} unique agent types:")
        
        for agent_type in unique_types_list:
            count = Agents.objects.filter(agent_type=agent_type).count()
            self.stdout.write(f"  - {agent_type} ({count} agents)")

        # Step 2: Normalize and create/reuse AgentType entries
        self.stdout.write("\n📝 Step 2: Creating/Reusing AgentType entries...")
        
        created_types = {}
        created_count = 0
        reused_count = 0
        
        for old_type in unique_types_list:
            # Normalize: lowercase, remove _AGENT suffix
            normalized_name = old_type.replace("_AGENT", "").lower()
            
            # Generate display name: Title Case with spaces
            if "_" in normalized_name:
                display_name = normalized_name.replace("_", " ").title() + " Agent"
            else:
                display_name = normalized_name.title() + " Agent"
            
            # Check if already exists (use get_or_create to handle existing entries)
            if not dry_run:
                agent_type_obj, created = AgentType.objects.get_or_create(
                    name=normalized_name,
                    defaults={
                        "display_name": display_name,
                        "description": f"Agent type for {display_name.lower()} tasks",
                        "is_active": True,
                    },
                )
                created_types[old_type] = agent_type_obj
                if created:
                    created_count += 1
                    status = "✅ Created"
                    self.stdout.write(
                        f"  {status}: {display_name} (name: {normalized_name})"
                    )
                else:
                    reused_count += 1
                    status = "♻️  Reused"
                    self.stdout.write(
                        f"  {status}: {agent_type_obj.display_name} (name: {normalized_name}) - already exists"
                    )
            else:
                self.stdout.write(
                    f"  Would create: {display_name} (name: {normalized_name})"
                )

        # Step 3: Update Agents to use ForeignKey
        self.stdout.write("\n🔗 Step 3: Linking agents to new AgentType...")
        
        updated_count = 0
        errors = []
        
        if not dry_run:
            with transaction.atomic():
                for old_type, agent_type_obj in created_types.items():
                    # Find agents by current agent_type CharField value
                    agents_to_update = Agents.objects.filter(agent_type=old_type)
                    count = agents_to_update.count()
                    
                    try:
                        # Update CharField value to normalized name
                        # Note: This updates the CharField, not a ForeignKey yet
                        # Later migration will convert CharField -> ForeignKey
                        for agent in agents_to_update:
                            agent.agent_type = agent_type_obj.name
                            agent.save()
                        
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✅ Updated {count} agents from '{old_type}' -> '{agent_type_obj.name}'"
                            )
                        )
                        updated_count += count
                        
                    except Exception as e:
                        error_msg = f"Error updating agents with type '{old_type}': {str(e)}"
                        self.stdout.write(self.style.ERROR(f"  ❌ {error_msg}"))
                        errors.append(error_msg)
        else:
            # Dry run - just count
            for old_type in unique_types_list:
                count = Agents.objects.filter(agent_type=old_type).count()
                self.stdout.write(f"  Would update {count} agents with type '{old_type}'")
                updated_count += count

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 MIGRATION SUMMARY"))
        self.stdout.write("=" * 80)

        if not dry_run:
            self.stdout.write(f"\n✅ AgentTypes Created: {created_count}")
            self.stdout.write(f"♻️  AgentTypes Reused: {reused_count}")
            self.stdout.write(f"✅ Agents Updated: {updated_count}")
            
            if errors:
                self.stdout.write(f"\n❌ Errors: {len(errors)}")
                for error in errors:
                    self.stdout.write(f"  - {error}")
        else:
            self.stdout.write(f"\nWould create: {len(unique_types_list)} AgentTypes")
            self.stdout.write(f"Would update: {updated_count} Agents")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  This was a DRY-RUN. Run without --dry-run to execute migration."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Migration completed successfully!")
            )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ MIGRATION COMPLETE"))
        self.stdout.write("=" * 80)

        # Recommendations
        self.stdout.write("\n💡 Next Steps:")
        self.stdout.write("  1. Verify AgentType entries at: http://localhost:8080/agenttype/")
        self.stdout.write("  2. Check Agents are correctly linked")
        self.stdout.write("  3. Update forms and filters to use AgentType")
