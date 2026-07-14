---
id: ADR-275
title: "Registry-SSoT-Konsolidierung — canonical.yaml als einzige Quelle, github_repos.yaml stilllegen"
status: accepted
decision_date: 2026-07-14
implemented: 2026-07-14
implementation_status: implemented
implementation_evidence:
  - "P0 Archiv-Lifecycle-View + gen_archived (additiv): PR #1137"
  - "P0.5+P1 sovereign hubs + sync-workflows.sh auf Flat-View: PR #1139"
  - "P2 runner-health.yml via registry_api: PR #1140"
  - "P3 sync-drift-meter (Kommentar-Fix; war Nicht-Consumer): PR #1142"
  - "P4 validate_repos.py auf canonical.yaml: PR #1144"
  - "P5 github_repos.yaml → registry/_ARCHIVED/ (direkter Move, s. Umsetzung): PR #1145"
  - "Hygiene (bfagent/doc-hub/ifc-mcp/schutztat-reporting): PR #1146, Issue #1143"
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: []
related: [ADR-022, ADR-157, ADR-234]
tags: [registry, ssot, drift-prevention, ci, generated, governance]
external_sparring_by: "ollama-local: dolphin3 + qwen2.5:7b @2026-07-14"   # lokale 7B-Klasse, kein Egress; Befunde AD-1/AD-4 dennoch repo-verifiziert
drift_check_paths:
  - "registry/canonical.yaml"
  - "registry/_ARCHIVED/github_repos.yaml"
  - "registry/repos.yaml"
---

# ADR-275 — Registry-SSoT-Konsolidierung

## Context and Problem Statement

Die Plattform pflegt **zwei** Repo-Registries, die beide von sich behaupten, die
„Single Source of Truth" zu sein, und **beide von aktiver CI live gelesen werden**:

| Datei | Selbstanspruch (Header) | Realität | Schutz |
|---|---|---|---|
| `registry/canonical.yaml` → `registry/repos.yaml` (View) | „Kanonische Quelle" (ADR-234 P0) | generiert, zuletzt 2026-07-10; 53 aktive Repos, reiches Schema | **CI-Drift-Gate** `registry-consistency.yml`; View-Reader-Guard (ADR-234 §11.1) |
| `registry/github_repos.yaml` | „Single Source of Truth für Cascade, port_audit, onboard-repo, deploy-check" | **manuell** gepflegt, Snapshot **2026-04-03** (86 Repos), zuletzt berührt 2026-06-29; 113 Einträge inkl. 68 Archive | **kein** Gate — nur ein `runner-health`-Kommentar „manually maintained" |

Das ist kein historisches Relikt: `github_repos.yaml` wird nachweislich von **vier
aktiven Konsumenten** gelesen (per `grep` verifiziert, 2026-07-14):

1. `scripts/sync-workflows.sh` — liest die Sektions-Keys `django_apps` +
   `org_django_apps` → `DJANGO_HUBS`, `frameworks` → `PACKAGES` (Repo-Typ-Klassifikation
   für die Workflow-Symlink-Verteilung).
2. `.github/workflows/runner-health.yml` — iteriert `django_apps` + `org_django_apps`
   mit `deployed==true` + `github`-Feld (Runner-Health-Abgleich).
3. `.github/workflows/sync-drift-meter.yml` — erwartet die Datei unter
   `$GITHUB_DIR/platform/registry/github_repos.yaml` (Fleet-Drift-Melder).
4. `infra/scripts/validate_repos.py` — Cross-Check GitHub ↔ `github_repos.yaml` ↔
   `ports.yaml`.

**Kernbefund:** Manche Workflows entscheiden gegen die frische, gegatete Quelle,
andere gegen einen 3,5 Monate alten, ungeschützten Snapshot. Ein April-Snapshot
kennt z. B. `dms-hub` nicht (erst später onboarded) und führt dekommissionierte
Repos (`bfagent`, seit 2026-06-03) evtl. noch als aktiv. **Stille Fehlfunktion durch
Datenalter ist der eigentliche Schaden, nicht die Existenz zweier Dateien.**

