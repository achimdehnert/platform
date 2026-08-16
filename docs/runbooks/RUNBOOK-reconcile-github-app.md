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
5. **Variable und Secret setzen** — ein Kommando, zwei echte Argumente, kein Klicken:

   ```bash
   bash tools/reconcile-app-setup.sh 1234567 ~/Downloads/dein-key.private-key.pem
   ```

   Vorher gefahrlos prüfen: dasselbe mit `--dry-run` anhängen — es wird nichts gesetzt.
   Zum Löschen der `.pem` im selben Zug: `--shred` anhängen (bewusst opt-in).

   Das Skript prüft **vor** jedem Schreibzugriff und bricht laut ab, wenn die App-ID
   keine Zahl ist, die Argumente vertauscht sind oder die Datei kein PEM ist. Der
   Grund ist konkret: ein still gesetzter Platzhalter wäre der teuerste Fehler hier —
   die Token-Schritte im Workflow liefen an, scheiterten je Org, und der Lauf bliebe
   dank `continue-on-error` **grün**. Ein Konfigurationsfehler sähe dann exakt aus wie
   eine fehlende Installation.

   Der Schlüssel geht ausschließlich über stdin an `gh` — nie als Argument (wäre in der
   Prozessliste sichtbar), nie in der Shell-History, nie in einer Ausgabe.
6. **`.pem` löschen** — mit `--shred` oben schon erledigt, sonst `shred -u <datei>`.
   Der Wert lebt ab jetzt nur im Secret; in `~/.secrets/` gehört höchstens ein
   **Zeiger** auf App-Name und Fundort, nie der Schlüssel selbst.

## Abnahme

Ein Lauf, eine Zeile — als Einzeiler kopierbar:

```bash
gh workflow run handover-reconcile.yml -R achimdehnert/platform && sleep 90 && \
gh run list -R achimdehnert/platform --workflow handover-reconcile.yml -L1 \
  --json databaseId -q '.[0].databaseId' | xargs -I{} \
  gh run view {} -R achimdehnert/platform --log | grep -E "Geprüft|Token-Abdeckung"
```

**Erfolgskriterium ist die Abdeckungszeile, nicht der grüne Haken** — der Lauf ist auch
dann grün, wenn keine einzige Installation greift (bewusst, siehe „Grenzen"):

```
Token-Abdeckung: eigener Token für **achimdehnert, iilgmbh, meiki-lra, ttz-lif, bahn-sqf**
```

Fehlt eine Org in dieser Aufzählung, ist ihre Installation nicht durchgekommen; die
betroffenen Referenzen stehen dann weiter unter „nicht prüfbar".

**Vergleichswert vom 2026-08-16, gemessen auf `main` vor der App** ([Lauf
31938846553](https://github.com/achimdehnert/platform/actions/runs/31938846553)):

```
Geprüft: 23 Referenzen · OK 3 · DISKREPANZ 8 · ADRESSFEHLER 0 · nicht prüfbar 12
Token-Abdeckung: kein Org-Token · Default-Token für achimdehnert, iilgmbh, meiki-lra, ttz-lif
```

Erwartung nach der App: `nicht prüfbar` fällt Richtung 0, **`DISKREPANZ` steigt** Richtung
18. Der Anstieg ist der gewollte Effekt — zehn veraltete Referenzen, die vorher niemand
sehen konnte —, kein Rückschritt.

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
