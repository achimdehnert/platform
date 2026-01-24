"""
Management command to seed BookType workflows and phase-action mappings
Creates complete workflows for each book type with appropriate phases and actions

Usage: python manage.py seed_booktype_workflows
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import (
    AgentAction,
    Agents,
    BookTypePhase,
    BookTypes,
    PhaseActionConfig,
    WorkflowPhase,
)


class Command(BaseCommand):
    help = "Seeds BookType workflows with phases and actions"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n🌱 Seeding BookType Workflows...\n"))

        with transaction.atomic():
            # Get or create phases
            phases = self._create_phases()
            
            # Get or create book types
            book_types = self._get_or_create_book_types()
            
            # Get or create agents and actions
            agents = self._get_or_create_agents()
            actions = self._create_actions(agents)
            
            # Create workflows
            self._create_novel_workflow(book_types, phases, actions)
            self._create_nonfiction_workflow(book_types, phases, actions)
            self._create_shortstory_workflow(book_types, phases, actions)
            
        self.stdout.write(self.style.SUCCESS("\n✅ DONE! Workflows created successfully\n"))

    def _create_phases(self):
        """Create or get workflow phases"""
        phases = {}
        
        phase_definitions = [
            ("brainstorming", "Brainstorming", "Initial ideation and concept development", "lightbulb", "warning"),
            ("research", "Research", "Gather information and background material", "search", "info"),
            ("outline", "Outline", "Structure and plot development", "list-task", "primary"),
            ("character_development", "Character Development", "Create and develop characters", "people", "success"),
            ("world_building", "World Building", "Build the story universe and settings", "globe", "info"),
            ("chapter_planning", "Chapter Planning", "Plan individual chapters", "book", "secondary"),
            ("writing", "Writing", "Main writing phase", "pencil", "primary"),
            ("revision", "Revision", "Content revision and improvements", "arrow-repeat", "warning"),
            ("editing", "Editing", "Final edits and polish", "check-circle", "success"),
            ("formatting", "Formatting", "Format for publication", "file-text", "secondary"),
        ]
        
        for name, display, desc, icon, color in phase_definitions:
            phase, created = WorkflowPhase.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "icon": f"bi-{icon}",
                    "color": color,
                    "is_active": True,
                }
            )
            phases[name] = phase
            if created:
                self.stdout.write(f"  ✅ Created phase: {display}")
            else:
                self.stdout.write(f"  ℹ️  Phase exists: {display}")
        
        return phases

    def _get_or_create_book_types(self):
        """Get or create book types"""
        book_types = {}
        
        bt_definitions = [
            ("Novel", "Full-length novel (60,000+ words)", "high"),
            ("Non-Fiction", "Non-fiction book", "medium"),
            ("Short Story", "Short story (under 20,000 words)", "low"),
            ("Novella", "Novella (20,000-60,000 words)", "medium"),
        ]
        
        for name, desc, complexity in bt_definitions:
            bt, created = BookTypes.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "complexity": complexity,
                }
            )
            book_types[name] = bt
            if created:
                self.stdout.write(f"  ✅ Created book type: {name}")
        
        return book_types

    def _get_or_create_agents(self):
        """Get or create AI agents"""
        agents = {}
        
        agent_definitions = [
            ("Brainstorm Agent", "brainstorm", "Helps with ideation and concept development"),
            ("Research Agent", "research", "Gathers and synthesizes information"),
            ("Outline Agent", "outline", "Creates story structure and outlines"),
            ("Character Agent", "character", "Develops characters and relationships"),
            ("World Agent", "world", "Builds settings and universes"),
            ("Writing Agent", "writing", "Assists with chapter writing"),
            ("Editor Agent", "editor", "Provides editing and revision suggestions"),
        ]
        
        for name, agent_type, desc in agent_definitions:
            agent, created = Agents.objects.get_or_create(
                name=name,
                defaults={
                    "agent_type": agent_type,
                    "description": desc,
                    "status": "active",
                    "system_prompt": f"You are a {name}. {desc}",
                }
            )
            agents[agent_type] = agent
            if created:
                self.stdout.write(f"  ✅ Created agent: {name}")
        
        return agents

    def _create_actions(self, agents):
        """Create agent actions"""
        actions = {}
        
        action_definitions = [
            # Brainstorming actions
            ("generate_story_ideas", "Generate Story Ideas", agents.get("brainstorm"), "Generate story concepts and themes"),
            ("develop_premise", "Develop Story Premise", agents.get("brainstorm"), "Create compelling story premise"),
            
            # Research actions
            ("research_topic", "Research Topic", agents.get("research"), "Research background information"),
            
            # Outline actions
            ("create_outline", "Create Story Outline", agents.get("outline"), "Structure the story"),
            ("analyze_structure", "Analyze Story Structure", agents.get("outline"), "Review and improve structure"),
            
            # Character actions
            ("create_character", "Create Character Profile", agents.get("character"), "Develop detailed character"),
            ("analyze_relationships", "Analyze Character Relationships", agents.get("character"), "Map character dynamics"),
            
            # World building actions
            ("build_world", "Build Story World", agents.get("world"), "Create settings and environments"),
            
            # Writing actions
            ("write_chapter", "Write Chapter", agents.get("writing"), "Draft chapter content"),
            ("enhance_prose", "Enhance Prose", agents.get("writing"), "Improve writing quality"),
            
            # Editing actions
            ("edit_content", "Edit Content", agents.get("editor"), "Provide editing suggestions"),
            ("check_consistency", "Check Consistency", agents.get("editor"), "Verify story consistency"),
        ]
        
        for name, display, agent, desc in action_definitions:
            if agent:  # Only create if agent exists
                action, created = AgentAction.objects.get_or_create(
                    name=name,
                    agent=agent,
                    defaults={
                        "display_name": display,
                        "description": desc,
                    }
                )
                actions[name] = action
                if created:
                    self.stdout.write(f"  ✅ Created action: {display}")
        
        return actions

    def _create_novel_workflow(self, book_types, phases, actions):
        """Create workflow for novels"""
        novel = book_types.get("Novel")
        if not novel:
            return
        
        self.stdout.write(self.style.WARNING("\n📚 Creating Novel Workflow..."))
        
        workflow = [
            (phases["brainstorming"], 1, True, 7, ["generate_story_ideas", "develop_premise"]),
            (phases["research"], 2, False, 5, ["research_topic"]),
            (phases["outline"], 3, True, 10, ["create_outline", "analyze_structure"]),
            (phases["character_development"], 4, True, 14, ["create_character", "analyze_relationships"]),
            (phases["world_building"], 5, True, 10, ["build_world"]),
            (phases["chapter_planning"], 6, True, 7, ["create_outline"]),
            (phases["writing"], 7, True, 90, ["write_chapter", "enhance_prose"]),
            (phases["revision"], 8, True, 21, ["edit_content", "check_consistency"]),
            (phases["editing"], 9, True, 14, ["edit_content"]),
            (phases["formatting"], 10, False, 3, []),
        ]
        
        self._create_workflow_for_booktype(novel, workflow, actions)

    def _create_nonfiction_workflow(self, book_types, phases, actions):
        """Create workflow for non-fiction"""
        nonfiction = book_types.get("Non-Fiction")
        if not nonfiction:
            return
        
        self.stdout.write(self.style.WARNING("\n📖 Creating Non-Fiction Workflow..."))
        
        workflow = [
            (phases["brainstorming"], 1, True, 5, ["generate_story_ideas"]),
            (phases["research"], 2, True, 21, ["research_topic"]),
            (phases["outline"], 3, True, 14, ["create_outline", "analyze_structure"]),
            (phases["writing"], 4, True, 60, ["write_chapter", "enhance_prose"]),
            (phases["revision"], 5, True, 14, ["edit_content", "check_consistency"]),
            (phases["editing"], 6, True, 10, ["edit_content"]),
            (phases["formatting"], 7, False, 3, []),
        ]
        
        self._create_workflow_for_booktype(nonfiction, workflow, actions)

    def _create_shortstory_workflow(self, book_types, phases, actions):
        """Create workflow for short stories"""
        shortstory = book_types.get("Short Story")
        if not shortstory:
            return
        
        self.stdout.write(self.style.WARNING("\n📝 Creating Short Story Workflow..."))
        
        workflow = [
            (phases["brainstorming"], 1, True, 2, ["generate_story_ideas", "develop_premise"]),
            (phases["outline"], 2, True, 3, ["create_outline"]),
            (phases["writing"], 3, True, 7, ["write_chapter", "enhance_prose"]),
            (phases["revision"], 4, True, 3, ["edit_content"]),
            (phases["editing"], 5, True, 2, ["edit_content"]),
        ]
        
        self._create_workflow_for_booktype(shortstory, workflow, actions)

    def _create_workflow_for_booktype(self, book_type, workflow, actions):
        """Helper to create workflow for a book type"""
        for phase, order, is_required, est_days, action_names in workflow:
            # Create BookTypePhase
            btp, created = BookTypePhase.objects.get_or_create(
                book_type=book_type,
                phase=phase,
                defaults={
                    "order": order,
                    "is_required": is_required,
                    "estimated_days": est_days,
                }
            )
            
            if created:
                self.stdout.write(f"  ✅ {book_type.name} - Step {order}: {phase.name}")
            
            # Create PhaseActionConfig for each action
            for action_name in action_names:
                action = actions.get(action_name)
                if action:
                    PhaseActionConfig.objects.get_or_create(
                        phase=phase,
                        action=action,
                        defaults={
                            "is_required": False,
                            "order": 0,
                        }
                    )
