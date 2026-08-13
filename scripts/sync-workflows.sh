#!/usr/bin/env bash
# sync-workflows.sh — Platform Workflows als Symlinks in alle Repos verteilen
#
# Single Source of Truth: platform/.windsurf/workflows/
# Repos bekommen Symlinks statt Kopien → immer aktuell.
#
# Usage:
#   ./scripts/sync-workflows.sh           # Alle Repos
#   ./scripts/sync-workflows.sh --dry-run # Nur anzeigen, nichts ändern
#   ./scripts/sync-workflows.sh risk-hub  # Nur ein Repo
#
# Kategorien:
#   UNIVERSAL   — Jedes Repo bekommt diese Workflows
#   DJANGO_HUB  — Nur Django-Hubs (deploybare Services)
#   PACKAGE     — Nur Python-Packages (PyPI)
#   PLATFORM    — Nur platform selbst (bleiben dort)

set -euo pipefail

GITHUB_DIR="${GITHUB_DIR:-$HOME/github}"
PLATFORM_WF="${GITHUB_DIR}/platform/.windsurf/workflows"
DRY_RUN=false
STRICT=false
SINGLE_REPO=""

# SKIP-Längsaggregation (ADR-265 REC-1): sammelt Repo-Namen, die SKIP-REPO
# (Ignore-Guard) bzw. SKIP-TRACKED (Tracked-Guard) ausgelöst haben, für die
# Schluss-Summary-Zeile. Rein additiv — ändert das Guard-Verhalten selbst nicht.
SKIP_REPO_NAMES=()
SKIP_TRACKED_NAMES=()

# --- Workflow-Kategorien ---

# Jedes Repo bekommt diese
UNIVERSAL=(
    knowledge-capture
    agent-session-start
    agentic-coding
    adr
    adr-review
    pr-review
    governance-check
    repo-health-check
    hotfix
    windsurf-clean
    workflow-index
    sync-repo
    use-case
    session-start
    session-ende
    session-docu
    docu-update
    complete
    prompt
    drift-check
    docu-repo-active
    teste-repo
    sync-project-facts
    secrets
    onboarding-new-repo
    pre-code
    process-agent-queue
    create-pdf
)

# Nur Django-Hubs (deploybare Services mit Docker)
DJANGO_HUB=(
    deploy
    deploy-check
    backup
    ship
    ship-staging
    run-local
    run-prod
    run-staging
    rollback
    incident
    frontend-ui-test
    pre-release-test
    testing-setup
    testing-conventions
    onboard-repo
    onboard-repo-testing-addendum
    new-github-project
    stack-upgrade
    refresh-github-token
    compose-audit
    nginx-check
    uptime-monitoring
    infra-health
)

# Nur Python-Packages (PyPI)
PACKAGE=(
    release
)

# Nur platform (werden NICHT verteilt — Meta-Repo-spezifisch):
# cascade-auftraege, idea-intake, agent-review, workflow-review,
# docu-repo-all, platform-audit, onboard-stack

# --- Repo-Typen (SSoT: registry/repos.yaml → generierte Flat-View der canonical.yaml) ---
# ADR-275 P1: Migriert von der manuell gepflegten, stalen registry/github_repos.yaml
# auf die gegatete Flat-View (scripts/repo-registry.yaml, aus canonical.yaml generiert).
# Klassifikation nach `type`: django → DJANGO_HUBS, library/framework → PACKAGES.
# Die Zuordnung ist total (unbekannte Typen → weder django noch package = 'other',
# unverändertes bestehendes Verhalten).

REGISTRY="${GITHUB_DIR}/platform/scripts/repo-registry.yaml"

if [[ ! -f "$REGISTRY" ]]; then
    echo "ERROR: Registry nicht gefunden: $REGISTRY" >&2
    exit 1
fi

read -r -a DJANGO_HUBS <<< "$(python3 -c "
import yaml
with open('${REGISTRY}') as f:
    data = yaml.safe_load(f)
repos = data.get('repos', {})
print(' '.join(n for n, v in repos.items() if (v or {}).get('type') == 'django'))
")"

read -r -a PACKAGES <<< "$(python3 -c "
import yaml
with open('${REGISTRY}') as f:
    data = yaml.safe_load(f)
repos = data.get('repos', {})
print(' '.join(n for n, v in repos.items() if (v or {}).get('type') in ('library', 'framework')))
")"

