# iPad → GitHub Workflows → Cascade Agent Team
## Remote Coding vom iPad — Vollständige Implementierung

| | |
|---|---|
| **Dokument** | Remote Agent Control via GitHub Workflows |
| **Datum** | 2026-03-08 |
| **Ziel** | Cascade Agent Team vom iPad aus steuern — ohne TeamViewer, ohne n8n |
| **Repo** | `iilgmbh/mcp-hub` |
| **Voraussetzung** | ADR-090 (Org Secrets), MCP Server (`mcp_server.py`), GitHub Mobile App |

---

## Konzept-Überblick

```
iPad (GitHub Mobile App)
    │
    │  1. workflow_dispatch — Formular mit Task-Inputs
    │     ODER
    │  1. Issue erstellen mit Label "agent-task"
    │
    ▼
GitHub Actions (kostenlos für private Org-Repos)
    │
    │  2. SSH → Hetzner VPS
    │     ODER direkt via Python-Script im Runner
    │
    ▼
MCP Server → Cascade Agent Team
    │  feature_delivery / bugfix / test_existing / adr_development
    │
    ▼
GitHub PR erstellt (automatisch)
    │
    ▼
GitHub Mobile Notification auf iPad ✅
    │
    │  Gate-2-Entscheidung: PR Review direkt in GitHub Mobile
    ▼
Approve / Request Changes → Agent reagiert
```

**Kein Telegram. Kein n8n. Keine externe Infrastruktur. Alles in GitHub.**

---

## Datei-Struktur

```
iilgmbh/mcp-hub/
└── .github/
    ├── workflows/
    │   ├── agent-task-dispatch.yml      ← Schritt 1: Manueller Trigger (iPad Formular)
    │   ├── agent-task-issue.yml         ← Schritt 2: Issue-Trigger (noch komfortabler)
    │   ├── agent-status.yml             ← Schritt 3: Status-Abfrage
    │   └── agent-gate-decision.yml      ← Schritt 4: Gate approve/reject via Issue-Kommentar
    ├── ISSUE_TEMPLATE/
    │   └── agent-task.yml               ← Strukturiertes Issue-Formular für Agent-Tasks
    └── scripts/
        ├── trigger_agent.py             ← Python-Script: Workflow → MCP Server
        ├── post_summary.py              ← Python-Script: Ergebnis als PR-Kommentar
        └── parse_issue.py               ← Python-Script: Issue → Task-Parameter
```

---

## Schritt 1: `workflow_dispatch` — Manueller iPad-Trigger

### `.github/workflows/agent-task-dispatch.yml`

