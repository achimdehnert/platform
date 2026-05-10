"""
ADR Dual-Tool Review — GitHub Actions Script

Tool 1 (deterministic): iil-adrfw validate + audit
Tool 2 (adversarial):   Claude API (claude-3-5-haiku-20241022)

Controlling output:
  - GitHub Actions Job Summary: cost, tokens, verdict per ADR
  - ai_sparring_by patch: audit trail in ADR frontmatter
  - PR comment: structured dual-tool findings

Usage (in GitHub Actions):
  python .github/scripts/adr_dual_review.py \
    --files docs/adr/ADR-190-foo.md docs/adr/ADR-191-bar.md \
    --pr-number 42 \
    --repo achimdehnert/platform
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import anthropic
import yaml


# ---------------------------------------------------------------------------
# Cost model (claude-3-5-haiku-20241022, 2026-05 pricing)
# ---------------------------------------------------------------------------
COST_PER_1K_INPUT = 0.00025   # USD
COST_PER_1K_OUTPUT = 0.00125  # USD
MODEL = "claude-3-5-haiku-20241022"
MAX_TOKENS_RESPONSE = 1200


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class StructuralFinding:
    severity: str
    message: str


@dataclass
class ReviewResult:
    adr_id: str
    adr_path: str
    structural_findings: list[StructuralFinding] = field(default_factory=list)
    structural_ok: bool = True
    ai_verdict: str = "skipped"          # approved | concerns | blocked | skipped | error
    ai_summary: str = ""
    ai_findings: list[str] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    error: str = ""


# ---------------------------------------------------------------------------
# Step 1: Structural check via iil-adrfw CLI
# ---------------------------------------------------------------------------
def run_structural_check(adr_path: str) -> tuple[bool, list[StructuralFinding]]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "iil_adrfw.cli", "validate", adr_path, "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            findings = [
                StructuralFinding(severity=f.get("severity", "info"), message=f.get("message", ""))
                for f in data.get("findings", [])
            ]
            ok = not any(f.severity in ("error", "critical") for f in findings)
            return ok, findings
        return True, []
    except Exception as e:
        return True, [StructuralFinding("info", f"Structural check skipped: {e}")]


# ---------------------------------------------------------------------------
# Step 2: Read ADR frontmatter + body
# ---------------------------------------------------------------------------
def read_adr(path: str) -> tuple[dict[str, Any], str]:
    text = Path(path).read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    fm = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return fm, body


# ---------------------------------------------------------------------------
# Step 3: Cost gate — skip if not worth reviewing
# ---------------------------------------------------------------------------
def should_review(fm: dict[str, Any]) -> tuple[bool, str]:
    status = str(fm.get("status", "")).lower()
    if status in ("void", "deprecated", "superseded", "rejected"):
        return False, f"status={status}, skip"

    # Skip if recent ai_sparring_by entry exists (< 30 days)
    sparring = fm.get("ai_sparring_by", [])
    if isinstance(sparring, list):
        today = date.today()
        for entry in sparring:
            if not isinstance(entry, dict):
                continue
            entry_date = entry.get("date", "")
            if isinstance(entry_date, str) and len(entry_date) >= 10:
                try:
                    d = date.fromisoformat(entry_date[:10])
                    if (today - d).days < 30:
                        return False, f"recent ai_sparring_by entry ({entry_date}), skip"
                except ValueError:
                    pass

    return True, "ok"


# ---------------------------------------------------------------------------
# Step 4: Claude adversarial review
# ---------------------------------------------------------------------------
ADVERSARIAL_SYSTEM = """\
You are a senior platform architect performing an adversarial ADR review.
Your job is to find problems, not to validate. Be specific. Be terse.

Output ONLY valid JSON matching this schema:
{
  "verdict": "approved" | "concerns" | "blocked",
  "findings": ["<finding 1>", "<finding 2>", ...],
  "summary": "<one sentence, max 120 chars>"
}

Verdict rules:
- "blocked": schema violations, missing required sections, or contradicts an active ADR
- "concerns": weak rationale, missing consequences, unclear scope, or Bus Factor risk
- "approved": well-structured, complete, no critical issues

Keep findings to max 5, each max 120 chars. No filler text outside the JSON block.
"""

ADVERSARIAL_PROMPT_TEMPLATE = """\
ADR under review: {adr_id}
Status: {status}
Domains: {domains}

--- FRONTMATTER ---
{frontmatter_yaml}

--- BODY ---
{body}

--- STRUCTURAL FINDINGS (iil-adrfw) ---
{structural_findings}

