Changelog
=========

v0.2.0 (2026-02-18)
--------------------

**Phase 4: LLM Integration**

* Added ``llm_client.py`` — async HTTP gateway client with OpenAI direct fallback
* Added ``prompts.py`` — Google-style docstring and DIATAXIS prompt templates
* Added ``generator/docstring_gen.py`` — batch LLM docstring generation
* Added ``generator/code_inserter.py`` — non-destructive insertion via ``libcst``
* Added ``analyzer/llm_classifier.py`` — LLM fallback for low-confidence DIATAXIS
* Added ``generate`` CLI command with ``--dry-run/--apply``, ``--max-items``, ``--model``
* Added ``--refine`` and ``--llm-url`` flags to ``audit`` command

**Phase 5: Automation**

* Added ``.pre-commit-hooks.yaml`` with ``docs-agent-coverage`` hooks
* Added GitHub Actions CI workflow (``ci-docs-agent.yml``)
* Added complete Sphinx documentation

**Tests:** 29/29 passing (7 AST + 6 inserter + 8 DIATAXIS + 8 LLM classifier)


v0.1.0 (2026-02-17)
--------------------

**Phase 3: MVP**

* Initial release
* ``analyzer/ast_scanner.py`` — AST-based docstring coverage scanning
* ``analyzer/diataxis_classifier.py`` — heuristic DIATAXIS classification
* ``models.py`` — data models (CodeItem, ModuleCoverage, RepoCoverage, DiaxisClassification)
* ``cli.py`` — ``audit`` command with ``--scope``, ``--apps-only``, ``--min-coverage``, ``--output``
* ``pyproject.toml`` — hatchling build, typer + rich dependencies

**Tests:** 15/15 passing (7 AST + 8 DIATAXIS)
