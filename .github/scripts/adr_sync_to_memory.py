"""
ADR → pgvector Memory Sync

Verbindet die drei bisher getrennten Schichten:
  1. iil-adrfw ADR-Graphen (inbound_links, depends_on)
  2. pgvector Memory Store (Orchestrator)
  3. ADR Dual-Review Ergebnisse (ai_sparring_by)

Ergebnis: Claude bekommt beim nächsten `agent_memory_context`-Aufruf
  - Den vollständigen ADR-Nachbarschafts-Graphen
  - Die Review-History jedes ADR
  - Kritische Knoten (inbound_links >= 3) mit höherem half_life

Wird von adr-nightly-metrics.yml nach dem metrics-Schritt aufgerufen.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# pgvector connection (direkt via psycopg — kein Django)
# ---------------------------------------------------------------------------
def _get_conn():
    import psycopg
    db_url = os.environ.get("ORCHESTRATOR_MCP_MEMORY_DB_URL", "")
    if not db_url:
        pw_file = Path.home() / ".secrets" / "orchestrator_mcp_db_password"
        if pw_file.exists():
            pw = pw_file.read_text().strip()
            db_url = f"postgresql://orchestrator:{pw}@127.0.0.1:15435/orchestrator_mcp"
    if not db_url:
        raise RuntimeError("No DB URL — set ORCHESTRATOR_MCP_MEMORY_DB_URL")
    return psycopg.connect(db_url)


# ---------------------------------------------------------------------------
# Read ADRs + build graph
# ---------------------------------------------------------------------------
def load_adr_graph(adrs_dir: Path) -> dict:
    """Returns {adr_id: {title, status, domains, depends_on, ai_sparring_by, metrics}}"""
    graph = {}
    for md in sorted(adrs_dir.glob("ADR-*.md")):
        m = re.search(r"ADR-\d+", md.name)
        if not m:
            continue
        adr_id = m.group().upper()
        text = md.read_text(encoding="utf-8")
        match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if not match:
            continue
        fm = yaml.safe_load(match.group(1)) or {}
        graph[adr_id] = {
            "title": fm.get("title", ""),
            "status": str(fm.get("status", "")),
            "domains": fm.get("domains", []),
            "depends_on": [
                re.search(r"ADR-\d+", str(d)).group().upper()
                for d in (fm.get("depends_on") or [])
                if re.search(r"ADR-\d+", str(d))
            ],
            "ai_sparring_by": fm.get("ai_sparring_by") or [],
            "metrics": fm.get("metrics") or {},
        }
    return graph


def compute_inbound(graph: dict) -> dict[str, list[str]]:
    """Returns {adr_id: [adr_ids that depend_on it]}"""
    inbound: dict[str, list[str]] = {k: [] for k in graph}
    for adr_id, data in graph.items():
        for dep in data["depends_on"]:
            if dep in inbound:
                inbound[dep].append(adr_id)
    return inbound


# ---------------------------------------------------------------------------
# Upsert ADR memory entry
# ---------------------------------------------------------------------------
UPSERT_SQL = """
INSERT INTO agent_memory_entries
  (id, tenant_id, entry_type, title, content, agent, tags, related_ids,
   half_life_days, content_hash, metadata, updated_at)
VALUES
  (%(id)s, 1, %(entry_type)s, %(title)s, %(content)s, %(agent)s,
   %(tags)s, %(related_ids)s, %(half_life_days)s, %(content_hash)s,
   %(metadata)s::jsonb, now())
ON CONFLICT (id, tenant_id) DO UPDATE SET
  title        = EXCLUDED.title,
  content      = EXCLUDED.content,
  tags         = EXCLUDED.tags,
  related_ids  = EXCLUDED.related_ids,
  half_life_days = EXCLUDED.half_life_days,
  content_hash = EXCLUDED.content_hash,
  metadata     = EXCLUDED.metadata,
  updated_at   = now()
