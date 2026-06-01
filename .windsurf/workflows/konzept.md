---
description: Aus einem Problem ein entscheidungsreifes Konzept ausarbeiten — geerdet, right-sized (T1/T2/T3), adversarial, mit Lifecycle-Artefakt und Kill-Gate. Schreibt docs/konzepte/KONZ-<repo>-NNN.md.
---

# /konzept — Konzept entwickeln (entscheidungsreif)

> **Wann:** Aus einem Problem soll ein tragfähiges, pilotierbares, rückbaubares Konzept werden —
> die Stufe *vor* ADR, Use Case oder Klickdummy.
> **Wann NICHT:** Bestehenden ADR challengen → `/adr-challenger`. Rohe Idee aus Outline triagieren
> → `/idea-intake`. Use Case schneiden → `/use-case`. Schema/Format eines ADR → `/adr-review`.

## Verwendung

```
/konzept <Arbeitstitel> — <Problem in 1–3 Sätzen>
```

Fehlt Kontext, **frage nur**, wenn die fehlende Eingabe die spätere Entscheidungsempfehlung
*kippt*. Sonst: plausibel annehmen, Annahme markieren, weiterarbeiten.

---

## Step 0 — Erdung (PFLICHT, vor jeder Konzeptarbeit)

Theoretisiere nicht über die Infrastruktur — schlage sie nach. Öffne real (nicht aus dem Gedächtnis):

1. **`project-facts.md`** des Repos (Kontext, Owner, Stack).
2. Betroffene **ADR(s)**, insb. **ADR-211** (Spec = System of Record; Klickdummy rendert;
   Parity-Test = Konformitäts-Gate) + lokale Repo-ADRs unter `docs/adr/`.
3. Betroffene **Spec(s)** + Schema (`spec_id`, `spec_sha256`, `spec_schema_version`).
4. Genesor-Lifecycle `pipeline_status ∈ {idea, klickdummy, pilot, prod, sunset}`.
5. Offene **Failure-Items** und ihren *aktuellen* Stand: F11 Prod-Guard
   (`klickdummy_prod_guard.sh`), F17 DSL-Drift, F18 Locator-Fragilität, F19 Skip-Debt-Aggregation.

**Die Invarianten I1–I4 und die F-Items sind eine To-Verify-Liste, kein Gospel.** Wo der Stand
vom Erwarteten abweicht → Abweichungsbeleg nennen. Wo nicht prüfbar → ausdrücklich sagen.

**Evidenz-Ehrlichkeit (ganzer Output):** `E2` (Code) / `E3` (Issue/PR/CI) **nur**, wenn die
Datei/der PR **in dieser Session geöffnet** wurde — sonst `H`. `E1` = ADR/Invariant/Bridge/Genesor.
`E4` = externe Quelle. `D` = Design-Setzung (muss Alternative nennen). Kein hoher/kritischer
Befund ohne E1–E4. Keine erfundenen Pfade/PRs/Zeilen/Testergebnisse.

**Root-Cause-Tiefe (gegen voreilige Lösung):** Bevor du einen Mechanismus *konzipierst*, belege,
dass er **nicht schon existiert** (grep Generator/Gate/Script). Stoppe **nicht** bei der ersten
plausiblen Ursache — verifiziere die *tatsächliche*. Die naheliegende Lösung ist oft die falsche:
ein Konzept gegen ein bereits gelöstes Problem ist verlorene Arbeit. Grabe, bis die echte
Quelle des Schmerzes belegt ist (Beispiel-Dogfood: „fehlendes Dedup" → falsch, der Generator
war idempotent; echte Ursache war ein zweiter, menschen-geklickter Erzeuger).

**Evidence-Manifest (gegen performative Erdung — extern bemängelt: Erdung ist sonst nur
Selbstdeklaration).** Das Konzept-Doc trägt einen `evidence_manifest`-Block: pro belegtem Claim
`{claim_id, source_path, commit_or_pr, opened_in_session: true|false}`. **Harte Kopplung:** Nennst
du im Text eine Datei/Zeile/PR (gegen das Verbot generischer Recs), **muss** sie im Manifest mit
`opened_in_session: true` stehen — sonst ist die Aussage `H`, nicht `E2/E3`. Das verhindert
*Scheinkonkretheit* (erfundene Datei-/Gate-Namen ohne echten Beleg).

