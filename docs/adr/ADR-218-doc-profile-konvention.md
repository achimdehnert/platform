---
id: ADR-218
title: "Adopt projekttyp-spezifisches Doc-Profile mit plattform-globalem Pflicht-Katalog-Schema"
status: proposed
decision_date: 2026-05-21
amended: 2026-05-25
deciders: [Achim Dehnert]
consulted: [self-advocatus-diabolus, /adr-challenger, /adr-review]
informed: [meiki-lra, bahn-sqf, ttz-lif, iilgmbh, achimdehnert]
domains: [governance, documentation, compliance, klickdummy]
implementation_status: partial
implementation_evidence:
  - "platform PR #290 — ADR + Schema + Check + Policy (dieser PR)"
  - "meiki-hub PR #41 — Pilot-Instanziierung lra-pilot + A0-Skeleton"
scope:
  include_paths:
    - "docs/conventions/doc-profile-schema.yaml"
    - "scripts/checks/doc_profile_check.sh"
    - "policies/doc-profile.md"
    - "docs/adr/ADR-218-*"
supersedes: []
amends: []
depends_on: [ADR-211, ADR-213]
related: [ADR-077, ADR-138, ADR-207, ADR-209]
tags: [doc-profile, documentation, governance, lastenheft, pflichtenheft, compliance, dsfa, ozg, bsi, wibe, bitv]
---

# ADR-218 — Adopt projekttyp-spezifisches Doc-Profile mit plattform-globalem Pflicht-Katalog-Schema

## Status

