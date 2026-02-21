# ADR-060: Developer Workstation SSH Key Configuration Standard

**Status:** Accepted  
**Date:** 2026-02-21  
**Scope:** All platform repositories, all developer workstations (WSL2/Linux)  
**Supersedes:** —  
**Related:** ADR-021 (Unified Deployment Pattern), ADR-022 (Repository Consistency)

---

## Context

During CI/local development runs the following warning appeared:

```
Warning: Identity file /home/dehnert/.ssh/github_ed25519 not accessible: No such file or directory.
```

The SSH config referenced `github_ed25519` as the identity file for GitHub, but the actual key on the workstation is named `id_ed25519` (OpenSSH default). This caused:

- Silent fallback to password auth (which fails for GitHub)
- Confusing warning on every `git pull / push`
- Inconsistency between documentation, global user rules, and actual filesystem state

There was no authoritative, documented standard for SSH key naming and `~/.ssh/config` layout across developer workstations.

---

## Decision

### 1. Canonical SSH Key Name: `id_ed25519`

The platform standard key for GitHub authentication is:

```
~/.ssh/id_ed25519        (private key)
~/.ssh/id_ed25519.pub    (public key)
```

**Rationale:** `id_ed25519` is the OpenSSH default. It is picked up automatically without any `IdentityFile` directive, eliminating the need for explicit config and reducing misconfiguration risk.

### 2. Canonical `~/.ssh/config` for GitHub

```sshconfig
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
```

- `IdentitiesOnly yes` — prevents SSH from trying other keys (avoids agent noise)
- `AddKeysToAgent yes` — adds key to ssh-agent on first use (no repeated passphrase prompts)
- **No** `github_ed25519` or custom names — use the default

### 3. Git URL Rewrite (global)

```bash
git config --global url."git@github.com:".insteadOf "https://github.com/"
```

This ensures all `git clone https://...` calls transparently use SSH.

### 4. Verification Command

```bash
ssh -T git@github.com
# Expected: Hi achimdehnert! You've successfully authenticated...
```

### 5. Key Generation (if key missing)

```bash
ssh-keygen -t ed25519 -C "achim.dehnert@iil.gmbh" -f ~/.ssh/id_ed25519
# Then add ~/.ssh/id_ed25519.pub to GitHub → Settings → SSH Keys
```

---

## Consequences

### Positive
- No more `Identity file not accessible` warnings
- Consistent setup across all developer machines and CI environments
- Self-documenting: OpenSSH default requires zero config to work

### Negative
- Developers with existing `github_ed25519` keys must rename or update `~/.ssh/config`

### Migration for existing `github_ed25519` setups

```bash
# Option A: Rename key (recommended)
mv ~/.ssh/github_ed25519 ~/.ssh/id_ed25519
mv ~/.ssh/github_ed25519.pub ~/.ssh/id_ed25519.pub
chmod 600 ~/.ssh/id_ed25519

# Option B: Update config only (keep old key name)
# Edit ~/.ssh/config: change IdentityFile to ~/.ssh/github_ed25519
# (non-standard, not recommended)
```

---

## Enforcement

### `repo_checker.py` check (informational)

`check_ssh_config` is **not** added to `repo_checker.py` — SSH config is a workstation concern, not a repo concern.

### Onboarding checklist (`onboard-repo.md`)

The `/onboard-repo` workflow references this ADR in the developer setup section.

### Global User Rules

The global user rules memory is updated to reflect `id_ed25519` as the canonical key name (replacing the previous `github_ed25519` reference).

---

## Reference: Complete WSL2 Setup Sequence

```bash
# 1. Generate key (skip if id_ed25519 already exists)
ssh-keygen -t ed25519 -C "achim.dehnert@iil.gmbh" -f ~/.ssh/id_ed25519

# 2. Add public key to GitHub
cat ~/.ssh/id_ed25519.pub
# → GitHub → Settings → SSH and GPG keys → New SSH key

# 3. Configure SSH
cat >> ~/.ssh/config << 'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    AddKeysToAgent yes
EOF
chmod 600 ~/.ssh/config

# 4. Configure git URL rewrite
git config --global url."git@github.com:".insteadOf "https://github.com/"

# 5. Verify
ssh -T git@github.com
```
