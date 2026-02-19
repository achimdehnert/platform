"""
agents/onboarding_coach.py — Onboarding Coach (Agent A5)

Interaktiver Onboarding-Assistent für neue Teammitglieder:
  - 5 Module (M1..M5) mit Themen und Übungen
  - Fortschritts-Tracking pro Benutzer
  - Kontext-Anreicherung aus bestehenden Docs/ADRs
  - Quiz-Fragen zur Wissensüberprüfung

Nutzung:
  python -m agents.onboarding_coach --list-modules
  python -m agents.onboarding_coach --module M1
  python -m agents.onboarding_coach --quiz M1
  python -m agents.onboarding_coach --progress

Gate-Integration:
  Onboarding → Gate 0 (AUTONOMOUS — reines Lese-/Erklärungs-Tool)
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("onboarding_coach")


@dataclass
class Exercise:
    """Eine Übungsaufgabe."""

    id: str
    instruction: str
    hint: str | None = None
    verification: str | None = None


@dataclass
class QuizQuestion:
    """Eine Quiz-Frage."""

    question: str
    options: list[str]
    correct: int
    explanation: str


@dataclass
class Module:
    """Ein Onboarding-Modul."""

    id: str
    title: str
    duration: str
    topics: list[str]
    content: str
    exercises: list[Exercise] = field(default_factory=list)
    quiz: list[QuizQuestion] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.id}: {self.title}",
            f"\n**Dauer:** {self.duration}",
            f"**Themen:** {', '.join(self.topics)}\n",
            "---\n",
            self.content,
        ]

        if self.exercises:
            lines.append("\n## Übungen\n")
            for i, ex in enumerate(self.exercises, 1):
                lines.append(f"### Übung {i}: {ex.id}\n")
                lines.append(f"{ex.instruction}\n")
                if ex.hint:
                    lines.append(
                        f"> **Hinweis:** {ex.hint}\n"
                    )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "duration": self.duration,
            "topics": self.topics,
            "exercises": len(self.exercises),
            "quiz_questions": len(self.quiz),
        }


MODULES: list[Module] = [
    Module(
        id="M1",
        title="Platform-Überblick",
        duration="30min",
        topics=[
            "Architektur", "Prinzipien P-001..P-005",
            "Service-Map",
        ],
        content="""\
## Willkommen zur Platform!

Die Platform besteht aus mehreren Django-Applikationen,
die auf einem gemeinsamen Hetzner-Server (88.198.191.108)
laufen. Jede App hat eine eigene PostgreSQL-Datenbank
und wird per Docker Compose orchestriert.

### Aktive Projekte

| Projekt | Beschreibung | URL |
|---------|-------------|-----|
| **risk-hub** (Schutztat) | Arbeitsschutz SaaS | schutztat.de |
| **bfagent** | Book Factory Agent | bfagent.iil.pet |
| **travel-beat** (DriftTales) | Reise-Stories | drifttales.app |
| **weltenhub** (Weltenforger) | Story-Universen | weltenforger.com |
| **mcp-hub** | MCP Server Collection | — |
| **platform** | Shared Packages, ADRs | — |

### 5 Architektur-Prinzipien

1. **P-001 Database-First** — Jede Änderung beginnt
   mit dem Datenmodell
2. **P-002 Zero Breaking Changes** — Expand/Contract
   Pattern, nie bestehende APIs entfernen
3. **P-003 Tenant-Isolation** — Jedes Model hat
   `tenant_id = UUIDField(db_index=True)`
4. **P-004 Minimal Diff** — PRs < 400 Zeilen,
   Feature-Branches für große Änderungen
5. **P-005 Service Layer** — views.py → services.py
   → models.py (Separation of Concerns)
