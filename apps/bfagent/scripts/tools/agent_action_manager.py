#!/usr/bin/env python
"""
BF Agent - Enterprise Agent Action Manager v1.0.0
==================================================

Manages agent actions using YAML templates for consistency and automation.

Features:
- Template-based action creation
- Automatic agent alias resolution (writer/writer_agent/WRITER_AGENT)
- Missing action detection
- Bulk action creation/update
- Comprehensive reporting

Usage:
    python scripts/agent_action_manager.py sync          # Sync all actions from templates
    python scripts/agent_action_manager.py status        # Show current status
    python scripts/agent_action_manager.py missing       # Find missing actions
    python scripts/agent_action_manager.py fix --agent planning_agent

Author: BF Agent Development Team
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django

django.setup()

# Disable SQL query logging for cleaner output
import logging
logging.getLogger('django.db.backends').setLevel(logging.WARNING)

# Now we can import Django models
from django.db import OperationalError, transaction
from apps.bfagent.models import AgentAction, Agents


class AgentActionManager:
    """Enterprise agent action management system"""
    def __init__(self, template_path: str = "config/agent_action_templates.yaml"):
        self.template_path = Path(template_path)
        self.templates = self._load_templates()
        self.agent_lookup = self._build_agent_lookup()

    def _load_templates(self) -> Dict:
        """Load agent action templates from YAML"""
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

        with open(self.template_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return data.get("agent_action_templates", {})

    def _build_agent_lookup(self) -> Dict[str, int]:
        """Build lookup table for agent types including aliases"""
        lookup = {}

        for agent in Agents.objects.all():
            agent_type_lower = agent.agent_type.lower()
            lookup[agent_type_lower] = agent.id
            lookup[agent.agent_type] = agent.id  # Keep original case too

        return lookup

    def _resolve_agent(self, agent_type: str) -> Optional[int]:
        """Resolve agent ID from type, checking aliases"""
        # Try direct match first
        agent_id = self.agent_lookup.get(agent_type)
        if agent_id:
            return agent_id

        # Check template aliases
        template = self.templates.get(agent_type, {})
        aliases = template.get("aliases", [])

        for alias in aliases:
            agent_id = self.agent_lookup.get(alias.lower())
            if agent_id:
                return agent_id
            agent_id = self.agent_lookup.get(alias)
            if agent_id:
                return agent_id

        return None

    def get_status(self) -> Dict:
        """Get current status of all agent actions"""
        status = {
            "agents": {},
            "summary": {
                "total_agents": 0,
                "active_agents": 0,
                "total_actions": 0,
                "missing_agents": [],
                "missing_actions": 0,
            },
        }

        # Get all agents
        agents = Agents.objects.all()
        status["summary"]["total_agents"] = agents.count()
        status["summary"]["active_agents"] = agents.filter(status="active").count()

        # Check each template against database
        for agent_type, template in self.templates.items():
            agent_id = self._resolve_agent(agent_type)

            if not agent_id:
                status["summary"]["missing_agents"].append(agent_type)
                status["agents"][agent_type] = {
                    "exists": False,
                    "actions_defined": len(template["actions"]),
                    "actions_in_db": 0,
                    "missing_actions": len(template["actions"]),
                }
                continue

            # Get agent
            agent = Agents.objects.get(id=agent_id)

            # Get existing actions for this agent
            existing_actions = set(
                AgentAction.objects.filter(agent=agent).values_list("name", flat=True)
            )

            # Check which template actions are missing
            template_action_names = {
                action["name"] for action in template["actions"]
            }
            missing_actions = template_action_names - existing_actions

            status["agents"][agent_type] = {
                "exists": True,
                "agent_name": agent.name,
                "agent_status": agent.status,
                "actions_defined": len(template["actions"]),
                "actions_in_db": len(existing_actions),
                "missing_actions": len(missing_actions),
                "missing_action_names": list(missing_actions),
            }

            status["summary"]["total_actions"] += len(existing_actions)
            status["summary"]["missing_actions"] += len(missing_actions)

        return status

    def _close_old_connections(self):
        """Close all old database connections to prevent locks"""
        from django.db import connections
        for conn in connections.all():
            conn.close_if_unusable_or_obsolete()

    def _retry_with_backoff(self, func, max_retries=3, initial_delay=0.5):
        """Retry function with exponential backoff for DB locks"""
        for attempt in range(max_retries):
            try:
                return func()
            except OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"⚠️  Database locked, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    self._close_old_connections()
                else:
                    raise

    def sync_actions(self, agent_type: Optional[str] = None, dry_run: bool = False) -> Dict:
        """Sync actions from templates to database with retry logic"""
        result = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
        }

        # Filter templates if specific agent requested
        templates_to_process = (
            {agent_type: self.templates[agent_type]}
            if agent_type
            else self.templates
        )

        # Close old connections before starting
        self._close_old_connections()

        def _sync_batch():
            """Inner function to handle sync with proper transaction management"""
            local_result = {
                "created": 0,
                "updated": 0,
                "skipped": 0,
                "errors": [],
            }
            
            try:
                with transaction.atomic():
                    for current_agent_type, template in templates_to_process.items():
                        agent_id = self._resolve_agent(current_agent_type)

                        if not agent_id:
                            local_result["errors"].append(
                                f"Agent '{current_agent_type}' not found in database"
                            )
                            local_result["skipped"] += len(template["actions"])
                            continue

                        # Get agent INSIDE transaction
                        agent = Agents.objects.get(id=agent_id)

                        print(f"\n🤖 {agent.name} ({agent.agent_type}):")

                        for action_config in template["actions"]:
                            try:
                                if dry_run:
                                    # Check if action exists
                                    exists = AgentAction.objects.filter(
                                        agent=agent, name=action_config["name"]
                                    ).exists()
                                    status = "Would update" if exists else "Would create"
                                    print(f"  [DRY RUN] {status}: {action_config['display_name']}")
                                    continue

                                action, created = AgentAction.objects.update_or_create(
                                    agent=agent,
                                    name=action_config["name"],
                                    defaults={
                                        "display_name": action_config["display_name"],
                                        "description": action_config["description"],
                                        "order": action_config["order"],
                                        "is_active": True,
                                    },
                                )

                                if created:
                                    local_result["created"] += 1
                                    print(f"  ✅ Created: {action.display_name}")
                                else:
                                    local_result["updated"] += 1
                                    print(f"  🔄 Updated: {action.display_name}")

                            except Exception as e:
                                local_result["errors"].append(
                                    f"Error processing {action_config['name']}: {str(e)}"
                                )
                
                # Transaction committed successfully - now close connection
                self._close_old_connections()
                
            except Exception as e:
                # Transaction will rollback automatically on exception
                local_result["errors"].append(f"Transaction error: {str(e)}")
                raise
                
            return local_result

        # Execute with retry logic
        try:
            local_result = self._retry_with_backoff(_sync_batch)
            # Copy local_result to outer result
            result.update(local_result)
            
        except OperationalError as e:
            result["errors"].append(f"Database error after retries: {str(e)}")
            print("\n❌ FEHLER: Datenbank ist gesperrt!")
            print("💡 Lösung: Stoppe den Dev Server und versuche es erneut")
            print("   Befehl: Strg+C im Server-Terminal")

        return result

    def find_missing_actions(self) -> Dict[str, List[str]]:
        """Find all missing actions per agent"""
        missing = {}

        for agent_type, template in self.templates.items():
            agent_id = self._resolve_agent(agent_type)

            if not agent_id:
                missing[agent_type] = [
                    action["name"] for action in template["actions"]
                ]
                continue

            agent = Agents.objects.get(id=agent_id)
            existing_actions = set(
                AgentAction.objects.filter(agent=agent).values_list("name", flat=True)
            )

            template_action_names = {
                action["name"] for action in template["actions"]
            }
            missing_actions = template_action_names - existing_actions

            if missing_actions:
                missing[agent_type] = list(missing_actions)

        return missing


def print_status(status: Dict) -> None:
    """Print status report in compact table format"""
    print("\n" + "=" * 120)
    print("  AGENT ACTION STATUS REPORT")
    print("=" * 120)
    
    # Summary
    summary = status['summary']
    print(f"📊 Summary: {summary['total_agents']} Agents | "
          f"{summary['active_agents']} Active | "
          f"{summary['total_actions']} Actions in DB | "
          f"{summary['missing_actions']} Missing")
    
    if summary["missing_agents"]:
        print(f"❌ Missing Agents: {', '.join(summary['missing_agents'])}")
    
    print()
    
    # Table header
    print(f"{'ST':<3} {'AGENT TYPE':<25} {'NAME':<30} {'STATUS':<10} {'DEF':<4} {'DB':<4} {'MISS':<4}")
    print("-" * 120)
    
    # Table rows
    for agent_type, info in sorted(status["agents"].items()):
        if not info["exists"]:
            status_icon = "❌"
            agent_name = "NOT FOUND"
            agent_status = "-"
            actions_in_db = "-"
            missing_count = str(info['actions_defined'])
        else:
            status_icon = "✅" if info["missing_actions"] == 0 else "⚠️"
            agent_name = info['agent_name'][:28]  # Truncate if too long
            agent_status = info['agent_status'][:9].upper()
            actions_in_db = str(info['actions_in_db'])
            missing_count = str(info['missing_actions'])
        
        print(f"{status_icon:<3} "
              f"{agent_type:<25} "
              f"{agent_name:<30} "
              f"{agent_status:<10} "
              f"{info['actions_defined']:<4} "
              f"{actions_in_db:<4} "
              f"{missing_count:<4}")
        
        # Show missing action details if any
        if info.get("missing_actions", 0) > 0 and info.get("missing_action_names"):
            missing_actions_str = ", ".join(info["missing_action_names"])
            print(f"     ⚠️  Missing: {missing_actions_str}")
    
    print("=" * 120)
    print("\nLegende: ST=Status, DEF=Definiert (Template), DB=In Database, MISS=Fehlend")
    print()


# Agent Type Registry - Pre-defined agent types with defaults
AGENT_TYPE_REGISTRY = {
    "planning_agent": {
        "name": "Planning Agent",
        "description": "Handles project planning, structure, and organization",
        "system_prompt": "You are a planning specialist focused on project structure and organization. Analyze requirements, create outlines, and structure projects effectively.",
        "category": "planning"
    },
    "project_manager_agent": {
        "name": "Project Manager Agent",
        "description": "Manages project workflow, timelines, and coordination",
        "system_prompt": "You are a project management specialist. Coordinate tasks, manage timelines, and ensure project success.",
        "category": "management"
    },
    "writer_agent": {
        "name": "Content Writing Agent",
        "description": "General writing and content enhancement",
        "system_prompt": "You are a professional writer specialized in content creation and enhancement. Write engaging, polished content.",
        "category": "writing"
    },
    "chapter_agent": {
        "name": "Chapter Writing Agent",
        "description": "Specialized in chapter writing and narrative development",
        "system_prompt": "You are a chapter writing specialist. Create compelling chapters with strong narrative flow and engaging content.",
        "category": "writing"
    },
    "character_agent": {
        "name": "Character Development Agent",
        "description": "Creates and develops character profiles and arcs",
        "system_prompt": "You are a character development specialist. Create compelling, multi-dimensional characters with depth and authenticity.",
        "category": "character"
    },
    "story_agent": {
        "name": "Story Structure Agent",
        "description": "Handles story structure, plot, and narrative arcs",
        "system_prompt": "You are a story structure specialist. Design compelling plots, manage narrative arcs, and ensure story coherence.",
        "category": "story"
    },
    "outline_agent": {
        "name": "Outline Agent",
        "description": "Creates structured outlines and content frameworks",
        "system_prompt": "You are an outlining specialist. Create clear, logical outlines that guide content development.",
        "category": "planning"
    },
    "consistency_agent": {
        "name": "Consistency Checker Agent",
        "description": "Validates consistency across content and story elements",
        "system_prompt": "You are a consistency specialist. Identify contradictions, validate continuity, and ensure coherent narratives.",
        "category": "analysis"
    },
    "world_conflict_agent": {
        "name": "World & Conflict Agent",
        "description": "Develops world-building and conflict structures",
        "system_prompt": "You are a world-building and conflict specialist. Create rich worlds and compelling conflicts.",
        "category": "world"
    },
    "prompt_agent": {
        "name": "Prompt Engineering Agent",
        "description": "Optimizes and refines AI prompts",
        "system_prompt": "You are a prompt engineering specialist. Craft effective, precise prompts for optimal AI responses.",
        "category": "technical"
    },
    "research_agent": {
        "name": "Research Agent",
        "description": "Conducts research and gathers information",
        "system_prompt": "You are a research specialist. Gather, analyze, and synthesize information effectively.",
        "category": "analysis"
    },
    "editor_agent": {
        "name": "Editor Agent",
        "description": "Reviews and refines content for quality and polish",
        "system_prompt": "You are an editorial specialist. Review, refine, and polish content to professional standards.",
        "category": "editing"
    },
}


def suggest_actions_for_agent(agent_type: str, description: str) -> List[Dict]:
    """Suggest actions based on agent type and description"""
    # Get category from registry
    category = "general"
    if agent_type in AGENT_TYPE_REGISTRY:
        category = AGENT_TYPE_REGISTRY[agent_type]["category"]
    
    # Action patterns by category
    action_patterns = {
        "planning": [
            {"name": "analyze_requirements", "display": "Analyze Requirements", "desc": "Analyze and validate project requirements"},
            {"name": "generate_outline", "display": "Generate Outline", "desc": "Create structured project outline"},
            {"name": "create_structure", "display": "Create Structure", "desc": "Define project structure and hierarchy"},
            {"name": "validate_plan", "display": "Validate Plan", "desc": "Validate planning consistency and completeness"},
        ],
        "writing": [
            {"name": "write_content", "display": "Write Content", "desc": "Generate initial content draft"},
            {"name": "enhance_text", "display": "Enhance Text", "desc": "Improve and polish existing text"},
            {"name": "improve_flow", "display": "Improve Flow", "desc": "Enhance narrative flow and pacing"},
            {"name": "check_style", "display": "Check Style", "desc": "Validate writing style and tone"},
        ],
        "analysis": [
            {"name": "analyze_content", "display": "Analyze Content", "desc": "Perform content analysis"},
            {"name": "extract_insights", "display": "Extract Insights", "desc": "Extract key insights and patterns"},
            {"name": "generate_report", "display": "Generate Report", "desc": "Create analysis report"},
            {"name": "validate_consistency", "display": "Validate Consistency", "desc": "Check for inconsistencies"},
        ],
        "character": [
            {"name": "develop_character", "display": "Develop Character", "desc": "Create detailed character profile"},
            {"name": "enhance_backstory", "display": "Enhance Backstory", "desc": "Develop character backstory"},
            {"name": "define_arc", "display": "Define Character Arc", "desc": "Define character development arc"},
            {"name": "create_relationships", "display": "Create Relationships", "desc": "Define character relationships"},
        ],
        "story": [
            {"name": "develop_plot", "display": "Develop Plot", "desc": "Create story plot and structure"},
            {"name": "design_arc", "display": "Design Story Arc", "desc": "Design narrative arc"},
            {"name": "create_tension", "display": "Create Tension", "desc": "Build dramatic tension"},
            {"name": "resolve_conflicts", "display": "Resolve Conflicts", "desc": "Resolve story conflicts"},
        ],
        "world": [
            {"name": "build_world", "display": "Build World", "desc": "Create world-building details"},
            {"name": "design_conflicts", "display": "Design Conflicts", "desc": "Design conflict structures"},
            {"name": "create_systems", "display": "Create Systems", "desc": "Define world systems and rules"},
        ],
        "editing": [
            {"name": "review_content", "display": "Review Content", "desc": "Comprehensive content review"},
            {"name": "polish_text", "display": "Polish Text", "desc": "Final polish and refinement"},
            {"name": "check_grammar", "display": "Check Grammar", "desc": "Grammar and syntax check"},
        ],
    }
    
    # Return actions for category
    if category in action_patterns:
        return action_patterns[category]
    
    # Default suggestions
    return [
        {"name": "process_content", "display": "Process Content", "desc": "Process and transform content"},
        {"name": "analyze_data", "display": "Analyze Data", "desc": "Analyze input data"},
        {"name": "generate_output", "display": "Generate Output", "desc": "Generate structured output"},
    ]


def create_agent_wizard():
    """Interactive wizard to create new agent with template"""
    print("\n" + "=" * 70)
    print("  🤖 NEUER AGENT ERSTELLEN - INTERACTIVE WIZARD")
    print("=" * 70)
    print()
    
    # Step 1: Select Agent Type from Registry
    print("📋 SCHRITT 1: Agent-Typ auswählen")
    print("-" * 70)
    print("Verfügbare Agent-Typen:\n")
    
    # Group by category for better overview
    categories = {}
    for agent_type, config in AGENT_TYPE_REGISTRY.items():
        category = config["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append((agent_type, config))
    
    # Display grouped by category
    agent_list = []
    index = 1
    for category, agents in sorted(categories.items()):
        print(f"  [{category.upper()}]")
        for agent_type, config in sorted(agents, key=lambda x: x[1]["name"]):
            print(f"    {index:2}. {agent_type:<25} - {config['name']}")
            agent_list.append((agent_type, config))
            index += 1
        print()
    
    print(f"    {index}. [CUSTOM] - Eigener Agent-Typ")
    print()
    
    # Get selection
    choice = input("Deine Wahl (Nummer oder Agent-Type): ").strip()
    
    # Parse selection
    agent_type = None
    agent_config = None
    
    if choice.isdigit():
        choice_num = int(choice)
        if 1 <= choice_num <= len(agent_list):
            agent_type, agent_config = agent_list[choice_num - 1]
        elif choice_num == len(agent_list) + 1:
            # Custom agent
            agent_type = input("\nAgent Type (z.B. 'custom_agent'): ").strip().lower().replace(" ", "_")
            if not agent_type:
                print("❌ Agent Type erforderlich!")
                return
            agent_config = None
    else:
        # Direct agent_type input
        agent_type = choice.lower().replace(" ", "_")
        if agent_type in AGENT_TYPE_REGISTRY:
            agent_config = AGENT_TYPE_REGISTRY[agent_type]
    
    if not agent_type:
        print("❌ Ungültige Auswahl!")
        return
    
    print()
    print(f"✅ Agent-Typ: {agent_type}")
    print()
    
    # Step 2: Configure Agent (with defaults from registry)
    print("📋 SCHRITT 2: Agent konfigurieren")
    print("-" * 70)
    
    if agent_config:
        # Show defaults
        print(f"Standardwerte für '{agent_type}':")
        print(f"  Name:        {agent_config['name']}")
        print(f"  Beschreibung: {agent_config['description']}")
        print(f"  Kategorie:   {agent_config['category']}")
        print()
        
        use_defaults = input("Standard-Werte übernehmen? (ja/nein): ").strip().lower()
        
        if use_defaults in ["ja", "j", "yes", "y"]:
            agent_name = agent_config["name"]
            description = agent_config["description"]
            system_prompt = agent_config["system_prompt"]
        else:
            agent_name = input(f"Agent Name [{agent_config['name']}]: ").strip() or agent_config["name"]
            description = input(f"Beschreibung [{agent_config['description']}]: ").strip() or agent_config["description"]
            system_prompt = input("System Prompt (Enter für Standard): ").strip() or agent_config["system_prompt"]
    else:
        # Custom agent - no defaults
        agent_name = input("Agent Name: ").strip()
        if not agent_name:
            print("❌ Agent Name erforderlich!")
            return
        
        description = input("Beschreibung: ").strip()
        if not description:
            description = f"{agent_name} - AI Agent"
        
        system_prompt = input("System Prompt: ").strip()
        if not system_prompt:
            system_prompt = f"You are {agent_name.lower()}, specialized in {description.lower()}."
    
    print()
    print("✅ Konfiguration:")
    print(f"   Name:   {agent_name}")
    print(f"   Type:   {agent_type}")
    print(f"   Desc:   {description[:50]}...")
    print()
    
    # Step 3: Action Suggestions
    print("📋 SCHRITT 3: Actions definieren")
    print("-" * 70)
    print(f"Basierend auf '{description}' schlage ich folgende Actions vor:\n")
    
    suggested_actions = suggest_actions_for_agent(agent_type, description)
    
    for i, action in enumerate(suggested_actions, 1):
        print(f"  {i}. {action['name']:<25} - {action['desc']}")
    
    print()
    print("Optionen:")
    print("  [a] Alle übernehmen")
    print("  [b] Auswählen (z.B. '1,2,4')")
    print("  [c] Eigene Actions eingeben")
    print("  [d] Abbrechen")
    print()
    
    choice = input("Deine Wahl: ").strip().lower()
    
    actions = []
    if choice == "a":
        actions = suggested_actions
    elif choice == "b":
        indices = input("Nummern (z.B. 1,2,4): ").strip()
        try:
            selected = [int(i.strip()) - 1 for i in indices.split(",")]
            actions = [suggested_actions[i] for i in selected if 0 <= i < len(suggested_actions)]
        except (ValueError, IndexError):
            print("❌ Ungültige Auswahl!")
            return
    elif choice == "c":
        print("\nEigene Actions eingeben (leer lassen zum Beenden):")
        while True:
            action_name = input(f"  Action #{len(actions) + 1} Name (z.B. 'analyze_project'): ").strip()
            if not action_name:
                break
            display_name = input("  Display Name (z.B. 'Analyze Project'): ").strip() or action_name.replace("_", " ").title()
            desc = input("  Beschreibung: ").strip() or f"{display_name} action"
            actions.append({"name": action_name, "display": display_name, "desc": desc})
    else:
        print("❌ Abgebrochen")
        return
    
    if not actions:
        print("❌ Mindestens eine Action erforderlich!")
        return
    
    print()
    
    # Step 4: Generate Template
    print("📋 SCHRITT 4: Template generieren")
    print("-" * 70)
    
    template_content = f"""
