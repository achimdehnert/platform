---
status: accepted
decision_date: 2026-07-21
deciders: Achim Dehnert
domains: [tooling, dx, drift-prevention, governance]
supersedes: []
amends: [ADR-230]
related: [ADR-229, ADR-230, ADR-233, ADR-280]
tags: [skills, distribution, symlink, drift-prevention, claude-code, cc-skill-dist]
---

# ADR-281: Verteile Skills als Symlinks auf den Repo-Checkout statt als generierte Kopien

## Metadaten

| Attribut          | Wert                                                                 |
|-------------------|----------------------------------------------------------------------|
| **Status**        | Accepted (2026-07-22, nach §8.1 6/6 — Nachweis s. §8.1)              |
| **Scope**         | platform                                                             |
| **Erstellt**      | 2026-07-21                                                           |
| **Autor**         | Achim Dehnert                                                        |
| **Reviewer**      | –                                                                    |
| **Supersedes**    | –                                                                    |
| **Superseded by** | –                                                                    |
| **Relates to**    | ADR-230 (amendiert §2.2), ADR-233 (Worktree-Guard), ADR-280 (Lane-Konsolidierung) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                                      |
|----------------|------------|---------------------------------------------------------------------|
| `platform`     | Primär     | `tools/cc-skill-dist/generate.py`, `doctor.py`, `.github/workflows/cc-skill-dist-doctor.yml` |
| *(alle Maschinen)* | Sekundär | `~/.claude/skills/` — Installationsziel, kein Repo |

---

## Verifikationsstand

Diese Entscheidung hängt an fremdbestimmter Werkzeug-Semantik. Ohne benannte Version wäre
sie Behauptung — dieselbe Lehre, die ADR-280 Rev 2 erzwungen hat.

| | |
|---|---|
| Werkzeug | Claude Code |
| Version | **2.1.216** (`claude --version`, 2026-07-21) |
| Quelle | `code.claude.com/docs/en/slash-commands`, abgerufen 2026-07-21 |

**Verifiziert (Dokumentation):**

1. *„A `<skill-name>` entry in the enterprise, personal, or project locations **can be a
   symlink to a directory elsewhere on disk**. Claude Code follows the symlink and reads
   `SKILL.md` from the target directory, and if the same target is reachable from more than
   one location, Claude Code loads the skill once."*
2. *„Claude Code watches skill directories for file changes. Adding, editing, or removing a
   skill under `~/.claude/skills/` … takes effect **within the current session** without
   restarting."*

**Verifiziert (Messung im Repo, 2026-07-21):**

