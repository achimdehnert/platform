#!/usr/bin/env bash
# docu-audit.sh — Documentation Health Score Calculator (ADR-158)
#
# Usage: bash docu-audit.sh [repo-path] [--json] [--fail-under SCORE]
#
# Options:
#   repo-path      Path to repo (default: current directory)
#   --json         Output as JSON (for CI/dev-hub Health Score API)
#   --fail-under   Exit 1 if Health Score below SCORE (0-100)
#
# Exit-Codes:
#   0  Audit passed
#   1  Health Score below --fail-under threshold
#   2  Critical error (repo path not found)

set -euo pipefail

# --- Argument Parsing ---
REPO_PATH="."
OUTPUT_JSON=false
FAIL_UNDER=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      OUTPUT_JSON=true
      shift
      ;;
    --fail-under)
      FAIL_UNDER="${2:?'--fail-under expects a value'}"
      shift 2
      ;;
    -*)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
    *)
      REPO_PATH="$1"
      shift
      ;;
  esac
done

if [[ ! -d "${REPO_PATH}" ]]; then
  echo "ERROR: Repo path not found: ${REPO_PATH}" >&2
  exit 2
fi

REPO_PATH="$(cd "$REPO_PATH" && pwd)"
REPO_NAME="$(basename "$REPO_PATH")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

score=0
max_score=0

check() {
    local weight=$1
    local label=$2
    local pass=$3
    max_score=$((max_score + weight))
    if [[ "$pass" == "1" ]]; then
        score=$((score + weight))
        printf "  ${GREEN}✅${NC} %-45s ${GREEN}+%d${NC}\n" "$label" "$weight"
    else
        printf "  ${RED}❌${NC} %-45s ${RED}+0${NC} (max %d)\n" "$label" "$weight"
    fi
}

partial() {
    local weight=$1
    local label=$2
    local earned=$3
    max_score=$((max_score + weight))
    score=$((score + earned))
    if [[ "$earned" -eq "$weight" ]]; then
        printf "  ${GREEN}✅${NC} %-45s ${GREEN}+%d${NC}\n" "$label" "$earned"
    elif [[ "$earned" -gt 0 ]]; then
        printf "  ${YELLOW}⚠️${NC}  %-45s ${YELLOW}+%d${NC}/%d\n" "$label" "$earned" "$weight"
    else
        printf "  ${RED}❌${NC} %-45s ${RED}+0${NC}/%d\n" "$label" "$weight"
    fi
}

echo ""
echo "═══════════════════════════════════════════════"
printf " Documentation Health Audit: ${BOLD}%s${NC}\n" "$REPO_NAME"
echo "═══════════════════════════════════════════════"
echo ""

# --- 1. README.md (10 points) ---
printf "${BOLD}📄 Essential Files${NC}\n"
if [[ -f "$REPO_PATH/README.md" ]]; then
    readme_chars=$(wc -c < "$REPO_PATH/README.md")
    if [[ "$readme_chars" -gt 500 ]]; then
        check 10 "README.md (${readme_chars} chars, >500)" 1
    else
        partial 10 "README.md (${readme_chars} chars, needs >500)" 5
    fi
else
    check 10 "README.md exists" 0
fi

# --- 2. CORE_CONTEXT.md (10 points) ---
if [[ -f "$REPO_PATH/CORE_CONTEXT.md" ]] || [[ -f "$REPO_PATH/docs/CORE_CONTEXT.md" ]]; then
    check 10 "CORE_CONTEXT.md" 1
else
    check 10 "CORE_CONTEXT.md" 0
fi

# --- 3. ADRs (10 points) ---
echo ""
printf "${BOLD}📐 Architecture Decision Records${NC}\n"
adr_count=0
if [[ -d "$REPO_PATH/docs/adr" ]]; then
    adr_count=$(find "$REPO_PATH/docs/adr" -maxdepth 1 -name "ADR-*.md" 2>/dev/null | wc -l)
fi
if [[ "$adr_count" -gt 0 ]]; then
    check 10 "docs/adr/ with ${adr_count} ADR(s)" 1
else
    check 10 "docs/adr/ with ≥1 ADR" 0
fi

# --- 4. DIATAXIS Structure (15 points) ---
echo ""
printf "${BOLD}📂 DIATAXIS Structure${NC}\n"
diataxis_score=0
diataxis_total=0
for quad in tutorials guides reference explanation; do
    dir="$REPO_PATH/docs/$quad"
    if [[ -d "$dir" ]]; then
        file_count=$(find "$dir" -name "*.md" 2>/dev/null | wc -l)
        if [[ "$file_count" -gt 0 ]]; then
            printf "  ${GREEN}✅${NC} docs/%-15s (%d files)\n" "$quad/" "$file_count"
            diataxis_score=$((diataxis_score + 1))
        else
            printf "  ${YELLOW}⚠️${NC}  docs/%-15s (empty)\n" "$quad/"
        fi
    else
        printf "  ${RED}❌${NC} docs/%-15s (missing)\n" "$quad/"
    fi
    diataxis_total=$((diataxis_total + 1))