---

## Step 1 — Tier-Gate (PFLICHT — bestimmt die Tiefe)

Klassifiziere gegen die `adr-threshold`-Trigger. **Tiefe skaliert mit Stakes. Im Zweifel kleiner.**

| Tier | Trigger | Lieferumfang |
|---|---|---|
| **T1** | Addition n. Muster, 1 Repo, reversibel durch Entfernen *einer* Sache | Step 0 + Kernthese + MVC + Kill-Gate + Threshold. **~1 Seite. Stop.** |
| **T2** | Neue lokale Konvention / neue Boundary in einem Repo | T1 + Steelman + Advocatus Diabolus + 2 Alternativen + Top-3-Risiken |
| **T3** | Org-weit / SSoT-Reversal / neue Dependency / neuer Lifecycle / Cross-Repo | Vollprogramm + adversarialer Agenten-Fan-out (Step 3) |

Gib die Tier-Entscheidung als ersten Satz aus, mit harter Begründung. Eskaliert ein T1-Konzept
im Verlauf zu einer neuen Grenze → **sichtbar** auf T2/T3 hochstufen.

**Bedingtes Tier ist erlaubt** — wenn das Tier von einem *noch unverifizierten* Fakt abhängt,
benenne beide Zweige + den billigsten Check, statt vorschnell ein Tier vorzutäuschen. Beispiel:
„T1, *falls* der Fix repo-lokal ist; T2, *falls* er ein geteiltes Package trifft — Check: grep
`<symbol>` in `<cross-repo-pfad>`." Löse den Zweig auf, sobald der Check vorliegt.

**Auto-Eskalation (gegen T1 als Fluchtweg — extern bemängelt: Tier ist selbst-einstufbar).**
Berührt das Konzept eines von: **persistentes Artefakt · SSoT-Verschiebung · Cross-Repo ·
Security-Perimeter · Lizenz · neue Boundary · Reversal** → **mind. T2**, unabhängig von der
Selbsteinstufung. Diese Trigger sind nicht verhandelbar; ein als T1 gerahmtes Konzept, das einen
davon trifft, ist falsch klassifiziert. (Spätere Härtung: ein Threshold-Check-Bot statt
Selbsteinstufung — Backlog, OOTB-5.)

---

## Step 2 — Ausarbeiten nach Template

Folge der Struktur in **`platform/.windsurf/templates/konzept-template.md`** (Steelman →
Konzeptdefinition → Adversariale Analyse → Deep-Dive → Alternativen → OOTB → Befunde →
Top-5-Risiken → Empfehlungen → Entscheidung+Kill-Gate). Tiefe pro Achse nach Tier.
**Wichtig:** Die *Denk*-Achsen des Templates gelten für alle Tiers — die *persistierte Form* aber
nach Step 4 (T1/T2 = strukturiertes Ledger, T3 = Prosa-Doc). Bei T1/T2 wird die Template-Prosa zu
Ledger-/Tabellenzeilen verdichtet, nicht als Freitext gespeichert.

**Pflicht-Disziplinen** (egal welches Tier):
- **Steelman vor Kritik.**
- **Kein neues Feld/Gate/Scoreboard ohne SSoT-Prüfung** (erzeugt es eine zweite Wahrheit?).
- **Keine neue Boundary ohne Threshold-Begründung.**
- **Verbotene Empfehlungen:** „besser dokumentieren" / „mehr Tests" / „klarere Ownership" /
  „Security prüfen" / „CI verbessern". Immer konkret: welche Datei/Feld/Gate/Test/Status.
- **Kill-Gate Pflicht:** eine *messbare* Abbruchschwelle + datiertes Exception-Budget.

---

## Step 3 — Adversariat (Schärfe nach Tier)

