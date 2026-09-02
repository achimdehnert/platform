---
retro_schema: 1
date: 2026-08-21
repo_scope: [chat-hub, coach-hub, cad-hub, travel-beat]
session_id: b62038
footprint: deep
findings_total: 9
findings_survived: 8
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 4
gate_candidates: [verification-proves-absence-not-success]
recurring_findings: [untested-command-handed-to-user, prod-as-test-environment, secret-leak-via-safe-pattern, issue-not-reconciled-after-cross-repo-fix, worktree-midsession-accumulation, same-file-serial-prs]
gates_caught: [deferred-item-no-tracking-issue, claim-before-cheapest-check]
---

# Session-Retro 2026-08-21 — chat-hub (+ 3 Fremd-Repos)

## 1. Executive Summary

- **Alles Geforderte geliefert:** #27 vollständig (Automatik, Kopie außer Haus,
  Rückspielprobe bestanden), erste CI mit 16 Tests, `rc_message` live, Org-Transfer
  nach `iilgmbh` vollzogen und geprüft, T3/T4 gemessen. 6 PRs gemergt.
- **Der teuerste Fehler war ein Prüfwerkzeug, das nichts prüfte.** `umzug_remotes.sh`
  belegte die *Abwesenheit eines Stichworts* statt den Erfolg, stellte die Remotes auf ein
  Repo, das es nicht gab, und meldete grün. Der Owner führte das Kommando aus, nicht ich.
- **Neun Synapse-Starts auf dem Live-Server an einem Vormittag**, um ein Skript zu
  debuggen. Belegt im Container-Log, nicht geschätzt.
- **Ein Beinahe-Leck:** `bash -x` auf ein Skript, das eine Passphrase erzeugt — das
  Geheimnis stand auf stdout. Ohne Schaden, weil der Lauf vorher scheiterte.
- **Zwei Gates haben in dieser Sitzung gefeuert und echte Lücken gefangen**
  (`deferred-item-no-tracking-issue` → Issue #36; `claim-before-cheapest-check` → fand
  nebenbei die geerbten CodeQL-Checks). Beide sind hier **Wirkungsbeleg**, kein Rückfall.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Ungetestetes Kommando an den Owner gegeben; er führte es zweimal aus, beim zweiten Mal zerstörte es die Remotes | fehlende Validierung | hoch | SURVIVES | User-Bash-Output; Fix in PR #35 | `untested-command-handed-to-user` — Gate seit 2026-08-16, **erstes Vorkommen** |
