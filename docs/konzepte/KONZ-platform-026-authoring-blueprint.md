---
concept_id: KONZ-platform-026
title: authoring-blueprint — contract-getriebenes Mensch↔KI-Protokoll für strukturierte Vorhaben
pipeline_status: pilot
tier: T2
owner: Achim Dehnert
spec_refs: []              # Methodik/Konvention — kein Klickdummy-Spec; folgt spec-first-DNA (ADR-211-Umfeld)
adr_threshold: kein ADR    # Muster folgt bestehender contract-/SSoT-DNA (writing-hub ADR-273/274, idea_import); Konvention, kein neuer Service-Boundary/Trade-off
review_by: 2026-10-19
kill_criteria: "Bis 2026-10-19: wenn ein zweiter Pilot in einer ANDEREN Domäne (nicht-Buch, z.B. Vorlesung/Dossier) das Fünf-Schritt-Protokoll nur mit domänen-spezifischem UMBAU (nicht bloß anderem Contract) zum Laufen bringt, ist der 'general blueprint'-Anspruch falsch → auf 'writing-hub-Import-Runbook' zurückstufen, KONZ archivieren. Ebenso Kill, wenn nach 2 Läufen KEIN Dogfooding-Fund einen writing-hub-Fix ausgelöst hat (dann ist die Verify-Gabelung Dekoration)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: writing-hub apps/idea_import/, commit_or_pr: main, opened_in_session: true}   # Import-Contract (staging + commit)
  - {claim_id: C2, source_path: writing-hub apps/authoring/defaults.py::distribute_chapter_targets, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C3, source_path: "writing-hub#254, writing-hub#255", commit_or_pr: issues, opened_in_session: true}  # erste Dogfooding-Funde
  - {claim_id: C4, source_path: "~/shared/books/zimmer7/_blueprint/ (contracts.md, mapping.yaml, blueprint.md, learnings.md)", commit_or_pr: shared, opened_in_session: true}
created: 2026-07-19
---

# KONZ-platform-026 — authoring-blueprint

## Problem

Strukturierte generative Vorhaben (Buch, Vorlesung, Weltenbau, Dossier) laufen heute **ad-hoc**:
Mensch chattet mit einem LLM, kopiert Ergebnisse von Hand in eine App. Der Round-Trip ist weder
reproduzierbar noch verlässlich, und was im Chat entsteht, driftet gegen das strukturierte System.
Gleichzeitig ist die Plattform bereits *contract-getrieben* (Klickdummies/ADR-211, writing-hub als
Kompositions-SSoT ADR-273/274, `idea_import`) — das Muster ist implizit da, aber nicht benannt.

## Kern-These

Jedes strukturierte Vorhaben ist eine **Kette typisierter Verträge**. Die generative Arbeit gehört in
den Dialog (das LLM ist die Instanz, die die Domänen-App ohnehin aufruft); die Ergebnisse müssen über
**verifizierte Verträge** verlässlich zurücklaufen. Der Blueprint macht diesen Round-Trip reproduzierbar.

## Zwei Schichten

1. **Daten-Verträge** (existieren größtenteils schon je Hub) — z. B. writing-hub `idea_import`:
   `extracted_data{title,description,outline_beats|chapters,characters,world}` → Commit je `approved_sections`
   → `BookProject`/`OutlineVersion`. Werden **entlang des Weges** verifiziert, nicht als Vorab-Wasserfall.
2. **Interaktions-Protokoll** (das Übertragbare) — fünf Züge je Vertrag:
   **Propose** (KI entwirft) → **Decide** (Mensch gibt frei = HITL-Gate) → **Serialize** (in die verifizierte
   Contract-Form) → **Verify** (gegen echten Contract/Schema/Kanon; binär) → **Persist** (sanktionierter Pfad,
   nie roher INSERT; **Prod ist ein Gate**).
   - **Verify-Gabelung:** ein Fund ist entweder **(a) unser Content/Kanon** → Quelle korrigieren, oder
     **(b) eine Werkzeug-Limitierung** → Issue/PR gegen den Hub (**Dogfooding**).

