---
retro_schema: 1
date: 2026-09-10
repo_scope: [platform]
session_id: oqu6Z6
footprint: full
footprint_reduction_reason: "deep-Trigger (Prod: zwei Dienst-Neustarts, ein Token-Wechsel in Gate-Workflow) auf full reduziert — (a) jeder Prod-Schritt explizit vom Owner freigegeben (Neustarts vom Owner selbst ausgefuehrt; Token-Wechsel per Owner-Wort in #3027, Klassifizierer hatte den Agenten gestoppt), (b) voll rollback-faehig, keine Migration, (c) findings_total-Schaetzung ≤10 vor Phase 2"
findings_total: 22
findings_survived: 19
refuted_rate: 0.14
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [service-declared-without-ingress-check, branch-reused-for-second-pr, closes-keyword-in-commit-overrides-refs-body, bot-command-error-is-red-run, pr-workflow-runs-with-fleet-token, pr-body-claims-commit-not-in-pr, real-thread-key-in-public-fixture, outbound-claim-must-match-own-repo-facts]
recurring_findings: [claim-before-cheapest-check, deferred-item-no-tracking-issue, parallel-session-pr-collision, same-file-serial-prs, ci-gate-maskiert-failure, test-asserts-the-case-in-mind-not-the-harmful-one]
gates_caught: [handover-stale-vor-merge]
over_ask_klassen: []
over_act_klassen: [refs-nachtraeglich-fuer-mandat]
widerlegung: "4 gekippt, 4 neu"
streichkandidaten: []
streich_begruendung: "keiner, weil jedes heute beruehrte Gate entweder gefangen hat (Frische 2x, Check-Run-Ebene) oder nachgeschaerft wird (aufschub-anker, parallel-session, serielle-prs); der einzige Kandidat mit Belegart kein-Effekt (serielle-prs-Melder laeuft erst am Sitzungsende) traegt die einzige Falsifikationsregel fuer same-file-serial-prs x12 und wird umgebaut, nicht gestrichen"
---

# Session-Retro 2026-09-10 — platform — Auftrag #3015 (Mailcheck / To-do / Zeitung), Drill-Vorlage, To-do-Links, zwei Gate-Reparaturen

## 1. Executive Summary

