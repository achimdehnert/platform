# Phase 0 Baseline-Messungen — ADR-177

> Pre-Requisite für ADR-177 Agent Role Specialization.
> Verlinkt in: [ADR-177 v1.4](../docs/adr/ADR-177-agent-role-specialization.md)
> Tracking-Issue: [mcp-hub#13](https://github.com/achimdehnert/mcp-hub/issues/13)

## Methode (γ-Kombination)

Beide Datenquellen parallel sammeln, in Phase 5 vergleichen:

| Phase | Was | Wie | Wann |
|-------|-----|-----|------|
| **0a Goldset** | 50 synthetische Tasks | `run_goldset_baseline.py` | 1 Tag — sofort |
| **0b Real** | 14 Tage echte Workload | tägliche `/process-agent-queue` Sessions | 14 Tage parallel |
| **0c Vergleich** | Goldset vs Real | manuelle Auswertung | Phase 5 |

## Phase 0a — Goldset-Baseline

### Ein-Mal-Lauf (echt)

```bash
cd $HOME/github/platform
# Pre-flight: Tunnel + DB checken
ss -tlnp | grep 15435 || sudo systemctl start ssh-tunnel-postgres

# Real-Lauf (kostet ~$0.50–$2.00 je nach Token-Schätzung)
python3 scripts/run_goldset_baseline.py
```

### Dry-Run (kostenlos, zur Verifikation)

```bash
python3 scripts/run_goldset_baseline.py --dry-run
# Output: baselines/goldset-2026-04-results.json
```

### Einzel-Task testen

```bash
python3 scripts/run_goldset_baseline.py --task-id gs-001 --verbose
```

### Output

`baselines/goldset-2026-04-results.json` — enthält:
- `total_cost_usd` über alle Tasks
- `aggregated_by_task_type` (cost/tokens/duration pro task_type)
- `results[]` — jeder Task einzeln mit Erfolg/Fehler/Duration

Parallel werden alle LLM-Calls in der `llm_calls` Tabelle gespeichert mit
`routing_reason='goldset_baseline_2026-04'` (post-tagged nach Lauf-Ende).

### Verifikation in DB

```sql
SELECT task_type_inferred, COUNT(*), SUM(cost_usd), AVG(prompt_tokens + completion_tokens)
FROM llm_calls
WHERE routing_reason = 'goldset_baseline_2026-04'
GROUP BY task_type_inferred;
```

## Phase 0b — Real-Modus (14 Tage parallel)

### Ziel

Mindestens **50 echte Tasks** in 14 Tagen abarbeiten, deren LLM-Calls in `llm_calls`
mit `routing_reason='auto_dispatch'` landen.

### Methode

Täglich (idealerweise Vormittag) eine Cascade-Session in Windsurf:

```text
/process-agent-queue
```

Dies arbeitet die labels:auto-Issues über alle Repos ab, Wave-1-Auto-Dispatch
setzt `routing_reason='auto_dispatch'` automatisch (siehe agentic-coding v6).

### Tracking-Vorschlag

Tägliche Stichproben:

```bash
PW=$(cat ~/.secrets/orchestrator_mcp_db_password) python3 -c "
import os
from sqlalchemy import create_engine, text
eng = create_engine(f'postgresql://orchestrator:{os.environ[\"PW\"]}@127.0.0.1:15435/orchestrator_mcp')
with eng.connect() as c:
    rows = c.execute(text('''
        SELECT date(created_at), COUNT(*), SUM(cost_usd)
        FROM llm_calls
        WHERE routing_reason = 'auto_dispatch'
          AND created_at > now() - interval '14 days'
        GROUP BY date(created_at)
        ORDER BY 1
    ''')).fetchall()
    for r in rows: print(r)
"
```

### Akzeptanz

Nach 14 Tagen müssen ≥ 50 Einträge mit `routing_reason='auto_dispatch'` vorliegen.
Bei zu wenig: weiter sammeln oder Sample-Size für Phase 5 reduziert akzeptieren.

## Phase 0c — Vergleichs-Report (in Phase 5)

```bash
# Beispiel-Query für den Vergleichs-Report
PW=... python3 -c "
import os
from sqlalchemy import create_engine, text
eng = create_engine(...)
with eng.connect() as c:
    rows = c.execute(text('''
        SELECT routing_reason,
               COUNT(*) AS calls,
               SUM(cost_usd) AS total_cost,
               AVG(prompt_tokens + completion_tokens) AS avg_tokens,
               AVG(duration_ms) AS avg_duration
        FROM llm_calls
        WHERE routing_reason IN ('goldset_baseline_2026-04', 'auto_dispatch')
          AND created_at > '2026-04-30'
        GROUP BY routing_reason
    ''')).fetchall()
    for r in rows: print(r)
"
```

Output landet in `baselines/phase-0-report.md` (manuell erstellt nach 14 Tagen).

## Pre-Requisites

- ✅ `ORCHESTRATOR_DATABASE_URL` exportiert ([mcp-hub@e58908a](https://github.com/achimdehnert/mcp-hub/commit/e58908a))
- ✅ pgvector-Tunnel läuft (`localhost:15435`)
- ⚠️ `aifw>=0.5.0` muss installiert sein (`pip install aifw` im venv)
- ⚠️ `agent_team/workflows.py` muss `agent_role`/`complexity` befüllen — TODO mcp-hub#13

## Files

| File | Purpose |
|------|---------|
| `goldset-2026-04.yaml` | 50 Goldset-Task-Definitionen |
| `goldset-2026-04-results.json` | Output nach Runner-Lauf |
| `phase-0-report.md` | Vergleichs-Report (Phase 5) |
| `../scripts/run_goldset_baseline.py` | Runner-Script |

## Status

| Schritt | Status |
|---------|--------|
| Goldset-Skeleton | ✅ done (50 Tasks) |
| Runner-Script | ✅ done, dry-run grün |
| Echter Goldset-Run | ⏳ pending |
| Real-Modus 14 Tage | ⏳ pending (Tag 1 = Tag des ersten echten Goldset-Runs) |
| Phase-0-Report | ⏳ pending (Tag 14+) |
