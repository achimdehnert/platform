---
status: proposed
decision_date: 2026-07-23
deciders: Achim Dehnert
domains: [mail, data, dsgvo, tooling, infrastructure, dx]
supersedes: []
amends: []
related: [ADR-283, ADR-238, ADR-154]
tags: [mail, index, threading, classification, nl2sql, deletion-strategy, move-strategy, postgres, dev-hub, pii]
---

# ADR-284: Mail-Intelligence-&-Action-System — Postgres-Mail-Index, 100 %-Übersicht, gegatete Verschiebe-/Lösch-Strategien

> **Status: proposed.** Geht nach der Erstfassung in eine **externe Zweitmeinung**
> (`/adr-handoff-extern`, wie ADR-283). Nicht als entschieden lesen, bevor die offenen
> Fragen (§10) beantwortet sind.

## Metadaten

| Attribut     | Wert                                                             |
|--------------|-----------------------------------------------------------------|
| **Status**   | Proposed                                                        |
| **Scope**    | platform (Governance) · Umsetzung dev-hub                       |
| **Erstellt** | 2026-07-23                                                      |
| **Entscheider** | Achim Dehnert                                               |

## 1. Kontext & Problem

Korrespondenz über drei Postfächer (IIL/Graph, HNU/IMAP, AD/IMAP) ist geschäftskritisch,
aber es fehlt eine **verlässliche Übersicht** und ein **präziser Aktionsweg**. Der Auslöser
ist ein realer Fehler: Beim `/mailcheck IIL` am 2026-07-23 wurde per `--scan-senders` nur nach
**Absender-Domains** geprüft und ganze Domains **ungelesen als „Rauschen" abgetan** — dabei
gingen ein aktiver Kundenvorgang (**Zinser/Amos, Aufwandsschätzung**) und eine Security-Frist
(**Azure Copilot, 1. Aug**) unter. **Weniger als 100 % geprüft ist inakzeptabel.**

Der Owner will: **perfekte Übersicht über alle Mails**, **präzise und fehlerfreie
Reaktion**, und die Fähigkeit, **Lösch- und Verschiebe-Strategien präzise zu bewerten und
umzusetzen.** Dieser ADR entscheidet das System dahinter.

## 2. Anforderungen

1. **100 %-Abdeckung by construction** — jede Mail ist erfasst; kein Sampling, keine ungelesen
   verworfene Kategorie.
2. **Threading** — zusammengehörige Mails sind ein Vorgang (Zinsers Problem-Mail + Rückfrage).
3. **Signalbasierte Klassifikation** — Spam/NL/wichtig aus Kopfzeilen-Signalen, nicht geraten;
   Ambiguität → „prüfen", nie stumm droppen.
4. **Präzise Aktion** — draft-first Antworten, Flag/Prio, Vorgangs-Zustand.
5. **Strategien bewertbar vor Umsetzung** — Lösch-/Verschiebe-Regeln als Abfragen dry-run-bar.
6. **DSGVO-fest & auditierbar** — kontrollierte Ablage, reversible Aktionen, Audit-Spur.

## 3. Die Schichten

| # | Schicht | Zweck | Risiko |
|---|---|---|---|
| **1** | **Mail-Index (Postgres)** | Zeile/Mail (3 Postfächer, Ein+Ausgang): `message_id`, `in-reply-to`/`references`, `from`, `to`, `date`, `folder`, `flags`, `list-unsubscribe?`, `subject` | read-only Ingest; **PII-tragend** (Betreff/Absender) |
| **2** | **Klassifikation + Threading** | Threads aus references; Spam/NL/wichtig per Signal; „beantwortet?" per Inbox×Sent-Join | read-only |
| **3** | **Übersicht + Query (nl2sql)** | 100 %-Board nach Thread/Wichtigkeit/offen; Natural-Language→SQL als Abfrage-Interface | read-only (§7) |
| **4** | **Reagieren** | draft-first Antworten, Flag/Prio, **Vorgangs-Tracking (ADR-283, eingebettet)** | reversibel, kein Versand |
| **5** | **Verschiebe-Strategien** | Regel → dry-run gegen Index → Bestätigung → move | mittel |
| **6** | **Lösch-Strategien** | Regel → dry-run → Bestätigung → **nur Papierkorb**, Audit | **hoch** |

