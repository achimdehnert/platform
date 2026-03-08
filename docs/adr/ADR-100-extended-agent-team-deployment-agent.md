---
status: deprecated
date: 2026-03-08
decision-makers: Achim Dehnert
superseded_by: ADR-107-extended-agent-team-deployment-agent.md
---

# ADR-100: DEPRECATED — Nummerierungsfehler

Diese Datei entstand durch einen Fehler im ADR-Nummerierungs-Algorithmus.
ADR-100 war bereits durch `ADR-100-iil-testkit-shared-test-factory-package.md` belegt.

**Der Inhalt wurde korrekt nach ADR-107 verschoben:**
[ADR-107-extended-agent-team-deployment-agent.md](ADR-107-extended-agent-team-deployment-agent.md)

## Root Cause des Fehlers

`adr_next_number.py` verwendete eine range-basierte Strategie (`platform: 1–99`),
die nach ADR-059 aufgegeben wurde. Das Script lieferte fälschlicherweise eine
Nummer aus dem bereits erschöpften Bereich statt den globalen Max+1.

**Fix**: `get_next_free()` verwendet jetzt `global max(used) + 1` — unabhaengig
von Repo-Bereichen. Behoben in commit nach ADR-107.
