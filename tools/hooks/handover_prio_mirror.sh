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
        # Praezisiert nach Retro 2026-07-22 Befund B1: das Teilstring-Match verschluckte
        # auch TEILerledigung ("## Prioritaeten — 2 von 5 erledigt") und liess offene
        # Items still verschwinden. Regel jetzt identisch zum Python-Pendant
        # (_is_archive_heading in tools/next-sync/claude-next-sync):
        # Mengen-/Teil-Qualifier => KEIN Archiv; sonst Marker am ENDE oder am ANFANG.
        # ZWEI DURCHLAEUFE ueber dieselbe Datei (Retro 2026-07-22, Befund B2).
        # Vorher lief awk sequenziell und sammelte JEDE Trigger-Sektion ein — bei einem
        # Dokument mit "## Naechste Schritte" VOR "## Prioritaeten" gab der Hook die Items
        # BEIDER Sektionen aus, das Python-Pendant nur die der exakten "## Prioritaeten".
        # Reproduziert: awk 4 Items, Python 2. Ursache: awk kannte keine Vorrang-Logik.
        # Pass 1 bestimmt die Start-Zeile nach denselben Regeln wie _find_section_start:
        #   exakt "## Prioritaeten" (Level 2) schlaegt alles, sonst erste Heuristik-
        #   Ueberschrift; Archiv-Ueberschriften zaehlen nie.
        # Pass 2 gibt NUR diese eine Sektion aus.
        function heading_text(line,   t) {
            t = line; sub(/^#+[ \t]+/, "", t); return t
        }
        function heading_level(line,   m) {
            match(line, /^#+/); return RLENGTH
        }
        function is_archive(h,   partial) {
            partial = (h ~ /[0-9]+[ \t]*(von|\/|of)[ \t]*[0-9]+/) ||
                      (h ~ /[Tt]eilweise|[Tt]eils|[Tt]lw\./) ||
                      (h ~ /[0-9]+[ \t]*%/)
            if (partial) return 0
            if (h ~ /([ \t]|—|–|-|\(|\[)([Ee]rledigt|[Aa]bgeschlossen|[Aa]rchiv(iert)?|✅)[ \t]*[)\]]?[ \t]*$/) return 1
            if (h ~ /^([Aa]rchiv|[Ee]rledigt|[Aa]bgeschlossen|✅)/) return 1
            return 0
        }
        # Trigger-Woerter und die "nur unter den ersten ZWEI Woertern"-Regel gespiegelt
        # von _is_priority_heading/_PRIORITY_TRIGGER. Der awk-Regex kannte frueher nur
        # vier Woerter (Priorit/Priorisiert/Naechste/Offene) und pruefte sie irgendwo im
        # Heading — beides wich vom Python-Pendant ab (Befund B2, zweiter Teil).
        function is_prio(h,   w, n, i) {
            n = split(h, w, /[ \t—–:\/-]+/)
            for (i = 1; i <= n && i <= 2; i++) {
                if (w[i] ~ /^([Pp]riorit|[Oo]ffen|[Nn][aä]chst|[Nn]aechst|[Nn]ext|[Tt][Oo][Dd][Oo]|[Ss]lice|[Oo]pen|[Bb]acklog|[Kk]nown|[Aa]ufgaben)/) return 1
            }
            return 0
        }
        function is_exact_prio(h,   t) {
            t = h; gsub(/[ \t]+$/, "", t); sub(/:$/, "", t); gsub(/[ \t]+$/, "", t)
            return (t ~ /^[Pp]riorit(ä|ae)ten$/)
        }
        # ---- Pass 1: Start-Zeile bestimmen ----
        NR == FNR {
            if ($0 ~ /^#{1,4}[ \t]/) {
                h = heading_text($0)
                if (!is_archive(h)) {
                    if (heading_level($0) == 2 && is_exact_prio(h)) {
                        if (!exact) exact = FNR
                    } else if (!heuristic && is_prio(h)) {
                        heuristic = FNR
                    }
                }
            }
            next
        }
        # ---- Pass 2: nur die gewaehlte Sektion ausgeben ----
        FNR == 1 { start = exact ? exact : heuristic }
        !start { next }
        FNR < start { next }
        FNR == start { insec=1; header_done=0; item_col=0; tier_col=0; next }
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
    ' "${HANDOVER}" "${HANDOVER}")"
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
