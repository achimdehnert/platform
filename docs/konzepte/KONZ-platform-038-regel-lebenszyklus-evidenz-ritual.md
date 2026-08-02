---
concept_id: KONZ-platform-038
title: Regel-Lebenszyklus mit erzwungenem Evidenz-Ritual (Lotse-Ausbau)
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []        # Governance-Konzept, keine App-Spec (ADR-211 nicht berührt)
adr_threshold: org-weiter ADR — aber erst NACH 3 überlebten Ritual-Zyklen (sonst kein ADR)
review_by: 2026-08-31
kill_criteria: "K1–K4 in §13; hart: 2 verpasste Ritual-Fenster in Folge ⇒ Status stale"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: tools/retro_kpis.py, commit_or_pr: d5824acb, opened_in_session: true}   # Verstoß-Matrix 63 Retros, Lauf 2026-08-02
  - {claim_id: C2, source_path: "~/.claude/hooks/ + ~/.claude/settings.json", commit_or_pr: "maschinen-lokal (teilw. git-getrackt, 43d8eaa2)", opened_in_session: true}
  - {claim_id: C3, source_path: "platform#705, #1182–#1191, #1631–#1638", commit_or_pr: "gh issue list 2026-08-02", opened_in_session: true}
  - {claim_id: C4, source_path: ".windsurf/workflows/ (git log origin/main)", commit_or_pr: d5824acb, opened_in_session: true}   # 55 Skills, +14 Juli
  - {claim_id: C5, source_path: "~/.claude/projects/*/memory/MEMORY.md", commit_or_pr: "grep-Zählung 2026-08-02", opened_in_session: true}   # ~730 Einträge, ~52% Drift
  - {claim_id: C6, source_path: "~/.claude/hooks/evidence_claim_scanner.py (Kopf gelesen)", commit_or_pr: "Stop-Hook feuerte live in dieser Session", opened_in_session: true}
  - {claim_id: C7, source_path: "retro_kpis-Output: 3 Parse-Artefakte aus Retro a50bc6", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}
created: 2026-08-02
---

# KONZ-platform-038 — Regel-Lebenszyklus mit erzwungenem Evidenz-Ritual

**Tier-Entscheidung: T3** — org-weit (alle 3 Orgs), neue Boundary (Regel-Lebenszyklus),
persistente Artefakte, berührt den Security-Perimeter (Gates). Auto-Eskalation greift mehrfach;
keine Selbsteinstufungs-Frage.

## 1 Executive Summary

**Basis:** 55 Skills, 12 Policies, ~730 Memory-Regeln (52 % Drift-Lehren) — und trotzdem 18
gate-pflichtige Wiederholungs-Verstöße, Spitze ×34, unter dem aktuellen Modell (C1, C4, C5).
0/18 Gates fertig; für ~5 Slugs existiert Enforcement, das nachweislich feuert und trotzdem
nicht verhindert (C2, C6). **Analyse:** Der Engpass ist weder Regelmangel noch Modellschwäche,
sondern (a) fehlende Konversion Regel→wirksames Enforcement und (b) fehlender Rückbau-Pfad —
die Ratsche kennt nur eine Richtung. **Fazit:** Gebraucht wird ein geschlossener Regelkreis:
klassifizieren → wirksam durchsetzen (mit Wirksamkeits-Beweis) → messen (erzwungen, 14-Tage) →
zurückbauen (evidenzbasiert). **Handlungsempfehlung:** Welle-1-Gates bauen (Reconcile+Drill,
§12 D2), Ritual per Cron erzwingen (D3), Klassifikation in die Regel-Quellen schreiben (D4) —
Entscheidungen ungebündelt in §12.

## 2 Scope & Evidenzbasis

Scope: alle 3 Orgs (achimdehnert, ttz-lif, meiki-lra); Gov-Detailbefunde bleiben in den
Gov-Repos. Evidenz: siehe `evidence_manifest` (alle Quellen in der Session vom 2026-08-02
geöffnet/ausgeführt); Zusammenfassung im Phase-1-Report (`~/.claude/boards/
lotse-phase1-bestandsaufnahme.md`, via Loopback-Dienst lesbar). Nicht verifiziert:
Retro-Abdeckungsquote (wie viele Sessions OHNE Retro enden) — billigster Check: Session-Count
aus `~/.claude/projects/*` gegen Retro-Count je 14-Tage-Fenster (erste Ritual-Aufgabe).