done
# adr/ counts as explanation quadrant
if [[ -d "$REPO_PATH/docs/adr" ]] && [[ "$adr_count" -gt 0 ]]; then
    if [[ ! -d "$REPO_PATH/docs/explanation" ]]; then
        diataxis_score=$((diataxis_score + 1))
        printf "  ${GREEN}✅${NC} docs/adr/ counts as explanation quadrant\n"
    fi
fi
diataxis_earned=0
if [[ "$diataxis_score" -ge 4 ]]; then
    diataxis_earned=15
elif [[ "$diataxis_score" -ge 3 ]]; then
    diataxis_earned=10
elif [[ "$diataxis_score" -ge 2 ]]; then
    diataxis_earned=5
fi
partial 15 "DIATAXIS (${diataxis_score}/4 quadrants)" "$diataxis_earned"

# --- 5. Docstring Coverage (20 points, AST-based) ---
# Measures the *documentable semantic surface*, not boilerplate, and does
# not reward filler. Replaces the old grep heuristic (triple-quote lines/2,
# which scored 1-line docstrings as 0 and rewarded multi-line formatting).
#
# Denominator excludes scaffolding that shouldn't need prose: Django Meta /
# Migration classes, __dunder__ methods, test_* functions, @overload stubs,
# and property setters/deleters. A docstring only *counts* if it is
# non-trivial (>= 2 words and >= 8 non-space chars) so "Num."-style filler
# cannot inflate the score. Layout-agnostic: falls back to the repo root
# when apps/src/packages are absent, and prunes junk dirs.
echo ""
printf "${BOLD}📝 Docstring Coverage${NC}\n"
read -r py_with_doc py_total < <(
python3 - "$REPO_PATH" <<'PYEOF' 2>/dev/null || echo "0 0"
import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
PRUNE = {".git", ".venv", "venv", "node_modules", "build", "dist",
         ".tox", ".mypy_cache", ".pytest_cache", "__pycache__", "migrations"}

bases = [root / b for b in ("apps", "src", "packages") if (root / b).is_dir()]
if not bases:
    bases = [root]

def is_overload(node):
    for d in node.decorator_list:
        t = d.func if isinstance(d, ast.Call) else d
        name = getattr(t, "attr", None) or getattr(t, "id", None)
        if name in ("overload", "setter", "deleter"):
            return True
    return False

def nontrivial(doc):
    if not doc:
        return False
    txt = doc.strip()
    return len(txt.replace(" ", "")) >= 8 and len(txt.split()) >= 2

documented = total = 0
seen = set()
for base in bases:
    for p in base.rglob("*.py"):
        if PRUNE & set(p.parts) or p.name == "__init__.py":
            continue
        rp = p.resolve()
        if rp in seen:                       # base overlap (root + nested)
            continue
        seen.add(rp)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, ValueError):
            continue
        for n in ast.walk(tree):
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.ClassDef)):
                continue
            nm = n.name
            if isinstance(n, ast.ClassDef):
                if nm in ("Meta",) or nm.endswith("Migration"):
                    continue
            else:
                if nm.startswith("test_") or (
                    nm.startswith("__") and nm.endswith("__")
                ) or is_overload(n):
                    continue
            total += 1
            if nontrivial(ast.get_docstring(n)):
                documented += 1
print(f"{documented} {total}")
PYEOF
)
py_with_doc=${py_with_doc:-0}
py_total=${py_total:-0}

if [[ "$py_total" -gt 0 ]]; then
    coverage=$((py_with_doc * 100 / py_total))
    coverage_earned=0
    if [[ "$coverage" -ge 80 ]]; then
        coverage_earned=20
    elif [[ "$coverage" -ge 60 ]]; then
        coverage_earned=15
    elif [[ "$coverage" -ge 40 ]]; then
        coverage_earned=10
    elif [[ "$coverage" -ge 20 ]]; then
        coverage_earned=5
    fi
    partial 20 "Docstring coverage ~${coverage}% (${py_with_doc}/${py_total})" "$coverage_earned"
else
    printf "  ${YELLOW}⚠️${NC}  No Python files found to scan\n"
    partial 20 "Docstring coverage (no Python)" 0
fi

# --- 6. Reference-Docs freshness (15 points) ---
echo ""
printf "${BOLD}📚 Reference Documentation${NC}\n"
ref_dir="$REPO_PATH/docs/reference"
if [[ -d "$ref_dir" ]]; then
    ref_count=$(find "$ref_dir" -name "*.md" 2>/dev/null | wc -l)
    if [[ "$ref_count" -gt 0 ]]; then
        newest=$(find "$ref_dir" -name "*.md" -printf '%T@\n' 2>/dev/null | sort -rn | head -1)
        now=$(date +%s)
        age_days=$(( (now - ${newest%.*}) / 86400 ))
        if [[ "$age_days" -le 7 ]]; then
            check 15 "Reference-Docs (${ref_count} files, ${age_days}d old)" 1
        else
            partial 15 "Reference-Docs (${ref_count} files, ${age_days}d old, >7d)" 8
        fi
    else
        check 15 "Reference-Docs (dir exists but empty)" 0
    fi
