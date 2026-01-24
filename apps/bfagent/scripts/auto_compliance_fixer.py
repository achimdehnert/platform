#!/usr/bin/env python
"""
Auto Compliance Fixer - BF Agent v2.0.0
Automatically fixes compliance issues while protecting custom code

SAFE GUARDS:
- Detects CUSTOM_CODE_START/END markers
- Creates backups before modifications
- Dry-run mode for testing
- Rollback capability

Usage:
    python scripts/auto_compliance_fixer.py --dry-run
    python scripts/auto_compliance_fixer.py --fix
    python scripts/auto_compliance_fixer.py --model BookProjects --fix
"""

import argparse

# ============================================================================
# UTF-8 ENCODING FIX FOR WINDOWS
# ============================================================================
import io
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

# Force UTF-8 encoding for Windows console output
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.apps import apps

# ============================================================================
# PROTECTED CODE DETECTION
# ============================================================================

PROTECTED_MARKERS = [
    "# CUSTOM_CODE_START",
    "# BUSINESS_LOGIC_START",
    "# DO_NOT_MODIFY",
    "# USER_CODE_START",
]


def is_protected_section(content: str, start_pos: int, end_pos: int) -> bool:
    """Check if code section is protected"""
    section = content[start_pos:end_pos]
    return any(marker in section for marker in PROTECTED_MARKERS)


def extract_custom_code(content: str) -> Dict[str, str]:
    """Extract all custom code sections"""
    custom_sections = {}
    lines = content.split("\n")

    in_custom = False
    current_section = None
    current_lines = []

    for line in lines:
        if "# CUSTOM_CODE_START:" in line:
            in_custom = True
            # Extract section name
            current_section = line.split("# CUSTOM_CODE_START:")[1].strip()
            current_lines = [line]
        elif "# CUSTOM_CODE_END" in line:
            current_lines.append(line)
            if current_section:
                custom_sections[current_section] = "\n".join(current_lines)
            in_custom = False
            current_section = None
            current_lines = []
        elif in_custom:
            current_lines.append(line)

    return custom_sections


# ============================================================================
# BACKUP SYSTEM
# ============================================================================


def create_backup(file_path: Path) -> Path:
    """Create timestamped backup of file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BASE_DIR / "backups" / "auto_fix"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_dir / f"{file_path.name}.{timestamp}.bak"
    shutil.copy2(file_path, backup_path)

    print(f"  📦 Backup created: {backup_path.relative_to(BASE_DIR)}")
    return backup_path


# ============================================================================
# PHASE 1: MODEL HEALTH CHECK
# ============================================================================


class ModelHealthChecker:
    """Checks and fixes model health issues"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.issues_found = []
        self.fixes_applied = []

    def check_model(self, model):
        """Check single model for compliance"""
        model_name = model.__name__
        issues = []

        # Check 1: CRUDConfig exists
        if not hasattr(model, "CRUDConfig"):
            issues.append(f"Missing CRUDConfig")
        else:
            # Check CRUDConfig completeness
            crud_config = model.CRUDConfig
            has_list_display = hasattr(crud_config, "list_display") or hasattr(
                crud_config, "list_display_fields"
            )
            has_form_fields = hasattr(crud_config, "form_fields") or hasattr(
                crud_config, "form_layout"
            )

            if not has_list_display:
                issues.append("CRUDConfig missing list_display")
            if not has_form_fields:
                issues.append("CRUDConfig missing form_fields/form_layout")

        # Check 2: __str__ method
        if model.__str__ == object.__str__:
            issues.append("Missing __str__ method")

        # Check 3: Meta class
        if not hasattr(model, "_meta"):
            issues.append("Missing Meta class")

        if issues:
            self.issues_found.append({"model": model_name, "issues": issues})

        return len(issues) == 0


# ============================================================================
# PHASE 2: DB CONSISTENCY CHECK
# ============================================================================


class DBConsistencyChecker:
    """Checks database and model consistency"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.issues = []

    def check_migrations(self) -> bool:
        """Check if migrations are up to date"""
        from io import StringIO

        from django.core.management import call_command

        print("  🔍 Checking migrations...")

        # Check for unapplied migrations
        out = StringIO()
        try:
            call_command("showmigrations", "--plan", stdout=out)
            output = out.getvalue()

            # Check for [ ] (unapplied)
            unapplied = [line for line in output.split("\n") if "[ ]" in line]
            if unapplied:
                print(f"  ⚠️  Found {len(unapplied)} unapplied migrations")
                self.issues.append(f"Unapplied migrations: {len(unapplied)}")
                return False
        except Exception as e:
            print(f"  ❌ Migration check failed: {e}")
            return False

        # Check for missing migrations
        out = StringIO()
        try:
            call_command("makemigrations", "--dry-run", stdout=out)
            output = out.getvalue()

            if "No changes detected" not in output:
                print(f"  ⚠️  Model changes detected - migrations needed")
                self.issues.append("Model changes require new migrations")

                if not self.dry_run:
                    print(f"  🔧 Creating migrations...")
                    call_command("makemigrations")
                    print(f"  ✅ Migrations created")
                else:
                    print(f"  🔍 [DRY-RUN] Would create migrations")
                return False
        except Exception as e:
            print(f"  ❌ Makemigrations check failed: {e}")
            return False

        print("  ✅ Migrations up to date")
        return True


# ============================================================================
# CONFIGURATION LOADER
# ============================================================================


class CRUDConfigLoader:
    """Load and validate CRUD configuration from YAML"""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = BASE_DIR / "config" / "crud_config.yaml"

        self.config_path = config_path
        self.config = {}
        self.models_config = {}
        self.generation_options = {}
        self.exclusions = {}

        if config_path.exists():
            self._load_config()
        else:
            print(f"⚠️  Config file not found: {config_path}")
            print("   Using default configuration...")

    def _load_config(self):
        """Load YAML configuration"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)

            self.models_config = self.config.get("models", {})
            self.generation_options = self.config.get("generation_options", {})
            self.exclusions = self.config.get("exclusions", {})

            print(f"✅ Loaded configuration: {len(self.models_config)} models defined")
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            raise

    def get_model_config(self, model_name: str) -> Dict:
        """Get configuration for specific model"""
        return self.models_config.get(model_name, {})

    def should_process_model(self, model_name: str) -> bool:
        """Check if model should be processed"""
        # Check exclusions
        if model_name in self.exclusions.get("exclude_models", []):
            return False

        # Check if model is in config
        if model_name not in self.models_config:
            print(f"   ⚠️  {model_name} not in config - skipping")
            return False

        # Check level
        config = self.models_config[model_name]
        level = config.get("level", "SKIP")

        return level != "SKIP"

    def get_crud_level(self, model_name: str) -> str:
        """Get CRUD level for model"""
        config = self.get_model_config(model_name)
        return config.get("level", "SKIP")

    def needs_feature(self, model_name: str, feature: str) -> bool:
        """Check if model needs specific feature (forms, views, etc)"""
        config = self.get_model_config(model_name)
        features = config.get("features", [])
        return feature in features

    def has_custom_code(self, model_name: str) -> bool:
        """Check if model has custom code to protect"""
        config = self.get_model_config(model_name)
        return config.get("custom_code", False)

    def get_priority(self, model_name: str) -> str:
        """Get processing priority"""
        config = self.get_model_config(model_name)
        return config.get("priority", "medium")

    def get_models_by_priority(self) -> List[str]:
        """Get model names sorted by priority"""
        priority_order = {"high": 0, "medium": 1, "low": 2, "none": 3}

        models = []
        for model_name, config in self.models_config.items():
            if config.get("level", "SKIP") != "SKIP":
                priority = config.get("priority", "medium")
                models.append((model_name, priority_order.get(priority, 2)))

        # Sort by priority
        models.sort(key=lambda x: x[1])
        return [m[0] for m in models]

    def print_summary(self):
        """Print configuration summary"""
        print("\n" + "=" * 80)
        print("CRUD CONFIGURATION SUMMARY")
        print("=" * 80)

        levels = {}
        for model_name, config in self.models_config.items():
            level = config.get("level", "SKIP")
            if level not in levels:
                levels[level] = []
            levels[level].append(model_name)

        for level, models in sorted(levels.items()):
            print(f"\n{level}: {len(models)} models")
            for model in sorted(models):
                priority = self.models_config[model].get("priority", "?")
                print(f"   - {model} (priority: {priority})")


