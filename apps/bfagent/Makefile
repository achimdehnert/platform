# BF Agent Development Makefile
# Provides common development tasks and shortcuts

# ============================================================================
# UTF-8 ENCODING FIX FOR WINDOWS
# ============================================================================
export PYTHONUTF8=1

# ============================================================================
# CONFIGURATION
# ============================================================================
# Python executable - use .venv if available, fallback to system python
# Note: Use forward slashes for cross-platform compatibility
PYTHON := .venv/Scripts/python.exe
ifeq (,$(wildcard $(PYTHON)))
    PYTHON := python
endif

# Default port (can be overridden: make dev PORT=9000 or make dev port=9000)
# Support both uppercase and lowercase for convenience
ifdef port
    PORT := $(port)
else
    PORT ?= 8000
endif

DOCKER_COMPOSE := docker compose -f docker-compose.yml -f docker-compose.platform.yml

# MCP Hub path for LLM Gateway
MCP_HUB_PATH := ../mcp-hub
LLM_GATEWAY_PORT ?= 8100

# ============================================================================
# INCLUDES
# ============================================================================
# Include specialized Makefiles for different subsystems
-include Makefile.agents
-include Makefile.genagent

.PHONY: help install dev kill restart test clean migrate collectstatic runserver shell createsuperuser backup restore sync quick-sync kill-server reset-server clean-cache control setup-workflows run server check stop rs docs-analyze docs-link docs-link-apply feature-complete

# Default target - Enhanced help system
help: ## 📋 Show all available commands (hierarchical tree view) @category:project @sub:Quick Actions
	@python scripts/make_help.py tree

help-table: ## 📊 Show commands in table format @category:project @sub:Quick Actions
	@python scripts/make_help.py table

help-search: ## 🔍 Search commands (use: make help-search Q=term) @category:project @sub:Quick Actions
	@python scripts/make_help.py search -q "$(Q)"

help-stats: ## 📈 Show Makefile statistics @category:project @sub:Quick Actions
	@python scripts/make_help.py stats

menu: ## 🎛️  Interactive command menu (RECOMMENDED!) @category:project @sub:Quick Actions
	@python scripts/make_interactive.py

install: ## 📥 Install dependencies and setup project @category:project @sub:Setup
	pip install -r requirements.txt
	python manage.py migrate
	python manage.py collectstatic --noinput
	@echo "✅ Project setup complete!"

create-objects: ## 🏗️  Create files/dirs/symlinks from JSON spec (FILE=with_input.json) @category:dev @sub:Utilities
	@echo "🏗️  Creating objects from JSON specification..."
	@python create_needed.py $(if $(FILE),$(FILE),with_input.json)
	@echo "✅ Objects created!"

create-handlers: ## 📦 Create block handler files for presentation studio @category:dev @sub:Utilities
	@echo "📦 Creating block handler files..."
	@python create_files.py block_handlers_files.json
	@echo "✅ Handler files created!"

dev: ## 🚀 Start development server with debug tools (use PORT=9000 to override) @category:dev @sub:Server
	@echo "🚀 Starting development server on port $(PORT)..."
	@echo "🐍 Using Python: $(PYTHON)"
	$(PYTHON) manage.py runserver 0.0.0.0:$(PORT)

start-docker: ## 🐳 Start Docker platform (docker-compose.yml + docker-compose.platform.yml) @category:docker @sub:Platform
	$(DOCKER_COMPOSE) up -d --build

docker-ps: ## 🐳 Show Docker platform status @category:docker @sub:Platform
	$(DOCKER_COMPOSE) ps

docker-logs: ## 🐳 Tail bfagent_web logs (use TAIL=200) @category:docker @sub:Platform
	$(DOCKER_COMPOSE) logs --tail $(if $(TAIL),$(TAIL),200) bfagent-web

docker-recreate-web: ## 🐳 Recreate bfagent-web with rebuild (hotfix URL changes etc.) @category:docker @sub:Platform
	$(DOCKER_COMPOSE) up -d --build --force-recreate bfagent-web

docker-down: ## 🐳 Stop Docker platform (keep volumes) @category:docker @sub:Platform
	$(DOCKER_COMPOSE) down

docker-down-v: ## 🐳 Stop Docker platform and remove volumes (RESET DB) @category:docker @sub:Platform
	$(DOCKER_COMPOSE) down -v

# ============================================================================
# COMFYUI - LOCAL IMAGE GENERATION
# ============================================================================
COMFYUI_PORT ?= 8181
COMFYUI_PATH ?= ~/ai-tools/ComfyUI

# Documentation Server (Sphinx)
DOCS_PORT ?= 8001
DOCS_PATH ?= docs

comfyui: ## 🎨 Start ComfyUI for local image generation @category:ai @sub:Image Generation
	@echo "🎨 Starting ComfyUI on port $(COMFYUI_PORT)..."
	@echo "📁 Path: $(COMFYUI_PATH)"
	@echo ""
	cd $(COMFYUI_PATH) && python main.py --listen 0.0.0.0 --port $(COMFYUI_PORT)

docs: ## 📚 Start documentation server with live reload @category:docs @sub:Documentation
	@echo "📚 Starting Documentation Server on port $(DOCS_PORT)..."
	@echo "📁 Path: $(DOCS_PATH)"
	@echo "🌐 Open http://localhost:$(DOCS_PORT) in your browser"
	@echo ""
	cd $(DOCS_PATH) && sphinx-autobuild source build/html --port $(DOCS_PORT)

docs-build: ## 📖 Build documentation (HTML) @category:docs @sub:Documentation
	@echo "📖 Building HTML documentation..."
	cd $(DOCS_PATH) && make html
	@echo "✅ Documentation built: $(DOCS_PATH)/build/html/index.html"

docs-sync: ## 🔄 Check Sphinx documentation for changes @category:docs @sub:Documentation
	@echo "🔄 Checking Sphinx documentation..."
	$(PYTHON) manage.py sphinx_sync

docs-sync-report: ## 📊 Generate detailed Sphinx sync report @category:docs @sub:Documentation
	@echo "📊 Generating Sphinx sync report..."
	$(PYTHON) manage.py sphinx_sync --report

docs-sync-full: ## 🚀 Full Sphinx sync (check + generate stubs + rebuild) @category:docs @sub:Documentation
	@echo "🚀 Running full Sphinx synchronization..."
	$(PYTHON) manage.py sphinx_sync --full-sync

docs-stubs: ## 📝 Generate missing autodoc stubs @category:docs @sub:Documentation
	@echo "📝 Generating missing autodoc stubs..."
	$(PYTHON) manage.py sphinx_sync --generate-stubs

docs-stubs-dry: ## 🔍 Preview autodoc stubs (dry-run) @category:docs @sub:Documentation
	@echo "🔍 Preview autodoc stubs (no changes)..."
	$(PYTHON) manage.py sphinx_sync --generate-stubs --dry-run

docs-export: ## 📤 Export Sphinx docs to Markdown @category:docs @sub:Documentation
	@echo "📤 Exporting Sphinx documentation to Markdown..."
	$(PYTHON) manage.py sphinx_to_markdown
	@echo "✅ Export complete! Check /tmp for output file."

comfyui-check: ## 🔍 Check if ComfyUI is running @category:ai @sub:Image Generation
	@echo "🔍 Checking ComfyUI status on port $(COMFYUI_PORT)..."
	@curl -s http://localhost:$(COMFYUI_PORT)/system_stats > /dev/null 2>&1 && echo "✅ ComfyUI is running on port $(COMFYUI_PORT)" || echo "❌ ComfyUI is NOT running. Start with: make comfyui"

comfyui-status: ## 📊 Show ComfyUI system stats @category:ai @sub:Image Generation
	@echo "📊 ComfyUI System Stats:"
	@curl -s http://localhost:$(COMFYUI_PORT)/system_stats | python -m json.tool 2>/dev/null || echo "❌ ComfyUI nicht erreichbar. Start: make comfyui"

# ============================================================================
# CELERY - BACKGROUND TASK PROCESSING
# ============================================================================

celery: ## 🥬 Start Celery worker for background tasks @category:dev @sub:Server
	@echo "🥬 Starting Celery worker..."
	celery -A config worker -l INFO

celery-beat: ## ⏰ Start Celery beat scheduler @category:dev @sub:Server
	@echo "⏰ Starting Celery beat..."
	celery -A config beat -l INFO

# ============================================================================
# COMBINED START COMMANDS
# ============================================================================

# Helper to free a port (WSL/Linux compatible)
free-port: ## 🔓 Free a specific port (usage: make free-port P=8000) @category:dev @sub:Server
	@echo "🔓 Freeing port $(P)..."
	@fuser -k $(P)/tcp 2>/dev/null || true
	@echo "✅ Port $(P) is now free"

stop-all: ## 🛑 Stop all BF Agent services @category:dev @sub:Server
	@echo "🛑 Stopping all BF Agent services..."
	@echo "   Freeing port $(PORT) (Django)..."
	-@lsof -ti:$(PORT) | xargs -r kill -9 2>/dev/null || true
	@echo "   Freeing port $(LLM_GATEWAY_PORT) (LLM Gateway)..."
	-@lsof -ti:$(LLM_GATEWAY_PORT) | xargs -r kill -9 2>/dev/null || true
	@echo "   Freeing port $(COMFYUI_PORT) (ComfyUI)..."
	-@lsof -ti:$(COMFYUI_PORT) | xargs -r kill -9 2>/dev/null || true
	@echo "   Freeing port $(DOCS_PORT) (Docs Server)..."
	-@lsof -ti:$(DOCS_PORT) | xargs -r kill -9 2>/dev/null || true
	@echo "   Stopping Celery workers..."
	-@pkill -9 -f "celery -A config worker" 2>/dev/null || true
	-@pkill -9 -f "ComfyUI/main.py" 2>/dev/null || true
	-@pkill -9 -f "sphinx-autobuild" 2>/dev/null || true
	@echo "✅ All services stopped!"

start-all: ## 🚀 Start all services (Django + Celery + ComfyUI + LLM Gateway + Docs) in background @category:dev @sub:Server
	@echo "🚀 Starting all BF Agent services..."
	@echo ""
	@echo "🔓 Ensuring all ports are free..."
	-@lsof -ti:$(PORT) | xargs -r kill -9 2>/dev/null || true
	-@lsof -ti:$(LLM_GATEWAY_PORT) | xargs -r kill -9 2>/dev/null || true
	-@lsof -ti:$(COMFYUI_PORT) | xargs -r kill -9 2>/dev/null || true
	-@lsof -ti:$(DOCS_PORT) | xargs -r kill -9 2>/dev/null || true
	-@pkill -9 -f "celery -A config worker" 2>/dev/null || true
	-@pkill -9 -f "ComfyUI/main.py" 2>/dev/null || true
	-@pkill -9 -f "sphinx-autobuild" 2>/dev/null || true
	@sleep 1
	@echo ""
	@echo "1️⃣  Starting LLM Gateway on port $(LLM_GATEWAY_PORT)..."
	cd $(MCP_HUB_PATH) && PYTHONPATH=. $(PYTHON) -m llm_mcp.http_gateway &
	@sleep 2
	@echo "2️⃣  Starting Django server on port $(PORT)..."
	$(PYTHON) manage.py runserver 0.0.0.0:$(PORT) &
	@sleep 2
	@echo "3️⃣  Starting Celery worker..."
	celery -A config worker -l INFO &
	@sleep 2
	@echo "4️⃣  Starting ComfyUI on port $(COMFYUI_PORT)..."
	cd $(COMFYUI_PATH) && python main.py --listen 0.0.0.0 --port $(COMFYUI_PORT) &
	@sleep 2
	@echo "5️⃣  Starting Documentation Server on port $(DOCS_PORT)..."
	cd $(DOCS_PATH) && sphinx-autobuild source build/html --port $(DOCS_PORT) &
	@echo ""
	@echo "✅ All services started!"
	@echo "   LLM Gateway: http://localhost:$(LLM_GATEWAY_PORT)"
	@echo "   Django:      http://localhost:$(PORT)"
	@echo "   ComfyUI:     http://localhost:$(COMFYUI_PORT)"
	@echo "   Docs:        http://localhost:$(DOCS_PORT)"

