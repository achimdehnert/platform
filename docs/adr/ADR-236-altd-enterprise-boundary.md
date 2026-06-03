---
status: proposed
implementation_status: none
date: 2026-06-03
decision-makers: Achim Dehnert
domains: [governance, security, secrets, ci-cd]
scope: platform
relates_to: [ADR-235, ADR-045, ADR-220, ADR-226, ADR-230]
tags: [enterprise, org-topology, boundary, data-sovereignty, push-protection, portability, exit-class, consolidation]
---

# ADR-236 — ALT-D Enterprise-Boundary: IIL-Org-Topologie konsolidieren (mit Portabilität by construction)

> **Amends ADR-235** (Reversal der „public native / private CI-Fallback"-Aufteilung **für org-/enterprise-eigene Repos**).
> **Basiert auf** Konzept [KONZ-platform-002](../konzepte/KONZ-platform-002-enterprise-consolidation.md); Rollout-Mechanik in [`docs/runbooks/KONZ-002-consolidation-rollout.md`](../runbooks/KONZ-002-consolidation-rollout.md).
> Status `proposed`; **Umsetzung gegated** durch das KONZ-002 Kill-Gate (a/b/c) — dieser ADR ist die *Boundary-Entscheidung*, nicht ihre Ausführung.

## 1. Kontext

### 1.1 Ausgangslage (API-verifiziert 2026-06-03)
Die GitHub-Topologie des IIL-Ökosystems ist zersplittert:
- Enterprise **`iilgmbh`** enthält **nur** `bahn-sqf` (1 Member-Org).
- Vier weitere Orgs laufen auf **separaten Team-Plänen außerhalb** der Enterprise: `iilgmbh` (Org ≠ Enterprise-Slug), `ttz-lif`, `meiki-lra`, `pactive-de`.
- Der User-Account **`achimdehnert`** hält 54 Repos und kann **keiner** Enterprise beitreten (User ≠ Org).
- Die Enterprise hat bereits die **richtige Security-Config** (ID 17 „GitHub recommended", volle Suite enabled) — aber angewandt auf **nur 3 `bahn-sqf`-Repos** und **nicht** als Default für neue Repos.
- **Abrechnung pro Person** (2 Seats: `achimdehnert` + `iljalerch`; 2 GHAS-Committer), **nicht** pro Org/Repo.

### 1.2 Problem / Lücken
- **Native Prävention nur insular:** native Push-Protection (pre-history) wirkt nur dort, wo die Enterprise-Config greift. Private Org-/User-Repos verlassen sich auf den CI-gitleaks-Fallback aus ADR-235 — Detektion *nach* dem Push, nicht Prävention *davor*.
- **Vier redundante Team-Pläne**, obwohl die Abrechnung pro Person läuft → Konsolidierung wäre kostenneutral.
- **Datensouveränität ungeklärt:** `ttz-lif`/`meiki-lra` sind Behörden-/Bürgerdaten-Workloads — ein zentraler Enterprise-Ownership-Wechsel berührt, *wer verwalten/auditieren darf* (unabhängig vom technischen Datenschutz).
- **Exit nicht bewiesen:** Orgs/Repos müssen später wieder austreten können (Kundenende, Behörden-Übergabe) — Exit-Readiness war bisher behauptet, nicht getestet.

### 1.3 Constraints
- **SSoT** — keine zwei Wahrheitsstände; ableiten statt duplizieren.
- Ein Mechanismus zählt erst als „mandatory", wenn er **by construction** erzwungen ist.
- Der bindende Gate gehört **unmittelbar vor die irreversible Aktion** (ADR-210-Prinzip).
- **Behörden-/Public-Sector-Workloads** unterliegen Daten-Souveränitäts-Regeln, die *unabhängig* vom technischen Datenschutz gelten.
- Org-Erstellung/-Aufnahme nur per **Web-UI/SCIM** (API = 404; SCIM braucht SAML, ist null).

## 2. Entscheidung

Wir adoptieren **ALT-D** als Org-Topologie-Boundary:

1. **Konsolidieren** (`central-ok`): die Org `iilgmbh` in die Enterprise `iilgmbh` aufnehmen. `pactive-de` ebenfalls `central-ok`, aber **nur mit Zustimmung der Dritt-Owner** (kein einseitiger Move — `achimdehnert` ist dort nur `member`).
2. **Config 17** als **Enterprise-Default + apply-to-all** setzen (erst `unenforced` beobachten → dann `enforced`).
3. **Government-Orgs `ttz-lif`/`meiki-lra` bleiben standalone** (`must-stay-local`) mit **gespiegelter Security-Config** + CI-Gleichheits-Audit. Sie werden **nicht** in die Enterprise aufgenommen.
4. **Reversal von ADR-235 für org-/enterprise-eigene Repos:** dort wird native Push-Protection (auch privat, via Enterprise-Config) **Layer 1**; CI-gitleaks → **Defense-in-depth**. Die ADR-235-Aufteilung **bleibt** für `achimdehnert`-User-Account-Repos bestehen, bis diese migriert/ausgetrocknet sind.
5. **`exit_class` als abgeleitete Policy-SSoT** (OOTB-8): jede Org wird getaggt `central-ok | exit-likely | must-stay-local`; eine deklarative Quelle leitet daraus `placement`, `allowed_features`, `required_checks`, `exit_tests` und **`teardown_authority`** ab. `teardown_authority: none` ist für `exit-likely`/`must-stay-local` unzulässig.
6. **Portabilität by construction:** Exit-Readiness ist abgeleitet/getestet/getaggt (`make exit-plan`, Exit-Feuerübung), kein gepflegtes Dokument.

**Umsetzung gegated** durch das KONZ-002 Kill-Gate; Reihenfolge + Rollback je Phase im Runbook.

## 3. Betrachtete Alternativen

| Alt | Inhalt | Verworfen weil |
|---|---|---|
| **ALT-A** (Status quo) | Keine Moves; Config 17 nur auf `bahn-sqf`, ADR-235 CI-gitleaks überall sonst | private Org-/User-Repos bleiben ohne native Prävention; 4 Team-Pläne bleiben. (= Fallback/Kill-Gate-Ziel) |
| **ALT-B** (per-Org Secret Protection) | Jede Org kauft „Secret Protection" (Team) einzeln | teurer pro Org; keine zentrale Kontrollebene; löst Souveränität nicht sauber |
| **ALT-C** (Voll-Konsolidierung) | **Alle** Orgs inkl. Government in die Enterprise | **Souveränitätsbruch** — Behörden-Org unter zentrales Ownership ist Compliance-Risiko |
| **ALT-D** (Hybrid) ✅ | Nicht-Government konsolidieren; Government standalone + gespiegelt | **gewählt** — trennt Souveränitätsrisiko sauber ab, nutzt Kostenneutralität |

## 4. Begründung im Detail

- **Kostenneutralität ist gesetzt** (Abrechnung pro Person, API-verifiziert) → Org-Aufnahme kostet nichts Zusätzliches, solange keine neue Person dazukommt; die 4 Team-Pläne werden redundant. (€-Sätze extern noch unbestätigt → Restlücke, siehe §6.)
- **Prävention schlägt Detektion:** native Push-Protection blockt Secrets **vor** der History; CI-gitleaks findet sie danach. Eine Enterprise-Config liefert native Prävention auch auf **privaten** org-eigenen Repos — das ist der eigentliche Hebel.
- **Souveränität braucht Trennung, nicht Zentralisierung:** für Behörden zählt *wer verwalten/auditieren darf*. ALT-D hält GOV-Orgs standalone und spiegelt nur die Posture (Verbesserung ohne Ownership-Wechsel).
- **Portabilität bewiesen, nicht behauptet** (KONZ-002 §15, Feuerübung Runde 1): exit-plan-Runbook + Exit-Feuerübung falsifizierten 2 Annahmen (Variable überlebt Transfer/Secret nicht; Push-Protection nach Transfer in Nicht-Enterprise-Org verloren & nicht reaktivierbar) und deckten den **Teardown-Authority-Befund** auf → REC-8/`teardown_authority`.

## 5. Implementation Plan

Vollständig im Runbook [`docs/runbooks/KONZ-002-consolidation-rollout.md`](../runbooks/KONZ-002-consolidation-rollout.md). Kurzform:

| Phase | Inhalt | Gate |
|---|---|---|
| **S1** | `iilgmbh`-Org in Enterprise aufnehmen | DR-A (Kostenakte) |
| **S2** | Config 17 Default → `unenforced`→`enforced` | S1 grün + FP-Rate ausgewertet |
| **S3** | Wertvolle private User-Repos migrieren (Wellen) | S2 enforced; Ziel admin-kontrolliert |
| **S4** | User-Account austrocknen | S3 verifiziert |
| **GOV** | `ttz-lif`/`meiki-lra` standalone + gespiegelte Config | DR-B (bounded); **kein** Ownership-Move |
| **`pactive-de`** | Konsolidierung | ⛔ Dritt-Owner-Zustimmung |

Org-Ops = Web-UI/SCIM (Owner führt aus); CC pflegt Plan/Audit.

## 6. Risiken

| Risiko | Mitigation |
|---|---|
| **Souveränitätsbruch** (B4) | ALT-D — GOV standalone + gespiegelt; Ownership-/Transfer-Schritte hart gesperrt bis **schriftlicher** Träger-Sign-off |
| **Einbahn-Exit / Kontrollverlust** beim Transfer in Fremd-Org (REC-8) | `teardown_authority`-Pflichtfeld; Transfer nur in admin-kontrollierte Ziele |
| **Config-Drift** auf gespiegelten GOV-Orgs | CI-Gleichheits-Audit (deklarativer Soll/Ist-Vergleich) |
| **Kosten** — €-Sätze extern unbestätigt | DR-A-Restlücke: Account-Team-Mail **vor** Team-Plan-Kündigung |
| **Push-Protection-Verlust** bei Migration in Nicht-Enterprise-Ziel (REC-9) | S3-Gate: Ziel muss Enterprise-Config (Push-Protection aktiv) haben |

## 7. Konsequenzen

### 7.1 Positiv
- **Eine Kontrollebene** für Security-Posture statt vier Team-Pläne.
- **Native Prävention überall** auf org-/enterprise-eigenen Repos (auch privat).
- **Portabilität getestet/getaggt** — Exit ist machbar und vorab bewiesen.

### 7.2 Trade-offs
- **Zwei Betriebsmodelle** (zentral vs. standalone-gespiegelt für GOV) — höhere Pflege.
- Mirror-Aufwand + CI-Gleichheits-Audit für GOV-Orgs.

### 7.3 Nicht in Scope
- **`pactive-de`** bis Dritt-Owner-Zustimmung.
- **`achimdehnert`-User-Account-Repos** bis S3/S4 (ADR-235-Aufteilung bleibt dort vorerst).
- **EMU / SAML / SCIM-Provisioning** (nicht vorhanden; Exit deshalb machbar, aber nicht kostenlos).

## 8. Validation Criteria

KONZ-002 Kill-Gate (Frist 2026-08-15), Kriterium D1:
- **(a)** Kostenneutralität bestätigt (aktuell: Budget-Owner-Aktennotiz DR-A; €-Sätze extern offen).
- **(b)** GOV-Souveränitäts-Sign-off (aktuell: mündlich protokolliert DR-B; **formaler schriftlicher** Sign-off vor jeder GOV-Eskalation über Config-Spiegelung hinaus ausstehend).
- **(c)** Portabilität bewiesen ✅ (exit-plan-Runbook + Feuerübung grün, PR #429).
Fehlt eine Bedingung → keine Org-Aufnahme; Sunset auf ALT-A.

## 9. Glossar

| Begriff | Bedeutung |
|---|---|
| **ADR** | Architecture Decision Record |
| **Enterprise (GitHub)** | oberste Org-Klammer mit zentraler Billing-/Security-Verwaltung |
| **Org-Slug ≠ Enterprise-Slug** | Enterprise `iilgmbh` und Org `iilgmbh` sind zwei verschiedene Objekte |
| **GHAS** | GitHub Advanced Security — schaltet Secret Scanning + Push Protection auf privaten Repos frei |
| **Push Protection** | blockiert `git push` mit erkanntem Secret **vor** dem Landen in der History |
| **Config 17 / Enterprise Security Configuration** | benannte Security-Config („GitHub recommended"), zentral auf Repos anwendbar |
| **Seat** | abgerechnete Person (nicht Org/Repo) |
| **EMU** | Enterprise Managed Users — zentral verwaltete Identitäten |
| **SAML / SCIM** | SSO- bzw. User-Provisioning-Standards (hier nicht eingerichtet) |
| **exit_class** | abgeleitetes Org-Tag (`central-ok`/`exit-likely`/`must-stay-local`) → Platzierung + Feature-Allowlist + Checks + Exit-Tests |
| **teardown_authority** | Pflichtfeld: wer darf eine Org/ein Repo zurückbauen (`self-owner`/`contractual-clause`/`none`) |
| **GOV-A / GOV-B** | anonymisierte Behörden-Orgs (`ttz-lif` / `meiki-lra`) |
| **must-stay-local** | Org, die aus Souveränitätsgründen nicht zentralisiert werden darf |

## 10. Referenzen
- Konzept **KONZ-platform-002** + Runbook `docs/runbooks/KONZ-002-consolidation-rollout.md`.
- **ADR-235** (Secret-Prevention-Posture — wird hier für org/enterprise-Repos amendiert) · **ADR-226** (Mandatory Secret-Scan + shared Action) · **ADR-220** (OIDC-Publish) · **ADR-045** (Secrets-Storage) · **ADR-230** (CC-first).
- Portabilitätsnachweis: PR #429 (KONZ-002 §15 Feuerübung Runde 1).

## 11. Changelog
- 2026-06-03: Initial (Proposed) — ALT-D Boundary aus KONZ-002; Umsetzung gegated (Kill-Gate a/b/c). Amends ADR-235 (Reversal für org/enterprise-Repos).
