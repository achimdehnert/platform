# =============================================================================
# BF Agent Documentation - Makefile
# =============================================================================
# Automatisierte Build-Kommandos für Sphinx-Dokumentation
#
# Verwendung:
#   make html      - Erstellt HTML-Dokumentation
#   make pdf       - Erstellt PDF-Dokumentation
#   make live      - Startet Live-Server mit Auto-Reload
#   make clean     - Löscht Build-Verzeichnis
#   make apidocs   - Generiert API-Dokumentation aus Code
#   make help      - Zeigt alle verfügbaren Kommandos
# =============================================================================

# Konfiguration
SPHINXOPTS    ?= --keep-going
SPHINXBUILD   ?= sphinx-build
SPHINXAPIDOC  ?= sphinx-apidoc
SPHINXAUTOBUILD ?= sphinx-autobuild
SOURCEDIR     = source
BUILDDIR      = build

# Projekt-Pfade (BF Agent Struktur)
PROJECT_ROOT  = ../../../..
APPS_DIR      = $(PROJECT_ROOT)/apps
WRITING_HUB   = $(APPS_DIR)/writing_hub
CAD_HUB       = $(APPS_DIR)/cad_hub
CONTROL_CENTER = $(APPS_DIR)/control_center
RESEARCH      = $(APPS_DIR)/research