Dieser Konflikt ist wiederholt als „bekannt" notiert worden (KONZ-platform-015
Befund; AGENT_HANDOVER), aber nie aufgelöst — dasselbe „bekannt, nicht befolgt"-Muster
wie beim Port-Duplikat (Issue #1033, real getroffen 2026-07-14).

## Decision Drivers

1. **Genau eine SSoT** — prüfbar, gegen die neue Consumer validieren, kein zweiter
   Anspruch.
2. **Kein stiller Datenzerfall** — die maßgebliche Quelle muss ein CI-Gate haben
   (wie `canonical.yaml` bereits), nicht auf manuelle Disziplin bauen.
3. **Reversibel & inkrementell** — kein Big-Bang; jeder der 4 Consumer muss einzeln,
   verifizierbar migrierbar sein, sonst bleibt ein Consumer auf einer toten Quelle.
4. **Coverage-Ehrlichkeit** — `github_repos.yaml` trägt Dinge, die `canonical.yaml`
   heute **nicht** hat (s. u.). Diese Lücken müssen VOR der Stilllegung geschlossen
   werden, nicht danach.

## Coverage-Delta (verifiziert 2026-07-14, nicht geschätzt)

`canonical.yaml` (53 Repos) deckt die aktiven Felder ab, die die Consumer brauchen —
je Repo `github` (owner/repo), `deployed`, `type`, plus `deploy`/`staging`-Blöcke.
Typverteilung: django 23, library 22, infra 2, fastapi/static/bot/python/other je 1–2.

**Was `github_repos.yaml` UNIQUE trägt und vor der Stilllegung migriert werden muss:**

| Lücke | Umfang | Betroffener Consumer |
|---|---|---|
| **68 Archive-Repos** | `canonical.yaml` schließt Archiv bewusst aus | `validate_repos.py` (Cross-Check gegen GitHub-Vollinventar) |
| **`django-lms-lite`** | 1 aktives Framework, in canonical **gar nicht** vorhanden | coach-hub-Dep (bereits als CI-Auth-Problem separat bekannt) |
| **Sektions-Gruppierung** (`django_apps`/`frameworks`/…) | canonical nutzt flaches `repos{}`-Dict + `type`-Feld statt Sektionen | `sync-workflows.sh`, `runner-health.yml` extrahieren nach Sektion, nicht nach `type` |

Die Sektions-Gruppierung ist rein mechanisch aus `type` ableitbar
(`type==django → django_apps`, `type∈{library,framework} → frameworks`), aber der
Ableitungscode existiert noch nicht.

## Considered Options

### Option A — canonical.yaml als alleinige SSoT, github_repos.yaml stilllegen (empfohlen)

Die 4 Consumer werden einzeln auf `canonical.yaml` (bzw. die generierte `repos.yaml`-View)
umgestellt; `github_repos.yaml` wird nach vollständiger Consumer-Migration nach
`registry/_archived/` verschoben. Coverage-Lücken (Archive-Liste, `django-lms-lite`)
werden vorher in `canonical.yaml` bzw. eine dedizierte `archived-repos.yaml` überführt.

- **Pro:** Ein Anspruch, ein Gate. Datenalter strukturell unmöglich (generiert).
- **Contra:** 4 Consumer-Migrationen + Lückenschluss; nicht trivial.

### Option B — github_repos.yaml aus canonical.yaml generieren (Zwei-Dateien, ein Ursprung)

`github_repos.yaml` bleibt als generierte View bestehen, wird aber aus `canonical.yaml`
erzeugt (wie `repos.yaml` heute), mit MANAGED-Header + Drift-Gate. Consumer bleiben
unverändert.

- **Pro:** Null Consumer-Änderung; kleinster Diff.
- **Contra:** Zementiert zwei Schema-Formate dauerhaft; der Generator muss die
  Sektions-Gruppierung + Archive-Liste + `django-lms-lite` mitführen — d. h. dieselben
  Lücken müssen ohnehin geschlossen werden, nur landen sie in einem Generator statt in
  einer Migration. Verlängert die „zwei SSoT sehen"-Verwirrung optisch.

### Option C — Status quo + Waiver (verworfen)

Nichts tun, Konflikt dokumentieren. Verworfen: genau das ist seit 2026-04 passiert,
der Snapshot altert weiter, `runner-health`/`sync-workflows` treffen zunehmend falsche
Entscheidungen.

## Decision Outcome

**Gewählt: Option A**, in reversiblen Phasen, jede mit eigenem verifizierbaren Gate.
Begründung gegen B als *Endzustand*: B behält dauerhaft zwei Schemata — das widerspricht
Driver 1. **Aber** (externes Sparring AD/OOB-1): B ist als *zeitlich befristeter
Migrations-Adapter* wertvoll und wird übernommen — s. „Kompatibilitäts-View" unten. Der
Endzustand bleibt A (eine Quelle), der Übergang nutzt eine generierte Wegwerf-View.

### Vorab-Klärungen (aus externem Sparring, VOR den Phasen zu entscheiden)

Zwei Punkte, die das externe Review zu Recht als „im ADR entscheiden, nicht im PR
verstecken" markiert hat (AD-2, AD-4, M28-1):

1. **Consumer-Vertrag = die generierte View `repos.yaml`, NICHT `canonical.yaml`
   direkt.** `canonical.yaml` bleibt reine Authoring-/Generator-/Validierungs-Quelle.
   **Achtung Kollision (verifiziert):** ADR-234 §11.1 führt eine eingefrorene Baseline
   „legitimer Direct-Reader" der Views (aktuell 21) und failt bei neuen. Die 4
   migrierten Consumer werden daher **explizit in diese Baseline aufgenommen** (mit
   Begründung je Reader), nicht als Verstoß — oder, falls REC-4/OOB-2 gewählt wird,
   hinter eine gemeinsame Query-Funktion gelegt, die selbst der einzige neue Reader ist.
   Ohne diese Klärung reißt die Consumer-Migration ein bestehendes Gate.
2. **Archiv-Modell = `lifecycle: archived` in `canonical.yaml`** mit einer gefilterten
   View `archived-repos.yaml` (generiert, kein zweiter Authoring-Ort). Damit ist auch
   der Zukunfts-Lifecycle eindeutig (M28-1): Archivieren = Feld-Flip, nicht Datei-Umzug.

### Phasen (jede ein eigener PR, jede einzeln reversibel)

- **P0 — Datenmodell + Import + Reconciliation (rein additiv, keine Consumer-Migration) —
  UMGESETZT 2026-07-14:** (a) `lifecycle`-Feld genutzt (existierte bereits im Schema) +
  neue gefilterte View `archived-repos.yaml` (Generator `gen_archived`, ins `verify`-Gate
  verdrahtet); (b) `build`-Landmine gehärtet (rekonstruiert-aus-Views hätte canonical-only-
  Archive gedroppt).
  **Reconciliation-Realbefund (AD-8 bestätigt sich drastisch):** die „68 Archive" aus
  `github_repos.yaml` waren zu **96 % Fiktion** — GitHub-live-verifiziert (2026-07-14):
  **0** real archiviert, **65** gelöscht/nicht existent, **3** in Wahrheit *aktiv*
  (fehlklassifiziert: `ifc-mcp`, `lastwar-bot`, `schutztat-reporting`). Die **3 real
  GitHub-archivierten** Repos (`adr-doctor`, `bfagent`, `testkit`) standen *gar nicht* in
  der Liste. P0 importiert daher **nicht 68, sondern die 3 echten** (via Live-GitHub, nicht
  Snapshot); die 65 Phantome werden mit `github_repos.yaml` in P5 entsorgt.
  **NICHT in P0 (weil nicht additiv-neutral — würden in aktive Views lecken):**
  `django-lms-lite` (aktive Library → Package-View von `sync-workflows`) und die 3
  fehlklassifiziert-aktiven Repos wandern in die jeweilige Consumer-Phase, wo ihr Delta
  reviewt wird; `bfagent`s Fehl-Flag `in_rich:true` (archiviert, projiziert aber in die
  Deploy-View) ist eine view-berührende Alt-Wart und ebenfalls einer Consumer-Phase
  vorbehalten. **Gate erfüllt:** die zwei aktiven Views (`repos.yaml`,
  `repo-registry.yaml`) sind **byte-identisch** vor/nach (md5 geprüft), nur die neue
  Archiv-View kam hinzu; `registry-canonical.py verify` grün auf allen drei.
- **P1–P4 — je ein Consumer auf `repos.yaml` umstellen** (`sync-workflows.sh`,
  `runner-health.yml`, `sync-drift-meter.yml`, `validate_repos.py`), jeder in die
  Reader-Baseline aufgenommen. **Identitäts-Gate als Drei-Teil-Vertrag (AD-1, REC-1) —
  NICHT „Ausgabe unverändert":** (i) für die Schnittmenge *unveränderter* Datensätze
  vorher==nachher; (ii) eine explizit reviewte **Soll-Delta-Liste** der bekannten
  Korrekturen (z. B. `dms-hub` erscheint neu, `bfagent` verschwindet — genau das ist
  der Zweck der Migration weg von der stalen Quelle); (iii) Fehler bei *jeder* nicht
  genehmigten Zusatz-Abweichung. Ein „identisch"-Gate allein würde die notwendige
  Korrektur blockieren.
- **P5 — Stilllegung + Rollback-Fenster (M28-2, REC-8):** `github_repos.yaml` wird
  NICHT sofort entfernt, sondern für ein definiertes Rollback-Fenster als **generierte,
  schreibgeschützte Kompatibilitäts-View** (aus `canonical.yaml`, `DEPRECATED`-Header,
  hartes Löschkriterium/Datum) am alten Pfad gehalten. So bleibt jeder P1–P4-PR bis
  Fensterende einzeln rollback-fähig (findet seine alte Eingabe noch). Erst nach
  Fensterende → `registry/_archived/`, Header-Selbstanspruch gelöscht.

**Enforcement + dessen Grenzen (Driver 2; M28-4, AD-6):** Ein `grep`-Guard in
`check_registry_view_readers.py` failt, sobald ein Nicht-archivierter Pfad
`github_repos.yaml` wieder direkt liest. **Ehrliche Grenze:** `grep` fängt weder
dynamisch zusammengesetzte Pfade noch Leser in *anderen* Repos/externen Automationen
und kann bei Doku/Fixtures falsch-positiv sein — er ist Defense-in-Depth, kein Beweis.
Daher **vor P5 zwingend** eine org-weite Code-Suche (`gh search code`, alle Repos) +
ausführbare Dry-Runs aller Consumer, nicht nur der platform-lokale `grep`.

## Umsetzung — abgeschlossen 2026-07-14

Alle Phasen gemergt auf `main`; Endzustand verifiziert (`github_repos.yaml` nur noch
in `registry/_ARCHIVED/`, reader-guard grün, `registry-canonical.py verify` grün).

| Phase | Consumer / Inhalt | PR |
|---|---|---|
| P0 | Archiv-Lifecycle-View + `gen_archived` (additiv) | #1137 |
| P0.5+P1 | sovereign hubs (meiki/ttz) + `sync-workflows.sh` → Flat-View | #1139 |
| P2 | `runner-health.yml` → `registry_api` | #1140 |
| P3 | `sync-drift-meter.yml` Kommentar-Fix | #1142 |
| P4 | `validate_repos.py` → `canonical.yaml` | #1144 |
| P5 | `github_repos.yaml` → `registry/_ARCHIVED/` | #1145 |
| Hygiene | `bfagent`/`doc-hub`/`ifc-mcp`/`schutztat-reporting` (#1143) | #1146 |

### Abweichungen vom Plan (ehrlich dokumentiert, nicht geglättet)

- **P3 war kein echter Consumer.** Die Phasen-Liste zählte `sync-drift-meter.yml` als
  github_repos.yaml-Leser. Real liest es **keine** Registry: es ruft `list_megatest_repos.py`
  (liest die Flat-View) und `sync_drift_meter.py` auf, das `sync-workflows.sh --dry-run`
  invokt (in P1 bereits migriert). Der einzige github_repos-Bezug war ein seit P1 falscher
  **Kommentar** → P3 wurde ein reiner Doku-Fix, keine Logik-Migration.
- **P5 ohne Rollback-Fenster-View umgesetzt.** Der Plan (oben) sah `github_repos.yaml` als
  temporäre generierte Kompatibilitäts-View am alten Pfad vor, erst danach `→ _archived`.
  Umgesetzt wurde stattdessen ein **direkter** `git mv` nach `registry/_ARCHIVED/` mit
  RETIRED-Banner. **Begründung:** Zweck des Fensters war, dass P1–P4-Consumer ihre alte
  Eingabe noch finden — doch bei P5-Ausführung waren alle vier bereits gemergt **und** grün
  verifiziert (kein Consumer liest github_repos.yaml mehr, org-weite `gh search code` leer).
  Der Fenster-Zweck war damit gegenstandslos; Rollback bleibt über git-Historie + `_ARCHIVED/`
  möglich. Der reader-guard-Archiv-Skip wurde dabei auf verschachtelte `_ARCHIVED/`
  verallgemeinert (Archiv ≠ aktiver Reader).
- **Reader-Baseline nur für P1.** Die Phasen-Notiz sagte „jeder [Consumer] in die
  Reader-Baseline aufgenommen". Tatsächlich brauchten nur `sync-workflows.sh` + sein Test
  (P1) einen Baseline-Eintrag; P2/P4 lesen über `registry_api` (Accessor-exempt), P3 ist
  Kommentar — kein Baseline-Eintrag nötig/erfolgt.

### Getrackte Rest-/Folgearbeit

- `validate_repos --github` meldet noch 3 vorbestehende, un-katalogisierte Repos
  (`design-hub`, `iil-demo-fixture`, `molkerei-landing`) — dokumentiert in #1143 als
  „kein neuer Gap", außerhalb dieses ADR-Scopes.
- `ifc-mcp`/`schutztat-reporting` sind additiv-neutral (`in_flat:false`/`in_rich:false`)
  aufgenommen — Promotion in die rich-View (Domain-Zuordnung) optional, später.

## Consequences

**Positiv:** Eine autoritative Repository-Registry **für die hier behandelten Felder**
(Repo-Identität, Typ, Deploy/Staging, Lifecycle) — bewusst enger formuliert als „genau
eine SSoT" (M28-5): die ADR-022-§2.9-Port-Teilkopie besteht bis zu ihrem Folge-PR fort,
die Aussage wäre sonst irreführend. Die 4 Consumer treffen fortan Entscheidungen gegen
die generierte, aktuelle View.

**Wichtige Präzisierung (AD-3, verifiziert):** „generiert + driftgeprüft" ≠ „fachlich
aktuell". Das bestehende `registry-consistency`-Gate beweist nur **View == canonical**
(Quelle↔Ableitung), NICHT die Übereinstimmung mit dem realen GitHub-Bestand. Diese
zweite Garantie liefert erst der separate Reconciliation-Check (`reconcile_registry_live.py`
für Ports/Container/DNS; für Repo-/Archiv-Existenz in P0 neu ergänzt). Der ADR behandelt
beide als getrennte Garantien; „canonical ist SSoT" heißt „einzige *Autoring*-Wahrheit",
nicht „automatisch deckungsgleich mit GitHub".

**Offen als benannter Folge-Schritt (M28-3, OOB-2):** Vier direkte YAML-Leser können ihre
Filter-/Typ-/Lifecycle-Semantik langfristig erneut auseinanderentwickeln. Eine gemeinsame
Query-Schicht (`registry query --type django --deployed` bzw. importierbare Funktion)
kapselt den Consumer-Vertrag an einer Stelle — hier bewusst NICHT Teil der
Konsolidierung (YAGNI bei 4 Consumern), aber als Kipp-Punkt vermerkt: ab dem 5. Consumer
oder erneuter Filter-Drift wird sie fällig.

**Negativ / Risiko:** 6 PRs statt 1; jeder Consumer-PR braucht einen echten Vorher/Nachher-
Diff-Beleg (nicht nur „CI grün"). Falls ein Consumer eine `github_repos.yaml`-Eigenheit
nutzt, die hier übersehen wurde, bricht dessen Migration — deshalb je Phase ein
Identitäts-Gate statt eines Aggregat-Checks.

**Nicht verifiziert / offene Restlücke:** Ob `sync-drift-meter.yml` und `validate_repos.py`
über die hier belegten Feld-Zugriffe hinaus weitere `github_repos.yaml`-Felder lesen, ist
nur per `grep` geprüft, nicht per Ausführung beider Tools im Vorher/Nachher — der billigste
weitere Check ist ein Dry-Run beider Tools in P3/P4 (dort als Gate verankert).

## Abgrenzung

Dieses ADR betrifft **nur** die Registry-Doppelquelle. Die ADR-021-§2.9-Port-Tabelle ist
eine **dritte**, manuell gepflegte Teilkopie derselben Daten (Ports), schon jetzt
unvollständig (~24 vs. 53 Einträge) — sie ist ein verwandter, aber separater SSoT-Drift
und wird hier bewusst nicht mitbehandelt (eigener, kleinerer Folge-PR: Tabelle durch einen
Generator-Verweis auf `ports.yaml` ersetzen).

## Externes Sparring (2026-07-14)

Zwei adversariale Zweitmeinungen aus **lokalen Ollama-Modellen** (`dolphin3`,
`qwen2.5:7b`) — anbieter-fremd zu Claude, aber 7B-Klasse und lokal (kein Egress,
souveränitäts-sicher). **Wichtige Einordnung:** Ein 7B-Modell ist kein Frontier-Reviewer;
seine Befunde tragen nicht per se Autorität. Der Wert entstand hier durch den
**Verifikations-Filter**: die zwei tragendsten Befunde (AD-3, AD-4) wurden vor Übernahme
gegen das reale Repo geprüft und bestätigten sich (Reader-Guard-Baseline, Drift-Gate-Scope)
— eingearbeitet wurde also nicht „weil ein Modell es sagte", sondern weil der Check hielt.
Rückfluss kuratiert: jede Befund-/REC-ID getaggt, nur `[valid]`. Review 2 lag nur teilweise
vor (Paste abgeschnitten nach PRO-2); dessen Steelman konvergiert mit Review 1.

| ID | Verdikt | Aktion |
|---|---|---|
| PRO-1…PRO-5 | valid | Zustimmung, keine Änderung nötig (Steelman/Proponent-Seite) |
| AD-1 / REC-1 | **valid (verifiziert-logisch)** | Identitäts-Gate von „Ausgabe unverändert" auf **Drei-Teil-Vertrag** umgestellt (P1–P4) — der zentrale Fix |
| AD-2 / REC-2, M28-1 | valid | Archiv-Modell im ADR entschieden: `lifecycle: archived` in canonical + gefilterte View |
| AD-3 / REC-3 | **valid (repo-verifiziert)** | Consequences trennt jetzt „View==canonical"-Gate von GitHub-Reconciliation |
| AD-4 / REC-4 | **valid (repo-verifiziert)** | Consumer-Vertrag = `repos.yaml`-View; Reader-Baseline-Kollision (ADR-234 §11.1) explizit adressiert |
| AD-5 / REC-5 | valid | P0/P4-Ordering bereinigt: P0 rein additiv, validate_repos.py vollständig in einer Phase |
| AD-6 / REC-6, M28-4 | valid | grep-Guard-Grenzen benannt; org-weite Code-Suche + Dry-Runs vor P5 verpflichtend |
| AD-7 / REC-7 | valid | Typ→Sektion als totale Abbildung (inkl. `org_django_apps`, unbekannte Typen, Golden-Test) — als P1-Anforderung |
| AD-8 / REC-3 | **valid (repo-verifiziert)** | Archive gegen aktuelles GitHub reconciliiert statt Snapshot blind kopiert |
| AD-9 / REC-9 | valid | Voll-Diff aller Views + Consumer-Ausgaben als P0-Gate |
| M28-2 / REC-8 | valid | P5 hält alte Datei als generierte Read-only-Kompat-View über ein Rollback-Fenster |
| M28-3 / OOB-2 | valid (Scope: Folge-Schritt) | Als benannter Kipp-Punkt in Consequences, nicht als Blocker dieser Konsolidierung |
| M28-5 / REC-10 | valid | „genau eine SSoT" → „eine autoritative Registry für die hier behandelten Felder" |
| OOB-1 | **valid (übernommen)** | B als *befristeter* Migrations-Adapter (Kompat-View), Endzustand bleibt A |
| OOB-3 | valid-Kern | GitHub als Reconciliation-Quelle (= AD-8/REC-3), NICHT als Archiv-Speicherort (Reviewer selbst verworfen) |

Kein Befund als `[missversteht-Kontext]` oder `[out-of-scope]` — das Review respektierte
die gesetzten Grenzen (kein Versuch, `github_repos.yaml` als SSoT wiederzubeleben).
Hohe Valid-Quote ist hier ehrlicher Befund, kein Gummistempel: ADR-275 war ein
`proposed`-Entwurf mit bewusst offenen Punkten, die das Review kompetent getroffen hat.
