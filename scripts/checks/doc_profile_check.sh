#!/usr/bin/env bash
# ADR-218 — Doc-Profile-Konformitätscheck.
#
# Invariante: Jedes Repo mit <repo>/docs/doc-profile.yaml deklariert ein
# Plattform-bekanntes Profil. Aus Profil + Repo-Vars folgt ein Pflicht-Tier-
# Katalog. Dieser Check verifiziert, dass alle required-Tiers existieren
# und mind. den im Schema definierten Inhalt haben.
#
# Exit 0 = alle deklarierten Repos konform (oder kein Profil deklariert).
# Exit 1 = mindestens ein Verstoß. Exit 2 = Setup-/Parsefehler.
#
# Repos ohne doc-profile.yaml werden ÜBERSPRUNGEN (kein Vacuous Pass —
# sondern keine Pflicht). Migration ist repo-by-repo, kein Big-Bang.
#
# Reine bash + python3/pyyaml (kein yq).
set -euo pipefail

GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTRY="$REPO_ROOT/registry/repos.yaml"
SCHEMA="$REPO_ROOT/docs/conventions/doc-profile-schema.yaml"

STRICT=0
USE_REMOTE_MAIN=0
SINGLE_REPO=""
for arg in "$@"; do
  case "$arg" in
    --strict) STRICT=1 ;;
    --main)   USE_REMOTE_MAIN=1 ;;
    --repo=*) SINGLE_REPO="${arg#--repo=}" ;;
    -h|--help)
      cat <<EOF
Usage: $0 [--strict] [--main] [--repo=<name>]
  --strict   Repos ohne doc-profile.yaml als FAIL (Default: WARN).
  --main     Quelle origin/main statt Working-Tree (CI-Sicht).
  --repo=X   Nur Repo X prüfen statt alle aus registry/repos.yaml.
EOF
      exit 0 ;;
  esac
done

[[ -f "$REGISTRY" ]] || { echo "FATAL: $REGISTRY fehlt"; exit 2; }
[[ -f "$SCHEMA" ]]   || { echo "FATAL: $SCHEMA fehlt"; exit 2; }
command -v python3 >/dev/null || { echo "FATAL: python3 nötig"; exit 2; }

# --- Repo-Liste ermitteln ---------------------------------------------------
if [[ -n "$SINGLE_REPO" ]]; then
  REPOS=("$SINGLE_REPO")
else
  mapfile -t REPOS < <(python3 - "$REGISTRY" <<'PY'
import sys, yaml
doc = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
seen = set()
for d in doc.get("domains", []) or []:
    for s in d.get("systems", []) or []:
        r = s.get("repo")
        if r and r not in seen:
            seen.add(r); print(r)
PY
  ) || { echo "FATAL: registry/repos.yaml nicht parsebar"; exit 2; }
fi

# --- Header -----------------------------------------------------------------
printf '%-22s %-14s %-20s %s\n' "REPO" "PROFIL" "MISSING_TIERS" "STATUS"
printf '%s\n' "--------------------------------------------------------------------------------------------"

fail=0 warn=0 checked=0 skipped=0 conform=0