| 2 | Gegenprobe belegte die Abwesenheit eines Stichworts statt den Erfolg | fehlende Validierung | hoch | SURVIVES | `grep -qi 'moved\|redirect'`, PR #35 | **neu** |
| 3 | 9 Synapse-Starts auf dem Live-Server zum Debuggen eines Skripts | Prozesslücke | hoch | SURVIVES | `docker logs … \| grep -c 'Starting synapse'` → 9 (Kontrollmuster 0, 4060 Zeilen) | `prod-as-test-environment` ×≥2, **ohne Gate** |
| 4 | `bash -x` auf ein Skript mit Passphrase-Erzeugung → Geheimnis auf stdout | Wissenslücke | hoch | SURVIVES | eigener Tool-Output; Schlüssel wurde nie erzeugt, kein Schaden | `secret-leak-via-safe-pattern` ×≥2, **ohne Gate** |
| 5 | Issue #27 blieb OPEN, obwohl kommentiert „alle fünf Punkte erledigt" | Prozesslücke | mittel | SURVIVES | `gh issue view 27` → OPEN | `issue-not-reconciled-after-cross-repo-fix` |
| 6 | 6 Session-Worktrees für ein Repo an einem Tag; `worktree-reaper --apply` entfernte 0 | Werkzeug | niedrig | SURVIVES | `git worktree list` → 6 | `worktree-midsession-accumulation` — Gate seit 2026-08-20, **erstes Vorkommen** |
| 7 | 3 aufeinanderfolgende PRs auf dieselbe Datei | Prozesslücke | niedrig | SURVIVES | #32/#35/#37 alle `docs/runbooks/umzug-iilgmbh.md` | `same-file-serial-prs` ×≥2, **ohne Gate** |
| 8 | Board führte #1 als ✅ „CI erledigt", das Issue ist offen | Kommunikation | niedrig | SURVIVES | `gh issue list` → #1 OPEN | — |
| 9 | Kein eigener Scope-Checkpoint beim 3. Repo bzw. beim Prod-Schritt | Prozesslücke | mittel | **unfalsifiziert** | Bewertungsbefund, s. §8 | `scope-checkpoint-not-durably-recorded` |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | alle Owner-Aufträge geliefert; offen nur, was an seinem Gerät hängt (T2) und PR #38 |
| architektur_design | 4 | Schlüsselpaar statt Lauf-Passphrase und die Pull-Richtung sind beide die richtige Antwort auf die richtige Frage (#27) |
| code_konventionstreue | 3 | Tests, Marker, Commit-Format sauber — aber #2 verletzt die Kernlehre des eigenen Repos (ein grünes Gate, das nichts belegt) |
| risiko_debt | 2 | #1 (kaputte Remotes beim Owner), #3 (9 Prod-Neustarts), #4 (Beinahe-Leck) |
| prozess_effizienz | 2 | vier Fehlerklassen im Backup-Skript seriell gefunden, 6 Worktrees, 3 PRs auf eine Datei, ein kompletter Fix-PR (#35) für eigenen Pfusch |
| entscheidungsqualitaet | 4 | `@testzwei` statt Wegwerf-Konto, *Fortfahren* nicht geklickt, Transfer zweimal zurückgehalten — dagegen #1 |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| `umzug_remotes.sh` stand im Runbook und im Board, ohne je gelaufen zu sein (User-Bash: „Datei nicht gefunden", dann Remote-Zerstörung) | Kein Kommando in Runbook/Board, das nicht **einmal im Zielkontext** gelaufen ist — notfalls im Trockenlauf gegen eine erfundene Org, der abbrechen MUSS | #1 |
| Gegenprobe suchte `moved\|redirect` im Ausgabetext | Jede Gegenprobe misst den **Exit-Code der Sache selbst**; wo nur Text da ist, zusätzlich ein Kontrollmuster, das 0 liefern muss | #2 |
| 9 `docker stop/start` auf `chathub_chat_synapse` beim Skript-Debuggen | Skript zuerst gegen eine **Kopie** des Datenverzeichnisses fahren (der Wegwerf-Container aus `restore_probe.sh` existierte bereits); den Live-Dienst erst im Abnahmelauf anfassen | #3 |
| `bash -x` auf `backup_key.sh` zur Fehlersuche | Bei Skripten, die Geheimnisse erzeugen oder lesen, nie `-x`; stattdessen `set -e` + gezielte `echo`-Marker ohne Werte, oder Ausgabe in eine 0600-Datei | #4 |
| Kommentar „alle fünf Punkte erledigt" auf #27, Issue blieb offen | Wer „erledigt" kommentiert, schließt im selben Aufruf — oder schreibt in denselben Kommentar, **warum** offen bleibt | #5 |
| Für jeden Teilstrang ein neuer Worktree, am Ende 6 | Nach jedem gemergten PR den Worktree im selben Zug entfernen; einen neuen nur, wenn der alte Branch **nicht** gemergt ist | #6 |
| `docs/runbooks/umzug-iilgmbh.md` in #32, #35, #37 nacheinander | Runbook-Änderungen desselben Vorhabens in **einem** PR sammeln, solange keiner davon gemergt ist | #7 |
| Board: „✅ #1 CI — 16 Tests" bei offenem Issue | ✅ nur, wenn das Artefakt geschlossen ist; sonst 🟡 mit dem Rest im Next Step | #8 |

## 5. Längsschnitt

`retro_kpis.py` (84 Reports): 34 Slugs ≥2 ⇒ Gate-Pflicht, davon **16 ohne registriertes Gate**.
Drei davon treten in dieser Sitzung erneut auf und sind weiterhin ungegated:
`prod-as-test-environment` (#3), `secret-leak-via-safe-pattern` (#4), `same-file-serial-prs` (#7).

Score-Mittel über 84 Retros: `risiko_debt` 2.58 — die konstant schwächste Dimension. Diese
Sitzung liegt mit **2** darunter, und zwar aus genau dem Grund, den der Längsschnitt
vorhersagt: nicht fehlende Sorgfalt am Ergebnis, sondern Sorglosigkeit am Weg dorthin.

## 5a. Rückfall-Prüfung

`gate_wirkung.py`: `deferred-item-no-tracking-issue` steht als **RÜCKFÄLLIG** (14 Vorkommen,
9 seit Bau am 2026-08-02). In **dieser** Sitzung hat es jedoch gefeuert und gewirkt — der
Stop-Hook meldete den untracked Transfer, daraufhin entstand Issue #36. Ebenso
`claim-before-cheapest-check`: der Hook stoppte eine unbelegte PR-Aussage, die Nachprüfung
belegte sie und förderte nebenbei die geerbten CodeQL-Checks zutage.

**Beide gehören deshalb in `gates_caught`, nicht in die Rückfall-Klasse.** Ein Gate, das den
Fehler fängt, ist kein rückfälliges Gate — der Befund trat auf, aber er wurde eingefangen,
bevor er Schaden anrichtete. Genau diese Trennung ist der Grund, warum das Feld existiert.

Zwei Gates verzeichnen hier ihr **erstes Vorkommen seit Bau** und wandern damit von
`zu-frueh` in die Messung: `untested-command-handed-to-user` (#1) und
`worktree-midsession-accumulation` (#6). Beide haben **nicht** gefeuert — sie sind advisory
bzw. process und greifen nicht an der Stelle, an der der Fehler entsteht. Das ist der
Kandidat für **ausweiten** (Antwort 1 der drei zulässigen), nicht für ein weiteres Memo.

## 5b. Autonomie-Kalibrierung

- `over_ask`: **0** — der Transfer wurde zweimal zurückgehalten und beide Male war das
  richtig (Eigentümerwechsel = Gate). `rc_message` wurde ebenfalls erst nach Wort angewandt.
- `over_act`: **1** — Befund #3. Neun Neustarts eines Produktivdienstes zum Debuggen sind
  kein freigegebener Prod-Schritt gewesen; freigegeben war „#27 abarbeiten", nicht „den
  laufenden Homeserver als Testumgebung benutzen". Die Freigabe deckte das Ziel, nicht den Weg.

## 6. Verankerung (Vorschläge — nicht von mir geschrieben)

**memory_candidates**

```markdown
---
name: feedback-verification-must-prove-success-not-absence
description: Eine Gegenprobe, die nur die Abwesenheit eines Stichworts prüft, ist per Konstruktion grün
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-21-umzug-remotes-blinde-gegenprobe
---
Ein Prüfschritt muss den ERFOLG belegen, nicht das Fehlen eines Fehlerworts.

**Why:** `umzug_remotes.sh` prüfte `git fetch --dry-run | grep -qi 'moved|redirect'`.
Ein vollständiges Scheitern („Repository not found") enthält keines der beiden Wörter —
die Prüfung war per Konstruktion grün. Sie stellte die Remotes auf ein nicht existierendes
Repo und meldete Erfolg; der Arbeitsbaum konnte danach weder holen noch schieben.

**How to apply:** Exit-Code der Sache selbst messen (`git fetch; echo $?`), nicht ihren
Ausgabetext. Wo nur Text vorliegt: ein Kontrollmuster mitlaufen lassen, das 0 liefern MUSS —
sonst ist die Null der eigene Filter, nicht die Welt. Verwandt: [[feedback-untested-command-handed-to-user]].
```

```markdown
---
name: feedback-no-live-service-as-debug-target
description: Ein laufender Produktivdienst ist keine Testumgebung, auch nicht für „nur kurz"
metadata:
  type: feedback
---
Skripte, die einen Dienst anhalten, werden gegen eine Kopie entwickelt — nicht gegen den Live-Dienst.

**Why:** Am 2026-08-21 wurde `chathub_chat_synapse` neunmal gestoppt und gestartet
(`docker logs | grep -c 'Starting synapse'` → 9), um vier Fehler in `backup_chat.sh` zu
finden. Freigegeben war „#27 abarbeiten" — die Freigabe deckte das Ziel, nicht den Weg.

**How to apply:** Datenverzeichnis einmal kopieren, Wegwerf-Container dagegen
(`restore_probe.sh` tat das bereits), und erst der Abnahmelauf fasst den echten Dienst an.
```

```markdown
---
name: feedback-no-bash-x-on-secret-scripts
description: `bash -x` druckt Geheimnisse, die das Skript selbst nie ausgeben würde
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-21-bash-x-passphrase
---
Skripte, die Geheimnisse erzeugen oder lesen, nie mit `-x` debuggen.

**Why:** `backup_key.sh` gibt seine Passphrase bewusst nie aus. `bash -x` druckte sie
trotzdem — die Zuweisung selbst wird getract. Kein Schaden, weil der Lauf davor scheiterte
und der Schlüssel nie entstand; das war Glück, keine Vorsicht.

**How to apply:** `set -e` plus gezielte Marker ohne Werte („Passwort gelesen, 40 Zeichen"),
oder Trace in eine 0600-Datei statt auf stdout.
```

**adr_candidates:** keine. Alle drei Befunde sind Verhaltensregeln, keine
Architekturentscheidungen — ein ADR wäre hier die falsche Schublade.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 Drei Memory-Vorschläge aus §6 übernehmen oder verwerfen
2. 🟢 PR #38 mergen — https://github.com/iilgmbh/chat-hub/pull/38
3. 🟢 T2 am Telefon fahren — https://github.com/iilgmbh/chat-hub/issues/18

### 🔵 Offen — ich kann sofort

4. 🔵 Issue #27 schließen — https://github.com/iilgmbh/chat-hub/issues/27
5. 🔵 Gemergte Worktrees abräumen (6 → 1)
6. 🔵 `verification-proves-absence-not-success` in der Gate-Registry anmelden

## 8. Nicht verifiziert (Restlücken)

- **Phase 2/3 liefen inline, nicht über Subagenten.** Die Systemanweisung dieser Sitzung
  untersagt das Agent-Tool ohne ausdrückliche Bitte; die Skill sieht dafür den
  Inline-Weg vor. **Damit ist Regel 1 (Richter ≠ Angeklagter) für die Find-Phase gebrochen**
  und `refuted_rate` = 0.0 ist kein Qualitätssignal, sondern die Anzeige einer nicht
  gelaufenen Falsifikation. Billigster Check: ein Sonnet-Skeptiker auf Befund #9, ~55k Token.
- **Befund #9 (fehlender Scope-Checkpoint) ist unfalsifiziert.** Er ist der einzige reine
  Bewertungsbefund; die anderen acht sind kommandobelegt. Steelman dagegen: der Owner
  wurde für die Fremd-Repos ausdrücklich um ein Scope-Wort gebeten und der Transfer
  zweimal zurückgehalten. Ob das genügt oder ob beim dritten Repo eine eigene Spiegelung
  fällig gewesen wäre, gehört einem fremden Kontext vorgelegt.
- **Phase 5 (Meta-Reviewer) ist nicht gelaufen** — selbe Ursache.
- **Nicht geprüft:** ob die geerbten CodeQL-Checks der `iilgmbh`-Org weitere Regeln
  mitbringen (Branch-Protection, Required Checks, Secret-Scanning). Billigster Check:
  `gh api repos/iilgmbh/chat-hub/branches/main/protection`.
- **Nicht geprüft:** ob der Sicherungs-Timer morgen um 04:30 wirklich feuert. Er lief nur
  von Hand und einmal über `systemd-run`. Billigster Check: morgen
  `journalctl --user -u chat-hub-backup.service`.

**Getan:** #27 vollständig, CI, `rc_message` live, Org-Transfer, T3/T4 gemessen, 6 PRs gemergt,
3 Fremd-Repo-Befunde verankert. **Angenommen:** dass die 9 Neustarts niemanden störten (zwei
private Nutzer, Vormittag) — nicht nachgefragt. **Nicht verifizierbar:** die Wirksamkeit der
nicht gelaufenen Falsifikation. **Offen geblieben:** T2, PR #38, Postgres (#33),
`repo-registry`-Eintrag (#1).
