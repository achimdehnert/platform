---
concept_id: KONZ-platform-010
title: ~/shared als echtes Wegwerf-Element — Benötigtes an durablen SSoT-Orten sichern
pipeline_status: idea
tier: T2
owner: achim-dehnert
spec_refs: []
adr_threshold: lokale ADR-Kandidat (Security-Perimeter + Cross-Repo-Konvention; kein neuer Architektur-Entscheid, da SSoT ~/.secrets bereits existiert)
review_by: 2026-08-15
kill_criteria: "Nach Migration ist ~/shared NICHT komplett löschbar ohne Datenverlust oder Tool-Bruch — messbar: (a) `comm -13 <(ls ~/.secrets) <(ls ~/shared/inbox/secrets)` non-empty ODER (b) `retro_kpis.py` liest 0 Reports nach --dir-Repoint. Trifft eines zu → Konzept nicht eingelöst."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "~/shared (git rev-parse)", commit_or_pr: "n/a", opened_in_session: true}
  - {claim_id: C2, source_path: "~/.secrets vs ~/shared/inbox/secrets (comm)", commit_or_pr: "n/a", opened_in_session: true}
  - {claim_id: C3, source_path: AGENT_HANDOVER.md:164, commit_or_pr: "n/a", opened_in_session: true}
  - {claim_id: C4, source_path: tools/retro_kpis.py:94, commit_or_pr: "n/a", opened_in_session: true}
  - {claim_id: C5, source_path: ".windsurf/workflows/{session-retro,repo-optimize,platform-audit,adr-handoff-extern}.md (grep ~/shared)", commit_or_pr: "n/a", opened_in_session: true}
created: 2026-07-02
---

# KONZ-platform-010 — ~/shared als echtes Wegwerf-Element

## Kernthese

`~/shared` wird per Kontrakt ein **rein flüchtiges Scratch-/Handoff-Verzeichnis** (jederzeit
löschbar); die **einzigen zwei** Dinge, die es heute nicht wegwerfbar machen — **16 unikate Secrets**
(nur dort, nicht in der SSoT `~/.secrets/`) und die **retro-KPI-Basis** (`retro_kpis.py` liest
`~/shared/session-retro-*.md`) — wandern an ihre durablen SSoT-Orte (`~/.secrets/` bzw. git), und ein
enger Guard verhindert die Rückkehr des Secret-Drop-Zone-Antipatterns.

## Assumption-/Decision-Ledger

