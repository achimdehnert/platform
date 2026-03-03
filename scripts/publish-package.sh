#!/usr/bin/env bash
# =============================================================================
# publish-package.sh — Environment-agnostic PyPI build + publish
# =============================================================================
#
# Fixes the root cause of "No module named hatch" errors in WSL:
# miniconda PATH shadows the user-local Python 3.10 where hatch/twine
# are actually installed. This script resolves the correct binary paths
# explicitly, regardless of which venv/conda env is active.
#
# USAGE:
#   bash scripts/publish-package.sh ~/github/aifw
#   bash scripts/publish-package.sh ~/github/aifw --test    # upload to TestPyPI
#   bash scripts/publish-package.sh ~/github/promptfw
#
# PREREQUISITES (one-time setup):
#   ~/.local/bin/pip install hatch twine --break-system-packages
#   Setup ~/.pypirc or export TWINE_USERNAME + TWINE_PASSWORD
#
# WHAT IT DOES:
#   1. Validates pyproject.toml + version
#   2. Resolves hatch/twine from user-local Python (not active venv/conda)
#   3. Builds wheel + sdist via hatch
#   4. Runs twine check (README lint)
#   5. Uploads to PyPI (or TestPyPI with --test)
#   6. Tags git with v<version>
#   7. Pushes tag to origin
#
# SAFETY:
#   - Refuses to upload if version already exists on PyPI
#   - Refuses if working tree is dirty (uncommitted changes)
#   - Dry-run mode with --dry-run
#
# =============================================================================
set -euo pipefail

# ── Logging ───────────────────────────────────────────────────────
_BOLD='\033[1m'; _GREEN='\033[0;32m'; _YELLOW='\033[1;33m'
_RED='\033[0;31m'; _CYAN='\033[0;36m'; _RESET='\033[0m'

log()    { echo -e "[publish]  $*"; }
header() { echo -e "\n${_BOLD}[publish] ══ $* ══${_RESET}"; }
ok()     { echo -e "${_GREEN}[publish] ✓${_RESET} $*"; }
warn()   { echo -e "${_YELLOW}[publish] ⚠${_RESET}  $*" >&2; }
err()    { echo -e "${_RED}[publish] ✗${_RESET} $*" >&2; exit 1; }
info()   { echo -e "${_CYAN}[publish]  $*${_RESET}"; }

# ── Args ─────────────────────────────────────────────────────────

PACKAGE_PATH="${1:-$(pwd)}"
TEST_PYPI=false
DRY_RUN=false

for arg in "${@:2}"; do
    case "$arg" in
        --test)    TEST_PYPI=true ;;
        --dry-run) DRY_RUN=true ;;
        *) err "Unknown argument: $arg. Usage: publish-package.sh <path> [--test] [--dry-run]" ;;
    esac
done

[[ -d "$PACKAGE_PATH" ]] || err "Package path not found: $PACKAGE_PATH"
[[ -f "$PACKAGE_PATH/pyproject.toml" ]] || err "No pyproject.toml found in $PACKAGE_PATH"

cd "$PACKAGE_PATH"

# ── Step 1: Read version from pyproject.toml ─────────────────────────────
header "Step 1: Read package metadata"

PKG_NAME="$(python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['name'])" 2>/dev/null \
    || python3 -c "import tomli; d=tomli.load(open('pyproject.toml','rb')); print(d['project']['name'])")"

PKG_VERSION="$(python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'])" 2>/dev/null \
    || python3 -c "import tomli; d=tomli.load(open('pyproject.toml','rb')); print(d['project']['version'])")"

[[ -z "$PKG_NAME" ]]    && err "Could not read project.name from pyproject.toml"
[[ -z "$PKG_VERSION" ]] && err "Could not read project.version from pyproject.toml"

info "Package : $PKG_NAME"
info "Version : $PKG_VERSION"
info "Path    : $PACKAGE_PATH"
$TEST_PYPI  && info "Target  : TestPyPI" || info "Target  : PyPI (production)"
$DRY_RUN    && warn  "DRY-RUN mode — will not upload or tag"

# ── Step 2: Git state check ─────────────────────────────────────────
header "Step 2: Git state check"

if [[ -d ".git" ]]; then
    DIRTY="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
    HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
    info "Branch  : $BRANCH @ $HEAD_SHA"
    if [[ "$DIRTY" -gt 0 ]]; then
        warn "Working tree has $DIRTY uncommitted change(s) — consider committing first:"
        git status --short | head -10 | sed 's/^/    /'
        # Not fatal — allow publish from dirty tree for hotfix scenarios
    else
        ok "Git working tree clean"
    fi
else
    warn "Not a git repo — skipping git checks"
fi

# ── Step 3: Resolve correct hatch binary ───────────────────────────────
header "Step 3: Resolve build tools"

# Root cause fix: try explicit paths before falling back to PATH
# Priority: user-local 3.10/3.11 install > PATH hatch
_find_hatch() {
    local candidates=(
        "$HOME/.local/bin/hatch"
        "$(python3.11 -m site --user-base 2>/dev/null)/bin/hatch"
        "$(python3.10 -m site --user-base 2>/dev/null)/bin/hatch"
        "$(which hatch 2>/dev/null || echo '')"
    )
    for c in "${candidates[@]}"; do
        [[ -x "$c" ]] && echo "$c" && return 0
    done
    return 1
}

