Configuration
=============

Environment Variables
---------------------

.. list-table::
   :header-rows: 1
   :widths: 30 25 45

   * - Variable
     - Default
     - Description
   * - ``DOCS_AGENT_LLM_URL``
     - ``http://localhost:8100``
     - URL of the llm_mcp HTTP gateway
   * - ``DOCS_AGENT_LLM_MODEL``
     - ``gpt-4o-mini``
     - LLM model name for generation and classification
   * - ``OPENAI_API_KEY``
     - *(none)*
     - Direct OpenAI API key (fallback when gateway is unavailable)


LLM Backend Selection
---------------------

The LLM client uses a two-tier fallback strategy:

1. **llm_mcp HTTP gateway** — Production setup. Provides cost tracking, rate
   limiting, and multi-model routing. Configure via ``DOCS_AGENT_LLM_URL``.

2. **Direct OpenAI API** — Standalone fallback. Used only if the gateway is
   unreachable and ``OPENAI_API_KEY`` is set.

If neither backend is available, LLM-dependent features (``generate``,
``--refine``) will fail gracefully with an error message.


LLMConfig Dataclass
-------------------

All LLM settings can be configured programmatically:

.. code-block:: python

   from docs_agent.llm_client import LLMConfig

   config = LLMConfig(
       gateway_url="http://localhost:8100",
       model="gpt-4o-mini",
       temperature=0.3,
       max_tokens=1000,
       response_format="json",
       api_key="sk-...",  # optional OpenAI key
   )

Or load from environment:

.. code-block:: python

   config = LLMConfig.from_env()


Thresholds
----------

**Docstring coverage** (``--min-coverage``):
   Percentage of documented items. Recommended minimum: 50% for existing
   projects, 80% for new projects.

**DIATAXIS confidence** (``--refine``):
   Documents with heuristic confidence < 0.7 are candidates for LLM
   reclassification. This threshold is defined in
   ``analyzer.llm_classifier.DEFAULT_THRESHOLD``.

**Batch size** (``generator.docstring_gen.BATCH_SIZE``):
   Number of items sent per LLM call. Default: 10. Increase for faster
   processing, decrease if hitting context window limits.
