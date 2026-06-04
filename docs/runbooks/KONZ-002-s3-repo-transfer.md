# Runbook — KONZ-002 S3: Repo-Transfer `achimdehnert` → Enterprise-Org (pro Repo)

> Detaillierung von **S3** aus [`KONZ-002-consolidation-rollout.md`](./KONZ-002-consolidation-rollout.md).
> Governance: **[ADR-236](../adr/ADR-236-altd-enterprise-boundary.md)** (accepted). Ziel-Org-Default: `iilgmbh`.
> Stand: 2026-06-03.

## Wann S3 starten (Vorbedingungen — sonst NICHT)

- [ ] **S1 grün:** Ziel-Org ist Enterprise-Member.
- [ ] **S2 `enforced`:** Security-Config am Ziel aktiv → migrierte Repos erben native Push-Protection (REC-9). *Ohne das liegt das Repo unprotected.*
- [ ] **Ziel admin-kontrolliert:** `achimdehnert` hat **Org-Rolle `admin`** auf der Ziel-Org (nicht nur `admin:org`-Scope — REC-8). Verifiziert 2026-06-03 für `iilgmbh`. → ermöglicht Transfer **und** Rückbau.
- [ ] **In Wellen**, nicht alles auf einmal. Erste Welle = 1 risikoarmer Canary (kein Prod-Deploy, wenige Secrets).

## Rollenteilung
- **Owner** führt den **Transfer** aus (Org-Struktur-Schritt) und Secret-Re-Provisioning, das `~/.secrets/` liest.
- **CC** kann Inventar, Caller-Ref-PRs, Registry-Update, Post-Verify übernehmen (reversibel).

---

## Per-Repo-Checkliste

Platzhalter: `<repo>` = Repo-Name, `<org>` = Ziel-Org (default `iilgmbh`).

### A. Pre-Transfer-Inventar (das, was bricht, VORHER erfassen)

> Secrets sind **write-only** — vor dem Transfer **auflisten** (Werte aus `~/.secrets/` re-sourcen, nie aus GitHub auslesbar).

- [ ] **Actions-Secrets** (gehen verloren): `gh secret list -R achimdehnert/<repo>`
- [ ] **Dependabot-Secrets** (verloren): `gh secret list --app dependabot -R achimdehnert/<repo>`
- [ ] **Environment-Secrets** (verloren): `gh api repos/achimdehnert/<repo>/environments --jq '.environments[].name'` → je Env Secrets listen
- [ ] **Variables** (überleben Transfer — bestätigt im Drill, trotzdem verifizieren): `gh variable list -R achimdehnert/<repo>`
- [ ] **Webhooks:** `gh api repos/achimdehnert/<repo>/hooks --jq '.[].config.url'`
- [ ] **Deploy-Keys:** `gh api repos/achimdehnert/<repo>/keys --jq '.[].title'`
- [ ] **Branch-Protection / Rulesets:** `gh api repos/achimdehnert/<repo>/rulesets` (übertragen u.U. nicht sauber → notieren)
- [ ] **Package-Owner / GHCR-Refs** notieren (Container/Packages hängen am alten Owner)
- [ ] **Hardcoded Caller-Refs** (der ~14-Caller-Lock-in, KONZ B6): `gh search code "achimdehnert/<repo>" --owner achimdehnert --owner iilgmbh -- --filename=*.yml` → reusable-`uses:`-Referenzen sammeln
- [ ] **CI-Baseline:** aktueller Default-Branch-CI-Status grün? (Soll-Vergleich für Post-Verify)

### B. Transfer (Owner)

- [ ] UI: `Settings → Danger Zone → Transfer ownership` → Ziel-Org `<org>`. **Oder** API:
  ```bash
  gh api -X POST repos/achimdehnert/<repo>/transfer -f new_owner=<org>
  ```
- [ ] Bestätigen: `gh repo view <org>/<repo> --json owner,visibility`

### C. Re-Provisioning (sofort nach Transfer)

- [ ] **Actions-Secrets neu setzen** (aus `~/.secrets/`, nie echoen):
  ```bash
  gh secret set <NAME> -R <org>/<repo> < ~/.secrets/<quelle>
  ```
- [ ] **Dependabot- / Environment-Secrets** analog neu setzen.
- [ ] **Variables** prüfen (sollten da sein): `gh variable list -R <org>/<repo>`
- [ ] **Webhooks / Deploy-Keys** neu anlegen, falls nicht mitgewandert.
- [ ] **Config-Vererbung verifizieren** — native Push-Protection aktiv?
  ```bash
  gh api repos/<org>/<repo> --jq '.security_and_analysis'
  ```