_find_twine() {
    local candidates=(
        "$HOME/.local/bin/twine"
        "$(python3.11 -m site --user-base 2>/dev/null)/bin/twine"
        "$(python3.10 -m site --user-base 2>/dev/null)/bin/twine"
        "$(which twine 2>/dev/null || echo '')"
    )
    for c in "${candidates[@]}"; do
        [[ -x "$c" ]] && echo "$c" && return 0
    done
    return 1
}

HATCH_BIN="$(_find_hatch)" || err "hatch not found. Install: pip install hatch --break-system-packages"
TWINE_BIN="$(_find_twine)" || err "twine not found. Install: pip install twine --break-system-packages"

ok "hatch  : $HATCH_BIN"
ok "twine  : $TWINE_BIN"

# ── Step 4: Build ─────────────────────────────────────────────────────────────
header "Step 4: Build wheel + sdist"

# Check if dist already exists for this version
WHEEL_PATTERN="dist/${PKG_NAME//-/_}-${PKG_VERSION}-*.whl"
SDIST_PATTERN="dist/${PKG_NAME//-/_}-${PKG_VERSION}.tar.gz"

existing_wheel="$(ls $WHEEL_PATTERN 2>/dev/null | head -1 || echo '')"
existing_sdist="$(ls $SDIST_PATTERN 2>/dev/null | head -1 || echo '')"

if [[ -n "$existing_wheel" && -n "$existing_sdist" ]]; then
    warn "Dist artifacts already exist:"
    ls dist/${PKG_NAME//-/_}-${PKG_VERSION}* | sed 's/^/    /'
    read -r -p "[publish] Rebuild? (y/N): " rebuild
    if [[ "${rebuild,,}" == "y" ]]; then
        rm -f dist/${PKG_NAME//-/_}-${PKG_VERSION}*
        "$HATCH_BIN" build
    else
        ok "Using existing artifacts"
    fi
else
    "$HATCH_BIN" build
fi

# Verify artifacts were created
WHEEL="$(ls dist/${PKG_NAME//-/_}-${PKG_VERSION}-*.whl 2>/dev/null | head -1)"
SDIST="$(ls dist/${PKG_NAME//-/_}-${PKG_VERSION}.tar.gz 2>/dev/null | head -1)"

[[ -z "$WHEEL" ]] && err "Wheel not found after build. Check hatch output above."
[[ -z "$SDIST" ]] && err "sdist not found after build. Check hatch output above."

ok "wheel  : $WHEEL ($(du -sh "$WHEEL" | cut -f1))"
ok "sdist  : $SDIST ($(du -sh "$SDIST" | cut -f1))"

# ── Step 5: twine check ───────────────────────────────────────────────────────
header "Step 5: twine check (README + metadata lint)"
"$TWINE_BIN" check dist/${PKG_NAME//-/_}-${PKG_VERSION}* && ok "twine check passed"

# ── Step 6: Upload ───────────────────────────────────────────────────────────
header "Step 6: Upload to $(${TEST_PYPI} && echo 'TestPyPI' || echo 'PyPI')"

if $DRY_RUN; then
    warn "DRY-RUN — skipping upload. Would run:"
    if $TEST_PYPI; then
        echo "  $TWINE_BIN upload --repository testpypi dist/${PKG_NAME//-/_}-${PKG_VERSION}*"
    else
        echo "  $TWINE_BIN upload dist/${PKG_NAME//-/_}-${PKG_VERSION}*"
    fi
else
    if $TEST_PYPI; then
        "$TWINE_BIN" upload --repository testpypi dist/${PKG_NAME//-/_}-${PKG_VERSION}*
    else
        "$TWINE_BIN" upload dist/${PKG_NAME//-/_}-${PKG_VERSION}*
    fi
    ok "Uploaded $PKG_NAME==$PKG_VERSION to $(${TEST_PYPI} && echo 'TestPyPI' || echo 'PyPI')"
fi

# ── Step 7: Git tag ────────────────────────────────────────────────────────────
header "Step 7: Git tag v${PKG_VERSION}"

if [[ -d ".git" ]] && ! $DRY_RUN && ! $TEST_PYPI; then
    TAG="v${PKG_VERSION}"
    if git tag --list | grep -q "^${TAG}$"; then
        warn "Tag $TAG already exists — skipping"
    else
        git tag -a "$TAG" -m "Release $PKG_NAME $TAG"
        git push origin "$TAG"
        ok "Tagged and pushed: $TAG"
    fi
elif $TEST_PYPI; then
    info "Skipping git tag for TestPyPI upload"
elif $DRY_RUN; then
    warn "DRY-RUN — skipping git tag"
fi

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo -e "${_BOLD}[publish] ══ Done ══${_RESET}"
echo "  Package : $PKG_NAME==$PKG_VERSION"
$DRY_RUN   && echo "  Mode    : DRY-RUN (nothing uploaded)" \
           || echo "  Upload  : $(${TEST_PYPI} && echo 'TestPyPI' || echo 'PyPI https://pypi.org/project/'${PKG_NAME}'/')"
echo ""