## 3 Infrastruktur-Fit (SSoT-Prüfung)

Wiederverwendet, nichts Neues erfunden: `retro_kpis.py` (Sensor + `--file-issues`),
Hook-Schichten (PreToolUse/Stop/SessionStart), `cc-skill-dist` (Verteilung), KONZ-Lifecycle
(dieses Doc), `autonomy-gates.md` (Freigabe-Rahmen), Lotsen-Charta (Selbstbetroffenheits-Regel).
**Keine vierte Wahrheit:** A/B/C-Label leben IN der jeweiligen Regel-Quelle
(Memory-Frontmatter, Policy-Frontmatter), nie in einer Separatliste (§6 AD-3). Einziges neues
Artefakt: ein append-only Sunset-Ledger (`docs/governance/sunset-ledger.md`) — Ereignis-Log,
keine Regel-Quelle, daher keine SSoT-Kollision.

## 4 Steelman (Synthese des unabhängigen Reviews)

Das Konzept ist der erste Vorschlag, der die Regel-**Produktion** selbst unter Evidenzpflicht
stellt und einen Abbaupfad definiert — es ersetzt „Fehler → neue Regel → Hoffnung" durch einen
falsifizierbaren Regelkreis. Stärkste Stützen: (a) die quantifizierte Enforcement-Lücke
(0/18, risiko_debt 2.54 als schwächste Score-Dimension), (b) „Reconcile vor Neubau" ist durch
die Hook-Inventur direkt begründet (sonst entstehen 18 neue Gates neben 5 wirkungslosen alten),
(c) der Modellwechsel-Trigger ist geerdet (52 % Drift-Lehren unbekannten Verfallsdatums bei
~3-monatigen Modellwechseln). Ehrliche Grenze: Das Konzept baut selbst kein Gate und erklärt
nicht abschließend, ob der Top-Slug überhaupt vollständig hookbar ist (§7).

## 5 Konzeptdefinition

### 5.1 Klassifikation A/B/C — in der Regel-Quelle
Jede Regel erhält in ihrer Quelle (Memory-/Policy-Frontmatter): `rule_class: A|B|C`,
`assessed_with: <model-id>`, `reassess_by: <Datum>`.
**A** = Modell-Schwäche-Kompensation → sunset-fähig. **B** = Org-Präferenz → modell-unabhängig,
bleibt. **C** = Irreversibilitäts-/Security-Gate → bleibt unabhängig von Modellgüte; nie
sunset-fähig. Grenzfälle A/C werden als C geführt (konservativ).

### 5.2 Gate-Bau: Reconcile → Drill → Bau
Reihenfolge nach Verstoßzähler × Schadensklasse. Pro Slug PFLICHT-Sequenz:
1. **Reconcile:** Was existiert schon (Hook/CI/Skill-Phase)? Warum wirkt es nicht
   (advisory statt blockierend? falscher Zeitpunkt im Ablauf? Coverage-Lücke?).
2. **Drill:** provozierter Verstoß muss nachweislich blocken/melden („Rückspielprobe").
   **Ein Gate ohne bestandenen Drill gilt als NICHT gebaut** (§13 K4).
3. **Bau/Härtung** mit expliziter Einstufung `blocking | advisory` im Gate-Header.
Hooks werden git-getrackt (platform) verteilt, nicht nur maschinen-lokal gepflegt (§6 M-2).

### 5.3 14-Tage-Ritual — erzwungen, nicht vorgenommen
Cron-Trigger (2. + 16. des Monats), NICHT Vorsatz (§6 AD-1). Inhalt je Lauf:
`retro_kpis`-Delta; neue Slugs ≥2 → Issue via `--file-issues`; Gate-Backlog-Stand;
Sunset-Prüfung (§5.4). **Input-Bedingung:** ≥8 Retros im Fenster, sonst Ergebnis
„nicht bewertbar" (zählt nie als „stagniert/sauber", §6 AD-6/M-7). **Ausfallregel:** 2
verpasste Fenster in Folge ⇒ Konzept-Status automatisch → `stale` + Issue (§6 M-3).
1-Seiten-Runbook, damit jeder Dritte den Lauf fahren kann.

