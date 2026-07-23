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

> **Rev 2 (2026-07-21).** Die Erstfassung ruhte auf einer **falschen** technischen
> Prämisse. Zwei unabhängige externe Zweitmeinungen haben sie widerlegt, die Nachprüfung
> gegen die laufende Umgebung hat das bestätigt. §2, §3, §4.2 und §8 sind **neu
> geschrieben**, nicht nachgebessert. Was sich geändert hat: §11.

## Metadaten

| Attribut          | Wert                                                                 |
|-------------------|----------------------------------------------------------------------|
| **Status**        | Proposed                                                             |
| **Scope**         | platform                                                             |
| **Erstellt**      | 2026-07-21                                                           |
| **Autor**         | Achim Dehnert                                                        |
| **Externes Sparring** | 2 unabhängige externe LLM-Zweitmeinungen, 2026-07-21 — Verdikt **beide „überarbeiten"**; Tag-Bilanz in §12 |
| **Supersedes**    | ADR-229 — **erst bei Acceptance**, s. §9                             |
| **Superseded by** | –                                                                    |
| **Relates to**    | ADR-230 (CC-first Skill-Distribution), ADR-233 (Worktree-Konvention) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                                      |
|----------------|------------|---------------------------------------------------------------------|
| `platform`     | Primär     | `skills/`, `.windsurf/workflows/`, `tools/cc-skill-dist/`, `tools/check_workflow_index.py`, `.github/workflows/tools-tests.yml` |
| *(alle Maschinen)* | Sekundär | `~/.claude/skills/`, `~/.claude/commands/` — Installationsziele, kein Repo |

> **Kein Fleet-Claim.** Ein Repo plus die Installationsziele je Maschine. App-Hubs sind
> nicht betroffen (§6.3).

---

## Verifikationsstand

Diese Entscheidung hängt an fremdbestimmter Werkzeug-Semantik. Ohne benannte Version wäre
alles Weitere Behauptung — Rev 1 hat genau diesen Block vermissen lassen und ist deshalb
auf eine falsche Annahme gebaut.

| | |
|---|---|
| Werkzeug | Claude Code |
| Version | **2.1.216** (`claude --version`, 2026-07-21) |
| Quelle | `code.claude.com/docs/en/slash-commands`, abgerufen 2026-07-21 |
| Nachprüfpflicht | Bei jeder Änderung an §2/§4.2 erneut prüfen |

**Verifizierte Aussagen:**

1. *„Custom commands have been merged into skills. A file at `.claude/commands/deploy.md`
   and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and **work the
   same way**."*
2. Skills unterstützen `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N` sowie benannte `$name` über
   `arguments:` im Frontmatter.
3. `$N` ist **0-basiert** (`$0` = erstes Argument); klassische Slash-Commands waren 1-basiert.
4. Bei Namensgleichheit: *„if a skill and a command share the same name, **the skill takes
   precedence**."*
5. Ein Eintrag unter `~/.claude/skills/<name>` **darf ein Symlink** auf ein Verzeichnis
   anderswo sein; Claude Code folgt ihm und lädt dasselbe Ziel nur einmal.
6. Cowork- und Cloud-Sessions **inklusive Routinen lesen `~/.claude/skills/` nicht**. Sie
   laden account-seitig aktivierte Skills und — nur Cloud — Projekt-Skills aus
   `.claude/skills/` des geklonten Repos.
7. Skill-Verzeichnisse dürfen **Supporting Files** enthalten, die bei Bedarf geladen werden
   und selbst keine Skills sind.

**Ausdrücklich NICHT belegt:** dass `.claude/commands/` deprecated, „legacy" oder ein
bloßer Alias sei. Die Doku sagt *„Your existing `.claude/commands/` files keep working."*
Eine Suche nach `deprecat|legacy|no longer|will be removed|sunset` liefert dazu **keinen**
Treffer. Eine der beiden Reviews wollte die Entscheidung genau darauf umankern — das wäre
eine zweite unbelegte Prämisse gewesen und ist abgelehnt (§12).

---

## Decision Drivers

- **Zwei Quellverzeichnisse für Artefakte, die am Aufrufpunkt identisch sind.** Nach
  Verifikation 1 ist das keine Typunterscheidung, sondern Duplizierung.
