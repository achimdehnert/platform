---
concept_id: KONZ-platform-015
title: "Transparente & stabile Infrastruktur dev/staging/prod (Post-bfagent-Dekommissionierung)"
pipeline_status: pilot   # 2026-07-10: als MVP angenommen (Entscheid Achim 07-09, formalisiert 07-10) + Umsetzung begonnen (Nachtrag §14, Reconcile-Sweep live)
tier: T3
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "Amendment (ADR-264 D2-Delta + ADR-021 §2.17-Delta, REC-6)"
review_by: "2026-09-07"
kill_criteria: "Bis 2026-09-07 (T+60), REVIDIERT per Nachtrag §14 (2026-07-10): (a) Drift-Kennzahl (registry-live-reconcile.yml, NEU+baselined) nicht ≤3 mit 0 abgelaufenen Baseline-Einträgen ODER (b) kein fail-closed Dead-Reference-Gate mit dokumentiertem rotem CI-Testlauf im weltenhub-Deploy-Pfad ODER (c) scripts/checks/staging_*.sh weder verdrahtet noch gelöscht ODER (d) Gate-Fehlalarme: mehr als 0 FP in den ersten ≥10 Shadow-Läufen ohne beschlossenen Scope-Fix (absolute Zählung statt %-Quote — §14.4) → Rückbau statt Erweiterung (Schema-Felder deprecaten, Gate-Step entfernen, Alternative A3 als Fallback)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "docs/adr/ADR-264-canonical-deployment-strategy-and-supersession-gate.md", commit_or_pr: "accepted 2026-07-03, #882", opened_in_session: true}
  - {claim_id: C2, source_path: "docs/adr/ADR-210-local-staging-prod-architecture.md", commit_or_pr: "superseded_by: ADR-264", opened_in_session: true}
  - {claim_id: C3, source_path: "docs/adr/ADR-021-unified-deployment-pattern.md", commit_or_pr: "§2.17 accepted 2026-06-01", opened_in_session: true}
  - {claim_id: C4, source_path: "registry/repos.yaml", commit_or_pr: "main, 393 lines", opened_in_session: true}
  - {claim_id: C5, source_path: "registry/github_repos.yaml", commit_or_pr: "main, header self-declares SSoT, generated 2026-04-03", opened_in_session: true}
  - {claim_id: C6, source_path: "weltenhub/.github/workflows/deploy.yml", commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C7, source_path: "weltenhub/docker-compose.prod.yml + /opt/weltenhub/docker-compose.prod.yml (host)", commit_or_pr: "byte-identical, verified live", opened_in_session: true}
  - {claim_id: C8, source_path: "/opt/hub-builds/weltenhub/docker-compose.override.yml (host-only, not in git)", commit_or_pr: "host file, .bak-20260706 sibling", opened_in_session: true}
  - {claim_id: C9, source_path: ".github/CODEOWNERS", commit_or_pr: "main, line 7", opened_in_session: true}
  - {claim_id: C10, source_path: ".github/workflows/adr-validate.yml", commit_or_pr: "main, line 48, wires tools/check_deploy_adr_supersession.py", opened_in_session: true}
  - {claim_id: C11, source_path: "staging-demo.schutztat.de DNS A-record -> 178.104.184.168 (Cloudflare API)", commit_or_pr: "reported by parallel session, not independently re-verified", opened_in_session: false}
created: "2026-07-09"
---

# KONZ-platform-015 — Transparente & stabile Infrastruktur dev/staging/prod

> Ausgelöst durch einen Live-Incident (weltenhub Redis-500er, Ursache: stale `bfagent_redis`/`bfagent_db`-Hostnamen nach Dekommissionierung der `bfagent`-App) und den Nutzerauftrag: *"do a thorough analysis, prepare a konzept for a transparent and stable infrastructure ... dev, staging und prod .. we have sth. close to chaos."* Tier-Entscheidung: **T3** — Cross-Repo (10+ Hubs), SSoT-Frage (Registry-Sprawl), neue Boundary (Decommission-Gate) — alle drei Auto-Eskalations-Trigger aus dem `/konzept`-Skill greifen unabhängig voneinander. Adversariales Fan-out (Steelman/Advocatus Diabolus/Maintainer-2028, drei unabhängige Agenten) plus Fable-5-Synthese durchgeführt.

---

## 1. Executive Summary

**Empfehlung: als MVP annehmen** — nicht als Vollkonzept, denn die adversariale Prüfung hat den zentralen Reuse-Claim teilweise falsifiziert. Kernidee: Die drei Live-Incidents dieser Woche (weltenhub-Redis-500er, stale `bfagent`-DB-Referenzen, stale DNS auf `staging-demo.schutztat.de`) sind **eine** Fehlerklasse — Runtime-Referenzen auf dekommissionierte Infrastruktur, die kein Gate sieht — und werden nicht durch einen neuen Mechanismus geschlossen, sondern durch Erweiterung der zwei nachweislich *erzwungenen* Pfade: ADR-021 §2.17 (Deploy-Gate, live verifiziert) und ADR-264 D1 (CI-verdrahtet in `adr-validate.yml`). Die größte Stärke: Extension-over-Invention ist exakt das, was ADR-264 D1 nach fünf konkurrierenden Deployment-ADRs erzwingen soll, und beide Erweiterungspunkte haben je einen datierten, verifizierten Incident hinter sich. Das größte Risiko: Der ursprüngliche Entwurf wollte auf einen Mechanismus bauen, der nur zu ~38 % adoptiert ist, dessen CI-Einstiegspunkt (`verify-staging-strategy`) **nirgends existiert**, und hätte damit einen dritten Zustand geschaffen — *deklariert-aber-unerzwungen* — der schlimmer ist als Unsichtbarkeit. Deshalb gilt hier durchgängig **wire-before-extend**: Keine Erweiterung zählt als existent, bevor sie fail-closed in CI/Deploy-Pfad verdrahtet und einmal real ausgelöst wurde. Das MVC: (1) Dead-Reference-Gate im Deploy-Pfad von **einem** Pilot-Hub (weltenhub), gespeist aus einer `decommissioned:`-Liste in `registry/repos.yaml`; (2) `owner`+`expires_at`-Pflichtfelder für Host-Override-Ausnahmen nach dem Vorbild des D1-Waivers ("ohne Ablaufdatum → blockiert"); (3) wire-or-delete-Entscheid für die acht verwaisten `staging_*.sh`-Checks binnen 30 Tagen. Die größte Unsicherheit: ob die Registry-Konsolidierung (5 YAML-Dateien, zwei davon mit konkurrierendem SSoT-Anspruch) sauber gelingt, bevor die neuen Felder die Verflechtung vergrößern — deshalb ist der Präzedenz-Entscheid Teil desselben Amendments, nicht aufgeschoben. Zwei Fragen entscheidet dieses Dokument ausdrücklich **nicht**: den DNS-A-Record von `staging-demo.schutztat.de` und die Zukunft der "platform"-Governance-DB — beides sind benannte Human-Decision-Items (REC-5).

## 2. Scope & Evidence Base

**Inputs:** drei blinde adversariale Analysen (Steelman, Advocatus Diabolus, Maintainer-2028), Konfliktmatrix K1–K4, Incident-Evidenz aus zwei Sessions, plus eigene Verifikation in dieser Synthese-Session.

**In dieser Session direkt verifiziert (Repo `platform`, lokal auf `main`, clean):**

- `grep -rn "verify-staging-strategy" Makefile .github/workflows/` → **0 Treffer**. Das Makefile-Target, das ADR-210 als CI-Einstiegspunkt spezifiziert, existiert nicht; keines der Check-Skripte wird von irgendeinem Workflow referenziert.
- `scripts/checks/staging_*.sh` → **8 Skripte existieren** (devdesktop_clean, dns_schema, generated_drift, host_locality, naming, oidc_redirects, port_range, tunnel_ingress) — alle unverdrahtet.
- `registry/` enthält **5 YAML-Dateien + 1 Skript**: `canonical.yaml`, `github_repos.yaml`, `iil-migration.yaml`, `pypi-fleet.yaml`, `repos.yaml`, `sync_registry.py`.
- `registry/repos.yaml`: 7 `domains`, ~19 Systeme; `grep -c "owner"` → **0** — kein Owner-Feld im Schema.
- `registry/github_repos.yaml` Header: selbst-deklariert als "Single Source of Truth für Cascade, port_audit, onboard-repo, deploy-check", "Generiert aus: GitHub API (86 Repos, **2026-04-03**)" — dreimonatiger Stand, konkurrierender SSoT-Anspruch.
- `tools/check_deploy_adr_supersession.py` (ADR-264 D1) **ist** verdrahtet: `.github/workflows/adr-validate.yml:48` — der einzige CI-gebundene Check der ganzen Mechanik.
- `docs/adr/ADR-264-...md` gelesen: D1–D4 im Wortlaut; **Supersession-Matrix (Accept 2026-07-03): ADR-210 ist "ersetzt" (`superseded_by: ADR-264`), ADR-021 "übernommen, NICHT abgelöst" — §2.17 bleibt lebende SSoT-Klausel.** D1 enthält bereits den Präzedenzfall "Waiver ohne Ablaufdatum → blockiert". D2 (Promotion-Gate) laut Vorsession noch nicht implementiert.
- `.github/CODEOWNERS:7`: `/registry/ @achimdehnert @wirdigital` — pauschale Verzeichnis-Ownership, kein Per-Eintrag-Owner.

