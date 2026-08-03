# Policy: Error Handling — Ursache statt Quick-Fix
<!-- rule_class: B | assessed_with: claude-fable-5 | reassess_by: 2027-08-01 (KONZ-038 D4) -->

**Trigger words:** fehler, bug, root cause, ursache, quick fix, quickfix, hotfix, workaround, incident, schon wieder, erneut aufgetreten, nachhaltige lösung

## Rule (Owner-Weisung 2026-08-03 — gilt org-weit: achimdehnert, iilgmbh, ttz-lif, meiki-lra)

Bei jedem Fehler mit **Schadens- oder Wiederholungspotenzial**:

1. **Ursache belegen, nicht raten** — `evidence-discipline.md` gilt für Diagnosen genauso
   wie für Erfolgs-Claims (ein Ursachenlabel ohne Check ist eine Hypothese und wird so
   gekennzeichnet).
2. **Fix auf Ursachen-Ebene bevorzugen.** Ein Quick-Fix ist nur als Incident-Erstmaßnahme
   zulässig (stop the bleeding, /hotfix-Pfad) — dann PFLICHT: Folge-Ticket für den
   Ursachen-Fix **im selben Zug** (Tracking-Artefakt-Regel).
3. **Lehre nach bestehender Taxonomie sichern** — nicht „irgendwo notieren":
   🌀-Drift-Memory nur bei benennbarer Fehlhypothese · `error_pattern` in pgvector
   (`tools/session-memory`) · Outline-Lesson bei übertragbarem Muster — jeweils mit
   `rule_class`/`assessed_with`/`reassess_by` (KONZ-038 D4).
4. **Ab dem 2. Auftreten derselben Fehlerklasse: Gate bauen** (Reconcile → Drill → Bau,
   KONZ-038 §5.2) **statt einer weiteren Prosa-Regel.** Prävention leisten Gates —
   Aufschreiben allein hat Wiederholung nachweislich nicht verhindert (Drift-Historie,
   u. a. ×12 `handover-stale-vor-merge`).

## Abgrenzung — bewusst KEINE Fehler im Sinne dieser Policy

- **Gewollte Grenzen:** Permission-/Classifier-Blocks, Review-Pflichten, fehlende
  Freigaben. Lösung = etablierter Fallback (Kommando/Skript an den Owner, `~/shared/`),
  nie Engineering um die Grenze herum.
- **Proportionalität:** einmalige Trivialfehler ohne Schadens- und Wiederholungspotenzial
  brauchen keine Root-Cause-Analyse (Right-Sizing; Bash-/Token-Sparsamkeit bleibt gültig).

## Herkunft

Owner-Direktive 2026-08-03, adversarial geprüft (4 Einwände eingearbeitet: Incident-
Reihenfolge, Gate-statt-Regel, Memory-Inflation vs. D4/Sunset, Grenzen≠Fehler).
Prinzipien-Anker: Advocatus Diaboli · Out-of-the-box · Continuous Improvement ·
Predictive Maintenance (bestehende Programme: Megatest, Regel-Ritual, Health-Monitoring).
