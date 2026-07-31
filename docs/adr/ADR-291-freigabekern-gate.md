---
status: proposed
decision_date: 2026-07-31
deciders: [Achim Dehnert]
consulted: [Claude Code, Ilja Lerch (SB-Neu, indirekt)]
informed: []
supersedes: []
amends: []
related: [ADR-233, ADR-290]
implementation_status: none
last_reviewed: 2026-07-31
staleness_months: 3
tags: [ci, governance, drift, guardrails, konvention]
ai_sparring_by:
  - tool: other
    date: 2026-07-31
    role: adversarial-review
    summary: "Externes LLM Runde 1 (via /adr-handoff-extern): Verdikt ueberarbeiten — zwei von drei Pruefungen sind aus CI heraus nicht berechenbar; SUGGEST misst Rauschen statt Gueltigkeit und wuerde den Konstruktionsfehler zertifizieren. 18 Befunde, 10 Empfehlungen."
  - tool: other
    date: 2026-07-31
    role: adversarial-review
    summary: "Externes LLM Runde 2 (unabhaengig, via /adr-handoff-extern): Verdikt ueberarbeiten — Pruef-Ort, Claims und Abnahmekriterien neu schneiden; Manifest-Hash beweist weder Zielpfad noch Lane-Identitaet. 22 Befunde, 12 Empfehlungen."
---

# ADR-291: Integrität der Steuerzone — Quellprüfung in CI, Laufzeitprüfung am Ort

> **Nummern-Hinweis:** 291 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).

## Status-Hinweis

`proposed`, **Fassung 2 nach zwei unabhängigen externen Reviews** (2026-07-31). Beide
Verdikte: *überarbeiten*. Beide unabhängig mit derselben Hauptbegründung:

> Zwei der drei geplanten Prüfungen können aus CI heraus **genau den Zustand nicht
> beobachten, über den sie urteilen sollen.**

Fassung 1 hieß „Freigabekern-Gate" und wollte alles in einem CI-Job prüfen. Das war ein
Ortsfehler: SB-Neu prüft auf **derselben Maschine im selben Moment** wie die geschützte
Handlung; CI prüft auf einer anderen Maschine zu einer anderen Zeit und sieht
ausschließlich den PR. Fassung 1 benannte diesen Verlust nur für Prüfung 2 — er betrifft
alle drei.

**Selbstkritik, weil sie zur Sache gehört:** In derselben Sitzung habe ich
`evidence-discipline` Punkt 8 eingeführt — *„ein Prüflauf ohne Befund ist verdächtig"* —
und danach ein Gate entworfen, das aus strukturellen Gründen **nie rot werden kann**. Genau
davor warnt die Regel, die ich eine Stunde vorher geschrieben hatte.

**Und derselbe Fehler ein zweites Mal, im ersten Entwurf dieser Fassung:** A2 stand dort
als „Manifest-Ahnenschaft — beobachtbar in CI: ja", ohne dass ich geprüft hätte, **wo
`manifest.json` liegt.** Ein `find` über das Repo (null Treffer) widerlegt das: Die Datei
existiert nur unter `~/.claude/`. Ich hatte den Ortsfehler der Fassung 1 diagnostiziert und
ihn im selben Atemzug reproduziert. Korrigiert unten; die Lehre steht im Tagging-Abschnitt.

## Context

Wir haben ein wiederkehrendes, belegtes Problem: **Kanon-Entscheidungen driften weg, weil
nichts sie erzwingt.** Vier Vorfälle:

