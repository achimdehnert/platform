---
status: accepted
implementation_status: partial
implementation_evidence:
  - "Layer 2: secret-scan.yml auf 7 zuvor ungeschützte private Repos ausgerollt + gemerged (bahn-hub#9, design-hub#29, desktop-setup#1, django-lms-lite#1, iil-fieldprefill#1, illustration-fw#8, nl2iot-hub#1, 2026-06-02)"
  - "Layer 1: native Secret Scanning + Push Protection aktiv auf allen public Repos (Audit #412; platform/writing-hub/lastwar-bot 2026-06-03 wieder eingeschaltet)"
  - ".github/actions/gitleaks-scan (ADR-226) als geteilte Action mit einem Versions-Pin von Layer 2 konsumiert"
  - "desktop-setup-Fund bereinigt (secrets.env aus Tree + .gitignore + .gitleaksignore; Tokens waren bereits rotiert)"
  - "Audit-Skript + Befund als #412 dokumentiert"
decision_date: 2026-06-02
deciders: Achim Dehnert
domains: [security, ci-cd, governance, secrets]
scope: platform
related: [ADR-045, ADR-210, ADR-220, ADR-226]
tags: [secret-scanning, push-protection, gitleaks, ghas, prevention, cross-repo, by-construction]
---

# ADR-235: Org-weite Secret-Prevention-Posture — bindender Gate am Push-Rand (native Push-Protection) mit CI-gitleaks als Fallback