""",
        exercises=[
            Exercise(
                id="platform-overview",
                instruction=(
                    "Frage den Query Agent: "
                    "'Was sind die 5 Architekturprinzipien?'"
                ),
                hint="Nutze @query-agent-mcp in Windsurf",
            ),
            Exercise(
                id="service-map",
                instruction=(
                    "Öffne https://bfagent.iil.pet und "
                    "https://drifttales.app im Browser. "
                    "Notiere dir die Gemeinsamkeiten im UI."
                ),
            ),
        ],
        quiz=[
            QuizQuestion(
                question=(
                    "Welches Prinzip verlangt, dass jedes "
                    "Model ein tenant_id Feld hat?"
                ),
                options=[
                    "P-001 Database-First",
                    "P-002 Zero Breaking Changes",
                    "P-003 Tenant-Isolation",
                    "P-004 Minimal Diff",
                ],
                correct=2,
                explanation=(
                    "P-003 Tenant-Isolation: Jedes "
                    "User-Data-Model MUSS "
                    "`tenant_id = UUIDField(db_index=True)` "
                    "haben."
                ),
            ),
            QuizQuestion(
                question=(
                    "Wo liegt die Grenze für PR-Größe "
                    "(Prinzip P-004)?"
                ),
                options=[
                    "100 Zeilen",
                    "200 Zeilen",
                    "400 Zeilen",
                    "1000 Zeilen",
                ],
                correct=2,
                explanation=(
                    "P-004 Minimal Diff: PRs sollten < 400 "
                    "geänderte Zeilen haben."
                ),
            ),
        ],
    ),
    Module(
        id="M2",
        title="Lokale Entwicklungsumgebung",
        duration="45min",
        topics=[
            "Git Clone", "Docker Compose",
            "Erste Migration",
        ],
        content="""\
## Entwicklungsumgebung einrichten

### Voraussetzungen

- WSL2 (Ubuntu) oder native Linux
- Docker + Docker Compose
- Python 3.12+
- Git mit SSH-Key (github_ed25519)

### Projekt klonen

```bash
cd ~/github
git clone git@github.com:achimdehnert/travel-beat.git
cd travel-beat
```

### Docker Compose starten

```bash
# Lokale Entwicklung
docker compose -f docker-compose.prod.yml up -d

# Logs prüfen
docker logs travel_beat_web --tail 20
```

### Wichtige Konventionen

- **Settings**: `config.settings.base` (split: base/dev/prod)
- **Apps**: `apps/<app_name>/` (snake_case)
- **Templates**: `templates/<app>/` (NOT per-app)
- **Tests**: `pytest` mit `@pytest.mark.django_db`
- **Imports**: isort, ruff für Linting
""",
        exercises=[
            Exercise(
                id="clone-project",
                instruction=(
                    "Klone travel-beat und starte die "
                    "Docker-Container lokal."
                ),
                hint=(
                    "Nutze `docker compose -f "
                    "docker-compose.prod.yml up -d`"
                ),
                verification=(
                    "curl http://localhost:8000/health/ "
                    "sollte 200 zurückgeben"
                ),
            ),
        ],
        quiz=[
            QuizQuestion(
                question=(
                    "Wo liegt die Django-Settings-Datei "
                    "in Platform-Projekten?"
                ),
                options=[
                    "settings.py im Root",
                    "config/settings/base.py",
                    "apps/core/settings.py",
                    "django/settings.py",
                ],
                correct=1,
                explanation=(
                    "Platform-Konvention: Settings in "
                    "`config/settings/base.py` "
                    "(split: base/development/production)"
                ),
            ),
        ],
    ),
    Module(
        id="M3",
        title="Deployment verstehen",
        duration="30min",
        topics=[
            "CI/CD Pipeline", "Docker Build",
            "Health Checks",
        ],
        content="""\
## Deployment-Workflow

### Pipeline

```text
git push origin main
    → docker build -f docker/Dockerfile
    → docker push ghcr.io/achimdehnert/<app>:latest
    → SSH: docker compose pull + up -d --force-recreate
    → Health Check: curl https://<app-domain>/health/
```

### Server

- **Host**: 88.198.191.108 (Hetzner)
- **SSH**: `ssh root@88.198.191.108`
- **Reverse Proxy**: Nginx + Let's Encrypt TLS
- **Registry**: GHCR (ghcr.io/achimdehnert/)

### Docker-Konventionen

- `Dockerfile` in `docker/app/` oder Projekt-Root
- `docker-compose.prod.yml` im Projekt-Root
- `.env.prod` für Umgebungsvariablen (nie committen!)
- `env_file: .env.prod` statt `${VAR}` Interpolation

### Deployment MCP

