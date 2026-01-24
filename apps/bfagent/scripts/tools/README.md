# Production Tools

## Purpose
Enterprise-grade development tools for daily workflow, CI/CD, and production use.

## Tool Categories

### 🔍 Quality Assurance
- `htmx_scanner.py` - HTMX conformity scanning
- `model_consistency_checker.py` - Model-Form-Template validation
- `template_url_validator.py` - URL pattern validation
- `url_template_consistency_checker.py` - Cross-validation

### 🎨 Code Formatting
- `code_formatter.py` - Master formatter (Black, isort, flake8)
- `css_theme_switcher.py` - Theme management

### 🔧 Development Tools
- `git-sync-tool.py` - Intelligent git synchronization
- `make_help.py` - Makefile documentation generator
- `make_interactive.py` - Interactive development helper

### 🗄️ Database Tools
- `migration_analyzer.py` - Migration analysis
- `migration_utils.py` - Migration utilities
- `safe_migrate.py` - Safe migration execution

### 📊 Documentation & Visualization
- `screen_documentation_framework.py` - UI documentation
- `visual_model_explorer.py` - Interactive model visualization
- `generate_tool_docs_enhanced.py` - Tool documentation generator

### 🛠️ Development Frameworks
- `consistency_framework.py` - Consistency validation framework
- `agent_action_manager.py` - Agent management
- `phase_agent_template_manager.py` - Template management

### 🚀 API & Integration
- `api_endpoint_checker.py` - API validation
- `control_center.py` - Control Center integration

## Tool Standards

### ✅ All production tools must have:
1. **Version number** in docstring
2. **Help text** (`--help` flag)
3. **Error handling** with meaningful messages
4. **Logging** for debugging
5. **Documentation** in this README
6. **Tests** (if applicable)
7. **Control Center integration** (if UI needed)

### Tool Template:
```python
"""
Tool Name - Brief Description
Version: 1.0.0
Author: BF Agent Team
"""

import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Tool description")
    parser.add_argument('--version', action='version', version='1.0.0')
    # ... more arguments
    
    args = parser.parse_args()
    
    try:
        # Tool logic
        logger.info("✅ Success")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
```

## Integration

### Makefile Commands
Tools should be accessible via Makefile:

```makefile
format-code: ## 🎨 Format all code
	@python scripts/tools/code_formatter.py all

scan-htmx: ## 🔍 Scan HTMX conformity
	@python scripts/tools/htmx_scanner.py
```

### Control Center Registry
Enterprise tools should be registered:

```python
# apps/control_center/registry.py
from control_center.models import Tool

Tool.objects.create(
    name="htmx_scanner",
    version="3.0.0",
    command="python scripts/tools/htmx_scanner.py"
)
```

## Maintenance

### Tool Lifecycle:
1. **Active** - Regularly maintained, up-to-date
2. **Stable** - Feature-complete, minimal changes
3. **Deprecated** - Being phased out, use alternative
4. **Archived** - Moved to `scripts/archive/`

### Version Updates:
- Update version in docstring
- Update CHANGELOG.md
- Update this README
- Test thoroughly
- Create git tag for major versions