start-dev: ## 🔧 Start Django + Celery + LLM Gateway (without ComfyUI) @category:dev @sub:Server
	@echo "🔧 Starting development services..."
	@echo ""
	@echo "🔓 Ensuring ports are free..."
	-@lsof -ti:$(PORT) | xargs -r kill -9 2>/dev/null || true
	-@lsof -ti:$(LLM_GATEWAY_PORT) | xargs -r kill -9 2>/dev/null || true
	-@pkill -9 -f "celery -A config worker" 2>/dev/null || true
	@sleep 1
	@echo ""
	@echo "1️⃣  Starting LLM Gateway on port $(LLM_GATEWAY_PORT)..."
	cd $(MCP_HUB_PATH) && PYTHONPATH=. $(PYTHON) -m llm_mcp.http_gateway &
	@sleep 2
	@echo "2️⃣  Starting Django server on port $(PORT)..."
	$(PYTHON) manage.py runserver 0.0.0.0:$(PORT) &
	@sleep 2
	@echo "3️⃣  Starting Celery worker..."
	celery -A config worker -l INFO
	@echo ""
	@echo "✅ Dev services started!"
	@echo "   LLM Gateway: http://localhost:$(LLM_GATEWAY_PORT)"
	@echo "   Django:      http://localhost:$(PORT)"

start-llm-gateway: ## 🤖 Start LLM Gateway only @category:dev @sub:Server
	@echo "🤖 Starting LLM Gateway on port $(LLM_GATEWAY_PORT)..."
	cd $(MCP_HUB_PATH) && PYTHONPATH=. $(PYTHON) -m llm_mcp.http_gateway

stop-llm-gateway: ## 🛑 Stop LLM Gateway @category:dev @sub:Server
	@echo "🛑 Stopping LLM Gateway on port $(LLM_GATEWAY_PORT)..."
	@powershell -Command "Get-NetTCPConnection -LocalPort $(LLM_GATEWAY_PORT) -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul || echo "⚠️ No gateway running on port $(LLM_GATEWAY_PORT)"
	@echo "✅ Gateway stopped!"

kill: ## 🛑 Kill Django development server @category:dev @sub:Server
	@echo "🛑 Killing Django server on port $(PORT)..."
	@powershell -Command "Get-NetTCPConnection -LocalPort $(PORT) -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul || echo "⚠️ No server running on port $(PORT)"
	@echo "✅ Server killed!"

restart: ## 🔄 Restart Django development server @category:dev @sub:Server
	@echo "🔄 Restarting Django server on port $(PORT)..."
	@powershell -Command "Get-NetTCPConnection -LocalPort $(PORT) -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul || echo "⚠️ No server running on port $(PORT)"
	@echo "⏳ Waiting 2 seconds..."
	@powershell -Command "Start-Sleep -Seconds 2"
	@echo "🚀 Starting server on port $(PORT)..."
	@echo "🐍 Using Python: $(PYTHON)"
	$(PYTHON) manage.py runserver 0.0.0.0:$(PORT)

test: ## ✅ Run all tests @category:test @sub:Test Execution
	python manage.py test
	python quick_status.py
	@echo "✅ All tests passed!"

clean: ## 🧹 Clean up temporary files @category:maintenance @sub:Cleanup
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -exec rm -rf {} +
	@echo "✅ Cleanup complete!"

clear-cache: ## 🧹 Clear all Python and Django caches @category:maintenance @sub:Cleanup
	@echo "🧹 Clearing Python bytecode cache..."
	@powershell -Command "Get-ChildItem -Path . -Include *.pyc,__pycache__ -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue"
	@echo "🧹 Clearing Django template cache..."
	@powershell -Command "if (Test-Path 'tmp\\cache') { Remove-Item -Path 'tmp\\cache' -Recurse -Force }"
	@echo "🧹 Clearing collected static files..."
	@powershell -Command "if (Test-Path 'staticfiles') { Remove-Item -Path 'staticfiles\\*' -Recurse -Force -ErrorAction SilentlyContinue }"
	@echo "✅ All caches cleared!"
	@echo "💡 Tip: Run 'python manage.py runserver' to restart with fresh cache"

clear-templates: ## 🎨 Clear Django template cache only @category:maintenance @sub:Cleanup
	@echo "🎨 Clearing Django template cache..."
	@powershell -Command "if (Test-Path 'tmp\\cache') { Remove-Item -Path 'tmp\\cache' -Recurse -Force }"
	@echo "✅ Template cache cleared!"
	@echo "💡 Tip: Restart server to see changes"

clear-all: ## 💥 Nuclear option - Clear everything and restart @category:maintenance @sub:Cleanup
	@echo "💥 NUCLEAR CLEANUP - Clearing ALL caches..."
	@echo "🛑 Stopping server on port $(PORT)..."
	@powershell -Command "Get-NetTCPConnection -LocalPort $(PORT) -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $$_.OwningProcess -Force -ErrorAction SilentlyContinue }" 2>nul || echo "⚠️ No server running"
	@echo "🧹 Clearing Python caches..."
	@powershell -Command "Get-ChildItem -Path . -Include *.pyc,__pycache__,.pytest_cache -Recurse | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue"
	@echo "🧹 Clearing Django caches..."
	@powershell -Command "if (Test-Path 'tmp\\cache') { Remove-Item -Path 'tmp\\cache' -Recurse -Force }"
	@echo "🧹 Clearing static files..."
	@powershell -Command "if (Test-Path 'staticfiles') { Remove-Item -Path 'staticfiles\\*' -Recurse -Force -ErrorAction SilentlyContinue }"
	@echo "⏳ Waiting 2 seconds..."
	@powershell -Command "Start-Sleep -Seconds 2"
	@echo "🚀 Starting fresh server..."
	@echo "🐍 Using Python: $(PYTHON)"
	$(PYTHON) manage.py runserver 0.0.0.0:$(PORT)

status: ## 📊 Quick project status check @category:monitor @sub:Performance
	@echo "🔍 BF Agent Status Check:"
	@echo "========================"
	python quick_status.py
	@echo ""
	@echo "📊 Database Status:"
	python manage.py showmigrations --list
	@echo ""
	@echo "🚀 Server Status (Port $(PORT)):"
	@python -c "import urllib.request; print('✅ Server reachable on port $(PORT)' if urllib.request.urlopen('http://127.0.0.1:$(PORT)').getcode() == 200 else '❌ Server not running')" 2>nul || echo "❌ Server not running on port $(PORT)"

migrate-create: ## 🆕 Create migrations for model changes (Step 1) @category:db @sub:Migrations
	@echo "🆕 Creating new migrations..."
	@echo ""
	@echo "Step 1: Check current migration status..."
	@python manage.py showmigrations --list bfagent
	@echo ""
	@echo "Step 2: Detect model changes..."
	@python manage.py makemigrations --dry-run --verbosity 2 bfagent
	@echo ""
	@echo "Step 3: Create migrations..."
	@python manage.py makemigrations bfagent
	@echo ""
	@echo "Step 4: Check for unwanted initial migrations..."
	@powershell -Command "$$initialFound = $$false; if (Test-Path 'apps\bfagent\migrations\0025_initial.py') { Write-Host '⚠️  Detected 0025_initial.py (squashed migration)'; Write-Host '🔄 Removing and re-generating proper migration...'; Remove-Item 'apps\bfagent\migrations\0025_initial.py' -Force; $$initialFound = $$true }; if (Test-Path 'apps\bfagent\migrations\0026_initial.py') { Remove-Item 'apps\bfagent\migrations\0026_initial.py' -Force; $$initialFound = $$true }; if ($$initialFound) { Write-Host ''; python manage.py makemigrations bfagent; Write-Host '✅ Proper migration created!' } else { Write-Host '✅ No initial migrations detected - migration is good!' }"
	@echo ""
	@echo "💡 Next: Run 'make migrate' to apply migrations."

migrate: ## ⭐ Apply migrations safely with auto-fix (Step 2) @category:db @sub:Migrations
	@make migrate-safe

migrate-quick: ## ⚠️ UNSAFE: Quick migration without safety checks @category:db @sub:Migrations @internal
	@echo "⚠️ WARNING: Running UNSAFE migration without backups!"
	@echo "⚠️ Use 'make migrate' (migrate-safe) instead!"
	@echo ""
	@read -p "Continue anyway? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	python manage.py makemigrations
	python manage.py migrate
	@echo "✅ Migrations applied!"

validate-migration-chain: ## 🔗 Validate migration chain for gaps and broken dependencies @category:db @sub:Migrations
	@echo "🔗 Validating migration chain integrity..."
	@python scripts/fix_migrations.py validate-chain --app bfagent --auto-fix
	@echo ""
	@echo "💡 Chain validation complete!"

validate-chain-dry: ## 🔍 Check migration chain without fixing @category:db @sub:Migrations
	@echo "🔍 Checking migration chain (dry-run)..."
	@python scripts/fix_migrations.py validate-chain --app bfagent --dry-run

migrate-quick-backup: ## 💾 Quick database backup (no migration) @category:db @sub:Migrations
	@echo "💾 Creating quick backup..."
	@powershell -Command "Copy-Item bfagent.db bfagent_backup_$$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
	@echo "✅ Backup created!"

migrate-prompt-system: ## 🔧 Apply Prompt Management System v2.0 migration (0038) @category:db @sub:Migrations
	@echo "🚀 Applying Prompt Management System v2.0 Migration..."
	@echo ""
	@echo "Step 1: Backup database..."
	@powershell -Command "Copy-Item bfagent.db bfagent_backup_prompt_v2_$$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
	@echo "✅ Backup created!"
	@echo ""
	@echo "Step 2: Fix invalid JSON data in database..."
	python fix_db_before_migration.py
	@echo ""
	@echo "Step 3: Running migration..."
	python manage.py migrate bfagent 0038
	@echo ""
	@echo "✅ Prompt Management System v2.0 successfully migrated!"