**Aus den Incident-Sessions übernommen (dort verifiziert, hier nicht erneut geprüft):** weltenhub-Prod-Compose byte-identisch zu git, `deploy.yml` gepinnt auf `_deploy-unified.yml@v1.0.8`; git-unsichtbares `/opt/hub-builds/weltenhub/docker-compose.override.yml` (+ `.bak-20260706`); `.env.prod` mit toten Hostnamen `bfagent_redis`/`bfagent_db` bei `docker ps -a --filter name=bfagent` → 0 Containern; DNS-A-Record `staging-demo.schutztat.de` → `178.104.184.168` (alter ADR-210-Ära-Host "staging-platform"); ~10 Prod-Hubs am Netz `bf_platform_prod`, davon nur 3 in `repos.yaml` registriert.

**Als Annahme markiert:** die Nennerzahl "~50 Org-Repos" vs. 86 laut `github_repos.yaml` (inkl. vermutlich archivierter) — der belastbare Coverage-Befund ist deshalb **3/10 Prod-Hubs registriert**, nicht die Prozentzahl. **Nicht verifizierbar in dieser Session:** aktueller Host-Zustand zum Zeitpunkt des Lesens (kein durchgehender SSH-Zugriff in der Synthese-Session), aktueller DNS-Zustand (C11, nur aus Parallel-Session übernommen, nicht selbst re-verifiziert), Konsumenten der "platform"-Governance-DB.

## 3. Infrastruktur-Fit

| Infrastruktur-Baustein | Relevant? | Wiederverwenden | Erweitern | Risiko | Kommentar |
|---|---|---|---|---|---|
| ADR-264 D1 (Supersession-Gate) | ja | ✓ (Muster + Waiver-Schema) | ✓ (Ablaufdatum-Pflicht als Vorbild für E2) | niedrig | Einziger CI-verdrahteter Check der Mechanik (`adr-validate.yml:48`); "Waiver ohne Ablaufdatum → blockiert" ist der hauseigene Präzedenzfall für Ausnahmen-mit-Verfall |
| ADR-264 D2 (Promotion-Gate) | ja | — | ✓ (Dead-Reference-Check wird Teil des Promotion-Pfads) | mittel | **Noch nicht implementiert** — Prod ist weiter `push:main`-Direktschlag; dieses Konzept darf D2 nicht voraussetzen, kann aber in dessen Pfad einrasten |
| ADR-264 D3 (Signal→Gate-Loop, datierter Exit) | ja | ✓ (Muster für Kill-Gate §13) | — | niedrig | Datiertes Exit-Kriterium wird 1:1 für dieses Konzept übernommen |
| ADR-264 D4 (Ownership ≥2 Jahre) | ja | ✓ | ✓ (Owner-Feld pro Ausnahme, nicht nur pro Gate) | mittel | D4 existiert als Text; der Registry fehlt jedes Owner-Feld — Lücke eine Ebene tiefer |
| ADR-210 Registry/Generator/Checks | ja | ✓ (Artefakte: `repos.yaml`, `render_staging.py`, 8 Skripte) | nur nach Verdrahtung | **hoch** | **ADR-210 ist seit 2026-07-03 superseded (→ ADR-264)**; die Artefakte leben, die Entscheidungsautorität nicht. Erweiterungsziel ist ADR-264, nicht ADR-210. CI-Einstieg existiert nicht (wire-or-delete, REC-1) |
| ADR-021 §2.17 (Compose-Sync-Guard) | ja | ✓ | ✓ (Override-Manifest + Dead-Reference als §2.17-Delta) | niedrig | In Supersession-Matrix ausdrücklich "übernommen, NICHT abgelöst"; fail-closed im Deploy-Pfad, diese Session live verifiziert — der einzige Baustein, der den Reuse-Claim voll trägt |
| ADR-142 (OIDC/Authentik) | peripher | ✓ (`staging_oidc_redirects.sh` existiert) | — | niedrig | Stale-DNS-Klasse trifft Redirect-URIs; kein eigener Baustein, aber Prüfgegenstand des Sweeps |
| platform-agents.md (dev-hub-Routing) | teilweise | — | — | mittel | Für ein Standalone-Tool wäre `dev-hub/apps/` korrekt geroutet — aber genau dort gibt es keine Forcing-Function; die Gate-Logik gehört in den Deploy-Pfad (shared-ci), nur der manuelle Sweep-Modus bleibt Tool |
| Registry-Sprawl (5 YAML + `sync_registry.py`) | ja | teilweise | ✓ (Präzedenz-Entscheid nötig) | **hoch** | Zwei Dateien mit SSoT-Anspruch (`repos.yaml` via ADR-210-Erbe, `github_repos.yaml` per Header); jede neue Schreiboperation vor dem Präzedenz-Entscheid vergrößert die Verflechtung (AD-6) |

## 4. Steelman (kondensiert)

Der Kernzug — **erweitern statt erfinden** — ist durch die dokumentierte Historie des Repos gedeckt: ADR-264 D1 existiert, *weil* fünf konkurrierende "unified deployment"-ADRs (021/075/120/156/210) fragmentierten statt konvergierten. Ein Konzept, das sich weigert, Anlauf Nr. 6 zu starten, ist der Lehrbuchfall, für den D1 gebaut wurde. Beide Erweiterungspunkte zielen auf reale, lasttragende Infrastruktur: §2.17 wurde in der Incident-Session live re-verifiziert (weltenhub korrekt auf `_deploy-unified.yml@v1.0.8` gepinnt, Prod-Compose byte-identisch), und die ADR-210-Artefakte existieren konkret auf Platte. Die Lückendiagnose ist präzise, nicht handwedelnd: Lücke (a) — §2.17 sieht nur `docker-compose.prod.yml`, keine Out-of-band-Host-Dateien — ist exakt, was das git-unsichtbare `docker-compose.override.yml` durchließ; Lücke (b) — kein Decommission-Sweep — ist exakt, was `.env.prod` auf toten `bfagent_*`-Hostnamen sitzen ließ. Der stale-DNS-Fund auf `staging-demo.schutztat.de` ist eine **zweite, unabhängig entdeckte Instanz derselben Klasse** — zwei Incidents für einen Mechanismus ist ein gutes Verhältnis für ein T3-Konzept. Korrekt gehedgt ist der Entwurf dort, wo Evidenz fehlt: kein Rename von `bf_platform_prod` (30-Container-Blast-Radius für Kosmetik), keine stille Entscheidung über die Governance-DB, kein Registry-Rewrite ohne Befundlage. Nichts hier schlägt neue Abstraktionen oder neue ADR-Zeremonie über das Etablierte hinaus vor.

*(Synthese-Korrektur: Die Steelman-Prämisse "already working" und das ursprünglich geplante Erweiterungsziel "ADR-210" werden in §6/§10 korrigiert — die Substanz des Arguments überlebt, die Formulierung nicht.)*

## 5. Konzeptdefinition

### 5.1 Kernthese

Infrastruktur-Stabilität über dev/staging/prod entsteht hier nicht durch einen neuen Mechanismus, sondern dadurch, dass die zwei nachweislich *erzwungenen* Pfade (ADR-021 §2.17 im Deploy, ADR-264 D1 in CI) um genau die eine Fehlerklasse erweitert werden, die drei Live-Incidents verursacht hat — Runtime-Referenzen auf dekommissionierte Infrastruktur —, wobei jede Erweiterung erst dann als existent gilt, wenn sie fail-closed verdrahtet und einmal real ausgelöst wurde (**wire-before-extend**), weil unverdrahtete Checks in diesem Repo nachweislich der Median sind, nicht die Ausnahme.

### 5.2 Problem

