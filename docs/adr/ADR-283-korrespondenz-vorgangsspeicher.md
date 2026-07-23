---
status: proposed
decision_date: 2026-07-23
deciders: Achim Dehnert
domains: [data, correspondence, dsgvo, tooling, infrastructure]
supersedes: []
amends: []
related: [ADR-238, ADR-154, ADR-233]
tags: [mail, correspondence, vorgang, dsgvo, pii, data-home, risk-hub, ledger]
---

# ADR-283: Zentraler Korrespondenz-Vorgangs-Speicher — strukturierte, DSGVO-feste Heimat für themenübergreifende Mail-Vorgänge

> **Status: proposed.** Diese ADR trägt eine **Empfehlung mit einer bewusst offenen
> Kern-Frage** (§8, Heimat des Speichers) und geht **vor** der finalen Entscheidung in
> eine externe Zweitmeinung (`/adr-handoff-extern`). Nicht als „entschieden" lesen,
> bevor §8 aufgelöst ist.

## Metadaten

| Attribut     | Wert                                                             |
|--------------|-----------------------------------------------------------------|
| **Status**   | Proposed                                                        |
| **Scope**    | platform (Governance) · Umsetzung in einem noch zu wählenden Repo |
| **Erstellt** | 2026-07-23                                                      |
| **Entscheider** | Achim Dehnert                                               |

## 1. Kontext & Problem

Die drei angebundenen Postfächer (IIL/Graph, HNU/IMAP, AD/IMAP) tragen **themen­übergreifende**
Korrespondenz: MEiKI-Hosting (LRA), Hochschul-Vorgänge (HNU), Kundenprojekte (IIL),
DSGVO-Löschungen, Beratungs-Threads. Die Skills `/briefing` und `/mailcheck` müssen den
**Zustand** offener Vorgänge kennen — „wartend / beantwortet / nächste Stufe" — um gegen den
Gesendet-Ordner abzugleichen und die *eine* nächste Aktion vorzuschlagen, statt Erledigtes
doppelt anzustoßen.

Heute existiert dafür **kein solider Speicher**, sondern eine **künstliche Zweiteilung**
(kodiert in `/mailcheck`):

- **DSGVO-Löschungen** → `risk-hub` `DeletionRequest` (echte State-Machine, SSoT).
- **„Einfache Punkte"** → lokales JSON `~/.claude/mail-vorgaenge.json`.

Das lokale JSON ist ein **Pflaster**: pro Maschine, unstrukturiert, nicht übergabefähig,
keine Abfrage. Und der Normalfall — Korrespondenz quer zu den Repo-Themen — hat damit
**gar keine** verlässliche Heimat. Dieser ADR entscheidet, **wo und wie** Korrespondenz-
Vorgänge leben.

## 2. Anforderungen (Messlatte jeder Option)

Ein solider Vorgangs-Speicher muss **fünf** Eigenschaften zugleich erfüllen:

