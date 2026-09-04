# Secrets Management (ADR-045 + Issue #18 FIX-F)

## Overview

All IIL Platform secrets are managed in three layers:

| Layer | Where | What |
|-------|-------|------|
| **GitHub Repo Secrets** | Per-repo Settings → Secrets | CI/CD secrets (SSH keys, API tokens, deploy credentials) |
| **Server-side .env.prod** | `/opt/<repo>/.env.prod` | Runtime secrets (Django SECRET_KEY, DB passwords, API keys) |
| **Local Developer** | `~/.secrets/` | MCP tool tokens (Hetzner, GitHub, Cloudflare, IONOS) |

## Inventory

Full secrets inventory: [`secrets-inventory.yaml`](secrets-inventory.yaml)

## Phase 1: GitHub Secrets (Current)

Secrets are set per-repo in GitHub Settings → Secrets and variables → Actions.

### Shared secrets (duplicated across repos)

These secrets have identical values across multiple repos and should be
consolidated to GitHub Organization-level secrets when an organization is used:

- `DEPLOY_SSH_KEY` — SSH key for prod server (6 repos)
- `DEPLOY_HOST` / `DEPLOY_USER` — prod server access (6 repos)
- `PROJECT_PAT` — GitHub PAT for cross-repo ops (7 repos)
- `HETZNER_HOST` / `HETZNER_SSH_KEY` / `HETZNER_USER` — Hetzner access (3 repos)
- `HETZNER_DEV_*` — dev-server access (3 repos)
- `DISCORD_WEBHOOK` — deployment notifications (2 repos)

### Naming convention

| Prefix | Meaning |
|--------|---------|
| `DEPLOY_*` | Production deployment credentials |
| `STAGING_*` | Staging environment credentials |
| `HETZNER_*` | Hetzner server access |
| `HETZNER_DEV_*` | Hetzner dev-server (staging) |
| `STRIPE_*` | Stripe payment processing |
| `SOPS_*` | SOPS encryption keys |

## Phase 2: SOPS + age (Planned)

Encrypt `.env.staging` files so they can be safely committed to repos.

### Setup

```bash
# Install age + sops
sudo apt install age
# or: brew install age
wget -qO /usr/local/bin/sops https://github.com/getsops/sops/releases/latest/download/sops-v3-linux-amd64
chmod +x /usr/local/bin/sops

# Generate age key (on dev-server)
age-keygen -o /etc/secrets/staging.key
chmod 600 /etc/secrets/staging.key

# Extract public key
age-keygen -y /etc/secrets/staging.key
# → age1abc123...  (use this in .sops.yaml)
```

### Per-repo setup

1. Copy `infra/templates/sops.yaml` → `.sops.yaml` in repo root
2. Replace `age1REPLACE_WITH_ACTUAL_PUBLIC_KEY` with actual public key
3. Encrypt: `sops --encrypt .env.staging > .env.staging.enc`
4. Commit `.env.staging.enc`, add `.env.staging` to `.gitignore`
5. Add `SOPS_AGE_KEY` (private key content) to GitHub repo secrets

### CI/CD decryption

```yaml
- name: Decrypt staging secrets
  env:
    SOPS_AGE_KEY: ${{ secrets.SOPS_AGE_KEY }}
  run: |
    echo "$SOPS_AGE_KEY" > /tmp/age.key
    SOPS_AGE_KEY_FILE=/tmp/age.key sops --decrypt .env.staging.enc > .env.staging
    rm /tmp/age.key
```

## Rotationslauf (Stufe 1, KONZ-dev-hub-005 / platform#2813)

Die Tabelle darunter sagt, *wie oft*. Sie sagt nicht, *ob es geschehen ist* — bis
zum 2026-09-04 kannte das Inventar fuer keinen seiner Eintraege einen letzten
Lauf. Dafuer gibt es jetzt eine Kette mit Nachweis:

| Schritt | Werkzeug | Wer |
|---|---|---|
| Was haengt an diesem Secret, womit belegt man es? | `python3 tools/rotate.py pruefen <NAME>` | Agent |
| Setzen + Belegen + Protokollieren + Schleuse leeren | `python3 tools/rotate.py lauf <NAME> --quelle ~/shared/<datei>` | **Owner** (beruehrt den Wert) |
| Negativprobe nach dem Widerruf | `python3 tools/rotate.py widerruf-geprueft <LAUF-ID>` | Agent |
| Was ist faellig / ohne Beleg / Altlast? | `python3 tools/rotate.py faellig` | Runner-Phase 0.7.25 |

Das Lauf-Protokoll ist `infra/rotation-log.jsonl` (append-only, keine Werte, ein
Fingerabdruck je Lauf). Das Inventar bleibt SSoT — das Werkzeug schreibt nie hinein.

### Pruef-Workflow in einem Zielrepo einrichten

`docs/templates/secret-probe.yml` nach `.github/workflows/secret-probe.yml` im
Zielrepo kopieren, dann im Inventar beim Konsumenten eintragen:

```yaml
    consumers:
      - kind: github_repo_secret
        ref: iilgmbh/risk-hub
        name: PROJECT_PAT
        proof:
          workflow: secret-probe.yml
          log_marker: "✓ PROJECT_PAT gueltig"
```

Einmalige **Negativprobe** beim Anlegen: den Workflow mit dem alten oder ohne
Wert starten — er muss rot werden. Ein Beleg-Workflow, der nie rot war, belegt
nichts. Zwei Fallen, die das in der Praxis kaputt machen: ein Rueckfall auf
`secrets.GITHUB_TOKEN` (macht den Job auch ohne das Secret gruen) und ein
Beleg, der an einem Deploy-Workflow haengt (wird beim naechsten Mal nicht mehr
gefahren).

## Rotation Schedule

| Secret Type | Frequency | Process |
|-------------|-----------|---------|
| SSH keys | Quarterly | `ssh-keygen` → update GitHub secrets + `authorized_keys` |
| API keys (OpenAI, Anthropic) | Yearly | Regenerate on provider → update GitHub secrets |
| GitHub PAT | Yearly | GitHub Settings → regenerate → update all repos |
| Stripe keys | As needed | Stripe Dashboard → update GitHub secrets + .env.prod |
| Django SECRET_KEY | On breach only | Generate new → update .env.prod → restart containers |
| SOPS age key | Yearly | `age-keygen` → re-encrypt all .enc files → update GitHub secrets |

## Security Rules

1. **NEVER** commit plaintext `.env`, `.env.prod`, `.env.staging` files
2. **NEVER** use `${VAR}` interpolation in `docker-compose.prod.yml` `environment:` section — use `env_file:` instead
3. **NEVER** hardcode secrets in source code — use `decouple.config()` (ADR-045)
4. **NEVER** log secret values — mask in CI with `::add-mask::`
5. **ALWAYS** use `chmod 600` for key files on servers
6. **ALWAYS** use `umask 077` before writing SSH keys in CI
