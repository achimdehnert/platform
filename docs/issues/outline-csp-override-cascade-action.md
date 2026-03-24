# CSP Override für Outline sub_filter Script-Injection

**Labels:** documentation, security, knowledge-hub
**ADR:** ADR-143

## Kontext

Outline Wiki (knowledge.iil.pet) setzt einen CSP-Header mit dynamischem Nonce:
```
script-src https://knowledge.iil.pet 'nonce-abc123...'
```

### Problem
Per Nginx `sub_filter` injiziertes `<script src="/_cascade.js" defer>` hat keinen Nonce → Browser blockiert das Script → **leere Seite** (React-SPA bricht komplett).

### Fix (2026-03-24)
Nginx überschreibt den CSP-Header:
```nginx
proxy_hide_header Content-Security-Policy;
add_header Content-Security-Policy "...script-src 'self' 'unsafe-inline'..." always;
```

### Security-Bewertung
- ⚠️ `'unsafe-inline'` ist weniger restriktiv als Nonce-basierte CSP
- ✅ Akzeptabel: Internes Tool hinter authentik SSO, kein öffentlicher Zugang
- ✅ Andere Security-Header bleiben erhalten (X-Frame-Options, X-Content-Type-Options etc.)

### Betroffene Dateien
- `deployment/nginx/prod/knowledge.iil.pet.conf` — Config aktualisiert
- `docs/adr/ADR-143-knowledge-hub-outline-integration.md` — implementation_evidence ergänzt

### TODO (optional, Stufe 2)
- [ ] Prüfen ob Outline eine Option hat, CSP-Nonces zu deaktivieren
- [ ] Alternative: Outline Custom-Plugin mit eigenem Nonce statt sub_filter
- [ ] Webhook-Automatisierung für Cascade-Aufträge (research-hub Celery Task)

### Referenzen
- ADR-143: Knowledge-Hub — Outline Wiki + research-hub Integration
- Lesson Learned: CSP Nonce blockiert sub_filter (Outline Knowledge Base)
- Konzept: Cascade-Aufträge Workflow (Outline Knowledge Base)
