---
description: Pre-Code Contract Verification — Annahmen verifizieren bevor der erste Keystroke
---

# /pre-code — Contract Verification (PCV)

**Wann ausführen:** Vor jeder nicht-trivialen Implementierung. Teil von `/agentic-coding` Phase 0.
**Zweck:** Verhindert Review-Iterationen durch proaktive Verifikation aller Annahmen.
**ROI:** ~10 Tool-Calls, spart 2–3 Review-Zyklen à 8k Token.

---

## A) Pattern-Scan — Repo-spezifische Typen verifizieren

```bash
# Wie definiert DIESES Repo tenant_id, public_id, FK-Typen?
grep -r "tenant_id" src/ --include="models.py" | head -5
grep -r "public_id" src/ --include="models.py" | head -5
# Beispiel-Model lesen (ähnliche App)
```

→ Ergebnis als **Constraint Manifest** notieren.

Typische Fallstricke:
- `tenant_id = UUIDField` vs. `tenant_id = BigIntegerField` (repo-spezifisch!)
- `public_id = UUIDField` vorhanden oder nicht?
- FK `on_delete=PROTECT` vs. `CASCADE`

---

## B) Call-Scan — Externe Funktionssignaturen verifizieren

Für jede externe Funktion die aufgerufen wird — **nie aus dem Gedächtnis annehmen**:

```bash
# Signatur lesen
grep -n "^def \|^class " src/<app>/services.py | head -20
# Oder direkt lesen:
# read_file(path)
```

Besonders prüfen:
- `aifw.sync_completion(action_code, messages)` — korrekte Parameter?
- `audit.services.*` — existiert `log()` überhaupt?
- Alle iil-* Package APIs

---

## C) Infra-Scan — Constraints prüfen

```bash
# Nginx Upload-Limit (kritisch bei File-Uploads)
grep "client_max_body" docker/nginx/*.conf 2>/dev/null

# Storage-Backend (S3 oder lokal?)
grep -E "STORAGES|DEFAULT_FILE_STORAGE|S3_ENDPOINT" src/config/settings.py

# Migrations-Stand für betroffene Apps
python -m django showmigrations <app>

# Celery verfügbar?
grep "celery\|CELERY" src/config/settings.py | head -3
```

---

## D) Dependency-Scan

```bash
# Benötigte Packages installiert?
grep -E "<pkg1>|<pkg2>" requirements.txt
pip list | grep iil
```

---

## E) Assumption Register

Jede nicht-verifiable Annahme **inline im Code markieren**:

```python
# ASSUMPTION[verified]: tenant_id = BigAutoField (grep: 5/5 models)
# ASSUMPTION[unverified]: audit.services.log(actor_id, event_type) — vor Merge prüfen
# ASSUMPTION[infra]: nginx client_max_body_size >= 50M — Config prüfen!
```

Unverified Assumptions → **User informieren** und Klärung anfragen.

---

## Output: Constraint Manifest

Nach Phase 0 kurz zusammenfassen:

```
Constraint Manifest — <App-Name>:
- tenant_id: BigIntegerField (verifiziert: 4 Models gecheckt)
- public_id: UUIDField (verifiziert)
- aifw.sync_completion: action_code + messages (verifiziert)
- audit.services.log: NICHT EXISTENT — ASSUMPTION[unverified]
- nginx limit: 25M (Settings sagen 50M → KONFLIKT → User informiert)
- Celery: verfügbar (settings.py gecheckt)
```

→ Dieses Manifest steuert die Implementierung in Step 3.
