"""
Django Management Command: Create Missing PromptTemplates
Automatically creates basic PromptTemplates for all AgentActions without templates

Usage:
  python manage.py create_templates --dry-run  # Preview only
  python manage.py create_templates            # Create templates
"""

from django.core.management.base import BaseCommand

from apps.bfagent.models import AgentAction, PromptTemplate


class Command(BaseCommand):
    help = "Create basic PromptTemplates for actions without templates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without actually creating",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("📝 CREATE PROMPT TEMPLATES"))
        self.stdout.write("=" * 80)

        if dry_run:
            self.stdout.write(self.style.WARNING("\n⚠️  DRY-RUN MODE - No changes will be made\n"))

        # Get all actions without templates
        actions_without_templates = (
            AgentAction.objects.filter(prompt_template__isnull=True)
            .select_related("agent")
            .order_by("agent__name", "name")
        )

        total_actions = AgentAction.objects.count()
        actions_without_count = actions_without_templates.count()

        self.stdout.write(
            f"\n📊 Found {actions_without_count}/{total_actions} actions without templates\n"
        )

        created_count = 0
        errors = []

        for action in actions_without_templates:
            template_name = f"{action.agent.name} - {action.display_name}"

            # Create intelligent template based on action type
            template_text = self._generate_template_text(action)

            try:
                if not dry_run:
                    template = PromptTemplate.objects.create(
                        name=template_name,
                        description=f"Auto-generated template for {action.display_name}",
                        template_text=template_text,
                        agent=action.agent,
                        version=1,
                        usage_count=0,
                        avg_quality_score=0.0,
                    )
                    # Link template to action
                    action.prompt_template = template
                    action.save()

                self.stdout.write(self.style.SUCCESS(f"  ✅ Created: {template_name}"))
                created_count += 1

            except Exception as e:
                error = f"Error creating template for '{action.display_name}': {str(e)}"
                self.stdout.write(self.style.ERROR(f"  ❌ {error}"))
                errors.append(error)

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("📊 SUMMARY"))
        self.stdout.write("=" * 80)

        self.stdout.write(f"\n✅ Templates Created: {created_count}")
        self.stdout.write(
            f"📝 Templates Total: {total_actions - actions_without_count + created_count}/{total_actions}"
        )

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
                self.style.SUCCESS(f"\n✅ Successfully created {created_count} PromptTemplates!")
            )

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ TEMPLATE CREATION COMPLETE"))
        self.stdout.write("=" * 80)

        # Recommend next steps
        self.stdout.write("\n💡 Next Steps:")
        self.stdout.write("  1. Run: python manage.py check_workflow")
        self.stdout.write("  2. Review templates at: http://localhost:9000/prompt-templates/")
        self.stdout.write("  3. Edit and improve templates as needed")

    def _generate_template_text(self, action):
        """Generate intelligent template text based on action characteristics"""

        # Get action category from name
        action_lower = action.name.lower()

        # Generate category
        if "generate" in action_lower or "create" in action_lower:
            category = "generation"
        elif "check" in action_lower or "analyze" in action_lower or "calculate" in action_lower:
            category = "analysis"
        elif "improve" in action_lower or "enhance" in action_lower or "refine" in action_lower:
            category = "improvement"
        elif "expand" in action_lower or "develop" in action_lower:
            category = "expansion"
        else:
            category = "general"

        # Base template structure
        base = f"""# {action.display_name}

## Task
You are an expert {action.agent.name} performing: **{action.display_name}**

## Description
{action.description or 'No specific description provided.'}

## Instructions
"""

        # Category-specific instructions
        if category == "generation":
            base += """
1. Carefully analyze the provided context and requirements
2. Generate creative, original content that fits the project needs
3. Ensure consistency with existing project elements
4. Provide detailed, well-structured output
5. Include relevant examples and explanations

## Input Context
{{{{ context }}}}

## Requirements
{{{{ requirements }}}}

## Output
Generate your response following these guidelines:
- Be creative and original
- Maintain consistency with project style
- Provide comprehensive details
- Use clear, professional language
"""

        elif category == "analysis":
            base += """
1. Thoroughly review all provided materials
2. Identify patterns, inconsistencies, or areas of concern
3. Provide specific examples to support your findings
4. Rate the quality on relevant metrics
5. Suggest concrete improvements

## Content to Analyze
{{{{ content }}}}

## Analysis Criteria
{{{{ criteria }}}}

## Output
Provide your analysis in this format:

**Findings:**
- [List key findings]

**Issues:**
- [List any problems or inconsistencies]

**Score:** [Provide relevant scores]

**Recommendations:**
- [Specific suggestions for improvement]
"""

        elif category == "improvement":
            base += """
1. Review the current content carefully
2. Identify areas that need enhancement
3. Apply improvements while maintaining voice and style
4. Preserve key plot points and character traits
5. Enhance clarity, flow, and engagement

## Current Content
{{{{ current_content }}}}

## Improvement Focus
{{{{ focus_areas }}}}

## Output
Provide the improved version with:
- Enhanced prose quality
- Better flow and readability
- Maintained consistency
- Clear improvements over original
"""

        elif category == "expansion":
            base += """
1. Review the seed content or outline
2. Expand with rich, relevant details
3. Maintain consistency with established elements
4. Add depth and nuance
5. Keep the expansion focused and purposeful

## Seed Content
{{{{ seed_content }}}}

## Expansion Guidelines
{{{{ guidelines }}}}

## Output
Provide expanded content that:
- Builds naturally from the seed
- Adds meaningful details
- Maintains consistent tone
- Enhances overall quality
"""

        else:  # general
            base += """
1. Carefully review all provided information
2. Perform the requested task according to best practices
3. Ensure high quality output
4. Maintain consistency with project requirements

## Input
{{{{ input }}}}

## Context
{{{{ context }}}}

## Output
Provide your response clearly and professionally.
"""

        return base.strip()
