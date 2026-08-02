---
retro_schema: 1
date: 2026-07-31
repo_scope: [meiki-hub, platform]
session_id: 6bd412
footprint: full
findings_total: 9
findings_survived: 4
refuted_rate: 0.556
phase3_refuted: 3
pre_refuted: 2
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 5
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [sweep-fix-verified-on-one-of-n-files]
recurring_findings: [claim-before-cheapest-check]
---

# Session-Retro 2026-07-31 — meiki-hub (Datenschutz-Unterlagen, § 80 SGB X)

## 1. Executive Summary

- Die Session lieferte einen vollständigen Datenschutz-Unterlagenstrang (13 Dokumente,
  4 PRs, alle gemergt, main durchgehend grün) plus eine versandfertige Mail mit 9 Anlagen.
- **Zwei Lücken in versandfertigen Dokumenten**, beide erst nach der Session gefunden:
  § 80 Abs. 1 Satz 2 fehlte in einem der beiden AVV, und die Konsolidierung der DSB-Schreiben
  ließ das Landratsamt Traunstein stillschweigend fallen.
- Der Handover behauptete die AVV-Korrektur im **Plural**. Das ist ein weiteres Vorkommen von
  `claim-before-cheapest-check`, das bereits gate-pflichtig ist — besonders bemerkenswert,
  weil die Session dasselbe Muster in derselben Sitzung als Error-Pattern gespeichert hat.
- **Zwei eigene Befunde hielten der Falsifikation nicht stand.** Ein nachgelagerter
  Skeptiker-Pass (zwei Sonnet-Subagenten, ~115k Tokens) widerlegte die Befunde zu Rework und
  Dokumentversionen und fand stattdessen die Traunstein-Lücke. Details in § Self-Review.
- Die fachlichen Entscheidungen (A3-Empfehlung, KI-Klarstellung, Weglassen der
  Beteuerungsbitte) waren tragfähig und sind am Normtext belegt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | § 80 Abs. 1 **Satz 2 fehlt weiterhin** im Betriebs-AVV; nur der HNU-AVV wurde korrigiert. Anlage 4 fragt „Öffentliche Stelle? ja/nein" ab, ohne die Folge (zweite Anzeige) zu regeln | fehlende Validierung | **kritisch** | SURVIVES | `git show origin/main:docs/datenschutz/avv-lra-dienstleister-meiki-betrieb.md \| grep -c "Satz 2"` → **0**; derselbe Grep auf `avv-lra-hnu-forschungspartner.md` → **1**; Anlage-4-Zeile 280 | neu |
