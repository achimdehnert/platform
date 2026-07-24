---
concept_id: KONZ-platform-007
title: adr-handoff-extern — halb-automatisierter Round-Trip an externes Frontier-LLM
pipeline_status: sunset          # 2026-07-24: review_by (2026-07-20) ohne grünes Signal + 0 --auto-Läufe → Kill-Gate „Kein grünes Signal → sunset" zieht. Reversibel: manueller adr-handoff-extern-Pfad bleibt Default (ALT-2). Re-open nur mit REC-1 (Souveränitäts-Hard-Gate) zuerst.
tier: T2
owner: Achim Dehnert
spec_refs: []                         # Skill, keine ADR-211-Spec; Begründung: Tooling, kein Klickdummy
adr_threshold: kein ADR               # AUFGELÖST 2026-06-20: Perimeter-Crossing war bereits 2026-05-29 entschieden; Automatik ändert nur den Enforcement-Aktuator (Mensch→Gate-Test), reversibel per Flag. Getragen vom Hard-Gate-Test (Step 4b.1).
review_by: 2026-07-20
kill_criteria: "Nach 3 realen --auto-Läufen liefert der automatisierte Pfad keine Befund-Qualität, die der manuelle Copy-Paste-Pfad nicht auch lieferte (gemessen an Anzahl [valid]-getaggter AD-/REC-IDs pro Lauf) → --auto-Flag wieder entfernen, manuell bleibt Default."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: ~/.claude/commands/adr-handoff-extern.md, commit_or_pr: "managed-copy content_hash sha256:66cda3a04a18 (source=platform/.windsurf/workflows/adr-handoff-extern.md)", opened_in_session: true}
  - {claim_id: C2, source_path: ~/github/mcp-hub/orchestrator_mcp/model_registry.py:91-104, commit_or_pr: "working tree", opened_in_session: true}
  - {claim_id: C3, source_path: ~/github/mcp-hub/orchestrator_mcp/capability.py:95, commit_or_pr: "grep-Treffer, Datei NICHT geöffnet", opened_in_session: false}
  - {claim_id: C4, source_path: ~/.secrets/openai_api_key, commit_or_pr: "ls-verifiziert vorhanden", opened_in_session: true}
created: 2026-06-20
---

# KONZ-platform-007 — adr-handoff-extern halb-automatisieren

## Kernthese

Den manuellen Copy-Paste-Round-Trip von `adr-handoff-extern` durch einen **optionalen `--auto`-Pfad**
ersetzen, der das Briefing baut, das Souveränitäts-Gate **programmatisch hart** prüft, **einen**
externen Call (OpenAI reasoning-tier) absetzt und die strukturierte Antwort als `.md` ablegt —
**das Step-5-Rückfluss-Tagging bleibt bewusst beim Menschen**. Automatisiert wird der Transport,
nicht das Urteil.

## Decision-/Assumption-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| L1 | Manueller Round-Trip (`.md` → externer Chat → zurückkopieren) ist reine Friktion und automatisierbar | Annahme | Skill Step 4 schreibt `.md` nach `~/shared/`, Mensch trägt nach extern (C1) | belegt |
| L2 | Step-5-Rückfluss-Gate (AD-/REC-IDs als `[valid]/[missversteht]/[out-of-scope]` taggen) ist der **Sicherheitsmechanismus** und darf NICHT automatisiert werden | Entscheidung | Skill: „GPT-Befund ist externe Beobachtung, kein Fakt" (C1, Step 5 + Anti-Patterns) | gesetzt |
| L3 | OpenAI ist im Orchestrator-Gateway bereits verdrahteter Provider → kein neuer Boundary-Provider | Annahme | `model_registry.py` `provider="openai"`, budget=`gpt-4o-mini`, reasoning-tier vorhanden (C2) | belegt |
| L4 | Egress-Credential existiert | Annahme | `~/.secrets/openai_api_key` vorhanden (C4); **`~/shared/secrets-inbox/` existiert NICHT** — Policy-Pfad ist stale | belegt + Policy-Korrektur nötig |
| L5 | Exakte Ziel-Modell-ID „GPT 5.5 max" ist **unbestätigt**; verdrahtet ist die `gpt-4o`-Familie | Risiko | C2 zeigt gpt-4o/gpt-4o-mini, kein gpt-5.5; Cutoff 01/2026 | offen — Check: `GET /v1/models` |
| L6 | Souveränitäts-Gate (heute menschlich, Step 0) muss bei Automatik **vor** dem Call als Hard-Abort laufen | Entscheidung | Skill Anti-Pattern: ttz-lif/meiki-lra/Realdaten nie extern (C1) | gesetzt |
| L7 | Änderung gehört in `platform/.windsurf/workflows/adr-handoff-extern.md` (SSoT), nicht managed Copy | Annahme | Managed-Copy-Footer `do_not_edit`, verteilt via cc-skill-dist (C1) | belegt |
| L8 | **Lokales curl ist tot** — CC-Session kann den Key nicht lesen | Risiko→belegt | echter Lauf 2026-06-20: `~/.secrets/openai_api_key` = `root:root` 600, `devuser` Permission denied, kein sudo, Env UNSET | belegt → 4b.3 korrigiert |
| L9 | **Egress über aifw/Orchestrator; `provider: openai` zwingend** | Entscheidung | `workflow_executor.py:42-72` (frontmatter wins, Default `groq`); `review_adr` lief auf `anthropic/claude-sonnet-4-6` = keine Diversität | gesetzt |
| L10 | Kein neuer Bau nötig — aifw routet bereits zu jedem Provider | Annahme (User 2026-06-20) | aifw `LLMProvider`/`LLMModel` + workflow_executor provider-override | belegt |

