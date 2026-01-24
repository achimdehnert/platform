"""
Management command to create default workflow templates for book writing
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import (
    BookTypes,
    WorkflowPhase,
    WorkflowTemplate,
    WorkflowPhaseStep,
    PhaseActionConfig,
    Agents,
)


class Command(BaseCommand):
    help = "Create default workflow phases and templates for book writing"

    def handle(self, *args, **options):
        """Create default workflow data"""
        
        self.stdout.write("🔍 Analyzing existing book types and workflows...")
        self.stdout.write("")
        
        try:
            with transaction.atomic():
                # Create default phases
                phases = self.create_phases()
                self.stdout.write(self.style.SUCCESS(f"✅ Created {len(phases)} workflow phases"))
                self.stdout.write("")
                
                # Check existing book types
                self.stdout.write("📚 Existing Book Types:")
                all_book_types = BookTypes.objects.all()
                
                if not all_book_types.exists():
                    self.stdout.write("   No book types found. Creating 'Novel' as default...")
                    self.stdout.write("")
                
                types_with_workflow = []
                types_without_workflow = []
                
                for book_type in all_book_types:
                    has_workflow = WorkflowTemplate.objects.filter(book_type=book_type, is_default=True).exists()
                    if has_workflow:
                        self.stdout.write(f"   ✅ {book_type.name:20s} - has default workflow")
                        types_with_workflow.append(book_type.name)
                    else:
                        self.stdout.write(f"   ❌ {book_type.name:20s} - no workflow yet")
                        types_without_workflow.append(book_type.name)
                
                self.stdout.write("")
                
                # Create workflows for different book types
                workflows_created = []
                
                # Novel workflow
                novel_workflow = self.create_novel_workflow(phases)
                if novel_workflow:
                    workflows_created.append(novel_workflow)
                
                # Short Story workflow
                short_story_workflow = self.create_short_story_workflow(phases)
                if short_story_workflow:
                    workflows_created.append(short_story_workflow)
                
                # Non-Fiction workflow
                nonfiction_workflow = self.create_nonfiction_workflow(phases)
                if nonfiction_workflow:
                    workflows_created.append(nonfiction_workflow)
                
                # Display created workflows
                self.stdout.write("")
                for workflow in workflows_created:
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ Created workflow: '{workflow.name}' for book type '{workflow.book_type.name}'"
                    ))
                    self.stdout.write("\n📋 Workflow Steps:")
                    for step in workflow.steps.all().order_by('order'):
                        self.stdout.write(f"   {step.order}. {step.phase.name}")
                    self.stdout.write("")
                
                # Create Phase-Agent configurations
                self.stdout.write("\n🤖 Configuring Phase-Agent mappings...")
                phase_configs_count = self.create_phase_agent_configs(phases)
                self.stdout.write(self.style.SUCCESS(f"✅ Created {phase_configs_count} phase-agent configurations"))
                self.stdout.write("")
                
                # Summary
                self.stdout.write(self.style.SUCCESS(
                    f"📊 Summary: Created {len(workflows_created)} workflow template(s)"
                ))
                for wf in workflows_created:
                    self.stdout.write(f"   ✅ {wf.book_type.name}: {wf.steps.count()} steps")
                self.stdout.write("")
                
                self.stdout.write(self.style.SUCCESS("🎉 Default workflows created successfully!"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error creating workflows: {str(e)}"))
            raise

    def create_phases(self):
        """Create default workflow phases"""
        
        phases_data = [
            {
                "name": "Planning",
                "description": "Initial story planning and concept development",
                "icon": "lightbulb",
                "color": "info",
            },
            {
                "name": "Outlining",
                "description": "Create story structure and plot outline",
                "icon": "list-nested",
                "color": "primary",
            },
            {
                "name": "Character Development",
                "description": "Develop main and supporting characters",
                "icon": "people",
                "color": "warning",
            },
            {
                "name": "World Building",
                "description": "Define settings, locations, and world rules",
                "icon": "globe",
                "color": "success",
            },
            {
                "name": "Writing",
                "description": "Write chapters and scenes",
                "icon": "pen",
                "color": "primary",
            },
            {
                "name": "Revision",
                "description": "Review and improve manuscript",
                "icon": "arrow-repeat",
                "color": "warning",
            },
            {
                "name": "Finalization",
                "description": "Final polish and preparation for publication",
                "icon": "check-circle",
                "color": "success",
            },
        ]
        
        phases = []
        for phase_data in phases_data:
            phase, created = WorkflowPhase.objects.get_or_create(
                name=phase_data["name"],
                defaults={
                    "description": phase_data["description"],
                    "icon": phase_data["icon"],
                    "color": phase_data["color"],
                    "is_active": True,
                }
            )
            if created:
                self.stdout.write(f"  Created phase: {phase.name}")
            else:
                self.stdout.write(f"  Phase exists: {phase.name}")
            phases.append(phase)
        
        return {p.name: p for p in phases}

    def create_novel_workflow(self, phases):
        
        # Get or create Novel book type
        book_type, created = BookTypes.objects.get_or_create(
            name="Novel",
            defaults={
                "description": "Longer narrative fiction with complex plots and character development",
                "complexity": "intermediate",
                "target_word_count_min": 50000,
                "target_word_count_max": 120000,
                "estimated_duration_hours": 500,
            }
        )
        
        if created:
            self.stdout.write(f"  Created book type: {book_type.name}")
        else:
            self.stdout.write(f"  Book type exists: {book_type.name}")
        
        # Create workflow template
        workflow, created = WorkflowTemplate.objects.get_or_create(
            book_type=book_type,
            name="Standard Novel Workflow",
            defaults={
                "description": "Standard workflow for novel writing with all key phases",
                "is_default": True,
                "is_active": True,
            }
        )
        
        if not created:
            self.stdout.write("  Workflow template already exists")
            return workflow
        
        # Create workflow steps
        steps_config = [
            {"phase": "Planning", "order": 1, "required_chapters": 0, "required_characters": 0, "can_skip": False},
            {"phase": "Outlining", "order": 2, "required_chapters": 0, "required_characters": 0, "can_skip": False},
            {"phase": "Character Development", "order": 3, "required_chapters": 0, "required_characters": 0, "can_skip": False},
            {"phase": "World Building", "order": 4, "required_chapters": 0, "required_characters": 1, "can_skip": True},
            {"phase": "Writing", "order": 5, "required_chapters": 0, "required_characters": 2, "can_skip": False},
            {"phase": "Revision", "order": 6, "required_chapters": 1, "required_characters": 2, "can_skip": True},
            {"phase": "Finalization", "order": 7, "required_chapters": 1, "required_characters": 2, "can_skip": False},
        ]
        
        for step_config in steps_config:
            phase = phases.get(step_config["phase"])
            if phase:
                WorkflowPhaseStep.objects.create(
                    template=workflow,
                    phase=phase,
                    order=step_config["order"],
                    required_chapters=step_config["required_chapters"],
                    required_characters=step_config["required_characters"],
                    can_skip=step_config["can_skip"],
                    can_return=True,
                )
                self.stdout.write(f"  Created step {step_config['order']}: {phase.name}")
        
        return workflow
    
    def create_short_story_workflow(self, phases):
        """Create Short Story workflow template"""
        
        # Get or create Short Story book type
        book_type, created = BookTypes.objects.get_or_create(
            name="Short Story",
            defaults={
                "description": "Shorter narrative fiction focusing on a single plot or theme",
                "complexity": "beginner",
                "target_word_count_min": 1000,
                "target_word_count_max": 15000,
                "estimated_duration_hours": 50,
            }
        )
        
        if created:
            self.stdout.write(f"  Created book type: {book_type.name}")
        else:
            self.stdout.write(f"  Book type exists: {book_type.name}")
        
        # Create workflow template
        workflow, created = WorkflowTemplate.objects.get_or_create(
            book_type=book_type,
            name="Short Story Workflow",
            defaults={
                "description": "Streamlined workflow for short story writing",
                "is_default": True,
                "is_active": True,
            }
        )
        
        if not created:
            self.stdout.write("  Workflow template already exists")
            return workflow
        
        # Simplified steps for short stories
        steps_config = [
            {"phase": "Planning", "order": 1, "required_chapters": 0, "required_characters": 0, "can_skip": False},
            {"phase": "Outlining", "order": 2, "required_chapters": 0, "required_characters": 0, "can_skip": True},
            {"phase": "Character Development", "order": 3, "required_chapters": 0, "required_characters": 0, "can_skip": True},
            {"phase": "Writing", "order": 4, "required_chapters": 0, "required_characters": 1, "can_skip": False},
            {"phase": "Revision", "order": 5, "required_chapters": 1, "required_characters": 1, "can_skip": False},
        ]
        
        for step_config in steps_config:
            phase = phases.get(step_config["phase"])
            if phase:
                WorkflowPhaseStep.objects.create(
                    template=workflow,
                    phase=phase,
                    order=step_config["order"],
                    required_chapters=step_config["required_chapters"],
                    required_characters=step_config["required_characters"],
                    can_skip=step_config["can_skip"],
                    can_return=True,
                )
                self.stdout.write(f"  Created step {step_config['order']}: {phase.name}")
        
        return workflow
    
    def create_nonfiction_workflow(self, phases):
        """Create Non-Fiction workflow template"""
        
        # Get or create Non-Fiction book type
        book_type, created = BookTypes.objects.get_or_create(
            name="Non-Fiction",
            defaults={
                "description": "Informative writing based on facts and research",
                "complexity": "intermediate",
                "target_word_count_min": 40000,
                "target_word_count_max": 80000,
                "estimated_duration_hours": 400,
            }
        )
        
        if created:
            self.stdout.write(f"  Created book type: {book_type.name}")
        else:
            self.stdout.write(f"  Book type exists: {book_type.name}")
        
        # Create workflow template
        workflow, created = WorkflowTemplate.objects.get_or_create(
            book_type=book_type,
            name="Non-Fiction Workflow",
            defaults={
                "description": "Research-based workflow for non-fiction writing",
                "is_default": True,
                "is_active": True,
            }
        )
        
        if not created:
            self.stdout.write("  Workflow template already exists")
            return workflow
        
        # Non-fiction focused steps (no character development, focus on research)
        steps_config = [
            {"phase": "Planning", "order": 1, "required_chapters": 0, "required_characters": 0, "can_skip": False},
            {"phase": "Outlining", "order": 2, "required_chapters": 0, "required_characters": 0, "can_skip": False},
            {"phase": "Writing", "order": 3, "required_chapters": 0, "required_characters": 0, "can_skip": False},
            {"phase": "Revision", "order": 4, "required_chapters": 1, "required_characters": 0, "can_skip": False},
            {"phase": "Finalization", "order": 5, "required_chapters": 1, "required_characters": 0, "can_skip": False},
        ]
        
        for step_config in steps_config:
            phase = phases.get(step_config["phase"])
            if phase:
                WorkflowPhaseStep.objects.create(
                    template=workflow,
                    phase=phase,
                    order=step_config["order"],
                    required_chapters=step_config["required_chapters"],
                    required_characters=step_config["required_characters"],
                    can_skip=step_config["can_skip"],
                    can_return=True,
                )
                self.stdout.write(f"  Created step {step_config['order']}: {phase.name}")
        
        return workflow
    
    def create_phase_agent_configs(self, phases):
        """Create Phase-Agent action configurations"""
        
        # Define which agents/actions are available in each phase
        phase_agent_mapping = {
            "Planning": [
                {"agent_type": "outline_agent", "action": "generate_story_concept", "required": True, "order": 1},
                {"agent_type": "outline_agent", "action": "brainstorm_ideas", "required": False, "order": 2},
                {"agent_type": "prompt_agent", "action": "generate_prompt", "required": False, "order": 3},
            ],
            "Outlining": [
                {"agent_type": "outline_agent", "action": "generate_outline", "required": True, "order": 1},
                {"agent_type": "outline_agent", "action": "optimize_outline", "required": False, "order": 2},
                {"agent_type": "structure_agent", "action": "analyze_structure", "required": False, "order": 3},
            ],
            "Character Development": [
                {"agent_type": "character_agent", "action": "create_character", "required": True, "order": 1},
                {"agent_type": "character_agent", "action": "develop_backstory", "required": False, "order": 2},
                {"agent_type": "character_agent", "action": "analyze_relationships", "required": False, "order": 3},
            ],
            "World Building": [
                {"agent_type": "world_agent", "action": "create_world", "required": True, "order": 1},
                {"agent_type": "world_agent", "action": "define_rules", "required": False, "order": 2},
            ],
            "Writing": [
                {"agent_type": "chapter_agent", "action": "write_chapter", "required": True, "order": 1},
                {"agent_type": "writer_agent", "action": "expand_scene", "required": False, "order": 2},
                {"agent_type": "dialogue_agent", "action": "enhance_dialogue", "required": False, "order": 3},
            ],
            "Revision": [
                {"agent_type": "editor_agent", "action": "review_content", "required": True, "order": 1},
                {"agent_type": "consistency_agent", "action": "check_consistency", "required": True, "order": 2},
                {"agent_type": "style_agent", "action": "improve_style", "required": False, "order": 3},
            ],
            "Finalization": [
                {"agent_type": "editor_agent", "action": "final_polish", "required": True, "order": 1},
                {"agent_type": "consistency_agent", "action": "final_check", "required": True, "order": 2},
            ],
        }
        
        config_count = 0
        for phase_name, agent_configs in phase_agent_mapping.items():
            phase = phases.get(phase_name)
            if not phase:
                continue
            
            for config in agent_configs:
                _, created = PhaseActionConfig.objects.get_or_create(
                    phase=phase,
                    agent_type=config["agent_type"],
                    action_name=config["action"],
                    defaults={
                        "is_required": config["required"],
                        "order": config["order"],
                        "description": f"{config['action'].replace('_', ' ').title()} for {phase_name} phase",
                    }
                )
                if created:
                    config_count += 1
                    self.stdout.write(f"  ✓ {phase_name}: {config['agent_type']}.{config['action']}")
        
        return config_count
