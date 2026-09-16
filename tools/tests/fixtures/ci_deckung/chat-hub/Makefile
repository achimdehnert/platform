# Eingefrorener Auszug aus iilgmbh/chat-hub@03ddfa0 (2026-09-16), nur die Ziele
# mit Pruef-Schluesselwort (ADR-Realfall chat-hub#110: `lint` ruft shellcheck
# hinter `if command -v`). Der Rest des Makefiles ist bewusst nicht enthalten:
# chat-hub ist privat, platform oeffentlich. Fixture zu tools/tests/test_ci_deckung.py,
# platform#3247.
.PHONY: chat-verify chat-verify-init test lint

chat-verify:
	@test -f deploy/.env || { echo "deploy/.env fehlt — erst 'make rtc-init'."; exit 1; }
	@set -a; . ./deploy/.env; set +a; \
		CHAT_SERVER_NAME=$(CHAT_SERVER_NAME) RTC_HOST=$(RTC_HOST) \
		python3 deploy/chat_verify.py

# Bei Bedarf: eigener Pruefnutzer fuer das Gate. Bewusst NICHT der Owner-Account
# — ein Automat soll sich nicht als Mensch anmelden muessen.
# Passwortformat nach der Lehre aus #18: Vierergruppen, keine Verwechsler
# (kein l/1, kein O/0), auf einer Handytastatur eingebbar.
#
# Der Localpart traegt bewusst ein Datum: **eine deaktivierte Matrix-ID ist fuer
# immer verbrannt** und laesst sich nicht neu anlegen. Wer den Pruefnutzer nach
# Gebrauch deaktiviert (so gehoert es auf einem privaten Server), braucht beim
# naechsten Mal einen neuen Namen. Ueberschreibbar: make chat-verify-init VERIFY_USER=…
VERIFY_USER ?= verify-$(shell date +%Y%m%d)

chat-verify-init:
	@test -f deploy/.env || { echo "deploy/.env fehlt — erst 'make rtc-init'."; exit 1; }
	@grep -q '^CHAT_VERIFY_USER=' deploy/.env \
		&& { echo "CHAT_VERIFY_USER steht schon in deploy/.env — Abbruch."; exit 1; } || true
	@set -e; umask 077; \
		g() { tr -dc 'abcdefghjkmnpqrstuvwxyz23456789' < /dev/urandom | head -c4; }; \
		pw="$$(g)-$$(g)-$$(g)-$$(g)"; \
		docker exec chathub_chat_synapse register_new_matrix_user \
			-c /data/homeserver.yaml -u $(VERIFY_USER) -p "$$pw" --no-admin \
			http://localhost:8008 > /dev/null; \
		{ echo "# Pruefnutzer fuer 'make chat-verify', angelegt $$(date -I)."; \
		  echo "CHAT_VERIFY_USER=$(VERIFY_USER)"; \
		  echo "CHAT_VERIFY_PASSWORD=$$pw"; } >> deploy/.env
	@echo "Pruefnutzer @$(VERIFY_USER):$(CHAT_SERVER_NAME) angelegt, Zugangsdaten in deploy/.env."
	@echo "Das Passwort steht bewusst nirgends sonst — auch nicht hier auf stdout."
	@echo "Nach Gebrauch: Konto per Admin-API deaktivieren, dann die beiden"
	@echo "CHAT_VERIFY_-Zeilen aus deploy/.env entfernen."


test:
	$(TEST_PY) -m pytest tests/ -q

# Dieselben Pruefungen wie die CI (.github/workflows/ci.yml). shellcheck ist auf
# dem Dev-Host nicht installiert — dann laeuft es im Container (chat-hub#109).

lint:
	@if command -v shellcheck >/dev/null; then shellcheck deploy/*.sh; \
	else docker run --rm -v "$(CURDIR):/mnt" -w /mnt koalaman/shellcheck:stable deploy/*.sh; fi
	$(TEST_PY) -m ruff check deploy/ tests/
	$(TEST_PY) -m ruff format --check deploy/ tests/

