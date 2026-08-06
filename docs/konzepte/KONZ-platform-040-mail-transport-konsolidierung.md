---
concept_id: KONZ-platform-040
title: "Mail-Transport: Kante härten statt Bibliothek bauen — Konsolidierungs-Entscheid zu platform#1791"
pipeline_status: idea
tier: T3
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "MVC-1 (Wheel statt Mount) = kein ADR — vollendet den im Runbook mail-ingest-prod.md benannten Weg (a) nach bestehendem Muster (platform-context-Wheel). NUR falls später ein zentraler Vorgangsspeicher gebaut wird: Amendment an ADR-286 §4.9 zwingend (Befund D4)."
review_by: "2026-11-06"
kill_criteria: "MVC-1 wird abgebrochen/zurückgebaut, wenn der Wheel-Umbau >3 PT frisst ODER den 03:30-Ingest >7 Tage destabilisiert. Wiedervorlage O1-Vollbibliothek NUR, wenn bis 2027-02-06 ≥2 weitere belegte Cross-Repo-Doppel-Fixes auflaufen (Zähler startet bei 0; der Zitat-Fix voice-agent zählt als 1, wenn dieselbe Klasse dort erneut extern auffällt)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "dev-hub/docker-compose.prod.yml:100-130 (:ro-Mount, MAIL_GRAPH_CREDS, dev-hub#206-Kommentar)", commit_or_pr: "geöffnet", opened_in_session: true}
  - {claim_id: C2, source_path: "dev-hub/apps/mail_agent/graph.py:1-24 (Owner-Entscheid 2026-07-31 Client-Credentials, FELDER ohne body per ADR-286 §4.5)", commit_or_pr: "geöffnet", opened_in_session: true}
  - {claim_id: C3, source_path: "dev-hub/apps/mail_agent/adapters.py:1-50 (gate-freier Stub-Claim im Docstring, References-Threading)", commit_or_pr: "geöffnet", opened_in_session: true}
  - {claim_id: C4, source_path: "iil-voice-agent/src/voice_agent/mcp_mail/core.py:1-45 + adapters/imap_email_source.py:1-35 (stdlib-Entscheid, Betreff-Threading als Entscheid, ADR-249 G-1)", commit_or_pr: "geöffnet", opened_in_session: true}
  - {claim_id: C5, source_path: "platform/docs/adr/ADR-293 Kopf+§1 (Zwei-Repo-Schnitt, Maxime Verfügbarkeit, 4/15123-Befund)", commit_or_pr: "geöffnet", opened_in_session: true}
  - {claim_id: C6, source_path: "platform/tools/mail_agent/suche.py:1-25 (SSH-Brücke ADR-288 §4.7)", commit_or_pr: "geöffnet", opened_in_session: true}
  - {claim_id: C7, source_path: "dev-hub/apps/mail_agent/management/commands/mail_ingest.py:35-44 + mail_volltext.py:53-66 (sys.path-Import von read_mail aus dem Mount, Begründung 'zweimal pflegen war keine Option')", commit_or_pr: "geöffnet (Diabolus-Agent, diese Session)", opened_in_session: true}
  - {claim_id: C8, source_path: "platform PR #1555 (Reply-Threading: Änderungen NUR in tools/mail_agent) + tools/mail_agent/send_mail.py Commit e61973f5 (Empfänger-Beschwerde 2026-07-27 wörtlich im Code-Kommentar)", commit_or_pr: "#1555 / e61973f5", opened_in_session: true}
  - {claim_id: C9, source_path: "iil-voice-agent mcp_mail/core.py:236-241 (build_reply_draft: In-Reply-To/References korrekt, aber set_content OHNE Zitat)", commit_or_pr: "geöffnet (Diabolus-Agent, diese Session)", opened_in_session: true}
  - {claim_id: C10, source_path: "dev-hub/docs/runbooks/mail-ingest-prod.md §2 (Weg (a) 'als Wheel, dem vorhandenen Muster folgend' benannt, verworfen nur weil 'heute kein installierbares Paket')", commit_or_pr: "geöffnet (Maintainer-Agent, diese Session)", opened_in_session: true}
created: "2026-08-06"
---

# KONZ-platform-040 — Mail-Transport: Kante härten statt Bibliothek bauen

> Auftrag: platform#1791 („Transport genau 1×, Schnitt Bibliothek vs. Mount vs. Paket").
> T3 wegen Cross-Repo (platform, dev-hub, iil-voice-agent). Drei unabhängige
> Adversarial-Agenten (Steelman / Advocatus Diabolus / Maintainer-2028), Synthese mit
> Konfliktmatrix (§6). Evidenz: E = in dieser Session geöffnet (Manifest), H = Hypothese.

## 1 Executive Summary

Die Ausgangsdiagnose „Transport existiert 3×, also konsolidieren" hält der Erdung
**nicht stand**: dev-hub importiert den IMAP-Transport bereits heute aus platform
(C7) — die Konsolidierung ist dort *passiert, aber vertragslos* —, und die zwei
verbleibenden Differenzen sind **dokumentierte Entscheide**, keine Drift (C2, C4).
Das reale, von allen drei Adversarial-Agenten unabhängig benannte Risiko ist die
**ungepinnte Laufzeit-Kopplung dev-hub-Prod → platform-Host-Checkout** (C1, C7):
ein `git pull` auf dem Prod-Host ist dort ein ungetesteter Prod-Deploy.
**Empfehlung: O5 „Kante härten" — Wheel + Kontrakt-Test statt Mount; kein
Bibliotheks-Neubau, kein PyPI, voice-agent bleibt eigenständig** (plus zwei kleine
portierte Fixes und eine State-Triage). Aufwand ~3–4 PT statt 8–10 PT.

## 2 Scope & Evidenzbasis

In-Scope: die drei Transport-Implementierungen (platform `tools/mail_agent`,
dev-hub `apps/mail_agent`, voice-agent `mcp_mail`/`imap_email_source`), deren
Kopplungen, sowie die State-/Konfig-Streuung unter `~/.claude`. Out-of-Scope:
Recherche-/Index-Architektur (ADR-288/293 laufen), Rollen-Design (KONZ-033),
App-eigener Django-`send_mail` der Business-Hubs. Evidenzbasis: Manifest C1–C10;
zusätzlich `bodystructure.py`, `vorgang.py`, systemd-Units (durch Agenten geöffnet).

## 3 Infrastruktur-Fit

- ADR-293 kanonisiert den Zwei-Repo-Schnitt „Entscheidung platform, Umsetzung
  dev-hub-App + platform-Tools" (C5) — O5 ändert daran nichts, er macht die
  bestehende Kante explizit.
- Das Runbook `mail-ingest-prod.md` benennt selbst Weg (a) „als Wheel, dem
  vorhandenen Muster folgend" und verwarf ihn nur, weil `tools/mail_agent` noch
  kein Paket ist (C10) — O5 ist die Vollendung des eigenen Plans, kein Sonderweg
  (Konvergenz-Ratsche Art. 16 erfüllt).
- platform ist PUBLIC: der Transport-Code liegt heute schon öffentlich; ein Wheel
  ändert die Sichtbarkeit nicht. Echtdaten (mail-roles.json, Ordner-Mappings)
  bleiben wie bisher außerhalb des Repos.

## 4 Steelman der Voll-Konsolidierung (O1)

Stärkste Fassung (Steelman-Agent): Die drei Systeme teilen RFC-822/IMAP/Graph-
Mechanik; real belegte Doppelarbeit existiert — Reply-Threading wurde asynchron
3× behandelt, mit echtem Außenschaden (Empfänger-Beschwerde 2026-07-27, C8), und
die teuer gelernte Lektion „Betreff trägt die Strang-Bildung nicht" (platform
#1623) lebt in voice-agent als Gegen-Design weiter (C4). Ein gemeinsamer Kern
(IMAP-Primitiven, Envelope-Normalisierung, MIME-Reply-Builder, zwei Graph-Auth-
Strategien hinter einer Naht) hätte den Vorfall verhindert; der Prod-Mount
beweist, dass die Bibliotheks-Architektur implizit schon gewollt ist (C1).
Aufwand ehrlich 8–10 PT, phasenweise shippbar.

## 5 Konzeptdefinition (empfohlene Option O5)

**O5 = „Kante härten":**

1. **MVC-1 — Wheel statt Mount:** `platform/tools/mail_agent` bekommt ein
   `pyproject.toml` (Paketname z. B. `iil-mail-tools`, repo-lokal gebaut, KEIN
   PyPI); dev-hub-Image installiert das Wheel versioniert, der `:ro`-Mount und
   `sys.path.insert` entfallen. Dazu **ein Kontrakt-Test in dev-hub-CI**, der
   exakt die von `mail_ingest`/`mail_volltext` konsumierte API-Oberfläche gegen
   die gepinnte Version prüft (heute: nur Stubs, C7). Abnahme: ein echter
   Prod-Ingest-Lauf (Gate claim-before-cheapest-check).
2. **MVC-2 — dev-hub-interne Wahrheit herstellen:** Entscheid, welcher der zwei
   internen Ingest-Pfade der echte ist (`management/commands`-Pfad ist es;
   `adapters.py`+`tasks.py.ingest_delta` ist ein Synthetik-Skelett mit stalem
   Gate-Claim im Docstring, C3) — Skelett verdrahten ODER entfernen, Docstring
   korrigieren.
3. **MVC-3 — zwei portierte Fixes statt geteiltem Code:** (a) Zitat-Erhalt im
   voice-agent-Reply-Draft (Fehlerklasse aus #1555; dort heute `set_content`
   ohne Zitat, C9) im dortigen Idiom; (b) die #1623-Threading-Lektion als Issue
   im voice-agent dokumentieren (Betreff-Threading bleibt dortiger Entscheid,
   aber mit Kenntnis der Falsifikation).
4. **MVC-4 — State-Triage `~/.claude` (Inventar statt neuem Speicher):**
   sichern (verschlüsseltes Backup, nie public): `mail-vorgaenge.json`,
   `mail-links.json`, `mail-anker.json`, `mail-roles.json`, `mail-folders.env`;
   lokal ok: `mail-cache/`, Logs, Token-Verzeichnisse (Secrets bleiben lokal);
   dazu EINE Inventar-Seite „Datei → Konto/Transport/Art". Hand-`.bak`-Kopien
   durch Atomic-Write ersetzen. **Kein neuer Vorgangsspeicher** — der wäre die
   4./5. Vorgangs-Quelle gegen den ADR-286-§4.9-Entscheid „Ordnername ist die
   Vorgangskennung" (Befund D4); falls doch gewollt → eigenes ADR-286-Amendment.

**Non-Goals (bewusster Machtverzicht, Kill-Kriterium e der Charta):** kein
PyPI-Paket (O2), keine Zwangs-Anbindung des voice-agent an eine gemeinsame
Bibliothek (KONZ-002/003 + ADR-249 G-1 bleiben unangetastet), keine
Formalisierung des Mounts (O3), keine Rückabwicklung des Client-Credentials-
Entscheids 2026-07-31 (C2).

## 6 Adversariale Analyse — Konfliktmatrix (Pflicht)

| # | Dissens | Steelman | Diabolus | Maintainer-2028 | Synthese-Entscheid |
|---|---|---|---|---|---|
| K1 | Beweiskraft der Drift | „3× gebaut, 1 Außenschaden → Bibliothek" | „Kein Fix wurde 3× gemacht; #1555 betraf nur platform; voice-agent hatte Header vorher korrekt → 1 portierter Fix reicht" | — | Diabolus gewinnt auf der Faktenlage (C8: #1555-Diff nur tools/): Schaden rechtfertigt Fix-Portierung (MVC-3), keine Bibliothek |
| K2 | Umfang der Konsolidierung | O1 voll, inkl. voice-agent (8–10 PT) | Nur dev-hub↔platform-Kante härten | O1 modifiziert: Wheel ja, voice-agent nur Kontrakt-Test | Konvergenz bei „Kante härten" = O5; voice-agent out of scope |
| K3 | Vorgangsspeicher | (aus #1791 übernommen) | Wäre 4./5. Quelle, bricht ADR-286 §4.9 | mail-vorgaenge.json MUSS gesichert werden (Ziel KONZ-dev-hub-004 existiert) | Triage + Backup statt neuem Speicher; SSoT-Frage nur per ADR-Amendment (MVC-4) |
| K4 | Graph-Vereinheitlichung | Zwei Auth-Strategien hinter einer Naht | Feld-Zuschnitt divergiert bewusst (body vs. kein body, C2) und ADR-293 pivotiert genau diese Stelle | Beide Clients dokumentiert verschieden; Inventar der 2 App-Registrierungen nötig | Vertagt bis ADR-293 accepted+umgesetzt; heute nur Registrierungs-Inventar (§7) |

Konsens aller drei (kein Dissens): die ungepinnte Mount-Kante ist das reale
Risiko; „Drift-Wächter allein" (O4 solo) ließe genau sie bestehen.

## 7 Deep-Dive: Betriebs-Befunde jenseits des Schnitts (Maintainer-2028)

- **B1 (zeitgesteuert):** Entra-Client-Secret der Ingest-App-Registrierung
  (2026-07-31) läuft ≤ 24 Monate → Ausfall „invalid_client" spätestens ~2028-07;
  kein Ablaufdatum, kein Rotations-Runbook dokumentiert (H bzgl. exaktem Datum;
  billigster Check: Entra-Portal). → Inventar-Seite beider App-Registrierungen
  (IDs, Scopes, Ablauf, Creds-Fundort als Zeiger) anlegen.
- **B2 (SPOF):** mail.iil.pet läuft als User-systemd + cloudflared auf der
  Workstation; `ConditionPathExists` lässt die Unit bei verschobenem Checkout
  kommentarlos verschwinden; Link-Tokens nur in `mail-links.json`. → Standort-
  Entscheid dokumentieren („Workstation-SPOF akzeptiert bis X / Migration Y").
- **B3 (Alarmierung):** ImportError des 03:30-Ingest landet im Celery-Log;
  Alert-Routing nicht belegt (H; billigster Check: Logging-/Sentry-Config).

## 8 Alternativen

| Option | Kern | Verdikt |
|---|---|---|
| O1 Vollbibliothek | gemeinsamer Kern, 3 Konsumenten | verworfen: wickelt 2 dokumentierte Entscheide ab, 8–10 PT gegen unbewiesene Doppel-Fix-These (K1), friert Schnittstelle ein, die ADR-293 gerade umbaut (K4) |
| O2 PyPI | wie O1, öffentlich versioniert | verworfen: Release-Reibung ohne zweiten flottenexternen Konsumenten; kein iil-Mail-Paket existiert (geprüft — kein Re-Inventions-Fall) |
| O3 Mount formalisieren | Status quo + Doku | verworfen: adelt ungetestete Host-Pull-Deploys („gut dokumentiertes Problem statt keines") |
| O4 Nicht-Konsolidierung + Wächter | Kontrakt-Tests über 3 Impl. | teilweise übernommen (Kontrakt-Test in MVC-1); solo verworfen, weil die Mount-Kante bestehen bliebe |
| **O5 Kante härten** | Wheel+Pin+Kontrakt-Test, 2 portierte Fixes, State-Triage | **empfohlen** |

## 9 Out-of-the-Box

Der Diabolus-Befund „dev-hub behauptet eine SSoT, die Prod umgeht" (C3) ist
generalisierbar: ein billiger Fleet-Check „Docstring-Claims vs. tatsächliche
Konsumenten" (grep nach ‚SSoT'/‚gate'-Claims + Import-Graph) würde solche stalen
Selbstbeschreibungen systematisch finden. Nicht Teil dieses Konzepts; Kandidat
für /platform-audit.

## 10 Befunde

| ID | Befund | Evidenz |
|---|---|---|
| D1 | dev-hub-Prod importiert platform-Code zur Laufzeit ungepinnt; CI testet nur Stubs | C1, C7 |
| D2 | Graph-Differenz ist Owner-Entscheid (Weg B, 2026-07-31), keine Drift | C2 |
| D3 | voice-agent: Threading-Semantik + stdlib-Politik sind Entscheide; Reply-Draft ohne Zitat = latente #1555-Klasse | C4, C9 |
| D4 | „Vorgang" existiert 3–4× mit Entscheid pro Ordnername (ADR-286 §4.9); neuer Speicher wäre zusätzliche Quelle | vorgang.py (Agent), C3 |
| D5 | adapters.py-Docstring behauptet Gate-Stub, Prod ingestiert längst am adapters-Pfad vorbei | C3, C7 |
| D6 | Secret-Ablauf/SPOF/Alarmierung: drei Betriebs-Untiefen unabhängig vom Schnitt | §7 |

## 11 Top-5-Risiken (der Empfehlung O5)

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R1 | Wheel-Umbau destabilisiert 03:30-Ingest | Abnahme = 1 echter Prod-Lauf; Kill-Gate 7 Tage |
| R2 | Kontrakt-Test prüft die falsche Oberfläche | Oberfläche aus realen Imports von mail_ingest/mail_volltext ableiten (C7), nicht raten |
| R3 | „Kante härten" versandet, Mount bleibt „vorläufig" | teuerste Nicht-Entscheidung (Maintainer); Kill-Gate-Tabelle §13 trackt MVC-1 datiert |
| R4 | voice-agent-Fix (Zitat) driftet erneut, weil kein geteilter Code | bewusst akzeptiert; Zähler im Kill-Gate (≥2 neue Doppel-Fixes → O1-Wiedervorlage) |
| R5 | State-Backup (MVC-4) landet versehentlich im public Repo | Backup-Ziel explizit privat (dev-hub/`~/.secrets`-Muster); Personendaten-Grep als Pre-Commit-Probe |

## 12 Empfehlungen (konkret, verifizierbar)

1. `platform/tools/mail_agent/pyproject.toml` anlegen; dev-hub-Dockerfile
   installiert das Wheel; `docker-compose.prod.yml` Z. 124/169-Mounts entfernen;
   `mail_ingest.py`/`mail_volltext.py` von `sys.path.insert` auf Paket-Import.
2. dev-hub-CI: `test_mail_tools_contract.py` — importiert exakt die konsumierten
   Symbole aus dem installierten Wheel (kein Stub).
3. dev-hub: `adapters.py`-Docstring-Claim korrigieren + `tasks.ingest_delta`-
   Skelett entweder an den echten Pfad verdrahten oder löschen.
4. voice-agent: Zitat im `build_reply_draft` ergänzen (dortiges Idiom); Issue
   „#1623-Lektion: Betreff-Threading falsifiziert" anlegen.
5. `~/.claude`-Mail-State: Inventar-Seite + verschlüsseltes Backup der 5
   Muss-Dateien; Atomic-Write-Helfer statt Hand-`.bak`.
6. Betriebs-Inventar: beide Entra-App-Registrierungen mit Secret-Ablauf +
   Rotations-Runbook; mail.iil.pet-Standort-Entscheid dokumentieren.

## 13 Entscheidung + Kill-Gate + 30/60/90

**Zur Ratifikation:** O5 annehmen; O1/O2 verwerfen mit Wiedervorlage-Bedingung;
#1791-Checkliste auf die MVC-1..4 umschreiben.

30 Tage: MVC-1 + MVC-2 (inkl. 1 Prod-Ingest-Abnahme). 60 Tage: MVC-3 + MVC-4.
90 Tage: Betriebs-Inventar (Empf. 6) + Review dieses KONZ (review_by 2026-11-06).

| Kriterium | Status | Beleg |
|---|---|---|
| Wheel-Umbau ≤3 PT, Ingest ≤7 Tage stabil (sonst Rückbau) | offen | — |
| Kontrakt-Test läuft in dev-hub-CI gegen echtes Wheel | offen | — |
| Doppel-Fix-Zähler <2 bis 2027-02-06 (sonst O1-Wiedervorlage) | offen (Stand 0) | — |
| MVC-4-Backup existiert, 0 Personendaten im public Repo | offen | — |
| Betriebs-Inventar (2 App-Registrierungen, SPOF-Entscheid) | offen | — |

**Enforcement-Grenze (ehrlich):** review_by/kill_criteria wirken als
Review-Gate, kein CI-Exit-Code — das Lifecycle-Gate existiert noch nicht.