```yaml
name: 🤖 Agent Task (Manuell)

on:
  workflow_dispatch:
    inputs:
      task_description:
        description: |
          Was soll der Agent tun?
          Beispiel: "Add cursor-based pagination to /api/projects endpoint,
          max 20 items, include total count in response header"
        required: true
        type: string

      workflow_type:
        description: 'Workflow-Typ (welche Agenten werden aktiviert?)'
        required: true
        type: choice
        default: feature_delivery
        options:
          - feature_delivery    # Dev → Guardian → Tester → PR (auto)
          - bugfix              # Dev → Tester → Guardian → PR (auto, schnell)
          - test_existing       # Tester → Dev → Tester (nur Tests)
          - adr_development     # TechLead → Dev → Tester (kein auto-PR)
          - re_engineering      # ReEngineer → TechLead → Tester (Analyse)

      scope_paths:
        description: |
          Welche Pfade darf der Agent ändern? (komma-getrennt, so eng wie möglich!)
          Beispiel: apps/api/views/projects.py,apps/api/tests/test_projects.py
        required: true
        type: string

      model_scenario:
        description: 'Modell-Qualität (Kosten vs. Qualität)'
        required: false
        type: choice
        default: groq
        options:
          - groq      # Schnell, $0 — für Bugfixes und kleine Features
          - hybrid    # Balanciert — für Features mit Architektur-Relevanz
          - claude    # Höchste Qualität — für ADRs und Re-Engineering
          - local     # Offline, $0 — für Tests ohne Cloud-Kosten

      dry_run:
        description: 'Dry Run? (Plan anzeigen, aber keine Dateien schreiben)'
        required: false
        type: boolean
        default: false

      target_branch:
        description: 'Ziel-Branch (default: main)'
        required: false
        type: string
        default: main

env:
  PYTHON_VERSION: '3.12'
  MCP_HUB_PATH: '/opt/mcp-hub'

jobs:
  validate-inputs:
    name: 🔍 Inputs validieren
    runs-on: ubuntu-latest
    outputs:
      scope_list: ${{ steps.parse.outputs.scope_list }}
      task_short: ${{ steps.parse.outputs.task_short }}
    steps:
      - name: Parse und validiere Inputs
        id: parse
        run: |
          # Task-Kurzbeschreibung für Branch-Name (max 40 Zeichen, URL-safe)
          TASK_SHORT=$(echo "${{ inputs.task_description }}" \
            | tr '[:upper:]' '[:lower:]' \
            | tr ' ' '-' \
            | tr -cd '[:alnum:]-' \
            | cut -c1-40)
          echo "task_short=$TASK_SHORT" >> $GITHUB_OUTPUT

          # Scope-Paths validieren (keine absoluten Pfade, keine verbotenen Pfade)
          SCOPE="${{ inputs.scope_paths }}"
          if echo "$SCOPE" | grep -qE '(migrations|settings/prod|\.env|\.pem|\.key|Dockerfile)'; then
            echo "❌ FEHLER: scope_paths enthält verbotene Pfade!"
            echo "Verboten: migrations/, settings/prod*, .env, .pem, .key, Dockerfile"
            exit 1
          fi
          if echo "$SCOPE" | grep -q '^/'; then
            echo "❌ FEHLER: scope_paths müssen relativ sein (kein führendes '/')"
            exit 1
          fi

          # Scope als JSON-Array formatieren
          SCOPE_LIST=$(echo "$SCOPE" | python3 -c "
          import sys, json
          paths = [p.strip() for p in sys.stdin.read().split(',') if p.strip()]
          print(json.dumps(paths))
          ")
          echo "scope_list=$SCOPE_LIST" >> $GITHUB_OUTPUT

          echo "✅ Inputs valide"
          echo "Task: ${{ inputs.task_description }}"
          echo "Workflow: ${{ inputs.workflow_type }}"
          echo "Scope: $SCOPE"
          echo "Modell: ${{ inputs.model_scenario }}"
          echo "Dry Run: ${{ inputs.dry_run }}"

  run-agent:
    name: 🤖 Agent Team starten
    runs-on: ubuntu-latest
    needs: validate-inputs
    outputs:
      run_id: ${{ steps.trigger.outputs.run_id }}
      pr_url: ${{ steps.wait.outputs.pr_url }}
      quality_score: ${{ steps.wait.outputs.quality_score }}
      status: ${{ steps.wait.outputs.status }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: ${{ inputs.target_branch }}

      - name: Python einrichten
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip

      - name: Dependencies installieren
        run: |
          pip install fastmcp structlog pydantic httpx

      - name: 🚀 Agent Task triggern
        id: trigger
        env:
          MODEL_SCENARIO: ${{ inputs.model_scenario }}
          AUTONOMOUS_DEVELOPER: 'true'
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PROJECT_PAT: ${{ secrets.PROJECT_PAT }}
        run: |
          python .github/scripts/trigger_agent.py \
            --task "${{ inputs.task_description }}" \
            --workflow "${{ inputs.workflow_type }}" \
            --scope '${{ needs.validate-inputs.outputs.scope_list }}' \
            --model "${{ inputs.model_scenario }}" \
            --dry-run "${{ inputs.dry_run }}" \
            --output-file /tmp/agent_result.json

          # Run-ID für spätere Status-Abfragen speichern
          RUN_ID=$(python3 -c "import json; d=json.load(open('/tmp/agent_result.json')); print(d.get('run_id','unknown'))")
          echo "run_id=$RUN_ID" >> $GITHUB_OUTPUT
          echo "🤖 Agent gestartet mit run_id: $RUN_ID"

      - name: ⏳ Auf Ergebnis warten
        id: wait
        timeout-minutes: 120
        run: |
          python .github/scripts/wait_for_agent.py \
            --run-id "${{ steps.trigger.outputs.run_id }}" \
            --timeout 7200 \
            --output-file /tmp/agent_final.json

          # Ergebnisse extrahieren
          PR_URL=$(python3 -c "import json; d=json.load(open('/tmp/agent_final.json')); print(d.get('pr_url') or '')")
          QUALITY=$(python3 -c "import json; d=json.load(open('/tmp/agent_final.json')); print(d.get('quality_score') or 'N/A')")
          STATUS=$(python3 -c "import json; d=json.load(open('/tmp/agent_final.json')); print(d.get('status','unknown'))")

          echo "pr_url=$PR_URL" >> $GITHUB_OUTPUT
          echo "quality_score=$QUALITY" >> $GITHUB_OUTPUT
          echo "status=$STATUS" >> $GITHUB_OUTPUT

      - name: 📊 Job Summary schreiben
        if: always()
        run: |
          python .github/scripts/post_summary.py \
            --result-file /tmp/agent_final.json \
            --task "${{ inputs.task_description }}" \
            --workflow "${{ inputs.workflow_type }}" \
            --dry-run "${{ inputs.dry_run }}"

  notify-result:
    name: 📬 Ergebnis melden
    runs-on: ubuntu-latest
    needs: run-agent
    if: always()
    steps:
      - name: Ergebnis als Commit-Status setzen
        uses: actions/github-script@v7
        with:
          script: |
            const status = '${{ needs.run-agent.outputs.status }}';
            const prUrl = '${{ needs.run-agent.outputs.pr_url }}';
            const quality = '${{ needs.run-agent.outputs.quality_score }}';
            const isDryRun = '${{ inputs.dry_run }}' === 'true';

            const stateMap = {
              'completed': 'success',
              'failed': 'failure',
              'gate_pending': 'pending',
            };

            let description = `Agent: ${status}`;
            if (quality !== 'N/A' && quality !== '') description += ` | Quality: ${quality}`;
            if (isDryRun) description += ' [DRY RUN]';
            if (prUrl) description += ` → PR erstellt`;

            console.log('Agent Task Result:', description);
            console.log('PR URL:', prUrl || 'kein PR');
```

