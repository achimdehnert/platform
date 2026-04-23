CLI Reference
=============

The ``docs-agent`` CLI provides two main commands: ``audit`` and ``generate``.


``docs-agent audit``
--------------------

Audit a repository for documentation quality.

.. code-block:: text

   Usage: docs-agent audit [OPTIONS] REPO_PATH

**Arguments:**

``REPO_PATH``
   Path to the repository root. Must be an existing directory.

**Options:**

``--scope TEXT``
   Audit scope. One of ``docstrings``, ``diataxis``, or ``all``.
   Default: ``all``.

``--apps-only``
   Only scan the ``apps/`` directory for docstrings. Useful for Django projects.

``--min-coverage FLOAT``
   Fail (exit code 1) if docstring coverage is below this percentage.
   Example: ``--min-coverage 60``.

``--output TEXT``
   Output format: ``table`` (human-readable) or ``json`` (machine-readable).
   Default: ``table``.

``--refine``
   Use the LLM to re-classify DIATAXIS documents with confidence < 70%.
   Requires a running llm_mcp gateway or ``OPENAI_API_KEY``.

``--llm-url TEXT``
   URL of the llm_mcp HTTP gateway. Only used with ``--refine``.
   Default: ``http://localhost:8100``.

**Examples:**

.. code-block:: bash

   # Full audit with table output
   docs-agent audit /path/to/repo

   # JSON output for CI pipelines
   docs-agent audit /path/to/repo --output json

   # Django apps only, fail below 50%
   docs-agent audit /path/to/repo --apps-only --min-coverage 50

   # DIATAXIS with LLM refinement
   docs-agent audit /path/to/repo --scope diataxis --refine


``docs-agent generate``
-----------------------

Generate docstrings for undocumented code items via LLM.

.. code-block:: text

   Usage: docs-agent generate [OPTIONS] REPO_PATH

**Arguments:**

``REPO_PATH``
   Path to the repository root. Must be an existing directory.

**Options:**

``--apps-only``
   Only scan the ``apps/`` directory.

``--dry-run / --apply``
   Preview changes without writing (default), or apply them to files.

``--max-items INTEGER``
   Maximum number of items to generate docstrings for.
   Default: ``20``.

``--llm-url TEXT``
   URL of the llm_mcp HTTP gateway.
   Default: ``http://localhost:8100``.

``--model TEXT``
   LLM model name.
   Default: ``gpt-4o-mini``.

**Examples:**

.. code-block:: bash

   # Preview (dry run)
   docs-agent generate /path/to/repo

   # Apply changes to files
   docs-agent generate /path/to/repo --apply

   # Use a specific model, limit items
   docs-agent generate /path/to/repo --model gpt-4o --max-items 5

**Workflow:**

1. Scans for undocumented functions, classes, and methods via AST
2. Extracts source code context for each item (up to 30 lines)
3. Sends batches of 10 items to the LLM with Google-style docstring prompts
4. Parses LLM responses (JSON with docstring + confidence)
5. Inserts docstrings non-destructively using ``libcst``
6. Shows unified diff preview in dry-run mode
