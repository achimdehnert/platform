# Konzept-Template (referenziert von /konzept)

> Kanonische Inhaltsstruktur für Konzept-Dokumente. Der Skill `/konzept` erledigt Erdung (Step 0),
> Tier-Gate und Artefakt-Frontmatter; **dieses Template liefert die Abschnitts-Tiefe**.
> Tiefe pro Achse nach Tier (T1 schlank, T3 voll). Ein Nummernschema — keine Dubletten.

---

## Form nach Tier (Option A, 2026-06-01 — gegen Vor-Anforderungs-Drift)

Die *Denk*-Achsen unten (§1–§13) gelten für alle Tiers. Die **persistierte Form** unterscheidet sich:

- **T1 / T2 → Assumption-/Decision-Ledger** (kein Prosa-Doc). Nur strukturierte Records:
  1. Frontmatter · 2. **Kernthese** (ein Satz) · 3. **Ledger-Tabelle** · 4. **MVC** (konkreter Plan) ·
  5. **Kill-Gate + Threshold** · *(T2 zusätzlich)* **Befunde-Tabelle** inkl. Diabolus + **Alternativen** als Zeilen.
  Kein frei interpretierbarer Anforderungs-Freitext → nichts, das gegen die Spec driften kann.

  ```markdown
  ## Annahmen-/Entscheidungs-Ledger
  | id | Aussage | Typ (Annahme/Entscheidung/Risiko) | Evidenz / Falsifikation | Status |
  |----|---------|-----------------------------------|-------------------------|--------|
  | L1 | …       | Beobachtung                       | C1 (evidence_manifest)  | verifiziert |
  | L2 | …       | Annahme                           | nicht geöffnet — Check: …| offen (H)   |
  ```

- **T3 → voller Prosa-Doc** nach §1–§13 unten **+** `superseded_by_spec`-Gate (Prosa muss kontrolliert werden).

---

## 1. Executive Summary  *(≤10 Sätze)*
Entscheidungsempfehlung · Kernidee · wichtigste Stärke · wichtigstes Risiko · kleinste sinnvolle
Version (MVC) · wichtigste Unsicherheit.

## 2. Scope & Evidenzbasis
Verwendeter Input · in Step 0 **geöffnete** Quellen (Pfade/PRs) · genutzte externe Quellen ·
Annahmen (markiert) · nicht prüfbare Bereiche.

## 3. Infrastruktur-Fit  *(Tabelle)*

| Infrastruktur-Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---:|---|---|---|---|

Mindestens prüfen: ADR-211 · I1 Spec-first · I2 Prod-Sicherheit · I3 Off-Ramp+TTL · I4 Namensraum ·
Requirements-Bridge · Executable-Parity-Bridge · Genesor `pipeline_status` · Manifest/Scoreboard ·
`klickdummy_prod_guard.sh`/F11 · F17 DSL-Drift · F18 Locator-Fragilität · F19 Cross-Repo-Aggregation ·
pytest/Playwright · lokale Klickdummy-ADRs · `adr-threshold`.

## 4. Steelman  *(3–7 Sätze, evidenzbasiert)*
Stärkstmögliche positive Lesart, **bevor** du kritisierst: warum attraktiv, wo I1–I4 sauber genutzt,
welche Lücke elegant geschlossen, wo Komplexität vermieden, warum nicht over-engineered.

## 5. Konzeptdefinition

**5.1 Kernthese** — ein Satz: „Dieses Konzept sagt: `<KERNENTSCHEIDUNG>`."
**5.2 Problem** — Ausgangslage · Schmerz · Lücke · *warum jetzt?* — getrennt nach
Beobachtung / Interpretation / Hypothese / offene Frage.
**5.3 Zielbild** — was wird möglich · was wird unmöglich/sichtbar riskant · welche Entscheidung leichter.
**5.4 Nicht-Ziele** — was es **nicht** löst · was menschliche Prüfung / repo-lokal / optional /
kein Produktcode / **kein neuer System-of-Record** bleibt.
**5.5 Artefakte**