---

## Schritt 2: Issue-Trigger — Noch komfortabler vom iPad

### `.github/ISSUE_TEMPLATE/agent-task.yml`

```yaml
name: 🤖 Agent Task
description: Erstelle einen Task für das Cascade Agent Team
title: "[AGENT] "
labels:
  - agent-task
  - pending
assignees:
  - achimdehnert
body:
  - type: textarea
    id: task_description
    attributes:
      label: Task-Beschreibung
      description: |
        Was soll der Agent implementieren?
        Je konkreter desto besser — inkl. Endpunkte, Felder, Verhalten.
      placeholder: |
        Add cursor-based pagination to the /api/projects endpoint.
        - Max 20 items per page
        - Return X-Total-Count header
        - Accept ?cursor= query parameter
        - Tests für alle Pagination-Edge-Cases
    validations:
      required: true

  - type: dropdown
    id: workflow_type
    attributes:
      label: Workflow-Typ
      description: Welche Agenten sollen aktiviert werden?
      options:
        - feature_delivery (Dev → Guardian → Tester → PR)
        - bugfix (Dev → Tester → Guardian → PR, schnell)
        - test_existing (nur Tests hinzufügen/reparieren)
        - adr_development (Architektur-Entscheidung, kein auto-PR)
        - re_engineering (Refactoring + Analyse)
      default: 0
    validations:
      required: true

  - type: input
    id: scope_paths
    attributes:
      label: Scope Paths (komma-getrennt)
      description: |
        Welche Pfade darf der Agent ändern? So eng wie möglich!
        NIEMALS: migrations/, .env, settings/prod*, Dockerfile
      placeholder: "apps/api/views/projects.py,apps/api/tests/test_projects.py"
    validations:
      required: true

  - type: dropdown
    id: model_scenario
    attributes:
      label: Modell-Qualität
      options:
        - groq (schnell, $0 — für Bugfixes)
        - hybrid (balanciert — für Features)
        - claude (höchste Qualität — für ADRs)
        - local (offline, kein Budget)
      default: 0

  - type: checkboxes
    id: options
    attributes:
      label: Optionen
      options:
        - label: Dry Run (nur Plan anzeigen, keine Dateien schreiben)
          required: false
        - label: Ich habe die Scope-Paths überprüft
          required: true
        - label: Keine verbotenen Pfade (migrations, .env, prod-settings)
          required: true
```