## Beweis — Pilot 1 (zimmer7, metadata + outline), NICHT Theorie

Vollständiger Round-Trip am fertigen Buch „Zimmer 7" **lokal bewiesen** (`writing_hub_db_dev`, Prod nicht
berührt): `mapping.yaml` → `extracted_data` → sanktionierte `_commit_metadata`/`_commit_outline` →
realer `BookProject` „Zimmer 7" + `OutlineVersion` + **20 OutlineNodes**, unabhängig re-gequeried.

Der echte Lauf lieferte prompt drei belastbare Dogfooding-Funde — der Beweis, dass die Verify-Gabelung trägt:
- **writing-hub#254** — `idea_import`-Commit verwirft `genre`/`target_audience`/`content_type` (live belegt: `genre=''`); `override_existing` ist No-Op.
- **writing-hub#255** — 🔴 Crash: `distribute_chapter_targets` liefert negative `target_words` (Default 5000 ÷ 20 Kap. → −600) → `_commit_outline`-IntegrityError.

## Dogfooding-Schleife (der eigentliche Hebel)

Das Werkzeug am echten Vorhaben benutzen legt offen, was das Werkzeug braucht. Jeder Verify-Fund vom Typ (b)
wird zu einer getrackten Hub-Verbesserung. So entwickeln sich **Blaupause UND Hub aus denselben Läufen** weiter.
Meta-Beleg: die Verify-Gabelung selbst entstand *während* Pilot 1 aus einem Kapitäns-Hinweis — der Blueprint
verbesserte sich im ersten Lauf aus echtem Gebrauch.

## Generalisierung (geplant, gestaffelt)

| Stufe | Vorhaben | beweist | Status |
|---|---|---|---|
| Pilot 1 | zimmer7 (fertiges Buch) | Plumbing/Round-Trip + Verify | ✅ bewiesen |
| Pilot 2 | „Das Erwachen" Band 1 (Konzept) | generative Hälfte + Welten-*Systeme* gegen den **bestehenden** `weltenhub World.systems_data`-Vertrag (ADR-095; nicht writing-hub) | angefangen |
| Tier 3 | 137-Ökosystem | Protokoll **über Hubs** (Buch→writing-hub, Community→137-hub, Web→design-hub) | später |

## Adversarial / Risiken (Right-Sizing)

- **Meta vor Objekt:** die Blaupause NICHT im Abstrakten bauen — aus echten Läufen destillieren (dieser KONZ folgt dem: erst Pilot, dann Doc).
- **Ökosystem vor Fiktion:** 137 als Community/Brand darf die noch ungeschriebene Serie nicht überholen → bewusst Tier 3.
- **Scheingeneralität:** ein an *einem* Projekt gefittetes Protokoll ist keine Blaupause → Kill-Kriterium fordert einen zweiten, domänen-fremden Lauf.

## Right-Sizing-Entscheid

T2, kein ADR: folgt bestehender contract-/SSoT-DNA (Addition, kein neuer Service-Boundary/irreversibler
Trade-off — `adr-threshold.md`). Lebende Detailtiefe (Contracts je Schritt, konkrete Payloads) lebt in
`~/shared/books/zimmer7/_blueprint/` (Arbeits-Artefakte); dieser KONZ ist die durable Konzept-Schicht.

## Nächster Schritt
Pilot 2 („Das Erwachen" Band 1) fährt die generative Hälfte + mappt die Welten-Systeme auf den bestehenden
weltenhub-`WorldSystems`-Vertrag (ADR-095). Fällt dort das
Fünf-Schritt-Protokoll ohne domänen-spezifischen Umbau durch, ist die Blaupause bestätigt (sonst: Kill).
