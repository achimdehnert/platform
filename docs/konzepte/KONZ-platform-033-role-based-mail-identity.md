---
concept_id: KONZ-platform-033
title: Rollenbasiertes Mail-Identitäts-System (Role Profile Registry)
pipeline_status: idea
tier: T2
owner: Achim Dehnert
spec_refs: []            # kein Klickdummy-Spec betroffen (Backend-/CLI-Konvention, kein UI-Flow)
adr_threshold: kein ADR (lokale Konvention in einem Repo, PR genügt) — Re-Check falls Registry org-weit verteilt wird
review_by: 2026-10-24
kill_criteria: "Bis review_by <2 Rollen real über die Registry versendet ODER ein Fehlversand (falsche Rolle/Footer) trotz Pre-Send-Gate → verworfen, zurück zu per-Skript-Signaturen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: tools/mail_agent/send_mail.py, commit_or_pr: "PR#1420", opened_in_session: true}
  - {claim_id: C2, source_path: "~/.claude/{mail.env,mail-hnu.env,graph-mail-tokens}", commit_or_pr: "n/a (maschinen-config)", opened_in_session: true}
  - {claim_id: C3, source_path: "~/.claude/iil-signature.txt", commit_or_pr: "n/a", opened_in_session: true}
created: 2026-07-24
---

# KONZ-platform-033 — Rollenbasiertes Mail-Identitäts-System

**Tier T2** — neue lokale Konvention + persistentes Artefakt (Rollen-Registry) in *einem* Repo
(`platform/tools/mail_agent`), rückbaubar durch Entfernen der Registry-Schicht. Kein T3: nicht
org-weit, kein SSoT-Reversal, keine neue Dependency/Boundary nach außen.

## Kernthese

Achims Mail-Kommunikation über mehrere Rollen (IIL GmbH geschäftlich · HNU Professor · DSB /
Datenschutzbeauftragter · dehnert.team-Assistenz) wird von **einer deklarativen Rollen-Profil-
Registry** gesteuert; die bestehenden Skripte (`send_mail`/`graph_mail`/`draft_mail`) lösen daraus
per `--role <id>` **Absender, Transport, Signatur, Design-Tokens, Ton und Governance** auf — statt
heute verstreuter Einzelregeln (iil-signature.txt, HNU-Postfach-Sonderfälle, MEiKI-nur-über-HNU).

## Ledger (Annahmen · Entscheidungen · Risiken)

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Drei Transporte existieren bereits: Graph (IIL), SMTP (dehnert.team), IMAP-Append (HNU/dehnert) — Registry muss nur **mappen**, nichts neu bauen | Annahme | C2: `mail.env`, `mail-hnu.env`, `graph-mail-tokens` in dieser Session gesichtet | verifiziert |
| A2 | Signatur ist heute **single** (`iil-signature.txt`), keine Rollen-Abstraktion; per-Rolle-Regeln leben als verstreute Memory-Feedbacks | Annahme | C3: nur eine Signaturdatei vorhanden | verifiziert |
| A3 | Achims reale Rollen sind IIL-GF-nah (geschäftl.), HNU-Professor, DSB, dehnert.team | Annahme | H — Owner bestätigen (Tipp-Lesart „EIL"→IIL, „HNO"→HNU) | offen |
| D1 | Registry = **eine YAML `~/.claude/mail-roles.yaml`** (personenbez. Adressen/Kanäle bleiben lokal, wie `mail-*.env`); Templates + Design-Tokens **im Repo** unter `tools/mail_agent/roles/` | Entscheidung | D — Alt: alles im Repo → verworfen (Adressen/Transport gehören nicht ins Repo, Hardcoding-Verbot) | gesetzt |
| D2 | Ein `--role <id>`-Flag; Profil resolved `{from, transport, signature_template, design_tokens, tone_guide, legal_footer, requires_legal_footer}` | Entscheidung | D | gesetzt |
| D3 | **Ein** Design-System „Klare Linie" mit Rollen-Tokens (accent, monogram, legal_footer) — nicht vier getrennte Designs | Entscheidung | D — heutiges HTML-Template (Klare Linie) als Basis | gesetzt |
| R1 | Legal-Footer je Rolle ist **compliance-kritisch** (§35a-Pflichtangaben, DSB-Vertraulichkeit, HNU) — falscher Footer = Rechtsfehler | Risiko | Mitig.: `requires_legal_footer` als Pflichtfeld, Loader blockt Versand ohne Footer | offen |
| R2 | **Rollen-Verwechslung** (falscher Absender/Ton an falschen Adressaten, z.B. DSB-Sache mit dehnert.team-Absender) | Risiko | Mitig.: `--role` Pflicht (kein Silent-Default), Pre-Send-Gate zeigt Rolle+Absender+Footer | offen |
| R3 | **Zweite Wahrheit** — Registry dupliziert Transport-Config aus `mail-*.env` | Risiko | Mitig.: Registry referenziert Transport per **Key**, kopiert nie Credentials (SSoT bleibt `mail-*.env`/`~/.secrets`) | offen |

