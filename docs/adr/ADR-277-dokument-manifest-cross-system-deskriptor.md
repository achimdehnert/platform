---
status: proposed
decision_date: 2026-07-16
revision: 2
deciders: [Achim Dehnert]
scope: platform
implementation_status: none
ai_sparring_by:
  - tool: other
    date: 2026-07-16
    role: adversarial-review
    summary: "Zwei unabhängige externe LLM-Reviews (extern-llm-review-1, extern-llm-review-2) am 2026-07-16."
related: [platform:ADR-149, platform:ADR-261, meiki:ADR-015, dms-hub:KONZ-dms-hub-001]
supersedes: []
---

# ADR-277: Dokument-Manifest — sprachneutraler Cross-System-Deskriptor (Datenvertrag, nicht Zugriffsprotokoll)

> _Öffentliche, anonymisierte Fassung (dieses Repo ist public): konkrete LRA-/Mandanten-Namen und
> die Produkt↔Mandant-Zuordnung liegen in den privaten Repos (meiki-hub, dms-hub)._

> **Kurz (Rev 2):** Über heterogene, isoliert betriebene Mandanten (Privat=Paperless,
> Steuerkanzlei-Mandant=kommerzielles DMS, mehrere LRAs auf heterogenen on-prem-DMS) wird EIN
> sprachneutraler Vertrag geteilt — aber
> **bewusst schmal**: ein **unveränderliches Lifecycle-Referenz-Event** (stabile Identität +
> Ereignisart + Revision + Resolver-Verweis), JSON-Schema, optional als CloudEvents-Envelope. Die
> „fetten" Deskriptor-Felder (Klassifikation, Retention, Datei-Digest, Rohmetadaten) sind **optionale
> Ereignis-Profile**, die **erst bei namentlichem Consumer-Bedarf** hinzukommen. Komplementär zu
> **ADR-261** (CMIS-first DMS-*Zugriff*) und **ADR-149** (Archiv-Service). Kein geteilter Runtime,
> kein DMS-SDK.

> **Rev 2 nach zwei externen Cross-Provider-Reviews (2026-07-16).** Beide bewerteten „überarbeiten"
> (nicht ablehnen) und konvergierten unabhängig: Richtung richtig (Datenvertrag statt Code), aber
> v0.1 über-skopiert ohne semantischen/zeitlichen Vertrag. Kern-Änderung: **v0.1 auf ein dünnes,
> unveränderliches Event verengt; fette Felder deferred; Semantik-/Verarbeitungs-/Trust-/Governance-
> Vertrag ergänzt.** Rückfluss-Gate (Tagging) in §10.

## Status

`proposed`. Ausgearbeitet in `dms-hub:KONZ-dms-hub-001` (Rev 3). Schema-Entwurf v0.1
(`dms-hub:docs/konzepte/manifest/`) validiert, wird auf den verengten Rev-2-Scope nachgezogen
(Implementation Plan §9, Punkt 1 — bewusst offene Folgearbeit, hier getrackt).

## 1 · Kontext

### 1.1 Ausgangslage (geerdet, Cross-Repo)
- Drei Mandanten-Typen mit **maximaler Divergenz** (Eingang, DMS-Produkt, Verarbeitungslogik, DB);
  Deployments aus Datenhoheit isoliert. Privat=Paperless (kein Plattform-Code); Steuerkanzlei-Mandant=
  Paperless+LLM→kommerzielles DMS (GoBD 6/10 J.), umgeht den Hub für Suche; mehrere LRAs auf
  heterogenen on-prem-DMS-Produkten (je eigene Scan/OCR/KI-Kette, teils Metadaten-Sidecars).
- **ADR-261** regelt bereits den DMS-*Zugriff* (CMIS-first + Vendor-Profile + interne Fassade).
- Ein Plattform-SDK/Microkernel wurde 3-fach adversarial **verworfen** (Rule of Three; Adoption 2×
  verweigert; nicht COTS-fähig).