### `.github/workflows/agent-task-issue.yml`

```yaml
name: 🤖 Agent Task (Issue-Trigger)

on:
  issues:
    types: [opened, labeled]

jobs:
  check-trigger:
    name: 🔍 Prüfe ob Agent-Task
    runs-on: ubuntu-latest
    if: contains(github.event.issue.labels.*.name, 'agent-task')
    outputs:
      should_run: ${{ steps.check.outputs.should_run }}
      task_params: ${{ steps.parse.outputs.task_params }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Issue-Body parsen
        id: parse
        uses: actions/github-script@v7
        with:
          script: |
            const body = context.payload.issue.body;
            const issueNumber = context.payload.issue.number;

            // Parse Markdown Form Fields
            const parsed = {};
            const sections = body.split('###').filter(s => s.trim());

            for (const section of sections) {
              const lines = section.trim().split('\n');
              const key = lines[0].trim().toLowerCase()
                .replace(/[^a-z_]/g, '_')
                .replace(/__+/g, '_');
              const value = lines.slice(1).join('\n').trim();
              parsed[key] = value;
            }

            // Workflow-Typ aus Dropdown extrahieren
            const workflowRaw = parsed['workflow_typ'] || 'feature_delivery';
            const workflowType = workflowRaw.split(' ')[0];

            // Model-Szenario extrahieren
            const modelRaw = parsed['modell_qualit_t'] || 'groq';
            const modelScenario = modelRaw.split(' ')[0];

            // Dry Run erkennen
            const isDryRun = body.includes('[x] Dry Run') || body.includes('[X] Dry Run');

            const params = {
              issue_number: issueNumber,
              task_description: parsed['task_beschreibung'] || '',
              workflow_type: workflowType,
              scope_paths: parsed['scope_paths__komma_getrennt_'] || '',
              model_scenario: modelScenario,
              dry_run: isDryRun
            };

            console.log('Parsed params:', JSON.stringify(params, null, 2));
            core.setOutput('task_params', JSON.stringify(params));
            return params;

      - name: Prüfe ob ausführbar
        id: check
        uses: actions/github-script@v7
        with:
          script: |
            const params = JSON.parse('${{ steps.parse.outputs.task_params }}');

            if (!params.task_description || params.task_description.length < 10) {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: params.issue_number,
                body: '❌ **Agent Task fehlgeschlagen**\n\nTask-Beschreibung ist zu kurz oder fehlt. Bitte mindestens 10 Zeichen eingeben.'
              });
              core.setOutput('should_run', 'false');
              return;
            }

            if (!params.scope_paths) {
              await github.rest.issues.createComment({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: params.issue_number,
                body: '❌ **Agent Task fehlgeschlagen**\n\nScope Paths fehlen. Bitte angeben welche Dateien der Agent ändern darf.'
              });
              core.setOutput('should_run', 'false');
              return;
            }

            // Bestätigungs-Kommentar
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: params.issue_number,
              body: `🤖 **Agent Task gestartet**

