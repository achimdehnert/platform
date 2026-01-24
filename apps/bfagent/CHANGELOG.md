# Changelog

All notable changes to the BF Agent project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-12-26

#### AI-Assisted Prompt System for Illustrations v2.5.0
- **Prompt System Models:**
  - 🎨 `PromptMasterStyle` - Project-level visual style configuration
  - 👥 `PromptCharacter` - Character appearance prompts with roles
  - 🗺️ `PromptLocation` - Location/environment prompts
  - 📚 `PromptCulturalElement` - Cultural context glossary
  - 🎬 `PromptSceneTemplate` - Reusable scene templates
  - 📊 `PromptGenerationLog` - AI generation audit trail

- **AI Generation Features:**
  - ✨ Auto-generate style from book data (title, genre, description, atmosphere)
  - 🤖 KI-Assistent for complete prompt system generation
  - 📖 Extract characters from book content using AI
  - 🏔️ Extract locations from book content using AI
  - 🎯 Genre-based style presets (Fantasy, Märchen, Sci-Fi, Romance, etc.)
  - 🔄 Fallback to rule-based generation when no LLM available

- **Prompt System UI:**
  - 📋 Tabbed interface: Master Style, Characters, Locations, Cultural Elements, Templates
  - ⚡ Quick-start "Aus Buchdaten generieren" button
  - 🎨 Preset loading (Kazakh Fairytale, Fantasy Epic, etc.)
  - ✏️ CRUD modals for characters and locations
  - 🔗 Integration with Illustration Dashboard

- **New Endpoints (10):**
  - `prompt_system_setup` - Main configuration page
  - `save_master_style` - Save/update master style
  - `save_prompt_character` / `delete_prompt_character` - Character CRUD
  - `save_prompt_location` / `delete_prompt_location` - Location CRUD
  - `load_prompt_preset` - Load predefined presets
  - `generate_prompt_system_with_ai` - Full AI generation
  - `extract_characters_from_book` - AI character extraction
  - `extract_locations_from_book` - AI location extraction
  - `suggest_style_from_book` - Auto-suggest style from project data

- **Handler:**
  - 🔧 `PromptBuilderHandler` - Business logic for prompt assembly
  - 🏭 `PromptPresetFactory` - Preset configuration factory

