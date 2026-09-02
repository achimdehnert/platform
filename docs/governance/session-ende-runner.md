# session-ende-Runner (`tools/session_ende_checks.sh`)

**Zweck.** `/session-start` hat seit platform#1167 einen deterministischen Runner,
`/session-ende` hatte keinen — der mechanische Bash-Code stand im Fliesstext eines
965-Zeilen-Skills und war damit strukturell überspringbar (Retro c494a2: eine neue
Pflicht-Phase lag in der verteilten Kopie vor und wurde trotzdem nicht ausgeführt →
drei konkurrierende Handover-PRs). Ein Runner ist nicht überspringbar: ein Aufruf
führt alle mechanischen Phasen aus und endet mit einer Tabelle. Zahlt ein auf
[#2690](https://github.com/achimdehnert/platform/issues/2690) K1 und K5 (Mechanik
wandert in den Runner, statt ersatzlos zu entfallen — Lehre #1122/#1165).

## Aufruf

```bash
bash tools/session_ende_checks.sh <TARGET_REPO> [--session-id <id>]
```

Read-only. Exit 0 = kein FAIL, Exit 1 = mindestens ein FAIL. Überschreibbar per Env:
`GITHUB_DIR`, `PLATFORM_DIR`, `LEASE_DIR`, `OLLAMA_HOST`,
`SESSION_ENDE_ZUSAGEN_BUDGET` (Default 120 s je PR), `SESSION_ENDE_ZUSAGEN_MAX_PRS`
(Default 3), `SESSION_ENDE_DRIFT_TIMEOUT` (Default 480 s).

Laufzeit wird von zwei Phasen bestimmt: E.6 braucht **gemessen 411 s** für die ganze
Flotte, E.5 bis zu `BUDGET × MAX_PRS`. Wer schnell durch will, setzt beide Deckel
herunter — dann steht dort ehrlich `SKIP`, nicht `PASS`.

## Phasen und ihre Skill-Herkunft

| Runner | Skill-Phase | Was gemessen wird | Werkzeug |
|---|---|---|---|
| E.0 banner | −0.1 | Version + Commit der platform | — |
| E.1 deploy-status | 0a-deploy | letzter Deploy-Run je berührtem Repo: `success` / `failure` / `waiting` / kein Deploy | `gh run list` |
| E.2 handover-prs | 0a-handover-pr | offene PRs, die `AGENT_HANDOVER.md` anfassen; >1 = konkurrierende Stände | `gh pr list` |
| E.3 handover-frische | 0a-freshness | Gate `handover-stale-vor-merge` | `scripts/checks/agent_handover_freshness_check.py` |
| E.4 cross-repo-befunde | 0f | offene Fremd-Repo-Befunde ohne Artefakt/Verzicht (Zahl, nicht Deutung) | `tools/befund_journal.py --offen-cross-repo` |
| E.5 zusagen | 0g | eigene PRs von heute, 4 Ausgabeklassen (✅ / ⚠️ / NICHT PRUEFBAR / UNGEPRUEFT) | `tools/verankerung_pruefer.py` |
| E.6 template-drift | 1c | Error-Drifts gegen die Repo-Templates | `scripts/drift_check.py --severity=error` |
| E.7 dirty-repos | 3.3 | uncommittete Änderungen; eigene (Lease heute) = WARN, fremde = Hinweis | `git status --porcelain` |
| E.8 worktree-reap | 3.1c | **bewusst SKIP** — `repo-session.sh reap --alle` läuft in `session_start_checks.sh` 0.4.5 über alle Leases (Gate-Revision 2026-08-20); ein zweiter Lauf am Sitzungsende ist dieselbe Mechanik doppelt | — |
| E.9 dist-drift | (neu, analog Start 0.7.13) | weichen die verteilten Skills von `.windsurf/workflows/` ab | `tools/cc-skill-dist/doctor.py` |

**Repos dieser Sitzung** (Basis für E.1 und die Eigen/Fremd-Trennung in E.7):
Leases von `repo-session.sh` mit heutigem Datum; Fallback sind Repos unter
`$GITHUB_DIR` mit Commits von heute vom aktuellen git-User. Die Quelle steht in
der E.1-Note (`quelle=leases` bzw. `quelle=commits-heute`).

## Was bewusst Judgment bleibt

`0a` (blockierte Arbeit), `0b` (Handover-Text), `0c` (Prios), `0d` (Abnahme +
SA-4-Zähler), `0e` (Clear-Härte), `2` (Memory-Text), `3.5` (Clear-Freigabe). Die
letzte Runner-Zeile nennt sie — `JUDGMENT: 0a 0b 0c 0d 0e 2 3.5 — im Skill
abarbeiten` —, damit ihr Ausbleiben auffällt. Auch die *Deutung* bleibt im Skill:
E.1 sagt, dass ein Deploy rot ist, nicht ob rerun oder Handover-Eintrag richtig
ist; E.4 zählt, 0f entscheidet zwischen Verankern und begründetem Verzicht.

## SKIP ist kein Grün

Fehlt ein Werkzeug oder bricht es ab, steht `SKIP` (◌) in der Zeile und die Zahl
der SKIPs unter der Tabelle — nie `PASS`. „NICHT messbar" als Entwarnung zu
verbuchen war die teuerste Fehlklasse des Start-Runners (KONZ-platform-050).
Tests: `tools/tests/test_session_ende_checks.py` (14 Fälle, u.a. Positivkontrolle
dirty-Repo + Gegenprobe, `failure`/`waiting`, fehlendes Werkzeug → SKIP).