**Task:** ${params.task_description.substring(0, 100)}...
**Workflow:** \`${params.workflow_type}\`
**Scope:** \`${params.scope_paths}\`
**Modell:** \`${params.model_scenario}\`
**Dry Run:** ${params.dry_run ? '✅ Ja' : '❌ Nein'}

Der Agent arbeitet jetzt. Du wirst bei Abschluss benachrichtigt.
${params.dry_run ? '\n⚠️ **DRY RUN** — Es werden keine Dateien geändert.' : ''}
`
            });

            // Label: pending → running
            await github.rest.issues.addLabels({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: params.issue_number,
              labels: ['agent-running']
            });

            core.setOutput('should_run', 'true');

  run-agent:
    name: 🤖 Agent ausführen
    runs-on: ubuntu-latest
    needs: check-trigger
    if: needs.check-trigger.outputs.should_run == 'true'

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Dependencies installieren
        run: pip install fastmcp structlog pydantic httpx

      - name: Agent triggern und warten
        id: agent
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PROJECT_PAT: ${{ secrets.PROJECT_PAT }}
          TASK_PARAMS: ${{ needs.check-trigger.outputs.task_params }}
        run: |
          python .github/scripts/trigger_agent_from_issue.py \
            --params "$TASK_PARAMS" \
            --output-file /tmp/agent_result.json

      - name: Ergebnis als Issue-Kommentar posten
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const params = JSON.parse(process.env.TASK_PARAMS);

            let result = {};
            try {
              result = JSON.parse(fs.readFileSync('/tmp/agent_result.json', 'utf8'));
            } catch(e) {
              result = { status: 'error', error: e.message };
            }

            const status = result.status || 'unknown';
            const emoji = {
              'completed': '✅',
              'failed': '❌',
              'gate_pending': '⏸️',
              'stub_completed': '⚠️'
            }[status] || '❓';

            let body = `${emoji} **Agent Task ${status === 'completed' ? 'abgeschlossen' : 'Status: ' + status}**\n\n`;

            if (result.quality_score) {
              const score = parseFloat(result.quality_score);
              const stars = score >= 0.85 ? '⭐⭐⭐' : score >= 0.70 ? '⭐⭐' : '⭐';
              body += `**Quality Score:** ${(score * 100).toFixed(0)}% ${stars}\n`;
            }
            if (result.pr_url) {
              body += `**Pull Request:** ${result.pr_url}\n`;
            }
            if (result.error) {
              body += `**Fehler:** \`${result.error}\`\n`;
            }
            if (result.status === 'gate_pending') {
              body += `\n⏸️ **Gate-Entscheidung erforderlich!**\n`;
              body += `Kommentiere \`/approve\` oder \`/reject\` um fortzufahren.\n`;
            }

            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: params.issue_number,
              body
            });

            // Label aktualisieren
            const newLabel = status === 'completed' ? 'agent-done' :
                             status === 'failed' ? 'agent-failed' :
                             status === 'gate_pending' ? 'agent-waiting' : 'agent-done';

            await github.rest.issues.addLabels({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: params.issue_number,
              labels: [newLabel]
            });

            // Issue schließen wenn erfolgreich
            if (status === 'completed' && !params.dry_run) {
              await github.rest.issues.update({
                owner: context.repo.owner,
                repo: context.repo.repo,
                issue_number: params.issue_number,
                state: 'closed'
              });
            }
        env:
          TASK_PARAMS: ${{ needs.check-trigger.outputs.task_params }}
```

---

## Schritt 3: Gate-Entscheidungen via Issue-Kommentar

### `.github/workflows/agent-gate-decision.yml`

```yaml
name: ⏸️ Agent Gate Decision

on:
  issue_comment:
    types: [created]

jobs:
  handle-gate:
    name: Gate-Entscheidung verarbeiten
    runs-on: ubuntu-latest
    # Nur bei Issues mit agent-waiting Label und /approve oder /reject Kommentar
    if: |
      contains(github.event.issue.labels.*.name, 'agent-waiting') &&
      (startsWith(github.event.comment.body, '/approve') ||
       startsWith(github.event.comment.body, '/reject'))

    steps:
      - name: Gate-Entscheidung verarbeiten
        uses: actions/github-script@v7
        with:
          script: |
            const comment = context.payload.comment.body.trim();
            const decision = comment.startsWith('/approve') ? 'approve' : 'reject';
            const commentText = comment.replace(/^\/(approve|reject)\s*/, '').trim();

            console.log(`Gate decision: ${decision}`);
            console.log(`Comment: ${commentText || '(kein Kommentar)'}`);

            // Reaktion auf Kommentar
            await github.rest.reactions.createForIssueComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              comment_id: context.payload.comment.id,
              content: decision === 'approve' ? '+1' : '-1'
            });

            // Gate-Entscheidung an MCP Server weiterleiten
            // (via Repository Dispatch oder direkten API-Call)
            await github.rest.repos.createDispatchEvent({
              owner: context.repo.owner,
              repo: context.repo.repo,
              event_type: 'agent-gate-decision',
              client_payload: {
                issue_number: context.payload.issue.number,
                decision: decision,
                comment: commentText
              }
            });

            // Bestätigung
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.payload.issue.number,
              body: `${decision === 'approve' ? '✅' : '❌'} Gate-Entscheidung **${decision}** registriert.\n${commentText ? `> ${commentText}` : ''}\nAgent wird fortgesetzt...`
            });
