---
id: ADR-266
title: "PyPI-Fleet: Paket-Lifecycle, Publishing-Konvergenz und Health-Mechanismus (Programm)"
status: proposed
date: 2026-07-04
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
related: [ADR-226, ADR-255, ADR-265]
tags: [pypi, packaging, publish-gate, trusted-publishing, fleet-pattern, lifecycle, programm]
implementation_status: in-progress
---

# ADR-266 — PyPI-Fleet: Lifecycle, Publishing-Konvergenz, Health-Mechanismus

> Programm-ADR (Auftrag Achim 2026-07-04): „alle Repos, die als PyPI dienen,
> analysieren und so optimieren, dass sie ihren Zweck erfüllen und sich stetig
> verbessern können — mit einem Mechanismus, der das für die Zukunft übernimmt."
> Dieses ADR ist der **Aufsetzpunkt für jede Folge-Session** (Mensch oder Agent):
> Ground Truth = `registry/pypi-fleet.yaml` (regenerierbar), Plan = dieses ADR.

## Kontext und Problemstellung

Befund 2026-07-04 (Evidenz via `tools/pypi_fleet_inventory.py`, Stand im
Fleet-File): **21 Pakete**, aber kein konsistenter Zustand:

- **Inventar-Drift:** 4 publizierende Repos fehlten in der Registry
  (iil-django-commons, iil-fieldprefill¹, iil-klickdummy, riskfw); Registry-Paket
  `django-lms-lite` hat keinen Publish-Pfad; `gaeb-toolkit` ist Registry-Paket
  ohne publish-Workflow (¹fieldprefill war vorhanden — Korrektur betraf 3 + 1 Doppel-Fund).
- **Doppel-Publisher:** `iil-ingest` wird von Repo UND platform publiziert
  (beide zuletzt 2026-05-05); `iil-codeguard` nur noch von platform (Repo-seitig
  kein publish.yml auf main — lokale Datei ist Branch-Artefakt).
- **Tote Publisher:** platforms `publish-packages.yml` (Matrix: django-tenancy,
  concept-templates, dvelop-client) und `publish-platform-context.yml`
  referenzieren gelöschte `packages/`-Pfade; letzte Läufe rot (März) bzw.
  seit Pfad-Löschung nicht lauffähig. `testkit` (archiviert, Actions inert)
  trägt denselben Dist-Namen wie `iil-testkit`.
- **Auth-Flickenteppich:** 8× pur OIDC (Trusted Publishing), 3× pur Token-Secret
  (iil-codeguard, iil-django-commons, iil-ingest), 4× hybrid (aifw, learnfw,
  promptfw, weltenfw — OIDC deklariert, Token-Referenz zusätzlich).
- **Kein Verbesserungs-Eingang:** 0 gesampelte Paket-Repos mit Dependabot/
  Renovate; ADR-226-Reusable `_ci-pypi.yml` hat 0 externe Consumer (17
  handgerollte publish.yml).

## Entscheidung: gestuftes Programm

„Perfekt" wird operationalisiert als **7 prüfbare Kriterien je Paket** (K1–K7),
„stetig verbessern" als **detektierender, nie handelnder Mechanismus**.

### Kriterien K1–K7 (Soll-Zustand je Paket)

| # | Kriterium | Prüfung |
|---|---|---|
| K1 | CI grün auf main | main-Status |
| K2 | Publish-Gate by-construction (Test ODER gitleaks via `needs:` vor Upload, ADR-226) | `tools/check_publish_gate.py` |
| K3 | Version konsistent: pyproject ↔ git-Tag ↔ PyPI | Fleet-Inventar |
| K4 | Auth = pures Trusted Publishing (OIDC, keine Token-Secrets) | Fleet-Inventar |
| K5 | Genau EIN Publisher, im Paket-Repo selbst (ADR-226-Invariante) | Fleet-Inventar |
| K6 | Registry-Eintrag mit `pypi:`-Feld (SSoT canonical.yaml) | Fleet-Inventar |
| K7 | Consumer-Contract: designierter Consumer baut gegen Release-Kandidat vor Tag | CI-Job (Stufe 3a) |

### Stufen

