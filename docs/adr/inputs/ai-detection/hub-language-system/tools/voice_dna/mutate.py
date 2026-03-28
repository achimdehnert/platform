"""
Hub Language Identity System — Copy Mutation Engine (ADR-052)

Uses Claude API to generate evolved copy variants that:
  1. Preserve the hub's voice personality and tone
  2. Eliminate detected AI text fingerprint patterns
  3. Are contextually appropriate for DE + EN B2B audiences
  4. Track mutation history in the DNA YAML
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from aifw.service import sync_completion

from .schema import HubVoiceDNA, MutationRecord


SYSTEM_PROMPT = """\
You are a senior UX copywriter and brand voice specialist with deep expertise in
German and English B2B SaaS copy. You write micro-copy that sounds authentically
human — never like AI-generated filler.

Your task: Given a Hub's current Voice DNA and a list of AI text fingerprint patterns
detected in its copy, generate evolved micro-copy that:

1. PRESERVES the hub's tone, personality, and brand voice exactly
2. ELIMINATES all detected AI fingerprint phrases
3. SOUNDS like it was written by a senior copywriter who deeply understands the audience
4. USES active voice, concrete language, and appropriate formality for the hub

CRITICAL RULES FOR GERMAN COPY:
- Respect use_formal_address: true = "Sie/Ihr", false = "du/dein"
- No generic verbs: "loslegen", "starten", "entdecken", "erleben"
- No AI adjectives: "nahtlos", "leistungsstark", "innovativ", "umfassend", "robust"
- Error messages must be specific and actionable, not generic
- Toast messages must feel warm and direct, not corporate

CRITICAL RULES FOR ENGLISH COPY:
- No generic CTAs: "Get Started", "Learn More", "Explore", "Discover"
- No AI adverbs: "seamlessly", "effortlessly", "intuitively"
- No AI verbs: "leverage", "streamline", "unlock", "empower"
- Error messages must name the problem specifically
- Match the hub's tone exactly — bieterpilot is precise, DriftTales is warm, etc.

BANNED PHRASES (always avoid regardless of hub):
DE: "nahtlos", "leistungsstark", "innovativ", "umfassend", "jetzt loslegen",
    "mehr erfahren", "erleben Sie", "es ist wichtig zu beachten",
    "ein Fehler ist aufgetreten", "bitte versuchen Sie es erneut"
EN: "seamlessly", "leverage", "cutting-edge", "get started", "learn more",
    "something went wrong", "please try again", "it's worth noting", "delve into"

Respond ONLY with a valid JSON object containing:
{
  "de": { ...all LocalizedMicroCopy fields for German... },
  "en": { ...all LocalizedMicroCopy fields for English... },
  "banned_words_de": [...updated list...],
  "banned_words_en": [...updated list...],
  "preferred_words_de": {...updated map...},
  "preferred_words_en": {...updated map...}
}
No markdown, no preamble. Pure JSON only.
"""

USER_PROMPT_TEMPLATE = """\
Hub: {hub}
Display Name: {display_name}
Voice Description: {voice_description}
Tone: {tone}
Formal address (DE): {use_formal_address}
Use imperatives: {use_imperatives}
Sentence length preference: {sentence_length}

Current micro-copy (DE):
{current_de_json}

Current micro-copy (EN):
{current_en_json}

Detected AI text fingerprint patterns (score: {score}/100, threshold: 35):
{detected_json}

Mutation strength: {strength}
(low = refine wording, medium = rewrite problematic strings, high = rethink full voice)

Generate evolved copy that achieves a text fingerprint score < 20.
Return ONLY the JSON object described in the system prompt.
"""


class CopyMutationEngine:
    """
    Generates evolved hub copy using aifw (ADR-052).

    LLM calls go through aifw.service.sync_completion() which handles
    model routing, API keys, and fallback chains.
    """

    MAX_TOKENS = 4096  # Copy needs more tokens than CSS

    def mutate(
        self,
        dna: HubVoiceDNA,
        detected_patterns: list[dict],
        strength: str = "medium",
    ) -> HubVoiceDNA:
        """Generate evolved copy for a hub."""
        current_de = dna.micro_copy.de.model_dump()
        current_en = dna.micro_copy.en.model_dump()

        detected_json = json.dumps(
            [{"id": p["pattern_id"], "description": p["description"],
              "matched_value": p.get("matched_value", ""), "field": p.get("field_name", "")}
             for p in detected_patterns if p.get("matched") and p.get("weight", 0) > 0],
            indent=2, ensure_ascii=False,
        )

        user_message = USER_PROMPT_TEMPLATE.format(
            hub=dna.hub,
            display_name=dna.display_name,
            voice_description=dna.voice_description,
            tone=", ".join(t.value for t in dna.tone),
            use_formal_address=dna.use_formal_address,
            use_imperatives=dna.use_imperatives,
            sentence_length=dna.sentence_length.value,
            current_de_json=json.dumps(current_de, indent=2, ensure_ascii=False),
            current_en_json=json.dumps(current_en, indent=2, ensure_ascii=False),
            detected_json=detected_json,
            score=dna.text_fingerprint_score or "unknown",
            strength=strength,
        )

        matched_count = len(
            [p for p in detected_patterns if p.get('matched')]
        )
        print(
            f"  \U0001f916 Mutating copy for '{dna.hub}' "
            f"(strength: {strength}, DE+EN, {matched_count} patterns)..."
        )

        # aifw handles model selection, API keys, and routing
        raw = sync_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=self.MAX_TOKENS,
        ).strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            new_copy_data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Claude returned invalid JSON for '{dna.hub}': {e}\n"
                f"Raw (first 500 chars): {raw[:500]}"
            ) from e

        # Build updated DNA dict
        dna_dict = dna.model_dump(mode="json")
        dna_dict["micro_copy"]["de"] = new_copy_data["de"]
        dna_dict["micro_copy"]["en"] = new_copy_data["en"]

        if "banned_words_de" in new_copy_data:
            dna_dict["banned_words_de"] = new_copy_data["banned_words_de"]
        if "banned_words_en" in new_copy_data:
            dna_dict["banned_words_en"] = new_copy_data["banned_words_en"]
        if "preferred_words_de" in new_copy_data:
            dna_dict["preferred_words_de"] = new_copy_data["preferred_words_de"]
        if "preferred_words_en" in new_copy_data:
            dna_dict["preferred_words_en"] = new_copy_data["preferred_words_en"]

        # Mutation history
        changed_keys = _diff_copy(current_de, new_copy_data.get("de", {}), "de")
        changed_keys += _diff_copy(current_en, new_copy_data.get("en", {}), "en")

        dna_dict["mutation_history"].append(MutationRecord(
            timestamp=datetime.now(timezone.utc),
            reason=(
                f"Text fingerprint score {dna.text_fingerprint_score:.1f} >= threshold 35. "
                f"Strength: {strength}. Patterns: {len(changed_keys)} copy strings changed."
            ),
            previous_score=dna.text_fingerprint_score or 0.0,
            language="de+en",
            changed_keys=changed_keys,
        ).model_dump(mode="json"))
        dna_dict["last_mutated"] = datetime.now(timezone.utc).isoformat()
        dna_dict["text_fingerprint_score"] = None

        new_dna = HubVoiceDNA.model_validate(dna_dict)
        print(f"  ✅ Copy mutation complete for '{dna.hub}' ({len(changed_keys)} strings changed)")
        return new_dna


def _diff_copy(old: dict, new: dict, prefix: str) -> list[str]:
    return [
        f"{prefix}.{k}" for k in old
        if str(old.get(k, "")).strip() != str(new.get(k, "")).strip()
    ]
