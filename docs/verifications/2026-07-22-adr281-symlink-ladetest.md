# Verifikation: ADR-281 §8.1 Symlink-Ladetest + ADR-280 §8.1 Betriebsnachweis

**Datum:** 2026-07-22
**Ausführender:** Claude Code (Opus 4.8) in Session auf `dev-desktop`, Owner-Freigabe im Chat
**Werkzeugversion:** `claude --version` = **2.1.217 (Claude Code)**
**Ausgangscommit:** `ef4d190` (`origin/main`, nach Merge von #1295/#1296/#1321)
**Ergebnis in einem Satz:** ADR-281 §8.1 **5 von 6 Kriterien bestanden**, das sechste
(Kriterium 4) ist als Testfall **untauglich formuliert** und misst nicht den Symlink;
ADR-280 §8.1 **konnte nicht beginnen**, weil die migrierten Skills live nicht installiert sind.

---

## Teil A — ADR-281 §8.1: Symlink-Ladetest

### Aufbau

Gemäß §8.1 ein einzelner, von Hand gesetzter Symlink unter einem **noch unbenutzten**
Namen, damit nichts überdeckt wird:

```
~/.claude/skills/adr281-ladetest
  -> <worktree>/skills/adr281-ladetest        (Quelle im Repo-Checkout, Branch session/2026-07-22/…/adr281-ladetest)
```

Der Test-Skill enthält einen Versions-Marker im Body und ein Argument-Echo
(`>>>$ARGUMENTS<<<`), damit Laden und Substitution getrennt beobachtbar sind.

### Ergebnis je Kriterium

| # | Kriterium | Ergebnis | Beobachtung |
|---|---|---|---|
| 1 | Skill erscheint im `/`-Menü | ✅ bestanden | Erschien **ohne Session-Neustart**; die Roster-Aktualisierung kam als `system-reminder` wenige Sekunden nach dem `ln -s`. |
| 2 | Aufruf funktioniert, Body wird geladen | ✅ bestanden | `Skill(adr281-ladetest)` lieferte den Body samt Marker; `Base directory` zeigte auf den Symlink-Pfad. |
| 3 | `$ARGUMENTS` wird korrekt eingesetzt | ✅ bestanden | Einwortig und mehrwortig-gequotet: `>>>hallo welt<<<` bzw. `>>>"mehrwortiges gequotetes argument"<<<`. |
| 4 | Änderung an der Quelldatei wirkt ohne Neustart | ⚠️ **Testfall untauglich** | siehe unten — misst den Harness-Cache, nicht den Symlink. |
| 5 | Verhalten in frisch gestarteter Session | ✅ bestanden (Nachlauf 2026-07-22 19:0x, s. zweiten Nachtrag) | `adr281-k5` stand **beim Start** im Roster, Body inkl. `MARKER-K5-V1` geladen, Argument-Echo korrekt. |
| 6 | Entfernen des Symlinks entfernt den Skill sauber | ✅ bestanden | `rm` des Links entfernte den Eintrag; die **Quelldatei überlebte** unverändert. |

### Kriterium 4 im Detail — warum der Testfall nicht misst, was er soll

Wörtlich ausgeführt **scheitert** Kriterium 4: nach `sed`-Änderung der Quelle von
`MARKER-V1` auf `MARKER-V2` lieferte die Re-Invocation weiterhin **V1**, obwohl die Datei
*über den Symlink gelesen* nachweislich V2 enthielt (`grep MARKER ~/.claude/skills/…` → V2).

Der diskriminierende Gegentest entscheidet die Ursache: ein **zweiter, frischer** Skill-Name
(`adr281-ladetest-b`) auf denselben V2-Inhalt gelegt, lieferte beim ersten Aufruf **sofort
V2**.

**Schlussfolgerung:** Die Symlink-Auflösung ist zu jedem Ladezeitpunkt aktuell. Das
V1-Ergebnis stammt allein aus dem **Session-Cache des Harness** für einen bereits geladenen
Skill (die Re-Invocation wurde ausdrücklich als „skill instructions were previously loaded"
markiert). **Eine generierte Kopie verhielte sich identisch** — Kriterium 4 unterscheidet
Symlink und Kopie also gar nicht und taugt nicht als Entscheidungskriterium zwischen den
Optionen.

**Empfohlene Neufassung für Kriterium 4:**
> Ein **erstmals geladener** Skill löst über den Symlink den *aktuellen* Dateiinhalt auf.
> (Bereits geladene Skills werden pro Session gecacht — das gilt lane-unabhängig und ist
> keine Eigenschaft der Verteilform.)

In dieser Fassung ist Kriterium 4 **bestanden**.

### Nebenbefund 1 — `doctor.py` erkennt einen **dangling** Symlink nicht

ADR-281 §8.2 verlangt: „Negativtest: ein absichtlich gebrochener Link **muss** rot werden —
sonst ist der Gate-Name eine Schein-Garantie."

Real ausgeführt:

```
ln -s /nonexistent/pfad/skill-x ~/.claude/skills/adr281-dangling
python3 tools/cc-skill-dist/doctor.py --kind skills
  → Symlinks ok=0  symlink-stale=0  dangling=0
  → DRIFT-SCORE: 4        (unverändert gegenüber dem Lauf ohne den kaputten Link)
```

Der Zähler `dangling` existiert bereits im Werkzeug, **feuerte aber nicht**; der kaputte
Link blieb für den Doctor unsichtbar und veränderte den DRIFT-SCORE nicht. Der in §8.2
geforderte Negativtest würde heute also **nicht** bestehen. Das ist Phase-2-Arbeit, kein
Blocker für §8.1 — aber es muss vor dem Gate-Scharfschalten behoben sein, sonst trägt der
Gate-Name eine Garantie, die er nicht einlöst.

### Nebenbefund 2 — die Symlink-Klassifikation ist bereits vorhanden

`doctor.py --kind skills` gibt `Symlinks ok= / symlink-stale= / dangling=` aus. Die von
ADR-281 §4.2 geforderte „Auflösbarkeit statt Hashes" ist im Werkzeug also **schon angelegt**
und muss nicht neu gebaut, sondern nur scharf gemacht werden (siehe Nebenbefund 1).

---

## Teil B — ADR-280 §8.1: Betriebsnachweis konnte nicht beginnen

Die sechs Muss-Kriterien beziehen sich auf die drei migrierten Piloten (`next`, `escalate`,
`issues-offen`). Ist-Zustand dieser Maschine:

| Skill | Quelle auf `main` | live in `~/.claude/skills/` | live in `~/.claude/commands/` |
|---|---|---|---|
| `next` | `skills/next/SKILL.md` | **nein** | ja (verwaist) |
| `escalate` | `skills/escalate/SKILL.md` | **nein** | ja (verwaist) |
| `issues-offen` | `skills/issues-offen/SKILL.md` | **nein** | ja (verwaist) |

`doctor.py --kind skills` bestätigt: `fehlend (in Quelle, nicht im Ziel)=3 —
fehlende Skills: escalate, issues-offen, next`.

**Die verwaisten `commands`-Kopien sind aktiv und werden benutzt.** Belegt in dieser Session:
`/issues-offen` und `/next` wurden aufgerufen und lieferten Bodies mit dem Footer
`source=.windsurf/workflows/<name>.md · source_commit=0a5f4992bef6` — ein Quellpfad, den
`main` seit #1290 **nicht mehr enthält**. Es lief also die alte Lane, nicht die migrierte.

**Konsequenz:** ADR-280 §8.1 ist nicht „nicht bestanden", sondern **nicht durchführbar**,
solange die migrierten Skills nicht installiert sind. Der dafür nötige Schritt ist
`generate.py --kind skills --allow-live` — der gegatete Live-Rollout aus ADR-230 §8, dessen
Gate acht offene Checkboxen hat. Er wurde hier **bewusst nicht** ausgeführt (eigener
Owner-Entscheid, verändert die Skill-Installation der Maschine über einen Testfall hinaus).

---

## Entscheid

- **ADR-281:** §8.1 trägt — 5 von 6 Kriterien bestanden, das sechste nach Korrektur der
  Formulierung ebenfalls. **Kein** Anlass für `rejected`. Offen bleibt Kriterium 5
  (frische Session); der Negativtest aus §8.2 (Nebenbefund 1) ist seit #1335 behoben.
  → **Überholt durch den Nachlauf vom 2026-07-22 19:0x: Kriterium 5 ist bestanden,
  §8.1 damit vollständig (6/6, Kriterium 4 in der korrigierten Fassung).**

---

## Nachtrag 2026-07-22 (Session-Start-Session) — Kriterium 5 vorbereitet

Kriterium 5 lässt sich **nicht spontan nachholen**: die frische Session muss den Symlink
bereits beim Start vorfinden, und die Test-Artefakte des Erstlaufs waren bewusst entfernt
worden. Deshalb wurde der Link *vorbereitend* gesetzt statt in einer Session gemessen, die
ihn selbst erzeugt — dieser Selbstwiderspruch war der Grund, warum Kriterium 5 am 22.07.
offen blieb.

```
~/.claude/skills/adr281-k5  ->  ~/shared/adr281-k5      (gesetzt 2026-07-22 16:23)
```

**Abweichung zur Reproduktion oben, bewusst:** Die Quelle liegt außerhalb eines
Repo-Worktrees. Ein Session-Worktree kann vom `worktree-reaper` entfernt werden, bevor die
nächste Session startet; der Link wäre dann tot und das Ergebnis sähe wie ein
**gescheitertes** Kriterium 5 aus, obwohl nur die Quelle fehlt. Für die gemessene
Eigenschaft — löst der Harness einen Verzeichnis-Symlink beim Session-Start auf? — ist die
Herkunft des Ziels ohne Belang; git-Verwaltung des Zielverzeichnisses geht in die Frage
nicht ein.

**Auswertungsregeln** stehen im Body des Testskills selbst (`~/shared/adr281-k5/SKILL.md`),
damit die auswertende Session sie nicht aus diesem Dokument rekonstruieren muss:
bestanden = im `/`-Menü **schon beim Start** vorhanden + Body inkl. `MARKER-K5-V1` geladen +
Argument-Echo korrekt; gescheitert = beim Start abwesend, obwohl `ls -l` einen intakten
Symlink zeigt.

**Aufräumen ist Teil des Tests, nicht Nacharbeit:** `rm ~/.claude/skills/adr281-k5 &&
rm -rf ~/shared/adr281-k5`. Solange der Link liegt, weist `doctor.py --kind skills` ihn als
`extra` aus (nicht in der kanonischen Quelle) und der **DRIFT-SCORE steht auf 4 statt 3** —
verifiziert, erwartet, und ausdrücklich **kein** Drift-Befund. Nebenbeobachtung: `doctor.py`
zählt ihn unter `extra`, nicht unter `Symlinks ok` — die Symlink-Zählung erfasst nur Links
mit kanonischer Quelle.
- **ADR-280:** Betriebsnachweis **weiterhin offen**, Ursache benannt und behebbar. Kein
  Anlass für den Rückfall auf Option D, weil kein Kriterium *geprüft und gescheitert* ist.
- ~~Beide ADRs bleiben damit vorerst auf `status: proposed`.~~ **Überholt:** ADR-281 ist am
  2026-07-22 auf `accepted` gesetzt (Owner-Entscheid, gestützt auf §8.1 6/6 unten).
  ADR-280 bleibt `proposed`.

---

## Nachtrag 2 — 2026-07-22, ~19:06: Kriterium 5 **gemessen und bestanden**

**Messende Session:** frisch gestartet auf `dev-desktop`, `main` @ `a80e02b`,
Werkzeugversion unverändert **2.1.217 (Claude Code)** — der Vergleich zum Erstlauf ist
damit versionsgleich und nicht von einem Harness-Upgrade verfälscht.

Die Session hat den Symlink **nicht selbst gesetzt** (er lag seit 16:23), womit der
Selbstwiderspruch des Erstlaufs aufgelöst ist.

| Auswertungsregel (aus dem Skill-Body) | Beobachtung | Ergebnis |
|---|---|---|
| Skill **schon beim Session-Start** im Roster | `adr281-k5` stand in der Skill-Liste des Session-Starts, vor jeder Dateisystem-Aktion dieser Session | ✅ |
| Body vollständig geladen, inkl. `MARKER-K5-V1` | `Skill(adr281-k5)` lieferte den Body samt Marker; `Base directory: /home/devuser/.claude/skills/adr281-k5` (der Symlink-Pfad) | ✅ |
| Argument-Echo korrekt | `>>>K5-PROBE-2026-07-22-fresh-session<<<` | ✅ |

**Damit ist ADR-281 §8.1 vollständig durchgeprüft: 6/6** (Kriterium 4 in der oben
begründeten Neufassung). Der Erstlauf-Verdacht — Symlinks würden womöglich nur *dynamisch*,
nicht beim Start aufgelöst — ist widerlegt: **beide** Ladewege funktionieren.

**Zustand vor dem Aufräumen** (bestätigt die Vorhersage des ersten Nachtrags exakt):

```
python3 tools/cc-skill-dist/doctor.py --kind skills
  → Symlinks ok=0  symlink-stale=0  dangling=0
  → extra (nicht in Quelle)=1   [extra] adr281-k5
  → DRIFT-SCORE: 4
```

Der Link wurde anschließend gemäß Testprotokoll entfernt
(`rm ~/.claude/skills/adr281-k5 && rm -rf ~/shared/adr281-k5`); der Nachlauf von `doctor.py`
zeigt `extra=0` und **DRIFT-SCORE 3** — der Testaufbau ist rückstandsfrei abgebaut, die
verbleibende 3 sind die drei nicht installierten Piloten aus Teil B (ADR-280), nicht dieser
Test.

**Was das für die ADR-Stände heißt:**

- **ADR-281:** §8.1 ist erledigt. Vor `accepted` bleibt §8.2 — der Negativtest
  (dangling ⇒ rot). **Direkt im Anschluss nachgemessen, siehe Nachtrag 3.**
- **ADR-280:** unverändert offen — der Betriebsnachweis hängt weiter an
  `generate.py --kind skills --allow-live` (Owner-Entscheid, ADR-230 §8).

---

## Nachtrag 3 — 2026-07-22: §8.2 Negativtest nachgemessen — **besteht**, mit zwei Kanten

Ausgeführt gegen `main` @ `a80e02b` (enthält den Fix aus #1335 zu #1332). Zwei Läufe, weil
der erste ein unerwartetes Ergebnis lieferte und die Ursache erst der zweite entscheidet.

| Lauf | Linkname | Klassifikation | Befund-Zeile | DRIFT-SCORE |
|---|---|---|---|---|
| A | `adr281-dangling` (**nicht** kanonisch) | `extra=1`, `dangling=0` | `[extra] adr281-dangling` | 3 → **4** |
| B | `next` (**kanonisch**, war zuvor `fehlend`) | `dangling=1`, `extra=0` | `[dangling] next — Symlink ins Leere → …` | 3 → **3** |

**Ursache, aus dem Code statt geraten** (`tools/cc-skill-dist/doctor.py`): die
`name not in canon`-Prüfung steht **vor** der dangling-Prüfung und beendet die
Klassifikation mit `continue`. Ein gebrochener Link unter einem Namen, den die kanonische
Quelle nicht kennt, erreicht den dangling-Zweig also nie. Genau dieses Zusammenspiel
dokumentiert der Docstring von `enumerate_skills()` bereits — der Fix aus #1332 zielte auf
die *kanonische* Form und tut dort, was er soll.

**Verdikt zu §8.2 („ein absichtlich gebrochener Link **muss** rot werden"):**
**bestanden.** In beiden Läufen erscheint der kaputte Link als Befund und erhöht die
Drift-Zählung — die frühere Beobachtung aus Nebenbefund 1 (`dangling=0`, DRIFT-SCORE
unverändert) ist mit #1335 **erledigt** und nicht mehr reproduzierbar.

**Zwei Kanten, beide dokumentiert, keine davon ein Blocker:**

1. **Falsches Etikett bei nicht-kanonischen Namen** (Lauf A): erkannt wird der Link, aber
   als `extra`, nicht als `dangling`. Für den Drift-Score gleichwertig (beide zählen 1),
   für die Diagnose irreführend. Kosmetisch, sofern niemand auf das Etikett gatet.
2. **Score-Neutralität im Sonderfall** (Lauf B): war der Skill vorher `fehlend`, ersetzt der
   kaputte Link ein `fehlend` durch ein `dangling` — Summe unverändert, hier 3 → 3. Das
   ist ein **Artefakt der Ausgangslage dieser Maschine** (3 nicht installierte
   ADR-280-Piloten), kein allgemeiner Fehler: auf einer Maschine, auf der der Skill korrekt
   installiert ist und der Link *danach* bricht, geht `fehlend` nicht herunter und der Score
   steigt um 1. Relevant nur, wenn ein Gate auf die **Score-Zahl** statt auf die
   Befund-Liste triggert. Der heutige CI-Gate (`.github/workflows/cc-skill-dist-doctor.yml`)
   tut das nicht — er prüft einen frisch generierten Roundtrip-Baum auf Drift 0 und ist von
   dieser Kante nicht betroffen.

Beide Testlinks wurden unmittelbar nach dem Lauf entfernt; `~/.claude/skills/` enthält
danach wieder nur `antwort-modus-schablone`, `MANAGED_BY`, `manifest.json`.

**Stand ADR-281 nach diesem Nachtrag:** §8.1 6/6, §8.2 bestanden. Aus Sicht der in §8
geforderten Nachweise ist der ADR damit accept-reif. **Der Owner hat den Accept am
2026-07-22 erteilt** — `status: accepted`, im selben PR wie dieses Artefakt.
Offen bleiben Phase 2–4 (Tooling, Umstellung, Rückbau) und der Rollback-Nachweis §8.3;
der Accept schaltet sie frei, er ersetzt sie nicht.

## Reproduktion

```bash
# Aufbau
WT=<worktree>
mkdir -p "$WT/skills/adr281-ladetest" && $EDITOR "$WT/skills/adr281-ladetest/SKILL.md"
ln -s "$WT/skills/adr281-ladetest" ~/.claude/skills/adr281-ladetest

# Kriterien 1-3: Skill aufrufen, Argument-Echo prüfen
# Kriterium 4: Quelle ändern, DANN unter frischem Namen erneut verlinken (Cache umgehen)
# Kriterium 6: rm ~/.claude/skills/adr281-ladetest

# Negativtest §8.2
ln -s /nonexistent ~/.claude/skills/adr281-dangling
python3 tools/cc-skill-dist/doctor.py --kind skills   # erwartet: dangling>0 — real: 0
```
