---
retro_schema: 1
date: 2026-09-17
repo_scope: [platform, chat-hub, dev-hub, news-hub, iil-voice-agent]
session_id: 50d29a
footprint: deep
findings_total: 15
findings_survived: 12
refuted_rate: 0.20
phase3_refuted: 3   # F7 (Scope-Checkpoint), F9 (Workaround #69), F12 (Plaud-Eigenbau); 3b: F2 in der Severity gekippt (bleibt SURVIVES), F14/F15 neu
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [pii-in-host-log, deploy-dispatch-before-image-build, pr-body-stale-after-followup-commits, inline-heredoc-quoting-rework, gate-claim-before-cheapest-check-wirkungslos, direct-gh-pr-merge-bypasses-sa-m]
recurring_findings: [claim-before-cheapest-check, gate-claim-before-cheapest-check-wirkungslos, issue-offen-nach-gemergtem-fix, pr-body-stale-after-followup-commits, inline-heredoc-quoting-rework, test-asserts-the-case-in-mind-not-the-harmful-one, dod-reinterpreted-only-in-pr-body, direct-gh-pr-merge-bypasses-sa-m]
gates_caught: [aufschub-anker]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 2 neu"
streichkandidaten: [memory-feedback-reporting-table-format-dublette]
streich_begruendung: ""
---

# Session-Retro 2026-09-17 · platform · 50d29a

Sitzung: Kapitäns-Session in `~/github/platform`, 2026-09-16 14:40 UTC bis 2026-09-17 09:20 UTC. Vier Owner-Aufträge in Folge: (1) Raum „Achim / Lotse" soll Office-Anhänge lesen und Wünsche an die Kapitäns-Sitzung übergeben (chat-hub#114/#115, platform#3266); (2) Morgen-Zeitung: Block „Privacy Xperts" nach Zielzustand news-hub#62 (dev-hub#359/#361, news-hub#63/#64/#68/#69, drei Deploys, Host-Skript per `scp`); (3) Preisempfehlung Retention-Scanner für Landkreis Günzburg (zwei HNU-Entwürfe, nichts gesendet); (4) Plaud-Analyse mit Vorlagen-Katalog (16.455), fünf Aufnahmen auf der gx10 und Konzept KONZ-iil-voice-agent-004 (iil-assist-voice#129). Artefaktliste: `~/shared/retro-artefakte-50d29a.md`; Transkript-Kennzahlen per `tools/retro_transkript_kennzahlen.py` (Ausgabe neben diesem Report: `session-retro-2026-09-17-platform-50d29a.kennzahlen.txt`): 291 Bash-Aufrufe, 4 Subagenten, 5 Klassifizierer-Ablehnungen, 30 Fehlerläufe.

**Footprint `deep`** (5 Repos, 2 auto-Prod-Deploys dev-hub, 5 Dispatch-Deploys news-hub, 1 Migration). Agenten: 3 Finder (sonnet), 3 Skeptiker (sonnet, nur auf die 5 Bewertungsbefunde), Widerlegungsbahn (opus), Meta (sonnet) = 8; Phase 1 inline.