**Beobachtung (verifiziert):** (i) weltenhub-Prod schrieb Sessions gegen den toten Hostnamen `bfagent_redis` → 500er; (ii) `.env.prod` referenzierte `bfagent_db`, obwohl kein `bfagent`-Container mehr existiert; (iii) `staging-demo.schutztat.de` zeigt per A-Record auf `178.104.184.168`, einen abgelösten ADR-210-Ära-Host, und liefert falschen Content; (iv) ein git-unsichtbares `docker-compose.override.yml` (+ manuelle `.bak`-Kopie) definierte Redis/DB am CI vorbei um; (v) die ADR-210-Prüfbatterie ist vollständig unverdrahtet, die Registry deckt 3 von 10 Prod-Hubs am gemeinsamen Netz ab, und `github_repos.yaml` erhebt einen konkurrierenden SSoT-Anspruch mit Stand April.

**Interpretation:** Alle drei Incidents sind Instanzen **einer** Klasse: Beim Dekommissionieren einer App (bfagent, staging-platform-Host) blieb niemand zuständig dafür, was noch auf sie zeigt — und kein Gate prüft es. Zusätzlich existiert eine zweite Klasse: Host-Zustand außerhalb von git (Override-Dateien, DNS), den §2.17 konstruktionsbedingt nicht sieht.

**Hypothese (markiert als solche):** Weitere Instanzen beider Klassen existieren unentdeckt in der Fleet (z. B. weitere Hubs mit `bfagent_*`-Env-Werten, weitere DNS-Records auf Alt-Hosts). Billigster Falsifikationstest: der Retro-Sweep in REC-7.

**Offene Fragen (bewusst unentschieden):** Wird die "platform"-Governance-DB noch irgendwo gebraucht? Wie wird der DNS-Record von `staging-demo.schutztat.de` aufgelöst (umbiegen vs. löschen)? → REC-5, Human-Decision.

### 5.3 Zielbild

Ein Deploy in dieser Fleet kann nicht grün werden, wenn (a) sein Prod-Compose-Zustand nicht byte-identisch aus git kommt **oder** eine nicht-registrierte/abgelaufene Host-Override-Datei existiert, (b) seine runtime-aufgelösten Referenzen (Env-Werte, Connection-Strings, Hostnamen) auf einen Eintrag der `decommissioned:`-Liste zeigen. Dekommissionierung ist ein definierter Prozess mit kontinuierlicher Nachprüfung statt eines einmaligen Ereignisses. Es gibt genau **eine** normative Registry-Datei für Deploy-/Staging-/Decommission-Topologie, und jedes Check-Skript im Repo ist entweder CI-verdrahtet oder gelöscht — kein dritter Zustand.

### 5.4 Nicht-Ziele

- **Kein Rename von `bf_platform_prod`**: kosmetischer Name, ~30 Container/10 Hubs Blast-Radius, kein Runtime-Risiko — der Name wandert stattdessen auf die Allowlist des Dead-Reference-Checks.
- **Keine unilaterale Entscheidung über die "platform"-Governance-DB** — Inventar ja, Entscheid beim Owner (REC-5b).
- **Kein neues konkurrierendes ADR** — Anlauf Nr. 6 ist genau das, was D1 verhindert; Änderungen laufen als Amendment an ADR-264 (+ §2.17-Delta an ADR-021) durch den regulären Review (E6).
- **Kein Registry-Vollrewrite in einem Schritt** — Präzedenz-Entscheid und Deprecation-Pfad ja, Big-Bang-Konsolidierung nein.
- **Kein neues Standalone-Tooling ohne Forcing-Function** — nichts landet in `dev-hub/apps/`, das nur "bei Gelegenheit" aufgerufen werden müsste.

### 5.5 Artefakte

| Artefakt | Neu/Geändert | Owner | Normativ? | Generiert? | Lebenszyklus | Risiko |
|---|---|---|---|---|---|---|
| `registry/repos.yaml` Schema-Erweiterung: `decommissioned:`-Abschnitt ({name, date, dead_hostnames[], dead_ips[]}), pro System optional `overrides:` ({path, reason, owner, expires_at}) | Geändert | Registry-CODEOWNERS (@achimdehnert @wirdigital) | ja | nein | lebt mit Fleet; Validator-gebunden | mittel (AD-6: Schreiben in umkämpfte Datei — mitigiert durch Präzedenz-Entscheid in REC-4, gleicher PR-Zug) |
| `tools/validate_registry.py` (Schema-Validator, ggf. Erweiterung `sync_registry.py`) | Neu | D4-Owner | ja (erzwingt E2-Felder) | nein | CI-blocking in platform | niedrig |
| `tools/decommission_check.py` — Gate-Modus (prüft aufgelöste Env/Compose-Werte eines Repos gegen `decommissioned:`) + Sweep-Modus (fleet-weiter Retro-Lauf) | Neu | D4-Owner | nein (implementiert E3) | nein | verdrahtet via E5-Pflicht; ohne Verdrahtung → Löschung | mittel (Friedhof-Risiko, mitigiert: Verdrahtung ist Teil derselben PR) |
| `_deploy-unified.yml`-Step (shared-ci): ruft Gate-Modus + Override-Manifest-Prüfung fail-closed vor `compose up` | Geändert | shared-ci-Owner | ja | nein | versioniert (@vX-Bump, Consumer-Verifikation vor Merge) | mittel (Memory: Reusable-WF vor Merge auf Consumer verifizieren) |
| ADR-264-Amendment (D2-Delta: Dead-Reference + Override-Manifest) + ADR-021 §2.17-Delta | Geändert | du | ja | nein | ADR-Lifecycle, /adr-review-Pflicht | niedrig |
| wire-or-delete-PR für `scripts/checks/staging_*.sh` (REC-1) | Geändert | du | — | nein | einmalig, Ergebnis dauerhaft | niedrig |
| `registry/README.md` Präzedenz-Doku + Deprecation-Header in 4 von 5 YAMLs | Neu/Geändert | Registry-CODEOWNERS | ja | nein | bis Konsolidierung abgeschlossen | niedrig |
| Dieses KONZ-Dokument | Neu | du | nein (Entscheidungsgrundlage) | nein | nach Accept/Reject archiviert | — |

### 5.7 Prozessmodell: Decommission-Lifecycle

Der generische idea→klickdummy→pilot→prod-Lifecycle ist hier nicht anwendbar (kein Produkt-Konzept); das relevante Prozessmodell ist der **Decommission-Lifecycle**, den Vorschlag (b) eigentlich beschreibt:

1. **Announce** — Eintrag der App in `registry/repos.yaml` → `decommissioned:` (Name, Datum, tote Hostnamen/IPs). Der Eintrag ist der *Auslöser* aller nachgelagerten Enforcement-Schritte, nicht bloß Doku. Präzedenzfall: der bfagent-Freeze (import-only) hätte als solcher Eintrag beginnen müssen.
2. **Sweep** — `tools/decommission_check.py --sweep` läuft fleet-weit: greift Env-Dateien, Compose-Resolutionen, DNS-Records, Connection-Strings nach den registrierten toten Referenzen ab. **Scope: nur runtime-aufgelöste Referenzen** (Env-Werte, URLs, Hostnamen, IPs) — kosmetische Treffer wie der Netzname `bf_platform_prod` stehen auf einer Allowlist mit Ablaufdatum (M28-3-Falle).
3. **Fix** — Befunde als Issues je Repo, abgearbeitet vor Schritt 5.
4. **Verify** — die *kontinuierliche* Absicherung: Ab dem Announce-Eintrag schlägt der Gate-Modus in **jedem** Fleet-Deploy fail-closed an, wenn das deployende Repo noch eine tote Referenz auflöst. Das ist die Forcing-Function, die dem ursprünglichen Entwurf fehlte: Nicht der Mensch muss sich an den Sweep erinnern — jeder künftige Deploy erinnert sich an die Liste (Auflösung K4).
5. **Archive** — GitHub-Archivierung/Host-Teardown erst nach grünem Fleet-Sweep; abgesichert durch ein Wiedervorlage-Issue mit Datum (E4). Ehrlich benannt: Diesen letzten Schritt kann kein technischer Hook erzwingen (Archivierung ist ein UI-Klick) — er ist prozessual und wird durch Schritt 4 kompensiert, der auch nach vergessenem Sweep weiter greift.

### 5.8 Enforcement-Modell