### 5.4 Sunset — Abwesenheit reicht nicht
Typ-A-Regel wird Sunset-Kandidat erst bei: 2 aufeinanderfolgende saubere Fenster **UND**
≥5 Exposures (Situationen, in denen die Regel hätte greifen können — Exposure-Nenner statt
Kalenderzeit, §6 AD-4). Dann kontrollierter Auslass-Test (Regel suspendiert, Beobachtung 1
Fenster). Jede Rücknahme = realer Schadensfall, wird im Sunset-Ledger geführt (append-only).

### 5.5 Skills-Nachrang mit Zaun
Solange die Welle-1-Gates (D2) nicht Drill-bestanden sind: keine neuen Skill-PRs außer mit
wörtlichem Owner-Override (der geloggt wird). Enforcement ehrlich benannt: Stufe 1 =
Review-Checkliste (Review-Gate, kein Exit-Code); Stufe 2 (nach Welle 1) = CI-Check
„Skill-Datei neu + Gate-Backlog-Top-5 offen → rot". Bis Stufe 2 existiert, ist dieser Zaun
formal umgehbar (§6 AD-5/M-4) — bewusste Übergangs-Schwäche, befristet bis 2026-09-13.

### 5.6 Modellwechsel-Trigger — event-basiert
SessionStart-Hook vergleicht aktuelle Modell-ID gegen `~/.claude/hooks/state/model-id`;
bei Änderung: Hinweis + Smoke-Kalibrier-Suite (kleine Aufgaben mit bekannter Antwort) +
Re-Assessment-Pflicht aller A-Labels (`assessed_with` veraltet). Kein Kalender-Raten (§6 M-6).

## 6 Adversariale Analyse (3 unabhängige Agenten, sahen einander nicht)

Einwände vollständig übernommen und in §5 eingebaut:

| ID | Einwand (Kurz) | Antwort im Konzept |
|---|---|---|
| AD-1 | Ritual = Merksatz, Selbstwiderspruch | Cron-Zwang + Ausfall-Flip auf `stale` (§5.3) |
| AD-2 | „Gates senken Zähler" falsifiziert (Hook feuert, ×34 trotzdem) | blocking/advisory-Pflicht + Drill; Diagnose §7 |
| AD-3 | A/B/C = vierte Wahrheit | Labels in Regel-Quelle, keine Separatliste (§5.1) |
| AD-4 | Sunset misst Abwesenheit | Exposure-Nenner ≥5 (§5.4) |
| AD-5 | „Skills nachrangig" umgehbar | Zaun + Override-Log; Übergangs-Schwäche befristet (§5.5) |
| AD-6 | Zirkuläre Messbasis (Retro-Selbstauskunft) | Input-Bedingung + Abdeckungs-Messung (§2, §5.3) |
| AD-7 | Kill-Schwellen bei kleinem N Rauschen | Mindest-N (K3: N≥5) + „nicht bewertbar"-Zustand |
| M-1 | KPI-Parser einziger Sensor, drift-anfällig | Golden-Fixture-Test + Fail-on-unknown (D6); Beleg C7 |
| M-2 | Enforcement maschinen-lokal | Hooks git-getrackt verteilen (§5.2); teils schon so (43d8eaa2) |
| M-3 | Single-Owner-Ritual ohne Ausfallregel | Ausfall-Flip + Runbook (§5.3) |
| M-4 | Skills-Nachrang heute schon widerlegt | WIP-Zaun Stufe 2 als CI-Check (§5.5) |
| M-5 | A/B/C-Labels altern stumm | `assessed_with` + `reassess_by` + Re-Assessment bei Modellwechsel (§5.1/5.6) |
| M-6 | Kalender-Trigger skaliert nicht | Event-Trigger Modell-ID-Vergleich (§5.6) |
| M-7 | Sensor-Tod sieht aus wie Erfolg | „nicht bewertbar" statt „stagniert" (§5.3, K1) |
| M-8 | Reconcile prüft Existenz, nicht Wirkung | Drill-Pflicht als Bau-Definition (§5.2, K4) |

