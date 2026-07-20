---
concept_id: KONZ-platform-012
title: "platform-Meta-Repo (SSoT) vom User-Konto achimdehnert in die iilgmbh-Org heben — phasen- und vorbedingungs-gegatet"
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: Amendment (ADR-255 verweist auf platform als Nicht-Ziel; Transfer selbst = KONZ-002-S3-Fall, ggf. eigener ADR bei Transfer-Entscheid)
review_by: 2026-09-15
kill_criteria: "Wenn bis 2026-09-15 die Coupling-Indirektion (repointbare Alias-Stelle für reusable-workflow-Refs, KONZ-002 OOTB-5) NICHT existiert ODER der PyPI-org iil kein verifizierter 2. Owner ist, wird KEIN platform-Transfer terminiert — Konzept bleibt in Phase A (reversible Bus-Faktor-Maßnahmen) oder sunset. Der Transfer selbst ist nie ohne grünen Consumer-CI-Lauf gegen `uses: iilgmbh/platform/...@main` freigegeben."
superseded_by_spec: null
created: 2026-07-05
evidence_manifest:
  - {claim_id: C1, source_path: "registry/iil-migration.yaml", commit_or_pr: "line 116 dependencies:[platform,dev-hub]", opened_in_session: true}
  - {claim_id: C2, source_path: "docs/runbooks/KONZ-002-s3-repo-transfer.md", commit_or_pr: "line ~103 Nicht-in-dieser-Welle", opened_in_session: true}
  - {claim_id: C3, source_path: "docs/adr/ADR-255-iilgmbh-org-migration-pypi-family.md", commit_or_pr: "REC-1 line 92-105, REC-13 line 233-235", opened_in_session: true}
  - {claim_id: C4, source_path: ".github/workflows/", commit_or_pr: "10 aktive self-hosted Workflows (grep runs-on:self-hosted, ohne _ARCHIVED)", opened_in_session: true}
  - {claim_id: C5, source_path: "gh api repos/achimdehnert/platform/actions/runners", commit_or_pr: "total_count=1 (prod-server)", opened_in_session: true}
  - {claim_id: C6, source_path: "gh secret list --repo achimdehnert/platform", commit_or_pr: "15 Secrets", opened_in_session: true}
  - {claim_id: C7, source_path: "gh api orgs/iilgmbh/members?role=admin", commit_or_pr: "length=2 (achimdehnert,wirdigital) 2026-07-05", opened_in_session: true}
---

# KONZ-platform-012 — platform-SSoT in die iilgmbh-Org heben (phasen-/vorbedingungs-gegatet)

> **Tier T3** — harte Begründung: SSoT-Verschiebung (Registry/ADRs/Workflows) · Cross-Repo-Impact (~14 Caller der reusable Workflows) · irreversibler Org-Transfer (Reversal) · Security-Perimeter (15 Secrets, OIDC-Trust-Anchor). Jeder einzelne Trigger erzwingt T3; hier greifen vier.

## 1. Executive Summary

Die strategische **Richtung** — platform aus dem persönlichen Konto `achimdehnert` in die Org `iilgmbh` — ist tragfähig und konsistent mit ADR-255/KONZ-002. Aber die Ausgangsfrage „sollte platform migriert werden?" ist bereits beantwortet und **bewusst zurückgestellt**: Der KONZ-002-S3-Transfer-Runbook schließt komplex-gekoppelte Repos ausdrücklich aus der laufenden Welle aus (C2), und platform ist der am stärksten gekoppelte Fall überhaupt — es *ist* die Quelle der reusable Workflows, die die ~14 Caller konsumieren.

**Kernaussage:** Der Blocker ist nicht „ob", sondern **zwei konkrete Vorbedingungen** und ein **hohes Ausführungsrisiko** des rohen Transfers. Der frisch erfüllte 2. GitHub-Owner (C7) klärt nur die **halbe** REC-1-Bedingung (C3); die andere Hälfte (PyPI-org `iil` 2. Owner, Leaver-/Recovery-Prozess, Team-Rollen) ist offen. Ein sofortiger Transfer bräche 10 self-hosted-Workflows (Runner-Neuregistrierung), entleerte 15 Secrets, verletzte den OIDC-`repository_owner`-Claim und ist „Einbahn-Exit" (Rollback = zweiter Incident).