# ============================================================================
# PHASE 0: CUSTOM CODE PROTECTION
# ============================================================================


class CustomCodeProtector:
    """Protect and restore custom code during regeneration"""

    # Protected code markers
    MARKERS = [
        ("# CUSTOM_CODE_START:", "# CUSTOM_CODE_END:"),
        ("# BUSINESS_LOGIC_START:", "# BUSINESS_LOGIC_END:"),
        ("# USER_CODE_START:", "# USER_CODE_END:"),
        ("# DO_NOT_MODIFY", None),  # Single-line marker
    ]

    def __init__(self):
        self.protected_blocks = {}  # {file_path: {section_name: code}}
        self.issues = []

    def scan_and_extract(self, file_paths: list):
        """Scan files and extract all custom code blocks"""
        print("  🔍 Scanning for custom code blocks...")

        for file_path in file_paths:
            if not file_path.exists():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                blocks = self._extract_custom_blocks(content, file_path)

                if blocks:
                    self.protected_blocks[str(file_path)] = blocks
                    print(f"    ✅ Found {len(blocks)} custom blocks in {file_path.name}")
                    for section_name in blocks.keys():
                        print(f"       - {section_name}")
            except Exception as e:
                self.issues.append(f"Error scanning {file_path.name}: {e}")
                print(f"    ⚠️  Error scanning {file_path.name}: {e}")

    def _extract_custom_blocks(self, content: str, file_path) -> dict:
        """Extract custom code blocks from content"""
        import re

        blocks = {}

        for start_marker, end_marker in self.MARKERS:
            if end_marker:
                # Multi-line blocks
                pattern = f"{re.escape(start_marker)}(\\w+)\\n(.*?)\\n{re.escape(end_marker)}"
                matches = re.findall(pattern, content, re.DOTALL)

                for section_name, code_block in matches:
                    blocks[f"{start_marker}{section_name}"] = {
                        "code": code_block,
                        "start_marker": start_marker,
                        "end_marker": end_marker,
                        "section_name": section_name,
                    }
            else:
                # Single-line markers
                pattern = f"{re.escape(start_marker)}.*?$"
                matches = re.findall(pattern, content, re.MULTILINE)
                for i, match in enumerate(matches):
                    blocks[f"{start_marker}_{i}"] = {
                        "code": match,
                        "start_marker": start_marker,
                        "end_marker": None,
                        "section_name": f"line_{i}",
                    }

        return blocks

    def restore_custom_code(self, file_path, new_content: str) -> str:
        """Restore custom code blocks into newly generated content"""
        if str(file_path) not in self.protected_blocks:
            return new_content

        blocks = self.protected_blocks[str(file_path)]
        restored_content = new_content

        for block_key, block_data in blocks.items():
            start_marker = block_data["start_marker"]
            end_marker = block_data["end_marker"]
            section_name = block_data["section_name"]
            custom_code = block_data["code"]

            if end_marker:
                # Multi-line block restoration
                placeholder = f"{start_marker}{section_name}\n    # Add your custom {section_name} here\n    {end_marker}"
                replacement = f"{start_marker}{section_name}\n{custom_code}\n    {end_marker}"

                if placeholder in restored_content:
                    restored_content = restored_content.replace(placeholder, replacement)
                    print(f"    ✅ Restored custom block: {section_name}")
                else:
                    # Try to find marker and insert
                    marker_line = f"{start_marker}{section_name}"
                    if marker_line in restored_content:
                        print(f"    ⚠️  Found marker but couldn't restore: {section_name}")

        return restored_content

    def backup_custom_code(self, backup_dir):
        """Backup all extracted custom code to separate files"""
        backup_path = backup_dir / "custom_code_backup.json"

        import json

        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(self.protected_blocks, f, indent=2)

        print(f"  📦 Custom code backed up to: {backup_path}")
        return backup_path


# ============================================================================
# PHASE 3: COMPONENT GENERATOR
# ============================================================================


