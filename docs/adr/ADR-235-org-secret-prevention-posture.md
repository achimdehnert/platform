---
status: proposed
implementation_status: partial
date: 2026-06-02
decision-makers: Achim Dehnert
domains: [security, ci-cd, governance, secrets]
scope: platform
relates_to: [ADR-210, ADR-220, ADR-226]
tags: [secret-scanning, push-protection, gitleaks, ghas, prevention, cross-repo, by-construction]
---

# ADR-235: Org-weite Secret-Prevention-Posture — bindender Gate am Push-Rand (native Push-Protection) mit CI-gitleaks als Fallback

| Attribut       | Wert                                                              |
|----------------|-------------------------------------------------------------------|
| **Status**     | Proposed                                                          |
| **Scope**      | platform (org-weit, alle Repos `achimdehnert`)                    |
| **Repo**       | platform                                                          |
| **Erstellt**   | 2026-06-02                                                        |
| **Autor**      | Achim Dehnert                                                     |
| **Reviewer**   | –                                                                 |
| **Supersedes** | –                                                                 |
| **Relates to** | ADR-210 (Gate am irreversiblen Rand), ADR-226 (Mandatory Secret-Scan / shared Action), ADR-220 (OIDC Trusted Publishing) |
| **Quelle**     | Secret-Prevention-Audit 2026-06-02 (#412) + bfagent-Incident (#410) |

---

## 1. Kontext

### 1.1 Ausgangslage

Der bfagent-Incident (#410) brachte 78 committete Secrets in der Git-History ans
Licht (rotiert/tot, kein Live-Exposure mehr). Die Folgefrage war nicht „läuft
gitleaks?", sondern: **„läuft ein Secret-Scan zuverlässig auf JEDEM Repo — auch
wenn das Repo selbst nichts dafür konfiguriert?"**

Ein org-weiter Audit am 2026-06-02 (#412) über 54 aktive Repos ergab ein
überraschend klares, an der **Repo-Visibility** ausgerichtetes Bild:

- **26 public Repos**: GitHub-native Secret Scanning **+ Push Protection** ist
  **gratis und aktiv**. Das ist der stärkste denkbare Gate — er blockiert den
  Secret **vor** dem Landen in der History, also genau am irreversiblen
  Push-Rand (die Lehre aus ADR-210).
- **~25 private Repos**: native Scanning ist **absent** — GitHub Advanced
  Security (GHAS), das Secret Scanning auf privaten Repos freischaltet, ist
  nicht lizenziert. Der einzige serverseitige Fallback ohne GHAS ist CI-seitiges
  gitleaks (geteilte `gitleaks-scan`-Composite-Action, ADR-226).
- **Anomalie**: 3 *public* Repos hatten den gratis Schutz **abgeschaltet**:
  `platform`, `writing-hub`, `lastwar-bot`.

### 1.2 Problem / Lücken

- Der einzige serverseitige Scan vieler privater Repos hing bisher an der
  **freiwilligen Adoption** von `_ci-python.yml`. bfagent rief den Reusable nicht
  auf → kein Gate. Das F4-CI-Programm zeigt: viele Repos haben rote/fehlende CI.
- 7 private Repos hatten **null** serverseitigen Secret-Scan (bahn-hub,
  design-hub, desktop-setup, django-lms-lite, iil-fieldprefill, illustration-fw,
  nl2iot-hub). Beim ersten Scan nach dem Rollout fand sich in `desktop-setup`
  eine `secrets.env` mit GitHub-OAuth-Token **im aktuellen HEAD** (Tokens
  bereits rotiert; Datei entfernt) — exakt die bfagent-Fehlerklasse, vorher
  latent.
- Es gibt **keine festgelegte Posture**, *welcher* Gate verbindlich ist und
  *wo* er sitzt. Ohne Festlegung driften neue Repos zurück in die Lücke.

### 1.3 Constraints

- **GHAS auf privaten Repos kostet** (pro aktivem Committer/Monat). Eine
  org-weite Anschaffung ist eine Budget-Entscheidung, keine reine
  Architektur-Frage.
- CI-gitleaks ist **post-push**: Ein Secret ist beim Anschlagen des Gates bereits
  in der Remote-History → muss als kompromittiert gelten (rotieren). Nur
  Push-Protection ist **pre-history** (prevention statt detection).
- Lösungen dürfen nicht den per ADR-230 **abgeschalteten Auto-Distributor**
  voraussetzen — Workflow-Platzierung erfolgt bewusst pro Repo.

## 2. Entscheidung

Wir legen eine **gestufte, by-construction durchsetzbare** Secret-Prevention-Posture
für die gesamte Org fest:

- **Layer 1 — Prävention, bindend, am Push-Rand (bevorzugt).** GitHub-native
  Secret Scanning **+ Push Protection** ist **verpflichtend aktiviert auf jedem
  Repo, auf dem es kostenfrei verfügbar ist** — d. h. **allen public Repos**.
  Die 3 abgeschalteten (`platform`, `writing-hub`, `lastwar-bot`) werden wieder
  eingeschaltet; für neue public Repos gilt es als Org-Default. Dies ist der
  ADR-210-korrekte Gate: er verhindert, dass der Secret je in die History
  gelangt.

- **Layer 2 — Detektion-Fallback, post-push/pre-merge (für Repos ohne native).**
  Private Repos haben ohne GHAS keinen nativen Gate. Für sie ist der Standalone-
  Workflow `secret-scan.yml` (auf `push:main` + `pull_request`), der die
  geteilte `achimdehnert/platform/.github/actions/gitleaks-scan@main`-Action
  ruft, **verpflichtende Baseline** — entweder direkt oder transitiv über
  `_ci-python.yml` (das dieselbe Action trägt, ADR-226). Bereits ausgerollt auf
  die 7 zuvor ungeschützten Repos.

- **Layer 0 — beratend, shift-left.** Der `pre-commit`-gitleaks-Hook bleibt als
  lokale Entwickler-Bequemlichkeit (fängt vor dem Commit, aber clientseitig
  umgehbar → kein verbindlicher Gate).

- **GHAS org-weit kaufen = bewusst aufgeschobene Entscheidung** (siehe §3,
  Option 3) mit dokumentiertem Trigger (§7.3 / §8). Bis dahin ist CI-gitleaks die
  durable Baseline für private Repos; GHAS bleibt der empfohlene **Upgrade-Pfad**
  zuerst für die privaten Repos mit höchstem Blast-Radius.

## 3. Betrachtete Alternativen

1. **Status quo (Scan hängt an `_ci-python.yml`-Adoption).** Verworfen: genau die
   bfagent-Lücke — Repos ohne Caller (oder mit roter CI) sind ungeschützt.
2. **Nur CI-gitleaks überall, kein native.** Verworfen: ignoriert den gratis,
   architektonisch überlegenen Push-Rand-Gate, der auf public Repos schon da ist;
   CI ist post-push (Secret landet zuerst in History).
3. **GHAS sofort org-weit kaufen (native überall, auch privat).** Stärkste
   Lösung — Prävention am Push-Rand für *alle* Repos. Nicht als sofortige
   Entscheidung gewählt: erzwingt laufende Kosten, die eine Org-/Budget-Freigabe
   brauchen, nicht eine Architektur-Festlegung. Bleibt dokumentierter
   Upgrade-Pfad (§2, §7.3).
4. **Gestufte Posture (Layer 0/1/2) mit GHAS als aufgeschobenem Upgrade.**
   **Gewählt** — schließt die Lücke sofort und gratis, nutzt den stärksten Gate
   wo verfügbar, und macht die Kostenentscheidung explizit statt implizit.

## 4. Begründung im Detail

- **Der Gate gehört an den irreversiblen Rand (ADR-210).** Für Secrets ist die
  irreversible Aktion der `git push` in die Remote-History. Native Push
  Protection sitzt genau dort und ist serverseitig **nicht** per `--no-verify`
  umgehbar (nur mit auditiertem „allow secret"-Override). CI-gitleaks ist
  bestenfalls Detektion danach.
- **Kostenfreie Stärke zuerst ausschöpfen.** Auf public Repos ist der beste Gate
  gratis verfügbar — ihn abgeschaltet zu lassen (3 Repos) ist reiner Verlust.
- **Keine Coverage ohne Mechanismus.** Eine Posture, die nur „sollte scannen"
  sagt, driftet zurück (ADR-226-Lehre: ein Mandat ohne Messung lässt das Fenster
  offen). Daher §8 ein wiederkehrender Audit-Meter analog
  `pypi-ci-adoption-gate.yml`.
- **DRY.** Layer 2 nutzt dieselbe `gitleaks-scan`-Action mit einem Versions-Pin
  (ADR-226) — keine 14 divergierenden Inline-Scans.

## 5. Implementation Plan

- **P0 — erledigt (2026-06-02):** `secret-scan.yml` auf die 7 ungeschützten
  privaten Repos ausgerollt (PRs gemerged); `desktop-setup`-Fund bereinigt;
  Audit als #412 dokumentiert.
- **P1:** Native Push Protection auf `platform`, `writing-hub`, `lastwar-bot`
  wieder einschalten; Org-Default „enable Secret Scanning + Push Protection for
  new public repositories" setzen. (`lastwar-bot` ist public → native deckt es
  ab, kein CI-Workflow nötig.)
- **P2:** Audit-Meter (wöchentlich, analog `pypi-ci-adoption-gate.yml`): prüft
  je Repo die Invariante (§8) und pflegt **ein** Tracking-Issue mit
  schrumpfendem Backlog. Informational, fällt nie hart.
- **P3 — aufgeschoben:** GHAS-Kosten/Nutzen erneut bewerten, sobald ein Trigger
  (§7.3) feuert; bei Freigabe zuerst die privaten Repos mit höchstem
  Blast-Radius migrieren.

## 6. Risiken

- **CI-gitleaks ist post-push (Layer 2):** Ein Secret eines privaten Repos landet
  vor dem roten Gate in der History → Rotation nötig. Mitigation: Layer-0-Hook +
  schnelle Rotation + der Gate erzwingt einen roten PR (sichtbar, nicht
  mergebar ohne Triage). Echte Prävention nur via GHAS (P3).
- **`.gitleaksignore`-Missbrauch:** könnte einen echten künftigen Secret
  verdecken. Mitigation: nur **fingerprint-genaue** Suppressions (kein breites
  Allowlisting), im PR reviewt; die Action echot vorhandene Escape-Hatches als
  Warnung (Transparenz, ADR-226).
- **Setting-Drift auf public Repos:** Push Protection könnte wieder abgeschaltet
  werden. Mitigation: Org-Default + P2-Meter prüft `secret_scanning.status` je
  public Repo.
- **Heuristik-False-Positives** (z. B. `generic-api-key` auf Domänen-Keys, siehe
  bahn-hub): erzeugen Reibung. Mitigation: fingerprint-Suppression als
  dokumentierter Pfad.

## 7. Konsequenzen

### 7.1 Positiv

- Jeder Secret-Pfad hat einen verbindlichen serverseitigen Gate; die
  bfagent-Lücke ist by-construction geschlossen, nicht adoptions-abhängig.
- Der stärkste Gate (Push-Rand) ist auf allen public Repos gratis scharf.
- Eine messbare Invariante statt eines laufenden Reparatur-Tasks.

### 7.2 Trade-offs

- Privat bleibt ohne GHAS Detektion-statt-Prävention (post-push).
- Laufende Pflege eines Audit-Meters + gelegentliche FP-Triage.

### 7.3 Nicht in Scope / aufgeschoben

- **GHAS-Anschaffung** (Budget-Entscheidung). Trigger zum Wiederaufgreifen:
  (a) ein echter Secret erreicht trotz CI-gitleaks die History eines privaten
  Repos, **oder** (b) die Committer-Zahl macht die Seat-Kosten günstiger als die
  Rotationskosten eines Incidents.
- History-Purge alter toter Funde (Rotation ist der härtere Hebel; nur bei
  Bedarf).
- OIDC-Trusted-Publishing-Migration der Legacy-Publish-Workflows (ADR-220).

## 8. Validation Criteria

Die Posture gilt als eingehalten, wenn (maschinell prüfbar, vgl. Audit-Skript in #412):

1. **Jedes public Repo:** `security_and_analysis.secret_scanning.status == enabled`
   **und** `..._push_protection.status == enabled` (`gh api repos/<owner>/<repo>`).
2. **Jedes private Repo:** ein serverseitiger gitleaks-Workflow ist auf dem
   Default-Branch präsent (direktes `secret-scan.yml` **oder** `_ci-python.yml`-Caller).
3. **Audit-Meter** läuft wöchentlich grün bzw. mit schrumpfendem Backlog (ein
   Tracking-Issue).
4. → `implemented`, sobald P1 + P2 stehen; → `verified`, sobald der Meter ≥2
   Wochen ohne offene Invarianten-Verletzung läuft.

## 9. Glossar

| Abkürzung | Bedeutung |
|-----------|-----------|
| **ADR** | Architecture Decision Record — dokumentierte Architektur-Entscheidung |
| **CI** | Continuous Integration — automatische Prüfungen bei jeder Code-Änderung |
| **Composite Action** | Wiederverwendbarer CI-Baustein; hier die *eine* Stelle, an der der Scan definiert ist |
| **False Positive (FP)** | Fehlalarm — ein Treffer, der in Wahrheit kein Secret ist |
| **Fingerprint** | Eindeutiger gitleaks-Bezeichner `commit:datei:rule:zeile` eines Fundes |
| **GHAS** | GitHub Advanced Security — kostenpflichtiges Paket, das u. a. Secret Scanning + Push Protection auf **privaten** Repos freischaltet |
| **gitleaks** | Werkzeug, das Code/History nach versehentlich enthaltenen Secrets durchsucht |
| **OIDC** | Veröffentlichen ohne langlebiges Passwort über kurzlebige, geprüfte Nachweise (ADR-220) |
| **Push Protection** | GitHub-Funktion, die einen `git push` mit erkanntem Secret **vor** dem Landen in der History blockiert |
| **Secret / Geheimnis** | Zugangsdatum (Token, Schlüssel, Passwort), das nie in Code/History gehört |
| **Secret Scanning** | GitHub-Dienst, der Repos auf bekannte Secret-Muster prüft |

## 10. Referenzen

- Audit + Rollout: `achimdehnert/platform`#412 (2026-06-02), bfagent-Incident #410.
- ADR-210 — Gate unmittelbar vor der irreversiblen Aktion (PyPI-Publish-Gate).
- ADR-226 — Mandatory blocking Secret-Scan + geteilte `gitleaks-scan`-Composite-Action.
- ADR-220 — OIDC Trusted Publishing für PyPI.
- `.github/actions/gitleaks-scan/action.yml`, `.github/workflows/pypi-ci-adoption-gate.yml` (Meter-Vorlage).

## 11. Changelog

- 2026-06-02: Initial (Proposed). Aus dem org-weiten Secret-Prevention-Audit
  (#412) und dem bfagent-Incident (#410); CI-gitleaks-Rollout auf 7 private
  Repos bereits erledigt (P0).