| Artefakt | Neu/Geändert | Owner | Normativ? | Generiert? | Lebenszyklus | Risiko |
|---|---|---|---:|---:|---|---|

**5.6 Datenmodell/Schema** *(nur wenn nötig)* — pro Feld: Name · Typ · Pflicht/Optional · Bedeutung ·
Owner · Validierung · Migrationspfad · Beispiel · Failure-Mode. **Keine zweite Wahrheit; kein aus
der Spec ableitbares Feld.** Unvermeidbare Duplikation → Redundanzregel + Drift-Check Pflicht.
**5.7 Prozessmodell** — entlang `idea → klickdummy → pilot → prod → off-ramp → sunset`: pro Schritt
was passiert · wer entscheidet · welches Artefakt ändert sich · welches Gate · welche Evidenz · was bei Abweichung.
**5.8 Enforcement-Modell**

| Regel | Level (Doku/Warnung/Scoreboard/CI-Gate/Review/Runtime-Guard/Governance) | Mechanismus | Owner | Ausnahme? | Ablaufdatum nötig? |
|---|---|---|---|---:|---:|

**5.9 Minimal Viable Concept** *(Pflicht, auch T1)* — genau welche Felder/Dateien · welcher Prozess ·
welches Gate · was bewusst **nicht** drin · **wie Erfolg nachgewiesen** · **wie Rückbau geht**.
**5.10 Full Concept** *(nur T3)* — Zielversion, klar von der Minimalversion getrennt.

## 6. Adversariale Analyse  *(Schärfe/Trennung nach Tier — siehe Skill Step 3)*

**😈 Advocatus Diabolus** — jeder Befund kennzeichnet `bestehende Lücke nicht geschlossen` **oder**
`neuer Failure-Mode` (+ Governance-Lücke / SSoT-Risiko / Operationalisierungsrisiko / unklare Ownership).
**🔮 Maintainer 2028** — was ist in 2 Jahren verwaist / kopiert statt referenziert / ownerlos /
permanente Ausnahme / vergessene Reviewpflicht / falsche Runtime-Annahme; was würdest du löschen?

## 7. Deep-Dive  *(T2: relevante Achsen; T3: alle)*

1. **SSoT/Drift** — normativ vs. abgeleitet vs. generiert vs. menschlich; wo Drift entsteht,
   wie erkannt, wie verhindert; was bei Konflikt Spec/Test/Manifest/Doku/Runtime gilt.
2. **Boundary/Komplexität** — neue Grenze/Service/Dependency/Team-Interface? Gerechtfertigt? Als reine Erweiterung möglich?
3. **Governance** — wer ändert/besitzt/genehmigt Ausnahmen; Ablaufdaten; optional vs. pflicht;
   gating vs. sichtbar; wo gehört der Status hin (Spec/Manifest/Genesor/ADR/CI)?
4. **Security & Prod-Sicherheit** — öffnet es Demo-/Mock-/Preview-Pfade in Prod? Wirkung auf F11?
   neue Secrets/Tokens/CI-Rechte? sensible Daten in generierten Artefakten?
5. **Datenschutz** — PII in Manifesten/Logs/Testartefakten? Retention/Löschpflichten? prod-nahe Testdaten?
6. **Testbarkeit** — generiert vs. handgeschrieben; Negativtests; welche Coverage *irreführend*;
   wie sieht ein roter Test aus; wie ein legitimer Override?
7. **CI/CD & Betrieb** — blockierend vs. informativ; auditierbare Artefakte; Verhalten bei
   Generator-Fehler/flaky/Umgebungsdrift; Rollback; Versionierung.
8. **Migration** — wie kommt ein Repo rein/raus; erster sicherer Pilot; Legacy-Fälle;
   welche alte Praxis ersetzt, welche bleibt erlaubt.
