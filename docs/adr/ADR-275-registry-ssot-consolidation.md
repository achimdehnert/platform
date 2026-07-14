---
id: ADR-275
title: "Registry-SSoT-Konsolidierung — canonical.yaml als einzige Quelle, github_repos.yaml stilllegen"
status: proposed
decision_date: 2026-07-14
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: []
related: [ADR-022, ADR-157, ADR-234]
tags: [registry, ssot, drift-prevention, ci, generated, governance]
external_sparring_by: "2×extern@2026-07-14"   # 2 anbieter-fremde Reviews; Provider-Namen vom Autor zu bestätigen
drift_check_paths:
  - "registry/canonical.yaml"
  - "registry/github_repos.yaml"
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

- **P0 — Datenmodell + Import + Reconciliation (rein additiv, keine Consumer-Migration):**
  (a) `lifecycle`-Feld in `canonical.yaml`-Schema + gefilterte View `archived-repos.yaml`;
  (b) `django-lms-lite` aufnehmen; (c) **68 Archive NICHT blind aus dem 2026-04-Snapshot
  übernehmen** (AD-8) — beim Import gegen das aktuelle GitHub-Inventar reconciliieren
  (existiert das Repo noch? archiviert-Status stimmt?), Abweichungen als Soll-Delta
  gelistet. **Gate:** ein voller Diff *aller* aus `canonical.yaml` generierten Views +
  bestehenden Consumer-Ausgaben (AD-9) zeigt außer dem reviewten Soll-Delta keine
  Änderung; `registry-canonical.py verify` grün.
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

Zwei anbieter-fremde Zweitmeinungen (adversariales Review, `/adr-handoff-extern`).
Rückfluss kuratiert (nicht 1:1 übernommen): jede Befund-/REC-ID getaggt, nur `[valid]`
eingearbeitet, die zwei tragendsten Befunde (AD-3, AD-4) vor Übernahme **gegen das Repo
verifiziert**. Review 2 lag nur teilweise vor (Paste abgeschnitten nach PRO-2) — dessen
Steelman konvergiert mit Review 1; keine widersprechenden Befunde erkennbar.

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
