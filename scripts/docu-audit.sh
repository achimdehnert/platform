#!/usr/bin/env bash
# docu-audit.sh — Documentation Health Score Calculator (ADR-158)
# Usage: bash docu-audit.sh [repo-path]
# Example: bash docu-audit.sh /home/devuser/github/risk-hub
#          bash docu-audit.sh .  (current directory)

set -euo pipefail

REPO_PATH="${1:-.}"
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

# --- 5. Docstring Coverage (20 points, estimated) ---
echo ""
printf "${BOLD}📝 Docstring Coverage (estimate)${NC}\n"
py_total=0
py_with_doc=0
for pydir in "$REPO_PATH/apps" "$REPO_PATH/src" "$REPO_PATH/packages"; do
    if [[ -d "$pydir" ]]; then
        while IFS= read -r pyfile; do
            # Count classes and functions
            total_in_file=$(grep -cE "^[[:space:]]*(class |def )" "$pyfile" 2>/dev/null || true)
            total_in_file=${total_in_file:-0}
            # Count those followed by a docstring (triple-quote on next meaningful line)
            doc_in_file=$(grep -cE '"""' "$pyfile" 2>/dev/null || true)
            doc_in_file=${doc_in_file:-0}
            doc_in_file=$((doc_in_file / 2))  # pair of triple-quotes = 1 docstring
            py_total=$((py_total + total_in_file))
            py_with_doc=$((py_with_doc + doc_in_file))
        done < <(find "$pydir" -name "*.py" -not -path "*/migrations/*" -not -name "__init__.py" 2>/dev/null)
    fi
done

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
    py_in_docs=$(find "$REPO_PATH/docs" -name "*.py" ! -name "conf.py" 2>/dev/null | wc -l)
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
echo ""
echo "═══════════════════════════════════════════════"
pct=$((score * 100 / max_score))
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
