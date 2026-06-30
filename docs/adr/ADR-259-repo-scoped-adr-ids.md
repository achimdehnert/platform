---
status: proposed
date: 2026-06-30
revision: 1
decision-makers: [Achim Dehnert]
scope: platform
implementation_status: not-started
related: [ADR-138]
supersedes: []
repo: platform
---

# ADR-259: Repo-scoped ADR-IDs — `<repo>:ADR-NNN` als kanonische Cross-Repo-Referenz

> **Kurz:** ADR-Nummern sind **pro Repo** vergeben, nicht global eindeutig. Die Identität
> eines ADR ist `(repo, NNN)`; Cross-Repo-Referenzen nutzen verpflichtend `<repo>:ADR-NNN`.
> Formalisiert eine **bereits de-facto genutzte** Konvention; **keine** Umnummerierung von
> Bestandsdateien.

**Kontext:** platform (org-weit) · **Befund:** writing-hub Epic #11 / **F22** (Adversarial-Review ADR-180), dort ausdrücklich als „Folge-ADR im platform-Repo" geroutet.

---

## Kontext

Die Plattform ist ein **Polyrepo** (~40 Repos unter drei Orgs); viele Repos führen ein eigenes
`docs/adr/`. ADR-Nummern werden pro Repo monoton vergeben — und **kollidieren** damit über
Repos hinweg.

**Verifiziert 2026-06-30** (`ls docs/adr/` in beiden Repos): `platform` **und** `writing-hub`
haben jeweils ADR-180/181/182/183 mit **völlig verschiedenen** Themen:

| Nr. | platform | writing-hub |
|-----|----------|-------------|
| 180 | package-consolidation-strategy | lecture-outline-wizard |
| 181 | implementation-plan | lecture-datamodel-v2 |
| 182 | review | lecture-multi-owner-membership-authz |
| 183 | v2-concept-templates-package | lecture-revision-dag |

Allein in 180–183 also **vier** direkte Kollisionen. Eine bare „ADR-182" ist plattformweit
nicht eindeutig.

**Eine `<repo>:ADR-NNN`-Qualifizierung ist bereits de-facto in Gebrauch** — verifiziert per
`grep` über `writing-hub/docs/adr/`: u. a. **21× `writing-hub:ADR-180`**, `platform:ADR-211`,
`platform:ADR-253`, `risk-hub:ADR-046`. Sie wurde dort durch die „I4-Cross-Repo-Ref-
Qualifizierung" eingeführt (writing-hub PRs #22/#90/#96). Was fehlt, ist die **Formalisierung
+ Tooling-Durchsetzung** — nicht die Konvention selbst.

**Das Tooling modelliert das bereits:** das `iil-adrfw`-Frontmatter-Schema kennt `repo`
(„Origin repository of this ADR … null for repo-agnostic ADRs"), `scope`, `consumers`
(„Downstream repositories that … implement this ADR") und `per_repo_status`. Es gibt zudem ein
`iil_adrfw/cross_repo`-Modul (Class-1-Konfliktdetektion gegen Consumer-Repos). Die Modellierung
existiert; die **Policy** (welche Referenzform ist kanonisch, welches Feld ist Pflicht) ist nicht
festgeschrieben.

## Entscheidung (vorgeschlagen)

1. **ADR-Identität ist `(repo, NNN)`**, nicht `NNN` allein. Jedes Repo führt seinen **eigenen**
   ADR-Zähler; Nummern-Kollisionen über Repos hinweg sind **erlaubt und erwartet**. Es gibt
   **keinen** globalen Zähler.
2. **Kanonische Cross-Repo-Referenz: `<repo>:ADR-NNN`** (z. B. `writing-hub:ADR-182`). Eine
   **unqualifizierte** `ADR-NNN`-Referenz bedeutet immer „ADR-NNN **dieses** Repos".
3. **Frontmatter-Pflichtfeld `repo`:** jedes ADR trägt `repo: <origin-repo>` (vorhandenes
   iil-adrfw-Schema-Feld); repo-agnostische Plattform-ADRs `repo: platform`. Cross-Repo-Bezüge
   laufen über `consumers: [...]`, abweichende Lebenszyklen über `per_repo_status`.
4. **Tooling-Durchsetzung (iil-adrfw):** der `validate`-/`cross_repo`-Pfad
   (a) verlangt `repo` im Frontmatter und
   (b) flaggt **unqualifizierte** Referenzen, die nachweislich auf ein **fremdes** Repo zeigen.
   Rollout **gestaffelt**: zuerst `warning`, nach einer Backfill-Frist `block` — migrations-schonend.
5. **Bestandsdateien behalten ihre Nummern.** Keine Massen-Umbenennung, kein Renumbering. Die
   Kollisionen sind durch Identität `(repo, NNN)` + qualifizierte Referenzen bereits aufgelöst.

## Konsequenzen

**Positiv**
- **Keine** Renumbering-Migration über ~40 Repos × N ADRs; formalisiert nur Vorhandenes.
- Eindeutige, maschinell prüfbare Referenzen; Blast-Radius via `consumers`/Constitution-Graph.
- Repos bleiben **autonom** nummerierbar (offline, ohne plattformweite Koordination).

**Negativ / Kosten**
- Unqualifizierte Alt-Referenzen müssen schrittweise qualifiziert werden (iil-adrfw warn→block).
- `repo`-Feld-Backfill über bestehende ADRs nötig (scriptbar).

**Risiken**
- Bare „ADR-180" in Fließtext bleibt mehrdeutig, bis das Tooling greift → Mitigation: validate-
  Regel + dokumentierte Konvention; die de-facto-Praxis (21× qualifiziert) zeigt, dass es trägt.

## Erwogene & verworfene Alternativen

1. **Globaler Zähler über alle Repos** — verworfen: Serialisierungs-Engpass (jeder neue ADR
   bräuchte plattformweite Koordination, kein Offline-Nummerieren); widerspricht Polyrepo-Autonomie.
2. **Datei-Präfix `WH-ADR-180`** — verworfen: Churn auf **allen** Bestandsdateien (Umbenennung +
   Link-Bruch), während Identität `(repo, NNN)` dasselbe **ohne** Datei-Anfassen leistet.
3. **Per-Repo-Reset `writing-hub/ADR-001`** — verworfen: massive Umnummerierung bestehender ADRs,
   bricht alle Referenzen + erschwert Git-Blame/Historie.
4. **Status quo (nicht formalisieren)** — verworfen: de-facto-Konvention ohne Tooling driftet
   (unqualifizierte Refs schleichen sich ein — genau die I4-Ref-Drift, die in writing-hub
   nachgebessert werden musste).

## Implementierung (separat, nicht Teil dieses Accept)

- `iil-adrfw`: `repo` als Pflichtfeld in `validate`; Cross-Repo-Ref-Qualifizierungs-Check
  (`warning`→`block`, gestaffelt).
- Backfill `repo:`-Feld in bestehenden ADRs (Management-Script, pro Repo).
- Tracking-Issue im platform-Repo nach Accept.

## Verbindung

- **writing-hub Epic #11 / F22** — diese ADR ist die geroutete Cross-Repo-Governance-Antwort.
- **iil-adrfw** — Konsument/Durchsetzer (Schema `repo`/`scope`/`consumers`/`per_repo_status`
  existiert bereits; `cross_repo`-Modul).
- **ADR-138** (Implementation-Tracking-Standard) — gleiche ADR-Frontmatter-Governance-Linie.
