---
retro_schema: 1
date: 2026-07-06
repo_scope: [nl2cad, billing-hub, dms-hub, recruiting-hub, iilgmbh-enterprise-config]
session_id: a2c373
footprint: deep
findings_total: 10
findings_survived: 6
refuted_rate: 0.40
phase3_refuted: 4
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 2
gate_candidates: [claim-before-cheapest-check, stale-local-clone-as-ground-truth]
recurring_findings: [claim-before-cheapest-check, stale-local-clone-as-ground-truth]
---

# Session-Retro — GHAS-Kostenfrage → Coverage-Audit → Enterprise-Config-Fix (2026-07-06)

## 1. Executive Summary
- Auslöser war eine **Advisory-Frage** („lohnen GHAS-$91,47, gibt es eigene Alternativen?"). Endzustand korrekt: Kostenfrage beantwortet ($44,10/Monat verifiziert, per-Person, nichts zu kündigen), reale Lücke (nl2cad) geschlossen, tax-hub/nl2iot-hub auf slim-prevention — **aber der Weg dahin war laut**.
- **Ein dominanter Wurzelfehler**, 6 überlebende Befunde teilen ihn: **State behaupten/handeln, bevor der billigste echte Check läuft** (`claim-before-cheapest-check`) — hier ≥5× in einer Session.
- Konkretes Teuerstes: „13 von 20 Repos ungeschützt" war 13× falsch (real 1) → 3 überflüssige PRs in 5 Min auf/zu. Ursache: grep nach Literal statt `uses:`-Vererbung auflösen, falsche Org im Muster, stale lokale Klone.
- **Recovery-Disziplin war gut** (schnell, ehrlich, vollständig aufgeräumt, echter CI-Lauf als Korrektiv). **Prevention-Disziplin war die Schwäche.**
- Scope/Gate-Vorwürfe des Scope-Finders (Gate 3/4 umgangen, Frage nie beantwortet) sind **falsifiziert** — Over-Diagnosen, die die harte Freigabe-Spur (User „C dann A"/„ob CodeQL raus"/„go"/eigenhändiger Token-Refresh) unterschlugen.

## 2. Befund-Tabelle
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| A | „13/20 Repos ungeschützt" — real 1 (nl2cad); grep-Literal übersah shared-CI-Vererbung + falsche Org + stale Klone | fehlende Validierung | hoch | SURVIVES | billing-hub `ci.yml` → `uses: iilgmbh/shared-ci/_ci-python.yml` (blockierender gitleaks-`secrets-scan`-Job); Close-Kommentare #26/#5/#12 | Muster ×12 Retros |
| B | Wurzel: Proxy-statt-echter-Check ≥5× in einer Session (Coverage-grep, stale Klon, org-Rolle statt Token-Scope, „self-host spart $1100" vs. KONZ-002, „Bandit fleet-wide" real 3/62) | Prozesslücke / Evidenz | hoch | SURVIVES | Instanzen git-belegt: #A (grep), #C (stale-Klon-PRs), #E (org-Rolle); `retro_kpis.py` ×12 | **gate-pflichtig (×12)** |
| C | 3 Redundanz-PRs geöffnet 16:47:26–30, geschlossen 16:52:56–17:53:00 (je 5m30s) — Wasted Motion | fehlende Validierung | mittel | SURVIVES | `gh pr view` Timestamps + identische Close-Kommentare | stale-clone ×2 |
| D | Copy-Paste: dms-hub#5 + recruiting-hub#12 PR-Body enthält „billing-hub: 3 verifizierte False Positives" (repo-fremder Fakt) | Werkzeug/Sorgfalt | niedrig | SURVIVES | `gh pr view --json body` beider PRs | — |
| E | Capability vor Check behauptet: „kein Scope-Wall, ich kann ausführen" (org-Rolle=admin) → attach 403 (braucht admin:org) → Enterprise-Endpoint 422 (kein selected) → 2 OAuth-Flows für den User | verfrühte Festlegung | mittel | SURVIVES | Audit-Log remove→apply 07:31 UTC; 403/422-Verlauf | claim-before-check-Familie |
| G | Wiederholt ungeprüfte/kaputte Links an den User (u.a. `…/251767/edit` = Editor statt Apply) | Kommunikation | mittel | SURVIVES (transkript-belegt, nicht git) | User-Turn zitiert das falsche `…/edit` als Fehl-Link zurück; API `html_url` war Editor-Endpoint | — |
| F | ~~admin:enterprise war unnötig~~ | — | — | REFUTED | Config 251767 ist `target_type: enterprise` → admin:enterprise load-bearing | — |
| H | ~~Gate 3/4 umgangen, keine Freigabe~~ | — | — | REFUTED (Over-Diagnose) | Freigaben „C dann A"/„go"/„ob CodeQL raus" + User-eigener Token-Refresh | — |
| I | ~~Config-Downgrade ohne Owner-Entscheidung~~ | — | — | REFUTED (Over-Diagnose) | User: „für nl2iot-hub/tax-hub, ob CodeQL raus" — exakt diese 2 | — |
| J | ~~Kostenfrage nie beantwortet~~ | — | — | REFUTED (Over-Diagnose) | Juni-GHAS $44,10 im Gespräch belegt (billing usage API) | — |

## 3. Scorecard (1–5, ganzzahlig, je an Befund verankert)
| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 3 | Endzustand korrekt (A-Fix, Config, Antwort), aber signifikanter Rework-Umweg (C) + temporär 13×-Risiko-Fehldarstellung (A) |
| architektur_design | 4 | **kein Survivor betrifft Architektur** (A–G alle Prozess/Verifikation); kanonische Muster genutzt (secret-scan.yml, slim-prevention = KONZ-002) |
| code_konventionstreue | 4 | conventional commits + kanonischer Workflow; einzige Blemish = Copy-Paste-PR-Body (#D) |
| risiko_debt | 3 | Folge von #E: Token trägt jetzt dauerhaft admin:enterprise+admin:org (stehende Angriffsfläche) — realer Debt bis Rücknahme (M3) |
| prozess_effizienz | 2 | 3 Redundanz-PRs (C) + 2 OAuth-Flows (E) + Link-Iterationen (G) — verfehlt mit Rework |
| entscheidungsqualitaet | 2 | ≥5× Proxy-basierte Fehlschlüsse (B), self-korrigiert aber zu spät (nach 3 PRs statt davor) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #) — |Soll| == 6 Survivors
| Ist (mit Beleg) | Soll | eliminiert |
|---|---|---|
| grep nach Literal `gitleaks` in Repo-eigener `ci.yml`; „13 offen" gefolgert | Coverage = **`uses:`-Kette auflösen** (repo → shared-CI-Workflow) ODER Actions-Job-Liste (`gh api repos/…/actions/workflows`) — nie Literal-grep als Absence-Beweis | #A |
| 4 verschiedene Fehlschlüsse aus billigen Proxys | **Vor jeder prüfbaren State-Aussage** den unabhängigen Check gegen origin/echten Lauf ziehen; Proxy-Output = Kandidat, nicht Schluss | #B |
| 3 Fleet-PRs simultan aus einer (falschen) Audit-Ausgabe geöffnet | **Ein Canary-PR**, dessen CI abwarten (deckt vorhandenen `secrets-scan`-Job auf), erst dann fan-out | #C |
| billing-hub-Template unverändert in 2 andere PR-Bodies kopiert | pro-Repo-Substitution/Review vor `gh pr create`; kein Multi-PR aus einem ungeprüften Template | #D |
| „org-Rolle=admin → ich kann ausführen"; dann 403/422 | **Preflight des echten Ziel-Endpoints** (Scope + `scope`-Fähigkeit) vor „ich kann"; Rolle ≠ Token-Scope | #E |
| geratene/abgeleitete UI-Deep-Links gepostet | nur Links posten, die in-Turn als ladend geprüft sind (Docs via WebFetch) ODER On-Screen-Labels; auth. UI nie raten | #G |

## 5. Längsschnitt (retro_kpis.py — Pflicht)
- `python3 tools/retro_kpis.py`: **`claim-before-cheapest-check` in 12/12 Retros** → einer von 8 gate-pflichtigen Slugs. Diese Session = erneutes Vorkommen (B/E). Der Hebel ist **kein weiteres Memo**, sondern die bereits geforderte Gate-Verankerung.
- `stale-local-clone-as-ground-truth`: bisher ×1 (e17299) → mit dieser Session **×2 ⇒ Gate-Pflicht** (A/C stützen sich auf stale Klone).
- `refuted_rate`-Band gesund (0,40; kein 3× >0,8 / <0,2). Score-Kontext: `prozess_effizienz` (2) und `entscheidungsqualitaet` (2) liegen **unter** dem Retro-Mittel (3,21 / 3,29) — diese Session war prozess-schwächer als der Schnitt.

## 5b. Autonomie-Kalibrierung
- **over_act = 0** — jede gated Aktion hatte eine passende explizite Freigabe (Skeptiker refutierte H/I als Over-Diagnose; Token-Refresh vom User selbst ausgeführt). Autonomie-Grenze wurde **eingehalten**.
- **over_ask = 0** — keine deterministisch-reversible Aktion unnötig vorgelegt; nl2cad-Merge-Frage war korrekt (Merge = Prod-Schritt).
- **Kalibrierungs-Schluss:** Die Schwäche dieser Session war **nicht** Autonomie-Grenze, sondern **Verifikations-Disziplin vor dem Handeln** — Charter bleibt, Gate `claim-before-cheapest-check` ist der Hebel.

## 6. Verankerung (kopierfertig — Mensch entscheidet)
**memory_candidates:**
1. `coverage-detection-resolve-uses-inheritance` (type: feedback) — „Secret-Scan-/CI-Coverage eines Repos NIE per Literal-grep in der Repo-eigenen Workflow-Datei bestimmen — das übersieht Vererbung via `uses: <org>/shared-ci/_ci-python.yml`. Richtig: `uses:`-Kette auflösen oder `gh api repos/…/actions/workflows`. Beleg: GHAS-Audit 2026-07-06, 13×-Fehlklassifikation. Why: Absence-of-evidence aus einem Teil-Blick ist kein Beweis. Link [[fleet-greps-lokale-clones-stale]], [[ghas-cost-per-person-not-drop]]."
2. `capability-from-role-not-token-scope` (type: feedback) — „‚Ich kann ausführen' erst behaupten, wenn der **echte Ziel-Endpoint** preflight-geprüft ist (Token-Scope via `gh api -i` + unterstützte `scope`-Werte). Org-Rolle=admin ≠ Token-Scope. Beleg: attach 403(admin:org)+422(kein selected) → 2 OAuth-Flows. Link [[only-verified-links]]."

**adr_candidates:** keiner — reine Prozess-/Verifikations-Lehren, folgen bestehendem Muster (ADR-Schwelle nicht erreicht).

## 7. Maßnahmen (Action-Board, aus Soll-Ablauf abgeleitet)
| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Gate `claim-before-cheapest-check` als Hook/CI schärfen (coverage-Proxy + capability-Claim ergänzen) | platform / ~/.claude/hooks | evidence_claim_scanner.py | 🟢 offen | du: entscheiden, ob Hook-Erweiterung (Scanner fängt Deploy/Verify-Marker, nicht diese Klassen) |
| M2 | 2 memory_candidates verankern (§6) | memory | — | 🟢 offen | du: ok → ich schreibe die 2 Memories |
| M3 | Token-Scope zurücknehmen falls admin:enterprise/admin:org nicht dauerhaft gewollt | — | — | 🟢 offen | du: `gh auth refresh` mit reduzierter Scope-Liste |
| M4 | Diesen Report committen (Längsschnitt lebt in git) | platform | docs/retros/…-a2c373.md | 🔵 ich sofort | ich: Branch + PR (kein Direct-main) auf dein ok |
| M5 | Prävention #C+#D: „Canary-PR-first vor Fleet-Fan-out + pro-Repo-Body-Review" in memory `coverage-detection-resolve-uses-inheritance` (§6.1) als How-to-apply ergänzen | memory | — | 🟢 offen | du: ok → in M2 mitschreiben |

**Soll→Anker-Abdeckung (alle 6):** #A→M2.1 · #B→M1 · #C→M5 · #D→M5 · #E→M2.2/M3 · #G→bereits verankert (`only-verified-links`, diese Session).

## 8. Nicht verifiziert (Restlücken)
- **Freigabe-Spur nur im Gesprächsverlauf**, nicht in durablen Artefakten (PR-Body/Commit) — ein reiner Artefakt-Auditor (wie Finder 1) kann approved/unapproved nicht unterscheiden. Billigster Fix: bei Security-Config-Writes die Freigabe im PR-Body/Commit-Msg zitieren. (Kein Befund — Prozess-Notiz.)
- **admin:enterprise-Nutzung:** Skeptiker ruled „load-bearing", der erfolgreiche attach lief aber über den **Org**-Endpoint (admin:org). Ob admin:enterprise für den Endzustand strikt nötig war, ist nicht sauber isoliert — billigster Check: attach mit nur admin:org auf einem Test-Repo. (Als REFUTED akzeptiert, Restzweifel notiert.)
- **dms-hub Coverage-Nuance:** dms-hub bindet shared-CI nur in `deploy.yml` (push), nicht `ci.yml` (PR) → gitleaks post-merge, nicht PR-blockierend. „Nicht ungeschützt" stimmt, aber schwächer als bei billing-hub/recruiting-hub. Nicht als eigener Befund gewertet.
- **Beleg-Härte B & G (Meta-Review-Flag):** #B ruht auf git-belegten Instanzen (#A/#C/#E) + `retro_kpis.py`-Zähler — solide. #G ruht auf dem **Gesprächstranskript** (User zitierte den falschen `…/edit`-Link zurück), nicht auf einem git-Artefakt; als transkript-belegt markiert, nicht als git-verifiziert. Billigster unabhängiger Check für G existiert nicht (Links leben nicht in git) → bewusst schwächere Beleg-Klasse.
