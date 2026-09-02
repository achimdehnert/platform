---
retro_schema: 1
date: 2026-09-02
repo_scope: [meiki-hub, frist-hub, iil-pet-portal]
session_id: m1zgqt
footprint: full
findings_total: 18
findings_survived: 16
refuted_rate: 0.11
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 2
  architektur_design: 3
  code_konventionstreue: 2
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [onclick-ohne-funktion, publish-ohne-darstellungspruefung, generierte-zahl-weicht-von-quelle-ab, gate-stale-local-clone-as-ground-truth-wirkungslos, maus-only-bedienelement-im-kd]
recurring_findings: [stale-local-clone-as-ground-truth]
gates_caught: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded, deferred-item-no-tracking-issue]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 1 neu"
streichkandidaten: [frist-hub-shared-kd-nav-ohne-leser]
---

# Session-Retro 2026-09-02 · meiki-hub / frist-hub / iil-pet-portal

## 1. Executive Summary

- Der Auftrag (fuenf Klickdummies aus frist-hub im Modul-KD des meiki-hub zusammenfuehren, Einstiegsseite bauen, veroeffentlichen) ist inhaltlich erfuellt: 21 Bildschirme uebernommen, die Dublette Fristenmanagement aufgeloest, kein Inhalt verloren (drei unabhaengige Pruefer, Datei-fuer-Datei-Vergleich).
- **Der gemeldete Weg ist repariert, die gemeldete URL nicht.** Die Portal-Wurzelseite verlinkt meiki-hub jetzt auf die Uebersicht statt auf den nackten Ordner; bei Direkteingabe von `https://iil.pet/kd/meiki-hub/` bleibt es bei 404. Die Widerlegungsbahn hat den urspruenglich schaerferen Vorwurf entkraeftet: eine Startseite auf Repo-Ebene hat 1 von 25 Repos, die Sitemap-Konvention 16 von 25 — die Sitzung folgte der Mehrheit.
- **Vier weitere Fehler sind live veroeffentlicht:** acht Knoepfe ohne Funktion, ein Handbuch-Knopf ins Leere, eine falsche Zahl auf der neuen Uebersichtsseite (64 statt 68) und eine Portal-Zeile, die fuer frist-hub weiter mit "5 Klickdummys" wirbt.
- **Der teuerste Einzelfehler war ein veralteter Quell-Klon:** portiert wurde aus einem drei Commits alten lokalen frist-hub, gefunden nur durch Zufall. Dafuer existiert seit dem 2026-08-02 ein Gate — es sieht den Fall nicht, weil es nur das Sitzungs-Repo prueft, nicht ein fremdes Repo, das als Inhaltsquelle gelesen wird. Damit ist es rueckfaellig.
- **Zwei Dimensionen kamen erst spaet ans Licht:** die Barrierefreiheit (33 Bedienelemente mit ARIA-Rolle, null Tastatur-Handler) fand erst die Widerlegungsbahn, und die Scope-Spiegelung vor dem Veroeffentlichen stand nur im Chat, durabel erst danach.
- **Drei Gates haben heute gegriffen** (Evidenz-Check 2x, Scope-Checkpoint, Tracking-Artefakt) — alle drei Male hat der Melder eine falsche oder unverankerte Aussage gestoppt, bevor sie stehen blieb. Das ist der Wirksamkeits-Beleg, kein Rueckfall.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Die gemeldete URL `iil.pet/kd/meiki-hub/` ist bei Direkteingabe weiterhin 404 — auf Repo-Ebene liegt keine Startseite | fehlende Validierung | mittel | SURVIVES | `git cat-file -e origin/main:kd/meiki-hub/index.html` → fatal; Portal hat weder `404.html` noch `_config.yml`, `gh-pages.yml` setzt `.nojekyll` → GitHub Pages liefert die Standard-404. **Rahmen von der Widerlegungsbahn korrigiert:** eine Startseite auf Repo-Ebene hat 1 von 25 Repos, die Sitemap-Konvention 16 von 25 — die Sitzung folgte der Mehrheit. Der *gemeldete Weg* ist repariert (Portal-Commit 43e2cd6 aendert die Zeile von `./meiki-hub/` auf `./meiki-hub/klickdummy/sitemap/`) | neu |
| 2 | Acht `onclick`-Handler zeigen auf Funktionen, die im Modul-KD nicht existieren (`editRule`, `submitForFreigabe`, `freigeben`, `zurueckgeben`, `setPostkorb`, `setKlass`, `toggleAnh`, `setAnforderung`) | fehlende Validierung | kritisch | SURVIVES | Handler-Namen aus `modules/*/screens.html` gegen `shell.html` geprueft, 0 Definitionen; dieselben Funktionen je 1x in `frist-hub:docs/_archiv/*/shell.html` | neu |
| 3 | Portal-Wurzelseite nennt fuer frist-hub "5 Klickdummys", real liegt dort nur die Verweis-Seite | fehlende Validierung | hoch | SURVIVES | `iil-pet-portal origin/main:kd/index.html`; Quelle ist `frist-hub:klickdummy/_shared/kd-tree.json` mit toten Pfaden | neu, verankert frist-hub#129 |
| 4 | "FB <Zahl>" 26x und "Guenzburg" 3x hartkodiert in den neuen Packs; die Gate-Regel fuer Organisationsbezeichnungen kennt weder `FB \d+` noch Ortsnamen | Werkzeug | hoch | SURVIVES | `org_woerter`-Regex in `scripts/check-klickdummy-manifest.py`; `manifest-check` auf PR #207 SUCCESS trotz der Hardcodes | neu |
| 5 | Portiert wurde aus einem lokalen frist-hub-Klon, der drei Commits hinter `origin/main` lag; Spec, Bildschirme, 12 Bildschirmfotos und ein Handbuch mussten nachgezogen werden | Prozessluecke | hoch | SURVIVES | Commits 757fe90 → 87e5a16; frist-hub#127 war im lokalen Klon nicht enthalten | **Gate rueckfaellig** (`stale-local-clone-as-ground-truth`, x9) |
| 6 | Kein Mechanismus prueft die Darstellung im Portal nach der Veroeffentlichung; der einzige Post-Deploy-Test prueft nur, ob `iil.pet/` auf das Zugangs-Gate umleitet | Prozessluecke | hoch | SURVIVES | `grep -rilE 'playwright\|smoke\|verify'` ueber `.github/workflows/` + `scripts/` der drei Repos: meiki-hub 5, frist-hub 0, iil-pet-portal 3 Treffer — kein Treffer prueft die ausgelieferte Seite. Der einzige Post-Deploy-Test ist `iil-pet-portal:.github/workflows/gh-pages.yml:128-139` und prueft nur, ob `https://iil.pet/` per 302 auf `cloudflareaccess.com` umleitet | neu |
| 7 | Die neue Uebersichtsseite nennt 64 spezifizierte Bildschirme, die Quelle sagt 68 — `buergerportal-bevollmaechtigte` hat kein Modul und faellt aus der Summe | Werkzeug | mittel | SURVIVES | `abdeckung.json`: 42 gebaut + 19 offen + 7 teilweise = 68; veroeffentlichte Seite: "64 spezifizierte" | neu |
| 8 | `window.open('handout.html')` an neun Stellen; die Datei liegt unter `specs/`, nicht neben dem Pack → 404 | fehlende Validierung | mittel | SURVIVES | `modules/dokumentenworkflow-wohngeld/screens.html`; `git ls-tree` zeigt `handout.html` nur unter `specs/` | neu |
| 9 | Vier ungescopte `:root`-Bloecke; von 10 gemeinsamen Variablen weicht `--ok` im Wert ab (`#237a30` vs `#2e8b3d`). Der Commit behauptete "0 ungescopte Regeln, keine Variablen-Kollision" | Kommunikation | mittel | SURVIVES | `grep -c ':root'` je Pack = 1; normalisierter Wertvergleich: 9 gleich, 1 ungleich | neu |
| 10 | Doppelte Element-IDs ueber Module hinweg (`id="nav"` 9x in zwei Packs, `id="stepper"` 9x) — heute ohne Laufzeitwirkung, weil kein Selektor darauf zugreift | Wissensluecke | mittel | SURVIVES | Vorkommen ausgezaehlt; `getElementById('nav')` und bare `#nav`-Selektoren: 0 Treffer | neu |
| 11 | `docs/handouts/kd-dokumentenworkflow-wohngeld/build.py` in frist-hub schreibt weiter auf den alten, jetzt archivierten Pfad — der naechste Lauf stellt die kaputte Struktur wieder her | Prozessluecke | mittel | SURVIVES | `build.py` Z.29/33, Zielpfad existiert auf `origin/main` nicht mehr | neu |
| 12 | Zwei Restpunkte aus einem frueheren Kommentar auf #199 (19 offene Spec-Bildschirme, Aufloesung ADR-031–034/036) blieben ohne eigenes verlinktes Artefakt | Prozessluecke | mittel | SURVIVES | Issue #199, Kommentar 1, Zeilen mit Status offen, kein Link daneben | `deferred-item-no-tracking-issue` x36 |
| 13 | Der Regex-Fix am Pruefwerkzeug kam ohne Regressionstest | fehlende Validierung | niedrig | SURVIVES | `git show 3f7b448 --stat`: keine Datei unter `tests/` | neu |
| 14 | Zwei Arbeitsverzeichnisse und ihre Reservierungen wurden nach dem Merge nicht geschlossen | Prozessluecke | niedrig | SURVIVES | `/home/devuser/.repo-session/leases/2026-09-02-achim-dehnert-kd-konsolidierung-frist-hub-155422.json` und `…-kd-verweis-auf-meiki-161240.json` tragen kein `.closed`; im selben Verzeichnis liegen 3401 geschlossene zum Vergleich | `worktree-midsession-accumulation` x5 |
| 15 | Die uebernommenen Bildschirme sind maus-only: 33 Elemente tragen `tabindex="0"` mit einer ARIA-Rolle (`role="link"`, `role="checkbox"`) und `onclick`, aber im gesamten Modul-KD gibt es **null** Tastatur-Handler. Fuer einen buergernahen LRA-Workload ist der Klickdummy der Ort, an dem Barrierefreiheit mit dem Amt vereinbart wird (BITV 2.0) | Wissensluecke | hoch | SURVIVES | `grep -ciE 'keydown\|keypress'` ueber alle `.html`/`.js` unter `klickdummy/modul` = 0; `tabindex="0"` in `modules/dokumentenworkflow-wohngeld/screens.html` = 33. Von der Widerlegungsbahn gefunden, keiner der drei Finder hatte die Dimension | neu |
| 16 | Der gewachsene Scope wurde vor dem Veroeffentlichungsschritt nur im Chat gespiegelt, durabel erst danach. Der Kommentar von 15:38Z nennt weder Repo-Zahl noch das Portal als Schreibziel noch einen Prod-Schritt und stellt keine Frage — er protokolliert eine ausstehende Freigabe, die die Sitzung 48 Minuten spaeter selbst beantwortete | Kommunikation | mittel | SURVIVES | Issue #199 Kommentar 15:38:56Z gegen Ingest-Run 33654932004 (16:26:33Z) und Abschluss-Kommentar 16:29:22Z ("nachgetragen"). Von der Widerlegungsbahn aufgeworfen; ihre erste Begruendung (portal#44 als Prod-Schritt, 14:36:21Z) traegt **nicht** — dieser Merge gehoert zu einer frueheren Sitzung desselben Tages, meine Sitzung beginnt mit dem Kommentar 15:38:56Z und der Reservierung 15:54:22Z | gefangen von `scope-checkpoint-not-durably-recorded` |
| R1 | "88/68 sind nicht unabhaengig nachpruefbar" | — | — | **REFUTED** | Skeptiker A: `grep -o "<section data-screen='..."` ueber alle Packs = 88; YAML-Summe ueber 12 Specs = 68. Der Finder hatte nach falschen Mustern gesucht | — |
| R2 | "Der Merge in eine gemeinsame Shell war eine verfruehte Festlegung; die Sitemap allein haette gereicht" | — | — | **REFUTED** | Skeptiker B: Der Ein-Ziel-KD stand als Owner-Entscheid im Issue-Body (13:48Z), vor dem 404-Fund (15:38Z); Motiv war die Dublette, nicht die Landingpage | — |

