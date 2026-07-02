---
status: accepted
date: 2026-06-30
revision: 2
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

> **Rev 2 (2026-06-30) — externe Zweitmeinung eingearbeitet** (`/adr-handoff-extern`; Rückfluss-Tagging s. `~/shared/adr-handoff-ADR-259-2026-06-30-RUECKFLUSS.md`). Der Review bestätigte die Kern-Richtung („härten, nicht ersetzen") und schloss operative Lücken: Slug-Namespace/Eindeutigkeit, Frontmatter-vs-Kontext-SSoT, messbare `block`-Kriterien, Detection-Index, origin-vs-scope-Schärfe. Kern (Identität `(repo, NNN)`, keine Umnummerierung) unverändert.

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
2. **Kanonische Cross-Repo-Referenz: `<repo>:ADR-NNN`** (z. B. `writing-hub:ADR-182`).
   Unqualifiziertes `ADR-NNN` = „dieses Repo" — **aber nur außerhalb der Kollisionsmenge**
   (Rev 2, R2-REC-1, behebt den Kern-Blind-Spot): `iil-adrfw cross_repo` sieht den
   repo-übergreifenden Bestand und berechnet die Menge der über **≥2 Repos kollidierenden**
   Nummern (z. B. 180–183). **Für jede kollidierende Nummer ist die bare/unqualifizierte
   Schreibweise überall verboten — auch lokal** (Qualifizierung erzwungen). Sonst bände eine
   bare „ADR-182" still lokal, obwohl ein Fremd-Repo gemeint sein kann — genau im Bereich, der
   diesen ADR motiviert. Außerhalb der Kollisionsmenge bleibt „unqualifiziert = lokal" gültig.
3. **Frontmatter-Pflichtfeld `repo` = Origin, auto-abgeleitet** (Rev 2, R2-REC-4/R2-REC-5):
   `iil-adrfw` setzt `repo` bei `adr new`/`create` **aus dem Pfad** (= flacher `~/github/<repo>`-
   Name, s. „Repo-Slug-Namespace") **kanonisch** ins Frontmatter; danach prüft `validate` nur
   noch **Pfad-vs-Frontmatter-Konsistenz** (Mismatch = `warning`, fängt verschobene/umbenannte
   Dateien). So ist Backfill ein **einmaliger Skriptlauf**, laufende Autorenkosten = 0, das Feld
   bleibt Pflicht (Portabilität: überlebt Copy in PRs/Wikis/Vendoring — was pfad-abgeleitet nicht
   kann). **Feldsemantik scharf, eine Bedeutung je Feld:** `repo` = **Origin** (wo verfasst);
   **Geltungsbereich** über das bestehende `scope` (`platform`/org-wide vs. `repo`); echt
   repo-agnostische ADRs tragen `repo: null`. `repo: platform` heißt „im platform-Repo verfasst",
   **nicht** „gilt nur für platform". Cross-Repo-Bezüge über `consumers`, Zustände über `per_repo_status`.
4. **Tooling-Durchsetzung (iil-adrfw `validate`/`cross_repo`):**
   (a) `repo`-Pflicht + Pfad-Konsistenz (aus 3);
   (b) bare Nutzung einer **kollidierenden** Nummer verboten (aus 2);
   (c) im Fließtext auftauchende Cross-Repo-Refs werden gegen `consumers` **kreuzgeprüft**
   (R2-REC-6, `warning`) — hält strukturierten Blast-Radius-Graph und Prosa synchron.
   **Voraussetzung:** `cross_repo` kennt den repo-übergreifenden Bestand (Index); **offline ohne
   Index** → nur lokale Existenzprüfung möglich (degradiert, `warning`). Rollout s. „Rollout".
5. **Bestandsdateien behalten ihre Nummern.** Keine Massen-Umbenennung, kein Renumbering. Die
   Kollisionen sind durch Identität `(repo, NNN)` + erzwungene Qualifizierung (2) aufgelöst.

## Repo-Slug-Namespace (Rev 2, R1-REC-1)

Der Slug in `<repo>:ADR-NNN` ist der **flache `~/github/<repo>`-Verzeichnisname**. Die Plattform
legt **alle** Repos der drei Orgs (achimdehnert, ttz-lif, meiki-lra) **flach** unter einem
`GITHUB_DIR` ab → **Slug-Eindeutigkeit gilt per Layout-Invariante** (zwei Repos können denselben
Namen nicht teilen, auch nicht über Orgs). Damit ist `<repo>` ein eindeutiger Schlüssel, ohne dass
der Org-Name in die Referenz muss.

- **Rename/Org-Umzug** = seltenes **Governance-Event**: der alte Slug wird im umbenannten Repo als
  `aliases: [alt-slug]`-Frontmatter (bzw. ein Redirect-Eintrag) geführt, ein einmaliger Ref-Sweep
  qualifiziert Altlinks nach. (Eine **zentrale Slug-Registry** in `platform` ist die Eskalation,
  falls Renames häufig werden — bewusst **nicht** Teil dieser Stufe.)
- **Archivierte Repos** behalten ihren Slug (Nummern werden nie wiederverwendet, ADR-065-Linie).

## Konsequenzen

**Positiv**
- **Keine** Renumbering-Migration über ~40 Repos × N ADRs; formalisiert nur Vorhandenes.
- Eindeutige, maschinell prüfbare Referenzen; Blast-Radius via `consumers`/Constitution-Graph.
- Repos bleiben **autonom** nummerierbar (offline, ohne plattformweite Koordination).

**Negativ / Kosten**
- Unqualifizierte Alt-Referenzen müssen schrittweise qualifiziert werden (iil-adrfw warn→block).
- `repo`-Feld-Backfill über bestehende ADRs nötig (scriptbar).

**Risiken**
- Bare „ADR-180" in **Nicht-Datei-Kontexten** (Tickets, Commits, Chat, Volltextsuche) bleibt
  mehrdeutig — `iil-adrfw` erreicht diese Texte nicht (R2-AD-2). Das wird **nicht** als gelöst
  verkauft (s. „Scope / Nicht-Scope"); für ADR-Dateien selbst behebt die Kollisionsmengen-Regel
  (Entscheidung 2) den Kern.

## Scope / Nicht-Scope (Rev 2, R2-REC-7)

**Durchsetzung ist datei-skopiert** (ADR-Markdown + iil-adrfw). **Bare `ADR-NNN` in Commits,
Issues, PR-Beschreibungen, Chat** liegen **außerhalb** der erzwingbaren Reichweite — das wird hier
ehrlich abgegrenzt, nicht überclaimt. Adressiert als **nicht-blockierende Folge-Arbeit**:
CONTRIBUTING-/Commit-Template-Hinweis „Cross-Repo-ADR-Refs qualifizieren" + optionaler
PR-Titel/Commit-Linter (CI auf PR-Metadaten) für Cross-Repo-PRs.

## Rollout (Rev 2, R2-REC-3 — zwei Regeln getrennt gaten)

Statt eines `warn→block`-Schalters über alles: **pro Regel eigenes, abschließbares Gate + Metrik.**

| Regel | `block`-Kriterium (Owner: Achim) | Skopierung |
|---|---|---|
| `repo`-Pflicht + Pfad-Konsistenz | **0 fehlende `repo`** über alle Repos (Backfill = 100 %) — abschließbares Ereignis | ganzes Repo |
| Kollidierende bare Nummer / unqualifizierte Fremd-Ref | **0 neue** Verstöße in PRs über N aufeinanderfolgende Merges; **Bestand bleibt dauerhaft `warning`** | **nur PR-Diff / geänderte Zeilen** |

So endet die Warnphase nicht offen (M28-3 „Fire-Drill"): Regel 1 hat ein klares Abschluss-Event,
Regel 2 blockt nur Neuzugang (False-Positive-Risiko auf Altbestand vermieden). Cutover-Zieldatum
**2026-09-30**; PR-Bot mit Autokorrektur-Vorschlag als Rollout-Hilfe vor `block`.

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
5. **Immutabler Maschinenschlüssel `uid: <repo>/ADR-NNN`** (Rev 2, R2-REC-2/OOB-1) — *erwogen,
   vertagt:* ein eigenes immutables Feld, auf das Graph/Blast-Radius + externe Integrationen
   **joinen** (statt `<repo>:ADR-NNN` aus Prosa zu parsen) — schließt den AD-1/M28-1-Blind-Spot
   für Maschinen *strukturell*. **Nicht jetzt verpflichtend** (zusätzliches Feld + Backfill gegen
   „minimale Migration"); für die ADR-Datei-Ebene löst die Kollisionsmengen-Regel (Entscheidung 2)
   das Problem bereits. Re-Eval, falls externe Systeme (Jira/Commit-Linter/LLM-Index) auf einen
   stabilen Schlüssel joinen müssen.
6. **Slug-Identität statt Nummern** (`writing-hub/lecture-wizard`) — verworfen: global
   bedeutungstragend, aber bricht den **gesamten nummerierten Bestand** + die No-Renumbering-
   Kernprämisse; Menschen referenzieren lieber kurze Nummern.
7. **Kauf statt Bau** (Log4brains/adr-tools mit Namespacing) — verworfen: verwirft die bestehende
   `iil-adrfw`-Investition (Constitution-Graph, hauseigenes Schema/`per_repo_status`) und
   widerspricht dem gesetzten Constraint „iil-adrfw ist Durchsetzer".

## Implementierung (separat, nicht Teil dieses Accept)

- `iil-adrfw`: `repo` bei `adr new`/`create` **aus Pfad auto-setzen**; `validate` prüft
  Pfad-vs-Frontmatter-Konsistenz; **Kollisionsmengen-Check** (`cross_repo`) + Prosa-↔-`consumers`-
  Kreuzcheck; zwei getrennt gegatete Rollout-Regeln (s. „Rollout").
- **Einmaliger** `repo`-Backfill-Skriptlauf (pro Repo, aus Pfad) — danach Autorenkost 0.
- Optionaler PR-Bot (Autokorrektur-Vorschlag) als Rollout-Hilfe.
- Tracking-Issue im platform-Repo nach Accept.

## Verbindung

- **writing-hub Epic #11 / F22** — diese ADR ist die geroutete Cross-Repo-Governance-Antwort.
- **iil-adrfw** — Konsument/Durchsetzer (Schema `repo`/`scope`/`consumers`/`per_repo_status`
  existiert bereits; `cross_repo`-Modul).
- **ADR-138** (Implementation-Tracking-Standard) — gleiche ADR-Frontmatter-Governance-Linie.
