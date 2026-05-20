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

1. **Hybrid-Distribution (E1).** Python-Code + Schemas via **pip-Paket**
   `iil-klickdummy`; HTML-Snippets + Templates via **Git-Submodul**
   `platform-snippets`; lokale Workflows ergänzend via **Symlink-Mechanik**
   (Bestand aus ADR-211 Rev 5).
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

### E1 · Distribution: Hybrid (pip + Submodul + Symlink)

| Material | Wo | Wie distribuiert |
|---|---|---|
| **Python-Code** (`check_i1..i4.py`, `extract_requirements.py`, S11-Inventur) | `platform/packages/iil-klickdummy/` | **pip-Paket** mit semver; Repos installieren `pip install iil-klickdummy>=1.0,<2.0` |
| **JSON-Schemas** (`screens-spec.schema.json`, `feedback-payload.schema.json`, `module-manifest.schema.json`) | `iil-klickdummy/schemas/` (Paket-Resource) | mitversendet im pip-Paket; Repos referenzieren via `importlib.resources` oder `$ref` zu Paket-URL |
| **HTML-Snippets** (Widget CSS+HTML+JS, Spec-Template, Issue-Template) | `platform/snippets/klickdummy/` | **Git-Submodul** pro Repo `platform-snippets/`; via `<script src="platform-snippets/klickdummy/feedback-widget.js">` |
| **Lokale Convention-Pfade** (z. B. `~/.claude/policies/klickdummy.md`) | platform-Worktree | **Symlink** (Bestand aus ADR-211 Rev 5, unverändert) |

**Begründung Hybrid statt nur-pip oder nur-Submodul:**

- **pip** ist Standardweg für Python-Code+Schemas (Versionierung, CI-Reproduzierbarkeit, semver-Pinning). HTML-Snippets in pip-Paket sind „gegen die Norm" (Browser läuft kein pip).
- **Submodul** ist Standardweg für serverseitig-statische HTML-Assets (Build-Inline oder Direct-Reference). Für reinen Python-Code ist Submodul Overhead.
- **Symlink-Mechanik** für lokale Workflows (Convention-Dateien, gepinnter Worktree) hat sich in ADR-211 Rev 5 bewährt und bleibt unverändert.

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

### Submodul `platform-snippets`

```
platform/snippets/klickdummy/
├── feedback-widget/
│   ├── widget.html                          # FAB + Panel-Markup
│   ├── widget.css
│   └── widget.js                            # fbToggle, fbSubmit, etc.
├── issue-template/
│   └── klickdummy-feedback.md
├── spec-templates/
│   ├── screens-spec-template.yaml
│   └── module-manifest-template.json
└── shell-bootstrap/
    └── inject-widget.html                   # 3-Zeilen-Snippet zum Include
```

**Verteilung:** jeder Repo macht `git submodule add … platform-snippets`.
`KLICKDUMMY_FEEDBACK_ENDPOINT` ist Konfigurations-Variable, nicht im Snippet
hardcoded.

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

1. **pip-Pin in `requirements-dev.txt`** (oder `pyproject.toml`):
   `iil-klickdummy>=1.0,<2.0`
2. **Submodul hinzufügen:**
   `git submodule add git@github.com:achimdehnert/platform-snippets ... platform-snippets`
3. **Makefile aktualisieren** — alte Targets aus `scripts/klickdummy/check_iN.py`
   auf `python3 -m iil_klickdummy.check_iN ...` umstellen.
4. **shell.html aktualisieren** — Widget-Inline-Code entfernen, durch
   `<script src="platform-snippets/klickdummy/feedback-widget/widget.js">` ersetzen.
   Konfiguration: `window.KLICKDUMMY_FEEDBACK_ENDPOINT = "https://feedback.iil.pet/v1/issues";`
5. **Lokale Kopien deprecaten** — `scripts/klickdummy/` → `scripts/klickdummy.deprecated/`
   mit README, das auf `iil-klickdummy` verweist. Nach 30 Tagen löschen.
6. **CI testen** — `make klickdummy` muss grün bleiben.
7. **Provenance-Eintrag** (falls Co-Creation aktiviert): „Migration auf
   Plattform-Heimat (ADR-214)".

**ttz-hub (Erst-Adoption):** identisch Schritt 1+2+3+4, plus:
- Repo-lokales `ADR-XXX-klickdummy-ttz.md` mit `class:`, `sunset_after:`,
  `conforms_to: platform:ADR-211`, `tags:[klickdummy]`
- Mindestens 1 `screens-spec.yaml` (auch leer mit nur `class:` + 1 Screen)
- **Datenschutz-Override** (Gov-Workload): eigenen Endpoint setzen statt
  Platform-Default. ADR-214 §E2-Datenschutz dokumentiert das.

## Konsequenzen

**Positiv:**
- **1 Quelle für alle Klickdummy-Mechanik**: jede Iteration in `iil-klickdummy`
  wirkt cross-repo nach `pip install --upgrade` (oder Submodul `git pull`).
- **Adoption-Friction für ttz-hub von ~2 Tage auf ~30 Min**: pip + Submodul
  + Mini-ADR statt copy-paste-clone.
- **Co-Creation-Loop wird real aktivierbar**: Endpoint existiert → Pfad A
  vollständig.
- **Versions-Pinning**: Repos können auf `iil-klickdummy==1.2.0` bleiben,
  wenn sie noch nicht zu `1.3.0` migrieren wollen (semver-Verträglichkeit).

**Negativ / Kosten:**
- **Submodul-Komplexität**: 6 Repos müssen `git submodule update`
  routinemäßig laufen lassen (Submodul-Fatigue). Mitigation: Makefile-Target
  `make install` macht das transparent; CI macht das auf jedem Build.
- **Endpoint-Wartung**: 1 zusätzlicher Service (`feedback.iil.pet`). Klein,
  aber 24/7 verfügbar nötig (sonst Fallback auf Download-Mode).
- **PII-Filter im Endpoint**: Heuristik ist nie perfekt. Mitigation:
  `payload_redacted`-Flag transparent; Gov-Workloads (ttz-hub) nutzen
  Repo-Override.
- **Migrations-Aufwand**: 5 Repos × 30 Min = ~2.5 h einmalig.

**Offen / Folge-Punkte:**
- **F1 (ADR-214)**: PyPI-Hosting — initial Workspace-pip, später public PyPI
  oder privater Index? Entscheidung in `pyproject.toml`-PR.
- **F2 (ADR-214)**: GitHub-App vs. PAT für Endpoint-Repo-Auth? GitHub-App
  ist sauberer (Repo-Scope, fine-grained), aber Setup-Aufwand höher. Empfehlung:
  Start mit PAT (1 Bot-Account), Migration auf App in Rev 2.
- **F3 (ADR-214)**: Submodul-Branch — `main` oder eigener `release`-Branch?
  Empfehlung: `main` (semver-disziplin im pip-Paket trägt; Snippets sind
  rückwärts-kompatibel zu halten).

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
  ttz-hub-Onboarding-Trigger. 3 Bausteine (pip-Paket, Submodul, Endpoint)
  + 4 Adversarial-Self-Checks.

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
