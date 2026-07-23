---
status: proposed
decision_date: 2026-07-23
deciders: Achim Dehnert
domains: [mail, data, dsgvo, tooling, infrastructure, dx]
supersedes: []
amends: []
related: [ADR-283, ADR-238, ADR-154]
tags: [mail, index, triage-ledger, threading, classification, nl2sql, coverage-contract, postgres, dev-hub, pii]
ai_sparring_by:
  - tool: other
    date: 2026-07-23
    role: adversarial-review
    summary: "Externe Runde 1 (Provider extern): Über-Scoping — nur Phase 1 verbindlich, ephemerer Index, nl2sql→Allowlist; Bilanz §15."
  - tool: other
    date: 2026-07-23
    role: adversarial-review
    summary: "Externe Runde 2 (Provider extern): Versprechen → Verträge (Coverage-Contract, Triage-Ledger, occurrence≠message, live-fetch); Bilanz §15."
---

# ADR-284: Mail-Intelligence-&-Action-System — Coverage-Contract + Triage-Ledger (Phase 1 verbindlich)

> **Status: proposed. Rev 1 (2026-07-23)** nach **zwei** externen Zweitmeinungen. Beide
> urteilten „überarbeiten": Rev 0 rechtfertigte eine PII-tragende 6-Schicht-Plattform für ein
> Zwei-Personen-Team mit einem Bug, dessen Direktfix eine Skript-Änderung ist, und formulierte
> „100 %/präzise/sicher" als **Ziele statt als prüfbare Verträge**. Rev 1: **nur Phase 1 ist
> verbindlich**, mit scharfen Verträgen; die destruktiven Schichten sind auf je eigene Folge-ADRs
> vertagt. Rückfluss-Bilanz in §15.

## Metadaten

| Attribut     | Wert                                                             |
|--------------|-----------------------------------------------------------------|
| **Status**   | Proposed (Rev 1)                                                |
| **Scope**    | platform (Governance) · Umsetzung dev-hub · **verbindlich: nur Phase 1** |
| **Erstellt** | 2026-07-23                                                      |

## 1. Kontext & Problem

Beim `/mailcheck IIL` (2026-07-23) prüfte das Werkzeug nur Absender-**Domains** und verwarf
ganze Domains **ungelesen** als „Rauschen" — ein aktiver Kundenvorgang und eine Security-Frist
gingen unter. **Weniger als 100 % geprüft ist inakzeptabel.** Der Owner will perfekte Übersicht,
präzise Reaktion und bewertbare Lösch-/Verschiebe-Strategien. Rev 0 wollte das als große
Plattform lösen; die Reviews zeigen: der **Kern** ist eine **beweisbare Vollständigkeit** — und
die braucht Verträge, keine weitere Heuristik.

## 2. Anforderungen (als Verträge, nicht Adjektive)

1. **Coverage-Contract** — nicht „100 %", sondern *100 % der für den Connector sichtbaren
   Nachrichten in **explizit benannten** Accounts + Ordner-Scope zu einem ausgewiesenen
   Quell-Watermark*, mit sichtbaren Fehler-/Staleness-Zuständen.
2. **Triage-Ledger** — jede entdeckte Mail ist ein Prozess-Zustand; „geprüft" ist ein
   *bezeugter* Zustand, nicht „indexiert".
3. **Präzise Reaktion** — Index liefert Pointer, Inhalt wird **live** geholt (nicht dupliziert).
4. **DSGVO-fest & purgebar** — abgeleiteter Index physisch löschbar; Löschkaskade ist
   **Akzeptanzkriterium**, nicht offene Frage.
5. **Baseline schlagen** — die DB muss ein **gehärtetes Voll-Listing-Skript** (Phase 0) messbar
   übertreffen, sonst gewinnt das Skript.

## 3. Scope-Entscheidung (Kern der Revision)

**Verbindlich in diesem ADR ist NUR Phase 1** (read-only Einheits-Übersicht + Triage-Ledger).
Die risikoreichen Schichten sind **vertagt**, jede auf eine eigene schmale Folge-ADR:

| Phase | Inhalt | Status hier |
|---|---|---|
| **0** | Gehärtetes Voll-Listing-Skript (Baseline) | Sofort, kein DB-Risiko |
| **1** | **Index + Coverage-Contract + Triage-Ledger + Übersicht** (read-only) | **verbindlich** |
| 2 | Reagieren (draft-first, live-fetch; ADR-283-Vorgang) | Folge-ADR |
| 3 | Verschiebe-Strategien | Folge-ADR (Action-Contract, §10) |
| 4 | Lösch-Strategien (nur Papierkorb) | Folge-ADR (Action-Contract, §10) |
| — | nl2sql-*Action* | Folge-ADR; Phase 1 nur read-only-DSL (§8) |

