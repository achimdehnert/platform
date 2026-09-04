#!/usr/bin/env python3
"""hostzugang.py — der eine Weg zu einem Host aus infra/hosts.yaml (platform#2783).

`ssh_via`/`ssh_shell` (Hop-Zugang, weil der Schluessel fuer GPU-Box/GX10 nur auf
dem prod-Hop liegt, kein wg0-Peer von hier aus — Referenz: tools/flottenbild.py
`messe_knoten()`) stand bald darauf ein zweites Mal in tools/host_datei_drift.py
(#2781) und ein drittes Mal in tools/deploy-script-drift.sh — drei Kopien
derselben Konstruktion, bei denen die naechste Aenderung (neuer Peer, anderes
`ssh_shell`, anderer Timeout) eine davon vergessen haette und der betroffene
Host wieder still "nicht erreichbar" gemeldet haette (Realfall platform#2774).

`ssh_kommando()` baut NUR die (ggf. gehoppte) argv-Liste. Ob die Nutzlast per
stdin oder als eigenes argv-Element durchgeht, entscheidet weiterhin der
Aufrufer — die drei Werkzeuge unterscheiden sich genau darin (Python-stdin-
Skript, Bash-Heredoc, Kommandozeilen-Argument), und das Verhalten soll
byte-identisch bleiben, nicht vereinheitlicht werden (platform#2783).
"""

from __future__ import annotations

#: Optionen des AEUSSEREN ssh-Aufrufs — Default: tools/flottenbild.py, die
#: Referenzimplementierung. host_datei_drift.py und deploy-script-drift.sh
#: haben eigene (Timeout 10 statt 8, ohne StrictHostKeyChecking) und uebergeben
#: sie explizit als `ssh_opts=`, um ihr bisheriges Verhalten zu erhalten.
SSH_OPTS: list[str] = [
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=8",
    "-o",
    "StrictHostKeyChecking=accept-new",
]

#: Optionen des INNEREN, gehoppten ssh-Aufrufs — in allen drei Originalen
#: bereits identisch, deshalb hier fest statt als Parameter.
VIA_OPTS: list[str] = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]


def ssh_kommando(
    host: dict,
    shell_default: str = "bash -s",
    *,
    ssh_opts: list[str] | None = None,
    kommando_direkt: str | None = None,
) -> list[str]:
    """Baut die (ggf. per `ssh_via` gehoppte) argv-Liste fuer einen Host.

    Erwartet `host["ssh"]` (Zielhost/-alias, vom Aufrufer aufgeloest — z.B.
    inkl. `ssh_alias`-Fallback wie in flottenbild.py) sowie optional
    `host["ssh_via"]` (Hop, dessen Schluessel den Zielhost kennt) und
    `host["ssh_shell"]` (ersetzt die Remote-Shell, z.B. WSL bei Windows-
    Knoten; Vorgabe `shell_default`). `host["betrieb"]` (`auf_zuruf`) wird
    hier absichtlich nicht ausgewertet (Entscheidung, keine Restarbeit): es aendert nichts an der argv-Liste,
    nur an der Klassifikation eines Fehlschlags danach, und bleibt Sache der
    Aufrufer (unveraendert gegenueber vorher).

    Liegt `ssh_via` vor, geht das Kommando IMMER ueber ein verschachteltes
    ssh: `["ssh", *ssh_opts, ssh_via, inner]`, wobei `inner` ein einzelnes
    argv-Element ist, das seinerseits `ssh <VIA_OPTS> <ziel> "<shell>"`
    lautet — die Nutzlast wandert dann per stdin durch beide Verbindungen
    (Sache des Aufrufers, hier nicht gesetzt).

    Ohne `ssh_via` haengt ssh_kommando als letztes Element entweder die Shell
    an (Standardfall — die Nutzlast geht dann separat per stdin) oder, falls
    `kommando_direkt` gesetzt ist, dieses woertliche Kommando STATT der Shell:
    tools/host_datei_drift.py schickt im Direkt-Zweig sein Kommando als
    eigenes argv-Element durch, ohne stdin — dieser Unterschied ist Bestand
    des Originals und wird hier bewusst erhalten, nicht vereinheitlicht.
    """
    ziel = str(host["ssh"])
    opts = list(ssh_opts) if ssh_opts is not None else list(SSH_OPTS)
    shell = str(host.get("ssh_shell") or shell_default)
    ssh_via = host.get("ssh_via")
    if ssh_via:
        inner = f'ssh {" ".join(VIA_OPTS)} {ziel} "{shell}"'
        return ["ssh", *opts, str(ssh_via), inner]
    letzte = kommando_direkt if kommando_direkt is not None else shell
    return ["ssh", *opts, ziel, letzte]