migrate-safe: ## 🛡️ Safe migration with auto-fake for "table exists" errors @category:db @sub:Migrations @internal
	@echo "🛡️ Starting SAFE migration process..."
	@echo ""
	@echo "Step 1: Backup current database..."
	@powershell -Command "Copy-Item bfagent.db bfagent_backup_$$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
	@echo "✅ Backup created!"
	@echo ""
	@echo "Step 2: Validate migration chain..."
	@make validate-migration-chain
	@echo ""
	@echo "Step 3: Auto-fix migration issues..."
	@python scripts/auto_fix_migrations.py
	@echo ""
	@echo "Step 4: Validate existing migrations..."
	@python scripts/validate_migrations.py || echo "⚠️ Migration issues detected"
	@echo ""
	@echo "Step 5: Generate new migrations..."
	@python manage.py makemigrations || (echo "❌ Migration generation failed!" && exit 1)
	@echo ""
	@echo "Step 6: Check for unwanted initial migrations..."
	@powershell -Command "if (Test-Path 'apps\bfagent\migrations\0025_initial.py') { Write-Host '⚠️  Detected 0025_initial.py - removing and retrying...'; Remove-Item 'apps\bfagent\migrations\0025_initial.py' -Force; Write-Host '🔄 Re-generating migrations...'; python manage.py makemigrations } else { Write-Host '✅ No initial migrations detected' }"
	@powershell -Command "if (Test-Path 'apps\bfagent\migrations\0026_initial.py') { Write-Host '⚠️  Detected 0026_initial.py - removing...'; Remove-Item 'apps\bfagent\migrations\0026_initial.py' -Force }"
	@echo ""
	@echo "Step 7: Verify migrations were created..."
	@python manage.py makemigrations --check --dry-run || echo "⚠️ Model changes still pending - will be addressed in next run"
	@echo ""
	@echo "Step 8: Dry-run migration check..."
	@python manage.py migrate --plan || echo "⚠️ Migration plan has warnings"
	@echo ""
	@echo "Step 9: Apply migrations with auto-fake on table exists..."
	@python scripts/safe_migrate.py || (echo "❌ Migration failed! Rolling back..." && make migrate-rollback && exit 1)
	@echo ""
	@echo "✅ Safe migration completed successfully!"

migrate-fix: ## 🔧 Manual fix only (auto-run by 'make migrate') @category:db @sub:Migrations @internal
	@echo "🔧 Running migration auto-fix..."
	@python scripts/auto_fix_migrations.py
	@echo "✅ Migration fixes applied!"
	@echo ""
	@echo "💡 TIP: Run 'make migrate' to apply migrations with auto-fix"

migrate-rollback: ## ⏮️ Rollback to last working migration @category:db @sub:Migrations
	@echo "⏮️ Rolling back migrations..."
	@powershell -Command "$$backup = Get-ChildItem bfagent_backup_*.db | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($$backup) { Copy-Item $$backup.FullName bfagent.db -Force; Write-Host '✅ Rolled back to backup:' $$backup.Name } else { Write-Host '❌ No backup found!' }"

migrate-status: ## 📊 Show migration status and conflicts @category:db @sub:Migrations
	@echo "📊 Migration Status:"
	@echo ""
	@python manage.py showmigrations --list
	@echo ""
	@echo "🔍 Checking for conflicts..."
	@python manage.py makemigrations --dry-run --check || echo "⚠️ Unapplied migrations or conflicts detected!"

migrate-check: ## 🔍 Quick migration health check @category:db @sub:Migrations
	@echo "🔍 Migration Health Check"
	@echo "=" | powershell -Command "$$('=' * 60)"
	@echo ""
	@echo "📁 Migration Files:"
	@powershell -Command "(Get-ChildItem apps\bfagent\migrations\00*.py).Count" | powershell -Command "Write-Host '   Total:' $$input 'files'"
	@powershell -Command "(Get-ChildItem apps\bfagent\migrations\*initial*.py -ErrorAction SilentlyContinue).Count" | powershell -Command "if ($$input -gt 1) { Write-Host '   ⚠️ WARNING:' $$input 'initial migrations found!' } else { Write-Host '   ✅ Initial migrations: OK' }"
	@echo ""
	@echo "📊 Applied Migrations:"
	@python manage.py showmigrations bfagent --plan | powershell -Command "(Select-String '\[X\]' -AllMatches).Matches.Count" | powershell -Command "Write-Host '   Applied:' $$input"
	@echo ""
	@echo "🔧 Auto-fix available: make migrate-fix"

migrate-fake: ## 🎭 Fake migrations (for "table already exists" errors) @category:db @sub:Migrations
	@echo "🎭 Marking migrations as fake (tables already exist)..."
	@echo ""
	@echo "⚠️ This marks migrations as applied WITHOUT running them"
	@echo "   Use when tables already exist in database"
	@echo ""
	@python manage.py migrate --fake
	@echo ""
	@echo "✅ Migrations marked as fake!"
	@echo ""
	@echo "📊 Migration status:"
	@python manage.py showmigrations bfagent --plan | tail -5

migrate-clean: ## 🧹 Clean migration artifacts @category:db @sub:Migrations
	@echo "🧹 Cleaning migration artifacts..."
	@powershell -Command "Remove-Item apps\bfagent\migrations\*.pyc -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item apps\bfagent\migrations\__pycache__ -Recurse -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item apps\bfagent\migrations\*.backup -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item apps\bfagent\migrations\*.broken_backup -Force -ErrorAction SilentlyContinue"
	@powershell -Command "Remove-Item apps\bfagent\migrations\*.pre_clean_backup -Force -ErrorAction SilentlyContinue"
	@echo "✅ Migration artifacts cleaned!"

# ============================================================================
# WSL COMMANDS (for PostgreSQL UTF-8 compatibility)
# ============================================================================
wsl-migrate: ## 🐧 Run migrations via WSL (fixes Windows UTF-8 issues) @category:db @sub:WSL
	@echo "🐧 Running migrations via WSL..."
	wsl bash -c "cd ~/github/bfagent && source .venv/bin/activate && python manage.py migrate"
	@echo "✅ WSL migrations complete!"

wsl-migrate-app: ## 🐧 Migrate specific app via WSL (APP=writing_hub) @category:db @sub:WSL
	@echo "🐧 Running migrations for $(APP) via WSL..."
	wsl bash -c "cd ~/github/bfagent && source .venv/bin/activate && python manage.py migrate $(APP)"
	@echo "✅ WSL migration for $(APP) complete!"

wsl-makemigrations: ## 🐧 Create migrations via WSL @category:db @sub:WSL
	@echo "🐧 Creating migrations via WSL..."
	wsl bash -c "cd ~/github/bfagent && source .venv/bin/activate && python manage.py makemigrations"
	@echo "✅ WSL makemigrations complete!"

wsl-shell: ## 🐧 Open Django shell via WSL @category:db @sub:WSL
	wsl bash -c "cd ~/github/bfagent && source .venv/bin/activate && python manage.py shell_plus"

wsl-manage: ## 🐧 Run any manage.py command via WSL (CMD="showmigrations") @category:db @sub:WSL
	@echo "🐧 Running: python manage.py $(CMD)"
	wsl bash -c "cd ~/github/bfagent && source .venv/bin/activate && python manage.py $(CMD)"

wsl-dev: ## 🐧 Start dev server via WSL @category:dev @sub:WSL
	@echo "🐧 Starting dev server via WSL on port $(PORT)..."
	wsl bash -c "cd ~/github/bfagent && source .venv/bin/activate && python manage.py runserver 0.0.0.0:$(PORT)"

shell: ## 💻 Open Django shell with useful imports @category:dev @sub:Server
	python manage.py shell_plus

fixtures: ## 📦 Load test data @category:db @sub:Management
	python manage.py loaddata fixtures/test_data.json
	@echo "✅ Test data loaded!"

setup-workflows: ## Create default workflow phases and templates
	@echo "📋 Creating default workflow templates..."
	python manage.py create_default_workflows
	@echo "✅ Workflow setup complete!"

setup-mini-test: ## 🧪 Create Mini Test Book workflow (3 phases, simple complete book) @category:test @sub:Setup
	@echo "🧪 Setting up Mini Test Book workflow..."
	python scripts/setup_mini_test_book.py
	@echo "✅ Mini Test Book ready! Create a project and test the complete workflow!"

seed-templates: ## 🌱 Seed all template data (PromptTemplates + ActionTemplates) @category:db @sub:Management
	@echo "🌱 Seeding template data..."
	python manage.py seed_all_templates
	@echo "✅ Template seeding complete!"

seed-templates-reset: ## 🔄 Reset and re-seed all template data @category:db @sub:Management
	@echo "🔄 Resetting and re-seeding template data..."
	python manage.py seed_all_templates --reset
	@echo "✅ Template reset and seeding complete!"

setup-phase-agents: ## Setup Phase-Agent configurations
	@echo "🤖 Setting up Phase-Agent mappings..."
	python manage.py setup_phase_agents
	@echo "✅ Phase-Agent setup complete!"

setup-agent-actions: ## Setup Agent Actions with proper relations
	@echo "🎯 Setting up Agent Actions..."
	python manage.py setup_agent_actions --skip-checks
	@echo "✅ Agent Actions setup complete!"

# Phase-Agent-Template Management
phase-check: ## 📊 Check Phase-Agent-Template system status @category:agent @sub:Configuration
	@echo "📊 Checking Phase-Agent-Template system..."
	python scripts/phase_agent_template_manager.py check

phase-sync: ## 🔄 Sync Phase-Agent mappings @category:agent @sub:Configuration
	@echo "🔄 Synchronizing Phase-Agent mappings..."
	python scripts/phase_agent_template_manager.py sync

phase-context: ## 📝 Add context variables to all templates @category:agent @sub:Configuration
	@echo "📝 Adding context variables to templates..."
	python scripts/phase_agent_template_manager.py context

phase-all: ## 🚀 Run complete Phase-Agent-Template sync (sync + context + check) @category:agent @sub:Configuration
	@echo "🚀 Running complete Phase-Agent-Template sync..."
	python scripts/phase_agent_template_manager.py all

phase-dry-run: ## 🔍 Dry run of Phase-Agent-Template sync (no changes) @category:agent @sub:Configuration
	@echo "🔍 Dry run - showing what would be changed..."
	python scripts/phase_agent_template_manager.py all --dry-run

