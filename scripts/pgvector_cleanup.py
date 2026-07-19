"""F6 + Cleanup: ADR-Decisions soft-deleten, alte Sessions deaktivieren."""
import os
import sys

import psycopg

# SEC-5 (Issue #1198): kein stillschweigender Passwort-Fallback mehr. Der alte
# Default deckte sich zufällig mit dem lokalen docker-compose-Default
# (POSTGRES_PASSWORD:-change-me-in-production, mcp-hub/docker-compose.yml) —
# bleibt als EXPLIZITER Dev-Only-Opt-in erhalten (ALLOW_DEV_DB_FALLBACK=1),
# statt automatisch/leise verwendet zu werden.
_DEV_FALLBACK_DB_URL = "postgresql://orchestrator:change-me-in-production@localhost:15435/orchestrator_mcp"

DB_URL = os.environ.get("MEM_DB_URL")
if not DB_URL:
    if os.environ.get("ALLOW_DEV_DB_FALLBACK") == "1":
        DB_URL = _DEV_FALLBACK_DB_URL
        print("⚠ MEM_DB_URL fehlt — nutze Dev-Only-Fallback (ALLOW_DEV_DB_FALLBACK=1).", file=sys.stderr)
    else:
        sys.exit(
            "❌ MEM_DB_URL fehlt. Setze die Env-Var, oder für lokale Dev-Umgebungen "
            "explizit ALLOW_DEV_DB_FALLBACK=1 (nutzt dann den bekannten "
            "localhost-Dev-Connection-String)."
        )

with psycopg.connect(DB_URL) as conn, conn.cursor() as cur:
    print("=== STEP 1: Identify candidates ===\n")
    
    # 1a) ADR decisions in pgvector
    cur.execute("""
        SELECT id, title, LENGTH(content) as chars
        FROM agent_memory_entries
        WHERE is_active = true
          AND entry_type = 'decision'
          AND (id LIKE '%ADR-%' OR id LIKE '%adr:%' OR title ~* 'ADR-[0-9]')
        ORDER BY chars DESC LIMIT 30
    """)
    adrs = cur.fetchall()
    print(f"ADR-decisions in store: {len(adrs)}")
    adr_chars = sum(r[2] for r in adrs)
    print(f"  Chars: {adr_chars} (~{adr_chars//4} tokens)")
    for r in adrs[:5]:
        print(f"  - {r[0][:60]} | {r[2]} chars")
    
    # 1b) Session-context älter als 30 Tage
    cur.execute("""
        SELECT COUNT(*), SUM(LENGTH(content)) FROM agent_memory_entries
        WHERE is_active = true AND entry_type = 'context'
          AND updated_at < NOW() - INTERVAL '30 days'
    """)
    n, c = cur.fetchone()
    print(f"\nSession-contexts >30d: {n} | {c or 0} chars (~{(c or 0)//4} tok)")
    
    # 1c) Error-patterns mit occurrence_count=1, älter als 60 Tage
    cur.execute("""
        SELECT COUNT(*), SUM(LENGTH(content)) FROM agent_memory_entries
        WHERE is_active = true AND entry_type = 'error_pattern'
          AND occurrence_count <= 1
          AND updated_at < NOW() - INTERVAL '60 days'
    """)
    n2, c2 = cur.fetchone()
    print(f"Error-patterns single+old: {n2} | {c2 or 0} chars (~{(c2 or 0)//4} tok)")
    
    # 1d) Policy entries (sehr gross)
    cur.execute("""
        SELECT id, title, LENGTH(content) as chars
        FROM agent_memory_entries
        WHERE is_active = true AND id LIKE 'policy:%'
        ORDER BY chars DESC
    """)
    policies = cur.fetchall()
    print(f"\nPolicy-entries: {len(policies)}")
    for r in policies:
        print(f"  - {r[0]} | {r[2]} chars")
    
    print("\n=== STEP 2: Apply soft-deletes ===\n")
    
    # Soft-delete ADRs (Source of Truth ist docs/adr/*.md)
    cur.execute("""
        UPDATE agent_memory_entries
        SET is_active = false, updated_at = NOW()
        WHERE is_active = true AND entry_type = 'decision'
          AND (id LIKE '%ADR-%' OR id LIKE '%adr:%' OR title ~* 'ADR-[0-9]')
    """)
    print(f"  Soft-deleted ADR decisions: {cur.rowcount}")
    
    # Soft-delete alte session contexts
    cur.execute("""
        UPDATE agent_memory_entries
        SET is_active = false, updated_at = NOW()
        WHERE is_active = true AND entry_type = 'context'
          AND updated_at < NOW() - INTERVAL '30 days'
    """)
    print(f"  Soft-deleted old session contexts: {cur.rowcount}")
    
    # Soft-delete einmalige alte error patterns
    cur.execute("""
        UPDATE agent_memory_entries
        SET is_active = false, updated_at = NOW()
        WHERE is_active = true AND entry_type = 'error_pattern'
          AND occurrence_count <= 1
          AND updated_at < NOW() - INTERVAL '60 days'
    """)
    print(f"  Soft-deleted stale single-occurrence errors: {cur.rowcount}")
    
    conn.commit()
    
    # Final stats
    cur.execute("""
        SELECT entry_type, COUNT(*) as n, SUM(LENGTH(content)) as total
        FROM agent_memory_entries WHERE is_active = true
        GROUP BY entry_type ORDER BY total DESC
    """)
    print("\n=== AFTER ===")
    total = 0
    for et, n, c in cur.fetchall():
        total += c
        print(f"  {et:<20} {n:>4} | {c:>7} chars (~{c//4} tok)")
    print(f"\n  TOTAL active: ~{total//4} tokens (was ~61400)")
