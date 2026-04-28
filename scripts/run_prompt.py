#!/home/adehnert/CascadeProjects/platform/.venv/bin/python
"""run_prompt.py — Generiert optimierten Prompt via Groq (kostenlos) oder Template-Fallback.

Abhängigkeit: litellm kommt via aifw (bereits im platform-Venv) — kein pip install nötig.
Alternativ: python3 -c direkt mit venv: .venv/bin/python run_prompt.py

Usage (vom /prompt Workflow aufgerufen):
    .venv/bin/python run_prompt.py \\
        --repo risk-hub \\
        --instruction "fix Login-Bug: redirect nach /dashboard" \\
        --context-file /tmp/project-facts.md \\
        --affected-files "src/identity/views.py,src/identity/services.py" \\
        [--task-type bugfix]

Env:
    GROQ_API_KEY  — optional, aus ~/.secrets/groq_api_key
                    Ohne Key: Template-basierter Fallback (keine LLM-Kosten)

Venv-Aufruf (empfohlen):
    ${GITHUB_DIR:-~/CascadeProjects}/platform/.venv/bin/python run_prompt.py ...

Cost:
    Mit Groq Llama-3.3-70B: ~0.000 USD (Free Tier: 14.400 req/day)
    Ohne Groq: 0 USD, aber weniger kontextsensitiver Output
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Groq via litellm (optional — graceful fallback if not available)
# ---------------------------------------------------------------------------

def _call_groq(system_prompt: str, user_prompt: str, api_key: str) -> str | None:
    try:
        import litellm  # noqa: PLC0415
        resp = litellm.completion(
            model="groq/llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=api_key,
            max_tokens=2048,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        print(f"[run_prompt] Groq-Fehler: {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# System prompt for Groq
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Du bist ein technischer Prompt-Architekt für das IIL Platform-Ökosystem (Django 5, PostgreSQL 16, HTMX).

Deine Aufgabe: Aus einer Repo-Anweisung + Kontext einen VOLLSTÄNDIGEN, SELBSTENTHALTENDEN Prompt generieren.

AUTORITATIVE AUSGABE-STRUKTUR (exakt einhalten, Markdown-Formatierung Pflicht):

```markdown
# [task_type]: [kurzer Titel]

> Selbstenthaltender Prompt — kein separater Session-Kontext nötig.
> Repo: achimdehnert/[REPO] · Stand: [DATUM]

---

## Kontext

**Repo:** `[REPO]` · Pfad: `${GITHUB_DIR:-~/CascadeProjects}/[REPO]`  
**Settings (Prod):** `[exakter Wert aus project-facts.md]`  
**Settings (Test):** `[exakter Wert aus project-facts.md]`  
**HTMX-Detection:** `[exakter Wert aus project-facts.md — NICHT raten]`  
**pythonpath:** `[Wert]/`

---

## Aufgabe

**Ziel:** [ausführliche Beschreibung]

**Betroffene Dateien:**
- `[konkreter Pfad]`

**Schritt-für-Schritt:**
1. [konkreter Schritt]
2. ...

---

## Constraints (NICHT verhandelbar)

### Service-Layer (ADR-009)
```python
# CORRECT — views.py
def my_view(request):
    result = service.do_something(...)
    return render(request, \"...\", {\"result\": result})
# BANNED: Model.objects. in views.py
```

[weitere Constraints je nach task_type]

---

## Akzeptanzkriterien

- [ ] [messbar — kein \"es funktioniert\"]
- [ ] Service-Layer-Grenze eingehalten
- [ ] ruff check grün

---

## Verboten

- Model.objects. in views.py
- [weitere]
```

Pflichtregeln:
- Keine Platzhalter [TODO] wenn echte Daten aus project-facts.md vorhanden
- Checkboxen `- [ ]` in Akzeptanzkriterien sind PFLICHT
- Code-Blocks mit korrekter Sprache
- Auf Deutsch
- KEIN Fließtext — nur strukturierte Abschnitte"""


# ---------------------------------------------------------------------------
# Template fallback (no LLM needed)
# ---------------------------------------------------------------------------