- **Ein Verzeichnisname, der ein Werkzeug nennt, das dafür nicht mehr benutzt wird.**
- **ADR-230 hat die Umbenennung selbst vorgesehen** (§2.1, REC-3), vertagt seit 2026-05-30.
- **Die Zweitlane war für beide Gates unsichtbar** (bis #1290); ein Skill lag seit
  2026-06-05 un-indiziert, ohne dass etwas anschlug.
- **Der dritte Artefakttyp hat keine saubere Heimat** (§4.4).
- **Owner-Weisung 2026-07-21:** keine Parallelexistenz.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

Gemessen gegen `main` @ `805ee5d` (2026-07-21):

| | Lane `commands` | Lane `skills` |
|---|---|---|
| Quelle | `.windsurf/workflows/*.md` | `skills/<name>/SKILL.md` |
| Quell-Dateien (getrackt) | 52 | 4 |
| davon `distribute: false` | 3 | 0 |
| Installationsziel | `~/.claude/commands/` (flach) | `~/.claude/skills/` (verschachtelt) |
| Vollständigkeits-Gate | ja | ja (seit #1290) |
| CI-`paths`-Trigger | ja | ja (seit #1290) |

**Dritter Artefakttyp im selben Verzeichnis:** drei Dateien
(`adr-handoff-extern-reviewer{,-blind,-premortem}.md`) tragen `distribute: false` sowie
`provider: openai` / `model: openai/o3`. Es sind Persona-Prompts, die
`/adr-handoff-extern` als **Daten** liest — keine Skills. Der Generator filtert sie, aber
**nur** in der `commands`-Lane (`if args.kind == "commands" and DISTRIBUTE_FALSE.search(src)`).

### 1.2 Warum jetzt

Auslöser war eine unentscheidbare Frage im laufenden Betrieb: beim Rebase von
[#1013](https://github.com/achimdehnert/platform/pull/1013) gab es kein Kriterium dafür,
in welche Lane ein **neuer** Skill gehört. Beide Antworten waren begründbar. Eine
Konvention, die bei jedem neuen Artefakt eine Ad-hoc-Entscheidung erzwingt, ist keine.

---

## 2. Considered Options

> **Was sich gegenüber Rev 1 geändert hat:** Rev 1 verglich A und B unter der Annahme,
> Migration koste inhaltliche Überarbeitung (falsch, Verifikation 2), und schrieb A
> „Progressive Disclosure" als Vorteil gut (falsch, Verifikation 1 — beide Formen
> verhalten sich gleich). Beide Optionen sind **neu bewertet**, drei weitere kamen dazu.

### Option A: `skills/` wird die einzige Lane ✅

**Pros:**
- **Supporting Files** (Verifikation 7) — die einzige verifizierte Fähigkeit, die die
  flache Form **nicht** hat. Löst §4.4 ohne Sonderlogik.
- Tool-neutraler Pfadname; löst den in ADR-230 §2.1 selbst benannten Tool-Leak.
- Ein Generator-Modus, ein Gate-Scan, ein Installationsziel.
- Migrationskosten sind **mechanisch**: `git mv` plus Frontmatter-Kopf. Keine inhaltliche
  Überarbeitung (Verifikation 2 — das war Rev 1s Fehler).

**Cons:**
- Der Rückbau von `~/.claude/commands/` betrifft jede Maschine und ist der einzige nicht
  per Repo-Revert reversible Schritt.
- Bindet die Kanonik an eine **Herstellerbezeichnung**. `skills/` ist neutraler als
  `.windsurf/`, aber nicht neutral.

### Option B: `commands/` wird die einzige Lane (nur Umbenennung)

**Pros:**
- Beseitigt den `.windsurf`-Fehlnamen ebenfalls vollständig.
- Denkbar geringstes Risiko.

**Cons:**
- Keine Supporting Files → der dritte Artefakttyp bleibt auf `distribute: false`-Sonderlogik
  angewiesen, die heute schon lane-spezifisch und damit fragil ist.
  → **Abgelehnt weil:** der einzige verifizierte Unterschied zwischen den Formen ist genau
  die Fähigkeit, die wir brauchen. B verzichtet darauf, ohne dafür etwas zu gewinnen —
  seit A's Kosten (Verifikation 2) auf mechanisch geschrumpft sind.

### Option C: beide Lanes behalten, plus hartes Zuordnungskriterium

**Cons:** dauerhaft zwei Generator-Modi und zwei Scans für eine Unterscheidung, die am
Aufrufpunkt nicht existiert.
→ **Abgelehnt weil:** widerspricht der Owner-Vorgabe. Wird in §8.5 **nicht mehr** als
Rückfall geführt — ein Rückfall, den die Vorgabe verbietet, ist keiner (Review-Befund).

### Option D: beide Verzeichnisse behalten, weil der Hersteller sie vereint hat 🆕

Aus externer Review. `.windsurf/workflows/` → `.claude/commands/` umbenennen, beide Formen
weiter erzeugen, **ein** Gate über beide, Policy „`skills/` nur, wenn Supporting Files
gebraucht werden".

**Pros:**
- Nahezu null Migration, kein Maschinen-Rückbau.
- Nutzt die Herstellerhaltung (beide gleichwertig), statt gegen sie zu arbeiten.
- **Ist die risikoärmste aller Optionen.**

**Cons:**
- Zwei Quellformen bleiben — der Zustand, den die Owner-Vorgabe beendet.
- Verschiebt die Lane-Frage vom Anlegen auf den Moment, in dem ein Skill *später*
  Supporting Files braucht; dann ist doch ein Move fällig.
  → **Abgelehnt weil:** löst das Auslöseproblem aus §1.2 nicht, sondern vertagt es.
  **Ehrlich vermerkt:** ohne die Owner-Vorgabe wäre D die richtige Wahl. D bleibt der
  definierte Rückfall (§8.5).

### Option E: Symlink statt generierter Kopie 🆕

`~/.claude/skills/<name>` → Symlink auf `<repo>/skills/<name>` (Verifikation 5).

**Pros:**
- **Drift wird strukturell unmöglich** statt detektiert: Quelle *ist* Ziel. Manifest,
  Content-Hash, MANAGED-Footer und Round-Trip-Gate werden für diese Lane überflüssig.
- Kein Regenerate nach jedem Merge.

**Cons:**
- **Kehrt ADR-230 §2.2 um** („keine Symlinks auf volatilen Checkout"; der historische
  Hybrid wurde bewusst aufgelöst).
- Ein Checkout auf einem Feature-Branch verändert das Verhalten der laufenden Session.
  → **Nicht hier entschieden** — verdient ein eigenes ADR, weil es den Kern einer
  akzeptierten Entscheidung umkehrt. Tracking: §10.

### Option F: repo-lokale `.claude/skills/` 🆕

**Pros:**
- Schließt eine Lücke, die **alle** anderen Optionen offenlassen: Cowork-/Cloud-Sessions
  inklusive Routinen lesen `~/.claude/skills/` **nicht** (Verifikation 6). Nur
  repo-committete `.claude/skills/` erreichen Cloud-Sessions.

**Cons:**
- Repo-lokal heißt: nur in *diesem* Repo verfügbar, nicht maschinenweit.
  → **Nicht hier entschieden**, aber der Befund ist unabhängig von dieser Entscheidung
  gravierend. Tracking: §10.

---

## 3. Decision Outcome

**Gewählte Option: Option A — `skills/` wird die einzige Lane.**

Die Begründung ist gegenüber Rev 1 **vollständig ausgetauscht**:

Nach Verifikation sind beide Formen in allem gleich — Aufruf, Argumente, Frontmatter,
Ladeverhalten — **mit genau einer Ausnahme:** nur die Verzeichnisform trägt Supporting
Files. Das ist keine theoretische Eleganz, sondern die Antwort auf ein bestehendes
Problem: die drei Persona-Prompts sind heute allein durch lane-spezifische Sonderlogik
davor geschützt, versehentlich als Skills verteilt zu werden. Als Supporting Files ihres
konsumierenden Skills sind sie **per Konstruktion** keine Skills — die Sonderlogik
entfällt ersatzlos.

Gleichzeitig ist A's Preis stark gesunken: Rev 1 rechnete mit inhaltlicher Überarbeitung,
die es nicht gibt. Übrig bleibt ein mechanischer `git mv` plus Frontmatter-Kopf.

**Ehrlich benannt, was diese Entscheidung *nicht* trägt:**
- **kein** Hersteller-Trend — dafür fehlt der Beleg (Verifikationsstand),
- **kein** Kontextvorteil — beide Formen laden gleich,
- **keine** Argument-Migration — die gibt es nicht.

Die Entscheidung ruht damit auf **einem** Argument statt auf vieren. Das ist schmaler als
Rev 1 suggerierte, aber es ist geprüft.

---

## 4. Implementation Details

### 4.1 Phasen

| Phase | Inhalt | Zustand |
|---|---|---|
| 0 | Dieses ADR (Rev 2) | dieser PR |
| 1 | Pilot: 3 Skills migriert, Gate auf beide Lanes erweitert | [#1290](https://github.com/achimdehnert/platform/pull/1290) gemergt |
| 1b | Rev-1-Regression zurückgenommen (`$ARGUMENTS` wiederhergestellt) | [#1294](https://github.com/achimdehnert/platform/pull/1294) |
| 2 | Betriebsnachweis nach den Muss-Kriterien §8.1 | offen |
| 3a | Typ-3-Zielort umsetzen (§4.4) — **vor** dem Bulk-Move | offen |
| 3b | Bulk-Move der restlichen Skills | offen |
| 4 | Lane `commands` entfernen; `~/.claude/commands/` gegated zurückbauen | offen |
| 5 | **Bei Acceptance, gebündelt:** ADR-229-Status + Policy `claude-skills.md` | offen |

> Phase 0 umfasst **nur** dieses ADR. Rev 1 nannte hier zusätzlich das Policy-Update und
> widersprach damit dem eigenen §5 — von einer externen Review gefunden, hier bereinigt.

### 4.2 Argument-Substitution — Korrektur der Rev-1-Prämisse

Rev 1 behauptete, `$ARGUMENTS` entfalle unter Skills und drei Dateien bräuchten echte
Überarbeitung. **Das ist falsch** (Verifikation 2). Die Fehlannahme hatte drei Folgen:

1. Die Migrationskosten von Option A waren zu hoch angesetzt — was den A/B-Vergleich verzerrte.
2. Der „Pilot zuerst"-Grund war eine Scheinbegründung: die Frage war nicht offen, sondern
   in der Doku beantwortet. Der Pilot war trotzdem nützlich — er hat die Gate-Lücken
   gefunden —, aber nicht aus dem angegebenen Grund.
3. Im Pilot wurde in `issues-offen` funktionierendes `$ARGUMENTS` durch Prosa **ersetzt**.
   Laut Doku hängt die Laufzeit das Argument dann nur noch als `ARGUMENTS: <value>` an,
   statt es an der richtigen Stelle einzusetzen. Zurückgenommen in #1294.

**Was real zu prüfen ist**, statt der erfundenen Migration: `$N` ist 0-basiert, klassische
Slash-Commands waren 1-basiert. Wo eine Datei **positionale** Argumente nutzt, verschiebt
sich die Bedeutung still.

Bestandsprüfung über beide Lanes (2026-07-21):

| Datei | Form |
|---|---|
| `infra-cleanup.md:38` | ganzes `$ARGUMENTS` |
| `issues-abarbeiten.md:10,19` | ganzes `$ARGUMENTS` |
| `skills/issues-offen/SKILL.md` | ganzes `$ARGUMENTS` (nach #1294) |

**Keine Datei nutzt positionale Argumente in Substitutions-Position.** Der Indexwechsel ist
real, trifft unseren Bestand aber nicht. Fünf weitere `grep`-Treffer waren Fehlalarme
(Dollarbeträge, Prosa, ein `case "$1" in` **innerhalb** eines erzeugten Bash-Snippets).

> Diese Tabelle ist ein **Messwert mit Verfallsdatum**. Jeder neue Skill mit `$1`/`$2`
> fällt darunter — deshalb der Gate in §8.2.

### 4.3 Gates wachsen mit der Lane

Umgesetzt in #1290: `check_workflow_index.py` scannt beide Lanes; `tools-tests.yml`
triggert auf `skills/**`; fünf Tests decken Lane 2 ab; der Live-Test prüft sie mit.

**Nachzuziehen (Rev 2, §8.3):** der Duplikat-Test zählte einen in beiden Lanes vorhandenen
Namen **einmal** und maskierte damit genau die Kollision, die er hätte melden sollen — ein
Test, den ich selbst so geschrieben habe. Die Laufzeitwirkung ist zwar definiert (bei
Namensgleichheit gewinnt der Skill, Verifikation 4), aber „definiert" heißt nicht
„gewollt": eine stillschweigend gewinnende Kopie ist ein Drift-Vektor.

### 4.4 Dritter Artefakttyp — durch die Verzeichnisform gelöst

Die drei Persona-Prompts werden **Supporting Files** ihres konsumierenden Skills:

    skills/adr-handoff-extern/
    ├── SKILL.md
    └── prompts/
        ├── reviewer.md
        ├── reviewer-blind.md
        └── reviewer-premortem.md

Damit sind sie per Konstruktion keine Skills — kein Filter, kein `distribute: false`, keine
lane-spezifische Sonderlogik. Der Generator braucht **keine** Ausnahme mehr.

**Die Reihenfolge ist bindend:** Phase 3a kommt **vor** 3b. Ein Move der drei Dateien nach
`skills/` ohne diesen Schritt würde sie als aufrufbare Skills verteilen, weil
`distribute: false` heute nur in der `commands`-Lane ausgewertet wird. Rev 1 hatte das
erkannt, aber auf „vor Phase 3" terminiert — was denselben PR zuließ. Jetzt ist es eine
eigene, vorgelagerte Phase mit Negativtest (§8.2).

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` | 0 — ADR Rev 2 | 🔄 In Progress | 2026-07-21 | dieser PR |
| `platform` | 1 — Pilot + Gates | ✅ Abgeschlossen | 2026-07-21 | #1290 |
| `platform` | 1b — Regression zurück | 🔄 In Progress | 2026-07-21 | #1294 |
| *(Maschinen)* | 2 — Betriebsnachweis | ⬜ Ausstehend | – | Muss-Kriterien §8.1 |
| `platform` | 3a — Typ-3-Zielort | ⬜ Ausstehend | – | **vor** 3b, §4.4 |
| `platform` | 3b — Bulk-Move | ⬜ Ausstehend | – | Mengenidentität §8.3 |
| `platform` | 4 — `commands`-Lane entfernen | ⬜ Ausstehend | – | Transaktion §8.4 |
| `platform` | 5 — ADR-229-Status + Policy | ⬜ Ausstehend | – | gebündelt bei Acceptance |

---

## 6. Consequences

### 6.1 Good

- Ein Quellverzeichnis, ein Installationsziel, ein Generator-Modus, ein Gate-Scan.
- Der Pfadname nennt kein Werkzeug mehr, das nicht mehr benutzt wird.
- Neue Skills brauchen keine Lane-Entscheidung — die Frage aus §1.2 entfällt.
- Der dritte Artefakttyp verliert seine Sonderlogik ersatzlos.

### 6.2 Bad

- Der Maschinen-Rückbau ist der einzige nicht per Repo-Revert reversible Schritt.
- Bis Phase 4 existieren beide Lanes gleichzeitig — der Zustand, den dieses ADR beendet.
- **Die Kanonik hängt an einer Herstellerbezeichnung.** Benennt der Hersteller um,
  wiederholt sich exakt das `.windsurf`-Muster. Einstiegspunkt für die Neubewertung: §8.6.
- Die Entscheidung ruht auf **einem** Argument. Fällt Supporting-Files als Bedarf weg,
  fällt die Begründung.

### 6.3 Nicht in Scope

- **`.windsurf/`-Verzeichnisse in App-Hubs** (von `gen_project_facts.py` befüllt, ADR-265).
- **`windsurf-subset.py`** — in keinem CI-Workflow verdrahtet
  (`grep -rn 'windsurf-subset' .github/workflows/` → 0 Treffer); Schicksal in Phase 3b.
- **Optionen E und F** — eigene Entscheidungen, §10.

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Migrierter Skill verhält sich im Betrieb anders | Niedrig | Mittel | §8.1 Muss-Kriterien; Rückfall D |
| Maschinen-Rückbau entzieht laufenden Sessions Commands | Mittel | Hoch | §8.4 als getestete Transaktion mit Inventar + Restore |
| Typ-3-Prompts werden als Skills verteilt | Mittel | Mittel | Phase 3a vorgelagert + Negativtest §8.2 |
| Namenskollision während der Doppelphase | Mittel | Niedrig | Verhalten definiert (Skill gewinnt); Gate meldet Duplikate §8.3 |
| Neuer Skill nutzt `$1` 1-basiert gedacht | Mittel | Mittel | Gate §8.2 |
| Herstellersemantik ändert sich | Niedrig | Hoch | Versionspin + Kompatibilitätstest §8.6 |
| ADR bleibt „accepted" ohne Umsetzung | Mittel | Mittel | §8.5 Kill-Gate **mit Auslöser** |

---

## 8. Confirmation

### 8.1 Muss-Kriterien für Phase 2 (binär, kein Ermessen)

Bestanden nur, wenn **alle** zutreffen. Scheitert eines, gilt **ohne neue
Grundsatzdebatte** Option D:

1. Skill erscheint im `/`-Menü unter unverändertem Namen.
2. Aufruf **ohne** Argument verhält sich wie vorher.
3. Aufruf mit **einwortigem** Argument setzt es an der `$ARGUMENTS`-Stelle ein.
4. Aufruf mit **mehrwortigem, gequotetem** Argument ebenso.
5. Beschreibung ist gelistet, Body lädt erst beim Aufruf.
6. Verhalten in einer **neu gestarteten** Session, nicht nur der laufenden.

Ergebnis wird als versioniertes Artefakt im Repo abgelegt (Werkzeugversion, Ausgangscommit,
Testfälle, Beobachtung, Entscheid „A bestanden" / „Fallback D") — nicht als Chat-Notiz.

#### Messstand 2026-07-23 — 5/6, Kriterium 6 offen

Artefakt: [`docs/verifications/2026-07-23-adr280-betriebsnachweis.md`](../verifications/2026-07-23-adr280-betriebsnachweis.md)
(Werkzeugversion 2.1.218, Ausgangscommit `9371148`).

| # | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Ergebnis | ✅ | ✅ | ✅ | ✅ | ✅ | ⏳ offen |

Die Blockade aus dem Handover vom 2026-07-22 („Piloten live nicht installiert, es lief die
verwaiste `commands`-Lane") ist mit dem Live-Rollout am 2026-07-23 06:14 UTC entfallen;
`doctor.py --kind skills` meldet DRIFT-SCORE 0 ohne Lane-Dublette. **Kriterium 6 ist
konstruktionsbedingt erst in der nächsten Session messbar** — eine laufende Session kann
ihren eigenen Startzustand nicht rückwirkend herstellen. Vorbereitung ist dafür *nicht*
nötig (die Installation ist persistent); die Schritte stehen im Artefakt. Bis dahin bleibt
dieses ADR `proposed`: **kein** Entscheid „A bestanden", aber auch **kein** Fallback D,
weil kein Kriterium geprüft und gescheitert ist.

### 8.2 Automatisierte Gates

- **Index-Vollständigkeit** über beide Lanes (`check_workflow_index.py` in
  `tools-tests.yml`), Negativtest vorhanden.
- **Round-Trip je Lane** (`cc-skill-dist-doctor.yml`), DRIFT-SCORE 0. Nach Phase 4 muss der
  `commands`-Schritt **entfallen**, nicht dauergrün mitlaufen.
- **NEU — Positional-Argument-Gate:** ein Skill mit `$1`/`$2` in Substitutions-Position
  ohne `arguments:`-Frontmatter lässt den Build fehlschlagen.
- **NEU — Typ-3-Negativtest:** eine als nicht-invocable markierte Datei darf **nie** einen
  installierten Skill erzeugen.

### 8.3 Migrationsprüfung — Mengenidentität statt Bilanz

Rev 1 prüfte nur die **Summe** (49 + 3 = 52). Das ist unzureichend: ein verlorener und ein
doppelter Skill heben sich auf. Ersetzt durch **Mengenidentität der Namen** vor/nach jeder
Migrations-PR plus ein Migrationsmanifest (Quelle → Ziel → Inhalts-Hash oder ausdrücklich
genehmigte Transformation). Lane-übergreifende Duplikate lassen den Gate **fehlschlagen**
statt einmal gezählt zu werden; während eines Moves nur über eine befristete Allowlist mit
Ablaufdatum.

### 8.4 Phase 4 als getestete Transaktion + Invariante

Kein blindes Löschen: Dry-Run, Inventarliste **nicht-generierter** Nutzerdateien unter
`~/.claude/commands/`, deterministische Wiederherstellung aus einem gepinnten Commit
(ADR-230 REC-18), Prüfung nach dem Restore, klare Anweisung für laufende Sessions.

**Invariante danach:** auf jeder betroffenen Maschine liegen unter `~/.claude/commands/`
**keine** generierten oder verwaisten Dateien mehr. Prüfbar, nicht „wird beachtet".

### 8.5 Kill-Gate — mit Auslöser, nicht nur mit Datum

Rev 1 nannte ein Datum und Rückfalloptionen, aber weder Auslöser noch Verantwortlichen.
Beide Reviews stuften das übereinstimmend als Vorsatz statt Gate ein. Ersetzt durch:

- **Owner:** Achim Dehnert.
- **Tracking-Artefakt:** Issue [#1287](https://github.com/achimdehnert/platform/issues/1287),
  Fälligkeit **2026-12-31**.
- **Maschineller Auslöser:** geplanter CI-Job, der ab 2026-12-31 fehlschlägt, solange Phase
  4 offen ist. Ein Gate, das niemand auslöst, ist keines — dieselbe Regel, die dieses Repo
  unter „neue Lane ⇒ Gate wächst mit" längst auf Tooling anwendet.
- **Rückfall bei Auslösung:** Option **D** (nicht C — ein Rückfall, den die Owner-Vorgabe
  verbietet, ist keiner).

### 8.6 Vorausschauende Wartung

- Der **Verifikationsstand** trägt Werkzeugversion und Abrufdatum. Ein kleiner
  wiederholbarer Kompatibilitätstest deckt die vier tragenden Semantiken ab
  (Merge-Äquivalenz, `$ARGUMENTS`, Supporting Files, Namenspräzedenz) — ohne daraus eine
  Zukunftsgarantie abzuleiten.
- **Drift-Detector** (ADR-059), Staleness-Schwelle **6 Monate** — kurz, weil dieses ADR
  einen Übergangszustand beschreibt.
- **Frühwarnung:** ändert der Hersteller die Verzeichnissemantik, ist §6.2 der
  Einstiegspunkt für die Neubewertung, nicht ein erneutes Aufrollen der Grundsatzfrage.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — festgehaltene Architektur-Entscheidung mit Begründung und Alternativen |
| **Lane** | Vollständiger Verteilpfad von einer Quelle über einen Generator zu einem Installationsziel |
| **Supporting Files** | Zusatzdateien im Skill-Verzeichnis, die kein eigener Skill sind und nur bei Bedarf geladen werden |
| **Substitution** | Ersetzen eines Platzhalters wie `$ARGUMENTS` durch den beim Aufruf übergebenen Text |
| **Drift** | Auseinanderlaufen von Quelle und installierter Kopie |
| **Gate** | Automatischer Prüfschritt in der CI, der einen Merge blockieren kann |
| **CI** | Continuous Integration — automatische Prüfläufe bei jeder Änderung |
| **Frontmatter** | YAML-Kopfblock am Dateianfang zwischen zwei `---`-Zeilen |
| **Cowork / Cloud-Session** | Ausführungsumgebungen außerhalb der lokalen Maschine, die lokale Installationsverzeichnisse nicht lesen |

---

## 9. More Information

- **ADR-230** — amendiert; dieses ADR führt den dort in §2.1 (REC-3) vertagten
  Phase-2-Watchpoint aus und geht darüber hinaus, indem es die `commands`-Lane zurückbaut.
- **ADR-229** — **würde bei Acceptance dieses ADRs `superseded`**. Solange dieses ADR
  `proposed` ist, bleibt ADR-229 unverändert; die Relation ist maschinenlesbar in
  `docs/adr/index.json`. *(Rev 1 formulierte hier „superseded" als Tatsache — von einer
  externen Review als Widerspruch zum eigenen §5 gefunden.)*
- **ADR-233** — Umsetzungsarbeit läuft in per-Session-Worktrees.
- Issue [#1287](https://github.com/achimdehnert/platform/issues/1287) — Anker.
- PRs [#1290](https://github.com/achimdehnert/platform/pull/1290) (Pilot),
  [#1294](https://github.com/achimdehnert/platform/pull/1294) (Regression zurück).

---

## 10. Aufgeschobene Entscheidungen mit Tracking-Pflicht

Beide Punkte sind **nicht** Teil dieser Entscheidung, aber zu wertvoll zum Vergessen.
Aufgeschobene Restarbeit ohne Artefakt gilt in diesem Repo als nicht existent.

1. **Symlink statt Kopie (Option E).** Würde Manifest, Content-Hash und Round-Trip-Gate für
   diese Lane überflüssig machen, weil Drift strukturell unmöglich wird. Kehrt ADR-230 §2.2
   um → eigenes ADR.
2. **Reichweite über die lokale Maschine hinaus (Option F).** Cowork-/Cloud-Sessions
   inklusive Routinen lesen `~/.claude/skills/` **nicht**. Das gesamte Verteilmodell —
   `commands` wie `skills` — endet an der Maschinengrenze. Unabhängig von dieser
   Entscheidung ein offener Befund.

---

## 11. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-21 | Achim Dehnert | **Rev 2** nach zwei externen Zweitmeinungen (beide „überarbeiten"). Verifikationsstand mit Versionspin ergänzt. §4.2 korrigiert: `$ARGUMENTS` entfällt **nicht**. §2 neu: A/B neu bewertet, Optionen D/E/F ergänzt. §3 Begründung vollständig ausgetauscht (Supporting Files statt Kontext-/Migrationsargumenten). §8 Kill-Gate mit Owner + maschinellem Auslöser, Muss-Kriterien für Phase 2, Mengenidentität statt Bilanz, zwei neue Gates, Phase 4 als Transaktion. Phase 3a vorgelagert. Widersprüche §4.1/§5 und §9 bereinigt. §10 Tracking für E/F. Abgelehnt: Umankern auf „Hersteller macht `commands/` zur Altlast" — nicht belegbar. |
| 2026-07-21 | Achim Dehnert | Initial: Status Proposed |

---

## 12. Externes Sparring — Rückfluss-Tagging

Zwei unabhängige externe Zweitmeinungen am 2026-07-21, beide mit Verdikt **„überarbeiten"**.
Jeder Befund einzeln getaggt; nur `[valid]` ist eingeflossen, und zwar als Änderung mit
eigener Begründung, nicht als übernommene Prosa.

| Befund | Verdikt | Wirkung |
|---|---|---|
| `$ARGUMENTS` entfällt nicht | `[valid]` | §4.2 neu; Regression #1294 |
| `$N` 0-basiert, Off-by-one | `[valid]`, Bestand nicht betroffen | §4.2 Bestandstabelle + Gate §8.2 |
| Progressive Disclosure ist kein A-vs-B-Vorteil | `[valid]` | aus §2 entfernt |
| A-vs-B-Bilanz schrumpft | `[valid]` | §3 auf ein Argument reduziert, offen benannt |
| Vierte Option „beide behalten" fehlt | `[valid]` | Option D ergänzt, als Rückfall verankert |
| Kill-Gate ohne Auslöser/Owner | `[valid]` | §8.5 |
| Option C als Rückfall widerspricht der Vorgabe | `[valid]` | C als Rückfall entfernt, D ersetzt sie |
| Duplikat-Test maskiert Kollision | `[valid]` | §8.3 |
| Bilanzprüfung beweist nichts | `[valid]` | §8.3 Mengenidentität |
| Rollback Phase 4 nicht belastbar | `[valid]` | §8.4 |
| Widerspruch §4.1 vs. §5, §9-Wortlaut | `[valid]` | beide bereinigt |
| `distribute: false` lane-gebunden | `[valid]` | Phase 3a vorgelagert + Negativtest |
| Keine Muss-Kriterien für Phase 2 | `[valid]` | §8.1 |
| Kein Versionspin / Kompatibilitätsvertrag | `[valid]` | Verifikationsstand + §8.6 |
| Typ-3-Heimat sei kein tragfähiges A-Argument | `[missversteht-Kontext]` | Verifikation 7 belegt Supporting Files als exklusive Fähigkeit der Verzeichnisform — nach Wegfall aller anderen Argumente ist es das **einzige** tragende |
| Umankern auf „Hersteller macht `skills/` kanonisch, `commands/` Alias" | `[missversteht-Kontext]` | Doku sagt „keep working"; Suche nach `deprecat\|legacy\|no longer\|will be removed\|sunset` ohne Treffer. Hätte eine falsche Prämisse durch eine zweite ersetzt |
| Plugin-/Marketplace-Distribution | `[out-of-scope]` | eigene Re-Architektur; verwandter Befund als Option F in §10 getrackt |
| Tool-neutrale „capabilities/"-Abstraktion | `[out-of-scope]` | bei 52 Markdown-Dateien Über-Abstraktion; §6.2 hält den Auslöser fest, falls `skills/` mehrere Artefaktklassen aufnehmen müsste |

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
