# Lehren, Herleitungen und Historie — `/session-ende`

> Begleitdoku zu `.windsurf/workflows/session-ende.md`
> ([platform#2690](https://github.com/achimdehnert/platform/issues/2690), Kriterium **K5**
> Kontext-Diät). Der Skill trägt die **Anweisung**, diese Datei das **Warum**.
> Nichts hier ist gelöscht — jeder Abschnitt ist der wörtliche Text, der bis
> 2026-09-02 im Skill stand; die Überschrift nennt die Ursprungs-Phase, die erste
> Zeile das Datum der Lehre.
>
> **Ein Link ist kein Leser** (Advocatus Diabolus D1 des Streichplans): Regeln, die
> eine Handlung im selben Moment verbieten, sind **nicht** hierher gewandert — sie
> stehen weiter als imperative Zeile im Skill. Hier steht nur die Herleitung.
>
> Die **Mechanik** dieser Phasen läuft seit 2026-09-02 im Runner
> `tools/session_ende_checks.sh` (E.0–E.9, dokumentiert in
> [`session-ende-runner.md`](../session-ende-runner.md)) — der Skill deutet, der
> Runner misst.

> **Zweite Kürzung am 2026-10-06** (V2b,
> [platform#3785](https://github.com/achimdehnert/platform/issues/3785)): Der Skill ging von
> 32 295 auf unter 20 000 Bytes (Ratsche `docs/governance/startlast-deckel.json`). Was dabei
> aus dem Skill fiel, steht im jeweiligen Abschnitt unter **„Aus dem Skill ausgelagert (V2b)"**
> im Wortlaut; die Überschriften mit Datum und Anlass stehen in `#ueberschriften-vor-v2b`.

---


## kopf

**Aus dem Skill ausgelagert (V2b), Wortlaut des Kopfblocks:**

> Gegenstück `/session-start` · `LEHREN` = `docs/governance/session-skills-lehren/ende.md` ·
> Runner-Doku = `docs/governance/session-ende-runner.md`.
> **Der User muss NICHTS auflisten** — der Agent scannt die Session autonom. Läuft in
> Claude Code (ADR-230): stabile Tool-Namen `mcp__github__*`/`mcp__orchestrator__*`, nie
> `mcpN_` (Quelle: `project-facts.md`); Owner/Org aus dem git-Remote, nie hardcoden.
> **Platform Sync Loop:** Ende = commit → push → GitHub → alle Repos beim nächsten Start.
> GitHub ist die einzige Source of Truth (Diagramm in `/session-start`).


## e-r

**Aus dem Skill ausgelagert (V2b), Wortlaut aus Phase E.R:**

> Die mechanischen Phasen laufen in **einem** Aufruf und sind damit strukturell nicht
> überspringbar; die Einzel-Befehle leben in `platform/tools/session_ende_checks.sh` (dort
> gepflegt, hier NICHT duplizieren).

> → **Jede ⚠️ WARN-Zeile ist ein Befund** und gehört ins Abschluss-Board der Sitzung.
> → **Jede `◌`/`SKIP`/`nicht messbar`-Zeile ist eine Lücke, kein Pass — als solche ins Board.**
> → Der Runner **misst**, dieser Skill **deutet**. Herleitung je Phase: `LEHREN`.

Die Tabellenzeilen vor der Verdichtung:

> | `E.3 handover-frische` | ❌ Commits seit dem letzten Nachtrag und kein offener Handover-PR · ⚠️ Stand älter als der letzte Commit der Datei · **Fragment-Modus:** ❌ kein eigenes Fragment · ❌ `veraltet`: nach dem jüngsten eigenen Fragment legte die Sitzung weitere PRs an · ◌ Sitzung nicht zuordenbar (Lease ohne `claude_session`) | Exit 0, Nachtrag offen als PR, oder eigenes Fragment auf `main`/im PR ohne späteren Sitzungs-PR | Deutung in 0a-freshness bzw. 0b-fragment; `veraltet` → neues Fragment |
> | `E.5 zusagen` | Vertagung ohne Anker im Segment (advisory) | `✅` je Zusage | Deutung in 0g |
> | `E.8 worktree-hygiene` | ❌ verknüpfter Baum älter als 14 Tage (`SESSION_ENDE_WORKTREE_MAX_TAGE`); `prunable`-Einträge räumt der Runner selbst | kein Baum über der Grenze | entfernen (`repo-session.sh reap` / `git worktree remove`) oder Grund in `<gitdir>/behalten` |
> | `E.11 main-status` | ⚠️ `rot auf main: <repo>: <Workflow> (<Run-ID>)`, jüngster Push-Lauf von heute je Workflow · ◌ `nicht messbar` | kein Workflow zuletzt rot | **nicht auf ein rotes main mergen**; eigene Ursache: fixen oder `gh run rerun <id> --failed`; fremde oder bekannte Ursache: Issue-Link ins Board |

> **Läuft der Runner nicht** (Shell blockiert, keine Ausgabe nach 5 s): Session neu starten;
> bis dahin nur `Read`/`Write`/`Edit` + `mcp__github__*`, und **auf einem Branch, nie auf
> `main`** (geschützt in platform + 10 Repos, ADR-242/GH013).

Die Zeile `E.5 zusagen` ist mit der Phase 0g entfallen, siehe `#0g`.


## ueberschriften-vor-v2b

Die Phasen-Überschriften trugen bis 2026-10-06 Datum und Anlass. Im Skill steht seither nur
noch die Kennung mit PFLICHT-Markierung; der Wortlaut davor:

> ## Phase E.R: Runner ausführen (PFLICHT — NEU 2026-09-02; ersetzt −0.1/0a-deploy/0a-handover-pr/1b-Erzeuger/1c/3.1c/3.2-Banner/3.3)
> ### 0a-merge: Den eigenen Handover-PR selbst mergen (PFLICHT — Owner-Weisung 2026-08-10)
> ### 0b-fragment: Eigenes Fragment statt geteilter Dateien (PFLICHT in Repos mit `docs/handover.d/` — NEU 2026-09-16, #1944 K6)
> ### 0c: Erledigte/verschobene Prioritäten nachziehen (PFLICHT — NEU 2026-06-24)
> ### 0d: Abnahme gegen den Session-Zielzustand + SA-4-Zähler (PFLICHT — NEU 2026-08-07)
> ### 0e: Clear-Härte — was überlebt den Kontext-Verlust? (PFLICHT — NEU 2026-08-12)
> ### 0f: Cross-Repo-Befunde ins Zielrepo bringen (PFLICHT — NEU 2026-08-16, platform#2004)
> ### 0f-verankerung: Neues Gate nur mit Drill, Positivkontrolle, Messpunkt (PFLICHT — NEU 2026-09-02, platform#2690 K4)
> ### 0g: Zusagen dieser Sitzung gegen Tracking-Artefakte prüfen (PFLICHT — NEU 2026-08-23, platform#2211)
> ### 0h: Fremder Blick auf 0d und 0e (PFLICHT ab `full` — NEU 2026-08-17, Owner-Freigabe)
> ### 0i: Auftragsraum — keine Korrektur ohne Artefakt (PFLICHT — NEU 2026-09-11, KONZ-platform-059 / #3079)
> ### 3.1 Alle geänderten Repos committen + pushen (PFLICHT — Session-Attribution, Protection-aware)
> ### 3.4: Abschluss — Maßnahmen statt Nacherzählung (PFLICHT, wenn etwas zu entscheiden ist — NEU 2026-10-05, Owner-Wort)
> ### 3.5: Clear-Freigabe — expliziter letzter Satz (PFLICHT — NEU 2026-08-30, Owner-Weisung)

---


## −0.1 version-banner

Stand bis 2026-09-02 · heute Runner-Phase `E.0 banner`.

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


## 0a

Lesson 2026-04-05.

> Lesson Learned: Wenn Tools blockiert sind, ist es besser die Lösung in einer
> .fixed-Datei zu hinterlegen als die Session ergebnislos zu beenden.


## 0a-deploy

Lesson 2026-06-22 · heute Runner-Phase `E.1 deploy-status`.

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


## 0a-handover-pr

Lesson 2026-07-14 · heute Runner-Phase `E.2 handover-prs`.

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


## 0a-merge

Owner-Weisung 2026-08-10 (illustration-hub PR #197).

> **Ein Handover-PR ist ein Bericht über bereits Geschehenes, keine Entscheidung.** Der
> Owner kann ihm nichts zustimmen, was nicht ohnehin schon passiert ist — und sein Inhalt
> wird beim nächsten `/session-start` wieder eingelesen. Ihn zur Freigabe vorzulegen
> verzögert genau die Information, für die er existiert, und erzeugt die Lage, gegen die
> Phase 0a-handover-pr geschrieben wurde: zwei konkurrierende Stände nebeneinander
> (Realfall 2026-07-14). Owner-Weisung 2026-08-10 (illustration-hub PR #197).

**Aus dem Skill ausgelagert (V2b), Wortlaut der Grenzen-Tabelle:**

> **Grenzen — hier gilt die Weisung NICHT, dann bleibt es bei der Vorlage:**
>
> | Bedingung | Warum |
> |---|---|
> | PR enthält mehr als Dokumentation | Code/Konfiguration ist eine Entscheidung, kein Bericht |
> | ADR-Statuswechsel im selben PR | Aussage über Wirklichkeit, kein Protokoll |
> | Repo mit Auto-Deploy-on-`main` | Der Merge IST dort der Prod-Schritt → Gate 2 |
> | CI rot oder Required Checks fehlen | Grün ist die Bedingung, nicht die Formalie |
>
> → Trifft eine Grenze zu: PR offen lassen, im Abschlussbericht **mit Grund** nennen.


## 0b-fragment

NEU 2026-09-16, #1944 K6 (KONZ-platform-027).

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> Parallele Sitzungen sind in Querschnitt-Repos der Normalfall; deshalb schreibt jede Sitzung
> nur **ihre eigene** Datei. Liegt `docs/handover.d/` im Repo, **ersetzt** dieser Schritt
> 0a-freshness, 0b, 0c und den Eintrag in `AGENT_HANDOVER_LOG.md`:

> - `AGENT_HANDOVER.md` und `AGENT_HANDOVER_LOG.md` **nicht** anfassen — erledigte Punkte
>   fallen von selbst heraus, sobald ihr Issue zu ist; offene stehen im gerenderten Stand.
> - Das Fragment kommt in den letzten PR der Sitzung (oder einen eigenen); nach dem Merge
>   ist es **unveränderlich**, eine Korrektur ist ein neues Fragment (CI prüft das).
> - Memory (Phase 2) bleibt Pflicht — das Fragment ersetzt den Handover, nicht pgvector.
> - `E.3` ist grün, sobald das Fragment auf `main` oder in einem offenen PR liegt **und** die
>   Sitzung danach keinen weiteren PR angelegt hat (Branches aus den Leases, Feld
>   `claude_session`). Weitergearbeitet nach dem Fragment → neues Fragment (#2234).


## 0a-freshness

Welle 1 KONZ-038, Issue #1457, 2026-08-02 · Messung heute in `E.3 handover-frische`.

> **Warum als Skill-Gate:** Das CI-Gate (`handoff-banner-gate.yml`) läuft nur, wenn
> `AGENT_HANDOVER.md` im PR IST — der ×12-Verstoß (`handover-stale-vor-merge`) ist aber
> gerade, sie NICHT anzufassen. Ein paths-gefiltertes Gate kann diese Klasse strukturell
> nicht sehen; der Prozess-Schritt hier kann es (Vier-Wege-Prüfung KONZ-038 §5.7: Ablauf
> statt N-ter Regel).

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> Gemessen in `session_ende_checks.sh` **E.3**, gedeutet hier. Registry-`module`:
> `scripts/checks/agent_handover_freshness_check.py`; zusätzlich läuft
> `.github/workflows/handover-freshness-advisory.yml` bei **jedem** PR (Registry-Revision
> 2026-08-20).
>
> - **❌ FAIL** (seit 2026-09-14, Retro oqu6Z6 #22) → seit dem letzten Nachtrag sind Commits
>   gelandet und kein Handover-PR ist offen. Der Nachtrag ist der letzte Schritt vor dem
>   Sitzungsende — auch wenn der letzte Stand von einer Parallelsitzung stammt.
> - **Exit 0** → frisch, weiter.
> - **Exit 1** → Stand-Abschnitt JETZT nachziehen (Datum + Prio-Zeilen), dann erneut prüfen.
>   Ihn stehen zu lassen ist zulässig, braucht aber einen Satz mit Grund im Commit-/PR-Text —
>   stillschweigend stale mergen ist der ×12-Verstoß.


## 0b

KONZ-027 Arm A / Pilot #1302, gemessen 2026-07-22.

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

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> **Zwei Ziele, zwei Regeln:** `AGENT_HANDOVER_LOG.md` wird **nur angehängt** (neuer Block ans
> Ende, bestehende Einträge nie ändern — CI-Check `handover-append-only` blockt Verstöße).
> `AGENT_HANDOVER.md` wird **umgeschrieben** (0c verlangt das); Konflikte bleiben laut.
> Danach `git add docs/AGENT_HANDOVER.md && git commit -m "chore: update AGENT_HANDOVER"` —
> `/session-start` Phase 1 liest die Datei beim nächsten Mal.


## 0c

Lesson 2026-06-24 (iil-klickdummy).

> **Unabhängig von WIP** (Phase 0b feuert nur bei uncommitted Stand — eine
> *abgeschlossene* Prio hinterlässt aber oft gar keine dirty Files und fiel
> bisher durchs Raster). Lesson 2026-06-24 (iil-klickdummy): siehe
> session-start Phase 2.6.

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> 2. **Handover UND Memory (Phase 2) aktualisieren, nie nur eins.** Cross-Host-Sessions
>    (iPad/claude.ai) schreiben nur ins geteilte pgvector-Memory → der git-getrackte Handover
>    driftet.


## 0d

Zielzustand-Loop, 2026-08-07.

> Gegenstück zu `session-start` Phase 2.7. Abnahme heißt: gegen den **akzeptierten
> Zielzustand** prüfen, nicht gegen die Liste erledigter Schritte
> (`policies/zielzustand.md` Pkt. 4). Und: SA-4 ist eine Konvention mit Ratsche —
> ohne Messstelle driftet sie (`feedback_canon_decision_needs_enforcement_gate`);
> diese Phase IST die Messstelle.

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> 1. **Abnahme:** für den in `/session-start` 2.7 geklärten Zielzustand genau einen Ausgang im
>    Stand-Block: **erreicht** (Kriterien einzeln verifiziert, nicht pauschal) · **nicht
>    erreicht** (mit dem fehlenden Kriterium) · **verschoben** (nur mit Tracking-Artefakt im
>    selben Zug). Ohne Zielzustand: „Zielzustand: n/a (begründet)".
> 2. **SA-4-Zähler**, eine Zeile im Stand-Block: `SA-4: <n> Anwendungen · <m> Einzel-OK trotz
>    Klassen-Deckung · <f> Fehlanwendungen`. `f > 0` → SA-4 fällt auf Einzelfreigabe zurück:
>    sofort als Befund melden. `m` speist den Kill-Test (Signal G, >30 %).


## 0e

Realfall illustration-hub, 2026-08-12.

> **Der Skill räumt Flüchtiges weg (3.1b, 3.1c) und fragt nirgends, ob dort etwas
> Dauerhaftes liegt.** Belegt am 2026-08-12 (illustration-hub): `grep -ic` findet in diesem
> Dokument 36× „handover" und 16× „worktree", aber **0×** „clear" und 0× irgendeine
> Formulierung für flüchtigen Gesprächskontext — die Null ist die Welt, nicht der Filter.

**Frage 3 ist die gefährlichste**, weil sie als einzige nicht auffällt: das Dokument
*sieht* vollständig aus. Der Realfall, der diese Phase auslöste: ein frisch geschriebener
Handover verwies auf „das Sitzungsprotokoll", also auf den Chat, und eine Datensicherung
(alte Kanon-Texte vor einer Produktionsdaten-Änderung, ausdrücklich als Rückweg gefordert)
lag ausschließlich im Session-Scratchpad — den Phase 3.1b gelöscht hätte. Beides fiel erst
auf, als der Owner „also /clear?" fragte, nachdem die Session bereits zweimal als
„sauber geschlossen" gemeldet worden war.

**Der Selbsttest in einem Satz:** nicht „ist alles gemergt?" fragen — das beantwortet eine
andere Frage —, sondern **„was verschwindet, wenn dieses Fenster zugeht?"**

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> Nach dem Handover-Block, **vor** Phase 1, drei Fragen. Jede mit „ja" beantwortete Zeile
> bekommt im selben Zug ein dauerhaftes Artefakt (Issue-Kommentar, Handover-Zeile,
> Memory-Datei) — „steht im Gesprächsverlauf" zählt so wenig wie „steht im PR-Text".

> **Frage 3 ist die gefährlichste**, weil sie als einzige nicht auffällt. **Kein
> automatisches `/clear` einbauen** — der Wert steckt in der Frage.


## 0f

platform#2004, 2026-08-16 · Melder-Urteile 2026-08-20 · Messung heute in `E.4 cross-repo-befunde`.

> **Der Befund über ein fremdes Repo bleibt sonst als Prosa in diesem Repo liegen.**
> Gemessen am 2026-08-16: fünf offene `[deploy-health]`-Issues — apo-hub (10 Tage),
> trading-hub (10 Tage), travel-beat, cad-hub, tax-hub — **alle im Repo `platform`**,
> alle über andere Repos, **keins bearbeitet**. Der Melder war zuverlässig; ein Leser
> fehlte. Dieselbe Klasse wie 🌀 `melder-ohne-leser`.

**Warum das zählt:** Am 2026-08-20 waren in einer einzigen Sitzung vier Melder-Befunde
falsch — ein `DOPPELLAUF` ohne laufende Container, drei `required-file`-Errors für
Dateien, die existieren (nur an anderer Stelle), ein Footer-Hash, der jede korrekte
Kopie als Drift meldet, und zwei Melder, die gemergte PRs als offene Referenz lesen.
Vier Melder, vier Fehlalarme, null Messung. Ein Melder, der öfter irrt als trifft,
erzieht zum Wegsehen — und das trifft dann auch seine **richtigen** Befunde.

Die Quote erscheint im Session-Start als Phase `0.7.19`, aber erst ab drei Urteilen
je Melder: darunter ist jede Quote Zufall.

Was **nicht** zulässig ist: die Zeile stehen lassen und die Sitzung beenden. Genau das ist
die Mechanik, mit der `claim-before-cheapest-check` 16 Rückfälle sammeln konnte, ohne dass
je jemand das Gate anfasste — jede einzelne Sitzung hielt es für die Aufgabe der nächsten.

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

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> Gemessen in `session_ende_checks.sh` **E.4** (`tools/befund_journal.py --offen-cross-repo`),
> gedeutet hier.

> **Das Issue gehört ins Zielrepo, nicht hierher.** **Fremdes Repo = Scope-Checkpoint:** ab
> drei betroffenen Repos oder bei fremder Org (`meiki-lra`, `ttz-lif`, `iilgmbh`) erst den
> Owner fragen.
>
> **Jeder behandelte Melder-Befund bekommt `--echt` oder `--falsch`** — ohne Urteil ist die
> Präzision des Melders unbekannt (Quote im Start als `0.7.19`, ab drei Urteilen):
> `befund_journal.py --echt '<ID>' '<Notiz>'` bzw. `--falsch '<ID>' '<warum Fehlalarm>'`.
>
> **Rückfällige Gates aus `tools/gate_wirkung.py`** (geprüft in `/session-retro` Phase 0.0/5a; Gate
> `gate-rueckfall-unbemerkt`, Registry-`module` `tools/gate_wirkung.py`): genau zwei zulässige Abschlüsse — **behandelt**
> (Gate ausgeweitet/umgebaut/herabgestuft, der Eintrag unter `docs/governance/gates/` im selben PR
> nachgezogen, bei Herabstufung `declined` mit Begründung) **oder Verzicht mit Grund**. Die
> Zeile stehen zu lassen ist keine dritte Antwort.


## 0f-verankerung

platform#2690 K4, 2026-09-02.

> **Ein Gate ohne Positivkontrolle ist ein Melder, der nie beweisen musste, dass er
> etwas finden kann.** Gemessen am 2026-09-02: 14 von 33 Gates sind rückfällig
> (#2374, #2678); von 31 Registry-Einträgen trug **keiner** einen Beleg, dass er den
> Fall, gegen den er gebaut wurde, je getroffen hat. Der Eintrag in
> ein Eintrag unter `docs/governance/gates/` ist eine Behauptung über Wirkung — bis hierhin
> konnte sie jeder aufstellen, der eine Zeile JSON schreibt.

**`faengt` ist kein Ersatz für die Positivkontrolle.** Es belegt, dass der Fall im Drill
**vorkommt** — `gate_namensdeckung.py` schreibt die Grenze in den eigenen Kopf: „Er misst
NICHT, ob der Test den Fall wirklich abfängt." Die Positivkontrolle belegt, dass das Gate
bei diesem Fall **rot wurde**.

**Bestandsschutz ist Absicht:** die Alt-Einträge werden nicht rückwirkend eingefordert.
`--neu` greift nur, was gegenüber `origin/main` neu oder in einem Nicht-Prosa-Feld geändert
ist; ein Tippfehler-Fix im `note` färbt keinen PR. Die Ist-Zahl steht in `--alle`; das
Nachziehen der Bestands-Gates ist getrackt in platform#2703.

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> - **Exit 0** — der Eintrag trägt alle drei Nachweise: `drill` (Datei existiert),
>   `positivkontrolle: {ref, datum}`, Messpunkt (`slug` in Slug-Form + `built`/`revised` als
>   ISO-Datum). Er darf in die Registry.
> - **Exit 1** — der Eintrag wird **NICHT eingetragen**, sondern geht in die
>   `kandidaten`-Liste der Registry (Tracking: platform#2234).
> - **Exit 2** — Werkzeugfehler (Basis nicht lesbar). Kein Verdikt, also auch kein Eintrag.
>
> `faengt` ersetzt die Positivkontrolle nicht. Alt-Einträge fordert `--neu` nicht rückwirkend
> ein; Nachziehen des Bestands: platform#2703.


## 0g

platform#2211, 2026-08-23 · dritte Ausgabeklasse #2469, 2026-08-30 · Messung heute in `E.5 zusagen`.

> **Der Slug `deferred-item-no-tracking-issue` steht bei 23 Vorkommen und hat seit dem
> 2026-08-02 ein Gate — mit 9 Rückfällen danach.** Der Grund ist gemessen, nicht vermutet
> (`docs/governance/verankerung-kalibrierung-2026-08-23.md`): die bestehenden Gates sind
> Wortlisten, und der reale Rückfall stand als `bewusst **nicht** mitgemacht` da — mit
> Markdown-Fettschrift zwischen den Wörtern, die jedes Muster zerreißt, und einer
> PR-Referenz im selben Satz, die jeden Anker-Test besteht, ohne irgendetwas zu verfolgen.

- **`◌ … Segment(e) UNGEPRUEFT — Zeitbudget erschoepft`** — der Lauf lief, wurde aber nicht
  fertig. Die dritte Klasse, ergänzt am 2026-08-30 ([#2469](https://github.com/achimdehnert/platform/issues/2469)):
  gemessen rund **80 s je Segment** (`qwen2.5:7b`, echter PR-Text), bei elf Segmenten also
  rund eine Viertelstunde — die Sitzung davor brach beide Läufe nach 240 s ab und hatte
  **gar kein** Ergebnis. Auch das ist keine Entwarnung: der ungeprüfte Rest steht in der
  Ausgabe, und die dort genannten Segmente sind schlicht nicht angesehen worden.
  `--budget-sekunden` (Default 300, `0` = unbegrenzt) steuert das.

**Modus `advisory`, bewusst.** Die gemessene Präzision liegt bei 0,50 auf vier echten
PR-Texten (1 Treffer, 1 Fehlalarm, 2 saubere Texte); ein blockierendes Gate mit dieser
Quote wird umgangen statt befolgt. Scharfschaltung erst nach Auswertung des
Kalibrierfensters — als eigene Entscheidung, nicht als Nebeneffekt eines Edits.

**E.5 entfernt am 2026-10-06.** Das Gate `zusage-ohne-verankerung` ist gestrichen und liegt
in `declined/`; damit hat der Zusagen-Prüfer (`tools/verankerung_pruefer.py`) am
Sitzungsende keinen Auftrag mehr. Phase 0g, die Tabellenzeile `E.5 zusagen` und
Checklisten-Zeile 20 sind aus dem Skill genommen, die übrigen Checklisten-Nummern bleiben
stabil. Owner-Wort „V2b go" —
[platform#3785](https://github.com/achimdehnert/platform/issues/3785).

Der letzte Wortlaut von Phase 0g im Skill:

> ### 0g: Zusagen dieser Sitzung gegen Tracking-Artefakte prüfen (PFLICHT — NEU 2026-08-23, platform#2211)
>
> Gemessen in `session_ende_checks.sh` **E.5** (`tools/verankerung_pruefer.py` über die eigenen
> PR-Texte von heute), gedeutet hier. Gate `zusage-ohne-verankerung`, Registry-`module`
> `tools/verankerung_pruefer.py`. Geprüft wird der **Typ** der Zusage, nicht ihr Wortlaut.
>
> - **`✅`** — jede erkannte Zusage trägt ein Tracking-Issue. Weiter.
> - **`⚠️`** — je Stelle **eine** von zwei Antworten, nie keine: Issue anlegen und die Nummer
>   **im selben Abschnitt** des PR-Textes nennen, **oder** die Meldung als Fehlalarm in
>   `docs/governance/verankerung-kalibrierung-2026-08-23.md` notieren (mit Zitat).
> - **`◌ NICHT PRUEFBAR`** (kein Klassifikator erreichbar) und **`◌ … UNGEPRUEFT`**
>   (Zeitbudget erschöpft, rund 80 s je Segment) benennen eine Lücke — die dort genannten
>   Segmente sind nicht angesehen worden.
>
> **Modus `advisory`** bei gemessener Präzision 0,50 — der Befund wird gelesen, nicht
> erzwungen.

Checklisten-Zeile 20 im Wortlaut:

> | 20 | Zusagen-Prüfer: `✅`, oder je Meldung Issue bzw. dokumentierter Fehlalarm (E.5 / 0g) | ☐ |


## 0h

Owner-Freigabe 2026-08-17 (#2036), portiert auf die gekürzte Skill-Fassung am 2026-09-02.

> **Zwei Phasen dieses Skills sind Selbstbeurteilung, und genau dafür hat `/session-retro`
> die Regel „Richter ≠ Angeklagter".** In 0d beurteile ich, ob ich mein eigenes Ziel
> erreicht habe; in 0e, was von meinem eigenen Kontext verschwindet. Beides ist strukturell
> voreingenommen: die Restmenge definiere ich selbst, und was nur im Gesprächsverlauf lebt,
> **fühlt sich für mich vorhanden an**.

Realfall im Anlass-Retro `session-retro-2026-08-17-platform-37e8e0.md`: „Zielzustand
erreicht, mit benannter Restmenge" — Restmenge von mir gesetzt, niemand gegengelesen, und
derselbe Retro musste `refuted_rate 0.00` ausweisen, weil Falsifikation nicht lief.

**Warum nur zwei Phasen.** Der Rest des Skills ist mechanisch — Deploy-Status, Freshness,
Docu-/Template-Drift, Worktree-Reaper, Git-Sync. Dort ist ein Skript reproduzierbar,
protokollierbar und kostenlos; ein Agent wäre teurer und unzuverlässiger.

**Warum `/session-start` keine Subagenten bekommt.** Am Sitzungsanfang **ist** der Agent
der frische Kontext — das Problem, das Subagenten lösen, existiert dort nicht. Ein Agent,
der den Handover liest und zusammenfasst, schöbe eine Verdichtungsschicht zwischen Agent
und Stand, den er im Original braucht. Der Engpass dort ist Ausführungstreue, und die löst
eine Checkliste.

**Selbstbetreffend.** Diese Änderung erweitert den eigenen Handlungsspielraum (mehr Agenten
pro Sitzung). Sie stand deshalb allein in ihrem PR, ungebündelt, und geht auf eine wörtliche
Owner-Freigabe zurück.

**Kosten.** ~55k Token je eng geführtem Agenten (gemessen, `/session-retro` Phase 0) ⇒ rund
110k je Sitzungsende ab `full`. Kein Rundungsfehler — daher der Footprint-Schalter.

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> 0d und 0e sind **Selbstbeurteilung** — die Restmenge setze ich selbst, und was nur im
> Gesprächsverlauf lebt, fühlt sich für mich vorhanden an. Für genau das führt
> `/session-retro` seit jeher „Richter ≠ Angeklagter".

> - **Agent 1 (zu 0d)** bekommt nur Zielzustand und Artefakte, **nicht** meine Erzählung:
>   je Kriterium ERFÜLLT / NICHT ERFÜLLT / NICHT PRÜFBAR **mit Beleg**. Weicht sein Urteil
>   ab, gewinnt **seins** im Stand-Block.
> - **Agent 2 (zu 0e)** bekommt **ausschließlich die durablen Artefakte** und die drei
>   0e-Fragen. Er darf den Gesprächsverlauf **nicht** sehen — das ist der Punkt.
> - Beide Ergebnisse in den Stand-Block, auch wenn sie unbequem sind.
> - **Subagenten untersagt?** 0d/0e inline, aber den Bruch **im Stand-Block benennen**.
>
> **Kosten, damit die Entscheidung bewusst fällt:** ~55k Token je Agent ⇒ **~110k je
> Sitzungsende** dieser Klasse. Deshalb der Footprint-Schalter statt „immer".


## 0i

NEU 2026-09-11, KONZ-platform-059 / #3079 — Gegenstück zu Start 1.8.

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> `python3 tools/chat_agent/auftragsraum.py offen --block` (nur platform-Sessions). Exit 1 heißt:
> eine Owner-Korrektur aus dem Chat-Raum hat noch kein Regel-Artefakt — je Zeile `regel
> <nachricht_id> --why …` ausführen oder den Verzicht mit Grund im Stand-Block nennen. Offene
> Aufträge ohne Issue werden hier gemeldet, nicht angelegt (das bleibt Phase 1.8 des Starts).
> Betriebsakte: `docs/betrieb/auftragsraum.md`.


## 1

**Aus dem Skill ausgelagert (V2b), Wortlaut von Phase 1:**

> Outline-Schreiben **nicht hier inline duplizieren** — Klassifikation, Cross-Repo-Tagging und
> Tool-Wahl macht `/knowledge-capture`. session-ende ruft es und **prüft den Erfolg**:
> Doc-URL/ID zurück? → für Phase 2 merken. Kein Ergebnis? → offener Punkt im Handover (0b).


## 1b

Docu-Drift-Check, 2026-04-23 · gestrichen 2026-09-02 (Streichkandidat S2 des Streichplans: der Verarbeiter läuft als CI `docu-update-agent.yml`, 6 von 10 `docu-update`-Issues offen, älteste 31 Tage — Median-Liegezeit rund 28 Tage gegen die K3-Schwelle von 14). Der Erzeuger-Text im Wortlaut:

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


**Aus dem Skill ausgelagert (V2b), Wortlaut der Zeiger-Phase 1b:**

> Der Verarbeiter läuft als CI (`.github/workflows/docu-update-agent.yml`); die Erzeugung von
> `[docu-update]`-Issues ist kein Schritt dieses Skills mehr. Fällt beim Committen (3.1) eine
> Doku-Lücke auf — README-Version ≠ Code-Version, leeres CHANGELOG, neue Module ohne Doku —,
> gehört sie als Issue **ins betroffene Repo**, nicht in `platform`.


## 1c

Template-Drift-Check, 2026-04-28 · heute Runner-Phase `E.6 template-drift`.

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


## 2

CLI-statt-MCP-Begründung 2026-07 · `--session-id`-Realfall A1, 2026-07-20.

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


**Aus dem Skill ausgelagert (V2b), Wortlaut aus Phase 2:**

> Primärer Pfad ist die CLI `platform/tools/session-memory`, **nicht** der MCP: sie wirkt
> unabhängig von der MCP-Bindung in jedem Repo.

> → **`--session-id <slug>` bei Parallelbetrieb** (`tools/session-leases --repo <repo>` zeigt
>   es). Ohne ihn weicht die CLI auf `<key>-2`, `-3`, … aus statt zu überschreiben;
>   `--allow-overwrite` erzwingt das alte Verhalten.
> → **Error-Patterns** (nur bei Bug-Fixes): gleiche CLI, `--type error_pattern`,
>   `--key "error:<repo>:<YYYYMMDD>-<shortid>"`, Inhalt Symptom/Root Cause/Fix/Prevention.
> → `entry_type` default `context`; `--type`-Werte: open_task | decision | lesson_learned |
>   error_pattern | repo_context | agent_handoff.


## 3.1

Drei harte Lehren · PR-Kadenz session-retro 2026-07-02 · `[skip ci]`-Messung platform#1992, 2026-08-15.

> 🌀 **Drei harte Lehren fließen hier ein:**
> 1. `feedback_git_add_all_swept_artifacts` — pauschales `git add -A` schwemmte `.pyc`/
>    `.coverage`/Editor-Artefakte in Commits → **nie ungefiltert `add -A`**.
> 2. `feedback_session_attribution_by_conversation_not_date` — im geteilten Tree können
>    dirty Files von PARALLELEN Sessions stammen → nur committen, was DIESE Session
>    nachweislich angefasst hat (eigene Turn-Historie); Fremdes dem User melden.
> 3. **ADR-242 Branch-Protection:** `main` ist in etlichen Repos geschützt (`ci / gate` /
>    `guardian` required) — ein Direkt-Push auf main scheitert dort mit GH013.

**PR-Kadenz-Hygiene (session-retro 2026-07-02, PK-3/PK-4):**
- **Rebase-on-ready (R-6):** `gh pr update-branch` erst **unmittelbar vor** dem finalen
  Push/Merge, nicht früh — verkürzt das Konflikt-Fenster gegen zwischenzeitlich gemergte
  main-Änderungen (Realfall: 2 manuelle Textkonflikte #829/#832).
- **Bündeln statt Kleinst-PR-Schwarm (R-7):** thematisch gekoppelte Kleinfixes in **wenige,
  breitere** PRs zusammenfassen, wo sie nicht kollidieren — 11/17 PRs dieser Session trugen
  Catch-up-Merge-Tax durch sequenzielles Selbst-Mergen gegen den wandernden eigenen main.

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


**Aus dem Skill ausgelagert (V2b), Wortlaut zu `[skip ci]`:**

> → **`[skip ci]` gehört nur ins Squash-Subject beim Mergen** (`gh pr merge --squash --subject
>   "… [skip ci]"`) — **niemals** in einen Commit eines offenen PR-Branches, auch nicht
>   zitiert: GitHub matcht den Marker im gesamten Commit-Body und überspringt dann **alle**
>   Läufe, auch das `pull_request`-Event. Erkennungsmerkmal ist ein **leerer Check-Rollup** —
>   der ist kein „läuft noch", sondern der Befund. Reparatur: `git commit --amend` ohne den
>   Token + Force-Push; close/reopen ist überflüssig.


## 3.1c

Worktree-Reaper, Retro 2026-06-14 · gestrichen 2026-09-02 (Streichkandidat S3: Gate-Registry `worktree-midsession-accumulation` `revision_note` vom 2026-08-20 und `session_start_checks.sh` Phase 0.4.5 räumen jedes Repo mit Lease; ein zweiter Lauf am Sitzungsende ist dieselbe Mechanik doppelt — Runner-Phase `E.8` steht deshalb bewusst auf SKIP mit Hinweis). · wieder eingesetzt 2026-09-14 in anderer Form (Retro oqu6Z6 §5a / #21): nicht als zweiter Reaper-Lauf, sondern als `git worktree prune` plus Altersgrenze (FAIL) — die SKIP-Zeile hatte 13 Bäume, zwei davon `prunable`, folgenlos stehen lassen.

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


**Aus dem Skill ausgelagert (V2b), Wortlaut von 3.1b:**

> `find ${GITHUB_DIR:-$HOME/github}/ -maxdepth 4 \( -name "*.fixed" -o -name "*.updated" -o
> -name "*.new" \)` → prüfen ob übernommen, dann löschen; sonst User warnen. Gemergte
> Session-Worktrees räumt `session_start_checks.sh` 0.4.5 über **alle** Leases ab; `E.8` führt
> `git worktree prune` aus und macht jeden Baum über der Altersgrenze zum ❌ (seit 2026-09-14,
> Retro oqu6Z6 #21).


## 3.2

project-facts-SSoT-Begründung · ADR-230-Hinweis · Version-After-Banner (heute Runner-Phase `E.0`).

```bash
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


**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> → `platform` selbst ist geschützt (ADR-242): dirty `platform` geht über Worktree-Branch +
>   PR, nie per Direkt-Push auf `main`.
> → `project-facts.md` erzeugt der CI-Cron `gen-project-facts.yml` (Mo 04:00 UTC) — hier
>   nicht zusätzlich. On-demand: `python3 platform/scripts/gen_project_facts.py --repo <name>`.
> → Für **CC-Skills** ist `platform/tools/cc-skill-dist/` der kanonische Weg (Messung `E.9`).


## 3.3

Finale Dirty-Prüfung · heute Runner-Phase `E.7 dirty-repos`.

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


## 3.4

Shell-Hang-Fallback, gestrichen 2026-09-02 (Streichkandidat S4: der Block empfahl `branch: "main"`, während dieselbe Datei zwei Abschnitte höher `main` als geschützt beschreibt — ADR-242/GH013 —, und die Einschränkung „nur für public Repos" ist eine Token-Frage, keine Sichtbarkeits-Frage). Der Wortlaut:

Falls Shell blockiert ist, nutze GitHub MCP für kritische Pushes (`<OWNER>` aus
dem git-Remote, siehe Phase 1b):
```
mcp__github__push_files(owner: <OWNER>, repo: "<repo>", branch: "main",
  files: [{"path": "<pfad>", "content": "<inhalt>"}],
  message: "session-ende: <beschreibung>")
```
→ Funktioniert nur für **public Repos** oder Repos mit Write-Token.
→ Für private Repos: User muss manuell pushen.


## 3.4-abschluss

Phase 3.4 Abschluss-Maßnahmen, NEU 2026-10-05 (Owner-Wort „dieses Vorgehen sollten wir
etablieren", platform#3716). Nicht zu verwechseln mit `#3.4`, dem gestrichenen
Shell-Hang-Fallback unter derselben Nummer.

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> Die letzte Antwort der Sitzung ist eine Entscheidungsvorlage, kein Prüfprotokoll:
>
> 1. **Erster Satz:** ob die Sitzung gefahrlos geschlossen werden kann — er muss zur
>    Clear-Freigabe-Zeile (3.5) passen.
> 2. **Nummerierte Maßnahmenliste**, je Zeile: stabiles Kürzel · was zu entscheiden ist ·
>    die Empfehlung · ein Link auf ein bestehendes Issue oder einen PR. Getrennt nach
>    „dein Wort nötig" und „kann ich ohne dich".
> 3. **Beispielantwort** am Ende („Z1 Z3 go, Z4 Liste"), damit die Freigabe per Kürzel geht.
>
> Belege eigener Prüfungen stehen in einem Satz, nicht als eigene Antwort. Die Liste ersetzt
> kein Tracking: eine Zeile ohne Issue-/PR-Link ist ein Verstoß gegen 0e. Gibt es nichts zu
> entscheiden, entfällt die Liste — der erste Satz bleibt.


## 3.5

Owner-Rückmeldung 2026-08-30.

> Phase 0e stellt die Frage „was überlebt den Kontext-Verlust?", aber die Antwort blieb
> bisher ein internes Häkchen (Checkliste-Zeile „Clear-Härte") — sichtbar nur, wer die
> Checkliste selbst aufklappt. Owner wörtlich (2026-08-30): „session-ende liefert häufig
> keinen sauberen Zustand für clear, ich muss immer nachfragen." Der Fix ist kein
> automatisches `/clear` (Phase 0e begründet das explizit ab) — sondern die Antwort auf die
> Frage laut und zuletzt auszusprechen, statt sie in einer Checkliste verschwinden zu lassen.


**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> - **🔴 CLEAR-FREIGABE: NEIN — <konkreter Grund>** — mindestens ein Punkt **aus dieser
>   Sitzung** offen (selbst dirty gemachtes Repo, offene Checkliste-Zeile, unbeantwortete oder
>   ungefixte 0e-Frage). Der Grund benennt das fehlende Ding, nicht nur „nicht grün".
>
> **Fremder Stand hemmt die Freigabe nicht** (Owner-Weisung 2026-09-10): ein dirty Repo aus
> einer anderen Sitzung, ein rotes Deploy fremder Herkunft, ein konkurrierender Handover-PR —
> das wird **gemeldet** (Board-Zeile) und blockiert die Zeile **nicht**. Die Freigabe misst
> ausschließlich, ob **diese** Sitzung etwas Ungesichertes zurücklässt. Prüffrage: „habe ich
> das dirty gemacht?" — beantwortet mit einem Blick auf Änderungszeit und Turn-Historie, nicht
> per Vermutung. Wer fremden Stand zur eigenen Bremse macht, liefert eine Freigabe, die
> nie 🟢 wird, und trainiert damit das Überlesen der Zeile.
>
> Keine dritte Formulierung, kein Weglassen dieser Zeile.


## mcp-quick-reference

Gestrichen 2026-09-02 (Streichkandidat S5: die `mcpN_`-Prefixe stammen aus der Windsurf-Ära, der Skill erklärte `project-facts.md` in derselben Sektion zur Quelle, und `~/.claude/policies/claude-skills.md` Z. 10 hält fest, dass Windsurf nicht mehr zum Coden genutzt wird). Der Wortlaut:

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


## anti-patterns

**Aus dem Skill ausgelagert (V2b), Wortlaut der Anti-Patterns:**

> - ❌ Owner/Org/MCP-Prefixe/IPs hardcoden — Owner aus dem git-Remote ableiten, Tools mit
>   stabilen CC-Namen nennen, `mcpN_`-Nummern nie aus einem Skill-Text übernehmen
>   (`project-facts.md` + `ToolSearch` sind die Quelle).
> - ❌ Outline-Schreiben hier inline duplizieren statt an `/knowledge-capture` zu delegieren
>   und den **Erfolg zu prüfen**.
> - ❌ `git push`, wenn der User „nicht pushen" sagt oder ein PR-Review läuft (3.1).
> - ❌ **`git add -A` — in keiner Phase.** Immer explizite Pfade nach Sichtung
>   (🌀 `feedback_git_add_all_swept_artifacts`: .pyc/.coverage landeten in Commits).
> - ❌ Fremd-Session-Artefakte einsammeln — dirty Files ohne Bezug zur eigenen Turn-Historie
>   melden statt committen (🌀 Session-Attribution, Realfall #734).
> - ❌ Direkt-Push auf geschützte `main`-Branches (ADR-242) — Session-Branch + PR ist der Pfad.
> - ❌ Memory-Calls mit der alten Windsurf-Signatur (`entry: {entry_id…}`) — die CC-Signatur
>   ist flach mit `entry_key`.
> - ❌ Eine Runner-Zeile mit `SKIP`/`◌` als Entwarnung verbuchen (E.R).
>
> **Idempotenz:** Re-Run ist sicher — Commits/Sync sind wiederholbar, der Runner ist read-only,
> Memory-Upserts deduplizieren per `content_hash`.


## abschluss-selbstcheck

Retro `session-retro-2026-07-15-platform-c494a2`, Befund #8.

> **Pflicht-Selbstcheck (nicht überspringen):** Zähle die `###`/`##`-Phasen-Überschriften
> oben im Dokument, die als PFLICHT/NEU markiert sind, gegen diese Tabelle — jede neue
> Pflicht-Phase braucht eine eigene Zeile hier. Diese Checkliste selbst driftete bereits
> einmal aus dem Takt: Phase 0a-handover-pr wurde am 2026-07-14 ergänzt, aber erst am
> 2026-07-15 (Retro c494a2, Befund #8) als fehlende Checklisten-Zeile bemerkt — eine
> Session hatte die Phase im Dokument vorliegen, aber nicht ausgeführt, weil die
> Abschluss-Checkliste sie nicht abfragte.


**Aus dem Skill ausgelagert (V2b), Checklisten-Zeilen vor der Verdichtung** (Zeile 20 steht
unter `#0g`):

> | 11 | Erledigte/verschobene Prios in Handover UND Memory nachgezogen (0c) — Fragment-Modus: eigenes Fragment geschrieben, `pruefen` grün (0b-fragment) | ☐ |
> | 26 | Letzte Antwort: erster Satz „schließbar ja/nein", Maßnahmen mit Empfehlung + Link, Beispielantwort — oder nichts zu entscheiden (3.4) | ☐ |


## laufzeit

Runner-Laufzeit, platform#3373 (2026-09-22). Messreihe: `laufzeit.md` im selben Verzeichnis.

**Aus dem Skill ausgelagert (V2b), Wortlaut:**

> Der Runner endet mit einer `LAUFZEIT:`-Zeile (Gesamtdauer + fünf teuerste Phasen);
> `SESSION_CHECKS_TIMING=voll` gibt jede Phase einzeln aus. Die Prüfungen laufen seit
> [#3373](https://github.com/achimdehnert/platform/issues/3373) nebenläufig —
> `SESSION_CHECKS_PARALLEL` (Default 8) stellt das enger, `=1` schaltet auf den alten
> sequenziellen Ablauf zurück, `SESSION_CHECKS_VORLAUF_BEHALTEN=1` behält `.out`/`.err`/`.rc`
> je Auftrag für die Fehlersuche. E.6 prüft die Repos seither ebenfalls nebenläufig
> (`DRIFT_CHECK_PARALLEL`, Default 6; `=1` = alter Ablauf) — es bleibt mit Abstand die
> teuerste Phase, also dort zuerst nachsehen, wenn die Zeile auffällig steigt. Herleitung und
> Messung: `docs/governance/session-skills-lehren/laufzeit.md`.


## changelog-historie

Alle Einträge im Wortlaut. Im Skill stehen seit der Kürzung vom 2026-10-06 (V2b,
[platform#3785](https://github.com/achimdehnert/platform/issues/3785)) nur noch die letzten
drei als je eine Zeile (Policy seit platform#2696). Die folgenden Einträge standen bis dahin
wörtlich im Skill:

- 2026-10-05: **Runner-Phase E.11 main-status** (Retro 8a0235 R14). Anlass: main war nach einem
  eigenen Merge 30 Minuten rot, eine fremde Sitzung mergte darauf, und ein zweiter Workflow blieb
  stundenlang unbemerkt rot. E.11 meldet je berührtem Repo die Workflows, deren jüngster
  Push-Lauf von heute auf main rot ist. Geplante Audit-Läufe zählen nicht, weil sie absichtlich
  rot enden. Advisory, deshalb keine neue Checklisten-Zeile: Zeile 0 spiegelt jede WARN.
  Zusätzlich fragen E.1 und E.11 jetzt unter dem Owner des berührten Repos ab. Bisher fragte E.1
  ein Repo aus einer anderen Org unter dem falschen Owner ab und meldete „kein-Deploy“, obwohl
  in Wahrheit ein Messfehler vorlag.
- 2026-10-05: **Phase 3.4 Abschluss-Maßnahmen (PFLICHT) + Checklisten-Zeile 26** (Owner-Wort
  „dieses Vorgehen sollten wir etablieren", platform#3716). Anlass: Ein Abschluss, der die
  eigenen Prüfungen nacherzählte, ließ offen, was zu entscheiden war.
- 2026-09-22: **Runner misst sich selbst und wartet nebenläufig** (platform#3373). Neue
  `LAUFZEIT:`-Zeile; E.1–E.7/E.9/E.10 starten zusammen und werden an ihrer Phasenstelle
  geerntet, die bis zu drei Zusagen-Prüfungen in E.5 laufen untereinander nebeneinander,
  E.9 prüft seine drei Lanes in EINEM Auftrag (drei gleichzeitige `git fetch` stritten um
  dieselbe Ref-Sperre). Weil danach eine einzige Phase 254 von 264 s ausmachte, prüft auch
  `scripts/drift_check.py` die Repos jetzt nebenläufig (259 s → 92 s, Ausgabe zeichengleich).
  Gesamt 302,5 s → 94,9 s, Status aller 11 Phasen unverändert. Messung:
  `docs/governance/session-skills-lehren/laufzeit.md`.
- 2026-09-24: **Sitzungsabgrenzung für E.3 und E.10** (#2234, Retro #3543 Befunde #2/#4) —
  Leases tragen `claude_session`; E.10 prüft mit `--session-id` nur die PRs der eigenen
  Branches und nennt Anzahl + Refs (vorher: 35 kontoweite Befunde, eine abgeschnittene
  Zeile sichtbar, das eigene offene Issue nicht). E.3 im Fragment-Modus ❌, wenn die
  Sitzung nach ihrem jüngsten Fragment weitere PRs anlegte (vorher: grün ab dem ersten
  Fragment, obwohl drei Stunden Arbeit folgten).
- 2026-09-16: **Phase 0b-fragment + Runner mit `--session-id`** (#1944 K6, KONZ-platform-027) —
  in Repos mit `docs/handover.d/` schreibt jede Sitzung ihr eigenes Fragment statt die
  geteilten Handover-Dateien zu ändern; `E.3` prüft das eigene Fragment. Anlass: parallele
  Sitzungen sind in Querschnitt-Repos nicht vermeidbar (Owner 2026-09-16), 8 der 61
  Kollisionspaare in 14 Tagen lagen auf `AGENT_HANDOVER.md`.
- 2026-09-11: **Phase 0i Auftragsraum + Checklisten-Zeile 24** (KONZ-platform-059, #3079) —
  `offen --block` schließt die Lernschleife: eine Owner-Korrektur aus dem Chat-Raum ohne
  Regel-Artefakt hemmt das Sitzungsende, bis `regel` das Artefakt anlegt oder der Verzicht
  begründet ist. Gegenstück zu Start 1.8.
- 2026-09-10: **3.5 misst nur die eigene Sitzung + Checklisten-Zeile 6 gescharft** —
  Owner wörtlich: „fremde dirty sollten kein clear hemmen !! -> mehr fokus auf eigenen
  sitzung !". Anlass: eine Sitzung ohne jede Repo-Änderung lieferte 🔴, weil drei fremde
  Repos seit Tagen dirty lagen. Fremder Stand wird gemeldet, nicht zur eigenen Bremse.
- 2026-09-02: **Kontext-Diät + Runner-Verdrahtung** (#2690 K5, +K1) — 55 516 → ~20 400 B.
  Phase `E.R` ruft `tools/session_ende_checks.sh` (E.0–E.9) und ersetzt die mechanischen
  Abschnitte; Lehren/Historie in `session-skills-lehren/ende.md`; gestrichen: S2–S5.
- 2026-09-02: **Phase 0f-verankerung (PFLICHT) + Checklisten-Zeile 22** (#2690 K4) — ein Gate
  kommt nur mit Drill, Positivkontrolle und Messpunkt in die Registry. Anlass: 14 von 33
  Gates rückfällig, 0 von 31 Einträgen mit Beleg eines echten Treffers (#2374, #2678).

Ältere Einträge (schon vor 2026-10-06 hier):

- 2026-09-02: **Phase 0h Fremder Blick (PFLICHT ab `full`) + Checklisten-Zeile 23** (#2036) —
  Owner-Freigabe für Subagenten in den Session-Skills, ausdrücklich **selbstbetreffend**.
  Nur 0d und 0e bekommen fremden Kontext; der mechanische Rest bleibt Skript. Der Zweig
  stammt vom 2026-08-17 und hieß dort `0g`; `main` vergab denselben Buchstaben inzwischen
  an #2211, deshalb `0h` und Zeile 23. Beim Nachziehen **neu geschrieben** statt gemergt:
  `main` hatte die Datei zwischenzeitlich von 55 auf 20 kB gekürzt, ein Merge hätte das
  zurückgedreht. Herleitung in `LEHREN#0h`.

- 2026-08-20: **Phase 0f um rückfällige Gates erweitert** + Checklisten-Zeile 17. Ein vom
  Session-Start gemeldetes rückfälliges Gate braucht denselben Abschluss wie ein
  Fremd-Repo-Befund: behandelt (Registry im selben PR nachgezogen) oder Verzicht mit Grund.
  Ohne diese Zeile hielt jede Sitzung das Gate für die Aufgabe der nächsten — genau die
  Mechanik, mit der ein Gate 16 Rückfälle sammelte, ohne dass es je jemand anfasste.
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