- **T1:** Advocatus Diabolus inline, kurz.
- **T2:** Steelman / Diabolus / Maintainer-2028 als getrennte Abschnitte.
- **T3:** Steelman, Advocatus Diabolus und Maintainer-2028 als **drei unabhängige Agenten**
  (`Agent`/`Task`), die sich gegenseitig *nicht sehen* — sonst zieht der Kritiker die Schläge
  zurück. Danach ein Synthese-Pass. Optional externe Zweitmeinung via `/adr-handoff-extern`.
  **Konfliktmatrix Pflicht (gegen Kosten ohne Erkenntnis):** der Synthese-Pass liefert eine
  Tabelle belegter Dissense zwischen den Agenten — *oder* die explizite Feststellung „keine
  Divergenz". Drei Agenten ohne dokumentierten Dissens = verschwendete Kosten, kein Mehrwert.

Advocatus-Diabolus-Pflichtfragen: Wo entsteht eine Doppelquelle? Wo wird SSoT nur *behauptet*?
Wo wird ein „Tool" faktisch zur Boundary? Wo manuelle Pflicht ohne Enforcement? Wo ist „sichtbar
machen" schwächer als „verhindern"? Wo kann ein Team formal erfüllen und praktisch umgehen?
Wo werden F11/F17/F18/F19 *verschlimmert*?

---

## Step 4 — Artefakt schreiben (read-write)

Schreibe **ein** Dokument nach `docs/konzepte/KONZ-<repo>-NNN.md` (NNN = nächste freie Nummer im
Repo) mit Lifecycle-Frontmatter — das Konzept lebt nicht im luftleeren Raum:

```yaml
---
concept_id: KONZ-<repo>-NNN
title: <KONZEPTNAME>
pipeline_status: idea          # Genesor — kein neues Statusmodell
tier: T1 | T2 | T3
owner: <pflicht — kein TBD>
spec_refs: [<spec_id>, ...]    # Bezug zur SoR-Spec (ADR-211); leer nur wenn begründet
adr_threshold: kein ADR | Amendment | lokale ADR | org-weiter ADR | unklar
review_by: <YYYY-MM-DD>        # TTL — ohne Pflege Auto-Sunset (I3)
kill_criteria: "<messbare Abbruchschwelle>"
superseded_by_spec: <spec_id|null>   # gesetzt sobald Spec existiert → Doc wird read-only (Gate, s.u.)
evidence_manifest:             # gegen performative Erdung; Datei-/Zeilen-Claims MÜSSEN hier stehen
  - {claim_id: C1, source_path: <pfad>, commit_or_pr: <sha|#N>, opened_in_session: true}
created: <YYYY-MM-DD>
---
```

**Ehrliche Enforcement-Grenze (extern bemängelt, AD-5/RISK-5):** Dieser Skill *schreibt* die
Felder, *erzwingt* sie aber nicht. `review_by`/`kill_criteria`/`superseded_by_spec` wirken erst,
wenn ein **Lifecycle-Gate** sie liest (überfällige Konzepte → `stale`; Edit eines
`superseded_by_spec`-Docs in CI blockiert, außer `reactivation_reason` + I1-Review-Label gesetzt).
Solange dieses Gate fehlt, ist die Lifecycle-Kontrolle **Review-Gate, kein Exit-Code** — sag das,
verkauf es nicht als geschlossen.

**Artefakt-Form nach Tier (Entscheidung 2026-06-01, Option A — gegen Vor-Anforderungs-Drift
AD-6/12/13).** Persistiert werden **strukturierte Records** (Tabellen, Ledger, Ein-Satz-Thesen,
Befund-IDs) — **kein frei interpretierbarer Anforderungs-Freitext** außer bei T3:

- **T1 / T2 → Assumption-/Decision-Ledger** (kein Prosa-Doc). Inhalt:
  1. Frontmatter (oben)
  2. **Kernthese** (ein Satz)
  3. **Ledger-Tabelle:** `| id | Aussage | Typ (Annahme/Entscheidung/Risiko) | Evidenz/Falsifikation | Status |`
  4. **MVC** (konkreter Plan — Dateien/Felder/Gate; keine Anforderungsprosa)
  5. **Kill-Gate** + Threshold
  6. *(nur T2)* **Befunde-Tabelle** inkl. Diabolus-Zeilen + **2 Alternativen** als Tabellenzeilen
  → Es gibt **keinen** Freitext, der als „Vor-Anforderung" gelesen werden oder gegen die Spec driften kann.
- **T3 → voller Prosa-Doc** (ein Nummernschema): 1 Executive Summary · 2 Scope & Evidenzbasis ·
  3 Infrastruktur-Fit · 4 Steelman · 5 Konzeptdefinition · 6 Adversariale Analyse · 7 Deep-Dive ·
  8 Alternativen · 9 Out-of-the-Box · 10 Befunde · 11 Top-5-Risiken · 12 Empfehlungen ·
  13 Entscheidung + Kill-Gate + 30/60/90. **Plus** `superseded_by_spec`-Gate (oben), weil hier
  Prosa persistiert, die kontrolliert werden muss.

**Off-Ramp des Konzept-Docs selbst:** wird es ADR/Issue/Use-Case → `pipeline_status` weiterziehen,
Doc als Quelle markieren; wird es verworfen → `sunset` + Begründung. Ein Doc ohne `review_by`-Pflege
ist per I3 abgelaufen.

---

## Step 5 — Selbstcheck vor Abgabe

- [ ] Step 0 ausgeführt — Quellen *geöffnet*, nicht erinnert?
- [ ] Tier begründet, Tiefe entsprechend (kein T1-Overkill, kein T3-Underkill)?
- [ ] Jeder E2/E3-Beleg in dieser Session geöffnet — sonst auf H zurückgestuft?
- [ ] Steelman vor Kritik?
- [ ] Kein neues Feld/Gate/Scoreboard ohne SSoT-Prüfung, keine Boundary ohne Threshold?
- [ ] Kill-Gate messbar, Exception-Budget datiert?
- [ ] Jede REC konkret + verifizierbar?
- [ ] Artefakt hat `owner` + `review_by` + `pipeline_status` + `kill_criteria`?

---

## Changelog

- 2026-06-01: Initial. Aus dem Maximal-Monolith-Prompt destilliert (Tier-Gate, Pflicht-Erdung,
  ehrliche Evidenzregeln, Lifecycle-Artefakt, Kill-Gate). Threshold-Hinweis: org-weite Einführung
  ist Cross-Repo-Impact → Amendment an ADR-211 prüfen, bevor via cc-skill-dist verteilt wird.
- 2026-06-01: v1.1 nach T1-Dogfood (ausschreibungs-hub, Klickdummy-Issue-Dubletten #66/#67):
  Step 0 um **Root-Cause-Tiefe** ergänzt (Mechanismus-Nichtexistenz belegen, nicht bei erster
  plausibler Ursache stoppen — der Test falsifizierte die naheliegende Lösung 3×) und Step 1 um
  **bedingtes Tier** (Tier hängt an unverifiziertem Fakt → beide Zweige + Check benennen).
- 2026-06-01: v1.2 nach externem Adversarial-Review (anderer Anbieter, Handover): **Evidence-
  Manifest** (Step 0, gegen performative Erdung + Scheinkonkretheit AD-2/4/8), **Auto-Eskalation**
  (Step 1, gegen T1-Fluchtweg RISK-2), **Konfliktmatrix** für T3-Agenten (Step 3, gegen Kosten
  ohne Erkenntnis RISK-4), `superseded_by_spec` + ehrliche Enforcement-Grenze (Step 4, AD-5/RISK-5).
- 2026-06-01: v1.3 — Fork entschieden (Option A): **Artefakt-Form nach Tier** — T1/T2 =
  Assumption-/Decision-Ledger (kein Anforderungs-Freitext), T3 = voller Prosa-Doc + Supersession-Gate.
  Senkt das Vor-Anforderungs-Drift-Risiko (AD-6/12/13) strukturell statt nur per Constraint.
