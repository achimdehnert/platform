# Verifikation: ADR-280 §8.1 Betriebsnachweis der migrierten Skills

**Datum:** 2026-07-23
**Ausführender:** Claude Code (Opus 4.8), Session `4bacc290` auf `dev-desktop`
**Werkzeugversion:** `claude --version` = **2.1.218 (Claude Code)**
**Ausgangscommit:** `9371148` (`origin/main`)
**Installationsstand:** Skills-Lane live installiert am **2026-07-23 06:14:08 UTC** durch
Parallel-Session `2f30b5aa` (`generate.py --kind skills --allow-live`, Owner-Freigabe im
Chat) — `manifest.json` weist `source_commit=9371148`, `target_type=copy`, `skill_count=4`.

**Ergebnis in einem Satz:** **5 von 6 Muss-Kriterien gemessen und bestanden**; Kriterium 6
(neu gestartete Session) ist konstruktionsbedingt erst in der **nächsten** Session messbar —
damit steht noch **kein** Entscheid „A bestanden", aber auch **kein** Fallback-D-Auslöser,
weil kein Kriterium *geprüft und gescheitert* ist.

---

## Ausgangslage

Der Handover vom 2026-07-22 führte §8.1 als **nicht durchführbar**: die drei migrierten
Piloten (`next`, `escalate`, `issues-offen`) waren live nicht installiert, es lief die
verwaiste `commands`-Lane. Diese Blockade ist seit dem Live-Rollout weg. Gegenprobe:

```
python3 tools/cc-skill-dist/doctor.py --kind skills
  Ziel /home/devuser/.claude/skills: 4 Einträge
  Kopien fresh=4  copy-stale=0
  extra=0  fehlend=0   Hybrid? nein
  DRIFT-SCORE: 0   DANGLING: 0
```

Die verwaisten `commands`-Kopien (`next.md`, `escalate.md`, `issues-offen.md`) sind
**nicht mehr vorhanden** — es besteht also keine Lane-Dublette, die die Messung
verfälschen könnte. Das ist der entscheidende Unterschied zum Vortag: damals hätte ein
Aufruf nicht eindeutig einer Lane zugeordnet werden können.

## Ergebnis je Kriterium

| # | Kriterium (ADR-280 §8.1) | Ergebnis | Beobachtung |
|---|---|---|---|
| 1 | Skill erscheint im `/`-Menü unter unverändertem Namen | ✅ bestanden | `next`, `escalate`, `issues-offen`, `antwort-modus-schablone` im Roster dieser Session, Namen unverändert. Einschränkung s.u. |
| 2 | Aufruf **ohne** Argument verhält sich wie vorher | ✅ bestanden | `Skill(escalate)` lieferte den vollständigen Body; `Base directory: /home/devuser/.claude/skills/escalate`. |
| 3 | **Einwortiges** Argument an der `$ARGUMENTS`-Stelle | ✅ bestanden | `Skill(issues-offen, "platform")` → beide Substitutionsstellen ersetzt (`` `platform`: `` und `Repo bestimmen: `platform` → `<repo>``). |
| 4 | **Mehrwortiges, gequotetes** Argument ebenso | ✅ bestanden | `"org:achimdehnert repo:platform,dev-hub"` wörtlich eingesetzt — **inklusive** der Anführungszeichen (Nebenbefund 2). |
| 5 | Beschreibung gelistet, Body lädt **erst beim Aufruf** | ✅ bestanden | Roster zeigt nur die `description:` aus dem Frontmatter; der Body erschien erst mit dem `Skill(...)`-Aufruf. |
| 6 | Verhalten in einer **neu gestarteten** Session | ⏳ offen | Diese Session startete **06:13:56**, die Installation endete **06:14:08** — der Session-Start liegt 12 s *vor* dem Rollout. Nicht nachholbar, s.u. |

**Lane-Beweis für die Kriterien 2–4:** jeder geladene Body trug den Footer
`MANAGED-BY: platform/tools/cc-skill-dist · source=skills/<name>/SKILL.md ·
source_commit=9371148f567d`. Die alte Lane trug an derselben Stelle
`source=.windsurf/workflows/<name>.md · source_commit=0a5f4992bef6` — die Herkunft ist
also nicht erschlossen, sondern am Artefakt selbst ablesbar.

### Einschränkung zu Kriterium 1 — bewusst benannt statt übergangen

Das Roster **dieser** Session wurde 12 Sekunden vor Abschluss der Installation aufgebaut,
als die gleichnamigen `commands`-Kopien noch existierten. Für die reinen Namen ist das
folgenlos (beide Lanes verwenden dieselben), aber es beweist nicht, dass der
*Menü-Eintrag beim Start* aus der Skills-Lane kam. Der Aufruf tat es nachweislich
(Base directory + Footer). Kriterium 6 schließt genau diese Lücke — es ist damit nicht
nur formal, sondern inhaltlich der letzte offene Punkt.

### Warum Kriterium 6 nicht nachholbar ist

