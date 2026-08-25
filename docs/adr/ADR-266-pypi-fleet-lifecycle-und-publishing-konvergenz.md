---
id: ADR-266
title: "PyPI-Fleet: Paket-Lifecycle, Publishing-Konvergenz und Health-Mechanismus (Programm)"
status: accepted
decision_date: 2026-07-04
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
related: [ADR-226, ADR-255, ADR-265]
tags: [pypi, packaging, publish-gate, trusted-publishing, fleet-pattern, lifecycle, programm]
implementation_status: partial
---

# ADR-266 — PyPI-Fleet: Lifecycle, Publishing-Konvergenz, Health-Mechanismus

> **Accepted 2026-07-04 durch Achim Dehnert** (Session e17299, wörtlich „ADR-265 + ADR-266 accepted").

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
    Menschen-/Session-Sache; Sichtung binnen einer Woche. Der wöchentliche
    Health-Report listet je Paket-Repo offene Bot-PRs **und rote main-Checks**
    (Workflow-Step „Bot-PRs + rote main-Checks"; zugleich das Gate
    `critical-alert-no-ticket` ×2 aus Retro e17299-incr B2/B5 — Korrektur:
    die ursprüngliche Fassung dieses Satzes behauptete die Sichtbarkeit,
    bevor sie implementiert war). Regel: jeder dauerrote Check braucht einen
    Issue-Link (Realfall iil-adrfw#50, bandit). Konflikt-Bumps ohne kompatibles
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
   - ~~**PyPI-Org `iil`: zweiten Owner eintragen** (blockt ADR-255 Phase-0, REC-1).~~ **Entfallen 2026-08-25:** die PyPI-Org wird bewusst nicht in Betrieb genommen (ADR-255 Rev 5, platform#2291); an ihre Stelle tritt die Härtung des Kontos `iildehnert` (Recovery-Codes im Vault, Firmenadresse).
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

## Amendment 2026-08-19 — Vier-Org-Vollerhebung + Strategie-Klassifikation ([#2075](https://github.com/achimdehnert/platform/issues/2075) Kriterium 1)

### Vollerhebungs-Nachweis (kein Sampling, kein Search-Index)

Alle Repos je Org paginiert enumeriert, je Repo `pyproject.toml` + `publish*.yml`
gezielt gegen die GitHub-API geprüft (Contents-API, authoritativ):

| Org | Repos gesamt | davon privat | Treffer pyproject/publish | davon PyPI-Fleet-relevant |
|---|---|---|---|---|
| `achimdehnert` | 58 | 29 | 46 | 20 (Registry) + gpufw, iil-demo-fixture |
| `iilgmbh` | 15 | 14 | 9 | iil-fieldprefill, iil-klickdummy, illustration-fw (Registry) + django-lms-lite, iil-doc-templates |
| `ttz-lif` | 1 | 1 | 1 (ttz-hub, App) | 0 |
| `meiki-lra` | 3 | 3 | 2 (Apps) | 0 |

Messfehler in der Erhebung selbst gefunden und korrigiert: `/users/<login>/repos`
liefert nur **öffentliche** Repos (35 statt 58) — für das eigene Konto ist
`/user/repos?affiliation=owner` nötig. Erst damit ist die Erhebung eine Vollerhebung.

### Registry-Lücken (in diesem PR geschlossen → Fleet 20 → 23 Pakete)

| Paket (dist) | Repo | Beleg publiziert | Consumer-Evidenz |
|---|---|---|---|
| `iil-gpufw` | iilgmbh/gpufw (Transfer 2026-08-19, s.u.) | PyPI v0.1.1, Upload 2026-08-16, Author iil.gmbh | writing-hub `requirements.txt` |
| `iil-django-lms-lite` | iilgmbh/django-lms-lite | PyPI v0.1.1, Upload 2026-07-27 | coach-hub `requirements.txt` |
| `iil-doc-templates` | iilgmbh/iil-doc-templates | PyPI v0.3.1, Upload 2026-07-08 | risk-hub `pyproject.toml` |

Damit ist der Handover-Entscheid „django-lms-lite publizieren oder `pypi:`-Feld
entfernen" durch die Realität entschieden: es **ist** publiziert und konsumiert.

### Befunde ohne Registry-Änderung (Folge-Issues, je verlinkt)

- **ifc-mcp:** PyPI-Name `ifc-mcp` gehört einem Dritten (Author „Imants",
  github.com/imants/ifc-mcp) — Namenskollision; unter diesem Namen nie publizieren.
  (Kein Folge-Issue: reine Dokumentation, keine aufgeschobene Arbeit.)
- **nl2cad ist eine 6-Dist-Familie** (`iil-nl2cadfw`-Umbrella + `nl2cad-core/
  -areas/-brandschutz/-gaeb/-nlp`); Registry und Inventar-Tool zählen 1 Zeile
  pro Repo, nicht pro Dist. risk-hub/cad-hub konsumieren `nl2cad-core` von PyPI.
  → [platform#2076](https://github.com/achimdehnert/platform/issues/2076)
- **shared-ci stale:** `install-iil-packages/action.yml` behauptet „iil-fieldprefill
  not on PyPI" — falsch (auf PyPI, 3 372 Downloads/30d) und installiert per Git+PAT.
  → [shared-ci#1](https://github.com/achimdehnert/shared-ci/issues/1)
- **dms-hub vendored `iil-ingest`** (`vendor/iil-ingest/`) statt PyPI-Bezug.
  → [dms-hub#64](https://github.com/achimdehnert/dms-hub/issues/64)
- **riskfw doppelt:** risk-hub trägt eine eingebettete Kopie (`src/riskfw/`) und
  importiert sie; das PyPI-Paket (letzter Upload 2026-03-03) ist umgangen —
  Doppel-Pflege-Risiko, Konsolidierungsentscheid nötig.
  → [risk-hub#618](https://github.com/iilgmbh/risk-hub/issues/618)
- **iil-demo-fixture publish.yml-Rückbau** (Klasse einfrieren, s. Tabelle).
  → [iil-demo-fixture#4](https://github.com/achimdehnert/iil-demo-fixture/issues/4)

### Strategie-Klassifikation (Stand 2026-08-19)

Downloads = pypistats 30 Tage, enthalten Mirror-Rauschen — nur **relativ** lesen.
Consumer-Evidenz = Grep über die lokale Fleet (Hinweis, kein Beweis). Klassen:
**aktiv** = Invest-Ziel für #2075 K2–K4; **einfrieren** = kein Invest, kein
Publish, Repo bleibt; **archivieren-Kandidat** = Owner-Entscheid, nur Vorschlag.

| Paket | letzter Upload | dl/30d | Consumer | Klasse |
|---|---|---|---|---|
| aifw | 2026-08-12 | 4 969 | breit (aifw-Ökosystem) | aktiv |
| promptfw | 2026-07-19 | 4 640 | writing-hub u.a. | aktiv |
| authoringfw | 2026-07-31 | 4 559 | writing-hub | aktiv |
| weltenfw | 2026-08-14 | 4 475 | weltenhub | aktiv |
| iil-testkit | 2026-05-14 | 3 517 | Test-Fleet | aktiv |
| iil-fieldprefill | 2026-04-08 | 3 372 | writing-hub, risk-hub, shared-ci | aktiv |
| iil-reflex | 2026-07-27 | 2 490 | — (jung) | aktiv |
| iil-adrfw | 2026-08-06 | 1 685 | platform-Tooling | aktiv |
| iil-klickdummy | 2026-08-02 | 1 018 | KD-Fleet (ADR-211) | aktiv |
| illustration-fw | 2026-08-04 | 653 | illustration-hub | aktiv |
| iil-codeguard | 2026-05-10 | 497 | dev-hub, risk-hub, shared-ci | aktiv |
| iil-ingest | 2026-05-05 | 405 | dms-hub (vendored), ausschreibungs-hub | aktiv |
| iil-gpufw | 2026-08-16 | 236 | writing-hub | aktiv (NEU) |
| iil-django-lms-lite | 2026-07-27 | 200 | coach-hub | aktiv (NEU) |
| learnfw | 2026-04-29 | 177 | coach-hub, onboarding-hub | aktiv |
| iil-doc-templates | 2026-07-08 | 149 | risk-hub | aktiv (NEU) |
| outlinefw | 2026-07-19 | 80 | writing-hub (git-Pin) | aktiv |
| researchfw | 2026-04-17 | 61 | writing-hub (git-Pin) | aktiv |
| nl2cad-Familie | 2026-06-14 | 21+ | risk-hub, cad-hub | aktiv (Sonderweg uv-Monorepo, ≠ `_ci-pypi`) |
| iil-django-commons | 2026-03-24 | 35 | keine gefunden | einfrieren |
| iil-enrichment | nie publiziert | — | keine gefunden | einfrieren |
| iil-demo-fixture | nie publiziert | — | nur platform-Governance-Refs, kein pip-Consumer | einfrieren (publish.yml zurückbauen) |
| riskfw | 2026-03-03 | 19 | keine (risk-hub nutzt eigene Kopie) | archivieren-Kandidat |
| gaeb-toolkit | nie publiziert | — | Funktion lebt in nl2cad-gaeb | archivieren-Kandidat |

Konsequenz für #2075: K2–K4 (Cold-Start, Kontextdateien, Readiness-Score)
laufen **nur** über die 19 aktiv-Pakete. Archivierung selbst bleibt Owner-Gate
(Out of Scope #2075); dieses Amendment ist der Klassifikations-Beschluss,
wirksam mit Merge dieses PRs (Required-Owner-Review = Freigabe).

### Heimat-Regel (Owner-Weisung 2026-08-19, Kapitäns-Kanal)

**„iilgmbh ist die Heimat unserer Pakete"** — als **Zielbild**, nicht als
Sofort-Fanout: Die Umsetzung je Paket läuft weiter über die ADR-255-Migrationsbahn
(`registry/iil-migration.yaml`), weil bestehende Trusted-Publisher-Bindings an
`achimdehnert/<repo>` gebunden sind und ein Transfer ohne Binding-Umzugsplan den
Publish-Pfad bricht. Erstvollzug: **gpufw** am 2026-08-19 nach `iilgmbh/gpufw`
transferiert (einziger Fall ohne bestehendes Binding — nichts zu brechen;
org-weite Code-Search: 1 Doku-Treffer, kein Install-Pfad). Durchsetzungs-Gate:
der K3-Health-Lauf (#2075) meldet künftig `org != iilgmbh` je aktivem Paket als
Advisory-Metrik „Heimat-Drift".

## Glossar

- **Trusted Publishing (OIDC):** PyPI akzeptiert kurzlebige GitHub-Actions-
  Identitäts-Tokens statt statischer API-Tokens; erzeugt automatisch
  Sigstore-Provenance. Binding wird auf pypi.org je Projekt konfiguriert.
- **Doppel-Publisher:** zwei Workflows (verschiedene Repos) können dasselbe
  Dist auf PyPI hochladen — Race-/Drift-Risiko, verletzt K5.
- **Fleet-File:** `registry/pypi-fleet.yaml`, generiert, nie von Hand editiert.
- **Remote-Publisher:** platform-Workflow, der ein fremdes Repo auscheckt und
  dessen Paket publiziert (Übergangskonstrukt, Abbau in Stufe 2b).
