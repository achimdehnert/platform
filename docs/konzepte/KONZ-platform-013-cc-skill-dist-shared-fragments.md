---
concept_id: KONZ-platform-013
title: "cc-skill-dist Shared-Fragment-Include — Single-Source für über mehrere Skill-Dateien verteilte Konventionsinhalte"
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []
adr_threshold: kein ADR (Erweiterung von ADR-230, kein Reversal)
review_by: 2026-10-06
kill_criteria: "Binnen 90 Tagen (bis 2026-10-06) nutzen weniger als 2 unabhängige Skill-Datei-Gruppen den Include-Mechanismus → Mechanismus wieder aus generate.py/doctor.py entfernen, stattdessen dauerhaft auf den doctor.py-Feld-Check (Issue #970) allein setzen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "platform/tools/cc-skill-dist/doctor.py:26-27", commit_or_pr: HEAD, opened_in_session: true}
  - {claim_id: C2, source_path: "platform/docs/adr/ADR-230-cc-first-skill-distribution.md", commit_or_pr: HEAD, opened_in_session: true}
  - {claim_id: C3, source_path: "platform/tools/cc-skill-dist/generate.py + doctor.py (grep include|fragment|shared|template)", commit_or_pr: HEAD, opened_in_session: true}
  - {claim_id: C4, source_path: "platform/.windsurf/rules/project-facts.md", commit_or_pr: HEAD, opened_in_session: true}
  - {claim_id: C5, source_path: "platform/.windsurf/workflows/{kd-scout,klickdummy,kd-review}.md", commit_or_pr: "#965", opened_in_session: true}
  - {claim_id: C6, source_path: "platform/tools/cc-skill-dist/generate.py:38 + doctor.py:31 (distribute:false-Mechanismus)", commit_or_pr: HEAD, opened_in_session: true}
  - {claim_id: C7, source_path: "GitHub Issue achimdehnert/platform#970", commit_or_pr: "#970", opened_in_session: true}
created: 2026-07-06
---

## Kernthese