## MVC (Minimal Viable Concept — konkret)

1. **Flag:** `--auto` (Default ohne Flag = heutiges Verhalten, kopierbar). Für ttz-lif/meiki-lra-ADRs
   ist `--auto` **wirkungslos** (Gate bricht ab, s. 3).
2. **Datei:** Quelle `platform/.windsurf/workflows/adr-handoff-extern.md`; neuer Step 4b zwischen
   Step 4 (Briefing schreiben) und Step 5 (Rückfluss).
3. **Hard-Gate vor Call:** Programmatischer Abort, wenn `project-facts.md` Org ∈ {ttz-lif, meiki-lra}
   ODER ADR-Text Mandantendaten-Marker trägt → **kein Call, keine Datei**, Exit mit Verweis auf
   `/adr-challenger`. Dieses Gate ist Vorbedingung, kein Best-Effort.
4. **Call-Pfad:** OpenAI reasoning-tier via Orchestrator-Gateway (C2). `headless_run` **nicht** —
   ist `RiskClass.IRREVERSIBLE` (C3, grep-Ebene) und für Repo-Agenten, nicht für einen Prompt-Call.
5. **Output:** Antwort als zweite `.md` neben dem Briefing: `~/shared/adr-handoff-<ADR>-<datum>-response.md`,
   deterministischer Name (Idempotenz wie Briefing).
6. **Step 5 unverändert manuell:** Mensch/Session taggt jede AD-/REC-ID im Repo-Kontext.

## Kill-Gate

- **Messbare Abbruchschwelle:** siehe `kill_criteria` im Frontmatter — 3 reale Läufe ohne
  Mehrwert gegenüber manuell (gemessen an `[valid]`-Quote pro Lauf) → `--auto` entfernen.
- **Exception-Budget:** bis **2026-07-20** (`review_by`). Kein grünes Signal bis dahin → `sunset`.

## Befunde (T2 — Steelman, Advocatus Diabolus, Maintainer-2028)

| ID | Rolle | Befund | Schwere |
|---|---|---|---|
| STEEL | Steelman | Der Skill existiert für **Provider-Diversität** (Cross-Provider-Zweitmeinung, die der interne Single-Provider-`adr-challenger` nicht liefert). Automatisierung senkt die Friktion genau des einen Schritts, der Diversität liefert — mehr ADRs bekommen real eine externe Gegenstimme statt sie aus Bequemlichkeit zu überspringen. | — |
| AD-1 | Advocatus Diabolus | Automatischer Call = **automatisierter Egress** von ADR-Inhalt. Heute ist der Mensch der Egress-Aktuator und fängt „oops, das referenziert Realdaten" ab. Ein nur *behauptetes* programmatisches Gate (L6) ohne harten Marker-Test verschiebt den Perimeter, ohne ihn zu sichern. | hoch |
| AD-2 | Advocatus Diabolus | „GPT 5.5 max" ist Wunschdenken (L5) — verdrahtet ist gpt-4o. Wer das hart verdrahtet, baut gegen ein Modell, das es auf dem Account evtl. nicht gibt (Präzedenz: Routing-Policy-Reality-Check 2026-05-13). | mittel |
| AD-3 | Advocatus Diabolus | Bequemerer Round-Trip verleitet zur **zweiten/dritten Runde reflexhaft** — der Skill warnt explizit vor sinkendem Grenznutzen. Automatik untergräbt die „eine Runde"-Default-Disziplin. | niedrig |
| M28 | Maintainer 2028 | Ich erbe einen Skill, der still OpenAI-Calls absetzt. Wenn niemand `[valid]`-Quoten misst, weiß keiner, ob die Automatik je etwas brachte — sie läuft als Kostenposten weiter. Das Kill-Gate (oben) ist die Versicherung dagegen. | mittel |

## Alternativen

| # | Alternative | Vorteil | Nachteil | verworfen? |
|---|---|---|---|---|
| ALT-1 | **Voll-Automatik inkl. Auto-Rückfluss** (LLM taggt eigene Befunde) | maximal schnell | hebelt L2-Sicherheitsgate aus; Zweitmeinung wird Gummistempel | ja — widerspricht Skill-Designziel |
| ALT-2 | **Status quo lassen** (rein manuell) | null Egress-Risiko, null Bauaufwand | Friktion bleibt; ADRs überspringen externe Runde aus Bequemlichkeit | nein — ist der Fallback, wenn Kill-Gate zieht |
| ALT-3 | **Multi-Provider-Fan-out** (OpenAI + Gemini + Mistral parallel) | breitere Diversität | mehr Egress, mehr Kosten, mehr Synthese-Aufwand; T3-Eskalation | ja (für jetzt) — erst nach MVC-Bewährung |

