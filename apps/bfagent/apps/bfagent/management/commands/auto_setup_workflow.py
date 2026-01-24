"""
Django Management Command: Auto-Setup Workflow
Automatically creates missing PhaseActionConfigs and optionally PromptTemplates

Usage:
  python manage.py auto_setup_workflow --dry-run  # Preview only
  python manage.py auto_setup_workflow             # Create configs
  python manage.py auto_setup_workflow --with-templates  # Also create templates
"""

from django.core.management.base import BaseCommand

from apps.bfagent.models import AgentAction, PhaseActionConfig, PromptTemplate, WorkflowPhase


class Command(BaseCommand):
    help = "Auto-setup workflow: Create PhaseActionConfigs and PromptTemplates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without actually creating",
        )
        parser.add_argument(
            "--with-templates",
            action="store_true",
            help="Also create basic PromptTemplates for actions without templates",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        with_templates = options["with_templates"]

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("🚀 AUTO-SETUP WORKFLOW"))
        self.stdout.write("=" * 80)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  DRY-RUN MODE - No changes will be made\n"))

        # Define intelligent phase-action mapping
        phase_action_mapping = {
            "Planning": [
                ("Generate Prompt Template", 1, True),
                ("Generate Character Cast", 2, True),
                ("Track Progress", 3, False),
            ],
            "Outlining": [
                ("Generate Full Outline", 1, True),
                ("Refine Outline", 2, False),
                ("Generate Plot Points", 3, True),
                ("Analyze Pacing", 4, False),
            ],
            "World Building": [
                ("Expand World Details", 1, True),
                ("Develop Conflict", 2, True),
                ("Analyze World Consistency", 3, False),
            ],
            "Character Development": [
                ("Generate Character Cast", 1, True),
                ("Derive Characters from Outline", 2, True),
                ("Develop Character Backstory", 3, False),
                ("Analyze Character Arc", 4, False),
            ],
            "Writing": [
                ("Generate Chapter Outline", 1, True),
                ("Write Chapter Draft", 2, True),
                ("Expand Scene", 3, False),
                ("Enhance Description", 4, False),
                ("Add Dialogue", 5, False),
            ],
            "Revision": [
                ("Check Consistency", 1, True),
                ("Check Character Voice", 2, True),
                ("Check Timeline", 3, True),
                ("Check Arc Consistency", 4, False),
                ("Identify Plot Holes", 5, False),
            ],
            "Editing": [
                ("Improve Prose", 1, True),
                ("Improve Flow", 2, False),
                ("Enhance Description", 3, False),
            ],
            "Review": [
                ("Calculate Consistency Score", 1, True),
                ("Check Setting", 2, False),
                ("Suggest Arc Improvements", 3, False),
            ],
            "Publishing": [
                ("Estimate Completion Time", 1, False),
                ("Track Progress", 2, False),
            ],
            "Finalization": [
                ("Summarize Chapter", 1, False),
                ("Suggest Next Steps", 2, False),
            ],
        }

        created_configs = 0
        skipped_configs = 0
        created_templates = 0
        errors = []

        # Process each phase
        for phase_name, action_configs in phase_action_mapping.items():
            self.stdout.write(f"\n{'=' * 80}")
            self.stdout.write(self.style.WARNING(f"📌 PHASE: {phase_name}"))
            self.stdout.write("=" * 80)

            try:
                phase = WorkflowPhase.objects.get(name=phase_name)
            except WorkflowPhase.DoesNotExist:
                error = f"Phase '{phase_name}' not found in database!"
                self.stdout.write(self.style.ERROR(f"  ❌ {error}"))
                errors.append(error)
                continue

            for action_name, order, is_required in action_configs:
                try:
                    # Find action by display_name or name
                    action = AgentAction.objects.filter(display_name=action_name).first()

                    if not action:
                        # Try by internal name
                        action = AgentAction.objects.filter(
                            name__icontains=action_name.lower().replace(" ", "_")
                        ).first()

                    if not action:
                        error = f"Action '{action_name}' not found"
                        self.stdout.write(self.style.ERROR(f"  ❌ {error}"))
                        errors.append(error)
                        continue

                    # Check if PhaseActionConfig already exists
                    existing = PhaseActionConfig.objects.filter(phase=phase, action=action).first()

                    if existing:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⚠️  Config already exists: {action.display_name} (skipped)"
                            )
                        )
                        skipped_configs += 1
                        continue

                    # Create PhaseActionConfig
                    if not dry_run:
                        PhaseActionConfig.objects.create(
                            phase=phase,
                            action=action,
                            is_required=is_required,
                            order=order,
                            description=f"Auto-created config for {action.display_name}",
                        )

                    required_text = "Required" if is_required else "Optional"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Created: {action.display_name} (Order: {order}, {required_text})"
                        )
                    )
                    created_configs += 1

                    # Create PromptTemplate if requested
                    if with_templates and not action.prompt_template:
                        template_name = f"{action.agent.name} - {action.display_name}"
                        template_text = f"""You are tasked with: {action.display_name}

Agent: {action.agent.name}
Description: {action.description or 'No description provided'}

Please perform this action based on the provided context and input.

Context:
{{{{ context }}}}

Input:
{{{{ input }}}}

Provide your response in a clear, structured format."""

                        if not dry_run:
                            template = PromptTemplate.objects.create(
                                name=template_name,
                                description=f"Auto-generated template for {action.display_name}",
                                template_text=template_text,
                                agent=action.agent,
                                version=1,
                            )
                            action.prompt_template = template
                            action.save()

                        self.stdout.write(
                            self.style.SUCCESS(f"    📝 Created template: {template_name}")
                        )
                        created_templates += 1

                except Exception as e:
                    error = f"Error processing '{action_name}': {str(e)}"
                    self.stdout.write(self.style.ERROR(f"  ❌ {error}"))
                    errors.append(error)

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 SUMMARY"))
        self.stdout.write("=" * 80)

        self.stdout.write(f"\n✅ PhaseActionConfigs Created: {created_configs}")
        self.stdout.write(f"⚠️  PhaseActionConfigs Skipped: {skipped_configs}")

        if with_templates:
            self.stdout.write(f"📝 PromptTemplates Created: {created_templates}")

        if errors:
            self.stdout.write(f"\n❌ Errors: {len(errors)}")
            for error in errors:
                self.stdout.write(f"  - {error}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  This was a DRY-RUN. Run without --dry-run to actually create."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Successfully created {created_configs} PhaseActionConfigs!"
                )
            )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ AUTO-SETUP COMPLETE"))
        self.stdout.write("=" * 80)

        # Recommend next steps
        self.stdout.write("\n💡 Next Steps:")
        self.stdout.write("  1. Run: python manage.py check_workflow")
        self.stdout.write("  2. Review configs at: http://localhost:9000/phaseactionconfig/")
        if with_templates:
            self.stdout.write("  3. Review templates at: http://localhost:9000/prompt-templates/")
