---
id: ADR-214
title: Klickdummy Plattform-Heimat — Distribution & Feedback-Endpoint
status: proposed
date: 2026-05-20
deciders: [achim]
informed: [all-repos-with-klickdummy]
domains: [klickdummy, distribution, services, cross-repo]
supersedes: []
extends: [platform:ADR-211]
depends_on: []
tags: [klickdummy, distribution, plattform-heimat]
scope:
  include_paths:
    - "packages/iil-klickdummy/**"
    - "snippets/klickdummy/**"
    - "schemas/klickdummy/**"
    - "scripts/checks/klickdummy_*.sh"
    - "services/feedback-bridge/**"
---

# ADR-214: Klickdummy Plattform-Heimat — Distribution & Feedback-Endpoint

- **Status:** proposed *(2026-05-20)*
- **Datum:** 2026-05-20
- **Entscheider:** Achim Dehnert
- **Verwandt:** platform:ADR-211 (Rev 12, accepted — Konvention) ← dieser ADR ergänzt um Mechanik
- **Empiriebasis:** meiki-hub PR #23 (7 Iterationen), Cross-Repo-Migrationsrunde 2026-05-20 (writing-hub#21, risk-hub#125, platform#272, meiki-hub#21/#23/#24)

## Zusammenfassung

`platform:ADR-211` Rev 12 etablierte als Konvention zwei optionale Capabilities
(Co-Creation-Loop, Requirements-Bridge) und markierte ihre Plattform-Heimat als
„Best-Effort, kein Termin". Mit **ttz-hub** als 6. Repo + dem expliziten
Anspruch *„permanente Weiterentwicklung wirkt cross-repo"* wird die Frage der
Verteilung verbindlich.

Drei harte Entscheidungen:

1. **pip-Paket als alleinige Distribution (E1, revidiert).** Python-Code +
   Schemas + (in v1.1) HTML-Snippets als `package_data` im **pip-Paket**
   `iil-klickdummy` (initial via `pip install git+...`, später privates PyPI).
   Lokale Convention-Workflows ergänzend via **Symlink-Mechanik** (Bestand
   aus ADR-211 Rev 5). *Initial-Vorschlag „pip + Submodul" wurde im
   adversarial Pass (J2) verworfen — Submodul auf platform/ würde das
   ganze Repo ziehen.*
2. **Zentraler Feedback-Endpoint (E2).** `feedback.iil.pet` (FastAPI o. ä.)
   nimmt Co-Creation-Loop-Payloads entgegen und erzeugt Issues im jeweiligen
   Repo via GitHub-API. Erkennung per Origin-Header und Repo-Token; ein
   Audit-Pfad, eine Wartungs-Stelle.
3. **Eigenständiges ADR (E3).** Nicht als ADR-211 Rev 13, weil
   Distributions-Mechanik orthogonal zur Spec-Konvention ist und Future-
   Challenger den Trade-Off (Submodul vs. pip vs. Symlink) klar lesen
   können soll. ADR-214 referenziert ADR-211 als `extends:`.

## Kontext

