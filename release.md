---
description: Publish a Python package (iil-aifw, promptfw, authoringfw, ...) to PyPI
---

# Release Workflow — PyPI Publish

## iil-testkit — Autonomer Publish (kein lokaler Token nötig)

`iil-testkit` nutzt `PYPI_API_TOKEN` aus dem **platform-Repo** GitHub Secrets.

```bash
# Direkt auslösen — kein ~/.pypirc, kein lokaler Token:
TOKEN=$(cat ~/.secrets/github_PAT)
curl -s -X POST \
  -H "Authorization: token ${TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/achimdehnert/platform/actions/workflows/publish-iil-testkit.yml/dispatches" \
  -d '{"ref":"main","inputs":{"dry_run":"false"}}'

# Status + Verify:
sleep 30
curl -s "https://pypi.org/pypi/iil-testkit/json" | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['version'])"
```

---

## Andere Packages (aifw, promptfw, authoringfw, ...) — via ~/.pypirc

For any Python package in the ecosystem (`aifw`, `promptfw`, `authoringfw`, ...).

## Prerequisites (one-time setup)

If `~/.pypirc` does not exist yet:

```bash
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = <YOUR_PYPI_API_TOKEN>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <YOUR_TESTPYPI_API_TOKEN>
EOF
chmod 600 ~/.pypirc
```

PyPI API Tokens: https://pypi.org/manage/account/token/

## Step 1: Verify package state

// turbo
```bash
cd ${GITHUB_DIR:-$HOME/github}/aifw && git log --oneline -3 && git status
```

## Step 2: Build + publish to PyPI

```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/publish-package.sh ${GITHUB_DIR:-$HOME/github}/aifw
```

For other packages:
```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/publish-package.sh ${GITHUB_DIR:-$HOME/github}/promptfw
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/publish-package.sh ${GITHUB_DIR:-$HOME/github}/authoringfw
```

## Step 3: Test upload first (optional)

```bash
bash ${GITHUB_DIR:-$HOME/github}/platform/scripts/publish-package.sh ${GITHUB_DIR:-$HOME/github}/aifw --test
```

## Step 4: Verify on PyPI

// turbo
```bash
pip index versions iil-aifw 2>/dev/null | head -3
```

## Notes

- Script resolves `hatch`/`twine` from `~/.local/bin/` — immune to active venv/conda
- Existing `dist/` artifacts are reused (prompts before rebuild)
- Git tag `v<version>` is created + pushed automatically on production publish
- `--dry-run` flag available for safe testing
- See `scripts/publish-package.sh --help` equivalent: read script header
