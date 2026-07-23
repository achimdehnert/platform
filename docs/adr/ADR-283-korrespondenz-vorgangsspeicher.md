---
status: proposed
decision_date: 2026-07-23
deciders: Achim Dehnert
domains: [data, correspondence, dsgvo, tooling, infrastructure]
supersedes: []
amends: []
related: [ADR-238, ADR-154, ADR-233]
tags: [mail, correspondence, vorgang, dsgvo, pii, data-home, risk-hub, ledger]
ai_sparring_by:
  - tool: other
    date: 2026-07-23
    role: adversarial-review
    summary: "2 externe Runden (Provider extern): fanden unabhängig den pointer-first-Umbau; Verdikt-Bilanz + [valid]-Tags in §11."
---


# ADR-283: Korrespondenz-Vorgangs-Speicher — pointer-first, strukturiert, DSGVO-fest

> **Status: proposed. Rev 1 (2026-07-23)** nach **zwei** externen Zweitmeinungen. Beide
> fanden unabhängig denselben Hebel: die ursprüngliche Fassung nahm an, der Speicher
> **kopiere** Personendaten — genau daraus entstand das C⟂D-Dilemma. Rev 1 stellt auf
> **pointer-first** um (Referenzen statt Kopien), wodurch die Heimat-Frage großteils
> entschärft ist. Die Rückfluss-Bilanz steht in §11. Nicht als „entschieden" lesen,
> bevor §8 aufgelöst ist.

## Metadaten

| Attribut     | Wert                                                             |
|--------------|-----------------------------------------------------------------|
| **Status**   | Proposed (Rev 1)                                                |
| **Scope**    | platform (Governance) · Umsetzung in einem noch zu wählenden Repo |
| **Erstellt** | 2026-07-23                                                      |
| **Entscheider** | Achim Dehnert                                               |

## 1. Kontext & Problem

Die drei angebundenen Postfächer (IIL/Graph, HNU/IMAP, AD/IMAP) tragen **themen­übergreifende**
Korrespondenz: MEiKI-Hosting (LRA), Hochschul-Vorgänge, Kundenprojekte, DSGVO-Löschungen,
Beratungs-Threads. Die Skills `/briefing` und `/mailcheck` müssen den **Zustand** offener
Vorgänge kennen — „wartend / beantwortet / nächste Stufe" — um gegen den Gesendet-Ordner
abzugleichen und die *eine* nächste Aktion vorzuschlagen.

Heute existiert dafür **kein solider Speicher**, sondern eine künstliche Zweiteilung
(kodiert in `/mailcheck`): DSGVO-Löschungen → `risk-hub` `DeletionRequest` (SSoT); „einfache
Punkte" → lokales JSON `~/.claude/mail-vorgaenge.json`. Das JSON ist ein Pflaster: pro
Maschine, unstrukturiert, nicht übergabefähig, keine Abfrage. **Themenfremde Korrespondenz —
der Normalfall — hat gar keine verlässliche Heimat.** Dieser ADR entscheidet, **wo und wie**
Korrespondenz-Vorgänge leben.

## 2. Anforderungen (Messlatte jeder Option)

1. **Dauerhaft & strukturiert** — abfragbar (Zustand, `next_trigger`, Frist), nicht Freitext.
2. **Maschinen-übergreifend** — nicht auf einem Dev-Host gefangen.
3. **DSGVO-fest** — für **personenbezogene** Anteile: zugriffskontrolliert, backup-gesichert,
   lösch-/auskunftsfähig. **Rev-1-Präzisierung:** Diese Anforderung ist keine Konstante — ihr
   Gewicht hängt davon ab, *wie viel* PII der Speicher überhaupt hält (§5, pointer-first).
4. **Themen-klassifiziert mit Zustandsmaschine je Vorgang** — auslöser-getrieben.
5. **Übergabefähig** — eine spätere Session/Mensch nimmt den exakten Stand auf.

## 3. Betrachtete Optionen

Die Optionen werden **nach** der pointer-first-Weiche (§5) bewertet — sie verschiebt das
Gewicht von Anforderung 3.