# {agent_name} - Auto-generated Template
# Created: {time.strftime('%Y-%m-%d %H:%M:%S')}

agent_action_templates:
  {agent_type}:
    description: "{description}"
    system_prompt: "{system_prompt}"
    actions:
"""
    
    for i, action in enumerate(actions, 1):
        template_content += f"""
      - name: "{action['name']}"
        display_name: "{action['display']}"
        description: "{action['desc']}"
        order: {i}
"""
    
    print("\n✅ Template generiert!")
    print("\nVorschau:")
    print("-" * 70)
    print(template_content)
    print("-" * 70)
    print()
    
    # Step 5: Save Options
    print("📋 SCHRITT 5: Speichern & Erstellen")
    print("-" * 70)
    
    save_template = input("Template in YAML speichern? (ja/nein): ").strip().lower()
    if save_template in ["ja", "j", "yes", "y"]:
        template_file = Path("config") / f"agent_template_{agent_type}.yaml"
        template_file.write_text(template_content, encoding="utf-8")
        print(f"✅ Template gespeichert: {template_file}")
    
    create_in_db = input("\nAgent in Datenbank erstellen? (ja/nein): ").strip().lower()
    if create_in_db in ["ja", "j", "yes", "y"]:
        # Check if LLM exists
        from apps.bfagent.models import Llms
        default_llm = Llms.objects.filter(is_active=True).first()
        
        if not default_llm:
            print("❌ Kein aktives LLM gefunden! Bitte erst LLM erstellen.")
        else:
            try:
                agent = Agents.objects.create(
                    name=agent_name,
                    agent_type=agent_type,
                    status="active",
                    description=description,
                    system_prompt=system_prompt,
                    llm_model_id=default_llm.id,
                    creativity_level=0.7,
                    consistency_weight=0.8
                )
                print(f"✅ Agent erstellt: {agent.name} (ID: {agent.id})")
                
                # Add to main template
                add_to_main = input("\nZu Haupt-Template hinzufügen? (ja/nein): ").strip().lower()
                if add_to_main in ["ja", "j", "yes", "y"]:
                    main_template = Path("config/agent_action_templates.yaml")
                    if main_template.exists():
                        with main_template.open("a", encoding="utf-8") as f:
                            f.write("\n" + template_content)
                        print("✅ Zu Haupt-Template hinzugefügt!")
                
                # Sync actions
                sync_now = input("\nActions jetzt synchronisieren? (ja/nein): ").strip().lower()
                if sync_now in ["ja", "j", "yes", "y"]:
                    # Reload manager with new template
                    manager = AgentActionManager()
                    result = manager.sync_actions(agent_type=agent_type)
                    print_sync_results(result)
                
            except Exception as e:
                print(f"❌ Fehler beim Erstellen: {e}")
    
    print("\n🎉 FERTIG!")
    print("=" * 70)


def interactive_menu():
    """Interactive CLI menu for agent action management"""
    print("\n" + "=" * 70)
    print("  BF AGENT - AGENT ACTION MANAGER")
    print("=" * 70)
    print("\nWähle eine Option:\n")
    print("  1. 📊 Status anzeigen (alle Agents)")
    print("  2. 🔄 Sync - Alle Actions synchronisieren")
    print("  3. 🔍 Sync (Dry-Run) - Vorschau ohne Änderungen")
    print("  4. ⚠️  Missing - Fehlende Actions auflisten")
    print("  5. 🔧 Fix - Einzelnen Agent reparieren")
    print("  6. ⚡ Quick Fix - Häufige Probleme beheben")
    print("  7. 📋 Agent Liste anzeigen")
    print("  8. 🤖 NEUER AGENT ERSTELLEN (Wizard)")
    print("  9. ❌ Beenden")
    print()
    
    choice = input("Deine Wahl (1-9): ").strip()
    
    manager = AgentActionManager()
    
    if choice == "1":
        print("\n🔍 Lade Status...")
        status = manager.get_status()
        print_status(status)
        
    elif choice == "2":
        print("\n🔄 Starte Synchronisation...")
        confirm = input("⚠️  Änderungen werden in DB geschrieben. Fortfahren? (ja/nein): ")
        if confirm.lower() in ["ja", "j", "yes", "y"]:
            result = manager.sync_actions(dry_run=False)
            print_sync_results(result)
        else:
            print("❌ Abgebrochen")
            
    elif choice == "3":
        print("\n🔍 Dry-Run Synchronisation...")
        result = manager.sync_actions(dry_run=True)
        print_sync_results(result)
        
    elif choice == "4":
        print("\n⚠️  Suche fehlende Actions...")
        missing = manager.find_missing_actions()
        if not missing:
            print("\n✅ Alle Actions sind synchronisiert!")
        else:
            print("\n⚠️  Fehlende Actions:")
            for agent_type, actions in missing.items():
                print(f"\n{agent_type}:")
                for action in actions:
                    print(f"  - {action}")
                    
    elif choice == "5":
        print("\n🔧 Einzelnen Agent reparieren")
        print("\nVerfügbare Agent-Types:")
        for i, agent_type in enumerate(manager.templates.keys(), 1):
            print(f"  {i}. {agent_type}")
        
        agent_choice = input("\nAgent-Nummer wählen: ").strip()
        try:
            agent_idx = int(agent_choice) - 1
            agent_types = list(manager.templates.keys())
            if 0 <= agent_idx < len(agent_types):
                selected_agent = agent_types[agent_idx]
                print(f"\n🔧 Repariere {selected_agent}...")
                result = manager.sync_actions(agent_type=selected_agent, dry_run=False)
                print_sync_results(result)
            else:
                print("❌ Ungültige Nummer")
        except ValueError:
            print("❌ Bitte eine Nummer eingeben")
            
    elif choice == "6":
        print("\n⚡ Quick Fix - Häufigste Probleme beheben")
        print("Repariere: planning_agent, writer_agent, outline_agent")
        for agent in ["planning_agent", "writer_agent", "outline_agent"]:
            print(f"\n🔧 {agent}...")
            result = manager.sync_actions(agent_type=agent, dry_run=False)
            
    elif choice == "7":
        print("\n📋 Agents in Database:")
        agents = Agents.objects.all().order_by("agent_type")
        for agent in agents:
            action_count = AgentAction.objects.filter(agent=agent).count()
            status_icon = "✅" if agent.status.lower() == "active" else "⚪"
            print(f"  {status_icon} {agent.agent_type:<30} | {agent.name:<30} | {agent.status:<10} | {action_count:>3} actions")
    
    elif choice == "8":
        print("\n🤖 Agent Creator Wizard wird gestartet...")
        create_agent_wizard()
            
    elif choice == "9":
        print("\n👋 Auf Wiedersehen!")
        return
        
    else:
        print("\n❌ Ungültige Wahl")
    
    print("\n" + "=" * 70)
    input("\nDrücke Enter um zurück zum Menü zu kommen...")
    interactive_menu()  # Recursive call for menu loop


def print_sync_results(result: Dict):
    """Print sync results in formatted way"""
    print("\n" + "=" * 70)
    print("  SYNC RESULTS")
    print("=" * 70)
    print(f"✅ Created: {result['created']}")
    print(f"🔄 Updated: {result['updated']}")
    print(f"⏭️  Skipped: {result['skipped']}")

    if result["errors"]:
        print(f"\n❌ Errors ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  - {error}")

    print("\n✅ Sync complete!")


def main():
    parser = argparse.ArgumentParser(
        description="BF Agent Enterprise Action Manager"
    )
    parser.add_argument(
        "command",
        nargs="?",  # Make command optional
        choices=["sync", "status", "missing", "fix", "interactive"],
        help="Command to run (omit for interactive mode)",
    )
    parser.add_argument(
        "--agent", help="Specific agent type to process"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--template",
        default="config/agent_action_templates.yaml",
        help="Path to template file",
    )

    args = parser.parse_args()
    
    # If no command given, start interactive mode
    if not args.command:
        interactive_menu()
        return

    manager = AgentActionManager(template_path=args.template)

    if args.command == "status":
        print("🔍 Analyzing agent action status...")
        status = manager.get_status()
        print_status(status)

    elif args.command == "missing":
        print("🔍 Finding missing actions...")
        missing = manager.find_missing_actions()

        if not missing:
            print("\n✅ All actions are synced!")
        else:
            print("\n⚠️  Missing Actions:")
            for agent_type, actions in missing.items():
                print(f"\n{agent_type}:")
                for action in actions:
                    print(f"  - {action}")

    elif args.command == "sync":
        print("🔄 Syncing actions from templates...")
        result = manager.sync_actions(agent_type=args.agent, dry_run=args.dry_run)

        print("\n" + "=" * 70)
        print("  SYNC RESULTS")
        print("=" * 70)
        print(f"✅ Created: {result['created']}")
        print(f"🔄 Updated: {result['updated']}")
        print(f"⏭️  Skipped: {result['skipped']}")

        if result["errors"]:
            print(f"\n❌ Errors ({len(result['errors'])}):")
            for error in result["errors"]:
                print(f"  - {error}")

        print("\n✅ Sync complete!")

    elif args.command == "fix":
        if not args.agent:
            print("❌ Error: --agent required for fix command")
            sys.exit(1)

        print(f"🔧 Fixing actions for {args.agent}...")
        result = manager.sync_actions(agent_type=args.agent, dry_run=args.dry_run)

        print(f"\n✅ Fixed! Created {result['created']}, Updated {result['updated']}")


if __name__ == "__main__":
    main()
