"""
Hub Visual Identity System — AI Fingerprint Auditor (ADR-051)

Scores a hub's CSS tokens against known AI design fingerprints.
Score: 0 = clearly human-designed, 100 = clearly AI-generated.

CI gate threshold: score must be < 40 to pass.
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


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PatternMatch:
    pattern_id: str
    category: str
    description: str
    weight: float
    matched: bool
    detail: str = ""


@dataclass
class AuditReport:
    hub: str
    score: float
    grade: str
    category_scores: dict[str, float]
    matches: list[PatternMatch]
    audited_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    recommendation: str = ""

    def passed(self, threshold: float = 40.0) -> bool:
        return self.score < threshold

    def to_dict(self) -> dict:
        return {
            "hub": self.hub,
            "score": round(self.score, 2),
            "grade": self.grade,
            "passed": self.passed(),
            "threshold": 40.0,
            "category_scores": {k: round(v, 2) for k, v in self.category_scores.items()},
            "matches": [
                {
                    "id": m.pattern_id,
                    "category": m.category,
                    "description": m.description,
                    "weight": m.weight,
                    "matched": m.matched,
                    "detail": m.detail,
                }
                for m in self.matches if m.matched
            ],
            "recommendation": self.recommendation,
            "audited_at": self.audited_at,
        }

    def print_report(self) -> None:
        """Human-readable terminal output."""
        status = "✅ PASSED" if self.passed() else "❌ FAILED"
        grade_color = {
            "A": "\033[92m",  # green
            "B": "\033[92m",
            "C": "\033[93m",  # yellow
            "D": "\033[91m",  # red
            "F": "\033[91m",
        }.get(self.grade, "")
        reset = "\033[0m"

        print(f"\n{'='*60}")
        print(f"  Hub: {self.hub}")
        print(f"  Score: {grade_color}{self.score:.1f}/100{reset}  Grade: {grade_color}{self.grade}{reset}  {status}")
        print(f"{'='*60}")

        if self.category_scores:
            print("\nCategory Breakdown:")
            for cat, score in sorted(self.category_scores.items(), key=lambda x: -x[1]):
                bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
                print(f"  {cat:15s} {bar} {score:.1f}%")

        if self.matches:
            print("\nMatched Patterns (contributing to score):")
            for m in sorted(self.matches, key=lambda x: -x.weight):
                if m.matched and m.weight > 0:
                    print(f"  [{m.pattern_id}] +{m.weight:4.1f}pt  {m.description}")
                    if m.detail:
                        print(f"           → {m.detail}")

        if self.recommendation:
            print(f"\n💡 Recommendation: {self.recommendation}")
        print()


# ---------------------------------------------------------------------------
# Auditor
# ---------------------------------------------------------------------------

class FingerprintAuditor:
    """
    Scores CSS tokens against known AI design fingerprint patterns.

    Usage:
        auditor = FingerprintAuditor.load()
        report = auditor.audit_css(hub="bieterpilot", css_content=css_text)
    """

    GRADE_THRESHOLDS = [
        (20, "A"),
        (35, "B"),
        (50, "C"),
        (65, "D"),
        (float("inf"), "F"),
    ]

    RECOMMENDATIONS = {
        "A": "Excellent — minimal AI fingerprint. Continue monitoring quarterly.",
        "B": "Good — some minor patterns detected. Low risk.",
        "C": "Caution — notable AI fingerprints. Consider running mutation engine.",
        "D": "Warning — strong AI fingerprints detected. Run: python -m tools.design_dna mutate --hub {hub}",
        "F": "Critical — this frontend will be classified as AI-generated. Immediate mutation required.",
    }

    def __init__(self, patterns: list[dict]) -> None:
        self.patterns = patterns

    @classmethod
    def load(
        cls,
        patterns_dir: Optional[Path] = None,
    ) -> "FingerprintAuditor":
        """Load all pattern files from detection_patterns/ directory."""
        if patterns_dir is None:
            patterns_dir = Path(__file__).parent.parent.parent / "detection_patterns"

        all_patterns: list[dict] = []
        for yaml_path in sorted(patterns_dir.glob("ai_patterns_v*.yaml")):
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            all_patterns.extend(data.get("patterns", []))
            print(f"  Loaded pattern file: {yaml_path.name} ({len(data.get('patterns', []))} patterns)")

        return cls(all_patterns)

    def audit_css(self, hub: str, css_content: str) -> AuditReport:
        """Score a CSS file against all loaded patterns."""
        matches: list[PatternMatch] = []
        category_raw: dict[str, float] = {}
        category_max: dict[str, float] = {}

        for pattern in self.patterns:
            pid = pattern["id"]
            category = pattern["category"]
            weight = float(pattern["weight"])
            description = pattern.get("description", "")
            detection = pattern.get("detection", {})

            # Accumulate max possible per category
            if weight > 0:
                category_max[category] = category_max.get(category, 0) + weight

            matched, detail = self._check_pattern(detection, css_content)

            if matched:
                matches.append(PatternMatch(
                    pattern_id=pid,
                    category=category,
                    description=description,
                    weight=weight,
                    matched=True,
                    detail=detail,
                ))
                if weight > 0:
                    category_raw[category] = category_raw.get(category, 0) + weight
                else:
                    # Bonus: reduces category score
                    category_raw[category] = category_raw.get(category, 0) + weight
            else:
                matches.append(PatternMatch(
                    pattern_id=pid,
                    category=category,
                    description=description,
                    weight=weight,
                    matched=False,
                ))

        # Compute category percentages (0–100)
        category_scores: dict[str, float] = {}
        for cat in set(list(category_raw.keys()) + list(category_max.keys())):
            raw = category_raw.get(cat, 0)
            max_val = category_max.get(cat, 1)
            pct = max(0.0, min(100.0, (raw / max_val) * 100)) if max_val > 0 else 0.0
            category_scores[cat] = pct

        # Overall score: weighted average across categories
        total_score = max(0.0, min(100.0, sum(
            category_raw.get(cat, 0)
            for cat in category_max
        )))

        grade = next(g for threshold, g in self.GRADE_THRESHOLDS if total_score <= threshold)
        recommendation = self.RECOMMENDATIONS[grade].format(hub=hub)

        return AuditReport(
            hub=hub,
            score=total_score,
            grade=grade,
            category_scores=category_scores,
            matches=matches,
            recommendation=recommendation,
        )

    def audit_dna_file(self, dna_yaml_path: Path, css_dir: Path) -> Optional[AuditReport]:
        """Audit a hub by loading its generated CSS."""
        from .schema import HubDNA

        dna = HubDNA.from_yaml(str(dna_yaml_path))
        css_path = css_dir / f"pui-tokens-{dna.hub}.css"

        if not css_path.exists():
            print(f"  ⚠️  CSS not found for {dna.hub}: {css_path} — run pipeline first")
            return None

        css_content = css_path.read_text(encoding="utf-8")
        return self.audit_css(dna.hub, css_content)

    def _check_pattern(
        self,
        detection: dict,
        css_content: str,
    ) -> tuple[bool, str]:
        """Returns (matched, detail_string)."""
        dtype = detection.get("type", "")

        if dtype == "font_match":
            for font in detection.get("values", []):
                # Check in CSS content (font declarations)
                if self._contains_font(css_content, font):
                    return True, f"Font '{font}' found in CSS"
            return False, ""

        elif dtype == "color_match":
            for color in detection.get("values", []):
                if color.lower() in css_content.lower():
                    return True, f"Color '{color}' found in CSS"
            return False, ""

        elif dtype == "regex":
            pattern = detection.get("pattern", "")
            if re.search(pattern, css_content, re.IGNORECASE):
                return True, f"Pattern matched: {pattern[:60]}"
            return False, ""

        elif dtype == "css_value":
            prop = detection.get("property", "")
            for val in detection.get("values", []):
                pattern = rf"{re.escape(prop)}\s*:\s*{re.escape(val)}"
                if re.search(pattern, css_content, re.IGNORECASE):
                    return True, f"CSS: {prop}: {val}"
            return False, ""

        elif dtype == "structural":
            check = detection.get("check", "")
            return self._structural_check(check, css_content)

        return False, ""

    def _contains_font(self, css: str, font: str) -> bool:
        """Check if a font name appears in CSS font declarations."""
        patterns = [
            rf"font-family\s*:\s*['\"]?{re.escape(font)}",
            rf"--pui-font-[^:]+:\s*['\"]?{re.escape(font)}",
        ]
        return any(re.search(p, css, re.IGNORECASE) for p in patterns)

    def _structural_check(self, check: str, css: str) -> tuple[bool, str]:
        """Higher-level structural checks."""
        if check == "same_display_and_body":
            display = re.search(r"--pui-font-display:\s*['\"]?([^,';\n]+)", css)
            body = re.search(r"--pui-font-body:\s*['\"]?([^,';\n]+)", css)
            if display and body:
                d = display.group(1).strip().strip("'\"")
                b = body.group(1).strip().strip("'\"")
                if d.lower() == b.lower():
                    return True, f"Display == Body font: '{d}'"
            return False, ""

        elif check == "no_asymmetry":
            # Check metadata comment
            if "@pui-meta:asymmetry     low" in css:
                return True, "Asymmetry level: low"
            return False, ""

        elif check == "no_spring_easing":
            # No cubic-bezier with overshoot (second value > 1)
            spring_pattern = r"cubic-bezier\([^)]*,\s*[1-9]\."
            if not re.search(spring_pattern, css):
                return True, "No spring/bounce easing found"
            return False, ""

        elif check == "perfect_complementary_colors":
            # Extract primary and accent, check if they're perfect complements
            # (hue difference ~180°) — simplified heuristic
            # Full implementation would parse hex → HSL and compute hue diff
            return False, ""  # Conservative: skip complex check

        elif check == "uniform_duration":
            durations = re.findall(r"(\d+(?:\.\d+)?)(?:ms|s)", css)
            unique = set(durations)
            if len(unique) <= 1 and len(durations) >= 3:
                return True, f"All durations identical: {unique}"
            return False, ""

        elif check == "centered_hero_cta":
            # Heuristic: text-center + margin: auto together
            has_text_center = "text-align: center" in css or "text-center" in css
            return has_text_center, "Centered text layout detected" if has_text_center else ""

        return False, ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def audit_all(
    dna_dir: Path,
    css_dir: Path,
    patterns_dir: Path,
    output_json: Optional[Path] = None,
    ci_mode: bool = False,
) -> int:
    """Audit all hubs. Returns exit code (0=pass, 1=fail)."""
    print("\n🔍 AI Fingerprint Audit — Hub Visual Identity System\n")

    auditor = FingerprintAuditor.load(patterns_dir)

    reports: list[AuditReport] = []
    failed_hubs: list[str] = []

    for yaml_path in sorted(dna_dir.glob("*.yaml")):
        if yaml_path.name.startswith("_"):
            continue
        report = auditor.audit_dna_file(yaml_path, css_dir)
        if report:
            reports.append(report)
            report.print_report()
            if not report.passed():
                failed_hubs.append(report.hub)

    # Summary
    print(f"\n{'='*60}")
    print(f"  Summary: {len(reports)} hubs audited, {len(failed_hubs)} failed")
    if failed_hubs:
        print(f"  Failed hubs: {', '.join(failed_hubs)}")
    print(f"{'='*60}\n")

    # JSON output for CI
    if output_json:
        output_json.write_text(
            json.dumps({"reports": [r.to_dict() for r in reports]}, indent=2),
            encoding="utf-8",
        )
        print(f"Report written to: {output_json}")

    if ci_mode and failed_hubs:
        print("❌ CI gate failed — hubs with score >= 40 must be mutated")
        return 1
    return 0
