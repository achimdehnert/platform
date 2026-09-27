#!/usr/bin/env python3
"""Byte-Vergleich Orchestrator-pgvector gegen klickdummy-sync-NDJSON — ohne LLM im Pfad.

Liest den Orchestrator-MCP-Eintrag aus ~/.claude.json (URL + Authorization-Header),
spricht den Server per Streamable-HTTP-JSON-RPC direkt an und vergleicht den
``content`` aus ``agent_memory_search`` byte-genau mit der NDJSON-Zeile des
Producers (``klickdummy-sync --cross-repo``). Kontext: platform#2462, #1733.

Aufruf:
    tools/klickdummy_pgvector_bytecheck.py <ndjson> [entry_key ...]

Ohne entry_keys werden alle Zeilen der NDJSON geprüft. Exit-Code 1, sobald ein
DIFF gefunden wurde; nicht auffindbare Entries zählen nicht als DIFF (Temporal
Decay des Stores, separat getrackt).

Cloudflare beantwortet den Default-User-Agent von urllib mit Error 1010 —
deshalb der explizite UA. Der Key wird nie ausgegeben.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) klickdummy-pgvector-bytecheck/1.0"
PROTOCOL_VERSION = "2025-03-26"


def _orchestrator_config() -> dict:
    cfg = json.load(open(os.path.expanduser("~/.claude.json")))
    scopes = [cfg.get("mcpServers", {})] + [
        p.get("mcpServers", {}) for p in cfg.get("projects", {}).values()
    ]
    for scope in scopes:
        if "orchestrator" in scope:
            return scope["orchestrator"]
    sys.exit("kein orchestrator-Eintrag in ~/.claude.json")


class McpClient:
    def __init__(self, cfg: dict) -> None:
        self.url = cfg["url"]
        self.headers = dict(cfg.get("headers", {}))
        self.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "User-Agent": USER_AGENT,
            }
        )
        self.session_id: str | None = None
        self._next_id = 1

    def rpc(self, method: str, params: dict, *, notify: bool = False) -> dict | None:
        body: dict = {"jsonrpc": "2.0", "method": method, "params": params}
        req_id = None
        if not notify:
            req_id = self._next_id
            self._next_id += 1
            body["id"] = req_id
        headers = dict(self.headers)
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        req = urllib.request.Request(
            self.url, data=json.dumps(body).encode(), headers=headers, method="POST"
        )
        try:
            resp = urllib.request.urlopen(req, timeout=90)
        except urllib.error.HTTPError as exc:
            print(
                f"HTTP {exc.code} bei {method}: {exc.read()[:160]!r}", file=sys.stderr
            )
            return None
        self.session_id = resp.headers.get("Mcp-Session-Id") or self.session_id
        raw = resp.read().decode()
        if notify:
            return None
        if "text/event-stream" in resp.headers.get("Content-Type", ""):
            for line in raw.splitlines():
                if line.startswith("data:"):
                    try:
                        data = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if data.get("id") == req_id:
                        return data
            return None
        return json.loads(raw) if raw else None

    def initialize(self) -> bool:
        res = self.rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "klickdummy-pgvector-bytecheck",
                    "version": "1.0",
                },
            },
        )
        if not res or "result" not in res:
            return False
        self.rpc("notifications/initialized", {}, notify=True)
        return True

    def search(self, query: str, entry_type: str, limit: int = 3) -> list[dict]:
        res = self.rpc(
            "tools/call",
            {
                "name": "agent_memory_search",
                "arguments": {"query": query, "entry_type": entry_type, "limit": limit},
            },
        )
        if not res or "result" not in res:
            return []
        text = "".join(c.get("text", "") for c in res["result"].get("content", []))
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return []


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    rows = {}
    for line in open(argv[1], encoding="utf-8"):
        row = json.loads(line)
        rows[row["entry_key"]] = row
    keys = argv[2:] or list(rows)
    client = McpClient(_orchestrator_config())
    if not client.initialize():
        print("MCP initialize fehlgeschlagen", file=sys.stderr)
        return 2
    diffs = 0
    for key in keys:
        row = rows[key]
        hit = next(
            (
                it
                for it in client.search(row["title"], row["entry_type"])
                if it.get("id") == key
            ),
            None,
        )
        if hit is None:
            print(f"NICHT-AUFFINDBAR {key}")
            continue
        stored, source = hit["content"], row["content"]
        if stored == source:
            print(
                f"BYTE-GLEICH      {key}  (len {len(source)}, agent={hit.get('agent')})"
            )
            continue
        diffs += 1
        pos = next(
            (i for i in range(min(len(stored), len(source))) if stored[i] != source[i]),
            min(len(stored), len(source)),
        )
        lo, hi = max(0, pos - 40), pos + 40
        print(
            f"DIFF             {key}  store={len(stored)} file={len(source)} pos={pos}\n"
            f"   store: {stored[lo:hi]!r}\n   file : {source[lo:hi]!r}"
        )
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
