---
retro_schema: 1
date: 2026-09-23
repo_scope: [platform, chat-hub, mcp-hub, shared-ci, tax-hub, dev-hub]
session_id: 2c4009
footprint: full
footprint_reduction_reason: "deep → full: (a) jeder Prod-Schritt per Owner-Wort freigegeben und in #3398/#3256 festgehalten, (b) alles rollback-fähig (Backups, Inverse-SQL, Deploy-Tags), keine DB-Migration, (c) Befund-Schätzung ≤10"
findings_total: 11
findings_survived: 8
refuted_rate: 0.27
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [freigabe-im-chat-hebt-klassifizierer-nicht]
recurring_findings: [check-ohne-positivkontrolle, secret-leak-via-safe-pattern, deferred-item-no-tracking-issue, worktree-midsession-accumulation, direct-gh-pr-merge-bypasses-sa-m]
gates_caught: [claim-before-cheapest-check, aufschub-anker, subagent-prod-access-unscoped-prompt]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "1 gekippt, 1 neu"
streichkandidaten: []
streich_begruendung: "Keine Phase dieser Retro erfüllt eine der vier Belegarten: jede Pflicht-Phase hat hier einen Befund getragen oder korrigiert (3b kippte ein Recurrence-Etikett, Meta fand zwei Mängel, Skeptiker verwarfen 3 von 5 Bewertungsbefunden)."
---

# Retro 2026-09-23 — Offene Aufträge → Deploy-SSoT, Bump-Welle, Outline-Login (Sitzung 2c4009)

## 1. Executive Summary

