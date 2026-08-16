# Runbook: GitHub App für den Handover-Reconciler

> **Status:** wartet auf Owner-Ausführung (2026-08-16). Der Code-Pfad ist gemergt und
> läuft ohne die App weiter — er nutzt sie automatisch, sobald sie existiert.
> Kein Folge-PR nötig.

## Warum

Der nächtliche `handover-reconcile` läuft mit `${{ github.token }}` und sieht damit nur
das öffentliche `platform`. Gemessen am 2026-08-16, derselbe Handover:

| | Repo-Token (heute) | Flotten-Sicht |
|---|---|---|
| DISKREPANZ | 8 | 18 |
| nicht prüfbar | 12 | 0 |

**Zehn echte veraltete Referenzen sind derzeit unsichtbar.**

App statt fine-grained PAT, weil die Flotte in **fünf Orgs** liegt und ein PAT an genau
einen Resource Owner gebunden ist — fünf Tokens, fünf Ablaufdaten, fünf Stellen für einen
stillen Ausfall. Ein abgelaufener PAT färbt den Nightly nicht rot; er meldet wieder
„nicht prüfbar" für alles.

## Schritte (Owner, ~20 Minuten)

1. **App anlegen** — <https://github.com/settings/apps/new>
   - Name: `iil-handover-reconciler` · Homepage: das platform-Repo
   - **Webhook: deaktivieren** (die App wird nie aufgerufen, sie wird nur gelesen)
   - **Repository permissions — nur diese drei, alle `Read-only`:**
     `Metadata`, `Issues`, `Pull requests`
   - Keine Organization permissions, keine Account permissions
   - „Where can this GitHub App be installed?" → **Any account**
2. **App ID notieren** (steht oben auf der App-Seite).
3. **Private Key erzeugen** → „Generate a private key", die `.pem` wird heruntergeladen.
4. **In fünf Orgs installieren** — App-Seite → „Install App":
   `achimdehnert` · `iilgmbh` · `meiki-lra` · `ttz-lif` · `bahn-sqf`
   Je Org **„All repositories"** (sonst fehlen neue Repos still).
5. **In `achimdehnert/platform` hinterlegen:**
   - Variable `RECONCILE_APP_ID` = die App ID
     (`Settings → Secrets and variables → Actions → Variables`)
   - Secret `RECONCILE_APP_PRIVATE_KEY` = **kompletter** Inhalt der `.pem`,
     inklusive `-----BEGIN…`/`-----END…`-Zeilen
6. **`.pem` lokal löschen** (Wert lebt ab jetzt nur im Secret).
   Zeiger auf den Fundort gehört in `~/.secrets/`, **nie** der Wert selbst.

## Abnahme

`gh workflow run handover-reconcile.yml -R achimdehnert/platform`, dann die Job-Summary
lesen. **Erfolgskriterium ist eine Zeile, nicht ein grüner Haken:**

```
Token-Abdeckung: eigener Token für **achimdehnert, iilgmbh, meiki-lra, ttz-lif, bahn-sqf**
```

Fehlt eine Org in dieser Aufzählung, ist ihre Installation nicht durchgekommen — der Lauf
bleibt trotzdem grün (bewusst), die betroffenen Referenzen stehen unter „nicht prüfbar".
Zusätzlich sollte `nicht prüfbar` deutlich sinken; `DISKREPANZ` **steigt** dabei, das ist
der gewollte Effekt und kein Rückschritt.

## Rückweg

App in der betroffenen Org deinstallieren — wirkt sofort und nur dort. Oder Variable
`RECONCILE_APP_ID` löschen: dann laufen die Token-Schritte gar nicht mehr und alles
verhält sich wie vor diesem Runbook. Kein Code-Rollback nötig.

## Grenzen, bewusst

- Der Private Key liegt als Secret in einem **öffentlichen** Repo. Secrets sind für
  Fork-PRs gesperrt, aber jede Workflow-Änderung auf einem Branch dieses Repos läuft mit
  ihnen. Deshalb die drei Read-only-Berechtigungen und keine einzige mehr.
- Die App bekommt **kein** Schreibrecht. Stufe 2 des Reconcilers (Kommentare schreiben)
  ist per Gate `autonomous-no-human-review` separat gegated und ist hiermit **nicht**
  freigegeben.
