---
concept_id: KONZ-platform-024
title: "authentik-OIDC Staging-Rollout (5 Hubs) — eingemottet mit Invalidatoren-Register (erste Forward-Anwendung KONZ-023)"
pipeline_status: idea
tier: T1
owner: "Achim Dehnert"
spec_refs: []   # Ausführungsprogramm zu platform:ADR-142 Phase 2; kein ADR-211-Spec-Bezug
adr_threshold: "kein ADR — reine Ausführung einer accepted-Entscheidung (ADR-142); dieses KONZ ist Lifecycle-Artefakt für die Pause, keine neue Architektur-Entscheidung"
review_by: "2026-10-31"
kill_criteria: "Kill-Gate 2026-10-31: Ist bis dahin keine Wiederaufnahme erfolgt UND feuert kein Invalidator, wird beim Review entschieden: weiter eingemottet (mit neuem review_by) oder archivieren (Staging-OIDC für die 5 Hubs dann bewusst nicht gebaut, Begründung nachtragen)."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: E1, source_path: "CC-Memory platform: project_authentik_oidc_rollout_execution_ready.md (Vollrecherche 2026-07-09 inkl. 2 Korrektur-Nachträgen)", commit_or_pr: "Memory, degradiert zum Sperr-Verweis auf dieses KONZ", opened_in_session: true}
  - {claim_id: E2, source_path: "Live-Baseline 2026-07-17: 5 Staging-well-known 404 (137-hub-staging, ausschreibungs-hub-staging, pptx-hub-staging, trading-hub-staging, writing-hub-staging); coach-hub-staging + 4 Prod-Slugs 200", commit_or_pr: "curl-Lauf in Session 2026-07-17", opened_in_session: true}
  - {claim_id: E3, source_path: "Outline-Runbook /doc/authentik-oidc-rollout-kunden-hubs-status-amp-ausfuhrungsplan-stand-2026-07-09-UaiWftIlMI", commit_or_pr: "Outline (org-weit auffindbar)", opened_in_session: false}
created: "2026-07-17"
lebenszyklus: eingemottet
eingefroren_am: "2026-07-17"
wiederaufnahme_trigger: "bevor am authentik-OIDC-Rollout (ADR-142 Phase 2) weitergearbeitet wird — typisch: Session mit deployment-mcp/SSH auf hetzner-prod und User sagt 'authentik Rollout' / 'OIDC Rollout'"
coverage_claim: non_exhaustive
---

# KONZ-platform-024 — authentik-OIDC Staging-Rollout: eingemottet

> ⏸ **EINGEMOTTET seit 2026-07-17.** Vor Wiederaufnahme ZUERST die Invalidatoren
> unten prüfen (Reihenfolge: `strongest` zuerst), dann RAT-01 ausführen, erst danach
> die starre Zone als Arbeitsgrundlage lesen. `unknown` ist nie `pass`; positivstes
> Ergebnis heißt `no_known_break_found`. Erste Forward-Anwendung der
> Feld-Konvention aus KONZ-platform-023.

## Wiederaufnahmeversprechen

Nach dem Ausmotten kann ich die **5 fehlenden Staging-Applications** (137-hub,
ausschreibungs-hub, pptx-hub, trading-hub, writing-hub) in authentik anlegen
(Plan in der starren Zone), ohne die Recherche (Redirect-URI-Konvention,
client_id-Fixierung per Code-Default, Live-Status aller 11 Hubs, Middleware-Lage)
neu aufzubauen.

## Invalidatoren (veraltet_wenn)