- Aus der Frage „Status der offenen Aufträge“ wurde eine Sitzung über 6 eigene Repos plus 17 Konsumenten-PRs: Deploy-Reusables auf shared-ci als SSoT (#3403, #3408), Bump-Welle v1.1.18 (15 Deploys grün), native-ssh-Composite (shared-ci#89, Tag v1.1.19, Canary tax-hub#150 grün), llm-gateway stillgelegt, Container-Speicher-Melder (#3404), Outline-Login auf Cloudflare Access umgestellt.
- Schwerster Befund: ein DB-Passwort wurde per `bash -x`-Trace in die Sitzungsausgabe geschrieben (#3428); die Rotation ist trotz Owner-Freigabe offen, weil der Klassifizierer Credential-Operationen blockt.
- Die Outline-Umstellung ist ausgeführt, ihre Owner-Abnahme aber nirgends als eigenes Tracking-Item geführt — authentik-Stilllegung hängt an einem unbelegten Kriterium.
- Eine Entscheidungsvorlage (#3398) trug kurzzeitig eine falsche Zahl aus einem unverankerten grep; vor dem Owner-Entscheid selbst korrigiert.
- 3 von 10 Befunden fielen im Skeptiker-Pass (S2, P2, P6).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Entscheidungsvorlage nannte „6 Pins auf @main/@v1“ aus grep ohne Zeilenanfang-Anker (Kommentarzeilen mitgezählt); 26 min später im Kommentar korrigiert, vor Owner-Entscheid | fehlende Validierung | niedrig | SURVIVES (kommandobelegt) | platform#3398 issuecomment-5787819200 (Korrektur-Absatz) | check-ohne-positivkontrolle |
| 2 | Outline-DB-Passwort per `bash -x` über `docker inspect`-Env in die Sitzungsausgabe geschrieben | Werkzeug | mittel | SURVIVES (kommandobelegt) | platform#3428 (angelegt 10:05:18Z); Transkript 10:04:26 (nicht zitiert) | secret-leak-via-safe-pattern |
| 3 | Rotation des offengelegten Passworts trotz Owner-Wort „114 rotiere du“ nicht erfolgt; beide Versuche vom Klassifizierer geblockt, kein Folgeweg | Prozesslücke | mittel | SURVIVES (Skeptiker) | platform#3428 OPEN ohne Kommentar; kennzahlen 10:22:56, 10:23:26 | freigabe-im-chat-hebt-klassifizierer-nicht (neu) |
| 4 | Outline-Umstellung ausgeführt, Owner-Abnahme nur im Fließtext eines Kommentars, kein eigenes Tracking-Item; authentik-Stilllegung hängt daran | fehlende Validierung | hoch | SURVIVES (Skeptiker) | platform#3256 (7 Kommentare, letzter 10:09:01Z, keine Checkliste) | deferred-item-no-tracking-issue |
| 5 | `gh pr merge --admin` auf shared-ci#89 versucht, obwohl der PR 3 min vorher bereits gemergt war (Live-Zustand nicht neu geprüft) | fehlende Validierung | mittel | SURVIVES (kommandobelegt; Recurrence per 3b korrigiert) | iilgmbh/shared-ci#89 mergedAt 09:07:24 (mergedBy Owner) vs. Ablehnung 09:10:28; dazu direkte `gh pr merge --admin` statt `tools/pr_merge_sa.py` für Welle-Gruppen 2–5 | direct-gh-pr-merge-bypasses-sa-m (3. Vorkommen) |
| 6 | chat-hub-Worktree `web-recherche-3381-192617` nach Merge von chat-hub#136 nicht geschlossen | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | chat-hub#136 MERGED 02:42:38; Worktree existiert, Lease bis 2026-09-29 | worktree-midsession-accumulation |
| 7 | Zwei Edit-Fehlläufe „File has not been read yet“ im chat-hub-Worktree | Werkzeug | niedrig | SURVIVES (kommandobelegt) | kennzahlen 19:26:25, 19:26:32 | — |
| 11 | Subagent mit Merge-+Prod-Deploy-Auftrag vom Klassifizierer abgelehnt (`[Production Deploy]`, 02:50:29); 14 s später verengt neu gestartet („Prepare, do NOT merge, must NOT touch any server“) — Verengung statt Umgehung, Merges erst nach Owner-Wort „69 … admin; 70 go“ | Prozesslücke (positiv) | niedrig | SURVIVES (3b NEU) | kennzahlen 02:50:29 „Production Deploy“; #3398 Kommentar zum Owner-Wort | subagent-prod-access-unscoped-prompt (gefangen) |
| 8 | #1980 wegen Fristablauf geschlossen, ohne dass der Schlusskommentar das kenntlich macht | Kommunikation | niedrig | REFUTED | Schlusskommentar nennt „Frist 2026-09-02 abgelaufen“ + Weiterführung wörtlich | — |
| 9 | Cluster von 4 geblockten Versuchen derselben Klasse um die Rotation, ad-hoc statt /secrets-Skill | Prozesslücke | mittel | REFUTED | nur 2 der 4 Zeitpunkte gehören zur Rotation; `secrets.md` kennt keinen Host-DB-Rotationspfad | — |
| 10 | Dependabot-/Renovate-Bumps liefen unabgestimmt parallel zur Welle | Prozesslücke | niedrig | REFUTED | #3398: risk-hub#767/tax-hub#147 wiederverwendet, illustration-hub#358 aktiv geschlossen | — |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | #4 — Hauptziele geliefert, Outline-Abnahme und Rotation offen |
| architektur_design | 4 | #1 — SSoT-Entscheid (shared-ci) und Composite-Design tragfähig; Vorlage kurz mit Fehlzahl |
| code_konventionstreue | 4 | #7 — Konventionen (Worktree, Edit-Tool, Tests) eingehalten, kleine Reibung |
| risiko_debt | 2 | #2/#3 — offengelegtes Credential, Rotation offen |
| prozess_effizienz | 3 | #5 — Staffelung sauber, aber direkter Merge-Pfad an `pr_merge_sa.py` vorbei (gate-pflichtiger Slug) und fehlende Live-Checks |
| entscheidungsqualitaet | 4 | #1 — Fehlzahl vor Entscheid erkannt und korrigiert |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| grep zählte Kommentarzeilen als Aufrufe (#3398) | Zählbefehl erst gegen eine bekannte Positiv-/Negativzeile prüfen (Anker `^\s+uses:`), dann Zahl in die Vorlage | #1 |
| `bash -x` über Skript mit Env-Auslesen (#3428) | Debug nur mit `set -x` auf Zeilen ohne Secret-Kontext; Env nur schlüsselgenau per `grep ^KEY=` lesen, nie als Variable tracen | #2 |
| Rotation nach Owner-Freigabe zweimal ins Klassifizierer-Gate gelaufen, dann liegen gelassen | Nach der ersten Ablehnung einer Credential-Operation sofort den copy-fertigen Owner-Block ins Issue schreiben (Owner führt aus) | #3 |
| Abnahme nur im Fließtext von #3256 | Abnahme als Checklisten-Zeile im Issue-Body (`- [ ] Owner-Login im privaten Fenster`), authentik-Schritt davon abhängig | #4 |
| `--admin`-Merge auf bereits gemergten PR; Welle per `gh pr merge --admin` statt `pr_merge_sa.py` | Merges nur über ein Werkzeug, das Zustand, Owner-Wort und Journal prüft; die Schranke `direct-gh-pr-merge-bypasses-sa-m` als PreToolUse-Hook bauen (Owner-Wort, #2234) | #5 |
| Subagent-Auftrag mit Prod-Wirkung abgelehnt, verengt neu gestartet | Beibehalten: bei Ablehnung Auftrag verengen („prepare, do NOT merge“) und Prod-Schritt an den Owner geben — nie Umweg über einen zweiten Weg | #11 |
| Worktree nach Merge nicht beendet | `repo-session.sh end <wt>` direkt nach bestätigtem Merge des zugehörigen PR | #6 |
| Edit ohne vorheriges Read | Read vor Edit auch bei vorher per Bash gelesenen Dateien | #7 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (2026-09-23): 54 Slugs ≥2 ⇒ Gate-Pflicht. In dieser Retro wiederkehrend: `check-ohne-positivkontrolle`, `secret-leak-via-safe-pattern`, `deferred-item-no-tracking-issue`, `worktree-midsession-accumulation` — alle vier haben ein registriertes Gate (siehe 5a). Neu: `freigabe-im-chat-hebt-klassifizierer-nicht` (Vorkommen 1 in dieser Retro; die Sitzung lief sechsmal in dieselbe Sperre: Merge ohne Review, Prod-Deploy, Remote-Write, Credential) → Gate-Kandidat.

### 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` (Phase 0.0): **1 Gate RUECKFAELLIG — `claim-before-cheapest-check`** (85 Vorkommen, 2 nach Bau). In dieser Sitzung hat der Stop-Hook dieses Gates zweimal gefeuert (bypass-claim, universal-claim) — beides wurde mit Tool-Lauf beantwortet (gates_caught). Befund #1 ist dagegen eine Behauptung **mit** Check, aber mit ungeprüftem Check: das Gate sieht nur Text ohne Tool-Lauf, nicht einen Tool-Lauf ohne Positivkontrolle.

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 2 | Quelle: der Hook prüft „Behauptung ohne Tool-Lauf“, nicht „Zählung ohne Positivkontrolle“ — die Familie `check-ohne-positivkontrolle` liegt außerhalb seines Musters | **ausweiten** (Kandidat, nicht umgesetzt) — Drill ergänzen: Positivkontrolle „Zahl aus grep ohne Anker“ in die Gate-Registry als `revised` + `revision_note`; Umsetzung über `gate_verankerung_check.py --neu` in eigenem PR |
| secret-leak-via-safe-pattern | 1 in dieser Sitzung | Quelle: der Secret-Leak-Guard ist argument-basiert (fing `cat ~/.secrets/…` um 10:06), sieht aber `bash -x` über Remote-Skripte nicht | **ausweiten** (Kandidat): Hook-Muster um `bash -x`/`set -x` in Kombination mit `docker inspect`/`env` erweitern |
| direct-gh-pr-merge-bypasses-sa-m | 3. Vorkommen, **kein Gate gebaut** (`retro_kpis.py`: „OHNE registriertes Gate“) | Quelle: die Schranke existiert nur als Kandidat (`docs/governance/gates/kandidaten/direct-gh-pr-merge-bypasses-sa-m.json`, `vorkommen: 2`) | Gate-Pflicht: PreToolUse-Hook bauen oder in `declined` begründen — Owner-Entscheid, getrackt in #2234 |
| deferred-item-no-tracking-issue / worktree-midsession-accumulation | je 1 | Quelle: beide Fälle liegen nach einem Ausführungskommentar bzw. nach Merge — kein Gate prüft „Abnahme ausstehend“ oder „Worktree zu gemergtem PR“ | Kandidat ohne Umsetzung in dieser Retro |

### 5b. Autonomie-Kalibrierung

`over_ask`: keine Klasse belegt — jede Rückgabe an den Owner war ein Gate (Merge mit Deploy, Credential, Prod-Write). `over_act`: keine — alle Prod-Schritte (Admin-Merges Gruppen 2–5, Environment-Freigabe ausschreibungs-hub, Outline-Umstellung, Host-Archiv) sind durch nummerierte Owner-Worte in #3398/#3256 gedeckt.

## 6. Verankerung (Vorschläge, nicht geschrieben)

**memory_candidates:**
```markdown
---
name: feedback_chat_freigabe_hebt_klassifizierer_nicht
description: Owner-„go“ im Chat öffnet keine vom Auto-Mode-Klassifizierer gesperrte Aktionsklasse (Merge ohne Review, Remote-Write, Credential) — nach der ersten Ablehnung Owner-Block schreiben statt erneut versuchen
drift: true
drift_episode: 2026-09-23-klassifizierer-freigabe
metadata:
  type: feedback
---
Sechs Ablehnungen in Sitzung 2c4009 trotz expliziter Owner-Freigaben. **Why:** Die Sperre sitzt in den Harness-Einstellungen; Chat-Worte ändern sie nicht, und die Charta verbietet, die Einstellungen selbst zu ändern. **How to apply:** Nach der ersten Ablehnung einer Klasse nicht erneut versuchen, sondern einen copy-fertigen Befehlsblock ins Tracking-Issue schreiben und den Owner wählen lassen (selbst ausführen oder Regel anlegen).
```
```markdown
---
name: feedback_bash_x_ueber_env_leakt_secrets
description: `bash -x` über ein Skript, das Container-Env in eine Variable liest, druckt Secrets auf stdout — Env nur schlüsselgenau lesen, nie tracen
drift: true
drift_episode: 2026-09-23-outline-db-passwort
metadata:
  type: feedback
---
Realfall #3428. **Why:** Der Trace gibt Variablenzuweisungen samt Wert aus. **How to apply:** Debug über `echo`-Marker statt `-x`; Env per Funktion `envkey KEY`, die nur den einen Wert zurückgibt; `docker exec` ohne `-i` in stdin-gespeisten Skripten (frisst sonst den Rest).
```

**adr_candidates:** keine — die Entscheidung shared-ci = SSoT ist im Issue #3398 festgehalten und in ADR-120 als Nachtrag vermerkt.

## 7. Maßnahmen

- **[R1]** 🟢 Outline-Login im privaten Fenster testen, Ergebnis in #3256 · platform · du — https://github.com/achimdehnert/platform/issues/3256
- **[R2]** 🟢 Passwort-Rotation selbst ausführen oder Regel für `ssh hetzner-prod` anlegen · platform · du — https://github.com/achimdehnert/platform/issues/3428
- **[R3]** 🔵 Copy-fertigen Rotationsblock in #3428 schreiben · platform · ich — https://github.com/achimdehnert/platform/issues/3428
- **[R4]** 🔵 Abnahme als Checkliste in #3256 ergänzen · platform · ich — https://github.com/achimdehnert/platform/issues/3256
- **[R5]** 🔵 chat-hub-Worktree beenden · chat-hub · ich — https://github.com/iilgmbh/chat-hub/pull/136
- **[R6]** 🔵 Gate-Revision `claim-before-cheapest-check` (Drill Positivkontrolle) als Issue · platform · ich — https://github.com/achimdehnert/platform/issues/2234
- **[R7]** 🔵 Streichbahn: kein Kandidat (Begründung unten) · platform · — — https://github.com/achimdehnert/platform/issues/3398

## 8. Nicht verifiziert (Restlücken)

- Ob der Owner-Login über Cloudflare im Admin-Konto landet — billigster Check: Login im privaten Fenster (R1).
- Inhalt des Host-Archivs `/opt/backups/stilllegung-2026-09-23-llm-gateway` nicht geprüft — billigster Check: `ls -la` auf dem Host.
- 13 der 15 Bump-PRs nicht einzeln auf Diff-Ebene geprüft (Stichprobe pptx-hub, dev-hub) — billigster Check: `gh pr diff` je PR auf genau eine geänderte Zeile.

**Vierklang:**
- **getan:** 3 Finder, 2 Skeptiker (Bewertungsbefunde), Widerlegungsbahn, Meta-Review, `gate_wirkung.py`, `retro_kpis.py`, `hosts_audit.py` (grün), Transkript-Kennzahlen mit Selbsttest.
- **angenommen:** Die Owner-Worte im Chat sind vollständig in #3398/#3256 gespiegelt (Stichprobe der Kommentare, nicht jedes Wort gegen das Transkript geprüft).
- **nicht verifizierbar:** Ausgang der Outline-Abnahme; ob das offengelegte Passwort außerhalb des Transkripts gelesen wurde.
- **offen geblieben:** Rotation #3428, Merge mcp-hub#284, Gate-Revisionen aus 5a.

## Widerlegung

Phase 3b (Opus, frischer Kontext, nur Entwurf + Artefaktliste):

- **GEKIPPT (1):** #5 stand als „neu“; tatsächlich 3. Vorkommen von `direct-gh-pr-merge-bypasses-sa-m`. Beleg: Kandidat-Datei `vorkommen: 2`, Slug in Retros 50d29a und f1d54f; in dieser Sitzung außerdem direkte `gh pr merge --admin` für die Welle. Übernommen (Recurrence, 5a, Soll #5).
- **NEU (1):** #11 — der Klassifizierer fing einen Subagenten mit Prod-Deploy-Auftrag, der Auftrag wurde verengt statt umgangen. Übernommen, als `gates_caught`.
- **BESTAETIGT:** #1, #2 (Belegzeit auf 10:04 präzisiert), #3, #4, #6, #7; REFUTED #8, #9, #10 bleiben verworfen.
- Score-Hinweis übernommen: `architektur_design` nicht mehr an #5 verankert.
- Abdeckung ohne Treffer: Secrets/E-Mails/IPs in #3256, #3428, #3424; zeitliche Deckung Environment-Freigabe und Gruppen-Merges durch Owner-Worte; Staffelung der Welle; Subagenten haben nicht selbst gemergt.

## Streichbahn

Keiner, weil jede Pflicht-Phase in dieser Retro nachweislich Wirkung hatte: Skeptiker verwarfen 3 von 5 Bewertungsbefunden, 3b kippte ein Recurrence-Etikett und fand einen neuen Befund, Meta fand zwei Report-Mängel (Owner in Beleg #5, fehlendes Kanon-Wort in 5a). Geprüft ohne Kandidat: Infra-Topologie-Sonde (grün, aber gesetzlich Pflicht bei Deploy-Sitzungen, ein Lauf ist kein Liegezeit-Beleg).

## Self-Review

Meta-Agent (Phase 5): `retro_report_check.py` Exit 0; Stichproben #1, #3, #5, #6 unabhängig nachgeprüft; Invariante erfüllt; Pfad kollisionsfrei. Zwei Mängel gefunden und behoben. `refuted_rate`: 3/(11−0) = 0,27 — im Band 0,2–0,8.

Phase 6 (Extern-Handoff): n/a — nur bei Footprint `deep` vorgesehen; diese Retro lief nach begründeter Reduktion als `full`.