Die Annahme dieses ADR macht die Hochrisiko-Schichten **nicht** implementierungsreif.

## 4. Coverage-Contract + Triage-Ledger (das Herzstück)

**„indexiert" ≠ „geprüft".** Metadaten-Abdeckung garantiert weder das inhaltliche Erkennen
einer Frist noch eine erfolgte menschliche Triage. Daher ein **Zustandsautomat je Mail**:

`discovered → indexed → classified → triaged`

- Eine Mail verlässt `untriaged` **nur** durch (a) explizite menschliche Bestätigung oder
  (b) eine **versionierte, auditierte Policy**. Damit ist der Ur-Bug strukturell unmöglich:
  eine „weggefilterte" Mail bleibt sichtbar `untriaged`, nicht stumm verschwunden.
- **Board-Regel:** „vollständig" nur bei voll reconcilierten Quellen; sonst `partial/stale`
  mit `as_of`, Fehlerliste und letztem erfolgreichen Cursor — **prominente Coverage-/Staleness-
  Anzeige je Postfach**.
- **Coverage ≠ DB-Form:** „100 %" gilt für den **Ingest** in benannten Accounts/Ordnern zum
  Watermark — nicht-erfasste Ordner sind explizit als Scope-Lücke ausgewiesen, nicht still.

## 5. Index — abgeleitet, minimal, purgebar

- **Ephemer bevorzugt (Phase 1):** rebuild-on-demand aus IMAP/Graph (dem SSoT). Das killt
  Reconciliation-Drift + PII-at-rest + entschärft ADR-238 (kein persistenter, agent-erreichbarer
  PII-Store). Persistiert wird nur, was den Lern-Loop/Triage-Zustand braucht (§7/§4) — low-PII.
- **Feld-Scope entschieden (nicht offen):** Betreff, Absender, Empfänger, Datum, **Quell-Pointer**,
  Folder/Flags, nötige Header — **ja**. Vollständige **Bodies** und **volle URLs** — **nein**
  (Body live holen, §3; volle URLs vergrößern die Schadensfläche ohne Use-Case).
- **Purgebar:** „nie Hard-Delete" betrifft die **Quellmail** (Papierkorb-Grenze). Der
  **abgeleitete Index** muss zur Erfüllung von Retention/Betroffenen-Löschung **physisch
  purgebar** sein — Löschkaskade (Index + Vorgang + Audit) ist **Akzeptanzkriterium** von Phase 1.

## 6. Datenmodell — Occurrence ≠ Message

Trenne die **logische Nachricht/Thread-Kante** von ihrer **Postfach-Occurrence**. Stabiler
Occurrence-Schlüssel = `(account, connector, source-nativer Identifier)`. `Message-ID`/
`References`/`In-Reply-To` **verknüpfen**, sind aber **nicht** alleiniger Primärschlüssel
(brechen über Graph+2×IMAP). **Threading-Konfidenz:** Referenz-Header = hohe Konfidenz;
Betreff-/Teilnehmer-Heuristik = niedrige Konfidenz, **kein** automatischer Low-confidence-Merge;
persistente **manuelle Split/Merge-Overrides** mit Herkunftsnachweis. „Threading-unsicher" läuft
in denselben `needs_review`-Pfad wie mehrdeutige Klassifikation.

## 7. Klassifikation Phase 1 — konservativ, versioniert

Getrennte, **versionierte** Signale statt eines „wichtig"-Ratens: `bulk`, `automated`,
`known_sender`, `needs_review`, `confidence`. Header-Signale taugen für „bulk/automatisiert",
**nicht** verlässlich für „wichtig" — „wichtig" ohne belastbare Evidenz **konservativ**
(→ `needs_review`, nie stumm weg). **Keine** Move-/Trash-Regel allein aufgrund einer ML-/LLM-
Klassifikation. Lern-Loop: eine Einzelkorrektur darf **keine** globale Absender-/Domain-Abwertung
ohne Vorschau + Rollback erzeugen; ML/LLM erst mit owner-korrigiertem Eval-Satz + Versionslog
(späteres Ausbaustadium, nicht Phase-1-Pflicht).

## 8. nl2sql — Sicherheit korrigiert

Rev 0 sagte „ein SELECT kann höchstens falsche Zeilen zeigen" — **zu optimistisch**: freies SQL
auf einer geteilten Postgres kann fremde Tabellen offenlegen, Last erzeugen, Funktionen aufrufen;
**Betreffs sind angreifer-kontrollierter Text** (Prompt-Injection → SQL). Daher:

- **Eigene Postgres-Rolle + eigenes Schema / kuratierte Views**, kein Zugriff auf andere
  dev-hub-Daten; **Statement-Timeout, Zeilenlimit, erlaubte Spalten/Funktionen** fest.
