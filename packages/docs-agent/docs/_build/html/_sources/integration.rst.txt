Integration Guide
=================

Pre-Commit Hook
---------------

Add docs-agent to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   repos:
     - repo: https://github.com/achimdehnert/platform
       rev: main
       hooks:
         - id: docs-agent-coverage
           args: ["--scope", "docstrings", "--min-coverage", "50"]

Available hook IDs:

``docs-agent-coverage``
   Runs docstring coverage audit and prints the table. Does not enforce a minimum.

``docs-agent-coverage-strict``
   Fails if docstring coverage is below 50%. Customize via ``args``.


GitHub Actions
--------------

A ready-made CI workflow is provided at
``packages/docs-agent/.github/workflows/ci-docs-agent.yml``.

To use it in your own repo, create ``.github/workflows/docs-quality.yml``:

.. code-block:: yaml

   name: Documentation Quality

   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   jobs:
     docs-audit:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4

         - uses: actions/setup-python@v5
           with:
             python-version: "3.12"

         - name: Install docs-agent
           run: |
             pip install typer rich
             pip install git+https://github.com/achimdehnert/platform.git@main#subdirectory=packages/docs-agent

         - name: Audit docstrings
           run: docs-agent audit . --min-coverage 50 --output json


Python API
----------

You can also use docs-agent programmatically:

.. code-block:: python

   from docs_agent.analyzer.ast_scanner import scan_repo
   from docs_agent.analyzer.diataxis_classifier import classify_repo
   from pathlib import Path

   repo = Path("/path/to/repo")

   # Docstring coverage
   coverage = scan_repo(repo, apps_only=True)
   print(f"Coverage: {coverage.coverage_pct:.1f}%")

   for module in coverage.modules:
       for item in module.undocumented:
           print(f"  {item.kind.value}: {item.name} (line {item.line})")

   # DIATAXIS classification
   results = classify_repo(repo)
   for r in results:
       print(f"  {r.file_path.name}: {r.quadrant.value} ({r.confidence:.0%})")


LLM Integration
---------------

For LLM-powered features (``generate`` command, ``--refine`` flag):

1. **llm_mcp gateway** (recommended): Start the gateway at ``http://localhost:8100``
2. **Direct OpenAI**: Set ``OPENAI_API_KEY`` environment variable

.. code-block:: python

   import asyncio
   from docs_agent.generator.docstring_gen import generate_docstrings
   from docs_agent.llm_client import LLMConfig

   config = LLMConfig(
       gateway_url="http://localhost:8100",
       model="gpt-4o-mini",
   )

   # items = list of CodeItem from ast_scanner
   results = asyncio.run(generate_docstrings(items, config=config))

   for gen in results:
       print(f"{gen.item.name}: {gen.docstring[:60]}...")