> **Statuskorrektur 2026-07-04 (2. Evidenzrunde, Stufe-2b/3-Umsetzung):**
> (a) Der Erst-Scan las **lokale Klone** — die waren stale; das Tool liest jetzt
> **origin/main** (lokal) bzw. die **GitHub-API** (`--remote`, CI).
> (b) Das K2-Backlog (aifw, researchfw, iil-ingest) war durch **Parallel-PRs
> bereits gedraint** (aifw#26, researchfw#7, iil-ingest#4). (c) iil-ingest#4
> entschied den Doppel-Publisher **anders als unten skizziert**: repo-seitiger
> Publisher entfernt, „platform-Kopie kanonisch" — akzeptiert; K5 heißt damit
> „genau EIN Publisher", nicht zwingend im Paket-Repo. Verbleibender
> Doppel-Publisher: **iil-testkit** (Remote-Scan-Fund: repo-seitig UND
> platform-remote). (d) Stufe 3 umgesetzt: `pypi-fleet-health.yml`
> (wöchentlich Mo 06:30, read-only, ein Tracking-Issue) + `--remote`/`--downloads`.

- **Stufe 1 — Inventar-Wahrheit** ✅ *(PR #910)*: Fleet-Inventar-Tool +
  `registry/pypi-fleet.yaml`; Registry-Reconcile (3 Einträge ergänzt); tote
  platform-Publisher entfernt (`publish-packages.yml`, `publish-platform-context.yml`).
- **Stufe 2a — Auth-Konvergenz (Token-Abbau)** 🟡: **Run-Log-Prüfung 2026-07-04
  falsifizierte die Ausgangsannahme** „Hybrid = Token tot": aifw (Run 28024503285,
  2026-06-23) und learnfw (25115929231) publizierten nachweislich MIT Token
  (`password set by command options`) — die OIDC-Deklaration ist dort der tote
  Teil; promptfw hat keinen erfolgreichen Publish-Run. Folge: **kein** Token darf
  vor PyPI-seitigem Trusted-Publisher-Binding entfernt werden (Binding headless
  nicht prüfbar) → 2a = Evidenz im Fleet-File + Owner-Checkliste (Bindings für
  die 7 Nicht-pur-OIDC-Repos), Code-Umstellung folgt binding-weise als
  Trivial-Commit (Token-Zeile raus, Run beweist OIDC).
- **Stufe 2b — CI-Konvergenz** ✅ *(2026-07-04, freigegeben + ausgeführt)*:
  **18/19 Repos** rufen `_ci-pypi.yml@main` als Thin-Caller (CI, nicht Publish —
  Re-Scope der 2. Evidenzrunde: das Reusable publiziert nicht; Publish bleibt
  per ADR-226 pro Repo). **Ausnahme nl2cad (dokumentierter Entscheid):**
  uv-Workspace-Monorepo, `pip install -e .`-Annahme des Reusables passt nicht —
  nl2cad#36 begründet geschlossen, bespoke uv-CI bleibt kanonisch, K-Kriterien
  laufen über den Health-Report. **Gelernter Preis (Retro e17299 F6):** Die
  Erst-Konvergenz ließ blockierendes mypy (iil-adrfw, outlinefw) und bandit
  (iil-adrfw) still entfallen — wiederhergestellt via `mypy_blocking`/
  `enable_bandit`-Inputs; Regel seither: **CI-Replace erfordert
  Job-Katalog-Diff** (Namen + Blocking-Flags) im PR-Body.
- **Stufe 3 — Health-Mechanismus** ✅ *(2026-07-04, live)*:
  `pypi-fleet-health.yml` — wöchentlich Mo 06:30, read-only, pflegt EIN
  Tracking-Issue (Label `pypi-fleet-health`); `pull_request`-Trigger =
  erzwungener Dry-Run als dauerhafter Wiring-Beweis.
  **Kein Auto-Publish, kein Auto-Fix, keine LLM-Urteile** (deterministisch).
  - **3a Consumer-Canary** (K7) ⬜ — noch offen, je Paket-Release.
  - **3b Dependabot** ✅ fleet-weit (19 Repos, monatlich gruppiert, nie
    Auto-Merge). **Triage-Pfad (Retro e17299 F3):** Folge-PRs sind
    Menschen-/Session-Sache; Sichtung binnen einer Woche (der Health-Report
    hält offene Bot-PRs sichtbar); Konflikt-Bumps ohne kompatibles
    Parent-Release (Realfall iil-adrfw#48: pydantic-core 2.47.0 ohne
    passendes pydantic) werden im PR zurückgenommen, nicht gemergt.
  - **3c Totes-Paket-Signal** ✅: `--downloads` (pypistats) → Finding
    `archival_candidate_stale_and_unused`; Kandidaten werden Issue, nie Auto-Aktion.

### Betrachtete Alternativen

- *Zentraler Publish in shared-ci:* verworfen — ADR-226-Invariante (Gate
  unmittelbar vor Upload, Publish pro Repo).
- *Auto-Fix im Mechanismus:* verworfen — Publish ist irreversibel;
  Gate `autonomous-no-human-review`.
- *Qualitäts-Prozent-Gates (Coverage/Doku) über alle Pakete:* verworfen —
  erzeugt bei heterogener Reife Dauerrot statt Verbesserung.

## Konsequenzen

- Positiv: ein maschinenlesbarer, regenerierbarer Fleet-Zustand; jede
  Verbesserung wird messbar (K1–K7-Abdeckung); Secrets-Fläche sinkt (2a),
  Wartung sinkt (2b), Drift wird sichtbar statt vergessen (3).
- Negativ/Preis: `pypi-fleet.yaml` churnt bei Regeneration (bewusst — Frische
  ist Signal); Stufe 2b berührt 17 Repos (koordinierter Sweep nötig).

### Confirmation

- `python3 tools/pypi_fleet_inventory.py --check` → Findings-Delta gegen
  eingecheckten Stand ist das Programm-Backlog.
- Stufen-Fortschritt = sinkende Finding-Klassen im Fleet-File
  (Ziel: nur noch leere `findings:`-Listen).

## Handover — wo eine Folge-Session aufsetzt

1. `python3 tools/pypi_fleet_inventory.py` laufen lassen (regeneriert Ground
   Truth; `--offline` ohne Netz). Diff gegen eingecheckten Stand lesen.
2. Offene Owner-Aktionen (nur Mensch kann sie tun):
   - **PyPI-Org `iil`: zweiten Owner eintragen** (blockt ADR-255 Phase-0, REC-1).
   - **Trusted-Publisher-Bindings auf pypi.org anlegen/prüfen** für alle 7
     Nicht-pur-OIDC-Repos: iil-codeguard, iil-django-commons, iil-ingest
     (pur Token) + aifw, learnfw, promptfw, weltenfw (hybrid; aifw/learnfw
     publizieren beweisbar per Token, s. Stufe 2a). Je Binding danach:
     Agent entfernt die Token-Zeile und der nächste Release-Run ist der Beleg.
   - Entscheiden: `django-lms-lite` + `gaeb-toolkit` + `packages/adr-review` —
     publizieren (dann publish.yml nach 2b-Muster) oder Registry-`pypi:`-Feld
     entfernen.
3. Stufe 2b/3 sind **ausgeführt** (2026-07-04, Freigabe Achim erteilt — s.
   Stufen-Status oben); NICHT erneut anstoßen. Offen aus 2b/3: 3a-Canary,
   Dependabot-Folge-PR-Triage, iil-testkit-Doppel-Publisher. Historischer
   Wortlaut (überholt): „gegated — Freigabe einholen,
   dann: 2b-Sweep mit Canary-Consumer-PR pro Repo; 3 als `pypi-fleet-health.yml`
   (Namensregel beachten: NICHT `publish-*` nennen — `publish_gate_invariant.sh`
   globt darauf).
4. Offender-Issues (K2-Backlog, Stand 2026-06-30): iil-adrfw#14, iil-codeguard#3,
   iil-ingest#3, nl2cad#24, iil-enrichment (Meter-Fund).

## Glossar

- **Trusted Publishing (OIDC):** PyPI akzeptiert kurzlebige GitHub-Actions-
  Identitäts-Tokens statt statischer API-Tokens; erzeugt automatisch
  Sigstore-Provenance. Binding wird auf pypi.org je Projekt konfiguriert.
- **Doppel-Publisher:** zwei Workflows (verschiedene Repos) können dasselbe
  Dist auf PyPI hochladen — Race-/Drift-Risiko, verletzt K5.
- **Fleet-File:** `registry/pypi-fleet.yaml`, generiert, nie von Hand editiert.
- **Remote-Publisher:** platform-Workflow, der ein fremdes Repo auscheckt und
  dessen Paket publiziert (Übergangskonstrukt, Abbau in Stufe 2b).
