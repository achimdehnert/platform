"""Management command to batch-evaluate chat conversations.

Usage::

    # Evaluate all conversations from last 24h
    python manage.py evaluate_conversations

    # Evaluate specific app, last 48h
    python manage.py evaluate_conversations --app drifttales --since 48

    # Force re-evaluate, specific metrics
    python manage.py evaluate_conversations --force --metrics answer_relevancy,helpfulness

    # Limit number of conversations
    python manage.py evaluate_conversations --limit 10
"""

from __future__ import annotations

import asyncio

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Evaluate chat conversations using LLM-based quality metrics"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            type=str,
            default=None,
            help="Filter by app_name (e.g. drifttales)",
        )
        parser.add_argument(
            "--since",
            type=int,
            default=24,
            help="Evaluate conversations from last N hours (default: 24)",
        )
        parser.add_argument(
            "--metrics",
            type=str,
            default=None,
            help="Comma-separated metric names (default: all)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-evaluate even if scores already exist",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Max conversations to evaluate (default: 50)",
        )

    def handle(self, *args, **options):
        from chat_logging.evaluation import (
            METRIC_PROMPTS,
            batch_evaluate,
        )

        app_name = options["app"]
        since_hours = options["since"]
        force = options["force"]
        limit = options["limit"]

        metrics = None
        if options["metrics"]:
            metrics = [
                m.strip()
                for m in options["metrics"].split(",")
            ]
            invalid = [
                m for m in metrics
                if m not in METRIC_PROMPTS
            ]
            if invalid:
                self.stderr.write(
                    self.style.ERROR(
                        f"Unknown metrics: {invalid}\n"
                        f"Available: {list(METRIC_PROMPTS.keys())}"
                    )
                )
                return

        self.stdout.write(
            f"Evaluating conversations"
            f" (app={app_name or 'all'}"
            f", since={since_hours}h"
            f", limit={limit}"
            f", force={force})"
        )

        result = asyncio.run(
            batch_evaluate(
                app_name=app_name,
                since_hours=since_hours,
                metrics=metrics,
                force=force,
                limit=limit,
            )
        )

        self.stdout.write(
            f"\nFound: {result['conversations_found']} conversations"
        )
        self.stdout.write(
            f"Scored: {result['conversations_scored']} conversations"
        )
        self.stdout.write(
            f"Metrics: {result['total_metrics']} total scores"
        )

        if result["averages"]:
            self.stdout.write("\nAverage scores:")
            for metric, avg in sorted(
                result["averages"].items()
            ):
                bar = "█" * int(avg * 20) + "░" * (20 - int(avg * 20))
                self.stdout.write(
                    f"  {metric:30s} {bar} {avg:.3f}"
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\nNo conversations to evaluate."
                )
            )

        self.stdout.write(
            self.style.SUCCESS("\nEvaluation complete.")
        )