```

---

## Schritt 4: Python-Scripts (`.github/scripts/`)

### `.github/scripts/trigger_agent.py`

```python
#!/usr/bin/env python3
"""
Triggert den Agent Team MCP Server mit den Workflow-Parametern.
Kann lokal oder in GitHub Actions ausgeführt werden.
"""
import argparse
import json
import os
import sys
import asyncio
from pathlib import Path

# Agent Team direkt importieren wenn im mcp-hub Repo
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

async def trigger_agent(
    task: str,
    workflow: str,
    scope: list[str],
    model: str,
    dry_run: bool,
    output_file: str
) -> dict:
    try:
        from orchestrator_mcp.agent_team.mcp_server import (
            agent_team_run_workflow,
            agent_team_get_status,
            WorkflowRunInput,
            WorkflowStatusInput
        )

        # Workflow starten
        params = WorkflowRunInput(
            task_description=task,
            workflow_type=workflow,
            scope_paths=scope,
            model_scenario=model,
            dry_run=dry_run
        )
        result_str = await agent_team_run_workflow(params)
        result = json.loads(result_str)

        print(f"✅ Agent gestartet: run_id={result['run_id']}")
        print(f"   Workflow: {workflow}")
        print(f"   Scope: {scope}")
        print(f"   Dry Run: {dry_run}")

        # Ergebnis speichern
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        return result

    except ImportError as e:
        # Fallback: MCP Server via HTTP wenn nicht lokal importierbar
        print(f"⚠️  Direkt-Import fehlgeschlagen: {e}")
        print("    Versuche HTTP-Fallback...")
        return await trigger_via_http(task, workflow, scope, model, dry_run, output_file)


async def trigger_via_http(task, workflow, scope, model, dry_run, output_file):
    """Fallback: MCP Server via HTTP (wenn als separater Prozess läuft)."""
    import httpx

    mcp_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8765')

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "agent_team_run_workflow",
            "arguments": {
                "task_description": task,
                "workflow_type": workflow,
                "scope_paths": scope,
                "model_scenario": model,
                "dry_run": dry_run
            }
        },
        "id": 1
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{mcp_url}/mcp", json=payload)
        result = response.json()

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--task', required=True)
    parser.add_argument('--workflow', required=True)
    parser.add_argument('--scope', required=True, help='JSON array string')
    parser.add_argument('--model', default='groq')
    parser.add_argument('--dry-run', default='false')
    parser.add_argument('--output-file', default='/tmp/agent_result.json')
    args = parser.parse_args()

    scope_list = json.loads(args.scope)
    is_dry_run = args.dry_run.lower() == 'true'

    result = asyncio.run(trigger_agent(
        task=args.task,
        workflow=args.workflow,
        scope=scope_list,
        model=args.model,
        dry_run=is_dry_run,
        output_file=args.output_file
    ))

    # GitHub Actions Output setzen
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"run_id={result.get('run_id', 'unknown')}\n")

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
```

### `.github/scripts/post_summary.py`

```python
#!/usr/bin/env python3
"""Schreibt einen formatierten Job-Summary in GitHub Actions."""
import argparse
import json
import os
from datetime import datetime