**Konfliktmatrix (Pflicht):** Ein echter Dissens: Steelman hält die A/B/C-Klassifikation für
den konzeptionellen Kern; Diabolus hält sie für sekundär gegenüber Enforcement (AD-1/AD-2).
**Auflösung:** Owner-Entscheid „Gate-Bau zuerst" (2026-08-02) — Klassifikation läuft parallel
als billige Frontmatter-Pflege, blockiert nichts. Übrige Befunde konvergieren
(Code-statt-Prosa, Wirkung-statt-Existenz, Messbasis-Härtung) — keine weiteren Divergenzen.

## 7 Deep-Dive: das ×34-Paradox (Hook feuert, Verstoß bleibt Spitzenreiter)

Befund (C2, C6): `evidence_claim_scanner.py` existiert seit Juni (Reaktion auf Vorfall
2026-06-01), ist git-getrackt, feuerte in dieser Session nachweislich — und
`claim-before-cheapest-check` ist trotzdem ×34, zuletzt 31.07. **Diagnose:** Der Hook ist (a)
**advisory** (hängt eine Erinnerung an, blockt nicht) und (b) ein **Stop-Hook** — er feuert
NACH dem Absenden der Behauptung. Er ist konstruktionsbedingt Reparatur, nicht Prävention
(heute live beobachtet: Behauptung raus → Hook → Korrektur-Turn). **Konsequenz für D2:** Der
Slug ist im Sendemoment vermutlich nicht vollständig hookbar; das Gate braucht eine zweite,
blockierende Ebene am nächsten harten Artefakt-Übergang — PR-Ebene: CI-Check „PR-Body
behauptet Testergebnis/Status ohne verlinkten Run" → rot. **Hypothese-Kennzeichnung:** Ob
die PR-Ebene die Verstoß-Klasse messbar senkt, ist unverifiziert — genau dafür misst K1.

## 8 Alternativen (geprüft, verworfen)

| Alternative | Warum verworfen |
|---|---|
| Status quo (Regel-Akkretion weiter) | Empirisch scheiternd: ×34 bei wachsendem Bestand; risiko_debt 2.54 |
| „Modell vertrauen, Regeln radikal löschen" | Juli-Evidenz: aktuelle Modell-Ära verstößt weiter; C-Gates dürfen nie modellabhängig sein |
| Nur Gates bauen, kein Sunset/Ritual | Ratsche bleibt einseitig; Bestand wächst monoton (+14 Skills/Monat), Pflegekosten komponieren |

## 9 Out-of-the-Box

- **Verstöße pro Exposure** als Standard-KPI statt Rohzähler (macht Fenster vergleichbar).
- **Regel = Hypothese mit Halbwertszeit:** jede neue Typ-A-Regel entsteht ab jetzt MIT
  `reassess_by` — Regeln ohne Verfallsprüfung sind der Ausnahmefall, nicht der Normalfall.
- **Gate-Drill als wiederkehrender CI-Lauf** (nicht nur beim Bau): toter Hook wird binnen
  eines Fensters entdeckt statt 2028 (M-8 dauerhaft beantwortet).

## 10 Befunde

