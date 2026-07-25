# Convention: Schema-Migrationen im Deploy

> Gilt für alle Repos, die über `/opt/scripts/deploy.sh` (ADR-120/166) deployen.
> Quelle des Skripts: `platform/scripts/deploy.sh`.

## Was der Deploy garantiert

Seit `deploy.sh` 2026-07-25.1 führt jeder Deploy die Django-Migrationen selbst aus.
Reihenfolge innerhalb eines Deploys:

```
pull (neues Image)
  └─ migrate            ← Wegwerf-Container des NEUEN Images, alter Stack bedient noch Traffic
  └─ migrate --check    ← Verifikation: nichts mehr pending
up -d --force-recreate  ← erst jetzt übernimmt der neue Code
health-check + crashloop-gate
```

Diese Reihenfolge ist bewusst gewählt:

| Fehlerfall | Ergebnis |
|---|---|
| `migrate` schlägt fehl | Deploy bricht ab (`exit 2`), **alter Code + altes Schema laufen unberührt weiter**. `.env` wird auf den laufenden Tag zurückgesetzt. |
| Nach `migrate` bleibt etwas pending | Deploy bricht ab (`exit 2`). Kein Auto-Rollback — Teil-Migrationen lassen sich nicht sicher zurückrollen. |
| Kein Django-Stack | Deploy läuft normal weiter (No-op, wird geloggt). |

Es gibt **kein** Fenster, in dem der neue Code auf ein altes Schema trifft. Das umgekehrte
Fenster — alter Code auf neuem Schema — existiert für die Dauer von `up -d` und ist der
Grund für die Regel unten.

## Deine Pflicht: expand/contract

Eine Migration muss zum **alten** Code rückwärtskompatibel sein, weil der alte Code sie für
einige Sekunden bereits sieht.

- ✅ Spalte hinzufügen (nullable oder mit Default), Tabelle hinzufügen, Index hinzufügen
- ✅ Neue Spalte befüllen (Data-Migration)
- ❌ Spalte/Tabelle löschen oder umbenennen, `NOT NULL` ohne Default nachziehen,
  Typ inkompatibel ändern — **im selben Release, in dem der Code sie noch nutzt**

Löschen/Umbenennen geht in **zwei** Releases: Release 1 nimmt den Code raus (Feld unbenutzt),
Release 2 löscht die Spalte. Das ist die übliche expand/contract-Disziplin und keine
Eigenheit dieses Setups.

## Stellschrauben

| Env | Wirkung |
|---|---|
| `DEPLOY_MIGRATE=0` | Migrate-Schritt aus. Für Stacks, die bewusst anders migrieren. Begründung gehört ins Repo-CLAUDE.md. |
| `DEPLOY_MIGRATE_SERVICE=<svc>` | Überschreibt die Service-Heuristik (`*web`), falls der Django-Service anders heißt. |

## Wenn der Deploy am Migrations-Gate rot wird

1. `showmigrations` auf dem Host ansehen — **nicht** blind `--fake`.
2. `--fake` ist genau die Ursache des schlimmsten Falls, den wir hatten: ein
   half-applied `0002` (Spalte physisch da, aber nicht in `django_migrations`)
   ließ jedes spätere `migrate` mit „already exists" abbrechen
   (illustration-hub#66, 2026-07-24).
3. Erst wenn der Zustand verstanden ist, gezielt heilen — dann neu deployen.

## Warum es das braucht (Historie)

`deploy.sh` hatte bis 2026-07-25 **keinen** migrate-Schritt — gemessen, nicht vermutet
(`grep -c migrate` = 0 in Git *und* auf beiden Hosts). Kein Layer der Kette (Host-Skript,
shared-ci `_deploy-unified.yml`, compose, Entrypoint) migrierte. Gemergte Migrationen
erreichten die Prod-DB also nie, während der Deploy grün meldete — maskiert, solange kein
Code-Pfad die neuen Spalten las.

Aufgeflogen am 2026-07-24, als der erste echte Render in illustration-hub an
`column "is_active" does not exist` starb, obwohl die Migration seit einem Tag gemergt und
„deployt" war (illustration-hub#66).

Ergänzend prüft `tools/deploy-script-drift.sh` (in jeder Session via
`tools/session_start_checks.sh` Phase 0.7.1), dass die Host-Kopie des Skripts überhaupt dem
Git-Stand entspricht — auch das lief unbemerkt auseinander.