```yaml
- id: vw-slug-codedefault
  strongest: true
  locus: repo
  annahme: "In allen 5 Hub-Repos ist der Code-Default config('OIDC_APP_SLUG', default='<hub-name>') unverändert — der Prod-/Staging-client_id ist dadurch fixiert (Staging = <hub-name>-staging)."
  veraltet_wenn: "git grep 'OIDC_APP_SLUG' auf origin/main eines der 5 Repos liefert keinen Treffer mit default='<hub-name>' an der Settings-Fundstelle aus der Baseline-Tabelle."
  pruefung:
    modus: maschine
    kommando: "je Repo: git fetch origin && git grep -n \"OIDC_APP_SLUG\" origin/main -- '*settings*'"
    rot_wenn: "kein Treffer ODER default != Hub-Name"
  baseline: "Fundstellen-Tabelle Stand 2026-07-09 (starre Zone); z.B. 137-hub src/config/settings/base.py, trading-hub src/trading_hub/django/settings.py"
  impact: stop_all
  bei_rot: "Neuen Default lesen und client_id daran ausrichten — NICHT die Baseline-Slugs anlegen (falsche client_id fällt erst beim Hub-Login auf, nicht beim Anlegen)."

- id: vw-staging-fehlliste
  locus: extern
  annahme: "Genau diese 5 Staging-Slugs fehlen in authentik: 137-hub-staging, ausschreibungs-hub-staging, pptx-hub-staging, trading-hub-staging, writing-hub-staging."
  veraltet_wenn: "curl auf https://id.iil.pet/application/o/<slug>/.well-known/openid-configuration liefert für mindestens einen der 5 Slugs HTTP 200."
  pruefung:
    modus: maschine
    kommando: "for s in 137-hub-staging ausschreibungs-hub-staging pptx-hub-staging trading-hub-staging writing-hub-staging; do curl -s -o /dev/null -w \"$s %{http_code}\\n\" https://id.iil.pet/application/o/$s/.well-known/openid-configuration; done"
    rot_wenn: "mindestens eine Zeile mit 200"
  baseline: "5x 404 verifiziert 2026-07-17 (E2)"
  impact: reopen_scope
  bei_rot: "Existenz-Check in ak shell neu fahren und Fehlliste neu schneiden — Arbeit kann teilerledigt sein (Muster travel-beat 2026-07-09: 'fehlend' war in Wahrheit längst live)."

- id: vw-prod-bestand
  locus: extern
  annahme: "Alle 9 Prod-Applications liefern weiterhin HTTP 200 auf well-known — es ist KEIN Prod-Write nötig (Rollout ist prod-seitig komplett)."
  veraltet_wenn: "curl well-known liefert für einen der 9 Prod-Slugs (137-hub, ausschreibungs-hub, coach-hub, pptx-hub, risk-hub, trading-hub, wedding-hub, weltenhub, writing-hub) nicht 200."
  pruefung:
    modus: maschine
    kommando: "analog vw-staging-fehlliste mit den 9 Prod-Slugs"
    rot_wenn: "mindestens eine Zeile ohne 200"
  baseline: "9x 200 verifiziert 2026-07-09; Stichprobe 4x 200 am 2026-07-17 (E2)"
  impact: reopen_scope
  bei_rot: "Prod-Teil zurück in den Scope; VOR jedem Prod-Write gilt das Sicherheits-Gate (starre Zone): explizite User-Freigabe."

- id: vw-redirect-konvention
  locus: repo
  annahme: "Alle 5 Hubs registrieren path('oidc/', include('mozilla_django_oidc.urls')) — Redirect-URI ist damit exakt https://<staging-domain>/oidc/callback/ (matching_mode STRICT)."
  veraltet_wenn: "git grep 'mozilla_django_oidc.urls' auf origin/main eines der 5 Repos liefert keinen Treffer in einer urls.py."
  pruefung:
    modus: maschine
    kommando: "je Repo: git grep -n 'mozilla_django_oidc.urls' origin/main -- '*urls*.py'"
    rot_wenn: "kein Treffer"
  baseline: "grep-Lauf über alle urls.py, 2026-07-09 (E1)"
  impact: stop_all
  bei_rot: "Tatsächliche Callback-Route im Hub lesen und RedirectURI daran ausrichten; NICHT die generische /auth/callback aus dem Pattern-Guide nehmen (bekannt falscher Default)."

- id: vw-ak-zugang
  locus: extern
  annahme: "Der authentik-Server läuft als Container iil_authentik_server auf hetzner-prod und ak shell (docker exec -it iil_authentik_server ak shell) ist der Write-Pfad für Provider/Application."
  veraltet_wenn: "docker ps --filter name=iil_authentik_server auf hetzner-prod listet keinen laufenden Container dieses Namens."
  pruefung:
    modus: maschine
    kommando: "ssh hetzner-prod 'docker ps --filter name=iil_authentik_server --format \"{{.Names}} {{.Status}}\"'"
    rot_wenn: "leere Ausgabe"
  baseline: "Container-Name aus Plan-Schritt 0, Stand 2026-07-09"
  impact: stop_all
  bei_rot: "authentik-Deploy-Pfad neu ermitteln (compose-Datei auf Host / IaC) — Plan-Schritte 0+3 an neuen Write-Pfad anpassen."
```

## Wiederaufnahme-Akzeptanztest

```yaml
resume_acceptance_tests:
  - id: RAT-01
    zweck: "Beweist Ende-zu-Ende und ursachenunabhängig: authentik erreichbar, well-known-Pfadschema unverändert, Staging-Slug-Namensschema (<hub>-staging) trägt weiterhin."
    prozedur: "curl -s -o /dev/null -w '%{http_code}' https://id.iil.pet/application/o/coach-hub-staging/.well-known/openid-configuration"
    erwartet: "HTTP 200"
    baseline_beim_einfrieren: pass   # 200, ausgeführt 2026-07-17
```