## 3. Scorecard

| Dimension | Wert | Verankert an |
|---|---|---|
| zielerreichung | 2 | #2, #3, #7 — drei sichtbare Fehler im veroeffentlichten Ergebnis; #1 als Anker von der Widerlegungsbahn entkraeftet |
| architektur_design | 3 | R2 (Merge-Entscheidung haelt) gegen #9/#10 (Scoping halb durchgezogen) |
| code_konventionstreue | 2 | #4 — 29 hartkodierte Organisations- und Ortsangaben im selben PR, der genau dafuer die Shell erweitert hat; dazu #15 (keine Tastaturbedienung) |
| risiko_debt | 2 | #1, #2, #3, #7, #8 live veroeffentlicht; nur #3 war zum Retro-Zeitpunkt verankert |
| prozess_effizienz | 3 | #5 — ein vermeidbarer Rework-Zyklus, sonst durchgaengig von der Analyse bis zur Veroeffentlichung |
| entscheidungsqualitaet | 3 | R2 haelt die Architektur-Entscheidung; #9 und #16 zeigen Aussagen, die weiter gingen als die Pruefung |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Nach der Veroeffentlichung wurden Portal-Baum und Linkziel geprueft, nie die vom Owner gemeldete URL selbst | Jede vom Owner woertlich genannte URL kommt nach dem Publish einmal als Aufruf zurueck — sie ist die Abnahmebedingung, nicht ein Ableger davon | #1 |
| Der Browser-Durchgang rief Bildschirme auf und mass ihre Sichtbarkeit | Der Durchgang klickt in jedem neuen Modul jeden Knopf einmal; ein Handler ohne Funktion faellt dabei sofort auf | #2 |
| Der Ingest galt als fertig, als Exit-Code und vendorierter Inhalt stimmten | Nach dem Ingest wird die **Beschriftung** neben dem Link gelesen, nicht nur das Linkziel | #3 |
| Die Gate-Regel fuer Organisationsbezeichnungen wurde als abdeckend angenommen | Vor dem Vertrauen auf ein Gate einmal seine Musterliste lesen und gegen den eigenen Inhalt halten | #4 |
| Der Quell-Klon wurde gelesen, ohne ihn zu fetchen | Vor der ersten Zeile Uebernahme: `git fetch` auf die **Quelle** und `rev-list --count HEAD..origin/main` | #5 |
| Die Richtigkeit der Veroeffentlichung wurde von Hand im Issue behauptet | Ein Post-Publish-Check im Portal prueft je Repo Erreichbarkeit und Beschriftung und schlaegt fehl, wenn beides auseinanderlaeuft | #6 |
| Der Generator summierte nur Themen mit Modul | Eine generierte Zahl wird einmal gegen ihre Quelle gerechnet, bevor die Seite veroeffentlicht wird | #7 |
| Beim Verschieben von `img/` und `handout.html` wurde nur der Bildbezug geprueft | Nach jedem Verschieben alle Verweise auf die bewegte Datei suchen, nicht nur den, an den man gerade denkt | #8 |
| Die CSS-Isolation wurde geprueft, `:root` dabei bewusst ausgenommen und die Ausnahme nicht mitgeteilt | Was von einer Pruefung ausgenommen wird, steht in derselben Zeile wie ihr Ergebnis | #9 |
| Beim Zusammenfuehren wurden IDs uebernommen, wie sie waren | Beim Merge mehrerer Seiten in ein Dokument werden IDs praefixiert oder durch `data-`-Attribute ersetzt | #10 |
| Nur die erzeugten Artefakte wurden auf den neuen Pfad gezogen | Wer ein Artefakt verschiebt, zieht seinen Generator mit — sonst stellt der naechste Lauf den alten Zustand wieder her | #11 |
| Restpunkte standen in einer Tabelle in einem Sammel-Kommentar | Jeder Restpunkt bekommt im selben Zug ein eigenes verlinktes Artefakt | #12 |
| Der Regex-Fix wurde durch den Gate-Lauf selbst belegt | Ein Fix an einem Pruefwerkzeug bekommt den Fall, den es vorher nicht sah, als Test | #13 |
| Nach dem Merge blieb das Arbeitsverzeichnis stehen | Der Merge und das Schliessen des Arbeitsverzeichnisses sind ein Schritt | #14 |
| Der Klick-Durchgang benutzte die Maus | Der Durchgang faehrt einmal mit der Tastatur: Tab durch alle fokussierbaren Elemente, Enter/Leertaste auf jedem — ein `role`-Element ohne Tastatur-Handler faellt dabei auf | #15 |
| Der gewachsene Scope wurde im Chat gespiegelt und erst danach verankert | Beim dritten Repo oder vor dem Publish steht die Spiegelung **als Frage** im Artefakt, bevor der Schritt laeuft — mit Repo-Zahl, Schreibzielen und dem Prod-Schritt benannt | #16 |