- Neun PRs in einem Repo gemergt (#3016, #3024, #3030, #3034, #3037, #3038, #3039, #3042, #3043), Auftrag #3015 mit Zielzustand K1–K5 angelegt; drei Owner-Befunde an der To-do-Liste am selben Tag behoben — zwei mit Artefakt-Beleg live, das dritte (#3042) laut Handover noch als offener Owner-Neustart geführt (Befund #22).
- Der Auftrag ist nach heute bei keinem Kriterium vollständig: die Betriebsakte (K1-Kern) fehlt, K2/K4/K5 sind nicht begonnen, K3 hat einen Bauschritt. Die Session lieferte Symptom-Fixes, die K1 beanspruchen, ohne K1 zu erfüllen.
- Sicherheitsbefund aus der Widerlegungsbahn (#19): der Gate-Workflow `handover-append-only.yml` läuft seit #3030 als einziger `pull_request`-Workflow mit dem Flotten-Token `PROJECT_PAT`, den `apply-branch-protection.yml` für Admin-Schreibaktionen nutzt; ADR-238 (accepted) verlangt einen kurzlebigen App-Token statt `PROJECT_PAT`. Die Freigabe in #3027 stand auf einer falschen Gleichsetzung.
- Ein Betreff-Schlüssel eines realen Vorgangs (#189) ist über eine Test-Fixture ins öffentliche Repo gelangt (#21), obwohl der Auftrag „keine Betreffs" vorschreibt.
- Der Skeptiker kippte alle drei Bewertungsbefunde, die Widerlegungsbahn kippte davon zwei zurück und zwei weitere SURVIVES: das Urteil dieser Retro wurde zweimal korrigiert, bevor es stand.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | K1-Kernartefakt (Betriebsakte `docs/betrieb/`) fehlt, obwohl #3034/#3042 K1 beanspruchen | verfrühte Festlegung | kritisch | SURVIVES (3b BESTAETIGT: Issue schließt Outline aus) | `git ls-tree -r origin/main --name-only \| grep -i betrieb` → kein docs/betrieb; #3015 Body „Betriebsakte im Repo statt in Outline" | – |
| 2 | K2, K4, K5 nicht begonnen; K3 nur ein Bauschritt | Prozesslücke | hoch | SURVIVES (kommandobelegt) | #3015 Sachstand; `git ls-tree … \| grep -iE 'journal'` nur befund_journal.py | – |
| 3 | Sechs Folgearbeiten nur als Prosa im Sachstand-Kommentar, keine Anker-Form | Prozesslücke | mittel (3b: von hoch herabgesetzt, Punkte nummeriert im offenen Issue) | SURVIVES (3b BESTAETIGT) | `tools/deferral_anchor_check.py` ANKER-Regex; Kommentar-Punkte 1/3/6/7/9/11 ohne Link | deferred-item-no-tracking-issue ×40 |
| 4 | #3024 deklarierte todo.iil.pet als Alias von mail-links; #3039 korrigierte auf eigenen Dienst 8789 | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | PR #3039 Body „mein Fehler"; ade8acf2 vs a88d5bc7 | claim-before-cheapest-check ×81 |
| 5 | news-hub (Zeitung) nicht berührt — Reihenfolge eingehalten, 0 von 3 Anwendungen vollständig | Statusbefund | mittel | SURVIVES (kommandobelegt) | `gh pr list --repo achimdehnert/news-hub --search "merged:2026-09-10"` → [] | – |
| 6 | #3038 (Review-Bot) ohne Bezug zu #3015, vom Co-Owner gemergt | Scope, gegated | niedrig | SURVIVES (kommandobelegt) | `gh pr view 3038 --json mergedBy` → wirdigital (CODEOWNERS) | – |
| 7 | #3042 legt `TODO_BASIS` neu an statt aus board.py zu importieren | Werkzeug | niedrig-mittel | SURVIVES (kommandobelegt) | board.py:78 vs mail_link_server.py:110 | – |
| 8 | #3043 reparierte nur den gerissenen Test; alle sieben Tests hängen am Produktivkatalog, zwei weitere an Positionen (`dienste[0]/[1]`, `kippt_als_naechstes[0]`) | fehlende Validierung | niedrig-mittel | SURVIVES (Skeptiker A1 REFUTED, 3b GEKIPPT zurück: Fragilitätsklasse „Position in Produktivdaten") | test_iil_assist_katalog.py: Fixture `ik.lade(ik.KATALOG)`; `test_should_rank_blocked_repo_first_in_wartung` | test-asserts-the-case-in-mind-not-the-harmful-one ×6 |
| 9 | #3042 Docstring/Commit behaupten „gerenderte Mails tragen keinen `<body>`" — mail_view.py:269 hat einen | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | mail_link_server.py:166-167 vs mail_view.py:216-269 | claim-before-cheapest-check |
| 10 | #3030 und #3033 (Parallelsitzung) lösten dieselbe Ursache im selben Workflow; dritter Anlauf nötig | Prozesslücke | hoch | SURVIVES (kommandobelegt) | #3030 08:35:58 vs #3033 09:05:31, Merge-Kommentar Z.101-107 | parallel-session-pr-collision ×9 |
| 11 | Regex-Injektion der Rückweg-Leiste in `_sende()` vertretbar für `/a/` und `/m/` (Fremd-HTML aus `read_mail.render`), zu großzügig nur für `/r/` (`_graph_rendern` hat eigenen `<body>`) | Werkzeug | niedrig | SURVIVES (Skeptiker A2 REFUTED, 3b GEKIPPT zurück per Routenzählung) | mail_link_server.py Z.313-316, 425-445, 836/958, 588 | – |
| 12 | Required Check pytest durch nicht-idempotenten Test (Parallelsitzung) für alle PRs rot | fehlende Validierung | hoch | SURVIVES (kommandobelegt) | Run 34464904488, 34465119193; Fix #3043 | test-asserts-the-case-in-mind-not-the-harmful-one |
| 13 | #3024 gemergt trotz rotem Gate-Lauf, ohne Vermerk | Merge-Disziplin | mittel | REFUTED (3b GEKIPPT: #3027 existierte 9 Minuten vor dem Merge, Check advisory, Merger Co-Owner) | #3027 createdAt 08:23:11Z vs mergedAt 08:32:21Z; rules/branches/main | – |
| 14 | Branch `3015-todo-deklaration` für zwei PRs (#3024, #3030) wiederverwendet; CI-Läufe vermischt | Werkzeug | mittel | SURVIVES (kommandobelegt) | `gh pr list --search "head:session/2026-09-10"` identischer headRefName | – |
| 15 | Vier Merges durch `wirdigital` ohne Mandats-Vermerk | Kommunikation | niedrig-mittel | REFUTED (Skeptiker A3, 3b BESTAETIGT: exakt die CODEOWNERS-Pfade, entworfene Kontrolle) | CODEOWNERS Z.8-14; `gh pr view --json files` der vier PRs | – |
| 16 | Review-Bot lief grün, approvte aber nichts (gh-CLI-Inkompatibilität als „kein Kommentar" gewertet) | Werkzeug | hoch | SURVIVES (kommandobelegt) | Run 34463044567; Fix #3038; Wirkungsbeweis Approval an #3039 | ci-gate-maskiert-failure ×11 |
| 17 | „Closes #2719" im Commit-Text schloss das Issue beim Merge, obwohl der PR-Body auf „Refs" stand | Werkzeug | niedrig | SURVIVES (Skeptiker B2) | Timeline #2719 closed 07:43:22Z commit 637b820e; Body nur Refs | – |
| 18 | Leiste per Regex nachgespritzt, obwohl `board_als_html()`/`_graph_rendern()` eigene Hüllen sind (mittel) | Werkzeug | mittel | REFUTED (3b GEKIPPT: `board_als_html` bedient `/d/`, liegt nicht auf dem Injektionspfad; Restform in #11) | mail_link_server.py Z.362 (`_board`) | – |
| 19 | `handover-append-only.yml` läuft seit #3030 als einziger `pull_request`-Workflow mit `PROJECT_PAT` (Admin-Token laut apply-branch-protection.yml Z.25); ADR-238 C5 (accepted) verlangt App-Token statt PROJECT_PAT; weder #3027 noch #3030 nennen ADR-238 | Sicherheit / Wissenslücke | hoch | SURVIVES (3b NEU-1) | `git grep -l PROJECT_PAT origin/main -- .github/workflows` → 8 Workflows, nur einer `on: pull_request`; `docs/adr/ADR-238` | – |
| 20 | PR-Body #3024 beschreibt einen „dritten Commit" (Token-Umstellung), den der PR nicht enthält — öffentlich, nie korrigiert | Kommunikation | mittel | SURVIVES (3b NEU-2) | `gh pr view 3024 --json body,commits`; `git show --stat ade8acf2` | outbound-claim-must-match-own-repo-facts |
| 21 | Betreff-Schlüssel des realen Vorgangs 189 („Submission of Chapters") als Test-Fixture ins öffentliche Repo (#3042); Auftrag verbietet Betreffs ausdrücklich; ältere Fälle seit 2026-09-01 | Sicherheit / Konvention | mittel | SURVIVES (3b NEU-3) | test_mail_link_server.py:701,733; `git log -S` → 30cc4d62; #3015 K2/Out-of-Scope | – |
| 22 | Report-Entwurf behauptete „drei Owner-Befunde live verifiziert"; für #3042 gibt es kein Artefakt außerhalb der Erzählung (Handover Z.42 führt den Neustart als offen) | fehlende Validierung (am Report) | niedrig | SURVIVES (3b NEU-4) | #3015 Sachstand Nr. 13 „Wirkt nach Neustart"; `git show origin/main:AGENT_HANDOVER.md` Z.42 | claim-before-cheapest-check |

Widersprüche aus Phase 2.5, vom Skeptiker entschieden: B1 Sammler „Required-Check FAIL beim Merge" REFUTED (advisory); B2 Schließung #2719 durch Commit-Schlüsselwort; B3 Sammler „keine Memory-Dateien heute" REFUTED (zwei Dateien + MEMORY.md); B4 Sammler „Frische alle pass" gilt nur auf Lauf-Ebene — die Widerlegungsbahn zog die Check-Run-Ebene: `freshness` an d5a57e16 (#3024) und cfd6db83 (#3042) je **failure**, nach den Handover-Commits success; der Lauf 34464576309 meldet trotzdem `success` (`continue-on-error`).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | #1/#2: Owner-Zurufe geliefert; Auftrag K1–K5 nach heute 0/5 erfüllt, Abweichung im Sachstand begründet |
| architektur_design | 4 | #7 (Dublette TODO_BASIS), #11 (Regex nur für `/r/` zu großzügig) |
| code_konventionstreue | 4 | #9 (falsche Docstring-Behauptung), #20 (PR-Text ≠ PR-Inhalt); Commit-Format und test_should_* konform |
| risiko_debt | 2 | #19 (Flotten-Token in PR-Workflow gegen ADR-238, Rework nötig), #21 (Betreff im öffentlichen Repo), #3 |
| prozess_effizienz | 3 | #10 (Doppelarbeit), #12 (zwei rote CI-Zyklen fremder Ursache), #14 (Branch-Wiederverwendung) |
| entscheidungsqualitaet | 3 | #4 (verfrühte Deklaration), #19 (Freigabe auf falscher Gleichsetzung „derselbe Token wie …") |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| #3034/#3042 tragen „K1" im PR-Body, `docs/betrieb/` existiert nicht | PR nennt ein Kriterium nur, wenn er das im Issue definierte Artefakt des Kriteriums anfasst; sonst „zahlt vor auf K1" | #1 |
| Nach neun PRs kein Messjournal, kein Melder, kein Prüfskript, kein Drill | Erster Bauschritt je Anwendung ist die Betriebsakte mit Messjournal-Pfad; Symptom-Fixes erst danach | #2 |
| Sechs Folgearbeiten als Prosa ohne Anker-Form | Je Folgearbeit eine Zeile in Anker-Form (`#N`/Link) im Issue-Body oder Sub-Issue, im selben Turn — die Regex aus deferral_anchor_check.py ist der Maßstab | #3 |
| #3024 ordnete Alias ohne Tunnel-Check zu; `~/.cloudflared/mail-links.yml` hätte 8789 gezeigt | Vor jedem ports.yaml-Eintrag: Ingress-Config und Unit-Liste lesen, Zeile im PR-Body | #4 |
| Zeitung nicht berührt | Reihenfolge im Issue-Body als Checkliste, damit „Zeitung offen" sichtbar bleibt | #5 |
| #3038 ohne Refs auf den Auftrag | Nebenbefund bekommt „Refs #3015 (Blocker)" oder ein eigenes Issue, bevor der PR entsteht | #6 |
| `TODO_BASIS` zweimal | `from board import TODO_BASIS` oder gemeinsames Konstanten-Modul in tools/mail_agent | #7 |
| Sieben Tests lesen den Produktivkatalog, drei an Positionen | Fixture-Kopie mit synthetischen Diensten für Verhaltenstests; ein einziger, so benannter Golden-Test gegen den ausgelieferten Katalog ohne Positionsannahmen | #8 |
| Docstring behauptet Abwesenheit von `<body>` ohne Grep | Behauptung über Fremdcode im Kommentar braucht `grep -n` + Zeilennummer (Memory `behauptung-ueber-fremdcode`) | #9 |
| #3030 gebaut, ohne offene PRs des Tages auf derselben Datei zu prüfen | `repo-session start` listet offene PRs des Tages mit denselben Pfaden (Gate parallel-session-pr-collision umbauen, Quelle) | #10 |
| `/r/`-Seite hat eigenen `<body>` und bekommt die Leiste trotzdem per Regex | `_graph_rendern()` bekommt einen `nav`-Parameter; Regex-Einschub nur für `/a/`, `/m/` (Fremd-HTML) | #11 |
| Test der Parallelsitzung las `laeufe[0]` des Produktivkatalogs | Test prüft die eigene Handlung (`[-1]`); Golden-Test des Artefakts als eigener, so benannter Test | #12 |
| Zweiter Commit auf den Branch eines gemergten PR gepusht → neuer PR auf altem Branch | Nach „* [new branch]" beim Push: PR-Zustand prüfen, neuen Branch anlegen (Memory `vor-dem-nachschieben`) | #14 |
| Bot-Lauf grün, `gh pr view --comments --json` bricht, `grep -q` sieht nichts | Fehler eines Kommandos im Bot ist ein roter Lauf, nie „kein Kommentar" (`set -o pipefail` + Exit prüfen) | #16 |
| „Closes #2719" in der Commit-Message, PR-Body auf „Refs" umgestellt, Issue trotzdem zu | Schließ-Schlüsselwort nur im PR-Body, nie in der Commit-Message (Memory geschrieben) | #17 |
| Freigabe „derselbe Token wie sechs andere Workflows" — die laufen aus vertrauenswürdigen Refs, dieser aus PR-Code | Vor jedem Token-Wechsel: Trigger des Workflows (`on:`) und Reichweite des Secrets (`git grep`) nennen, ADR-238 prüfen; für `pull_request` nur App-Token | #19 |
| PR-Body #3024 kündigte einen Commit an, der in #3030 landete; Body nie korrigiert | Wenn ein angekündigter Commit nicht in diesen PR kommt: PR-Body im selben Turn korrigieren (öffentliches Repo) | #20 |
| Test-Fixture trägt den Betreff-Schlüssel eines realen Vorgangs | Fixtures nur mit synthetischen `thread_key`s; Kontrollprobe vor dem Commit: `grep -c '<fixture-key>' ~/.claude/mail-vorgaenge.json` muss 0 sein | #21 |
| „live verifiziert" für #3042 nur in der Chat-Erzählung | Verifikation als Artefakt: Kommando + Ergebnis als Zeile im Auftrags-Issue oder Handover, bevor der Report es zählt | #22 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (120 Reports): `claim-before-cheapest-check` ×80 → mit #4/#9/#22 ×81; `deferred-item-no-tracking-issue` ×39 → ×40 (#3); `parallel-session-pr-collision` ×8 → ×9 (#10); `same-file-serial-prs` ×11 → ×12 (#3034/#3042 überlappend in tools/tests/test_todo_board.py 467-531 vs 526-542 — auf todo_board.py disjunkt, 3b); `ci-gate-maskiert-failure` ×10 → ×11 (#16; zweiter Tagesbeleg: Frische-Lauf grün bei rotem Job); `test-asserts-the-case-in-mind-not-the-harmful-one` ×5 → ×6 (#8/#12); `outbound-claim-must-match-own-repo-facts` (#20) hat als Memory ein Vorkommen, im Retro-Zähler noch keines — deshalb gate_candidate, nicht recurring. Alle sechs recurring-Slugs sind GATE-PFLICHT (≥2).

Memory-Abgleich (`grep` in MEMORY.md, existent): `feedback_runner_befund_vor_worktree_offene_prs_pruefen` — #10 ist dessen Wiederholung; `feedback_vor_dem_nachschieben_pr_zustand_pruefen` — #14; `feedback_behauptung_ueber_fremdcode_im_kommentar_braucht_dieselbe_pruefung` — #9; `feedback_outbound_claim_must_match_own_repo_facts` — #20. Vier Memories, die je einmal nicht wirkten: Memory trägt als Gate-Form für diese Klassen nicht.

### 5a. Rückfall-Prüfung (`gate_wirkung.py`: 0 RUECKFAELLIG, 13 zu-frueh, Rest unerprobt)

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| handover-stale-vor-merge (revised 2026-09-07) | 0 — zweimal gefangen (Check-Run `freshness` failure an d5a57e16 und cfd6db83, beide Male nachgezogen) | – | **Beleg FÜR das Gate** → gates_caught; Nebenbefund: `continue-on-error` färbt den Lauf grün, der Fang ist nur auf Check-Run-Ebene sichtbar (ci-gate-maskiert-failure) |
| aufschub-anker (blocking, unerprobt) | 1 (#3) | Quelle: der Required Check liest PR-Text, nicht die Sachstand-Kommentare des Auftrags-Issues | **ausweiten (Quelle):** Kommentare des verlinkten Auftrags-Issues mit derselben ANKER-Regex prüfen; `revised` + `revision_note` + Positivkontrolle über `gate_verankerung_check.py --neu` |
| parallel-session-pr-collision (process, revised 2026-08-12) | 1 (#10) | Quelle: Regel ohne Werkzeug; nichts zwingt den Check vor `repo-session start` | **umbauen:** `repo-session start` gibt offene PRs des Tages mit denselben Pfaden aus; Positivkontrolle: zwei Branches auf einer Datei |
| serielle-prs-auf-derselben-datei (advisory, built 2026-09-07, Modul tools/session_abgleich.py, Erzwingung Runner-Phase E.10) | 1 (#3034→#3042) | Quelle, zu spät: läuft erst am Sitzungsende, nach allen Merges; heute kein Lauf (kein Workflow, `gh run list --created 2026-09-10` ohne Treffer) | **umbauen:** Abgleich beim Anlegen des PR (oder `repo-session start`) statt am Ende; Falsifikationsregel (disjunkte Hunks) beibehalten |
| ci-gate-maskiert-failure | kein Registry-Gate unter diesem Slug | Quelle: Bot-Skript ohne Fehlerprüfung; Frische-Job mit `continue-on-error` | gate_candidate `bot-command-error-is-red-run` |

### 5b. Autonomie-Kalibrierung

- `over_ask` = 0: Neustart der Dienste und Token-Wechsel wurden vorgelegt — beides Prod/Security-Config (Gate); den Token-Edit stoppte der Klassifizierer selbst.
- `over_act` = 1, Klasse `refs-nachtraeglich-fuer-mandat`: #3043 wurde nachträglich per „Refs #3015" an das Mandats-Issue gehängt, damit `pr_merge_sa.py` M1 sah, obwohl der Test aus einer Parallelsitzung stammt. Sachlich ein Blocker für K1-PRs; die Verknüpfung entstand aber für das Werkzeug. Kein Prod-Effekt.

## 6. Verankerung

memory_candidates (Vorschläge, nicht selbst geschrieben):
- `feedback_ports_eintrag_braucht_ingress_und_unit_check` — „Ein ports.yaml-Eintrag ohne Blick in `~/.cloudflared/*.yml` und `systemctl --user list-units` beschreibt womöglich einen anderen Dienst (todo.iil.pet: 8789 statt 8787, 2026-09-10, #3024→#3039)." drift: true.
- `feedback_branch_nach_merge_nicht_wiederverwenden` — „Nach ‚* [new branch]' beim zweiten Push ist der PR gemergt: neuer Branch, nicht neuer PR auf altem Branch — sonst vermischen sich die CI-Läufe zweier PRs (#3024/#3030)." Ergänzung zu `vor-dem-nachschieben`.
- `feedback_token_freigabe_nennt_trigger_und_reichweite` — „‚Derselbe Token wie Workflow X' ist keine Begründung: entscheidend ist `on:` (pull_request führt PR-Code aus) und was das Secret sonst darf; ADR-238 verlangt für PR-Workflows App-Token (#3027/#3030, 2026-09-10)." drift: true.
- `feedback_fixture_keys_nie_aus_dem_ledger` — „Test-Fixtures im öffentlichen Repo tragen nur synthetische `thread_key`s; Kontrollprobe `grep -c` gegen `~/.claude/mail-vorgaenge.json` = 0 (#3042, Vorgang 189)."
- Bereits in der Session geschrieben und vom Skeptiker (B2) bestätigt: `feedback_closes_im_commit_text_schliesst_trotz_refs_im_pr_body`.

adr_candidates: keine neue ADR — #19 ist ein Verstoß gegen die bestehende ADR-238, kein neuer Entscheid.

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Betriebsakte je Anwendung anlegen | platform | #3015 | 🔵 ich | ich: K1 zuerst, dann Symptome |
| M2 | Sechs Folgearbeiten in Anker-Form in #3015 | platform | #3015 | 🔵 ich | ich, nächster Turn |
| M3 | `TODO_BASIS` importieren, Docstring korrigieren, `nav`-Parameter für `/r/` | platform | #3015 | 🔵 ich | ich, ein PR (#7, #9, #11) |
| M4 | PROJECT_PAT im PR-Workflow gegen ADR-238 (App-Token) | platform | #3046 | 🟢 du | du: Entscheid, dann ich |
| M5 | Fixture-Betreff in test_mail_link_server.py synthetisieren | platform | #3015 | 🔵 ich | ich, mit M3 |
| M6 | PR-Body #3024 korrigieren (Nachtrag 2 gehört zu #3030) | platform | #3024 | 🔵 ich | ich, ein Edit |
| M7 | Verifikation #3042 als Artefakt in #3015 | platform | #3015 | 🔵 ich | ich, ein Kommentar |
| M8 | Gate parallel-session-pr-collision umbauen | platform | Registry | 🟢 du | du: Konsequenz bestätigen |
| M9 | aufschub-anker auf Issue-Kommentare ausweiten | platform | Registry | 🟢 du | du: Konsequenz bestätigen |
| M10 | serielle-prs-Melder vor den Merge ziehen | platform | Registry | 🟢 du | du: Konsequenz bestätigen |
| M11 | Katalog-Tests auf Fixture-Kopie umstellen (#8) | platform | #3047 | 🔵 ich | ich, nach Owner-Blick auf iil-assist |
| M12 | Streichbahn: keiner (Begründung im Frontmatter) | – | – | ✅ | – |

## 8. Nicht verifiziert (Restlücken)

- Ob der Fixture-Schlüssel „Submission of Chapters" wörtlich der Betreff ist — billigster Check (lokal, nicht im Repo): `grep -c 'Submission of Chapters' ~/.claude/mail-vorgaenge.json`, nur die Zahl.
- Ob der vom Prozess-Finder erwähnte rote Frische-Lauf auf einem dritten Branch liegt — `gh run list --workflow handover-freshness-advisory.yml --json conclusion,headBranch --limit 50` (durch die Check-Run-Belege an #3024/#3042 nicht mehr entscheidungsrelevant).
- news-hub lokal nicht gelesen (Finder-Mandat), nur `gh pr list`.
- Wer die zweite Memory-Datei von heute (`mcp-werkzeugliste-…`, 10:04) schrieb — Parallelsitzung oder diese; kein Einfluss auf Befunde.
- Fork-PRs bekommen bei `pull_request` keine Secrets; betroffen von #19 sind Branch-PRs im Repo — ob ein Branch-PR eines Nicht-Owners möglich ist (Collaborator-Liste), wurde nicht geprüft: `gh api repos/achimdehnert/platform/collaborators --jq '.[].login'`.

## Widerlegung

Phase 3b (Opus, frischer Kontext, sah Report-Entwurf + Footprint + Artefaktliste):
- #1 BESTAETIGT (Issue schließt Outline ausdrücklich aus). #3 BESTAETIGT, Severity hoch → mittel. #13 GEKIPPT (Issue #3027 neun Minuten vor dem Merge, Check advisory, Merger Co-Owner). #18 GEKIPPT (`board_als_html` liegt nicht auf dem Injektionspfad; Restform in #11).
- #8 GEKIPPT zurück auf SURVIVES (alle sieben Tests am Produktivkatalog, drei an Positionen). #11 GEKIPPT zurück auf SURVIVES (Routenzählung: `/a/`, `/m/` Fremd-HTML). #15 BESTAETIGT als REFUTED (Merge-Verteilung = CODEOWNERS-Kontrolle).
- NEU: #19 Token-Reichweite gegen ADR-238; #20 PR-Body #3024 beschreibt fremden Commit; #21 realer Betreff-Schlüssel in öffentlicher Fixture; #22 „live verifiziert" ohne Artefakt.
- §8 entschieden: Frische-Gate zweimal gefangen (Check-Run-Ebene); serielle-prs-Melder läuft strukturell zu spät.
- Abdeckung ohne Fund: Personenbezug in Issue-Kommentaren, neun PR-Bodies, Commit-Messages und Diffs — nur `noreply@anthropic.com`.

## Streichbahn

Keiner. Begründung: Jedes heute berührte Gate hat entweder gefangen (Frische, zweimal auf Check-Run-Ebene) oder wird nachgeschärft (aufschub-anker, parallel-session, serielle-prs). Der einzige Kandidat mit Belegart „kein Effekt" — der serielle-prs-Melder, der erst am Sitzungsende läuft — trägt die einzige Falsifikationsregel (disjunkte Hunks) für `same-file-serial-prs` ×12 und wird deshalb vor den Merge gezogen, nicht gestrichen.

## Self-Review

Meta-Agent (sonnet, sah nur Report + Skill): 10 von 11 Checks PASS. FAIL an Punkt 2: `phase3_refuted: 3` — die Zahl ist die des unabhängigen Phase-3-Skeptikers (A1 #8, A2 #11, A3 #15 REFUTED), die REFUTED-Menge im Endstand nach 3b ist eine andere (#13, #15, #18): 3b kippte #8 und #11 zurück und #13, #18 hinzu. Beide Mengen haben drei Elemente, `refuted_rate` 0.14 bleibt; die Definition im Frontmatter folgt dem Skill (Skeptiker-Zahl), der Endstand steht in §2. Weitere Korrekturen nach Meta: Streuzeile im Widerlegungsabschnitt entfernt; `outbound-claim-must-match-own-repo-facts` von recurring (Zähler 1) nach gate_candidates verschoben. Band-Vergleich: 0.14 liegt unter 0,2 — Aussage erst über mehrere Retros; die echte Falsifikationsquote 3/22 = 0.14 ist identisch, weil `pre_refuted` 0 ist. Bemerkenswert an dieser Retro: der Skeptiker kippte 3/3 Bewertungsbefunde, die Widerlegungsbahn kippte 2 davon zurück — zwei Instanzen mit frischem Kontext waren sich bei zwei von drei Urteilen uneins; Entscheider war jeweils die breitere Routen-/Testzählung.

**getan** · Phase 0 (gate_wirkung, retro_kpis, Nominierung) · Phase 1 Collector haiku · Phase 2 drei Finder sonnet · Phase 2.5 vier Widersprüche markiert · Phase 3 ein gebündelter Skeptiker sonnet · Phase 3b Opus · Phase 7 — **angenommen** · Session-Grenze über PR-Nummern/Branches, Parallel-PRs ausgeschlossen — **nicht verifizierbar** · §8 — **offen geblieben** · Phase 5 Meta, Commit des Reports, Tracking-Artefakte für M4/M11 (#3046, #3047 angelegt).
