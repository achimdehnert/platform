"""
Management command to create or update Outline Agent with Story Framework actions

Usage:
    python manage.py create_outline_agent
"""

from django.core.management.base import BaseCommand
from apps.bfagent.models import Agents, Llms, AgentAction, WorkflowPhase, PhaseActionConfig
from apps.bfagent.services.outline_actions import OUTLINE_ACTIONS


class Command(BaseCommand):
    help = 'Create or update Outline Agent with Story Framework actions'

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write("📋 CREATING/UPDATING OUTLINE AGENT")
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        # Get first active LLM
        llm = Llms.objects.filter(is_active=True).first()
        if not llm:
            self.stdout.write(self.style.ERROR("❌ No active LLM found!"))
            self.stdout.write("   Please create an LLM first.")
            return
        
        self.stdout.write(f"🤖 Using LLM: {llm.llm_name}")
        self.stdout.write("")
        
        # Create or update Outline Agent
        agent, created = Agents.objects.update_or_create(
            agent_type='outline_agent',
            defaults={
                'name': 'Story Framework Outline Generator',
                'status': 'active',  # Using status field instead of is_active
                'description': 'Generates structured story outlines using proven frameworks like Hero\'s Journey, Save the Cat, and Three-Act Structure',
                'system_prompt': '''You are an expert story structure consultant specializing in proven narrative frameworks.

Your expertise includes:
- Hero's Journey (Joseph Campbell's Monomyth)
- Save the Cat Beat Sheet (Blake Snyder)
- Three-Act Structure (Classical dramatic structure)
- Story beats and pacing
- Emotional arc design
- Genre-appropriate structure selection

When generating outlines, you:
1. Analyze the project's genre, premise, and themes
2. Recommend the most suitable story framework
3. Create detailed chapter-by-chapter outlines with clear beats
4. Provide guidance for each chapter's focus and emotional arc
5. Ensure consistent pacing and narrative flow

Always be specific, actionable, and aligned with proven storytelling principles.''',
                'llm_model_id': llm.id
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS("✅ Created new Outline Agent"))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Updated existing Outline Agent"))
        
        self.stdout.write(f"   ID: {agent.id}")
        self.stdout.write(f"   Name: {agent.name}")
        self.stdout.write(f"   Type: {agent.agent_type}")
        self.stdout.write("")
        
        # Create AgentAction objects for each framework action
        self.stdout.write("📚 Creating AgentAction objects...")
        self.stdout.write("")
        
        actions_created = 0
        actions_updated = 0
        
        for idx, (action_id, action_info) in enumerate(OUTLINE_ACTIONS.items(), 1):
            icon = action_info.get('icon', '📋')
            label = action_info.get('label', action_id)
            description = action_info.get('description', '')
            
            # Create or update AgentAction
            action_obj, action_created = AgentAction.objects.update_or_create(
                agent=agent,
                name=action_id,
                defaults={
                    'display_name': label,
                    'description': description,
                    'target_model': 'project',
                    'target_fields': ['outline', 'story_structure_analysis', 'story_beats_suggestion'],
                    'order': idx,
                    'is_active': True
                }
            )
            
            if action_created:
                actions_created += 1
                status = "✅ Created"
            else:
                actions_updated += 1
                status = "🔄 Updated"
            
            self.stdout.write(f"  {icon} {label}")
            self.stdout.write(f"     {status}")
            self.stdout.write(f"     Action ID: {action_id}")
            self.stdout.write(f"     {description}")
            self.stdout.write("")
        
        self.stdout.write("")
        self.stdout.write(f"📊 Summary: {actions_created} created, {actions_updated} updated")
        self.stdout.write("")
        
        # Find or create Outline Phase
        self.stdout.write("🔍 Finding Outline Phase...")
        outline_phase = WorkflowPhase.objects.filter(name__icontains='outline').first()
        
        if not outline_phase:
            self.stdout.write(self.style.WARNING("⚠️  No Outline phase found!"))
            self.stdout.write("   Creating generic 'Outline' phase...")
            
            # Get first workflow template or create a basic one
            from apps.bfagent.models import WorkflowTemplate
            workflow = WorkflowTemplate.objects.first()
            
            if not workflow:
                self.stdout.write(self.style.ERROR("❌ No WorkflowTemplate found!"))
                self.stdout.write("   Please create a WorkflowTemplate first, then run this command again.")
                return
            
            outline_phase = WorkflowPhase.objects.create(
                workflow=workflow,
                name='Outline',
                description='Story structure and outline development',
                phase_type='outline',
                order=1
            )
            self.stdout.write(self.style.SUCCESS(f"   ✅ Created Outline phase"))
        else:
            self.stdout.write(f"   ✅ Found phase: {outline_phase.name}")
        
        self.stdout.write("")
        
        # Assign Actions to Outline Phase
        self.stdout.write("🔗 Assigning actions to Outline Phase...")
        self.stdout.write("")
        
        phase_configs_created = 0
        phase_configs_updated = 0
        
        for action_obj in AgentAction.objects.filter(agent=agent, is_active=True):
            config, config_created = PhaseActionConfig.objects.update_or_create(
                phase=outline_phase,
                action=action_obj,
                defaults={
                    'is_required': False,
                    'order': action_obj.order,
                    'description': f"Story framework action: {action_obj.display_name}"
                }
            )
            
            if config_created:
                phase_configs_created += 1
                status = "✅ Assigned"
            else:
                phase_configs_updated += 1
                status = "🔄 Updated"
            
            self.stdout.write(f"   {status} {action_obj.display_name} → {outline_phase.name}")
        
        self.stdout.write("")
        self.stdout.write(f"📊 Phase Config Summary: {phase_configs_created} created, {phase_configs_updated} updated")
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("✅ OUTLINE AGENT READY!"))
        self.stdout.write("=" * 70)
        self.stdout.write("")
        
        self.stdout.write("💡 How to use:")
        self.stdout.write("1. Go to Project Detail page")
        self.stdout.write("2. Click 'Project Enrichment' tab")
        self.stdout.write(f"3. Select agent: '{agent.name}'")
        self.stdout.write("4. Choose a framework action:")
        self.stdout.write("   - Generate Hero's Journey Outline")
        self.stdout.write("   - Generate Save the Cat Outline")
        self.stdout.write("   - Generate Three-Act Outline")
        self.stdout.write("   - Analyze Story Structure")
        self.stdout.write("   - Suggest Key Story Beats")
        self.stdout.write("5. Click 'Run' to generate structured outline")
        self.stdout.write("")
        
        self.stdout.write("📖 The outline will be saved to the project and can be used")
        self.stdout.write("   as input for the Book Generator script.")
        self.stdout.write("")