9. **Messbarkeit** — Metriken getrennt nach **Vanity / echte Qualitäts-Sicherheits-Metrik /
   Frühindikator / Spätindikator** (Adoption, Drift-Funde, Skip-Debt, Off-Ramp-Zeit, false pos/neg,
   Produktionslecks, Wartungsaufwand, Zahl dauerhafter Ausnahmen).

## 8. Alternativen  *(T2: 2; T3: ≥3, davon je eine radikal kleiner / technischer / organisatorischer)*
Pro Alternative: Idee · Funktionsweise · genutzte Infra · einfacher · gefährlicher · teurer · besser · verwerfen.

## 9. Out-of-the-Box  *(T3: ≥3 nicht-naheliegende Ansätze)*
Pro Ansatz: Idee · Vorteil · Nachteil · wann sinnvoll · warum evtl. verwerfen · welche Infra dadurch
überflüssig/stärker genutzt. Anregungen: Concept-as-Policy statt -as-Tool · Scoreboard-only vs.
CI-Gate-only · Kill-Switch statt Off-Ramp-Logik · Spec-Diff-Risk-Scoring · Exception-Budget mit
Ablaufdatum · Shadow-Mode 30 Tage · „Delete-the-renderer"-Default · Runtime- statt Build-Probe ·
Property-based Tests aus Spec · Threat-model-as-code · Local-first-Pilot · **Entfernen** statt Hinzufügen.

## 10. Befunde  *(Tabelle, stabile IDs)*

| ID | Rolle | Kategorie | Befund (1 Satz) | Evidenz | Schweregrad | Confidence | Betroffener Teil |
|---|---|---|---|---|---|---|---|

ID-Präfixe: `PRO-` `AD-` `M28-` `SSOT-` `GOV-` `SEC-` `PRIV-` `TEST-` `OPS-` `ARCH-` `MIG-` `DOC-`.
Schweregrad: `stark positiv`/`positiv`/`niedrig`/`mittel`/`hoch`/`kritisch`. Confidence: `hoch`/`mittel`/`niedrig`.
Regeln: ein Satz · hoher/kritischer Befund braucht E1–E4 · `H` markieren · keine generischen
Best-Practice-Befunde · keine Stilfragen außer strukturelles Risiko · positive Befunde ebenfalls evidenzbasiert.

## 11. Top-5-Risiken
Pro Risiko: warum wichtig · konkretes Schadensszenario · Wahrscheinlichkeit · Impact ·
**kleinster wirksamer Fix** · stärkster Gegenbeleg · Restunsicherheit.

## 12. Empfehlungen  `REC-n`
Pro REC: Bezug auf Befund-ID · Ziel · **konkrete Änderung (welche Datei/Feld/Gate/Test/Status)** ·
Aufwand S/M/L · Risiko der Änderung · Verifikation · Akzeptanzkriterium · Migrationshinweis · Owner-Vorschlag.
**Verboten:** „besser dokumentieren" / „mehr Tests" / „klarere Ownership" / „Security prüfen" / „CI verbessern".

## 13. Entscheidung + Kill-Gate + 30/60/90
Empfehlung ∈ {annehmen · als MVP annehmen · überarbeiten · pilotieren · ablehnen · durch Alternative ersetzen}.
Je *eins*: wichtigste Begründung · Stärke · Schwäche · Sofortmaßnahme · Unsicherheit · finaler Threshold-Status.
**Kill-Gate (Pflicht):** messbare Abbruchschwelle (z. B. „<2/5 Pilot-Repos adoptieren in 60 Tagen") +
Exception-Budget mit Ablaufdatum pro zugelassener Ausnahme.
**30/60/90:** 30 = Owner + Minimalartefakte + erste Validierung; 60 = Pilot + Integration +
erste Gegenbelege/False-Positives; 90 = Kill-Gate auswerten → ausrollen / umbauen / **stoppen**.