else
    check 15 "docs/reference/ exists" 0
fi

# --- 7. audience.yaml (10 points) ---
echo ""
printf "${BOLD}🎯 Audience Configuration${NC}\n"
if [[ -f "$REPO_PATH/docs/audience.yaml" ]]; then
    check 10 "audience.yaml configured" 1
else
    check 10 "docs/audience.yaml" 0
fi

# --- 8. No banned files (10 points) ---
echo ""
printf "${BOLD}🚫 ADR-046 Violations${NC}\n"
violations=0
if [[ -d "$REPO_PATH/docs" ]]; then
    # R-04-Ausnahmen (ADR-046 Amendment 2026-07-09): Vorlagen unter docs/templates/
    # und konsumierte ADR-Inputs unter docs/adr/inputs/ — konsistent mit
    # scripts/hardcode_scanner.py (exclude_dirs). conf.py bleibt die Alt-Ausnahme.
    py_in_docs=$(find "$REPO_PATH/docs" -name "*.py" ! -name "conf.py" \
        -not -path "*/templates/*" -not -path "*/adr/inputs/*" 2>/dev/null | wc -l)
    bin_in_docs=$(find "$REPO_PATH/docs" -name "*.pdf" -o -name "*.docx" -o -name "*.zip" 2>/dev/null | wc -l)
    build_in_docs=$(find "$REPO_PATH/docs" -type d -name "_build" -o -name "build" 2>/dev/null | wc -l)
    violations=$((py_in_docs + bin_in_docs + build_in_docs))
    [[ "$py_in_docs" -gt 0 ]] && printf "  ${RED}❌${NC} %d .py files in docs/ (R-04)\n" "$py_in_docs"
    [[ "$bin_in_docs" -gt 0 ]] && printf "  ${RED}❌${NC} %d binary files in docs/ (R-02)\n" "$bin_in_docs"
    [[ "$build_in_docs" -gt 0 ]] && printf "  ${RED}❌${NC} %d build dirs in docs/ (R-03)\n" "$build_in_docs"
fi
if [[ "$violations" -eq 0 ]]; then
    check 10 "No banned files in docs/" 1
else
    check 10 "No banned files (${violations} violations)" 0
fi

# --- Final Score ---
pct=$((score * 100 / max_score))

if [[ "$OUTPUT_JSON" == "true" ]]; then
    # JSON output for CI/dev-hub API
    cat <<EOF
{
  "repo_path": "${REPO_PATH}",
  "repo_name": "${REPO_NAME}",
  "total_score": ${pct},
  "score_raw": ${score},
  "score_max": ${max_score},
  "metrics": {
    "readme_present": $(( readme_chars > 500 ? 1 : 0 )),
    "core_context_present": $([[ -f "$REPO_PATH/CORE_CONTEXT.md" || -f "$REPO_PATH/docs/CORE_CONTEXT.md" ]] && echo 1 || echo 0),
    "adr_present": $(( adr_count > 0 ? 1 : 0 )),
    "diataxis_quadrants": ${diataxis_score},
    "docstring_coverage_pct": ${coverage:-0},
    "reference_docs_present": $([[ -d "$REPO_PATH/docs/reference" ]] && echo 1 || echo 0),
    "audience_yaml_configured": $([[ -f "$REPO_PATH/docs/audience.yaml" ]] && echo 1 || echo 0),
    "banned_file_violations": ${violations}
  }
}
EOF
else
    echo ""
    echo "═══════════════════════════════════════════════"
    if [[ "$pct" -ge 70 ]]; then
        color="$GREEN"
        grade="GOOD"
    elif [[ "$pct" -ge 50 ]]; then
        color="$YELLOW"
        grade="NEEDS IMPROVEMENT"
    else
        color="$RED"
        grade="POOR"
    fi
    printf " ${BOLD}Documentation Health Score:${NC} ${color}${BOLD}%d/%d (%d%%) — %s${NC}\n" "$score" "$max_score" "$pct" "$grade"
    echo "═══════════════════════════════════════════════"
    echo ""
fi

# --- Exit-Code based on --fail-under ---
if [[ "$FAIL_UNDER" -gt 0 ]] && [[ "$pct" -lt "$FAIL_UNDER" ]]; then
    [[ "$OUTPUT_JSON" != "true" ]] && echo "FAIL: Health Score ${pct}% < --fail-under ${FAIL_UNDER}%" >&2
    exit 1
fi