| Regel | Level | Mechanismus | Owner | Ausnahme? | Ablaufdatum nötig? |
|---|---|---|---|---|---|
| E1: Prod-Compose nur byte-identisch aus git (ADR-021 §2.17, bestehend) | hart (fail-closed) | `deploy.sh` sha-verify vor `compose up` | Hub-Owner + D4-Owner | nein | n/a |
| E2: Host-only Override-Dateien nur mit Registry-Eintrag (`path`, `reason`, `owner`, `expires_at`) | hart | Deploy-Gate liest `overrides:`-Manifest; fehlender **oder abgelaufener** Eintrag → Deploy-Abbruch | Registry-CODEOWNERS | ja — aber nur befristet | **ja, Pflichtfeld** — ohne `expires_at` verweigert der Validator den Merge (Vorbild: D1-Waiver "ohne Ablaufdatum → blockiert"). Ablauf fail-closed, nicht Erinnerungs-Mail (Auflösung M28-2) |
| E3: Keine runtime-aufgelöste Referenz auf `decommissioned:`-Einträge | hart | `tools/decommission_check.py` (Gate-Modus) als Step in `_deploy-unified.yml`, vor `compose up` | D4-Owner | Allowlist nur für kosmetische Treffer (z. B. `bf_platform_prod`) | Allowlist-Einträge mit Ablauf |
| E4: Archivierung erst nach grünem Fleet-Sweep | prozessual (SOLL) | Decommission-Checklist + Wiedervorlage-Issue mit Datum; technisch nicht erzwingbar, kompensiert durch E3 | du | — | Issue trägt Datum |
| E5: wire-or-delete — kein Check-Skript ohne CI-Verdrahtung | hart | CI-Job in platform: jedes Skript unter `scripts/checks/` muss von Workflow oder Makefile referenziert sein, sonst rot; Verdrahtungs-PR ist Teil derselben PR wie jedes neue Skript (Definition of Done) | Repo-Owner | begründeter Waiver | ja |
| E6: Entscheidungsinhalte nur per ADR-Amendment-PR (/adr-review + adr-challenger), nie code-only | prozessual + Ruleset | bestehendes platform-Ruleset (2. Owner-Review seit 2026-07-05, kein Self-Merge) | CODEOWNERS | nein | n/a |

E3 ist die Auflösung von K1/K4: Die Forcing-Function sitzt nicht in einem Skript, das jemand aufrufen muss, sondern im einzigen Pfad, den keine App überspringen kann — demselben Chokepoint, der §2.17 seit dem Crash-Loop-Incident am Leben hält.

### 5.9 Minimal Viable Concept

Ausdrücklich kleiner als 5.10 — kein Fleet-Rollout, kein Host-Scanner, keine ausgeführte Konsolidierung:

1. **Schema + Validator** (eine PR): `decommissioned:`- und `overrides:`-Felder in `registry/repos.yaml`; `tools/validate_registry.py` blocking in platform-CI; erster `decommissioned:`-Eintrag: `bfagent` (dead_hostnames: `bfagent_redis`, `bfagent_db`) und der Alt-Host `178.104.184.168`. Im selben PR: Präzedenz-Satz in `registry/README.md` ("`repos.yaml` ist normativ für Deploy-/Staging-/Decommission-Topologie") — damit AD-6 nicht greift.
2. **Pilot-Gate** (eine PR in shared-ci + Consumer-Verifikation): `tools/decommission_check.py` Gate-Modus als Step in `_deploy-unified.yml`, **nur weltenhub** konsumiert den neuen Tag; 14–30 Tage Shadow-Mode (report-only, FP-Rate messen), dann fail-closed. Nachweis "einmal real ausgelöst": ein absichtlicher Testlauf mit toter Referenz muss rot werden, bevor das Gate als existent gilt.
3. **wire-or-delete** (eine PR): Entscheid über die 8 `staging_*.sh` gemäß REC-1 — verdrahten oder löschen, kein dritter Zustand.

MVC-Erfolgskriterium: Der Gate hätte den weltenhub-Incident verhindert (Replay: `.env.prod` mit `bfagent_redis` → Deploy rot).

### 5.10 Full Concept

Zusätzlich zum MVC: (a) Fleet-Rollout des Gates über `_deploy-unified.yml`-Tag-Bump, Tier-A-Repos zuerst (ADR-270-Tiering), Vorbedingung: die 7 unregistrierten Prod-Hubs sind in `repos.yaml` erfasst; (b) Override-Manifest (E2) fleet-weit fail-closed; (c) Registry-Konsolidierung ausgeführt: `github_repos.yaml` zum generierten Inventar degradiert (SSoT-Claim aus Header entfernt, Regenerations-Check), `canonical.yaml` auf Server-Meta beschränkt, `iil-migration.yaml`/`pypi-fleet.yaml` bleiben programm-scoped mit Verfall = Programmende; (d) host-seitiger `docker compose config`-Diff-Scanner (Alternative A2) als zweite Stufe gegen *undeklarierte* Override-Dateien — schließt Diabolus' "sichtbar-nur-wenn-deklariert"-Lücke; (e) ADR-264-Amendment + ADR-021 §2.17-Delta dokumentieren all das normativ; (f) Retro-Sweep-Befunde (REC-7) abgearbeitet.

## 6. Adversariale Analyse

Die Angriffe werden hier unverdünnt konserviert; Auflösung erst in §10–13.

**Advocatus Diabolus (alle Kernfakten in dieser Synthese-Session re-verifiziert):**

- **AD-1** *[bestehende Lücke nicht geschlossen + SSoT-Risiko]*: `registry/repos.yaml` deckt 19 Systeme ab — nur 3 der 10 Prod-Hubs am `bf_platform_prod`-Netz sind registriert. Der Vorschlag verlangt Registrierung in einer Datei, in der für die Mehrheit der Fleet gar kein Eintrag existiert, ohne Vollständigkeit zur Vorbedingung zu machen.
- **AD-2** *[Governance-Lücke + Operationalisierungsrisiko]*: Kein `owner`-Feld existiert im Registry-Schema (grep: 0 Treffer); CODEOWNERS ist eine pauschale Zwei-Personen-Verzeichniszeile. "Exception mit Owner" kollabiert zu "wer auch immer den PR abgenickt hat" — unzuweisbar, unauditierbar, nie ablaufend. Direkte Wiederholung des Problems, das D4 eine Ebene höher lösen sollte.
- **AD-3** *[neuer Failure-Mode + Operationalisierungsrisiko]*: Der "registrierte Ausnahme"-Pfad hat schwächere Zähne als der Mechanismus, den er erweitert: §2.17 ist fail-closed, die Ausnahme wäre ein YAML-Eintrag mit Prosa, geprüft von Skripten, die nachweislich nirgends laufen. Das schafft einen dritten Zustand — *deklariert-aber-unerzwungen* — der schlimmer ist als unsichtbar, weil er falsche Governance-Sicherheit trägt. Unter Zeitdruck gewinnt immer der Pfad ohne Konsequenzen.
- **AD-4** *[Lücke nicht geschlossen + Operationalisierung + unklare Ownership]*: ~40 Skripte in `scripts/`+`tools/` sind in keinen CI-Trigger verdrahtet; `verify-staging-strategy` — der spezifizierte Einstiegspunkt des zu erweiternden Mechanismus — existiert nicht einmal als Makefile-Target. Ein neues Sweep-Skript in `dev-hub/apps/` tritt einem Friedhof bei, in dem "einmal geschrieben, nie verdrahtet, beim nächsten Incident wiederentdeckt" der Median ist.
- **AD-5** *[Governance-Lücke + SSoT-Risiko]*: "Erweitern statt neu" umgeht den Buchstaben von D1, aber potenziell auch die Review-Substanz: als "Extension" gelabelte Entscheidungsinhalte, die code-only landen, umgehen /adr-review + adr-challenger + CODEOWNERS-Review — und lassen den ADR-Text gegenüber der Implementierung veralten (exakt das "ADR sagt X, Realität sagt Y"-Muster, das diese Woche zweimal gefunden wurde). *Synthese-Verschärfung: Das Erweiterungsziel "ADR-210" war selbst schon falsch — ADR-210 ist seit 2026-07-03 superseded (→ SSOT-2 in §10).*
- **AD-6** *[Governance-Lücke + SSoT-Risiko]*: (c) Registry-Konsolidierung ist gleichzeitig unter-scoped (die Evidenz — Coverage-Lücke, fehlendes Owner-Feld, Naming-Mismatch — reicht bereits für einen committeten Befund) und scope-creep-gefährdet; (a)/(b) schreiben derweil *mehr* Einträge in eine der 6 umkämpften Dateien, bevor entschieden ist, welche gewinnt — die spätere Konsolidierung muss mehr entwirren.

**Maintainer-2028:**

