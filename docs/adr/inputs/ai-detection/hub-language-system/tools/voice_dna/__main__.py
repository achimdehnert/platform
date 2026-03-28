"""
Hub Language Identity System — CLI (ADR-052)

Usage:
    python -m tools.voice_dna generate [--hub HUB]
    python -m tools.voice_dna audit    [--hub HUB] [--ci] [--output JSON]
    python -m tools.voice_dna mutate   [--hub HUB] [--strength low|medium|high] [--dry-run]
    python -m tools.voice_dna validate [--hub HUB]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT    = Path(__file__).parent.parent.parent
DNA_DIR      = REPO_ROOT / "hub_voice_dnas"
GENERATED_DIR = REPO_ROOT / "generated_po"
PATTERNS_DIR = REPO_ROOT / "detection_patterns" / "text"
REPORTS_DIR  = REPO_ROOT / "reports"


def cmd_generate(args: argparse.Namespace) -> int:
    from .pipeline import VoicePipeline
    from .schema import HubVoiceDNA

    pipeline = VoicePipeline(output_root=GENERATED_DIR)
    print(f"\n🌐 Generating .po files → {GENERATED_DIR}\n")

    if args.hub:
        dna = HubVoiceDNA.from_yaml(str(DNA_DIR / f"{args.hub}.yaml"))
        pipeline.generate(dna)
    else:
        pipeline.generate_all(DNA_DIR)

    print("\n✅ Done — run 'python manage.py compilemessages' in each hub")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    from .audit import audit_all

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_json = REPORTS_DIR / "text-audit-report.json" if not args.output else Path(args.output)
    return audit_all(DNA_DIR, PATTERNS_DIR, output_json, ci_mode=args.ci)


def cmd_mutate(args: argparse.Namespace) -> int:
    from .schema import HubVoiceDNA
    from .mutate import CopyMutationEngine
    import json

    audit_report = REPORTS_DIR / "text-audit-report.json"
    if not audit_report.exists():
        print("  ✗ No audit report. Run 'audit' first.", file=sys.stderr)
        return 1

    with open(audit_report) as f:
        data = json.load(f)

    failing = [r for r in data.get("reports", []) if not r.get("passed", True)]
    if args.hub:
        failing = [r for r in failing if r["hub"] == args.hub]

    if not failing:
        print("✅ All hubs passed — no mutation needed")
        return 0

    if args.dry_run:
        print("DRY RUN:")
        for r in failing:
            print(f"  Would mutate: {r['hub']} (score: {r['score']})")
        return 0

    engine = CopyMutationEngine()
    mutated_dir = DNA_DIR / "_mutated"
    mutated_dir.mkdir(exist_ok=True)

    for report in failing:
        hub = report["hub"]
        dna = HubVoiceDNA.from_yaml(str(DNA_DIR / f"{hub}.yaml"))
        dna.text_fingerprint_score = report["score"]
        new_dna = engine.mutate(dna, report.get("matches", []), args.strength)
        out = mutated_dir / f"{hub}.yaml"
        new_dna.to_yaml(str(out))
        print(f"  💾 Written: {out}")

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from .schema import HubVoiceDNA

    print(f"\n✅ Validating Voice DNA schemas in {DNA_DIR}\n")
    errors = 0
    paths = [DNA_DIR / f"{args.hub}.yaml"] if args.hub else sorted(DNA_DIR.glob("*.yaml"))
    for path in paths:
        if path.name.startswith("_"):
            continue
        try:
            dna = HubVoiceDNA.from_yaml(str(path))
            print(f"  ✓ {dna.hub}  [{', '.join(t.value for t in dna.tone)}]")
        except Exception as e:
            print(f"  ✗ {path.stem}: {e}", file=sys.stderr)
            errors += 1

    if errors:
        print(f"\n❌ {errors} validation error(s)")
        return 1
    print("\n✅ All voice DNA files valid")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Hub Language Identity System — CLI (ADR-052)")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate .po files from Voice DNA")
    gen.add_argument("--hub")

    aud = sub.add_parser("audit", help="Audit AI text fingerprint scores")
    aud.add_argument("--hub")
    aud.add_argument("--ci", action="store_true")
    aud.add_argument("--output")

    mut = sub.add_parser("mutate", help="Mutate failing hubs via Claude API")
    mut.add_argument("--hub")
    mut.add_argument("--strength", choices=["low", "medium", "high"], default="medium")
    mut.add_argument("--dry-run", action="store_true")

    val = sub.add_parser("validate", help="Validate Voice DNA schemas")
    val.add_argument("--hub")

    args = parser.parse_args()
    sys.exit({"generate": cmd_generate, "audit": cmd_audit,
               "mutate": cmd_mutate, "validate": cmd_validate}[args.command](args))


if __name__ == "__main__":
    main()
