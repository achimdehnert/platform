---
status: draft
date: 2026-06-11
decision-makers: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-209, ADR-226, ADR-230, ADR-234, ADR-235]
implementation_status: none
last_reviewed: 2026-06-11
staleness_months: 3
tags: [branch-protection, ci, governance, enforcement, no-bypass, enterprise-core]
---

# ADR-242: Fleet-weite Branch-Protection — required status checks auf `main` (no-bypass by construction)

> **Nummern-Hinweis:** 242 = nächste freie Nummer zum Draft-Zeitpunkt; final allokiert
> zur Merge-Zeit (ADR-228).

## Status-Hinweis

`draft` — **entscheidungsreif**: alle drei Gates (§7) sind am 2026-06-11
API-verifiziert abgeräumt. Kandidat für den `enterprise-core`-Subset.

## Kontext & Problemstellung

Die „no-bypass"-Regel (rote CI wird nicht gemergt) existiert heute nur als
Konvention — **nicht als Enforcement**. Inventur (API-verifiziert 2026-06-11,
alle 49 Repos mit `main`-Branch der achimdehnert-Installation):

1. **47/49 Repos ohne Branch-Protection auf `main`.** Nur platform (required
   check `guardian`) und risk-hub (volles Set inkl. Staging-Gate) sind
   geschützt. Nichts hindert in den übrigen 47 einen Merge bei roter CI.
2. **Der Fall ist real eingetreten:** trading-hub#13 wurde manuell rot gemergt —
   der Defekt wanderte ungebremst auf `main` (Drift 2026-06-09).
3. **Verschärfung durch Auto-Deploy:** **24 Repos** haben ein
   `on: push: [main]`-Deploy ohne Path-Filter (deploy.yml-Inventur 2026-06-11);
   davon defaulten ~20 auf `target_environment: production` — ein roter Merge
   ist dort ein **Prod-Deploy eines bekannten Defekts**. Ausnahmen: risk-hub
   (GitHub-Environment-Freigabe, kein Auto-Prod), bfagent (leeres
   Environment-Default + eingefroren).
4. **Wechselwirkung F4:** ein Teil der Flotte hat aktuell rote main-CI
   (F4-Programm, Stand 2026-06-08: Größenordnung 30+/57 Repos). Auf einem
   Repo mit roter main-CI blockiert ein required-check **jeden** Merge — das
   Enforcement muss daher der CI-Grün-Konvergenz **folgen**, nicht vorauslaufen.

Die Lehre aus ADR-226 gilt wörtlich: ein Gate ist nur dann ein Gate, wenn es
**unmittelbar vor der irreversiblen Aktion** sitzt und nicht umgangen werden
kann. Für „Defekt erreicht `main` (und damit ggf. Prod)" ist diese Stelle der
Merge — also Branch-Protection, nicht Konvention.

## Entscheidungstreiber

- **By-construction-Philosophie** (ADR-226, ADR-234/235): Regeln werden erzwungen
  und gemessen, nicht dokumentiert. Die Konvention ist nachweislich gedriftet.
- **Zwei-Personen-Kapazität:** kein Review-Zwang — der würde den Solo-Flow
  blockieren und Bypass-Druck erzeugen. Nur das Minimum erzwingen: CI grün.
- **Auto-Deploy-Risiko zuerst:** Repos mit `on: push: [main]`-Prod-Deploy und das
  Live-Kundenprodukt (risk-hub) haben die höchste Schadenshöhe.
- **Wartungsarm & idempotent:** Konfiguration als Code im platform-Repo,
  Rollout per Script, Drift per Meter — kein manuelles UI-Klicken pro Repo.
- **Kosten/Plan-Realität:** Branch-Protection für **private** Repos ist
  plan-gated (analog Push-Protection, Secret-Audit 2026-06-02) — die Baseline
  darf daran nicht scheitern (öffentliche Repos zuerst, private nach G1).

## Betrachtete Optionen

### Option A — Status quo (Konvention + Disziplin)