- **M28-1**: `verify-staging-strategy` + die 8 `staging_*.sh` sind das wahrscheinlichste 2028-Waisenkind — heute schon offen bewiesen (onboarding-hub unregistriert und mit divergierenden, beide unerreichbaren Staging-Domains, unentdeckt). Ein schlafendes Check-Skript ist schlimmer als keines, weil es nach Coverage *aussieht*. Unter Incident-Druck löscht ein müder Maintainer genau diese Batterie als toten Ballast — und tauscht damit eine benannte Lücke gegen eine unsichtbare (die Schwester-Incident-Klasse Staging-Drift). Deshalb: vor Löschung Obsoleszenz beweisen, nicht vermuten.
- **M28-2**: "Documented exception with owner" ist die Lehrbuchform der vergessenen Review-Pflicht: keine Re-Attestierungs-Kadenz, kein Verfall, kein Check, dass der Owner noch existiert oder die Datei noch gebraucht wird — während §2.17 daneben fail-closed im Deploy-Pfad sitzt. Durabel nur, wenn Ausnahmen bei Ablauf fail-closed reißen, nicht nur einen Namen tragen.
- **M28-3**: Der Decommission-Sweep überlebt als Skript-ohne-Auslöser nicht: blocking *was*, getriggert *von wem*, *wann*? Archivierung passiert per UI-Klick, `compose down` oder schlicht Verrotten (wörtlich bfagent). Ohne Einhängung in einen unüberspringbaren Pfad wird er einmal (vielleicht) retroaktiv für bfagent laufen, dann nie wieder. Zusätzliche Falle: ein naiver Fleet-grep nach `bfagent` trifft den kosmetischen Netznamen `bf_platform_prod` neben den gefährlichen Runtime-Referenzen — ohne Scope auf runtime-aufgelöste Referenzen ertrinkt der 2028-Maintainer in False Positives oder lernt, das Tool zu ignorieren.

## 7. Deep-Dive

**Achse 1 — SSoT/Drift:** Der Ist-Zustand hat nicht zu wenig SSoT, sondern zu viele: `repos.yaml` (ADR-210-Erbe, 19 Systeme, normativ gemeint), `github_repos.yaml` (Header-Claim "Single Source of Truth", generiert 2026-04-03, 86 Repos — drei Monate stale), `canonical.yaml` (Server-Meta), dazu zwei Programm-Dateien. Der Incident-Mechanismus war in allen drei Fällen identisch: Eine Referenz (Env-Wert, DNS-Record, Override-Datei) lebte außerhalb jeder dieser Quellen und driftete unbemerkt. Konsequenz: Neue Felder dürfen nur in **eine** Datei (Präzedenz-Entscheid REC-4, im selben Zug wie die Schema-Erweiterung), und das Gate muss gegen *aufgelöste Laufzeitwerte* prüfen, nicht gegen Deklarationen — sonst entsteht nur die nächste driftende Kopie (das `overrides:`-Manifest kann genauso von der realen `compose -f a -f b`-Invocation abweichen wie `.env.prod` von den realen Containernamen abwich).

**Achse 3 — Governance:** Drei Befunde greifen ineinander: kein Owner-Feld (AD-2), pauschale CODEOWNERS-Zeile als De-facto-Approval-Board (nie als solches entschieden), und die Review-Umgehungs-Gefahr des "Extension"-Labels (AD-5) — verschärft dadurch, dass der Entwurf ADR-210 erweitern wollte, das bereits superseded ist. Die Auflösung nutzt hausinterne Präzedenzfälle statt neuer Erfindungen: D1s Waiver-Schema (Owner · Ablaufdatum · Grund · Wiedervorlage-Issue, "ohne Ablaufdatum → blockiert") wird 1:1 auf Override-Ausnahmen übertragen (E2); E6 zwingt die Entscheidungsinhalte durch den seit 2026-07-05 bestehenden Ruleset-Review (2. Owner, kein Self-Merge). Damit ist "Owner" nicht mehr Prosa, sondern Validator-geprüftes Pflichtfeld mit fail-closed-Verfall.

**Achse 7 — CI/CD & Betrieb:** Die Betriebsrealität dieses Repos ist asymmetrisch: Der einzige CI-verdrahtete Check der ganzen Deployment-Governance (`check_deploy_adr_supersession.py` in `adr-validate.yml:48`) funktioniert; die ~40 unverdrahteten Skripte daneben sind betrieblich inexistent. Daraus folgt die härteste Regel dieses Konzepts (E5, wire-or-delete): Verdrahtung ist Teil der Definition of Done derselben PR, nie ein Follow-up. Für das Gate selbst gilt die Memory-Lektion "Reusable-WF vor Merge auf Consumer verifizieren": Der `_deploy-unified.yml`-Step wird auf einem Consumer-PR gegen den Feature-Ref grün gezogen, bevor der Tag gebumpt wird — und "existiert" erst nach einem absichtlich roten Testlauf (run-conclusion ≠ Tool-Health). Shadow-Mode (14–30 Tage, FP-Ziel < 5 %) verhindert, dass ein übereifriges Gate die Fleet blockiert und sofort per Allowlist entkernt wird.

**Achse 8 — Migration:** Reihenfolge ist hier Risikosteuerung: (1) Präzedenz-Entscheid + Schema (sonst AD-6), (2) Pilot-Gate weltenhub (der Hub mit dem Original-Incident — Replay als Akzeptanztest), (3) Registrierung der 7 fehlenden Prod-Hubs (sonst kann E2/E3 fleet-weit gar nicht greifen, AD-1), (4) Tag-Bump Tier-gestaffelt nach ADR-270-Muster, (5) Konsolidierung per Deprecation-Header statt Big-Bang. Rollback-Pfad je Stufe: Gate per Tag-Pin rückrollbar (Consumer bleibt auf altem `@vX`), Schema-Felder additiv (Entfernen bricht nichts), Deprecation-Header rein deklarativ. Kein Schritt ist irreversibel; das einzige Irreversible im Umfeld — Archivierung/Host-Teardown — steht bewusst am Ende des Decommission-Lifecycle hinter E4.

## 8. Alternativen

**A1 — Radikal kleiner: nur die zwei Live-Incidents fixen, kein Mechanismus.** weltenhub-`.env.prod` bereinigen (erledigt/in Arbeit), DNS-Record-Entscheid herbeiführen, Override-Datei in git holen oder löschen — fertig. *Bewertung:* billigste Option, null neues Tooling-Risiko; aber drei Instanzen derselben Klasse in einer Woche (zwei davon aus einer *parallelen* Session, unabhängig entdeckt) sind kein Einzelfall-Muster mehr — A1 kauft den vierten Incident. A1 ist allerdings als **Teilmenge** in jedem Szenario Pflicht und in REC-5 enthalten.

**A2 — Technischer: host-seitiger `docker compose config`-Diff-Scanner.** Nächtlicher Lauf auf dem Host, der die *aufgelöste* Compose-Konfiguration (inkl. aller `-f`-Overrides) gegen den git-Stand difft und Abweichungen als Issue an die CODEOWNERS meldet — erkennt undeklarierte Override-Dateien, ohne dass irgendjemand irgendetwas deklariert. *Bewertung:* adressiert Diabolus' stärksten Punkt ("sichtbar-wenn-deklariert < verhindert") direkt und braucht keine Registry-Mitarbeit der Hub-Teams; aber er ist Detektion statt Prävention, läuft außerhalb CI (eigene Friedhof-Gefahr auf dem Host) und hätte den bfagent-Env-Drift *nicht* gefangen (Env-Werte ≠ Compose-Struktur). → Wird als **Stufe 2 ins Full Concept übernommen** (5.10d), ersetzt aber das Deploy-Gate nicht.

**A3 — Organisatorischer: quartalsweises Infra-Audit-Ritual, rotierender benannter Owner, kein neues Tooling.** Checkliste (DNS-Records vs. Registry, Host-Dateien vs. git, Env-Werte vs. lebende Container), vier Augen, Protokoll. *Bewertung:* sofort startbar, null Code; aber die Memory-Lage dieses Ökosystems dokumentiert präzise, wie Rituale ohne Erzwingung enden (advisory-scanner-Alarm-Müdigkeit, ~40 unverdrahtete Skripte, `verify-staging-strategy` selbst), und ein Quartalsrhythmus hätte den weltenhub-Incident bis zu 89 Tage leben lassen. Als **Übergangs-Kompensation** bis zum Fleet-Rollout sinnvoll (ein manueller Sweep-Lauf pro Quartal = REC-7-Wiederholung), als Dauerlösung dem Gate unterlegen.

## 9. Out-of-the-Box

