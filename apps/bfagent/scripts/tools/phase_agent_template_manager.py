#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase-Agent-Template Management Tool
Enterprise tool for managing Phase-Agent mappings and Context Variables

Usage:
    python scripts/phase_agent_template_manager.py [command] [options]
    
Commands:
    check       - Check current status
    sync        - Synchronize phase-agent mappings
    context     - Add context variables to templates
    all         - Run all operations (sync + context + check)
    
Options:
    --dry-run   - Show what would be done without making changes
    --verbose   - Show detailed output
"""
import os
import sys
import django
import argparse
from pathlib import Path

# Fix Windows Unicode
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.bfagent.models import (
    WorkflowPhase,
    Agents,
    AgentAction,
    PromptTemplate,
    PhaseAgentConfig,
)


class PhaseAgentTemplateManager:
    """Enterprise manager for Phase-Agent-Template system"""
    
    # Configuration: Phase -> Agent mappings (COMPLETE - Only agents WITH actions!)
    PHASE_AGENT_MAPPINGS = {
        "Planning": "Project Manager Agent",        # Has: Track Progress, Suggest Next Steps, etc.
        "Outlining": "Outline Agent",               # Has: Generate Full Outline, Refine Outline, etc.
        "World Building": "World & Conflict Agent", # Has: Expand World Details, Develop Conflict, etc.
        "Character Development": "Character Agent", # Has: Generate Character Cast, Develop Backstory, etc.
        "Writing": "Chapter Writing Agent",         # Has: Generate Chapter Outline, Write Draft, etc.
        "Revision": "Consistency Checker Agent",    # Has: Check Consistency, Check Timeline, etc.
        "Editing": "Consistency Checker Agent",     # Has: Check Consistency, Check Voice, etc.
        "Review": "Consistency Checker Agent",      # Has: Check Consistency, Check Setting, etc.
        "Publishing": "Project Manager Agent",      # Has: Track Progress, Estimate Completion, etc.
        "Finalization": "Project Manager Agent",    # Has: Track Progress, Identify Bottlenecks, etc.
    }
    
    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            "phases_synced": 0,
            "phases_skipped": 0,
            "templates_updated": 0,
            "templates_skipped": 0,
            "errors": 0,
        }
    
    def print_header(self, title):
        """Print formatted header"""
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)
    
    def print_status(self, status, message):
        """Print formatted status message"""
        symbols = {"OK": "[OK]", "SKIP": "[SKIP]", "ERROR": "[ERROR]", "INFO": "[*]"}
        print(f"   {symbols.get(status, '[?]')} {message}")
    
    def check_status(self):
        """Check current system status"""
        self.print_header("SYSTEM STATUS CHECK")
        
        # Check phases
        all_phases = WorkflowPhase.objects.all()
        total_phases = all_phases.count()
        phases_with_agents = 0
        
        print("\n[*] Workflow Phases:")
        for phase in all_phases.order_by('name'):
            agent_count = PhaseAgentConfig.objects.filter(phase=phase).count()
            if agent_count > 0:
                phases_with_agents += 1
            status = "YES" if agent_count > 0 else "NO"
            print(f"   {phase.name}: {agent_count} agents [{status}]")
        
        phase_coverage = (phases_with_agents / total_phases * 100) if total_phases > 0 else 0
        print(f"\n[COVERAGE] {phases_with_agents}/{total_phases} phases have agents ({phase_coverage:.0f}%)")
        
        # Check templates
        all_actions = AgentAction.objects.filter(prompt_template__isnull=False)
        total_templates = all_actions.count()
        templates_with_context = 0
        
        print("\n[*] Prompt Templates:")
        for action in all_actions.select_related('prompt_template'):
            if "{{ context }}" in action.prompt_template.template_text:
                templates_with_context += 1
        
        template_coverage = (templates_with_context / total_templates * 100) if total_templates > 0 else 0
        print(f"[COVERAGE] {templates_with_context}/{total_templates} templates have context variables ({template_coverage:.0f}%)")
        
        # Summary
        print("\n" + "=" * 80)
        if phase_coverage == 100 and template_coverage == 100:
            print("[SUCCESS] System is fully configured!")
        else:
            print(f"[WARNING] Phase Coverage: {phase_coverage:.0f}% | Template Coverage: {template_coverage:.0f}%")
        print("=" * 80)
        
        return phase_coverage == 100 and template_coverage == 100
    
    def sync_phase_agents(self):
        """Synchronize phase-agent mappings"""
        self.print_header("SYNCHRONIZING PHASE-AGENT MAPPINGS")
        
        print("\n[*] Processing mappings...")
        
        for phase_name, agent_name in self.PHASE_AGENT_MAPPINGS.items():
            try:
                # Get phase and agent
                phase = WorkflowPhase.objects.get(name=phase_name)
                agent = Agents.objects.get(name=agent_name)
                
                # Check if mapping exists
                existing = PhaseAgentConfig.objects.filter(phase=phase, agent=agent).exists()
                
                if existing:
                    self.print_status("SKIP", f"{phase_name} -> {agent_name} (already exists)")
                    self.stats["phases_skipped"] += 1
                else:
                    if not self.dry_run:
                        PhaseAgentConfig.objects.create(
                            phase=phase,
                            agent=agent,
                            is_required=False,
                            order=0,
                            description=f"Auto-assigned agent for {phase_name} phase"
                        )
                    action = "Would create" if self.dry_run else "Created"
                    self.print_status("OK", f"{action}: {phase_name} -> {agent_name}")
                    self.stats["phases_synced"] += 1
                    
            except WorkflowPhase.DoesNotExist:
                self.print_status("ERROR", f"Phase not found: {phase_name}")
                self.stats["errors"] += 1
            except Agents.DoesNotExist:
                self.print_status("ERROR", f"Agent not found: {agent_name}")
                self.stats["errors"] += 1
            except Exception as e:
                self.print_status("ERROR", f"{phase_name}: {e}")
                self.stats["errors"] += 1
        
        print(f"\n[SUMMARY] Synced: {self.stats['phases_synced']} | Skipped: {self.stats['phases_skipped']} | Errors: {self.stats['errors']}")
    
    def add_context_variables(self):
        """Add context variables to all templates"""
        self.print_header("ADDING CONTEXT VARIABLES TO TEMPLATES")
        
        print("\n[*] Processing all templates...")
        
        all_actions = AgentAction.objects.filter(prompt_template__isnull=False).select_related('prompt_template', 'agent')
        
        for action in all_actions:
            try:
                template = action.prompt_template
                
                # Check if context variables exist
                has_context = "{{ context }}" in template.template_text
                has_requirements = "{{ requirements }}" in template.template_text
                
                if has_context and has_requirements:
                    if self.verbose:
                        self.print_status("SKIP", f"{action.agent.name} -> {action.display_name}")
                    self.stats["templates_skipped"] += 1
                    continue
                
                # Add context sections
                template_text = template.template_text
                
                if "## Output" in template_text:
                    parts = template_text.split("## Output")
                    context_section = "\n\n## Input Context\n{{ context }}\n\n## Requirements\n{{ requirements }}\n\n"
                    template_text = parts[0] + context_section + "## Output" + parts[1]
                else:
                    template_text += "\n\n## Input Context\n{{ context }}\n\n## Requirements\n{{ requirements }}\n"
                
                if not self.dry_run:
                    template.template_text = template_text
                    template.save()
                
                action_text = "Would update" if self.dry_run else "Updated"
                self.print_status("OK", f"{action_text}: {action.agent.name} -> {action.display_name}")
                self.stats["templates_updated"] += 1
                
            except Exception as e:
                self.print_status("ERROR", f"{action.display_name}: {e}")
                self.stats["errors"] += 1
        
        print(f"\n[SUMMARY] Updated: {self.stats['templates_updated']} | Skipped: {self.stats['templates_skipped']} | Errors: {self.stats['errors']}")
    
    def run_all(self):
        """Run all operations"""
        self.print_header("RUNNING COMPLETE SYNC")
        
        # Step 1: Sync phase-agents
        self.sync_phase_agents()
        
        # Step 2: Add context variables
        self.add_context_variables()
        
        # Step 3: Check status
        success = self.check_status()
        
        # Final summary
        self.print_header("FINAL SUMMARY")
        print(f"Phase-Agent Mappings: {self.stats['phases_synced']} created, {self.stats['phases_skipped']} skipped")
        print(f"Template Updates: {self.stats['templates_updated']} updated, {self.stats['templates_skipped']} skipped")
        print(f"Errors: {self.stats['errors']}")
        
        if self.dry_run:
            print("\n[DRY RUN] No changes were made. Run without --dry-run to apply changes.")
        
        if success and not self.dry_run:
            print("\n[SUCCESS] System is fully configured and ready for testing!")
        
        return success


def main():
    parser = argparse.ArgumentParser(
        description="Phase-Agent-Template Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "command",
        choices=["check", "sync", "context", "all"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    manager = PhaseAgentTemplateManager(dry_run=args.dry_run, verbose=args.verbose)
    
    if args.command == "check":
        manager.check_status()
    elif args.command == "sync":
        manager.sync_phase_agents()
    elif args.command == "context":
        manager.add_context_variables()
    elif args.command == "all":
        manager.run_all()


if __name__ == "__main__":
    main()