**Empfehlung (Vorgriff auf §12/§13):** **Kein Transfer jetzt.** Stattdessen dreiphasig: **Phase A** (jetzt, reversibel, ohne Transfer) holt ~80 % des Bus-Faktor-Nutzens; **Phase B** baut die Vorbedingung (Coupling-Indirektion + PyPI-Owner); **Phase C** ist der gegatete Transfer mit Runner-Reprovisionierungs-Runbook, Secret-Inventar und grünem Consumer-CI-Beweis.

## 2. Scope & Evidenzbasis

**In-Scope:** GitHub-Transfer `achimdehnert/platform` → `iilgmbh/platform`; die daran hängende Verdrahtung (Runner, Secrets, Refs, OIDC, Webhooks).
**Out-of-Scope:** Die iil-* PyPI-Familien-Migration (ADR-255, läuft separat); Enterprise-Kostenkonsolidierung (KONZ-002 Kern, verwandt).

Geerdete Ist-Fakten (alle in dieser Session verifiziert, s. evidence_manifest):
- platform ist **kein ADR-255-Migrationsziel**, nur Konsument (`dependencies:[platform,dev-hub]`, C1).
- **10 aktive** self-hosted-Workflows (+1 archiviert), **1 Runner** `prod-server` auf Repo-Ebene registriert (C4/C5). *Korrektur der Auftrags-Annahme „11" — die zählte das archivierte mit; die kursierende „8" war zu niedrig.*
- **15 Repo-Secrets** inkl. `PLATFORM_DEPLOY_TOKEN`, `HETZNER_*`, `SOPS_AGE_KEY`, `PYPI_API_TOKEN`, `DEVHUB_WEBHOOK_SECRET` (C6).
- **14 Workflow- + 77 md- + 19 tools/scripts-Dateien** mit hartkodiertem `achimdehnert/platform`.
- iilgmbh: **2 Owner** (C7); PyPI-org `iil` 2. Owner **nicht verifiziert** (keine GitHub-API-Fläche — H).
- `iilgmbh/platform` existiert noch nicht (Name frei).

## 3. Infrastruktur-Fit

platform ist die einzige tragende SSoT, die per Rolle Governance für andere definiert (Rulesets, reusable Workflows, Registry) und selbst außerhalb der Org-Governance-Fähigkeiten liegt. Der Fit ist real — aber die Kopplung ist genau der Grund, warum KONZ-002-S3 (C2) diese Klasse zurückstellt, bis eine **repointbare Alias-Stelle** (OOTB-5) existiert, die die ~14 Caller entkoppelt.

## 4. Steelman (stärkster Pro-Fall, ungehedged)

1. **Personen-Konto-Risiko ist konkret:** Account-Kompromittierung/Handlungsunfähigkeit/2FA-Verlust an `achimdehnert` legt die SSoT des *gesamten* Ökosystems lahm — größerer Blast-Radius als jedes Package-Repo.
2. **Org-Fähigkeiten existieren am User-Konto strukturell nicht:** Owner-Mehrzahl, Teams mit granularen Rollen, org-weite Rulesets/Required-Workflows, zentrale Security-Config, Nachfolge.
3. **Zeitfenster offen:** 2. GitHub-Owner ist gerade erfüllt; ADR-255 bewegt ohnehin die halbe Familie; iilgmbh hält schon 12+ Repos.
4. **Redirects erhalten History/Issues/PRs/Stars** und fangen `git clone`/`gh`/Web-Links — Sicherheitsnetz-Fenster statt Hard-Cut.
5. **Konsistenz-Kosten kumulieren:** Jede neue ADR/Workflow/Referenz verankert den alten Pfad tiefer; eine SSoT, die die eigene Regel nicht auf sich anwendet, untergräbt deren Glaubwürdigkeit.

## 5. Konzeptdefinition — der phasen-gegatete Pfad