Schicht 1–3 liefert „perfekte Übersicht + fehlerfreie Reaktion" **ohne** destruktives Risiko.

## 4. Kern-Prinzip: Regeln sind Abfragen (bewerten vor umsetzen)

Sobald jede Mail eine Zeile ist, wird aus „welche Mails löschen/verschieben?" eine
**dry-run-bare Abfrage**: Eine Regel („alle NL älter 90 Tage", „alles von X nach Ordner Y")
zeigt **exakt, welche Mails sie träfe** — Zahl, Liste, Stichprobe — **bevor** etwas passiert.
„Präzise **bewerten** und dann umsetzen" ist damit eingebaut, nicht nachträglich.

## 5. Sicherheitsmodell (der Grund, warum das ein ADR ist)

- **Nie Hard-Delete.** Einzige „Lösch"-Aktion ist Verschieben in den Papierkorb — reversibel
  (bestehende Werkzeug-Konvention `organize_mail`).
- **Dry-run + menschliche Bestätigung** vor **jeder** destruktiven oder Verschiebe-Charge;
  `--yes` nur bei benanntem Kriterium.
- **Konservative Klassifikation:** signalbasiert (`List-Unsubscribe`, `Precedence: bulk`,
  `no-reply@`), **im Zweifel „prüfen"**, nie stumm droppen (der 2026-07-23-Fehler wird zum
  festen Invariant: **keine Domain/Mail ungelesen verwerfen**).