| Attribut       | Wert                                                              |
|----------------|-------------------------------------------------------------------|
| **Status**     | Accepted                                                         |
| **Scope**      | platform (org-weit, alle Repos `achimdehnert`)                    |
| **Repo**       | platform                                                          |
| **Erstellt**   | 2026-06-02                                                        |
| **Autor**      | Achim Dehnert                                                     |
| **Reviewer**   | /adr-review + /adr-challenger (Findings adressiert)               |
| **Supersedes** | –                                                                 |
| **Relates to** | ADR-045 (Secrets-Storage/Injection — 235 ergänzt *Leak-Prävention*), ADR-210 (Gate am irreversiblen Rand), ADR-226 (Mandatory Secret-Scan / shared Action), ADR-220 (OIDC Trusted Publishing) |
| **Quelle**     | Secret-Prevention-Audit 2026-06-02 (#412) + bfagent-Incident (#410) |

---

## 1. Kontext

### 1.1 Ausgangslage

Der bfagent-Incident (#410) zeigte 78 committete Secrets in der Git-History (rotiert/tot). Die Folgefrage: **„läuft ein Secret-Scan zuverlässig auf JEDEM Repo — auch wenn das Repo selbst nichts konfiguriert?"** Ein org-weiter Audit (#412, 54 Repos) ergab ein an der **Repo-Visibility** ausgerichtetes Bild:

- **public Repos**: GitHub-native Secret Scanning **+ Push Protection** ist **gratis & aktiv** — der stärkste Gate, da er den Secret **vor** dem Landen in der History blockiert (ADR-210-Rand).
- **private Repos**: native Scanning **absent** — GitHub Advanced Security (GHAS) nicht lizenziert (empirisch: `gh api repos/<o>/<r>` → `secret_scanning` = absent; aus dem Audit-Ist, nicht aus Lizenz-Docs). Einziger Fallback: CI-seitiges gitleaks (geteilte `gitleaks-scan`-Action, ADR-226).
- **Anomalie**: 3 *public* Repos hatten den gratis Schutz abgeschaltet (`platform`, `writing-hub`, `lastwar-bot`).

### 1.2 Problem / Lücken

- Der einzige serverseitige Scan vieler privater Repos hing an der **freiwilligen Adoption** von `_ci-python.yml`. bfagent rief ihn nicht auf → kein Gate.
- 7 private Repos hatten **null** serverseitigen Scan; beim ersten Lauf fand sich in `desktop-setup` eine `secrets.env` mit GitHub-OAuth-Token im HEAD (rotiert; entfernt) — die bfagent-Fehlerklasse, vorher latent.
- Es gab **keine festgelegte Posture**, *welcher* Gate verbindlich ist und *wo* er sitzt → neue Repos driften zurück in die Lücke.

### 1.3 Constraints

- GHAS auf privaten Repos **kostet** (pro aktivem Committer/Monat) → Budget-, nicht reine Architektur-Frage.
- CI-gitleaks ist **post-push** (Secret schon in Remote-History → rotieren); nur Push-Protection ist **pre-history** (Prävention statt Detektion).
- Der per ADR-230 **abgeschaltete Auto-Distributor** darf nicht vorausgesetzt werden — Platzierung bewusst pro Repo.

## 2. Entscheidung

Gestufte, by-construction durchsetzbare Posture für die gesamte Org:

- **Layer 1 — Prävention, bindend, am Push-Rand (bevorzugt).** Native Secret Scanning **+ Push Protection** ist **verpflichtend aktiviert auf jedem Repo, wo es kostenfrei verfügbar ist** = alle public Repos. Verhindert, dass der Secret je in die History gelangt (ADR-210-korrekt). **Mechanismus je Account-Typ (Amendment 2026-06-03):** `achimdehnert` ist ein **User-Account** (keine Org → es gibt **kein** Org-Default-Setting); neue Repos dort werden über P2 (`onboard-repo`-Scaffold) bzw. per-Repo-Toggle abgedeckt. Für **org-/enterprise-eigene** Repos liefert eine **Enterprise Security Configuration** native Push-Protection auch auf *privaten* Repos (Enterprise `iilgmbh`, Config 17) — dort ist Layer 1 **nativ** und CI-gitleaks (Layer 2) wird Defense-in-depth; Topologie/Konsolidierung siehe **KONZ-platform-002**.
- **Layer 2 — Detektion-Fallback, post-push/pre-merge (Repos ohne native).** Für private Repos ist `secret-scan.yml` (`push:main` + `pull_request`), das die geteilte `gitleaks-scan@main`-Action ruft, **verpflichtende Baseline** — direkt oder transitiv über `_ci-python.yml` (ADR-226).
- **Layer 0 — beratend, shift-left.** `pre-commit`-gitleaks-Hook bleibt (clientseitig umgehbar → kein bindender Gate).
- **GHAS org-weit = bewusst aufgeschoben** (§3 Opt. 3, Trigger §7.3) — bis dahin CI-gitleaks als durable Baseline; GHAS bleibt empfohlener Upgrade-Pfad.

## 3. Betrachtete Alternativen

1. **Status quo (Scan hängt an `_ci-python.yml`-Adoption).** Gut: kein Aufwand. Schlecht: die bfagent-Lücke — ungeschützt ohne Caller, nicht messbar. → **Verworfen.**
2. **Nur CI-gitleaks überall, kein native.** Gut: einheitlich, gratis. Schlecht: ignoriert den gratis, überlegenen Push-Rand-Gate (public); post-push = Rotation statt Prävention. → **Verworfen.**
3. **GHAS sofort org-weit kaufen.** Gut: stärkste Lösung — Push-Rand-Prävention für *alle* Repos, ohne CI-Pflege. Schlecht: laufende Seat-Kosten, braucht Budget-Freigabe (keine reine Architektur-Festlegung). → Nicht sofort; dokumentierter Upgrade-Pfad (§7.3).
4. **Gestufte Posture (L0/L1/L2) mit GHAS als Upgrade.** Gut: schließt die Lücke sofort & gratis, nutzt den stärksten Gate wo verfügbar, macht die Kostenfrage explizit, messbar (§8). Schlecht/akzeptiert: privat vorerst Detektion statt Prävention. → **Gewählt.**

## 4. Begründung im Detail

- **Gate an den irreversiblen Rand (ADR-210).** Für Secrets ist `git push` in die Remote-History irreversibel. Native Push Protection sitzt dort, serverseitig **nicht** per `--no-verify` umgehbar (nur auditierter „allow secret"-Override); CI-gitleaks ist bestenfalls Detektion danach. Gratis-Stärke (public) zuerst ausschöpfen — abgeschaltet lassen ist reiner Verlust.
- **Keine Coverage ohne Mechanismus + DRY.** Ein Mandat ohne Durchsetzung driftet zurück (ADR-226-Lehre) → P2 (by-construction) + P3 (Meter). Layer 2 nutzt dieselbe `gitleaks-scan`-Action mit einem Versions-Pin — keine divergierenden Inline-Scans.

## 5. Implementation Plan

- **P0 — erledigt (2026-06-02):** `secret-scan.yml` auf 7 ungeschützte private Repos (PRs gemerged); `desktop-setup`-Fund bereinigt; Audit #412.
- **P1 — erledigt (2026-06-03):** native Push Protection auf `platform`/`writing-hub`/`lastwar-bot` wieder ein (`gh api` verifiziert). **Korrektur:** ein „Org-Default für neue Repos" ist für `achimdehnert` **nicht anwendbar** (User-Account, keine Org — `/orgs/...` gibt 404, kein Scope-Problem); neue Repos werden über P2 abgedeckt. Native Org-/Enterprise-Defaults gelten nur für echte Orgs/die Enterprise (KONZ-platform-002).
- **P2 — by-construction-Enforcement:** `secret-scan.yml` in den **`onboard-repo`-Pfad** (Skill/Scaffold) aufnehmen → jedes neue private Repo erhält den Gate ohne menschliches Zutun (der Auto-Distributor ist tot, ADR-230). Sonst wiederholt sich „Mandat ohne Mechanismus" eine Ebene höher.
- **P3:** Audit-Meter (wöchentlich, analog `pypi-ci-adoption-gate.yml`): prüft die Invariante (§8), pflegt **ein** Tracking-Issue, fällt nie hart — die Detektion hinter der P2-Prävention.
- **P4 — aufgeschoben:** GHAS-Kosten/Nutzen erneut bewerten, sobald ein Trigger (§7.3) feuert; bei Freigabe höchster Blast-Radius zuerst.

## 6. Risiken

- **CI-gitleaks ist post-push (Layer 2):** Secret landet vor dem roten Gate in der History → Rotation. Mitigation: Layer-0-Hook + schnelle Rotation + roter, nicht ohne Triage mergebarer PR. Echte Prävention nur via GHAS (P4).
- **`.gitleaksignore`-Missbrauch:** könnte echten künftigen Secret verdecken. Mitigation: nur **fingerprint-genaue** Suppressions, im PR reviewt; die Action echot Escape-Hatches als Warnung (ADR-226).
- **Setting-Drift auf public Repos:** Push Protection könnte abgeschaltet werden. Mitigation: P3-Meter prüft `secret_scanning.status` je public Repo (ein Org-/Enterprise-Default greift nur für echte Orgs/die Enterprise, **nicht** den User-Account).
- **Heuristik-FPs** (z. B. `generic-api-key` auf Domänen-Keys, bahn-hub): Reibung. Mitigation: fingerprint-Suppression als dokumentierter Pfad.

## 7. Konsequenzen

### 7.1 Positiv
- Jeder Secret-Pfad hat einen verbindlichen serverseitigen Gate; die bfagent-Lücke ist by-construction geschlossen, nicht adoptions-abhängig.
- Der stärkste Gate (Push-Rand) ist auf allen public Repos gratis scharf.
- Messbare Invariante statt laufendem Reparatur-Task.

### 7.2 Trade-offs
- Privat bleibt ohne GHAS Detektion statt Prävention (post-push).
- Laufende Pflege eines Audit-Meters + gelegentliche FP-Triage.

### 7.3 Nicht in Scope / aufgeschoben
- **GHAS-Anschaffung** (Budget). **Beziffert:** GitHub „Secret Protection" wird **pro aktivem Committer/Monat** abgerechnet (Listenpreis z. Z. grob ~$19/Committer/Monat — *vor* der Entscheidung aktuelle GitHub-Preisseite verifizieren, nicht aus diesem ADR zitieren). Diese Org hat **effektiv 1–3 aktive Committer** → Seat-Kosten niedrig zweistellig $/Monat. **Entscheidungsregel:** GHAS adoptieren, sobald `Preis × aktive Committer/Monat` < erwartete annualisierte Rotations-/Cleanup-Kosten **eines** Private-Repo-Incidents. Bei dieser Committer-Zahl ist der limitierende Faktor faktisch **`admin:org`-Aktivierung + Intent, nicht das Budget** — der Trade-off neigt sich zu „kaufen", sobald ein einziger Beinahe-Incident auftritt. Sofort-Trigger: (a) echter Secret erreicht trotz CI-gitleaks die History eines privaten Repos, **oder** (b) die Regel kippt.
- History-Purge alter toter Funde (Rotation ist der härtere Hebel; nur bei Bedarf).
- OIDC-Trusted-Publishing-Migration der Legacy-Publish-Workflows (ADR-220).

## 8. Validation Criteria

Maschinell prüfbar (vgl. Audit-Skript in #412):

1. **Jedes public Repo:** `secret_scanning.status == enabled` **und** `secret_scanning_push_protection.status == enabled` (`gh api repos/<o>/<r>`).
2. **Jedes private Repo:** ein serverseitiger gitleaks-Workflow auf dem Default-Branch (`secret-scan.yml` **oder** `_ci-python.yml`-Caller).
3. **Audit-Meter** läuft wöchentlich grün / mit schrumpfendem Backlog (ein Tracking-Issue).
4. → `implemented`, sobald P1 + P2 + P3 stehen; → `verified`, sobald der Meter ≥2 Wochen ohne offene Invarianten-Verletzung läuft.

## 9. Glossar

| Begriff | Bedeutung |
|---------|-----------|
| **ADR** | Architecture Decision Record — dokumentierte Architektur-Entscheidung |
| **CI** | Continuous Integration — automatische Prüfungen bei jeder Code-Änderung |
| **Composite Action** | Wiederverwendbarer CI-Baustein; hier die *eine* Stelle, an der der Scan definiert ist |
| **False Positive (FP)** | Fehlalarm — ein Treffer, der kein Secret ist |
| **Fingerprint** | gitleaks-Bezeichner `commit:datei:rule:zeile` eines Fundes |
| **GHAS** | GitHub Advanced Security — kostenpflichtig; schaltet Secret Scanning + Push Protection auf **privaten** Repos frei |
| **gitleaks** | Werkzeug, das Code/History nach Secrets durchsucht |
| **OIDC** | Publish ohne langlebiges Passwort über kurzlebige Nachweise (ADR-220) |
| **Push Protection** | blockiert `git push` mit erkanntem Secret **vor** dem Landen in der History |
| **Secret** | Zugangsdatum (Token/Schlüssel/Passwort), das nie in Code/History gehört |
| **Secret Scanning** | GitHub-Dienst, der Repos auf bekannte Secret-Muster prüft |

## 10. Referenzen

- Audit + Rollout: `achimdehnert/platform`#412 (2026-06-02), bfagent-Incident #410.
- ADR-210 (Gate am irreversiblen Rand) · ADR-226 (Mandatory Secret-Scan + shared Action) · ADR-220 (OIDC) · ADR-045 (Secrets-Storage).
- `.github/actions/gitleaks-scan/action.yml`, `.github/workflows/pypi-ci-adoption-gate.yml` (Meter-Vorlage).

## 11. Changelog

- 2026-06-02: Initial (Proposed) — aus Audit #412 + bfagent #410; P0 (CI-gitleaks auf 7 Repos) erledigt.
- 2026-06-03: `/adr-review` adressiert (`implementation_evidence`, §3 Pro/Contra, GHAS empirisch).
- 2026-06-03: `/adr-challenger` adressiert (ADR-045-Link; P2 by-construction via `onboard-repo`; GHAS in §7.3 beziffert; P-Schritte renummeriert).
- 2026-06-03: **Accepted** + gestrafft (~180 Z.); P1 erledigt (native auf 3 public Repos wieder ein).
- 2026-06-03: **Amendment** — „Org-Default für neue Repos" korrigiert: für `achimdehnert` (User-Account, keine Org) nicht anwendbar (`/orgs/...` 404, kein Scope-Problem) → neue Repos via P2-Scaffold; §2/§5/§6 entsprechend. Querverweis **KONZ-platform-002**: für org-/enterprise-eigene Repos liefert eine Enterprise Security Configuration native Push-Protection auch privat → dort Layer 1 nativ, CI-gitleaks → Defense-in-depth.
- 2026-06-03: **Amendment (KONZ-002-Gates)** — bewusste, dokumentierte Lockerung der KONZ-002-Kill-Kriterien (a)/(b) von „schriftlich/formal" auf **Budget-Owner-Aktennotiz** (DR-A/DR-B), Restrisiko vom Platform-Lead getragen und benannt; (c) bewiesen (PR #429). Operativer Plan + Aktennotizen: [`docs/runbooks/KONZ-002-consolidation-rollout.md`](../runbooks/KONZ-002-consolidation-rollout.md). **Harte Sperren bleiben:** GOV-Ownership/-Transfer (`ttz-lif`/`meiki-lra`) bis schriftlicher Träger-Sign-off; `pactive-de` (Dritt-Org). Reversal der „public native / private CI-Fallback"-Aufteilung erst mit dem ALT-D-Boundary-ADR (noch ausstehend).
