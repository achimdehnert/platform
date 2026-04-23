Generator
=========

Docstring Generator
-------------------

.. module:: docs_agent.generator.docstring_gen
   :synopsis: LLM-based batch docstring generation.

.. autoclass:: GeneratedDocstring
   :members:
   :undoc-members:

.. autofunction:: generate_docstrings

.. autodata:: BATCH_SIZE

Code Inserter
-------------

.. module:: docs_agent.generator.code_inserter
   :synopsis: Non-destructive docstring insertion via libcst.

.. autoclass:: InsertionResult
   :members:
   :undoc-members:

.. autofunction:: insert_docstrings

.. autodata:: MODULE_DOCSTRING_KEY
