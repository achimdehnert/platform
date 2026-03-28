"""
LLM-based mutation strategy (Design #3).

Only used when deterministic strategies are insufficient.
Requires iil-aifw (optional dependency).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hub_identity.core.schema import HubDNA
    from hub_identity.core.scoring import ScoreNode


SYSTEM_PROMPT = """\
You are a senior UX copywriter specializing in German and English B2B SaaS copy.
Rewrite the given micro-copy strings to sound authentically human.

RULES:
- Preserve tone, formality, and brand personality exactly
- Eliminate all AI-typical phrases
- Use active voice, concrete language
- Respect formal/informal address setting
- Return ONLY valid JSON: {"de": {...}, "en": {...}}
"""

USER_TEMPLATE = """\
Hub: {hub} ({display_name})
Voice: {voice_description}
Tone: {tone}
Formal address (DE): {formal}

Strings to rewrite (detected as AI-typical):
{strings_json}

Return rewritten versions as JSON. Same keys, new values.
"""


class LLMCopyRewriteStrategy:
    """
    Rewrite micro-copy strings that can't be fixed by 1:1 replacement.

    This is the LAST strategy in the pipeline — only runs
    when deterministic strategies haven't brought the score
    below threshold.
    """

    name = "llm_rewrite"
    requires_llm = True

    def should_apply(
        self, dna: HubDNA, score: ScoreNode,
    ) -> bool:
        mc = score.find("MicroCopy")
        if not mc:
            return False
        return mc.raw_score > 25

    def apply(self, dna: HubDNA) -> HubDNA:
        from aifw.service import sync_completion

        data = dna.model_dump(mode="json")
        mc = data["voice"]["micro_copy"]

        # Collect non-empty strings for rewriting
        strings_to_rewrite = {}
        for lang in ("de", "en"):
            for key, val in mc.get(lang, {}).items():
                if val and isinstance(val, str) and len(val) > 3:
                    strings_to_rewrite[f"{lang}.{key}"] = val

        if not strings_to_rewrite:
            return dna

        tone_str = ", ".join(
            t if isinstance(t, str) else t
            for t in data["voice"].get("tone", [])
        )

        user_msg = USER_TEMPLATE.format(
            hub=data["hub"],
            display_name=data.get("display_name", ""),
            voice_description=data["voice"].get(
                "voice_description", "",
            ),
            tone=tone_str,
            formal=data["voice"].get("use_formal_address", True),
            strings_json=json.dumps(
                strings_to_rewrite,
                indent=2,
                ensure_ascii=False,
            ),
        )

        raw = sync_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=4096,
        ).strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            end = -1 if lines[-1] == "```" else len(lines)
            raw = "\n".join(lines[1:end])

        try:
            rewritten = json.loads(raw)
        except json.JSONDecodeError:
            return dna  # Fail gracefully — keep original

        # Apply rewritten strings back
        for lang in ("de", "en"):
            if lang in rewritten:
                for key, val in rewritten[lang].items():
                    if key in mc.get(lang, {}):
                        mc[lang][key] = val

        data["voice"]["micro_copy"] = mc
        return dna.model_validate(data)