| # | Vorfall | Aus einem PR-Check fangbar? |
|---|---|---|
| 1 | Kanon-Entscheidung als Banner dokumentiert, ohne Gate — driftete weg | teilweise |
| 2 | Policy-Edit am **verteilten** Ort (`~/.claude/policies/`) statt an der Quelle | **nein** — passiert außerhalb jedes Repos |
| 3 | Ruleset-Bypass ohne Audit-Spur | **nein, prinzipiell** — ein Bypass ist das Umgehen genau dieser Prüfung |
| 4 | `generate.py --target` tauschte das komplette Lane-Verzeichnis `~/.claude` aus; `--allow-live` prüfte nur Gleichheit, nicht Identität des Ziels (#1558) | **nein** — passiert auf der Betreibermaschine |

**Diese Tabelle ist die eigentliche Korrektur gegenüber Fassung 1.** Dort stand,
das Gate gebe „vier belegten Drift-Vorfällen erstmals einen mechanischen Fänger". Das war
falsch: Drei der vier passieren dort, wo CI nicht hinsieht. Vorfall 3 kann von einer
PR-Prüfung **prinzipiell** nicht gefangen werden.

**Vergleichsfall (Fremdsystem), Übertragbarkeit ausdrücklich als Hypothese.** SB-Neu prüft
seine Steuerzone bei jedem Werkzeuglauf gegen den festgeschriebenen Stand, mit eigenem
Rückgabewert, der allen anderen Befunden vorgeht. Ich habe das einmal (n=1) unter Linux
scharf laufen lassen; es funktioniert dort. **Die Konstruktion überträgt sich aber nicht,
weil die Prüfung dort am Ort der Handlung sitzt** — bei uns wäre sie es nur, wenn sie beim
Verteilen und beim Sessionstart läuft, nicht im PR.

## Decision

**Die Integrität der Steuerzone wird an zwei getrennten Orten gesichert. Nur was CI
beobachten kann, läuft in CI.**

### Invariante A — Quellintegrität (in CI, path-gefiltert)

Prüft ausschließlich reproduzierbare Eigenschaften der **Quelle**:

| Prüfung | Rechnung | Beobachtbar in CI? |
|---|---|---|
| **A1 Zonen-Vollständigkeit** | kein Zonenpfad wird von `.gitignore` erfasst; keine aus dem Repo herausführenden Symlinks in der Zone | ja |
| **A2 Generator-Determinismus** | zwei Läufe des Generators gegen zwei temporäre Ziele erzeugen identische Hashes — der Generator ist reproduzierbar | ja |
| **A3 Erwartungs-Manifest aktuell** | der Generator schreibt ein **im Repo committetes** `manifest.expected.json`; CI regeneriert es und diffed gegen den Commit (Muster wie `ADR index freshness`) | ja, **sobald es dieses Manifest gibt** |

#### Voraussetzung von A3 — nachgemessen, nicht angenommen

**`manifest.json` existiert heute ausschließlich unter `~/.claude/{skills,commands}/`, nicht
im Repo** (`find` über `platform`: null Treffer; die Live-Datei trägt
`source_commit: 9371148f…`, `generator_version: 0.2.0`). Damit hat CI **keinen
Vergleichsgegenstand** — jede Prüfung, die das Manifest liest, ist in CI so unberechenbar
wie die Prüfungen aus Fassung 1.

**Das ist mein eigener Fehler derselben Klasse**, gefunden beim zweiten Durchgang durch
Runde 1 AD-4/REC-5: Fassung 2 dieses ADR schrieb zunächst „A2 Manifest-Ahnenschaft:
beobachtbar in CI — ja", ohne den Ort der Datei zu prüfen. Der billigste Check (ein `find`)
widerlegt das.

**Folge, als Entscheidung:** Der Generator schreibt künftig **zusätzlich** ein
`manifest.expected.json` in das Repo — den erwarteten Verteilstand, aus der Quelle
ableitbar. Erst dadurch bekommen A3 **und** die Laufzeitprüfung B2 einen definierten
Vergleichsgegenstand: B2 hält das Live-Manifest gegen das committete Erwartungs-Manifest.
Ohne diesen Schritt entfällt A3 ersatzlos, und B2 kann nur gegen `origin/main` als
Quellbaum prüfen statt gegen eine erklärte Erwartung.

**A1 ersetzt die „Versionsbindung" aus Fassung 1.** Die war in CI tautologisch: Der
Arbeitsbaum in einem Actions-Lauf **ist** der ausgecheckte Commit; ein Unterschied ist
konstruktionsbedingt nicht herstellbar. Die ursprüngliche Absicht (Arbeitsbaum gegen
Commit) gehört in einen Pre-Commit-Hook, nicht in CI.

**Prüfung 3 aus Fassung 1 („Anfügungsfestigkeit") entfällt ersatzlos in CI.** Sie sollte
feststellen, dass eine Policy-Änderung nicht nur am verteilten Ort geschah — ein Ereignis,
das im CI-Beobachtungsraum überhaupt nicht vorkommt. Der Name war zudem aus SB-Neu
entlehnt, wo er eine Append-only-Eigenschaft eines Journals meint; hier meinte er die
Herkunft einer Änderung. Name und geprüfte Invariante fielen auseinander.

### Invariante B — Laufzeitintegrität (am Ort, nicht in CI)

| Ort | Maßnahme |
|---|---|
| **B1 Generator-Härtung** (beim Schreiben) | `generate.py` verweigert `--target` auf Verzeichnisse ohne Lane-**Identitätsmarker** (nicht nur Inhaltsgleichheit), löscht keine manifestfremden Einträge, sichert vor dem Schreiben, schließt atomar ab |
| **B2 Sessionstart-Selbstcheck** (beim Lesen) | der Agent vergleicht beim Start sein `~/.claude`-Manifest gegen `origin/main`: kanonisch aufgelöster Zielpfad, erlaubte Zielwurzel, alle Hashes, unerwartete Dateien — Abweichung wird gemeldet |

**B1 ist die wichtigste Einzelmaßnahme dieses ADR** und war in Fassung 1 gar nicht
erwogen. Sie fängt Vorfall 2 und 4 **am Entstehungsort**, mit einer Fehlermeldung, die den
Fehler benennt — ohne CI-Job. Und sie **entfernt eine Fehlermöglichkeit**, statt eine
Prüfung hinzuzufügen: Sie verbessert die Komplexitäts-Bilanz, statt gerechtfertigt werden
zu müssen.

### Abbildung je Zonenpfad — wer prüft was, und was passiert bei Abweichung

Ohne diese Tabelle bleibt offen, welche Zonenpfade überhaupt verteilt werden und welche
nur im Repo leben. Fassung 2 beschrieb die Distributionsprüfung zunächst nur für
`skills`/`commands` und ließ `policies/`, `CLAUDE.md`, `CORE_CONTEXT.md` unbestimmt.

| Zonenpfad (ADR-290) | Laufzeitziel | Verteilmechanismus | Manifest | Prüf-Ort | Bei Abweichung |
|---|---|---|---|---|---|
| `.windsurf/workflows/` | `~/.claude/commands/` | `generate.py --kind commands` | ja | A1–A3 + B1/B2 | B2 meldet, `restore-from-source` |
| `skills/` | `~/.claude/skills/` | `generate.py --kind skills` | ja | A1–A3 + B1/B2 | B2 meldet, `restore-from-source` |
| `policies/` | `~/.claude/policies/` → **Symlink** nach `platform-pinned/policies` | `refresh_pinned_policies.sh` bei SessionStart (`checkout --detach origin/main`) | entfällt — Symlink, keine Kopie | **C6** (`klickdummy_policy_sync.sh`), auf der Maschine — **nicht** in CI, dort skippt er immer | C6 meldet stale Pin; Refresh-Hook zieht nach |
| `CLAUDE.md`, `CORE_CONTEXT.md` | wird **aus dem Repo** gelesen, nicht verteilt | keiner | entfällt | nur A1 | — |

**Die dritte Zeile ist ein Befund, kein Design:** `policies/` hat eine verteilte Kopie
unter `~/.claude/policies/`, aber — anders als `skills`/`commands` — **keinen belegten
Generator-Lane und kein Manifest**. Genau dort passierte Vorfall 2 (Policy-Edit am
verteilten Ort). Solange das ungeklärt ist, deckt weder A noch B diesen Pfad ab. Das ist
die größte verbleibende Lücke dieses ADR und steht als offener Punkt 4.

### Vorrangregel — auf ihren Adressaten verkleinert

Fassung 1 übernahm den SB-Neu-Satz *„dieses Urteil stammt nicht vom versionsführenden
Werkzeug"*. **In GitHub Actions ist das versionsführende Werkzeug der Urteilende** — der
Satz hat hier keinen Adressaten und wird gestrichen.

Was bleibt, ist der tragfähige Kern: *Ein Check, der die Steuerzone **liest**, urteilt
nicht belastbar, wenn deren Quellintegrität verletzt ist.* Das gilt für die zonelesenden
Checks (die beiden KI-Reviews, Guardian) — **nicht** für Lint oder Secret-Scan, die
`CLAUDE.md` nie anfassen. Nur diese bekommen `needs:`; alles andere bleibt parallel.
Andernfalls würde der Zonen-Job zur Latenz-Untergrenze jedes PRs — und erzeugte genau den
Zeitdruck, aus dem Vorfall 3 (Bypass) entstand.

### Abnahmekriterium — kein Gate ohne bewiesene Rot-Fähigkeit

**Jede gatende Prüfung liefert einen Negativ-Test mit, der in CI nachweislich rot wird.**
„Grüner Lauf auf einem echten PR" (Fassung 1, Schritt 2) ist als Abnahme **unzureichend**:
Grün beweist nichts über die Fähigkeit, rot zu werden.

Mutationsfälle, die A1–A3 erkennen müssen: geänderte Quelldatei ohne aktualisiertes
Manifest · manipuliertes Manifest · Manifest-Commit ist kein Vorfahr · Zonenpfad per
`.gitignore` ausgeblendet · Symlink aus der Zone heraus. Für B1/B2 zusätzlich: geänderte
Live-Datei · zusätzliche Live-Datei · falscher/umgeleiteter Zielpfad · Austausch des
gesamten Lane-Verzeichnisses.

**Und die Gegenprobe zuerst:** Bevor irgendetwas gebaut wird, wird versucht, A1 in CI rot
zu bekommen. Gelingt das nicht, ist die Prüfung tautologisch und entfällt — so wie A1 die
Prüfung 1 aus Fassung 1 abgelöst hat.

### Kein eigener Job

Der CI-Teil (A1–A3) läuft **path-gefiltert** (nur bei Änderungen an Steuerzone, Generator,
Manifest oder Gate-Code) und wird in einen bestehenden Check integriert (Guardian oder
Repo-Health), statt eine neue Check-Oberfläche zu erzeugen. Das Repo trägt schon 14 Checks.

### Begriffe

„Festgeschrieben" heißt in diesem ADR: **der Digest des tatsächlich verteilten Quellbaums**,
wie ihn `manifest.json` führt — nicht PR-Head, nicht Merge-Commit. Wo ein Commit-Bezug
nötig ist (A2), ist er ausdrücklich als Ahnenschafts-Relation zum PR-Head formuliert.

## Options considered

| Option | Beschreibung | Konsequenz | Verdikt |
|---|---|---|---|
| **A — Status quo** | Regel in Memory + Policy, keine Prüfung | Das Muster ist viermal aufgetreten. | verworfen |
| **B — Alles in einem CI-Gate** (Fassung 1) | drei Prüfungen im PR | Zwei davon aus CI nicht berechenbar; erzeugt Vertrauen, das sie nicht deckt. | **verworfen nach externem Review** |
| **C — Zweiteilung Quelle/Laufzeit** (gewählt) | A in CI, B am Ort | Jede Prüfung sitzt dort, wo ihr Gegenstand beobachtbar ist. Zwei Umsetzungsorte statt einem. | **gewählt** |
| **D — Freigabejournal wie SB-Neu** | Pflicht-Eintrag je Zonenänderung | Doppelung: Der PR **ist** unser Freigabejournal. | verworfen |
| **D' — Nur Generator-Härtung, kein CI-Teil** | ausschließlich B1, gar keine Prüfung in CI | Fängt Vorfall 2 und 4 am Entstehungsort, kostet keinen Job, **entfernt** eine Fehlermöglichkeit. Deckt aber Vorfall 1 nicht und lässt die Quelle selbst ungeprüft (Zonenpfad in `.gitignore`, Symlink aus dem Repo). | **teilweise übernommen** — B1 ist der erste Schritt und trägt den Großteil des Ertrags; A1 bleibt, weil es echte Quellfehler fängt, die B1 nicht sieht |
| **E — GitHub-native Mittel** | CODEOWNERS auf `policies/`, `skills/`, `.windsurf/workflows/` + Ruleset | Null neue Jobs, null Skripte. Sagt nichts über die verteilten Kopien. | **ergänzend übernommen** — konsequente Fortsetzung von „der PR ist das Journal" |
| **F — Gepinnter Checkout statt Kopie** | `~/.claude/skills` ist ein Checkout bzw. commit-adressiertes Bundle mit atomarem `current`-Verweis, kein kopiertes Verzeichnis | Das Drift-Problem **löst sich auf**, statt einen Detektor zu bekommen: „Abweichung" ist dann `git status`. Unklar, ob die Agenten-Laufzeit ein `.git`/Symlinks im Lane-Verzeichnis toleriert. | **Spike vor dem Bau** — die „Löschen statt Hinzufügen"-Option, die unsere eigene Konvention hätte hervorbringen müssen |
| **G — Steuerzone als eigenes Repo** | Zone = ganzes Repo, Ruleset erzwingt Review | Tauscht Drift gegen ein Submodul-Synchronisationsproblem. | verworfen |

## Consequences

**Positiv.** Jede Prüfung sitzt dort, wo ihr Gegenstand beobachtbar ist. B1 entfernt eine
Fehlermöglichkeit am Entstehungsort. Das Abnahmekriterium (bewiesene Rot-Fähigkeit)
verhindert ein Gate, das nur Vertrauen erzeugt.

**Was diese Entscheidung ausdrücklich NICHT leistet:**

> **Vorfall 3 (Ruleset-Bypass) wird von nichts hier gefangen** und kann es prinzipiell
> nicht — ein Bypass umgeht genau die Prüfung, die ihn fangen sollte. Sein Nachweis lebt
> im Ruleset-Bypass-Log bzw. Org-Audit-Log, außerhalb der Reichweite dieses ADR.
>
> Gedeckt sind: Vorfall 2 und 4 durch B1/B2, Vorfall 1 teilweise durch A und E.

**Negativ / Kosten.** Zwei Umsetzungsorte statt einem. B2 läuft auf der Betreibermaschine
und ist damit selbst Teil der Zone — es kann prinzipiell mitdriften. Das ist eine echte,
nicht auflösbare Restlage: Ein Selbstcheck, der Teil des Geprüften ist, hat eine
Selbstbezüglichkeit, die nur ein zweiter, unabhängiger Ort auflösen könnte.

**Komplexitäts-Bilanz.** Anders als in Fassung 1 **positiv**: B1 entfernt eine
Fehlermöglichkeit aus `generate.py` (die stillschweigende Ziel-Ersetzung), A1–A3 laufen
path-gefiltert in einem bestehenden Check statt in einem neuen Job, und Prüfung 3 aus
Fassung 1 entfällt ersatzlos.

## Umsetzungs-Reihenfolge

| Schritt | Inhalt | Gate |
|---|---|---|
| 0 | **Gegenprobe:** A1 in CI rot bekommen. Gelingt es nicht, entfällt A1. | empirisch |
| 1 | ADR-290 accepted (Zone deklariert, Pfade final) | Owner |
| 2 | **B1 Generator-Härtung** — höchster Ertrag, kein CI-Job | Negativ-Tests grün rot |
| 3 | Spike Option F (Bundle/Symlink statt Kopie) | Ergebnis entscheidet, ob B2 überhaupt nötig ist |
| 4 | A1–A3 path-gefiltert im bestehenden Check | Mutationstests + echter CI-Lauf |
| 5 | B2 Sessionstart-Selbstcheck | nur falls Schritt 3 negativ |
| 6 | Option E (CODEOWNERS/Ruleset) | Owner |

**Schritt 2 vor Schritt 4** ist die wichtigste Änderung der Reihenfolge: Die billigste und
wirksamste Maßnahme kommt zuerst, nicht der CI-Job.

## Externe Zweitmeinung — Rückfluss-Tagging (Step 5)

Zwei unabhängige Reviews am 2026-07-31, je eine Runde. **40 Befunde, 22 Empfehlungen.**
Verdikt beider: *überarbeiten*. Nur `[valid]` ist eingeflossen, jeweils eigene Formulierung.

| ID (Runde) | Kern | Verdikt | Aktion in Fassung 2 |
|---|---|---|---|
| AD-1 (1) | Ortsfehler betrifft **alle drei** Prüfungen, nicht nur Prüfung 2 | `[valid]` | Zweiteilung A/B — trägt die ganze Fassung |
| AD-2 (1) · AD-1 (2) | Prüfung 1 ist in CI tautologisch | `[valid]` | ersetzt durch A1 (Zonen-Vollständigkeit) |
| AD-3 (1) · AD-6 (2) | SUGGEST misst Rauschen, nicht Gültigkeit — zertifiziert den Konstruktionsfehler | `[valid]` | schärfster Befund; Prüfung 2 aus dem Gate genommen |
| AD-4 (1) · REC-5 (1) · AD-9 (2) | Ort von `manifest.json` und „festgeschriebener Stand" unterspezifiziert | `[valid]`, **zweiter Durchgang nötig** | Abschnitt „Begriffe". **Beim ersten Durchgang zu dünn behandelt:** Fassung 2 schrieb „A2 Manifest-Ahnenschaft — beobachtbar in CI: ja", ohne den Ort zu prüfen. Nachgemessen: `manifest.json` liegt **nur** unter `~/.claude/`, nicht im Repo → A2/A3 neu geschnitten, `manifest.expected.json` als Voraussetzung eingeführt |
| REC-4 (2) | explizite Abbildung je Zonenpfad (Quelle, Ziel, Mechanismus, Manifest, Prüf-Ort, Reaktion) | `[valid]`, **erst im zweiten Durchgang** | eigene Tabelle. **Genau diese Tabelle deckte auf, dass meine erste Antwort zu `policies/` falsch war** (Kopie statt Symlink) — Richtigstellung bei den offenen Punkten. Der Reviewer verlangte die Abbildung nicht ohne Grund: Sie erzwingt, jede Spalte einzeln zu beantworten, statt eine Annahme durchzuwinken |
| REC-4 (1) | Generator-Härtung als eigene Option in „Options considered" | `[valid]`, **erst im zweiten Durchgang** | Option D' mit Begründung, warum sie den CI-Teil nur teilweise ersetzt |
| AD-5 (1) | Vorfall 3 bekommt keinen Fänger, wird aber als gedeckt reklamiert | `[valid]` | Vorfalls-Tabelle + explizite Nicht-Leistung |
| AD-6 (1) · AD-11 (2) | „Anfügungsfestigkeit" ist ein Fremdbegriff, der hier etwas anderes meint | `[valid]` | Prüfung 3 entfällt, Begriff gestrichen |
| AD-7 (1) · AD-8 (2) | Vorrangregel hat in Actions keinen Adressaten / braucht Serialisierung | `[valid]` | auf zonelesende Checks verkleinert |
| AD-8 (1) | scharfer Lauf belegt, dass SB-Neu-Code läuft, nicht dass er überträgt | `[valid]` | als Hypothese gekennzeichnet |
| AD-9 (1) | billigste Alternative fehlt: Härtung von `generate.py` | `[valid]` | **B1, wichtigste Einzelmaßnahme** |
| AD-4 (2) | Distributionsprüfung nur für `skills`/`commands` beschrieben, nicht für die ganze Zone | `[valid]` | B2 prüft das ganze Manifest |
| AD-5 (2) | Manifest-Hash beweist weder Zielpfad noch Lane-Identität — also nicht Vorfall 4 | `[valid]` | B1 prüft **Identität**, nicht nur Gleichheit |
| AD-7 (2) · M28-2 (2) | eigener Job unverhältnismäßig, path-Filter fehlt | `[valid]` | path-gefiltert, in bestehenden Check integriert |
| AD-10 (2) · M28-1 (1) | keine Negativtests; grün beweist nichts über Rot-Fähigkeit | `[valid]` | Abnahmekriterium + Mutationsliste + Schritt 0 |
| AD-12 (2) | „deterministisch-strukturell" verwechselt Determinismus mit Beobachtbarkeit | `[valid]` | Formulierung gestrichen |
| M28-2 (1) | Zone steht zweimal (ADR-290-Tabelle + Prüfskript) — SSoT-Verstoß | `[valid]` | offener Punkt 1: Zone einmal maschinenlesbar |
| M28-3 (1) | `AGENT_HANDOVER.md` in der Zone ⇒ faktisch ein PR je Session | **`[erledigt]`** | bereits in ADR-290 Fassung 2 aus der Zone entfernt — vor diesem Review |
| M28-4 (1) | Vorrangregel per `needs:` macht den Job zur Latenz-Untergrenze | `[valid]` | nur zonelesende Checks |
| M28-5 (1) | Vokabular ist Prototyp-Metaphorik | `[valid]` | Titel und Prüfnamen sagen jetzt, was sie rechnen |
| M28-3 (2) · OOTB 2 (beide) | Kopplung an ein veränderliches Home-Verzeichnis; Kopien als Fehlerklasse abschaffen | `[valid]` | Option F + Spike als Schritt 3 |
| M28-5 (2) · REC-10 (2) | keine festgelegte Reparaturhandlung bei Drift | `[valid]` | offener Punkt 2 |
| M28-4 (2) · REC-12 (2) | 291 nicht vor 290 akzeptieren | `[valid]` | Schritt 1 der Reihenfolge |
| OOTB 3 (1) | GitHub-native Mittel (CODEOWNERS/Ruleset) | `[valid]` | Option E, ergänzend |
| OOTB 5 (1) | Steuerzone als eigenes Repo | `[valid]`, aber verworfen | Option G, mit Begründung |
| PRO-1…5 (beide) | Intent trägt: mechanische Durchsetzung ist richtig, ADR-233 belegt das Muster | `[valid]` | Entscheidung *zu gaten* bleibt |
| REC-5 (2) Teil „atomarer Installationsabschluss" | Detailanforderung an die Laufzeitprüfung | `[out-of-scope]` | Implementierungsdetail von B1, nicht ADR-Ebene |

**Bilanz:** 22 Empfehlungen, 20 eingeflossen, 1 `[out-of-scope]`, 1 bereits vorab erledigt.
**Fassung 1 hat den Ort der Prüfung nicht hinterfragt** — sie hat eine Konstruktion
übernommen, die auf einer Ein-Maschinen-Welt beruht, und sie in eine PR-Welt gestellt.
Das ist der eine Fehler, aus dem fast alle Befunde folgen.

## Offene Punkte

| # | Punkt | Wer entscheidet |
|---|---|---|
| 1 | Steuerzone genau **einmal** maschinenlesbar deklarieren (eine Datei im Repo); ADR-290 referenziert sie, das Prüfskript liest dieselbe Datei | Owner |
| 2 | Deterministische Reparaturhandlungen bei Drift (`verify`, `reinstall`, `show-diff`, `restore-from-source`) | Owner |
| 3 | Ergebnis des Spikes zu Option F — er kann B2 ganz überflüssig machen | offen |
| 4 | **`refresh_pinned_policies.sh` unter Versionskontrolle bringen** — der Hook, der die Steuerzone aktuell hält, ist selbst unversioniert (Richtigstellung unten) | Owner |
| 5 | Ob der Generator ein committetes `manifest.expected.json` schreibt — Voraussetzung für A3 und für ein aussagekräftiges B2 | Owner |
| 6 | **Wo C6 aufgerufen wird** — in CI ist er wirkungslos (Richtigstellung unten); Kandidat ist die SessionStart-Kette direkt nach dem Refresh | Owner |
| 7 | **Mid-Session-Drift** — der Refresh läuft nur bei SessionStart; während einer langen Sitzung veraltet die Zone unbemerkt (Realfall: 17 Commits) | Owner |

### Richtigstellung zum `policies/`-Pfad (2026-07-31, nachgemessen)

Die erste Fassung dieses offenen Punktes behauptete, `policies/` habe „eine verteilte Kopie
ohne Generator-Lane und ohne Manifest". **Das war zweifach falsch.** Was tatsächlich gilt:

| Behauptung (falsch) | Befund (gemessen) |
|---|---|
| „verteilte **Kopie**" | `~/.claude/policies` ist ein **Symlink** → `~/github/platform-pinned/policies` (`ls -ld`). Es gibt keine Kopie, die driften könnte. |
| „ohne Manifest" | Ein Symlink **braucht** kein Manifest. Die Invariante ist eine andere: der gepinnte Worktree darf nicht veralten. |
| „kein Prüfer" | `scripts/checks/klickdummy_policy_sync.sh` (ADR-211 C6) prüft **genau das** — SSoT gegen Injektionsziel gegen `origin/main`. Am 2026-07-31 grün laufen gesehen. |
| „kein Refresh" | `~/.claude/hooks/refresh_pinned_policies.sh` refresht bei SessionStart (`fetch` + `checkout --detach origin/main`), mit Dirty-Guard und fail-soft. Auch das ist in ADR-272 als Mechanismus geführt. |

**Der echte Befund ist ein anderer und schärfer** — drei Lagen, alle verifiziert:

1. **C6 hat keinen Aufrufer.** Ein Grep über alle Workflows, YAMLs und Skripte findet den
   Check nur in ADR-211 und CONCEPT-003 erwähnt, **in keinem Aufruf**. Das ist Vorfall 1
   dieses ADR in Reinform: Prüfer gebaut, funktioniert, wird nie ausgeführt.
2. **C6 gehört nicht in CI.** Das Skript skippt per Konstruktion, wenn `~/.claude/policies`
   fehlt — auf einem CI-Runner also **immer** (`exit 0`, „keine Injektions-Umgebung").
   Ihn dort einzuhängen erzeugte genau das Gate, das nie rot werden kann, gegen das der
   Abschnitt „Abnahmekriterium" oben geschrieben ist. Sein Ort ist die Maschine.
3. **Der Refresh-Hook ist selbst unversioniert.** `refresh_pinned_policies.sh` hat **keine
   Repo-Quelle** (`find` über `platform`: null Treffer) — anders als die `managed/`-Hooks,
   die aus der hooks-Lane kommen. Nach ADR-290 Regel 2 (Zonenintegrität) ist damit
   ausgerechnet das Werkzeug, das die Zone aktuell hält, kein owner-freigegebener,
   hash-prüfbarer Generator, sondern ein handgepflegtes Skript außerhalb jeder Kontrolle.

**Und die Latenz, die den Anlass gab:** Am 2026-07-31 stand der Pin auf `6d9c692b`
(11:09 Uhr, gesetzt vom Hook einer parallelen Session), während `origin/main` 17 Commits
weiter war — darunter geänderte `llm-routing.md` und `session-routing.md`. Die injizierte
Modell-Leiter war damit überholt. Der Hook hatte **nicht versagt**; er läuft nur bei
SessionStart, und es startete keine neue Session. Manuell über den Hook selbst nachgezogen
(`pinned → 0d078b29`, C6 danach grün, `git diff` gegen `origin/main` über `policies/` leer).
Das ist die „unbounded Redistribution-Latenz" aus ADR-272, hier einmal mit Zahlen.

## Herkunft

Analyse des Fremdsystems SB-Neu am 2026-07-31; Bewertung in
`~/.claude/boards/sb-neu-bewertung.md`. Fassung 1 in PR #1592.
Externe Review-Briefings: `~/shared/adr-handoff-ADR-291-2026-07-31.md`.