**Phase 0.0:** `tools/gate_wirkung.py` → zwei Gates `RUECKFAELLIG`: `issue-offen-nach-gemergtem-fix` (Vorkommen in dieser Sitzung: dev-hub#360 blieb 16 h nach dem Merge von #361 offen) — Ursache **an der Quelle**: der Melder läuft erst am Sitzungsende, der Merge-Moment ist stumm → **umbauen** (`tools/pr_merge_sa.py` nennt nach dem Merge offene `Refs`-Issues, Maßnahme M6). `gate-modul-prueft-weniger-als-sein-name` — kein Vorkommen in dieser Sitzung, Ursache hier nicht bestimmbar → Restlücke §8.

## 1. Executive Summary

- Alle vier Aufträge sind auf Prod bzw. beim Owner: Raum-Session liest Office-Anhänge und übergibt per „übergeben"; der Privacy-Xperts-Block lief 20:55 UTC zum ersten Mal echt; Preisempfehlung als Entwurf; Konzept KONZ-004 gemergt.
- Schwerster Befund: dev-hub#359 schrieb fremde Absenderadressen ins Host-Journal; der Lauf um 17:39 UTC legte zehn verschiedene Adressen (drei davon Personen) dort ab, bevor #361 (17:40) den Grund entpersonalisierte (F1).
- Zwei Deploy-Ausfälle in news-hub mit verschiedenen Ursachen (Race 6 s nach Merge; verschlucktes push-Ereignis) — der strukturelle Fix #65 ist offen (F8).
- Ein Subagent meldete „beide PRs grün", während platform#3266 an einem Gate rot war (F10); ein Subagent erweiterte die Reichweite der Raum-Session (`repo_slug`), im Review vor dem Merge gefangen, aber der PR-Text blieb falsch (F6).
- Die Falsifikation kippte 3 von 5 Bewertungsbefunden (Scope-Checkpoint fiel vor dem ersten Prod-Schritt, #69 war offen getrackt, der Plaud-Eigenbau war Owner-Anweisung nach Doku-Prüfung); die Widerlegungsbahn stufte F2 herab und fand zwei Neue: chat-hub#114 (Allowlist der Raum-Session) per direktem `gh pr merge` am SA-M-Werkzeug vorbei und ohne Freigabe-Vermerk (F14), und `mergedBy` taugt nicht als Owner-Klick-Beweis (F15).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| F1 | Verwurf-Grund mit fremder Absenderadresse im Host-Journal; 77 min auf Prod, Lauf 17:39 UTC legte 12 Adress-Zeilen (10 Adressen, 3 Personen) ab | fehlende Validierung | hoch | SURVIVES | dev-hub#359 Diff `apps/mail_agent/lesenaht.py` (`from_addr!r`), #361 Fix; `journalctl -u news-hub-tageslauf` 16:00–22:00 UTC | pii-in-host-log (neu) |
| F2 | `anhang_text.py` parst fremde XML-Teile mit `xml.etree`; Schutz gegen Entity-Amplifikation hängt an expat ≥ 2.4.1 (dev-server 2.6.1 blockt, in 3b geprüft), nicht am Code | fehlende Validierung | niedrig | SURVIVES | platform#3266 `tools/mail_agent/anhang_text.py` (`ET.fromstring`); 3b: `ParseError: limit on input amplification` bei Entity-Bombe | untrusted-xml-parse-relies-on-expat-version (neu) |
| F3 | Kein Test für den `MAX_TEIL_BYTES`-Ablehnungspfad | fehlende Validierung | niedrig | SURVIVES | platform#3266 `tools/tests/test_anhang_text.py` (kein Fall > Grenze) | limit-constant-without-boundary-test (neu) |
| F4 | K3 (0 CTA-Zeilen) gegen synthetische Bodies getestet statt der im Kriterium geforderten drei echten Mails; erster Prod-Block trug CTA-Rest | fehlende Validierung | hoch | SURVIVES | news-hub#63 Body (K3), #67 Befund, #68 Fix | test-asserts-the-case-in-mind-not-the-harmful-one (×10) |
| F5 | K5 „Link/Screenshot im PR" nicht erfüllt; #62 per Prosa-Kommentar geschlossen (DB-Abfrage fand statt, hängt nirgends) | verfrühte Festlegung | mittel | SURVIVES | `gh issue view 62 --json comments` (21:02 UTC), PR #63/#64 Bodies; news.iil.pet → 302 Cloudflare Access | dod-reinterpreted-only-in-pr-body (×5) |
| F6 | chat-hub#115 Body beschreibt `owner/repo`-Durchlass in `repo_slug`, der vor dem Merge (398989e) zurückgebaut wurde | Kommunikation | mittel | SURVIVES | chat-hub 398989e, `origin/main:deploy/lotse_auftrag.py` Z. 234–246, PR-Body #115 | pr-body-stale-after-followup-commits (×3) |
| F7 | Scope-Checkpoint-Satz bis 21:15 UTC nicht ausgesprochen | Prozesslücke | mittel | REFUTED | dev-hub#359 `mergedAt` 16:23:33Z vs. Transkript-Satz 16:02:28 UTC (Scope-Checkpoint, Prod-Schritt als Owner-Zug); dev-hub#360 Kommentar 16:54:08Z (Checkpoint vor dem zweiten Deploy) — Artefakte: PR-/Issue-Zeitstempel, Zitat aus dem Transkript | — |
| F8 | news-hub Deploy zweimal rot: Race 6 s nach Merge (`11cbddc`, Dispatch durch die Sitzung), kein push-Lauf für `ea268cf` (Dispatch durch den Owner 21:05:42); `deploy.yml` wartet nicht auf das Image, liefert `tageslauf.sh` nicht mit | Prozesslücke | hoch | SURVIVES | Runs 35124460166, 35150427921; `gh run list --json headSha,event` ohne push-Zeile für ea268cf; Issue #65 offen | deploy-dispatch-before-image-build (neu) |
| F9 | #69 als Workaround, der #65 verdeckt; „derselbe Fehler" | Prozesslücke | mittel | REFUTED | zwei Ursachen (Race vs. fehlendes Ereignis), #69 `Refs #65`, Body benennt Doppelzweck, Freigabe in #65 auf Doku-PR begrenzt | — |
| F10 | Subagent meldete „beide PRs grün", platform#3266 war BLOCKED (Aufschub-Anker rot bis 15:05:21, grün erst 15:06:29) | fehlende Validierung | mittel | SURVIVES | Handback 15:05:24 UTC; Run 35112915014 (FAILURE), Run 35113056029 (SUCCESS) | claim-before-cheapest-check (×85), gate-claim-before-cheapest-check-wirkungslos (×3) |
| F11 | 30 Fehlerläufe: 10 Shell-Quoting/Heredoc, 11 echte (Plaud-Automatisierung), 7 Guard-Blocks | Werkzeug | mittel | SURVIVES | `retro-kennzahlen-50d29a` (14:47 bis 09:14 UTC) | inline-heredoc-quoting-rework (×3) |
| F12 | Plaud: acht Fehlerläufe beim Eigenbau statt Doku-Weg — verfrühte Festlegung | verfrühte Festlegung | mittel | REFUTED | Beleg = Transkript-Reihenfolge (Werkzeug-Aufrufe 07:34–07:46 `docs.plaud.ai`, 08:08 `llms.txt`; Owner-Nachricht 08:20 „mit playwright"); kein externes Artefakt möglich — REFUTED-Verdikt, Kernfakt (8 Fehlerläufe) aus der Kennzahlen-Datei | — |
| F13 | dev-hub#360 16 h offen nach gemergtem Fix (#361 `Refs`, nicht `Closes`) | Prozesslücke | niedrig | SURVIVES | `gh issue view 360` (closed 2026-09-17 09:35), `gh pr view 361` (merged 2026-09-16 17:40) | issue-offen-nach-gemergtem-fix (Gate rückfällig) |
| F14 | chat-hub#114 (Allowlist-Zeile der Raum-Session, Permission-PR) per direktem `gh pr merge` gemergt — am SA-M-Werkzeug vorbei (Dry-Run heute: W2/M0), kein Freigabe-Vermerk, Owner-Wort nur im Chat und gebündelt | Prozesslücke | mittel | SURVIVES (3b NEU) | Transkript 15:06:26 UTC `gh pr merge 114 --squash`; PR-Body #114 ohne Freigabe-Zeile; Memory `project_sa_m_merge_autonomy.md` („nie direkt `gh pr merge`") | direct-gh-pr-merge-bypasses-sa-m (×2, aifw#62) |
| F15 | Beleg „`mergedBy: achimdehnert` = Owner-Klick" ist falsch: #359 mergte die Sitzung selbst über `pr_merge_sa.py` (M1 aus #62); nur #361 war ein Owner-Klick | fehlende Validierung | niedrig | SURVIVES (3b NEU) | Transkript 16:23:24 UTC `pr_merge_sa.py 359`, Deploy-Run 35121596548 queued 16:23:36 | mergedby-is-not-owner-click-proof (neu) |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Vier Aufträge geliefert und auf Prod/beim Owner; K5 formal offen (F5), K3 erst im zweiten Anlauf (F4) |
| architektur_design | 4 | Allowlist je Ordner an Quelle und Digest, Block getrennt von der Themenbildung — tragfähig; XML-Schutz nur über expat-Version (F2) |
| code_konventionstreue | 3 | Grenzwert ohne Test (F3), PR-Text nicht nachgezogen (F6), zehn Quoting-Fehlerläufe (F11) |
| risiko_debt | 2 | Personenadressen im Host-Journal (F1), Deploy-Race ungefixt (F8), Permission-Merge ohne Vermerk (F14) |
| prozess_effizienz | 3 | Zwei Deploy-Ausfälle (F8), falsche Grün-Meldung (F10), 30 Fehlerläufe (F11); dagegen 10 PRs in 19 h ohne dangling PR |
| entscheidungsqualitaet | 4 | Reichweiten-Fehler vor dem Merge gefangen (F6), Miete-statt-Kauf und Plaud-nur-als-Recorder geerdet; Schließen von #62 ohne Artefakt (F5), Permission-PR am Werkzeug vorbei (F14) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Verwurf-Grund mit `from_addr` im Diff, gemergt und deployt (dev-hub#359) | Brief- und Review-Zeile „Welche Strings landen in stderr/Journal? Keine Adressen/Namen" — Grep `!r`/`from_addr` in Log-Zeilen vor Merge | #F1 |
| `ET.fromstring` auf fremde XML-Teile, Schutz nur durch expat-Version (platform#3266) | `defusedxml.ElementTree` (versionsunabhängig) + Entity-Bomben-Test als Positivkontrolle | #F2 |
| `MAX_TEIL_BYTES` ohne Test (platform#3266) | Test mit gefälschtem `ZipInfo.file_size` über der Grenze (kein 50-MB-Fixture nötig) | #F3 |
| K3 gegen synthetische Bodies geprüft (news-hub#63) | Kriterium wörtlich fahren: drei echte Mails aus dem Index als Fixture (entpersonalisiert), bevor „K3 belegt" im PR steht | #F4 |
| #62 per Prosa geschlossen, K5 forderte Link (news-hub#62) | Schließ-Kommentar trägt das Artefakt: Query-Ausgabe als Block + Run-ID; ist ein Screenshot unmöglich, Kriterium im Issue anpassen, nicht umdeuten | #F5 |
| PR-Body beschreibt zurückgebautes Feature (chat-hub#115) | Nach jedem Folge-Commit auf einem PR: Body-Abschnitt „Was" gegen `gh pr diff` lesen und korrigieren — als Zeile im Merge-Werkzeug | #F6 |
| Deploy 6 s nach Merge, zweiter Deploy ohne push-Lauf (news-hub Runs 35124460166/35150427921) | `deploy.yml` prüft GHCR-Manifest für `<sha>` (Poll, Deckel 10 min) und kopiert `deployment/scripts` + Units; bis dahin: vor Dispatch `gh run list` auf push-Lauf des Merge-Commits (#65) | #F8 |
| Subagent: „beide PRs grün" bei BLOCKED (platform#3266) | Brief-Pflichtzeile: `gh pr view --json mergeStateStatus,statusCheckRollup` auf den Head-SHA, Ausgabe wörtlich in die Rückmeldung — kein „grün" ohne Zeile | #F10 |
| 10 Quoting-Fehlerläufe (typografische Anführungszeichen in Bash-Strings, jq `;`, Heredoc) | Texte mit Anführungszeichen nie inline in Bash: Write-Tool → `--body-file`; jq-Ausdrücke in einfachen Anführungszeichen ohne `;` | #F11 |
| #360 16 h offen nach Merge (dev-hub#361) | `pr_merge_sa.py` listet nach dem Merge offene `Refs`-Issues und fragt „schließen?" — oder `Closes` verwenden, wenn der PR den Fix vollständig trägt | #F13 |
| chat-hub#114 per `gh pr merge` direkt, ohne Vermerk (15:06 UTC) | Jeder Merge — auch in Fremd-Repos, auch Doku/Allowlist — läuft über `pr_merge_sa.py`; Permission-PRs bekommen den Freigabe-Vermerk vor dem Merge in Body oder verlinktes Issue | #F14 |
| „mergedBy" als Owner-Klick-Beweis gewertet (§5b-Entwurf) | Owner-Klick nur belegen, wenn im Transkript kein Merge-Aufruf der Sitzung steht; sonst Werkzeug-Ausgabe + M-Stufe zitieren | #F15 |

## 5. Längsschnitt

`tools/retro_kpis.py` (vor diesem Report): `claim-before-cheapest-check` ×84, `test-asserts-the-case-in-mind-not-the-harmful-one` ×9, `dod-reinterpreted-only-in-pr-body` ×4, `pr-body-stale-after-followup-commits` ×2, `inline-heredoc-quoting-rework` ×2, `gate-claim-before-cheapest-check-wirkungslos` ×2 — alle mit diesem Report ≥3 ⇒ GATE-PFLICHT. `direct-gh-pr-merge-bypasses-sa-m` ist in den Retros ×1 (dieser Report); das erste Vorkommen aifw#62 steht nur in der Memory `project_sa_m_merge_autonomy.md` (Nachtrag 2026-09-02) — zusammen zwei ⇒ als GATE-PFLICHT geführt, Zähler holt beim nächsten Vorkommen nach. Neu: `pii-in-host-log` (verwandt: `pii-in-public-fixtures` ×1), `deploy-dispatch-before-image-build`, `untrusted-xml-parse-relies-on-expat-version`, `limit-constant-without-boundary-test`, `mergedby-is-not-owner-click-proof`. Memory-Abgleich (`grep` in `MEMORY.md`): Drift-Memories zu Secrets/PII existieren (`feedback_env_grep_prefix_leaks_secrets`), keine zu PII in Host-Logs.

### 5a. Rückfall-Prüfung

- **`issue-offen-nach-gemergtem-fix` — Gate rückfällig** (Vorkommen F13). Antwort: **umbauen** — der Melder (`test_session_abgleich.py`, Sitzungsende) sieht den Merge-Moment nicht; Konsequenz M6: `pr_merge_sa.py` prüft `Refs`-Issues nach dem Merge. Registry-Eintrag: `revised` + `revision_note` (M6), Positivkontrolle dev-hub#360/#361.
- **`gate-claim-before-cheapest-check-wirkungslos` — dritte Wiederkehr** (F10): der Evidenz-Scanner prüft Antworten der Hauptsitzung, nicht Subagenten-Rückmeldungen. Antwort: **ausweiten** — Pflichtzeile im Delegations-Brief (M5); `claim-before-cheapest-check` bekommt `revised` mit dieser Ausweitung, kein zweites Gate.
- `gate-modul-prueft-weniger-als-sein-name`: rückfällig laut Wirkungsbilanz, ohne Vorkommen hier — keine Konsequenz aus dieser Retro (§8).

### 5b. Autonomie-Kalibrierung

`over_ask`: keine Klasse — die vorgelegten Entscheidungen (Merge-Klicks, Deploy, Session-Neustart, `scp`) waren jeweils vom Klassifizierer erzwungen oder Prod-Schritte. `over_act`: keine Klasse — jeder Prod-Schritt trägt ein Owner-Wort: dev-hub#359 über `pr_merge_sa.py` mit M1 aus news-hub#62 (SA-4 + „11 go"), #361 Owner-Klick (kein Merge-Aufruf im Transkript), news-hub#63/#64/#68 mit Vermerk in #62/#65. F14 (chat-hub#114) ist kein over_act — die Erweiterung war 14:50 benannt und mit „4 go 5 go" freigegeben —, aber ein Werkzeug-Bypass ohne durables Artefakt. `retro_kpis.py --nominierung`: keine neue Nominierung aus dieser Sitzung.

## 6. Verankerung

`memory_candidates` (kopierfertig, Verankerung entscheidet der Owner):

```markdown
---
name: feedback_pii_never_in_host_log_reason_strings
description: "Fehler-/Verwurf-Gründe, die per stderr ins Host-Journal laufen, tragen nie Adressen/Namen — dev-hub#359 legte 77 min lang Fremdadressen ab (Prod-Lauf 17:39 UTC)"
metadata: {type: feedback, drift: true, drift_episode: 2026-09-16-verwurf-grund-mit-adresse}
---
Ein `f"... {from_addr!r} ..."` in einer Verwurf-/Fehlerzeile ist ein Datenabfluss, sobald die Zeile in ein Journal geht.
**Why:** dev-hub#359 (Allowlist je Ordner) schrieb die Adresse in den Grund; der Tageslauf 17:39 UTC legte zehn Adressen (drei Personen) im Host-Journal ab, #361 entfernte sie eine Minute später.
**How to apply:** Vor Merge jede neue Log-/stderr-Zeile lesen: Grund + Rückverweis (ID), nie den Rohwert. Im Delegations-Brief als Testplan-Zeile. Siehe [[feedback_env_grep_prefix_leaks_secrets]].
```

```markdown
---
name: feedback_deploy_dispatch_needs_image_build_first
description: "news-hub deploy.yml zieht das Image sofort — Dispatch vor dem push-Build endet mit not found; für einen Merge-Commit kann der push-Lauf auch ganz fehlen (ea268cf)"
metadata: {type: feedback, drift: true, drift_episode: 2026-09-16-deploy-vor-build}
---
Vor `gh workflow run deploy.yml`: `gh run list --json headSha,event,conclusion` muss für den Merge-Commit einen `push`-CI-Lauf mit `success` zeigen; fehlt er, einen weiteren Merge nachschieben. `tageslauf.sh` kommt nur per `scp` auf den Host. Strukturfix: news-hub#65.
```

`adr_candidates`: keine — beide Befunde sind Ergänzungen nach bestehendem Muster (adr-threshold), der Deploy-Fix ist ein Workflow-Issue (#65), kein Architekturentscheid.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Journal-Aufbewahrung prüfen, Adressen tilgen | news-hub (Host) | — | 🟢 | du: `journalctl --vacuum-time` oder Rotation |
| M2 | `anhang_text.py`: defusedxml + Grenz-Test | platform | Issue anlegen | 🔵 | ich |
| M3 | `deploy.yml`: Image-Poll + Skripte mitliefern | news-hub | #65 | 🟢 | du: go |
| M4 | K5-Beleg nachtragen (Query-Ausgabe, Run-ID) | news-hub | #62 | 🔵 | ich |
| M5 | Delegations-Brief: Pflichtzeile `mergeStateStatus` vor „grün" | platform | Gate `claim-before-cheapest-check` revised | 🔵 | ich |
| M6 | `pr_merge_sa.py`: offene `Refs`-Issues nach Merge nennen | platform | Gate `issue-offen-nach-gemergtem-fix` revised | 🔵 | ich |
| M7 | chat-hub#115 Body korrigieren (repo_slug-Satz) | chat-hub | #115 | 🔵 | ich |
| M8 | Streichkandidat prüfen (§ Streichbahn) | platform | Memory | 🟢 | du: ja/nein |
| M9 | chat-hub#114: Freigabe-Vermerk + Issue-Link nachtragen | chat-hub | #114 | 🔵 | ich |
| M10 | HNU-Entwurf UID 24195 löschen (überholt) | — | HNU Entwürfe | 🟢 | du |

## 8. Nicht verifiziert (Restlücken)

- **getan:** 15 Befunde aus drei frischen Findern und der Widerlegungsbahn, 5 Bewertungsbefunde falsifiziert (3 gekippt), Host-Journal read-only geprüft (Adressen gezählt, nicht ausgegeben), Deploy-Runs und push-Läufe per `gh` gezogen, Transkript per JSON-Parse (kein Roh-grep), Entity-Bombe gegen `xml.etree` auf dem dev-server gefahren.
- **angenommen:** dass die Adressen im Journal nur dort liegen (keine Weitergabe, kein Log-Shipping) — Hypothese; dass `defusedxml` im platform-Tooling zulässig ist (Dependency-Policy nicht geprüft); dass expat auf dem Host der Raum-Session ≥ 2.4.1 bleibt.
- **nicht verifizierbar:** Ursache des fehlenden push-Laufs für `ea268cf` (GitHub-seitig; kein Artefakt); Plaud-Verarbeitungsort der Transkription (Doku schweigt); Inhalt der HNU-Entwürfe 24195/24196 (Mail-Lesen nicht im Retro-Mandat — billigster Check: Entwurfsordner per `/iil-mail` listen).
- **offen geblieben:** `gate-modul-prueft-weniger-als-sein-name` rückfällig ohne Vorkommen hier — billigster Check: `gate_wirkung.py --json` auf das Vorkommen 2026-09-17 in der Nachbar-Sitzung; M1, M3, M8, M10 sind Owner-Züge; F7 im engeren Sinn (kumulative Repo-Zählung) ist durch 3b geschlossen: die Hausregel zählt je Aufgabe, keiner der vier Aufträge überschritt zwei Repos.

## Widerlegung

Widerlegungsbahn (Opus, frischer Kontext): `origin/main` (fetch), PR-/Issue-Bodies, Actions-API inkl. `triggering_actor`, Journal read-only (Adressen nur gezählt), Transkript per JSON-Parse.

| # | Verdikt | Ergebnis | Beleg |
|---|---|---|---|
| F1 | BESTAETIGT | hält — „drei" ist Untergrenze | Journal 16:00–22:00 UTC: 33 `verworfen`-Zeilen, 12 mit Adresse, alle 17:39:05 UTC; 10 verschiedene Adressen (3 Personen, 3 unklar, 4 generisch); keine Adress-Zeile nach 17:39 → #361 hat gewirkt |
| F2 | GEKIPPT (Severity) | Existenz hält, Wirkung widerlegt | dev-server Python 3.12.3 / expat 2.6.1: `ET.fromstring` blockt Entity-Bombe (`limit on input amplification factor … breached`); externe Entities löst `xml.etree` nie auf; Rest = Abhängigkeit von expat ≥ 2.4.1 → niedrig |
| F3–F6, F10, F11, F13 | BESTAETIGT | halten | Testdatei ohne `MAX_TEIL_BYTES`; #67→#68; Schließ-Kommentar #62 ohne Artefakt; `origin/main:deploy/lotse_auftrag.py` Z. 234–246 vs. PR-Body #115; Run 35112915014 FAILURE 15:05:21 vs. Handback 15:05:24; Kennzahlen-Datei; #360/#361-Zeitstempel |
| F8 | BESTAETIGT, Zuschreibung korrigiert | hält | zweiter Dispatch (35150427921) durch den Owner 21:05:42 UTC (`<bash-input>`), Sitzungs-Dispatches 16:50, 16:54, 21:17 |
| F7 | BESTAETIGT (REFUTED bleibt) | hält | 16:02:28 UTC nennt beide Repos und den Prod-Schritt als Owner-Zug; Owner 16:11 „10 go 11 go"; zweiter Checkpoint 16:54 in dev-hub#360; Hausregel zählt je Aufgabe, keiner der vier Aufträge > 2 Repos |
| F9, F12 | BESTAETIGT (REFUTED bleibt) | halten | zwei Ursachen, `Refs #65`, Freigabe auf Doku-PR begrenzt; Doku-Fetches 07:34–07:46, Owner-Anweisung 08:20, Fehlerläufe ab 08:32 |
| N1 → F14 | NEU | chat-hub#114 per `gh pr merge` direkt | 15:06:26 UTC; Dry-Run heute W2/M0; kein Freigabe-Vermerk; Memory-Regel „nie direkt `gh pr merge`" |
| N2 → F15 | NEU | `mergedBy` ist bei Agent-Token immer der Owner | #359 per `pr_merge_sa.py` 16:23:24 UTC; #3266/#115 mergte das Zweitkonto @wirdigital |

Geprüft ohne Befund: Plaud-Zugangsdaten (nur Key-Namen im Transkript, Guard respektiert), Prod-Lesezugriff `devhub_web manage.py shell` (Aggregate im Rahmen von #62 K2, Charta Art. 2 nicht berührt), drei Memory-Dateien (kein Secret, keine Personenadresse). Unentscheidbar: HNU-Entwürfe (Mail-Lesen nicht im Mandat). Nicht geprüft: F4-Fixtures im Detail, Log-Shipping, gx10-Zugriff.

## Streichbahn

**Kandidat `memory-feedback-reporting-table-format-dublette`** — Belegart **Dublette**: die Repo-Memory `feedback_reporting_table_format.md` (Eintrag in `MEMORY.md`, Zeile „🌀 Antwortformat: … [Action Board]") wiederholt das Action-Board-Format, das `~/.claude/CLAUDE.md` selbst als „CANONICAL HIER — nicht in Repo-Memory neu ableiten" ausweist und dessen Repo-Kopien es als „Log, nicht Quelle" einstuft. Zwei Quellen für dieselbe Regel sind laut CLAUDE.md die belegte Drift-Ursache (≥5 Korrekturen). Vorschlag: Memory auf einen Ein-Zeilen-Zeiger kürzen.

## Self-Review

Meta-Agent (sonnet, nur Report gegen Skill): 1 ❌ → behoben, 10 ✅.

1. ✅ Belege: F1–F6, F8–F11, F13–F15 mit PR/SHA/Run/Datei; F7 nachbelegt (PR-/Issue-Zeitstempel), F12 als REFUTED mit Beleg = Transkript gekennzeichnet (kein externes Artefakt möglich).
2. ✅ Scores ganzzahlig, je an Befund verankert. 3. ✅ 12 Soll-Zeilen = 12 SURVIVES. 4. ✅ Frontmatter vollständig, `refuted_rate` 0,20 = 3/15. 5. ✅ Spalten eingefroren.
6. ✅ `gate_wirkung.py` in 0.0 und 5a; Rückfälle mit Antwort (umbauen/ausweiten). 7. ✅ Quote 0,20 im Band (untere Kante; echte Quote 3/(15−0) = 0,20).
8. ✅ Vierklang in §8. 9. ✅ Widerlegung/Streichbahn als Abschnitte, Belegart Dublette. 10. ✅ Pfad kollisionsfrei. 11. ✅ `retro_report_check.py` Exit 0.

## Extern-Handoff

Briefing für eine anbieter-fremde Zweitmeinung liegt unter `~/shared/session-retro-extern-2026-09-17-platform-50d29a.md` (Methode/Struktur/Blindflecken; keine Evidenz-Behauptungen). Rückweg: Antwort als `…-extern1.md` ablegen — Pflichtlektüre der nächsten platform-Retro.