**Phase A — Bus-Faktor JETZT, reversibel, ohne Transfer** (holt ~80 % des Nutzens):
- PyPI-org `iil` 2. Owner verifizieren/hinzufügen (schließt die offene REC-1-Hälfte, die der Transfer NICHT löst).
- Leaver-/Recovery-/Owner-Matrix für platform schreiben (REC-1/REC-9-Muster, aber für den Normalfall Owner-Ausfall — existiert bisher nur für den PyPI-Break-Glass).
- CODEOWNERS + Branch-Protection „Required Reviewer = 2. Mensch" auf platform (Zugriffsredundanz ohne Transfer).
- Trockenspiegelung: Runner zusätzlich in einen **Org-Runner-Pool** + Secrets als **Org-Secrets** anlegen — testet die Ziel-Verdrahtung, ohne das Repo zu verschieben.

**Phase B — Vorbedingung (der eigentliche Blocker):**
- Coupling-Indirektion (KONZ-002 OOTB-5): eine repointbare Alias-Stelle für die reusable-workflow-Refs, sodass die ~14 Caller beim Transfer nicht brechen.
- Runner-Reprovisionierungs-Runbook (existiert für platform noch nicht; KONZ-002-S3 kennt nur Secrets/Webhooks/Deploy-Keys).

**Phase C — Transfer, gegatet:**
- Nur nach A+B, mit Pre-Transfer-Secret-Inventar (Schema A), Runner-Runbook, und **grünem Consumer-CI-Lauf gegen `uses: iilgmbh/platform/...@main`** als Identitätsbeweis (REC-6-Grundsatz: Dry-Run beweist nicht Identität).
- REC-13 anwenden: Redirect-Gnadenfrist + automatischer Stale-Ref-Checker (`tools/`-Skript analog `iil_migration_check.py`, WARN→FAIL nach N Wochen).

## 6. Adversariale Analyse + Konfliktmatrix

Drei blinde Agenten (Steelman/Advocatus Diabolus/Maintainer-2028), danach Synthese.

**Konfliktmatrix (belegte Dissense):**

| # | Streitpunkt | Steelman | Advocatus Diabolus | Maintainer-2028 | Auflösung (Evidenz) |
|---|---|---|---|---|---|
| K1 | Reichen Redirects? | „praktisch risikofrei für Refs" | „fangen NICHT OIDC-Claim, PAT-Scopes, Webhook-Filter, raw.githubusercontent" | „werden stille Schuld ohne REC-13-Gate" | **Diabolus+Maintainer gewinnen** — REC-13 (C3) existiert *genau weil* Redirects unzureichend sind; OIDC-`repository_owner` ist String-Claim, kein Redirect-Ziel |
| K2 | Ist der Zeitpunkt reif? | „ja, 2. Owner + Momentum" | „REC-1 nur halb, PyPI-Owner offen = Scheinsicherheit" | „platform in S3-Welle bewusst zurückgestellt" | **Nicht reif** — 2 Owner sind *notwendig, nicht hinreichend* (C3); Kopplungs-Ausschluss (C2) steht |
| K3 | Konsistenz-Argument | „SSoT muss eigene Regel befolgen" | „ADR-255 listet platform bewusst NICHT" | „S3 schließt gekoppelte Repos explizit aus" | **Teil-Auflösung** — Richtung stimmt, aber der Ausschluss ist *bewusst+korrekt* (Kopplung), keine Heuchelei |
| K4 | Rollback-Sicherheit | (implizit: Redirect-Netz) | „Rollback = 2. Incident, Secret-Neubefüllung + Runner-Neuregistrierung" | „ohne Runbook ist ‚läuft wieder' Glück" | **Diabolus/Maintainer** — „Einbahn-Exit" (KONZ-002), Rollback nicht kostenlos |

Kein Dissens bestand darin, dass die **Richtung** langfristig sinnvoll ist — nur über **Reife, Reihenfolge und Ausführungsrisiko**. Das ist der Kern der Empfehlung.

## 7. Deep-Dive — die konkreten Bruchstellen des rohen Transfers