`generate.py` bekommt einen Include-Mechanismus (`<!-- cc-skill-dist:include <fragment> -->`), der
zur Build-Zeit den Inhalt einer als `distribute: false` markierten Fragment-Quelldatei **inline**
in die generierte Kopie kopiert — damit Konventionsinhalte, die mehrere distribuierte Skill-Dateien
teilen (wie das KD-Referenz-Schema aus PR #965), eine echte Single-Source haben, ohne den
Relativlink-Guard zu verletzen oder eine zur Laufzeit unauflösbare externe Link-Abhängigkeit zu
erzeugen.

## Scope & Evidenzbasis

Geöffnet in dieser Session: `tools/cc-skill-dist/doctor.py` (REL_LINK-Regex, `distribute:false`-
Filter), `tools/cc-skill-dist/generate.py` (Lane-Konfiguration, `distribute:false`-Filter, kein
Include/Fragment/Template-Treffer bei gezieltem grep), `docs/adr/ADR-230-cc-first-skill-distribution.md`
(Policy-Kollaps-Präzedenz „eine kanonische Kopie + Pointer-Stubs" für `claude-skills.md`, aber für
eine ANDERE Distributionslane als `commands`), `.windsurf/workflows/{kd-scout,klickdummy,kd-review}.md`
(Ist-Zustand: KD-Referenz-Schema dreifach dupliziert, PR #965), GitHub Issue #970 (bereits verankerter,
separater Detection-Mechanismus).

**Root-Cause-Tiefe (Step 0 Pflicht):** Vor Konzeption geprüft, ob ein Include/Fragment-Mechanismus
in `cc-skill-dist` bereits existiert — `grep -rn "include|fragment|shared.*doc|canonical.*doc|template"
generate.py doctor.py` → **0 Treffer** (C3). Es existiert **kein** Mechanismus, der dieses Problem
schon löst; das Problem ist real, nicht nur ungefunden.

**Annahme (markiert):** Es wird angenommen, dass zukünftige Skill-Gruppen (nicht nur die
KD-Pipeline) ähnliche Konventions-Duplikate erzeugen werden — das ist die Prämisse für „wieder-
verwendbares Muster", nicht empirisch für einen zweiten Fall belegt (daher Kill-Gate unten).

**Nicht anwendbar:** Genesor-Lifecycle (`pipeline_status`), F11/F17/F18/F19 — dieses Konzept
betrifft `cc-skill-dist`-Distributions-Tooling, keine Klickdummy-Spec/Genesor-Artefakte.

## Annahmen-/Entscheidungs-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|--------------------------|--------|
| L1 | `doctor.py`s Relativlink-Guard verbietet `](pfad/datei.md)`-Links in `commands`-Lane-Quellen | Beobachtung | C1 — Regex `REL_LINK` verifiziert | verifiziert |
| L2 | Ein extrahiertes `docs/conventions/kd-referenz.md`, per Relativ-Link referenziert, würde CI (doctor.py) rot färben | Beobachtung | C1 (Regex matcht `.md`-Pfade mit Slash) | verifiziert |
| L3 | Ein absoluter GitHub-Link wäre zur Laufzeit einer CC-Session nicht ohne `WebFetch` einlösbar — praktisch nutzlos für einen Slash-Command, der selbstständig lauffähig sein soll | Design-Setzung (D) | Alternative: Link akzeptieren + WebFetch-Pflicht dokumentieren (verworfen, s. Alternative B unten) | verifiziert (Konsens dieser Session) |
| L4 | Kein Include/Fragment-Mechanismus existiert aktuell in `generate.py`/`doctor.py` | Beobachtung | C3 — gezielter grep, 0 Treffer | verifiziert |
| L5 | `distribute: false` ist ein bereits etablierter, realer Mechanismus (interne System-Prompt-Workflows) — wiederverwendbar, um eine Fragment-Quelldatei aus der flachen `commands`-Distribution auszunehmen | Beobachtung | C6 — `generate.py:38`, `doctor.py:31`, ≥3 real existierende `distribute:false`-Dateien (`adr-handoff-extern-reviewer*.md`) | verifiziert |
| L6 | ADR-230 hat für eine STRUKTURELL ähnliche Doppelquellen-Lage (`claude-skills.md` ≥4-fach dupliziert) bereits „eine kanonische Kopie + Pointer-Stubs" entschieden — aber für die Policy-Lane, nicht die `commands`-Lane mit ihrem Relativlink-Guard | Beobachtung | C2 — ADR-230 §1.3/§2.4 | verifiziert (Präzedenz ist Analogie, kein direkter Transfer) |
| L7 | Issue #970 (doctor.py-Feldcheck) ist Detection, keine Prevention — löst die Duplikation selbst nicht, macht nur künftige Divergenz sichtbar | Beobachtung | C7 | verifiziert |
| L8 | Ein zweiter realer Bedarfsfall für geteilte Fragmente (jenseits KD-Referenz) ist noch nicht eingetreten | Annahme | Nicht geprüft — Check: `grep`-Audit über alle 69 Workflows auf wiederholte Absatz-Muster >20 Zeilen | offen (H) |

## MVC (konkreter Plan)

1. **Neue Fragment-Quelldatei** `.windsurf/workflows/_shared/kd-referenz-schema.md` mit Frontmatter
   `distribute: false` — Inhalt: die bestehende Step-3.5-Tabelle aus `kd-scout.md` (Spec/Lokal/GitHub/
   iil.pet, `—`+Grund-Regel), textgleich zum heutigen Stand in PR #965.
2. **`generate.py`-Erweiterung:** vor dem Schreiben jeder Ziel-Kopie den Quelltext auf
   `<!-- cc-skill-dist:include <relativer-fragment-pfad> -->` scannen (einfacher Regex, ein
   Include-Level, **keine Verschachtelung** — Risiko R2 unten) und durch den Fragment-Inhalt
   ersetzen, **bevor** `content_hash` berechnet wird (Determinismus bleibt erhalten — gleicher
   `source_commit` ⇒ gleiche aufgelöste Ausgabe).
3. **`doctor.py`-Spiegelung:** dieselbe Resolve-Funktion (aus einem gemeinsamen Modul importiert,
   nicht dupliziert — sonst Risiko R1) nutzen, damit Drift-Vergleich gegen den AUFGELÖSTEN Inhalt
   läuft, nicht gegen den rohen Quelltext mit Include-Marker.
4. **`kd-scout.md`/`klickdummy.md`/`kd-review.md`** auf den Include-Marker umstellen (ersetzt die
   heutige Dreifach-Kopie aus PR #965).
5. **Issue #970 bleibt zusätzlich bestehen** als Backstop — falls ein Autor trotzdem von Hand
   dupliziert statt den Marker zu nutzen (Diabolus-Befund D4 unten), fängt der Feldcheck es trotzdem.

**Bewusst NICHT Teil des MVC:** verschachtelte Includes (Fragment inkludiert Fragment) — Komplexität
ohne belegten Bedarf (L8 offen).

## Befunde-Tabelle (inkl. Diabolus + Alternativen)

| id | Befund | Kategorie | Evidenz | Status |
|----|--------|-----------|---------|--------|
| D1 | **Doppelquellen-Risiko:** entsteht NICHT neu — das Fragment ist die eine Quelle, `distribute:false` verhindert eine zweite sichtbare Kopie im Ziel (L5) | Diabolus | C6 | entkräftet |
| D2 | **Tool-als-Boundary-Risiko:** `generate.py` und `doctor.py` müssen dieselbe Resolve-Logik anwenden — bei Divergenz (z.B. `doctor.py` vergisst die Include-Auflösung) meldet der Drift-Check false-positives/negatives gegen den rohen Marker-Text statt den echten Inhalt | Diabolus | C1+C3 (kein bestehender Shared-Helper) | **Top-Risiko R1** |
| D3 | **Verschachtelungs-/Zyklus-Risiko:** ein Fragment, das ein anderes Fragment inkludiert, kann zyklisch werden | Diabolus | Design-Setzung: MVC verbietet Verschachtelung (Punkt „Bewusst NICHT Teil") | **Top-Risiko R2**, im MVC durch Verbot entschärft |
| D4 | **Manuelle Pflicht ohne Enforcement:** nichts hindert einen Autor daran, trotz vorhandenem Marker weiterhin Text von Hand zu kopieren | Diabolus | — (kein Enforcement in generate.py denkbar, nur Konvention) | **Top-Risiko R3**, durch Issue #970 als Backstop gemildert, nicht eliminiert |
| D5 | **Maintainer-2028:** ein Autor in 2 Jahren sieht `<!-- cc-skill-dist:include … -->` ohne Kontext — Verwechslungsgefahr mit HTML-Kommentaren, die der Skill selbst schon nutzt (z.B. MANAGED-Footer) | Maintainer-2028 | Bestehendes `MANAGED-BY`-Footer-Muster als Präzedenz für HTML-Kommentar-Direktiven in diesen Dateien (C6-Kontext) | gemildert (konsistent mit bestehender Konvention, nicht neuartig) |
| A1 | **Alternative — Status quo + nur Issue #970 (Detection statt Prevention):** kein neuer Mechanismus, volles Risiko der erneuten Duplikation bleibt, aber 0 zusätzliche Tooling-Komplexität | Alternative | C7 | verworfen (löst das eigentliche Duplikations-Problem nicht, nur seine Sichtbarkeit) |
| A2 | **Alternative — Absoluter GitHub-Link statt Include:** `docs/conventions/kd-referenz.md` per `https://github.com/.../blob/main/...`-Link referenzieren | Alternative | L3 | verworfen (zur Laufzeit einer Session ohne `WebFetch`-Zwang nicht einlösbar — Skill wäre nicht mehr self-contained) |

## Top-3-Risiken (aus Befunden)

1. **R1 (D2):** `generate.py`/`doctor.py`-Resolve-Divergenz → **Mitigation:** eine gemeinsame Python-Funktion (z.B. `tools/cc-skill-dist/_resolve.py`), von beiden importiert, kein Copy-Paste der Include-Logik.
2. **R2 (D3):** Zyklische/verschachtelte Includes → **Mitigation:** MVC verbietet Verschachtelung explizit (v1: Fragment darf selbst keinen Include-Marker enthalten, `generate.py` bricht mit Fehler ab, falls doch).
3. **R3 (D4):** Konvention ohne Zwang, Autoren duplizieren trotzdem von Hand → **Mitigation:** Issue #970 bleibt als unabhängiger Feldcheck bestehen (Detection-Backstop), unabhängig davon ob der Include-Mechanismus gebaut wird.

## Kill-Gate

**Threshold:** Bis **2026-10-06** (90 Tage) muss der Include-Mechanismus von **mindestens 2 unabhängigen
Skill-Datei-Gruppen** genutzt werden (die KD-Pipeline zählt als 1). Wird das nicht erreicht, wird
`generate.py`/`doctor.py` wieder auf den Stand ohne Include-Auflösung zurückgebaut — Issue #970s
Feldcheck bleibt dauerhaft der alleinige Schutz gegen diese Klasse von Drift.

## Empfehlung

**T2, empfohlen zur Umsetzung** (nicht in diesem Zyklus zwingend, aber als entscheidungsreifes
Konzept): Baue den Include-Mechanismus als eigenständige Tooling-PR (getrennt von Content-PRs,
`claude-skills.md` F-H), inkl. Round-Trip-Test in `cc-skill-dist-doctor.yml` (Gate-wächst-mit-Konvention,
F-A) — dann `kd-scout.md`/`klickdummy.md`/`kd-review.md` auf den neuen Marker umstellen. Issue #970
bleibt unabhängig davon bestehen. Falls die Umsetzung jetzt nicht priorisiert wird: Konzept-Doc als
`idea` liegen lassen, `review_by` 2026-10-06 markiert es automatisch als überfällig, falls bis dahin
nicht neu bewertet.
