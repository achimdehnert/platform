---
concept_id: KONZ-platform-028
title: Generischer Fach-/Experten-Reviewer (persona-parametrisierter Domänen-Kritiker)
pipeline_status: idea
tier: T2
owner: Achim Dehnert (pg@dehnert.team)
spec_refs: []                 # keine KD-Spec — Reviewer-Capability, kein Klickdummy
adr_threshold: kein ADR für den Pilot (1 Skill, reversibel) · org-weite Distribution via cc-skill-dist ⇒ Amendment ADR-100-Reviewer-Familie / ADR-211
review_by: 2026-10-23
kill_criteria: "Nach 3 realen Einsätzen: wenn die belegt-Findings-Trefferquote (durch menschlichen Fachprüfer bestätigt) < 50 % ODER die Persona-Parametrisierung in ≥2 Domänen keinen Mehrwert über einen Ad-hoc-Subagent-Prompt zeigt ⇒ verworfen."
superseded_by_spec: null
created: 2026-07-23
evidence_manifest:
  - {claim_id: C1, source_path: "platform/.windsurf/workflows/{kd-review,agent-review,adr-review}.md + ls workflows/*review*", commit_or_pr: "grep 2026-07-23", opened_in_session: true}
  - {claim_id: C2, source_path: "~/.claude/agents/ (leer) + ~/.claude/skills/", commit_or_pr: "ls 2026-07-23", opened_in_session: true}
  - {claim_id: C3, source_path: "frist-hub Fachaudit Wohngeld-Handout (Opus-Subagent, dieselbe Session)", commit_or_pr: "meiki-lra/frist-hub#74", opened_in_session: true}
---

# KONZ-platform-028 — Generischer Fach-/Experten-Reviewer

> **Cross-cutting Reviewer-Capability · Heimat platform** (Org `achimdehnert`). Geerdet am
> frist-hub-Fachaudit des Wohngeld-Handouts (`meiki-lra/frist-hub#74`); hierher graduiert, weil
> die Capability fleet-weit gilt — und weil das Souveränitäts-Gate ein in `meiki-lra` liegendes
> Konzept von externer Zweitmeinung ausschließt, in `platform` aber nicht (kein Bürgerdaten-Inhalt).

## Kernthese

Ein einziger, **read-only, persona-parametrisierter** Reviewer-Mechanismus — *Persona × Artefakt ×
Maßstab* variabel, *Evidenz-Ausgabe-Kontrakt fix* — schließt die fehlende **Fachlichkeits-Achse** im
Reviewer-Ökosystem und **komponiert** mit den bestehenden achsen-spezifischen Reviewern, statt sie zu ersetzen.

## Assumption-/Decision-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|-------------------------|--------|
| A1 | Es gibt keine *Fachlichkeits-/Domänen*-Reviewachse — alle bestehenden Reviewer sind achsen-spezifisch (UX/Code/ADR/Security/Fleet) | Annahme | C1: `kd-review`=UX, `agent-review`=PR-vs-ADR/Ruff/Bandit (ADR-100), `adr-review`=ADR-Checklist, `adr-handoff-extern-reviewer*`=externe Zweitmeinung, `platform-audit`=Fleet — kein Domänen-Persona-Reviewer | belegt |
| A2 | LLM-Fachkritik liefert **Hypothesen**, keine Ratifizierung; final entscheidet die Fachstelle | Annahme | C3: Fachaudit trennte belegt/Hypothese; Finding #2 (§84 SGG→§70 VwGO) ging an Rechtsamt (frist-hub PR #5), Finding #1 (§66 Abs.3) war belegt+umgesetzt | belegt |
| A3 | Der eigentliche Mehrwert ist der **erzwungene Kontrakt**, nicht der Freitext-Prompt | Annahme | C3: derselbe Auditor re-derivte unabhängig die PR-#5-Korrektur — reproduzierbare Tiefe kam aus Persona+Kontrakt, nicht Zufall | plausibel |
| D1 | **Read-only**, ratifiziert nie; Output ephemer (Issue/PR-Kommentar/Handover), **kein neues Scoreboard/SSoT** | Entscheidung | SSoT-Prüfung: keine zweite Wahrheitsquelle, Findings sind Vorschläge | gesetzt |
| D2 | Fixer Ausgabe-Kontrakt: Findings **P1/P2/P3 · belegt‖Hypothese · „gegen was verifizieren"** | Entscheidung | Invariante über alle Läufe; Persona/Maßstab variabel | gesetzt |
| D3 | Form = **Skill**, der pro Lauf einen **Sub-Agenten** mit gesetzter Persona + Modell-Tier spawnt — **nicht** ein statisches CC-Sub-Agent-File | Entscheidung | C2: `~/.claude/agents` leer; Persona wechselt pro Einsatz → statisches File zu starr; `kd-review` spawnt bereits Sonnet-Subagent | gesetzt |
| D4 | Modell-Tier **pro Einsatz**: Domänen-Korrektheit mit rechtlichen/Sicherheits-Einsätzen ⇒ **Opus**; reine Verständlichkeit/Stil ⇒ **Sonnet** | Entscheidung | C1/C3: `kd-review`-UX lief Sonnet; Wohngeld-Fachaudit lief Opus (rechtliche Einsätze) — Ergebnis rechtfertigte die Tier-Wahl | gesetzt |
| R1 | **Scheinkompetenz** — klingt autoritativ, liegt falsch (falsch-autoritatives P1 kostet Vertrauen) | Risiko | Mitigation D2 (belegt/Hypothese + verify-against); Restrisiko → Kill-Gate misst Trefferquote | offen |
| R2 | Overlap/Verwirrung mit bestehenden Reviewern → Doppelarbeit | Risiko | Mitigation: Achsen-Abgrenzung dokumentiert (s. MVC); Persona/Maßstab machen die Achse explizit | offen |
| R3 | Org-weite Distribution ohne Governance (cc-skill-dist) = Cross-Repo-Impact | Risiko | Mitigation: Distribution ist eigenes Gate (ADR-Amendment), **nicht** Teil des T2-Pilots | offen |