- Pro: kein Aufwand
- Contra: nachweislich gescheitert (trading-hub#13); Konvention ohne Enforcement
  driftet — exakt der Defekt-Typ, den ADR-234/235 adressieren. Abgelehnt.

### Option B — Required status checks via Ruleset, fleet-weit, ohne Review-Pflicht ✅ (vorgeschlagen)

Pro Repo ein **Branch-Ruleset** auf `main`: `required_status_checks` (der
Standard-CI-Check des Repos), `enforce` auch für Admins, **keine**
Review-Pflicht, keine weiteren Regeln. Konfiguration als JSON-SSoT in
`platform/governance/rulesets/`, Rollout per idempotentem Script (`gh api`),
Compliance per Meter (§Confirmation).

- Pro: erzwingt genau die eine gebrochene Regel (kein roter Merge); minimale
  Friktion; als Code versioniert; messbar; Rulesets sind per API verwaltbar
  und auditierbar (Disable/Bypass erscheint im Audit-Log)
- Contra: plan-gated für private Repos (G1); erfordert Check-Namen-Inventur
  (G2); blockiert Merges auf Repos mit roter main-CI → Rollout muss F4 folgen

### Option C — Zusätzlich required PR-Reviews (1 Approval)

- Contra: 2-Personen-Team — Review-Zwang blockiert Solo-Arbeit und erzeugt
  Selbst-Approve-Theater oder Bypass-Druck. Right-sizing: abgelehnt für die
  Baseline; pro Repo später zuschaltbar (z. B. risk-hub bei Team-Wachstum).

### Option D — Merge-Queue / Bot-Gate (Mergify o. ä.)

- Contra: neue Komponente/Vendor für ein Problem, das GitHub nativ löst;
  Overkill für die Flottengröße. Abgelehnt.

## Entscheidung (vorgeschlagen)

**Option B.** Konkret:

1. **Ruleset-SSoT:** ein generisches Ruleset-Template
   (`platform/governance/rulesets/main-required-checks.json`):
   Target `main`, `required_status_checks` = Standard-CI-Check des Repos,
   enforcement `active`, Bypass-Liste **leer**.
   **Check-Namen-Vorgabe (G2-Befund):** shared-ci-Repos liefern stabile Namen
   (`ci / Unit Tests`, `ci / Lint & Format`, …) — **aber**
   `ci / Coverage Gate (≥${{ inputs.coverage_threshold }}%)` erscheint je Repo
   teils unexpandiert/teils expandiert und ist als required-check-Name fragil.
   Vorgabe daher: shared-ci bekommt einen **Aggregat-Job mit statischem Namen**
   (z. B. `ci / gate`, needs: alle CI-Jobs) und genau dieser eine Check wird
   required — robust gegen Job-Umbenennungen und Threshold-Parameter.
2. **Kein Review-Zwang** in der Baseline (bewusster Trade-off, Option C).
3. **Break-Glass statt Bypass-Liste:** im Notfall wird das Ruleset temporär
   auf `disabled` gestellt (API-Call, erscheint im Audit-Log) und nach dem
   Notfall-Merge reaktiviert; der Meter meldet jedes disabled-Ruleset.
   Kein stehender Admin-Bypass.
4. **Rollout gated auf grüne main-CI** (F4-Kopplung): ein Repo bekommt das
   Ruleset erst, wenn seine main-CI grün ist — Reihenfolge nach Risiko:
   - **Welle 1:** Auto-Prod-Deploy-Repos + risk-hub + platform + mcp-hub
   - **Welle 2:** übrige Repos mit grüner CI
   - **Welle 3:** Rest, jeweils nach F4-Konvergenz
5. **Meter (Enforcement der Enforcement):** wöchentlicher scheduled Workflow
   `branch-protection-meter` in platform prüft via API: jedes Soll-Repo hat
   ein aktives Ruleset mit required check; Verletzung/disabled → Issue
   (Label `protection-violation`) + Discord. Der Meter ist die *Confirmation*
   dieses ADRs. **Hinweis (G2-Nebenfund):** die Profil-B-App (`iilgmbh-admin`)
   hat aktuell **kein** `checks: read` („Resource not accessible by
   integration") — der Meter braucht entweder diese App-Permission-Ergänzung
   oder läuft mit dem Actions-`GITHUB_TOKEN`/PAT.

## Konsequenzen

**Positiv:** „no-bypass" wird vom Wunsch zur Eigenschaft; rote Merges auf
Auto-Deploy-Repos (= Prod-Deploys von Defekten) sind by construction
ausgeschlossen; Compliance ist messbar; Konfiguration versioniert.

**Negativ:** Merges auf Repos mit flakiger CI werden härter (gewollt — Druck
Richtung F4); Break-Glass kostet im echten Notfall einen API-Call; private
Repos ggf. plan-gated (G1) — bis zur Klärung bleibt dort die Konvention.

**Neutral:** Review-Pflicht bleibt pro Repo nachrüstbar; Org-Level-Rulesets
(statt per-Repo) sind ein mögliches späteres Upgrade, wenn die
Enterprise-Konsolidierung (KONZ-002) greift.

## Confirmation (maschinell prüfbar)

1. `branch-protection-meter`-Workflow existiert in platform, läuft wöchentlich,
   Status grün (alle Soll-Repos: aktives Ruleset + required check vorhanden).
2. `governance/rulesets/` enthält das Template + die Soll-Repo-Liste; Rollout-
   Script ist idempotent (zweiter Lauf = 0 Änderungen).
3. Negativ-Test dokumentiert: ein PR mit rotem Check ist auf einem Welle-1-Repo
   nachweislich nicht mergebar (Screenshot/API-Response im Rollout-Protokoll).

## Gates vor Accept (§7) — alle abgeräumt (2026-06-11, API-verifiziert)

| Gate | Inhalt | Ergebnis |
|---|---|---|
| G1 ✅ | Plan-Verfügbarkeit private Repos | **Verfügbar, kein Plan-Gate.** Doppelbeweis: `GET /branches/main/protection` auf trading-hub (privat) → 404 „Branch not protected" (nicht 403 „Upgrade"); risk-hub (privat) **hat** bereits aktive Protection. |
| G2 ✅ | Check-Namen-Inventur | shared-ci-konvergente Repos liefern stabile `ci / <Job>`-Namen; **Fragilität:** Coverage-Gate-Name teils unexpandiert (`${{ inputs.coverage_threshold }}`) → Vorgabe Aggregat-Job `ci / gate` (§Entscheidung 1). Nicht konvergent: dev-hub (nur `contract-tests`). Nebenfund: Profil-B-App ohne `checks: read`. |
| G3 ✅ | Welle-1-Liste aus deploy.yml | **24 Repos** mit `on: push: [main]`-Deploy ohne Path-Filter; ~20 defaulten auf `production`. Ausnahmen: risk-hub (Environment-Freigabe), bfagent (leer + eingefroren). Ist-Schutz: nur platform + risk-hub (2/49). |

## Rollout (nach Accept)

| Phase | Inhalt | Aufwand |
|---|---|---|
| 1 | ~~G1–G3 abräumen~~ ✅ erledigt 2026-06-11 (siehe §7) | — |
| 2 | shared-ci Aggregat-Job `ci / gate` + Ruleset-Template + Rollout-Script + Pilot auf platform | 2 h |
| 3 | Welle 1 (Auto-Prod-Deploy-Repos mit grüner CI + mcp-hub) inkl. Negativ-Test | 1 h |
| 4 | branch-protection-meter + Discord-Alert | 1.5 h |
| 5 | Welle 2/3 nach F4-Konvergenz (event-getrieben, ADR-209-Programm) | laufend |

## Glossar

| Begriff | Erläuterung |
|---|---|
| **Branch-Protection / Ruleset** | GitHub-Funktion, die Regeln für einen Zweig erzwingt — hier: auf `main` darf nur gemergt werden, wenn die Prüfungen grün sind. Rulesets sind die neuere, per Schnittstelle verwaltbare Variante. |
| **Break-Glass** | Bewusst dokumentierter Notfall-Pfad: die Schutzregel wird kurzzeitig abgeschaltet, der Vorgang ist protokolliert und wird gemeldet — statt eines stillen Dauer-Schlupflochs. |
| **by construction** | Eigenschaft ist durch den Aufbau des Systems erzwungen, nicht von manueller Disziplin abhängig. |
| **CI (Continuous Integration)** | Automatische Prüfkette (Tests, Stil-Prüfungen), die bei jeder Code-Änderung läuft; „rot" = mindestens eine Prüfung schlägt fehl. |
| **Merge** | Übernahme einer Änderung in den Hauptzweig (`main`) — ab dort gilt sie als produktiv nutzbar und löst in einigen Repos automatisch ein Prod-Deployment aus. |
| **Meter** | Automatischer Mess-Job, der regelmäßig prüft, ob der Soll-Zustand real existiert, und bei Abweichung Alarm schlägt (ADR-234/235-Philosophie). |
| **no-bypass** | Hausregel: rote CI wird nicht gemergt — bisher Konvention, künftig erzwungen. |
| **required status checks** | Konkrete GitHub-Einstellung: benannte CI-Prüfungen müssen grün sein, sonst ist der Merge-Knopf gesperrt. |

## References

- ADR-209: CI-Health-Konvergenz-Programm (F4) — Rollout-Taktung Welle 2/3
- ADR-226: Publish-Gate by construction — Lehre „Gate unmittelbar vor der irreversiblen Aktion"
- ADR-230: Coding nur über Claude Code (PR-zentrierter Flow)
- ADR-234/235: Derived-Invariant-/Meter-Philosophie
- Drift-Memory 2026-06-09 (shared-ci-Tag-Episode): trading-hub#13 rot gemergt; 0/14 Hubs Branch-Protection
- Drift-Memory 2026-06-06: `on: push: [main]`-deploy.yml deployt nach Merge direkt Prod
- Secret-Prevention-Audit 2026-06-02: Plan-Gating nativer GitHub-Schutzfunktionen (Analogie für G1)