Das `deployment-mcp` bietet Tools für:
- `docker_manage`: Container-Verwaltung
- `ssh_manage`: Remote-Befehle
- `database_manage`: PostgreSQL-Operationen
- `cicd_manage`: GitHub Actions
""",
        exercises=[
            Exercise(
                id="check-deployment",
                instruction=(
                    "Prüfe den Health-Status aller "
                    "deployten Services mit dem "
                    "deployment-mcp."
                ),
                hint="Nutze /health Workflow in Windsurf",
            ),
        ],
        quiz=[
            QuizQuestion(
                question=(
                    "Welche Container-Registry wird "
                    "für Docker-Images genutzt?"
                ),
                options=[
                    "Docker Hub",
                    "AWS ECR",
                    "GHCR (GitHub Container Registry)",
                    "Hetzner Registry",
                ],
                correct=2,
                explanation=(
                    "Alle Images liegen unter "
                    "`ghcr.io/achimdehnert/<app>:latest`"
                ),
            ),
        ],
    ),
    Module(
        id="M4",
        title="AI-Tools & MCP",
        duration="30min",
        topics=[
            "Windsurf Setup", "Query Agent",
            "Deployment MCP",
        ],
        content="""\
## AI-gestützte Entwicklung

### MCP Server (Model Context Protocol)

Die Platform nutzt MCP Server für AI-gestützte
Entwicklung in Windsurf:

| MCP Server | Funktion |
|------------|----------|
| **deployment-mcp** | Server, Docker, DB, CI/CD |
| **orchestrator-mcp** | Task-Routing, Gates, Audit |
| **llm-mcp** | LLM-Generierung (Multi-Model) |
| **query-agent-mcp** | RAG über Platform-Docs |
| **github** | Repository-Operationen |
| **filesystem** | Dateisystem-Zugriff |

### Orchestrator Gate-System

| Gate | Freigabe | Beispiel |
|------|----------|----------|
| 0 | Auto | Docs abfragen |
| 1 | Auto + Notify | PR-Kommentar posten |
| 2 | Human Approval | PR blocken |
| 3 | Team Review | ADR vorschlagen |
| 4 | Governance Board | Architektur ändern |

### Platform Agents

| Agent | Funktion |
|-------|----------|
| A1: Query Agent | Semantische Docs-Suche |
| A2: Guardian | PR-Architektur-Check |
| A3: ADR Scribe | ADR-Draft-Generator |
| A4: Drift Detector | Docs-Freshness |
| A5: Coach | Onboarding (dieses Tool!) |
| A6: Reviewer | PR-Kontext-Review |
""",
        exercises=[
            Exercise(
                id="query-agent",
                instruction=(
                    "Frage den Query Agent: "
                    "'Wie funktioniert Tenant-Isolation?'"
                ),
                hint=(
                    "Nutze @query-agent-mcp query_docs "
                    "in Windsurf"
                ),
            ),
        ],
        quiz=[
            QuizQuestion(
                question=(
                    "Welcher Gate-Level erfordert "
                    "Human Approval?"
                ),
                options=[
                    "Gate 0",
                    "Gate 1",
                    "Gate 2",
                    "Gate 4",
                ],
                correct=2,
                explanation=(
                    "Gate 2 (APPROVE): AI schlägt vor, "
                    "Mensch genehmigt vor Ausführung."
                ),
            ),
        ],
    ),
    Module(
        id="M5",
        title="Erster eigener PR",
        duration="45min",
        topics=[
            "Feature Branch", "PR Guidelines",
            "Guardian Check",
        ],
        content="""\
## Deinen ersten PR erstellen

### Branch-Konvention

```bash
git checkout -b feat/my-first-change
```

Prefixe: `feat/`, `fix/`, `refactor/`, `docs/`

### Commit-Messages

```text
feat: add user profile page
fix: correct tenant filter in dashboard
refactor: extract service layer from views
docs: update deployment runbook
```

### PR-Checkliste

- [ ] Branch von `main` erstellt
- [ ] Tests geschrieben (`test_should_*`)
- [ ] Linting bestanden (`ruff check .`)
- [ ] Migration erstellt (falls Model geändert)
- [ ] PR < 400 Zeilen (Prinzip P-004)
- [ ] Beschreibung: Was, Warum, Wie

### Was passiert nach dem PR?

1. **Architecture Guardian** prüft automatisch:
   - G-001: Migration vorhanden?
   - G-002: API-Signatur geändert?
   - G-003: tenant_id vorhanden?
   - G-004: PR-Größe OK?
