# Convention: Einheitlicher Dev-Test-User (`demo.iil.pet` / `demo12345`)

> **Scope:** ORG-WEIT (platform = kanonische Quelle) · gilt für alle lokal/Dev lauffähigen
> Apps in allen Hubs (illustration-hub, risk-hub, ttz-hub, dev-hub, …).
> **Status:** ENTWURF 2026-06-28 (abgeleitet illustration-hub, Comic-UI-Testsession) —
> Review/Freigabe ausstehend, dann org-weiter Rollout.
> **Motivation:** Beim lokalen Testen nicht raten müssen, *welcher* Login gilt; ein
> gleichnamiger Account über alle Repos spart Reibung.

---

## 1 — Regel

Jede lokal/Dev lauffähige App stellt einen **dev-only** Test-User bereit:

| Feld | Wert |
|---|---|
| Username | **`demo.iil.pet`** (org-weit identisch) |
| Passwort | **`demo12345`** |
| Rechte | `is_staff=True` (Login über `/admin/login/` o. ä.), **kein** Superuser by default |

Ein **einziger** Name über alle Repos (nicht `demo-<repo>`): minimaler Tipp-Aufwand,
nichts zu merken. Der Name ist bewusst **unauffällig** (hostname-artig statt schlicht
`demo`) — schwerer zu erraten, falls eine Dev-Instanz versehentlich exponiert ist; ersetzt
aber **nicht** den Prod-Guard (§2). Eindeutigkeit pro Repo ist nicht nötig, weil jede App
ihre **eigene** lokale DB hat (kein gemeinsamer Account-Raum).

## 2 — Guardrail (verbindlich)

Der Demo-User ist **ausschließlich** für Dev/Local. Verboten in Staging/Prod.

- Anlage **nur** wenn `DEBUG=True` (bzw. äquivalenter Dev-Marker). Der Seed-Mechanismus
  **muss** bei `DEBUG=False` hart abbrechen.
- Niemals in Migrationen/Fixtures, die in Prod laufen. Niemals als Superuser seeden.
- Kein Commit echter Session-Cookies/Tokens dieses Users.

Begründung: ein Account mit öffentlich bekanntem Schwachpasswort in Prod ist ein
direktes Einfallstor (`evidence-discipline` / Security-Perimeter).

## 3 — Mechanismus: idempotentes Seed-Command

Jedes Repo stellt einen reproduzierbaren, idempotenten Befehl bereit. Django-Referenz
(illustration-hub, `apps/core/management/commands/seed_demo_user.py`):

```python
class Command(BaseCommand):
    def handle(self, *args, **opts):
        if not settings.DEBUG:                       # Guardrail
            raise CommandError("seed_demo_user ist dev-only (DEBUG=True erforderlich).")
        user, _ = get_user_model().objects.get_or_create(username="demo.iil.pet")
        user.set_password("demo12345"); user.is_staff = True; user.is_active = True
        user.save()
```

Aufruf: `python manage.py seed_demo_user`. Nicht-Django-Stacks bilden dasselbe Verhalten
(idempotent + Dev-Guard) in ihrem nativen Seed-Werkzeug ab.

## 4 — Einstieg dokumentieren

Repo-`README`/`AGENT_HANDOVER` nennt den lokalen Einstieg explizit, z. B.:

> Lokal testen: `make dev` → `http://localhost:<port>/admin/login/` → `demo.iil.pet` / `demo12345`
> (vorher einmalig `python manage.py seed_demo_user`).

## 5 — Wann NICHT

- Repos ohne lokal lauffähige UI/Auth (reine Libraries, MCP-Server ohne Login).
- Geteilte Staging-DBs mit echten Test-Accounts — dort gelten die normalen Identitäten.

## Changelog

- 2026-06-28: Initial-Entwurf. Abgeleitet aus illustration-hub (Comic-UI-Testsession,
  PR #43): dort `seed_demo_user` + `demo.iil.pet`/`demo12345` eingeführt. Org-weite Freigabe offen.