1. **Shadow-Mode als Existenzbeweis, nicht als Feature:** Das Gate läuft 14–30 Tage report-only und muss zwei Dinge *messbar* liefern, bevor es blocken darf: FP-Rate < 5 % und mindestens einen echten (oder injizierten) Treffer. Ein Gate, das im Shadow-Mode nie etwas gefunden hat, wird nicht scharf geschaltet, sondern hinterfragt. (→ ins MVC übernommen.)
2. **Decommission-as-Deploy (Tombstone-Deploy):** Dekommissionierung wird nicht als Sonderprozess behandelt, sondern als *letzter Deploy* der App durch dieselbe Pipeline — ein Tombstone-Commit, der Container/Compose entfernt, den `decommissioned:`-Eintrag schreibt und den Fleet-Sweep als Pipeline-Step ausführt. Damit erbt der Ausstiegs-Pfad automatisch die komplette §2.17/E3-Erzwingung, statt eine eigene zu brauchen. Der bfagent-Fall wäre so nie "einfach verrottet".
3. **Kill-Switch statt Ausnahme-Registry (Umkehrung der Beweislast):** Statt zu verlangen, dass Teams Override-Dateien deklarieren, meldet ein nächtlicher Host-Job jede `docker-compose.override*`-Datei unter `/opt/hub-builds/`, die *nicht* im Manifest steht, automatisch als Issue an die CODEOWNERS — Entdeckung ist Push, nicht Pull. Kombinierbar mit E2: Nach N Tagen ohne Registrierung blockt der nächste Deploy des betroffenen Hubs.
4. **Registry-Sprawl per Verfallsdatum statt Konsolidierungsprojekt:** Statt 5 Dateien in einem Projekt zu mergen, bekommen 4 von 5 einen Deprecation-Header mit hartem Datum ("keine neuen Felder; normativ ist repos.yaml; diese Datei wird am TT.MM. read-only/generiert"); `sync_registry.py` erzeugt Übergangs-Views. Kurzfristige Brüche werden bewusst in Kauf genommen, um die Ambiguität zu töten, statt sie zu verwalten — die billigere und ehrlichere Form von (c).

## 10. Befunde

| ID | Rolle | Kategorie | Befund (1 Satz) | Evidenz | Schweregrad | Confidence | Betroffener Teil |
|---|---|---|---|---|---|---|---|
| PRO-1 | Steelman | Architektur | Extension-over-Invention ist der ADR-264-D1-konforme Zug nach fünf gescheiterten "unified"-ADRs | ADR-264 D1 + Supersession-Matrix (C1) | hoch (positiv) | hoch | Gesamtansatz |
| PRO-2 | Steelman | Evidenz | Beide Lücken (Out-of-band-Host-Dateien, fehlender Decommission-Sweep) haben je einen datierten, verifizierten Incident; der DNS-Fund ist eine unabhängige zweite Instanz derselben Klasse | weltenhub-Session (C6-C8) + Parallel-Session (C11, H) | hoch (positiv) | hoch | §5.2 |
| PRO-3 | Steelman | Scope-Disziplin | Kein `bf_platform_prod`-Rename, keine stille Governance-DB-Entscheidung, kein Registry-Rewrite — korrekt gehedgt | Entwurfstext | mittel (positiv) | hoch | §5.4 |
| AD-1 | Diabolus | SSoT/Coverage | `repos.yaml` deckt nur 3 der 10 `bf_platform_prod`-Prod-Hubs ab; Registrierungspflichten laufen für die Mehrheit ins Leere | yaml-Load: 7 Domains/19 Systeme (C4), diese Session re-verifiziert | hoch | hoch | registry/repos.yaml |
| AD-2 | Diabolus | Governance | Kein `owner`-Feld im Registry-Schema; CODEOWNERS ist pauschale Zwei-Personen-Zeile — "Exception mit Owner" ist unimplementierbar | grep 0 Treffer; CODEOWNERS:7 (C9) — re-verifiziert | hoch | hoch | Schema + CODEOWNERS |
| AD-3 | Diabolus | Failure-Mode | Der Ausnahme-Pfad schafft den Zustand *deklariert-aber-unerzwungen* — schwächer als der fail-closed-Mechanismus daneben, für genau die Incident-Artefaktklasse | §2.17 (C3) vs. unverdrahtete R-Checks | **kritisch** | hoch | E2-Design |
| AD-4 | Diabolus | Operationalisierung | ~40 unverdrahtete Skripte; `verify-staging-strategy` existiert nicht als Makefile-Target; neues Tool ohne CI-Zwang tritt dem Friedhof bei | grep Makefile+workflows: 0 — re-verifiziert | **kritisch** | hoch | Tooling-Strategie |
| AD-5 | Diabolus | Governance | "Extension"-Label kann /adr-review-Scrutiny umgehen und ADR-Text von der Implementierung wegdriften lassen | zweimal "ADR sagt X, Realität Y" diese Woche | hoch | mittel-hoch | E6 |
| AD-6 | Diabolus | SSoT | (a)/(b) schreiben in eine umkämpfte Datei, bevor (c) entschieden hat, welche gewinnt — Konsolidierung wird teurer | 5 YAML + konkurrierende SSoT-Claims (C4, C5) | hoch | hoch | Reihenfolge |
| M28-1 | Maintainer-2028 | Orphan-Risiko | Die 8 `staging_*.sh` sind das wahrscheinlichste 2028-Waisenkind und werden unter Druck gelöscht — Obsoleszenz vorher beweisen, nicht vermuten | onboarding-hub-Divergenz unentdeckt trotz existierender Checks | hoch | hoch | scripts/checks/ |
| M28-2 | Maintainer-2028 | Governance-Verfall | Ausnahmen ohne Re-Attestierung/Verfall werden nie zurückgebaut; Owner-Name allein hat keine Zähne | D4-Kontrast; ADR-185-Realbeleg in ADR-264 | hoch | hoch | E2 |
| M28-3 | Maintainer-2028 | Forcing-Function | Der Sweep ohne Einhängung in einen unüberspringbaren Pfad läuft genau einmal; naiver grep ertränkt Maintainer in `bf_platform_prod`-False-Positives | bfagent verrottete wörtlich; Netzname-Kollision | **kritisch** | hoch | E3/E4-Design |
| SSOT-1 | Synthese | SSoT | `github_repos.yaml` erhebt per Header eigenen SSoT-Anspruch, Stand 2026-04-03 (86 Repos) — zweite normative Quelle neben `repos.yaml` | Header gelesen (C5), diese Session | mittel | hoch | registry/ |
| SSOT-2 | Synthese | SSoT/Governance | Der Entwurf wollte ADR-210 erweitern — das seit Accept 2026-07-03 von ADR-264 superseded ist; Amendment-Ziel muss ADR-264 (+ ADR-021 §2.17-Delta) sein | ADR-264 Supersession-Matrix (C1), diese Session gelesen | hoch | hoch | Amendment-Routing |
| GOV-1 | Synthese | Governance | Die `/registry/`-CODEOWNERS-Zeile wird als Nebeneffekt zum plattformweiten Staging-Governance-Board, ohne je als solches entschieden worden zu sein | CODEOWNERS:7 (C9) | mittel | hoch | CODEOWNERS |
| OPS-1 | Synthese | Betrieb | ADR-264 D2 (Promotion-Gate) ist nicht implementiert — Prod bleibt `push:main`-Direktschlag; dieses Konzept darf D2 nicht als vorhandenes Fundament behandeln | Vorsession-Verifikation + ADR-264-Text (C1) | mittel | mittel-hoch | Abhängigkeiten |

## 11. Top-5-Risiken

**R1 — Der Ausnahme-Pfad wird zum Schlupfloch (*deklariert-aber-unerzwungen*, AD-3/M28-2).**
*Warum wichtig:* Er betrifft exakt die Artefaktklasse (Host-Override), die den Live-Incident verursachte. *Schadensszenario:* Ein Override wird mit "temporär"-Prosa registriert, nie entfernt, driftet — nächster 500er, diesmal mit dem Feigenblatt "war doch registriert". *Wahrscheinlichkeit:* hoch (unter Zeitdruck gewinnt immer der Pfad ohne Konsequenzen). *Impact:* hoch. *Kleinster wirksamer Fix:* `expires_at` als Validator-Pflichtfeld, Ablauf reißt den Deploy fail-closed (E2) — kein neues Konstrukt, D1-Waiver-Kopie. *Stärkster Gegenbeleg:* Der D1-Waiver mit identischem Design ist seit Accept in Kraft, ohne dass Waiver-Akkumulation gemeldet wurde. *Restunsicherheit:* ob Zwei-Personen-CODEOWNERS-Review Registrierungen in großen Sammel-PRs wirklich prüft.

