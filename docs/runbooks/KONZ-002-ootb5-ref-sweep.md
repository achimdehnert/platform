# Runbook — KONZ-002 OOTB-5: Coupling-Indirektion (Ref-Sweep)

> Baustein zu **[KONZ-platform-002](../konzepte/KONZ-platform-002-enterprise-consolidation.md)** OOTB-5; entsperrt **S3 Welle 3** (Prod-`-hub`-Migration).
> Werkzeug: [`tools/ref-sweep.py`](../../tools/ref-sweep.py). Stand: 2026-06-04.

## Analyse

Sorge des Konzepts: verstreute, eigentümer-gebundene `uses: achimdehnert/...@ref`-Referenzen brechen beim Org-/Account-Wechsel (~14 geschätzt). **Reliable-Discovery** (Workflow-Inhalte direkt gelesen — `gh search code` lieferte falsch **0**, indiziert private Repos unzuverlässig):

**Befund: keine verstreute Kopplung, sondern EINE Quelle.** Alle Refs zeigen auf **`achimdehnert/platform`** — 4 geteilte Bausteine:
`_ci-python.yml`, `_deploy-unified.yml`, `_build-docker.yml` (reusable workflows) + `actions/gitleaks-scan` (composite action), dazu diverse `publish-*`/`_ci-pypi`.

**Umfang (2026-06-04, vollständig): 52 Refs in 30 Repos** — alle `-hub`-Apps (privat+public), die 5 bereits migrierten iilgmbh-Repos, **und `platform` selbst** (Self-Refs in seinen eigenen Workflows).

## Werkzeug `tools/ref-sweep.py`

- **Dry-Run (default, read-only):** findet alle `uses: <old>/...@ref` und listet Repo/Datei/Anzahl.
- **`--apply`:** öffnet **eine PR pro Consumer**, ersetzt `<old>/…` → `<new>/…` (Pfad+`@ref` bleiben). Idempotent.
- Args: `--old achimdehnert/platform --new iilgmbh/platform --owners achimdehnert,iilgmbh`.
- **Bug-Lehre (gefangen):** eigene **private** Repos via `user/repos?affiliation=owner` listen — `users/<name>/repos` liefert nur public (führte zu Unterzählung 10 statt 30). Code-Search ebenfalls unzuverlässig → Contents-API ist die Wahrheit.

## Strategie (löst OOTB-5 ohne generischen Alias)

1. **Reihenfolge:** Consumer **zuerst** migrieren (ihre Refs auf `achimdehnert/platform` bleiben gültig, solange platform dort liegt). **`platform` als LETZTES.**
2. **Beim platform-Move:** `ref-sweep.py --apply` über alle Consumer **und** platform-Self-Refs → `iilgmbh/platform`. Ein koordinierter Pass.
3. **Redirect ist KEINE Brücke für `uses:`** (verifiziert 2026-06-04, GitHub-Doku): `git clone/fetch/push` auf der alten URL folgt dem Redirect — **`uses:`-Action-/Reusable-Workflow-Aufrufe aber NICHT.** O-Ton GitHub: *„GitHub will not redirect calls to an action hosted by a renamed repository … fail with `repository not found`."* → Beim `platform`-Move brechen **alle Consumer-`uses:`-Refs sofort**, bis der Sweep durch ist. Konsequenz: **harter Cutover**, nicht „redirect-überbrückt". Optionen:
   - **(a) Minimiertes Cutover-Fenster:** Sweep-PRs vorab als Branches stagen (`ref-sweep` vorbereiten), `platform` moven, dann **alle Sweep-PRs sofort/automatisiert mergen** → Consumer-CI nur Minuten rot. In Low-Activity-Fenster legen.
   - **(b) Zero-Gap via separater Shared-CI-Quelle:** die geteilten Workflows **zuerst** an einem neuen iilgmbh-Ort bereitstellen (eigenes Repo, nicht via Transfer), Consumer dorthin sweepen + grün prüfen, **dann** `platform` ungestört moven (Consumer zeigen schon woanders hin). Kein Fenster, aber mehr Vorlauf.
4. Danach: alles unter `iilgmbh` → Bruchstelle existiert dauerhaft nicht mehr.

## Reihenfolge im Gesamt-Rollout
- S3 Welle 1/2 (isoliert + publiziert): ✅ erledigt — deren Self-Workflows referenzieren weiter `achimdehnert/platform` (gültig).
- **S3 Welle 3 (Prod-Hubs):** kann jetzt laufen — Refs bleiben gültig bis zum platform-Move.
- **Letzter Schritt:** `platform` migrieren + `ref-sweep.py --apply`.

## Gates / Leitplanken
- `--apply` = **scharf** (öffnet ~30 PRs, berührt platform + alle Consumer = max. Blast-Radius) → **separater, ausdrücklich freigegebener** Schritt, gekoppelt an den platform-Move.
- Dry-Run + Review der PR-Liste **vor** `--apply`.
- Redirect-Annahme **verifiziert & falsifiziert** (2026-06-04): `uses:` folgt dem Redirect NICHT → Cutover-Strategie (a)/(b), nicht „redirect-überbrückt".
- **Welle 3 (Hub-Moves) ist davon NICHT betroffen:** Hubs referenzieren `achimdehnert/platform` (bleibt liegen) → ihre Refs gelten weiter; Hubs werden selbst von niemandem via `uses:` referenziert. Der Redirect-Befund betrifft nur den **finalen `platform`-Move**.

## Changelog
- 2026-06-04: Initial — Single-Source-Befund (52 Refs/30 Repos → `platform`), Tool `ref-sweep.py` (dry-run + --apply), Sweep-Strategie + Reihenfolge.