1. **Runner-Bindung bricht sofort:** Registrierung ist repo-gebunden; `iilgmbh/platform` sieht `prod-server` nicht → 10 Workflows tot bis manuelle Neuregistrierung, darunter `_ci-python` (Blocking-Gate JEDER Cross-Repo-PR der shared-ci-Konsumenten) und `backup-meter` (Backup-Blindheit — Kategorie des risk-hub-NULL-Backup-Vorfalls).
2. **Secrets werden NICHT mit-transferiert** (GitHub-Fakt): alle 15 leer → Hetzner-Deploy (kein SSH-Key), sync-to-devhub (kein Webhook-Secret), SOPS unentschlüsselbar (kein AGE-Key), PyPI-Publish (kein Token). Exakt die coach-hub-Signatur, diesmal am SSoT.
3. **Kontrollebene ignoriert Redirects:** OIDC-`repository_owner`-Claim (→ `invalid-publisher` bis PyPI-seitig umgestellt, braucht PyPI-Owner-Rechte = offen), Fine-grained-PAT-Repo-Auswahl (silent 404), Webhook-Payload `owner.login=iilgmbh` (dev-hub-Filter verwirft still), raw.githubusercontent-URLs (404 statt Redirect bei Token-Pfaden).

## 8. Alternativen

| Alt | Beschreibung | Bus-Faktor-Nutzen | Risiko/Reversibilität | Verdikt |
|---|---|---|---|---|
| **A0** | Status quo (platform bleibt am User-Konto) | 0 | keins | Verwirft das Ziel — nur Nullmessung |
| **A1 (empfohlen)** | Phase A: CODEOWNERS+Required-Reviewer + PyPI-2.-Owner + Leaver-Matrix + Org-Runner/Secret-Spiegelung, KEIN Transfer | ~80 % | niedrig, voll reversibel | **Jetzt umsetzen** |
| **A2** | Roher Transfer jetzt | 100 % nominal, real < A1 (PyPI-Owner offen) | hoch, „Einbahn-Exit" | Abgelehnt bis Phase B |
| **A3** | Transfer nach Phase A+B, gegatet (Phase C) | 100 % echt | mittel, mit Runbook+Rollback-Grenze | Ziel-Zustand, terminieren wenn Vorbedingungen grün |

## 9. Out-of-the-Box

- **Coupling-Indirektion als eigenständiger Wert:** Die repointbare Alias-Stelle (OOTB-5) nützt jedem künftigen Transfer der Fleet, nicht nur platform — sie ist die generische Lösung des „~14 Caller brechen"-Problems.
- **Org-Runner-Pool + Org-Secrets als Trockenlauf:** liefert schon vor jedem Transfer Redundanz (ein zweiter Runner-Host) und testet die Ziel-Verdrahtung risikofrei.

## 10. Befunde

| ID | Befund | Schwere | Evidenz |
|---|---|---|---|
| B1 | platform bewusst aus S3-Transfer-Welle ausgeschlossen (Kopplung) — Transfer ist kein „neuer" Entscheid | H | C2 |
| B2 | 2. GitHub-Owner klärt nur halbe REC-1; PyPI-Owner + Leaver-Prozess offen | H | C3, C7 |
| B3 | Roher Transfer bricht 10 Workflows (Runner) + 15 Secrets + OIDC/Webhook/raw-URLs | H | C4/C5/C6 |
| B4 | Kein Runner-Reprovisionierungs-Runbook für platform | M | C2 (S3 kennt nur Secrets/Webhooks) |
| B5 | 14 Workflow-/77 md-/19 tools-Refs = stille Redirect-Schuld ohne REC-13-Gate | M | C3 |

## 11. Top-5-Risiken

