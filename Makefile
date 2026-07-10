# =============================================================================
# BF Agent Platform — Makefile
# =============================================================================
#
# Zentrale Benutzersteuerung für alle Platform-Operationen.
# Verwendung: make <target>
#
# =============================================================================

.PHONY: help menu test lint setup windsurf-clean windsurf-status windsurf-force

# Default target
.DEFAULT_GOAL := help

# ── Farben ───────────────────────────────────────────────────────────────────
BOLD := $(shell tput bold 2>/dev/null || echo "")
RESET := $(shell tput sgr0 2>/dev/null || echo "")
GREEN := $(shell tput setaf 2 2>/dev/null || echo "")
YELLOW := $(shell tput setaf 3 2>/dev/null || echo "")
CYAN := $(shell tput setaf 6 2>/dev/null || echo "")

# ── Konfiguration ────────────────────────────────────────────────────────────
DEV_SERVER := hetzner-dev
PROD_SERVER := hetzner-prod

# =============================================================================
# HELP & MENU
# =============================================================================

help: ## Diese Hilfe anzeigen
	@echo ""
	@echo "$(BOLD)═══════════════════════════════════════════════════════════$(RESET)"
	@echo "$(BOLD)  BF Agent Platform — Makefile                             $(RESET)"
	@echo "$(BOLD)═══════════════════════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(CYAN)Dieses Makefile läuft lokal (WSL) und steuert Remote-Server via SSH.$(RESET)"
	@echo ""
	@echo "$(BOLD)Schnellstart:$(RESET)"
	@echo "  $(GREEN)make menu$(RESET)            Interaktives Hauptmenü"
	@echo ""
	@echo "$(BOLD)━━━ SERVER (hetzner-dev) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo ""
	@echo "$(BOLD)Windsurf Remote-SSH:$(RESET)"
	@grep -E '^windsurf-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Server-Zugriff:$(RESET)"
	@grep -E '^ssh-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)━━━ LOKAL (WSL) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo ""
	@echo "$(BOLD)Deployment:$(RESET)"
	@grep -E '^deploy-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Infrastruktur:$(RESET)"
	@grep -E '^(backup|logs)-[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Entwicklung & Sonstiges:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		grep -vE '^(help|menu|windsurf-[a-zA-Z_-]+|ssh-[a-zA-Z_-]+|deploy-[a-zA-Z_-]+|backup-[a-zA-Z_-]+|logs-[a-zA-Z_-]+):' | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Tipp: Tab-Completion funktioniert! make wind<TAB>$(RESET)"
	@echo "$(CYAN)Neue Targets zeigen sich hier automatisch — einfach '## Beschreibung' anhängen.$(RESET)"
	@echo ""

menu: ## Interaktives Hauptmenü
	@echo ""
	@echo "$(BOLD)═══ BF Agent Platform ═══$(RESET)"
	@echo ""
	@echo "  1) Windsurf Cleanup     — Stale Prozesse bereinigen"
	@echo "  2) Windsurf Status      — Aktive Sessions anzeigen"
	@echo "  3) SSH Dev-Server       — Verbindung zu hetzner-dev"
	@echo "  4) SSH Prod-Server      — Verbindung zu hetzner-prod"
	@echo "  h) Hilfe                — Alle verfügbaren Befehle"
	@echo "  q) Beenden"
	@echo ""
	@read -p "Auswahl [1-4, h, q]: " choice; \
	case $$choice in \
		1) $(MAKE) windsurf-clean ;; \
		2) $(MAKE) windsurf-status ;; \
		3) $(MAKE) ssh-dev ;; \
		4) $(MAKE) ssh-prod ;; \
		h) $(MAKE) help ;; \
		q) echo "Beendet." ;; \
		*) echo "Ungültige Auswahl: $$choice" ;; \
	esac

# =============================================================================
# WINDSURF REMOTE-SSH
# =============================================================================

windsurf-clean: ## Interaktives Cleanup-Menü (empfohlen)
	@ssh -t $(DEV_SERVER) 'bash ~/fix-windsurf-remote.sh --menu'

windsurf-status: ## Aktive Windsurf-Sessions anzeigen
	@echo "$(BOLD)Aktive Windsurf-Sessions auf $(DEV_SERVER):$(RESET)"
	@ssh $(DEV_SERVER) 'pgrep -af "workspace_id" -u deploy 2>/dev/null | \
		grep -oP "workspace_id \K[^ ]+" | sort -u | sed "s/^/  ✔ /" || echo "  (keine)"'
	@echo ""
	@echo "$(BOLD)Prozesse:$(RESET)"
	@ssh $(DEV_SERVER) 'echo "  $$(pgrep -c -f windsurf-server -u deploy 2>/dev/null || echo 0) Windsurf-Prozesse laufen"'

windsurf-force: ## ALLE Windsurf-Prozesse killen (Notfall)
	@echo "$(YELLOW)ACHTUNG: Dies killt ALLE Windsurf-Sessions!$(RESET)"
	@read -p "Wirklich fortfahren? [j/N]: " confirm && \
		[ "$$confirm" = "j" ] || [ "$$confirm" = "J" ] && \
		ssh $(DEV_SERVER) 'bash ~/fix-windsurf-remote.sh --force' || \
		echo "Abgebrochen."

# =============================================================================
# ENTWICKLUNG (lokaler Einstieg — SSoT für den Testbefehl dieses Repos)
# =============================================================================