### Option A — Dateien (lokales JSON, Status quo) / **A+ gehärtet**
Rohes JSON erfüllt nur **1 (dünn)** und **3 (weil lokal)**. Reißt bei **2/4/5**. Aber:
eine **gehärtete Variante A+** — verschlüsselte **SQLite hinter einer schmalen
authentisierten API** auf einem kontrollierten Host — erfüllt **1/2/4/5** bei minimaler
Wartung und **3 in Kombination mit pointer-first**. A+ ist damit **kein bloßer Stopgap
mehr**, sondern ein ernstzunehmender Kandidat für den synthetischen Pilot (Zwei-Personen-Team).

### Option B — Geteilte Vektor-Memory (Orchestrator/pgvector)
Scheitert an **3 und 4**: breit lesbarer, semantischer Speicher (ADR-238 „untrusted
insider"); Bürger-/Behörden-PII dort = DSGVO-Verstoß. **Abgelehnt für personenbezogenen
Inhalt** (settled).

### Option C — Relationale Tabelle in `risk-hub` (Domänen-App)
Läuft bereits (Postgres, multi-tenant, schutztat.de), ist das Compliance-System, ist SSoT
für den Löschfall. **Contra (Rev 1 verschärft):** (a) koppelt einen cross-cutting-Dienst an
ein verkaufbares Domänen-Produkt; (b) **das Traffic-Argument kollabiert an der eigenen
Prämisse** — wenn Nicht-Risk-Korrespondenz der Normalfall ist, landet die *Mehrheit* der
Vorgänge risk-domänen-fremd in der Risk-Produkt-DB; (c) eigene Privat-/HNU-Mail
ununterscheidbar in ein Kundenprodukt zu legen ist ein eigener Datenhoheits-Geruch; (d) die
Behauptung „C erfüllt alle fünf" ist unbelegt — `DeletionRequest` deckt nicht automatisch
generische Aufbewahrung/Auskunft/Zweckbindung für alle drei Kontexte.

### Option D — Relationale Tabelle in einem **domänenunabhängigen** Repo
Architektonisch am ehrlichsten (Korrespondenz-Tracking ist Infrastruktur). **Contra
(Rev 1):** verlangt bei PII-Kopie einen **zweiten** DSGVO-Grade-Postgres, dessen laufende
Kosten **sofort und sicher** sind, während C's Contra ein *spekulativer Zukunftsfall* ist —
ein asymmetrischer Trade gegen ein Zwei-Personen-Team. Ein `deletion_ref` von dort nach
risk-hub ist eine **verteilte** Referenz (dangling bei Retention-Purge).

## 4. Die eigentliche Entscheidung ist **nicht** eine Achse, sondern vier

Rev-0 verengte alles auf „Reinheit (D) ⟂ Wiederverwendung (C)". Die externen Reviews zeigen:
das sind **vier getrennte** Entscheidungen, die Rev 0 vermischte:

| Achse | Frage | Rev-1-Richtung |
|---|---|---|
| **Code-Heimat** | In welchem Repo lebt Modell + API? | domänenunabhängig, Default `dev-hub/apps/` |
| **Logische Service-Grenze** | Eine Fassade oder föderierte Lese-Verträge? | **eine** Client-API (§6) |
| **Physische Daten-Heimat** | Welche DB / welches RZ? | **separat** entscheiden; LRA-Live → Behörden-RZ (s.u.) |
| **Deployment je Datenhoheit** | Eine Instanz oder pro Hoheitsbereich? | föderierbar halten, nicht auf *eine* physische DB festlegen |

**Wichtig (aus AD-8/Kontext):** echte LRA-Personendaten liegen im **Zielzustand im
behördlichen Rechenzentrum**, nicht bei uns. Eine einzelne physische DB ist damit womöglich
schon falsch — der Entwurf muss **föderierbar** sein (ein logisches Modell/Vertrag, physisch
je Hoheitsbereich getrennt deploybar).

## 5. Empfehlung (Rev 1, zur weiteren Prüfung)

**Der Schlüssel ist das Datenmodell, nicht die Heimat: pointer-first.**

- **Standardmäßig speichert der Store nur Referenzen + Zustand** — `case_id`, Konto,
  Hoheitsbereich, `thema`, `zustand`, `next_trigger`, `frist`, **opake** Quell-Referenz
  (`message_id`/`thread_key`), `deletion_ref?`. **Name, Adresse, Betreff, Zitat, Body,
  Anhänge bleiben im Postfach als Inhalts-SSoT** und werden bei Bedarf live aufgelöst.
- **Damit schrumpft Anforderung 3 drastisch** (nicht auf null — `thema` + Hoheitsbereich +
  Datum + opake Keys behalten Rest-Bezug; das ist der einzuhegende Rest, nicht die Hauptmasse).
  **Ohne PII-Kopie entfällt die PII-Vorbedingung großteils** → die C⟂D-Achse entspannt sich,
  und ein **leichter Store (A+ SQLite-hinter-API oder kleines dev-hub-Schema)** schlägt die
  risk-hub-Kopplung für den Pilot.
- **Jedes personenbezogene Feld ist eine begründungspflichtige Ausnahme** (dokumentierter
  Zweck + Aufbewahrungsregel + Löschstrategie), technisch abgesichert durch einen Lint/Check,
  der PII-Felder in der *allgemeinen* Heimat verbietet. Die Pointer-vs-Copy-Regel ist
  **bindend**, nicht „Skizze".
- **Zugriffskontrolle by-construction (ADR-238 auf API-Ebene):** Konto-Isolation,
  Least-Privilege, getrennte Lese-/Schreibrechte; **kein** generisches Agenten-Leserecht —
  sonst kehrt das bei pgvector vermiedene Broad-Read-Problem zurück.
- **Löschfall:** bleibt in `risk-hub` (Compliance-Domäne). `deletion_ref` ist ein **weicher,
  entkoppelter Status-Snapshot**, **kein** Live-FK — der fachliche Löschstatus + Fristen
  gehören **ausschließlich** risk-hub (Feld-für-Feld-SSoT-Matrix, §6), damit kein
  Doppel-Wahrheitsstand und keine dangling refs beim Retention-Purge entstehen.

**Daten-Klassen-Trennung — verschärft (AD-4/AD-12):**

| Klasse | Inhalt | Heimat |
|---|---|---|
| **Personenbezogen** | Referenzen bleiben im Postfach; im Store nur opake Keys | **nur** kontrollierte DB, nie pgvector |
| **Vorgangs-abgeleitet** | Thema/Status/Datum — bei benanntem Pilot **re-identifizierbar (k=1)** | **standardmäßig geschützt**; Repo-Issue nur nach bestandenem Re-ID-Test (§8-Q3-Antwort: **es leckt**, daher Default „nicht ins Issue") |

## 6. Datenmodell (Skizze, Regeln bindend)

`Korrespondenzvorgang { case_id, konto, hoheitsbereich, thema, zustand, next_trigger, frist,
angelegt, letzte_prüfung, deletion_ref? }` — **getrennt** von `QuellReferenz { case_id,
provider, thread_key, message_id, gültig_ab }` (n:1). **`case_id` ≠ Thread:** ein Thread kann
mehrere Vorgänge tragen, ein Vorgang über mehrere Threads/Postfächer laufen (Merge/Split/
Weiterleitung sind explizit zu behandeln). Zustandsmaschine analog
`DeletionRequest.advance_workflow`, **noch zu spezifizieren** vor Bau: erlaubte Übergänge,
Transition-Akteur, idempotente Writes, optimistische Versionierung, **ein** eindeutiger
Betreiber der zeit-basierten `next_trigger`. Domänen-Workflows sind Erweiterungen **außerhalb**
des allgemeinen Kerns.

## 7. Konsequenzen & Cutover

- **Positiv:** ein SSoT statt Zweiteilung; cross-machine; abfragbar; minimale PII-Fläche; die
  Skills reden mit **einer** API; übergabefähig.
- **Kosten:** neues Modell + Migration; Rest-PII-Einhegung; API-Vertrag (Auth, Idempotenz,
  Teilausfall-Verhalten wenn risk-hub nicht erreichbar).
- **Cutover-Plan (Vorbedingung der Umsetzung, AD-15):** Inventur · Dry-Run · Dublettenregel ·
  Schreibstopp · Mengen-/Feldabgleich · Rollback-Punkt · **nachgewiesene sichere Löschung**
  aller lokalen JSON-/Backup-/Entwicklerkopien (sonst kennt bei Auskunft/Löschung niemand mehr
  alle Datenorte).

## 8. Owner-Entscheid & verbleibende Build-Time-Fragen

> **Owner-Entscheid 2026-07-23 (Achim Dehnert):** **Heimat = `dev-hub` + A+/SQLite für den
> Piloten, pointer-first**; risk-hub nur als Rückfall, Migrationspfad ins Behörden-RZ für
> LRA-Live. Umsetzung als **[dev-hub#148](https://github.com/achimdehnert/dev-hub/issues/148)**
> (`model:sonnet-5`, execution-ready). Damit sind Q1 und Q4 entschieden; Q2/Q3 sind
> Build-Time-Auflagen, keine Blocker mehr.

1. **Heimat** je Achse (§4): Code = `dev-hub`? Physische Daten-Heimat = A+/SQLite (Pilot) mit
   Migrationspfad ins Behörden-RZ (LRA-Live)? risk-hub nur noch als Rückfall? — **✅ entschieden:
   dev-hub + A+/SQLite Pilot, risk-hub Rückfall.**
2. **PII-Readiness-Gate** vor Live-Cutover: benannte Kriterien + Verantwortliche für Zweck/
   Hoheit je Konto, Rollen/Least-Privilege, Verschlüsselung/Secrets, Audit, Aufbewahrung,
   Auskunft, Löschung inkl. Backup-Regel, Restore-Test, Datenstandort, Incident-Prozess —
   **testbar**, nicht als Adjektiv „DSGVO-fest". — **⏳ Build-Time, vor Live-Cutover (dev-hub#148).**
3. **Re-ID-Test** für „vorgangs-abgeleitet ins Issue" scharf genug? (Rev-1-Antwort: Default
   **geschützt**, Issue nur nach bestandenem Test.) — **⏳ Build-Time (dev-hub#148).**
4. **Über-Engineering:** Reicht **A+ (SQLite-hinter-API) + pointer-first** für Pilot und ggf.
   Live? — **✅ für den Pilot bejaht (A+/SQLite gewählt); LRA-Live evtl. Postgres im Behörden-RZ.**

**Status bleibt `proposed`** bis zum formalen Owner-Accept — die Heimat ist entschieden und der
Bau läuft über dev-hub#148, aber die Accept-Bedingungen (Q2/Q3 als testbare Gates) werden erst
im Zuge der Umsetzung erfüllt.

## 9. Kill-Gate (korrigiert)

Prüfzeitpunkt **`Umsetzung + 6 Monate`** (das in Rev 0 gesetzte `2026-01-23` lag *vor* dem
Entscheidungsdatum — Fehler, ersetzt). Bewertung **nicht** allein an „< 5 Vorgänge", sondern
an vermiedenen Doppelaktionen, eingehaltenen Fristen, erfolgreichen Übergaben, Bedienaufwand,
Verfügbarkeit, Fallzahl. **Automatischer Trigger** (Vorgangs-Zähler + Datum als CI-Check),
damit das Gate nicht an Trägheit scheitert. **Rückfall NICHT auf rohes lokales JSON** nach
erstem echten PII-Betrieb — sondern auf die kleinste weiterhin **kontrollierte und
maschinen-übergreifende** Variante (A+).

## 10. Nicht-Ziele (Scope-Zaun, dauerhaft)

**Kein** Mailarchiv · **kein** CRM · **keine** Attachment-Ablage · **keine** Volltextsuche ·
**keine** domänenspezifischen Workflows außer über Referenzen. Der Dienst bleibt auf
**Vorgangsstatus, Fristen, Übergabe** begrenzt. (Verhindert das „schleichende Mini-CRM",
Maintainer-2028-Reue beider Reviews.)

## 11. Externes Sparring — Rückfluss-Bilanz (Step 5)

Zwei externe Runden am 2026-07-23. Alle Befunde getaggt; nur `[valid]` eingeflossen, als
eigene Änderung (nicht GPT-Prosa 1:1). Verdikt-Bilanz: **überwiegend `[valid]`** — die
Reviews waren hochwertig und konvergent.

| Thema | Quelle (R1/R2) | Verdikt | Eingearbeitet in |
|---|---|---|---|
| **Pointer-first statt PII-Kopie** (zentral) | R1 AD-9/OOB1/REC-6 · R2 AD-6/OOB1/REC-1 | **[valid]** | §5, §6, §3 |
| C⟂D ist teils Scheindilemma / D-Kosten unbeziffert & asymmetrisch | R2 AD-1/AD-2/AD-3 · R1 AD-16 | **[valid]** | §3C/D, §4, §8 |
| Heimat = vier getrennte Achsen | R1 AD-1/AD-2/REC-1 | **[valid]** | §4 |
| „Anonymisierter Sachstand → Issue" leckt (k=1) | R1 AD-12/REC-7 · R2 AD-4/REC-3 | **[valid]** | §5-Tabelle, §8-Q3 |
| Kill-Gate-Datum vor Entscheidungsdatum | R1 AD-13 · R2 AD-8 | **[valid]** | §9 |
| Kill-Gate-Metrik/Trigger/Rückfall | R1 AD-14/REC-10/REC-11 · R2 M28-3/REC-8 | **[valid]** | §9 |
| `deletion_ref` = verteilte/dangling Referenz → weich entkoppeln | R1 AD-5/REC-4 · R2 AD-7/REC-4 | **[valid]** | §5, §6 |
| `thread_key` ≠ Vorgangs-Identität | R1 AD-10/M28-3/REC-8 | **[valid]** | §6 |
| Broad-Read auf API-Ebene / Zugriffskontrolle | R1 AD-4/REC-3 | **[valid]** | §5 |
| A+ (SQLite-hinter-API) ernstnehmen | R1 OOB4 · R2 OOB2 | **[valid]** | §3A, §8-Q4 |
| Föderiert je Hoheitsbereich / LRA→Behörden-RZ | R1 OOB3/AD-8 · R2 AD-5 | **[valid]** | §4 |
| Non-Ziele (kein CRM/Archiv/…) | R1 REC-14/M28-1 · R2 M28-2 | **[valid]** | §10 |
| Cutover-Plan (Dry-Run/Rollback/sichere Löschung) | R1 AD-15/M28-5/REC-12 | **[valid]** | §7 |
| eigene Priv/HNU-Mail nicht in Kundenprodukt | R2 AD-5/REC-5 | **[valid]** | §3C, §4 |
| Voller Enterprise-PII-Gate (RPO/RTO/Incident detailliert) | R1 REC-3/REC-9 | **[valid, scope-reduziert]** | §8-Q2 (als „vor Bau definieren", nicht hier ausspezifiziert) |
| Kaufen statt Bauen (Ticketsystem) | R1 OOB · R2 OOB3 | **[valid, verworfen]** | von beiden Reviewern selbst verworfen (Integrationsbruch/Vendor-Overhead) — dokumentiert, nicht verfolgt |

## 12. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-23 | Achim Dehnert (Entscheid) / Claude Code (Protokoll) | **Owner-Entscheid protokolliert:** Heimat = dev-hub + A+/SQLite Pilot, pointer-first; risk-hub Rückfall. §8 von „offene Fragen" auf Entscheid-Banner umgestellt (Q1/Q4 ✅, Q2/Q3 Build-Time), Umsetzung dev-hub#148. Status bleibt `proposed` bis formaler Accept. |
| 2026-07-23 | Claude Code (Opus 4.8) | **Rev 1** nach zwei externen Zweitmeinungen (§11). Kern-Umbau auf **pointer-first** (Referenzen statt PII-Kopie) → C⟂D-Dilemma großteils entschärft. Heimat in vier Achsen zerlegt (§4); A+ (SQLite-hinter-API) als ernster Kandidat (§3A); `deletion_ref` weich entkoppelt (§5/§6); `case_id` ≠ Thread (§6); Zugriffskontrolle by-construction (§5); Daten-Klassen-Trennung verschärft, „ins Issue" nur nach Re-ID-Test (§5/§8); Kill-Gate-Datum korrigiert + automatischer Trigger + Rückfall auf A+ statt JSON (§9); Non-Ziele ergänzt (§10); Cutover-Plan (§7). |
| 2026-07-23 | Claude Code (Opus 4.8) | Initial (proposed, Rev 0). Anforderungen, Optionen A–D, Achse C⟂D, Empfehlung D-mit-Synthese + offene Frage §8. |
