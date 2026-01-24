# BF Agent - Version 0.4.0

## Release Information
- **Version**: 0.4.0
- **Release Date**: October 6, 2025
- **Status**: Stable

## What's New in Version 0.4.0

### 🔧 Enterprise Consistency Framework V4
- **Fix Mode Engine** - Automatic issue detection and repair
  - Detects wrong URL patterns (underscore vs dash)
  - Fixes partial template paths automatically
  - Regenerates broken components with backup
- **Enhanced Architecture**
  - Abstract base classes for extensibility
  - Complete type hints throughout (95% coverage)
  - Dataclasses for type safety
  - SOLID principles implementation
- **Backup & Rollback System**
  - Session-based backup management
  - Automatic rollback on errors
  - Registry for all backups
- **Advanced Analysis**
  - Severity classification (Critical/Warning/Info)
  - Color-coded output with Django style
  - Issue grouping by file
  - Fix availability detection
- **New Commands**
  - `fix` - Automatically fix detected issues
  - `batch` - Process multiple models
  - `--dry-run` - Preview changes before applying
  - `--force` - Force regeneration

### 🐛 Root Cause Fixes
- **URL Pattern Bug** - Generator now creates correct URL names with dashes
  - Before: `{% url 'bfagent:worlds_create' %}` ❌
  - After: `{% url 'bfagent:worlds-create' %}` ✅
- **Circular Dependency Detection** - Fixed false positives
- **Partial Template Paths** - Automatic `partials/` folder structure

### 📦 Worlds CRUD
- Complete Worlds model CRUD implementation
- Fixed template URL naming inconsistencies
- Proper partials folder structure

### 📊 Performance & Quality
- Type hints coverage: 0% → 95%
- Architecture: Monolithic → Modular
- Fix time: Hours → Seconds
- Async support for batch operations

## Previous Release Notes (0.3.0)

### ✅ Frontend Stability & UX
- Standardized HTMX CRUD baseline across forms
  - `hx-ext="response-targets"`, `hx-target-422="this"`, `hx-swap="outerHTML"`
  - Invalid HTMX POST returns form partial with HTTP 422
  - Valid HTMX POST returns updated paginated list partial
- Stable list container ids so edits continue working after swaps
  - Agents: `#agent-content`
  - Characters: `#character-content`
  - LLMs: `#llm-content`
- Project detail page added and Back navigation fixed

### ✍️ Agent Prompt Templates
- Prompt template selector in Agent form (Writer, Editor, Planner)
- Preview modal with Insert action
- LocalStorage persistence of last-used template + defaults
- Defaults auto-apply on Agent Type change

### 🧪 Tests
- Minimal pytest for Agent HTMX 422 flow

### 📚 Documentation
- CRUD Frontend Baseline doc with 422/error handling/pagination contract
- README updated with v0.3.0 summary

## Previous Release Notes (0.1.0)
See earlier sections for initial features and stack overview.

## Dependencies
- Django 5.2
- django-htmx
- django-template-partials
- python-decouple
- whitenoise
- gunicorn

## Contributors
- Achim Dehnert (Project Lead)

## Next Release - Planned
- Valid HTMX POST returns updated list with filter preservation
- Agent-driven project enrichment workflows