# Farben für Output
BLUE  = \033[0;34m
GREEN = \033[0;32m
RED   = \033[0;31m
NC    = \033[0m  # No Color

# =============================================================================
# HAUPTZIELE
# =============================================================================

.PHONY: help
help:  ## Zeigt diese Hilfe an
	@echo ""
	@echo "$(BLUE)BF Agent Documentation - Build Commands$(NC)"
	@echo "=========================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

.PHONY: html
html: ## Erstellt HTML-Dokumentation
	@echo "$(BLUE)Building HTML documentation...$(NC)"
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS)
	@echo "$(GREEN)✓ HTML documentation built: $(BUILDDIR)/html/index.html$(NC)"

.PHONY: pdf
pdf: ## Erstellt PDF-Dokumentation (benötigt LaTeX)
	@echo "$(BLUE)Building PDF documentation...$(NC)"
	@$(SPHINXBUILD) -b latex "$(SOURCEDIR)" "$(BUILDDIR)/latex" $(SPHINXOPTS)
	@cd "$(BUILDDIR)/latex" && make
	@echo "$(GREEN)✓ PDF documentation built: $(BUILDDIR)/latex/bf_agent.pdf$(NC)"

.PHONY: epub
epub: ## Erstellt EPUB-Dokumentation
	@echo "$(BLUE)Building EPUB documentation...$(NC)"
	@$(SPHINXBUILD) -b epub "$(SOURCEDIR)" "$(BUILDDIR)/epub" $(SPHINXOPTS)
	@echo "$(GREEN)✓ EPUB documentation built: $(BUILDDIR)/epub/$(NC)"

.PHONY: live
live: ## Startet Live-Server mit Auto-Reload
	@echo "$(BLUE)Starting live documentation server...$(NC)"
	@echo "$(GREEN)Open http://127.0.0.1:8001 in your browser$(NC)"
	@$(SPHINXAUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)/html" --port 8001 --open-browser

# =============================================================================
# API-DOKUMENTATION
# =============================================================================

.PHONY: apidocs
apidocs: apidocs-writing apidocs-cad apidocs-control ## Generiert API-Dokumentation für alle Hubs
	@echo "$(GREEN)✓ All API documentation generated$(NC)"

.PHONY: apidocs-writing
apidocs-writing: ## Generiert Writing Hub Dokumentation
	@echo "$(BLUE)Generating Writing Hub API documentation...$(NC)"
	@mkdir -p "$(SOURCEDIR)/api/writing_hub"
	@$(SPHINXAPIDOC) -f -e -M -o "$(SOURCEDIR)/api/writing_hub" "$(WRITING_HUB)" \
		"$(WRITING_HUB)/migrations"
	@echo "$(GREEN)✓ Writing Hub documentation generated$(NC)"

.PHONY: apidocs-cad
apidocs-cad: ## Generiert CAD Hub Dokumentation
	@echo "$(BLUE)Generating CAD Hub API documentation...$(NC)"
	@mkdir -p "$(SOURCEDIR)/api/cad_hub"
	@$(SPHINXAPIDOC) -f -e -M -o "$(SOURCEDIR)/api/cad_hub" "$(CAD_HUB)" \
		"$(CAD_HUB)/migrations"
	@echo "$(GREEN)✓ CAD Hub documentation generated$(NC)"

.PHONY: apidocs-control
apidocs-control: ## Generiert Control Center Dokumentation
	@echo "$(BLUE)Generating Control Center API documentation...$(NC)"
	@mkdir -p "$(SOURCEDIR)/api/control_center"
	@$(SPHINXAPIDOC) -f -e -M -o "$(SOURCEDIR)/api/control_center" "$(CONTROL_CENTER)" \
		"$(CONTROL_CENTER)/migrations"
	@echo "$(GREEN)✓ Control Center documentation generated$(NC)"

# =============================================================================
# QUALITÄTSSICHERUNG
# =============================================================================

.PHONY: linkcheck
linkcheck: ## Prüft alle Links auf Gültigkeit
	@echo "$(BLUE)Checking links...$(NC)"
	@$(SPHINXBUILD) -b linkcheck "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck" $(SPHINXOPTS)
	@echo "$(GREEN)✓ Link check complete$(NC)"

.PHONY: coverage
coverage: ## Zeigt Dokumentations-Abdeckung
	@echo "$(BLUE)Checking documentation coverage...$(NC)"
	@$(SPHINXBUILD) -b coverage "$(SOURCEDIR)" "$(BUILDDIR)/coverage" $(SPHINXOPTS)
	@cat "$(BUILDDIR)/coverage/python.txt"
	@echo "$(GREEN)✓ Coverage report complete$(NC)"

.PHONY: spelling
spelling: ## Prüft Rechtschreibung (benötigt enchant)
	@echo "$(BLUE)Checking spelling...$(NC)"
	@$(SPHINXBUILD) -b spelling "$(SOURCEDIR)" "$(BUILDDIR)/spelling" $(SPHINXOPTS)
	@echo "$(GREEN)✓ Spelling check complete$(NC)"

.PHONY: lint
lint: ## Lint RST und Markdown Dateien
	@echo "$(BLUE)Linting documentation...$(NC)"
	@doc8 "$(SOURCEDIR)" --ignore D001 --ignore D004 || true
	@sphinx-lint "$(SOURCEDIR)" || true
	@echo "$(GREEN)✓ Lint complete$(NC)"

# =============================================================================
# WARTUNG
# =============================================================================

.PHONY: clean
clean: ## Löscht Build-Verzeichnis
	@echo "$(BLUE)Cleaning build directory...$(NC)"
	@rm -rf "$(BUILDDIR)"
	@echo "$(GREEN)✓ Build directory cleaned$(NC)"

.PHONY: clean-all
clean-all: clean ## Löscht Build und generierte API-Docs
	@echo "$(BLUE)Cleaning generated API docs...$(NC)"
	@rm -rf "$(SOURCEDIR)/api/generated"
	@rm -rf "$(SOURCEDIR)/reference/handlers/*.rst"
	@rm -rf "$(SOURCEDIR)/reference/models/*.rst"
	@echo "$(GREEN)✓ All generated files cleaned$(NC)"

.PHONY: rebuild
rebuild: clean html ## Clean Build und dann HTML erstellen
	@echo "$(GREEN)✓ Rebuild complete$(NC)"

# =============================================================================
# DEPLOYMENT
# =============================================================================

.PHONY: deploy-local
deploy-local: html ## Kopiert HTML zu lokalem Server
	@echo "$(BLUE)Deploying to local server...$(NC)"
	@cp -r "$(BUILDDIR)/html/"* /var/www/docs/bf-agent/
	@echo "$(GREEN)✓ Deployed to local server$(NC)"

.PHONY: deploy-gh-pages
deploy-gh-pages: html ## Deployed zu GitHub Pages
	@echo "$(BLUE)Deploying to GitHub Pages...$(NC)"
	@ghp-import -n -p -f "$(BUILDDIR)/html"
	@echo "$(GREEN)✓ Deployed to GitHub Pages$(NC)"

# =============================================================================
# DEVELOPMENT
# =============================================================================

.PHONY: install
install: ## Installiert Dokumentations-Dependencies
	@echo "$(BLUE)Installing documentation dependencies...$(NC)"
	@pip install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

.PHONY: setup
setup: install apidocs ## Vollständiges Setup: Install + API-Docs generieren
	@echo "$(GREEN)✓ Documentation setup complete$(NC)"
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Run 'make html' to build documentation"
	@echo "  2. Run 'make live' for development with auto-reload"
	@echo "  3. Open build/html/index.html in your browser"

# =============================================================================
# UTILITIES
# =============================================================================

.PHONY: open
open: html ## Erstellt HTML und öffnet im Browser
	@echo "$(BLUE)Opening documentation in browser...$(NC)"
	@xdg-open "$(BUILDDIR)/html/index.html" 2>/dev/null || \
	 open "$(BUILDDIR)/html/index.html" 2>/dev/null || \
	 start "$(BUILDDIR)/html/index.html" 2>/dev/null || \
	 echo "Please open $(BUILDDIR)/html/index.html manually"

.PHONY: stats
stats: ## Zeigt Dokumentations-Statistiken
	@echo "$(BLUE)Documentation Statistics$(NC)"
	@echo "========================"
	@echo "RST files: $$(find $(SOURCEDIR) -name '*.rst' | wc -l)"
	@echo "MD files:  $$(find $(SOURCEDIR) -name '*.md' | wc -l)"
	@echo "Images:    $$(find $(SOURCEDIR) -name '*.png' -o -name '*.jpg' -o -name '*.svg' | wc -l)"
	@echo "Total lines: $$(find $(SOURCEDIR) -name '*.rst' -o -name '*.md' | xargs wc -l | tail -1)"

# Catch-all für Sphinx-Builder
%:
	@$(SPHINXBUILD) -b $@ "$(SOURCEDIR)" "$(BUILDDIR)/$@" $(SPHINXOPTS)
