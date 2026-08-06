# Policy: Zielzustand-first
<!-- rule_class: A | assessed_with: claude-fable-5 | reassess_by: 2026-12-01 -->

**Trigger words:** zielzustand, zielbild, target state, akzeptanzkriterien, acceptance criteria, definition of done, soll-zustand, endzustand, woran erkennen wir

## Rule (User-Weisung 2026-08-06, org-weit)

Aufgaben, Änderungen und Umbauten werden gegen einen **klar beschriebenen
und akzeptierten Zielzustand** erledigt. **Fehlt er, wird er VOR
Arbeitsbeginn geklärt** — nicht während oder nach der Arbeit rekonstruiert.

1. **Zielzustand = beobachtbares Endergebnis**, nicht Tätigkeitsliste:
   „Was ist am Ende wahr, und woran erkennen wir es?" — 1 Satz Endzustand
   + 2–5 prüfbare Akzeptanzkriterien + Out-of-Scope, falls abgrenzungsbedürftig.
2. **Fehlt er:** kurzen Zielzustands-Vorschlag (3–7 Zeilen) formulieren und
   Akzeptanz einholen, bevor substanzielle Arbeit beginnt. Schweigen ≠ Zustimmung.
3. **Akzeptiert heißt akzeptiert:** existiert bereits ein Artefakt mit
   Akzeptanzkriterien (Issue, ADR, KONZ), IST das der Zielzustand —
   referenzieren statt neu erfinden; bei Widerspruch zuerst klären.
4. **Abnahme gegen den Zielzustand**, nicht gegen erledigte Schritte:
   „fertig" = Zielzustand im Zielkontext verifiziert (Evidenz-Pflicht
   aus `evidence-discipline.md` unverändert).
5. **Drift-Anker:** Weicht die Arbeit vom akzeptierten Zielzustand ab
   (drittes Repo, neue Anforderung, Prod-Wirkung), greift der
   Scope-Checkpoint — Zielzustand aktualisieren + erneut akzeptieren
   lassen, nicht stillschweigend erweitern (`autonomy-gates.md`).

## Right-Sizing (kein Bürokratie-Overhead)

- **Trivial/mechanisch** (Typo, 1-Datei-Fix, eindeutige direkte Anweisung):
  die Anweisung selbst IST der Zielzustand — kein separater Klärungsschritt.
- **Substanziell** (neues Feature, Refactor, cross-repo, Prod-Wirkung,
  mehrdeutige oder lückenhafte Anweisung): expliziter Zielzustand PFLICHT
  vor Beginn.
- **Ort:** Chat genügt für Kleines; alles, was einen PR überlebt, trägt
  den Zielzustand im Artefakt (Issue-Body, ADR, KONZ) — dort prüft ihn
  auch der Review.

## Warum

Wiederkehrendes Muster über Retros: Arbeit lief „autonom durch" und
verfehlte das eigentlich Gewollte, weil das Ziel nie explizit vereinbart
war — Scope-Drift, Doppelarbeit, Abnahme gegen „was getan wurde" statt
„was erreicht sein sollte". Ein vorab akzeptierter Zielzustand macht
Drift sichtbar (Punkt 5) und Abnahme prüfbar (Punkt 4).
