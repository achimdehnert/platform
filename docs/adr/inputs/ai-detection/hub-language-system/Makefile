# Hub Language Identity System — Makefile (ADR-052)

.PHONY: help install validate generate-voice audit-text mutate-copy compile-messages pipeline-text

PYTHON   := python3
MODULE   := tools.voice_dna
STRENGTH ?= medium

help:
	@echo ""
	@echo "Hub Language Identity System (ADR-052)"
	@echo "======================================="
	@echo ""
	@echo "  make install           Install Python dependencies"
	@echo "  make validate          Validate all Voice DNA schemas"
	@echo "  make generate-voice    Generate .po files for all hubs (DE + EN)"
	@echo "  make audit-text        Run AI text fingerprint audit"
	@echo "  make mutate-copy       Mutate failing hubs via Claude API"
	@echo "  make compile-messages  Compile .po → .mo (runs compilemessages per hub)"
	@echo "  make pipeline-text     validate → generate → audit"
	@echo ""
	@echo "  HUB=X       Target single hub"
	@echo "  STRENGTH=low|medium|high  (default: medium)"
	@echo ""

install:
	pip install pydantic pyyaml anthropic --break-system-packages

validate:
	$(PYTHON) -m $(MODULE) validate $(if $(HUB),--hub $(HUB),)

generate-voice:
	$(PYTHON) -m $(MODULE) generate $(if $(HUB),--hub $(HUB),)

audit-text:
	$(PYTHON) -m $(MODULE) audit $(if $(HUB),--hub $(HUB),) --output reports/text-audit-report.json

audit-text-ci:
	$(PYTHON) -m $(MODULE) audit --ci --output reports/text-audit-report.json

mutate-copy:
	$(PYTHON) -m $(MODULE) mutate $(if $(HUB),--hub $(HUB),) --strength $(STRENGTH)

mutate-dry:
	$(PYTHON) -m $(MODULE) mutate $(if $(HUB),--hub $(HUB),) --dry-run

compile-messages:
	@echo "Compiling .po → .mo for all generated locales …"
	@find generated_po -name "django.po" -exec sh -c \
		'dir=$$(dirname "{}"); msgfmt -o "$${dir}/django.mo" "{}" && echo "  ✓ $${dir}"' \;

pipeline-text: validate generate-voice audit-text
	@echo "✅ Text pipeline complete"