2. **Context Reviewer** fügt Kontext-Kommentare hinzu
3. **Human Review** durch Teammitglied
4. **Merge** via Squash-and-Merge
""",
        exercises=[
            Exercise(
                id="first-pr",
                instruction=(
                    "Erstelle einen PR mit einer kleinen "
                    "Docs-Änderung in einem beliebigen "
                    "Projekt. Beobachte den Guardian-Check."
                ),
                hint=(
                    "Ändere z.B. eine Typo-Korrektur "
                    "in einer README.md"
                ),
                verification=(
                    "PR ist auf GitHub sichtbar und "
                    "Guardian hat kommentiert"
                ),
            ),
        ],
        quiz=[
            QuizQuestion(
                question=(
                    "Welcher Commit-Prefix wird für "
                    "neue Features verwendet?"
                ),
                options=[
                    "fix:",
                    "feat:",
                    "new:",
                    "add:",
                ],
                correct=1,
                explanation=(
                    "Konvention: `feat:` für neue "
                    "Features, `fix:` für Bugfixes."
                ),
            ),
        ],
    ),
]

MODULE_MAP: dict[str, Module] = {m.id: m for m in MODULES}


@dataclass
class OnboardingProgress:
    """Fortschritt eines Benutzers."""

    completed_modules: list[str] = field(
        default_factory=list,
    )
    quiz_scores: dict[str, float] = field(
        default_factory=dict,
    )

    @property
    def completion_pct(self) -> float:
        if not MODULES:
            return 0.0
        return (
            len(self.completed_modules) / len(MODULES)
        ) * 100

    def to_markdown(self) -> str:
        lines = [
            "# Onboarding Fortschritt\n",
            f"**Abgeschlossen:** "
            f"{len(self.completed_modules)}/{len(MODULES)} "
            f"Module ({self.completion_pct:.0f}%)\n",
        ]

        for m in MODULES:
            done = m.id in self.completed_modules
            icon = "✅" if done else "⬜"
            score = self.quiz_scores.get(m.id)
            score_str = (
                f" (Quiz: {score:.0f}%)" if score else ""
            )
            lines.append(
                f"- {icon} **{m.id}**: "
                f"{m.title} ({m.duration}){score_str}"
            )

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed": self.completed_modules,
            "total_modules": len(MODULES),
            "completion_pct": self.completion_pct,
            "quiz_scores": self.quiz_scores,
        }


def run_quiz(module_id: str) -> float:
    """Führt ein Quiz durch und gibt die Score zurück."""
    module = MODULE_MAP.get(module_id)
    if not module or not module.quiz:
        return 0.0

    correct = 0
    total = len(module.quiz)

    print(f"\n## Quiz: {module.title}\n")
    for i, q in enumerate(module.quiz, 1):
        print(f"**Frage {i}:** {q.question}\n")
        for j, opt in enumerate(q.options):
            print(f"  {j + 1}. {opt}")
        print()

        try:
            answer = int(input("Deine Antwort (1-4): ")) - 1
        except (ValueError, EOFError):
            answer = -1

        if answer == q.correct:
            print(f"✅ Richtig! {q.explanation}\n")
            correct += 1
        else:
            right = q.options[q.correct]
            print(
                f"❌ Falsch. Richtig: {right}\n"
                f"   {q.explanation}\n"
            )

    score = (correct / total) * 100 if total > 0 else 0
    print(f"\n**Ergebnis:** {correct}/{total} ({score:.0f}%)")
    return score


def list_modules_markdown() -> str:
    """Listet alle Module als Markdown."""
    lines = [
        "# Onboarding Curriculum\n",
        "**Gesamtdauer:** ~3 Stunden\n",
    ]
    for m in MODULES:
        lines.append(
            f"- **{m.id}: {m.title}** ({m.duration}) — "
            f"{', '.join(m.topics)}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Onboarding Coach — "
            "Interaktiver Onboarding-Assistent"
        ),
    )
    parser.add_argument(
        "--list-modules", action="store_true",
        help="Alle Module auflisten",
    )
    parser.add_argument(
        "--module", type=str, default=None,
        choices=[m.id for m in MODULES],
        help="Bestimmtes Modul anzeigen",
    )
    parser.add_argument(
        "--quiz", type=str, default=None,
        choices=[m.id for m in MODULES],
        help="Quiz für ein Modul starten",
    )
    parser.add_argument(
        "--format", choices=["markdown", "json"],
        default="markdown",
    )
    args = parser.parse_args()

    if args.list_modules:
        if args.format == "json":
            data = [m.to_dict() for m in MODULES]
            print(json.dumps(data, indent=2))
        else:
            print(list_modules_markdown())

    elif args.module:
        module = MODULE_MAP[args.module]
        if args.format == "json":
            print(json.dumps(module.to_dict(), indent=2))
        else:
            print(module.to_markdown())

    elif args.quiz:
        run_quiz(args.quiz)

    else:
        print(list_modules_markdown())

    sys.exit(0)


if __name__ == "__main__":
    main()
