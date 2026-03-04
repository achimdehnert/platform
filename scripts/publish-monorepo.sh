#!/usr/bin/env bash
# =============================================================================
# publish-monorepo.sh — uv-workspace PyPI build + publish for monorepos
# =============================================================================
#
# Designed for repos using 'uv' workspaces (pyproject.toml with
# [tool.uv.workspace] members = ["packages/*"]).
#
# ROOT CAUSE FIX for 'syntax error near unexpected token newline':
#   Never pass a PyPI token as a CLI argument with angle-bracket placeholders.
#   This script reads the token ONLY via:
#     1. PYPI_TOKEN environment variable  (preferred for CI)
#     2. Interactive 'read -s' prompt     (preferred for local use)
#   Passing '<DEIN_TOKEN>' on the command line is now impossible by design.
#
# USAGE:
#   bash scripts/publish-monorepo.sh                          # all packages
#   bash scripts/publish-monorepo.sh --only nl2cad-core       # single package
#   bash scripts/publish-monorepo.sh --only nl2cad-core,nl2cad-areas
#   bash scripts/publish-monorepo.sh --dry-run                # build only, no upload
#   bash scripts/publish-monorepo.sh --test                   # upload to TestPyPI
#   PYPI_TOKEN=pypi-xxx bash scripts/publish-monorepo.sh      # non-interactive CI
#
# PREREQUISITES:
#   uv must be installed: curl -LsSf https://astral.sh/uv/install.sh | sh
#   pyproject.toml must have [tool.uv.workspace] members
#
# OPTIONAL — configure default packages in your repo's publish-monorepo.sh:
#   Copy this script locally and set DEFAULT_PACKAGES below.
#
# =============================================================================
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
_BOLD='\033[1m'; _GREEN='\033[0;32m'; _YELLOW='\033[1;33m'
_RED='\033[0;31m'; _CYAN='\033[0;36m'; _RESET='\033[0m'

log()    { echo -e "[publish]  $*"; }
header() { echo -e "\n${_BOLD}[publish] ══ $* ══${_RESET}"; }
ok()     { echo -e "${_GREEN}[publish] ✓${_RESET} $*"; }
warn()   { echo -e "${_YELLOW}[publish] ⚠${_RESET}  $*" >&2; }
err()    { echo -e "${_RED}[publish] ✗${_RESET} $*" >&2; exit 1; }
info()   { echo -e "${_CYAN}[publish]  $*${_RESET}"; }

# ── Defaults (override in repo-local copy) ────────────────────────────────────
# Read from [tool.uv.workspace] members if not set explicitly.
DEFAULT_PACKAGES=()

# ── Argument parsing ──────────────────────────────────────────────────────────
TEST_PYPI=false
DRY_RUN=false
ONLY_PACKAGES=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --test)    TEST_PYPI=true; shift ;;
        --dry-run) DRY_RUN=true;   shift ;;
        --only)
            [[ -z "${2:-}" ]] && err "--only requires a comma-separated package list"
            ONLY_PACKAGES="$2"; shift 2 ;;
        --only=*)
            ONLY_PACKAGES="${1#--only=}"; shift ;;
        -h|--help)
            grep '^#' "$0" | grep -v '#!/' | sed 's/^# \?//'
            exit 0 ;;
        *) err "Unknown argument: $1. Use --help for usage." ;;
    esac
done

# ── Locate repo root ──────────────────────────────────────────────────────────
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

[[ -f "pyproject.toml" ]] || err "No pyproject.toml found in $REPO_ROOT"

# ── Resolve packages to build ─────────────────────────────────────────────────
if [[ -n "$ONLY_PACKAGES" ]]; then
    IFS=',' read -ra PACKAGES <<< "$ONLY_PACKAGES"
