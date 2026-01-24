from pathlib import Path
from typing import Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bfagent.models import Agents

# Paths to prompt templates
BASE_DIR = Path(__file__).resolve().parents[5]
PROMPTS_DIR = BASE_DIR / "memory-bank" / "agent-prompts"

PROMPT_FILES = {
    "writer": PROMPTS_DIR / "writer_agent.md",
    "editor": PROMPTS_DIR / "editor_agent.md",
    "planner": PROMPTS_DIR / "planner_agent.md",
}


def read_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        # Fallback minimal prompt
        return (
            "You are an AI agent. Follow instructions carefully, return concise, structured output."
        )


def upsert_agent(name: str, agent_type: str, system_prompt: str) -> Tuple[Agents, bool]:
    defaults = {
        "status": "active",
        "description": f"Default {agent_type} agent",
        "system_prompt": system_prompt,
        "instructions": None,
        "llm_model_id": None,
        "creativity_level": 0.7,
        "consistency_weight": 0.5,
    }
    obj, created = Agents.objects.update_or_create(
        name=name,
        agent_type=agent_type,
        defaults=defaults,
    )
    return obj, created


class Command(BaseCommand):
    help = (
        "Seed default Agents (Writer, Editor, Planner) with prompts from memory-bank/agent-prompts"
    )

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for agent_type, file_path in PROMPT_FILES.items():
            prompt = read_prompt(file_path)
            name = f"{agent_type.capitalize()} Agent"
            agent, created = upsert_agent(name=name, agent_type=agent_type, system_prompt=prompt)
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded default agents. Created: {created_count}, Updated: {updated_count}"
            )
        )