- **Aktions-relevante Sprache erzeugt kein freies SQL, sondern eine typisierte Regel-DSL**
  (eingeschränkter Filterbaum → deterministisch zu parametrisiertem SQL). Query, Preview, Audit
  und Aktionsplan nutzen **dasselbe validierbare Objekt** (senkt SQL- und TOCTOU-Risiko).
- Phase 1: nur **read-only** auf der begrenzten View; freies nl2sql höchstens explorativ auf
  dieser View, nie über rohem Angreifer-Text als Aktion.

## 9. Reconciliation & Staleness

Wenn (statt ephemer) persistiert wird: inkrementeller Sync **+** Reconciliation nach jeder
eigenen Move-/Trash-Aktion **+** regelmäßiger voller Soll-/Ist-Abgleich, Frequenz nach
**Staleness-SLO**. Ein **still scheiternder Reconciler muss laut degradieren** (Board zeigt
`stale`). Verschwundene Occurrences → **Tombstone/ungeklärt**, nicht sofort „gelöscht". Ein
still veralteter Index (falsche 100 %-Sicherheit) ist schlimmer als keiner.

## 10. Vertagte Aktions-Schichten (Phase 3/4) — Pflichtinhalt der Folge-ADRs

Jede destruktive/Verschiebe-Schicht braucht **vor** dem Bau eine eigene ADR mit:
- **Unveränderlicher `action_plan`** (Operation, Ziel-Occurrence-IDs, Kandidatenzahl + Digest,
  Regel-/Klassifikationsversion, Preview-Zeitpunkt, Ablaufzeit, erwarteter Quellzustand).
- **TOCTOU-Schutz:** bei Ausführung jede Occurrence **live revalidieren** (Dry-run-Menge ≠
  garantiert Aktions-Menge); Ergebnis je Occurrence `pending/succeeded/failed/skipped`, idempotenter
  Retry, Teilfehler-Modell.
- Mengenlimits, Wiederanlauf, vollständiger **Audit** (Plan-ID, Vor-/Nachzustand je externem
  Seiteneffekt), Restore-Verhalten. Grenze bleibt: **nur Papierkorb**, menschliche Bestätigung.

## 11. Verhältnis zu ADR-283

ADR-283 (Vorgangs-Speicher, **pointer-first**, dev-hub-Postgres) ist die spätere **Phase-2**-
Substanz und bleibt gültig: der Vorgang referenziert Occurrences im Index. Die Feld-Scope-Feinheit
(Index trägt Betreff = PII, Vorgang bleibt pointer-first) ist in §5 entschieden.

## 12. Baseline, die die DB schlagen muss

- **Phase 0:** gehärtetes Voll-Listing-Skript (jede Mail, jede Quelle, keine Domain-Verwerfung).
- **Client-Features als Benchmark:** Graph-Search + Kategorien, IMAP-SIEVE, gespeicherte Suchen
  decken „nichts still verwerfen + Übersicht" teilweise — die reale Lücke ist die **postfach-
  übergreifende Einheitssicht + deterministischer Audit + Headless**. Jede Komponente wird gegen
  die Client-Funktion gebenchmarkt; die DB muss den Mehrwert **belegen**.

## 13. Nicht-Ziele

Kein Ersatz für Outlook/Thunderbird · kein Content-/Body-Store (Body live holen) · keine
volle-URL-Ablage · kein autonomer Versand · kein Hard-Delete der Quellmail · keine Aktion aus
einer nl2sql-Ausgabe · Phasen 3–6 sind **nicht** durch Annahme dieses ADR freigegeben.

## 14. Kill-Gate (messbar)

Statt „kein weiterer Vorfall" konkrete Metriken: **Quell-/Index-Zählparität**, Anzahl
**ungeklärter Gaps**, **Sync-Staleness**, Anteil **vollständig triagierter** neuer Mail, und ob
der reale Mail-Check den Index **tatsächlich nutzt**. Ein übersehener Vorgang **stoppt die nächste
Phase + löst Root-Cause-Analyse aus** (Ingest/Threading/Klassifikation/Darstellung/Mensch), statt
automatisch die ganze Index-Entscheidung zu verwerfen. Prüfzeitpunkt: `Phase-1-Umsetzung + 3 Monate`.

## 15. Externes Sparring — Rückfluss-Bilanz (Step 5)

Zwei externe Runden am 2026-07-23. Alle Befunde getaggt; nur `[valid]` eingeflossen, als eigene
Änderung. **Verdikt-Bilanz: praktisch durchgehend `[valid]`** — beide Reviews trafen echte
Schwächen; keiner war `[out-of-scope]`/`[missversteht]`.