| id | Aussage | Typ | Evidenz/Falsifikation | Status |
|---|---|---|---|---|
| A1 | `~/shared` ist kein git-Repo, ungebackupt → jeder Inhalt nur dort | Annahme | C1: `git -C ~/shared rev-parse` → fail | verifiziert |
| A2 | `~/shared/inbox/secrets/` hält **16 Secrets, die es NUR dort gibt** (nicht in `~/.secrets/`): github_Enterprise_PAT, github_HETZNER_PULL, github_write_packages, IBKR_Credentials, IBKR_PAPERTRADING_Credentials, apocenna_db, apocenna.env, betterstack_api_key, cf_svc_client_id/secret, dvelop_zugangsdaten.txt, Fal.pages, finnhub_api_key, iil-voice-agent.env, IMAP.env.txt, mittwald_mail.env | Annahme | C2: `comm -13` = 16 unique (34 vs 33, ~10 Duplikate) | verifiziert |
| A3 | `~/.secrets/` ist die dokumentierte einzige Secret-Heimat seit 2026-05-30 — inbox/secrets ist Drift dagegen | Annahme | C3: AGENT_HANDOVER.md:164 | verifiziert |
| A4 | `retro_kpis.py` liest `~/shared/session-retro-*.md`, aber `--dir` ist parametrierbar (default `~/shared`) | Annahme | C4: tools/retro_kpis.py:94 | verifiziert |
| A5 | 4 Skills schreiben nach `~/shared` (session-retro, repo-optimize, platform-audit, adr-handoff-extern); ihr *durables* Ergebnis liegt aber schon woanders (Memory/PRs) — nur die retro-KPI-Basis ist echte ~/shared-Abhängigkeit | Annahme | C5: grep über .windsurf/workflows | verifiziert |
| D1 | **Secrets → `~/.secrets/`** migrieren (16 unikate verschieben, ~10 Duplikate reconcilen), `inbox/secrets/` leeren + Guard | Entscheidung | D — Alt: dedizierter Secret-Manager (Vault/SOPS); zu groß für jetzt, ~/.secrets ist bestehende SSoT | vorgeschlagen |
| D2 | **retro-KPI-Basis → git** (`platform/docs/retros/`), `retro_kpis.py --dir` default darauf repointen, `session-retro`-Skill Report-Pfad → `docs/retros/` | Entscheidung | D — Alt: ~/shared behalten + KPI-Reset bei Cleanup akzeptieren; verwirft Längsschnitt-Historie | vorgeschlagen |
| D3 | **`~/shared/README.md`-Kontrakt**: „EPHEMERAL — jederzeit löschbar; nichts Benötigtes hier; Secrets→~/.secrets, Reports→git/Outline/Memory" | Entscheidung | D | vorgeschlagen |
| D4 | **`shared-reaper.sh`** (dry-run-first, schützt `inbox/`, warnt bei non-Report-Dateien) — optional, Phase 3 | Entscheidung | D — Alt: manuelle Löschung reicht, wenn Kontrakt steht | vorgeschlagen |
| R1 | Guard „inbox/secrets leer" blockiert legitime temporäre Token-Drops (User legt neuen Token dort ab bevor ~/.secrets) | Risiko | Diabolus | offen → Mitigation in MVC |
| R2 | git-getrackte Retros = Retro-Kritik der eigenen PRs im eigenen Repo (könnte unerwünscht sein) | Risiko | Diabolus | offen → Alternative Outline |

## MVC (Minimal Viable Concept — konkreter Plan)

**Phase 1 — Secrets (kritisch, Owner-Aktion, NIE Agent — Security-Perimeter):**
1. Die 16 unikaten Secrets aus `~/shared/inbox/secrets/` nach `~/.secrets/` **verschieben** (mv, nicht cp).
2. Die ~10 Duplikate: verifizieren dass die `~/.secrets/`-Version aktuell ist (Datei-Hash/Datum), dann die inbox-Kopie löschen. Bei Divergenz: Owner entscheidet welche gilt.
3. `~/shared/inbox/secrets/` löschen (Verzeichnis ganz weg).
4. **Guard:** `session-start` Phase 0 um einen Check ergänzen: `[ -d ~/shared/inbox/secrets ] && [ "$(ls -A ~/shared/inbox/secrets 2>/dev/null)" ] && echo "⛔ Secrets in ~/shared/inbox/secrets — gehören nach ~/.secrets (KONZ-010)"`. **R1-Mitigation:** Warn, kein Hard-Fail — der Guard erinnert, blockiert keinen legitimen Zwischen-Drop.

**Phase 2 — retro-KPI-Basis durabel (git):**
5. `platform/docs/retros/` anlegen, die 5 `~/shared/session-retro-*.md` dorthin verschieben (git-versioniert + gebackupt).
6. `tools/retro_kpis.py`: `--dir` default `~/shared` → `<repo>/docs/retros` (ein-Zeilen-Change, Zeile 94).
7. `session-retro`-Skill (Step 4 Report-Pfad): schreibt künftig nach `docs/retros/` im Session-Worktree (statt `~/shared`); Kollisions-Suffix bleibt. **R2-Mitigation:** falls Retro-im-Repo unerwünscht → Alt: Reports nach Outline via `/knowledge-capture`, `retro_kpis.py --dir` auf eine gebackupte, aber nicht-git Location; dann ist git-Tracking vermieden, aber Durabilität via Outline-Backup.

**Phase 3 — Kontrakt + optionaler Reaper:**
8. `~/shared/README.md` schreiben (Kontrakt-Text, s. D3).
9. Optional `tools/shared-reaper.sh` (dry-run default; löscht Report-/Asset-Dateien älter als N Tage; **rührt `inbox/` nie an**; warnt bei unbekannten Datei-Typen).