class ImportConsistencyChecker:
    """Check and fix import consistency issues"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.issues = []
        self.fixes_applied = []

    def check_form_imports(self):
        """Check all Python files for correct Form imports"""
        print("  🔍 Checking Form import consistency...")

        views_dir = BASE_DIR / "apps" / "bfagent" / "views"
        if not views_dir.exists():
            return

        # Get all actual form names from forms.py
        forms_path = BASE_DIR / "apps" / "bfagent" / "forms.py"
        actual_forms = self._extract_form_names(forms_path)

        # Check all view files
        for view_file in views_dir.glob("*.py"):
            if view_file.name == "__init__.py":
                continue

            content = view_file.read_text(encoding="utf-8")
            wrong_imports = self._find_wrong_imports(content, actual_forms)

            if wrong_imports:
                print(f"    ⚠️  Found {len(wrong_imports)} wrong imports in {view_file.name}")
                for wrong, correct in wrong_imports:
                    print(f"       {wrong} → {correct}")
                    self.issues.append({"file": view_file, "wrong": wrong, "correct": correct})

                if not self.dry_run:
                    self._fix_imports(view_file, wrong_imports)

    def _extract_form_names(self, forms_path):
        """Extract all Form class names from forms.py"""
        import re

        content = forms_path.read_text(encoding="utf-8")
        pattern = r"class (\w+Form)\(forms\.ModelForm\)"
        return set(re.findall(pattern, content))

    def _find_wrong_imports(self, content, actual_forms):
        """Find imports that don't match actual form names"""
        import re

        wrong_imports = []

        # Find all form imports
        import_pattern = r"from\s+\.\.forms\s+import\s+([^\n]+)"
        matches = re.findall(import_pattern, content)

        for match in matches:
            imported_forms = [f.strip() for f in match.split(",")]
            for imported in imported_forms:
                # Remove 'as' alias
                imported = imported.split(" as ")[0].strip()

                if imported.endswith("Form") and imported not in actual_forms:
                    # Try to find correct name
                    correct = self._guess_correct_form_name(imported, actual_forms)
                    if correct:
                        wrong_imports.append((imported, correct))

        return wrong_imports

    def _guess_correct_form_name(self, wrong_name, actual_forms):
        """Guess the correct form name based on similarity"""
        # Common patterns:
        # BookProjectForm → BookProjectsForm (missing 's')
        # CharacterForm → CharactersForm (missing 's')

        # Try adding 's' before 'Form'
        candidate = wrong_name.replace("Form", "sForm")
        if candidate in actual_forms:
            return candidate

        # Try other variations
        base = wrong_name.replace("Form", "")
        for actual in actual_forms:
            if actual.startswith(base) or base in actual:
                return actual

        return None

    def _fix_imports(self, view_file, wrong_imports):
        """Fix wrong imports in file"""
        content = view_file.read_text(encoding="utf-8")

        for wrong, correct in wrong_imports:
            # Replace in import statements
            content = content.replace(f"import {wrong}", f"import {correct}")
            content = content.replace(f"{wrong},", f"{correct},")
            content = content.replace(f", {wrong}", f", {correct}")

            # Replace in code (form_class = ...)
            content = content.replace(f"form_class = {wrong}", f"form_class = {correct}")

        # Create backup
        create_backup(view_file)

        # Write fixed content
        with open(view_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"    ✅ Fixed imports in {view_file.name}")
        self.fixes_applied.append(str(view_file))


class ModelNamingStrategy:
    """
    ============================================================================
    CENTRAL NAMING STRATEGY - SINGLE SOURCE OF TRUTH
    ============================================================================

    This class manages ALL naming conventions for CRUD components.
    NEVER hardcode names elsewhere - always use this class!

    Consistency across:
    - URLs (path in browser AND name in templates)
    - Templates (filenames and internal {% url %} references)
    - Views (class names)
    - Forms (class names)
    - Display names (in UI)
    """

    # ============================================================================
    # CENTRAL MAPPING - SINGLE SOURCE OF TRUTH
    # ============================================================================
    MAPPINGS = {
        "BookChapters": {
            "url_path": "chapters",  # Browser: /chapters/
            "url_name": "chapter",  # Template: {% url 'chapter-list' %}
            "display_name": "Chapter",  # UI: "Create Chapter"
        },
        "Agents": {
            "url_path": "agents",
            "url_name": "agent",
            "display_name": "Agent",
        },
        "Characters": {
            "url_path": "characters",
            "url_name": "character",
            "display_name": "Character",
        },
        "Llms": {
            "url_path": "llms",
            "url_name": "llm",
            "display_name": "LLM",
        },
        "StoryArc": {
            "url_path": "storyarc",
            "url_name": "storyarc",
            "display_name": "Story Arc",
        },
        "PlotPoint": {
            "url_path": "plotpoint",
            "url_name": "plotpoint",
            "display_name": "Plot Point",
        },
        "AgentExecutions": {
            "url_path": "executions",
            "url_name": "execution",
            "display_name": "Execution",
        },
        "AgentArtifacts": {
            "url_path": "artifacts",
            "url_name": "artifact",
            "display_name": "Artifact",
        },
        "BookTypes": {
            "url_path": "booktypes",
            "url_name": "booktype",
            "display_name": "Book Type",
        },
        "QueryPerformanceLog": {
            "url_path": "performance-log",
            "url_name": "performance-log",
            "display_name": "Performance Log",
        },
        "Worlds": {
            "url_path": "worlds",
            "url_name": "world",
            "display_name": "World",
        },
        "Genre": {
            "url_path": "genres",
            "url_name": "genre",
            "display_name": "Genre",
        },
        "TargetAudience": {
            "url_path": "audiences",
            "url_name": "targetaudience",
            "display_name": "Target Audience",
        },
        "WritingStatus": {
            "url_path": "statuses",
            "url_name": "writingstatus",
            "display_name": "Writing Status",
        },
        "PromptTemplate": {
            "url_path": "prompt-templates",
            "url_name": "prompttemplate",
            "display_name": "Prompt Template",
        },
    }

    @classmethod
    def get(cls, model_name: str) -> dict:
        """
        Get all naming conventions for a model.

        Returns dict with:
        - url_path: Path in browser (e.g., /chapters/)
        - url_name: Name for templates (e.g., chapter-list)
        - display_name: Human-readable name (e.g., "Chapter")
        """
        # Default: use lowercase model name
        default = {
            "url_path": model_name.lower().replace("_", "-"),
            "url_name": model_name.lower().replace("_", "-"),
            "display_name": model_name,
        }
        return cls.MAPPINGS.get(model_name, default)