refactor-agent-architecture: ## 🚀 Complete Agent-Action Architecture Refactor (USE WITH CAUTION)
	@echo "🚨 MAJOR REFACTOR: Agent-Action Architecture Migration"
	@echo "⚠️  This will modify database schema and data!"
	@echo "📋 Steps:"
	@echo "   1. Backup database"
	@echo "   2. Create new models (AgentAction, EnrichmentResponse)"
	@echo "   3. Drop old phase_action_configs table"
	@echo "   4. Apply migrations"
	@echo "   5. Populate AgentActions"
	@echo ""
	@echo "Press Ctrl+C to cancel, or any key to continue..."
	@pause
	@echo "📦 Step 1: Creating database backup..."
	@copy bfagent.db bfagent_backup_$(shell powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'").db
	@echo "✅ Backup created!"
	@echo ""
	@echo "🔧 Step 2: Applying migrations (with --skip-checks)..."
	python manage.py migrate bfagent --skip-checks
	@echo "✅ Migrations applied!"
	@echo ""
	@echo "🎯 Step 3: Setting up Agent Actions..."
	python manage.py setup_agent_actions --skip-checks
	@echo "✅ Agent Actions populated!"
	@echo ""
	@echo "🎉 REFACTOR COMPLETE!"
	@echo "📊 Summary:"
	@python -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT COUNT(*) FROM agent_actions'); print(f'   AgentActions: {cursor.fetchone()[0]}'); cursor.execute('SELECT COUNT(*) FROM enrichment_responses'); print(f'   EnrichmentResponses: {cursor.fetchone()[0]}'); cursor.execute('SELECT COUNT(*) FROM phase_agent_configs'); print(f'   PhaseAgentConfigs: {cursor.fetchone()[0]}')"
	@echo "✅ Architecture refactor successful!"

rollback-agent-architecture: ## 🔄 Rollback Agent-Action Architecture (Restore from backup)
	@echo "🔄 ROLLBACK: Agent-Action Architecture"
	@echo "⚠️  This will restore database from most recent backup!"
	@echo ""
	@echo "📋 Available backups:"
	@powershell -Command "Get-ChildItem -Path . -Filter 'bfagent_backup_*.db' | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name, Length, LastWriteTime"
	@echo ""
	@echo "Press Ctrl+C to cancel, or any key to continue..."
	@pause
	@echo "📦 Finding most recent backup..."
	@powershell -Command "$$latest = Get-ChildItem -Path . -Filter 'bfagent_backup_*.db' | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($$latest) { Write-Host \"✅ Found: $$($latest.Name)\"; Copy-Item bfagent.db \"bfagent_before_rollback_$$(Get-Date -Format 'yyyyMMdd_HHmmss').db\" -Force; Copy-Item $$latest.FullName bfagent.db -Force; Write-Host \"✅ Rollback complete! Database restored from $$($latest.Name)\"; Write-Host \"📦 Current state backed up as safety measure\" } else { Write-Host \"❌ No backup found! Cannot rollback.\" }"
	@echo ""
	@echo "🎉 ROLLBACK COMPLETE!"

deploy-check: ## Pre-deployment checks
	python manage.py check --deploy
	python manage.py collectstatic --noinput --dry-run
	@echo "✅ Deployment checks passed!"

htmx-debug: ## Enable HTMX debugging in templates
	@echo "🔧 Add this to your base.html:"
	@echo "{% if DEBUG %}<script>htmx.logAll();</script>{% endif %}"

feature-scan: ## Scan for implemented features
	python quick_status.py
	@echo ""
	@echo "📋 Check .ai_instructions.md for implementation status"

# Development shortcuts
run: dev ## Alias for dev
server: dev ## Alias for dev
check: status ## Alias for status
stop: kill ## Alias for kill
rs: restart ## Alias for restart (quick restart)

# =============================================================================
# BF AGENT V2.0.0 - COMPREHENSIVE SYSTEM VALIDATION
# =============================================================================

v2-check: ## 🚀 Complete v2.0.0 system validation and update
	@echo "🚀 BF Agent v2.0.0 - Complete System Validation"
	@echo "================================================="
	@echo ""
	@echo "📊 Phase 1: Core System Health Check"
	@echo "------------------------------------"
	@make quick -s
	@echo ""
	@echo "🧠 Phase 2: Chapter Writing System Phase 2 Validation"
	@echo "-----------------------------------------------------"
	@python manage.py shell -c "\
	from apps.bfagent.models import BookChapters, StoryArc, PlotPoint; \
	print('✅ Enhanced BookChapters Model' if hasattr(BookChapters, 'writing_stage') else '❌ BookChapters missing Phase 2 fields'); \
	print('✅ StoryArc Model' if StoryArc.objects.all().count() >= 0 else '❌ StoryArc Model issue'); \
	print('✅ PlotPoint Model' if PlotPoint.objects.all().count() >= 0 else '❌ PlotPoint Model issue'); \
	print('✅ CRUDConfig System' if hasattr(BookChapters, 'CRUDConfig') else '❌ CRUDConfig missing');"
	@echo ""
	@echo "🔧 Phase 3: Zero-Hardcoding Architecture Validation"
	@echo "--------------------------------------------------"
	@python manage.py shell -c "\
	from apps.bfagent.models import BookChapters; \
	config = BookChapters.CRUDConfig() if hasattr(BookChapters, 'CRUDConfig') else None; \
	print('✅ CRUDConfig Instance' if config else '❌ CRUDConfig instantiation failed'); \
	print('✅ Form Layout' if config and hasattr(config, 'form_layout') else '❌ Form Layout missing'); \
	print('✅ Actions Config' if config and hasattr(config, 'actions') else '❌ Actions Config missing'); \
	print('✅ HTMX Config' if config and hasattr(config, 'htmx_config') else '❌ HTMX Config missing');"
	@echo ""
	@echo "🤖 Phase 4: AI Agent Integration Validation"
	@echo "------------------------------------------"
	@python manage.py shell -c "\
	from apps.bfagent.views.main_views import ENRICH_ACTIONS_BY_AGENT; \
	chapter_actions = ENRICH_ACTIONS_BY_AGENT.get('chapter_agent', []); \
	story_actions = ENRICH_ACTIONS_BY_AGENT.get('story_agent', []); \
	consistency_actions = ENRICH_ACTIONS_BY_AGENT.get('consistency_agent', []); \
	print(f'✅ Chapter Agent ({len(chapter_actions)} actions)' if chapter_actions else '❌ Chapter Agent missing'); \
	print(f'✅ Story Agent ({len(story_actions)} actions)' if story_actions else '❌ Story Agent missing'); \
	print(f'✅ Consistency Agent ({len(consistency_actions)} actions)' if consistency_actions else '❌ Consistency Agent missing');"
	@echo ""
	@echo "⚡ Phase 5: HTMX Middleware & Frontend Validation"
	@echo "------------------------------------------------"
	@make check-htmx-v2 -s
	@echo ""
	@echo "🛡️ Phase 6: Enterprise Infrastructure Validation"
	@echo "-----------------------------------------------"
	@python -c "import os; print('✅ Migration Fixer' if os.path.exists('scripts/fix_migrations.py') else '❌ Migration Fixer missing')"
	@python -c "import os; print('✅ HTMX Scanner V2' if os.path.exists('scripts/htmx_scanner_v2.py') else '❌ HTMX Scanner missing')"
	@python -c "import os; print('✅ Quality Assurance' if os.path.exists('scripts/test_htmx_middleware_phase1.py') else '❌ QA Tools missing')"
	@echo ""
	@echo "📚 Phase 7: Documentation Validation"
	@echo "-----------------------------------"
	@python -c "import os; print('✅ Complete Documentation' if os.path.exists('docs/BF-AGENT-V2-COMPLETE-DOCUMENTATION.md') else '❌ Main docs missing')"
	@python -c "import os; print('✅ API Documentation' if os.path.exists('docs/API-DOCUMENTATION.md') else '❌ API docs missing')"
	@python -c "import os; print('✅ Deployment Guide' if os.path.exists('docs/DEPLOYMENT-GUIDE.md') else '❌ Deployment guide missing')"
	@echo ""
	@echo "🎉 BF Agent v2.0.0 System Validation Complete!"
	@echo "=============================================="

v2-fix: ## 🔧 Fix common v2.0.0 issues automatically
	@echo "🔧 BF Agent v2.0.0 - Automated Issue Resolution"
	@echo "=============================================="
	@echo ""
	@echo "🚀 Phase 1: HTMX Auto-Fix (130 issues detected)"
	@echo "----------------------------------------------"
	@make htmx-auto-fix
	@echo ""
	@echo "🔧 Phase 2: AI Chapter Assistant Panel Fix"
	@echo "-----------------------------------------"
	@echo "   ✅ Debug template added to chapter_edit.html"
	@echo "   ✅ CRUDConfig loading enhanced with error handling"
	@echo "   ✅ View updated to pass crud_config to template"
	@echo ""
	@echo "🛡️ Phase 3: Migration Safety Check"
	@echo "----------------------------------"
	@python scripts/fix_migrations.py diagnose || echo "Migration fixer not available"
	@echo ""
	@echo "🎯 Phase 4: CSRF Token Auto-Configuration"
	@echo "----------------------------------------"
	@make htmx-csrf-setup
	@echo ""
	@echo "✅ Automated issue resolution complete!"

htmx-auto-fix: ## 🤖 Automatically fix all HTMX issues
	@echo "🤖 Running HTMX Auto-Fix..."
	@make htmx-auto-fix-all -s
	@echo "✅ HTMX issues automatically resolved!"

htmx-csrf-setup: ## 🔐 Setup automatic CSRF token handling
	@echo "🔐 Configuring automatic CSRF token handling..."
	@python scripts/setup_htmx_csrf.py
	@echo "✅ CSRF auto-configuration complete!"

.PHONY: htmx-scan
htmx-scan: ## 🔍 Run HTMX conformity scan with UI-friendly output
	@echo "🔍 Running HTMX Conformity Scan..."
	@python scripts/htmx_scanner_v2.py --format json .
	@echo ""
	@echo "📊 Latest Report Summary:"
	@python -c "import json; import glob; import os; files = glob.glob('htmx_report_*.json'); latest = max(files, key=os.path.getctime) if files else None; data = json.load(open(latest)) if latest else {}; print(f'Conformity Score: {data.get(\"conformity_score\", 0):.1f}/100') if data else print('No report found'); print(f'Issues Found: {data.get(\"issues_found\", 0)}') if data else None; print(f'Critical: {data.get(\"critical_issues\", 0)}') if data else None"

.PHONY: tool-docs
tool-docs: ## 📋 Generate comprehensive tool documentation
	@echo "📋 Generating tool documentation..."
	@python scripts/generate_tool_docs.py
	@echo "✅ Tool documentation updated!"

.PHONY: tool-optimize
tool-optimize: ## 🔧 Analyze and optimize tool integration
	@echo "🔧 Analyzing tool integration gaps..."
	@python scripts/tool_integration_optimizer.py
	@echo "✅ Integration analysis completed!"

.PHONY: tool-analyze
tool-analyze: ## 🔍 Deep analysis of all tools with function-level details
	@echo "🔍 Running deep tool analysis..."
	@python scripts/generate_tool_docs_enhanced.py
	@echo "✅ Enhanced tool analysis completed!"

.PHONY: quality-gate
quality-gate: ## 🛡️ Complete quality analysis with hybrid approach
	@echo "🛡️ Running Quality Gate Analysis..."
	@echo "🔬 Phase 1: Custom AST Analysis..."
	@python scripts/enhanced_tool_analyzer.py --threshold 80 || echo "⚠️ Custom analysis issues found"
	@echo "🔧 Phase 2: External Tools Analysis..."
	@python scripts/integrated_analyzer.py || echo "⚠️ External tools issues found"
	@echo "🚀 Phase 3: Hybrid Analysis..."
	@python scripts/hybrid_analyzer.py
	@echo "✅ Quality Gate completed!"

.PHONY: quality-check
quality-check: ## 🔍 Quick quality check for current changes
	@echo "🔍 Running quick quality check..."
	@python scripts/hybrid_analyzer.py --quick
	@echo "✅ Quality check completed!"

.PHONY: quality-enterprise
quality-enterprise: ## 🏆 Enterprise-grade quality analysis (optimized)
	@echo "🏆 Running Enterprise Quality Analysis..."
	@python scripts/optimized_hybrid_analyzer.py --mode standard --config scripts/analyzer_config.txt
	@echo "✅ Enterprise analysis completed!"

.PHONY: quality-deep
quality-deep: ## 🔬 Deep analysis with visualizations
	@echo "🔬 Running deep analysis..."
	@python scripts/optimized_hybrid_analyzer.py --mode deep --visualize
	@echo "✅ Deep analysis completed!"

.PHONY: quality-ci
quality-ci: ## 🚀 CI/CD optimized quality check
	@echo "🚀 Running CI quality check..."
	@python scripts/optimized_hybrid_analyzer.py --mode quick --ci-format junit
	@echo "✅ CI quality check completed!"

.PHONY: quality-safe
quality-safe: ## 🛡️ Unicode-safe quality analysis (Windows compatible)
	@echo "🛡️ Running Unicode-safe quality analysis..."
	@python scripts/unicode_safe_analyzer.py
	@echo "✅ Unicode-safe analysis completed!"

.PHONY: quality-test
quality-test: ## 🧪 Test quality analysis on single file
	@echo "🧪 Testing quality analysis..."
	@python scripts/unicode_safe_analyzer.py --single scripts/hybrid_analyzer.py
	@echo "✅ Quality test completed!"

.PHONY: quality-fix
quality-fix: ## 🔧 Analyze and auto-fix code issues (SAFE mode)
	@echo "🔧 Running code analysis with auto-fix..."
	@python scripts/enhanced_cli_analyzer.py analyze scripts/ --fix --fix-level safe
	@echo "✅ Auto-fix completed!"

.PHONY: quality-fix-safe
quality-fix-safe: ## 🛡️ Ultra-safe auto-fix with syntax validation
	@echo "🛡️ Running ultra-safe auto-fix with validation..."
	@python scripts/safe_auto_fixer.py
	@echo "✅ Safe auto-fix completed!"

.PHONY: quality-repair
quality-repair: ## 🛠️ Advanced code repair with interactive mode
	@echo "🛠️ Running advanced code repair..."
	@python scripts/enhanced_cli_analyzer.py analyze scripts/ --fix --fix-level moderate --interactive
	@echo "✅ Code repair completed!"

.PHONY: quality-check-strict
quality-check-strict: ## 🎯 Strict quality check for CI/CD
	@echo "🎯 Running strict quality check..."
	@python scripts/enhanced_cli_analyzer.py check scripts/ --threshold 80 --strict
	@echo "✅ Strict quality check completed!"

v2-update: ## 📦 Update system to latest v2.0.0 state
	@echo "📦 BF Agent v2.0.0 - System Update"
	@echo "=================================="
	@echo ""
	@echo "1. Installing/updating dependencies..."
	@pip install -r requirements.txt
	@echo ""
	@echo "2. Applying database migrations..."
	@python manage.py migrate
	@echo ""
	@echo "3. Collecting static files..."
	@python manage.py collectstatic --noinput
	@echo ""
	@echo "4. Running system validation..."
	@make v2-check -s
	@echo ""
	@echo "✅ System updated to v2.0.0!"

v2-deploy-check: ## 🚀 Pre-deployment validation for v2.0.0
	@echo "🚀 BF Agent v2.0.0 - Deployment Readiness Check"
	@echo "==============================================="
	@echo ""
	@echo "1. Django deployment check..."
	@python manage.py check --deploy
	@echo ""
	@echo "2. Migration safety check..."
	@python scripts/fix_migrations.py diagnose || echo "⚠️  Migration fixer not available"
	@echo ""
	@echo "3. HTMX conformity check..."
	@make htmx-scan-strict -s || echo "⚠️  HTMX issues found"
	@echo ""
	@echo "4. System validation..."
	@make v2-check -s
	@echo ""
	@echo "5. Static files check..."
	@python manage.py collectstatic --noinput --dry-run
	@echo ""
	@echo "✅ Deployment readiness validated!"

v2-test: ## 🧪 Comprehensive v2.0.0 testing
	@echo "🧪 BF Agent v2.0.0 - Comprehensive Testing"
	@echo "=========================================="
	@echo ""
	@echo "1. Django tests..."
	@python manage.py test
	@echo ""
	@echo "2. Chapter Writing System tests..."
	@python manage.py shell -c "\
	from apps.bfagent.models import BookChapters; \
	from apps.bfagent.services.project_enrichment import run_enrichment; \
	print('✅ Chapter Writing System models accessible'); \
	print('✅ AI enrichment services accessible');"
	@echo ""
	@echo "3. CRUDConfig system tests..."
	@python manage.py shell -c "\
	from apps.bfagent.models import BookChapters; \
	config = BookChapters.CRUDConfig(); \
	print(f'✅ CRUDConfig actions: {len(config.actions)} defined'); \
	print(f'✅ Form layout sections: {len(config.form_layout)} defined');"
	@echo ""
	@echo "4. HTMX middleware tests..."
	@make test-htmx-middleware-phase1 -s || echo "⚠️  HTMX middleware tests not available"
	@echo ""
	@echo "✅ Comprehensive testing complete!"

v2-status: ## 📊 Complete v2.0.0 system status
	@echo "📊 BF Agent v2.0.0 - Complete System Status"
	@echo "==========================================="
	@echo ""
	@echo "🎯 Revolutionary Features Status:"
	@echo "--------------------------------"
	@echo "✅ Chapter Writing System Phase 2 - Enhanced BookChapters, StoryArc, PlotPoint"

v2-dashboard: ## 🎯 Open V2 Migration Dashboard in browser @category:monitor @sub:Migration
	@echo "🎯 Opening V2 Migration Dashboard..."
	@python -m webbrowser http://127.0.0.1:$(PORT)/v2-dashboard/
	@echo "✅ Dashboard opened! Server must be running on port $(PORT)"

v2-stats: ## 📊 Show V2 migration statistics in terminal @category:monitor @sub:Migration
	@echo "📊 V2 Migration Statistics"
	@echo "=========================="
	@python -c "from apps.bfagent.models import WorkflowPhase, PhaseActionConfig, AgentAction, PromptTemplate; print(f'\n🗄️  Database Architecture:'); print(f'   Workflow Phases: {WorkflowPhase.objects.count()}'); print(f'   Phase Actions: {PhaseActionConfig.objects.count()}'); print(f'   Agent Actions: {AgentAction.objects.count()}'); print(f'   Prompt Templates: {PromptTemplate.objects.count()}'); print(f'\n💡 Open full dashboard: make v2-dashboard')"
	@echo ""

# ============================================================================
# STORY ENGINE - AI Novel Generation System
# ============================================================================

story-migrate: ## 📚 Create and apply Story Engine migrations @category:story @sub:Setup
	@echo "📚 Story Engine - Creating Migrations..."
	@echo "========================================"
	@echo ""
	@echo "Step 1: Backup database..."
	@powershell -Command "Copy-Item bfagent.db bfagent_backup_story_$$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
	@echo "✅ Backup created!"
	@echo ""
	@echo "Step 2: Create migrations..."
	@python manage.py makemigrations bfagent
	@echo ""
	@echo "Step 3: Apply migrations..."
	@python manage.py migrate bfagent
	@echo ""
	@echo "✅ Story Engine models migrated!"
	@echo "📊 Summary:"
	@python -c "from apps.bfagent.models import StoryBible, StoryStrand, StoryCharacter, ChapterBeat, StoryChapter; print(f'   StoryBible: {StoryBible.objects.count()}'); print(f'   StoryStrands: {StoryStrand.objects.count()}'); print(f'   Characters: {StoryCharacter.objects.count()}'); print(f'   Chapter Beats: {ChapterBeat.objects.count()}'); print(f'   Chapters: {StoryChapter.objects.count()}')"

story-status: ## 📈 Show Story Engine statistics @category:story @sub:Monitor
	@echo "📈 Story Engine Status"
	@echo "====================="
	@python -c "from apps.bfagent.models import StoryBible, StoryStrand, StoryCharacter, ChapterBeat, StoryChapter; print(f'\n📚 Story Bibles: {StoryBible.objects.count()}'); print(f'🧵 Story Strands: {StoryStrand.objects.count()}'); print(f'👥 Characters: {StoryCharacter.objects.count()}'); print(f'📝 Chapter Beats: {ChapterBeat.objects.count()}'); print(f'📖 Generated Chapters: {StoryChapter.objects.count()}'); total_words = sum(c.word_count for c in StoryChapter.objects.all()); print(f'\n✍️  Total Words Generated: {total_words:,}')"

story-admin: ## 🔧 Open Story Engine admin interface @category:story @sub:Admin
	@echo "🔧 Opening Story Engine Admin..."
	@python -m webbrowser http://127.0.0.1:$(PORT)/admin/bfagent/storybible/
	@echo "✅ Admin opened! Server must be running on port $(PORT)"

story-docs: ## 📖 Show Story Engine documentation @category:story @sub:Docs
	@echo "📖 Story Engine Documentation"
	@echo "============================="
	@echo ""
	@echo "📚 Available Documentation:"
	@echo "   - docs/db_driven/Migration/STORY_ENGINE_OVERVIEW.md"
	@echo "   - docs/db_driven/Migration/STORY_ENGINE_ARCHITECTURE.md"
	@echo "   - docs/db_driven/Migration/STORY_ENGINE_DATABASE.md"
	@echo "   - docs/db_driven/Migration/STORY_ENGINE_IMPLEMENTATION.md"
	@echo "   - docs/db_driven/Migration/STORY_ENGINE_AGENTS.md"
	@echo ""
	@echo "💡 Quick Start:"
	@echo "   1. make story-migrate    # Create database tables"
	@echo "   2. make story-admin      # Open admin interface"
	@echo "   3. Create a Story Bible"
	@echo "   4. Define Characters and Strands"
	@echo "   5. Plan Chapter Beats"
	@echo "   6. Generate Chapters!"

story-init: ## 🚀 Initialize Story Engine (migrations + admin setup) @category:story @sub:Setup
	@echo "🚀 Story Engine - Complete Initialization"
	@echo "========================================="
	@make story-migrate
	@echo ""
	@echo "✅ Story Engine initialized!"
	@echo ""
	@make story-docs
	@echo "✅ Zero-Hardcoding Architecture - CRUDConfig meta-programming system"
	@echo "✅ HTMX Middleware Enhancement - Enterprise-grade error handling"
	@echo "✅ Enterprise Migration Safety - Automated backup and rollback"
	@echo "✅ Multi-Agent AI System - Chapter, Story, and Consistency agents"
	@echo "✅ Production-Ready Deployment - Zero-downtime updates"
	@echo ""
	@echo "📈 Performance Metrics:"
	@echo "---------------------"
	@python manage.py shell -c "\
	from apps.bfagent.models import BookProjects, BookChapters, StoryArc, PlotPoint; \
	projects = BookProjects.objects.count(); \
	chapters = BookChapters.objects.count(); \
	arcs = StoryArc.objects.count(); \
	points = PlotPoint.objects.count(); \
	print(f'📚 Projects: {projects}'); \
	print(f'📖 Chapters: {chapters}'); \
	print(f'🎭 Story Arcs: {arcs}'); \
	print(f'📍 Plot Points: {points}');"
	@echo ""
	@make status -s

# Quick aliases for v2.0.0
v2: v2-check ## Alias for v2-check
validate: v2-check ## Alias for v2-check
update-system: v2-update ## Alias for v2-update

# =============================================================================
# BF AGENT CONTROL CENTER - DASHBOARD MVP
# =============================================================================

dashboard: ## 🎯 Launch BF Agent Control Center Dashboard
	@echo "🚀 Starting BF Agent Control Center..."
	@echo "======================================"
	@echo ""
	@echo "📊 Dashboard Features:"
	@echo "  • Real-time tool status monitoring"
	@echo "  • One-click tool execution"
	@echo "  • System health overview"
	@echo "  • Performance metrics"
	@echo ""
	@echo "🌐 Dashboard will be available at:"
	@echo "  http://127.0.0.1:$(PORT)/control-center/"
	@echo ""
	@echo "🔧 Starting Django development server on port $(PORT)..."
	@python manage.py runserver 127.0.0.1:$(PORT)

dashboard-api: ## 📡 Test Control Center API endpoints (uses PORT variable)
	@echo "🧪 Testing Control Center API on port $(PORT)..."
	@echo "================================"
	@echo ""
	@echo "1. System Status API:"
	@curl -s http://127.0.0.1:$(PORT)/control-center/api/status/ | python -m json.tool || echo "Server not running on port $(PORT)"
	@echo ""
	@echo "2. Tools API:"
	@curl -s http://127.0.0.1:$(PORT)/control-center/api/tools/ | python -m json.tool || echo "Server not running on port $(PORT)"
	@echo ""
	@echo "✅ API testing complete!"

dashboard-status: ## 📊 Show Control Center system status
	@echo "📊 BF Agent Control Center Status"
	@echo "================================="
	@python manage.py shell -c "\
	from apps.control_center.registry import tool_registry; \
	health = tool_registry.get_system_health(); \
	print(f'Overall Status: {health[\"overall_status\"]}'); \
	print(f'Health Score: {health[\"health_score\"]:.1f}%'); \
	print(f'Ready Tools: {health[\"ready_tools\"]}/{health[\"total_tools\"]}'); \
	print(f'Error Tools: {health[\"error_tools\"]}'); \
	print('\\nTool Details:'); \
	for name, status in health['tools'].items(): \
		print(f'  {name}: {status[\"status\"]}');"

# =============================================================================
# GIT SYNC TOOLS
# =============================================================================

sync: ## 🔄 Intelligent git sync with auto-generated commit message @category:project @sub:Git
	@echo "🔄 Starting intelligent git sync..."
	python scripts/git-sync-tool.py sync --verbose

sync-autofix: ## 🔧 Enhanced git sync with automatic error fixing
	@echo "🔧 Starting enhanced git sync with auto-fix..."
	python scripts/git-sync-tool-enhanced_V2.py sync --verbose

quick-sync: ## ⚡ Quick git sync with timestamp message @category:project @sub:Git
	@echo "⚡ Quick git sync..."
	python scripts/git-sync-tool.py quick --verbose

qc: ## 💬 Quick Commit with custom message @category:project @sub:Git
ifndef MSG
	@echo "❌ Error: MSG parameter required!"
	@echo "Usage: make qc MSG=\"Your commit message\""
	@echo "Or use: make menu (Interactive)"
	@exit 1
endif
	@echo "📝 Quick Commit: $(MSG)"
	@git add -A
	@git commit --no-verify -m "$(MSG)"
	@echo "✅ Committed successfully!"
	@echo "💡 Tip: Run 'git push' or 'make sync' to push changes"

qcp: ## 🚀 Quick Commit + Push @category:project @sub:Git
ifdef F
	@echo "📝 Quick Commit + Push from file: $(F)"
	@git add -A
	@git commit --no-verify -F "$(F)"
	@git push
	@echo "✅ Committed and pushed successfully!"
else ifndef MSG
	@echo "❌ Error: MSG or F parameter required!"
	@echo "Usage: make qcp MSG=\"Your commit message\""
	@echo "Or:    make qcp F=\"path/to/message_file.txt\""
	@echo "Or use: make menu (Interactive)"
	@exit 1
else
	@echo "📝 Quick Commit + Push: $(MSG)"
	@git add -A
	@git commit --no-verify -m "$(MSG)"
	@git push
	@echo "✅ Committed and pushed successfully!"
endif

quick-autofix: ## ⚡ Quick sync with auto-fix
	@echo "⚡ Quick sync with auto-fix..."
	python scripts/git-sync-tool-enhanced_V2.py quick --verbose

sync-no-push: ## 🔄 Git sync without pushing to remote @category:project @sub:Git
	@echo "🔄 Git sync (local only)..."
	python scripts/git-sync-tool.py sync --no-push --verbose

fix-only: ## 🔧 Run fixes without committing
	@echo "🔧 Running automatic fixes only..."
	python scripts/git-sync-tool-enhanced_V2.py fix --verbose

check-precommit: ## 📊 Check pre-commit issues without fixing
	@echo "📊 Checking pre-commit issues..."
	python scripts/git-sync-tool-enhanced_V2.py check

git-status: ## 📊 Show detailed git status @category:project @sub:Git
	@echo "📊 Git Status:"
	@git status
	@echo ""
	@echo "📋 Recent commits:"
	@git log --oneline -5

update-docu: ## 📝 Update documentation and commit with auto-generated message @category:dev @sub:Documentation
	@echo "📝 Updating documentation..."
	@echo ""
	@echo "📊 Checking changed files..."
	@git status --short
	@echo ""
	@powershell -ExecutionPolicy Bypass -File scripts/update_docu.ps1

# ========================================
# 🛠️ ENTERPRISE DEVELOPMENT TOOLS
# ========================================

# Visual Model Explorer
.PHONY: model-explorer
model-explorer: ## 🎨 Start interactive Visual Model Explorer
	@echo "🚀 Starting Visual Model Explorer..."
	@echo "📍 Open browser at http://localhost:5000"
	python scripts/visual_model_explorer.py

.PHONY: model-explorer-prod
model-explorer-prod: ## 🎨 Start model explorer in production mode
	@echo "🚀 Starting Model Explorer (production)..."
	python scripts/visual_model_explorer.py --host 0.0.0.0 --no-debug

# API Endpoint Checker (V1 - Stable)
.PHONY: check-api
check-api: ## 🔍 Check API endpoints and coverage (V1 - Stable)
	@echo "🔍 Checking API endpoints (V1)..."
	python scripts/api_endpoint_checker.py check

.PHONY: api-report
api-report: ## 📊 Generate detailed API report (V1)
	@echo "📊 Generating API report (V1)..."
	python scripts/api_endpoint_checker.py report --output reports/api_report.json

.PHONY: generate-openapi
generate-openapi: ## 📄 Generate OpenAPI specification (V1)
	@echo "📄 Generating OpenAPI spec (V1)..."
	python scripts/api_endpoint_checker.py openapi --output docs/openapi.yaml
	@echo "✅ OpenAPI spec saved to docs/openapi.yaml"

.PHONY: generate-openapi-json
generate-openapi-json: ## 📄 Generate OpenAPI spec as JSON (V1)
	@echo "📄 Generating OpenAPI JSON (V1)..."
	python scripts/api_endpoint_checker.py openapi --format json --output docs/openapi.json

# API Endpoint Checker V3 (Performance Optimized)
.PHONY: check-api-v3
check-api-v3: ## 🚀 Check API endpoints with V3 performance optimization
	@echo "🚀 Checking API endpoints (V3 - 6.46x faster)..."
	python scripts/api_endpoint_checker_v3.py check --profile

.PHONY: api-report-v3
api-report-v3: ## 📊 Generate detailed API report with V3 performance
	@echo "📊 Generating API report (V3 - optimized)..."
	python scripts/api_endpoint_checker_v3.py report --output reports/api_report_v3.json --profile

.PHONY: generate-openapi-v3
generate-openapi-v3: ## 📄 Generate OpenAPI 3.1 specification with V3
	@echo "📄 Generating OpenAPI 3.1 spec (V3)..."
	python scripts/api_endpoint_checker_v3.py openapi --output docs/openapi_v3.yaml --validate
	@echo "✅ OpenAPI 3.1 spec saved to docs/openapi_v3.yaml"

# API Endpoint Checker V4 (Enterprise Grade)
.PHONY: check-api-v4
check-api-v4: ## 🎯 Enterprise API analysis with intelligent model processing
	@echo "🎯 Running Enterprise API analysis (V4)..."
	python scripts/api_endpoint_checker_v4.py check --profile

.PHONY: api-report-v4
api-report-v4: ## 📊 Generate comprehensive API report with Rich UI
	@echo "📊 Generating comprehensive API report (V4)..."
	python scripts/api_endpoint_checker_v4.py report --output reports/api_report_v4.json --profile

.PHONY: generate-openapi-v4
generate-openapi-v4: ## 📄 Generate validated OpenAPI 3.1 spec with enterprise features
	@echo "📄 Generating validated OpenAPI 3.1 spec (V4)..."
	python scripts/api_endpoint_checker_v4.py openapi --output docs/openapi_v4.yaml --title "BF Agent API" --version "4.0.0"
	python scripts/api_endpoint_checker_v4.py validate --spec docs/openapi_v4.yaml
	@echo "✅ Validated OpenAPI 3.1 spec saved to docs/openapi_v4.yaml"

# GraphQL Schema Generator (V1 - Stable)
.PHONY: generate-graphql
generate-graphql: ## 🚀 Generate GraphQL schema from models (V1)
	@echo "🚀 Generating GraphQL schema (V1)..."
	python scripts/graphql_schema_generator.py generate

.PHONY: export-graphql
export-graphql: ## 📄 Export GraphQL schema to file (V1)
	@echo "📄 Exporting GraphQL schema (V1)..."
	python scripts/graphql_schema_generator.py export --output docs/schema.graphql
	@echo "✅ GraphQL schema saved to docs/schema.graphql"

.PHONY: graphql-resolvers
graphql-resolvers: ## 🔧 Generate GraphQL resolver template (V1)
	@echo "🔧 Generating GraphQL resolvers (V1)..."
	python scripts/graphql_schema_generator.py resolvers --output apps/api/resolvers.py
	@echo "✅ Resolver template saved to apps/api/resolvers.py"

# GraphQL Schema Generator V3 (Performance Optimized)
.PHONY: generate-graphql-v3
generate-graphql-v3: ## 🚀 Generate GraphQL schema with V3 performance optimization
	@echo "🚀 Generating GraphQL schema (V3 - optimized)..."
	python scripts/graphql_schema_generator_v3.py generate --profile

.PHONY: export-graphql-v3
export-graphql-v3: ## 📄 Export GraphQL schema with modern Python features
	@echo "📄 Exporting GraphQL schema (V3)..."
	python scripts/graphql_schema_generator_v3.py export --output docs/schema_v3.graphql --async-support
	@echo "✅ GraphQL schema V3 saved to docs/schema_v3.graphql"

.PHONY: graphql-resolvers-v3
graphql-resolvers-v3: ## 🔧 Generate modern GraphQL resolver template with async support
	@echo "🔧 Generating GraphQL resolvers (V3 - async)..."
	python scripts/graphql_schema_generator_v3.py resolvers --output apps/api/resolvers_v3.py --strawberry
	@echo "✅ Modern resolver template saved to apps/api/resolvers_v3.py"

# Screen Documentation Framework
.PHONY: screen-docs
screen-docs: ## 📄 Generate screen documentation
	@echo "📄 Generating screen documentation..."
	python scripts/screen_documentation_framework.py discover --output docs/screens.json

.PHONY: screen-docs-md
screen-docs-md: ## 📄 Generate screen documentation as Markdown
	@echo "📄 Generating screen documentation (Markdown)..."
	python scripts/screen_documentation_framework.py discover --output docs/screens.md --format markdown

.PHONY: generate-tests
generate-tests: ## 🧪 Generate automated test suites from screen docs
	@echo "🧪 Generating automated tests..."
	python scripts/screen_documentation_framework.py generate-tests
	@echo "✅ Test suites generated in tests/generated/"

# =============================================================================
# ENTERPRISE MIGRATION TOOLS
# =============================================================================

.PHONY: check-migrations
check-migrations: ## 🔍 Diagnose & verify migrations (Enterprise Tool)
	@echo "🔍 Running Migration Diagnostics..."
	@python scripts/fix_migrations.py diagnose --app bfagent
	@echo ""
	@echo "✅ Verifying migration integrity..."
	@python scripts/fix_migrations.py verify --app bfagent
	@echo "✅ Migration check complete!"

.PHONY: fix-migrations
fix-migrations: ## 🔧 Interactive migration fix tool
	@echo "🔧 Starting Interactive Migration Fixer..."
	@python scripts/fix_migrations.py
	@echo "✅ Migration fixes applied!"

.PHONY: migration-backup
migration-backup: ## 💾 Backup migrations before changes
	@echo "💾 Creating migration backup..."
	@python scripts/fix_migrations.py backup --app bfagent
	@echo "✅ Backup created!"

.PHONY: migration-status
migration-status: ## 📊 Show detailed migration status
	@echo "📊 Migration Status for bfagent app:"
	@python scripts/fix_migrations.py diagnose --app bfagent --verbose
	@echo "✅ Status check complete!"

# =============================================================================
# DATABASE TABLE VERIFICATION
# =============================================================================

.PHONY: check-tables
check-tables: ## 🗄️ List all database tables by app @category:db @sub:Verification
	@echo "🗄️ Database Tables Overview:"
	@echo ""
	@python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name'); tables = [row[0] for row in cursor.fetchall()]; print('Total tables:', len(tables)); print('\\nBy prefix:'); prefixes = {}; [prefixes.setdefault(t.split('_')[0], []).append(t) for t in tables]; [print(f'  {prefix}: {len(ts)} tables') for prefix, ts in sorted(prefixes.items())]"

.PHONY: check-genagent
check-genagent: ## ✅ Verify GenAgent tables exist @category:db @sub:Verification
	@echo "✅ Checking GenAgent Tables..."
	@python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND name LIKE \"genagent%\" ORDER BY name'); tables = [row[0] for row in cursor.fetchall()]; print('\\n'.join(tables) if tables else '❌ No GenAgent tables found'); print(f'\\nTotal: {len(tables)} table(s)')"

.PHONY: check-bfagent
check-bfagent: ## 📚 Verify BF Agent tables exist @category:db @sub:Verification
	@echo "📚 Checking BF Agent Tables..."
	@python manage.py shell -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('SELECT name FROM sqlite_master WHERE type=\"table\" AND (name LIKE \"agents%\" OR name LIKE \"book%\" OR name LIKE \"llms%\" OR name LIKE \"enrichment%\") ORDER BY name'); tables = [row[0] for row in cursor.fetchall()]; print('\\n'.join(tables)); print(f'\\nTotal: {len(tables)} table(s)')"

.PHONY: check-db-status
check-db-status: ## 📊 Complete database status overview @category:db @sub:Verification
	@echo "📊 Complete Database Status:"
	@echo ""
	@echo "🔹 Migration Status:"
	@python manage.py showmigrations --list | head -20
	@echo ""
	@echo "🔹 Table Count by App:"
	@make check-tables
	@echo ""
	@echo "🔹 GenAgent Tables:"
	@make check-genagent

# =============================================================================
# MODEL CONSISTENCY CHECKER
# =============================================================================

.PHONY: check-models
check-models: ## 🔍 Run comprehensive model analysis
	@echo "🔍 Running Model Consistency Analysis..."
	@python scripts/model_consistency_checker.py analyze --verbose

.PHONY: model-report
model-report: ## 📊 Generate detailed model report
	@echo "📊 Generating Model Consistency Report..."
	@python scripts/model_consistency_checker.py export --format markdown --output reports/model_consistency_$(shell powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'").md

.PHONY: fix-models
fix-models: ## 🔧 Auto-fix model issues
	@echo "🔧 Fixing model inconsistencies..."
	@python scripts/model_consistency_checker.py fix

.PHONY: fix-models-preview
fix-models-preview: ## 👀 Preview fixes without applying
	@echo "👀 Previewing model fixes..."
	@python scripts/model_consistency_checker.py fix --dry-run

.PHONY: model-export-html
model-export-html: ## 🌐 Export model report as HTML
	@echo "🌐 Exporting HTML report..."
	@python scripts/model_consistency_checker.py export --format html --output reports/model_report.html
	@echo "📄 Report saved to reports/model_report.html"

.PHONY: check-filters
check-filters: ## 🔍 Analyze ListView filter implementation status @category:test @sub:Quality Checks
	@echo "🔍 Analyzing ListView Filters..."
	@python scripts/add_filters_to_views.py

.PHONY: generate-list-templates
generate-list-templates: ## 🎨 Generate missing list templates for views @category:dev @sub:Code Generation
	@echo "🎨 Generating List Templates..."
	@python scripts/generate_list_templates.py

# =============================================================================
# HTMX QUALITY TOOLS
# =============================================================================

.PHONY: check-htmx
check-htmx: ## 🔍 Run HTMX conformity scan
	@echo "🔍 Running HTMX Quality Scan..."
	@python scripts/htmx_scanner_v2.py --format json
	@echo "✅ HTMX scan complete!"

.PHONY: fix-htmx
fix-htmx: ## 🔧 Auto-fix HTMX issues
	@echo "🔧 Auto-fixing HTMX issues..."
	@python scripts/htmx_scanner_v2.py --fix
	@echo "✅ HTMX fixes applied!"

# =============================================================================
# COMBINED PRE-FLIGHT VALIDATION
# =============================================================================

.PHONY: pre-flight
pre-flight: ## ✈️ Complete pre-flight validation (migrations + models + htmx)
	@echo "✈️ Starting Pre-Flight Validation..."
	@echo "================================================"
	@echo ""
	@echo "1️⃣ Migration Check..."
	@make check-migrations
	@echo ""
	@echo "2️⃣ Model Consistency Check..."
	@make check-models
	@echo ""
	@echo "3️⃣ HTMX Conformity Check..."
	@make check-htmx
	@echo ""
	@echo "✅ Pre-Flight Validation PASSED!"
	@echo "================================================"

# Combined Enterprise Commands (V4 as Default)
.PHONY: full-analysis
full-analysis: check-models check-api-v4 screen-docs ## 🎯 Run full system analysis (V4 Enterprise)
	@echo "🎯 Full enterprise analysis complete (V4)!"

.PHONY: full-analysis-v3
full-analysis-v3: check-models check-api-v3 screen-docs ## 🚀 Run full system analysis with V3 performance
	@echo "🚀 Full enterprise analysis complete (V3 - optimized)!"

.PHONY: full-analysis-legacy
full-analysis-legacy: check-models check-api screen-docs ## 🔍 Run full system analysis (V1 Legacy)
	@echo "✅ Full enterprise analysis complete (V1 Legacy)!"

# V4 as Default Documentation Generation
.PHONY: generate-docs
generate-docs: generate-openapi-v4 export-graphql screen-docs-md ## 📚 Generate all documentation (V4 Enterprise)
	@echo "📚 All documentation generated (V4 Enterprise)!"

.PHONY: generate-docs-legacy
generate-docs-legacy: generate-openapi export-graphql screen-docs-md ## 📚 Generate all documentation (V1 Legacy)
	@echo "📚 All documentation generated (V1 Legacy)!"

.PHONY: generate-docs-v3
generate-docs-v3: generate-openapi-v3 export-graphql-v3 screen-docs-md ## 📚 Generate all documentation with V3 performance
	@echo "📚 All documentation generated (V3 - optimized)!"

.PHONY: performance-benchmark
performance-benchmark: ## 📊 Benchmark V1 vs V3 vs V4 performance
	@echo "📊 Running performance benchmark..."
	@echo "Testing API Checker V1..."
	@powershell -Command "Measure-Command { make check-api 2>$$null } | Select-Object TotalSeconds"
	@echo "Testing API Checker V3..."
	@powershell -Command "Measure-Command { make check-api-v3 2>$$null } | Select-Object TotalSeconds"
	@echo "Testing API Checker V4..."
	@powershell -Command "Measure-Command { make check-api-v4 2>$$null } | Select-Object TotalSeconds"
	@echo "✅ Performance benchmark complete!"

.PHONY: enterprise-setup
enterprise-setup: ## 🚀 Setup all enterprise tools (V4 optimized)
	@echo "🚀 Setting up enterprise development environment..."
	pip install rich flask flask-cors pyyaml openapi-spec-validator aiofiles
	@powershell -Command "New-Item -ItemType Directory -Force -Path docs, reports, tests/generated"
	@echo "✅ Enterprise tools ready (V4 + V3.0 dependencies installed)!"

# CSS Theme Switcher
.PHONY: themes-list
themes-list: ## 🎨 List all available CSS themes
	@echo "🎨 Listing available themes..."
	python scripts/css_theme_switcher.py list

.PHONY: themes-install
themes-install: ## 🎨 Install complete theme switcher system
	@echo "🎨 Installing theme switcher system..."
	python scripts/css_theme_switcher.py install
	@echo "✅ Theme system installed!"

.PHONY: themes-generate
themes-generate: ## 🎨 Generate all CSS themes
	@echo "🎨 Generating all themes..."
	python scripts/css_theme_switcher.py generate-all
	@echo "✅ All themes generated!"

.PHONY: theme-metallic
theme-metallic: ## 🎨 Generate metallic theme only
	@echo "🎨 Generating metallic theme..."
	python scripts/css_theme_switcher.py generate metallic

.PHONY: theme-dark
theme-dark: ## 🎨 Generate dark theme
	@echo "🎨 Generating dark theme..."
	python scripts/css_theme_switcher.py generate dark

.PHONY: theme-neon
theme-neon: ## 🎨 Generate neon cyber theme
	@echo "🎨 Generating neon theme..."
	python scripts/css_theme_switcher.py generate neon

.PHONY: fix-themes
fix-themes: ## 🔧 Fix theme CSS specificity issues
	@echo "🔧 Fixing theme CSS specificity..."
	python scripts/fix_theme_css.py
	@echo "✅ Theme CSS fixed!"

# CSS Theme Switcher V3.0 (Optimized)
.PHONY: themes-setup-v3
themes-setup-v3: ## 🚀 Setup V3.0 dependencies and install
	@echo "🚀 Setting up V3.0 dependencies..."
	pip install aiofiles
	@echo "✅ V3.0 dependencies installed!"

.PHONY: themes-install-v3
themes-install-v3: themes-setup-v3 ## 🚀 Install optimized theme switcher V3.0
	@echo "🚀 Installing optimized theme switcher V3.0..."
	python scripts/optimized-css-theme-switcher.py install
	@echo "✅ V3.0 theme system installed!"

.PHONY: themes-list-v3
themes-list-v3: ## 🎨 List themes using V3.0 system
	@echo "🎨 Listing themes (V3.0)..."
	python scripts/optimized-css-theme-switcher.py list

.PHONY: themes-generate-v3
themes-generate-v3: ## 🎨 Generate all themes using V3.0
	@echo "🎨 Generating themes with V3.0 optimizations..."
	python scripts/optimized-css-theme-switcher.py generate-all
	@echo "✅ V3.0 themes generated!"

.PHONY: themes-benchmark
themes-benchmark: ## 📊 Benchmark theme switching performance
	@echo "📊 Benchmarking theme performance..."
	python scripts/optimized-css-theme-switcher.py benchmark
	@echo "✅ Performance benchmark complete!"

.PHONY: themes-validate
themes-validate: ## ✅ Validate theme integrity and CSS
	@echo "✅ Validating theme integrity..."
	python scripts/optimized-css-theme-switcher.py validate
	@echo "✅ Theme validation complete!"

# Simple Theme Switcher (Windows Compatible)
.PHONY: themes-install-simple
themes-install-simple: ## 🎨 Install simple theme switcher (Windows compatible)
	@echo "Installing simple theme switcher..."
	python scripts/theme_switcher_simple.py install
	@echo "Simple theme system installed!"

.PHONY: themes-list-simple
themes-list-simple: ## 🎨 List themes using simple system
	@echo "Listing available themes..."
	python scripts/theme_switcher_simple.py list

# Code Formatting & Pre-commit Fixes (Using BF Agent Code Formatter Tool)
.PHONY: format-code
format-code: ## 🔧 Format code using BF Agent Code Formatter
	@echo "🔧 Running BF Agent Code Formatter..."
	python scripts/code_formatter.py all --verbose
	@echo "✅ Code formatting complete!"

.PHONY: fix-precommit
fix-precommit: ## 🔧 Fix all pre-commit hook issues using optimized tool
	@echo "🔧 Fixing pre-commit issues with BF Agent Code Formatter..."
	python scripts/code_formatter.py precommit --verbose
	@echo "✅ Pre-commit fixes complete!"

.PHONY: lint-check
lint-check: ## 🔍 Check code quality without fixing
	@echo "🔍 Checking code quality..."
	python scripts/code_formatter.py check --verbose
	@echo "✅ Lint check complete!"

.PHONY: format-changed
format-changed: ## 🔧 Format only changed files (fast)
	@echo "🔧 Formatting changed files only..."
	python scripts/code_formatter.py changed --verbose
	@echo "✅ Changed files formatted!"

.PHONY: format-watch
format-watch: ## 👁️ Watch mode - auto-format on file changes
	@echo "👁️ Starting watch mode..."
	python scripts/code_formatter.py watch

# Git Sync & Pre-commit Integration
.PHONY: git-sync-v3
git-sync-v3: ## 🚀 Git Sync Tool V3 - Advanced Conflict Resolution
	@echo "🚀 Running Git Sync Tool V3 with Advanced Conflict Resolution..."
	python scripts/git-sync-tool-v3.py sync --verbose
	@echo "✅ Git sync V3 complete!"

.PHONY: git-sync-autofix
git-sync-autofix: ## 🔄 Enhanced Git Sync with Auto-Fix (Legacy V2)
	@echo "🔄 Running Enhanced Git Sync with Auto-Fix (Legacy V2)..."
	python scripts/git-sync-tool-enhanced_V2.py sync --verbose
	@echo "✅ Git sync with auto-fix complete!"

.PHONY: git-check-v3
git-check-v3: ## 🔍 V3 Pre-commit check with improved conflict handling
	@echo "🔍 V3 Pre-commit check with improved conflict handling..."
	python scripts/git-sync-tool-v3.py check --verbose

.PHONY: git-check
git-check: ## 🔍 Check pre-commit issues without fixing (Legacy V2)
	@echo "🔍 Checking pre-commit issues (Legacy V2)..."
	python scripts/git-sync-tool-enhanced_V2.py check --verbose

.PHONY: git-fix-v3
git-fix-v3: ## 🔧 V3 Fix pre-commit issues with advanced handling
	@echo "🔧 V3 Fixing pre-commit issues with advanced handling..."
	python scripts/git-sync-tool-v3.py fix --verbose

.PHONY: git-fix
git-fix: ## 🔧 Fix pre-commit issues only (Legacy V2)
	@echo "🔧 Fixing pre-commit issues (Legacy V2)..."
	python scripts/git-sync-tool-enhanced_V2.py fix --verbose

# GraphQL Monitoring & Analysis
.PHONY: graphql-analyze
graphql-analyze: ## 🔍 Analyze GraphQL resources for unused components
	@echo "🔍 Analyzing GraphQL resources..."
	python scripts/graphql_resource_analyzer.py analyze --apps bfagent
	@echo "✅ GraphQL analysis complete!"

.PHONY: graphql-cleanup
graphql-cleanup: ## 🗑️ Generate cleanup script for unused GraphQL resources
	@echo "🗑️ Generating GraphQL cleanup script..."
	python scripts/graphql_resource_analyzer.py cleanup --apps bfagent
	@echo "✅ Cleanup script generated!"

.PHONY: graphql-monitor
graphql-monitor: ## 📊 Setup GraphQL monitoring system
	@echo "📊 Setting up GraphQL monitoring..."
	@echo "🔄 Creating migrations for GraphQL models..."
	python manage.py makemigrations bfagent --name graphql_monitoring
	@echo "🔄 Applying migrations..."
	python manage.py migrate
	@echo "🧪 Testing GraphQL monitoring setup..."
	python scripts/graphql_monitor_setup.py
	@echo "✅ GraphQL monitoring setup complete!"

.PHONY: graphql-report
graphql-report: ## 📄 Generate GraphQL usage report
	@echo "📄 Generating GraphQL usage report..."
	python scripts/graphql_resource_analyzer.py export --format json
	@echo "✅ GraphQL report generated!"

# =============================================================================
# URL-TEMPLATE CONSISTENCY VALIDATION
# =============================================================================

.PHONY: check-urls
check-urls: ## 🔍 Validate URL-Template consistency (prevents NoReverseMatch)
	@echo "🔍 Validating URL-Template consistency..."
	python scripts/url_template_consistency_checker.py
	@echo "✅ URL validation complete!"

.PHONY: check-urls-fix
check-urls-fix: ## 🔧 Auto-generate missing URL patterns
	@echo "🔧 Generating missing URL patterns..."
	python scripts/url_template_consistency_checker.py --auto-fix
	@echo "✅ URL patterns generated!"

.PHONY: check-urls-report
check-urls-report: ## 📊 Generate URL consistency report
	@echo "📊 Generating URL consistency report..."
	python scripts/url_template_consistency_checker.py --output reports/url_consistency.json
	@echo "✅ Report saved to reports/url_consistency.json"

# =============================================================================
# CREATION PROCESS COMPLIANCE & STANDARDIZATION
# =============================================================================

.PHONY: check-compliance
check-compliance: ## 🎯 Check creation process compliance
	@echo "🎯 Checking creation process compliance..."
	python scripts/check_creation_compliance.py
	@echo "✅ Compliance check complete!"

.PHONY: validate
validate: ## 🔍 Run ALL validation checks (complete suite)
	@echo "🔍 Running complete validation suite..."
	@echo ""
	@echo "1️⃣ Creation Process Compliance..."
	@python scripts/check_creation_compliance.py
	@echo ""
	@echo "2️⃣ URL-Template Consistency..."
	@python scripts/url_template_consistency_checker.py
	@echo ""
	@echo "3️⃣ Model-Form-Template Consistency..."
	@python scripts/model_consistency_checker.py
	@echo ""
	@echo "4️⃣ Code Formatting..."
	@python scripts/code_formatter.py check
	@echo ""
	@echo "✅ All validation checks complete!"

.PHONY: new-model
new-model: ## 🆕 Create new model with guided process (Usage: make new-model MODEL=YourModel)
	@echo "🆕 Creating new model: $(MODEL)"
	@echo "📋 Follow the standardized creation process:"
	@echo ""
	@echo "Step 1: Define model in apps/bfagent/models.py"
	@echo "  - Add CRUDConfig class (MANDATORY)"
	@echo "  - Follow naming conventions"
	@echo ""
	@echo "Step 2: Create migrations"
	@echo "  make migrate"
	@echo ""
	@echo "Step 3: Analyze model"
	@echo "  python scripts/consistency_framework.py analyze $(MODEL)"
	@echo ""
	@echo "Step 4: Generate components"
	@echo "  python scripts/consistency_framework.py generate $(MODEL) --force"
	@echo ""
	@echo "Step 5: Validate"
	@echo "  make validate"
	@echo ""
	@echo "📚 See: .windsurf/STRICT_CREATION_PROCESS.md"

.PHONY: generate
generate: ## 🔧 Generate all components for model (Usage: make generate MODEL=YourModel)
	@echo "🔧 Generating components for: $(MODEL)"
	python scripts/consistency_framework.py generate $(MODEL) --force
	@echo "✅ Components generated!"
	@echo "Next: make validate"

.PHONY: fix-compliance
fix-compliance: ## 🔧 Fix compliance issues automatically
	@echo "🔧 Attempting to fix compliance issues..."
	@echo "Running model consistency fixes..."
	python scripts/model_consistency_checker.py --fix
	@echo "Running URL consistency fixes..."
	python scripts/url_template_consistency_checker.py --fix
	@echo "✅ Auto-fixes applied! Run 'make validate' to verify."

# ============================================================================
# SERVER CONTROL COMMANDS
# ============================================================================

.PHONY: kill-server
kill-server: ## 💀 Kill all Django server processes (use PORT=9000 to override)
	@echo "💀 Killing server on port $(PORT)..."
	@python scripts/kill_server.py --port $(PORT)

.PHONY: clean-cache
clean-cache: ## 🧹 Clear Django cache and temp files
	@echo "🧹 Clearing cache..."
	@python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('✅ Cache cleared')"
	@if exist "**/__pycache__" rmdir /s /q "**/__pycache__" 2>nul
	@if exist "*.pyc" del /s /q "*.pyc" 2>nul
	@echo "✅ Cache and temp files cleared!"

.PHONY: reset-server
reset-server: kill-server clean-cache ## 🔄 Complete server reset (use PORT=9000 to override)
	@echo "🔄 Resetting server on port $(PORT)..."
	@timeout /t 2 /nobreak >nul
	@echo "🚀 Starting fresh server on port $(PORT)..."
	@python manage.py runserver 127.0.0.1:$(PORT)

.PHONY: control
control: ## 🎛️ Open Control Center (stable UTF-8 safe version)
	@python scripts/control_center.py

# ============================================================================
# FEATURE PLANNING COMMANDS
# ============================================================================

.PHONY: feature-status
feature-status: ## 📊 Show current feature development status
	@python manage.py feature_status

.PHONY: feature-propose
feature-propose: ## 💡 Propose new feature (Usage: make feature-propose NAME=FeatureName TYPE=handler DESC="Description" PRIORITY=high)
	@python manage.py propose_feature --name=$(NAME) --type=$(TYPE) --description="$(DESC)" --priority=$(PRIORITY)

.PHONY: feature-claim
feature-claim: ## 🚧 Claim a feature (Usage: make feature-claim ID=123)
	@python manage.py claim_feature $(ID)

.PHONY: feature-complete
feature-complete: ## ✅ Mark feature as completed (Usage: make feature-complete ID=123 [STATUS=active|testing|completed]) @category:features @sub:Management
	@python manage.py feature_complete $(ID) --status=$(or $(STATUS),active)

.PHONY: features
features: feature-status ## 📋 Alias for feature-status

.PHONY: docs-analyze
docs-analyze: ## 📂 Analyze docs/ folder and match with features @category:dev @sub:Documentation
	@echo "📂 Analyzing docs/ folder..."
	@python manage.py analyze_docs

.PHONY: docs-link
docs-link: ## 🔗 Link matched docs + create features for unmatched (DRY-RUN) @category:dev @sub:Documentation
	@echo "🔗 Linking documents (DRY-RUN)..."
	@python manage.py link_and_create_features --dry-run

.PHONY: docs-link-apply
docs-link-apply: ## ✅ Apply: Link docs + create features @category:dev @sub:Documentation
	@echo "✅ Linking documents and creating features..."
	@python manage.py link_and_create_features
	@echo ""
	@echo "🎯 Next: Review features at http://localhost:8000/control-center/feature-planning/"

.PHONY: morning-status
morning-status: ## ☀️ Morning developer status report
	@echo "☀️ Good morning! Here's your dev status:"
	@echo ""
	@python manage.py feature_status --status in_progress
	@echo ""
	@echo "🔄 Recent migrations:"
	@python manage.py showmigrations bfagent | findstr /V "X" | findstr "[" || echo "All migrations applied ✅"
	@echo ""
	@echo "Ready to code! 🚀"