## Coverage + Restunsicherheit

| Annahmeart | Abdeckung |
|---|---|
| vertrag | vw-slug-codedefault, vw-redirect-konvention |
| werkzeug | vw-ak-zugang |
| quelle | vw-staging-fehlliste, vw-prod-bestand |
| kontext | n_a: ADR-142 ist accepted; ein Supersede würde den Wiederaufnahme-Trigger selbst ändern und fällt beim Kill-Gate-Review auf |
| entscheidung | n_a: keine verriegelte Wahl mit plausiblem Wiederöffner — der Rollout führt nur eine accepted-Entscheidung aus |
| operator | n_a: Write-Pfad (ak shell) ist in vw-ak-zugang abgedeckt; Secrets-Verfahren je Hub wird laut Plan-Schritt 5 ohnehin je Hub neu verifiziert |
| bewertung | RAT-01 + Smoke-Test-Definition in Plan-Schritt 7 |

**Restunsicherheit (keine Vollständigkeitsbehauptung):** (a) Ein authentik-**Versions-Upgrade** ist NICHT als Auslöser erfasst — beim Einfrieren lag kein Baseline-Versionswert vor; die Pflicht-Details signing_key + Scope-Mappings (Plan-Schritt 3) könnten sich mit einem Major-Upgrade ändern → beim Ausmotten als `unknown` führen und die zwei Pflicht-Details gegen die dann laufende Version gegenprüfen. (b) weltenhub-Redis-Incident (HTTP 500 auf /oidc/, falscher Redis-Host `bfagent_redis`) ist **bewusst NICHT Teil dieses Pakets** — Deploy-Health-Thema, blockiert nur den weltenhub-Smoke-Test, nicht die 5 Staging-Anlagen. (c) onboarding-hub-Staging-Domain-Widerspruch (Registry vs. ports.yaml) ungeklärt, aber außerhalb des Pakets (onboarding-hub ist aus dem OIDC-Rollout raus, CF-Access stattdessen).

## Starre Zone (erst NACH den Checks lesen)

**Eingefrorener Stand (2026-07-17):** Prod-seitig ist ADR-142 Phase 2 faktisch
komplett (alle 9 Kunden-Hub-Prod-Applications live, inkl. cad-hub + travel-beat;
onboarding-hub via Cloudflare Access statt OIDC, User-Entscheid 2026-07-09).
Offen ist ausschließlich: **5 Hubs × Staging-Application.**

**Wiedereinstiegspunkt (erster konkreter Schritt):** Existenz-Check in ak shell
(Plan-Schritt 0), dann für die verbleibenden Slugs Provider+Application anlegen.

**Plan-Referenz (ankern statt kopieren):** Vollständiger Schritt-für-Schritt-Plan
(Schritte 0–8: Existenz-Check → Provider mit signing_key PFLICHT + Scope-Mappings
openid/email/profile PFLICHT → Application slug=<hub>-staging → RedirectURI STRICT
https://<staging-domain>/oidc/callback/ → Secret nach ~/.secrets/authentik/ →
Übersichtsdatei → Smoke-Test → ADR-142-Evidenz-PR) steht in E1 (CC-Memory) und
E3 (Outline-Runbook) — beide tragen denselben Stand 2026-07-09 inkl. der zwei
Korrektur-Nachträge (travel-beat/onboarding-hub raus; Live-Check-Ergebnisse).

**Staging-Domains der 5 Hubs:** staging.137herz.de · staging.bieterpilot.de ·
staging.prezimo.com · staging.trading-hub.iil.pet · staging.writing-hub.iil.pet.

**Sicherheits-Gate (unverändert gültig):** Staging-Writes ohne Rückfrage erlaubt;
**vor dem ersten Prod-Write explizite User-Freigabe** (Gates 2+3,
`~/.claude/policies/autonomy-gates.md`) — generische Autonomie-Freigaben zählen nicht.

## Nutzungs-Ledger (KONZ-023)

| Datum | Ereignis | Fund | Hätte Standing Rule gereicht? | Zeitkosten |
|---|---|---|---|---|
| 2026-07-17 | Einmotten (dieses Dokument) + Baseline-Lauf | Baseline bestätigt Memory-Stand (5×404, Prod 200, RAT-01 pass) | — (Einfrier-Ereignis, kein Fund) | ~20 Min |
