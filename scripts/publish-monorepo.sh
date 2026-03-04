#!/usr/bin/env bash
# =============================================================================
# publish-monorepo.sh — uv-workspace PyPI build + publish for monorepos
# Source: achimdehnert/platform/scripts/publish-monorepo.sh
# =============================================================================
#
# KEY FEATURE: --set-version <ver> sets version in pyproject.toml automatically.
# This means you NEVER need to manually bump pyproject.toml before tagging.
#
# USAGE:
#   bash scripts/publish-monorepo.sh                              # all packages
#   bash scripts/publish-monorepo.sh --only nl2cad-core           # single package
#   bash scripts/publish-monorepo.sh --only nl2cad-core,nl2cad-areas
#   bash scripts/publish-monorepo.sh --set-version 0.2.0          # auto-bump version
#   bash scripts/publish-monorepo.sh --dry-run                    # build only, no upload
#   bash scripts/publish-monorepo.sh --test                       # upload to TestPyPI
#   PYPI_TOKEN=pypi-xxx bash scripts/publish-monorepo.sh          # non-interactive CI
#
# TOKEN: never pass as CLI argument — use env var or interactive prompt.
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

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_PACKAGES=()

# ── Argument parsing ──────────────────────────────────────────────────────────
TEST_PYPI=false
DRY_RUN=false
ONLY_PACKAGES=""
SET_VERSION=""
# Root packages: live in repo root (not packages/ subdir) — comma-separated
ROOT_PACKAGES=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --test)         TEST_PYPI=true; shift ;;
        --dry-run)      DRY_RUN=true;   shift ;;
        --set-version)
            [[ -z "${2:-}" ]] && err "--set-version requires a version argument"
            SET_VERSION="$2"; shift 2 ;;
        --set-version=*) SET_VERSION="${1#--set-version=}"; shift ;;
        --root-packages)
            [[ -z "${2:-}" ]] && err "--root-packages requires a comma-separated list"
            ROOT_PACKAGES="$2"; shift 2 ;;
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
    mapfile -t PACKAGES < <(
        python3 - <<'PYEOF'
import tomllib, pathlib, glob, sys
try:
    d = tomllib.load(open("pyproject.toml", "rb"))
    members = d.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    pkgs = []
    for pattern in members:
        for path in sorted(glob.glob(pattern)):
            pt = pathlib.Path(path) / "pyproject.toml"
            if pt.exists():
                sub = tomllib.load(open(pt, "rb"))
                name = sub.get("project", {}).get("name", "")
                if name:
                    pkgs.append(name)
    # Also include root package if it has a name
    root_name = d.get("project", {}).get("name", "")
    if root_name and root_name not in pkgs:
        pkgs.append(root_name)
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

# ── Token ─────────────────────────────────────────────────────────────────────
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

# ── Header ────────────────────────────────────────────────────────────────────
header "Build + Publish"
info "uv      : $UV_VERSION"
info "Repo    : $REPO_ROOT"
info "Packages: ${PACKAGES[*]}"
[[ -n "$SET_VERSION" ]] && info "Version : $SET_VERSION (set from --set-version)"
$TEST_PYPI && info "Target  : TestPyPI" || info "Target  : PyPI (production)"
$DRY_RUN   && warn  "DRY-RUN — build only, no upload"

# ── Git state ─────────────────────────────────────────────────────────────────
header "Git state"
if command -v git &>/dev/null && git rev-parse --git-dir &>/dev/null; then
    DIRTY="$(git status --porcelain | wc -l | tr -d ' ')"
    info "Branch  : $(git rev-parse --abbrev-ref HEAD) @ $(git rev-parse --short HEAD)"
    [[ "$DIRTY" -gt 0 ]] \
        && warn "$DIRTY uncommitted change(s)" \
        || ok "Working tree clean"
fi

# ── Set version (if requested) ────────────────────────────────────────────────
if [[ -n "$SET_VERSION" ]]; then
    header "Version bump → $SET_VERSION"
    for pkg in "${PACKAGES[@]}"; do
        if echo ",$ROOT_PACKAGES," | grep -q ",$pkg,"; then
            uv version "$SET_VERSION"
        else
            uv version --package "$pkg" "$SET_VERSION"
        fi
        ok "Set $pkg → $SET_VERSION"
    done
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

ARTIFACT_COUNT="$(ls dist/*.whl dist/*.tar.gz 2>/dev/null | wc -l | tr -d ' ')"
[[ "$ARTIFACT_COUNT" -eq 0 ]] && err "No artifacts in dist/ after build"
ok "$ARTIFACT_COUNT artifact(s) ready in dist/"
ls dist/ | sed 's/^/    /'

# ── Upload ────────────────────────────────────────────────────────────────────
header "Upload"
if $DRY_RUN; then
    warn "DRY-RUN — skipping upload. Would run:"
    $TEST_PYPI \
        && echo "  uv publish dist/* --publish-url https://test.pypi.org/legacy/ --token pypi-***" \
        || echo "  uv publish dist/* --token pypi-***"
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
