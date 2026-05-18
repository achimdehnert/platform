---
status: accepted
date: 2026-05-18
decision-makers: [Achim Dehnert]
implementation_status: partial
related: [ADR-111, ADR-196, mcp-hub#59, dev-hub#53, platform#187]
---

# ADR-209: Cross-Repo CI-Health als wiederkehrendes gegatetes Programm (Contract-First)

## Status

accepted — Skill `/ci-green-program` live; Lauf 1 (2026-05-18) durchgeführt.

## Kontext

48 Repos unter `~/github`. CI-Grün ist kein erreichbarer *Zustand* (Dep-Bumps,
Drift, neuer Code machen kontinuierlich rot), sondern eine zu minimierende
**Mean-Time-to-Green**. Lauf 1 lieferte empirische Tradeoffs, die festgehalten
werden müssen, damit der Prozess wiederholbar stabil ist statt jedes Mal
dieselben Fehlgriffe zu machen. Der User-Zielzustand: Infra über
develop→staging→prod stabil, Methoden so dokumentiert, dass künftige stärkere
Modelle den Loop jederzeit fortführen/reviewen können.

## Entscheidung

CI-Health wird als **wiederkehrender Loop mit Triage-Gating** betrieben
(Skill `/ci-green-program`, Governance hier):

**Survey → Triage(verify) → Gate → Issue(Schema) → Queue/Direct → Merge → Lehren.**

Verbindliche Gates (empirisch begründet, Lauf 1):

- **G1 Survey-Korrektheit:** Status = letzter *push/PR*-getriggerter Lauf.
  `gh run list --limit 1` ist verboten (maskiert rot via grünem Dependabot).
- **G2 Verify vor Handlung:** jede Survey-Klassifikation am Repo prüfen.
- **G3 Versions-/API-Check** vor jedem „mechanischen" Dependency-Swap.
- **G4 Cross-cutting zuerst:** ein Fix der n Repos entsperrt (shared dep,
  shared workflow, repo-übergreifendes Gate) vor per-Repo-Arbeit. Opus.
- **G5 Hard-Gate Deploy/Infra:** Server-State nie in autonome Queue.
- **G6 Judgment-Gate:** Test-vs-Code / Coverage-Senkung / Star-Import →
  `ci-green` ohne `auto` (manuelle Sonnet-Session). Rein mechanisch → `auto`.
- **G7 Contract-First:** jedes Issue benennt die erzwungene Regel, die der Fix
  wiederherstellt. „Grün machen" = „Contract härten", nicht Symptom dämpfen.

**Modell-Routing:** Opus = Triage + Cross-cutting + Judgment. Sonnet =
spezifizierte mechanische Issues (Queue/manuell). Cerebras verworfen
(Tool-Use-Schwäche). Vgl. ADR-196, Policy llm-routing.

## Konsequenzen

**Positiv:** wiederholbar; teure Analyse (Opus) einmal → billige Ausführung
(Sonnet) skaliert; Contract-First verwandelt Wartung in Härtung; Gates
verhindern die teuren Lauf-1-Fehlklassen (Blind-Swap-Downgrade, Deploy-Flailing).

**Negativ / Risiko:** Triage bleibt Opus-Nadelöhr; Gate-Disziplin ist
menschen-/agenten-abhängig; ein falsch als `auto` gelabeltes Judgment-Issue
erzeugt teure Nacharbeit (Mitigation: G6 + Phase-7-Lehren-Rückschrieb).

**Reversibel:** Loop ist ein Skill + Labels; Abschalten = Skill nicht mehr
triggern. Kein Infra-Lock-in.

## Alternativen

- **Einmal-Aufräumen ohne Prozess** — verworfen: CI rottet nach, MTTR steigt
  wieder; Vision (selbst-fortführbar) nicht erfüllt.
- **Voll-autonom ohne Gates** — verworfen: Lauf 1 zeigte plausibel-falsche
  Fixes (8-Repo-Downgrade) und Deploy-Flailing; Nacharbeit > Ersparnis.
- **Pro-Repo manuell** — verworfen: skaliert nicht über 48 Repos.

## Kadenz

Phase 1+2 (Survey+Triage) monatlich bzw. via Repo-Health-Agent-Trigger
(dev-hub#38). Phasen 3–7 on-demand bei roten Clustern. Phase 7
(Lehren-Rückschrieb) ist Pflicht-Abschluss jedes Laufs.
