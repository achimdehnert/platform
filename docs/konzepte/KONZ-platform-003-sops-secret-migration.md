---
concept_id: KONZ-platform-003
title: SOPS-Secret-Migration — .env.prod → SOPS/run-secrets plattformweit
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []
adr_threshold: Amendment an ADR-045 (Operationalisierung + secrets-drift-Gate + Key-Custody)
review_by: 2026-07-15
kill_criteria: "Wenn nach dem Pilot-Repo das secrets-drift-Gate nicht GRÜN beweisen kann, dass das Repo keinen .env.prod-Bezug mehr hat, ODER ein Cutover einen Prod-Secret-Read-Fehler verursacht → Rollout ABBRECHEN, kein Customer-Data-Repo anfassen. Exception-Budget 2 Wochen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-045-secrets-management.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-159-shared-secrets-management.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C3, source_path: .sops.yaml, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C4, source_path: .github/workflows/_deploy-hetzner.yml, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C5, source_path: scripts/create-secrets.sh, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C6, source_path: "grep ~/github/*/config: read_secret vs decouple", commit_or_pr: session-2026-06-06, opened_in_session: true}
created: 2026-06-06
---

# KONZ-platform-003 — SOPS-Secret-Migration

**Tier T3** (hart begründet): org-weit ~25 Repos · SSoT-Reversal (ADR-159 `.env.prod` → ADR-045 SOPS) · Security-Perimeter · berührt regulierte Live-Kundendaten (risk-hub/tax-hub). Jeder einzelne Trigger erzwingt ≥T2; in Summe T3.

## 1. Executive Summary

ADR-045 (SOPS-age → `/run/secrets/`) ist die akzeptierte Ziel-Architektur; ADR-159 (`.env.prod` plaintext + `decouple.config`) wurde diese Session als **Interim** re-scoped. Geerdeter Schlüsselbefund: **die SOPS-Mechanik ist bereits gebaut, aber dormant** (`.sops.yaml` C3, `scripts/create-secrets.sh` C5, `_deploy-hetzner.yml` `secrets`-Job C4 — skip wenn `SOPS_AGE_KEY` ungesetzt). Migration = **Operationalisierung pro Repo** (secrets.enc.env schreiben + `SOPS_AGE_KEY` setzen), nicht „SOPS bauen".

Der adversariale Pass (3 unabhängige Agenten) ist eindeutig: der Plan ist **billig und tragfähig** — aber der vorhandene `read_secret → env`-Fallback, der ihn „low-risk" macht, ist zugleich der **gefährlichste Teil**: er versteckt Halb-Migrationen dauerhaft. **Empfehlung: Migration JA, aber die Sicherheit liegt NICHT im Fallback, sondern in einem neuen `secrets-drift`-Gate, das „migriert" maschinell beweist; plus Age-Key-Custody VOR jedem Customer-Repo.** Reihenfolge: Pilot auf Nicht-Customer-Hybrid-Repo → dann risk-hub/tax-hub → Rest.

## 2. Scope & Evidenzbasis

- **Ziel (C1):** secrets als SOPS-age-`secrets.enc.env` in git → CI-decrypt → Server `/run/secrets/<key>` (chmod 400); App liest via `config/secrets.py read_secret()` mit Fallback `/run/secrets/ → env`. Variante C (Hybrid).
- **Ist (C2, C6):** `.env.prod` plaintext auf Hetzner + `decouple.config`. Real **hybrid**: risk-hub/bfagent/dev-hub haben read_secret+decouple; tax-hub/coach-hub/billing-hub/recruiting-hub **pur** decouple/.env.prod.
- **Mechanik gebaut-aber-dormant (C3/C4/C5):** `.sops.yaml` = 2 age-Recipients (Dev-Maschine + Backup); `_deploy-hetzner.yml` `secrets`-Job decrypted + scp nach `/run/secrets/`, **skip-if-no-`SOPS_AGE_KEY`** und nur wenn `secrets.enc.env` existiert.
- **Live-Kundendaten:** risk-hub (schutztat.de, Multi-Tenant), tax-hub (Steuerkanzleien). DSGVO.

## 3. Infrastruktur-Fit

Kein neuer Stack, keine neue Dependency: SOPS 3.9.4 + age sind bereits in `_deploy-hetzner.yml` verdrahtet. Single Hetzner VPS, Docker-Compose, Self-Hosted-Runner — unverändert. Der Migrationspfad ist additiv (Fallback hält `.env.prod` lauffähig während des Cutovers).

## 4. Steelman (stärkster Fall dafür)

Zwei Prod-Systeme mit regulierten Live-Kundendaten halten Credentials als plaintext `.env.prod` auf geteiltem Host — schwächste Posture: Host-Compromise/Backup-Snapshot/Operator-Shell liest alles im Klartext, kein Audit-Trail. ADR-045 ist akzeptiert, ADR-159-Plaintext bereits als Interim deklariert — die *Richtung* ist entschieden, offen ist nur die Sequenz. Der Mechanismus ist **gebaut, reviewt, dormant**: Aktivierung = 2 reversible Schritte/Repo. Hybrid-Repos haben den `/run/secrets→env`-Fallback → **Zero-Downtime-Cutover** (encrypted secrets liefern *während* `.env.prod` noch läuft, dann erst entfernen). Gewinn (DSGVO Art. 32 TOM): verschlüsselt-at-rest in git (versioniert, rotierbar), weg vom plaintext-Host, root-only chmod-400. Build-Kosten sind versunken; Restkosten nahe null.

## 5. Konzeptdefinition (das WIE)

Operationalisierung pro Repo, mit zwei nicht-verhandelbaren Vorbedingungen und einem neuen Beweis-Gate:

- **Vorbedingung A — Age-Key-Custody (VOR jedem Customer-Repo):** `SOPS_AGE_KEY` ist heute ein einzelnes katastrophales Secret; `.sops.yaml` nennt 2 Recipients **ohne dokumentiertes Backup/Rotation** (C3). Erforderlich: 3. Recipient als Offline-Escrow (NICHT auf der Dev-Maschine), Rotations-Runbook, Backup in `~/.secrets` + offline. Schließt das „beide Keys auf einem Laptop"-Szenario.
- **Vorbedingung B — `secrets-drift`-Gate (das Keystone):** scheduled + pre-Phase-7-Job, der pro Repo `secrets.enc.env` entschlüsselt, das Key-Set hasht, gegen live `/run/secrets/` auf dem Server vergleicht und **HART failt bei**: fehlender `secrets.enc.env` · divergentem Key-Set · **überlebender `.env.prod`** · Secret-Quelle = env-Fallback statt `/run/secrets/`. Macht „migriert" maschinell beweisbar — tötet die Silent-Halb-Migrations-Klasse.
- **Phase-7-Härtung:** der `secrets`-Job in `_deploy-hetzner.yml` muss `.env.prod` **löschen** (schreibt heute nur `/run/secrets/`, C4) und im End-State den read_secret-Fallback abschalten/asserten.
- **Sequenz:** (1) Pilot auf **Nicht-Customer-Hybrid-Repo** (bfagent oder dev-hub — niedrigstes Risiko, Fallback vorhanden) → beweist Gate + Cutover. (2) **risk-hub, tax-hub** mit Gate grün. (3) Rest (coach/billing/recruiting + ~18 weitere).

## 6. Adversariale Analyse + Konfliktmatrix

| Achse | Steelman | Advocatus Diabolus | Maintainer-2028 | Auflösung |
|---|---|---|---|---|
| **read_secret-Fallback** | macht Cutover low-risk/zero-downtime | versteckt Halb-Migration dauerhaft; „migriert" nie verifiziert | Hauptursache: 3 Repos liefen 2027 auf 6-Mon-alten .env.prod, kein Alarm | **DISSENS aufgelöst:** Fallback NUR für Cutover; End-State Fallback-OFF; Gate (Vorb. B) ist der Safety-Net, nicht der Fallback |
| **DSGVO-Gewinn** | encrypted-at-rest = DSGVO-Win | Theater: plaintext wandert nur nach /run/secrets + Container-env; Art.17/20 ≠ Storage | — | **DISSENS aufgelöst:** ehrlich als **Art. 32 TOM** framen (Exposure-Fläche↓: git-History, .env.prod-Files, Operator-Shell), NICHT „plaintext eliminiert" |
| **Age-Key-Custody** | (nicht adressiert) | neues katastrophales Single-Secret, keine Rotation/Backup | Key-Verlust Q1-2027 → Hotfix unmöglich | **KEIN DISSENS:** Vorbedingung A, vor Customer-Repo |
| **.env.prod-Löschung** | (impliziert Phase 7) | nichts löscht es; bleibt autoritativ-on-fallback | „nie wirklich gelöscht" | **KEIN DISSENS:** Phase-7-Härtung (Job löscht + Gate failt auf Überleben) |
| **Customer-first** | richtige Front | erster Deploy-Path-Change live auf schutztat.de = riskant | — | **DISSENS aufgelöst:** Pilot auf Nicht-Customer-Hybrid ZUERST, dann Customer mit Gate |

## 7. Deep-Dive: warum stallte Phase 2/3/7?

Diabolus' schärfster Punkt: die Mechanik lag **Monate dormant** (ADR-045 §7: „all phases still pending"). Wenn der Blocker organisatorisch ist (niemand besitzt Key-Custody/Rotation), liefert reines technisches Sequencing dieselbe Dormanz mit höheren Stakes. → Vorbedingung A macht Custody zum benannten, terminierten Owner-Schritt; das `secrets-drift`-Gate macht Nicht-Fortschritt **sichtbar** (rot), statt still.

## 8. Alternativen

| Alt | Beschreibung | Verworfen weil |
|---|---|---|
| **Status quo (.env.prod)** | nichts tun | regulierte Kundendaten auf plaintext-Host; ADR-159 bereits als Interim deklariert |
| **Externer Secrets-Manager** (Vault/Doppler/Cloud-KMS) | Managed SaaS/Service | ADR-045 hat SOPS entschieden; neue Dependency + Kosten; SOPS-Pfad ist bereits gebaut → T3-Reversal nicht gerechtfertigt |
| **Nur secret-scanning verschärfen** (gitleaks, schon da) | Verlass auf Scan | scannt git, nicht Storage; adressiert den Treiber (plaintext-at-rest) nicht |

## 9. Out-of-the-Box

- **age-plugin-yubikey** oder Offline-Escrow-Recipient für Key-Custody (Vorbedingung A härter als Passwort-Manager).
- `secrets-drift`-Gate als wiederverwendbarer Job in `_deploy-hetzner.yml`, der org-weit denselben Beweis liefert (ein Reader, kein zweiter SSoT).

## 10. Befunde

| id | Aussage | Typ | Evidenz | Status |
|---|---|---|---|---|
| B1 | SOPS-Mechanik gebaut-aber-dormant; Migration = Operationalisierung, nicht Build | Befund | C3/C4/C5 | offen |
| B2 | read_secret-Fallback versteckt Halb-Migration → braucht Beweis-Gate | Risiko | Diabolus+Maintainer-Konvergenz | offen |
| B3 | `.env.prod` wird von keinem Job gelöscht | Risiko | C4 (Job schreibt nur) | offen |
| B4 | SOPS_AGE_KEY ohne Backup/Rotation = Single-Point | Risiko | C3 + ADR-045 §6 (H) | offen |
| B5 | DSGVO-Gewinn ist Art. 32 (TOM), nicht Art. 17/20 | Klarstellung | C1 + Diabolus | offen |

## 11. Top-5-Risiken

1. **Silent-Halb-Migration** (B2) — mitigiert durch `secrets-drift`-Gate (Vorb. B), nicht durch Fallback.
2. **Age-Key-Verlust/Compromise** (B4) — mitigiert durch Vorbedingung A vor Customer-Repo.
3. **Überlebendes `.env.prod`** (B3) — Phase-7-Job löscht + Gate failt auf Existenz.
4. **Live-Customer-Cutover-Fehler** — Pilot auf Nicht-Customer-Repo zuerst; brittler Quote-Parser (`_deploy-hetzner.yml` C4) vorher härten.
5. **Organisatorische Re-Dormanz** (Deep-Dive §7) — Custody-Owner + rotes Gate machen Stillstand sichtbar.

## 12. Empfehlungen (konkret)

- **REC-1:** `secrets-drift`-Gate bauen (decrypt → keyset-hash → vs `/run/secrets/` + .env.prod-Existenz-Check; HARD-fail). Reusable in `_deploy-hetzner.yml`.
- **REC-2:** Age-Key-Custody schließen: 3. Offline-Escrow-Recipient in `.sops.yaml` + Rotations-Runbook unter `docs/runbooks/`.
- **REC-3:** `_deploy-hetzner.yml` `secrets`-Job um `.env.prod`-Löschung (post-verify) erweitern.
- **REC-4:** Pilot: bfagent ODER dev-hub (hybrid, nicht-Customer) — Cutover + Gate-grün beweisen.
- **REC-5:** read_secret End-State: Fallback hart abschalten/asserten (kein stiller env-Pfad in Prod).
- **REC-6:** ADR-045 Amendment: Operationalisierungs-Plan + Gate + Custody dokumentieren (kein neuer ADR — Erweiterung).

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidung (vorgeschlagen):** Migration JA, gegated. Reihenfolge Pilot → Customer → Rest. Sicherheit über `secrets-drift`-Gate + Key-Custody, NICHT über den Fallback.

**Kill-Gate (messbar):** Wenn nach dem Pilot-Repo das `secrets-drift`-Gate nicht GRÜN beweisen kann, dass das Repo keinen `.env.prod`-Bezug mehr hat, ODER ein Cutover einen Prod-Secret-Read-Fehler verursacht → **Rollout ABBRECHEN, kein Customer-Data-Repo anfassen**. Exception-Budget 2 Wochen ab Pilot-Start.

**30 Tage:** Vorbedingung A (Key-Custody/Escrow/Rotation) + REC-1 `secrets-drift`-Gate + REC-3 .env.prod-Delete. Pilot (REC-4) auf 1 Hybrid-Nicht-Customer-Repo, Gate grün.
**60 Tage:** risk-hub + tax-hub migrieren (Customer-Data, Gate grün), Fallback-off, `.env.prod` gelöscht, Drift-Gate verifiziert.
**90 Tage:** Rest-Repos (coach/billing/recruiting + ~18) rollen; `secrets-drift` als required-CI; ADR-159 → superseded, ADR-045-Amendment.

> **Ehrliche Enforcement-Grenze:** Dieses Konzept *schreibt* Kill-Gate/`review_by`; sie wirken erst, wenn ein Lifecycle-Gate sie liest. Bis das `secrets-drift`-Gate gebaut ist (REC-1), ist „migriert" Review-behauptet, nicht maschinen-bewiesen — genau die Lücke, die REC-1 schließt.