| ID | Befund | Evidenz |
|---|---|---|
| B-1 | 0/18 Gates gebaut; 7 Slugs waren ohne Tracking-Issue (02.08. nachgeholt #1631–#1638) | E3 (C3) |
| B-2 | Partielles Enforcement für ~5 Slugs existiert, überwiegend advisory | E2 (C2) |
| B-3 | Top-Slug ×34 überspannt die Hook-Ära → Repair-not-Prevention | E2/E3 (C1, C6) |
| B-4 | KPI-Parser zählt 3 Artefakt-Slugs aus Retro a50bc6 mit | E2 (C7) |
| B-5 | Regelbestand wächst monoton: +14 Skills allein Juli | E2 (C4) |
| B-6 | Ritual ohne Cron-Zwang wäre Merksatz Nr. 731 | D (Alternative: Kalender-Vorsatz — verworfen, AD-1) |

## 11 Top-5-Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R1 | Ritual verhungert (Owner-Ausfall, Incident-Vorrang) | Cron + Ausfall-Flip `stale` + Runbook (K2) |
| R2 | Sunset trifft Falsche (Abwesenheit ≠ Wirkung; A/C-Fehleinstufung) | Exposure-Nenner, konservative C-Einstufung, Ledger (K3) |
| R3 | Label-Drift (vierte Wahrheit, Alterung) | Labels nur in Regel-Quelle + `assessed_with`/`reassess_by` |
| R4 | Sensor-Tod maskiert als Erfolg | Input-Bedingung ≥8 Retros; „nicht bewertbar"-Zustand (K1) |
| R5 | Zaun-Umgehung (Skills wachsen weiter) | Override nur wörtlich + geloggt; Stufe-2-CI bis 13.09. (K-Prüfung) |

## 12 Empfehlungen (ungebündelt — jede einzeln entscheidbar)

| ID | Empfehlung | Charakter | Owner-Entscheid nötig? |
|---|---|---|---|
| D1 | Dieses KONZ reviewen/mergen | Governance | Ja (manueller Merge) |
| D2 | Gate-Welle 1: Top-5-Slugs je Reconcile→Drill→Bau-PR (Start: claim-before-cheapest-check mit PR-Ebene §7; dann handover-stale, scope-checkpoint, stale-clone [Drill des existierenden SessionStart-Checks!], deferred-item-no-tracking) | Ausführung, gate-frei bis auf Hook-Verteilung | Reihenfolge-OK genügt |
| D3 | Ritual-Cron anlegen (2.+16., report-only, kein Schreibrecht außer Issue via bestehendem --file-issues) | Automatismus, read-only-Bericht | Kenntnisnahme; Abschaltung jederzeit |
| D4 | A/B/C-Frontmatter-Rollout: erst platform (148 Einträge), dann Fleet | Pflege, gate-frei | Nein |
| D5 | Skills-WIP-Zaun Stufe 1 sofort, Stufe 2 als CI nach Welle 1 | **Selbstbetreffend: schränkt MICH ein** | Ja (bewusste Selbstbindung) |
| D6 | retro_kpis-Härtung: Golden-Fixture, Fail-on-unknown, a50bc6-Parser-Fix | Ausführung, gate-frei | Nein |
| D7 | Modellwechsel-Detektor (SessionStart, model-id-State) + Smoke-Suite | Ausführung, gate-frei | Nein |

**Ausdrücklich NICHT in diesem KONZ:** Autonomie-Erweiterungen (neue SA-Klassen,
Gate-Absenkungen). Die werden — Charta Punkt 3 — erst NACH Drill-bestandener Welle 1 + einem
sauberen Ritual-Zyklus einzeln vorgeschlagen, jeweils markiert „erweitert meine Macht".

## 13 Entscheidung + Kill-Gate + 30/60/90

Empfehlung: D1–D7 wie oben; Pilot = 3 Ritual-Zyklen (16.08., 02.09., 16.09.); ADR-Entscheid
erst danach.

**Kill-Gate-Kriterien:**
- **K1:** Nach 3 Zyklen (Stichtag 2026-09-16): normalisierte Verstoßrate (Verstöße/Retro) der
  Top-3-Slugs nicht gestiegen vs. Baseline-Fenster 19.07.–01.08.; Fenster mit <8 Retros =
  „nicht bewertbar" und zählt nicht als bestanden. Sonst: Überarbeitung mit hartem Scope-Cut.
- **K2:** 2 aufeinanderfolgende Fenster ohne Ritual-Lauf ⇒ `pipeline_status: stale` +
  Auto-Issue. Kein drittes Fenster ohne Owner-Entscheid.
- **K3:** >30 % Sunset-Rücknahmen bei N≥5 ⇒ Sunset-Pfad eingefroren (jede Rücknahme = realer
  Schadensfall im Ledger).
- **K4:** Gate ohne bestandenen Negativ-Drill zählt in jeder Metrik als NICHT gebaut.

**Tracking-Tabelle (Pflicht §13):**

| Kriterium | Status | Beleg |
|---|---|---|
| K1 Verstoßraten-Stagnation nach 3 Zyklen | offen | — (Baseline-Messung = Aufgabe Ritual-Lauf 1, 16.08.) |
| K2 Ritual-Ausfallregel aktiv | offen | — (Cron-Anlage = D3) |
| K3 Sunset-Ledger existiert, 0 Einträge | offen | — |
| K4 Drill-Protokoll je Welle-1-Gate | offen | — |

**30/60/90:** 30 Tage = Welle-1-Gates + Zyklen 1–2 + Baseline; 60 Tage = erste
Sunset-Kandidaten-Bewertung + Fleet-Label-Rollout; 90 Tage = ADR-Entscheid (org-weit) oder
Kill nach K1.
