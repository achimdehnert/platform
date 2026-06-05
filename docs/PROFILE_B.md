# Profil B — GitHub-Admin Break-Glass (iilgmbh)

> **Lifecycle-Artefakt** für das github-admin-Mandat (Sessions 2026-06-05).
> Profil **A** (Cross-Repo-Dev) braucht keine Sonderrechte — der normale
> `gho_`-OAuth-Login deckt es. **Dieses Dokument = Profil B** (org/enterprise-
> Admin) und sein **Re-Narrow-Gate**.

## Entscheidung (festgeschrieben)

- **Mandat:** volle org/repo-Admin via **GitHub App** (nicht persönlicher PAT).
  Enterprise-Billing/-Policy bleiben Mini-Break-Glass über den Enterprise-PAT.
- **Auth-Bauform:** kurzlebiger Installation-Token (~1 h) statt langlebigem
  God-PAT. Token nie persistiert; pro Befehl/Session frisch geprägt.
- **Install-Scope:** `iilgmbh` + `bahn-sqf` + persönlicher Account `achimdehnert`.
  **Gov-Orgs (`ttz-lif`/`meiki-lra`) bewusst DRAUSSEN** — bei Bedarf 10-Sekunden-
  Scope-Erweiterung im UI, nicht per Default (Bürger-/Behörden-Workloads).
- **Modus:** Break-Glass pro Umbau-Task (`claude-ent`), nicht stehend.
  Irreversible Aktionen (Member entfernen · Billing · Org-Transfer · Repo-Delete)
  immer mit explizitem Einzel-OK des Owners, auch wenn der Token sie erlaubt.

## Permission-Manifest (beim App-Anlegen setzen)

**Repository** (Read & Write, außer Metadata=Read):
Administration · Contents · Actions · Workflows · Environments · Secrets ·
Variables · Pull requests · Issues · Pages · Webhooks · Deployments · *Metadata (R)*

**Organization** (Read & Write):
Administration · Members · Org secrets · Org variables · Org webhooks ·
Custom properties · Self-hosted runners · Teams

**Enterprise** (später, Public-Preview-Sets — nur wenn Enterprise-Ops nötig):
Org-Installations · People · Org-Management · SSO · Custom properties

## Anlege-Schritte (Owner, UI)

1. `github.com/organizations/iilgmbh/settings/apps` → **New GitHub App**.
2. Permissions = Manifest oben. Webhooks: keine (oder nach Bedarf).
   „Where can this be installed" → **Only this account**.
3. **Generate a private key** → speichern als
   `~/.secrets/github_app_iilgmbh_admin.pem` (chmod 600).
4. **App ID** notieren (App-Settings-Seite).
5. **Install** auf `iilgmbh`, `bahn-sqf`, `achimdehnert` → je **Installation ID**
   notieren (URL der Install-Settings: `.../installations/<ID>`).

## Token prägen + claude-ent

Nach dem Anlegen, in `~/.bashrc`:

```bash
export GH_APP_ID=<app-id>
export GH_APP_KEY="$HOME/.secrets/github_app_iilgmbh_admin.pem"
export GH_APP_INSTALL_ID=<install-id-iilgmbh>   # je Org eine; passende setzen
# Break-Glass-Session: Enterprise-/Org-Admin-Token nur in DIESEM Terminal
alias claude-ent='GH_TOKEN="$(~/github/platform/tools/gh-app-token.sh)" claude'
```

`claude-ent` startet eine Session, in der `gh` über den kurzlebigen App-Token
läuft (Profil B). Normaler `claude` = Profil A (dein OAuth-Login). Die
Terminal-Wahl **ist** der Scope-Checkpoint.

## Re-Narrow-Gate (Kill-Gate gegen den „temporär→permanent"-Ratchet)

Profil B ist breit, **weil** gerade Umbau läuft. Die Verengung ist eine
**getrackte Pflicht**, kein Vorsatz:

- **Trigger:** Abschluss der KONZ-002-Konsolidierung (S4 erledigt, Repos in
  Enterprise-Org, User-Account ausgetrocknet) **ODER** spätestens `review_by`.
- **`review_by`:** 2026-09-05.
- **Aktion bei Trigger:** Install-Scope auf das tatsächlich noch nötige Minimum
  zusammenziehen (UI, Sekunden); Permission-Set auf den dann real genutzten
  Subset reduzieren; Enterprise-PAT-Break-Glass auf Notwendigkeit prüfen.
- **Verifikation:** App-Install-Liste + Permission-Set gegen dieses Dokument;
  Abweichung = entweder hier begründen oder verengen.

## Verifiziert / nicht verifiziert

- **Verifiziert (2026-06-05):** GitHub Apps können org/repo-Admin voll (GA) +
  Enterprise-Member/Org/SSO (Public Preview); Billing/-Policy **nicht** → PAT-Rest.
- **Nicht verifiziert:** die App existiert noch nicht (UI-Schritt offen);
  App-ID/Install-IDs sind nach dem Anlegen einzutragen.