# --- Pro Repo ---------------------------------------------------------------
for repo in "${REPOS[@]}"; do
  repo_dir="$GITHUB_DIR/$repo"
  profile_file="$repo_dir/docs/doc-profile.yaml"

  if [[ ! -d "$repo_dir" ]]; then
    printf '%-22s %-14s %-20s %s\n' "$repo" "—" "—" "skipped: not-checked-out"
    ((skipped++)) || true
    continue
  fi

  if [[ ! -f "$profile_file" ]]; then
    if [[ $STRICT -eq 1 ]]; then
      printf '%-22s %-14s %-20s %s\n' "$repo" "—" "—" "FAIL: no doc-profile.yaml (--strict)"
      ((fail++)) || true
    else
      printf '%-22s %-14s %-20s %s\n' "$repo" "—" "—" "skip: no doc-profile.yaml"
      ((skipped++)) || true
    fi
    continue
  fi

  # --- Konformitäts-Check via Python ---------------------------------------
  result=$(python3 - "$SCHEMA" "$profile_file" "$repo_dir" <<'PY'
import sys, yaml, os, pathlib

schema_p, profile_p, repo_dir = sys.argv[1:4]
schema = yaml.safe_load(open(schema_p, encoding="utf-8"))
prof   = yaml.safe_load(open(profile_p, encoding="utf-8"))

profile_name = prof.get("profile")
if not profile_name:
    print(f"FAIL:no-profile-field:")
    sys.exit(0)

profiles = schema.get("profiles", {})
if profile_name not in profiles:
    print(f"FAIL:unknown-profile:{profile_name}")
    sys.exit(0)

tier_defs = schema.get("tiers", {})
pflicht   = profiles[profile_name].get("pflicht", {})
overrides = prof.get("overrides", {}) or {}

# Conditional-Evaluator (sehr einfache Subset-Sprache).
def eval_cond(cond: str, ctx: dict) -> bool:
    # Unterstützt: 'a.b == "x"', 'a.b == true', 'a.b contains "x"'
    if " == " in cond:
        left, right = cond.split(" == ", 1)
        val = ctx
        for p in left.strip().split("."):
            val = (val or {}).get(p) if isinstance(val, dict) else None
        right = right.strip().strip("'\"")
        if right == "true":  right_v = True
        elif right == "false": right_v = False
        else: right_v = right
        return val == right_v
    if " contains " in cond:
        left, right = cond.split(" contains ", 1)
        val = ctx
        for p in left.strip().split("."):
            val = (val or {}).get(p) if isinstance(val, dict) else None
        right = right.strip().strip("'\"")
        if isinstance(val, list): return right in val
        if isinstance(val, str):  return right in val
        return False
    return False

def check_min_inhalt_rule(rule: dict, path: pathlib.Path) -> str | None:
    """Return error string or None if rule passes. Returns None if file missing."""
    if not path.is_file():
        return None  # existence already checked separately
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"unreadable"
    rule_type = rule.get("type", "")
    if rule_type == "heading_count":
        count = sum(1 for ln in text.splitlines() if ln.startswith("## ") or ln.startswith("### "))
        mn = int(rule.get("min", 1))
        return None if count >= mn else f"heading_count={count}<{mn}"
    if rule_type == "table_rows":
        rows = [ln for ln in text.splitlines()
                if ln.strip().startswith("|") and not set(ln.replace("|","").replace("-","").replace(" ","")) == set()]
        # subtract header row (first |…| line)
        data_rows = max(0, len(rows) - 1)
        mn = int(rule.get("min", 1))
        return None if data_rows >= mn else f"table_rows={data_rows}<{mn}"
    if rule_type == "lines":
        count = sum(1 for ln in text.splitlines() if ln.strip())
        mn = int(rule.get("min", 1))
        return None if count >= mn else f"lines={count}<{mn}"
    if rule_type == "frontmatter_status":
        # Check YAML frontmatter (--- ... ---) for status field
        required_val = rule.get("required_value", "ready")
        lines = text.splitlines()
        if lines and lines[0].strip() == "---":
            fm_lines = []
            for ln in lines[1:]:
                if ln.strip() == "---":
                    break
                fm_lines.append(ln)
            try:
                import yaml as _yaml
                fm = _yaml.safe_load("\n".join(fm_lines)) or {}
                actual = fm.get("status", "")
                if actual != required_val:
                    return f"status={repr(actual)!s}!={repr(required_val)}"
                return None
            except Exception:
                return "frontmatter-parse-error"
        return f"no-frontmatter (need status:{required_val})"
    return None  # unknown rule type → skip

missing = []
content_fails = []

for tier, req in pflicht.items():
    if isinstance(req, dict):
        status = req.get("status", "required")
        cond   = req.get("condition")
        if status == "conditional" and cond and not eval_cond(cond, prof):
            continue  # condition false → tier nicht pflicht
        status_eff = "required" if status in ("required", "conditional") else status
    else:
        status_eff = req

    if status_eff != "required":
        continue

    # Override aus Repo-Profil zulässt Wegfall mit Begründung
    ov = overrides.get(tier)
    if ov and isinstance(ov, dict) and ov.get("status") == "na" and ov.get("reason"):
        continue

    tdef = tier_defs.get(tier, {})
    path = tdef.get("pflicht_pfad")
    if not path:
        continue
    full = pathlib.Path(repo_dir) / path
    if path.endswith("/"):
        if not full.is_dir() or not any(full.iterdir()):
            missing.append(tier)
    else:
        if not full.is_file():
            missing.append(tier)
        else:
            # Inhalt-Verifikation via min_inhalt_rule (ADR-218 OQ-1, Rev 2)
            rule = tdef.get("min_inhalt_rule")
            if rule and isinstance(rule, dict):
                err = check_min_inhalt_rule(rule, full)
                if err:
                    content_fails.append(f"{tier}:{err}")

all_fails = missing + content_fails
if all_fails:
    if missing and content_fails:
        print(f"FAIL:missing-and-content:{profile_name}:{','.join(missing)}|content:{','.join(content_fails)}")
    elif missing:
        print(f"FAIL:missing-tiers:{profile_name}:{','.join(missing)}")
    else:
        print(f"FAIL:content-check:{profile_name}::{','.join(content_fails)}")
else:
    print(f"OK::{profile_name}:")
PY
  )

  outcome="${result%%:*}"
  rest="${result#*:}"
  detail="${rest#*:}"
  profile="${detail%%:*}"
  miss="${detail#*:}"

  case "$outcome" in
    OK)
      printf '%-22s %-14s %-20s %s\n' "$repo" "$profile" "—" "✓ konform"
      ((conform++)) || true
      ((checked++)) || true
      ;;
    FAIL)
      reason="${rest%%:*}"
      case "$reason" in
        no-profile-field)
          printf '%-22s %-14s %-20s %s\n' "$repo" "—" "—" "FAIL: doc-profile.yaml ohne 'profile:'-Feld"
          ;;
        unknown-profile)
          printf '%-22s %-14s %-20s %s\n' "$repo" "$profile" "—" "FAIL: Profil unbekannt"
          ;;
        missing-tiers)
          # Sanity-Cut: max 3 tiers in der Spalte zeigen
          mshow="$miss"
          if [[ ${#mshow} -gt 18 ]]; then mshow="${mshow:0:15}…"; fi
          printf '%-22s %-14s %-20s %s\n' "$repo" "$profile" "$mshow" "FAIL: $miss"
          ;;
        content-check)
          cshow="${miss:0:18}"
          if [[ ${#miss} -gt 18 ]]; then cshow="${cshow}…"; fi
          printf '%-22s %-14s %-20s %s\n' "$repo" "$profile" "$cshow" "FAIL(inhalt): $miss"
          ;;
        missing-and-content)
          printf '%-22s %-14s %-20s %s\n' "$repo" "$profile" "—" "FAIL(missing+inhalt): $miss"
          ;;
        *)
          printf '%-22s %-14s %-20s %s\n' "$repo" "—" "—" "FAIL: $reason"
          ;;
      esac
      ((fail++)) || true
      ((checked++)) || true
      ;;
    *)
      printf '%-22s %-14s %-20s %s\n' "$repo" "—" "—" "ERROR: unparsable result '$result'"
      ((fail++)) || true
      ;;
  esac
done

# --- Summary ----------------------------------------------------------------
printf '%s\n' "--------------------------------------------------------------------------------------------"
printf 'Summary: %d checked · %d conform · %d failed · %d skipped (no doc-profile.yaml)\n' \
  "$checked" "$conform" "$fail" "$skipped"

if [[ $fail -gt 0 ]]; then
  echo ""
  echo "Hinweis: doc-profile.yaml-Schema siehe docs/conventions/doc-profile-schema.yaml"
  echo "         ADR-218 für Konvention; --strict um Repos ohne Profil zu rügen."
  exit 1
fi
exit 0
