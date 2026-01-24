"""
Management command to populate workflow system with initial data
Creates phases, templates, steps, and action configurations
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import (
    BookTypes,
    PhaseActionConfig,
    ProjectPhaseHistory,
    WorkflowPhase,
    WorkflowPhaseStep,
    WorkflowTemplate,
)


class Command(BaseCommand):
    help = "Setup workflow system with initial phases, templates, and actions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing workflow data before setup",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🚀 Setting up Workflow Engine System...\n"))

        if options["reset"]:
            self.stdout.write("⚠️  Resetting existing workflow data...")
            self.reset_workflow_data()

        with transaction.atomic():
            # Step 1: Create Phases
            phases = self.create_phases()
            self.stdout.write(self.style.SUCCESS(f"✅ Created {len(phases)} workflow phases"))

            # Step 2: Create Workflow Templates
            templates = self.create_templates()
            self.stdout.write(self.style.SUCCESS(f"✅ Created {len(templates)} workflow templates"))

            # Step 3: Create Phase Steps
            steps_count = self.create_phase_steps(phases, templates)
            self.stdout.write(self.style.SUCCESS(f"✅ Created {steps_count} phase steps"))

            # Step 4: Create Action Configurations
            actions_count = self.create_action_configs(phases)
            self.stdout.write(
                self.style.SUCCESS(f"✅ Created {actions_count} action configurations")
            )

        self.stdout.write(self.style.SUCCESS("\n🎉 Workflow Engine System setup completed!\n"))

    def reset_workflow_data(self):
        """Delete all existing workflow data"""
        ProjectPhaseHistory.objects.all().delete()
        PhaseActionConfig.objects.all().delete()
        WorkflowPhaseStep.objects.all().delete()
        WorkflowTemplate.objects.all().delete()
        WorkflowPhase.objects.all().delete()
        self.stdout.write("   Deleted all existing workflow data")

    def create_phases(self):
        """Create standard workflow phases"""
        phases_data = [
            {
                "name": "Planning",
                "description": "Initial project planning and concept development",
                "icon": "lightbulb",
                "color": "info",
            },
            {
                "name": "Outlining",
                "description": "Story structure and chapter outline creation",
                "icon": "list-nested",
                "color": "primary",
            },
            {
                "name": "World Building",
                "description": "Setting, world rules, and environment development",
                "icon": "globe",
                "color": "success",
            },
            {
                "name": "Character Development",
                "description": "Character creation and relationship mapping",
                "icon": "people",
                "color": "warning",
            },
            {
                "name": "Writing",
                "description": "First draft writing and content creation",
                "icon": "pencil",
                "color": "primary",
            },
            {
                "name": "Revision",
                "description": "Content review and structural improvements",
                "icon": "arrow-repeat",
                "color": "secondary",
            },
            {
                "name": "Editing",
                "description": "Grammar, style, and polish",
                "icon": "scissors",
                "color": "danger",
            },
            {
                "name": "Review",
                "description": "Final quality check and beta reading",
                "icon": "eye",
                "color": "info",
            },
            {
                "name": "Publishing",
                "description": "Preparation for publication",
                "icon": "rocket",
                "color": "success",
            },
        ]

        phases = {}
        for phase_data in phases_data:
            phase, created = WorkflowPhase.objects.get_or_create(
                name=phase_data["name"], defaults=phase_data
            )
            phases[phase.name] = phase
            if created:
                self.stdout.write(f"   📝 Created phase: {phase.name}")

        return phases

    def create_templates(self):
        """Create workflow templates for different book types"""
        templates = {}

        # Novel Workflow (Complete)
        novel_type, _ = BookTypes.objects.get_or_create(
            name="Novel", defaults={"description": "Full-length novel"}
        )

        novel_template, created = WorkflowTemplate.objects.get_or_create(
            name="Standard Novel Workflow",
            book_type=novel_type,
            defaults={
                "description": "Complete workflow for novel writing with all phases",
                "is_default": True,
                "is_active": True,
            },
        )
        templates["novel"] = novel_template
        if created:
            self.stdout.write("   📚 Created Novel workflow template")

        # Short Story Workflow (Streamlined)
        short_story_type, _ = BookTypes.objects.get_or_create(
            name="Short Story", defaults={"description": "Short story (< 20k words)"}
        )

        short_story_template, created = WorkflowTemplate.objects.get_or_create(
            name="Short Story Workflow",
            book_type=short_story_type,
            defaults={
                "description": "Streamlined workflow for short stories",
                "is_default": True,
                "is_active": True,
            },
        )
        templates["short_story"] = short_story_template
        if created:
            self.stdout.write("   📝 Created Short Story workflow template")

        # Novella Workflow (Medium)
        novella_type, _ = BookTypes.objects.get_or_create(
            name="Novella", defaults={"description": "Novella (20k-50k words)"}
        )

        novella_template, created = WorkflowTemplate.objects.get_or_create(
            name="Novella Workflow",
            book_type=novella_type,
            defaults={
                "description": "Balanced workflow for novella-length works",
                "is_default": True,
                "is_active": True,
            },
        )
        templates["novella"] = novella_template
        if created:
            self.stdout.write("   📖 Created Novella workflow template")

        return templates

    def create_phase_steps(self, phases, templates):
        """Create phase steps for each workflow template"""
        steps_count = 0

        # Novel Workflow - Complete Process
        novel_steps = [
            ("Planning", 1, {"required_chapters": 0, "required_characters": 0}),
            ("Outlining", 2, {"required_chapters": 0, "required_characters": 0}),
            (
                "World Building",
                3,
                {"required_chapters": 0, "required_characters": 0, "can_skip": True},
            ),
            ("Character Development", 4, {"required_chapters": 0, "required_characters": 3}),
            ("Writing", 5, {"required_chapters": 10, "required_characters": 3}),
            ("Revision", 6, {"required_chapters": 15, "required_characters": 3}),
            ("Editing", 7, {"required_chapters": 20, "required_characters": 3}),
            ("Review", 8, {"required_chapters": 20, "required_characters": 3}),
            (
                "Publishing",
                9,
                {"required_chapters": 20, "required_characters": 3, "can_return": False},
            ),
        ]

        for phase_name, order, requirements in novel_steps:
            WorkflowPhaseStep.objects.get_or_create(
                template=templates["novel"],
                phase=phases[phase_name],
                order=order,
                defaults=requirements,
            )
            steps_count += 1

        # Short Story Workflow - Streamlined
        short_story_steps = [
            ("Planning", 1, {"required_chapters": 0, "required_characters": 0}),
            ("Outlining", 2, {"required_chapters": 0, "required_characters": 0, "can_skip": True}),
            ("Character Development", 3, {"required_chapters": 0, "required_characters": 1}),
            ("Writing", 4, {"required_chapters": 1, "required_characters": 1}),
            ("Editing", 5, {"required_chapters": 1, "required_characters": 1}),
            (
                "Publishing",
                6,
                {"required_chapters": 1, "required_characters": 1, "can_return": False},
            ),
        ]

        for phase_name, order, requirements in short_story_steps:
            WorkflowPhaseStep.objects.get_or_create(
                template=templates["short_story"],
                phase=phases[phase_name],
                order=order,
                defaults=requirements,
            )
            steps_count += 1

        # Novella Workflow - Medium
        novella_steps = [
            ("Planning", 1, {"required_chapters": 0, "required_characters": 0}),
            ("Outlining", 2, {"required_chapters": 0, "required_characters": 0}),
            ("Character Development", 3, {"required_chapters": 0, "required_characters": 2}),
            ("Writing", 4, {"required_chapters": 5, "required_characters": 2}),
            ("Revision", 5, {"required_chapters": 8, "required_characters": 2}),
            ("Editing", 6, {"required_chapters": 10, "required_characters": 2}),
            (
                "Publishing",
                7,
                {"required_chapters": 10, "required_characters": 2, "can_return": False},
            ),
        ]

        for phase_name, order, requirements in novella_steps:
            WorkflowPhaseStep.objects.get_or_create(
                template=templates["novella"],
                phase=phases[phase_name],
                order=order,
                defaults=requirements,
            )
            steps_count += 1

        return steps_count

    def create_action_configs(self, phases):
        """Create action configurations for each phase"""
        actions_count = 0

        # Planning Phase Actions
        planning_actions = [
            ("outline_agent", "generate_story_premise", "Generate core story concept", True, 1),
            ("outline_agent", "create_genre_outline", "Create genre-specific outline", True, 2),
            ("outline_agent", "define_story_themes", "Define central themes", False, 3),
            ("character_agent", "brainstorm_protagonists", "Brainstorm main characters", False, 4),
        ]

        for agent, action, desc, required, order in planning_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Planning"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # Outlining Phase Actions
        outlining_actions = [
            (
                "outline_agent",
                "generate_chapter_outline",
                "Create detailed chapter breakdown",
                True,
                1,
            ),
            ("outline_agent", "define_plot_points", "Define key plot moments", True, 2),
            ("outline_agent", "create_story_arc", "Build complete story arc", True, 3),
            ("outline_agent", "validate_structure", "Check story structure", False, 4),
        ]

        for agent, action, desc, required, order in outlining_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Outlining"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # World Building Phase Actions
        world_building_actions = [
            ("world_agent", "create_world_basics", "Define world fundamentals", True, 1),
            ("world_agent", "define_world_rules", "Set world rules and logic", True, 2),
            ("world_agent", "create_locations", "Design key locations", False, 3),
            ("world_agent", "build_world_history", "Develop world backstory", False, 4),
        ]

        for agent, action, desc, required, order in world_building_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["World Building"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # Character Development Phase Actions
        character_actions = [
            ("character_agent", "generate_character_cast", "Create main character cast", True, 1),
            ("character_agent", "develop_character_arcs", "Define character journeys", True, 2),
            (
                "character_agent",
                "create_character_relationships",
                "Map character dynamics",
                False,
                3,
            ),
            (
                "character_agent",
                "write_character_backstories",
                "Develop detailed backstories",
                False,
                4,
            ),
        ]

        for agent, action, desc, required, order in character_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Character Development"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # Writing Phase Actions
        writing_actions = [
            ("chapter_agent", "generate_chapter_draft", "Write chapter first draft", True, 1),
            ("chapter_agent", "improve_chapter_content", "Enhance chapter content", False, 2),
            ("chapter_agent", "add_dialogue", "Develop character dialogue", False, 3),
            ("chapter_agent", "enhance_descriptions", "Improve scene descriptions", False, 4),
            ("style_agent", "apply_writing_style", "Apply consistent voice", False, 5),
        ]

        for agent, action, desc, required, order in writing_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Writing"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # Revision Phase Actions
        revision_actions = [
            ("editing_agent", "check_plot_consistency", "Verify plot coherence", True, 1),
            (
                "editing_agent",
                "check_character_consistency",
                "Validate character behavior",
                True,
                2,
            ),
            ("editing_agent", "improve_pacing", "Optimize story pacing", False, 3),
            ("editing_agent", "strengthen_scenes", "Enhance weak scenes", False, 4),
        ]

        for agent, action, desc, required, order in revision_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Revision"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # Editing Phase Actions
        editing_actions = [
            ("editing_agent", "proofread_chapter", "Grammar and spelling check", True, 1),
            ("editing_agent", "check_grammar", "Detailed grammar review", True, 2),
            ("editing_agent", "improve_sentence_flow", "Enhance readability", False, 3),
            ("editing_agent", "polish_prose", "Final polish", False, 4),
        ]

        for agent, action, desc, required, order in editing_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Editing"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # Review Phase Actions
        review_actions = [
            ("review_agent", "final_quality_check", "Complete manuscript review", True, 1),
            ("review_agent", "generate_book_blurb", "Create marketing copy", False, 2),
            ("review_agent", "create_synopsis", "Write synopsis", False, 3),
        ]

        for agent, action, desc, required, order in review_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Review"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        # Publishing Phase Actions
        publishing_actions = [
            ("publishing_agent", "format_manuscript", "Format for publication", True, 1),
            ("publishing_agent", "generate_metadata", "Create publishing metadata", True, 2),
            ("publishing_agent", "export_formats", "Export to various formats", False, 3),
        ]

        for agent, action, desc, required, order in publishing_actions:
            PhaseActionConfig.objects.get_or_create(
                phase=phases["Publishing"],
                agent_type=agent,
                action_name=action,
                defaults={"description": desc, "is_required": required, "order": order},
            )
            actions_count += 1

        return actions_count