class ComponentGenerator:
    """Generates missing components (Forms, URLs, Views, Templates)"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.generated = []

    def generate_urls(self, model) -> bool:
        """Generate URL patterns for model if missing"""
        model_name = model.__name__
        urls_path = BASE_DIR / "apps" / "bfagent" / "urls.py"

        if not urls_path.exists():
            print(f"  ⚠️  urls.py not found")
            return False

        content = urls_path.read_text(encoding="utf-8")

        # Models with custom URLs - DO NOT generate
        skip_url_generation = {"BookProjects"}  # Only BookProjects has fully custom URLs

        if model_name in skip_url_generation:
            print(f"  ℹ️  Skipping URL generation for {model_name} (custom URLs exist)")
            return True

        # Get naming strategy from CENTRAL source
        names = ModelNamingStrategy.get(model_name)
        url_path = names["url_path"]
        url_name = names["url_name"]

        # Check if URLs already exist
        if f'name="{url_name}-list"' in content:
            print(f"  ✅ URLs for {model_name} already exist")
            return True

        # Generate URL patterns (path vs name: path for browser, name for templates)
        url_patterns = f"""    # {model_name} URLs
    path("{url_path}/", views.{model_name}ListView.as_view(), name="{url_name}-list"),
    path("{url_path}/create/", views.{model_name}CreateView.as_view(), name="{url_name}-create"),
    path("{url_path}/<int:pk>/", views.{model_name}DetailView.as_view(), name="{url_name}-detail"),
    path("{url_path}/<int:pk>/edit/", views.{model_name}UpdateView.as_view(), name="{url_name}-update"),
    path("{url_path}/<int:pk>/delete/", views.{model_name}DeleteView.as_view(), name="{url_name}-delete"),
