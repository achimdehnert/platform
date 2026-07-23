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

### Option A — Dateien (lokales JSON, Status quo) / **A+ gehärtet (verworfen, s. u.)**
Rohes JSON erfüllt nur **1 (dünn)** und **3 (weil lokal)**. Reißt bei **2/4/5**. Die
Reviews schlugen eine **gehärtete Variante A+** vor — verschlüsselte **SQLite hinter einer
schmalen authentisierten API** — als wartungsarmen Kandidaten für ein Zwei-Personen-Team.
**Dieses Argument trägt aber nur, wenn die Alternative bedeutet, eine *neue* Datenbank
aufzusetzen.** Bei Heimat = `dev-hub` gilt das nicht: dev-hub **läuft bereits auf Postgres**.
SQLite würde dann nichts einsparen, sondern eine **zweite Engine + Django-Multi-DB-Routing +
separaten Backup-/Verschlüsselungspfad** *hinzufügen* — mehr Komplexität, nicht weniger; und
für den späteren Umzug ins Behörden-RZ (ebenfalls Postgres) einen unnötigen Engine-Wechsel.
**A+/SQLite ist damit verworfen** (Owner-Entscheid 2026-07-23, §8); der Pilot nutzt die
**bereits kontrollierte dev-hub-Postgres**. Der PII-Schutz hängt an *pointer-first*, nicht an
der Engine.

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
  und ein **schlankes Schema auf der bereits vorhandenen dev-hub-Postgres** schlägt die
  risk-hub-Kopplung für den Pilot — konsistent bis zum Behörden-RZ-Postgres (Live), ohne
  Engine-Wechsel.
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

