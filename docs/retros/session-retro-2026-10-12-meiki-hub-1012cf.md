---
retro_schema: 1
date: 2026-10-12
repo_scope: [meiki-hub, meiki-dms]
session_id: 1012cf
footprint: full
findings_total: 11
findings_survived: 5
refuted_rate: 0.55
phase3_refuted: 5
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: []
recurring_findings: [worktree-midsession-accumulation, issue-stand-nach-merge-nicht-nachgezogen, pr-text-erklaert-merge-zum-owner-entscheid, guard-wort-im-heredoc-trotz-memory]
gates_caught: [direct-gh-pr-merge-bypasses-sa-m, claim-before-cheapest-check, gh-body-file-leer-ueberschrieben]
gates_verwandt: ["scope-checkpoint-not-durably-recorded: Checkpoint stand durabel in meiki-hub#470, das dritte Repo wurde nie erreicht (geschrieben nur in meiki-hub und meiki-dms); Befund #5 ist ein veralteter Stand, kein fehlender Checkpoint", "issue-offen-nach-gemergtem-fix: meiki-hub#599 bleibt zu Recht offen, Kriterium 2 haengt an der PROSOZ-Antwort A1; Befund #8 ist nur der fehlende Haken an Kriterium 1"]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "0 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "Jede Phase hat in dieser Retro sichtbar gewirkt: 0.0 ordnete alle vier rueckfaelligen Gates bestehenden Beschluessen zu, der Skeptiker kippte 5 von 8 Bewertungsbefunden, und ohne ihn staenden zwei Merge-Vorwuerfe und zwei Festlegungs-Vorwuerfe falsch im Report."
---

# Session-Retro 1012cf — PROSOZ-Herstellerdoku, ADR-044 v1.3 und Testsysteme (meiki-hub)

