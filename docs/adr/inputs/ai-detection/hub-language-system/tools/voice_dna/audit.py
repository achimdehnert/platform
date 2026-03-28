"""
Hub Language Identity System — AI Text Fingerprint Auditor (ADR-052)

Scores hub copy against known AI text fingerprints.
Score: 0 = clearly human voice, 100 = clearly AI-generated copy.
CI gate threshold: score must be < 35.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class TextPatternMatch:
    pattern_id: str
    category: str
    lang: str
    description: str
    weight: float
    matched: bool
    matched_value: str = ""
    field_name: str = ""


@dataclass
class TextAuditReport:
    hub: str
    score: float
    grade: str
    category_scores: dict[str, float]
    matches: list[TextPatternMatch]
    audited_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    recommendation: str = ""

    def passed(self, threshold: float = 35.0) -> bool:
        return self.score < threshold

    def to_dict(self) -> dict:
        return {
            "hub": self.hub,
            "score": round(self.score, 2),
            "grade": self.grade,
            "passed": self.passed(),
            "threshold": 35.0,
            "category_scores": {k: round(v, 2) for k, v in self.category_scores.items()},
            "matches": [
                {"id": m.pattern_id, "category": m.category, "lang": m.lang,
                 "description": m.description, "weight": m.weight,
                 "matched_value": m.matched_value, "field": m.field_name}
                for m in self.matches if m.matched and m.weight > 0
            ],
            "recommendation": self.recommendation,
            "audited_at": self.audited_at,
        }

    def print_report(self) -> None:
        status = "✅ PASSED" if self.passed() else "❌ FAILED"
        print(f"\n{'='*60}")
        print(f"  Hub: {self.hub}")
        print(f"  Text Score: {self.score:.1f}/100  Grade: {self.grade}  {status}")
        print(f"{'='*60}")

        if self.category_scores:
            print("\nCategory Breakdown:")
            for cat, score in sorted(self.category_scores.items(), key=lambda x: -x[1]):
                bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
                print(f"  {cat:15s} {bar} {score:.1f}%")

        if self.matches:
            print("\nMatched Patterns:")
            for m in sorted(self.matches, key=lambda x: -x.weight):
                if m.matched and m.weight > 0:
                    print(f"  [{m.pattern_id}] +{m.weight:.1f}pt  [{m.lang}] {m.description}")
                    if m.matched_value:
                        print(f"           → found: \"{m.matched_value}\"  (field: {m.field_name})")

        if self.recommendation:
            print(f"\n💡 {self.recommendation}")
        print()


class TextFingerprintAuditor:
    """Scores hub copy (from VoiceDNA) against AI text fingerprint patterns."""

    GRADE_THRESHOLDS = [
        (15, "A"), (25, "B"), (35, "C"), (50, "D"), (float("inf"), "F"),
    ]
    RECOMMENDATIONS = {
        "A": "Excellent — copy sounds authentically human. Monitor quarterly.",
        "B": "Good — minor AI patterns detected. Low risk.",
        "C": "Caution — notable AI copy patterns. Run mutation engine.",
        "D": "Warning — strong AI text fingerprint. Run: python -m tools.voice_dna mutate --hub {hub}",
        "F": "Critical — copy will be classified as AI-generated. Immediate mutation required.",
    }

    def __init__(self, patterns: list[dict]) -> None:
        self.patterns = patterns

    @classmethod
    def load(cls, patterns_dir: Optional[Path] = None) -> "TextFingerprintAuditor":
        if patterns_dir is None:
            patterns_dir = Path(__file__).parent.parent.parent / "detection_patterns" / "text"
        all_patterns: list[dict] = []
        for yaml_path in sorted(patterns_dir.glob("ai_text_v*.yaml")):
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            all_patterns.extend(data.get("patterns", []))
            print(f"  Loaded: {yaml_path.name} ({len(data.get('patterns', []))} patterns)")
        return cls(all_patterns)

    def audit_dna(self, dna: "HubVoiceDNA") -> TextAuditReport:  # type: ignore[name-defined]
        """Score a HubVoiceDNA against all text patterns."""
        from .schema import HubVoiceDNA

        # Collect all copy strings per language
        copy_de = dna.micro_copy.de.model_dump()
        copy_en = dna.micro_copy.en.model_dump()

        # Also check banned/preferred words
        all_text_de = " ".join(str(v) for v in copy_de.values()).lower()
        all_text_en = " ".join(str(v) for v in copy_en.values()).lower()

        matches: list[TextPatternMatch] = []
        category_raw: dict[str, float] = {}
        category_max: dict[str, float] = {}

        for pattern in self.patterns:
            pid = pattern["id"]
            category = pattern["category"]
            lang = pattern.get("lang", "both")
            weight = float(pattern.get("weight", 0))
            description = pattern.get("description", "")
            detection = pattern.get("detection", {})

            if weight > 0:
                category_max[category] = category_max.get(category, 0) + weight

            matched, matched_value, field_name = self._check(
                detection, lang, copy_de, copy_en, all_text_de, all_text_en
            )

            if matched and weight > 0:
                category_raw[category] = category_raw.get(category, 0) + weight
                matches.append(TextPatternMatch(
                    pattern_id=pid, category=category, lang=lang,
                    description=description, weight=weight, matched=True,
                    matched_value=matched_value, field_name=field_name,
                ))
            else:
                matches.append(TextPatternMatch(
                    pattern_id=pid, category=category, lang=lang,
                    description=description, weight=weight, matched=False,
                ))

        # Scores
        category_scores: dict[str, float] = {}
        for cat in set(list(category_raw) + list(category_max)):
            raw = category_raw.get(cat, 0)
            max_v = category_max.get(cat, 1)
            category_scores[cat] = max(0.0, min(100.0, (raw / max_v) * 100)) if max_v > 0 else 0.0

        total = max(0.0, min(100.0, sum(category_raw.values())))
        grade = next(g for t, g in self.GRADE_THRESHOLDS if total <= t)
        recommendation = self.RECOMMENDATIONS[grade].format(hub=dna.hub)

        return TextAuditReport(
            hub=dna.hub, score=total, grade=grade,
            category_scores=category_scores, matches=matches,
            recommendation=recommendation,
        )

    def _check(
        self,
        detection: dict,
        lang: str,
        copy_de: dict,
        copy_en: dict,
        all_text_de: str,
        all_text_en: str,
    ) -> tuple[bool, str, str]:
        """Returns (matched, matched_value, field_name)."""
        dtype = detection.get("type", "")

        if dtype == "phrase":
            values = detection.get("values", [])
            texts_to_check: list[tuple[str, dict, str]] = []
            if lang in ("de", "both"):
                texts_to_check.append((all_text_de, copy_de, "de"))
            if lang in ("en", "both"):
                texts_to_check.append((all_text_en, copy_en, "en"))

            for full_text, copy_dict, l in texts_to_check:
                for phrase in values:
                    if phrase.lower() in full_text:
                        # Find which field contains it
                        field = next(
                            (k for k, v in copy_dict.items()
                             if phrase.lower() in str(v).lower()),
                            "unknown"
                        )
                        return True, phrase, f"{l}.{field}"
            return False, "", ""

        elif dtype == "structural":
            check = detection.get("check", "")
            return self._structural_check(check, copy_de, copy_en)

        return False, "", ""

    def _structural_check(
        self, check: str, copy_de: dict, copy_en: dict
    ) -> tuple[bool, str, str]:
        if check == "uniform_length":
            de_lengths = [len(str(v)) for v in copy_de.values() if v]
            if de_lengths:
                avg = sum(de_lengths) / len(de_lengths)
                variance = sum((l - avg) ** 2 for l in de_lengths) / len(de_lengths)
                if variance < 25:  # Very low variance = AI uniformity
                    return True, f"DE copy length variance={variance:.1f} (too uniform)", "de.*"
            return False, "", ""

        elif check == "passive_voice_errors":
            passive_patterns_de = [
                r"wurde[n]?\s+\w+",
                r"wird\s+\w+",
            ]
            error_keys = [k for k in copy_de if "error" in k or "toast" in k]
            for key in error_keys:
                text = str(copy_de.get(key, ""))
                for pat in passive_patterns_de:
                    if re.search(pat, text, re.IGNORECASE):
                        return True, f"Passive voice in '{key}': {text[:40]}", f"de.{key}"
            return False, "", ""

        return False, "", ""


def audit_all(
    dna_dir: Path,
    patterns_dir: Path,
    output_json: Optional[Path] = None,
    ci_mode: bool = False,
) -> int:
    from .schema import HubVoiceDNA

    print("\n🔍 AI Text Fingerprint Audit — Hub Language Identity System\n")
    auditor = TextFingerprintAuditor.load(patterns_dir)

    reports: list[TextAuditReport] = []
    failed_hubs: list[str] = []

    for yaml_path in sorted(dna_dir.glob("*.yaml")):
        if yaml_path.name.startswith("_"):
            continue
        try:
            dna = HubVoiceDNA.from_yaml(str(yaml_path))
            report = auditor.audit_dna(dna)
            reports.append(report)
            report.print_report()
            if not report.passed():
                failed_hubs.append(report.hub)
        except Exception as e:
            print(f"  ✗ {yaml_path.stem}: {e}", file=sys.stderr)

    print(f"\n{'='*60}")
    print(f"  Summary: {len(reports)} hubs audited, {len(failed_hubs)} failed")
    if failed_hubs:
        print(f"  Failed: {', '.join(failed_hubs)}")
    print(f"{'='*60}\n")

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(
            json.dumps({"reports": [r.to_dict() for r in reports]}, indent=2),
            encoding="utf-8",
        )

    if ci_mode and failed_hubs:
        print("❌ CI gate failed — hubs with text score >= 35 must be mutated")
        return 1
    return 0