setup: ## Dev-Dependencies + Hooks installieren (einmalig nach Clone)
	@pip install -r requirements-dev.txt --quiet
	@pre-commit install
	@$(MAKE) install-push-hook
	@echo "$(GREEN)Setup fertig — 'make test' für den lokalen Testlauf.$(RESET)"

test: ## CI-Test-Suite — SSoT: tools-tests.yml ruft exakt dieses Target (retro f4a546-incr #1)
	@python3 -m pytest tools/tests/ \
		tests/test_render_staging.py \
		tests/doc_profile_check/ \
		tools/claude-hooks/tests/ \
		agents/tests/ \
		--ignore=agents/tests/test_adr_scribe.py \
		-q

lint: ## Ruff über tools/ + scripts/ (ehrlich: schlägt bei Lint-Schuld fehl)
	@ruff check tools/ scripts/

# =============================================================================
# DEPLOYMENT (Platzhalter für zukünftige Erweiterung)
# =============================================================================

deploy-status: ## Deployment-Status aller Apps anzeigen
	@echo "$(BOLD)Deployment-Status:$(RESET)"
	@echo "  (noch nicht implementiert - siehe bf deploy CLI)"

# =============================================================================
# INFRASTRUKTUR
# =============================================================================

ssh-dev: ## SSH zum Dev-Server
	@ssh -t $(DEV_SERVER)

ssh-prod: ## SSH zum Prod-Server
	@ssh -t $(PROD_SERVER)

logs-dev: ## Letzte Logs vom Dev-Server
	@ssh $(DEV_SERVER) 'journalctl -n 50 --no-pager'

backup-db: ## Datenbank-Backup erstellen
	@echo "$(BOLD)Datenbank-Backup:$(RESET)"
	@echo "  (noch nicht implementiert - siehe /backup Workflow)"

# =============================================================================
# REGISTRY LINTING (ADR-212 Issue #247)
# =============================================================================

lint-tenancy: ## tenancy_mode Pflicht-Feld in registry/repos.yaml prüfen
	@python3 infra/scripts/validate_tenancy.py

lint-registry: ## Vollständige Registry-Validierung (ports + tenancy)
	@python3 infra/scripts/validate_repos.py
	@python3 infra/scripts/validate_tenancy.py

check-push: ## Lokale platform-Hard-Gates vor dem Push spiegeln (view-reader + publish-gate-invariant + check_publish_gate)
	@bash scripts/checks/pre_push_platform_gates.sh

install-push-hook: ## check-push als nativen pre-push-Hook installieren
	@bash scripts/checks/pre_push_platform_gates.sh --install-hook

.PHONY: lint-tenancy lint-registry

exit-plan: ## Exit-/Portability-Runbook für ORG=<org> aus Live-GitHub-Zustand (KONZ-002 OOTB-4; braucht GH_TOKEN mit repo+admin:org)
	@python3 tools/exit-plan.py $(ORG)

.PHONY: exit-plan

# =============================================================================
# REGISTRY (ADR-234 P0 — canonical.yaml ist die SSoT, Views sind generiert)
# Achtung: `registry-canonical.py build` (Views→canonical) ist die PRE-Flip-
# Bootstrap-Richtung und würde canonical-Edits aus den Views überschreiben —
# deshalb bewusst KEIN make-Target dafür. Schreibpfad ist flip (canonical→Views).
# =============================================================================

registry-flip: ## Views (repos.yaml + scripts/repo-registry.yaml) aus canonical.yaml regenerieren + verify (tools/registry-canonical.py flip)
	@python3 tools/registry-canonical.py flip

registry-verify: ## Round-trip prüfen: Views aus canonical.yaml regenerieren + gegen Altdateien vergleichen
	@python3 tools/registry-canonical.py verify

.PHONY: registry-flip registry-verify

# =============================================================================
# WORKFLOW-LINT (X-11 — lokales Preflight zu validate-workflows.yml)
# =============================================================================

workflow-lint: ## yamllint+actionlint lokal (Convenience-Preflight, Configs = validate-workflows.yml; KEIN Hard-Gate, CI bleibt maßgeblich)
	@if command -v yamllint >/dev/null 2>&1; then \
		yamllint -d "{extends: relaxed, rules: {line-length: {max: 200}}}" .github/workflows/*.yml \
			&& echo "$(GREEN)yamllint: keine Funde.$(RESET)"; \
	else \
		echo "$(YELLOW)yamllint nicht installiert — Installation: pip install yamllint$(RESET)"; \
	fi
	@if command -v actionlint >/dev/null 2>&1; then \
		ACTIONLINT_BIN=actionlint; \
	elif [ -x ./actionlint ]; then \
		ACTIONLINT_BIN=./actionlint; \
	else \
		ACTIONLINT_BIN=""; \
		echo "$(YELLOW)actionlint nicht gefunden — Installation: bash <(curl https://raw.githubusercontent.com/rhysd/actionlint/main/scripts/download-actionlint.bash)$(RESET)"; \
	fi; \
	if [ -n "$$ACTIONLINT_BIN" ]; then \
		$$ACTIONLINT_BIN -config-file .github/actionlint.yaml -ignore "shellcheck reported issue" .github/workflows/*.yml \
			&& echo "$(GREEN)actionlint: keine Funde.$(RESET)"; \
	fi
	@echo "$(CYAN)Hinweis: Convenience-Preflight, kein Hard-Gate — maßgeblich bleibt CI (.github/workflows/validate-workflows.yml).$(RESET)"

.PHONY: workflow-lint
