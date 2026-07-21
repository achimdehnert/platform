---
status: proposed
decision_date: 2026-07-21
deciders: Achim Dehnert
domains: [tooling, dx, drift-prevention, governance]
supersedes: [ADR-229]
amends: [ADR-230, claude-skills.md]
related: [ADR-229, ADR-230, ADR-233]
tags: [skills, commands, workflows, distribution, claude-code, windsurf, consolidation]
---

# ADR-280: Konsolidiere die Skill-Verteilung auf eine Lane — `skills/` wird einzige Kanonik, `commands`-Lane und `.windsurf`-Pfad werden zurückgebaut

## Metadaten

| Attribut          | Wert                                                                 |
|-------------------|----------------------------------------------------------------------|
| **Status**        | Proposed                                                             |
| **Scope**         | platform                                                             |
| **Erstellt**      | 2026-07-21                                                           |
| **Autor**         | Achim Dehnert                                                        |
| **Reviewer**      | –                                                                    |
| **Supersedes**    | ADR-229 (Kanonische `.windsurf`-Distribution — Single Global Source) |
| **Superseded by** | –                                                                    |
| **Relates to**    | ADR-230 (CC-first Skill-Distribution), ADR-233 (Clean-State / Worktree-Konvention) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                                      |
|----------------|------------|---------------------------------------------------------------------|
| `platform`     | Primär     | `skills/`, `.windsurf/workflows/`, `tools/cc-skill-dist/`, `tools/check_workflow_index.py`, `.github/workflows/tools-tests.yml` |
| *(alle Maschinen)* | Sekundär | `~/.claude/skills/`, `~/.claude/commands/` — Installationsziele, kein Repo |

> **Kein Fleet-Claim.** Diese Entscheidung betrifft **ein** Repo (`platform`) plus
> die Installationsziele je Entwicklermaschine. Sie berührt **keine** App-Hubs:
> deren `.windsurf/`-Inhalte stammen aus einem separaten Verteilpfad
> (`scripts/gen_project_facts.py`) und sind hier ausdrücklich **nicht** in Scope
> (siehe §6.3).

---

## Decision Drivers

- **Zwei Lanes, eine Nutzungsstelle:** Beide Verzeichnisse werden zur Laufzeit in
  **einer** Skill-Liste angeboten. Die Trennung kostet Pflege, ist beim Aufruf aber
  unsichtbar — sie erzeugt Aufwand ohne Gegenwert.
- **Ein Verzeichnisname, der lügt:** `.windsurf/workflows/` speist zu 100 %
  Claude Code. Laut ADR-230 §2.3 ist Windsurf **kein Coding-Ziel mehr**.