## 5. Laengsschnitt

`retro_kpis.py` ueber 111 Reports. Relevant fuer diese Sitzung:

- `stale-local-clone-as-ground-truth` x9 — **hat ein Gate seit 2026-08-02**, siehe 5a.
- `deferred-item-no-tracking-issue` x36 und `scope-checkpoint-not-durably-recorded` x25 — beide haben ein Gate, und beide haben in dieser Sitzung **gegriffen** (Melder feuerte, Artefakt wurde im selben Zug angelegt). Kein Rueckfall.
- `claim-before-cheapest-check` x77 — Gate hat in dieser Sitzung **zweimal gegriffen** und je eine zu weit gehende Aussage gestoppt.
- `worktree-midsession-accumulation` x5 — Befund #14, kein Gate-Modul registriert.

## 5a. Rueckfall-Pruefung

**`stale-local-clone-as-ground-truth` ist rueckfaellig** (Befund #5). Registry: `mode: advisory`, `module: tools/hooks/stale_clone_check.sh`, `built: 2026-08-02`, `faengt: lokaler Klon liegt hinter origin und wird als Wahrheit gelesen`.

**Ursache: an der Quelle.** Der Hook laeuft als SessionStart-Hook auf `CLAUDE_PROJECT_DIR` — also auf dem Repo, in dem die Sitzung laeuft. Er kann ein **fremdes** Repo nicht sehen, das mitten in der Sitzung als **Inhaltsquelle** gelesen wird. Genau das war der Fall: Sitzungs-Repo war meiki-hub, gelesen wurde frist-hub.

**Konsequenz: ausweiten.** Der bestehende Eintrag bekommt `revised` + `revision_note` und eine zweite Positivkontrolle fuer den Fall "Repo B wird als Quelle gelesen, waehrend sein Klon hinter origin liegt". Kein zweites Gate unter neuem Namen.

## 5b. Autonomie-Kalibrierung

`over_ask`: keine. `over_act`: keine. Der Publish-Schritt und die beiden Merges liefen auf ausdrueckliche Owner-Anweisung ("veroeffentlichen"), der gewachsene Scope stand 41 Minuten vor dem ersten Commit im dritten Repo durabel im Issue (Skeptiker D, REFUTED). Die einzige Entscheidung ohne ausdrueckliches Wort — den frist-hub-Einstieg als Verweis zu behalten statt zu entfernen — war die umkehrbare Variante und wurde vorher angekuendigt. Befund #16 ist deshalb **kein** `over_act`: der Publish war beauftragt. Er ist ein Formfehler der Spiegelung, nicht eine Handlung ohne Mandat.

## 6. Verankerung

### memory_candidates

```markdown
---
name: kd-portierung-quelle-fetchen
description: "Vor der Uebernahme von Inhalten aus einem anderen Repo dessen Klon fetchen — der Stale-Clone-Hook sieht nur das Sitzungs-Repo"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-02-kd-konsolidierung-stale-quelle
---

Wer Inhalte aus Repo B nach Repo A uebernimmt, fetcht **B** zuerst und prueft
`git -C B rev-list --count HEAD..origin/main`.

**Why:** Der SessionStart-Hook `stale_clone_check.sh` prueft `CLAUDE_PROJECT_DIR`,
also nur das Repo der laufenden Sitzung. Ein fremdes Repo, das mitten in der Sitzung
als Quelle gelesen wird, ist fuer ihn unsichtbar. Realfall 2026-09-02: portiert aus
einem frist-hub-Klon, der drei Commits hinter origin lag — Spec, Bildschirme, zwoelf
Bildschirmfotos und ein Handbuch fehlten; gefunden nur, weil ein Doku-Verweis auf
einen Bilderordner zeigte, den es lokal nicht gab.

**How to apply:** Erster Befehl jeder Uebernahme ist der Fetch auf die Quelle.
Verwandt: [[klickdummy-publish-iil-pet]].
```

```markdown
---
name: publish-die-gemeldete-url-aufrufen
description: "Nach dem Veroeffentlichen die vom Owner woertlich genannte URL selbst aufrufen, nicht nur Baum und Linkziel pruefen"
metadata:
  type: feedback
---

Meldet der Owner eine konkrete URL als kaputt, ist **diese URL** die Abnahme-
bedingung. Baum-Inhalt und Linkziel zu pruefen belegt sie nicht.

**Why:** Realfall 2026-09-02: gemeldet war `iil.pet/kd/meiki-hub/` als 404.
Repariert wurde die Portal-Wurzelseite, die jetzt auf die Uebersicht verlinkt —
die gemeldete URL selbst blieb ohne Startseite und damit 404. Der Beleg
("Stand auf origin/main geprueft") war echt und trotzdem am Symptom vorbei.

**How to apply:** Die gemeldete URL in die Abnahme-Liste schreiben und nach dem
Publish einmal aufrufen. Verwandt: [[klickdummy-publish-iil-pet]].
```

### adr_candidates

Keiner. Die Befunde sind Werkzeug- und Ablauf-Fragen, keine Architektur-Entscheidungen; die einzige Architektur-Behauptung (R2) wurde widerlegt.

## 7. Massnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Startseite fuer kd/meiki-hub | iil-pet-portal | (folgt) | 🔵 ready | Muster portal#33 anwenden — ich |
| 2 | Acht tote Knoepfe beleben | meiki-hub | (folgt) | 🔵 ready | JS der Einzel-KDs nachziehen — ich |
| 3 | Portal-Zahl frist-hub | frist-hub | #129 | 🟢 offen | kd-tree.json bereinigen — ich |
| 4 | Uebersichtsseite 64→68 | meiki-hub | (folgt) | 🔵 ready | Module ohne Pack mitzaehlen — ich |
| 5 | Handbuch-Knopf | meiki-hub | (folgt) | 🔵 ready | Pfad korrigieren — ich |
| 6 | Gate-Regex FB/Ortsnamen | meiki-hub | (folgt) | 🔵 ready | org_woerter erweitern — ich |
| 7 | Stale-Clone-Gate ausweiten | platform | (folgt) | 🟢 offen | revised + Positivkontrolle — du |
| 8 | Post-Publish-Pruefung | iil-pet-portal | (folgt) | 🟢 offen | Erreichbarkeit + Beschriftung — du |
| 9 | Tastaturbedienung | meiki-hub | (folgt) | 🟢 offen | keydown-Handler + axe-Lauf — du |

## 8. Nicht verifiziert (Restluecken)

- **Laufzeitverhalten der vier neuen Module unter echten Bedingungen:** geprueft wurde lokal ueber einen HTTP-Server und die Bildschirm-Sichtbarkeit; ein Klick-Durchgang durch alle Bedienelemente fand nicht statt. Billigster Check: Playwright-Lauf, der je Modul jeden `button` und `a.btn` einmal betaetigt und die Konsole liest.
- **Sieben der zwoelf Bildschirmfotos** wurden nicht einzeln auf Personendaten gesichtet (fuenf ja, alle mit Platzhaltern). Billigster Check: die restlichen sieben oeffnen.
- **`kd.iil.pet` (Altpfad)** wurde nicht gegen die Migration getestet; laut Issue-Kommentar als eigenes Los gefuehrt (portal#38, ab 2026-10-02). Billigster Check: `curl -sI https://kd.iil.pet/` und pruefen, ob die 301 auf das Portal zeigt.
- **Ein Hinweistext im Cross-Repo-Picker** (`shell.html`, "Start auf mockups/-Ebene") widerspricht dem daneben stehenden Befehl. Stammt aus PR #202, nicht aus dieser Sitzung — hier bewusst nicht als Befund gefuehrt, aber unkorrigiert mitveroeffentlicht. Billigster Check: `git show origin/main:klickdummy/modul/shell.html | grep -n "mockups/-Ebene"`.
- **Der Modellwechsel-Befund des Sitzungsstarts** (bewertet mit Fable, gelaufen auf Opus, Smoke rot) blieb unbehandelt. Billigster Check: `python3 platform/tools/modellwechsel_check.py --bericht` und der eine rote Test aus dem Smoke-Lauf.

## Widerlegung

Ein Agent auf Tier 4 mit frischem Kontext, der nur den Report-Entwurf und die Artefakte sah, wurde beauftragt, das
Urteil dieser Retro zu widerlegen. Ergebnis: **1 gekippt, 1 neu.**

| Frage | Verdikt | Ergebnis |
|---|---|---|
| Ist ein SURVIVES falsch stehen geblieben? | GEKIPPT (teilweise) | Kein Befund ist inhaltlich falsch, aber der Rahmen von #1 haelt nicht: eine Startseite auf Repo-Ebene hat 1 von 25 Klickdummy-Repos, die Sitemap-Konvention 16 von 25 — die Sitzung folgte der Mehrheit statt ein Muster zu ignorieren. Der gemeldete Weg ist an der Quelle repariert. #1 bleibt als Fakt, Severity von kritisch auf mittel, Scorecard-Anker umgehaengt. Zusaetzlich drei Zaehlfehler korrigiert (#8: 9 statt 5 Stellen, #4: 26 statt 27, #10: 9 Vorkommen). Gegenhypothesen zu #2 und #9 ausdruecklich falsifiziert: die acht Funktionen existieren nirgends (0 `<script>`-Tags, 0 externe `src` in allen 15 Packs), und `--ok` wird in beiden betroffenen Packs tatsaechlich benutzt, `--pui-success` ist nirgends definiert — der abweichende Fallback greift also wirklich. |
| Ist ein REFUTED zu frueh verworfen worden? | GEKIPPT (R3) | R3 kehrt als Befund #16 zurueck. **Die erste Begruendung der Widerlegungsbahn traegt allerdings nicht:** sie nennt `iil-pet-portal#44` (14:36:21Z) als den Prod-Schritt, der den Checkpoint ausgeloest haette — dieser Merge gehoert zu einer frueheren Sitzung desselben Tages. Die Sitzungsgrenze ist die Konversation, nicht der Kalendertag; meine Sitzung beginnt mit dem Issue-Kommentar 15:38:56Z und der Worktree-Reservierung 15:54:22Z. Die **zweite** Begruendung traegt: der Kommentar von 15:38Z spiegelt keinen Scope (keine Repo-Zahl, kein Schreibziel Portal, kein Prod-Schritt, keine Frage) — durabel wurde er erst um 16:29Z, nach der Veroeffentlichung. R1 und R2 halten unabhaengig nachgerechnet. |
| Fehlt eine ganze Dimension? | NEU | **Barrierefreiheit.** 33 Elemente mit `tabindex="0"` und ARIA-Rolle, null Tastatur-Handler im gesamten Modul-Klickdummy. Keiner der drei Finder hatte diese Dimension, und der in den Restluecken vorgeschlagene Playwright-Klick-Durchgang haette sie auch nicht gefunden — eine Maus findet eine fehlende Tastaturbedienung nicht. Aufgenommen als #15. |

Nachrangig, von der Widerlegungsbahn mitgebracht und hier nicht als eigener Befund gefuehrt: die Shell laedt beim
Start alle 15 Packs unabhaengig von der LRA-Buchung (eine Traunstein-Sitzung zieht auch das 94 KB grosse
Guenzburg-only-Pack); die Buchungs-Affordanz "nicht gebucht → buchen" gibt es nur fuer Fachverfahren, nicht fuer
Querschnittsmodule — Traunstein sieht die vier neuen Module ersatzlos nicht; und im Portal liegen weiter fuenf
`screen-lineage-frist-hub-*.html` aus dem alten Stand.

## Self-Review

Die echte Falsifikationsquote betraegt `phase3_refuted/(findings_total − pre_refuted)` = 2/18 = **0,11** und liegt
damit knapp unter dem Band von 0,2, das der Skill als "Falsifikation ist Theater" markiert. Numerische Einordnung
ohne Urteil ueber einzelne Verdikte: von 17 Befunden waren 14 **kommandobelegt** (Datei-Existenz, Zaehlung,
Textvergleich) und gingen nach der Klassentabelle bewusst nicht an den Skeptiker — dort haette er dieselbe Zahl ein
zweites Mal ausgefuehrt. Der Skeptiker lief auf die vier Bewertungsbefunde und verwarf drei davon; die Widerlegungsbahn holte einen davon
wieder zurueck, womit auf der Menge, auf der Falsifikation ueberhaupt wirken kann, 2 von 4 fielen. Die niedrige Gesamtquote ist damit eine Folge der
Befundmischung, nicht eines milden Skeptikers — sie bleibt trotzdem als Auffaelligkeit vermerkt.

## Streichbahn

**Kandidat: `frist-hub:klickdummy/_shared/kd-nav.js` und `kd-tree.js`** — Belegart **kein Leser**. Nach dem Umzug laedt keine Seite in `frist-hub/klickdummy/` diese Dateien mehr (Suche ueber `klickdummy/` ausserhalb von `_shared/`: 0 Treffer); die handgepflegte Verweis-Seite bindet nur Tailwind ein. Sie werden trotzdem weiter ins Portal vendoriert. Weg damit — im selben Zug wie die stehengebliebene `kd-tree.json` (frist-hub#129).