| Thema | Quelle | Verdikt | Eingearbeitet in |
|---|---|---|---|
| **Über-Scoping → nur Phase 1 verbindlich, Rest in Folge-ADRs** | R1 AD-1/AD-2/REC-6 · R2 M28-1/M28-2/REC-13 | **[valid]** | §3, §10 |
| **„indexiert ≠ geprüft" → Triage-Ledger** | R2 AD-8/OOB1 | **[valid, zentral]** | §4 |
| **Coverage = Contract (Watermark/Zustände/partial-stale), nicht DB-Form** | R1 AD-7/REC-1 · R2 AD-1/REC-1/M28-5 | **[valid]** | §2, §4 |
| **Ephemerer/minimaler Index statt persistentem PII-Store** | R1 AD-3/OOB3/REC-3 · R2 AD-11 | **[valid, stark]** | §5 |
| **Feld-Scope entscheiden (Betreff ja, Body/volle URL nein)** | R2 AD-10/REC-6 · R1 REC-3 | **[valid]** | §5 |
| **Index purgebar; „no hard-delete" nur Quellmail; Löschkaskade = Akzeptanzkriterium** | R1 M28-1/REC-7 · R2 AD-5/REC-6/REC-7 | **[valid]** | §5 |
| **nl2sql-Sicherheit: eigene Rolle/Schema/Views + Limits; typisierte Regel-DSL für Aktionen** | R1 AD-4/REC-2 · R2 AD-4/REC-5/OOB2 | **[valid, korrigiert Rev-0-Fehler]** | §8 |
| **Occurrence ≠ Message; stabiler Quellschlüssel** | R2 AD-2/REC-2 | **[valid]** | §6 |
| **Threading-Konfidenz + manuelle Split/Merge-Overrides + Betreff-Fallback jetzt** | R1 AD-5/REC-5 · R2 AD-7/REC-10 | **[valid]** | §6 |
| **Reaktion = live-fetch (Body nicht persistieren)** | R2 AD-8/REC-11 | **[valid]** | §3, §5 |
| **Reconciliation first-class + Staleness-SLO + Tombstones + laut degradieren** | R1 AD-6/M28-2/REC-4 · R2 AD-1/REC-12 | **[valid]** | §9 |
| **Klassifikation: versionierte Signale, konservativ, nie Action auf ML allein** | R2 AD-6/REC-8/REC-9 | **[valid]** | §7 |
| **Feld-Hoheitsmatrix (Postfach vs Index vs abgeleitet)** | R2 AD-9/REC-3 | **[valid]** | §5/§6 (Pointer=Quelle autoritativ, Triage=DB, Klassifik.=abgeleitet) |
| **Action-Contract (action_plan/TOCTOU/Retry/Audit/Restore) für Phase 3/4** | R2 AD-3/REC-4/REC-14/M28-4 | **[valid, vertagt]** | §10 (Pflichtinhalt der Folge-ADRs) |
| **Kill-Gate messbar statt „kein Vorfall"** | R2 AD-12/REC-15 · R1 (Baseline) | **[valid]** | §14 |
| **Baseline: gehärtetes Skript + Client-Features als Benchmark** | R1 AD-1/OOB1/REC-1 · R2 OOB3 | **[valid]** | §2, §12 |
| **Betriebs-/Recovery-Vertrag (Rebuild, Schema-/Algo-Version, Backfill)** | R2 M28-3/REC-14 | **[valid, tw. vertagt]** | §5/§9 (Phase 1: Rebuild); Detailvertrag mit Aktions-ADRs |

## 16. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-23 | Claude Code (Opus 4.8) | **Rev 1** nach zwei externen Zweitmeinungen (§15). Kern-Umbau: **nur Phase 1 verbindlich** (§3), Rest in Folge-ADRs (§10). „100 %/präzise/sicher" → Verträge: **Coverage-Contract + Triage-Ledger** (§4, „indexiert ≠ geprüft"), **ephemerer/minimaler purgebarer Index** + entschiedener Feld-Scope + Löschkaskade als Akzeptanzkriterium (§5), **occurrence ≠ message** + Threading-Konfidenz (§6), konservative versionierte Klassifikation (§7), **nl2sql-Sicherheit korrigiert** + Regel-DSL (§8), Reconciliation-SLO + Tombstones (§9), live-fetch statt Body-Kopie (§3/§5), messbares Kill-Gate (§14), Baseline die die DB schlagen muss (§12). |
| 2026-07-23 | Claude Code (Opus 4.8) | Initial (proposed, Rev 0). Sechs Schichten, „Regeln = Abfragen", nl2sql-Idee, ADR-283 eingebettet. Kundennamen nachträglich genericisiert (PII-frei vor externer Zweitmeinung). |
