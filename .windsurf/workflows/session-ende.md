---
description: Session beenden — Wissen sichern (via /knowledge-capture), Memory updaten, Repos committen/pushen
mode: write
---

# /session-ende

> Gegenstück: `/session-start`
> **Der User muss NICHTS auflisten.** Der Agent scannt die Session autonom.
> **Läuft in Claude Code** (CC-first, ADR-230) — Tools werden mit ihren
> stabilen CC-Namen (`mcp__github__*`, `mcp__orchestrator__*`) genannt, nicht
> mit volatilen `mcpN_`-Nummern. Owner/Org werden aus dem git-Remote abgeleitet,
> nie hardcoded (policies/claude-skills.md).

---

## Platform Sync Loop (Prinzip)

```
Session Start:  GitHub ──pull──▶ platform ──sync──▶ alle Repos  (aktuell starten)
Session Ende:   Änderungen ──commit──▶ push ──▶ GitHub ──sync──▶ alle Repos  (sofort deployen)
```

> **Jede Verbesserung an Workflows, Rules oder Scripts landet nach der Session
> automatisch platform-weit in ALLEN Repos — beim nächsten Session-Start.**
> GitHub ist die einzige Source of Truth. Lokale Pfade sind irrelevant.

---

## Phase −0.1: Version-Banner (allererster Schritt)

// turbo
```bash
# GITHUB_DIR sicherstellen (analog session-start)
if ! grep -q "GITHUB_DIR" ~/.bashrc 2>/dev/null; then
  echo "" >> ~/.bashrc
  echo "export GITHUB_DIR=\"\$HOME/github\"" >> ~/.bashrc
  echo "⚙️  GITHUB_DIR in ~/.bashrc eingetragen"
fi
export GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"

PLATFORM_DIR="${GITHUB_DIR}/platform"
VERSION_BEFORE=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_BEFORE=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
echo ""
echo "┌─────────────────────────────────────────┐"
echo "│  🏁 SESSION ENDE                        │"
echo "│  Platform v${VERSION_BEFORE} (${COMMIT_BEFORE})        │"
echo "│  $(date '+%Y-%m-%d %H:%M')                       │"
echo "└─────────────────────────────────────────┘"
```

---

## Phase 0: Blockierte Arbeit dokumentieren + AGENT_HANDOVER aktualisieren

### 0a: Blockierte Arbeit (Lesson 2026-04-05)

Falls während der Session Arbeit blockiert wurde (Shell-Hang, MCP-Fehler, Token-Probleme):

```
Prüfe:
1. Gibt es .fixed / .updated / .new Dateien die noch nicht übernommen wurden?
2. Gibt es unbeantwortete Fragen an den User?
3. Gibt es CI/CD Runs die noch verifiziert werden müssen?

Falls ja: Explizit als TODO dokumentieren mit konkretem Befehl zur Übernahme.
```

> Lesson Learned: Wenn Tools blockiert sind, ist es besser die Lösung in einer
> .fixed-Datei zu hinterlegen als die Session ergebnislos zu beenden.

### 0a-deploy: Deploy-Status der gemergten Code-/Migration-PRs prüfen (PFLICHT)

> **Lesson 2026-06-22 (trading-hub Retro, Längsschnitt `deploy-failures-no-fix` ×2):**
> Eine Session mergte den B1(b)-Fix, der Prod-Deploy scheiterte an transientem GHCR-403
> (Build-Step, vor Migrate) — `/session-ende` meldete „alles grün", weil der Deploy-Status
> nie geprüft wurde. Die Kern-Errungenschaft war nicht live. „main grün" ≠ „Prod aktuell".

Für **jedes** Repo dieser Session, das Code/Migrationen (nicht nur Docs) auf `main` gemergt hat:

```bash
# letzten Deploy-Run prüfen (Owner/Repo aus git-Remote, nicht hardcoden)
gh run list --repo <owner>/<repo> --workflow=Deploy --limit 1 \
  --json conclusion,headSha,databaseId -q '.[] | "\(.conclusion) sha=\(.headSha[0:7]) id=\(.databaseId)"'
```

- `success` → ok, weiter.
- `failure` → **nicht** als „fertig" melden. Entweder: (a) bei transientem Flake (GHCR-403/registry-unauthorized beim Pull, siehe Memory `*-deploy-smoke-unauthorized`) `gh run rerun <id> --failed` und Erfolg verifizieren; ODER (b) explizit als offenes To-do mit Run-ID ins `AGENT_HANDOVER.md` (Phase 0b).
- kein Deploy-Workflow im Repo → Schritt entfällt.

### 0a-handover-pr: Offene AGENT_HANDOVER.md-PRs gegenchecken (PFLICHT — NEU 2026-07-14)

> **Lesson 2026-07-14:** Eine Session öffnete einen PR mit neuem Handover-Stand,
> ließ ihn aber offen (kein Merge). Die nächste Session schrieb — ohne diesen Check —
> einen **zweiten**, konkurrierenden Handover-Stand, der den ersten PR sofort veraltete.
> Der User musste die Duplikat-PR manuell entdecken und schließen lassen. Ein einfacher
> PR-Suchlauf vor dem Schreiben hätte das verhindert.

Bevor `AGENT_HANDOVER.md` in dieser Session verändert wird:

```bash
gh pr list --repo <owner>/<repo> --search "AGENT_HANDOVER.md in:body" --state open \
  --json number,title,updatedAt -q '.[] | "\(.number)\t\(.updatedAt[:10])\t\(.title)"'
# Fallback falls die Suche nichts findet (Titel/Body nennen die Datei nicht explizit):
gh pr list --repo <owner>/<repo> --state open --json number,title,files \
  -q '.[] | select(.files[]?.path == "AGENT_HANDOVER.md") | "\(.number)\t\(.title)"'
```

- **Treffer gefunden** → NICHT blind einen neuen Stand parallel schreiben. Entweder
  (a) den bestehenden PR-Branch übernehmen/aktualisieren statt einen neuen zu öffnen,
  oder (b) falls der bestehende PR durch zwischenzeitliche Merges bereits veraltet ist,
  ihn explizit als „ersetzt durch PR #N" schließen, **bevor** der neue Stand gepusht wird.
- **Kein Treffer** → normal weiter mit 0b.

### 0a-merge: Den eigenen Handover-PR selbst mergen (PFLICHT — NEU 2026-08-10, Owner-Weisung)

