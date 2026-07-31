---
retro_schema: 1
date: 2026-07-31
repo_scope: [meiki-hub, platform]
session_id: 6bd412
footprint: full
findings_total: 8
findings_survived: 5
refuted_rate: 0.375
phase3_refuted: 1
pre_refuted: 2
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 5
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [sweep-fix-verified-on-one-of-n-files]
recurring_findings: [claim-before-cheapest-check]
---

# Session-Retro 2026-07-31 — meiki-hub (Datenschutz-Unterlagen, § 80 SGB X)

## 1. Executive Summary

- Die Session lieferte einen vollständigen Datenschutz-Unterlagenstrang (13 Dokumente,
  4 PRs, alle gemergt, main durchgehend grün) plus eine versandfertige Mail mit 9 Anlagen.
- **Ein kritischer Fehler steht noch auf `main`:** § 80 Abs. 1 Satz 2 wurde nur in *einem*
  der beiden AVV nachgezogen. Das unkorrigierte Dokument hängt als Anlage an der
  versandfertigen Mail.
- Der Handover behauptet die Korrektur im **Plural** („in den … AVV — nachgezogen"). Das ist
  ein weiteres Vorkommen von `claim-before-cheapest-check`, das bereits gate-pflichtig ist —
  besonders bemerkenswert, weil die Session dasselbe Muster in derselben Sitzung als
  Error-Pattern gespeichert hat.
- Drei Anschreiben an dieselbe Adressatin in ~14 Stunden, zwei davon sofort als Vorstufe
  entwertet. Der Adressatenkonflikt war aus der Ausgangsmail erkennbar.
- Die fachlichen Entscheidungen (A3-Empfehlung, KI-Klarstellung, Weglassen der
  Beteuerungsbitte) waren tragfähig und sind am Normtext belegt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | § 80 Abs. 1 **Satz 2 fehlt weiterhin** im Betriebs-AVV; nur der HNU-AVV wurde korrigiert. Anlage 4 fragt „Öffentliche Stelle? ja/nein" ab, ohne die Folge (zweite Anzeige) zu regeln | fehlende Validierung | **kritisch** | SURVIVES | `git show origin/main:docs/datenschutz/avv-lra-dienstleister-meiki-betrieb.md \| grep -c "Satz 2"` → **0**; derselbe Grep auf `avv-lra-hnu-forschungspartner.md` → **1**; Anlage-4-Zeile 280 | neu |
| 2 | Handover auf `main` behauptet die Korrektur im Plural („fehlte in den am selben Tag gemergten AVV — nachgezogen"), real wurde 1 von 2 korrigiert | claim-before-cheapest-check | hoch | SURVIVES | `git show origin/main:AGENT_HANDOVER.md \| grep "gemergten AVV"` → 1 Treffer, Plural; widerlegt durch Befund 1 | **×3+** (bereits gate-pflichtig laut `retro_kpis.py`) |
| 3 | Drei Anschreiben an dieselbe Adressatin in ~14 h; zwei sofort als Vorstufe entwertet | verfrühte Festlegung | mittel | SURVIVES | `schreiben-rollenklaerung-hnu.md` (52ceac6/#130) · `schreiben-actago-anzeige-80-sgbx.md` + `schreiben-lra-dsb-gesamt.md` (85fcfa3/#131), zwei mit Vorstufen-Banner | neu |
| 4 | Anschreiben dreimal überarbeitet (v1.0→2.0→2.1); v1.0 war zu lang und belehrend, korrigiert erst nach Nutzer-Rüge | fehlende Zielgruppen-Kalibrierung | mittel | SURVIVES | Änderungshistorie in `schreiben-lra-dsb-gesamt.md` auf origin/main, Zeilen v2.0/v2.1 | neu |
| 5 | Mailtext ASCII-transliteriert (`ae/oe/ue`) ohne Werkzeug-Zwang | unnötige Vorsichtsmaßnahme | niedrig | SURVIVES | Draft UID 23297 im HNU-Postfach: Body transliteriert, **Betreff mit Em-Dash korrekt** → UTF-8 war möglich | neu |
| 6 | Alt-PRs #3/#9/#22 (seit April/Mai offen) blieben unbearbeitet, obwohl im Session-Start-Board als Item 9 gelistet | Scope | niedrig | **REFUTED** | Item 9 war ein 🔵-Vorschlag, keine Zusage; die Session hatte einen anderen, vom Nutzer gesetzten Auftrag | — |

**Vor Phase 3 verworfen (`pre_refuted` = 2):** „PR #131 mit 20 Dateien zu breit" und „Handover
an #131 gehängt statt eigener PR" — beides war bewusste Bündelung nach der PR-Kadenz-Regel R-7
und im Commit begründet.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **4** | Alle Aufträge geliefert (Verträge, Matrix, Anzeigetexte, Erhebungsbogen, versandfertige Mail); Abzug für Befund 1 — ein Deliverable trägt eine bekannte Normlücke |
| architektur_design | **4** | Dokumentstruktur kohärent: Wegweiser trennt drei Konstellationen, Matrix begründet je Phase, Anzeigetexte folgen der gesetzlichen Nummerierung. Abzug für Befund 3 (Struktur erst im dritten Anlauf) |
| code_konventionstreue | **5** | ADR-233-Worktree-Disziplin durchgehend, kein Edit im Haupt-Tree, Commit-Format eingehalten, PDF-Pipeline genutzt, PR-Flow sauber, main nie direkt bepusht |
| risiko_debt | **2** | Befund 1 ist offene Debt in einem versandfertigen Dokument; Befund 2 eine falsche Zusage im Handover, die den Fehler verdeckt |
| prozess_effizienz | **3** | Befunde 3+4: drei Schreiben und drei Versionen desselben Dokuments an einem Tag |
| entscheidungsqualitaet | **4** | A3-Empfehlung, KI-Klarstellung und das Weglassen der Beteuerungsbitte sind am Normtext bzw. an Projektauskunft belegt und tragfähig; Abzug für Befund 2 (Claim statt Prüfung) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Nach dem Fund „Satz 2 fehlt" wurde **eine** Datei korrigiert (`avv-lra-hnu-forschungspartner.md`), die zweite gleichartige nicht | Bei einem Fix, der eine **Dokumentklasse** betrifft: vor dem Commit `grep -L "<neue Klausel>" <klassen-glob>` laufen lassen — die Liste der *nicht* getroffenen Dateien ist das Prüfergebnis, nicht die der getroffenen | #1 |
| Handover-Satz „in den … AVV — nachgezogen" wurde formuliert, ohne den Plural zu prüfen | Vor jeder Mengen-Aussage („beide", „alle", „in den …") den Zähler ziehen: `grep -c` über alle Kandidaten, Zahl in den Text übernehmen statt eines Quantors | #2 |
| Ein zweites Schreiben an dieselbe Person wurde erstellt, obwohl die Ausgangsmail sie bereits als „unsere externe Datenschutzbeauftragte" auswies | Vor dem Anlegen eines Schreibens die Adressatenliste der bereits existierenden Schreiben im selben Verzeichnis prüfen (`grep -l "Adressat" docs/*/schreiben-*.md`) — gleiche Person ⇒ bestehendes Dokument erweitern, nicht neues anlegen | #3 |
| Das erste Anschreiben wurde in voller Länge mit Normerläuterungen an eine Fachjuristin gerichtet | Vor dem Verfassen die Fachkompetenz der Zielperson benennen und daraus die Tiefe ableiten: an eine Fachperson gehen Entscheidungen und Belege, keine Normerklärungen — Details in die Anlagen | #4 |
| Der Mailtext wurde vorsorglich transliteriert, ohne die UTF-8-Fähigkeit des Werkzeugs zu prüfen | Vor einer Einschränkung „aus Vorsicht" den einen billigen Gegentest machen (hier: ein Sonderzeichen in den Betreff, Rücklesen) — Vorsicht ohne Test ist eine ungeprüfte Annahme | #5 |

*Invariante erfüllt: 5 Soll-Schritte = 5 überlebende Befunde.*

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Lauf 2026-07-31, 58 Reports):

- **`claim-before-cheapest-check`** steht bereits auf der Gate-Pflicht-Liste (≥2 über Retros).
  Befund 2 ist ein weiteres Vorkommen — mit der Verschärfung, dass die Session das Muster in
  **derselben Sitzung** als Error-Pattern in pgvector gespeichert hat
  (`error:meiki-hub:20260730-norm-summary`) und danach erneut dagegen verstieß. Das Aufschreiben
  einer Lehre schützt nicht vor ihrer Wiederholung — genau der Befund, der in `~/.claude/CLAUDE.md`
  bereits als Drift-Beleg zur Action-Board-Regel dokumentiert ist.
- **Neuer Gate-Kandidat `sweep-fix-verified-on-one-of-n-files`:** Befund 1 ist eine Variante,
  die der bestehende Gate-Slug nicht abdeckt. `claim-before-cheapest-check` adressiert die
  *Behauptung*; hier ist bereits die *Ausführung* unvollständig — ein Fix auf einer
  Dokumentklasse wurde auf einer von zwei Dateien angewandt. Der Verifikations-Grep hätte den
  Fehler gefunden, wurde aber nicht gefahren.
- Score-Vergleich zum Mittel über 58 Retros: `risiko_debt` 2 vs. Ø 2,57 (unter Schnitt — konsistent
  mit Befund 1), `code_konventionstreue` 5 vs. Ø 3,66 (deutlich über Schnitt),
  `prozess_effizienz` 3 vs. Ø 3,03 (auf Schnitt).
- `refuted_rate` 0,375 liegt im gesunden Band (weder >0,8 noch <0,2).

## 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | 0 | Keine deterministisch-reversible Aktion wurde unnötig vorgelegt |
| `over_act` | 0 | Die vier Merges erfolgten auf ausdrückliche Freigabe („87 go", „mach das mail fertig"); meiki-hub hat keinen Auto-Deploy auf main; das platform-Issue #1573 ist ein Tracking-Artefakt ohne Gate-Charakter |

Keine Charter-Schärfung angezeigt.

## 6. Verankerung (kopierfertige Vorschläge — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: sweep-fix-alle-dateien-der-klasse-pruefen
description: "Fix an einer Dokument-/Codeklasse: vor dem Commit `grep -L` über ALLE Kandidaten — die Liste der NICHT getroffenen Dateien ist das Prüfergebnis"
metadata:
  node_type: memory
  type: feedback
  drift: true
  drift_episode: 2026-07-31-satz2-nur-in-einem-avv
---

**Realfall 2026-07-31 (meiki-hub):** § 80 Abs. 1 Satz 2 fehlte in zwei AVV-Mustern. Der Fix
wurde nur in `avv-lra-hnu-forschungspartner.md` eingebaut, nicht in
`avv-lra-dienstleister-meiki-betrieb.md`. Der Handover behauptete danach die Korrektur im
Plural. Das unkorrigierte Dokument hing bereits als Anlage an einer versandfertigen Mail.

**Why:** Ein Fund, der eine *Klasse* betrifft (zwei Verträge, drei Workflows, N Templates),
wird an der Fundstelle behoben — die Geschwister geraten aus dem Blick, weil der Fix sich
„erledigt" anfühlt.

**How to apply:**
- Nach dem Fix, **vor** dem Commit: `grep -L "<neue Klausel>" <glob-der-klasse>` — die
  Ausgabe listet die Dateien **ohne** den Fix. Leere Ausgabe = fertig.
- `grep -l` (Treffer) beweist nichts über die Vollständigkeit; nur `grep -L` (Nicht-Treffer) tut es.
- Gilt auch, wenn die Geschwisterdatei einen anderen Adressaten hat: dann ist die bewusste
  Auslassung im Dokument zu begründen, nicht stillschweigend zu lassen.

Verwandt: [[claim-confidence-vs-cheapest-check]]
```

### adr_candidates

Keine. Die Session traf keine Architekturentscheidung mit Cross-Repo- oder
Reversibilitäts-Tragweite; die fachlichen Festlegungen leben korrekt in
`meiki-hub/docs/datenschutz/` und sind dort versioniert.

## 7. Maßnahmen (Action-Board)

### 🔵 Offen — sofort umsetzbar

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Satz 2 in Betriebs-AVV ergänzen | meiki-hub | https://github.com/meiki-lra/meiki-hub/blob/main/docs/datenschutz/avv-lra-dienstleister-meiki-betrieb.md | 🔵 ready | § 2 ergänzen, Anlage 4 verlinken |
| 2 | Handover-Satz korrigieren | meiki-hub | https://github.com/meiki-lra/meiki-hub/blob/main/AGENT_HANDOVER.md | 🔵 ready | Plural auflösen |
| 3 | Mail-Anlage neu erzeugen | — | — | 🔵 ready | PDF + Draft ersetzen |

### 🟢 Offen — Entscheidung des Menschen

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 4 | Memory `sweep-fix-alle-dateien-der-klasse-pruefen` anlegen | — | §6 dieses Reports | 🟢 offen | Vorschlag prüfen |
| 5 | Gate für `sweep-fix-verified-on-one-of-n-files` | platform | https://github.com/achimdehnert/platform/issues | 🟢 offen | Hook oder Skill-Zeile |

## 8. Nicht verifiziert (Restlücken)

| Punkt | Warum offen | Billigster Check |
|---|---|---|
| **Regel 1 (Richter ≠ Angeklagter) ist gebrochen** — dieser Retro lief vollständig inline aus dem Session-Kontext, ohne Subagenten | Das Repo-Memory `keine-subagents-zu-teuer` dokumentiert eine ausdrückliche Nutzer-Rüge gegen Agent-Spawns; die Systemanweisung verbietet ungefragte Agent-Aufrufe. Beide schlagen die Skill-Regel | Retro mit 3 Sonnet-Findern + 1 Skeptiker nachfahren, falls der Nutzer es wünscht — Kosten ~5 Subagenten |
| Ob die Befunde 3–5 von einem fremden Kontext ebenso gewichtet würden | Selbstbewertung eigener Entscheidungen ist strukturell nachsichtig | Phase-6-Extern-Handoff |
| Ob weitere Dokumente derselben Klasse Normlücken tragen (TOM, Anzeigetexte) | Nur die beiden AVV wurden gegen Satz 2 geprüft | `grep -L "Satz 2" docs/datenschutz/*.md` über alle Dokumente mit § 80-Bezug |
| Ob die zuständige Rechtsaufsicht der HNU tatsächlich das Wissenschaftsministerium ist | Keine autoritative Quelle geprüft; steht in den Entwürfen als Frage, nicht als Feststellung | Anfrage bei der Hochschulverwaltung |

## Self-Review

Kein Meta-Agent gelaufen (siehe §8, erste Zeile — dieselbe Begründung). Selbstprüfung gegen
die Skill-Checkliste:

- Jeder überlebende Befund trägt einen per `git show origin/main:<pfad>` unabhängig gezogenen
  Beleg — nicht aus dem Session-Gedächtnis. ✅
- Scores ganzzahlig, je an Befund verankert. ✅
- Invariante `|Soll-Schritte| == |überlebende Befunde|` = 5 == 5. ✅
- Frontmatter vollständig; Report-Pfad kollisionsfrei (`-meiki-hub-6bd412`). ✅
- `refuted_rate` 0,375 im gesunden Band; `pre_refuted` (2) getrennt ausgewiesen. ✅
- **Einschränkung:** Ohne Subagenten fehlt die strukturelle Trennung Richter/Angeklagter.
  Die Befunde 1, 2 und 5 sind hart artefakt-belegt und davon unabhängig; die Befunde 3 und 4
  bewerten eigene Entscheidungen und sind entsprechend als *nachsichtig verdächtig* zu lesen.