## MVC (konkreter Plan — Dateien/Felder/Gate)

1. **`~/.claude/mail-roles.yaml`** — `roles: {iil, hnu, dsb, dehnert_team}` je mit
   `display_name, from, transport (graph|smtp|imap_append), signature_file, accent, legal_footer_file,
   tone, requires_legal_footer`. Transport nur als **Key** (Auflösung via bestehende `mail-*.env`).
2. **`tools/mail_agent/roles.py`** — Loader + Resolver (`role_id → profile`) + Validierung
   (Pflichtfelder; `requires_legal_footer=true` ohne `legal_footer_file` → Fehler, kein Versand).
3. **`tools/mail_agent/templates/klare-linie.html.j2`** — ein Outlook-festes Tabellen-Template,
   Rollen-Tokens (`accent`, `monogram`, `signature`, `legal_footer`).
4. **`--role <id>`** in `send_mail.py` (dann `draft_mail`/`graph_mail`): resolved
   from/transport/signature/footer; **Pre-Send-Gate** zeigt Rolle · Absender · Footer vor Versand.
5. **Signaturen**: `iil-signature.txt` (bestehend) + neu `hnu-signature.txt`, `dsb-signature.txt`,
   `dehnert-signature.txt` in `~/.claude/`.
6. **Tests** (`test_roles.py`): Resolution je Rolle, `requires_legal_footer`-Enforcement,
   Template-Render pro Rolle, Transport-Key-Auflösung ohne Credential-Kopie.

## Befunde inkl. Advocatus Diabolus

| id | Befund | Antwort / Härtung |
|---|---|---|
| AD1 | Registry wird faktisch zur **Boundary** — jedes Mail-Skript muss sie kennen | Nur 3 Konsumenten (send/draft/graph), klein & repo-lokal; kein externer Konsument |
| AD2 | `requires_legal_footer` ist **manuelle Pflicht ohne Enforcement** | Ehrlich: Enforcement = **Loader-Validierung (Exit-Code)**, nicht nur Doku — Versand bricht ab ohne Pflicht-Footer |
| AD3 | „Rolle sichtbar machen" (Gate zeigt Rolle) ist **schwächer als verhindern** | Ergänzt: `--role` ist **Pflicht** (kein Default) → kein stiller Fehlversand; Gate ist die zweite Schicht |
| AD4 | Design-Tokens im Repo, Adressen lokal → **gespaltene Quelle** pro Rolle | Bewusst: statische/teilbare Teile (Design) versioniert, personenbez./geheime Teile (from/footer-Inhalt) lokal — dieselbe Trennung wie `mail.env` heute |

## Alternativen

| Alt | Beschreibung | Warum verworfen |
|---|---|---|
| ALT1 | **Status quo** — per-Skript-Signaturen + Memory-Regeln | Skaliert nicht auf 4 Rollen; Fehlversand-Risiko (R2) bleibt ungemindert; Design nicht wiederverwendbar |
| ALT2 | **Vier Skript-Wrapper** (`send-iil`, `send-hnu`, `send-dsb`, …) | Copy-Paste-Drift; kein gemeinsames Design-System; jede Änderung 4× |

## Top-3 Risiken

1. **R1 Legal-Footer** (compliance-kritisch) → Loader-Enforcement `requires_legal_footer`.
2. **R2 Rollen-Verwechslung** → `--role` Pflicht + Pre-Send-Gate.
3. **R3 Zweite Wahrheit** → Transport nur per Key referenzieren, keine Credential-Kopie.

## Entscheidung + Kill-Gate

**Empfehlung:** MVC bauen, mit **IIL** und **dehnert.team** starten (beide heute schon aktiv),
HNU + DSB nachziehen sobald deren Signatur-/Footer-Inhalte vom Owner freigegeben sind.

**Kill-Gate (messbar):**

| Kriterium | Status (offen/erfüllt/verworfen) | Beleg |
|---|---|---|
| Bis 2026-10-24 ≥2 Rollen real über die Registry versendet | offen | — |
| Kein Fehlversand (falsche Rolle/Footer) trotz Gate im Zeitraum | offen | — |
| `requires_legal_footer`-Enforcement greift (Test grün + 1 realer Abbruch belegt) | offen | — |

**Exception-Budget:** 1× Verlängerung um 30 Tage (bis 2026-11-23) erlaubt; danach ohne erfülltes
Kriterium → `sunset` + Rückbau auf per-Skript-Signaturen.

**Enforcement-Grenze (ehrlich):** Dieses Konzept beschreibt das System; die Lifecycle-Felder
(`review_by`/`kill_criteria`) wirken erst, wenn ein Konzept-Lifecycle-Gate sie liest — bis dahin
Review-Gate, kein Exit-Code.
