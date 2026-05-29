#!/bin/bash
# Token-Telemetry: zeigt Cascade Token-Verbrauch pro Tag/Repo
# ADR-Token-Efficiency — wöchentlich auswerten

set -euo pipefail

DB_URL="${ORCHESTRATOR_MCP_MEMORY_DB_URL:-postgresql://orchestrator:change-me-in-production@localhost:15435/orchestrator_mcp}"
DAYS="${1:-7}"

PYTHON="/home/devuser/github/mcp-hub/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON=$(which python3)

"$PYTHON" << PYEOF
import os, sys
import psycopg
DB="$DB_URL"
DAYS=$DAYS

with psycopg.connect(DB) as c, c.cursor() as cur:
    # Falls llm_calls Tabelle existiert
    cur.execute("""SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='llm_calls')""")
    if not cur.fetchone()[0]:
        print("⚠️  Tabelle llm_calls nicht vorhanden — Telemetry inaktiv.")
        sys.exit(0)
    
    cur.execute(f"""
        SELECT 
          DATE(created_at) as day,
          COALESCE(source, 'unknown') as src,
          COUNT(*) as calls,
          SUM(prompt_tokens) as in_tok,
          SUM(completion_tokens) as out_tok,
          ROUND(SUM(cost_usd)::numeric, 4) as cost
        FROM llm_calls
        WHERE created_at > NOW() - INTERVAL '{DAYS} days'
        GROUP BY day, src
        ORDER BY day DESC, in_tok DESC NULLS LAST
        LIMIT 50
    """)
    rows = cur.fetchall()
    if not rows:
        print(f"Keine LLM-Calls in den letzten {DAYS} Tagen.")
        sys.exit(0)
    print(f"📊 LLM-Token-Telemetry — letzte {DAYS} Tage\n")
    print(f"{'Tag':<12} {'Quelle':<22} {'Calls':>6} {'Input-Tok':>11} {'Output-Tok':>11} {'Cost USD':>10}")
    print("-" * 76)
    tot_in, tot_out, tot_cost = 0, 0, 0.0
    for d, s, n, ti, to, co in rows:
        ti, to, co = ti or 0, to or 0, float(co or 0)
        tot_in += ti; tot_out += to; tot_cost += co
        print(f"{str(d):<12} {s[:22]:<22} {n:>6} {ti:>11,} {to:>11,} {co:>10.4f}")
    print("-" * 76)
    print(f"{'TOTAL':<12} {'':<22} {sum(r[2] for r in rows):>6} {tot_in:>11,} {tot_out:>11,} {tot_cost:>10.4f}")
    
    # Top-5 teuerste einzelne Aufrufe
    cur.execute(f"""
        SELECT created_at::date, source, model, prompt_tokens, completion_tokens, cost_usd, COALESCE(repo,'') as repo, COALESCE(agent_role,'') as ar
        FROM llm_calls
        WHERE created_at > NOW() - INTERVAL '{DAYS} days'
        ORDER BY cost_usd DESC NULLS LAST LIMIT 10
    """)
    print("\n🔥 Top-10 teuerste einzelne Calls:")
    for d, s, m, ti, to, co, repo, ar in cur.fetchall():
        print(f"  {d} {s[:12]:<12} {m[:30]:<30} \${co or 0:>8.4f} | repo={repo[:18]:<18} role={ar[:15]}")
    
    # Source-Breakdown gesamt
    cur.execute(f"""
        SELECT source, COUNT(*) as n, SUM(cost_usd) as cost, SUM(prompt_tokens) as in_t
        FROM llm_calls
        WHERE created_at > NOW() - INTERVAL '{DAYS} days'
        GROUP BY source ORDER BY cost DESC NULLS LAST
    """)
    print("\n💰 Source-Breakdown:")
    for s, n, co, ti in cur.fetchall():
        print(f"  {s or 'NULL':<25} {n:>6} calls  \${co or 0:>10.2f}  {ti or 0:>15,} input-tok")
PYEOF
