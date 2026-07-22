#!/usr/bin/env bash
# handover_prio_mirror.sh — SessionStart-Hook (session-retro Gate 2A)
#
# Spiegelt die DOKUMENTIERTE Priorität salient in den Sitzungskontext und fordert,
# Abweichungen ausdruecklich zu bestaetigen. Direktive Kontrolle / Nudge — NICHT
# blockierend. Schnell, keine Heavy-Calls.
#
# Quelle (in Reihenfolge):
#   1. AGENT_HANDOVER.md — kuratierter Prio-Abschnitt (Tabelle ODER Liste) unter
#      einem Heading mit "Priorit/Priorisiert/Naechste/Offene". FUEHREND.
#   2. NEXT.md — numbered items (git-log-Fallback; nur wenn keine kuratierte Prio).
# Damit haengt das Signal an einer gepflegten Tabelle, nicht an claude-next-sync
# (das "Prioritaeten"-Headings + Tabellen nicht parst und auf git-log zurueckfaellt).
#
# Hintergrund: session-retro 2026-06-04, Befund 1/5 — dokumentierte Prio wurde
# still durch einen anderen Grossstrang ersetzt; Scope-Checkpoint loeste nicht aus.
#
# platform#1323 (2026-07-22) — drei Fixes gegen live verifiziertes Fehlverhalten:
#   1. Archiv-Ueberschriften ("... — erledigt/abgeschlossen/Archiv/✅") reaktivieren
#      die Sektion nicht mehr, auch wenn sie zusaetzlich ein Prio-Trigger-Wort tragen.
#   2. Tabellenspalte wird per Header-Name (Item/Task, Tier) aufgeloest statt hart
#      a[3]/a[4] — Position bleibt Fallback, wenn kein passender Header existiert.
#   3. Worktree-Blindheit: in einem git-Worktree ist .git eine DATEI, kein Verzeichnis
#      (ADR-233 macht Worktrees zum vorgeschriebenen Editier-Modus) — `-e` statt `-d`.

CWD="$(pwd)"
[ -e "${CWD}/.git" ] || exit 0   # nur in Git-Repos (Datei ODER Verzeichnis, siehe oben)

REPO_NAME="$(basename "${CWD}")"
HANDOVER="${CWD}/AGENT_HANDOVER.md"
NEXT="${CWD}/NEXT.md"

ITEMS=""; SRC=""

# 1) Kuratierte Prio aus AGENT_HANDOVER.md (Tabelle | # | Item | Tier | … | ODER Liste).
if [ -f "${HANDOVER}" ]; then
    ITEMS="$(awk '
        # Archiv-/Erledigt-Ueberschrift zuerst pruefen — reaktiviert die Sektion NICHT,
        # auch wenn sie zusaetzlich ein Prio-Trigger-Wort enthaelt (platform#1323 U1).
        /^#{1,4}[ \t]/ && /([Ee]rledigt|[Aa]bgeschlossen|[Aa]rchiv|✅)/ {
            if (insec) insec=0
            next
        }
        /^#{1,4}[ \t].*([Pp]riorit|[Pp]riorisiert|[Nn][aä]chste|[Oo]ffene)/ {
            insec=1; header_done=0; item_col=0; tier_col=0; next
        }
        /^#{1,4}[ \t]/ { if (insec) insec=0 }
        insec && /^\|/ {
            n = split($0, a, "|")
            first = a[2]; gsub(/^[ \t]+|[ \t]+$/, "", first)
            if (first ~ /^:?-+:?$/) next          # Trennzeile |---|---| ueberspringen
            if (first !~ /^[0-9]+$/) {
                # Header-Zeile (erste Nicht-Zahlen-/Nicht-Trennzeile): Spalten per
                # Name aufloesen statt Position anzunehmen (platform#1323 U2).
                if (!header_done) {
                    header_done = 1
                    for (i = 2; i <= n; i++) {
                        cell = a[i]; gsub(/^[ \t]+|[ \t]+$/, "", cell)
                        lc = tolower(cell)
                        if (lc == "item" || lc == "task") item_col = i
                        if (lc == "tier") tier_col = i
                    }
                }
                next
            }
            prio = first
            if (item_col > 0 && item_col <= n) { task = a[item_col] } else { task = a[3] }
            if (match(task, /\*\*[^*]+\*\*/)) task = substr(task, RSTART+2, RLENGTH-4)
            gsub(/^[ \t]+|[ \t]+$/, "", task)
            if (tier_col > 0 && tier_col <= n) {
                tier = a[tier_col]
            } else if (item_col == 0) {
                tier = a[4]   # reine Legacy-Tabelle ohne Header-Treffer: alte Position
            } else {
                tier = ""     # Item per Name aufgeloest, aber keine Tier-Spalte vorhanden
            }
            gsub(/[ \t`]/, "", tier)
            # Nur ein "[Tag]"-foermiger Wert ist wirklich ein Tier-Tag (Python-Pendant:
            # tier.startswith("[")) — sonst wuerde eine falsch zugeordnete Spalte den
            # Aufgabentext dupliziert an die Zeile haengen.
            if (tier !~ /^\[/) tier = ""
            if (tier == "") { printf "  %s. %s\n", prio, task } else { printf "  %s. %s  %s\n", prio, task, tier }
        }
        insec && /^([-*][ \t]|[0-9]+\.[ \t])/ { line=$0; sub(/^[ \t]+/, "", line); print "  " line }
    ' "${HANDOVER}")"
    [ -n "${ITEMS}" ] && SRC="AGENT_HANDOVER.md (kuratiert)"
fi

# 2) Fallback: NEXT.md numbered items.
if [ -z "${ITEMS}" ] && [ -f "${NEXT}" ]; then
    ITEMS="$(grep -E '^[0-9]+\. ' "${NEXT}" 2>/dev/null | head -3 | sed 's/^/  /')"
    [ -n "${ITEMS}" ] && SRC="NEXT.md (git-log-Fallback — bitte AGENT_HANDOVER ## Prioritäten pflegen)"
fi

[ -z "${ITEMS}" ] && exit 0   # nichts dokumentiert -> still

echo "⚑ HANDOVER-PRIO (${REPO_NAME}) — Quelle: ${SRC}"
echo "${ITEMS}"
echo "→ Diese Prio zuerst spiegeln. Bei Abweichung (anderes Thema / Mehrstunden-"
echo "  Großstrang) ausdrücklich benennen und bestätigen lassen — nicht still"
echo "  abdriften (Scope-Checkpoint · session-retro Gate 2A)."
exit 0