WHERE agent_memory_entries.content_hash != EXCLUDED.content_hash
"""

import hashlib


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def sync_adr_to_memory(conn, adr_id: str, data: dict, inbound: list[str]) -> bool:
    """Upsert one ADR as memory entry. Returns True if changed."""
    status = data["status"]
    # Skip void/deprecated — no value for future sessions
    if status in ("void", "deprecated"):
        return False

    inbound_count = len(inbound)
    sparring = data.get("ai_sparring_by", [])
    metrics = data.get("metrics", {})

    # Build rich content for semantic search
    last_review = ""
    if sparring:
        last = sparring[-1]
        last_review = f"\nLast AI review ({last.get('tool','')} {last.get('date','')}): {last.get('summary','')}"

    content = (
        f"ADR: {adr_id} — {data['title']}\n"
        f"Status: {status} | Domains: {', '.join(data['domains'])}\n"
        f"Depends on: {', '.join(data['depends_on']) or 'none'}\n"
        f"Depended on by: {', '.join(inbound) or 'none'} ({inbound_count} inbound links)\n"
        f"AI reviews: {len(sparring)} total{last_review}\n"
        f"Metrics: ttd={metrics.get('ttd_days','?')}d, "
        f"ttr={metrics.get('ttr_days','?')}d, "
        f"ai_90d={metrics.get('ai_interactions_90d', 0)}"
    )

    # Critical nodes live longer in memory
    half_life = 365 if inbound_count >= 3 else 180

    # related_ids: both directions (depends_on + inbound)
    related = list(set(data["depends_on"] + inbound))

    tags = data["domains"] + [status, "adr"]
    if inbound_count >= 3:
        tags.append("critical-node")

    h = _hash(content)
    with conn.cursor() as cur:
        cur.execute(UPSERT_SQL, {
            "id": f"adr:platform:{adr_id}",
            "entry_type": "decision",
            "title": f"{adr_id}: {data['title'][:100]}",
            "content": content,
            "agent": "adr-nightly-sync",
            "tags": tags,
            "related_ids": [f"adr:platform:{r}" for r in related],
            "half_life_days": half_life,
            "content_hash": h,
            "metadata": json.dumps({
                "adr_id": adr_id,
                "status": status,
                "inbound_links": inbound_count,
                "ai_interactions": len(sparring),
                "depends_on": data["depends_on"],
            }),
        })
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    adrs_dir = Path(os.environ.get("IIL_ADRFW_ADRS_DIR", "docs/adr"))
    if not adrs_dir.is_dir():
        print(f"[ERROR] {adrs_dir} not found", file=sys.stderr)
        return 2

    print(f"[INFO] Loading ADR graph from {adrs_dir}")
    graph = load_adr_graph(adrs_dir)
    inbound_map = compute_inbound(graph)

    print(f"[INFO] {len(graph)} ADRs, connecting to pgvector...")
    try:
        conn = _get_conn()
    except Exception as e:
        print(f"[WARN] pgvector unavailable: {e} — skipping sync")
        return 0

    synced = 0
    skipped = 0
    with conn:
        for adr_id, data in graph.items():
            inbound = inbound_map.get(adr_id, [])
            changed = sync_adr_to_memory(conn, adr_id, data, inbound)
            if changed:
                synced += 1
            else:
                skipped += 1

    print(f"[OK] pgvector sync: {synced} upserted, {skipped} unchanged/skipped")

    # Summary for GitHub Actions
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        critical = [aid for aid, d in inbound_map.items() if len(d) >= 3]
        with open(summary_path, "a") as f:
            f.write(f"\n### ADR → pgvector Sync\n")
            f.write(f"- **{synced}** entries upserted\n")
            f.write(f"- **{len(critical)}** critical nodes (≥3 inbound, half_life=365d)\n")
            f.write(f"- Graph edges encoded in `related_ids[]`\n")
            f.write(f"- Claude kann jetzt: `agent_memory_context('ADR-022')` → vollständige Nachbarschaft\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
