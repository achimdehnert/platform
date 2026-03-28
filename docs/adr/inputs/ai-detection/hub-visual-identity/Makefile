# =============================================================================
# Hub Visual Identity System — Makefile (ADR-051)
# =============================================================================

.PHONY: help validate generate audit mutate install

PYTHON := python3
MODULE := tools.design_dna
STRENGTH ?= medium

help:
	@echo ""
	@echo "Hub Visual Identity System (ADR-051)"
	@echo "====================================="
	@echo ""
	@echo "  make install          Install Python dependencies"
	@echo "  make validate         Validate all hub DNA schemas"
	@echo "  make generate         Generate pui-tokens-{hub}.css for all hubs"
	@echo "  make generate HUB=X   Generate CSS for a single hub"
	@echo "  make audit            Run AI fingerprint audit (all hubs)"
	@echo "  make audit HUB=X      Audit a single hub"
	@echo "  make mutate           Mutate all failing hubs via Claude API"
	@echo "  make mutate HUB=X     Mutate a single hub"
	@echo "  make mutate-dry       Dry run — show plan without API calls"
	@echo ""
	@echo "  STRENGTH=low|medium|high  (default: medium)"
	@echo ""

install:
	pip install pydantic pyyaml anthropic --break-system-packages

validate:
	$(PYTHON) -m $(MODULE) validate $(if $(HUB),--hub $(HUB),)

generate:
	$(PYTHON) -m $(MODULE) generate $(if $(HUB),--hub $(HUB),)

audit:
	$(PYTHON) -m $(MODULE) audit $(if $(HUB),--hub $(HUB),) --output reports/audit-report.json

audit-ci:
	$(PYTHON) -m $(MODULE) audit --ci --output reports/audit-report.json

mutate:
	$(PYTHON) -m $(MODULE) mutate $(if $(HUB),--hub $(HUB),) --strength $(STRENGTH)

mutate-dry:
	$(PYTHON) -m $(MODULE) mutate $(if $(HUB),--hub $(HUB),) --strength $(STRENGTH) --dry-run

# Full pipeline: validate → generate → audit
pipeline: validate generate audit
	@echo "✅ Full pipeline complete"