Sitzung `4c7f7475-d3d1-4143-84d6-92ff6a1012cf`, 2026-10-12, 07:12–14:00 UTC. Inhalt: Abgleich mit
der PROSOZ-Herstellerdoku ([#612](https://github.com/meiki-lra/meiki-hub/pull/612)), Prämisse
„Prosoz REST v2" als unbelegt vermerkt ([#613](https://github.com/meiki-lra/meiki-hub/pull/613)),
ADR-044 v1.3 „DMS ist einzige führende Ablage" ([#615](https://github.com/meiki-lra/meiki-hub/pull/615)),
D1 in KONZ-meiki-011 ([#616](https://github.com/meiki-lra/meiki-hub/pull/616)), Issue
[meiki-dms#33](https://github.com/meiki-lra/meiki-dms/issues/33), fünf Mail-Entwürfe an Günzburg,
Traunstein und PROSOZ (vom Owner versendet), Kommentare in #470, #600, #603, #606.

**Footprint `full`:** 4 Doku-PRs, 2 Repos, drei geänderte ADRs (ADR-024, ADR-037, ADR-044), kein
Prod, keine Migration. Agenten: 3 Finder (Sonnet), 1 Skeptiker (Sonnet, gebündelt statt je
Dimension, weil 3 Finder + 3 Skeptiker + 3b + Meta das Budget ≤6 sprengen), 3b (Opus), Meta (Sonnet).

## 0. Wirkungsbilanz (Phase 0.0)

`tools/gate_wirkung.py` meldet vier Gates `RUECKFAELLIG`. Für drei liegt ein Beschluss aus
früheren Retros vor; für `worktree-midsession-accumulation` gibt es nur den offenen Vorschlag M6
der Retro `4f385c-incr2` (🟢 „Owner entscheidet“), und diese Sitzung bringt dort einen neuen
Rückfall. „Rückfälle seit Bau“ zählt Vorkommen nach dem Gate-Bau; `retro_kpis.py` zählt den Slug
über alle Retros (dort ×12, inklusive der Vorkommen vor dem Bau).

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 4 | Quelle | **nachschärfen**, Beschluss [platform#2666](https://github.com/achimdehnert/platform/issues/2666) (Retro `728cf0-incr`); hier dreimal **gefangen** (Bash-Hook 2× am Kommentar #470, Stop-Hook 09:55Z) |
| built-but-never-called | 3 | Quelle | **ausweiten**, Beschluss Owner-Wort „187 go" (Retro `0405d4`); hier kein Vorkommen, kein Werkzeug gebaut |
| worktree-midsession-accumulation | 3 (Slug ×12) | Ausgang | **herabstufen** — entschieden in dieser Retro, Umsetzung braucht das Owner-Wort zu M6 (§7); bisher nur Vorschlag `4f385c-incr2` M6, Gate-Datei unverändert `mode: process`; hier **ein neuer Rückfall** (Befund #9) |
| scope-checkpoint-not-durably-recorded | 2 | Quelle | **nachschärfen**, Rev 10 (Retro `7152dd` F11, platform#3600); hier nur verwandt (Befund #5) |

## 1. Executive Summary

- Alle Owner-Aufträge sind geliefert: vier Doku-PRs grün und gemergt, fünf Mails nach Auftrag, Anfragen F6 (PROSOZ-Testmandant) und T6 (Traunstein-Testsysteme) in #470/#600 verbucht.
- Der Skeptiker kippte 5 von 8 Bewertungsbefunden, darunter den Vorwurf, die Merges über `pr_merge_sa.py` seien ungedeckt gewesen: der Guard nennt das Skript selbst als sanktionierten Weg.
- Überlebt haben zwei Nachzugsfehler im Issue-Stand (#5, #8) und die Bindung des Owner-Entscheids D2 an den Merge samt eigenem Abhaken vor dem „ja“ (#6).
- Die Widerlegungsbahn kippte nichts, brachte aber einen neuen Punkt: die PROSOZ-Doku steht unter Weitergabeverbot, und Repo-Texte tragen Zusammenfassungen statt nur Seitenverweisen (Hypothese, Owner-Entscheid M8).
- Zwei kommandobelegte Befunde: drei liegengebliebene Worktrees (#9, in der Retro entfernt) und ein Heredoc mit Guard-Wort trotz bekannter Memory (#10).
- Kein Gate-Kandidat: alle Überlebenden sind Einzelfälle oder fallen unter bestehende Gates/Beschlüsse.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Merges #612 (Fork-Subagent) und #616 über `pr_merge_sa.py` direkt nach Guard-Block, ohne Owner-Wort mit PR-Nummer | Prozesslücke | mittel | REFUTED (Phase 3) | Merge-Journal `~/.claude/pr-merge-sa.jsonl`: #612 08:51:33Z und #616 09:44:56Z „M0 deckt W2“, gemergt; #613 zweimal `nicht_gedeckt` (Governance-Pfad `docs/adr/`), danach 09:05:30Z vom Owner per `OWNER_WORT=613` gemergt; Hook-Docstring `~/.claude/hooks/block_direct_pr_merge.py` Z. 19–23 nennt `pr_merge_sa.py` sanktioniert; Klassifizierer-Ablehnung kam erst 09:45Z nach #616; Memory `gruene-pr-selbst-mergen` deckt Doku-PRs | — |
| 2 | #613 vermerkt „REST v2" nur im Kopf; Fließtext von ADR-037 Z. 90/274 und KONZ-meiki-001 Z. 64/116/220 bleibt unmarkiert | fehlende Validierung | mittel | REFUTED (Phase 3) | #599 Kriterium 1 verlangt „je einen Vermerk" pro Dokument; die Vermerke nennen die betroffenen Zeilen | — |
| 3 | ADR-044 v1.3 legt „DMS einzige führende Ablage" fest, während PROSOZ-Frage F5 offen ist | verfrühte Festlegung | niedrig | REFUTED (Phase 3) | ADR-044 Z. 148–174: bei positivem F5 entfallen Punkte 2 und 3; #615 nennt F5 offen | — |
| 4 | D1 (Pilot Günzburg SGB XII) entschieden, obwohl Ablösung ok.Sozius offen | verfrühte Festlegung | niedrig | REFUTED (Phase 3) | KONZ-meiki-011 Z. 233 trennt Pilot-Wahl vom Start `[offen → Haus, G3 und Ablösezeitpunkt]` | — |
| 5 | Scope-Checkpoint-Kommentar in #470 (08:53:45Z) meldet „#613 wartet auf den Merge durch den Owner“; der Owner mergte 09:05:32Z, der Stand im Issue wurde nie nachgezogen | Kommunikation | niedrig | SURVIVES | [#470 Kommentar 12.10. 08:53Z](https://github.com/meiki-lra/meiki-hub/issues/470); `gh pr view 613` mergedAt 09:05:32Z; kein späterer Kommentar zu #613 | neu: `issue-stand-nach-merge-nicht-nachgezogen`; verwandt scope-checkpoint (s. Frontmatter) |
| 6 | PR-Text #615 band den Owner-Entscheid D2 an den Merge („Mit dem Merge ist D2 in #603 entschieden“), und die Sitzung hakte D2 in #603 um 09:37:29Z selbst ab; das ausdrückliche „D2 ja“ kam 09:40:56Z, und §2c weicht von der Issue-Option „Verweis oder nur Chronik-Kopie“ ab | Kommunikation | niedrig | SURVIVES | #615 Body; mergedAt 09:35:45Z unter dem Owner-Konto (Weg unklar, s. §8); #603-Body-Edit 09:37:29Z „[x] **D2**“; Owner-Nachricht „D1 ja go ; D2 D3 ja gfo“ 09:40:56Z nur im Sitzungstranskript belegt (`retro_transkript_kennzahlen.py`, nicht per gh prüfbar); [#603 Kommentar 09:41:40Z](https://github.com/meiki-lra/meiki-hub/issues/603) „D2 und D3 waren schon entschieden“ stützt die Bindung an den Merge; ADR-044 §2c | neu: `pr-text-erklaert-merge-zum-owner-entscheid` |
| 7 | meiki-dms#33 aus meiki-hub nicht verlinkt | Kommunikation | niedrig | REFUTED (Phase 3) | #470-Kommentar 08:53Z enthält „Issue meiki-lra/meiki-dms#33 angelegt" | — |
| 8 | #599 Kriterium 1 durch #613 sachlich erfüllt, im Issue weder Haken noch Kommentar | Prozesslücke | niedrig | SURVIVES | `gh issue view 599`: OPEN, 0 Kommentare, Kriterium 1 `- [ ]`; Vermerke in ADR-024/037, KONZ-meiki-001 auf origin/main | neu: `issue-stand-nach-merge-nicht-nachgezogen`; verwandt issue-offen-nach-gemergtem-fix |
| 9 | Drei Worktrees dieser Sitzung (#612, #613, #615/#616) lagen nach dem Merge bis zur Retro | Werkzeug | niedrig | SURVIVES (kommandobelegt) | `git worktree list` 14:0xZ: `…-adr-prosoz-rest-praemisse-084823`, `…-adr044-dokumentablage-092558`, `…-prosoz-herstellerdoku-abgleich-084204`; in der Retro per `git worktree remove` entfernt, danach 0 | Gate `worktree-midsession-accumulation` rückfällig (§0, §5a) |
| 10 | Memory-Nachtrag 09:54Z per Bash-Heredoc mit dem Merge-Befehlstext; der Merge-Guard blockte, obwohl Memory `auto-modus-merge-ohne-review-abgelehnt` (Nachtrag 2026-10-01) genau das beschreibt: Guard liest Heredocs, Text per Write-Tool | Wissenslücke | niedrig | SURVIVES (kommandobelegt) | Kennzahlen Fehlerlauf 09:54:44Z „Merge-Guard (SA-M, #2234)"; Memory-Datei Z. 34–38 | neu: `guard-wort-im-heredoc-trotz-memory` |
| 11 | Commit-Body #616 trägt „Co-authored-by: Claude Opus 5.5" statt einer anderen Attribution | Werkzeug | niedrig | REFUTED (pre) | Sitzungstranskript `4c7f7475….jsonl`: 418 Antworten mit `"model":"claude-opus-5-5"`, kein anderes Hauptmodell; die Attributionszeile nennt genau dieses Modell | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Alle Aufträge geliefert; Fortschritt in #599 nicht vermerkt (#8) |
| architektur_design | 4 | ADR-044 v1.3 mit Rückfallregel für F5 (#3 REFUTED); D2-Inhalt weicht von Issue-Option ab (#6) |
| code_konventionstreue | 4 | Commit-Format durchgehend `docs(scope): …` (#11 REFUTED); Heredoc gegen bekannte Regel (#10) |
| risiko_debt | 4 | Liegengebliebene Worktrees (#9), in der Retro bereinigt |
| prozess_effizienz | 3 | Veralteter Checkpoint-Stand (#5), Guard-Treffer am Heredoc (#10), Hook-Treffer am #470-Kommentar |
| entscheidungsqualitaet | 4 | D1/D2 mit Vorbehalten sauber verankert (#3, #4 REFUTED); D2 an den Merge gebunden (#6) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Checkpoint-Kommentar #470 08:53Z nennt #613 offen, Merge 09:05Z ohne Nachtrag | Nach jedem Merge, den ein eigener Kommentar als offen nennt, eine Zeile „erledigt: #613 gemergt <SHA>" im selben Issue | #5 |
| #615-Text „Mit dem Merge ist D2 entschieden", Owner-„ja" danach | Owner-Entscheid vor dem PR einholen; der PR-Text verweist auf das Wort („D2 entschieden am …, #603"), statt den Merge zum Entscheid zu machen; Abweichung von der Issue-Option im PR-Text benennen | #6 |
| #613 erfüllt #599 Kriterium 1, Issue unverändert | Mit „Refs #599" im PR das erfüllte Kriterium im Issue abhaken und den PR verlinken | #8 |
| Drei Worktrees gemergter PRs bis Sitzungsende | Direkt nach jedem bestätigten Merge `git worktree remove <pfad>` des eigenen Worktrees | #9 |
| Memory-Nachtrag per Heredoc mit Guard-Wort, Guard blockt | Memory- und Befehlstexte mit Guard-Wörtern immer per Write/Edit-Tool, nie per Heredoc | #10 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Stand origin/main 12.10.):

- `worktree-midsession-accumulation` ×12 über Retros, Gate vorhanden, Beschluss „herabstufen" (s. §5a).
- `issue-stand-nach-merge-nicht-nachgezogen`, `pr-text-erklaert-merge-zum-owner-entscheid`, `guard-wort-im-heredoc-trotz-memory`: neu, ×1. Nächste Verwandte: `issue-not-reconciled-after-cross-repo-fix` ×8 (cross-repo, hier nicht gegeben), `issue-offen-nach-gemergtem-fix` ×6 (Issue hier zu Recht offen), `inline-heredoc-quoting-rework` ×12 (Quoting, hier Guard-Wort). Keine Zählung ≥2 ⇒ keine neue Gate-Pflicht.
- Abgrenzung, damit kein Alias entsteht: `issue-stand-nach-merge-nicht-nachgezogen` trägt #5 und #8, zählt aber je Retro einmal. Es geht um einen veralteten Stand in einem **offen bleibenden** Issue, nicht um ein Issue, das nach dem Fix hätte schließen müssen (`issue-offen-nach-gemergtem-fix`), und nicht um einen Cross-Repo-Fix (`issue-not-reconciled-…`). `guard-wort-im-heredoc-trotz-memory` ist kein Quoting-Rework: der Text war korrekt gequotet, der Guard las das Wort im Heredoc. `direct-gh-pr-merge-bypasses-sa-m` hat gefangen (gates_caught), ein Rückfall liegt nicht vor.
- MEMORY.md-Abgleich (`grep`): `auto-modus-merge-ohne-review-abgelehnt` trägt die Heredoc-Regel bereits (Befund #10 ist Anwendungs-, nicht Wissenslücke im Bestand); `closes-nur-mit-vollstaendiger-kriterientabelle` deckt #599 („Refs" korrekt), nicht aber den Haken an erfüllten Teilkriterien.
- refuted_rate-Trend vor dieser Retro: 8be895 0.27 · 728cf0-incr 0.54 · 8be895-incr 0.00 · 767d40 0.42 · 6189d3 0.37 · 767d40-incr 0.39 · 3b46a0 0.41 · 213b56-incr 0.16; dieser Lauf 0.55, im Band.

### 5a. Rückfall-Prüfung

**Gate `worktree-midsession-accumulation` ist rückfällig** (Befund #9). Antwort: **herabstufen**.
Die Retro `4f385c-incr2` hatte das als M6 nur vorgeschlagen (🟢 „Owner entscheidet“); die
Gate-Datei führt weiter `mode: process`, `revised: 2026-09-30` — umgesetzt ist nichts. Dieser
Fall stützt den Vorschlag: der Melder (Hygiene-Hook beim Sitzungsstart) nannte Kandidaten,
gehandelt wurde erst in der Retro. Umsetzung als Edit der bestehenden Gate-Datei (`revised` +
`revision_note`, durch `gate_verankerung_check.py --neu`) nach Owner-Wort zu M6 (§7).

Die übrigen drei rückfälligen Gates: kein neuer Rückfall in dieser Sitzung (§0).

### 5b. Autonomie-Kalibrierung

- over_ask: keine. Mails gingen als Entwürfe an den Owner (Außenwirkung), #615 wartete auf den Owner-Merge.
- over_act: keine. Die Skript-Merges #612/#616 sind durch `gruene-pr-selbst-mergen` und den sanktionierten Skriptweg gedeckt (#1 REFUTED). Nach der Klassifizierer-Ablehnung 09:45Z wurde kein weiterer Anlauf unternommen.

## 6. Verankerung

**memory_candidates** (der Owner entscheidet, nicht selbst geschrieben):

```markdown
---
name: owner-entscheid-vor-pr-nicht-per-merge
description: PR-Text darf einen offenen Owner-Entscheid nicht an den Merge binden; erst Wort holen, dann PR verweist darauf
metadata:
  type: feedback
---

Am 2026-10-12 schrieb meiki-hub#615 „Mit dem Merge ist D2 in #603 entschieden"; das ausdrückliche „D2 ja" kam fünf Minuten nach dem Merge, und ADR-044 §2c wich von der Issue-Option ab.
**Why:** Ein Merge-Klick ist keine inhaltliche Entscheidung; der Owner bestätigt sonst nachträglich eine Tatsache.
**How to apply:** Offenen Entscheid (Dx in einem Issue) zuerst als Owner-Wort holen und dabei Abweichungen von der Issue-Formulierung nennen; der PR-Text zitiert das Wort mit Datum.
```

```markdown
---
name: refs-pr-hakt-teilkriterium-ab
description: Erfüllt ein PR mit „Refs #N" ein Teilkriterium, im selben Zug den Haken in #N setzen und den PR verlinken
metadata:
  type: feedback
---

meiki-hub#613 erfüllte #599 Kriterium 1; das Issue blieb ohne Haken und Kommentar, der Fortschritt stand nur im PR.
**Why:** Wer das Issue liest, sieht sonst keinen Fortschritt; der nächste Agent arbeitet das Kriterium erneut ab.
**How to apply:** Nach dem Merge eines „Refs"-PR das erfüllte Kriterium abhaken (`gh issue edit --body-file`) und den PR verlinken. Verwandt: [[closes-nur-mit-vollstaendiger-kriterientabelle]].
```

**adr_candidates:** keine (Prozessfragen, keine Architekturentscheidung).

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | #599 Kriterium 1 abgehakt | meiki-hub | [#599](https://github.com/meiki-lra/meiki-hub/issues/599#issuecomment-6125974909) | ✅ | — |
| M2 | Stand #613 in #470 nachgetragen | meiki-hub | [#470](https://github.com/meiki-lra/meiki-hub/issues/470#issuecomment-6125975355) | ✅ | — |
| M3 | Memory owner-entscheid-vor-pr | meiki-hub | §6 | 🟢 | Owner: übernehmen ja/nein |
| M4 | Memory refs-pr-hakt-teilkriterium-ab | meiki-hub | §6 | 🟢 | Owner: übernehmen ja/nein |
| M5 | Worktrees der Sitzung entfernt | meiki-hub | #612 #613 #615 #616 | ✅ | — |
| M6 | Gate Baum-Zählung herabstufen | platform | [#2234](https://github.com/achimdehnert/platform/issues/2234) | 🟢 | Owner: Wort „M6 herabstufen“, dann Gate-Edit durch mich |
| M7 | Merge-Memories widersprechen sich | meiki-hub | [#616](https://github.com/meiki-lra/meiki-hub/pull/616) | 🟢 | Owner: welche Regel gilt |
| M8 | PROSOZ-Zusammenfassungen im Repo zulässig? | meiki-hub | [#612](https://github.com/meiki-lra/meiki-hub/pull/612) | 🟢 | Owner: zulässig oder kürzen |

## 8. Nicht verifiziert (Restlücken)

- Die Owner-Nachricht 09:40:56Z zu D1–D3 (Befund #6) ist nur im Sitzungstranskript belegt, nicht in einem GitHub-Artefakt.
- Ob der Owner den Inhalt von ADR-044 §2c vor seinem Merge von #615 gelesen hat (Befund #6): nicht prüfbar aus Artefakten.
- Die PDF-Anlage an PROSOZ wurde nicht erneut gegen origin/main verglichen (in der Sitzung geprüft, nicht in der Retro).
- Auf welchem Weg #615 um 09:35:45Z unter dem Owner-Konto gemergt wurde: nicht per Skript (kein Journal-Eintrag), nicht per Owner-Terminal (der Befehl 09:37:06Z meldete „already merged“). Billigster Check: Owner fragen, ob über die Weboberfläche.
- Memory-Widerspruch (M7): der Sitzungs-Nachtrag 2026-10-12 in `auto-modus-merge-ohne-review-abgelehnt` verlangt für grüne Doku-PRs ein Owner-Wort, `gruene-pr-selbst-mergen` erlaubt den Selbst-Merge. Den Nachtrag schrieb die Sitzung ohne Owner-Freigabe; welche Regel gilt, entscheidet der Owner.
- Weitergabeverbot PROSOZ-Doku (M8, Hypothese aus 3b): der #470-Kommentar 08:42Z sagt „nur Seitenverweise“, #612 und #615 tragen aber eigene inhaltliche Zusammenfassungen. Ob das als „Auszug“ zählt, ist eine Vertragsfrage. Billigster Check: Owner-Urteil oder Rückfrage bei PROSOZ.

Vierklang: **getan:** Wirkungsbilanz, 3 Finder, 1 Skeptiker, Widerlegungsbahn, Meta-Review, Längsschnitt, Rückfall-Prüfung, M1, M2, M5.
**angenommen:** Der Hook-Docstring ist die maßgebliche Aussage zum sanktionierten Merge-Weg.
**nicht verifizierbar:** Owner-Kenntnis von §2c vor dem Merge (#6).
**offen geblieben:** M3, M4, M6, M7, M8.

## Widerlegung

Ein Opus-Agent mit frischem Kontext prüfte den Entwurf. Er hatte Report, Footprint und
Artefaktliste, aber nicht die Sitzungserzählung.

| Frage | Ergebnis | Verdikt |
|---|---|---|
| 1. SURVIVES falsch? | #5, #6, #8, #9, #10 halten. #6 ist schärfer: D2 wurde in #603 um 09:37:29Z selbst abgehakt (eingearbeitet). | BESTAETIGT |
| 2. REFUTED zu früh? | #1–#4, #7, #11 halten. Im Beleg zu #1 stand ein falsches Faktum: #613 hat der Owner gemergt, nicht das Skript (korrigiert). Dazu kommt der Memory-Widerspruch M7 (§8). | BESTAETIGT |
| 3. Fehlende Dimension | Weitergabeverbot der PROSOZ-Doku: die Repo-Texte tragen Zusammenfassungen, behauptet waren „nur Seitenverweise“. Das ist eine Hypothese zum Verstoß, belegt ist nur die falsche Behauptung. Owner-Entscheid M8. | NEU |

Ohne Fund geprüft:
- „go B1–B6“ ist vollständig umgesetzt (B1 #612, B2 #470-Kommentar 08:42Z, B3 #613, B4 meiki-dms#33, B5/B6 Mails).
- Die Mails sind stimmig zur LRA↔DMS-Zuordnung.
- Die Frontmatter-Zahlen sind konsistent.

## Streichbahn

Keine Streichung. Jede Phase hat in dieser Retro sichtbar gewirkt: 0.0 zeigte, dass die
Herabstufung der Baum-Zählung seit einer Woche als Vorschlag liegt (M6), der Skeptiker kippte 5
von 8 Bewertungsbefunden, und der Meta-Review fand den falsch als „Beschluss“ geführten Vorschlag.
Beobachtung ohne Streichantrag: Die Vorgabe „Skeptiker je Dimension" und das Budget ≤6 für `full`
mit 3b und Meta passen nicht zusammen (3+3+1+1 = 8); diese Retro bündelte auf einen Skeptiker.

## Self-Review

Der Meta-Agent prüfte Zahlen, die Invariante (5 Soll-Schritte = 5 überlebende Befunde),
Gate-Antworten und den Pfad; `retro_report_check.py` war grün, die Stichproben #5 und #8 hielten
per gh. Er fand den als „Beschluss“ geführten Vorschlag M6 (korrigiert in §0, §5a, Streichbahn),
die dünnen Belege zu #6 und #11 (nachgetragen) und die fehlende Slug-Abgrenzung (§5). M1 und M2
standen als eigene Nachzug-Items im Report, der genau diesen Nachzug rügt; beide sind vor dem
Commit erledigt. refuted_rate 0.55 liegt im Band.