"""

        # PRE-FLIGHT VALIDATION: Find insertion point FIRST
        lines = content.split("\n")
        insert_pos = -1

        # Find urlpatterns closing bracket
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            # Look for standalone ] or ] with comment
            if line == "]" or line.startswith("]"):
                # Verify urlpatterns exists in file (check ALL lines before closing bracket)
                context_before = "\n".join(lines[0:i])  # Check entire file before ]
                
                # Must find urlpatterns declaration
                if "urlpatterns" in context_before or "urlpatterns =" in context_before:
                    # Additional check: Should be at reasonable position (not in first 10 lines)
                    if i > 10:
                        insert_pos = i
                        break

        # VALIDATE BEFORE ANY ACTION
        if insert_pos < 0:
            print(f"  ❌ Could not find insertion point in urls.py")
            print(f"     Expected: urlpatterns = [...] structure")
            print(f"     Debug: File has {len(lines)} lines")
            # Show last few lines for debugging
            print(f"     Last 3 lines:")
            for i in range(max(0, len(lines) - 3), len(lines)):
                print(f"       {i}: {repr(lines[i][:50])}")
            return False

        if self.dry_run:
            print(f"  🔍 [DRY-RUN] Would add URL patterns for {model_name}")
            print(f"      Preview: {url_patterns[:100]}...")
            print(f"      Insertion point found at line {insert_pos}")
        else:
            # NOW create backup (operation will succeed)
            create_backup(urls_path)

            # Insert BEFORE the closing bracket
            lines.insert(insert_pos, url_patterns)
            new_content = "\n".join(lines)

            with open(urls_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"  ✅ Added URL patterns for {model_name}")
            self.generated.append(f"{model_name} URLs")

        return True

    def generate_views(self, model) -> bool:
        """Generate CRUD views for model if missing or outdated"""
        model_name = model.__name__

        # Check for dedicated views file first
        views_dir = BASE_DIR / "apps" / "bfagent" / "views"
        model_views_file = views_dir / f"{model_name.lower()}_views.py"

        # If no dedicated file, use main_views.py
        if not model_views_file.exists():
            views_path = views_dir / "main_views.py"
            if not views_path.exists():
                views_path = BASE_DIR / "apps" / "bfagent" / "views.py"
        else:
            views_path = model_views_file

        if not views_path.exists():
            print(f"  ⚠️  views.py not found")
            return False

        content = views_path.read_text(encoding="utf-8")

        # Check for auto-generated marker
        auto_gen_start = f"# AUTO_GENERATED_START: {model_name}_VIEWS"
        auto_gen_end = f"# AUTO_GENERATED_END: {model_name}_VIEWS"

        has_auto_gen_section = auto_gen_start in content and auto_gen_end in content

        # Generate views code
        views_code = self._generate_views_code(model)

        if self.dry_run:
            action = "Replace" if has_auto_gen_section else "Create"
            print(f"  🔍 [DRY-RUN] Would {action.lower()} views for {model_name}")
            print(f"      Preview:\n{views_code[:200]}...")
        else:
            # Create backup
            create_backup(views_path)

            if has_auto_gen_section:
                # REPLACE existing auto-generated section
                start_idx = content.index(auto_gen_start)
                end_idx = content.index(auto_gen_end) + len(auto_gen_end)

                new_content = content[:start_idx] + views_code + content[end_idx:]

                views_path.write_text(new_content, encoding="utf-8")
                print(f"  ✅ Replaced views for {model_name}")
                self.generated.append(f"{model_name} Views (replaced)")
            else:
                # APPEND new section
                with open(views_path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n{views_code}")

                print(f"  ✅ Created views for {model_name}")
                self.generated.append(f"{model_name} Views (created)")

        return True

    def _generate_views_code(self, model) -> str:
        """Generate CRUD views code from model"""
        model_name = model.__name__
        model_lower = model_name.lower()
        app_label = model._meta.app_label

        # Get naming strategy from CENTRAL source
        names = ModelNamingStrategy.get(model_name)
        url_name = names["url_name"]  # For reverse() URLs

        # Get list fields from CRUDConfig
        list_fields = []
        if hasattr(model, "CRUDConfig"):
            crud = model.CRUDConfig
            if hasattr(crud, "list_display"):
                list_fields = crud.list_display
            elif hasattr(crud, "list_display_fields"):
                list_fields = crud.list_display_fields

        if not list_fields:
            list_fields = [
                f.name
                for f in model._meta.get_fields()[:5]
                if not f.auto_created and hasattr(f, "verbose_name")
            ]

        # Use model_lower without _list suffix for context
        # Django paginated ListViews automatically provide 'page_obj'
        # But also set context_object_name for consistency
        context_name = model_lower

        views_template = f'''# AUTO_GENERATED_START: {model_name}_VIEWS
# ============================================================================
# {model_name} CRUD Views (Auto-generated by auto_compliance_fixer.py)
# DO NOT MANUALLY EDIT THIS SECTION - Changes will be overwritten
# To customize: Add code in CUSTOM_CODE_START/END blocks below
# ============================================================================

from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse
from django.contrib import messages

from apps.{app_label}.models import {model_name}
from apps.{app_label}.forms import {model_name}Form


class {model_name}ListView(ListView):
    """List view for {model_name}"""
    model = {model_name}
    template_name = "{app_label}/{model_lower}_list.html"
    context_object_name = "{context_name}"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        # Add select_related/prefetch_related if needed
        return queryset


class {model_name}DetailView(DetailView):
    """Detail view for {model_name}"""
    model = {model_name}
    template_name = "{app_label}/{model_lower}_detail.html"
    context_object_name = "{model_lower}"


class {model_name}CreateView(CreateView):
    """Create view for {model_name}"""
    model = {model_name}
    form_class = {model_name}Form
    template_name = "{app_label}/{model_lower}_form.html"

    def get_success_url(self):
        return reverse("{app_label}:{url_name}-detail", kwargs={{"pk": self.object.pk}})

    def form_valid(self, form):
        messages.success(self.request, f"{model_name} created successfully!")
        return super().form_valid(form)


class {model_name}UpdateView(UpdateView):
    """Update view for {model_name}"""
    model = {model_name}
    form_class = {model_name}Form
    template_name = "{app_label}/{model_lower}_form.html"
    context_object_name = "{model_lower}"

    def get_success_url(self):
        return reverse("{app_label}:{url_name}-detail", kwargs={{"pk": self.object.pk}})

    def form_valid(self, form):
        messages.success(self.request, f"{model_name} updated successfully!")
        return super().form_valid(form)


class {model_name}DeleteView(DeleteView):
    """Delete view for {model_name}"""
    model = {model_name}
    template_name = "{app_label}/{model_lower}_confirm_delete.html"
    context_object_name = "{model_lower}"

    def get_success_url(self):
        return reverse("{app_label}:{url_name}-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, f"{model_name} deleted successfully!")
        return super().delete(request, *args, **kwargs)

# AUTO_GENERATED_END: {model_name}_VIEWS
'''

        return views_template

    def generate_templates(self, model) -> bool:
        """Generate CRUD templates for model if missing"""
        model_name = model.__name__
        model_lower = model_name.lower()
        app_label = model._meta.app_label

        # Models with CUSTOM templates - NEVER overwrite
        custom_template_models = {"BookProjects"}

        if model_name in custom_template_models:
            print(f"  ℹ️  Skipping template generation for {model_name} (custom templates)")
            return True

        # FIX: Templates should be in apps/{app_label}/templates/{app_label}/
        templates_dir = BASE_DIR / "apps" / app_label / "templates" / app_label
        templates_dir.mkdir(parents=True, exist_ok=True)

        # SOLUTION: Enforce UTF-8 encoding for ALL generated files

        # Templates to generate
        templates = {
            "list": f"{model_lower}_list.html",
            "detail": f"{model_lower}_detail.html",
            "form": f"{model_lower}_form.html",
            "delete": f"{model_lower}_confirm_delete.html",
        }

        created_count = 0
        replaced_count = 0

        for template_type, template_name in templates.items():
            template_path = templates_dir / template_name

            # Check for auto-generated marker
            auto_gen_marker = f"<!-- AUTO_GENERATED: {model_name}_{template_type.upper()} -->"
            has_auto_gen_marker = False

            if template_path.exists():
                content = template_path.read_text(encoding="utf-8")
                has_auto_gen_marker = auto_gen_marker in content

            template_content = self._generate_template_content(model, template_type)

            if self.dry_run:
                action = (
                    "Replace"
                    if has_auto_gen_marker
                    else "Create" if not template_path.exists() else "Skip"
                )
                print(f"      🔍 [DRY-RUN] Would {action.lower()} {template_name}")
            else:
                if has_auto_gen_marker or not template_path.exists():
                    # Create backup if replacing
                    if template_path.exists():
                        create_backup(template_path)
                        replaced_count += 1
                    else:
                        created_count += 1

                    with open(template_path, "w", encoding="utf-8") as f:
                        f.write(template_content)

        if created_count > 0 or replaced_count > 0:
            if not self.dry_run:
                msg_parts = []
                if created_count > 0:
                    msg_parts.append(f"created {created_count}")
                if replaced_count > 0:
                    msg_parts.append(f"replaced {replaced_count}")
                print(f"  ✅ Templates for {model_name}: {', '.join(msg_parts)}")
                self.generated.append(
                    f"{model_name} Templates ({created_count} new, {replaced_count} replaced)"
                )
        else:
            print(f"  ✅ All templates for {model_name} exist")

        return True

    def _generate_template_content(self, model, template_type: str) -> str:
        """Generate template content based on type"""
        model_name = model.__name__
        model_lower = model_name.lower()  # For template filenames
        app_label = model._meta.app_label

        # Get naming strategy from CENTRAL source
        names = ModelNamingStrategy.get(model_name)
        url_name = names["url_name"]  # For {% url 'url_name-list' %}
        display_name = names["display_name"]  # For UI text

        # Get display fields from CRUDConfig
        list_fields = []
        if hasattr(model, "CRUDConfig"):
            crud = model.CRUDConfig
            if hasattr(crud, "list_display"):
                list_fields = crud.list_display[:5]
            elif hasattr(crud, "list_display_fields"):
                list_fields = crud.list_display_fields[:5]

        if not list_fields:
            list_fields = [
                f.name for f in model._meta.get_fields()[:5] if not f.auto_created and f.editable
            ]

        if template_type == "list":
            # Generate table headers
            headers = "\n".join(
                [f'                    <th>{f.replace("_", " ").title()}</th>' for f in list_fields]
            )
            # Generate table cells - use 'item' as loop variable
            cells = "\n".join(
                [f"                    <td>{{{{ item.{f} }}}}</td>" for f in list_fields]
            )

            return f"""<!-- AUTO_GENERATED: {model_name}_LIST -->
{{% extends "base.html" %}}
{{% load static %}}

