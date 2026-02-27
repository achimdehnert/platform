# =============================================================================
# BF Agent Platform — Makefile
# =============================================================================
#
# Zentrale Benutzersteuerung für alle Platform-Operationen.
# Verwendung: make <target>
#
# =============================================================================

.PHONY: help menu windsurf-clean windsurf-status windsurf-force windsurf-install

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
	@echo "$(CYAN)Tipp: Tab-Completion funktioniert! make wind<TAB>$(RESET)"
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

windsurf-install: ## Vollständige Windsurf-Stabilisierung installieren
	@scp docs/adr/inputs/fix-windsurf-remote.sh $(DEV_SERVER):~/
	@ssh $(DEV_SERVER) 'bash ~/fix-windsurf-remote.sh'

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
