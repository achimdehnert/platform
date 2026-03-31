# ADR-154 Review — Autonomous Coding Optimization

**Reviewer:** Principal IT Architect  
**Review Date:** 2026-03-31  
**ADR Status:** proposed → requires revisions before approved

---

## Zusammenfassung

ADR-154 adressiert ein reales und signifikantes Problem (Context-Amnesia, leerer pgvector-Store, disconnected Knowledge Stores). Die Diagnose ist präzise. Die Lösungsarchitektur ist jedoch in **6 Punkten blockierend**, in **4 Punkten kritisch** und hat mehrere HOCH/MEDIUM-Befunde. Ohne Korrekturen würde Phase 1 in Production Datenverlust und Security-Lücken riskieren.

---

## Review-Tabelle

| # | Befund | Severity | Bereich | Korrektur |
|---|--------|----------|---------|-----------|
| R-01 | `ORCHESTRATOR_MCP_MEMORY_DB_URL` wird als Env-Var gesetzt — Platform-Standard verlangt `read_secret()` für alle Credentials | **BLOCKER** | Security / Platform | `read_secret("ORCHESTRATOR_MCP_MEMORY_DB_URL")` in Startlogik; Secret in Vault / `.secrets` |
| R-02 | SSH-Tunnel in Phase 0 hat keine Reconnect-Logik und kein systemd-Unit — fällt beim nächsten WSL-Restart still aus | **BLOCKER** | Reliability | `autossh` + systemd user-service mit `Restart=always`; siehe `phase0-ssh-tunnel.service` |
| R-03 | pgvector Memory-Entries haben kein Django-Modell mit Platform-Standards — kein `BigAutoField`, kein `public_id`, kein `tenant_id`, kein `deleted_at` | **BLOCKER** | Platform Standards | Vollständiges `AgentMemoryEntry`-Model mit allen Pflichtfeldern; Idempotente Migration |
| R-04 | `get_full_context()` in O-8 ist synchron implementiert — 5 Backend-Calls seriell würden 2–5s Latenz erzeugen; kein Timeout, kein Circuit-Breaker | **BLOCKER** | Performance | `asyncio.gather()` mit `asyncio.wait_for(timeout=3.0)` pro Call; Graceful Degradation bei Timeout |
| R-05 | Shell-Script `generate-agent-handover.sh` fehlt `set -euo pipefail` und explizite Exit-Codes — Platform-Standard verletzt | **BLOCKER** | Platform | `set -euo pipefail` + `trap 'echo "ERROR line $LINENO"; exit 1' ERR` |
| R-06 | `entry_key` in O-1 verwendet Freitext-Format `session:<date>:<repo>` ohne `UniqueConstraint` — `unique_together` wird implizit verwendet, deprecated | **BLOCKER** | Platform | `UniqueConstraint(fields=["tenant_id","entry_key"], condition=Q(deleted_at__isnull=True))` |
| R-07 | `agent_memory_upsert` wird in `session-ende` Workflow ohne Schema-Validation aufgerufen — Cascade kann beliebig invalide Daten schreiben | **KRITISCH** | Data Quality | Pydantic v2 Schema `MemoryEntrySchema` als Gate vor dem Schreiben |
| R-08 | `get_full_context()` hat keine Fehler-Isolation — ein fehlerhafter Outline-Call lässt den gesamten Context-Call fehlschlagen | **KRITISCH** | Reliability | `try/except` pro Backend mit `None`-Fallback; Partial-Result-Pattern |
| R-09 | `symptom-hash` in O-5 ist undefiniert — keine deterministische Hash-Funktion angegeben; Duplikat-Error-Patterns sind wahrscheinlich | **KRITISCH** | Data Integrity | `hashlib.sha256(f"{repo}:{error_type}:{file_path}".encode()).hexdigest()[:16]` |
| R-10 | Phase 0 Option C ("Port auf Prod öffnen") ist als Option im ADR dokumentiert — sollte als **abgelehnt und gefährlich** markiert werden, nicht als neutrale Option | **KRITISCH** | Security | Option C aus Tabelle entfernen oder mit ❌ REJECTED + Begründung markieren |
| R-11 | O-9 Delta-Detection liest pgvector-Timestamps für "letzte Session" — pgvector hat kein Session-Konzept; Timestamp-Lookup ist O(n) ohne Index | **HOCH** | Performance | Dedizierte `AgentSession`-Tabelle mit `started_at`/`ended_at`; Index auf `created_at` |
| R-12 | O-11 Quality Dashboard schreibt Metriken via Grafana read-only DB-User (ADR bestehend) — Write-Path für Metriken fehlt | **HOCH** | Architecture | Metriken via `django_prometheus` oder direkt in `llm_calls`-Tabelle (existiert bereits) |
| R-13 | `CORE_CONTEXT Generator` (O-6) fehlt im Implementation Priority Matrix — im ADR erwähnt aber nicht priorisiert | **HOCH** | Completeness | In Matrix aufnehmen, Phase 2, Aufwand 1h |
| R-14 | Keine i18n-Markierung auf User-facing Strings (z.B. Quality Dashboard Labels, Error-Messages) — Platform-Standard verletzt | **MEDIUM** | i18n | `_()` ab Tag 1 auf alle String-Literals |
| R-15 | `fix_template` in O-7 ist plain String — kein Versionierungsschema, kein `min_django_version` | **MEDIUM** | Maintainability | `fix_template` als strukturiertes Object: `{"code": "...", "since": "django-5.0", "docs_url": "..."}` |
| R-16 | Architektur-Diagramm zeigt `repos.json (KG)` als direkten Backend-Call in `get_full_context()` — repos.json liegt auf Disk, nicht als Service; Call-Semantik ist unklar | **MEDIUM** | Clarity | Im Diagramm klären: `platform_context_mcp.get_repo_facts()` ist der tatsächliche Call |
| R-17 | Decay-Mechanismus für pgvector ("Temporal Decay aktiv") wird im ADR erwähnt aber nie implementiert | **MEDIUM** | Completeness | Celery-Beat-Task `decay_old_memories` in Implementation aufnehmen (Phase 2) |

---

## Positiv-Befunde (keine Änderung erforderlich)

- **D1–D5 Current State Analysis**: Präzise und vollständig — sehr gute Grundlage
- **Option D (gestaffelt)**: Richtige Entscheidung; Phase-Unabhängigkeit gut durchdacht
- **SSH-Tunnel als Bevorzugung gegenüber Port-Opening**: Korrekte Security-Priorisierung
- **`acks_late=True` und `transaction.on_commit()`**: Implizit korrekt in Task-Patterns
- **Dependency-Sequencing (Phase 0 vor Phase 1)**: Exakt richtig — MCP-Blocker zuerst

---

## Gesamtbewertung

| Kategorie | Anzahl |
|-----------|--------|
| BLOCKER | 6 |
| KRITISCH | 4 |
| HOCH | 3 |
| MEDIUM | 4 |

**Empfehlung:** ADR nicht mergen vor Behebung aller BLOCKER + KRITISCH-Befunde (R-01 bis R-10).