## Top-Risiken

| ID | Risiko | Gegenmaßnahme |
|---|---|---|
| RISK-1 | ~~**ADR-Reklassifizierung:** Falls automatisierter Egress als neuer Security-Perimeter-Schritt gilt~~ **AUFGELÖST 2026-06-20 → kein ADR.** Perimeter-Crossing war bereits 2026-05-29 bei Skill-Erstellung entschieden; OpenAI verdrahtet (C2); reversibel per Flag. Geändert wird nur der Enforcement-Aktuator (Mensch→programmatisches Gate). | **Bedingung erfüllt:** Hard-Gate-Test (Step 4b.1, souveräne Org/Mandantendaten → Abort) trägt die Einstufung. Ohne diesen Test kippte es zu ADR-pflichtig. |
| RISK-2 | **Stille Egress ohne Gate** (AD-1) | Hard-Marker-Test im Gate als Vorbedingung; Test `test_should_abort_auto_for_sovereign_org` als Akzeptanzkriterium vor Merge. |
| RISK-3 | **Modell-ID-Drift** (AD-2/L5) | Modell-ID aus model_registry reasoning-tier ziehen, nicht hardcoden; `GET /v1/models` als Preflight. |

## Empfehlungen

- **REC-1 → AD-1/RISK-2:** Souveränitäts-Gate als programmatischen Hard-Abort mit Marker-Test bauen,
  **bevor** überhaupt ein Call-Pfad verdrahtet wird. Kein `--auto` ohne grünen Gate-Test.
- **REC-2 → AD-2/L5:** Ziel-Modell aus `model_registry.py` reasoning-tier beziehen (C2), nie
  „gpt-5.5" hardcoden; `GET /v1/models` als Preflight-Check.
- **REC-3 → L4:** Policy `llm-routing.md` + CLAUDE.md korrigieren: Key liegt in `~/.secrets/`,
  nicht `~/shared/secrets-inbox/`; aifw-Repo ist `~/github/aifw`, nicht `iil-aifw`.
- **REC-4 → L2/M28:** Step 5 bleibt manuell + Kill-Gate-Messung (`[valid]`-Quote) ab Lauf 1 mitführen.

## Entscheidung

**Pilot empfohlen** als T2-MVC (Flag + Hard-Gate + Single-Call + manueller Rückfluss). **Vorbedingung:**
RISK-1 (ADR-Threshold) vor Bau einmal explizit auflösen, da der Egress-Charakter die „kein ADR"-Einstufung
kippen könnte. Kein Voll-Automatik (ALT-1). Review bis 2026-07-20.

## Umsetzungs-Status (Abschluss-Checkliste)

> Ergänzt 2026-07-24 (#1167, Muster PR #1275): macht den Ausführungsstand jeder
> Empfehlung + des Kill-Gates explizit, damit das Dokument abgearbeitet statt
> überflogen wird. Stand: `pipeline_status: idea` — noch nichts gebaut.

| Bedingung / REC | Status | Beleg / nächster Schritt |
|---|---|---|
| **Vorbedingung** RISK-1 (ADR-Threshold) explizit aufgelöst | ✅ erledigt | „AUFGELÖST 2026-06-20 → kein ADR" (§Top-Risiken); Hard-Gate-Test trägt die Einstufung |
| **REC-1** Souveränitäts-Gate = programmatischer Hard-Abort + Marker-Test, VOR Call-Pfad | ⬜ offen | kein `--auto` ohne grünen Gate-Test; `test_should_abort_auto_for_sovereign_org` |
| **REC-2** Ziel-Modell aus `model_registry.py` (reasoning-tier) + `GET /v1/models`-Preflight | ⬜ offen | nicht gebaut |
| **REC-3** Policy `llm-routing.md` + CLAUDE.md korrigieren (Key-Pfad, aifw-Repo-Name) | ⬜ offen | nicht verifiziert |
| **REC-4** Step 5 manuell + `[valid]`-Quote ab Lauf 1 mitführen | ⬜ offen | Kill-Gate-Messgrundlage |
| **Kill-Gate** 3 reale `--auto`-Läufe ohne Mehrwert → `--auto` entfernen | ⬜ nicht erreicht | 0 Läufe (MVC nicht gebaut) |
| **Exception-Budget** grünes Signal bis `review_by` 2026-07-20 | ⛔ überschritten → **`sunset` 2026-07-24** | Budget verstrichen, 0 `--auto`-Läufe → Kill-Gate zieht. `pipeline_status: sunset`. Manueller Pfad (ALT-2) bleibt Default; Re-open nur mit REC-1 zuerst. |