- **ADR-230 hat die Umbenennung selbst schon vorgesehen** (§2.1, REC-3: „den
  Windsurf-benannten Pfad in einen tool-neutralen `skills/`-Pfad umbenennen") und
  ausdrücklich auf Phase 2 vertagt. Diese Phase ist seit 2026-05-30 offen.
- **Die Zweitlane war für Gates unsichtbar:** `check_workflow_index.py` scannte
  `skills/` nie; `tools-tests.yml` triggerte nicht auf `skills/**`. Der einzige
  Agent-Skill stand seit dem 2026-06-05 in keinem Index, ohne dass ein Gate anschlug.
- **Owner-Weisung 2026-07-21:** keine Parallelexistenz von `.claude`/`.windsurf`
  bzw. `commands`/`skills`.

---

## 1. Context and Problem Statement

Skill-artige Artefakte in `platform` existieren in zwei parallelen Lanes mit zwei
Quellverzeichnissen, zwei Installationszielen und zwei Generator-Modi
(`cc-skill-dist --kind commands|skills`). Beide liefern dasselbe Nutzungsbild:
ein per `/name` aufrufbares, agenten-lesbares Markdown-Dokument.

Die Trennung war 2026-06-05 als Unterscheidung zweier *Artefakttypen* gedacht
(Slash-Command vs. Anthropic Agent Skill). In der Praxis ist ein Typ auf **einen**
Vertreter geblieben, während der andere auf 51 gewachsen ist — und die
Unterscheidung ist am Nutzungsort nicht mehr sichtbar.

### 1.1 Ist-Zustand

Gemessen gegen `main` @ `cf3e08a` (2026-07-21):

| | Lane `commands` | Lane `skills` |
|---|---|---|
| Quelle | `.windsurf/workflows/*.md` | `skills/<name>/SKILL.md` |
| Quell-Dateien (getrackt) | 55 | 1 |
| davon `distribute: false` | 3 | 0 |
| Installationsziel | `~/.claude/commands/` (flach) | `~/.claude/skills/` (verschachtelt) |
| installiert | 51 | 1 |
| Vollständigkeits-Gate | ja | **nein** (bis #1290) |
| CI-`paths`-Trigger | ja | **nein** (bis #1290) |

Die Zahlen gehen auf: 55 − 3 (`distribute: false`) − 1 (`delete-repo`, am
2026-07-21 gemergt, noch nicht regeneriert) = 51. Ein Gegencheck auf Ziel-Dateien
ohne Quelle ist leer — es gibt keine verwaisten Installationsartefakte.

**Ein dritter Artefakttyp liegt mit im selben Verzeichnis.** Drei Dateien
(`adr-handoff-extern-reviewer{,-blind,-premortem}.md`) tragen `distribute: false`
und im Frontmatter `provider: openai` / `model: openai/o3`. Es sind Persona-/
System-Prompts, die `/adr-handoff-extern` als **Daten** liest — keine Skills,
weder für Claude Code noch als Agent Skill. Der Generator filtert sie heute
korrekt, aber **nur in der `commands`-Lane** (`if args.kind == "commands" and
DISTRIBUTE_FALSE.search(src)`).

### 1.2 Warum jetzt

Auslöser war eine unentscheidbare Frage bei laufender Arbeit: beim Rebase von
[#1013](https://github.com/achimdehnert/platform/pull/1013) (neuer Skill
`/delete-repo`) gab es kein Kriterium dafür, in welche der beiden Lanes ein
**neuer** Skill gehört. Beide Antworten waren begründbar. Eine Konvention, die bei
jedem neuen Artefakt eine Ad-hoc-Entscheidung erzwingt, ist keine Konvention.

Verschärfend: die Zweitlane war bis
[#1290](https://github.com/achimdehnert/platform/pull/1290) für beide relevanten
Gates unsichtbar. Der Vollständigkeits-Gate lief grün, **ohne** die Lane zu
prüfen — die Deckungslücke war strukturell nicht bemerkbar.

---

## 2. Considered Options

### Option A: `skills/` wird die einzige Lane ✅

Alle Slash-Commands wandern nach `skills/<name>/SKILL.md`; `.windsurf/workflows/`
und `~/.claude/commands/` werden zurückgebaut; `cc-skill-dist` verliert die Lane
`commands`.

**Pros:**
- Tool-neutraler Pfadname — löst den in ADR-230 §2.1/REC-3 selbst benannten Tool-Leak ein.
- Ein Verzeichnis je Skill erlaubt gebündelte Referenzen (Assets, Teilprompts) beim
  Skill — genau das, was der dritte Artefakttyp (§1.1) braucht.
- Progressive Disclosure: die Beschreibung wird gelistet, der Body erst beim Aufruf
  geladen. Bei ~50 Einträgen ist das der günstigere Kontextpfad.
- Nur **ein** Generator-Modus, **ein** Gate-Scan, **ein** Installationsziel.

**Cons:**
- `$ARGUMENTS`-Textsubstitution entfällt — 3 Dateien brauchen echte Überarbeitung.
- Rückbau von `~/.claude/commands/` betrifft jede Maschine; zu früh ausgeführt
  nimmt er Nutzern laufende Slash-Commands weg.

### Option B: `commands/` wird die einzige Lane (Quellverzeichnis nur umbenannt)

`.windsurf/workflows/` → `commands/`, Ziel bleibt `~/.claude/commands/`; der eine
Agent-Skill wandert zurück.

**Pros:**
- Minimales Risiko: `$ARGUMENTS` und Frontmatter funktionieren unverändert,
  **0** Dateien brauchen inhaltliche Überarbeitung.
- Beseitigt den `.windsurf`-Fehlnamen ebenfalls vollständig.

**Cons:**
- Verzichtet auf Progressive Disclosure und auf gebündelte Skill-Verzeichnisse —
  der dritte Artefakttyp bliebe heimatlos im selben flachen Verzeichnis.
  → **Abgelehnt weil:** die Lane, auf die man sich festlegt, wäre die ältere
  Ausdrucksform; der strukturelle Mangel (flach, keine Bündelung) bliebe bestehen.

### Option C: beide Lanes behalten, aber ein hartes Zuordnungskriterium schreiben

Status quo plus eine Regel, wann ein Artefakt in welche Lane gehört, plus
Gate-Abdeckung für beide.

**Pros:**
- Kein Migrationsaufwand, keine `$ARGUMENTS`-Umbauten.
- Erhält die konzeptuelle Unterscheidung, die die Policy `claude-skills.md` zieht.

**Cons:**
- Jedes neue Artefakt braucht weiter eine Zuordnungsentscheidung, jetzt nur
  regelbasiert statt ad hoc.
- Zwei Generator-Modi, zwei Ziele, zwei Scans dauerhaft zu pflegen — bei einem
  Lane-Verhältnis von 51 : 1.
  → **Abgelehnt weil:** die Regel würde eine Unterscheidung zementieren, die am
  Nutzungsort nicht existiert. Die Kosten sind dauerhaft, der Nutzen ist die
  Erhaltung einer Kategorie, die niemand beim Aufruf sieht.

---

## 3. Decision Outcome

**Gewählte Option: Option A — `skills/` wird die einzige Lane.**

Ausschlaggebend ist nicht die Ersparnis an Verzeichnissen, sondern dass Option A
die einzige ist, die alle drei Probleme gleichzeitig löst: den Tool-Leak im
Pfadnamen (den ADR-230 selbst als offene Phase 2 führt), die dauerhafte
Zuordnungsfrage bei neuen Artefakten, und die fehlende Heimat des dritten
Artefakttyps — für den ein Skill-**Verzeichnis** die passende Struktur bietet,
ein flaches Command-Verzeichnis nicht.

Option B wäre risikoärmer und ist ausdrücklich die Rückfalloption, falls die
Pilotphase die `$ARGUMENTS`-Semantik nicht sauber ersetzbar zeigt (§8).

---

## 4. Implementation Details

### 4.1 Phasen

| Phase | Inhalt | Zustand |
|---|---|---|
| 0 | Dieses ADR + Policy `claude-skills.md` nachziehen | dieser PR |
| 1 | Pilot: 3 Skills migrieren, Gate auf beide Lanes erweitern | [#1290](https://github.com/achimdehnert/platform/pull/1290), CI grün |
| 2 | Live-Rollout des Pilots + Betriebsnachweis in echter Session | offen |
| 3 | Bulk-Move der restlichen Skills; Zielort für Typ 3 entscheiden | offen |
| 4 | Lane `commands` aus `cc-skill-dist` entfernen; `~/.claude/commands/` gegated zurückbauen | offen |

Phase 1 lief **vor** Phase 0 bewusst vor: die Entscheidung hängt an einer
technischen Frage (§4.2), die sich nur durch Ausprobieren beantworten lässt.
Ein ADR, das diese Frage als beantwortet unterstellt, wäre eine Behauptung.

### 4.2 `$ARGUMENTS` — der eigentliche Migrationspunkt

Textsubstitution (`$ARGUMENTS`, `$1`) ist ein Slash-Command-Feature. Agent Skills
erhalten ihre Argumente über den Aufruf, nicht durch Ersetzung im Dateitext. Ein
unaufgelöst stehengebliebener Platzhalter wäre ein stiller Semantikfehler.

Betroffen sind **3** Dateien:

| Datei | Vorkommen |
|---|---|
| `infra-cleanup.md` | Zeile 38 |
| `issues-abarbeiten.md` | Zeilen 10, 19 |
| `issues-offen.md` | Zeilen 29, 35 — im Pilot bereits umgestellt |

> **Korrektur zur ersten Schätzung.** Ein erster `grep -l` meldete **8** Dateien.
> Fünf davon waren Fehlalarme: Dollarbeträge (`~$0.001`), Prosa („kein
> `$1`-Problem") und ein `case "$1" in` **innerhalb** eines Bash-Snippets, das der
> Skill erzeugt. Die Zahl im Fließtext ist geprüft, nicht geschätzt.

`provider:`/`model:`-Frontmatter erzeugt **keine** Reibung: die drei Treffer sind
genau die `distribute: false`-Dateien aus §1.1 und beschreiben ein externes
Review-LLM, nicht Claude Code.

### 4.3 Gates wachsen mit der Lane

Verbindlich (Konvention F-A aus `claude-skills.md`): eine Lane ohne mitwachsenden
Gate ist eine Schein-Garantie. In [#1290](https://github.com/achimdehnert/platform/pull/1290) umgesetzt:

- `check_workflow_index.py` scannt beide Lanes (`skills/<name>/SKILL.md`).
- `tools-tests.yml` triggert zusätzlich auf `skills/**` — ohne diesen Trigger liefe
  der Gate bei einer reinen `skills/`-Änderung nicht und bliebe fälschlich grün.
- Der Live-Test prüft die zweite Lane mit; fünf Tests decken sie ab.

### 4.4 Dritter Artefakttyp

`distribute: false` wird heute **nur** in der `commands`-Lane ausgewertet. Ein
unveränderter Move der drei Reviewer-Prompts nach `skills/` würde sie als Agent
Skills verteilen. Vor Phase 3 ist daher zu entscheiden, ob sie als gebündelte
Referenz beim konsumierenden Skill liegen
(`skills/adr-handoff-extern/prompts/…`) oder in einem eigenen `prompts/`-Baum —
und der Filter entsprechend zu ziehen.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` | 0 — ADR + Policy | 🔄 In Progress | 2026-07-21 | dieser PR |
| `platform` | 1 — Pilot (3 Skills) + Gates | ✅ Abgeschlossen | 2026-07-21 | #1290, CI grün, Drift 0 |
| *(Maschinen)* | 2 — Live-Rollout Pilot | ⬜ Ausstehend | – | Betriebsnachweis offen |
| `platform` | 3 — Bulk-Move + Typ-3-Zielort | ⬜ Ausstehend | – | 49 Skills, 2 × `$ARGUMENTS` |
| `platform` | 4 — `commands`-Lane entfernen | ⬜ Ausstehend | – | gegatet, s. §8 |
| `platform` | bei Acceptance — ADR-229 auf `superseded` setzen | ⬜ Ausstehend | – | bewusst **nicht** jetzt, s. u. |
| `platform` | bei Acceptance — `policies/claude-skills.md` nachziehen | ⬜ Ausstehend | – | bewusst **nicht** jetzt, s. u. |

**Zwei Änderungen sind bewusst aufgeschoben, nicht vergessen.** Solange dieses ADR
`proposed` ist, wäre beides eine Falschaussage:

- **ADR-229 bleibt vorerst `proposed`.** Ein ADR als „superseded by" einen erst
  vorgeschlagenen Nachfolger zu markieren, behauptet eine Ablösung, die noch nicht
  beschlossen ist. Der Statuswechsel gehört in denselben Zug wie die Acceptance
  dieses ADRs.
- **`policies/claude-skills.md` bleibt vorerst unverändert.** Die Policy beschreibt
  den geltenden Zustand — und der ist bis zur Acceptance die Zwei-Lane-Welt. Eine
  Policy, die eine geplante Welt beschreibt, ist genau die Sorte „Deklaration ≠
  Realität", die ADR-230 §2.4 abstellen wollte.

---

## 6. Consequences

### 6.1 Good

- Ein Quellverzeichnis, ein Installationsziel, ein Generator-Modus, ein Gate-Scan.
- Der Pfadname nennt kein Werkzeug mehr, das nicht mehr benutzt wird.
- Neue Skills brauchen keine Lane-Entscheidung — die Frage aus §1.2 entfällt.
- Gebündelte Skill-Verzeichnisse geben dem dritten Artefakttyp eine Heimat.

### 6.2 Bad

- Drei Dateien verlieren `$ARGUMENTS` und brauchen eine inhaltliche Umformulierung;
  jede davon ist eine mögliche Verhaltensänderung.
- Der Rückbau von `~/.claude/commands/` ist ein Eingriff je Maschine und nicht
  durch einen Repo-Merge erledigt.
- Bis Phase 4 existieren beide Lanes **gleichzeitig** — der Zustand, den dieses
  ADR beendet, besteht während der Umsetzung fort. Deshalb der Doppelscan aus §4.3.

### 6.3 Nicht in Scope

- **`.windsurf/`-Verzeichnisse in App-Hubs.** Die werden von
  `scripts/gen_project_facts.py` befüllt (Workflow-Kopien + Rules-Symlinks) und
  folgen ADR-265, nicht dieser Entscheidung. Ob deren Existenz zur Prämisse von
  ADR-229 passt, ist eine **offene, hier nicht geprüfte Frage** (§9).
- **`windsurf-subset.py`.** Das Review-Subset für Windsurf ist heute in keinem
  CI-Workflow verdrahtet (`grep -rn 'windsurf-subset' .github/workflows/` → 0
  Treffer). Sein Schicksal wird in Phase 3 entschieden, nicht hier.
- **Anthropic-seitige Semantik.** Ob `~/.claude/commands/` künftig unterstützt
  bleibt, ist keine Entscheidung dieses Repos und wird hier nicht behauptet.

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Migrierter Skill verhält sich im Betrieb anders (Argumente, Auffindbarkeit) | Mittel | Mittel | Phase 2 ist ein reiner Betriebsnachweis vor dem Bulk-Move; Rückfall auf Option B bleibt offen |
| Rückbau von `~/.claude/commands/` entzieht laufenden Sessions Slash-Commands | Mittel | Hoch | Phase 4 erst nach Phase 2/3; Rückbau je Maschine, Rollback über vorheriges Manifest (ADR-230 REC-18) |
| Typ-3-Prompts werden versehentlich als Skills verteilt | Mittel | Mittel | §4.4 — Zielort und Filter **vor** Phase 3 festlegen |
| Doppelphase (beide Lanes gleichzeitig) erzeugt Namenskollisionen | Niedrig | Niedrig | Gate zählt einen Namen einmal, auch wenn er in beiden Lanes liegt (Test vorhanden) |
| ADR bleibt „accepted" ohne Umsetzung | Mittel | Mittel | §5 Migration Tracking + Kill-Gate §8.4 |

---

## 8. Confirmation

1. **Vollständigkeits-Gate über beide Lanes:** `tools/check_workflow_index.py`
   läuft in `tools-tests.yml` und scannt `.windsurf/workflows/*.md` **und**
   `skills/*/SKILL.md`. Prüfbar: ein `skills/`-Eintrag ohne Index-Zeile liefert
   `rc=1` (Negativtest ist Teil der Suite).
2. **Round-Trip-Gate je Lane:** `cc-skill-dist-doctor.yml` erzeugt beide Lanes mit
   `generate.py` und verlangt von `doctor.py` DRIFT-SCORE 0. Nach Phase 4 muss der
   `commands`-Schritt **entfallen**, nicht dauergrün mitlaufen.
3. **Bilanzprüfung beim Bulk-Move:** Summe aus beiden Lanes bleibt vor und nach
   jeder Migrations-PR konstant (Pilot: 49 + 3 = 52).
4. **Kill-Gate:** Ist Phase 4 am **2026-12-31** nicht abgeschlossen, gilt die
   Konsolidierung als gescheitert; dann wird entweder auf Option B umgeschwenkt
   oder Option C bewusst als Dauerzustand akzeptiert — mit dann verbindlichem
   Zuordnungskriterium. Kein stilles Weiterlaufen im Doppelzustand.
5. **Drift-Detector:** Dieses ADR wird von ADR-059 auf Aktualität geprüft —
   Staleness-Schwelle: 6 Monate (kurz, weil es einen Übergangszustand beschreibt).

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — schriftlich festgehaltene Architektur-Entscheidung mit Begründung und Alternativen |
| **Lane** | Hier: ein vollständiger Verteilpfad von einer Quelle über einen Generator zu einem Installationsziel |
| **Slash-Command** | Per `/name` aufrufbares Markdown-Dokument; sein Text wird beim Aufruf direkt eingesetzt |
| **Agent Skill** | Verzeichnis mit `SKILL.md`; die Beschreibung wird gelistet, der Inhalt erst beim Aufruf geladen |
| **Progressive Disclosure** | Prinzip, zunächst nur Kurzbeschreibungen bereitzustellen und Details erst bei Bedarf nachzuladen |
| **Drift** | Auseinanderlaufen von Quelle und installierter Kopie |
| **Gate** | Automatischer Prüfschritt in der CI, der einen Merge blockieren kann |
| **CI** | Continuous Integration — automatische Prüfläufe bei jeder Änderung |
| **Frontmatter** | YAML-Kopfblock am Dateianfang zwischen zwei `---`-Zeilen |

---

## 9. More Information

- ADR-230: CC-first Skill-Distribution — **amendiert**; dieses ADR führt den dort
  in §2.1 (REC-3) benannten und vertagten Phase-2-Watchpoint aus und geht über ihn
  hinaus, indem es die `commands`-Lane ganz zurückbaut.
- ADR-229: Kanonische `.windsurf`-Distribution — **superseded**. Das ADR war nie
  über `proposed` hinausgekommen; seine Namensprämisse (`.windsurf` als Kanonik)
  entfällt mit dieser Entscheidung. Seine noch gültige Aussage (kein zweiter
  Wahrheitsstand neben `platform`) wird hier fortgeschrieben. **Offen und hier
  nicht geprüft:** ob die von `gen_project_facts.py` in App-Hubs angelegten
  `.windsurf/`-Inhalte dieser Aussage widersprechen.
- ADR-233: Worktree-Konvention — Umsetzungsarbeit zu diesem ADR läuft in
  per-Session-Worktrees.
- Issue [#1287](https://github.com/achimdehnert/platform/issues/1287) — Anker mit
  Messwerten und zwei protokollierten Korrekturen eigener Zahlen.
- PR [#1290](https://github.com/achimdehnert/platform/pull/1290) — Phase 1.
- Policy `~/.claude/policies/claude-skills.md` — wird mit diesem ADR nachgezogen.

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-21 | Achim Dehnert | Initial: Status Proposed |

---

<!--
  GOVERNANCE-HINWEISE (werden nicht in dev-hub angezeigt):

  Drift-Detector-Felder (ADR-059):
  - staleness_months: 6
  - drift_check_paths:
      - platform/skills
      - platform/tools/cc-skill-dist
      - platform/tools/check_workflow_index.py
  - supersedes_check: true

  Review-Checkliste: /docs/templates/adr-review-checklist.md
  Template-Version: 2.1 (2026-07-10 — ADR-271)
-->
