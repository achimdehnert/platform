# Klausel-3-Migration (ADR-216 Ziel-Architektur)

**Status:** vorbereitet, nicht deployed.
**Aktivierung:** wenn ADR-212 (Traefik) + ADR-142 (Authentik) auf `staging-platform` real deployed.

## Inhalt

| Datei | Zweck |
|---|---|
| `docker-compose.klausel3.yml` | nginx-Container mit Traefik-Labels + Authentik forwardAuth |
| `MIGRATION-CHECKLIST.md` | 6-Schritt-Migration (~30 Min) |
| `README.md` | Diese Datei |

## Wann aktivieren

Trigger (mind. 1):
- Klickdummy soll auf "prod" Hostname `klickdummy.iil.pet` (Klausel 1) — vorher muss Klausel 3 stabil sein
- Erster Stakeholder fragt nach SSO statt BasicAuth
- BasicAuth-Friction wird zu groß (>6 User, viele Passwort-Resets)
- Audit-Anforderung: Authentik-Event-Log statt Traefik-Access-Log

## Was bleibt unverändert nach Migration

- URL-Pattern `https://staging-klickdummy.iil.pet/<owner>/<repo>/<kd>/`
- 11 Klickdummies live
- sync.sh-Logic
- Cron-Frequenz
- Cross-Repo-Picker (sub_filter wird in Traefik-Variante anders gelöst — siehe §Picker-Patch)
- Home-Button (Traefik kann auch `headers.contentSecurityPolicy` — aber sub_filter nicht direkt)

## Was sich ändert

| Komponente | Klausel 2 (heute) | Klausel 3 (Ziel) |
|---|---|---|
| Reverse-Proxy | Host-nginx-vhost | Traefik-Container-Labels |
| TLS | Wildcard `*.iil.pet` von acme.sh in nginx | Let's Encrypt DNS-01 in Traefik |
| Auth | BasicAuth (htpasswd-Files pro Owner) | Authentik forwardAuth + Group-Bindings |
| Session-Mgmt | Browser-Cache (Realm) | Authentik-Cookie + Logout-fähig |
| User-Mgmt | htpasswd via deploy.sh | Authentik-Admin-UI |
| Picker-Patch | nginx `sub_filter` | **Migration-Item**: Traefik kann sub_filter nicht nativ, muss via Custom-Middleware oder injected im widget.js |
| Home-Button | nginx `sub_filter` | gleiches Problem wie Picker — Lösung: ins widget.js verschieben |

## Picker-Patch + Home-Button nach Migration

Da Traefik kein `sub_filter` hat, müssen Patch + Home-Button **vor** Migration aus dem nginx-vhost in das zentrale `widget.js` wandern. Das ist eine Erweiterung von `iil-klickdummy v1.5` (`platform-snippets/klickdummy/feedback-widget/widget.js`):

```javascript
// Add to widget.js init:
(function injectClickdummyChrome() {
  if (location.hostname !== 'staging-klickdummy.iil.pet') return;

  // Home-Button
  if (!document.getElementById('kd-home-btn')) {
    const a = document.createElement('a');
    a.id = 'kd-home-btn';
    a.href = '/';
    a.textContent = '⌂ Übersicht';
    Object.assign(a.style, {
      position: 'fixed', top: '12px', left: '12px', zIndex: 9999,
      background: '#1a3a6c', color: '#fff', padding: '6px 12px',
      borderRadius: '18px', fontFamily: 'system-ui, sans-serif',
      fontSize: '12px', textDecoration: 'none',
      boxShadow: '0 2px 8px rgba(0,0,0,.2)'
    });
    document.body.appendChild(a);
  }

  // Picker-Aktivierung (alle KDs same-origin → klickbar)
  function patchPicker() {
    if (typeof CROSS_REPO_INDEX === 'undefined' || !Array.isArray(CROSS_REPO_INDEX)) return;
    CROSS_REPO_INDEX.forEach(e => {
      e.local = true; e.reachable = true;
      if (!e.path_rel && e.url) e.path_rel = e.url;
    });
    if (typeof renderCrossRepoCard === 'function') {
      const s = document.getElementById('crpSelect');
      if (s) renderCrossRepoCard(s.value);
    }
  }
  setTimeout(patchPicker, 200);
  setTimeout(patchPicker, 1500);
  setTimeout(patchPicker, 3500);
})();
```

→ Vor Klausel-3-Migration: Patch in `iil-klickdummy v1.5.x` releasen, dann alle Klickdummies-Repos updaten (PR pro Repo).

## Aufwand-Schätzung (gesamt)

| Phase | Was | Aufwand |
|---|---|---|
| **Pre-Migration** | Picker+Home in widget.js v1.5.x | 1 h + 6 Repo-PRs ≈ 2 h |
| **Migration Phase 1** (1 Gruppe) | ADR-212 + ADR-142 müssen schon stehen + Migration-Checkliste | 30 Min |
| **Migration Phase 2** (Owner-Auth) | 5 Apps + 5 Bindings + Path-Filter | 30 Min |
| **Roll-Back-Test** | Falls Klausel 3 instabil | 10 Min |

## Roll-Back

Migration-Checkliste §Roll-Back beschreibt 5 Befehle für volle Klausel-2-Rückkehr.

## Refs

- ADR-216 §Klausel-2-Übergangs-Variante
- ADR-216 §Per-Repo-Auth ohne Authentik (Iter. 32 Patch)
- ADR-217 Owner-Auth Phase 2 (Authentik-Groups + Bindings)
- ADR-212 Traefik-Ingress
- ADR-142 Authentik IdP