# Alle Registry-Namen — Grundlage fuer den Registry-Guard in sync_repo (s. dort).
#
# Quelle ist die KANONISCHE Registry, nicht die flache View oben: `repo-registry.yaml`
# enthaelt nur Eintraege mit `in_flat` (53 von 59). Der erste Entwurf dieses Guards las
# die View und haette damit `bahn-hub`, `nl2iot-hub` und `testkit` als "nicht
# registriert" aus der Bewertung genommen — registrierte Repos waeren stillschweigend
# aus dem Scan gefallen. Fallback auf die View nur, wenn die kanonische Datei fehlt.
CANON_REGISTRY="${GITHUB_DIR}/platform/registry/canonical.yaml"
read -r -a REGISTRY_REPOS <<< "$(python3 -c "
import yaml, os
quelle = '${CANON_REGISTRY}' if os.path.isfile('${CANON_REGISTRY}') else '${REGISTRY}'
with open(quelle) as f:
    data = yaml.safe_load(f)
print(' '.join((data.get('repos') or {}).keys()))
")"
NOT_REGISTERED_NAMES=()

# --- Parse Args ---

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --strict) STRICT=true ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--strict] [repo-name]"
            echo ""
            echo "Sync platform workflows as symlinks to all repos."
            echo "  --dry-run   Show what would be done, don't change anything"
            echo "  --strict    Exit 1 if any repo was skipped (SKIP-REPO/SKIP-TRACKED)"
            echo "  repo-name   Only sync a single repo"
            exit 0
            ;;
        *) SINGLE_REPO="$arg" ;;
    esac
done

# --- Functions ---

in_array() {
    local needle="$1"; shift
    for item in "$@"; do
        [[ "$item" == "$needle" ]] && return 0
    done
    return 1
}

sync_workflow() {
    local repo_dir="$1"
    local workflow="$2"
    local repo_name
    repo_name=$(basename "$repo_dir")

    local wf_dir="${repo_dir}/.windsurf/workflows"
    local target="${PLATFORM_WF}/${workflow}.md"
    local link="${wf_dir}/${workflow}.md"

    # Source muss existieren
    if [[ ! -f "$target" ]]; then
        echo "  WARN: ${workflow}.md nicht in platform gefunden"
        return
    fi

    # Tracked-Guard (ADR-265): einen im Ziel-Index getrackten Pfad NIE durch einen
    # Symlink ersetzen — das erzeugt permanenten Typechange-Dirt. Erst untracken
    # (git rm --cached, Rollout-Commit), dann synct dieser Lauf ihn.
    if git -C "$repo_dir" ls-files --error-unmatch ".windsurf/workflows/${workflow}.md" >/dev/null 2>&1; then
        echo "  SKIP-TRACKED: ${workflow}.md ist im Index getrackt — erst 'git rm --cached' (ADR-265)"
        return
    fi

    # Zielverzeichnis anlegen
    if [[ ! -d "$wf_dir" ]]; then
        if $DRY_RUN; then
            echo "  MKDIR: ${wf_dir}"
        else
            mkdir -p "$wf_dir"
        fi
    fi

    # Bereits korrekter Symlink?
    if [[ -L "$link" ]]; then
        local current
        current=$(readlink "$link")
        if [[ "$current" == "$target" ]]; then
            return  # Bereits korrekt
        fi
        # Falscher Symlink → ersetzen
        if $DRY_RUN; then
            echo "  FIX-LINK: ${workflow}.md (${current} → ${target})"
        else
            rm "$link"
            ln -s "$target" "$link"
            echo "  FIX-LINK: ${workflow}.md"
        fi
        return
    fi

    # Eigene Datei vorhanden → durch Symlink ersetzen
    if [[ -f "$link" ]]; then
        if $DRY_RUN; then
            echo "  REPLACE: ${workflow}.md (eigene Kopie → Symlink)"
        else
            rm "$link"
            ln -s "$target" "$link"
            echo "  REPLACE: ${workflow}.md"
        fi
        return
    fi

    # Neu anlegen
    if $DRY_RUN; then
        echo "  LINK: ${workflow}.md"
    else
        ln -s "$target" "$link"
        echo "  LINK: ${workflow}.md"
    fi
}