{{% block title %}}{display_name} List{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1><i class="bi bi-list"></i> {display_name} List</h1>
        <a href="{{% url '{app_label}:{url_name}-create' %}}" class="btn btn-primary">
            <i class="bi bi-plus-circle"></i> Create {display_name}
        </a>
    </div>

    <div class="card shadow">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
{headers}
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {{% for item in page_obj %}}
                        <tr>
{cells}
                            <td>
                                <div class="btn-group btn-group-sm">
                                    <a href="{{% url '{app_label}:{url_name}-detail' item.pk %}}"
                                       class="btn btn-outline-primary" title="View">
                                        <i class="bi bi-eye"></i>
                                    </a>
                                    <a href="{{% url '{app_label}:{url_name}-update' item.pk %}}"
                                       class="btn btn-outline-secondary" title="Edit">
                                        <i class="bi bi-pencil"></i>
                                    </a>
                                    <a href="{{% url '{app_label}:{url_name}-delete' item.pk %}}"
                                       class="btn btn-outline-danger" title="Delete">
                                        <i class="bi bi-trash"></i>
                                    </a>
                                </div>
                            </td>
                        </tr>
                        {{% empty %}}
                        <tr>
                            <td colspan="{len(list_fields) + 1}" class="text-center text-muted">
                                No {display_name.lower()}s found.
                                <a href="{{% url '{app_label}:{url_name}-create' %}}">Create one now</a>
                            </td>
                        </tr>
                        {{% endfor %}}
                    </tbody>
                </table>
            </div>

            {{% if is_paginated %}}
            <nav aria-label="Page navigation">
                <ul class="pagination justify-content-center">
                    {{% if page_obj.has_previous %}}
                    <li class="page-item">
                        <a class="page-link" href="?page=1">First</a>
                    </li>
                    <li class="page-item">
                        <a class="page-link" href="?page={{{{ page_obj.previous_page_number }}}}">Previous</a>
                    </li>
                    {{% endif %}}

                    <li class="page-item active">
                        <span class="page-link">Page {{{{ page_obj.number }}}} of {{{{ page_obj.paginator.num_pages }}}}</span>
                    </li>

                    {{% if page_obj.has_next %}}
                    <li class="page-item">
                        <a class="page-link" href="?page={{{{ page_obj.next_page_number }}}}">Next</a>
                    </li>
                    <li class="page-item">
                        <a class="page-link" href="?page={{{{ page_obj.paginator.num_pages }}}}">Last</a>
                    </li>
                    {{% endif %}}
                </ul>
            </nav>
            {{% endif %}}
        </div>
    </div>
</div>
{{% endblock %}}
"""

        elif template_type == "detail":
            # Generate detail fields
            detail_fields = "\n".join(
                [
                    f"""            <div class="row mb-3">
                <div class="col-md-3"><strong>{f.replace("_", " ").title()}:</strong></div>
                <div class="col-md-9">{{{{ object.{f} }}}}</div>
            </div>"""
                    for f in list_fields
                ]
            )

            return f"""<!-- AUTO_GENERATED: {model_name}_DETAIL -->
{{% extends "base.html" %}}
{{% load static %}}

{{% block title %}}{display_name} Detail{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1><i class="bi bi-eye"></i> {model_name} Detail</h1>
        <div>
            <a href="{{% url '{app_label}:{url_name}-list' %}}" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Back to List
            </a>
            <a href="{{% url '{app_label}:{url_name}-update' object.pk %}}" class="btn btn-primary">
                <i class="bi bi-pencil"></i> Edit
            </a>
        </div>
    </div>

    <div class="card shadow">
        <div class="card-body">
{detail_fields}
        </div>
        <div class="card-footer">
            <a href="{{% url '{app_label}:{url_name}-delete' object.pk %}}" class="btn btn-danger">
                <i class="bi bi-trash"></i> Delete
            </a>
        </div>
    </div>
</div>
{{% endblock %}}
"""

        elif template_type == "form":
            return f"""<!-- AUTO_GENERATED: {model_name}_FORM -->
{{% extends "base.html" %}}
{{% load static %}}

{{% block title %}}{{% if object %}}Edit{{% else %}}Create{{% endif %}} {display_name}{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1>
            <i class="bi bi-{{% if object %}}pencil{{% else %}}plus-circle{{% endif %}}"></i>
            {{% if object %}}Edit{{% else %}}Create{{% endif %}} {model_name}
        </h1>
        <a href="{{% url '{app_label}:{url_name}-list' %}}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> Back to List
        </a>
    </div>

    <div class="card shadow">
        <div class="card-body">
            <form method="post" class="needs-validation" novalidate>
                {{% csrf_token %}}

                {{% if form.non_field_errors %}}
                <div class="alert alert-danger">
                    {{{{ form.non_field_errors }}}}
                </div>
                {{% endif %}}

                {{% for field in form %}}
                <div class="mb-3">
                    <label for="{{{{ field.id_for_label }}}}" class="form-label">
                        {{{{ field.label }}}}
                        {{% if field.field.required %}}<span class="text-danger">*</span>{{% endif %}}
                    </label>
                    {{{{ field }}}}
                    {{% if field.help_text %}}
                    <small class="form-text text-muted">{{{{ field.help_text }}}}</small>
                    {{% endif %}}
                    {{% if field.errors %}}
                    <div class="invalid-feedback d-block">
                        {{{{ field.errors }}}}
                    </div>
                    {{% endif %}}
                </div>
                {{% endfor %}}

                <div class="d-flex justify-content-between">
                    <a href="{{% url '{app_label}:{url_name}-list' %}}" class="btn btn-outline-secondary">
                        Cancel
                    </a>
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-{{% if object %}}save{{% else %}}check-circle{{% endif %}}"></i>
                        {{% if object %}}Save{{% else %}}Create{{% endif %}}
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{{% endblock %}}
"""

        else:  # delete confirmation
            return f"""<!-- AUTO_GENERATED: {model_name}_DELETE -->
{{% extends "base.html" %}}
{{% load static %}}

{{% block title %}}Delete {display_name}{{% endblock %}}

{{% block content %}}
<div class="container-fluid">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h1><i class="bi bi-trash"></i> Delete {display_name}</h1>
        <a href="{{% url '{app_label}:{url_name}-detail' object.pk %}}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> Back
        </a>
    </div>

    <div class="card shadow border-danger">
        <div class="card-body">
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle-fill"></i>
                <strong>Warning!</strong> This action cannot be undone.
            </div>

            <p>Are you sure you want to delete <strong>{{{{ object }}}}</strong>?</p>

            <form method="post">
                {{% csrf_token %}}
                <div class="d-flex justify-content-between mt-4">
                    <a href="{{% url '{app_label}:{url_name}-detail' object.pk %}}" class="btn btn-secondary">
                        <i class="bi bi-x-circle"></i> Cancel
                    </a>
                    <button type="submit" class="btn btn-danger">
                        <i class="bi bi-trash"></i> Delete
                    </button>
                </div>
            </form>
        </div>
    </div>
</div>
{{% endblock %}}
"""

    def generate_form(self, model) -> bool:
        """Generate form for model if missing"""
        model_name = model.__name__
        forms_path = BASE_DIR / "apps" / "bfagent" / "forms.py"

        if not forms_path.exists():
            print(f"  ⚠️  forms.py not found")
            return False

        content = forms_path.read_text(encoding="utf-8")

        # PRE-GENERATION VALIDATION: Check for wrong form names
        expected_form_name = f"{model_name}Form"
        wrong_form_variations = self._find_wrong_form_variations(model_name, content)

        if wrong_form_variations:
            print(f"  ⚠️  WARNING: Found wrong form name variations:")
            for wrong_name in wrong_form_variations:
                print(f"     - {wrong_name} should be {expected_form_name}")
            print(f"     Run Import Consistency Checker to fix!")
            return False

        # Check if correct form already exists
        expected_form = f"class {expected_form_name}"
        if expected_form in content:
            print(f"  ✅ {expected_form_name} already exists")
            return True

        # Generate form code
        form_code = self._generate_form_code(model)

        if self.dry_run:
            print(f"  🔍 [DRY-RUN] Would create {model_name}Form")
            print(f"      Preview:\n{form_code[:200]}...")
        else:
            # Create backup
            create_backup(forms_path)

            # CRITICAL: Ensure model is imported BEFORE adding form
            if not self._ensure_model_imported(forms_path, model_name):
                print(f"  ⚠️  Failed to add import for {model_name}")
                return False

            # Append form to file
            with open(forms_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n{form_code}")

            print(f"  ✅ Created {model_name}Form")
            self.generated.append(f"{model_name}Form")

        return True

    def _find_wrong_form_variations(self, model_name: str, content: str) -> list:
        """Find wrong form name variations (e.g., BookProjectForm instead of BookProjectsForm)"""
        import re

        wrong_forms = []

        # Pattern: class SomethingForm(forms.ModelForm)
        pattern = r"class (\w+Form)\(forms\.ModelForm\)"
        found_forms = re.findall(pattern, content)

        expected_form = f"{model_name}Form"
        base_name = model_name.rstrip("s")  # Remove trailing 's' if exists

        for form in found_forms:
            # Check if this form is a variation of our model
            if form != expected_form:
                # Common wrong patterns:
                # BookProjectForm vs BookProjectsForm
                # CharacterForm vs CharactersForm
                if form == f"{base_name}Form" and expected_form == f"{base_name}sForm":
                    wrong_forms.append(form)
                elif form.replace("Form", "") in model_name:
                    wrong_forms.append(form)

        return wrong_forms

    def _ensure_model_imported(self, forms_path, model_name: str) -> bool:
        """
        Ensure model is imported in forms.py
        Adds to existing from .models import (...) block
        """
        import re  # Import re here for pattern matching

        content = forms_path.read_text(encoding="utf-8")

        # Check if model already imported
        if f"{model_name}" in content and "from .models import" in content:
            # Model might already be imported, verify
            import_match = re.search(r"from \.models import \(([\s\S]*?)\)", content)
            if import_match:
                imports = import_match.group(1)
                if model_name in imports:
                    return True  # Already imported

        # Find the import block
        import_pattern = r"(from \.models import \()([\s\S]*?)(\))"
        match = re.search(import_pattern, content)

        if not match:
            print(f"  ⚠️  Could not find 'from .models import (...)' block")
            return False

        # Extract existing imports
        before = match.group(1)
        imports_text = match.group(2)
        after = match.group(3)

        # Parse imports into list
        imports = [
            imp.strip().rstrip(",") for imp in imports_text.strip().split("\n") if imp.strip()
        ]

        # Add new model alphabetically
        imports.append(model_name)
        imports = sorted(set(imports))  # Remove duplicates and sort

        # Rebuild import statement
        imports_formatted = ",\n    ".join(imports)
        new_import_block = f"{before}\n    {imports_formatted},\n{after}"

        # Replace in content
        new_content = content.replace(match.group(0), new_import_block)

        # Write back
        forms_path.write_text(new_content, encoding="utf-8")
        print(f"  ✅ Added {model_name} to imports")
        return True

    def _generate_form_code(self, model) -> str:
        """Generate form code from model"""
        model_name = model.__name__

        # Get fields from CRUDConfig if available
        fields = []
        if hasattr(model, "CRUDConfig"):
            crud = model.CRUDConfig
            if hasattr(crud, "form_layout") and isinstance(crud.form_layout, dict):
                # Flatten form_layout
                for section_fields in crud.form_layout.values():
                    fields.extend(section_fields)
            elif hasattr(crud, "form_fields"):
                fields = crud.form_fields

        # If no fields from CRUDConfig, use model fields
        if not fields:
            fields = [f.name for f in model._meta.get_fields() if not f.auto_created and f.editable]

        fields_str = ", ".join([f"'{f}'" for f in fields[:10]])  # Limit to 10

        form_template = f'''class {model_name}Form(forms.ModelForm):
    """Form for {model_name} model"""

    class Meta:
        model = {model_name}
        fields = [{fields_str}]
        widgets = {{
            # Add custom widgets here
        }}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                current_classes = field.widget.attrs.get('class', '')
                if 'form-control' not in current_classes and 'form-check-input' not in current_classes:
                    field.widget.attrs['class'] = f"{{current_classes}} form-control".strip()

    # CUSTOM_CODE_START: validation
    # Add your custom validation methods here
    # CUSTOM_CODE_END:

    # CUSTOM_CODE_START: save_override
    # Override save method if needed
    # CUSTOM_CODE_END:'''

        return form_template


# ============================================================================
# MAIN AUTO-FIXER
# ============================================================================


class AutoComplianceFixer:
    """Main auto-fixer orchestrator"""

    def __init__(
        self,
        dry_run: bool = True,
        model_filter: Optional[str] = None,
        config_path: Optional[Path] = None,
    ):
        self.dry_run = dry_run
        self.model_filter = model_filter

        # Load configuration FIRST
        self.config = CRUDConfigLoader(config_path)

        # Initialize components
        self.custom_protector = CustomCodeProtector()
        self.health_checker = ModelHealthChecker()
        self.db_checker = DBConsistencyChecker(dry_run)
        self.import_checker = ImportConsistencyChecker(dry_run)
        self.component_gen = ComponentGenerator(dry_run)

    def run(self):
        """Run all phases"""
        print("=" * 80)
        if self.dry_run:
            print("AUTO COMPLIANCE FIXER - DRY RUN")
        else:
            print("AUTO COMPLIANCE FIXER - LIVE MODE")
        print("=" * 80)
        print()

        # Show config summary
        self.config.print_summary()
        print()

        models = self._get_models()

        # Phase 0: Custom Code Protection
        print("🛡️  PHASE 0: CUSTOM CODE PROTECTION")
        print("-" * 80)
        self._scan_custom_code()
        print()

        # Phase 1: Model Health
        print("📋 PHASE 1: MODEL HEALTH CHECK")
        print("-" * 80)
        for model in models:
            print(f"Checking: {model.__name__}")
            self.health_checker.check_model(model)
        print()

        # Phase 2: DB Consistency
        print("💾 PHASE 2: DATABASE CONSISTENCY")
        print("-" * 80)
        self.db_checker.check_migrations()
        print()

        # Phase 2.5: Import Consistency
        print("🔍 PHASE 2.5: IMPORT CONSISTENCY CHECK")
        print("-" * 80)
        self.import_checker.check_form_imports()
        print()

        # Phase 3: Component Generation
        print("🔧 PHASE 3: COMPONENT GENERATION (FULL CRUD)")
        print("-" * 80)
        for model in models:
            print(f"Checking: {model.__name__}")
            print(f"  📝 Forms...")
            self.component_gen.generate_form(model)
            print(f"  👁️  Views...")
            self.component_gen.generate_views(model)
            print(f"  🔗 URLs...")
            self.component_gen.generate_urls(model)
            print(f"  📄 Templates...")
            self.component_gen.generate_templates(model)
        print()

        # Summary
        self._print_summary()

    def _scan_custom_code(self):
        """Scan all files for custom code blocks BEFORE generation"""
        # Collect all files that might have custom code
        files_to_scan = []

        # 1. Forms
        forms_path = BASE_DIR / "apps" / "bfagent" / "forms.py"
        if forms_path.exists():
            files_to_scan.append(forms_path)

        # 2. Views
        views_dir = BASE_DIR / "apps" / "bfagent" / "views"
        if views_dir.exists():
            files_to_scan.extend(views_dir.glob("*.py"))

        # 3. Models
        models_path = BASE_DIR / "apps" / "bfagent" / "models.py"
        if models_path.exists():
            files_to_scan.append(models_path)

        # Scan and extract
        self.custom_protector.scan_and_extract(files_to_scan)

        # Backup custom code
        if self.custom_protector.protected_blocks and not self.dry_run:
            backup_dir = BASE_DIR / "backups" / "auto_fix"
            backup_dir.mkdir(parents=True, exist_ok=True)
            self.custom_protector.backup_custom_code(backup_dir)

    def _get_models(self):
        """Get models to process based on configuration"""
        all_models = {m.__name__: m for m in apps.get_models() if m._meta.app_label == "bfagent"}

        # If specific model requested, return it
        if self.model_filter:
            if self.model_filter in all_models:
                model = all_models[self.model_filter]
                if self.config.should_process_model(self.model_filter):
                    return [model]
                else:
                    print(f"⚠️  Model {self.model_filter} is configured to SKIP")
                    return []
            else:
                print(f"❌ Model {self.model_filter} not found")
                return []

        # Get models sorted by priority from config
        models_to_process = []
        for model_name in self.config.get_models_by_priority():
            if model_name in all_models:
                if self.config.should_process_model(model_name):
                    models_to_process.append(all_models[model_name])
            else:
                print(f"   ⚠️  Config references non-existent model: {model_name}")

        print(f"\n📊 Processing {len(models_to_process)} models (by priority)")
        return models_to_process

    def _print_summary(self):
        """Print summary of actions"""
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print()

        # Custom Code Protection
        if self.custom_protector.protected_blocks:
            total_blocks = sum(
                len(blocks) for blocks in self.custom_protector.protected_blocks.values()
            )
            print(
                f"🛡️  Custom Code Protected: {total_blocks} blocks in {len(self.custom_protector.protected_blocks)} files"
            )
            for file_path, blocks in self.custom_protector.protected_blocks.items():
                print(f"   - {Path(file_path).name}: {len(blocks)} blocks")
            print()
        else:
            print("ℹ️  No custom code blocks found")
            print()

        # Model Health Issues
        if self.health_checker.issues_found:
            print(f"❌ Model Health Issues Found: {len(self.health_checker.issues_found)}")
            for issue in self.health_checker.issues_found:
                print(f"   - {issue['model']}: {', '.join(issue['issues'])}")
            print()
        else:
            print("✅ All models healthy")
            print()

        # DB Consistency Issues
        if self.db_checker.issues:
            print(f"⚠️  Database Issues Found: {len(self.db_checker.issues)}")
            for issue in self.db_checker.issues:
                print(f"   - {issue}")
            print()
        else:
            print("✅ Database consistent")
            print()

        # Import Consistency Issues & Fixes
        if self.import_checker.issues:
            print(f"🔧 Import Issues Found: {len(self.import_checker.issues)}")
            if self.import_checker.fixes_applied:
                print(f"   ✅ Fixed {len(self.import_checker.fixes_applied)} files:")
                for fixed_file in self.import_checker.fixes_applied:
                    print(f"      - {Path(fixed_file).name}")
            else:
                print("   ⚠️  Run with --fix to apply corrections")
            print()
        else:
            print("✅ Import consistency validated")
            print()

        # Generated Components
        if self.component_gen.generated:
            print(f"✅ Components Generated: {len(self.component_gen.generated)}")
            for component in self.component_gen.generated:
                print(f"   - {component}")
            print()
        else:
            print("ℹ️  No components needed generation")
            print()

        # Metrics
        total_issues = (
            len(self.health_checker.issues_found)
            + len(self.db_checker.issues)
            + len(self.import_checker.issues)
        )
        total_fixes = len(self.component_gen.generated) + len(self.import_checker.fixes_applied)

        print("📊 METRICS")
        print("-" * 80)
        print(f"Total Issues Found: {total_issues}")
        print(f"Components Generated: {len(self.component_gen.generated)}")
        print(f"Imports Fixed: {len(self.import_checker.fixes_applied)}")
        print(f"Total Fixes Applied: {total_fixes}")
        if total_issues > 0:
            fix_rate = (total_fixes / total_issues) * 100 if total_issues > 0 else 0
            print(f"Fix Rate: {fix_rate:.1f}%")
        print()

        if self.dry_run:
            print("💡 This was a DRY RUN. Use --fix to apply changes.")
        else:
            print("✅ All changes have been applied!")
            print("📦 Backups saved to: backups/auto_fix/")


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Auto Compliance Fixer")
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Run in dry-run mode (default)"
    )
    parser.add_argument("--fix", action="store_true", help="Apply fixes (overrides --dry-run)")
    parser.add_argument("--model", type=str, help="Fix specific model only")

    args = parser.parse_args()

    dry_run = not args.fix

    fixer = AutoComplianceFixer(dry_run=dry_run, model_filter=args.model)
    fixer.run()


if __name__ == "__main__":
    main()
