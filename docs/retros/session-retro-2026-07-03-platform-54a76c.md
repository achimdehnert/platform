---
retro_schema: 1
date: 2026-07-03
repo_scope: [platform, mcp-hub, travel-beat, shared-ci]
session_id: 54a76c
footprint: deep
findings_total: 10
findings_survived: 8
refuted_rate: 0.20
phase3_refuted: 1
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, host-fix-not-mirrored-to-iac]
recurring_findings: [claim-before-cheapest-check, host-fix-not-mirrored-to-iac]
---

# Session-Retro 2026-07-03 — Deployment-Strategie-Arc (platform + Prod-Incident)

Scope: Aus „Deployment-Strategie analysieren" wurde KONZ-011 (#859), ADR-264 (Deployment-SSoT:
#878→#881→#882 accept), mcp-hub SSE-404-Fix (#165), Canary-Fix (#877), shared-ci Artefakt-Verify
(#17), plus Prod-Host-Eingriffe (nginx `location /mcp`, travel-beat web/caddy) nach einem
Host-Overload. Richter≠Angeklagter: 1 Collector (haiku) + 3 Finder + 3 Skeptiker (sonnet), alle
Belege unabhängig aus gh/git/curl neu gezogen.

## 1. Executive Summary
- **Kern-Ziel erreicht + extern gehärtet:** ADR-264 accepted mit Supersession-Matrix; ADR-021 (52 §-Refs) durch die Matrix vor Fehl-Ablösung gerettet; o3-Gegenmeinung eingearbeitet. Finder attestieren die Governance-Arbeit „solide + selbstkritisch".
- **Dominantes Muster (RECURRING, gate-pflichtig):** **Host-Fixes hinter dem Code** — nginx `/mcp` + docker-Netz nur am Host, NICHT ins getrackte IaC gespiegelt; der nginx-IaC-Spiegel warnt im Header selbst vor genau dieser Klasse (Vorfall 2026-06-01) → Rezidiv.
- **claim-before-cheapest-check erneut** — aber diesmal als **Über-Anklage**: „meine Merges heizten den Meltdown mit" ist unbelegt (Runner-Health-Check 07:09 grün, #884/885-CI auf ubuntu-latest). Bidirektional dieselbe Disziplin.
- **Falsifikation schützte in beide Richtungen:** meine Abschluss-Sorge „travel-beat down" war FALSCH — Dienst ist live (`/livez/`→200; die 404 war die Variante ohne Trailing-Slash).
- **ADR-Governance-Reihenfolge verletzt:** ADR-264 accepted (06:12) VOR Merge seiner Konzept-Basis KONZ-011 (06:47); ADR-264-Body sagt auf main weiter „Status proposed".

## 2. Befund-Tabelle (nur Survivor)
| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | nginx `location /mcp`-Fix am Host, NICHT in `infra/orchestrator-host/orchestrator.iil.pet.conf` gespiegelt — Datei warnt im Header vor genau dieser Klasse (2026-06-01) | fehlende Validierung | hoch | SURVIVES | Datei hat /sse, kein /mcp; `git log`→1 Commit 2026-06-01; mcp-hub #165 fügt /mcp im Code hinzu | **RECURRING** (2026-06-01) |
| 2 | travel-beat `docker network create bfagent_platform`-Pflaster stellt eine Abhängigkeit wieder her, die ADR-022 (accepted 2026-02-21) als „FALSCH → SOFORT/5min entfernen" führt; Quell-Repo bfagent archiviert | verfrühte Festlegung | mittel-hoch | SURVIVES | ADR-022 Z.88/404; `docker-compose.prod.yml:228` external; bfagent isArchived=true | — |
| 3 | Prod-Host-Eingriffe (nginx-Reload, docker-Netz, 2 Deploy-Re-Runs) + travel-beat-Deploy-Failure (04:43) haben KEIN GitHub-Artefakt (Issue/PR/Kommentar/Runbook) | Prozesslücke | hoch | SURVIVES | 0 Treffer org-weit für nginx/bfagent/overload/88.198; docs/retros ebenso | — |
| 4 | ADR-264 Frontmatter `status: accepted`, Fließtext (Z.18/28/130/144) sagt weiter „Status proposed / bei Accept wirksam" | fehlende Validierung | niedrig-mittel | SURVIVES | `git show origin/main:…ADR-264…` — Widerspruch wörtlich auf main | — |
| 5 | ADR-264 accepted (#882, 06:12) VOR Merge der deklarierten Konzept-Basis KONZ-011 (#859, 06:47) | ADR-Governance | mittel | SURVIVES | `gh pr view 882/859 --json mergedAt`: 06:12:30 vs 06:47:24 | — |
| 6 | Prod-Uptime-Canary blieb nach Fix #877 rot (4+ FAILURE-Runs); #877 fixte nur Dedup/Close, nicht Signal-Genauigkeit → 08:43-Run meldet 14 Hubs `000000`, die live 200 sind | Monitoring-Zuverlässigkeit | hoch | SURVIVES | 8/8 letzte Runs failure; runs-on ubuntu-latest ohne Retry; Direkt-curls 200 | — |
| 7 | Über-Anklage: „Session-Merges verursachten den Host-Overload mit" ist unbelegt (2h-Lücke; Runner-Health 07:09 grün; #884/885-CI auf ubuntu-latest) | fehlende Validierung | mittel | SURVIVES | `gh run list` Runner Health 07:09 SUCCESS; Deploy-Failure-Monitor vorbestehend rot | **claim-before-cheapest-check** |
| 8 | ADR-Nummer 2× in <24h neu vergeben (…→261→264) — Kollision mit in-flight-PRs #708/#838; Nummernvergabe prüft nur gemergte Dateien, nicht offene Branches | Werkzeug | mittel | SURVIVES | Squash-Commits #878; `adr_open_pr_guard` fing es reaktiv | — |

## 3. Scorecard (1–5, an Befunden verankert)
| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Kern-Ziel + externe Härtung erreicht; beide Prod-Dienste live (S-A refuted); kleine Mängel (Body-Widerspruch #4) |
| architektur_design | 4 | ADR-264/Matrix/021-Rettung + Streamable-HTTP solide (Finder-Lob); kein Design-Survivor |
| code_konventionstreue | 3 | IaC-Drift (#1), ADR-022-Verstoß (#2), Body-Inkonsistenz (#4) |
| risiko_debt | 2 | reale Infra-Schuld: IaC-Drift (#1), Netz-Pflaster (#2), untracked Host-State (#3), Canary rot (#6) |
| prozess_effizienz | 2 | 2 ADR-Umnummerierungen (#8) + Firefight über 3 widerlegte Hypothesen (Kontext zu #1/#3: Image/mkdir/Proxy alle host-seitig widerlegt) |
| entscheidungsqualitaet | 3 | Governance stark (Matrix/o3/021), aber Accept-vor-Konzept (#5) + Pflaster-statt-ADR-022-Fix (#2) + Schuld-Über-Claim (#7) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert; |Soll| == 8 Survivor)
| Ist (beobachtet, Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| nginx-Fix nur am Host, IaC-Spiegel unangetastet | Neue HTTP-Route im Code ⇒ **im selben PR** den nginx-IaC-Spiegel diffen; Gate „`location`-Diff Pflicht bei neuer Route" | #1 |
| `network create bfagent_platform` als Pflaster | Vor Host-Pflaster: `grep <symbol> docs/adr/` — existiert eine accepted-ADR-Vorschrift (ADR-022: rename→travelbeat_network)? Dann DIE umsetzen, nicht das Falsche zementieren | #2 |
| SSH-root-Reparatur ohne Spur | Jeder Host-Eingriff bekommt VOR/NACH einen Issue-Kommentar (Befehl + Ergebnis) — Vier-Augen-/Rekonstruktionsspur | #3 |
| Accept-PR flippte Frontmatter, ließ Body-„proposed" | Accept-PR macht `grep -n proposed <adr>` und räumt den Fließtext im selben Diff | #4 |
| ADR-264 accepted vor Konzept-Merge | Reihenfolge erzwingen: Konzept-PR mergen ODER `Refs`, BEVOR das ADR daraus accepted wird | #5 |
| Canary „gefixt" gemeldet, blieb rot | „Fix X" erst nach 1 grünem post-merge-Run behaupten; #877 adressierte Genauigkeit gar nicht → Retry/Backoff + Einzel-Hub-Isolation nötig | #6 |
| „meine Merges heizten mit" ohne Beleg | Kausalitäts-Claim = Hypothese bis zum Beleg (welcher Job, welcher Host, welche Zeit); Runner-Health/`runs-on` prüfen, DANN zuschreiben | #7 |
| ADR-Nummer 2× kollidiert | Nummernvergabe gegen **offene PR-Branches** prüfen (`adr_open_pr_guard` VOR dem Commit, nicht danach) | #8 |

## 5. Längsschnitt (retro_kpis.py über docs/retros/)
- **`claim-before-cheapest-check` ×4 → GATE-PFLICHT** (bereits); Befund #7 ist die neue Instanz (Über-Anklage-Richtung). Slugs: [0181a7-incr, 73003f, a50bc6, 54a76c].
- **`host-fix-not-mirrored-to-iac` — NEU als recurring** (Befunde #1+#3): der nginx-IaC-Header dokumentiert denselben Vorfall 2026-06-01 → in-the-wild Vorkommen-2, verwandt mit Memory `feedback_deploy_green_not_change_live`. Gate-Kandidat.
- refuted_rate 0.20 (1 phase3_refuted + 1 pre_refuted / 10) — erreicht **genau** die 0.2-„Theater"-Schwelle (nicht darüber); im Trend 0.09/0.00/0.00/0.17→0.20 der erste Wert, der sie erreicht (steigend). Der eine echte REFUTED (travel-beat live) war substanziell (schützte vor Über-Anklage).

## 6. Verankerung (kopierfertig — Mensch entscheidet)
### memory_candidates
1. **`feedback_host_fix_must_mirror_to_iac`** (drift: true) — Ein Host-seitiger Fix (nginx `location`, docker network, systemd) muss im **selben PR** ins getrackte IaC gespiegelt werden; sonst Drift + Rezidiv. Realfall 2026-07-03: nginx `location /mcp` am Host gesetzt, `infra/orchestrator-host/orchestrator.iil.pet.conf` unangetastet — obwohl deren Header genau diesen Vorfall (2026-06-01) vordokumentiert. Verwandt [[feedback_deploy_green_not_change_live]]. **Wie anwenden:** neue HTTP-Route/Netz/Mount im Code ⇒ vor „live/fertig" den IaC-Spiegel diffen + Host-Eingriff als Issue-Kommentar loggen.
2. **`feedback_host_bandaid_check_accepted_adr_first`** — Vor einem Host-Pflaster gegen ein Symptom: `grep <symbol> docs/adr/` — schreibt eine accepted-ADR bereits den echten Fix vor? Realfall 2026-07-03: `docker network create bfagent_platform` zementierte, was ADR-022 (2026-02-21) als „FALSCH → SOFORT/5min: rename travelbeat_network" führt. Instanz von claim-before-cheapest-check (Pflaster ohne Vor-Check der SoT).
3. **Ergänzung zu [[feedback_cheapest_check_in_retro_too]]** — die Disziplin gilt auch für **Selbst-Anklage**: „meine Merges verursachten den Ausfall" braucht denselben Beleg wie „nicht meins". Realfall 2026-07-03 Befund #7 (Meltdown-Kausalität unbelegt).

### adr_candidates
- **CI-Runner-Host-Isolation** (T3-Konzept angeboten, nicht gebaut): 23–25 Repo-Runner auf 1 Prod-Host (`infra/hosts.yaml`) = strukturelle Meltdown-Wurzel; ADR-257-Pilot nicht fleet-weit. → eigener /konzept-Strang.

## 7. Maßnahmen (Action Board, aus Soll-Ablauf)
🔵 **Ich kann sofort (auf dein Wort)**
| # | Item | Repo | PR/ADR | Status | Next Step |
|---|------|------|--------|--------|-----------|
| 1 | nginx `/mcp` in IaC-Spiegel nachziehen (+ Header-Klasse als Gate) | platform | infra/orchestrator-host/…conf | 🔵 | Block ergänzen, PR |
| 2 | travel-beat `bfagent_platform`→`travelbeat_network` per ADR-022 (Compose-PR) statt Host-Pflaster | travel-beat | ADR-022 | 🔵 | Compose-Fix + Netz-Preflight |
| 3 | ADR-264-Body „proposed"→accepted glätten | platform | ADR-264 | 🔵 | grep+Edit-PR |
| 4 | Canary: Retry/Backoff + Einzel-Hub-Isolation (000000-False-Positives) | platform | prod-uptime-canary.yml | 🔵 | härten |

🟢 **Dein Zug**
| # | Item | Repo | Status | Next Step |
|---|------|------|--------|-----------|
| 5 | Gate `host-fix-not-mirrored-to-iac` verankern (≥2, gate-pflichtig) | platform | 🟢 | Hook/CI-Check-Entscheid |
| 6 | shared-ci #17 (Artefakt-Verify) validieren + Rollout | shared-ci | 🟢 | review→tag |
| 7 | T3-/konzept CI-Runner-Host-Isolation | platform | 🟢 | „go konzept runner" |

## 8. Nicht verifiziert / Restlücken
- **Meltdown-Kausalität** (Befund #7): als Hypothese geführt — billigster Check wäre `journalctl`/Docker-Events auf dem Host zum Zeitfenster; nicht gezogen.
- **3 offene rote PRs #838/#884/#885** (Prozess-Finder A/B): **NICHT dieser Session zugeordnet** — #884/#885 = fremde Fable-Session (iil-adrfw-Retro), #838 = fremde adr-fleet-convergence-Session (Skeptiker Prozess-B via Co-Author + Retro-Referenz belegt). Fleet-Aufräumbedarf, nicht diese Session; daher kein Survivor, hier als Kontext.
- **Scope-Drift-ohne-Checkpoint** (Finder Soll-Ist #1): **pre_refuted** — die Scope-Spiegelung erfolgte mehrfach im Chat („3. Repo", „Prod-Perimeter"), für die artefakt-blinden Finder unsichtbar; kein echtes Versäumnis.