sync_repo() {
    local repo_dir="$1"
    local repo_name
    repo_name=$(basename "$repo_dir")

    # platform selbst skippen
    [[ "$repo_name" == "platform" ]] && return


    # SSoT-Skip (ADR-265): auch Pins/Worktrees des platform-Repos (z. B. platform-pinned)
    # nie besyncen — der Sync würde die SSoT-Dateien dort durch selbstreferenzielle
    # Symlinks ersetzen (Realfall 2026-07-04: 37 Typechanges in platform-pinned).
    local origin_url
    origin_url=$(git -C "$repo_dir" remote get-url origin 2>/dev/null || true)
    case "$origin_url" in
        */platform|*/platform.git) return ;;
    esac

    # Registry-Guard: die Schleife unten laeuft ueber VERZEICHNISSE in $GITHUB_DIR,
    # `fleet_checkout.py` aktualisiert aber nur Repos AUS DER REGISTRY. Ein Klon, der
    # in keiner Registry steht, wird also nie gezogen — und trotzdem beurteilt.
    #
    # Realfall design-hub (2026-06-01 bis 2026-08-13, ~10 Wochen): die `.windsurf/`-Zeile
    # steht seit dem 01.06. in seiner `.gitignore` (Commit 8a0ee9ca). Der Melder meldete
    # sie trotzdem woechentlich als fehlend, weil der Klon auf dem Runner aus der Zeit
    # davor stammte. Ein frischer Klon liefert `check-ignore` = 0, der Runner-Klon = 1.
    # Der Meter war damit dauerhaft rot auf einem Befund, den es auf `main` nicht gab —
    # und ein dauerhaft roter Melder meldet nichts mehr (platform#1508, #1953).
    #
    # Nicht bewerten heisst nicht verschweigen: solche Verzeichnisse kommen als eigene
    # Kategorie in die Summary, damit die Registry-Luecke sichtbar wird statt als Drift
    # verkleidet (🌀 stale_local_clone_never_ground_truth).
    if [[ ${#REGISTRY_REPOS[@]} -gt 0 ]] && ! in_array "$repo_name" "${REGISTRY_REPOS[@]}"; then
        echo "📦 ${repo_name}"
        echo "  NOT-REGISTERED: steht in keiner Registry — nicht bewertet (Klon wird nie aktualisiert)"
        NOT_REGISTERED_NAMES+=("$repo_name")
        return
    fi

    # Ignore-Guard (ADR-265): ohne wirksamen .windsurf/-Ignore erzeugt jeder neue Link
    # ??-Dirt im Ziel-Repo. Repo überspringen, bis die .gitignore-Zeile committet ist.
    #
    # `check-ignore` kennt DREI Ausgaenge, nicht zwei: 0 = ignoriert, 1 = nicht
    # ignoriert, 128 = git konnte gar nicht antworten (kein Repo, dubious ownership,
    # kaputter Index). Die frühere Fassung warf 1 und 128 zusammen und meldete beides
    # als "`.windsurf/` fehlt in .gitignore" — eine Diagnose, die im 128-Fall schlicht
    # falsch ist und den echten Grund verdeckt. Realfall design-hub: die Zeile steht
    # nachweislich in .gitignore auf `main` (per API geprueft 2026-08-10), der Melder
    # meldete sie trotzdem seit Wochen als fehlend. Der Fund war deshalb nicht
    # nachvollziehbar und blieb liegen.
    local ci_rc=0
    git -C "$repo_dir" check-ignore -q ".windsurf/workflows/__adr265_probe__.md" 2>/dev/null || ci_rc=$?
    if [ "$ci_rc" -eq 1 ]; then
        echo "📦 ${repo_name}"
        echo "  SKIP-REPO: '.windsurf/' nicht in .gitignore — Zeile committen, dann sync (ADR-265)"
        SKIP_REPO_NAMES+=("$repo_name")
        return
    elif [ "$ci_rc" -ne 0 ]; then
        # Nicht als .gitignore-Fund ausgeben: das waere eine erfundene Ursache.
        # Die Fehlermeldung von git selbst ist die einzige belastbare Auskunft.
        echo "📦 ${repo_name}"
        echo "  SKIP-REPO: check-ignore nicht auswertbar (git exit ${ci_rc}) — Repo-Zustand pruefen, NICHT die .gitignore"
        git -C "$repo_dir" check-ignore -q ".windsurf/workflows/__adr265_probe__.md" 2>&1 >/dev/null \
          | sed 's/^/    git: /' || true
        SKIP_REPO_NAMES+=("$repo_name")
        return
    fi

    # Repo-Typ bestimmen
    local is_django=false
    local is_package=false
    in_array "$repo_name" "${DJANGO_HUBS[@]}" && is_django=true
    in_array "$repo_name" "${PACKAGES[@]}" && is_package=true

    local type_label="other"
    $is_django && type_label="django-hub"
    $is_package && type_label="package"

    local changes=0
    # SKIP-Längsaggregation (ADR-265 REC-1): merkt sich nur, OB dieses Repo
    # mindestens einen SKIP-TRACKED-Treffer hatte (nicht welche Workflows) —
    # additive Auswertung des ohnehin schon geechoten Guard-Outputs.
    local tracked_hit=false

    # Universal Workflows
    for wf in "${UNIVERSAL[@]}"; do
        local before
        before=$(sync_workflow "$repo_dir" "$wf" 2>&1)
        if [[ -n "$before" ]]; then
            if [[ $changes -eq 0 ]]; then
                echo "📦 ${repo_name} (${type_label})"
            fi
            echo "$before"
            changes=$((changes + 1))
            [[ "$before" == *"SKIP-TRACKED"* ]] && tracked_hit=true
        fi
    done

    # Django-Hub Workflows
    if $is_django; then
        for wf in "${DJANGO_HUB[@]}"; do
            local before
            before=$(sync_workflow "$repo_dir" "$wf" 2>&1)
            if [[ -n "$before" ]]; then
                if [[ $changes -eq 0 ]]; then
                    echo "📦 ${repo_name} (${type_label})"
                fi
                echo "$before"
                changes=$((changes + 1))
                [[ "$before" == *"SKIP-TRACKED"* ]] && tracked_hit=true
            fi
        done
    fi

    # Package Workflows
    if $is_package; then
        for wf in "${PACKAGE[@]}"; do
            local before
            before=$(sync_workflow "$repo_dir" "$wf" 2>&1)
            if [[ -n "$before" ]]; then
                if [[ $changes -eq 0 ]]; then
                    echo "📦 ${repo_name} (${type_label})"
                fi
                echo "$before"
                changes=$((changes + 1))
                [[ "$before" == *"SKIP-TRACKED"* ]] && tracked_hit=true
            fi
        done
    fi

    $tracked_hit && SKIP_TRACKED_NAMES+=("$repo_name")
    # Expliziter Erfolgs-Return: unter `set -e` würde sonst der obige `&&`-
    # Ausdruck mit tracked_hit=false (Exit 1, kein Guard-Fehler) als
    # sync_repo()-Exit-Status durchschlagen und den ganzen Lauf abbrechen.
    return 0
}

# --- Main ---

echo "=== Workflow Sync ==="
echo "Source: ${PLATFORM_WF}"
echo "Workflows: ${#UNIVERSAL[@]} universal + ${#DJANGO_HUB[@]} django-hub + ${#PACKAGE[@]} package"
$DRY_RUN && echo "Mode: DRY-RUN (keine Änderungen)"
echo ""

if [[ -n "$SINGLE_REPO" ]]; then
    repo_dir="${GITHUB_DIR}/${SINGLE_REPO}"
    if [[ ! -d "$repo_dir" ]]; then
        echo "ERROR: Repo '${SINGLE_REPO}' nicht gefunden in ${GITHUB_DIR}"
        exit 1
    fi
    sync_repo "$repo_dir"
else
    for repo_dir in "${GITHUB_DIR}"/*/; do
        [[ -d "$repo_dir" ]] && sync_repo "$repo_dir"
    done
fi

echo ""
echo "=== Done ==="

# SKIP-Längsaggregation (ADR-265 REC-1): Schluss-Summary über den Lauf, damit
# ein dauerhaft übersprungenes Repo nicht unbemerkt von Workflow-Updates
# abgeschnitten bleibt. Rein additiv — die Per-Lauf-Echos oben bleiben
# unverändert; --strict nutzt dieselbe Aggregation für einen CI-Fallback.
if [[ ${#NOT_REGISTERED_NAMES[@]} -gt 0 ]]; then
    echo "NOT-REGISTERED-SUMMARY: ${#NOT_REGISTERED_NAMES[@]} Verzeichnis(se) ohne Registry-Eintrag, nicht bewertet: $(IFS=,; echo "${NOT_REGISTERED_NAMES[*]-}")"
fi
TOTAL_SKIPS=$((${#SKIP_REPO_NAMES[@]} + ${#SKIP_TRACKED_NAMES[@]}))
if [[ $TOTAL_SKIPS -gt 0 ]]; then
    echo "SKIP-SUMMARY: ${TOTAL_SKIPS} Repo(s) übersprungen (SKIP-REPO: $(IFS=,; echo "${SKIP_REPO_NAMES[*]-}"); SKIP-TRACKED: $(IFS=,; echo "${SKIP_TRACKED_NAMES[*]-}"))"
else
    echo "SKIP-SUMMARY: 0 Repos übersprungen"
fi

if $STRICT && [[ $TOTAL_SKIPS -gt 0 ]]; then
    exit 1
fi