def _build_template(
    repo: str,
    instruction: str,
    task_type: str,
    context: str,
    affected_files: list[str],
    today: str,
) -> str:
    # Parse key fields from context (project-facts.md)
    def _extract(key: str, default: str = "[TODO]") -> str:
        for line in context.splitlines():
            if key.lower() in line.lower() and "**" in line:
                parts = line.split("`")
                if len(parts) >= 2:
                    return parts[1]
        return default

    htmx = _extract("HTMX-Detection", 'request.headers.get("HX-Request")')
    settings_prod = _extract("Prod-Modul", "[TODO: Settings-Modul prüfen]")
    settings_test = _extract("Test-Modul", "[TODO: Test-Settings]")
    prod_url = _extract("Prod-URL", "")
    port = _extract("Port", "8000")
    db = _extract("DB-Name", repo.replace("-", "_"))
    pythonpath = _extract("pythonpath", ".")

    # Apps
    apps_lines = [
        line.strip().lstrip("- ").strip("`")
        for line in context.splitlines()
        if line.strip().startswith("- `") and "/" not in line and "**" not in line
    ]

    files_block = "\n".join(f"- `{f}`" for f in affected_files) if affected_files else "- [TODO: relevante Dateien ermitteln]"

    task_extra = ""
    criteria_extra = ""
    if task_type == "bugfix":
        task_extra = "\n5. Regression-Test schreiben: `test_should_[was-gefixed-wurde]`"
        criteria_extra = "\n- [ ] Regression-Test vorhanden und grün"
    elif task_type == "feature":
        task_extra = "\n5. Migration erstellen: `python manage.py makemigrations`"
        criteria_extra = "\n- [ ] Migration vorhanden + `migrate --check` grün"
    elif task_type == "refactor":
        criteria_extra = "\n- [ ] Alle bestehenden Tests weiter grün"

    htmx_block = ""
    if any(w in instruction.lower() for w in ("template", "htmx", "form", "button", "view", "html")):
        htmx_block = f"""
### HTMX (ADR-048)
- IMMER: `hx-target` + `hx-swap` + `hx-indicator` (alle drei, keine Ausnahme)
- IMMER: `data-testid` auf interaktiven Elementen
- Partials: kein `{{% extends %}}`, kein `<html>`
- Detection in diesem Repo: `{htmx}`
"""

    return f"""# {task_type.capitalize()}: {instruction.strip('"')}

> Selbstenthaltender Prompt — kein separater Session-Kontext nötig.
> Repo: achimdehnert/{repo} · Stand: {today}

---

## Kontext

**Repo:** `{repo}` · Pfad: `${{GITHUB_DIR:-~/CascadeProjects}}/{repo}`
**Settings (Prod):** `{settings_prod}`
**Settings (Test):** `{settings_test}`
**Prod-URL:** `https://{prod_url}` · Port: `{port}` · DB: `{db}`
**HTMX-Detection:** `{htmx}`
**pythonpath:** `{pythonpath.rstrip('/')}/`

**Apps:** {", ".join(f"`{a}`" for a in apps_lines[:8])}{"..." if len(apps_lines) > 8 else ""}

---

## Aufgabe

**Ziel:** {instruction}

**Betroffene Dateien (Analyse-Pflicht vor Implementierung):**
{files_block}

**Schritt-für-Schritt:**
1. Betroffene Dateien lesen + Root Cause analysieren
2. Fix/Implementation in Service-Layer (`services.py`)
3. View nur für HTTP/Response — kein ORM
4. Template anpassen falls nötig{task_extra}

---

## Constraints (NICHT verhandelbar)

### Service-Layer (ADR-009) — CRITICAL
```python
# CORRECT — views.py
def my_view(request):
    result = my_service.do_something(...)
    return render(request, "...", {{"result": result}})

# BANNED in views.py:
# Model.objects.filter(...)  ← ORM in view
# model.save()               ← ORM in view
```

### Database-First
- `BigAutoField` PKs — NIEMALS `UUIDField(primary_key=True)`
- Kein `JSONField()` für strukturierte Daten
{htmx_block}
---

## Akzeptanzkriterien

- [ ] {instruction.strip('"')} funktioniert korrekt
- [ ] Service-Layer-Grenze eingehalten (kein ORM in views.py)
- [ ] `ruff check {pythonpath.rstrip('/')}/ && ruff format --check {pythonpath.rstrip('/')}/ ` — grün
- [ ] Kein `print()` — `logging.getLogger(__name__)` stattdessen{criteria_extra}

---

## Verboten

- `Model.objects.` direkt in `views.py`
- `UUIDField(primary_key=True)`
- `except:` ohne Exception-Typ
- `unittest.TestCase`
- Hardcoded Secrets / IPs
"""


# ---------------------------------------------------------------------------
# Complexity estimate
# ---------------------------------------------------------------------------

def _estimate_complexity(instruction: str, affected_files: list[str]) -> str:
    keywords_complex = ["refactor", "migrate", "architecture", "new model", "neues model",
                        "service", "celery", "async", "api"]
    keywords_simple = ["fix", "bug", "typo", "rename", "text", "farbe", "color"]
    instr = instruction.lower()
    if any(k in instr for k in keywords_complex) or len(affected_files) > 4:
        return "COMPLEX → empfehle `/agentic-coding` für vollständigen Plan + Gate-Checks"
    if any(k in instr for k in keywords_simple):
        return "SIMPLE → direkt implementieren"
    return "MODERATE → direkt implementieren, Regressions-Test nicht vergessen"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    from datetime import date  # noqa: PLC0415

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--context-file", default="")
    parser.add_argument("--affected-files", default="")
    parser.add_argument("--task-type", default="feature")
    args = parser.parse_args()

    today = date.today().isoformat()
    context = Path(args.context_file).read_text() if args.context_file and Path(args.context_file).exists() else ""
    affected = [f.strip() for f in args.affected_files.split(",") if f.strip()]

    # Load Groq key
    api_key = (
        os.environ.get("GROQ_API_KEY")
        or Path.home().joinpath(".secrets/groq_api_key").read_text().strip()
        if Path.home().joinpath(".secrets/groq_api_key").exists() else ""
    )

    result = None
    if api_key:
        user_msg = f"""Repo: {args.repo}
Task-Type: {args.task_type}
Instruction: {args.instruction}
Affected Files: {', '.join(affected) or 'noch nicht bekannt'}
Date: {today}

--- project-facts.md ---
{context[:3000] if context else '[nicht verfügbar]'}
"""
        print("[run_prompt] Rufe Groq Llama-3.3-70B...", file=sys.stderr)
        result = _call_groq(SYSTEM_PROMPT, user_msg, api_key)

    if not result:
        print("[run_prompt] Fallback: Template-Generierung", file=sys.stderr)
        result = _build_template(args.repo, args.instruction, args.task_type, context, affected, today)

    # Complexity hint
    complexity = _estimate_complexity(args.instruction, affected)
    result += f"\n---\n\n> **Komplexität:** {complexity}\n"

    print(result)


if __name__ == "__main__":
    main()
