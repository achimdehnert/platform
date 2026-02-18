Analyzer
========

AST Scanner
-----------

.. module:: docs_agent.analyzer.ast_scanner
   :synopsis: AST-based docstring coverage scanning.

.. autofunction:: scan_repo

.. autofunction:: scan_module

DIATAXIS Classifier (Heuristic)
-------------------------------

.. module:: docs_agent.analyzer.diataxis_classifier
   :synopsis: Heuristic DIATAXIS classification via trigger words.

.. autofunction:: classify_file

.. autofunction:: classify_repo

.. autodata:: TRIGGER_PATTERNS

.. autodata:: DOC_EXTENSIONS

.. autodata:: SKIP_DIRS

DIATAXIS Classifier (LLM)
--------------------------

.. module:: docs_agent.analyzer.llm_classifier
   :synopsis: LLM-based fallback classifier for low-confidence documents.

.. autofunction:: reclassify_low_confidence

.. autodata:: DEFAULT_THRESHOLD

.. autodata:: PREVIEW_CHARS
