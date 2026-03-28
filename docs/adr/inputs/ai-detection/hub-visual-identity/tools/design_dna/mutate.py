"""
Hub Visual Identity System — Mutation Engine (ADR-051)

Uses Claude API to generate evolved Hub DNA variants that:
  1. Maintain the hub's brand personality and aesthetic direction
  2. Avoid known AI design fingerprint patterns
  3. Track mutation history in the DNA YAML

This is the future-proofing mechanism: as detection technology evolves,
update detection_patterns/ and re-run mutation to adapt all hubs.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from aifw.service import sync_completion

from .schema import HubDNA, MutationRecord


# ---------------------------------------------------------------------------
# Prompt Engineering
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert UI/UX designer and design systems architect with deep knowledge
of CSS, typography, and color theory. You specialize in creating DISTINCTIVE,
human-feeling design systems for B2B SaaS applications.

Your task: Given a Hub's current design DNA and a list of AI fingerprint patterns
that have been detected in its CSS, generate an EVOLVED DNA variant that:

1. PRESERVES the hub's personality, aesthetic direction, and brand identity
2. ELIMINATES the detected AI fingerprint patterns
3. INTRODUCES genuine design character through:
   - Distinctive, non-generic font pairings (not Inter, Roboto, Space Grotesk, Poppins)
   - Unique color palette with intentional imperfections (not mathematically perfect)
   - Asymmetric layout characteristics
   - Spring/bounce easing instead of generic ease-in-out
   - Off-white or textured surfaces instead of pure white

CRITICAL RULES:
- ONLY use fonts available on fonts.bunny.net (DSGVO-compliant, no Google Fonts)
- Maintain EXACT hub semantic (bieterpilot = professional/industrial, not casual)
- Color changes must be incremental — no complete rebrands
- All colors must be valid hex (#RRGGBB format)
- Font source URL must use fonts.bunny.net
- border-radius values must NOT be 8px or 12px (most common AI values)
- Do NOT use Inter, Roboto, Arial, system-ui, Space Grotesk, Poppins as primary fonts

Available distinctive fonts on Bunny Fonts (examples — choose based on personality):
  Serif: Crimson Pro, DM Serif Display, Fraunces, Libre Baskerville, Newsreader,
         Playfair Display, EB Garamond, Cormorant Garamond, Lora, Merriweather
  Sans: Barlow, DM Sans, Figtree, Instrument Sans, Lexend, Manrope, Nunito,
        Outfit, Plus Jakarta Sans, Raleway, Syne, Work Sans, Yantramanav
  Mono: Fira Code, IBM Plex Mono, JetBrains Mono, Source Code Pro

Respond ONLY with a valid JSON object matching the HubDNA schema (no markdown, no preamble).
The JSON must be parseable by json.loads() directly.
"""

USER_PROMPT_TEMPLATE = """\
Hub DNA to evolve:
```json
{current_dna_json}
```

Detected AI fingerprint patterns (score: {current_score}/100, threshold: 40):
```json
{detected_patterns_json}
```

Mutation strength: {mutation_strength}
(low = minor adjustments, medium = significant changes, high = near-complete redesign while preserving personality)

Generate an evolved DNA that achieves a score < 30 while preserving the hub's identity.
Return ONLY the complete updated JSON — no markdown, no explanation.
"""


# ---------------------------------------------------------------------------
# Mutation Engine
# ---------------------------------------------------------------------------