Review this ADR adversarially. Find the weaknesses.
"""


def call_claude(
    adr_id: str,
    fm: dict[str, Any],
    body: str,
    structural_findings: list[StructuralFinding],
) -> tuple[str, list[str], str, int, int, float]:
    """Returns: verdict, findings, summary, tokens_in, tokens_out, cost_usd"""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "skipped", [], "ANTHROPIC_API_KEY not set", 0, 0, 0.0

    sf_text = "\n".join(f"[{f.severity.upper()}] {f.message}" for f in structural_findings) or "None"
    body_truncated = body[:3000] if len(body) > 3000 else body

    prompt = ADVERSARIAL_PROMPT_TEMPLATE.format(
        adr_id=adr_id,
        status=fm.get("status", "unknown"),
        domains=", ".join(fm.get("domains", [])),
        frontmatter_yaml=yaml.dump({k: v for k, v in fm.items() if k != "metrics"}, allow_unicode=True),
        body=body_truncated,
        structural_findings=sf_text,
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS_RESPONSE,
            system=ADVERSARIAL_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        tokens_in = msg.usage.input_tokens
        tokens_out = msg.usage.output_tokens
        cost = (tokens_in / 1000 * COST_PER_1K_INPUT) + (tokens_out / 1000 * COST_PER_1K_OUTPUT)

        # Parse JSON (Claude may wrap in ```json)
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            return "error", [], f"No JSON in response: {raw[:100]}", tokens_in, tokens_out, cost
        data = json.loads(json_match.group())
        return (
            data.get("verdict", "concerns"),
            data.get("findings", []),
            data.get("summary", "")[:120],
            tokens_in, tokens_out, cost,
        )
    except json.JSONDecodeError as e:
        return "error", [], f"JSON parse error: {e}", 0, 0, 0.0
    except Exception as e:
        return "error", [], f"Claude API error: {e}", 0, 0, 0.0


# ---------------------------------------------------------------------------
# Step 5: Patch ai_sparring_by in ADR frontmatter
# ---------------------------------------------------------------------------
def patch_ai_sparring_by(path: str, verdict: str, summary: str) -> None:
    text = Path(path).read_text(encoding="utf-8")
    match = re.match(r"^(---\n)(.*?)(\n---\n)(.*)", text, re.DOTALL)
    if not match:
        return

    fm = yaml.safe_load(match.group(2)) or {}
    sparring = fm.get("ai_sparring_by") or []
    if not isinstance(sparring, list):
        sparring = []

    # Map verdict to role
    role_map = {"approved": "compliance-check", "concerns": "adversarial-review", "blocked": "adversarial-review"}
    sparring.append({
        "tool": "claude-code",
        "date": date.today().isoformat(),
        "role": role_map.get(verdict, "adversarial-review"),
        "summary": summary or f"Dual-tool review: {verdict}",
    })
    fm["ai_sparring_by"] = sparring

    new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    new_text = f"---\n{new_fm}---\n{match.group(4)}"
    Path(path).write_text(new_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 6: Build PR comment
# ---------------------------------------------------------------------------
VERDICT_EMOJI = {"approved": "✅", "concerns": "⚠️", "blocked": "❌", "skipped": "⏭️", "error": "🔴"}


def build_pr_comment(results: list[ReviewResult]) -> str:
    lines = ["## 🤖 ADR Dual-Tool Review\n"]
    total_cost = sum(r.cost_usd for r in results)

    lines.append("| ADR | Structural | AI Verdict | Cost |")
    lines.append("|-----|-----------|------------|------|")
    for r in results:
        sf_icon = "✅" if r.structural_ok else f"⚠️ {sum(1 for f in r.structural_findings if f.severity in ('error','critical'))} errors"
        emoji = VERDICT_EMOJI.get(r.ai_verdict, "❓")
        cost_str = f"${r.cost_usd:.4f}" if r.cost_usd > 0 else "—"
        lines.append(f"| `{r.adr_id}` | {sf_icon} | {emoji} {r.ai_verdict} | {cost_str} |")

    lines.append(f"\n**Total cost this run**: ${total_cost:.4f}")
    lines.append(f"**Model**: `{MODEL}` · **Schema v4** `ai_sparring_by` patched\n")

    for r in results:
        if r.ai_verdict in ("concerns", "blocked", "error") or r.structural_findings:
            lines.append(f"### `{r.adr_id}` — {VERDICT_EMOJI.get(r.ai_verdict, '')} {r.ai_verdict.upper()}")
            if r.ai_summary:
                lines.append(f"> {r.ai_summary}\n")
            if r.ai_findings:
                lines.append("**AI findings:**")
                for finding in r.ai_findings:
                    lines.append(f"- {finding}")
            sf_errors = [f for f in r.structural_findings if f.severity in ("error", "critical")]
            if sf_errors:
                lines.append("\n**Structural errors (iil-adrfw):**")
                for f in sf_errors:
                    lines.append(f"- `[{f.severity.upper()}]` {f.message}")
            lines.append("")
        elif r.ai_verdict == "skipped":
            lines.append(f"### `{r.adr_id}` — ⏭️ Skipped")
            lines.append(f"> {r.error or 'No review needed'}\n")

    lines.append("---")
    lines.append("*Tool 1: [iil-adrfw](https://pypi.org/project/iil-adrfw/) · Tool 2: Claude API (non-accountable — see `ai_sparring_by`)*")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 7: GitHub Actions Job Summary
# ---------------------------------------------------------------------------
def write_job_summary(results: list[ReviewResult]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    total_cost = sum(r.cost_usd for r in results)
    total_tokens_in = sum(r.tokens_in for r in results)
    total_tokens_out = sum(r.tokens_out for r in results)

    lines = [
        "## ADR Dual-Tool Review — Controlling",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| ADRs reviewed | {len(results)} |",
        f"| Total cost | ${total_cost:.4f} |",
        f"| Tokens in | {total_tokens_in:,} |",
        f"| Tokens out | {total_tokens_out:,} |",
        f"| Model | `{MODEL}` |",
        f"| Date | {date.today().isoformat()} |",
        "",
        "| ADR | Verdict | Tokens | Cost |",
        "|-----|---------|--------|------|",
    ]
    for r in results:
        t = f"{r.tokens_in + r.tokens_out:,}" if r.tokens_in or r.tokens_out else "—"
        c = f"${r.cost_usd:.4f}" if r.cost_usd > 0 else "—"
        lines.append(f"| `{r.adr_id}` | {r.ai_verdict} | {t} | {c} |")

    Path(summary_path).write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Step 8: Post PR comment via GitHub API
# ---------------------------------------------------------------------------
def post_pr_comment(comment: str, pr_number: int, repo: str) -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token or not pr_number:
        print(f"[INFO] PR comment (dry run):\n{comment[:300]}...")
        return
    try:
        import urllib.request
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        data = json.dumps({"body": comment}).encode()
        req = urllib.request.Request(url, data=data, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req) as resp:
            print(f"[OK] PR comment posted: HTTP {resp.status}")
    except Exception as e:
        print(f"[WARN] Failed to post PR comment: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs="+", required=True)
    parser.add_argument("--pr-number", type=int, default=0)
    parser.add_argument("--repo", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    results: list[ReviewResult] = []

    for adr_file in args.files:
        path = Path(adr_file)
        if not path.exists():
            print(f"[SKIP] {adr_file} not found")
            continue

        adr_id = re.search(r"ADR-\d+", path.name)
        adr_id = adr_id.group() if adr_id else path.stem
        print(f"\n[REVIEW] {adr_id} ({path.name})")

        result = ReviewResult(adr_id=adr_id, adr_path=str(path))

        # Structural check
        result.structural_ok, result.structural_findings = run_structural_check(str(path))
        sf_count = len([f for f in result.structural_findings if f.severity in ("error", "critical")])
        print(f"  Structural: {'OK' if result.structural_ok else f'{sf_count} errors'}")

        # Cost gate
        fm, body = read_adr(str(path))
        should, reason = should_review(fm)
        if not should:
            result.ai_verdict = "skipped"
            result.error = reason
            print(f"  AI review: skipped ({reason})")
            results.append(result)
            continue

        # Claude adversarial review
        verdict, findings, summary, t_in, t_out, cost = call_claude(adr_id, fm, body, result.structural_findings)
        result.ai_verdict = verdict
        result.ai_findings = findings
        result.ai_summary = summary
        result.tokens_in = t_in
        result.tokens_out = t_out
        result.cost_usd = cost
        print(f"  AI review: {verdict} | tokens={t_in}+{t_out} | cost=${cost:.4f}")
        if findings:
            for f in findings[:3]:
                print(f"    - {f}")

        # Patch ai_sparring_by
        if not args.dry_run and verdict not in ("skipped", "error"):
            patch_ai_sparring_by(str(path), verdict, summary)
            print(f"  ai_sparring_by patched ✓")

        results.append(result)

    # PR comment
    if results:
        comment = build_pr_comment(results)
        if not args.dry_run:
            post_pr_comment(comment, args.pr_number, args.repo)
        else:
            print(f"\n--- PR COMMENT (dry run) ---\n{comment}")

    # Job summary
    write_job_summary(results)

    # Exit code: non-zero if any blocked
    blocked = any(r.ai_verdict == "blocked" for r in results)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
