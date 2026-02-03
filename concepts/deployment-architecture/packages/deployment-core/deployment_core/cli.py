"""
CLI tools for deployment-core.

Provides command-line utilities:
- deploy-health: Run health checks
- deploy-analyze: Analyze error logs

Usage:
    deploy-health https://myapp.example.com/health/
    deploy-analyze error.log
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import NoReturn


def health_check() -> NoReturn:
    """CLI entry point for health checks."""
    parser = argparse.ArgumentParser(
        description="Run health checks against a URL",
        prog="deploy-health",
    )
    parser.add_argument("url", help="Health check URL")
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of retries (default: 3)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds between retries (default: 5)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Total timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Include deep health checks (DB, Redis)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    args = parser.parse_args()

    async def run() -> int:
        from deployment_core.health import HealthChecker, HTTPProbe

        checker = HealthChecker(
            timeout=args.timeout,
            retries=args.retries,
            interval=args.interval,
        )

        # Add main health probe
        checker.add_probe(HTTPProbe(args.url, name="main"))

        # Add deep health probe if requested
        if args.deep:
            deep_url = args.url.rstrip("/") + "/deep/"
            checker.add_probe(HTTPProbe(deep_url, name="deep"))

        result = await checker.run()

        if args.json:
            import json

            print(json.dumps(result.to_dict(), indent=2))
        else:
            status_symbol = "✅" if result.is_healthy else "❌"
            print(f"\n{status_symbol} {result.name}: {result.status.value}")
            print(f"   Message: {result.message}")
            print(f"   Latency: {result.latency_ms:.0f}ms")

            if result.error:
                print(f"   Error: {result.error}")

            if result.details.get("checks"):
                print("\n   Individual checks:")
                for check in result.details["checks"]:
                    symbol = "✅" if check["status"] == "healthy" else "❌"
                    print(f"   {symbol} {check['name']}: {check['message']}")

        return 0 if result.is_healthy else 1

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


def analyze_error() -> NoReturn:
    """CLI entry point for error analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze deployment error logs",
        prog="deploy-analyze",
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        help="Error log file (or stdin if not provided)",
    )
    parser.add_argument(
        "--app",
        help="Application name for context",
    )
    parser.add_argument(
        "--deploy-path",
        help="Deployment path for context",
    )
    parser.add_argument(
        "--use-ai",
        action="store_true",
        help="Use Claude AI for analysis (requires ANTHROPIC_API_KEY)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show fix commands without executing (default: True)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute fix commands (use with caution!)",
    )

    args = parser.parse_args()

    async def run() -> int:
        from deployment_core.healing import ErrorAnalyzer, execute_fix

        # Read error log
        if args.log_file:
            with open(args.log_file) as f:
                error_log = f.read()
        else:
            error_log = sys.stdin.read()

        if not error_log.strip():
            print("Error: No error log provided", file=sys.stderr)
            return 1

        # Build context
        context = {}
        if args.app:
            context["app"] = args.app
        if args.deploy_path:
            context["deploy_path"] = args.deploy_path

        # Analyze
        analyzer = ErrorAnalyzer(use_patterns_first=not args.use_ai)
        analysis = await analyzer.analyze(error_log, context)

        if args.json:
            import json

            print(json.dumps(analysis.to_dict(), indent=2))
        else:
            print("\n" + "=" * 60)
            print("🔍 ERROR ANALYSIS")
            print("=" * 60)
            print(f"\nCategory:   {analysis.category.value}")
            print(f"Severity:   {analysis.severity.value}")
            print(f"Confidence: {analysis.confidence}%")
            print(f"Root Cause: {analysis.root_cause}")

            if analysis.matched_pattern:
                print(f"Pattern:    {analysis.matched_pattern}")

            print(f"\n{'─' * 60}")
            print("📋 RECOMMENDED FIX")
            print(f"{'─' * 60}")
            print(f"\nAction: {analysis.fix.action.value}")
            print(f"Risk:   {analysis.fix.risk.value}")

            if analysis.fix.commands:
                print("\nCommands:")
                for cmd in analysis.fix.commands:
                    print(f"  $ {cmd}")

            if analysis.fix.rollback_commands:
                print("\nRollback:")
                for cmd in analysis.fix.rollback_commands:
                    print(f"  $ {cmd}")

            if analysis.fix.prevention:
                print(f"\nPrevention: {analysis.fix.prevention}")

            can_auto = "Yes ✅" if analysis.can_auto_fix else "No ❌"
            print(f"\nCan Auto-Fix: {can_auto}")

        # Execute if requested
        if args.execute and not args.dry_run:
            if not analysis.can_auto_fix:
                print("\n⚠️  Cannot auto-fix: confidence < 85% or risk too high")
                return 1

            confirm = input("\n⚠️  Execute fix commands? [y/N] ")
            if confirm.lower() != "y":
                print("Aborted.")
                return 0

            result = await execute_fix(analysis, dry_run=False)
            print(f"\nExecution: {'Success ✅' if result['success'] else 'Failed ❌'}")

            for cmd_result in result.get("commands_executed", []):
                status = "✓" if cmd_result.get("status") == "success" else "✗"
                print(f"  {status} {cmd_result['command']}")

        return 0

    exit_code = asyncio.run(run())
    sys.exit(exit_code)


if __name__ == "__main__":
    # For testing
    health_check()
