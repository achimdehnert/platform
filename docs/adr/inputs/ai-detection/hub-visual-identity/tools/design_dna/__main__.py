"""
Hub Visual Identity System — CLI (ADR-051)

Usage:
    python -m tools.design_dna generate [--hub HUB] [--all]
    python -m tools.design_dna audit [--hub HUB] [--all] [--ci] [--output JSON]
    python -m tools.design_dna mutate [--hub HUB] [--all] [--strength LEVEL] [--dry-run]
    python -m tools.design_dna validate [--hub HUB] [--all]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Paths (relative to repository root)
REPO_ROOT = Path(__file__).parent.parent.parent
DNA_DIR = REPO_ROOT / "hub_dnas"
GENERATED_DIR = REPO_ROOT / "generated"
PATTERNS_DIR = REPO_ROOT / "detection_patterns"
REPORTS_DIR = REPO_ROOT / "reports"


def cmd_generate(args: argparse.Namespace) -> int:
    from .pipeline import Pipeline
    from .schema import HubDNA

    pipeline = Pipeline(output_dir=GENERATED_DIR)

    print(f"\n🎨 Generating CSS tokens → {GENERATED_DIR}\n")

    if args.hub:
        dna_path = DNA_DIR / f"{args.hub}.yaml"
        if not dna_path.exists():
            print(f"  ✗ Hub DNA not found: {dna_path}", file=sys.stderr)
            return 1
        dna = HubDNA.from_yaml(str(dna_path))
        out = pipeline.generate(dna)
        print(f"  ✓ {dna.hub} → {out.name}")
    else:
        pipeline.generate_all(DNA_DIR)

    print("\n✅ Done")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    from .audit import FingerprintAuditor, audit_all

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_json = REPORTS_DIR / "audit-report.json" if args.output is None else Path(args.output)

    return audit_all(
        dna_dir=DNA_DIR,
        css_dir=GENERATED_DIR,
        patterns_dir=PATTERNS_DIR,
        output_json=output_json,
        ci_mode=args.ci,
    )


def cmd_mutate(args: argparse.Namespace) -> int:
    from .mutate import mutate_failing_hubs

    audit_report = REPORTS_DIR / "audit-report.json"
    if not audit_report.exists():
        print("  ✗ No audit report found. Run 'audit' first.", file=sys.stderr)
        return 1

    mutated_dir = DNA_DIR / "_mutated"  # Review before merging back to hub_dnas/
    mutate_failing_hubs(
        dna_dir=DNA_DIR,
        audit_report_json=audit_report,
        output_dir=mutated_dir,
        mutation_strength=args.strength,
        dry_run=args.dry_run,
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    from .schema import HubDNA

    print(f"\n✅ Validating Hub DNA schemas in {DNA_DIR}\n")
    errors = 0

    paths = [DNA_DIR / f"{args.hub}.yaml"] if args.hub else sorted(DNA_DIR.glob("*.yaml"))

    for path in paths:
        if path.name.startswith("_"):
            continue
        try:
            dna = HubDNA.from_yaml(str(path))
            print(f"  ✓ {dna.hub}")
        except Exception as e:
            print(f"  ✗ {path.stem}: {e}", file=sys.stderr)
            errors += 1

    if errors:
        print(f"\n❌ {errors} validation error(s)")
        return 1
    print("\n✅ All DNA files valid")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hub Visual Identity System — CLI (ADR-051)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    gen = subparsers.add_parser("generate", help="Generate pui-tokens-{hub}.css from DNA")
    gen.add_argument("--hub", help="Single hub name (default: all)")

    # audit
    aud = subparsers.add_parser("audit", help="Audit AI fingerprint scores")
    aud.add_argument("--hub", help="Single hub name (default: all)")
    aud.add_argument("--ci", action="store_true", help="CI mode: exit 1 if any hub fails")
    aud.add_argument("--output", help="JSON report output path")

    # mutate
    mut = subparsers.add_parser("mutate", help="Generate evolved DNA for failing hubs")
    mut.add_argument("--hub", help="Single hub name (default: all failing)")
    mut.add_argument("--strength", choices=["low", "medium", "high"], default="medium")
    mut.add_argument("--dry-run", action="store_true", help="Don't call API or write files")

    # validate
    val = subparsers.add_parser("validate", help="Validate DNA YAML schemas")
    val.add_argument("--hub", help="Single hub name (default: all)")

    args = parser.parse_args()

    commands = {
        "generate": cmd_generate,
        "audit": cmd_audit,
        "mutate": cmd_mutate,
        "validate": cmd_validate,
    }

    sys.exit(commands[args.command](args))


if __name__ == "__main__":
    main()
