# ⚠️ Migration Issue - Resolved

**Date:** 2025-12-08 21:15 UTC+1

## Problem:

Performance-Indizes Migration (`0042_add_handler_performance_indices.py`) wurde in der **falschen App** erstellt:
- ❌ Erstellt in: `apps/bfagent/migrations/`
- ✅ Sollte sein: `apps/core/migrations/`

## Grund:

Handler wurden am 17. Nov 2025 von `bfagent.Handler` zu `core.Handler` migriert.
Die neue Migration versuchte Indizes auf `bfagent.Handler` anzulegen, das nicht mehr existiert.

## Fehler:

```
KeyError: ('bfagent', 'handler')
```

Django konnte das Model nicht finden, weil es in der falschen App gesucht wurde.

## Lösung:

Migration gelöscht: `apps/bfagent/migrations/0042_add_handler_performance_indices.py`

## Status:

- ✅ BF Agent funktioniert normal
- ✅ Alle bestehenden Migrationen angewendet
- ⏸️ Performance-Indizes verschoben auf "später"

## Wenn Performance-Indizes später gewünscht:

**Richtig wäre:**

1. Migration in `apps/core/migrations/` erstellen
2. Model: `core.Handler` (nicht `bfagent.Handler`)
3. Dann anwenden

**Oder:** Manuell SQL ausführen:
```sql
CREATE INDEX handler_code_idx ON handlers(code);
CREATE INDEX handler_cat_code_idx ON handlers(category_fk_id, code);
CREATE INDEX handler_active_cat_idx ON handlers(is_active, category_fk_id);
CREATE INDEX handler_recent_idx ON handlers(created_at DESC);
```

---

**Resolved:** Migration deleted, system stable.
**Next:** Continue with BauCAD testing.