| R | Risiko | Wahrscheinlichkeit | Impact | Gegenmaßnahme |
|---|---|---|---|---|
| R1 | `_ci-python` fleet-weit tot während Runner-Lücke | hoch (bei Transfer ohne Runbook) | hoch (alle Cross-Repo-PRs blockiert) | Phase C: Runner-Runbook + Org-Runner-Pool VOR Transfer |
| R2 | Prod-Deploy/SOPS/PyPI brechen an leeren Secrets | sehr hoch | hoch | Pre-Transfer-Secret-Inventar + sofortige Re-Population aus ~/.secrets |
| R3 | „2 Owner" ist Scheinsicherheit (PyPI offen, kein Recovery-Test) | mittel | hoch | Phase A: PyPI-Owner + getesteter Recovery-Pfad |
| R4 | Rollback wird 2. Incident (Einbahn-Exit) | mittel | hoch | Kill-Gate + definierte Rollback-Grenze; Transfer nur nach grünem Consumer-CI |
| R5 | Stille Webhook-/raw-URL-Brüche (kein Alert) | hoch | mittel | REC-13-Stale-Ref-Checker + dev-hub-Filter auf neue Owner-ID prüfen |

## 12. Empfehlungen (konkret, verifizierbar)

1. **Jetzt (Phase A, reversibel):** (a) PyPI-org `iil` 2. Owner verifizieren/hinzufügen; (b) `docs/runbooks/platform-owner-recovery.md` schreiben (Leaver + Recovery, benannter Principal); (c) `.github/CODEOWNERS` + Branch-Protection „1 Required Reviewer ≠ Autor" auf platform; (d) Runner zusätzlich als Org-Runner registrieren + kritische Secrets als Org-Secrets spiegeln (Trockenlauf).
2. **Vorbedingung (Phase B):** Coupling-Indirektion (KONZ-002 OOTB-5) bauen; Runner-Reprovisionierungs-Runbook ergänzen.
3. **Transfer (Phase C, nur gegatet):** Pre-Transfer-Secret-Inventar (Schema A) · grüner Consumer-CI-Lauf gegen `uses: iilgmbh/platform/...@main` · REC-13-Stale-Ref-Checker scharf · definierte Rollback-Grenze.
4. **Nicht tun:** rohen Transfer jetzt (A2) — er löst den Bus-Faktor nicht, den er vorgibt (PyPI-Owner + Recovery hängen nicht am Repo-Pfad), und riskiert einen SSoT-Prod-Incident.

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidungs-Vorlage an den Owner:** Phase A freigeben (reversibel, hoher Nutzen, kein Gate berührt außer Org-Secret-Anlage). Phase C bleibt eine **separate, spätere** Freigabe (irreversibel, Gate 1+2+3).

**Kill-Gate (messbar):** Wenn bis **2026-09-15** die Coupling-Indirektion (OOTB-5) nicht existiert ODER PyPI-`iil` keinen verifizierten 2. Owner hat → **kein Transfer-Termin**; Konzept bleibt in Phase A oder `sunset`. Exception-Budget: einmalige Verlängerung um 30 Tage mit datierter Begründung, dann Zwangs-Sunset.

**30/60/90:**
- **30 Tage:** Phase A komplett (PyPI-Owner, Recovery-Runbook, CODEOWNERS, Org-Spiegelung). Messpunkt: `gh api` zeigt PyPI-2.-Owner + Branch-Protection required-reviewer aktiv.
- **60 Tage:** Phase B — OOTB-5-Alias-Stelle gebaut + Runner-Runbook; ein Consumer-Repo testweise auf die Alias-Stelle gezogen, CI grün.
- **90 Tage:** Go/No-Go für Phase C anhand Kill-Gate; bei Go: gegateter Transfer mit vollem Runbook, sonst Sunset-Entscheid.

## Verwandt
- **ADR-255** (iil-* PyPI-Familien-Migration; platform = Nicht-Ziel/Konsument) — Rev 4 hält den REC-1-GitHub-Owner-Stand fest.
- **KONZ-platform-002** (Enterprise-Konsolidierung, pilot) — platform-Transfer ist ein KONZ-002-S3-Fall.
- **docs/runbooks/KONZ-002-s3-repo-transfer.md** (Transfer-Runbook; schließt gekoppelte Repos aus) · **docs/runbooks/iil-migration-breakglass-pypi-token.md** (Break-Glass-Muster).

<!-- Adversariat: 3 blinde Agenten (Steelman/Diabolus/Maintainer-2028) + Synthese, 2026-07-05. Konfliktmatrix §6. -->