#### Roadmap: Universal Workflow Orchestration Platform v3.0
- 📋 Documentation: `docs/graphen/Universal Workflow Orchestration Platform README.md`
- 🎯 Planned: Graph-based visualization with Cytoscape.js
- 🎯 Planned: DB-driven Framework Registry (Save the Cat, Hero's Journey, C4 Model)
- 🎯 Planned: GraphNode/GraphEdge for complex story relationships
- 🎯 Planned: ReAct Agent Loop for AI-powered content generation

### Added - 2025-10-30

#### Complete Book Writing System v2.0
- **Chapter Management:**
  - ✏️ Full-featured Chapter Editor with live word count
  - ⭐ Single chapter AI generation with context awareness
  - ⚡ Batch generation: "Alle Generieren" button for full-book generation
  - Sequential processing with progress display
  - Smart skip logic for existing content

- **Outline Generation:**
  - 📖 Save the Cat Beat Sheet (15-beat structure)
  - Modal UI with framework selection
  - Auto chapter creation based on beats
  - Beat-based outlines for each chapter

- **Character Management:**
  - 👥 Complete CRUD for characters
  - Character details: Name, Role, Age, Description
  - Background, Personality, Appearance
  - Motivation, Conflict, Character Arc
  - URLs: create, edit, delete, detail views

- **World Building:**
  - 🌍 WorldSetting model (OneToOne with Project)
  - 📍 Locations with hierarchy (parent/child)
  - 📜 World Rules with categories and importance
  - Complete CRUD for all world components
  - URLs: world detail, edit, location/rule management

- **Handlers:**
  - `UniversalStoryChapterHandler` - Works for ALL chapters
  - Beat-aware content generation
  - Previous chapter context integration
  - Dynamic handler selection (Essay vs Story)

- **Database:**
  - New models: WorldSetting, Location, WorldRule
  - Migration: `0042_world_building_models.py`
  - OneToOne relationship: Project ↔ World
  - ForeignKey relationships for locations and rules

- **Documentation:**
  - Complete system documentation in `docs/BOOK_WRITING_SYSTEM.md`
  - Architecture overview
  - Usage examples (Romance, Fantasy)
  - API reference
  - Testing checklist

### Changed - 2025-10-30
- Chapter views: Dynamic handler selection based on book type
- Chapter generation now supports previous chapter context
- Outline generation integrated into project detail page
- Project detail UI: Added "Alle Generieren" button

### Fixed - 2025-10-30
- Handler not found for chapters 4+ (now using UniversalStoryChapterHandler)
- Modal close issue after outline generation
- Chapter generation now includes beat description in content

### Added - 2025-01-19

#### Enterprise-Grade Scripts Organization & Root Folder Cleanup
- **NEW**: `scripts/analyze_makefile_scripts.py` - Automatic Makefile tool discovery
  - Scans all Makefiles (Main, Agents, Quick)
  - Categorizes 51 scripts by usage frequency
  - Generates Python lists for reorganization
  - Identifies missing scripts

- **NEW**: `scripts/cleanup_root_folder.py` - Automated root folder cleanup
  - Organizes 60+ root-level files
  - Database backups → `backups/database/`
  - HTMX reports → `reports/htmx/`
  - Helper scripts → `scripts/helpers/`
  - MD documentation → `docs/` subfolders
  - DRY RUN mode with preview

- **NEW**: `scripts/reorganize_scripts.py` - Script reorganization tool
  - Categorizes scripts by Makefile usage
  - Creates professional folder structure
  - Safe backup-based moves

- **NEW**: Requirements management improvements
  - `requirements-dev.txt` - Development tools (black, flake8, mypy, pylint)
  - Updated `requirements.txt` with exact versions (Django 5.2.6)
  - Updated `requirements_llm.txt` with version constraints

- **NEW**: Documentation structure
  - `docs/MAKEFILE_ORGANIZATION.md` - Complete organization guide
  - `docs/ROOT_FOLDER_CLEANUP.md` - Cleanup guide with examples
  - `docs/templates/COMMIT_MESSAGE_TEMPLATE.md` - Commit message template
  - `memory-bank/@scripts-organization.md` - Scripts & tooling reference
  - `memory-bank/@frontend-patterns.md` - Bootstrap Modal patterns

### Fixed

#### Bootstrap Modal Flickering Issue (phase_detail.html)
- **5-Layer Protection Pattern** implemented:
  - Layer 1: Early script in `<head>` (capture phase)
  - Layer 2: Synchronous inline script (immediate execution)
  - Layer 3: Manual modal control with debounce (500ms)
  - Layer 4: CSS pointer-events isolation
  - Layer 5: Sortable.js filter configuration
- Tested across Firefox, Edge, Chrome
- Stable modal behavior in Sortable tables
- Documented solution pattern for future use

### Changed

- **README.md** - Added Enterprise-Grade Development Tools section
- **Project Structure** - Recommended organization for scripts and documentation
- **Requirements** - Pinned versions for stability, separated dev dependencies

### Added - 2025-01-07

#### Configuration-Driven Auto-Compliance-Fixer
- **NEW**: `config/crud_config.yaml` - Declarative CRUD configuration
  - Define CRUD levels (FULL_CRUD, READ_ONLY, UD_ONLY, SKIP)
  - Priority-based model processing
  - Feature-specific generation (forms, views, templates, urls)
  - Custom code protection flags
  - Model exclusion rules

- **NEW**: `CRUDConfigLoader` class - YAML configuration loader
  - Validates configuration on load
  - Priority-based model sorting
  - Feature checking per model
  - Configuration summary display

- **Phase 0: Custom Code Protection**
  - Automatic detection of custom code markers
  - Extraction and backup before regeneration
  - JSON backup: `backups/auto_fix/custom_code_backup.json`
  - Supported markers:
    - `# CUSTOM_CODE_START:` / `# CUSTOM_CODE_END:`
    - `# BUSINESS_LOGIC_START:` / `# BUSINESS_LOGIC_END:`
    - `# USER_CODE_START:` / `# USER_CODE_END:`
    - `# DO_NOT_MODIFY`

- **Phase 2.5: Import Consistency Checker**
  - Automatic detection of wrong form imports
  - Intelligent name matching (BookProjectForm → BookProjectsForm)
  - Automatic fixes with backup
  - Reports fixed files in summary

- **Pre-Flight Validation Pattern**
  - Validate operations BEFORE creating backups
  - Prevents wasted backups on failed operations
  - Better error messages with expected structure
  - Applied to URL generation

- **Documentation**
  - `docs/auto-compliance-fixer.md` - Complete usage guide
  - Configuration examples
  - Troubleshooting guide
  - Success stories

### Changed

- **auto_compliance_fixer.py** - Major refactoring
  - Configuration-driven model processing
  - Priority-based execution order
  - Feature-specific component generation
  - Improved backup strategy
  - Pre-flight validation for all generators
  - UTF-8 encoding enforced everywhere

- **Workflow Phases** - Enhanced
  - Phase 0 (NEW): Custom Code Protection
  - Phase 1: Model Health Check
  - Phase 2: Database Consistency
  - Phase 2.5 (NEW): Import Consistency Check
  - Phase 3: Component Generation (with Pre-Flight Validation)

### Fixed

- **Wasted Backups** - Pre-Flight Validation prevents backup creation when operations will fail
- **Import Errors** - Automatic detection and fixing of form name mismatches
- **Custom Code Loss** - Protection system preserves all marked custom code
- **UTF-8 Issues** - Enforced encoding for all generated files
- **URL Generation** - Better insertion point detection with helpful error messages

### Technical Details

#### Configuration Schema
```yaml
models:
  ModelName:
    level: FULL_CRUD | READ_ONLY | UD_ONLY | SKIP
    priority: high | medium | low | none
    custom_code: true | false
    features: [forms, views, templates, urls]
```

#### Protected Code Markers
- Multi-line: `# CUSTOM_CODE_START:name` ... `# CUSTOM_CODE_END:`
- Single-line: `# DO_NOT_MODIFY`

#### Pre-Flight Validation Benefits
- No wasted backup files
- Fail fast with clear error messages
- Shows validation details in dry-run mode
- Cleaner backup directory

## [Previous Releases]

See git history for previous changes before this changelog was introduced.
# Auto-Deploy enabled 2026-01-21T12:52:10+01:00