### 1.2 Problem / Lücke
ADR-261 löst *Zugriff*, nicht die systemübergreifende *Beschreibung*/*Ereignis-Faktizität* eines
Dokuments. Aber: der ursprüngliche „Voll-Deskriptor" (Rev 1) hätte SSoT-kritische Werte dupliziert
und ein PII-Loch geöffnet — daher der schmale Zuschnitt (Rev 2).

## 2 · Entscheidung

1. **Der geteilte Vertrag ist ein unveränderliches Lifecycle-*Event*, kein Zustands-Deskriptor.**
   Ein Manifest ist ein **Fakt „zum Zeitpunkt des Ereignisses"**, nie der aktuelle Zustand — der
   aktuelle Zustand ist **ausschließlich** eine Consumer-Projektion bzw. die Quellanwendung
   (löst „vierte Wahrheit"/Replay-Inkonsistenz). *(AD-2/AD-9/M28-4 R2; AD-1 R1)*
2. **Identitäts-Kern (Pflicht, v0.1):** `schema_ref` (unveränderliche Schema-Identität) ·
   `event_type` ∈ {ingested, classified, archived, retention_due} · `event_id` ·
   `occurred_at` · **Identitätsmodell** `{namespace, minting_system, document_id (stabil),
   source_system, source_object_id, document_revision, rendition_id?}` · `resolver_link`
   (systemlokaler Verweis auf die autoritative Quelle). *(AD-3/M28-7 R2; AD-3 R1)*
3. **Fette Felder sind optionale, versionierte Ereignis-Profile — NICHT im Kern.** `classification`,
   `retention`, `digest`, Erweiterungsblöcke kommen **erst hinzu, wenn ein namentlich benannter
   Consumer sie fordert**, je mit Pflicht/Optional/**Verboten**-Feldliste + Conformance-Tests
   pro `event_type`. Ein Universal-„Feldbeutel" ist untersagt. *(AD-10 R2; OOTB-1 R1, OOB-2 R2)*
4. **Kein freies `source_metadata`.** Ersetzt durch **namespaced, größenbegrenzte Erweiterungsblöcke
   mit eigener `schema_ref`** oder durch einen `resolver_link` auf **systemlokal** gehaltene
   Rohmetadaten. **Verboten im egress-fähigen Manifest:** Dokumentinhalt, Secrets, Zugangstoken,
   signierte URLs, nicht freigegebene Personendaten — **schema-erzwungen**, nicht als Kommentar.
   *(AD-5/M28-3 R2; AD-4/M28-2 R1)*
5. **`classification`/`retention` nur mit Autorität + Provenienz.** Kontrollierte Vokabulare **oder**
   explizit namespaced lokale Werte inkl. Mapping-Version; `retention` ist **rein beschreibend** mit
   benannter fachlicher Quelle; `retention_due` ist **keine** Löschfreigabe; Legal Hold/Korrektur/
   Aufhebung brauchen explizite Semantik. *(AD-1/M28-1/AD-13 R2; AD-5 R1)*
6. **Eine Versionsachse.** Autoritativ ist `schema_ref` (unveränderliche Referenz). Der zweite
   Suffix im CloudEvents-`type` entfällt/wird daraus abgeleitet. Je Änderungsart dokumentiert:
   Consumer darf ignorieren / muss parallel unterstützen / braucht neuen `event_type`.
   *(AD-4/M28-2 R2; AD-7 R1)*
7. **Verarbeitungs- + Trust-Vertrag (Pflicht):** Idempotenzschlüssel, Zustellsemantik, Verhalten bei
   Duplikaten/Reihenfolge/Replay/Korrektur/unbekannter Version/ungültiger Nachricht; **pro
   Deployment** authentifizierte Emitter, autorisierte Event-Typen, Integritätsschutz. Ausdrücklich:
   **das Manifest allein ist weder revisionssicherer Audit-Trail noch Beweis fachlicher Richtigkeit.**
   *(AD-6/AD-9 R2; AD-8 R1)*
8. **CloudEvents-Envelope optional** für Datei-/Outbox-Emitter (Zeremonie-Hürde senken für genau die
   Emitter, von denen das Kill-Gate abhängt); Pflicht nur auf Bus/HTTP. *(AD-8 R1)*
9. **Kein DMS-SDK, kein Provider-Port in diesem ADR.** Die d.velop-Client-Wiederverwendung wird aus
   ADR-277 **entfernt** und ist Sache einer eigenen Code-Sharing-Entscheidung bzw. ADR-261.
   *(AD-15 R2; M28-4 R1)*

## 3 · Non-Goals (verbindlich)

Der ADR autorisiert **nicht**: zentrale Metadaten-Speicherung; globale/mandantenübergreifende Suche;
mandantenübergreifende Datenübertragung; revisionssichere Archivierung (die bleibt beim DMS);
automatische Löschung. Cross-Tenant-Föderation/Reporting ist **nur** mit namentlichem Besteller **und**
dokumentierter Rechtsgrundlage zulässig — bis dahin trägt das Manifest **nur mandanteninterne**
Nutzen (Events, Audit-Baustein). *(AD-1/AD-10 R1; AD-9/AD-12/REC-16 R2)*

## 4 · Betrachtete Alternativen

| Alt | Inhalt | Bewertung |
|---|---|---|
| A0 — nichts teilen | 3 Apps, Copy-Paste | ehrlicher Fallback, wenn Kill-Gate reißt (§8) |
| A1 — Plattform-SDK/Microkernel | geteilter Code | verworfen (KONZ-001 §8b) |
| A2 (Rev 1) — Voll-Deskriptor-Manifest | fette Felder im Kern | **verworfen** — SSoT-/PII-/Scope-Probleme (beide Reviews) |
| **A3 (Rev 2, gewählt) — schmales Lifecycle-Event + optionale Profile** | Identitäts-Kern, fette Felder deferred | gewählt — kleinster dauerhafter Vertrag |
| A4 — Standard adaptieren (XÖV/XDomea, PREMIS/records-mgmt) | existierendes Vokabular als Profil | **Prüfpflicht offen** (§7) — XDomea akten-, nicht dokumentzentriert; Eignung nicht angenommen |

## 5 · Verhältnis zu ADR-261 (Reconciliation)

ADR-261 = DMS-**Zugriff** (CMIS-Kern + Vendor-Profile, LRA-scoped). ADR-277 = Dokument-**Ereignis/
Beschreibung** (plattformweit inkl. Steuerkanzlei/Privat). Beide referenzieren dieselbe interne
Fassade (`meiki:ADR-015`) als Naht; kein CMIS-/Vendor-Konzept leakt ins Manifest.

## 6 · Risiken

| Risiko | Schwere | Gegenmaßnahme |
|---|---|---|
| Totes Artefakt (keine Adoption) | hoch | operationalisiertes Kill-Gate §8 |
| PII/Secrets in Erweiterungsblöcken | hoch | schema-erzwungenes Verbot (§2.4), namespaced/größenbegrenzt, egress-Klassifikation |
| „vierte Wahrheit"/Replay-Inkonsistenz | hoch | Event-Fakt statt Zustand (§2.1), Provenienz (§2.5) |
| Schema-Drift ohne Owner | hoch | benannter Owner + Releasekanal + Conformance-Suite (§9) |
| COTS-Emittierbarkeit nur angenommen | hoch | Annahmekriterium: 2 reale E2E-Emitter-Pfade belegen (§8/§9) |
| Kompatibilitäts-Matrix explodiert | mittel | eine Versionsachse (§2.6), Profile mit Conformance-Tests |

## 7 · Offene Prüfpunkte (vor „accepted")

- **Standard-vs-Eigenbau:** dokumentierte Evaluation gegen XÖV/XDomea bzw. ein Records-/Preservation-
  Metadatenmodell (PREMIS o. ä.) — *warum* Eigenbau. *(OOTB-3 R1; OOB-3 R2)*
- **`tenant`-Feld:** fachlich begründen oder streichen — bei vollständig isoliertem Deployment +
  CloudEvents-`source` ggf. redundant; wenn, dann nur nicht-personenbezogener deployment-lokaler Code.
  *(AD-12/REC-15 R2)*
- **`digest`/Renditions:** erweiterbares Modell (Algorithmus, Wert, Hash-Gegenstand, Rendition-ID),
  optional/best-effort (kein Byte-Zwang), Cross-Tenant-Korrelation explizit entscheiden.
  *(AD-14 R2; AD-6 R1)*
- **Prototyp-Vergleich** A3 (schmal) vs. OOB-1 (Referenz-Event) an **einem realen Flow** vor
  „accepted". *(REC-18 R2)*

## 8 · Kill-Gate (operationalisiert)

Fixes Fenster **2026-07-16 → 2026-10-16** (nicht 6 Wochen — an realistische COTS-/On-prem-Release-
Zyklen gekoppelt), **plus zweites Gate 2027-01-16**. Bestanden nur bei: **zwei namentlich benannten
Systemen** (welches Produkt, welcher Emitter, **wer baut ihn**, in wessen Backlog) als **realer
Producer** UND **fachlich nutzender Consumer** über ≥ 2 unabhängige produktionsnahe E2E-Flows mit
messbarem Nutzen (Suche/Reporting/Audit-Evidenz/Integration). **Ein Validator/Test-Consumer allein
zählt nicht; plattform-interne Selbstbedienung zählt nicht.** Reißt es → A0 (getrennte Apps) bzw.
Fallback „Vokabular-Doku ohne Vertrag" (OOTB-4 R1). *(AD-8/REC-11 R2; AD-2/AD-9/M28-5 R1)*

## 9 · Implementation Plan

1. **Schema v0.1 auf Rev-2-Scope nachziehen** (Identitäts-Kern + optionale Profile), Beispiele +
   Negativtests neu — *bewusst offene Folgearbeit, hier getrackt* (dms-hub:docs/konzepte/manifest/).
2. **Owner + Governance festlegen:** Repo, Freigabe-/Reviewprozess, Releasekanal, **Offline-Verteilung
   für On-prem**, Änderungsprotokoll, Deprecation-Frist, Verfahren für lokale Erweiterungen. *(AD-11/
   M28-5 R2; M28-3 R1)*
3. **Conformance-Suite** je `event_type` (positive + mehrere negative Tests) als Onboarding-Gate.
4. **Zwei reale E2E-Emitter-Pfade** dokumentieren (Komponente, Exportformat, XML→JSON, Validierungsort,
   Fehlerablage, Verhalten bei Schema-Upgrade). *(AD-7/M28-6 R2)*
5. Standard-Evaluation (§7) + `tenant`-Entscheid + `digest`-Modell.

## 10 · Rückfluss-Gate — externe Reviews (Audit)

Zwei externe Cross-Provider-Reviews (2026-07-16), beide „überarbeiten". Adjudikation (nur `[valid]`
eingearbeitet, mit eigener Begründung — keine wörtliche Übernahme):

| Thema (Review-IDs) | Verdikt | Eingearbeitet in |
|---|---|---|
| Event-Fakt vs. Zustand trennen (R1 AD-1; R2 AD-2/AD-9/M28-4, REC-2) | [valid] | §2.1 |
| Identitätsmodell/Minter für document_id (R1 AD-3; R2 AD-3/M28-7, REC-3) | [valid] | §2.2 |
| v0.1 verengen, fette Felder deferred (R1 OOTB-1; R2 OOB-1/OOB-2, REC-9) | [valid] | §2.3 |
| `source_metadata`-PII-Loch schema-erzwingen (R1 AD-4/M28-2; R2 AD-5/M28-3, REC-5/6) | [valid] | §2.4 |
| classification/retention: Autorität+Provenienz, retention_due≠Löschung (R1 AD-5; R2 AD-1/AD-13, REC-1/13) | [valid] | §2.5 |
| Eine Versionsachse (R1 AD-7; R2 AD-4/M28-2, REC-4) | [valid] | §2.6 |
| Verarbeitungs-+Trust-Vertrag (R2 AD-6/AD-9, REC-7/8) | [valid] | §2.7 |
| CloudEvents optional für Datei/Outbox (R1 AD-8) | [valid] | §2.8 |
| d.velop-Client aus ADR entfernen (R1 M28-4; R2 AD-15, REC-17) | [valid] | §2.9 |
| Non-Goals/Föderation begrenzen (R1 AD-1/AD-10; R2 AD-9/AD-12, REC-16) | [valid] | §3 |
| Kill-Gate operationalisieren (R1 AD-2/AD-9/M28-5; R2 AD-8, REC-11) | [valid] | §8 |
| Owner/Governance/Conformance (R1 M28-3; R2 AD-11/M28-5, REC-12) | [valid] | §9.2/9.3 |
| COTS-Emittierbarkeit belegen (R2 AD-7/M28-6, REC-10) | [valid] | §9.4 |
| Standard-vs-Eigenbau (XÖV/XDomea/PREMIS) prüfen (R1 OOTB-3; R2 OOB-3, REC — ) | [valid-scoped] | §7 (Prüfpflicht, nicht Adoption) |
| tenant-Feld begründen/streichen (R2 AD-12, REC-15) | [valid] | §7 |
| digest/Rendition-Modell (R1 AD-6; R2 AD-14, REC-14) | [valid] | §7 |
| Prototyp A3 vs OOB-1 (R2 REC-18) | [valid] | §7 |
| PRO-1..6 (beide) — Steelman bestätigt | [valid, keine Änderung] | — |

Kein Befund als `[missversteht-Kontext]`/`[out-of-scope]` getaggt — die Reviews trafen durchgehend.
OOB-2 R2 „Manifest als CMIS-Projektion" bleibt bewusst außen vor (verletzt §5-Abgrenzung; als
Design-Test übernommen: was aus CMIS ableitbar ist, gehört nicht ins Manifest).

## 11 · Referenzen

- `dms-hub:KONZ-dms-hub-001` (Rev 3) · `dms-hub:docs/konzepte/manifest/` (Schema)
- `platform:ADR-261` (CMIS-first DMS-Zugriff) · `platform:ADR-149` (Archiv-API) · `meiki:ADR-015` (Fassade)

## 12 · Changelog

- **2026-07-16 (Rev 1):** Erstellt aus KONZ-dms-hub-001 Rev 3.
- **2026-07-16 (Rev 2):** Zwei externe Cross-Provider-Reviews eingearbeitet (§10). Kern: v0.1 auf
  unveränderliches Lifecycle-Event verengt; fette Felder → optionale Profile; Semantik-/Verarbeitungs-/
  Trust-/Governance-Vertrag + Non-Goals + operationalisiertes Kill-Gate ergänzt; d.velop-Client-Reuse
  entfernt; Standard-vs-Eigenbau + tenant + digest als offene Prüfpunkte.
