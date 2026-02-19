Quickstart
==========

Installation
------------

From the platform monorepo (recommended):

.. code-block:: bash

   pip install -e packages/docs-agent

With LLM support (httpx, openai, libcst):

.. code-block:: bash

   pip install -e "packages/docs-agent[llm]"

From GitHub (e.g. in ``requirements.txt``):

.. code-block:: text

   docs-agent @ git+https://github.com/achimdehnert/platform.git@main#subdirectory=packages/docs-agent


First Audit
-----------

Run a full documentation audit on any Python repository:

.. code-block:: bash

   docs-agent audit /path/to/your/repo

This produces:

1. **Docstring Coverage** — per-module table showing documented vs. undocumented items
2. **DIATAXIS Classification** — categorization of ``docs/`` files into tutorial, guide, reference, explanation


Docstrings Only
---------------

.. code-block:: bash

   docs-agent audit /path/to/repo --scope docstrings

DIATAXIS Only
-------------

.. code-block:: bash

   docs-agent audit /path/to/repo --scope diataxis


JSON Output for CI
------------------

.. code-block:: bash

   docs-agent audit /path/to/repo --output json


Enforce Minimum Coverage
------------------------

Fail the command (exit code 1) if docstring coverage is below a threshold:

.. code-block:: bash

   docs-agent audit /path/to/repo --min-coverage 60

This is useful in CI pipelines and pre-commit hooks.


Generate Missing Docstrings
----------------------------

Use the LLM-powered generator to create docstrings for undocumented items:

.. code-block:: bash

   # Preview what would be generated (dry run, default)
   docs-agent generate /path/to/repo

   # Actually write the docstrings into source files
   docs-agent generate /path/to/repo --apply

   # Limit to 10 items
   docs-agent generate /path/to/repo --max-items 10

The generator:

1. Scans for undocumented functions, classes, and methods
2. Sends code context to the LLM in batches
3. Receives Google-style docstrings
4. Inserts them non-destructively using ``libcst`` (preserving all formatting)
