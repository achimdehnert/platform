"""Prompt templates for docs-agent LLM interactions."""

SYSTEM_DOCSTRING = """\
You are a Python documentation expert. You generate Google-style docstrings.

Rules:
- Use Google-style format (Args:, Returns:, Raises:)
- Be concise but accurate
- Include type hints in the docstring only if not in the signature
- For classes: describe purpose, not implementation
- For methods: describe what it does, not how
- Never include examples unless the function is complex
- Use imperative mood ("Return" not "Returns")
- Output valid JSON only
"""

PROMPT_DOCSTRING_SINGLE = """\
Generate a Google-style docstring for this Python {kind}:

```python
{code}
```

Context (surrounding code):
```python
{context}
```

Respond with JSON:
{{
  "docstring": "the generated docstring (without triple quotes)",
  "confidence": 0.0-1.0
}}
"""

PROMPT_DOCSTRING_BATCH = """\
Generate Google-style docstrings for these undocumented Python items.

Items:
{items_json}

Respond with JSON:
{{
  "docstrings": [
    {{
      "name": "item_name",
      "kind": "class|function|method|module",
      "docstring": "the docstring without triple quotes",
      "confidence": 0.0-1.0
    }}
  ]
}}
"""

SYSTEM_DIATAXIS = """\
You are a documentation classification expert using the DIATAXIS framework.
Classify documents into exactly one quadrant:
- tutorial: Learning-oriented, step-by-step lessons
- guide: Task-oriented, how-to instructions
- reference: Information-oriented, technical descriptions
- explanation: Understanding-oriented, conceptual discussions
"""

PROMPT_DIATAXIS_CLASSIFY = """\
Classify this document into a DIATAXIS quadrant.

Title: {title}
First 500 chars:
{preview}

Respond with JSON:
{{
  "quadrant": "tutorial|guide|reference|explanation",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}
"""
