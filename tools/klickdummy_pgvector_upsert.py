#!/usr/bin/env python3
"""Upsert aller klickdummy-sync-NDJSON-Zeilen in den Orchestrator-pgvector — ohne LLM im Pfad.

Gegenstück zu ``klickdummy_pgvector_bytecheck.py`` (gleicher HTTP-Client, gleiche
Config aus ~/.claude.json). Schickt jede Zeile byte-genau an ``agent_memory_upsert``
und zählt ok/failed/written. Kontext: platform#2462, #1733; Läufe 2026-09-16 ff.

Aufruf:
    tools/klickdummy_pgvector_upsert.py <ndjson>

``written: true`` ist KEIN Fidelity-Signal (klemmender content_hash, mcp-hub#274) —
Beleg ist ausschliesslich der Byte-Check danach.
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from klickdummy_pgvector_bytecheck import McpClient, _orchestrator_config

ndjson = sys.argv[1]
client = McpClient(_orchestrator_config())
if not client.initialize():
    sys.exit("MCP initialize fehlgeschlagen")
ok = failed = written = 0
written_keys = []
for line in open(ndjson, encoding="utf-8"):
    row = json.loads(line)
    args = {k: row[k] for k in ("entry_key", "entry_type", "title", "content", "tags")}
    args["agent"] = "klickdummy-sync"
    res = None
    for attempt in range(3):
        res = client.rpc("tools/call", {"name": "agent_memory_upsert", "arguments": args})
        if res and "result" in res:
            break
        time.sleep(2)
    if not res or "result" not in res or res["result"].get("isError"):
        failed += 1
        print(f"FAIL {row['entry_key']} {str(res)[:200]}")
        continue
    text = "".join(c.get("text", "") for c in res["result"].get("content", []))
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"raw": text[:200]}
    if data.get("status", "ok") not in ("ok", "success") and "written" not in data:
        failed += 1
        print(f"FAIL {row['entry_key']} {text[:200]}")
        continue
    ok += 1
    if data.get("written"):
        written += 1
        written_keys.append(row["entry_key"])
print(f"ok={ok} failed={failed} written={written}")
print("written_keys:", *written_keys, sep="\n  ")
