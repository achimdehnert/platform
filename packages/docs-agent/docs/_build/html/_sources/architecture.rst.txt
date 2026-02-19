Architecture
============

Overview
--------

Docs Agent follows a layered architecture with clear separation between
analysis, generation, and presentation.

.. code-block:: text

   ┌─────────────────────────────────────────────┐
   │                  CLI (typer)                 │
   │            audit  │  generate                │
   └──────┬────────────┴──────────────┬───────────┘
          │                           │
   ┌──────▼────────────┐    ┌───────▼──────────┐
   │     Analyzer         │    │    Generator      │
   │  ┌───────────────┐  │    │ ┌──────────────┐  │
   │  │ ast_scanner   │  │    │ │ docstring_gen│  │
   │  ├───────────────┤  │    │ ├──────────────┤  │
   │  │ diataxis_cls  │  │    │ │ code_inserter│  │
   │  ├───────────────┤  │    │ └──────┬───────┘  │
   │  │ llm_classifier│  │    │        │          │
   │  └───────────────┘  │    └────────┼──────────┘
   └─────────────────────┘             │
                                ┌──────▼──────┐
                                │  llm_client  │
                                │ (gateway /   │
                                │  OpenAI)     │
                                └─────────────┘


Modules
-------

**analyzer/** — Read-only analysis of existing code and documentation.

- ``ast_scanner.py`` — Walks Python files, builds AST, counts documented vs.
  undocumented classes, functions, methods, and modules.
- ``diataxis_classifier.py`` — Heuristic classification of Markdown/RST files
  using trigger-word pattern matching against DIATAXIS quadrants.
- ``llm_classifier.py`` — LLM-based fallback for documents where the heuristic
  classifier has confidence < 0.7.

**generator/** — Write operations that modify source code.

- ``docstring_gen.py`` — Builds prompts from source code context, calls the LLM
  in batches of 10, and parses JSON responses into ``GeneratedDocstring`` objects.
- ``code_inserter.py`` — Uses ``libcst`` to insert docstrings into Python files
  without altering any existing formatting, comments, or whitespace.

**llm_client.py** — Async HTTP client that tries the llm_mcp gateway first,
then falls back to direct OpenAI API calls.

**prompts.py** — Jinja-style prompt templates for docstring generation and
DIATAXIS classification.

**models.py** — Frozen dataclasses for all data structures: ``CodeItem``,
``ModuleCoverage``, ``RepoCoverage``, ``DiaxisClassification``.

**cli.py** — Typer-based CLI with ``audit`` and ``generate`` commands.


Data Flow: Audit
-----------------

1. CLI receives ``repo_path`` and options
2. ``ast_scanner.scan_repo()`` walks ``*.py`` files, builds ``RepoCoverage``
3. ``diataxis_classifier.classify_repo()`` walks ``docs/*.md`` files
4. If ``--refine``: ``llm_classifier.reclassify_low_confidence()`` re-classifies
5. CLI renders table or JSON output


Data Flow: Generate
-------------------

1. CLI receives ``repo_path`` and LLM options
2. ``ast_scanner.scan_repo()`` identifies undocumented items
3. ``docstring_gen.generate_docstrings()`` calls LLM in batches
4. ``code_inserter.insert_docstrings()`` applies changes via libcst
5. In dry-run mode: shows unified diff preview
6. In apply mode: writes modified files to disk


Design Decisions
-----------------

**No CSTTransformer inheritance**
   ``_DocstringInserter`` uses a manual ``.transform()`` method rather than
   inheriting from ``libcst.CSTTransformer``. This avoids the complexity of
   the visitor pattern for simple docstring insertion.

**Explicit module key**
   Module-level docstrings are only inserted when the key ``__module__`` is
   present in the docstrings dict. This prevents false matches from lowercase
   function names.

**Gateway-first LLM strategy**
   The HTTP gateway is tried first because it provides cost tracking, rate
   limiting, and model routing. Direct OpenAI is only used as fallback.

**Batch processing**
   Items are sent to the LLM in batches of 10 to balance between API call
   overhead and context window limits.
