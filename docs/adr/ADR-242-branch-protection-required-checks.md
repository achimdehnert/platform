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

`draft` — entscheidungsreif bis auf zwei Gates (§7: Plan-Verfügbarkeit für private
Repos, Check-Namen-Inventur). Kandidat für den `enterprise-core`-Subset.

## Kontext & Problemstellung

Die „no-bypass"-Regel (rote CI wird nicht gemergt) existiert heute nur als
Konvention — **nicht als Enforcement**. Inventur-Befund (2026-06-09, shared-ci-Episode):

1. **0/14 Hubs haben required-status-checks auf `main`.** Nichts hindert einen
   Merge bei roter CI.
2. **Der Fall ist real eingetreten:** trading-hub#13 wurde manuell rot gemergt —
   der Defekt wanderte ungebremst auf `main`.
3. **Verschärfung durch Auto-Deploy:** mehrere Repos deployen bei Push auf `main`
   direkt nach Prod (`on: push: [main]` ohne Path-Filter — u. a. recruiting-hub,
   trading-hub, dms-hub, dev-hub; Drift-Memory 2026-06-06). Ein roter Merge ist
   dort nicht nur ein Repo-Problem, sondern ein **Prod-Deploy eines bekannten
   Defekts**.
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
   dieses ADRs.

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

## Offene Gates vor Accept (§7)

| Gate | Inhalt | Owner | billigster Check |
|---|---|---|---|
| G1 | Plan-Verfügbarkeit: gelten Rulesets/required checks für die **privaten** Repos der Orgs (Free vs. Team/Enterprise)? | ich | 1× `gh api` Ruleset-Create gegen ein privates Test-Repo (dry) bzw. Org-Plan-Read |
| G2 | Check-Namen-Inventur: welcher CI-Check ist je Repo der verbindliche (shared-ci-Konvergenz nutzen)? | ich | Script über `gh api /repos/<r>/commits/main/check-runs` |
| G3 | Welle-1-Repo-Liste bestätigen (Auto-Deploy-Inventur: `on: push: [main]`-deploy.yml je Repo verifizieren, nicht aus Memory) | ich | grep über deploy.yml aller Repos |

## Rollout (nach Accept)

| Phase | Inhalt | Aufwand |
|---|---|---|
| 1 | G1–G3 abräumen (Plan-Check, Check-Inventur, Welle-1-Liste) | 1 h |
| 2 | Ruleset-Template + Rollout-Script + Pilot auf platform | 1.5 h |
| 3 | Welle 1 (Auto-Deploy-Repos + risk-hub + mcp-hub) inkl. Negativ-Test | 1 h |
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