- [ ] **Security-Config je Repo-Typ setzen** (Canary-Befund 2026-06-03, s.u.): transferierte Repos erben **Config 17 / volle Suite** (Default-for-new), inkl. CodeQL.
  - **Echte Anwendung (Code)** → Config 17 **behalten** (CodeQL erwünscht). Nichts tun.
  - **Nicht-Code (Konfig/Setup/Doku/Daten)** → **schlank überschreiben** (CodeQL aus, Push-Protection bleibt) via **Org-Level**-Attach (`scope=selected`; Enterprise-Attach kann nur `all`):
    ```bash
    RID=$(gh api repos/<org>/<repo> --jq .id)
    GH_TOKEN=<enterprise-pat> gh api -X POST orgs/<org>/code-security/configurations/251767/attach -f scope=selected -F "selected_repository_ids[]=$RID"
    # verify: …/code-scanning/default-setup -> state=not-configured
    ```
- [ ] **Caller-Refs umstellen:** je Caller-Repo PR `uses: achimdehnert/<repo>/...@x` → `uses: <org>/<repo>/...@x`.
- [ ] **Registry:** `scripts/repo-registry.yaml` neuen Owner eintragen.
- [ ] **Deploy-Pfade / Package-Refs** aktualisieren (ship-Skripte, Compose, Image-Tags).

### D. Post-Verify (Akzeptanz — alle grün = Welle ok)

- [ ] Test-Push / Re-Run → **CI grün** (gegen Baseline aus A).
- [ ] **Positiv-Kontrolle:** ein bekanntes Test-Secret pushen → **Push-Protection blockt** (beweist Config-Vererbung wirkt).
- [ ] Alte URL `github.com/achimdehnert/<repo>` **leitet weiter**.
- [ ] Caller-Repos grün (keine gebrochenen reusable-Workflows).
- [ ] Test-Secret-Commit wieder entfernen.

### E. Rollback (innerhalb derselben Welle)

> Möglich, weil `achimdehnert` admin auf der Ziel-Org ist (REC-8). Bei einer Fremd-Org wäre das ein Einbahn-Exit.

- [ ] Zurück-Transfer: `gh api -X POST repos/<org>/<repo>/transfer -f new_owner=achimdehnert`
- [ ] **Secrets erneut re-provisionieren** (gehen beim Rück-Transfer wieder verloren).
- [ ] Caller-Ref-PRs reverten.
- [ ] Registry zurücksetzen.

---

## Wellen-Steuerung

| Welle | Auswahl | Stopp-Kriterium |
|---|---|---|
| 0 (Canary) | 1 Repo ohne Prod-Deploy, ≤1 Secret | Post-Verify rot → S3 pausieren, Ursache fixen |
| 1..n | Batches nach Risiko (zuerst ohne Deploy, dann mit) | je Welle erst nach grünem Post-Verify der Vorwelle |

**Nicht in dieser Welle:** Repos mit komplexem Package-/Deploy-Coupling bis OOTB-5 (Coupling-Indirektion / repointbare Alias-Stelle) gebaut ist — sonst brechen die ~14 Caller (KONZ B6/AD-4). Bis dahin: Caller-Refs manuell pro Transfer mitziehen (Schritt C).

## Canary-Welle (2026-06-03) — Ergebnis

Canary = `desktop-setup` (Nicht-Code, 0 Secrets) → `iilgmbh`. **Transfer + Redirect + Push-Protection-Vererbung + gitleaks grün ✅, kostenneutral (Committer 2/2).**

**Hauptbefund — Config-Vererbung beim Transfer:** Ein transferierter Repo wird wie ein **Neuzugang** behandelt → erbt die **Default-for-new-Config (17, volle Suite inkl. CodeQL)**, NICHT die schlanke apply-to-all. Für die meisten Migrationsziele (echte `-hub`-Apps) ist das **erwünscht** (CodeQL = SAST/Daten-Fluss-Analyse, eigene Verteidigungslinie neben Secret-Scanning). Nur für **Nicht-Code-Repos** ist es Overhead/Kosten → dort gezielt schlank überschreiben (Schritt C).

**Regel (verfeinert ggü. „immer schlank"):**

| Repo-Typ | Security-Config | Aktion nach Transfer |
|---|---|---|
| echte Anwendung (Code) | Config 17 (mit CodeQL) | nichts — Default ist richtig |
| Konfig / Setup / Doku / Daten | `slim-prevention` | Org-Level-Attach `scope=selected` (Schritt C) |

**Operativer Befund:** Enterprise-Attach kann nur `all`/`all_without_configurations`; **per-Repo-Override nur über Org-Level-Attach** (`orgs/<org>/code-security/configurations/<id>/attach scope=selected`). Verifikation: `…/code-scanning/default-setup` → `state=not-configured` bei schlank.

## Changelog
- 2026-06-03: Initial — S3-Per-Repo-Transfer-Checkliste (Inventar/Transfer/Re-Provision/Verify/Rollback + Wellen).
- 2026-06-03: Canary `desktop-setup` durchgeführt + Config-je-Repo-Typ-Regel (Code→17, Nicht-Code→slim via Org-Level-Attach) ergänzt; Step C erweitert.
