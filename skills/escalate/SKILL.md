---
name: escalate
description: Eskaliert eine Aufgabe an ein höheres Modell-Tier (Sonnet → Opus, oder Stop+Refactor)
metadata:
  mode: read-only
  migrated_from: .windsurf/workflows/escalate.md
---

# /escalate — Tier-Mismatch-Signal

**Zweck**: User-Trigger, wenn die aktuelle Session-Modell-Stufe für die
laufende Aufgabe zu klein ist. Im Gegensatz zu modellseitiger Selbst-
Detection (unzuverlässig) ist `/escalate` ein **expliziter User-Befehl**.

## Output

```
⚠️ Tier-Escalation angefordert.

Aktuelle Session-Modell: <model aus System-Context>
Empfohlene Aktion:

  • Wenn aktuell Haiku/Sonnet → `/model claude-opus-4-7`  (Tier 4)
  • Wenn aktuell Opus 4.7    → Aufgabe splitten:
       1. den Anteil identifizieren, der NICHT konvergiert
       2. ihn extrahieren und neu formulieren
       3. ggf. mit /next neu priorisieren

Tipps zum Erkennen, dass eine Aufgabe wirklich Tier-4 ist:
  - Synthese über mehrere ADRs/Policies/Repos
  - Reversibilitäts-Frage (DSGVO, Sicherheit, Lizenzen)
  - Architektur-Entscheidung mit Folge-ADRs
  - Wiederholte Sackgassen in Sonnet trotz klaren Inputs
```

## Anschluss

- Wenn der User nach `/escalate` `/model claude-opus-4-7` ruft und denselben
  Prompt wiederholt: in der neuen Session ist der Kontext frisch — daher den
  bisherigen Stand mit 1–2 Sätzen rekapitulieren (was wurde versucht, wo
  blieb's hängen), bevor die neue Lösung gestartet wird.

## Was der Skill NICHT tut

- Kein automatischer Modell-Wechsel (das geht nur über `/model`).
- Keine Garantie, dass Opus die Aufgabe löst — manche Aufgaben sind nicht
  Tier-, sondern Daten-/Klarheits-Probleme.

## Changelog

- 2026-05-20: Initial (live-only CC-Utility-Skill).
- 2026-05-30: In den Kanon `platform main .windsurf/workflows/` promoted (ADR-230 CC-first); `mode: read-only` ergänzt.