1. **Dauerhaft & strukturiert** — abfragbar (Zustand, `next_trigger`, Frist), nicht Freitext.
2. **Maschinen-übergreifend** — nicht auf einem Dev-Host gefangen (Ziel „überall wenn ich
   per SSH einlogge", vgl. `/briefing`-Portabilität).
3. **DSGVO-fest** — enthält **echte Personendaten** (Bürger-/Behörden-Adressen, Namen,
   Betreffs). Muss zugriffskontrolliert, backup-gesichert, lösch-/auskunftsfähig sein.
4. **Themen-klassifiziert mit Zustandsmaschine je Thread** — `thema`, `zustand`,
   `next_trigger`, Frist; mehrstufige Vorgänge (z.B. DSGVO Art. 17) auslöser-getrieben.
5. **Übergabefähig** — eine spätere Session oder ein Mensch nimmt den exakten Stand auf.

## 3. Betrachtete Optionen

### Option A — Dateien (lokales JSON, Status quo)
Erfüllt nur **1 (dünn)** und **3 (weil lokal)**. Reißt bei **2** (per-Maschine), **4** (kaum
Struktur) und **5** (nicht übergabefähig). **Nur als Übergangs-Stopgap tragbar.**

### Option B — Geteilte Vektor-Memory (Orchestrator/pgvector, `agent_memory_*`)
Erfüllt **2** und ist bereits Cross-Session-SSoT für Agent-Kontext. Scheitert aber an **3
und 4**: Die pgvector-Memory ist ein **breit lesbarer, semantischer** Speicher — jede
Session **und jede Cloud-Routine** liest ihn (vgl. ADR-238 „Agent = untrusted insider").
**Bürger-/Behörden-Personendaten dort abzulegen ist ein DSGVO-Verstoß** (kein
Zugriffs-Perimeter, kein gezieltes Löschen, semantische statt relationaler Form).
**Abgelehnt für den personenbezogenen Inhalt** — taugt höchstens für *anonymisierten*
Sachstand.

### Option C — Relationale Tabelle in `risk-hub` (Domänen-App)
Erfüllt **alle fünf**. Stark, weil `risk-hub` **schon** läuft (Postgres, multi-tenant,
schutztat.de), **schon** das DSGVO-Compliance-System mit Zugriffskontrolle ist und **schon**
der SSoT für den Löschfall. **Traffic-Argument:** der real dichteste Vorgangs-Strom
(MEiKI/LRA, DSGVO) berührt ohnehin die risk-hub-Domäne. **Contra:** koppelt einen
**cross-cutting**-Infrastrukturdienst (Korrespondenz-Tracking) an ein **Domänen-Produkt** —
zwei Lebenszyklen werden verschweißt (das Risk-Produkt könnte verkauft/geteilt/stillgelegt
werden, unabhängig vom Korrespondenz-Speicher). Zieht PII in die Produkt-DB.

### Option D — Relationale Tabelle in einem **domänenunabhängigen** Repo
Erfüllt **1, 2, 4, 5** und **3, sofern die Heimat einen PII-sicheren, zugriffskontrollierten,
backup-gesicherten Postgres bereitstellt.** Architektonisch am ehrlichsten: Korrespondenz-
Tracking ist **Infrastruktur**, keine Risk-Domäne. Konkrete Kandidaten: eine kleine App in
`dev-hub` (bestehendes Zuhause cross-cutting Platform-Dienste) **oder** ein dediziertes
Schema in einem Infra-Postgres. **Contra:** Die genannte DSGVO-feste Ablage (Backups,
Zugriffskontrolle, Lösch-Workflow) existiert in einem solchen Repo **noch nicht** — sie
müsste erst etabliert werden, während `risk-hub` sie bereits hat.

## 4. Entscheidungs-Achse (der eigentliche Trade-off)

> **Architektur-Reinheit (D) ⟂ Wiederverwendung des einzigen bereits PII-sicheren Stores (C).**

`platform` scheidet als Heimat **aus** (Meta-Repo, kein App-Code/Django, kein Prod-Daten-
Zuhause). Es bleibt: **C (risk-hub)** — sofort tragfähig, aber domänen-gekoppelt — versus
**D (domänenunabhängig)** — sauber, aber die PII-Ablage muss dort erst gebaut werden.

## 5. Empfehlung (zur externen Prüfung gestellt)

**Ziel-Heimat = Option D (domänenunabhängig), mit einer Synthese, die risk-hubs Traffic ehrt:**

- **Der DSGVO-Löschfall bleibt in `risk-hub`** (`DeletionRequest`) — er *ist* Compliance-Domäne
  und dort korrekt aufgehoben. **Nicht** herausmigrieren.
- **Der allgemeine `Korrespondenzvorgang` lebt domänenunabhängig** (Empfehlung: kleine App in
  `dev-hub`) und **referenziert** risk-hub für den Lösch-Subtyp. Das kehrt die heutige
  Default-Regel um: *allgemein = domänenunabhängig; Löschung = risk-hub*, statt *„alles
  Einfache = lokales JSON".*
- **Harte Vorbedingung für D:** die Ziel-Heimat muss einen zugriffskontrollierten,
  **backup-gesicherten** Postgres bereitstellen, **bevor** sie Personendaten trägt. Ist diese
  Vorbedingung zu teuer, ist **C (risk-hub) der Rückfall** — dann bewusst mit der
  Domänen-Kopplung als akzeptiertem Preis.

**Daten-Klassen-Trennung (gilt in jeder Option):**

| Klasse | Inhalt | Heimat |
|---|---|---|
| **Personenbezogen** | Namen, Adressen, Betreffs, Zitate | **nur** kontrollierte DB — nie Repo-Issue, nie pgvector-Memory |
| **Anonymisierter Sachstand** | „Hosting-Gate = Datenschutz/TOM; nächster Schritt X" | darf in Repo-Issue (gov-Repo) / Board |

## 6. Datenmodell (Skizze, nicht bindend)

`Korrespondenzvorgang { konto, thread_key, gegenüber, thema, zustand, next_trigger, frist,
quelle, angelegt, letzte_prüfung, deletion_ref? }` mit einer Zustandsmaschine analog
`DeletionRequest.advance_workflow`. `/briefing` legt an, `/mailcheck` schreibt fort/schließt.

## 7. Konsequenzen

- **Positiv:** ein SSoT statt Zweiteilung; Cross-Machine; abfragbar; DSGVO-fest; die Skills
  reden mit **einer** API statt Postfach-Raten; Vorgänge sind übergabefähig.
- **Negativ / Kosten:** ein neues Modell + Migration des lokalen JSON; bei D zusätzlich die
  PII-Ablage-Vorbedingung; bei C die Domänen-Kopplung.
- **Migration:** `~/.claude/mail-vorgaenge.json` wird einmalig importiert und dann als
  Stopgap **abgeschaltet** (bleibt bis dahin die einzige Quelle — kein Datenverlust).

## 8. Offene Frage für den externen Challenger (`/adr-handoff-extern`)

1. **Heimat:** Trägt die Synthese aus §5 (allgemein → domänenunabhängig, Löschung → risk-hub),
   oder wiegt risk-hubs realer Traffic + bereits vorhandene PII-Ablage schwerer als die
   Architektur-Reinheit — d.h. **C statt D**?
2. **Ist `dev-hub` die richtige domänenunabhängige Heimat**, oder braucht es ein dediziertes
   Repo/Schema? Welche etabliert die PII-Vorbedingung am billigsten?
3. **Ist die Daten-Klassen-Trennung (§5) scharf genug**, oder leckt der „anonymisierte
   Sachstand" in der Praxis doch Personenbezug (Re-Identifikation über Thema + Datum)?
4. **Über-Engineering?** Reicht für den tatsächlichen Vorgangs-Durchsatz nicht doch ein
   gehärtetes, **synchronisiertes** File-Modell (A+), statt einer DB (C/D)?

## 9. Kill-Gate

Wenn **6 Monate** nach Umsetzung (a) `/briefing`/`/mailcheck` den Speicher nicht real
beschreiben/lesen **oder** (b) weniger als ~5 Vorgänge je darin geführt wurden, war die DB
Über-Engineering → zurück auf das lokale JSON (A) und diesen ADR auf `superseded`.
**Prüfdatum: 2026-01-23.**

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-23 | Claude Code (Opus 4.8) | Initial (proposed). Anforderungen, Optionen A–D, Entscheidungs-Achse C⟂D, Empfehlung D-mit-Synthese + offene Frage §8 für externe Zweitmeinung. Ausgelöst durch Owner-Befund „themenfremde Mails sind der Normalfall — braucht solide Lösung". |