**Danach ist ~/shared echt wegwerfbar:** `rm -rf ~/shared/*` verliert kein Secret (weg) und bricht kein Tool (retro_kpis liest aus git). Working-Dirs (bahn-hub/, CAD/, comic-spike/, stash-backup-*) bleiben Fall-für-Fall Scratch — der Kontrakt sagt explizit „hier nichts Benötigtes", also ist ihr Verlust per Definition akzeptiert.

## Kill-Gate + Threshold

**Messbare Abbruchschwelle (aus Frontmatter):** Nach Migration muss gelten —
`comm -13 <(ls ~/.secrets) <(ls ~/shared/inbox/secrets 2>/dev/null)` = **leer** UND
`retro_kpis.py` findet ≥1 Report am neuen `--dir`. Trifft nach Phase 1+2 eines der beiden **nicht** zu,
ist das Konzept nicht eingelöst → zurück zu Migration, nicht „done" behaupten.
**Exception-Budget:** bis `review_by: 2026-08-15`. Danach ohne Erfüllung: Konzept `sunset` oder re-charter.

## Befunde-Tabelle (T2, inkl. Advocatus Diabolus)

| # | Befund | Schwere | Quelle | Antwort im MVC |
|---|---|---|---|---|
| B1 | 16 irreplaceable Secrets nur in ~/shared → „shared löschbar" ist heute FALSCH; direkter SSoT-Verstoß (AGENT_HANDOVER:164) | hoch | C2/C3 | Phase 1 (mv → ~/.secrets) |
| B2 | Secret-Store-Doppelung (~10 Dubletten) = Governance-Smell: welche gilt bei Divergenz? | mittel | C2 | Phase 1.2 (reconcile, Owner bei Divergenz) |
| B3 | retro_kpis-Kopplung macht ~/shared für eine benötigte Funktion nicht-wegwerfbar | mittel | C4 | Phase 2 (git + --dir-Repoint) |
| B4-Diabolus | „~/shared/README-Kontrakt" ist reine Prosa ohne Enforcement — Secrets landen wieder dort | mittel | D3 vs. Realität | Phase 1.4 Guard (warn) macht es sichtbar; Hard-Enforcement bewusst nicht (R1) |
| B5-Diabolus | Verschiebe-Migration ist Einmal-Akt; ohne Guard driftet inbox/secrets erneut (wie schon 1× nach der 2026-05-30-Konsolidierung) | hoch | A3 (Drift trotz „konsolidiert") | Guard (Phase 1.4) ist genau die Wiederholungs-Bremse |
| B6-Diabolus | git-getrackte Retros könnten Retro-Kritik unerwünscht sichtbar machen | niedrig | D2 | R2-Alternative (Outline statt git) |

## Alternativen (verworfen, mit Grund)

- **Alt-1: ~/shared komplett aufgeben** (alles nur git/Secret-Manager, kein Scratch-Dir). Verworfen: Skills brauchen einen billigen flüchtigen Write-Ort; ein Ephemeral-Scratch ist legitim und gewollt — das Ziel ist „wegwerfbar", nicht „abgeschafft".
- **Alt-2: ~/shared git-tracken** (versionieren). Verworfen: widerspricht dem Ziel direkt (dann ist es kein Wegwerf-Element), und Secrets in git = No-Go.

## Empfehlung

**D1 (Secrets → ~/.secrets + Guard) ist der einzige nicht verhandelbare, sofortige Schritt** — er
behebt den Security-/Datenverlust-Kern (B1/B5) und ist Owner-Aktion. **D2 (KPI-Basis → git)** ist der
zweite substanzielle Schritt (löst B3), agent-umsetzbar als PR. D3/D4 (Kontrakt + Reaper) sind die
Drift-Prävention und billig. Reihenfolge: **1 → 2 → 3**; nach 1+2 ist ~/shared faktisch wegwerfbar,
3 hält es so.