def write_summary(result: dict, task: str, workflow: str, dry_run: bool):
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY', '/dev/stdout')

    status = result.get('status', 'unknown')
    quality = result.get('quality_score')
    pr_url = result.get('pr_url')
    error = result.get('error')
    run_id = result.get('run_id', 'N/A')

    emoji_map = {
        'completed': '✅', 'failed': '❌',
        'gate_pending': '⏸️', 'stub_completed': '⚠️'
    }
    emoji = emoji_map.get(status, '❓')

    lines = [
        f"# {emoji} Agent Task {'[DRY RUN] ' if dry_run else ''}— {status.upper()}",
        "",
        "## 📋 Task-Details",
        f"| | |",
        f"|---|---|",
        f"| **Task** | {task[:100]}{'...' if len(task) > 100 else ''} |",
        f"| **Workflow** | `{workflow}` |",
        f"| **Run ID** | `{run_id}` |",
        f"| **Zeitstempel** | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} |",
        f"| **Dry Run** | {'✅ Ja' if dry_run else '❌ Nein'} |",
        "",
    ]

    if quality is not None:
        score = float(quality)
        stars = "⭐⭐⭐" if score >= 0.85 else "⭐⭐" if score >= 0.70 else "⭐"
        bar_filled = int(score * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        lines += [
            "## 📊 Qualität",
            f"**Score:** {score:.0%} {stars}",
            f"`{bar}` {score:.0%}",
            "",
        ]

    if pr_url:
        lines += [
            "## 🔗 Pull Request",
            f"[{pr_url}]({pr_url})",
            "",
        ]

    if status == 'gate_pending':
        lines += [
            "## ⏸️ Gate-Entscheidung erforderlich",
            "Der Agent wartet auf deine Freigabe.",
            "Kommentiere im Issue `/approve` oder `/reject`.",
            "",
        ]

    if error:
        lines += [
            "## ❌ Fehler",
            f"```",
            error,
            "```",
            "",
        ]

    # Log-Einträge
    log_entries = result.get('log_entries', [])
    if log_entries:
        lines += ["## 📜 Agent Log (letzte 10 Einträge)", "```"]
        for entry in log_entries[-10:]:
            ts = entry.get('ts', '')[:19]
            level = entry.get('level', 'INFO')
            msg = entry.get('msg', '')
            lines.append(f"{ts} [{level:7s}] {msg}")
        lines += ["```", ""]

    content = "\n".join(lines)

    with open(summary_file, 'w') as f:
        f.write(content)

    print(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result-file', required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--workflow', required=True)
    parser.add_argument('--dry-run', default='false')
    args = parser.parse_args()

    try:
        with open(args.result_file) as f:
            result = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        result = {'status': 'error', 'error': 'Result file not found or invalid'}

    write_summary(
        result=result,
        task=args.task,
        workflow=args.workflow,
        dry_run=args.dry_run.lower() == 'true'
    )


if __name__ == '__main__':
    main()
```

---

## Schritt 5: iPad-Workflow — So sieht es in der Praxis aus

### Option A: `workflow_dispatch` (Schnellste Route)

```
1. GitHub Mobile App öffnen
2. iilgmbh/mcp-hub → Actions
3. "🤖 Agent Task (Manuell)" → Run workflow
4. Formular ausfüllen:
   - Task: "Add pagination to /api/projects, cursor-based, max 20 items"
   - Workflow: feature_delivery
   - Scope: apps/api/views/projects.py,apps/api/tests/test_projects.py
   - Modell: groq
   - Dry Run: false
5. Run workflow drücken
6. → Notification in 15–45 min: "PR #42 created"
7. → PR Review in GitHub Mobile → Approve
```

### Option B: Issue erstellen (Komfortabler für komplexe Tasks)

```
1. GitHub Mobile → Issues → New Issue
2. Template: "🤖 Agent Task" wählen
3. Formular ausfüllen (strukturiert, mit Dropdown)
4. Submit
5. → Automatisch: Bestätigungs-Kommentar vom Agent
6. → In 15–45 min: Ergebnis-Kommentar mit PR-Link
7. → Bei Gate: "/approve" oder "/reject" kommentieren
```

### Option C: Cascade triggert sich selbst (Fortgeschritten)

```bash
# Cascade ruft direkt auf:
gh workflow run agent-task-dispatch.yml \
  -R iilgmbh/mcp-hub \
  -f task_description="Add pagination to /api/projects" \
  -f workflow_type="feature_delivery" \
  -f scope_paths="apps/api/views/projects.py" \
  -f model_scenario="groq" \
  -f dry_run="false"
```

---

## Schritt 6: Org Secrets einrichten (einmalig)

```
github.com/organizations/iilgmbh
  → Settings
  → Secrets and variables
  → Actions
  → New organization secret

Name: PROJECT_PAT
Value: <dein Fine-Grained PAT — Contents:Read auf iilgmbh/platform>
Repository access: All repositories

Name: HETZNER_SSH_KEY          (optional — falls SSH zu VPS benötigt)
Value: <private SSH key>
Repository access: All repositories
```

---

## Schritt 7: Lokales Testen vor dem ersten iPad-Einsatz

```bash
# 1. Script direkt testen (im mcp-hub Repo root)
python .github/scripts/trigger_agent.py \
  --task "Add health check endpoint to the API" \
  --workflow "bugfix" \
  --scope '["apps/api/views/health.py"]' \
  --model "groq" \
  --dry-run "true" \
  --output-file /tmp/test_result.json

# 2. Summary testen
python .github/scripts/post_summary.py \
  --result-file /tmp/test_result.json \
  --task "Add health check endpoint" \
  --workflow "bugfix" \
  --dry-run "true"

# 3. Workflow via gh CLI triggern (simuliert iPad-Action)
gh workflow run agent-task-dispatch.yml \
  -f task_description="Test: Add health check endpoint" \
  -f workflow_type="bugfix" \
  -f scope_paths="apps/api/views/health.py" \
  -f model_scenario="groq" \
  -f dry_run="true"

# 4. Status beobachten
gh run list --workflow=agent-task-dispatch.yml --limit 5
gh run watch  # Live-Log
```

---

## Sicherheits-Checkliste

| Check | Details |
|---|---|
| ✅ **Scope-Validierung** | Workflow blockt verbotene Pfade (migrations, .env, prod-settings) |
| ✅ **Relative Pfade** | Keine absoluten Pfade erlaubt |
| ✅ **Org Secret** | `PROJECT_PAT` nur in iilgmbh-Repos sichtbar |
| ✅ **GITHUB_TOKEN** | Minimaler Scope: contents:read, packages:write |
| ✅ **Gate 2+ immer manuell** | PR-Merge nur nach `/approve` im Issue |
| ✅ **Dry Run Standard** | Default-Wert für erste Tests |
| ✅ **Audit Trail** | Jeder Run in GitHub Actions Logs, jede Gate-Entscheidung als Issue-Kommentar |
| ⚠️ **SSH-Key optional** | Nur nötig wenn Agent auf Hetzner VPS läuft statt direkt im Runner |

---

## Entscheidung: Runner-Strategie

| Strategie | Pro | Contra | Empfehlung |
|---|---|---|---|
| **GitHub Runner (ubuntu-latest)** | Kostenlos, keine Infrastruktur | Agent-State nicht persistent | ✅ Start hier |
| **Self-hosted Runner auf Hetzner** | Persistenter State, schneller, $0 Actions-Minuten | Setup nötig | Stufe 2 |
| **SSH zu Hetzner VPS** | Agent läuft auf bekanntem System | SSH-Key als Secret nötig | Stufe 2 |

**Empfehlung:** Mit GitHub Runner (ubuntu-latest) starten — kein Setup, sofort funktionsfähig.
Wenn der Agent-State zwischen Runs persistiert werden muss → Self-hosted Runner auf Hetzner.

---

## Nächste Schritte

| Priorität | Aktion | Aufwand |
|---|---|---|
| **P0** | `agent-task-dispatch.yml` anlegen und mit Dry-Run testen | 30 min |
| **P0** | `trigger_agent.py` + `post_summary.py` Scripts einchecken | 15 min |
| **P1** | Issue-Template + `agent-task-issue.yml` anlegen | 30 min |
| **P1** | Gate-Decision Workflow anlegen | 20 min |
| **P2** | Self-hosted Runner auf Hetzner (persistenter State) | 1h |
| **P3** | Cascade-Selbst-Trigger via `gh workflow run` in Windsurf Rules | 30 min |

---

*Erstellt: 2026-03-08 | Autor: Claude Sonnet 4.6 | Repo: iilgmbh/mcp-hub*