3. ADR-233 (`decision_date: 2026-06-01`) ist **jünger** als ADR-230 (`2026-05-30`).
4. Der Haupt-Tree-Guard **erzwingt** tatsächlich: `.git/iil-guard-events.log` enthält zwei
   `unauthorized_head_flip`-Einträge vom 2026-07-21, beide mit Rücksetzung auf `main`.
   ADR-233 selbst hatte diesen Nachweis ausdrücklich zur Bedingung gemacht
   („‚unerreichbar' gilt *nur*, wenn der Guard tatsächlich erzwingt").
5. ADR-230s Rollout-Gate (§8) hat **8 offene Checkboxen, 0 abgehakt** — darunter
   „**Rollback** (vorheriges Manifest reaktivierbar) **getestet** (REC-18)".
6. `~/github/platform-pinned` steht auf einem detached HEAD, **11 Commits hinter `main`**,
   und wird von keinem Tooling gepflegt: die einzigen Fundstellen in `tools/` und
   `scripts/` behandeln es als etwas zum **Überspringen**.

**~~NICHT verifiziert~~ → verifiziert am 2026-07-22 (Nachtrag, Werkzeugversion 2.1.217):**
dass ein symlinkter Skill in dieser Umgebung tatsächlich lädt. Zum Zeitpunkt der
Erstfassung stammte die Aussage aus der Dokumentation, nicht aus einem Lauf. Phase 1
(§8.1) ist inzwischen vollständig durchgeführt — **6/6**, inklusive des Ladeverhaltens in
einer frisch gestarteten Session. Belegt in
[`docs/verifications/2026-07-22-adr281-symlink-ladetest.md`](../verifications/2026-07-22-adr281-symlink-ladetest.md).

Die Prämisse dieses ADR ist damit nicht mehr angenommen, sondern gemessen — das ist der
Grund, warum es von `proposed` auf `accepted` wechseln konnte.

---

## Decision Drivers

- **Drift ist heute ein Detektionsproblem, kein gelöstes.** Manifest, Content-Hash,
  MANAGED-Footer, `doctor.py` und ein CI-Round-Trip existieren ausschließlich, um
  Abweichungen zwischen Quelle und Kopie zu *finden*. Ohne Kopie gäbe es nichts zu finden.
- **ADR-230s Einwand galt der Volatilität, nicht dem Symlink** — im Wortlaut: „keine
  Symlinks auf **volatilen** Checkout". Diese Prämisse hat sich geändert (Verifikation 3/4).
- **Die Gegenleistung der Kopie ist unbelegt** (Verifikation 5): Pin und Rollback sind
  zugesagt, aber der Nachweis wurde nie erbracht.
- **Jeder Merge erfordert heute ein Regenerate je Maschine**, sonst läuft die Maschine auf
  altem Stand — ein stiller, wiederkehrender Handgriff.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand

`cc-skill-dist/generate.py` liest die Quelle aus einem aufgelösten Git-Commit, erzeugt
Kopien in ein Staging-Verzeichnis, hängt jeder Datei einen MANAGED-Footer
(`source_commit`, `content_hash`, `do_not_edit`) an, schreibt ein `manifest.json` und
tauscht das Zielverzeichnis atomar. `doctor.py` vergleicht Ziel gegen Quelle und meldet
einen DRIFT-SCORE; ein CI-Job erzwingt Score 0.

Der gesamte Apparat hat **einen** Zweck: die Kopie kann von der Quelle abweichen, also muss
das erkennbar sein.

### 1.2 Warum jetzt

ADR-230 verwarf Symlinks am 2026-05-30 mit der Begründung „keine Symlinks auf volatilen
Checkout". Zwei Prämissen dieser Begründung gelten nicht mehr:

- **Der Checkout ist nicht mehr volatil.** ADR-233 (2026-06-01, also *nach* ADR-230) macht
  den Haupt-Tree unerreichbar für Branch-Wechsel, und der Guard erzwingt das nachweislich
  (Verifikation 4).
- **Der Hersteller dokumentiert Symlink-Auflösung ausdrücklich** (Verifikation 1). Ob das
  am 2026-05-30 schon galt, ist unbekannt — dieses ADR behauptet dazu nichts.

Hinzu kommt ein Befund, der bei der ADR-280-Revision auffiel: ADR-230s Rollout-Gate ist
nach über sieben Wochen zu **0 %** abgehakt. Die Vorteile, die man für den Apparat in Kauf
nimmt, sind nie eingelöst worden.

---

## 2. Considered Options

### Option A: Symlink auf den Haupt-Tree ✅

`~/.claude/skills/<name>` → `<GITHUB_DIR>/platform/skills/<name>`, erzeugt von
`generate.py --kind skills --link`.

**Pros:**
- **Drift wird strukturell unmöglich** statt detektiert: Quelle *ist* Ziel. Manifest,
  Content-Hash, MANAGED-Footer und Round-Trip-Gate entfallen für diese Lane ersatzlos.
- Kein Regenerate nach jedem Merge — ein `git pull` genügt, und die Änderung greift laut
  Verifikation 2 sogar in der laufenden Session.
- Der `do_not_edit`-Schutz wird überflüssig: eine Änderung am Ziel *ist* eine Änderung an
  der git-verfolgten Quelle und damit in `git status` sichtbar. Das ist strenger als ein
  Footer, den niemand durchsetzt.

**Cons:**
- **Kein Pin, kein Rollback auf Installations-Ebene.** Der installierte Stand ist immer der
  aktuelle Checkout. Rückweg ist `git revert` plus `git pull` — nicht die Reaktivierung
  eines früheren Manifests.
- **Dangling Symlink bei verschobenem/gelöschtem Repo** ⇒ Skills verschwinden still.
- Setzt voraus, dass das Repo auf jeder Maschine existiert. Kopien laufen auch ohne.
- `generate.py` verschwindet **nicht** — Pfade unterscheiden sich je Maschine, die Links
  müssen weiterhin erzeugt werden. Der Apparat schrumpft, er endet nicht.

### Option B: Symlink auf einen gepflegten, gepinnten Worktree

`~/.claude/skills/<name>` → `platform-pinned/skills/<name>`, wobei der Pin bewusst
weitergesetzt wird. Vereint Drift-Freiheit *und* Pin.

**Cons:**
- **Die Infrastruktur existiert nicht.** `platform-pinned` steht 11 Commits hinter `main`
  und wird von keinem Tooling gepflegt (Verifikation 6); die vorhandenen Fundstellen
  behandeln es als Sonderfall zum Überspringen.
  → **Abgelehnt weil:** die Option führt die Pin-Pflege als *neue* Maschinerie wieder ein,
  die man gerade abbauen will — und baut auf einem Artefakt auf, das heute unbetreut ist.
  *(Diese Option stammt von mir und ist an der eigenen Faktenprüfung gescheitert. Sie bleibt
  als Eskalationspfad in §9, falls Pinning je gebraucht wird.)*

### Option C: Status quo — generierte Kopien behalten

**Pros:**
- Pin, Manifest, Audit-Spur und ein definierter Rollback-Pfad.
- Funktioniert ohne lokales Repo.

**Cons:**
- Der einzige Grund für den gesamten Drift-Apparat ist die Kopie selbst.
- Die zugesagten Vorteile sind **unbelegt** (Verifikation 5).
  → **Abgelehnt weil:** man zahlt dauerhaft für Eigenschaften, deren Nachweis seit sieben
  Wochen aussteht. Bliebe der Nachweis dauerhaft aus, wäre die Kopie reine Zeremonie.

### Option D: Hybrid — Symlink lokal, Kopie anderswo

**Cons:** Genau der Hybrid, den ADR-230 §2.2 ausdrücklich aufgelöst hat („EINE Form, kein
Hybrid"), und dessen Auflösung dort fail-closed als Akzeptanzbedingung gesetzt ist.
→ **Abgelehnt weil:** würde eine bewusst beseitigte Fehlerquelle wiederbeleben. Wenn eine
Umgebung ohne Repo bedient werden muss, ist das ein Reichweiten-Problem (ADR-280 §10,
Option F), kein Grund für zwei Installationsformen nebeneinander.

---

## 3. Decision Outcome

**Gewählte Option: Option A — Symlink auf den Haupt-Tree.**

Der Ausschlag ist ein Vergleich zweier *unbelegter* Zusagen unter ungleichem Aufwand: Die
Kopie verspricht Pin und Rollback und hat den Nachweis in sieben Wochen nicht erbracht
(Verifikation 5). Der Symlink verspricht Drift-Freiheit — ebenfalls noch nicht in einem
Lauf bestätigt (§8.1) —, braucht dafür aber **keinen** Apparat, sondern dessen Abwesenheit.
Zwischen zwei ungeprüften Zusagen ist die mit weniger beweglichen Teilen die bessere Wette.

**Was bewusst aufgegeben wird:** der Pin. Der installierte Stand folgt dem Checkout. Für
52 Markdown-Dateien ohne Laufzeitverhalten ist `git revert` ein angemessener Rückweg —
und im Unterschied zum Manifest-Rollback ein Mechanismus, der täglich benutzt und dadurch
tatsächlich funktioniert.

**Ausdrücklich nicht behauptet:** dass Symlinks generell besser seien als Kopien. Die
Entscheidung gilt für **diesen** Inhalt (Markdown, git-verfolgt, ein Repo, wenige Maschinen)
unter **diesen** Bedingungen (Guard hält den Haupt-Tree auf `main`). Ändert sich eine davon,
ist §9 der Einstieg für die Neubewertung.

---

## 4. Implementation Details

### 4.1 `generate.py --link`

Neuer Modus neben dem Kopiermodus, zunächst **additiv**: statt Dateien zu schreiben, legt
er je Skill einen Verzeichnis-Symlink im Staging an und tauscht wie bisher atomar. Der
MANAGED-Footer entfällt (er würde die Quelle verändern); `manifest.json` bleibt, schrumpft
aber auf `source_repo`, `generator_version`, `target_type: symlink` und die Link-Ziele —
es ist dann eine **Inventarliste**, keine Integritätsprüfung mehr.

### 4.2 `doctor.py` — vom Hash-Vergleich zur Ziel-Auflösung

Der Drift-Vergleich verliert seinen Gegenstand. An seine Stelle tritt die einzige
Fehlermöglichkeit, die der Symlink neu einführt:

1. Zeigt jeder Link auf ein existierendes Verzeichnis mit `SKILL.md`? (**dangling** = Skill
   still weg — der Hauptrisikofall, §7)
2. Zeigt jeder Link in den erwarteten Repo-Pfad und nicht irgendwohin?
3. Ist jeder Skill der Quelle verlinkt und kein Fremdeintrag vorhanden?

### 4.3 Verhältnis zu ADR-230

Amendiert, nicht umgekehrt. ADR-230s tragende Sätze bleiben gültig: **eine** kanonische
Quelle, **eine** Form, kein Hybrid, fail-closed. Ersetzt wird ausschließlich die
Realisierung der „einen Form" — Symlink statt Kopie — und die daran hängende
Determinismus-Definition, die mit identischer Quelle trivial erfüllt ist.

Für die `commands`-Lane ändert dieses ADR **nichts**; sie wird laut ADR-280 ohnehin
zurückgebaut.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` | 0 — dieses ADR | ✅ Done | 2026-07-22 | `accepted` nach §8.1 6/6 |
| *(1 Maschine)* | 1 — Einzel-Symlink-Nachweis | ✅ Done | 2026-07-22 | §8.1 **6/6**; Artefakt `docs/verifications/2026-07-22-adr281-symlink-ladetest.md` |
| `platform` | 2 — `--link` + `doctor`-Umbau + Gate | ⬜ Ausstehend | – | §4.1/§4.2; Gate-Vorbedingung: [#1368](https://github.com/achimdehnert/platform/issues/1368) |
| *(alle Maschinen)* | 3 — Umstellung je Maschine | ⬜ Ausstehend | – | gegatet |
| `platform` | 4 — Kopier-Apparat für die skills-Lane entfernen | ⬜ Ausstehend | – | erst nach §8.4 |

---

## 6. Consequences

### 6.1 Good

- Eine ganze Fehlerklasse verschwindet, statt überwacht zu werden.
- Weniger Code: Hash-Vergleich, Footer-Erzeugung und Footer-Parsing entfallen.
- Änderungen sind nach `git pull` sofort wirksam, ohne Zwischenschritt.
- Hand-Edits am Ziel werden von `git status` sichtbar gemacht — strenger als ein Kommentar.

### 6.2 Bad

- Kein Installations-Pin mehr; Rückweg läuft über die Repo-Historie.
- Neue, wenn auch schmale Fehlerklasse: dangling Symlinks (§7).
- Abhängigkeit vom lokalen Repo an einem auflösbaren Pfad.
- Ein `git pull` auf `main` verändert das Verhalten der laufenden Session (Verifikation 2)
  — meist erwünscht, aber es ist ein Verhaltenswechsel und wird hier nicht schöngeredet.

### 6.3 Nicht in Scope

- Die `commands`-Lane (ADR-280 baut sie zurück).
- Reichweite über die lokale Maschine hinaus — Cowork-/Cloud-Sessions lesen
  `~/.claude/skills/` nicht (ADR-280 §10, Option F). **Symlinks ändern daran nichts.**
- Repo-Hooks und andere `cc-skill-dist`-Lanes.

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Dangling Symlink nach Repo-Umzug ⇒ Skills still weg | Mittel | Hoch | `doctor.py`-Auflösungsprüfung (§4.2) + Session-Start-Check |
| Kein Rollback auf Installations-Ebene | Mittel | Mittel | `git revert` ist der Rückweg; §8.3 verlangt einen Nachweis, dass er trägt |
| `git pull` ändert Skills mitten in einer Session | Mittel | Niedrig | Verifikation 2 ist dokumentiertes Verhalten; Guard hält den Haupt-Tree auf `main` |
| ~~Symlink lädt in dieser Umgebung doch nicht~~ **entfallen 2026-07-22** | – | – | §8.1 durchgeführt: **6/6**. Das Risiko ist keine Prognose mehr, sondern gemessen widerlegt (Artefakt `docs/verifications/2026-07-22-adr281-symlink-ladetest.md`). |
| Guard fällt aus, Haupt-Tree wandert auf einen Branch | Niedrig | Mittel | ADR-233 `report` zählt Flips; §8.4 macht Nicht-Null zum Blocker |

---

## 8. Confirmation

### 8.1 Muss-Kriterien Phase 1 (binär) — vor jeder Tooling-Arbeit

Ein einzelner, von Hand gesetzter Symlink unter einem **noch unbenutzten** Namen, damit
nichts überdeckt wird:

1. Der Skill erscheint im `/`-Menü.
2. Aufruf funktioniert, Body wird geladen.
3. `$ARGUMENTS` wird korrekt eingesetzt.
4. Eine Änderung an der Quelldatei wirkt ohne Neustart (Verifikation 2).
5. Verhalten in einer **frisch gestarteten** Session.
6. Entfernen des Symlinks entfernt den Skill sauber.

Scheitert eines, wird dieses ADR **`rejected`** und ADR-230 §2.2 bleibt unverändert.
Ergebnis als versioniertes Artefakt im Repo, nicht als Chat-Notiz.

**Ergebnis (2026-07-22, Werkzeugversion 2.1.217) — 6/6, kein Kriterium gescheitert.**
Artefakt: [`docs/verifications/2026-07-22-adr281-symlink-ladetest.md`](../verifications/2026-07-22-adr281-symlink-ladetest.md).

| # | Ergebnis | Kurzbeleg |
|---|---|---|
| 1 | ✅ | erscheint im `/`-Menü, sogar **ohne** Neustart (dynamisch nachgeladen) |
| 2 | ✅ | Body inkl. Versions-Marker geladen; `Base directory` = Symlink-Pfad |
| 3 | ✅ | Argument-Echo ein- und mehrwortig korrekt |
| 4 | ✅ | **nach Neufassung** — der ursprüngliche Wortlaut maß den Session-Cache des Harness, nicht den Symlink, und traf für Kopie und Link gleichermaßen zu. Neufassung: *„Ein erstmals geladener Skill löst über den Symlink den aktuellen Dateiinhalt auf."* Diskriminierender Gegentest bestanden. |
| 5 | ✅ | frisch gestartete Session, die den Link **nicht selbst gesetzt** hat: beim Start im Roster, Body + Argument-Echo korrekt |
| 6 | ✅ | `rm` des Links entfernt den Skill; die Quelldatei überlebt unverändert |

### 8.2 Automatisierte Gates nach Phase 2

- `doctor.py --kind skills` prüft **Auflösbarkeit statt Hashes** (§4.2); ein dangling Link
  lässt den Job fehlschlagen.
- Negativtest: ein absichtlich gebrochener Link **muss** rot werden — sonst ist der
  Gate-Name eine Schein-Garantie.
  **Vorgezogen und bestanden am 2026-07-22** (der Test brauchte kein Phase-2-Tooling):
  ein gebrochener Link unter kanonischem Namen wird als `[dangling]` gemeldet. Zwei
  dokumentierte Kanten, beide unkritisch und im Verifikationsartefakt (Nachtrag 3)
  festgehalten: nicht-kanonische Namen erhalten das Etikett `extra` statt `dangling`
  (erkannt, nur falsch benannt), und war der Skill zuvor `fehlend`, bleibt die
  DRIFT-SCORE-Summe gleich, weil ein `fehlend` durch ein `dangling` ersetzt wird.
  Beides ist vor dem **Scharfschalten** des Gates zu bereinigen, blockiert den Accept
  dieses ADR aber nicht — §8.2 ist ein Phase-2-Gate, keine Accept-Vorbedingung.
  **Getrackt als [#1368](https://github.com/achimdehnert/platform/issues/1368)** (Folge von
  #1332/#1335), mit Reproduktion, Code-Ursache und Akzeptanzkriterien. Phase 2 gilt erst als
  erfüllt, wenn #1368 geschlossen ist — insbesondere muss das Gate auf `dangling > 0` aus der
  Befund-Liste triggern, nicht auf die DRIFT-SCORE-Summe.
- Der bisherige Round-Trip-Schritt für die skills-Lane **entfällt**, statt dauergrün
  mitzulaufen.

### 8.3 Rollback-Nachweis — die Lücke nicht wiederholen

ADR-230 hat Rollback zugesagt und nie geprüft (Verifikation 5). Dieses ADR darf denselben
Fehler nicht machen: vor Phase 3 wird **einmal real** durchgespielt, dass ein fehlerhafter
Skill per `git revert` + `git pull` auf allen verlinkten Maschinen zurückgenommen ist, mit
festgehaltener Dauer. Ohne diesen Nachweis bleibt Phase 3 gesperrt.

### 8.4 Kill-Gate — mit Auslöser

- **Owner:** Achim Dehnert.
- **Tracking:** Issue zu diesem ADR, Fälligkeit **2026-12-31**.
- **Maschineller Auslöser:** CI-Job, der ab dem Datum fehlschlägt, solange Phase 3 offen ist.
- **Zusätzlicher Abbruch-Auslöser:** meldet `main-tree-guard.sh report` über 30 Tage einen
  Wert **> 0**, ist die Volatilitäts-Prämisse (Verifikation 4) verletzt — dann zurück auf
  Option C, ohne neue Grundsatzdebatte.
- **Rückfall:** Option C (Kopien). Sie bleibt bis Phase 4 funktionsfähig.

### 8.5 Vorausschauende Wartung

- Der Verifikationsstand trägt Werkzeugversion und Abrufdatum; der Kompatibilitätstest aus
  ADR-280 §8.6 wird um „Symlink-Auflösung" erweitert.
- **Drift-Detector** (ADR-059), Staleness-Schwelle **6 Monate**.
- Frühwarnung: Nimmt der Hersteller die Symlink-Unterstützung zurück, ist §8.1 Kriterium 1
  der erste Punkt, der bricht — und Option C der dokumentierte Rückweg.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — festgehaltene Architektur-Entscheidung mit Begründung und Alternativen |
| **Symlink** | Verweis im Dateisystem, der auf eine andere Datei oder ein anderes Verzeichnis zeigt, statt Inhalt zu duplizieren |
| **Dangling Symlink** | Verweis, dessen Ziel nicht mehr existiert — er sieht vorhanden aus, führt aber ins Leere |
| **Drift** | Auseinanderlaufen von Quelle und installierter Kopie |
| **Pin** | Festlegen auf einen bestimmten, unveränderlichen Stand |
| **Manifest** | Begleitdatei, die festhält, was aus welcher Quelle installiert wurde |
| **Gate** | Automatischer Prüfschritt in der CI, der einen Merge blockieren kann |
| **Worktree** | Zweiter Arbeitsordner desselben Git-Repos, auf einem anderen Stand |

---

## 9. More Information

- **ADR-230** — amendiert: §2.2 „keine Symlinks auf volatilen Checkout". Der Einwand galt
  der Volatilität; sie ist seit ADR-233 nicht mehr gegeben (Verifikation 3/4).
- **ADR-233** — liefert die Voraussetzung: der Haupt-Tree bleibt nachweislich auf `main`.
- **ADR-280** — Lane-Konsolidierung; dieses ADR ist die dort in §10 als Option E getrackte
  Folgeentscheidung.
- **ADR-229** — wollte 2026-05-30 bereits eine „generierte Symlink-Farm" (REC-3/OOTB-5),
  kam nie über `proposed` hinaus und wurde von ADR-230 überstimmt. Dieses ADR greift den
  Gedanken auf, aber mit einer belegten Voraussetzung statt einer Vermutung.
- **Eskalationspfad Option B:** Wird ein echter Installations-Pin gebraucht, ist ein
  *gepflegter* gepinnter Worktree der Weg. Voraussetzung wäre Pflege-Tooling, das heute
  nicht existiert (Verifikation 6).

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-21 | Achim Dehnert | Initial: Status Proposed |
| 2026-07-22 | Achim Dehnert | **Status → Accepted.** Phase 1 (§8.1) vollständig durchgeführt: 6/6, Kriterium 4 in korrigierter Fassung (der ursprüngliche Wortlaut maß den Harness-Cache, nicht den Symlink), Kriterium 5 in einer frischen Session gemessen, die den Link nicht selbst gesetzt hat. Der §8.2-Negativtest wurde vorgezogen und besteht ebenfalls, mit zwei dokumentierten Kanten. Verifikationsstand, Migration-Tracking (Phase 0+1 ✅) und Risiko-Tabelle entsprechend nachgeführt. Artefakt: `docs/verifications/2026-07-22-adr281-symlink-ladetest.md`. Offen bleiben Phase 2–4 sowie der Rollback-Nachweis §8.3. |

---

<!--
  GOVERNANCE-HINWEISE (werden nicht in dev-hub angezeigt):

  Drift-Detector-Felder (ADR-059):
  - staleness_months: 6
  - drift_check_paths:
      - platform/tools/cc-skill-dist
      - platform/skills
  - supersedes_check: true

  Review-Checkliste: /docs/templates/adr-review-checklist.md
  Template-Version: 2.1 (2026-07-10 — ADR-271)
-->