- **Lern-Loop:** Owner-Korrektur („das war wichtig") aktualisiert Absender-/Muster-Gewicht.
- **Audit-Spur:** jede Move-/Trash-Aktion wird protokolliert (wer/was/wann/Regel).

## 6. Daten & PII

Der Index ist **PII-tragend** (Betreffs tragen Fremd-PII, Absender sind personenbezogen). Es
ist das **eigene Postfach-Register in eigener kontrollierter DB** (wie der lokale Index von
Thunderbird/Outlook) — eine niedrigere Risikoklasse als Bürgerdaten in einem geteilten
Speicher (vgl. ADR-238), aber **kein** „Null-PII". Daher: zugriffskontrollierte dev-hub-Postgres,
Aufbewahrungsregel, **Löschung-auf-Anfrage**, kein Export in geteilte Vektor-Memory.

## 7. nl2sql-Schicht — die Sicherheitsgrenze

Natural-Language→SQL über den Index ist die **Abfrage**-Schicht (Owner-Idee). **Nur lesend
gefahrlos:** eine generierte `SELECT`-Abfrage kann höchstens falsche Zeilen zeigen. Eine
nl2sql-Ausgabe darf **niemals** direkt eine destruktive Aktion ausführen — jede aus nl2sql
abgeleitete Lösch-/Verschiebe-Absicht läuft durch das **dry-run + Bestätigungs-Gate (§5)**.
Read-only-nl2sql und action-nl2sql sind strikt getrennt.

## 8. Verhältnis zu ADR-283 (eingebettet, nicht ersetzt)

ADR-283 (Korrespondenz-Vorgangs-Speicher, **pointer-first**, dev-hub-Postgres) ist **Schicht 4**
dieses Systems und bleibt gültig. Feinheit: ADR-283 hält den **Vorgang** pointer-first (nur
Referenzen + Zustand, keine PII-Kopie); der **Mail-Index (Schicht 1)** erfasst dagegen bewusst
Metadaten (inkl. Betreff = PII). Das ist **kein Widerspruch, sondern zwei Schichten**: der Index
ist die vollständige Metadaten-Basis, der Vorgang die kuratierte, pointer-first Fall-Verfolgung
darauf. Diese ADR **erweitert** damit ADR-283s Datenbild um die Index-Schicht — die eine offene
Feld-Scope-Frage (Betreff/Links) steht in §10.

## 9. Heimat & Phasing

**Heimat = dev-hub-Postgres** (konsistent mit ADR-283; kein neuer Store). Ingest aus den drei
Postfächern über die bestehenden Werkzeuge (`graph_mail` für Graph, `read_mail`/IMAP ×2),
idempotent, mit Reconciliation (Mails werden anderswo verschoben/gelöscht/geflaggt).

- **Phase 1** — Schicht 1–3 (read-only Index + Threading + Klassifikation + Übersicht/nl2sql-read).
  Löst „100 %-Übersicht" mit **null** destruktivem Risiko. Höchster Sofort-Nutzen.
- **Phase 2** — Schicht 4 (Reagieren; ADR-283-Vorgang angebunden).
- **Phase 3** — Schicht 5 (Verschiebe-Strategien, dry-run + Bestätigung).
- **Phase 4** — Schicht 6 (Lösch-Strategien, am vorsichtigsten).

## 10. Offene Fragen (für die externe Zweitmeinung)

1. **Feld-Scope Index:** Betreff + Links im Index — der Nutzen ist groß (Threading/Übersicht),
   aber sie tragen Fremd-PII. Aufnehmen (Index bewusst PII-tragend, mit Kontrollen) oder
   weglassen/hashen?
2. **Klassifikations-Modell:** rein signalbasierte Regeln, ML, oder LLM-Klassifikation — und
   wo läuft das (Kosten/Datenhoheit, vgl. llm-routing)?
3. **nl2sql-Grenze scharf genug?** Reicht die read/action-Trennung (§7), oder braucht es eine
   Allowlist erlaubter Abfrage-Formen?
4. **Reconciliation:** Wie oft/robust wird der Index gegen die echten Postfächer abgeglichen,
   ohne Geister-Zeilen (verschobene/gelöschte Mails)?
5. **Retention:** Wie lange bleiben Index-Zeilen; was passiert bei einer Betroffenen-Löschung
   (Kaskade in den Index)?
6. **Threading-Stabilität:** Sind `message_id`/`references` über Graph **und** IMAP stabil genug,
   oder braucht es Betreff-/Teilnehmer-Heuristik als Fallback?

## 11. Nicht-Ziele

**Kein** Ersatz für Outlook/Thunderbird (ergänzt, ersetzt nicht) · **kein** Mailarchiv/Content-Store
· **kein** autonomer Versand · **kein** Hard-Delete · **keine** eigenmächtige Aktion aus einer
nl2sql-Ausgabe.

## 12. Kill-Gate

**`Phase-1-Umsetzung + 3 Monate`:** Nutzt der reale Mail-Check den Index (statt Live-Scan) und ist
die 100 %-Abdeckung nachweislich erreicht (kein weiterer „übersehene Mail"-Vorfall)? Wenn nein,
war die DB-Schicht Über-Engineering → zurück auf ein gehärtetes Voll-Listing im Skript.
Automatischer Trigger: ein „übersehene wichtige Mail"-Vorfall nach Phase 1 ist ein Fehlschlag des
Gates.

## 13. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-23 | Claude Code (Opus 4.8) | Initial (proposed). Anlass: `/mailcheck`-Domain-Sampling übersah reale Mail (Zinser/Azure). Sechs Schichten (Index→Klassifikation→Übersicht/nl2sql→Reagieren→Verschieben→Löschen), Kern-Prinzip „Regeln = Abfragen (bewerten vor umsetzen)", Sicherheitsmodell (nie Hard-Delete, dry-run+Bestätigung, konservativ, Audit, 100 %-Invariant), nl2sql-read/action-Grenze, ADR-283 als Schicht 4 eingebettet, dev-hub-Postgres, Phasing, offene Fragen für externe Zweitmeinung. |