Aktueller Stand (post platform#272, 2026-05-20):

- **5 Repos** haben Klickdummy-Code-Pfade: meiki-hub, writing-hub, risk-hub
  (aktiv); pptx-hub, dev-hub (N/A). **ttz-hub** kommt jetzt als 6. dazu.
- **Schemas + Skripte sind kopiert**, nicht geteilt: meiki-hub und writing-hub
  haben je eigene `screens-spec.schema.json`, `check_i1..i4.py`,
  `extract_requirements.py`. Iteration in einem Repo ist nicht in den anderen
  sichtbar (Drift-Risiko und manueller Re-Sync).
- **Widget-Code (≈290 LOC HTML+CSS+JS) lebt in meiki shell.html**. Bei
  Adoption in anderen Repos: copy-paste — und damit nicht in Co-Evolution.
- **Feedback-Endpoint existiert nicht.** Pfad A läuft heute „light"
  (Download → Inbox → Mensch); für die in ADR-211 Rev 12 §Co-Creation
  beschriebene Aktivierung (≥ 1 Mode ≠ download) fehlt der Server-Teil.

Wenn weitergebaut wird ohne Heimat:

- **Drift-Cascade**: jede Iteration in meiki-hub muss in 5 Repos nachgezogen
  werden (Iter. 7 hat das beim Type-Wechsel mock-prototyp → mock real gezeigt:
  5 PRs für eine konzeptuelle Änderung).
- **Adoption-Friction**: ttz-hub müsste copy-paste klonen statt installieren.
- **Co-Creation-Loop bleibt unbenutzbar** im Stakeholder-Sinn ohne Endpoint
  (Pfad A „vollständig" laut ADR-211 Rev 12 §Co-Creation Aktivierungs-
  Bedingung 4: `feedback_loop.path: A | B`).

## Entscheidung — drei Bausteine

### E1 · Distribution: pip-Paket (Python + HTML als package_data) + Symlink

**Initial-Vorschlag war Hybrid pip+Submodul. Im adversarial Pass (J2) wurde
gezeigt:** ein Git-Submodul auf `platform/snippets/` würde das ganze
platform-Repo (hunderte MB) in jeden Klickdummy-Repo ziehen — sparse-Checkout
ist fragil. **Vereinfachte E1:**

| Material | Wo | Wie distribuiert |
|---|---|---|
| **Python-Code** (`check_i1..i4.py`, `extract_requirements.py`, S11-Inventur) | `platform/packages/iil-klickdummy/src/iil_klickdummy/` | **pip-Paket** mit semver; Repos installieren `pip install "iil-klickdummy @ git+https://github.com/achimdehnert/platform.git@v1.0.0#subdirectory=packages/iil-klickdummy"` (F1 geschlossen: Git-URL statt PyPI in v1) |
| **JSON-Schemas** (`screens-spec.schema.json`, `feedback-payload.schema.json`, `module-manifest.schema.json`) | `iil_klickdummy/schemas/` | `package_data` im pip-Paket; Zugriff via `importlib.resources.files("iil_klickdummy.schemas")` ODER `$ref` zu Paket-URL in Spec-Files |
| **HTML-Snippets** (Widget CSS+HTML+JS, Spec-Template, Issue-Template) | `iil_klickdummy/snippets/` (in v1.1) | `package_data` im pip-Paket; Repo-Makefile hat `make klickdummy-install-snippets` Target, das via Python aus dem Paket nach `<repo>/platform-snippets/` kopiert/symlinkt |
| **Lokale Convention-Pfade** (z. B. `~/.claude/policies/klickdummy.md`) | platform-Worktree | **Symlink** (Bestand aus ADR-211 Rev 5, unverändert) |

**Begründung pip-only statt pip+Submodul:**

- **Ein Mechanismus** statt zwei (Vereinfachung).
- **Keine Submodul-Fatigue** in 6 Repos.
- HTML in `package_data` ist **idiomatisches Python**, kein „gegen die Norm"
  (Beispiele: `pip-tools`, `django`, `flask`-templates verteilen HTML so).
- Repos können die Snippets nach `<repo>/platform-snippets/` **kopieren**
  ODER **symlinken** (Wahl pro Repo) — Snippet-Updates via `pip install --upgrade`.

**Konsequenz für Snippet-Standort:** In Rev 1 dieses ADR liegen
Widget/Templates noch unter `platform/snippets/klickdummy/` (für historische
Sichtbarkeit). In v1.1 von `iil-klickdummy` wandern sie in `iil_klickdummy/
snippets/` als `package_data` — ein eigener PR auf platform, kein
Cross-Repo-Bruch (alte Snippet-Pfade werden parallel gehalten, bis alle
Repos auf v1.1 sind; Soft-Migrate-Pattern aus ADR-211 Rev 12).

### E2 · Feedback-Endpoint: zentral (`feedback.iil.pet`)

**Architektur:**

```
[Klickdummy-Widget im Browser]
       │  POST /v1/issues
       │  Body: { payload, markdown }
       │  Header: Origin: <repo-domain>
       ▼
[feedback.iil.pet]  (FastAPI, klein, stateless)
       │  1. Origin → Repo-Mapping (Konfig in platform-Repo)
       │  2. Repo-Token aus Secrets (GitHub App ODER PAT)
       │  3. GitHub API: POST /repos/<repo>/issues
       │     Label: klickdummy-feedback
       │     Body: markdown (vom Widget vorgeformt)
       ▼
[GitHub Issue im jeweiligen Repo]
       │
       ▼
[Coding-Agent (Watcher auf Label)] → Diff-PR
```

**Sicherheit:**

- **Rate-Limit** pro Origin (z. B. 20 Issues/h/Origin) — Spam-Schutz
- **CSRF**: Origin-Header-Allowlist, kein `*`-CORS
- **Audit-Log** pro Issue (Origin, Timestamp, Payload-Hash) — getrennt von Issue-Content
- **PII-Filter** vor Issue-Erstellung (Heuristik: E-Mail, Telefon, IBAN; mark
  `payload_redacted: true` in Issue-Frontmatter)
- **Repo-Allowlist** in Service-Config (kein Wildcard) — verhindert
  Hijack-Issues auf fremde Repos

**Datenschutz-Pfad für Gov-Workloads (ttz-hub-Besonderheit):**

ttz-hub ist `ttz-lif`-Org (Government / Public-Sector mit Data-Sovereignty-
Regeln). Default ist **zentral**; ttz-hub kann jedoch via Konfiguration
einen **eigenen Repo-Endpoint** überschreiben (GitHub Action Webhook im
ttz-hub-Repo). Mechanik:

```html
<!-- ttz-hub/klickdummy/shell.html: -->
<script>
  window.KLICKDUMMY_FEEDBACK_ENDPOINT = "https://ttz-feedback.ttz-lif.de/v1";
</script>
```

→ Repo-Override > Platform-Default. Doku-Empfehlung pro Gov-Repo in
ADR-214 §Migrations-Cookbook.

### E3 · ADR-Strategie: ADR-214 statt ADR-211 Rev 13

Begründung:

| Argument | für ADR-214 (eigenständig) | für ADR-211 Rev 13 (Aufladung) |
|---|---|---|
| **Orthogonalität** | Distributions-Mechanik ≠ Spec-Konvention | hält alles zusammen |
| **Future-Challenger** | sieht 1 ADR pro Frage — Submodul-vs-pip-vs-Symlink getrennt diskutierbar | muss durch alles scrollen |
| **Revisionierbarkeit** | ADR-214 Rev 2 möglich, ohne ADR-211 anzufassen | jede Mechanik-Änderung = ADR-211 Rev N+1 |
| **adr-threshold.md** | „new external dependency or service boundary" → ADR-Pflicht | umgeht den Threshold |

→ **ADR-214 eigenständig.** Referenziert ADR-211 als `extends:`, schließt
keine Frage von dort, erweitert nur die Mechanik.

## Plattform-Bausteine konkret

### Paket `iil-klickdummy` (Python)

```
platform/packages/iil-klickdummy/
├── pyproject.toml                          # name=iil-klickdummy, version=1.0.0
├── README.md
├── src/iil_klickdummy/
│   ├── __init__.py
│   ├── check_i1.py                         # Spec ↔ Route Coverage
│   ├── check_i2.py                         # 4-Pattern + Strict-Mode (LEGACY={})
│   ├── check_i3.py                         # Off-Ramp + Sunset
│   ├── check_i4.py                         # Cross-Repo-Ref-Format
│   ├── extract_requirements.py             # Spec → UC/FR/NFR/Lasten/Pflicht
│   ├── inventory.py                        # S11 Cross-Repo Legacy-Inventur
│   └── schemas/                            # importlib.resources
│       ├── screens-spec.schema.json
│       ├── feedback-payload.schema.json
│       └── module-manifest.schema.json
└── tests/
    ├── test_check_i1_2_3_4.py
    ├── test_extract_requirements.py
    └── fixtures/                            # Beispiel-Specs
```

**Versionierung:** semver. Repos pinnen `>=1.0,<2.0` (kompatibel innerhalb
Major). Breaking Changes (z. B. Pattern-Set ändern) → Major-Bump → ADR-Update.

**Distribution:** initial via `pip install -e ../platform/packages/iil-klickdummy`
(Workspace-Pattern); später PyPI (öffentlich oder privat `pypi.iil.pet`).

### Snippets (HTML/CSS/JS) — initial in `platform/snippets/`, ab v1.1 in pip-Paket

**v1.0 (jetzt):** in `platform/snippets/klickdummy/` (Repo-Sichtbarkeit).
Repos kopieren manuell oder via `curl`-Skript.

**v1.1 (geplant):** als `package_data` im pip-Paket unter
`iil_klickdummy/snippets/`. Repos erhalten sie automatisch via `pip install`;
ein `make klickdummy-install-snippets`-Target kopiert/symlinkt nach
`<repo>/platform-snippets/`.

```
snippets/klickdummy/                       # v1.0 Pfad (auf platform-Repo)
└── (v1.1: iil_klickdummy/snippets/)       # package_data im pip-Paket
├── feedback-widget/
│   └── widget.js                          # selbstständig (CSS+HTML injiziert)
├── issue-template/
│   └── klickdummy-feedback.md
├── spec-templates/
│   └── screens-spec-template.yaml
└── shell-bootstrap/
    └── inject-widget.html                 # 3-Zeilen-Snippet zum Include
```

`KLICKDUMMY_FEEDBACK_ENDPOINT` und `KLICKDUMMY_SPEC` sind Konfigurations-
Variablen vom Host gesetzt — nicht im Snippet hardcoded.

### Service `feedback-bridge`

```
platform/services/feedback-bridge/
├── pyproject.toml
├── src/feedback_bridge/
│   ├── main.py                              # FastAPI
│   ├── github_client.py                     # GitHub API Wrapper
│   ├── pii_filter.py                        # E-Mail/Tel/IBAN-Heuristik
│   ├── audit.py                             # JSON-Lines-Log
│   └── config.py                            # Origin→Repo-Mapping, Allowlist
├── Dockerfile
├── deployment/
│   ├── docker-compose.yml                   # für staging/prod
│   └── traefik.yml                          # via ADR-212 Ingress
└── tests/
```

**Deployment:** via Traefik-Ingress (ADR-212) auf `feedback.iil.pet`.
**Im Rahmen dieses ADR nur Skelett**; eigentliches Deployment ist
**separater Infra-PR** nach ADR-214-Annahme.

### Skript `klickdummy_legacy_class_inventory.sh`

```
platform/scripts/checks/klickdummy_legacy_class_inventory.sh
```

Ist die Migration zur **shared Library** als `python3 -m iil_klickdummy.inventory`.
Bash-Bootstrap aus ADR-211 Rev 12 §Migration bleibt als Fallback erhalten.

## Migrations-Cookbook (5 Repos)

Pro Repo, ~30 Min:

1. **pip-Install** in `requirements-dev.txt`:
   ```
   iil-klickdummy @ git+https://github.com/achimdehnert/platform.git@v1.0.0#subdirectory=packages/iil-klickdummy
   ```
   (Sobald privates PyPI: `iil-klickdummy>=1.0,<2.0`.)
2. **Makefile aktualisieren** — alte Targets aus `scripts/klickdummy/check_iN.py`
   auf `klickdummy-i1` (Console-Script) oder `python3 -m iil_klickdummy.check_iN`
   umstellen.
3. **Snippets installieren** — `make klickdummy-install-snippets` (kopiert
   aus pip-Paket nach `<repo>/platform-snippets/`). In v1.0 Übergangs-
   Vorgehen: snippets aus `platform/snippets/klickdummy/` per `curl` o. ä.
   ziehen; ab v1.1 via `iil_klickdummy.snippets`-Resource.
4. **shell.html aktualisieren** — Widget-Inline-Code entfernen, durch
   3-Zeilen-Bootstrap ersetzen (`platform-snippets/klickdummy/shell-bootstrap/
   inject-widget.html`). Konfiguration:
   ```js
   window.KLICKDUMMY_SPEC = { id: "repo:klickdummy-spec-<name>", version: "0.1", klickdummy_class: "mock" };
   window.KLICKDUMMY_FEEDBACK_ENDPOINT = "https://feedback.iil.pet/v1/issues";
   ```
5. **Issue-Template kopieren** nach `.github/ISSUE_TEMPLATE/klickdummy-feedback.md`
   (aus pip-Paket-Resource oder direkt aus `platform/snippets/.../issue-template/`).
6. **Coding-Agent-Watcher** (per F4 in v1: GitHub Action) — falls
   Co-Creation aktiviert: `.github/workflows/klickdummy-feedback-watcher.yml`
   anlegen, triggert auf `labeled:klickdummy-feedback`.
7. **Lokale Kopien deprecaten** — `scripts/klickdummy/` → `scripts/klickdummy.deprecated/`
   mit README, das auf `iil-klickdummy` verweist. Nach 30 Tagen löschen.
8. **CI testen** — `make klickdummy` muss grün bleiben.
9. **Provenance-Eintrag** (falls Co-Creation aktiviert): „Migration auf
   Plattform-Heimat (platform:ADR-214)".

**ttz-hub (Erst-Adoption):** identisch Schritt 1+2+3+4+5+8, plus:
- Repo-lokales `ADR-XXX-klickdummy-ttz.md` mit `class:`, `sunset_after:`,
  `conforms_to: platform:ADR-211`, `tags:[klickdummy]`
- Mindestens 1 `screens-spec.yaml` (auch minimal — Template unter
  `platform/snippets/klickdummy/spec-templates/screens-spec-template.yaml`).
- **Datenschutz-Override (Gov-Workload, Pflicht):** eigenen Endpoint setzen
  statt Platform-Default. PII-Filter im zentralen Endpoint ist Best-Effort
  (F6) — Gov-Repos müssen sich nicht darauf verlassen.

## Konsequenzen

**Positiv:**
- **1 Quelle für alle Klickdummy-Mechanik**: jede Iteration in `iil-klickdummy`
  wirkt cross-repo nach `pip install --upgrade` (v1.0 via Git-URL, v1.1+
  via privates PyPI sobald aufgesetzt).
- **Adoption-Friction für ttz-hub von ~2 Tage auf ~30 Min**: pip + Submodul
  + Mini-ADR statt copy-paste-clone.
- **Co-Creation-Loop wird real aktivierbar**: Endpoint existiert → Pfad A
  vollständig.
- **Versions-Pinning**: Repos können auf `iil-klickdummy==1.2.0` bleiben,
  wenn sie noch nicht zu `1.3.0` migrieren wollen (semver-Verträglichkeit).

**Negativ / Kosten:**
- **pip-via-Git-URL** in v1: `pip install` braucht Git-Zugang zur platform-
  Repo-URL (öffentlich oder per SSH-Schlüssel in CI). Mitigation: dokumentiert
  im Migrations-Cookbook; ab privates PyPI verschwindet das.
- **Endpoint-Wartung**: 1 zusätzlicher Service (`feedback.iil.pet`). Klein,
  aber 24/7 verfügbar nötig (sonst Fallback auf Download-Mode).
- **PII-Filter im Endpoint**: Heuristik ist nie perfekt. Mitigation:
  `payload_redacted`-Flag transparent; Gov-Workloads (ttz-hub) nutzen
  Repo-Override.
- **Migrations-Aufwand**: 5 Repos × 30 Min = ~2.5 h einmalig.

**Distributions-Mechanik konkret (vor Acceptance entschieden):**

- **F1 GESCHLOSSEN — Paket-Distribution via `pip install git+...`** statt
  PyPI in v1. `pip install "iil-klickdummy @ git+https://github.com/achimdehnert/platform.git@main#subdirectory=packages/iil-klickdummy"`
  funktioniert ohne PyPI-Infra; semver via Git-Tags (`v1.0.0`, `v1.1.0`).
  Migration auf privates PyPI (`pypi.iil.pet`) wenn aufgesetzt — eigenes
  Adoption-ADR/Rev, nicht Voraussetzung für Rev 1.
- **F2 (ADR-214)**: GitHub-App vs. PAT für Endpoint-Repo-Auth — Start mit
  PAT (1 Bot-Account), Migration auf App in Rev 2. Empfehlung steht.
- **F3 GESCHLOSSEN — HTML-Snippets via pip-Paket statt Submodul.**
  Initiale E1-Hybrid-Wahl wurde im adversarial Pass revidiert (J2): Submodul
  auf `platform/snippets/` zieht ganzes platform-Repo (hunderte MB ohne
  sparse-Checkout). **Saubere Lösung:** HTML/JS/CSS-Snippets sind
  `package_data` im pip-Paket; Repos installieren via `pip install` und
  bekommen die Resources über `importlib.resources`. Ein `make
  klickdummy-install-snippets`-Target kopiert/symlinkt sie in den
  Repo-Pfad `platform-snippets/` (oder direkt in `shell.html`-Pfad).
  → **E1 wird vereinfacht: nur pip-Paket** (Python + HTML+CSS+JS als
  Resources). Symlink-Mechanik (ADR-211 Rev 5) bleibt unverändert für
  Convention-Dateien.
- **F4 (ADR-214)**: Coding-Agent-Watcher — der Endpoint legt Issues mit
  Label `klickdummy-feedback`. **Wer reagiert?** Pro Rev 1: **GitHub Action
  pro Repo** (`.github/workflows/klickdummy-feedback-watcher.yml`), die
  bei Issue-Open mit dem Label einen Coding-Agent triggert (z. B. via
  Claude-Code-Action). Ein zentraler Cross-Repo-Watcher wäre Rev 2.
- **F5 (ADR-214)**: Rate-Limit-Skalierung — in-memory ist v1
  (single-replica). Multi-Replica via Redis o. ä. → Rev 2 + Infra-PR.
- **F6 (ADR-214)**: PII-Filter ist **Best-Effort-Heuristik**, KEIN
  DSGVO-konformer Anonymisierer. Gov-Workloads (`ttz-hub`) MÜSSEN
  Repo-Endpoint-Override nutzen (siehe §E2-Datenschutz). Doku-Pflicht im
  ttz-hub-Klickdummy-ADR.
- **F7 (ADR-214)**: Snippet-Templating — `REPO:klickdummy-spec-NAME`-
  Placeholder im `inject-widget.html` ist kein echtes Build-System.
  Migrations-Cookbook beschreibt: Repo führt `sed`/`envsubst`-Schritt im
  `make install`-Target aus, oder kopiert den Snippet und ersetzt manuell.
  Build-System (z. B. Jinja2-Render) als optionale Erweiterung in Rev 2.

## Adversarial-Self-Check (Pre-Review)

| Frage | Antwort |
|---|---|
| Schafft Hybrid mehr Komplexität als Mehrwert? | Komplexität ist real (2 Mechanismen), aber Mehrwert ist groß (pip-Versionierung für Code, Submodul-Direkt-Reference für HTML). Reine pip-Lösung mit `importlib.resources` für HTML wäre möglich, aber Browser-Build dann ungewohnt. |
| Single-Point-of-Failure beim zentralen Endpoint? | Ja. Mitigation: Widget hat Fallback auf Download-Mode bei Endpoint-down (`fbSubmit('download')` automatisch). Endpoint-Downtime = degradiertes Co-Creation, nicht Klickdummy-Ausfall. |
| Wer ist Owner des `iil-klickdummy`-Pakets? | platform-Repo-Maintainer. Releases via GitHub-Releases + (später) PyPI-publish-Workflow. |
| Was passiert, wenn Endpoint missbraucht wird (Spam, malicious issues)? | Rate-Limit + Origin-Allowlist + PII-Filter + Audit-Log + Repo-lokales `klickdummy-feedback`-Label kann gelöscht/blockiert werden. Coding-Agent reagiert nur auf Label. |
| Macht der Endpoint die Architektur-Entscheidung „Pfad B verboten" obsolet? | Nein. Pfad B (Direkt-LLM) wäre `feedback.iil.pet` → LLM-Call (Endpoint-seitig, nicht Browser-seitig). Das ist eine künftige Erweiterung dieses Endpoints — bleibt per ADR-211 Rev 12 §Co-Creation an „plattformweite A-Adoption + LLM-Audit-Framework" geknüpft. |
| Was wenn Repos `iil-klickdummy`-Major bumpen müssen (z. B. Pattern-Set ändert sich)? | semver-Disziplin: Major-Bump = Migrations-Cookbook im ADR (analog ADR-211 Rev 12 §Migration). Soft-Migrate-Pattern wiederverwendbar. |

## Acceptance-Trigger

`status` → `accepted`, sobald:
1. Decider ratifizieren E1/E2/E3-Wahl.
2. `iil-klickdummy`-Paket-Skelett gebaut + 1 Test grün.
3. Mindestens **1 Pilot-Migration** (meiki-hub) erfolgreich (ohne Klickdummy-CI-Bruch).

Adoption-Scoreboard `adr-214-followup` separat (analog ADR-211 SF1–SF11).

## Revisionshistorie

- **Rev 1 (proposed, 2026-05-20)** — Initial. Empirie-getrieben aus
  meiki-Iter.-7-Migrationsrunde (5 PRs für 1 konzeptuelle Änderung) +
  ttz-hub-Onboarding-Trigger. 3 Bausteine (pip-Paket, Snippets, Endpoint)
  + 6 Adversarial-Self-Checks.
- **Rev 1 adversarial Pass (2026-05-20)** — 6 Findings eingearbeitet vor
  Decider-Review:
  - **J1 (🔴):** F1 (Distributions-Mechanik) geschlossen — pip via
    `git+https://...@v1.0.0#subdirectory=...` statt PyPI in v1.
  - **J2 (🔴):** Submodul-Ansatz für HTML-Snippets verworfen (würde ganzes
    platform-Repo ziehen). **E1 vereinfacht zu pip-only mit `package_data`**
    für HTML/CSS/JS in v1.1.
  - **J3 (🟡):** Coding-Agent-Watcher als F4 konkret: GitHub Action pro
    Repo (`klickdummy-feedback-watcher.yml`); zentraler Cross-Repo-Watcher
    in Rev 2.
  - **J4 (🟡):** Rate-Limit als v1 single-replica markiert; Multi-Replica
    via Redis als F5 in Rev 2.
  - **J5 (🟡):** PII-Filter als „Best-Effort, KEIN DSGVO-konformer
    Anonymisierer" deklariert (F6); Gov-Workloads (ttz-hub) MÜSSEN
    Endpoint-Override nutzen.
  - **J6 (🟡):** Snippet-Templating als F7 — Migrations-Cookbook
    beschreibt `sed`/`envsubst`-Schritt; Build-System optional in Rev 2.

## Bezug

- **platform:ADR-211** (Rev 12, accepted) — Konvention, die dieser ADR mechanisch
  unterlegt. Co-Creation §+Requirements-Bridge §+§Migration sind die Vorgabe.
- **platform:ADR-212** (accepted) — Traefik-Ingress-Stack für *.iil.pet;
  `feedback.iil.pet` deployt darüber.
- **platform:ADR-213** (Rev 1) — Cross-Repo-ADR-Ref-Format (`repo:ADR-NNN`);
  `iil-klickdummy.check_i4` setzt das durch.
- **meiki-hub PR #23** — Empirie-Quelle (7 Iterationen).
- **Cross-Repo-Migrationsrunde 2026-05-20** — writing-hub#21, risk-hub#125,
  platform#272, meiki-hub#21/#23/#24 — belegt 5-PRs-pro-Konzeptänderung
  ohne Plattform-Heimat.
- **Policy `adr-threshold.md`** — Selbsttest bestanden: neue Service-
  Boundary + Cross-Repo-Impact + non-trivial trade-off ⇒ eigenständiges ADR.