> **Ein Handover-PR ist ein Bericht über bereits Geschehenes, keine Entscheidung.** Der
> Owner kann ihm nichts zustimmen, was nicht ohnehin schon passiert ist — und sein Inhalt
> wird beim nächsten `/session-start` wieder eingelesen. Ihn zur Freigabe vorzulegen
> verzögert genau die Information, für die er existiert, und erzeugt die Lage, gegen die
> Phase 0a-handover-pr geschrieben wurde: zwei konkurrierende Stände nebeneinander
> (Realfall 2026-07-14). Owner-Weisung 2026-08-10 (illustration-hub PR #197).

Sobald der Handover-PR grün ist, **ohne Rückfrage mergen** und das Ergebnis im
Abschlussbericht nennen:

```bash
gh pr merge <N> --squash --delete-branch     # CI grün? -> direkt
gh pr merge <N> --squash --delete-branch --auto   # CI läuft noch -> Auto-Merge scharf
```

**Grenzen — hier gilt die Weisung NICHT, dann bleibt es bei der Vorlage:**

| Bedingung | Warum |
|---|---|
| Der PR enthält mehr als Dokumentation | Code/Konfiguration ist eine Entscheidung, kein Bericht |
| ADR-Statuswechsel (`implementation_status`) im selben PR | Das ist eine Aussage über Wirklichkeit, kein Protokoll |
| Repo mit Auto-Deploy-on-`main` | Der Merge IST dort der Prod-Schritt → Gate 2 |
| CI rot oder Required Checks fehlen | Grün ist die Bedingung, nicht die Formalie |

→ Trifft eine Grenze zu: PR offen lassen, im Abschlussbericht **mit Grund** nennen.

### 0a-freshness: Handover-Rezenz erzwingen (PFLICHT — NEU 2026-08-02, Welle 1 KONZ-038, Issue #1457)

> **Warum als Skill-Gate:** Das CI-Gate (`handoff-banner-gate.yml`) läuft nur, wenn
> `AGENT_HANDOVER.md` im PR IST — der ×12-Verstoß (`handover-stale-vor-merge`) ist aber
> gerade, sie NICHT anzufassen. Ein paths-gefiltertes Gate kann diese Klasse strukturell
> nicht sehen; der Prozess-Schritt hier kann es (Vier-Wege-Prüfung KONZ-038 §5.7: Ablauf
> statt N-ter Regel).

Nach dem Aktualisieren von `AGENT_HANDOVER.md` (bzw. der bewussten Entscheidung, es
nicht zu tun) den vorhandenen Prüfer scharf laufen lassen:

```bash
python3 scripts/checks/agent_handover_freshness_check.py AGENT_HANDOVER.md
```

- **Exit 0** → frisch, weiter.
- **Exit 1** → die Datei trägt einen älteren Stand als ihr letzter Commit erwarten lässt:
  Stand-Abschnitt JETZT nachziehen (Datum + Prio-Zeilen), dann erneut prüfen. Ein
  „bewusst nicht aktualisiert, weil X" ist zulässig, gehört dann aber als Satz in den
  Commit-/PR-Text — stillschweigend stale mergen ist der ×12-Verstoß.

### 0b: AGENT_HANDOVER.md aktualisieren (PFLICHT bei WIP-Stand)

Falls uncommitted changes, offene Tasks oder abgebrochene Implementierungen existieren:

```bash
# Welche Repos haben uncommitted changes?
for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
  status=$(cd "$repo" && git status --porcelain 2>/dev/null)
  [ -n "$status" ] && echo "DIRTY: $(basename $repo)"
done
```

Für **jedes dirty Repo** das ein `docs/AGENT_HANDOVER.md` hat → Abschnitt **"⚡ Aktueller Stand"** aktualisieren:

```markdown
## ⚡ Aktueller Stand (<DATUM>)

**Aktiver Branch:** `<branch>`

**Was wurde implementiert:**
- <Datei> — <1-Zeile was geändert/neu>

**Uncommitted Changes:**
- <git status --short Ausgabe>

**Nächster Schritt:**
<konkreter nächster Schritt, copy-pasteable Befehle>

**Session Resume (falls verfügbar):**
claude --resume <session-id>
```

→ Dann `git add docs/AGENT_HANDOVER.md && git commit -m "chore: update AGENT_HANDOVER"`
→ Wird von `session-start Phase 1` automatisch gelesen: *"Repo-Kontext laden — AGENT_HANDOVER.md"*

> **Zwei Ziele, zwei Regeln (NEU 2026-07-22, KONZ-027 Arm A / Pilot #1302, platform-lokal):**
>
> - **`AGENT_HANDOVER_LOG.md`** — der Session-Stand kommt als **neuer Block ans Ende**.
>   Bestehende Einträge nie ändern, auch Korrekturen nur als neuer Eintrag darunter.
>   Diese Datei trägt `merge=union`, damit zwei parallele Sessions gleichzeitig anhängen
>   können. Der CI-Check `handover-append-only` blockt Verstöße.
> - **`AGENT_HANDOVER.md`** — Prio-Tabelle und laufender Stand, hier wird wie bisher
>   **umgeschrieben** (Phase 0c unten verlangt genau das). Kein `merge=union`, Konflikte
>   bleiben laut und werden von Hand aufgelöst.
>
> **Was Arm A leistet und was nicht** (gemessen 2026-07-22, Beleg im Kommentar an #1319):
> GitHub wendet `merge=union` **serverseitig nicht** an — ein zweiter PR bleibt
> `CONFLICTING`, auch "Update branch" hilft nicht. Der Gewinn liegt allein in der
> **lokalen** Auflösung: `git pull` im Worktree führt beide Stände still zusammen, danach
> genügt ein Push. Aus "von Hand auflösen" wird "pullen und pushen" — mehr nicht.
> Widersprüche (z.B. zwei "Stand: fertig"-Zeilen) bleiben bewusst als Doppelzeilen stehen
> (dumb-but-robust); das ist der Trade-off dieses Arms, kein Bug.

### 0c: Erledigte/verschobene Prioritäten im Handover nachziehen (PFLICHT — NEU 2026-06-24)

> **Unabhängig von WIP** (Phase 0b feuert nur bei uncommitted Stand — eine
> *abgeschlossene* Prio hinterlässt aber oft gar keine dirty Files und fiel
> bisher durchs Raster). Lesson 2026-06-24 (iil-klickdummy): siehe
> session-start Phase 2.6.

Falls diese Session eine Aufgabe aus der `## Prioritäten`-Tabelle des
`AGENT_HANDOVER.md` **erledigt oder verschoben** hat:

1. Tabelle aktualisieren — erledigte Zeile entfernen, Rest neu nummerieren, und
   eine `> **Erledigt <Datum>:** …`-Notiz unter die Tabelle setzen; zusätzlich
   einen Stichpunkt in `## ⚡ Aktueller Stand`.
2. **Beides aktualisieren — Handover UND Memory (Phase 2), nie nur eins.**
   Cross-Host-Sessions (iPad/claude.ai) updaten typischerweise nur das geteilte
   pgvector-Memory → der git-getrackte Handover driftet. Der Start-seitige
   Drift-Guard (`session-start` Phase 2.6) fängt nur, was beide Quellen abgleicht.

### 0d: Abnahme gegen den Session-Zielzustand + SA-4-Zähler (PFLICHT — NEU 2026-08-07, Zielzustand-Loop)

> Gegenstück zu `session-start` Phase 2.7. Abnahme heißt: gegen den **akzeptierten
> Zielzustand** prüfen, nicht gegen die Liste erledigter Schritte
> (`policies/zielzustand.md` Pkt. 4). Und: SA-4 ist eine Konvention mit Ratsche —
> ohne Messstelle driftet sie (`feedback_canon_decision_needs_enforcement_gate`);
> diese Phase IST die Messstelle.

1. **Abnahme:** Für den in 2.7 geklärten Zielzustand genau einen Ausgang festhalten
   (im Stand-Block des Handovers): **erreicht** (Kriterien einzeln verifiziert, nicht
   pauschal) · **nicht erreicht** (mit dem konkret fehlenden Kriterium) ·
   **verschoben** (nur mit Tracking-Artefakt im selben Zug). Sessions, die 2.7
   begründet übersprungen haben, schreiben „Zielzustand: n/a (begründet)".
2. **SA-4-Zähler** (nur wenn SA-4 ratifiziert und benutzt/benutzbar war), eine Zeile
   im Stand-Block: `SA-4: <n> Anwendungen · <m> Einzel-OK trotz Klassen-Deckung ·
   <f> Fehlanwendungen`. `f > 0` → SA-4 fällt laut Ratsche auf Einzelfreigabe zurück:
   sofort als Befund melden, nicht nur zählen. `m` speist den Kill-Test (Signal G,
   >30 % → Klasse überarbeiten/streichen) — Auswertung im Regel-Ritual (KONZ-038).

### 0e: Clear-Härte — was überlebt den Kontext-Verlust? (PFLICHT — NEU 2026-08-12)

> **Der Skill räumt Flüchtiges weg (3.1b, 3.1c) und fragt nirgends, ob dort etwas
> Dauerhaftes liegt.** Belegt am 2026-08-12 (illustration-hub): `grep -ic` findet in diesem
> Dokument 36× „handover" und 16× „worktree", aber **0×** „clear" und 0× irgendeine
> Formulierung für flüchtigen Gesprächskontext — die Null ist die Welt, nicht der Filter.

Nach dem Handover-Block, **vor** Phase 1, drei Fragen stellen. Jede mit „ja" beantwortete
Zeile bekommt im selben Zug ein dauerhaftes Artefakt (Issue-Kommentar, Handover-Zeile,
Memory-Datei) — „steht im Gesprächsverlauf" zählt so wenig wie „steht im PR-Text".

| # | Frage | Fix, falls ja |
|---|-------|---------------|
| 1 | Existiert eine **Entscheidung, ein Textvorschlag oder ein Messwert** nur im Gesprächsverlauf? | In das zugehörige Issue / den Handover schreiben |
| 2 | Liegt etwas Dauerhaftes im **Scratchpad / `/tmp`**, das 3.1b gleich wegräumt? | Vorher an einen dauerhaften Ort — Issue-Kommentar oder Repo |
| 3 | Verweist ein **dauerhaftes Dokument auf Flüchtiges** („siehe Sitzungsprotokoll", „wie oben besprochen", ein `/tmp`-Pfad)? | Verweis durch den Inhalt oder einen echten Link ersetzen |

**Frage 3 ist die gefährlichste**, weil sie als einzige nicht auffällt: das Dokument
*sieht* vollständig aus. Der Realfall, der diese Phase auslöste: ein frisch geschriebener
Handover verwies auf „das Sitzungsprotokoll", also auf den Chat, und eine Datensicherung
(alte Kanon-Texte vor einer Produktionsdaten-Änderung, ausdrücklich als Rückweg gefordert)
lag ausschließlich im Session-Scratchpad — den Phase 3.1b gelöscht hätte. Beides fiel erst
auf, als der Owner „also /clear?" fragte, nachdem die Session bereits zweimal als
„sauber geschlossen" gemeldet worden war.

**Kein automatisches `/clear` einbauen.** Das ist ein CLI-Builtin, kein Skill-Schritt; und
es zu automatisieren beschleunigt den Verlust, statt ihn zu verhindern. Der Wert steckt in
der Frage, nicht im Befehl.

**Der Selbsttest in einem Satz:** nicht „ist alles gemergt?" fragen — das beantwortet eine
andere Frage —, sondern **„was verschwindet, wenn dieses Fenster zugeht?"**

---

### 0g: Fremder Blick auf 0d und 0e (PFLICHT ab `full` — NEU 2026-08-17, Owner-Freigabe)

> **Zwei Phasen dieses Skills sind Selbstbeurteilung, und genau dafür hat `/session-retro`
> die Regel „Richter ≠ Angeklagter".** In 0d beurteile ich, ob ich mein eigenes Ziel
> erreicht habe; in 0e, was von meinem eigenen Kontext verschwindet. Beides ist strukturell
> voreingenommen: die Restmenge definiere ich selbst, und was nur im Gesprächsverlauf lebt,
> **fühlt sich für mich vorhanden an**. Realfall 2026-08-17 (`37e8e0`): „Zielzustand
> erreicht, mit benannter Restmenge" — Restmenge von mir gesetzt, niemand gegengelesen;
> derselbe Retro musste `refuted_rate 0.00` ausweisen, weil Falsifikation nicht lief.

**Right-Sizing zuerst — dieselbe Logik wie `/session-retro` Phase 0:**

| Footprint | Regel |
|---|---|
| **lean** (1 Repo, ≤2 PRs, kein Prod/Migration/Publish) | **überspringen** — die Selbstabnahme ist billig nachprüfbar, der Schaden klein |
| **full / deep** (≥3 Repos ODER Prod/Publish ODER Migration) | **zwei Subagenten**, eng geführt |

**Kosten, damit die Entscheidung bewusst fällt:** ~55k Token je eng geführtem Agenten
(gemessen, `/session-retro` Phase 0), also **~110k je Sitzungsende** dieser Klasse. Das ist
kein Rundungsfehler — deshalb der Footprint-Schalter statt „immer".

**Agent 1 — Abnahme (zu 0d).** Bekommt **nur** den Zielzustand (Issue/ADR/KONZ-Text) und die
Artefakte (PRs, CI-Läufe, Dateien), **nicht** meine Erzählung und **nicht** meinen
Abnahme-Entwurf. Auftrag wörtlich: *„Ist jedes Akzeptanzkriterium erfüllt? Antworte je
Kriterium mit ERFÜLLT / NICHT ERFÜLLT / NICHT PRÜFBAR und nenne den Beleg. Du lieferst NUR
Text zurück — keine Dateien, Commits, PRs."* Weicht sein Urteil von meinem ab, gewinnt
**seins** im Stand-Block; meine abweichende Sicht kommt als Satz daneben, nicht an seine Stelle.

**Agent 2 — Clear-Härte (zu 0e).** Bekommt **ausschließlich die durablen Artefakte**
(Handover, Issues, Memory-Einträge, Repo-Dateien) und die drei Fragen aus 0e. Auftrag:
*„Welche Entscheidung, welcher Messwert, welcher Textvorschlag ist in diesen Dokumenten
NICHT auffindbar, wird aber vorausgesetzt? Wo verweist ein dauerhaftes Dokument auf
Flüchtiges?"* Er darf den Gesprächsverlauf **nicht** sehen — das ist der ganze Punkt.

**Beide Ergebnisse landen im Stand-Block**, auch wenn sie unbequem sind. Ein Agent, dessen
Befund nur im Chat bleibt, ist genau der Fehler, gegen den 0e geschrieben wurde.

**Wenn Subagenten in der Umgebung untersagt sind:** 0d/0e inline machen wie bisher, aber
den Regel-1-Bruch **im Stand-Block benennen** (ein Satz: „Abnahme ohne fremden Blick") —
nicht stillschweigend als geprüft ausgeben.

---

### 0f: Cross-Repo-Befunde ins Zielrepo bringen (PFLICHT — NEU 2026-08-16, platform#2004)

> **Der Befund über ein fremdes Repo bleibt sonst als Prosa in diesem Repo liegen.**
> Gemessen am 2026-08-16: fünf offene `[deploy-health]`-Issues — apo-hub (10 Tage),
> trading-hub (10 Tage), travel-beat, cad-hub, tax-hub — **alle im Repo `platform`**,
> alle über andere Repos, **keins bearbeitet**. Der Melder war zuverlässig; ein Leser
> fehlte. Dieselbe Klasse wie 🌀 `melder-ohne-leser`.

Der Session-Start-Runner schreibt jeden Befund mit seinem **Zielrepo** ins Journal
(`tools/befund_journal.py`). Hier wird abgefragt, ob die Fremd-Repo-Befunde einen
Landeplatz haben:

```bash
python3 "${GITHUB_DIR:-$HOME/github}/platform/tools/befund_journal.py" \
  --offen-cross-repo --repo "$TARGET_REPO"
```

- **Exit 0** — nichts offen, weiter.
- **Exit 1** — je genanntem Befund **einen** der beiden Wege gehen, nicht keinen:

  | Weg | Wann | Kommando |
  |---|---|---|
  | Verankern | Der Befund gehört repariert | Issue **im Zielrepo** anlegen, dann `--verankert '<ID>' '<URL>'` |
  | Verzicht | Bewusst nicht verfolgen | `--verzichtet '<ID>' '<Grund>'` — ohne Grund zählt es nicht |

**Das Issue gehört ins Zielrepo, nicht hierher.** Ein roter Deploy in `cad-hub` wird von
jemandem repariert, der in `cad-hub` arbeitet — ein Issue in `platform` erreicht diese
Person nie. Genau daran sind die fünf Alt-Issues gescheitert.

**Fremdes Repo = Scope-Checkpoint.** Ein Issue in einem dritten Repo anzulegen ist ein
Schreibzugriff nach außen; bei mehr als zwei betroffenen Repos oder bei einer fremden Org
(`meiki-lra`, `ttz-lif`, `iilgmbh`) vorher den Owner fragen, nicht im Durchlauf erledigen.

**Warum das Gate eng ist:** es greift nur für Phasen aus `CROSS_REPO_PHASEN` (aktuell
`0.7 deploy-scan`). Der erste scharfe Lauf hätte sonst auch `0.4 repo-sync ·
risk-hub:GUARD(dirty)` eingefordert — ein **lokaler** Zustand des Arbeitsbaums, für den
ein Issue in `risk-hub` Unsinn wäre. Die Liste wächst durch Belege: eine Phase kommt dazu,
wenn ein konkreter Befund von ihr in einem fremden Repo repariert werden musste.

---

## Phase 1: Wissen sichern — an `/knowledge-capture` delegieren

Outline-Schreiben **nicht hier inline duplizieren** — Klassifikation
(Runbook/Konzept/Lesson), Cross-Repo-Tagging und die Outline-Tool-Wahl sind
Aufgabe von `/knowledge-capture`. session-ende ruft es und **prüft den Erfolg**:

1. `/knowledge-capture` ausführen (autonomer Session-Scan → schreibt nach Outline).
2. **Erfolgs-Check** (nicht stumm überspringen):
   - Hat es eine Outline-Doc-URL/ID zurückgegeben? → für Phase 2 (Memory-Cross-Ref) merken.
   - Kein Ergebnis / Fehler? → als offenen Punkt in `AGENT_HANDOVER.md` (Phase 0b)
     notieren, damit die nächste Session es nachholt.

→ session-ende-eigen bleibt nur der **Memory-Eintrag** (Phase 2, Verweis auf die
Outline-Doc). Die früher hier duplizierte Outline-Logik wurde entfernt (war
redundant zu `/knowledge-capture` und `/session-docu`).

---

## Phase 1b: Docu-Drift-Check (automatisch — NEU 2026-04-23)

**Einmal am Session-Ende — scannt ALLE in dieser Session geänderten Repos.**

### Schritt 1: Alle angefassten Repos der Session ermitteln

```bash
# Alle Repos mit Commits in den letzten 8h (= KANDIDATEN für diese Session)
for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
  [[ "$(basename $repo)" == *.* ]] && continue
  last=$(git -C "$repo" log --since="8 hours ago" --oneline 2>/dev/null | wc -l)
  [ "$last" -gt 0 ] && echo "$(basename $repo)"
done
```

> ⚠️ 🌀 `feedback_session_attribution_by_conversation_not_date`: Die 8h-Heuristik
> sammelt bei parallelen Sessions auch FREMDE Commits/Repos ein. Die Liste gegen die
> **eigene Turn-Historie** filtern — nur Repos behalten, die diese Session wirklich
> bearbeitet hat. Fremd-Aktivität nicht doppelt dokumentieren.

→ Ergibt Liste aller aktiven Repos dieser Session, z.B.:
```
iil-reflex
platform
risk-hub
```

### Schritt 2: Docu-Drift pro Repo prüfen

Für **jeden** Repo aus der Liste:

```bash
for REPO_NAME in <liste-aus-schritt-1>; do
  REPO=${GITHUB_DIR:-$HOME/github}/$REPO_NAME

  VER_CODE=$(grep -r '__version__\|^version' "$REPO/pyproject.toml" 2>/dev/null \
             | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  VER_README=$(head -10 "$REPO/README.md" 2>/dev/null \
               | grep -oP '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
  CL_ENTRIES=$(head -15 "$REPO/CHANGELOG.md" 2>/dev/null | grep -c '\[.*\]' 2>/dev/null || echo 0)
  NEW_PY=$(git -C "$REPO" log --since="8 hours ago" --name-only --pretty="" 2>/dev/null \
           | grep -c '\.py$' || echo 0)

  echo "$REPO_NAME | v_code=$VER_CODE | v_readme=$VER_README | cl=$CL_ENTRIES | new_py=$NEW_PY"
done
```

### Schritt 3: Issues erstellen (nur bei Trigger)

**Trigger-Regeln** — Issue erstellen wenn EINES zutrifft:

| Bedingung | Trigger | Kein Issue wenn |
|-----------|---------|-----------------|
| `v_code != v_readme` | README-Version veraltet | `v_code` leer (kein Python-Package) |
| `cl_entries == 0` | CHANGELOG leer | nur Infra/Skript-Repo ohne pyproject.toml |
| `new_py >= 1` | neue .py Datei in Session | nur Tests (`test_*.py`) |

**Owner aus dem git-Remote ableiten (nie hardcoden):**
```bash
OWNER=$(git -C "$PLATFORM_DIR" remote get-url origin \
        | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#')   # z.B. achimdehnert
```

**Duplikat-Schutz** — immer zuerst prüfen:
```
mcp__github__list_issues(owner: <OWNER>, repo: "platform",
  labels: ["docu-update"], state: "open")
→ Nur erstellen wenn KEIN Issue "[docu-update] <REPO_NAME>" bereits offen.
```

**Issue erstellen:**
```
mcp__github__create_issue(
  owner: <OWNER>, repo: "platform",
  title: "[docu-update] <REPO_NAME> — <Trigger-Grund>",
  body: "Automatisch erkannt via session-ende Phase 1b.\n\n
Trigger: <v_code != v_readme | cl leer | neue .py>\n\n
Acceptance Criteria:\n
- [ ] README.md Version = <VER_CODE>\n
- [ ] CHANGELOG.md hat Eintrag für v<VER_CODE>\n
- [ ] Outline-Eintrag vorhanden + aktuell\n
- [ ] Platform-Übersicht aktualisiert (❌→✅)\n
- [ ] git commit + push",
  labels: ["documentation", "docu-update", "automated"]
)
```

→ **`platform`-Repo selbst**: kein docu-update Issue — platform ist Meta-Repo.

---

## Phase 1c: Template-Drift-Check (automatisch — NEU 2026-04-28)

**Nur für Repos mit Änderungen in dieser Session — nur Error-Level (kein Lärm).**

```bash
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"

# Repos mit Commits in den letzten 8h (aus Phase 1b)
CHANGED_REPOS=$(for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
  [[ "$(basename $repo)" == *.* ]] && continue
  last=$(git -C "$repo" log --since="8 hours ago" --oneline 2>/dev/null | wc -l)
  [ "$last" -gt 0 ] && echo "$(basename $repo)"
done | grep -v '^platform$')

if [ -n "$CHANGED_REPOS" ]; then
  echo "Drift-Check für: $CHANGED_REPOS"
  python3 "$PLATFORM_DIR/scripts/drift_check.py" $CHANGED_REPOS \
    --severity=error \
    --fail-on-error 2>&1 | grep -E '🔴|✅|Errors|Gesamt' || true
else
  echo "ℹ️  Keine geänderten Repos — Drift-Check übersprungen"
fi
```

→ **Nur `--severity=error`** — Warnings werden täglich per GitHub Action erfasst, nicht im Session-Ende-Lärm.
→ Bei 🔴 Errors: Sofort fixen oder als Issue dokumentieren (analog Phase 1b).
→ Keine Issues wenn `--fail-on-error` sauber durchläuft (Exit 0).

---

## Phase 2: pgvector Memory schreiben (ADR-154)

> **Primärer Pfad = die CLI `platform/tools/session-memory` — NICHT der MCP.**
> Die frühere MCP-only-Variante (`mcp__orchestrator__agent_memory_upsert`) übersprang
> Phase 2 still, sobald der Orchestrator-MCP in der Session **nicht gebunden** war
> (häufig ausserhalb dev-hub/mcp-hub) → Summary ging verloren, nur „später nachziehen".
> Die CLI nutzt denselben gesegneten Transport wie `claude-policy` (SSH + `docker exec`
> in `mcp_hub_orchestrator_http`, ADR-209) und den **authoritativen** container-seitigen
> `store.upsert` (Embedding + content_hash-Dedup macht der Container). Sie funktioniert
> **unabhängig von der MCP-Bindung** in JEDEM Repo. Ist der MCP ausnahmsweise gebunden,
> darf `mcp__orchestrator__agent_memory_upsert` als Beschleuniger genutzt werden — die
> CLI bleibt der verlässliche Default.

7. **Session-Summary speichern** (CLI, MCP-unabhängig):
```bash
# Content in eine Datei (Multi-Line/Markdown sicher via base64-inline im Transport):
cat > /tmp/session-summary.md <<'SUMEOF'
# Session <date> — <repo>
## Erledigt … ## Entscheidungen … ## Offen …
SUMEOF
python3 "${GITHUB_DIR:-$HOME/github}/platform/tools/session-memory" write \
  --repo <repo> --title "Session <date> — <repo>: <1-Zeile>" \
  --session-id <kurz-slug>  # z.B. der --task-Slug des Worktrees; siehe Hinweis unten \
  --tag session --tag <repo> --tag <task-type> \
  --content-file /tmp/session-summary.md
# → {"ok": true, "written": true, "entry_key": "session:<repo>:<YYYYMMDD>:<sid>", ...}
# Verifizieren (Evidenz vor „gesichert"): session-memory get --key <entry_key aus der Ausgabe>
```

> **`--session-id` bei Parallelbetrieb (A1, seit 2026-07-20):** Der Default-Key
> `session:<repo>:<YYYYMMDD>` ist pro Repo und Tag eindeutig — zwei Sessions am
> selben Tag im selben Repo schrieben früher auf denselben Key, die zweite
> überschrieb die erste **lautlos** (Realfall: `session:platform:20260719` musste
> aus `AGENT_HANDOVER.md` rekonstruiert werden). Zwei Absicherungen:
> - **`--session-id <slug>`** macht den Key eindeutig (empfohlen, sobald du weißt,
>   dass parallel gearbeitet wird — `tools/session-leases --repo <repo>` zeigt es).
> - **Ohne** `--session-id` überschreibt die CLI **nicht mehr**, sondern weicht auf
>   `<key>-2`, `-3`, … aus. Der tatsächliche Key steht im `entry_key`-Feld der
>   Ausgabe — beim Verifizieren diesen nehmen, nicht den erwarteten.
>
> `--allow-overwrite` erzwingt das alte Verhalten (bewusst zu setzen).
entry_type default `context` (`--type` override: open_task|decision|lesson_learned|error_pattern|repo_context|agent_handoff). Bei Prod-Exec-Block im Auto-Mode: User um Freigabe bitten oder via `!` ausführen.

8. **Error-Patterns erfassen** (nur bei Bug-Fixes) — gleiche CLI, anderer Typ/Key:
```bash
python3 "${GITHUB_DIR:-$HOME/github}/platform/tools/session-memory" write \
  --repo <repo> --type error_pattern \
  --key "error:<repo>:<YYYYMMDD>-<shortid>" \
  --title "<symptom 1-Zeile>" --tag error --tag <repo> \
  --content "Repo: <repo>\nSymptom: …\nRoot Cause: …\nFix: …\nPrevention: …"
```

> ℹ️ Pattern-Recall: `session-memory get --key <key>` (exakt) bzw. bei gebundenem MCP
> `mcp__orchestrator__agent_memory_search(query: "…")` (semantisch).

---

## Phase 3: Git Sync — WSL ↔ Dev Desktop (IMMER am Ende)

### 3.1 Alle geänderten Repos committen + pushen (Session-Attribution + Protection-aware)

> 🌀 **Drei harte Lehren fließen hier ein:**
> 1. `feedback_git_add_all_swept_artifacts` — pauschales `git add -A` schwemmte `.pyc`/
>    `.coverage`/Editor-Artefakte in Commits → **nie ungefiltert `add -A`**.
> 2. `feedback_session_attribution_by_conversation_not_date` — im geteilten Tree können
>    dirty Files von PARALLELEN Sessions stammen → nur committen, was DIESE Session
>    nachweislich angefasst hat (eigene Turn-Historie); Fremdes dem User melden.
> 3. **ADR-242 Branch-Protection:** `main` ist in etlichen Repos geschützt (`ci / gate` /
>    `guardian` required) — ein Direkt-Push auf main scheitert dort mit GH013.

Pro dirty Repo:

```bash
cd "$repo"
BR=$(git branch --show-current)                      # 🌀 feedback_commit_on_main_recurs: Branch IMMER re-checken
git status --porcelain                                # sichten: gehört jede Datei zu DIESER Session?
# Nur session-eigene Dateien EXPLIZIT stagen (keine Artefakte, kein add -A):
git add <datei1> <datei2> ...
git commit -m "session-ende($(basename $repo)): $(date +%Y-%m-%d) — <kurze Beschreibung>"

# Push-Ziel bestimmen:
if [ "$BR" = "main" ]; then
  # Ist main geschützt? (Ruleset-Check, billig)
  if gh api "repos/{owner}/$(basename $repo)/rules/branches/main" --jq 'length' 2>/dev/null | grep -qv '^0$'; then
    echo "⛔ main geschützt — Direkt-Push scheitert. Worktree-Branch + PR nutzen:"
    echo "   bash platform/tools/repo-session.sh start . --task session-ende-sync && cherry-pick"
  else
    git push
  fi
else
  git push -u origin "$BR"   # Session-Branch → danach PR erstellen/verlinken
fi
```

**PR-Kadenz-Hygiene (session-retro 2026-07-02, PK-3/PK-4):**
- **Rebase-on-ready (R-6):** `gh pr update-branch` erst **unmittelbar vor** dem finalen
  Push/Merge, nicht früh — verkürzt das Konflikt-Fenster gegen zwischenzeitlich gemergte
  main-Änderungen (Realfall: 2 manuelle Textkonflikte #829/#832).
- **Bündeln statt Kleinst-PR-Schwarm (R-7):** thematisch gekoppelte Kleinfixes in **wenige,
  breitere** PRs zusammenfassen, wo sie nicht kollidieren — 11/17 PRs dieser Session trugen
  Catch-up-Merge-Tax durch sequenzielles Selbst-Mergen gegen den wandernden eigenen main.

→ Docs-only-Änderung in einem Deploy-on-push-Repo? **`[skip ci]` gehört in das
  Squash-Subject BEIM MERGEN — niemals in den Commit eines offenen PR-Branches.**
  Der Marker wirkt gegenläufig, je nachdem wo er steht:

  | Ort | Wirkung |
  |---|---|
  | **Squash-Subject** (`gh pr merge --squash --subject "… [skip ci]"`) | ✅ gewollt: der Merge-Commit auf `main` löst keinen Deploy aus (🌀 `feedback_skip_ci_uniform_on_docs_merges`) |
  | **Head-Commit des offenen PRs** (`git commit -m "… [skip ci]"`) | ⛔ tödlich: GitHub überspringt **alle** Workflow-Läufe für diesen Push, auch das `pull_request`-Event. Required Checks melden sich nie → PR steht dauerhaft `BLOCKED`, ohne dass irgendwo etwas rot wird (🌀 `feedback_blocked_without_any_pull_request_run`) |

  **GitHub matcht den Marker im GESAMTEN Commit-Body, nicht nur im Titel.** Wer den
  Fehler im Erklärtext des Korrektur-Commits *beschreibt* („kein `[skip ci]`, weil …"),
  setzt ihn damit erneut. Der Token darf in einer Commit-Message an keiner Stelle
  vorkommen — auch nicht zitiert. Über den Marker schreiben gehört in den PR-Text.

  **Erkennungsmerkmal:** der Check-Rollup ist leer bzw. zeigt nur `automerge: SKIPPED`.
  Ein leerer Rollup ist **kein** „läuft noch" — er ist der Befund.

  **Reparatur:** `git commit --amend` ohne den Token + Force-Push. Das genügt und wirkt
  sofort. `gh pr close` + `gh pr reopen` ist **nicht** nötig.

  **Messung 2026-08-15, platform#1992** (drei Anläufe, weil die Diagnose zweimal danebenlag):
  Anlauf 1 trug den Marker im Titel, Anlauf 2 wörtlich im Erklärtext — beide Male lief
  **nur** `pull_request_target` (`Dependabot auto-merge`), kein einziger Required Check.
  Anlauf 3 ohne den Token: Force-Push `11:04:50` → alle zehn `pull_request`-Checks
  gestartet `11:04:53`, drei Sekunden später. Das danach ausgeführte close/reopen
  (`11:05:34`/`11:05:36`) war **überflüssig** und erzeugte nur einen Zweitlauf.

  **Diagnose-Falle dabei:** `gh pr checks --watch` unmittelbar nach dem Push zeigte noch
  den leeren Rollup, woraus fälschlich „Force-Push hilft nicht, nur close/reopen" gefolgert
  wurde. Der billigste belastbare Check ist nicht der Rollup, sondern
  `gh run list --json event,headSha,createdAt` gegen den neuen SHA plus
  `gh api repos/<o>/<r>/issues/<n>/timeline` — erst die Zeitstempel nebeneinander zeigen,
  welches Ereignis die Läufe wirklich ausgelöst hat.
→ **NICHT ausführen** wenn der User explizit sagt "nicht pushen" oder ein PR-Review läuft.
→ Fremde dirty Files (andere Session/unbekannte Herkunft): **liegen lassen + melden**,
  nicht einsammeln.

### 3.1b Cleanup: Temporäre Dateien entfernen

```bash
# .fixed / .updated / .new Dateien die erfolgreich übernommen wurden
find ${GITHUB_DIR:-$HOME/github}/ -maxdepth 4 -name "*.fixed" -o -name "*.updated" -o -name "*.new" 2>/dev/null | head -10
```
→ Falls vorhanden: Prüfen ob übernommen, dann löschen. Falls NICHT übernommen → User warnen.

### 3.1c Worktree-Reaper: gemergte Session-Worktrees abräumen (ADR-233, PFLICHT)

> Ohne diesen Schritt akkumulieren Orphan-Worktrees über Tage (Retro 2026-06-14:
> 9 dangling, davon 3 am selben Tag erzeugt + gemergt, nie gereapt). Der Reaper ist
> **squash-merge-aware** und schützt DIRTY- + offene-PR-Worktrees selbst (kein Datenverlust).

// turbo
```bash
# Jedes Repo mit Session-Worktrees abräumen. --apply, aber tool-interne Guards
# lassen dirty / offene-PR-Worktrees absichtlich stehen. Restore-Manifest je Repo.
for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
  # NUR Haupt-Checkouts: .git ist ein Verzeichnis. Linked-Worktrees (z.B.
  # *-pinned) haben .git als DATEI → überspringen, sonst Doppel-Durchlauf.
  [ -d "$repo/.git" ] || continue
  summary=$(cd "$repo" && python3 ${GITHUB_DIR:-$HOME/github}/platform/tools/worktree-reaper.py --apply 2>/dev/null | grep -oE "[0-9]+ entfernt")
  [ -n "$summary" ] && [ "${summary%% *}" != "0" ] && echo "$(basename "$repo"): $summary"
done
echo "✅ Worktree-Reaper durchgelaufen (ADR-233)"
```
→ Wiederherstellung jederzeit via `worktree-reaper-manifest.jsonl` (pro Repo geschrieben).

### 3.2 Platform-Workflows + project-facts verteilen (IMMER — kein Conditional)

> ⚠️ **PFLICHT — nicht überspringen.** Dieser Schritt stellt sicher, dass Verbesserungen
> sofort platform-weit aktiv sind. Egal ob etwas geändert wurde oder nicht.

// turbo
```bash
# 1. Platform-Repo: main ist SEIT ADR-242 GESCHÜTZT (required check guardian) —
#    Direkt-Push scheitert mit GH013. Änderungen gehen via Session-Branch + PR:
cd ${GITHUB_DIR:-$HOME/github}/platform
if [ -n "$(git status --porcelain)" ]; then
  echo "⚠️ platform dirty — Direkt-Push auf main ist geblockt (ADR-242)."
  echo "   → Dateien sichten (Session-Attribution!), dann via Worktree-Branch + PR:"
  echo "     bash tools/repo-session.sh start . --task session-ende-platform-sync"
  echo "   → Dateien EXPLIZIT (kein add -A) in den Worktree übernehmen, PR erstellen."
else
  echo "ℹ️  platform: kein Commit nötig"
fi

# 2. Workflows an ALLE Repos verteilen (Symlinks aktualisieren)
GITHUB_DIR="${GITHUB_DIR:-$HOME/github}" \
  bash "${GITHUB_DIR:-$HOME/github}/platform/scripts/sync-workflows.sh" \
  2>&1 | grep -cE "LINK|REPLACE" | xargs -I{} echo "{} Workflow-Symlinks aktualisiert"

# 3. project-facts.md wird hier NICHT mehr lokal regeneriert.
#    Owner ist der CI-Cron `gen-project-facts.yml` (Mo 04:00 UTC, wöchentlich)
#    + on-demand `workflow_dispatch`. Der frühere Lokal-Lauf schrieb bei JEDEM
#    Session-Ende nur einen frischen Timestamp in die (getrackte) Datei → ließ
#    ALLE Repos dirty, konnte sie aber wegen Branch-Protection nie committen.
#    Zwei Erzeuger für dasselbe Artefakt = SSoT-Verletzung; der Lokal-Lauf war
#    der redundante. Gezielte On-demand-Regen für EIN Repo bleibt möglich:
#      python3 platform/scripts/gen_project_facts.py --repo <name>
```

→ **Ergebnis**: Nächster `session-start` auf JEDER Maschine hat automatisch die aktuellen Rules + Workflows.
→ project-facts.md aktualisiert der wöchentliche CI-Cron (`gen-project-facts.yml`) — kein Dirty-State am Session-Ende mehr.
→ Unregistrierte Repos → in `platform/scripts/repo-registry.yaml` eintragen (Warnung erscheint im CI-Cron-Log).

> ℹ️ **ADR-230 (CC-first):** `sync-workflows.sh` ist der **Windsurf-Ära**-Symlink-Pfad.
> Für **CC-Skills** ist die kanonische Verteilung `platform/tools/cc-skill-dist/`
> (`generate.py`/`doctor.py`); nach dem gegateten Live-Rollout ersetzt sie diesen
> Schritt für `~/.claude/commands`. Bis dahin laufen beide parallel.

// turbo
```bash
PLATFORM_DIR="${GITHUB_DIR:-$HOME/github}/platform"
VERSION_AFTER=$(cat "$PLATFORM_DIR/VERSION" 2>/dev/null || echo "unknown")
COMMIT_AFTER=$(git -C "$PLATFORM_DIR" log -1 --format="%h" 2>/dev/null || echo "?")
echo ""
if [ "$VERSION_BEFORE" != "$VERSION_AFTER" ] || [ "$COMMIT_BEFORE" != "$COMMIT_AFTER" ]; then
  echo "┌─────────────────────────────────────────┐"
  echo "│  ✅ DEPLOYED TO GITHUB                  │"
  echo "│  v${VERSION_BEFORE} → v${VERSION_AFTER}                │"
  echo "│  Commit: ${COMMIT_BEFORE} → ${COMMIT_AFTER}             │"
  echo "│  Plattformweit aktiv ab nächstem Start  │"
  echo "└─────────────────────────────────────────┘"
else
  echo "┌─────────────────────────────────────────┐"
  echo "│  ℹ️  KEINE PLATFORM-ÄNDERUNGEN         │"
  echo "│  Platform v${VERSION_AFTER} (${COMMIT_AFTER})       │"
  echo "└─────────────────────────────────────────┘"
fi
```

### 3.3 Finale Prüfung — Kein Repo darf dirty sein

```bash
dirty=0
for repo in ${GITHUB_DIR:-$HOME/github}/*/; do
  if [ -n "$(cd "$repo" && git status --porcelain 2>/dev/null)" ]; then
    echo "DIRTY: $(basename $repo)"
    dirty=$((dirty + 1))
  fi
done
[ $dirty -eq 0 ] && echo "✅ Alle Repos clean" || echo "⚠️ $dirty Repos noch dirty"
```
→ Ziel: **0 dirty Repos** am Session-Ende.
→ Falls dirty: nochmal committen + pushen oder User fragen.

### 3.4 Fallback bei Shell-Hang

Falls Shell blockiert ist, nutze GitHub MCP für kritische Pushes (`<OWNER>` aus
dem git-Remote, siehe Phase 1b):
```
mcp__github__push_files(owner: <OWNER>, repo: "<repo>", branch: "main",
  files: [{"path": "<pfad>", "content": "<inhalt>"}],
  message: "session-ende: <beschreibung>")
```
→ Funktioniert nur für **public Repos** oder Repos mit Write-Token.
→ Für private Repos: User muss manuell pushen.

---


## Anti-Patterns (Skill ist `mode: write`)

- ❌ Owner/Org/MCP-Prefixe/IPs hardcoden — Owner aus dem git-Remote ableiten,
  Tools mit stabilen CC-Namen (`mcp__github__*`, `mcp__orchestrator__*`) nennen.
- ❌ Outline-Schreiben hier inline duplizieren — an `/knowledge-capture` delegieren
  und **Erfolg prüfen** (Redundanz zu `/session-docu` vermeiden).
- ❌ `git push` ausführen, wenn der User „nicht pushen" sagt oder ein PR-Review
  läuft (Phase 3.1).
- ❌ **`git add -A` — in keiner Phase.** Immer explizite Pfade nach Sichtung
  (🌀 `feedback_git_add_all_swept_artifacts`: .pyc/.coverage landeten in Commits).
- ❌ Fremd-Session-Artefakte einsammeln — dirty Files/Commits ohne Bezug zur eigenen
  Turn-Historie melden statt committen (🌀 Session-Attribution, Realfall #734).
- ❌ Direkt-Push auf geschützte `main`-Branches versuchen (ADR-242: platform + 10
  weitere Repos haben required checks) — Session-Branch + PR ist der Pfad.
- ❌ Memory-Calls mit der alten Windsurf-Signatur (`entry: {entry_id…}}`) — die
  CC-Signatur ist flach mit `entry_key`.

**Idempotenz:** Re-Run ist sicher — Commits/Sync sind wiederholbar, Issue-Erstellung
ist Duplikat-geschützt (Phase 1b), Memory-Upserts deduplizieren per `content_hash`.

## Abschluss-Checkliste + MCP-Reference

### Checkliste (muss alles grün sein)

| # | Check | Status |
|---|-------|--------|
| 1 | Outline-Dokument geschrieben/aktualisiert | ☐ |
| 2 | pgvector Session-Summary gespeichert | ☐ |
| 3 | Error-Patterns erfasst (falls Bug-Fix) | ☐ |
| 4 | Alle Repos committed + pushed | ☐ |
| 5 | Platform gepusht → Workflows sync → project-facts aktuell | ☐ |
| 6 | Kein Repo dirty | ☐ |
| 7 | Keine .fixed/.updated Dateien übrig | ☐ |
| 8 | Blockierte Arbeit dokumentiert | ☐ |
| 9 | Docu-Drift-Check: Issue erstellt falls nötig (Phase 1b) | ☐ |
| 10 | Template-Drift-Check: Error-Drifts gefixt (Phase 1c) | ☐ |
| 11 | Erledigte/verschobene Prios im Handover UND Memory nachgezogen (Phase 0c) | ☐ |
| 12 | Offene AGENT_HANDOVER.md-PRs gegengecheckt vor eigenem Schreiben (Phase 0a-handover-pr) | ☐ |
| 13 | Handover-Freshness-Check gelaufen: Exit 0 oder begründet im Commit-/PR-Text (Phase 0a-freshness) | ☐ |
| 14 | Abnahme gegen Session-Zielzustand im Stand-Block: erreicht/nicht erreicht/verschoben+Tracking bzw. n/a-begründet (Phase 0d) | ☐ |
| 15 | SA-4-Zähler-Zeile geschrieben, Fehlanwendung ggf. als Befund gemeldet (Phase 0d) | ☐ |
| 16 | Handover-PR gemergt — oder eine der vier Grenzen aus Phase 0a-merge benannt | ☐ |
| 17 | Clear-Härte: nichts Dauerhaftes lebt nur im Gesprächsverlauf oder im Scratchpad, kein dauerhaftes Dokument verweist auf Flüchtiges (Phase 0e) | ☐ |
| 18 | `befund_journal.py --offen-cross-repo` gelaufen: Exit 0, oder jeder genannte Befund verankert bzw. mit Grund verzichtet (Phase 0f) | ☐ |
| 19 | Ab `full`-Footprint: Abnahme (0d) und Clear-Härte (0e) von je einem Subagenten mit fremdem Kontext gegengelesen, Ergebnis im Stand-Block — oder `lean` begründet bzw. Regel-1-Bruch benannt (Phase 0g) | ☐ |

> **Pflicht-Selbstcheck (nicht überspringen):** Zähle die `###`/`##`-Phasen-Überschriften
> oben im Dokument, die als PFLICHT/NEU markiert sind, gegen diese Tabelle — jede neue
> Pflicht-Phase braucht eine eigene Zeile hier. Diese Checkliste selbst driftete bereits
> einmal aus dem Takt: Phase 0a-handover-pr wurde am 2026-07-14 ergänzt, aber erst am
> 2026-07-15 (Retro c494a2, Befund #8) als fehlende Checklisten-Zeile bemerkt — eine
> Session hatte die Phase im Dokument vorliegen, aber nicht ausgeführt, weil die
> Abschluss-Checkliste sie nicht abfragte.

---

### MCP-Server Quick-Reference

> ⚠️ MCP-Prefix ist environment-spezifisch — IMMER `project-facts.md` als Quelle nehmen!

#### Dev Desktop (adehnert@dev-desktop)

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp1_` | orchestrator | Memory, Task-Analyse, Plans, Evaluate, Verify |

#### WSL / Prod-Server

| Prefix | Server | Zweck |
|--------|--------|-------|
| `mcp0_` | deployment-mcp | SSH, Docker, Git, DB, DNS, SSL, System |
| `mcp1_` | github | Issues, PRs, Repos, Files, Reviews |
| `mcp2_` | orchestrator | Memory, Task-Analyse, Agent-Team |
| `mcp3_` | outline-knowledge | Wiki: Runbooks, Konzepte, Lessons |
| `mcp4_` | paperless-docs | Dokumente, Rechnungen |
| `mcp5_` | platform-context | Architektur-Regeln, ADR-Compliance |

> **Claude Code:** stabile Namen `mcp__github__*` / `mcp__orchestrator__*` verwenden —
> `mcpN_`-Nummern sind Windsurf-Ära und environment-volatil.

## Changelog

- 2026-08-17: **Phase 0g Fremder Blick (PFLICHT ab `full`) + Checklisten-Zeile 19** —
  Owner-Freigabe für Subagenten in den Session-Skills. Bewusst **nur zwei** Phasen bekommen
  fremden Kontext: 0d (Abnahme) und 0e (Clear-Härte). Beide sind Selbstbeurteilung, für die
  `/session-retro` seit jeher die Regel „Richter ≠ Angeklagter" führt — und die dieser Skill
  bis hierhin ohne sie durchführte. Alles andere im Skill bleibt mechanisch (Deploy-Status,
  Freshness, Drift-Checks, Reaper, Git-Sync); dort wäre ein Agent teurer und unzuverlässiger
  als das vorhandene Skript. **`/session-start` bekommt bewusst KEINE Subagenten:** am
  Sitzungsanfang ist der Agent selbst der frische Kontext, das Problem existiert dort nicht;
  eine Verdichtungsschicht zwischen Agent und Handover würde sogar schaden. Footprint-Schalter
  statt „immer", weil ~110k Token je Sitzungsende kein Rundungsfehler sind. Anlass:
  `docs/retros/session-retro-2026-08-17-platform-37e8e0.md` — dort ist die Selbstabnahme
  („Zielzustand erreicht, mit benannter Restmenge", Restmenge selbst gesetzt) neben einer
  `refuted_rate 0.00` dokumentiert.
- 2026-08-12: **Phase 0e Clear-Härte (PFLICHT) + Checklisten-Zeile 17** — der Skill hatte
  Phasen, die Flüchtiges wegräumen (3.1b temporäre Dateien, 3.1c Worktree-Reaper), aber
  keine, die vorher fragt, ob dort etwas Dauerhaftes liegt. Belegt per `grep -ic` auf dieses
  Dokument: 36× „handover", 16× „worktree", **0×** „clear" und 0× jede Formulierung für
  flüchtigen Gesprächskontext — mit Positivkontrolle, die Null ist also die Welt und nicht
  der Filter. Anlass (illustration-hub, 2026-08-12): eine Session wurde zweimal als „sauber
  geschlossen" gemeldet, während ein Textvorschlag nur im Chat lag und eine Datensicherung
  vor einer Produktionsdaten-Änderung nur im Session-Scratchpad, den 3.1b gelöscht hätte;
  der frisch geschriebene Handover verwies dafür auf „das Sitzungsprotokoll". Aufgefallen
  erst durch die Owner-Frage „also /clear?". Bewusst **kein** automatisches `/clear`: das
  ist ein CLI-Builtin und würde den Verlust beschleunigen statt verhindern — der Wert
  steckt in der Frage „was verschwindet, wenn dieses Fenster zugeht?".
- 2026-08-10: **Phase 0a-merge (PFLICHT) + Checklisten-Zeile 16** — Handover-PRs werden
  ohne Rückfrage gemergt, sobald CI grün ist (Owner-Weisung, Anlass illustration-hub #197).
  Begründung: ein Handover-PR ist ein Bericht über bereits Geschehenes, keine Entscheidung —
  vorlegen verzögert genau die Information, für die er existiert, und erzeugt die Lage,
  gegen die 0a-handover-pr geschrieben wurde. Vier Grenzen ausdrücklich benannt (mehr als
  Doku, ADR-Statuswechsel, Auto-Deploy-Repo, CI nicht grün), damit die Weisung nicht zur
  Blankovollmacht für „Docs-PR" als Etikett wird.

- 2026-08-02: Phase 0a-freshness (PFLICHT) + Checklisten-Zeile 13 — Welle 1 KONZ-038,
  Issue #1457, Slug `handover-stale-vor-merge` (×12). Reconcile-Befund: das CI-Gate ist
  paths-gefiltert und kann die Verstoß-Klasse „Handover NICHT angefasst" strukturell
  nicht sehen; der Prüfer (`agent_handover_freshness_check.py`) existierte + ist getestet,
  lief aber an keiner Prozess-Stelle, die den Verstoß erreicht.
- 2026-07-15: Abschluss-Checkliste um Zeile 12 (Phase 0a-handover-pr) ergänzt + Pflicht-
  Selbstcheck-Hinweis. Aus Retro `session-retro-2026-07-15-platform-c494a2` (Befund #8):
  Phase 0a-handover-pr wurde 07-14 ergänzt, war in der verteilten Skill-Kopie vorhanden,
  wurde aber in derselben Session nicht ausgeführt — die Checkliste fragte sie nicht ab.
  Allgemeine Lehre (auch außerhalb dieses Skills): eine neue PFLICHT-Phase ohne
  Checklisten-Zeile ist strukturell überspringbar, egal wie deutlich sie im Fließtext
  markiert ist.
- 2026-07-02: v2 — Phase 3.1 komplett überarbeitet: kein `git add -A` mehr (🌀
  swept-artifacts), Branch-Re-Check + Session-Attribution-Filter (🌀 #734), Branch-
  Protection-aware Push (ADR-242: geschützte mains → Worktree-Branch + PR),
  `[skip ci]` bei docs-only auf Deploy-Repos; Phase 3.2 platform-Push auf PR-Pfad
  umgestellt (Direkt-Push auf main scheitert seit Wave 1 an guardian — Realfall:
  adr-nightly-metrics 30 Nächte rot an genau dieser Wand); Phase 1b mit
  Attribution-Warnung; Anti-Patterns erweitert; Changelog-Sektion ergänzt
  (claude-skills-Policy-Pflicht).
- ≤2026-06-24: Phase 0c (Handover-Prio-Nachzug), 0a-deploy (Deploy-Status-Pflicht),
  Worktree-Reaper 3.1c — Historie siehe git log.
