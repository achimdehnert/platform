from __future__ import annotations

from pathlib import Path
from typing import Dict

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import Agents

CURATED: Dict[str, Dict[str, str]] = {
    "Outline Agent": {
        "agent_type": "outline_agent",
        "prompt_file": "memory-bank/agent-prompts/outline_agent.md",
        "description": "Generates an extensive story outline from Story Fundamentals while respecting Genre Settings.",
    },
    "World & Conflict Agent": {
        "agent_type": "world_conflict_agent",
        "prompt_file": "memory-bank/agent-prompts/world_conflict_agent.md",
        "description": "Expands outline into world bible elements and escalating conflict ladders, genre-aware.",
    },
    "Character Agent": {
        "agent_type": "character_agent",
        "prompt_file": "memory-bank/agent-prompts/character_agent.md",
        "description": "Derives cast and arcs from outline, genre-aware; seeds protagonists/antagonists and key allies.",
    },
}

DEFAULT_SYSTEM_PROMPT = (
    "You are a focused book development agent. Produce clear, structured outputs. "
    "Always adapt to the project's genre and genre settings. Be concise but comprehensive."
)


class Command(BaseCommand):
    help = "Purge redundant agents and seed a curated set (Outline, World & Conflict, Character)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hard-delete",
            action="store_true",
            help="Hard delete non-curated agents (default: set status to INACTIVE)",
        )

    def handle(self, *args, **options):
        hard_delete: bool = options.get("hard_delete", False)
        base_dir = Path(settings.BASE_DIR)

        with transaction.atomic():
            self._purge_non_curated(hard_delete=hard_delete)
            created, updated = self._seed_curated(base_dir)

        self.stdout.write(
            self.style.SUCCESS(f"Seeding complete. Created: {created}, Updated: {updated}.")
        )

    def _purge_non_curated(self, hard_delete: bool) -> None:
        curated_types = {cfg["agent_type"] for cfg in CURATED.values()}
        qs = Agents.objects.exclude(agent_type__in=curated_types)
        if hard_delete:
            deleted_count, _ = qs.delete()
            self.stdout.write(
                self.style.WARNING(f"Hard-deleted {deleted_count} non-curated agents.")
            )
        else:
            updated = qs.update(status="INACTIVE")
            self.stdout.write(
                self.style.WARNING(f"Marked {updated} non-curated agents as INACTIVE.")
            )

    def _read_prompt(self, base_dir: Path, rel_path: str) -> str:
        path = base_dir / rel_path
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except Exception:
                return DEFAULT_SYSTEM_PROMPT
        return DEFAULT_SYSTEM_PROMPT

    def _seed_curated(self, base_dir: Path) -> tuple[int, int]:
        created = 0
        updated = 0
        for name, cfg in CURATED.items():
            agent_type = cfg["agent_type"]
            prompt = self._read_prompt(base_dir, cfg["prompt_file"])
            defaults = {
                "status": "ACTIVE",
                "description": cfg["description"],
                "system_prompt": prompt,
                "instructions": None,
                "creativity_level": 0.70,
                "consistency_weight": 0.60,
            }
            obj, was_created = Agents.objects.update_or_create(
                agent_type=agent_type,
                defaults={
                    **defaults,
                    "name": name,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return created, updated