> **Owner-Entscheid 2026-07-23 (Achim Dehnert):** **Heimat = `dev-hub`, physische Ablage =
> die bereits vorhandene dev-hub-Postgres** (konsistent bis Behörden-RZ-Postgres für LRA-Live),
> pointer-first; risk-hub nur als Rückfall. **A+/SQLite verworfen** — in einem Postgres-Projekt
> würde es eine zweite Engine addieren, nicht Wartung sparen (§3A). Umsetzung als
> **[dev-hub#148](https://github.com/achimdehnert/dev-hub/issues/148)** (`model:sonnet-5`,
> gebaut als [dev-hub#149](https://github.com/achimdehnert/dev-hub/pull/149), CI grün).
> Damit sind Q1 und Q4 entschieden; Q2/Q3 sind Build-Time-Auflagen, keine Blocker mehr.

1. **Heimat** je Achse (§4): Code = `dev-hub`, physische Daten-Heimat, risk-hub nur Rückfall? —
   **✅ entschieden: dev-hub-Code + dev-hub-Postgres-Ablage (konsistent), risk-hub Rückfall,
   Behörden-RZ-Postgres für LRA-Live.**
2. **PII-Readiness-Gate** vor Live-Cutover: benannte Kriterien + Verantwortliche für Zweck/
   Hoheit je Konto, Rollen/Least-Privilege, Verschlüsselung/Secrets, Audit, Aufbewahrung,
   Auskunft, Löschung inkl. Backup-Regel, Restore-Test, Datenstandort, Incident-Prozess —
   **testbar**, nicht als Adjektiv „DSGVO-fest". — **⏳ Build-Time, vor Live-Cutover (dev-hub#148).**
3. **Re-ID-Test** für „vorgangs-abgeleitet ins Issue" scharf genug? (Rev-1-Antwort: Default
   **geschützt**, Issue nur nach bestandenem Test.) — **⏳ Build-Time (dev-hub#148).**
4. **Über-Engineering:** Reicht ein schlankes **pointer-first-Schema** für Pilot und ggf. Live? —
   **✅ ja; Ablage = bestehende dev-hub-Postgres (kein neuer Dienst, keine zweite Engine).
   A+/SQLite wäre in einem Postgres-Projekt der Umweg, nicht der schlanke Weg — daher verworfen.**

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
maschinen-übergreifende** Variante (z. B. read-only-Export des Postgres-Schemas), nie zurück
in einen unkontrollierten lokalen Store.

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
| A+ (SQLite-hinter-API) ernstnehmen | R1 OOB4 · R2 OOB2 | **[valid, später revidiert]** | §3A/§8-Q4: in Rev 1 aufgenommen, dann verworfen — bei Heimat=dev-hub (schon Postgres) addiert SQLite eine 2. Engine statt Wartung zu sparen (Owner-Entscheid 2026-07-23) |
| Föderiert je Hoheitsbereich / LRA→Behörden-RZ | R1 OOB3/AD-8 · R2 AD-5 | **[valid]** | §4 |
| Non-Ziele (kein CRM/Archiv/…) | R1 REC-14/M28-1 · R2 M28-2 | **[valid]** | §10 |
| Cutover-Plan (Dry-Run/Rollback/sichere Löschung) | R1 AD-15/M28-5/REC-12 | **[valid]** | §7 |
| eigene Priv/HNU-Mail nicht in Kundenprodukt | R2 AD-5/REC-5 | **[valid]** | §3C, §4 |
| Voller Enterprise-PII-Gate (RPO/RTO/Incident detailliert) | R1 REC-3/REC-9 | **[valid, scope-reduziert]** | §8-Q2 (als „vor Bau definieren", nicht hier ausspezifiziert) |
| Kaufen statt Bauen (Ticketsystem) | R1 OOB · R2 OOB3 | **[valid, verworfen]** | von beiden Reviewern selbst verworfen (Integrationsbruch/Vendor-Overhead) — dokumentiert, nicht verfolgt |

## 12. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-23 | Achim Dehnert (Entscheid) / Claude Code (Protokoll) | **A+/SQLite verworfen → dev-hub-Postgres, konsistent.** Owner-Rückfrage „wieso nicht Postgres?": das SQLite-Wartungsargument trägt nur bei einer *neuen* DB — dev-hub läuft schon auf Postgres, SQLite hätte eine 2. Engine + Multi-DB-Routing + separaten Backup/Encryption-Pfad addiert und einen Engine-Wechsel vor dem Behörden-RZ-Umzug erzwungen. §3A/§5/§8/§9 nachgezogen; §11-Audit „A+ ernstnehmen" als *später revidiert* markiert. Code (dev-hub#149) war ohnehin schon Postgres — keine Code-Änderung. |
| 2026-07-23 | Achim Dehnert (Entscheid) / Claude Code (Protokoll) | **Owner-Entscheid protokolliert:** Heimat = dev-hub + A+/SQLite Pilot, pointer-first; risk-hub Rückfall. §8 von „offene Fragen" auf Entscheid-Banner umgestellt (Q1/Q4 ✅, Q2/Q3 Build-Time), Umsetzung dev-hub#148. Status bleibt `proposed` bis formaler Accept. |
| 2026-07-23 | Claude Code (Opus 4.8) | **Rev 1** nach zwei externen Zweitmeinungen (§11). Kern-Umbau auf **pointer-first** (Referenzen statt PII-Kopie) → C⟂D-Dilemma großteils entschärft. Heimat in vier Achsen zerlegt (§4); A+ (SQLite-hinter-API) als ernster Kandidat (§3A); `deletion_ref` weich entkoppelt (§5/§6); `case_id` ≠ Thread (§6); Zugriffskontrolle by-construction (§5); Daten-Klassen-Trennung verschärft, „ins Issue" nur nach Re-ID-Test (§5/§8); Kill-Gate-Datum korrigiert + automatischer Trigger + Rückfall auf A+ statt JSON (§9); Non-Ziele ergänzt (§10); Cutover-Plan (§7). |
| 2026-07-23 | Claude Code (Opus 4.8) | Initial (proposed, Rev 0). Anforderungen, Optionen A–D, Achse C⟂D, Empfehlung D-mit-Synthese + offene Frage §8. |