Dieselbe Struktur wie bei ADR-281 Kriterium 5: eine laufende Session kann ihren eigenen
Startzustand nicht rückwirkend herstellen. **Anders als dort ist jedoch keine
Vorbereitung nötig** — die Installation ist persistent, es braucht nur den nächsten
Session-Start. Auszuführen von der nächsten Session:

1. Vor jeder Dateisystem-Aktion prüfen, ob `next`, `escalate`, `issues-offen`,
   `antwort-modus-schablone` **schon beim Start** im `/`-Menü stehen.
2. Einen davon aufrufen und den Footer gegen `source=skills/<name>/SKILL.md` halten.
3. Ergebnis in der Tabelle oben nachtragen; bei ✅ ist §8.1 **6/6** und der Entscheid
   „**A bestanden**" fällig (ADR-280 von `proposed` auf `accepted`).

Scheitert Schritt 1 oder 2, gilt laut §8.1 ohne neue Grundsatzdebatte **Option D** —
dann gehört das ebenfalls hier hinein, nicht in eine Chat-Notiz.

## Testabdeckung — Restlücke benannt

Gemessen wurde an **2 von 3** migrierten Piloten (`escalate` für Kriterium 2,
`issues-offen` für 3+4). `next` wurde **nicht** invoziert: derselbe Lademechanismus ist
zweimal unabhängig belegt, und `next` ist der einzige Pilot mit einem — wenn auch
idempotenten — Seiteneffekt (`claude-next-sync` regeneriert `NEXT.md`). Billigster
Nachtest, falls gewünscht: `Skill(next)` aufrufen und den Footer prüfen.

`antwort-modus-schablone` ist kein Slash-Aufruf, sondern trigger-wortgesteuert
(`#antwort_modus_schablone`) — die Kriterien 2–4 sind darauf nicht anwendbar.

**Ebenfalls nicht ausgeführt (bewusst):** die Triage-Workflows selbst. Die Aufrufe von
`issues-offen` waren Substitutionsmessungen; Phase 1–4 des Skills wurden nicht gestartet.
Ein Skill-Body ist eine Anweisung an das Modell, kein autonom startender Prozess — der
Ladetest ist damit vom Ausführen trennbar.

## Nebenbefund 1 — §8.3 Mengenidentität ist erfüllt, aber nicht gegatet

Die Namensmenge stimmt vor/nach dem Rollout überein (4 kanonisch = 4 installiert,
`extra=0`, `fehlend=0`, `Hybrid? nein`). Das ist der von §8.3 geforderte Zustand, aber
`doctor.py` prüft ihn **je Lane**, nicht lane-übergreifend: die von §8.3 verlangte
Fehlschlag-Bedingung „lane-übergreifende Duplikate" wäre in dem Moment, als beide Lanes
`next` trugen, nicht gefeuert. Aktuell folgenlos (die `commands`-Leichen sind weg), vor
dem Scharfschalten des Gates aber zu schließen — sonst gilt dieselbe Kritik wie beim
dangling-Befund aus ADR-281 §8.2: ein Gate-Name, der eine Garantie trägt, die er nicht
einlöst.

## Nebenbefund 2 — `$ARGUMENTS` behält die Anführungszeichen

Bei mehrwortiger Übergabe wird der **rohe** Argumentstring eingesetzt, Quotes inklusive:
`$ARGUMENTS` → `"org:achimdehnert repo:platform,dev-hub"`. Ein Skill, der daraus einen
Bezeichner ableitet, muss sie selbst strippen. `issues-offen` Step 0.1 („Repo bestimmen:
`$ARGUMENTS` → `<repo>`") liefe mit Quotes auf einen Repo-Namen `"platform` — praktisch
irrelevant, weil die dokumentierte Aufrufform ohne Quotes auskommt
(`/issues-offen org:<org> repo:<r1>,<r2>`), aber es ist eine Eigenschaft der
Substitution, keine des Skills. Deckungsgleich mit der Beobachtung aus dem
ADR-281-Ladetest (`>>>"mehrwortiges gequotetes argument"<<<`) — also stabil über zwei
Werkzeugversionen (2.1.217 → 2.1.218) und beide Verteilformen.

## Entscheid

- **ADR-280 bleibt vorerst `status: proposed`.** §8.1 steht auf **5/6**; der Entscheid
  „A bestanden" ist an Kriterium 6 gebunden und wird von der nächsten Session gefällt.
- **Kein Fallback D.** Kein Kriterium wurde geprüft und gescheitert.
- **Phase 4** (Entfernen der `commands`-Lane) ist von diesem Nachweis unberührt und
  weiterhin über [#1287](https://github.com/achimdehnert/platform/issues/1287) gegatet.

## Reproduktion

```bash
python3 tools/cc-skill-dist/doctor.py --kind skills     # erwartet: DRIFT-SCORE 0, Hybrid? nein
tail -1 ~/.claude/skills/next/SKILL.md                  # erwartet: source=skills/next/SKILL.md
ls ~/.claude/commands/ | grep -E '^(next|escalate|issues-offen)\.md$'   # erwartet: leer
# Kriterien 2-4: Skill(escalate) · Skill(issues-offen, "platform") ·
#                Skill(issues-offen, "\"org:<org> repo:<a>,<b>\"")
```