class MutationEngine:
    """
    Generates evolved Hub DNA variants using aifw (ADR-051 §4.1).

    LLM calls go through aifw.service.sync_completion() which handles
    model routing, API keys, and fallback chains.
    """

    MAX_TOKENS = 2048

    def mutate(
        self,
        dna: HubDNA,
        detected_patterns: list[dict],
        mutation_strength: str = "medium",
    ) -> HubDNA:
        """
        Generate an evolved DNA variant for the given hub.

        Args:
            dna: Current hub DNA
            detected_patterns: List of matched pattern dicts from audit.py
            mutation_strength: "low" | "medium" | "high"

        Returns:
            New HubDNA with evolved visual properties
        """
        # Prepare prompt
        current_dna_json = json.dumps(
            dna.model_dump(mode="json", exclude={"mutation_history", "fingerprint_details"}),
            indent=2,
            ensure_ascii=False,
        )
        detected_json = json.dumps(
            [{"id": p["pattern_id"], "description": p["description"], "weight": p["weight"]}
             for p in detected_patterns if p.get("matched") and p.get("weight", 0) > 0],
            indent=2,
        )

        user_message = USER_PROMPT_TEMPLATE.format(
            current_dna_json=current_dna_json,
            detected_patterns_json=detected_json,
            current_score=dna.fingerprint_score or "unknown",
            mutation_strength=mutation_strength,
        )

        print(f"  🤖 Calling aifw for hub '{dna.hub}' (strength: {mutation_strength})...")

        # aifw handles model selection, API keys, and routing
        response = sync_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=self.MAX_TOKENS,
        )

        raw_text = response.strip()

        # Clean up potential markdown fences
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        # Parse and validate
        try:
            new_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Claude returned invalid JSON for hub '{dna.hub}': {e}\n"
                f"Raw response (first 500 chars):\n{raw_text[:500]}"
            ) from e

        # Preserve mutation history from current DNA
        new_data["mutation_history"] = [
            m.model_dump(mode="json") for m in (dna.mutation_history or [])
        ]
        new_data["mutation_history"].append(MutationRecord(
            timestamp=datetime.now(timezone.utc),
            reason=(
                f"Mutation triggered: score {dna.fingerprint_score:.1f} >= threshold 40. "
                f"Strength: {mutation_strength}. "
                f"Patterns eliminated: {len([p for p in detected_patterns if p.get('matched')])}"
            ),
            previous_score=dna.fingerprint_score or 0.0,
            changed_fields=_diff_dna(dna.model_dump(), new_data),
        ).model_dump(mode="json"))

        new_data["last_mutated"] = datetime.now(timezone.utc).isoformat()
        new_data["fingerprint_score"] = None  # Will be updated after next audit

        # Validate with Pydantic
        try:
            new_dna = HubDNA.model_validate(new_data)
        except Exception as e:
            raise ValueError(
                f"Claude generated invalid DNA for hub '{dna.hub}': {e}\n"
                f"Data: {json.dumps(new_data, indent=2)[:1000]}"
            ) from e

        print(f"  ✅ Mutation successful for '{dna.hub}'")
        return new_dna


def _diff_dna(old: dict, new: dict, prefix: str = "") -> list[str]:
    """Return list of changed field paths between two DNA dicts."""
    changed = []
    for key in set(list(old.keys()) + list(new.keys())):
        full_key = f"{prefix}.{key}" if prefix else key
        old_val = old.get(key)
        new_val = new.get(key)
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            changed.extend(_diff_dna(old_val, new_val, prefix=full_key))
        elif old_val != new_val:
            changed.append(full_key)
    return changed


# ---------------------------------------------------------------------------
# Batch Mutation
# ---------------------------------------------------------------------------

def mutate_failing_hubs(
    dna_dir: Path,
    audit_report_json: Path,
    output_dir: Path,
    mutation_strength: str = "medium",
    dry_run: bool = False,
) -> list[str]:
    """
    Mutate all hubs that failed the audit (score >= 40).

    Args:
        dna_dir: Directory containing hub DNA YAML files
        audit_report_json: Path to audit report from audit.py
        output_dir: Where to write updated DNA YAMLs
        mutation_strength: "low" | "medium" | "high"
        dry_run: If True, don't write files or call API

    Returns:
        List of mutated hub names
    """
    with open(audit_report_json) as f:
        audit_data = json.load(f)

    failing = [
        r for r in audit_data.get("reports", [])
        if not r.get("passed", True)
    ]

    if not failing:
        print("✅ All hubs passed audit — no mutation needed")
        return []

    print(f"\n🧬 Mutation Engine — {len(failing)} hub(s) require mutation\n")

    if dry_run:
        print("DRY RUN — no API calls, no files written")
        for r in failing:
            print(f"  Would mutate: {r['hub']} (score: {r['score']})")
        return [r["hub"] for r in failing]

    engine = MutationEngine()
    mutated = []
    output_dir.mkdir(parents=True, exist_ok=True)

    for report in failing:
        hub_name = report["hub"]
        dna_path = dna_dir / f"{hub_name}.yaml"

        if not dna_path.exists():
            print(f"  ⚠️  DNA file not found: {dna_path}")
            continue

        print(f"\n  Hub: {hub_name} (score: {report['score']:.1f})")

        dna = HubDNA.from_yaml(str(dna_path))
        # Inject current score + detected patterns from report
        dna.fingerprint_score = report["score"]

        detected_patterns = report.get("matches", [])

        try:
            new_dna = engine.mutate(dna, detected_patterns, mutation_strength)
            out_path = output_dir / f"{hub_name}.yaml"
            new_dna.to_yaml(str(out_path))
            print(f"  💾 Written: {out_path}")
            mutated.append(hub_name)
        except Exception as e:
            print(f"  ❌ Mutation failed for '{hub_name}': {e}", file=sys.stderr)

    print(f"\n✅ Mutated {len(mutated)} hub(s): {', '.join(mutated)}")
    return mutated
