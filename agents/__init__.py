"""
Platform Agents — LLM Agent Ecosystem (ADR-054).

Agents:
  - guardian: Architecture Guardian (A2, PR-Analyse, 4 Regeln)
  - onboarding_coach: Onboarding Coach (A5, Interaktiver Assistent)
  - context_reviewer: Context Reviewer (A6, PR-Kontext-Analyse)

Ehemalige Prototypen (A3 adr_scribe, A4 drift_detector) wurden entfernt —
die ADR-Scribe- und Drift-Detection-Rolle übernimmt die DB-gestützte Lösung
in dev-hub/apps/adr_lifecycle (ADR-059, accepted 2026-02-21).
"""

__version__ = "0.2.0"
