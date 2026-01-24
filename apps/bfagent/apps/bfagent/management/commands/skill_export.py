#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Management Command: skill_export

Exportiert Skills als SKILL.md gemäß AgentSkills.io Standard.

Usage:
    # Export all skills
    python manage.py skill_export ./skills/
    
    # Export specific skill
    python manage.py skill_export ./skills/ --skill research-skill
    
    # Validate only
    python manage.py skill_export --validate research-skill
    
    # List all skills
    python manage.py skill_export --list

Spec: https://agentskills.io/specification
"""
import os
import re
from django.core.management.base import BaseCommand, CommandError
from apps.bfagent.models import PromptTemplate


class Command(BaseCommand):
    help = "Export skills as SKILL.md (AgentSkills.io format)"
    
    def add_arguments(self, parser):
        parser.add_argument(
            "output_dir",
            nargs="?",
            default="./skills",
            help="Output directory for SKILL.md files",
        )
        parser.add_argument(
            "--skill",
            "-s",
            help="Export specific skill by template_key",
        )
        parser.add_argument(
            "--validate",
            metavar="SKILL_KEY",
            help="Validate a skill without exporting",
        )
        parser.add_argument(
            "--list",
            "-l",
            action="store_true",
            help="List all available skills",
        )
        parser.add_argument(
            "--active-only",
            action="store_true",
            default=True,
            help="Only export active skills (default: True)",
        )
    
    def handle(self, *args, **options):
        # List mode
        if options["list"]:
            return self.list_skills()
        
        # Validate mode
        if options["validate"]:
            return self.validate_skill(options["validate"])
        
        # Export mode
        output_dir = options["output_dir"]
        skill_key = options.get("skill")
        active_only = options.get("active_only", True)
        
        if skill_key:
            self.export_single_skill(skill_key, output_dir)
        else:
            self.export_all_skills(output_dir, active_only)
    
    def list_skills(self):
        """List all skills with their status."""
        self.stdout.write("\n📋 Available Skills:\n")
        self.stdout.write("-" * 70)
        
        skills = PromptTemplate.objects.exclude(
            skill_description=""
        ).order_by("category", "template_key")
        
        if not skills.exists():
            self.stdout.write(self.style.WARNING(
                "\nNo skills found. Add skill_description to PromptTemplates.\n"
            ))
            return
        
        current_category = None
        for skill in skills:
            if skill.category != current_category:
                current_category = skill.category
                self.stdout.write(f"\n🏷️  {skill.get_category_display()}:")
            
            status = "✅" if skill.is_active else "❌"
            version = f"v{skill.version}"
            self.stdout.write(
                f"  {status} {skill.template_key:<30} {version:<8} "
                f"({skill.usage_count} uses)"
            )
        
        total = skills.count()
        active = skills.filter(is_active=True).count()
        self.stdout.write(f"\n\nTotal: {total} skills ({active} active)\n")
    
    def validate_skill(self, skill_key: str):
        """Validate a skill against AgentSkills.io spec."""
        self.stdout.write(f"\n🔍 Validating: {skill_key}\n")
        self.stdout.write("-" * 50)
        
        try:
            skill = PromptTemplate.objects.get(template_key=skill_key)
        except PromptTemplate.DoesNotExist:
            raise CommandError(f"Skill not found: {skill_key}")
        
        errors = []
        warnings = []
        
        # Required: name (1-64 chars, lowercase, hyphens)
        name_pattern = r'^[a-z][a-z0-9-]{0,62}[a-z0-9]$|^[a-z]$'
        if not re.match(name_pattern, skill_key):
            if skill_key != skill_key.lower():
                errors.append("name must be lowercase")
            if "--" in skill_key:
                errors.append("name cannot contain consecutive hyphens")
            if skill_key.startswith("-") or skill_key.endswith("-"):
                errors.append("name cannot start or end with hyphen")
            if len(skill_key) > 64:
                errors.append(f"name too long: {len(skill_key)} > 64 chars")
        
        # Required: description (1-1024 chars)
        desc = skill.skill_description or skill.description
        if not desc:
            errors.append("description is required")
        elif len(desc) > 1024:
            errors.append(f"description too long: {len(desc)} > 1024 chars")
        elif len(desc) < 20:
            warnings.append("description should be more detailed")
        
        # Optional: compatibility (max 500 chars)
        if skill.compatibility and len(skill.compatibility) > 500:
            errors.append(f"compatibility too long: {len(skill.compatibility)} > 500")
        
        # Content checks
        if not skill.system_prompt and not skill.user_prompt_template:
            warnings.append("No prompt content defined")
        
        if not skill.required_variables and skill.user_prompt_template:
            if "{{" in skill.user_prompt_template:
                warnings.append("Template has variables but required_variables is empty")
        
        # Report
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f"  ❌ {e}"))
        
        if warnings:
            for w in warnings:
                self.stdout.write(self.style.WARNING(f"  ⚠️  {w}"))
        
        if not errors and not warnings:
            self.stdout.write(self.style.SUCCESS("  ✅ Skill is valid!"))
        elif not errors:
            self.stdout.write(self.style.SUCCESS(
                f"\n  ✅ Valid with {len(warnings)} warning(s)"
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"\n  ❌ Invalid: {len(errors)} error(s), {len(warnings)} warning(s)"
            ))
        
        # Show export preview
        self.stdout.write("\n📄 SKILL.md Preview:")
        self.stdout.write("-" * 50)
        content = skill.to_agentskills_format()
        # Show first 30 lines
        lines = content.split("\n")[:30]
        for line in lines:
            self.stdout.write(f"  {line}")
        if len(content.split("\n")) > 30:
            self.stdout.write("  ...")
        self.stdout.write("")
    
    def export_single_skill(self, skill_key: str, output_dir: str):
        """Export a single skill."""
        try:
            skill = PromptTemplate.objects.get(template_key=skill_key)
        except PromptTemplate.DoesNotExist:
            raise CommandError(f"Skill not found: {skill_key}")
        
        path = self._export_skill(skill, output_dir)
        self.stdout.write(self.style.SUCCESS(f"✅ Exported: {path}"))
    
    def export_all_skills(self, output_dir: str, active_only: bool = True):
        """Export all skills."""
        queryset = PromptTemplate.objects.exclude(skill_description="")
        
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        if not queryset.exists():
            self.stdout.write(self.style.WARNING(
                "No skills to export. Add skill_description to PromptTemplates."
            ))
            return
        
        self.stdout.write(f"\n📦 Exporting {queryset.count()} skills to {output_dir}/\n")
        
        exported = []
        for skill in queryset:
            try:
                path = self._export_skill(skill, output_dir)
                exported.append(path)
                self.stdout.write(f"  ✅ {skill.template_key}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"  ❌ {skill.template_key}: {e}"
                ))
        
        self.stdout.write(f"\n✅ Exported {len(exported)} skills\n")
    
    def _export_skill(self, skill: PromptTemplate, output_dir: str) -> str:
        """Export a single skill to filesystem."""
        # Create skill directory
        skill_dir = os.path.join(output_dir, skill.template_key)
        os.makedirs(skill_dir, exist_ok=True)
        
        # Write SKILL.md
        skill_path = os.path.join(skill_dir, "SKILL.md")
        content = skill.to_agentskills_format()
        
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Create scripts/ directory if agent_class is set
        if skill.agent_class:
            scripts_dir = os.path.join(skill_dir, "scripts")
            os.makedirs(scripts_dir, exist_ok=True)
            
            # Create a placeholder run.py
            run_script = os.path.join(scripts_dir, "run.py")
            if not os.path.exists(run_script):
                with open(run_script, "w", encoding="utf-8") as f:
                    f.write(f'''#!/usr/bin/env python
"""
Auto-generated script for {skill.template_key}
Agent: {skill.agent_class}
"""
import sys
sys.path.insert(0, "/path/to/bfagent")

from {skill.agent_class.rsplit(".", 1)[0]} import {skill.agent_class.rsplit(".", 1)[1]}

if __name__ == "__main__":
    agent = {skill.agent_class.rsplit(".", 1)[1]}()
    # Execute with provided context
    import json
    context = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {{}}
    result = agent.execute(context)
    print(json.dumps(result, indent=2))
''')
        
        # Create references/ if references is set
        if skill.references:
            refs_dir = os.path.join(skill_dir, "references")
            os.makedirs(refs_dir, exist_ok=True)
            
            for ref_name, ref_content in skill.references.items():
                ref_path = os.path.join(refs_dir, f"{ref_name}.md")
                with open(ref_path, "w", encoding="utf-8") as f:
                    f.write(f"# {ref_name}\n\n{ref_content}")
        
        return skill_path