elif [[ ${#DEFAULT_PACKAGES[@]} -gt 0 ]]; then
    PACKAGES=("${DEFAULT_PACKAGES[@]}")
else
    # Auto-detect from workspace members
    mapfile -t PACKAGES < <(
        python3 - <<'PYEOF'
import tomllib, pathlib, sys
try:
    d = tomllib.load(open("pyproject.toml", "rb"))
    members = d.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    import glob
    pkgs = []
    for pattern in members:
        for path in sorted(glob.glob(pattern)):
            pt = pathlib.Path(path) / "pyproject.toml"
            if pt.exists():
                sub = tomllib.load(open(pt, "rb"))
                name = sub.get("project", {}).get("name", "")
                if name:
                    pkgs.append(name)
    print("\n".join(pkgs))
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
PYEOF
    )
fi

[[ ${#PACKAGES[@]} -eq 0 ]] && err "No packages found. Use --only or set DEFAULT_PACKAGES."

# ── Verify uv is available ────────────────────────────────────────────────────
command -v uv &>/dev/null || err "'uv' not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
UV_VERSION="$(uv --version 2>&1 | head -1)"

# ── Token — secure read (no CLI arg, no history leakage) ──────────────────────
if ! $DRY_RUN; then
    if [[ -z "${PYPI_TOKEN:-}" ]]; then
        if $TEST_PYPI; then
            read -r -s -p "[publish] TestPyPI token (pypi-...): " PYPI_TOKEN; echo
        else
            read -r -s -p "[publish] PyPI token (pypi-...): " PYPI_TOKEN; echo
        fi
    fi
    [[ -z "${PYPI_TOKEN:-}" ]] && err "No token provided. Set PYPI_TOKEN env var or enter interactively."
    [[ "$PYPI_TOKEN" == pypi-* ]] || warn "Token does not start with 'pypi-' — double-check format"
fi

# ── Summary header ────────────────────────────────────────────────────────────
header "Build + Publish"
info "uv      : $UV_VERSION"
info "Repo    : $REPO_ROOT"
info "Packages: ${PACKAGES[*]}"
$TEST_PYPI && info "Target  : TestPyPI" || info "Target  : PyPI (production)"
$DRY_RUN   && warn  "DRY-RUN — build only, no upload"

# ── Git state check ───────────────────────────────────────────────────────────
header "Git state"
if command -v git &>/dev/null && git rev-parse --git-dir &>/dev/null; then
    DIRTY="$(git status --porcelain | wc -l | tr -d ' ')"
    BRANCH="$(git rev-parse --abbrev-ref HEAD)"
    SHA="$(git rev-parse --short HEAD)"
    info "Branch  : $BRANCH @ $SHA"
    [[ "$DIRTY" -gt 0 ]] \
        && warn "$DIRTY uncommitted change(s) — consider committing first" \
        || ok "Working tree clean"
else
    warn "Not a git repo — skipping git checks"
fi

# ── Build ─────────────────────────────────────────────────────────────────────
header "Build"

rm -rf dist/
mkdir -p dist/

for pkg in "${PACKAGES[@]}"; do
    info "Building: $pkg"
    uv build --package "$pkg" || err "Build failed for $pkg"
    ok "Built: $pkg"
done

# Verify artifacts
ARTIFACT_COUNT="$(ls dist/*.whl dist/*.tar.gz 2>/dev/null | wc -l | tr -d ' ')"
[[ "$ARTIFACT_COUNT" -eq 0 ]] && err "No artifacts in dist/ after build"
ok "$ARTIFACT_COUNT artifact(s) ready in dist/"
ls dist/ | sed 's/^/    /'

# ── Upload ────────────────────────────────────────────────────────────────────
header "Upload"

if $DRY_RUN; then
    warn "DRY-RUN — skipping upload. Would run:"
    if $TEST_PYPI; then
        echo "  uv publish dist/* --publish-url https://test.pypi.org/legacy/ --token pypi-***"
    else
        echo "  uv publish dist/* --token pypi-***"
    fi
else
    if $TEST_PYPI; then
        uv publish dist/* \
            --publish-url "https://test.pypi.org/legacy/" \
            --token "$PYPI_TOKEN"
    else
        uv publish dist/* --token "$PYPI_TOKEN"
    fi
    ok "Published ${#PACKAGES[@]} package(s)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${_BOLD}[publish] ══ Done ══${_RESET}"
for pkg in "${PACKAGES[@]}"; do
    if $DRY_RUN; then
        echo "  $pkg  (dry-run, not uploaded)"
    elif $TEST_PYPI; then
        echo "  https://test.pypi.org/project/$pkg/"
    else
        echo "  https://pypi.org/project/$pkg/"
    fi
done
echo ""