## MVC (Minimal Viable Concept — konkret)

- **1 Skill** `/fach-review` (Arbeitsname) in `platform/.windsurf/workflows/`, verteilt via `cc-skill-dist`.
- **Parameter:** `--persona <lens>` · `--artefakt <pfad|url>` · `--standard <ADR/Norm/Quellen>` · `--modell <opus|sonnet>` (Default per D4-Heuristik) · optional `--persona-lib <name>` (wiederverwendbare Persona-Bausteine, z. B. `wohngeld-sb+verwaltungsrecht`, `datenschutz`, `klinik`).
- **Ablauf:** Skill spawnt einen Agenten, dessen System-Prompt = Persona + 4 Prüf-Dimensionen (Tiefe/Vollständigkeit · Korrektheit · Verständlichkeit · Konventionen/Standards) + fixer Ausgabe-Kontrakt (D2) + read-only. Rückgabe = Findings-Liste; bei ≥3 Findings Issue-Vorschlag (nicht selbst anlegen).
- **Abgrenzung (gegen R2), fest im Skill dokumentiert:** Fachlichkeit/Domäne — **nicht** UX (`/kd-review`), **nicht** Code/PR-vs-ADR (`/agent-review`), **nicht** ADR-Schema (`/adr-review`), **nicht** Security-Perimeter (`/security-review`). Komposition: dieselbe Artefakt-Instanz kann mehrere Achsen-Reviewer nacheinander durchlaufen.
- **Kill-Gate-Datenbasis = erste 3 Realläufe:** (1) Wohngeld-Handout = **Referenzlauf, bereits erfolgt** (fand belegtes P1 §66 Abs.3), (2) ein Datenschutz-Artefakt, (3) ein ADR/Konzept.

## Adversariale Analyse (T2)

**Steelman:** Der Kontrakt (D2) ist die eigentliche Invariante und billig über Domänen wiederverwendbar; Persona/Maßstab sind reine Parameter; es *komponiert* statt zu ersetzen; und es ist an einem realen Lauf geerdet, der einen echten, belegten P1-Rechtsfehler fand, den die UX-Prüfung strukturell nicht finden konnte.

| Befund | Quelle | Antwort / Restrisiko |
|--------|--------|----------------------|
| AD-1: „Ein generischer Reviewer ist nur ein Prompt-Template — braucht es dafür einen Skill?" | Advocatus Diabolus | Wert = erzwungener Kontrakt (D2) + Persona-Lib + Modell-Routing (D4); ohne Skill driftet jeder Ad-hoc-Lauf (A3). Rest: gering. |
| AD-2: Scheinkompetenz — falsch-autoritatives P1 | Advocatus Diabolus | D2 mildert; **Restrisiko real** (R1) → Kill-Gate misst Trefferquote, Findings nie Freigabe |
| AD-3: Erzeugt es eine zweite Wahrheitsquelle? | Advocatus Diabolus | Nein — Output ephemer, kein Scoreboard (D1) |
| AD-4: Wird das „Tool" faktisch zur Boundary/zum Gate? | Advocatus Diabolus | Nein — read-only, kein Enforcement; „sichtbar machen", nicht „verhindern" |
| AD-5 (Maintainer-2028): Persona-Bibliothek veraltet (Normen ändern sich) | Maintainer-2028 | Persona/Standard sind Pro-Lauf-Parameter, keine eingefrorene Wahrheit; Norm-Quelle wird pro Lauf zitiert (verify-against) |

**2 Alternativen**

| Alt | Beschreibung | Warum nicht (allein) |
|-----|--------------|----------------------|
| Alt-1: Status quo (Ad-hoc-Subagent-Prompts) | Pro Bedarf einen Prompt schreiben | Billiger, aber kein Kontrakt, driftet, nicht wiederverwendbar, kein Modell-Routing (A3) |
| Alt-2: Je Domäne ein eigener Spezial-Skill (wie `kd-review` für UX) | N domänenspezifische Reviewer | Präziser je Domäne, aber Achsen-Explosion + N-facher Pflegeaufwand; nur lohnend bei dauerhaft hoher Frequenz einer Domäne |

## Empfehlung & Entscheidung

**Bauen als T2-Pilot:** 1 Skill `/fach-review`, Referenzlauf (Wohngeld, erledigt) + 2 weitere Realläufe (Datenschutz, ADR/Konzept), dann Kill-Gate-Auswertung. **Org-weite Distribution** via cc-skill-dist erst **nach** ADR-Amendment (ADR-100-Reviewer-Familie / ADR-211). Spezial-Skills (Alt-2) nur ergänzend, wo eine Domäne dauerhaft hohe Frequenz zeigt.

**Kill-Gate:** siehe `kill_criteria` (Frontmatter). Exception-Budget: bis `review_by` 2026-10-23; bei Nichterreichen der 3 Realläufe bis dahin ⇒ `sunset` mit Begründung.

## Externe Zweitmeinung (Audit-Nachweis)

- `external_sparring_by:` _(nach Rückfluss gesetzt — Provider@Datum)_
- Tag-Tabelle (AD-/REC-ID → Verdikt → Aktion): _folgt nach Step-5-Rückfluss._