**proposed** — mit pre-integriertem advocatus-diabolus-Review (Pattern aus
ADR-216/-217) und zwei externen Pässen (`/adr-challenger`, `/adr-review`,
2026-05-21). Tritt mit erster Repo-Instanziierung (meiki-hub PR #41) in
Kraft. Übergang zu `accepted` nach 30 Tagen Pilot ohne Schema-Wechsel
(analog ADR-211).

## Kontext

Die 6 Klickdummy-Repos (meiki-hub, bahn-sqf/sqf-hub, bahn-sqf/pg-hub,
ttz-hub, risk-hub, plus künftige) und Plattform-Apps brauchen Dokumentation,
deren *Pflicht-Katalog je Projekttyp variiert*:

- **LRA-Pilot** (meiki-hub) — DSGVO + BayDSG + OZG + BITV + BSI-Grundschutz
  Pflicht; EVB-IT-Vergabe oder intern offen.
- **Konzern-Pilot** (bahn-sqf) — KRITIS-Schutzbedarf, interne
  Compliance-Reviews, Investitionsrechnung Pflicht; keine OZG-Bindung.
- **Forschung** (ttz-hub) — Förderauflagen, Daten-Anonymisierung statt
  Personenbezug-DSFA; keine Vergabe.
- **Kommerzielles SaaS** (risk-hub) — ROI-Case, ISO 27001 statt BSI, ggf.
  EU-Kunden → BITV-relevant.

### Trigger für diese ADR

User-Frage 2026-05-21:

> „ich kann mir vorstellen, dass die dokumentation je nach projekt typ,
> kunde, … variiert. sollen wir das vorab festlegen oder als task parallel
> mit festlegen?"

Antwort als Entscheidung: **beides** — Profil vorab, Inhalte parallel.

## Decision Drivers

Ohne deklariertes Profil tritt ein typisches Anti-Pattern auf:

- **Compliance-Lücke nach Audit**: „BSI-Schutzbedarf fehlt" wird erst bei
  Audit-Termin gemerkt.
- **Doku-Overengineering**: alle Repos schreiben ein WiBe, auch wenn keine
  Investitionsrechnung nötig.
- **Inkonsistenz zwischen Klickdummy und Doku**: Use-Cases laufen aus der
  Spec, Spec aus der Doku.
- **Stakeholder-Frust**: „Ich kriege Pflichtenheft-Skelett, aber das passt
  nicht zu meinem Projekt."

## Considered Options

### Option A — Freihändiges Doku-Schema je Repo (Status quo)

Jedes Repo strukturiert seine `docs/` selbst, ohne Plattform-Vorgabe.

**Pros:**
- Keine Plattform-Wartung
- Maximale Repo-Autonomie

**Cons:**
- Compliance-Lücken werden erst bei Audit sichtbar (LRA-Pilot ohne BSI-Schutzbedarf, SaaS ohne ROI)
- Cross-Repo-Vergleichbarkeit unmöglich (jedes Repo erfindet eigene Tier-Namen)
- Doku-Overengineering nicht eingrenzbar
- Status quo, der explizit als Anti-Pattern identifiziert wurde

### Option B — Cookiecutter-Templates pro Projekttyp

Pro Projekttyp ein `cookiecutter-<typ>`-Repo mit fertigen Doc-Bäumen; Repo-Setup ruft Template einmalig auf.

**Pros:**
- Schneller Bootstrap (5 Min beim Repo-Onboarding)
- Klare Initial-Struktur
- Bekanntes Pattern (cookiecutter-django)

**Cons:**
- **Drift nach Repo-Lifetime**: einmaliger Template-Aufruf, danach driftet das Repo vom Template weg, ohne Erkennung
- Keine adversariale Konformitäts-Prüfung (Templates erzeugen, prüfen nicht)
- Profil-Wechsel praktisch unmöglich (Template-Re-Render würde lokale Änderungen überschreiben)
- Compliance-Tier-Pflicht ist nicht enforced — User kann Datei einfach löschen

### Option C — Backstage `catalog-info.yaml`-Erweiterung (ADR-077-Hub)

Repo-Selbstbeschreibung über das bestehende `catalog-info.yaml` (Backstage-Konvention), mit eigenen Annotations für Doku-Tiers.

**Pros:**
- Kein neues Schema-Format (reuse ADR-077)
- Backstage-Integration nativ
- TechDocs-Plugin könnte Tiers visualisieren

**Cons:**
- Backstage-spezifischer Lock-In für eine eigentlich Backstage-unabhängige Frage (Doku-Pflicht)
- Backstage-Annotations sind schwach-typisiert (`metadata.annotations: { … }`) — Schema-Validierung umständlich
- Cross-Repo-Check müsste Backstage-Catalog-API querien statt einfach `git`-Tree
- Profil-Logik (4 distinkte Pflicht-Kataloge) passt nicht zu Backstage's flachem Annotations-Modell

### Option D (gewählt) — Doc-Profile-Schema + externer Check (analog `klickdummy_registry.sh`)

Repo deklariert `docs/doc-profile.yaml` mit einem von 4 Initial-Profilen; Plattform-Schema definiert Pflicht-Tiers; externer Adversarial-Check prüft Konformität.

**Pros:**
- **Drift-sicher**: nightly + PR-Hook erkennen jede Lücke
- **Profil-Wechsel als ADR-Trigger** (Cross-Cutting, soll bewusst sein)
- **Konsistent mit existierendem Pattern** (`klickdummy_registry.sh` ADR-211 Confirmation C1)
- **Symlink-Sync zu `~/.claude/policies/`** via ADR-209 — Trigger-Words wirken in jeder Claude-Session
- **Conditional-Tiers** (z.B. „nur bei `vergabe.modus == 'evb-it'`") sind einfach evaluierbar
- **Kein neuer SaaS-Lock-In** — nur YAML + bash + Python (kein Backstage-Zwang)

**Cons:**
- Plattform-Wartungsaufwand (Schema-Edits sind zentralisiert)
- Schema-Versioning (`schema_version: 1`) ist heute deklariert aber nicht erzwungen — Migration bei v2 noch offen
- Pflicht-Inhalt (`min_inhalt`) ist im Schema definiert, vom Check aber nur als Datei-Existenz geprüft (siehe §Open Questions)

## Decision Outcome

**Gewählt: Option D — Doc-Profile-Schema + externer Check.**

Begründung: Nur Option D liefert *kontinuierliche* Konformitäts-Prüfung
(Drift-Sicherheit), passt zum etablierten `klickdummy_registry.sh`-Pattern
(ADR-211) und erzwingt keinen externen SaaS-Lock-In (vs. C). Cookiecutter
(B) ist ein Initial-Bootstrap-Tool, kein Governance-Mechanismus.

### Drei Bestandteile

1. **`platform/docs/conventions/doc-profile-schema.yaml`** — Plattform-Schema:
   - Definition von 4 Initial-Profilen (`public-admin` (vorher `lra-pilot`),
     `konzern-pilot`, `forschung`, `saas`)
   - Pro Profil: Pflicht-Tiers (A0, A, A-api, B, C, D, 08-Betrieb) ×
     Pflicht-Status (`required` / `optional` / `conditional` / `na`)
   - Pflicht-Frontmatter-Felder je Tier (z.B. `dsfa.kategorie`,
     `bsi.schutzbedarf`)
   - SSoT: Plattform; gepinnter Worktree gleicher Mechanik wie
     `klickdummy.md`-Policy

2. **Repo-lokales `<repo>/docs/doc-profile.yaml`** — Instanz:
   ```yaml
   profile: public-admin
   projektphase: discovery       # discovery | spec | build | rollout | maintain
   auftraggeber: lra
   stakeholder_extern: [guenzburg, traunstein]
   vergabe:
     modus: offen                 # intern | evb-it | offen | freihaendig
     wibe_pflicht: true
   ```
   Überschreibungen einzelner Tier-Pflichten möglich (`overrides.<tier>`)
   mit Begründung — `doc_profile_check.sh` warnt bei Override ohne `reason`.

3. **`platform/scripts/checks/doc_profile_check.sh`** — externer
   Adversarial-Check (analog `klickdummy_registry.sh`):
   - Liest `registry/repos.yaml` + `<repo>/docs/doc-profile.yaml`
   - Verifiziert je deklariertem Profil die Pflicht-Tiers existieren
   - Exit 0 = konform, 1 = Verstoß, 2 = Setup-Fehler
   - Nightly-Job + PR-Hook im jeweiligen Repo

### Vier Initial-Profile (Schema-Auszug)

| Tier / Pflicht | `public-admin` | `konzern-pilot` | `forschung` | `saas` |
|---|---|---|---|---|
| A0 Spec-Basis | ✅ | ✅ | ✅ | ✅ |
| A Use-Cases | ✅ | ✅ | ✅ | ✅ |
| A-api OpenAPI | ✅ | ✅ | ⚠ optional | ✅ |
| B Lastenheft | ✅ | ✅ | Projekt-Antrag | Product-Spec |
| B Pflichtenheft | wenn evb-it | wenn extern | – | – |
| C C4-Diagramme | ✅ | ✅ | ✅ | ✅ |
| C SLOs (RPO/RTO) | ✅ | ✅ KRITIS | ⚠ | ✅ |
| C BITV 2.0 | ✅ | wenn Endkunden-UI | ⚠ | wenn EU-Kunden |
| D DSFA | ✅ je FV | ✅ Mitarbeiter | ⚠ Anonymisierung | ✅ |
| D OZG | ✅ | – | – | – |
| D BSI-Schutzbedarf | ✅ | ✅ KRITIS | ⚠ | ISO 27001 |
| D WiBe | wenn >Schwelle | ✅ Invest. | – | ROI-Case |
| 08 Betrieb | ✅ vor GoLive | ✅ | ⚠ | ✅ |

### Profile sind erweiterbar

Neue Profile (z.B. `polit-stiftung`, `kommune-klein`, `internal-tool`,
`health-pharma`) per Plattform-PR auf das Schema. Repo-spezifische
*Abweichung* ohne neues Profil: `overrides.<tier>` mit `reason:`.

## Pros and Cons der gewählten Option D

**Pros (siehe §Considered Options Option D)** — Drift-Sicherheit,
Pattern-Konsistenz, kein SaaS-Lock-In, Conditional-Tiers, Policy-Sync.

**Cons mit Mitigation:**

| Cons | Mitigation |
|---|---|
| Plattform-Wartungsaufwand | Profile sind orthogonal zu Repos — Schema-Edits selten |
| Schema-Schein-Pflicht (Inhalt nicht geprüft) | Folge-Issue mit Akzeptanz-Kriterium (siehe §Open Questions) |
| Auto-Generator-Tooling existiert nicht | Folge-Issue (siehe §Open Questions) |
| Schema-Versioning ohne Migration-Strategie | Adressiert in ADR-218 Rev 2 (Phase-aware Check) |

## Advocatus-Diabolus-Review (pre-integriert)

| Einwand | Antwort |
|---|---|
| „Variantenexplosion: 4 Profile sind zu wenig / zu viel" | 4 ist die heute beobachtete Stakeholder-Streuung. Schema ist erweiterbar; Plattform-PR-Threshold = `klickdummy.md`-Pattern (Changelog-bump). |
| „Was, wenn ein Repo zwischen Profilen pendelt?" | `projektphase` ist orthogonal zum Profil — Phasenwechsel löst kein Profil-Wechsel aus. Profil-Wechsel nur per ADR (cross-cutting). |
| „Doppelt geschriebene Doku — Spec im Klickdummy + Use-Cases in Tier A" | Tier A0/A sind **auto-generierbar** aus Klickdummy-Spec (`gen-doc-from-spec.py`, siehe §Open Questions). Pflicht-Check prüft Existenz + Mindestinhalt. |
| „Compliance-Tiers können nicht aus Spec abgeleitet werden" | Korrekt — D ist *handgeschrieben*. Schema markiert D-Tiers als `auto_generatable: false`. |
| „Wer pflegt das Schema?" | Plattform-Ebene, gleiches Modell wie `klickdummy.md`-Policy: Symlink in gepinnten Worktree, PR-getrieben, Changelog-bump. |
| „Drift Profil-Schema vs. Repo-Instanz" | Schema-Version in `doc-profile.yaml` (`schema_version: 1`); Check prüft Kompatibilität (heute nur weicher Lese-Pfad; Rev 2: harter Cross-Check). |
| „Wann gilt es?" | Sobald `<repo>/docs/doc-profile.yaml` existiert. Repos ohne Profil sind aus dem Check ausgenommen (kein Vacuous Pass — sondern keine Pflicht). |
| „Was passiert in monorepo-artigen Repos (mehrere Projekte)?" | `doc-profile.yaml` ist mehrfach erlaubt unter `<repo>/projects/<projektname>/doc-profile.yaml`. Schema unterstützt das (`monorepo: true`). |
| „Konflikt mit klickdummy.md-Policy?" | Nein — `klickdummy.md` regelt Klickdummy-Spec-Cores, `doc-profile.yaml` regelt die *darüber-/daneben* liegenden Doku-Schichten. Beide referenzieren A0/A. |

## Konsequenzen

- ✅ **Compliance-Lücke verhindert**: Profil-Pflicht erzwingt vorab die
  rechtlich nötigen Tiers (DSFA, BSI, OZG, BITV, WiBe je nach Profil).
- ✅ **Kein Overengineering**: optional/n.a.-markierte Tiers bleiben weg.
- ✅ **Wiederverwendbar** über alle 6+ Klickdummy- und Plattform-Repos.
- ✅ **Drift-sicher**: externer Adversarial-Check `doc_profile_check.sh`
  meldet fehlende Pflicht-Artefakte (ADR-211-Pattern).
- ⚠ **Plattform-Wartungsaufwand**: Schema lebt zentral, Änderungen brauchen
  Plattform-PR. Mitigation: Profile sind orthogonal zu Repos — Schema-Edits
  selten.
- ⚠ **Bootstrap-Phase**: Repos ohne Profil bleiben aus dem Check raus
  (kein Big-Bang-Enforcement). Migration repo-by-repo.
- ⚠ **Profil-Wahl ist Entscheidung**: ein Repo, das fälschlich `forschung`
  deklariert, bekommt keine OZG-Pflicht aufgedrückt. Mitigation: Profil-Wahl
  ist im ADR-Threshold-Bereich (Profil-Wechsel = ADR-Trigger).

### Confirmation

Konformität wird wie folgt verifiziert:

1. **Nightly**: `scripts/checks/doc_profile_check.sh` läuft gegen `registry/repos.yaml`,
   meldet je Repo `OK`/`FAIL`/`skip`. Ergebnis als Plattform-Issue bei FAIL > 0.
2. **PR-Hook im Repo**: bei Änderung an `docs/doc-profile.yaml` oder
   `docs/05-spezifikation/**` wird der Check gegen das eigene Repo getriggert.
3. **Schema-Edits**: Pflichtiger Plattform-PR + Changelog-Bump im
   `docs/conventions/doc-profile-schema.yaml`. Symlink-Sync in
   `~/.claude/policies/doc-profile.md` zieht via ADR-209-Mechanismus nach.
4. **Profil-Wechsel** im Repo (`profile:`-Feld ändert sich): zukünftig
   per `--detect-profile-change`-Modus erzwingen, dass PR mit ADR-NNN-Link
   verlinkt ist (siehe §Open Questions OQ-4).

## Open Questions

| OQ | Frage | Ziel-Artefakt | Gefunden via |
|---|---|---|---|
| **OQ-1** | Wie wird `min_inhalt`-Schwelle (Heading-Count, Tabellenzeilen, Frontmatter-Flag) im Check durchgesetzt? | Plattform-Issue „doc_profile_check.sh Inhalt-Verifikation" | `/adr-challenger` Steel-Man #1 |
| **OQ-2** | Wie wird `gen-doc-from-spec.py` (Tier-A-Auto-Generator) gebaut? | Plattform-Issue „gen-doc-from-spec.py" | `/adr-challenger` Steel-Man #2 |
| **OQ-3** | Wie wird Bootstrap erzwungen (Trigger, der ein neues Repo zur Profil-Deklaration zwingt)? | ADR-218 Rev 2 §Trigger-Bedingung analog `klickdummy.md` | `/adr-challenger` Finding #3 |
| **OQ-4** | Wie wird Profil-Wechsel als ADR-Trigger enforced? | Plattform-Issue „doc_profile_check.sh --detect-profile-change" | `/adr-challenger` Finding #7 |
| **OQ-5** | Wie laufen Schema-Migrations bei Bump auf v2? | ADR-218 Rev 2 §Schema-Versioning + Kompatibilitäts-Matrix | `/adr-challenger` Finding #6 |
| **OQ-6** | Wie integriert sich Inheritance/Mixins ins Schema (~80% Pflicht-Kernel redundant)? | ADR-218 Rev 2 §_base_required-Sektion | `/adr-challenger` informativ |
| **OQ-7** | Welche Profil-Erweiterungen brauchen wir (`internal-tool`, `health-pharma`, `behoerden-zentral`, `finanz`)? | Plattform-PR mit Profil-Definitionen wenn Bedarf entsteht | `/adr-challenger` Finding #7 |

OQ-1, OQ-2, OQ-4 werden vor `proposed → accepted` als Plattform-Issues
angelegt; OQ-3, OQ-5, OQ-6, OQ-7 sind ADR-218-Rev-2-Material.

## Implementierungsplan

### Migrations-Tracking

| Phase | Repo | Profil | Status | PR | Datum |
|---|---|---|---|---|---|
| 1 — Plattform | platform | (kein Profil — definiert Schema) | 🔄 in Review | #290 | 2026-05-21 |
| 2 — Pilot | meiki-hub | `public-admin` (vorher `lra-pilot`) | 🔄 in Review | #41 | 2026-05-21 |
| 3 — Konzern | sqf-hub | `konzern-pilot` | ⬜ offen | – | – |
| 3 — Konzern | pg-hub | `konzern-pilot` | ⬜ offen | – | – |
| 4 — Forschung | ttz-hub | `forschung` | ⬜ offen | – | – |
| 5 — SaaS | risk-hub | `saas` | ⬜ offen | – | – |

Status-Lemmas: ⬜ offen · 🔄 in Review · ✅ gemerged · 🟢 nightly-konform 30d.

### Rollout-Reihenfolge

1. **Plattform-PR (diese ADR)**:
   - `docs/adr/ADR-218-doc-profile-konvention.md` (dieser File)
   - `docs/conventions/doc-profile-schema.yaml`
   - `scripts/checks/doc_profile_check.sh`
   - `policies/doc-profile.md` (für `~/.claude/policies/`-Sync via ADR-209)
2. **meiki-hub-PR (Pilot-Instanziierung)** parallel zu #1:
   - `docs/doc-profile.yaml` (profile: `public-admin`, vergabe.modus: `offen`)
   - `docs/05-spezifikation/A0/`-Skeleton (7 Dateien aus Klickdummy abgeleitet)
3. **Pilot-Reifezeit**: 30 Tage Beobachtung; bei Bedarf Schema-Patches per Folge-PR; sonst Übergang `proposed → accepted`.
4. **Rollout** nach Pilot-Stabilität: bahn-sqf/sqf-hub + pg-hub (`konzern-pilot`), ttz-hub (`forschung`), risk-hub (`saas`) — pro Repo eigener PR mit Profil-Instanz + Skeleton.
5. **INDEX.md-Sync**: separater Plattform-PR ergänzt ADR-210…218 in
   `docs/adr/INDEX.md` (heute Stand 2026-05-14, alle 21x noch nicht
   gelistet — Plattform-Backlog, nicht ADR-218-spezifisch).

## Refs

- ADR-211 Klickdummy-Rahmen (Spec-Basis Tier A0/A)
- ADR-213 Cross-Repo-ADR-Ref-Format (für Profil-Referenzen)
- ADR-207 Cross-Repo-Doku-Konvention (orthogonal)
- ADR-209 Policy-Auto-Sync (Mechanismus für `policies/doc-profile.md`)
- ADR-077 Backstage catalog-info.yaml (als Option C verworfen — siehe §Considered Options)
- ADR-138 Implementation Tracking (lifecycle der Frontmatter-Felder)
- `policies/klickdummy.md` (Schwester-Policy)

## Glossar

| Begriff | Erläuterung |
|---|---|
| **advocatus diabolus** | Vorausschauende Gegenrede zur eigenen Entscheidung — pre-integrierter Skeptiker-Standpunkt im ADR-Body. |
| **BayDSG** | Bayerisches Datenschutzgesetz — ergänzt die DSGVO um bayerische Landesregelungen. |
| **BITV 2.0** | Barrierefreie-Informationstechnik-Verordnung — Pflicht-Standard für barrierefreie IT in der öffentlichen Verwaltung Deutschlands (WCAG-Level-AA-äquivalent). |
| **BSI-Grundschutz** | Methodik des Bundesamts für Sicherheit in der Informationstechnik zur strukturierten IT-Sicherheits-Modellierung (Schutzbedarf je Datenkategorie, Maßnahmenkatalog). |
| **DSFA** | Datenschutz-Folgenabschätzung (DSGVO Art. 35) — Pflicht-Bewertung bei Verarbeitung mit hohem Risiko für personenbezogene Daten. |
| **EVB-IT** | Ergänzende Vertragsbedingungen für IT — Vergaberechts-Mustertexte (Bund/Länder) für IT-Aufträge der öffentlichen Hand. |
| **FIM** | Föderales Informationsmanagement — XÖV-Datenfeld-Standardisierung im OZG-Kontext. |
| **ISO 27001** | Internationale Norm für Informationssicherheits-Managementsysteme (ISMS) — Alternative/Ergänzung zu BSI-Grundschutz, im SaaS-Kontext üblich. |
| **KRITIS** | Kritische Infrastrukturen nach BSI-KritisV — sektorspezifische erhöhte Schutzbedarfe (Energie, Wasser, IT, Verkehr, …). |
| **MADR** | Markdown Architecture Decision Records — Format-Konvention für ADRs (siehe adr.github.io/madr). |
| **OZG** | Online-Zugangsgesetz — Bundesrecht zur Digitalisierung von Verwaltungsleistungen. |
| **smallest-viable-ADR** | ~120-Zeilen-Heuristik (🌀 Lehre aus ADR-201): ein ADR soll genau eine Entscheidung tragen, nicht mehrere. |
| **supersedes** | Frontmatter-Feld: dieses ADR ersetzt das genannte vorherige (Status des ersetzten wird `superseded`). |
| **WiBe** | Wirtschaftlichkeitsbetrachtung — Pflicht-Methodik bei IT-Vorhaben des Bundes/Länder >Schwellwert. |
| **WCAG** | Web Content Accessibility Guidelines — W3C-Standard für Barrierefreiheit, BITV-2.0-Referenz. |
| **XÖV** | XML in der öffentlichen Verwaltung — Datenaustausch-Standards zwischen Behörden. |

## Changelog

- 2026-05-21 Rev 1: Initial. Pre-integrierter advocatus-diabolus.
- 2026-05-21 Rev 2 (`amended`): Nach `/adr-challenger`- und `/adr-review`-Pässen:
  - Title als Decision-Statement
  - §Considered Options mit 4 Optionen + Pros/Cons
  - §Decision Drivers explizit
  - `### Confirmation`-Subsektion
  - §Open Questions mit 7 OQ-Items (Findings aus Challenger)
  - §Migrations-Tracking-Tabelle im Implementierungsplan
  - Glossar mit 15 Begriffen
  - `implementation_status: partial` + `implementation_evidence`
  - `scope:`-Block ergänzt
  - `related:` um ADR-077 + ADR-138 erweitert
- 2026-05-25 Rev 3 (`amended`): **Profile-Rename `lra-pilot` → `public-admin`**
  (Domain-Agnostik). Auslöser: Genesor-Tool ist nicht LRA-spezifisch, gilt
  für alle öffentlich-Verwaltung-Kontexte (Stadt/Land/Bund/EU). `lra-pilot`
  bleibt als `aliases:`-Eintrag im Schema für Bestand-Migration (Soft-
  Migrate). Migrations-Auswirkung: meiki-hub `docs/doc-profile.yaml` ändert
  `profile: lra-pilot → public-admin`. Andere Repos: bei Profil-Wahl bevorzugt
  `public-admin` (alias `lra-pilot` weiterhin gültig bis Rev 4 / Hard-
  Migration-Deadline). Schema-Erweiterung um Konzept `aliases:` für künftige
  Rename-Operationen.
