#!/usr/bin/env bash
# =============================================================================
# Auto-Venv: Automatic virtualenv activation for multi-repo workspaces
# =============================================================================
#
# Problem: When cd'ing between project directories, the previous project's
#          venv stays active → wrong packages → confusing ImportErrors.
#
# Solution: Override `cd` to auto-activate .venv when entering a project
#           directory, and deactivate when leaving.
#
# Installation:
#   echo 'source ~/github/platform/scripts/auto-venv.sh' >> ~/.bashrc
#
# Works with: bash. For zsh, add to ~/.zshrc instead.
# Requires: nothing (zero external dependencies).
# =============================================================================

_auto_venv_hook() {
    # Only act if .venv/bin/activate exists in current directory
    if [[ -f ".venv/bin/activate" ]]; then
        # Skip if this venv is already active
        local target_venv
        target_venv="$(pwd)/.venv"
        if [[ "$VIRTUAL_ENV" != "$target_venv" ]]; then
            # Deactivate any current venv first
            if command -v deactivate &>/dev/null; then
                deactivate
            fi
            source ".venv/bin/activate"
        fi
    fi
}

# Override cd to trigger the hook
cd() {
    builtin cd "$@" || return
    _auto_venv_hook
}

# Also trigger on shell startup (for terminals opened in a project dir)
_auto_venv_hook