**R2 — Das neue Tooling tritt dem Skript-Friedhof bei (AD-4/M28-3).**
*Warum wichtig:* ~40 unverdrahtete Skripte sind der empirische Median dieses Repos; ein schlafender Check ist schlimmer als keiner. *Schadensszenario:* `decommission_check.py` wird gemergt, die shared-ci-Verdrahtung "folgt später", folgt nie; 2028 findet ihn niemand. *Wahrscheinlichkeit:* hoch ohne Gegenmaßnahme, niedrig mit. *Impact:* hoch (Konzept wirkungslos). *Kleinster wirksamer Fix:* Verdrahtungs-Step und Skript in **derselben** PR (E5-DoD) + Existenzbeweis per absichtlich rotem Testlauf vor Scharfschaltung. *Stärkster Gegenbeleg:* `check_deploy_adr_supersession.py` beweist, dass verdrahtete Checks hier überleben. *Restunsicherheit:* shared-ci-Tag-Konsum ist fleet-seitig träge (Memory: Tag ≠ main).

**R3 — Registry-Verflechtung wächst schneller als die Konsolidierung (AD-6/AD-1/SSOT-1).**
*Warum wichtig:* Neue Felder in `repos.yaml` bei gleichzeitig konkurrierendem `github_repos.yaml`-SSoT-Claim vergrößern genau die Ambiguität, die die Incidents begünstigte. *Schadensszenario:* Ein Tool liest `github_repos.yaml`, das Gate liest `repos.yaml`, beide divergieren — Drift mit Governance-Anstrich. *Wahrscheinlichkeit:* mittel. *Impact:* mittel-hoch. *Kleinster wirksamer Fix:* Präzedenz-Satz + Deprecation-Header im **selben PR** wie die Schema-Erweiterung (MVC-Schritt 1), nicht als Folgeprojekt. *Stärkster Gegenbeleg:* Die neuen Felder (`decommissioned:`, `overrides:`) existieren in keiner der anderen Dateien — kein unmittelbarer Feld-Konflikt. *Restunsicherheit:* welche Konsumenten `github_repos.yaml` heute tatsächlich lesen (Header nennt vier; nicht verifiziert).

**R4 — False-Positive-Ermüdung entkernt das Gate (M28-3b).**
*Warum wichtig:* Ein Gate, das `bf_platform_prod`-Kosmetik als Alarm meldet, trainiert Ignorieren — das Advisory-Scanner-Muster aus der Memory. *Schadensszenario:* Nach drei Fehlalarmen wird der Step auf `continue-on-error` gesetzt und ist damit betrieblich tot. *Wahrscheinlichkeit:* mittel. *Impact:* hoch. *Kleinster wirksamer Fix:* Scope hart auf runtime-aufgelöste Referenzen (Env-Werte, URLs, Hostnamen, IPs), Allowlist mit Ablauf für Kosmetik, Shadow-Mode-KPI FP < 5 % als Scharfschalt-Bedingung. *Stärkster Gegenbeleg:* Die Trefferliste ist eng definierbar (exakte tote Hostnamen/IPs aus der Registry, keine Substring-Heuristik). *Restunsicherheit:* Env-Indirektionen (Secrets-Manager, Templating) könnten tote Werte vor dem Check verstecken.

**R5 — "Extension"-Label umgeht Review, ADR-Text driftet (AD-5/SSOT-2).**
*Warum wichtig:* Das Muster "ADR sagt X, Realität Y" wurde diese Woche zweimal gefunden; der Entwurf selbst zielte bereits auf ein superseded ADR. *Schadensszenario:* Gate + Schema landen code-only; 2027 liest jemand ADR-264, findet nichts über Dead-Reference-Gates und baut Anlauf Nr. 7. *Wahrscheinlichkeit:* mittel. *Impact:* mittel-hoch. *Kleinster wirksamer Fix:* E6 — Amendment-PR an ADR-264 (+ §2.17-Delta) durch /adr-review + adr-challenger, abgesichert durch das bestehende Ruleset (2. Owner-Review, kein Self-Merge). *Stärkster Gegenbeleg:* Das Ruleset erzwingt den Zweit-Review seit 2026-07-05 ohnehin für jeden platform-PR. *Restunsicherheit:* Ruleset prüft *dass* reviewt wird, nicht *ob* der ADR-Text mitgezogen wurde — bleibt Disziplinfrage.

## 12. Empfehlungen

**REC-1 — wire-or-delete für `verify-staging-strategy` (30 Tage, Owner: du).** Ein PR, der den dritten Zustand beendet: Entweder (a) neuer blocking CI-Job `staging-registry-checks` in `.github/workflows/` (Trigger: `paths: [registry/**, scripts/checks/**]`), der mindestens `staging_generated_drift.sh`, `staging_naming.sh`, `staging_dns_schema.sh` ausführt — die übrigen 5 Skripte je einzeln verdrahten oder löschen; oder (b) alle 8 Skripte + Referenzen löschen. **Vor jeder Löschung** (M28-1, "confirm before delete"): jedes Skript einmal manuell laufen lassen, Output im PR dokumentieren — ein Skript, das heute echte Befunde liefert (onboarding-hub!), wird verdrahtet, nicht gelöscht.

**REC-2 — Owner+Expiry ins Registry-Schema (mit MVC, Owner: du).** `registry/repos.yaml` erhält `decommissioned:` ({name, date, dead_hostnames[], dead_ips[]}) und pro System `overrides:` ({path, reason, owner, expires_at}); `tools/validate_registry.py` läuft blocking in platform-CI und lehnt Einträge ohne `owner` **oder** ohne `expires_at` ab (D1-Waiver-Vorbild). Erste Einträge: bfagent (`bfagent_redis`, `bfagent_db`) und `178.104.184.168`.

**REC-3 — Forcing-Function für den Decommission-Sweep (60 Tage, Owner: du + shared-ci).** `tools/decommission_check.py` Gate-Modus als fail-closed Step in `_deploy-unified.yml` **vor** `compose up`; Pilot weltenhub; Consumer-PR gegen den Feature-Ref grün ziehen, bevor der Tag gebumpt wird; 14–30 Tage Shadow-Mode mit FP-KPI < 5 %; Scharfschaltung erst nach einem absichtlich roten Testlauf (Replay des `.env.prod`-Incidents). Kein Standalone-Tool in `dev-hub/apps/` — der Sweep-Modus ist ein Aufruf-Flag desselben Skripts.

**REC-4 — Registry-Konsolidierung von "aufgeschoben" auf "committed" (60 Tage, Owner: du).** Entscheid **jetzt**, im selben PR wie REC-2: `repos.yaml` ist normativ für Deploy-/Staging-/Decommission-Topologie; `github_repos.yaml` wird zum generierten Inventar degradiert (SSoT-Claim aus dem Header entfernen, Regenerationsdatum-Check ergänzen); `canonical.yaml` auf Server-Meta beschränkt; `iil-migration.yaml`/`pypi-fleet.yaml` bleiben programm-scoped mit Verfall = Programmende. Deprecation-Header nach Muster §9.4. Zusätzlich, als Vorbedingung für Fleet-E2/E3: die **7 unregistrierten Prod-Hubs** (u. a. coach-hub, apo-hub, onboarding-hub, billing-hub, tax-hub, dms-hub, iil_dochub) in `repos.yaml` erfassen (AD-1).

**REC-5 — Die zwei offenen Live-Fragen als explizite Human-Decision-Items (Owner: du; dieses Dokument entscheidet sie NICHT).** (a) `staging-demo.schutztat.de`: A-Record `178.104.184.168` — Optionen: auf aktuellen Staging-Host umbiegen vs. Record löschen; als Issue mit Entscheidungsdatum anlegen. (b) "platform"-Governance-DB: erst Konsumenten-Inventar (Fleet-grep nach `PLATFORM_DB*`-Env-Referenzen — kann der Sweep-Modus miterledigen), dann Entscheid keep/migrate/drop; ebenfalls Issue mit Datum. Beides sind Gate-Themen (Prod/irreversibel) — keine autonome Ausführung.

**REC-6 — ADR-Amendment statt code-only (mit MVC, Owner: du).** Ein Amendment-PR an **ADR-264** (D2-Delta: Dead-Reference-Gate + Override-Manifest) mit §2.17-Delta an **ADR-021** — nicht an ADR-210, das superseded ist (SSOT-2); Dokument-Stellen, die ADR-210-Mechanik referenzieren, auf ADR-264 repointen. Durch /adr-review + adr-challenger + Ruleset-Zweit-Review. Memory-Lektion beachten: "accepted ≠ umgesetzt" — das Amendment merged erst mit oder nach den Umsetzungs-PRs.

**REC-7 — bfagent-Retro-Sweep als Validierungslauf (30 Tage, Owner: du/CI).** Erster manueller Lauf von `decommission_check.py --sweep` über Fleet + Host gegen die bfagent-Einträge: liefert (a) reale Befunde als Issues, (b) den Realdaten-Test des Tools inkl. FP-Messung vor der Gate-Scharfschaltung, (c) das Konsumenten-Inventar für REC-5b als Beifang.