| 2 | Handover auf `main` behauptet die Korrektur im Plural („fehlte in den am selben Tag gemergten AVV — nachgezogen"), real wurde 1 von 2 korrigiert | claim-before-cheapest-check | hoch | SURVIVES | `git show origin/main:AGENT_HANDOVER.md \| grep "gemergten AVV"` → 1 Treffer, Plural; widerlegt durch Befund 1 | **×3+** (bereits gate-pflichtig laut `retro_kpis.py`) |
| 3 | Drei Anschreiben an dieselbe Adressatin in ~14 h; zwei sofort als Vorstufe entwertet | verfrühte Festlegung | mittel | **REFUTED** | Prämisse falsch: `schreiben-rollenklaerung-hnu.md` adressiert die DSB **beider** Landratsämter („Adressaten: … ⟨Günzburg⟩ und ⟨Traunstein⟩"), nicht dieselbe Person wie die anderen zwei. Damit fällt auch die Vermeidbarkeits-These | — |
| 4 | Anschreiben dreimal überarbeitet (v1.0→2.0→2.1); v1.0 war zu lang und belehrend | fehlende Zielgruppen-Kalibrierung | mittel | **REFUTED** | v1.0 existiert nie als Commit — nur als Selbstauskunft in der Änderungshistorie desselben Erst-Commits (85fcfa3 führt die Datei bereits als v2.0 ein), also unbelegbar. v2.1 ist eine Scope-Änderung auf Nutzerwunsch (Frage gestrichen), keine Kalibrierungskorrektur | — |
| 7 | **Ersetzt-Vermerk ohne Abgleich der Adressatenmengen:** `schreiben-lra-dsb-gesamt.md` führt „Ersetzt: `schreiben-rollenklaerung-hnu.md`", adressiert aber nur Günzburg, während die Vorstufe beide Pilot-Landratsämter ansprach | fehlende Validierung | mittel | SURVIVES | `grep -ci traunstein` auf der damaligen Fassung → **0**. Gefunden vom Skeptiker zu Befund 3. **Severity von *hoch* auf *mittel* korrigiert:** die Projektauskunft vom selben Tag ergab, dass Projekt 2 (der einzige Anzeigefall) ohnehin für beide Häuser gilt — Traunstein ist über den Verteiler abgedeckt, es fehlte die *Kennzeichnung*, nicht die Sache | neu |
| 5 | Mailtext ASCII-transliteriert (`ae/oe/ue`) ohne Werkzeug-Zwang | unnötige Vorsichtsmaßnahme | niedrig | SURVIVES | Draft UID 23297 im HNU-Postfach: Body transliteriert, **Betreff mit Em-Dash korrekt** → UTF-8 war möglich | neu |
| 6 | Alt-PRs #3/#9/#22 (seit April/Mai offen) blieben unbearbeitet, obwohl im Session-Start-Board als Item 9 gelistet | Scope | niedrig | **REFUTED** | Item 9 war ein 🔵-Vorschlag, keine Zusage; die Session hatte einen anderen, vom Nutzer gesetzten Auftrag | — |

**Vor Phase 3 verworfen (`pre_refuted` = 2):** „PR #131 mit 20 Dateien zu breit" und „Handover
an #131 gehängt statt eigener PR" — beides war bewusste Bündelung nach der PR-Kadenz-Regel R-7
und im Commit begründet.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **3** | Alle Aufträge geliefert (Verträge, Matrix, Anzeigetexte, Erhebungsbogen, versandfertige Mail), aber **zwei** versandfertige Dokumente trugen Lücken (Befunde 1 und 7), beide erst nachträglich gefunden |
| architektur_design | **4** | Dokumentstruktur kohärent: Wegweiser trennt drei Konstellationen, Matrix begründet je Phase, Anzeigetexte folgen der gesetzlichen Nummerierung. Abzug für Befund 3 (Struktur erst im dritten Anlauf) |
| code_konventionstreue | **5** | ADR-233-Worktree-Disziplin durchgehend, kein Edit im Haupt-Tree, Commit-Format eingehalten, PDF-Pipeline genutzt, PR-Flow sauber, main nie direkt bepusht |
| risiko_debt | **2** | Befund 1 ist offene Debt in einem versandfertigen Dokument; Befund 2 eine falsche Zusage im Handover, die den Fehler verdeckt |
| prozess_effizienz | **4** | Nach der Widerlegung von Befund 3+4 bleibt kein belegtes Rework — der Dokumentbestand wuchs mit dem Erkenntnisstand. Abzug, weil die Konsolidierung selbst einen Fehler einführte (Befund 7) |
| entscheidungsqualitaet | **4** | A3-Empfehlung, KI-Klarstellung und das Weglassen der Beteuerungsbitte sind am Normtext bzw. an Projektauskunft belegt und tragfähig; Abzug für Befund 2 (Claim statt Prüfung) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Nach dem Fund „Satz 2 fehlt" wurde **eine** Datei korrigiert (`avv-lra-hnu-forschungspartner.md`), die zweite gleichartige nicht | Bei einem Fix, der eine **Dokumentklasse** betrifft: vor dem Commit `grep -L "<neue Klausel>" <klassen-glob>` laufen lassen — die Liste der *nicht* getroffenen Dateien ist das Prüfergebnis, nicht die der getroffenen | #1 |
| Handover-Satz „in den … AVV — nachgezogen" wurde formuliert, ohne den Plural zu prüfen | Vor jeder Mengen-Aussage („beide", „alle", „in den …") den Zähler ziehen: `grep -c` über alle Kandidaten, Zahl in den Text übernehmen statt eines Quantors | #2 |
| Ein Dokument wurde als „Ersetzt: X" gekennzeichnet, ohne die **Adressatenmengen** von X und dem Nachfolger zu vergleichen — X adressierte zwei Häuser, der Nachfolger eines | Vor jedem „ersetzt/abgelöst durch"-Vermerk die Adressatenzeilen beider Dokumente nebeneinanderlegen (`grep -i "Adressat" <alt> <neu>`). Ist die Menge im Nachfolger kleiner, muss der Vermerk den Geltungsbereich benennen — ein pauschales „ersetzt" lässt den Rest stillschweigend fallen | #7 |
| Der Mailtext wurde vorsorglich transliteriert, ohne die UTF-8-Fähigkeit des Werkzeugs zu prüfen | Vor einer Einschränkung „aus Vorsicht" den einen billigen Gegentest machen (hier: ein Sonderzeichen in den Betreff, Rücklesen) — Vorsicht ohne Test ist eine ungeprüfte Annahme | #5 |

*Invariante erfüllt: 4 Soll-Schritte = 4 überlebende Befunde (1, 2, 5, 7).*

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
| 1 | Satz 2 in Betriebs-AVV ergänzt | meiki-hub | https://github.com/meiki-lra/meiki-hub/pull/133 | ✅ done | gemergt `c55f7d6` |
| 2 | Handover-Satz korrigiert | meiki-hub | https://github.com/meiki-lra/meiki-hub/pull/133 | ✅ done | Plural aufgelöst |
| 3 | Mail-Anlage neu erzeugt | — | Draft UID 23300 | ✅ done | PDFs + Draft ersetzt |
| 6 | Traunstein-Lücke schließen (Befund 7) | meiki-hub | https://github.com/meiki-lra/meiki-hub/pull/134 | 🔵 ready | PR mergen |

### 🟢 Offen — Entscheidung des Menschen

| # | Item | Repo | PR/Issue | Status | Next Step |
|---|---|---|---|---|---|
| 4 | Memory `sweep-fix-alle-dateien-der-klasse-pruefen` anlegen | — | §6 dieses Reports | 🟢 offen | Vorschlag prüfen |
| 5 | Gate für `sweep-fix-verified-on-one-of-n-files` | platform | https://github.com/achimdehnert/platform/issues | 🟢 offen | Hook oder Skill-Zeile |

## 8. Nicht verifiziert (Restlücken)

| Punkt | Warum offen | Billigster Check |
|---|---|---|
| **Regel 1 (Richter ≠ Angeklagter) war in der Find-Phase gebrochen** — die Befunde entstanden inline aus dem Session-Kontext | Das Repo-Memory `keine-subagents-zu-teuer` + die Systemanweisung schlagen die Skill-Regel; der Nutzer gab den Skeptiker-Pass erst nachträglich frei | **teilweise geschlossen:** nachgelagerter Zwei-Skeptiker-Pass auf die Bewertungsbefunde (§ Self-Review). Offen bleibt die Find-Phase — ein fremder Finder hätte womöglich weitere Befunde erzeugt, die hier gar nicht auftauchen |
| Ob ein fremder Kontext die Befunde 1, 2 und 5 ebenso gewichten würde | Der Skeptiker-Pass prüfte nur 3 und 4; die kommandobelegten Befunde blieben ungeprüft | Zwei weitere Skeptiker (~110k) — Nutzen fraglich, da die Belege Kommandoergebnisse sind |
| Ob weitere „ersetzt/abgelöst"-Vermerke im Repo denselben Adressaten-Bruch tragen wie Befund 7 | Nur `docs/datenschutz/` wurde geprüft | `grep -rn "Ersetzt" docs/ --include=*.md` und je Treffer die Adressatenzeilen vergleichen |
| Ob weitere Dokumente derselben Klasse Normlücken tragen (TOM, Anzeigetexte) | Nur die beiden AVV wurden gegen Satz 2 geprüft | `grep -L "Satz 2" docs/datenschutz/*.md` über alle Dokumente mit § 80-Bezug |
| Ob die zuständige Rechtsaufsicht der HNU tatsächlich das Wissenschaftsministerium ist | Keine autoritative Quelle geprüft; steht in den Entwürfen als Frage, nicht als Feststellung | Anfrage bei der Hochschulverwaltung |

## Self-Review

Selbstprüfung gegen die Skill-Checkliste:

- Jeder überlebende Befund trägt einen per `git show origin/main:<pfad>` unabhängig gezogenen
  Beleg — nicht aus dem Session-Gedächtnis. ✅
- Scores ganzzahlig, je an Befund verankert. ✅
- Invariante `|Soll-Schritte| == |überlebende Befunde|` = 4 == 4. ✅
- Frontmatter vollständig; Report-Pfad kollisionsfrei (`-meiki-hub-6bd412`). ✅
- `refuted_rate` 0,556 im gesunden Band; `pre_refuted` (2) getrennt ausgewiesen. Echte
  Falsifikationsquote `phase3_refuted/(total − pre_refuted)` = 3/7 = 0,43. ✅

### Nachgelagerter Skeptiker-Pass — was er kostete und was er brachte

Die erste Fassung dieses Reports lief **ohne Subagenten** (Repo-Memory `keine-subagents-zu-teuer`
+ Systemanweisung schlagen die Skill-Regel) und wies das als Einschränkung aus: die Befunde 3
und 4 bewerteten eigene Entscheidungen und seien „nachsichtig verdächtig". Auf Nutzer-Freigabe
lief danach ein gezielter Pass — **zwei Sonnet-Skeptiker, je ein Befund, benannte Dateien,
kein Repo-Sweep**.

| | Ergebnis |
|---|---|
| Kosten | ~115.000 Tokens (61.976 + 52.752), 6 Tool-Calls je Agent |
| Befund 3 | REFUTED — Prämisse „dieselbe Adressatin" faktisch falsch |
| Befund 4 | REFUTED — v1.0 nie committet, v2.1 keine Korrektur |
| Neu gefunden | Befund 7 (Traunstein-Lücke), Severity hoch |

**Methodisch wichtig:** Der Verdacht war richtig, aber die *Richtung* falsch. Erwartet wurde
Nachsicht gegenüber eigenen Entscheidungen; tatsächlich waren beide Befunde zu **streng** —
schlecht belegte Selbstanklagen. Einer davon stützte sich auf eine Versionsangabe, die ich
selbst geschrieben hatte, ohne verifizierbares Artefakt dahinter.

**Zur Kostenschätzung:** Vor dem Lauf wurde geschätzt, zwei eng geführte Skeptiker lägen
„deutlich unter" den 126k des gerügten Drei-Agenten-Laufs. Real: 115k — knapp darunter. Die
Schätzung war zu optimistisch; für künftige Abwägungen ist **~55k pro eng geführtem Skeptiker**
die gemessene Größenordnung.

**Nachtrag: die Reparatur überschoss.** Aus Befund 7 wurde zunächst die Konsequenz gezogen,
Traunstein brauche ein **eigenes Schreiben** — formuliert, ohne den Projektzuschnitt zu
kennen. Die Rückfrage bei der Projektleitung ergab: Projekt 1 ist für Traunstein separat und
ohnehin nicht anzeigepflichtig, Projekt 2 gilt gemeinsam für beide Häuser. Richtig ist
deshalb eine **Kopie im Verteiler**, kein zweites Schreiben. Derselbe Fehlertyp wie in den
Befunden 3 und 4: aus einer real erkannten Lücke eine zu weit reichende Folgerung ziehen,
bevor die Faktenlage steht. Ein Skeptiker findet die Lücke — er ersetzt nicht die Rückfrage
zur Konsequenz.

**Wo der fremde Kontext wirkte und wo nicht:** Die Befunde 1, 2 und 5 sind kommandobelegt
(`grep -c`, Textvergleich, Draft-Feld) — ein Subagent hätte sie identisch gefunden, ohne
Mehrwert. Der Ertrag lag ausschließlich bei den Bewertungsbefunden und dem daraus
entstandenen Fund 7. Das ist ein verwertbares Auswahlkriterium: **Skeptiker auf
Bewertungsbefunde ansetzen, nicht auf artefakt-belegte.**