## 13. Entscheidung + Kill-Gate + 30/60/90

**Entscheidung: als MVP annehmen.** Nicht "annehmen" (das Vollkonzept setzt einen Mechanismus voraus, der zu ~38 % adoptiert, unverdrahtet und teilweise auf ein superseded ADR gemünzt war — AD-1/AD-4/SSOT-2), nicht "pilotieren" (der Pilot ist bereits als MVC-Schritt 2 im Zuschnitt enthalten, und die Fehlerklasse hat drei Live-Incidents in einer Woche produziert — Abwarten hat messbare Kosten), nicht "überarbeiten" (die adversarialen Befunde sind in E2/E3/E5/E6 bereits eingearbeitet, nicht offen). MVC-Zuschnitt gemäß §5.9; Fleet-Ausbau nur über das Expansions-Gate unten.

**Kill-Gate (messbar, Stichtag 2026-09-07 = T+60):** Das Konzept gilt als gescheitert und wird zurückgebaut statt erweitert, wenn zum Stichtag **eine** der folgenden Bedingungen zutrifft: (a) der Dead-Reference-Gate läuft nicht fail-closed im weltenhub-Deploy-Pfad mit mindestens **einem dokumentierten roten Testlauf in CI** (lokaler Lauf zählt nicht — Gate `claim-before-cheapest-check`); (b) die 8 `staging_*.sh` sind weder verdrahtet noch gelöscht (dritter Zustand besteht fort); (c) die Shadow-Mode-FP-Rate liegt ≥ 5 % ohne beschlossenen Scope-Fix. Rückbau heißt: Schema-Felder deprecaten, Gate-Step entfernen, Alternative A3 (Quartals-Audit) als Fallback aktivieren, Befund als 🌀-Memory sichern. **Expansions-Gate** (zusätzlich, für 5.10): Fleet-Rollout nur, wenn Pilot 30 Tage grün UND die 7 fehlenden Prod-Hubs registriert sind.

**30 Tage (bis 2026-08-08):** REC-1 ausgeführt (wire-or-delete-PR gemergt); REC-2 Schema + Validator gemergt inkl. Präzedenz-Satz + Deprecation-Header (REC-4-Teil 1); REC-3 Gate im Shadow-Mode auf weltenhub; REC-7 Retro-Sweep gelaufen, Befunde als Issues; REC-5-Issues (DNS, Governance-DB) mit Entscheidungsdatum angelegt; REC-6 Amendment-PR offen.

**60 Tage (bis 2026-09-07):** Kill-Gate-Review; Gate fail-closed auf weltenhub inkl. rotem Testlauf; REC-4 abgeschlossen (7 Hubs registriert, `github_repos.yaml`-Header bereinigt); REC-5-Entscheide gefallen oder eskaliert; Amendment gemergt.

**90 Tage (bis 2026-10-07):** Bei bestandenem Expansions-Gate: `_deploy-unified.yml`-Tag-Bump fleet-weit, Tier-A zuerst (ADR-270-Staffelung); Entscheid über Stufe 2 (host-seitiger Compose-Diff-Scanner, A2/5.10d) auf Basis der Shadow-/Pilot-Daten; Konzept-Retro mit Scorecard, Status-Flip dieses Dokuments auf umgesetzt/teilumgesetzt.

## 14. Nachtrag 2026-07-10 — Umgewichtung nach Fleet-Realabgleich (Entscheid Achim)

**Anlass:** Ein manueller Vollabgleich Registry↔Live (Session 2026-07-10, Fable-5-Review dieses Dokuments) lieferte binnen Stunden **6+ reale Befunde**, von denen der in §5.9 geplante Dead-Reference-Gate nur ~3–4 von 9 bekannten Fällen gefangen hätte: eine komplett unregistrierte laufende App (apo-hub), eine deklarierte prod_url ohne DNS-Eintrag (recruiting-hub), zwei weitere falsche prod_urls (mcp-hub, odoo-hub — vom neuen Sweep-Tool selbst gefunden), ein committeter-aber-nie-deployter Fix (tax-hub Port), zwei Port-Doppelvergaben (8111 decks/frist, staging-8099 risk/tax). Evidenz: PR #1036 (9 Hubs + apo-hub nachregistriert), Issue #1033 (Port-Uniqueness), PR #1032 (decks-hub 8112).

**Diagnose-Korrektur:** Die Fehlerklasse aus §5.2 („Runtime-Referenzen auf dekommissionierte Infra") ist eine **Teilmenge** der realen Krankheit: *Es fehlt ein kontinuierlicher Abgleich-Kreislauf zwischen deklariertem Zustand (Registry/git) und realem Zustand (Host/DNS/Container)*. Tote Referenzen sind eine Drift-Richtung; heute belegt sind vier weitere (ungemeldete Live-Systeme, unerreichbare Deklarationen, nie-applizierte Fixes, Doppel-Deklarationen).

**Revidierte Maßnahmen-Reihenfolge (ersetzt die Gewichtung in §5.9/§13, Inhalte bleiben gültig):**

1. **NEU Hauptmaßnahme — Reconcile-Sweep (UMGESETZT 2026-07-10):** `tools/reconcile_registry_live.py` + `.github/workflows/registry-live-reconcile.yml` (täglich, self-hosted Prod-Runner, read-only). Prüft C1 Port-Mismatch · C2 Container fehlt · C3 DNS-Auflösung · C4 unregistrierte Live-Ports · C5 Doppel-Deklaration. Baseline `infra/reconcile-baseline.yaml` nach E2-Waiver-Muster (owner+expires_at Pflicht, fail-closed bei Ablauf — D1-Vorbild, hier erstmals real dogfooded). Erstlauf-Evidenz: 7 Funde roh → 2 sofort gefixt (mcp-hub/odoo-hub prod_url) → **Kennzahl 6 baselined / 0 neu, Exit 0**. Die Drift-Kennzahl ist ab jetzt Kill-Gate-KPI (Frontmatter revidiert): **≤3 gesamt mit 0 abgelaufenen Stundungen bis T+60**.
2. **Tombstone-Deploy (aus §9.2 ins Kernpaket gehoben):** Dekommissionierung = letzter Deploy durch dieselbe Pipeline (schreibt `decommissioned:`-Eintrag, führt Sweep aus). Verhindert die Entstehung der §5.2-Klasse an der Quelle statt sie beim nächsten fremden Deploy zu erkennen — Prävention vor Detektion (ADR-209-Prinzip). Design-Issue: [#1045](https://github.com/achimdehnert/platform/issues/1045).
3. **Dead-Reference-Gate (§5.9 Schritt 2) wird ZWEITE Welle** — unverändert sinnvoll, aber nachgelagert. Fehlalarm-Kriterium repariert: „FP-Rate <5 % in 14–30 Tagen" ist auf einem Einzel-Pilot statistisch nicht auswertbar (3–5 Deploys ⇒ 1 FP = 20–33 %) → ersetzt durch **absolute Zählung: 0 FP in ≥10 Läufen** (Frontmatter-Kriterium d).
4. **Selbstanwendungs-Fix:** Dieses Dokument war seit Entscheid im eigenen verbotenen „dritten Zustand" (angenommen-aber-Status-idea, 0/7 RECs begonnen, REC-5-Issues nie angelegt). Behoben: `pipeline_status: pilot`, REC-5-Issues mit Datum angelegt ([#1043](https://github.com/achimdehnert/platform/issues/1043), [#1044](https://github.com/achimdehnert/platform/issues/1044)), Sweep verdrahtet-in-derselben-PR (E5-DoD eingehalten).

**Korrektur eines Gegenbelegs:** §11 R1 nennt als stärksten Gegenbeleg „D1-Waiver seit Accept in Kraft ohne gemeldete Akkumulation" — der Mechanismus war zum Schreibzeitpunkt ~1 Woche alt; Abwesenheit von Daten ist kein Haltbarkeitsbeleg. Der Punkt bleibt als Risiko voll gewichtet; die Baseline dieses Nachtrags liefert ab jetzt echte Verfalls-Empirie (6 Einträge, Ablauf 07-24/08-08).

**Nicht geändert:** Pilot-Wahl weltenhub (§5.9) — bei Erst-Review kritisiert, bei Tiefen-Review als richtig erkannt (die dort verbliebenen toten `bfagent_*`-Referenzen sind exakt das Replay-Testmaterial für MVC-Erfolgskriterium §5.9). Alle §12-RECs bleiben gültig, nur die Reihenfolge/Gewichtung ändert sich wie oben.
