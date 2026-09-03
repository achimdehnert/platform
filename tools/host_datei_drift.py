#!/usr/bin/env python3
"""Drift zwischen Git-Quelle und verteilten Host-Kopien (platform#2529 Befund 3).

Warum es das gibt (gemessen 2026-08-31):
  `/opt/platform` auf prod zieht `origin/main` von selbst nach — es stand binnen
  Minuten auf dem frischen Merge-Commit. Die Dateien, die tatsaechlich AUSGEFUEHRT
  werden, liegen aber woanders: `prod-offsite-daily.sh` unter `/usr/local/bin/`,
  die systemd-Units unter `/etc/systemd/system/`. Das sind KOPIEN, von Hand
  verteilt. Beim Ausrollen eines Backup-Fixes zeigte sich, dass die prod-Kopie
  einen Tag alt war und niemand es gemerkt haette.

  Fuer `scripts/deploy.sh` gab es diesen Melder laengst (tools/deploy-script-drift.sh,
  Phase 0.7.1) — fuer die uebrigen elf verteilten Dateien nicht. Ein Fix im Repo
  an einer Datei aus `infra/host-maintenance/` war damit KEIN Beleg, dass er auf
  dem Host wirkt.

Der Melder ENTDECKT statt zu deklarieren: er nimmt jede Datei der Quellverzeichnisse
und sucht sie an den bekannten Ablageorten. Eine gepflegte Liste waere ein zweiter
Ort, der selbst driften kann — dieselbe Lehre wie bei Phase 0.7.17, die vom Host
ausgeht und nicht von `expected-apps.json`.

Exit-Codes: 0 = synchron · 1 = Drift · 2 = Aufruffehler · 3 = nicht alles pruefbar.
Exit 3 ist eine eigene Klasse: ein Host, den wir nicht lesen konnten, ist NICHT
gruen (🌀 feedback_scope_gap_must_be_an_exit_state).

Usage:
    tools/host_datei_drift.py            # Bericht
    tools/host_datei_drift.py --quiet    # nur die RESULT-Zeile (fuer den Runner)
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

# Quellverzeichnisse: alles darin gilt als potenziell verteilte Datei.
QUELLEN = ("infra/host-maintenance",)

# Ablageorte, an denen eine verteilte Kopie liegen kann. `{name}` ist der
# Dateiname der Quelle. Der Glob-Eintrag deckt user-systemd ab, wo der Pfad den
# Benutzernamen enthaelt (flottenbild.timer liegt unter ~devuser).
ABLAGEORTE = (
    "/usr/local/bin/{name}",
    "/etc/systemd/system/{name}",
    "/home/*/.config/systemd/user/{name}",
)

SSH = ("ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes")

# Dateinamen gehen in eine Remote-Shell. Nur harmlose Namen werden eingesetzt —
# alles andere wird verworfen, nicht riskant gequotet.
SICHER = re.compile(r"^[A-Za-z0-9._-]+$")

# Ein Versionsmarker macht aus "weicht ab" ein "Host haengt N Staende zurueck".
VERSIONS_MARKER = re.compile(r'^[A-Z_]+_VERSION="([^"]*)"', re.MULTILINE)

# Von host_hashes() nebenbei gefuellt: Remote-Pfad -> Version der Host-Kopie.
VERSIONEN: dict[str, str] = {}


def _remote_pfad(ort: str, name: str) -> str:
    """Ein Ablageort als Remote-Shell-Wort.

    Ein Glob MUSS unquoted bleiben, sonst expandiert die Remote-Shell ihn nicht.
    Genau daran scheiterte der erste Entwurf: alle acht user-systemd-Units unter
    `/home/*/.config/systemd/user/` wurden stillschweigend uebersehen, der Melder
    meldete "synchron" ueber Gebiet, das er nie angesehen hatte — die Blindheit,
    gegen die er gebaut ist.
    """
    pfad = ort.format(name=name)
    return pfad if "*" in pfad else f"'{pfad}'"


def md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def hosts_aus_registry(platform_dir: Path) -> list[dict[str, str | None]]:
    """Zugangsfelder je Host aus der Infra-SoT. Nicht hier hartkodieren.

    `ssh_via`/`ssh_shell`/`betrieb` fehlten hier bisher komplett — der Melder
    baute das ssh-Kommando nur aus `ssh` und erklaerte GPU-Box/GX10 (Zugang nur
    ueber den prod-Hop, kein Schluessel auf dieser Maschine) fuer "nicht lesbar",
    obwohl sie vom Hop aus antworten (platform#2774 Befund).
    """
    import yaml

    daten = yaml.safe_load((platform_dir / "infra/hosts.yaml").read_text())
    ergebnis = []
    for name, h in (daten.get("hosts") or {}).items():
        if isinstance(h, dict) and h.get("ssh"):
            ergebnis.append(
                {
                    "name": name,
                    "ssh": h["ssh"],
                    "ssh_via": h.get("ssh_via"),
                    "ssh_shell": h.get("ssh_shell"),
                    "betrieb": h.get("betrieb"),
                }
            )
    return ergebnis


def quelldateien(platform_dir: Path) -> dict[str, Path]:
    """Dateiname -> Quellpfad. README und Runbooks werden nicht verteilt."""
    gefunden: dict[str, Path] = {}
    for rel in QUELLEN:
        d = platform_dir / rel
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and not f.name.endswith((".md", ".recommended")):
                gefunden[f.name] = f
    return gefunden


def host_hashes(
    ssh_ziel: str,
    namen: list[str],
    ssh_via: str | None = None,
    ssh_shell: str | None = None,
) -> dict[str, str] | None:
    """md5 je gefundener Kopie auf einem Host. None = Host nicht lesbar.

    Ein einziger ssh-Aufruf fuer alle Dateien: der Melder laeuft in JEDEM
    Sitzungsstart, und ein Call je Datei waere 11 Verbindungen pro Host.

    `ssh_via`: der Schluessel fuer den Knoten liegt nur auf dem Hop (GPU-Box,
    GX10 — analog tools/flottenbild.py messe_knoten()). Das Kommando geht dann
    als verschachteltes ssh vom Hop aus; das Skript wandert per stdin durch
    beide Verbindungen, statt als Kommandozeilen-Argument durch zwei Shells
    hindurch zitiert zu werden. `ssh_shell` ersetzt die Remote-Shell (WSL bei
    Windows-Knoten), Vorgabe ist "bash -s".
    """
    muster = " ".join(
        _remote_pfad(ort, n) for n in namen for ort in ABLAGEORTE if SICHER.match(n)
    )
    # `md5sum` schweigt ueber nicht existierende Pfade (2>/dev/null); der Glob
    # expandiert in der Remote-Shell, unexpandierte Muster fallen so heraus.
    # md5 UND Versionsmarker in einem Durchgang: der Hash sagt "weicht ab", der
    # Marker sagt "wie weit". Dateien ohne Marker liefern einfach keine VER-Zeile.
    befehl = (
        f'for p in {muster}; do [ -f "$p" ] || continue; md5sum "$p"; '
        f'v=$(grep -m1 -oE \'^[A-Z_]+_VERSION="[^"]*"\' "$p" 2>/dev/null); '
        f'[ -n "$v" ] && echo "VER $p $v"; done 2>/dev/null'
    )
    if ssh_via:
        shell = ssh_shell or "bash -s"
        inner = f'ssh -o BatchMode=yes -o ConnectTimeout=8 {ssh_ziel} "{shell}"'
        cmd = [*SSH, ssh_via, inner]
        lauf_kwargs: dict = {"input": befehl}
    else:
        cmd = [*SSH, ssh_ziel, befehl]
        lauf_kwargs = {}
    try:
        aus = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            **lauf_kwargs,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if aus.returncode not in (0, 1):
        return None
    treffer: dict[str, str] = {}
    for zeile in aus.stdout.splitlines():
        if zeile.startswith("VER "):
            _, pfad, marker = zeile.split(None, 2)
            VERSIONEN[pfad] = marker.split("=", 1)[1].strip('"')
            continue
        teile = zeile.split(None, 1)
        if len(teile) == 2:
            treffer[teile[1].strip()] = teile[0]
    return treffer


def pruefe(platform_dir: Path) -> tuple[list[str], list[str], list[str], int]:
    """(Drift-Zeilen, unpruefbare Hosts, schlafende Hosts, Anzahl gepruefter Kopien)."""
    quellen = quelldateien(platform_dir)
    if not quellen:
        return [], [], [], 0
    soll = {name: md5(p) for name, p in quellen.items()}
    soll_versionen = {
        name: m.group(1)
        for name, p in quellen.items()
        if (m := VERSIONS_MARKER.search(p.read_text(errors="replace")))
    }
    VERSIONEN.clear()

    drift: list[str] = []
    unpruefbar: list[str] = []
    schlaeft: list[str] = []
    gezaehlt = 0

    for host in hosts_aus_registry(platform_dir):
        treffer = host_hashes(
            host["ssh"], list(quellen), host.get("ssh_via"), host.get("ssh_shell")
        )
        if treffer is None:
            # `betrieb: auf_zuruf` — der Knoten laeuft planmaessig nur, wenn ihn
            # jemand weckt (GPU-Box, Owner-Entscheid Wake-on-LAN). Das ist kein
            # Ausfall und kein Scope-Gap, sondern ein erwarteter Zustand — sonst
            # stuende der Knoten dauerhaft als "nicht pruefbar" da (platform#2545).
            if host.get("betrieb") == "auf_zuruf":
                schlaeft.append(host["name"])
            else:
                unpruefbar.append(host["name"])
            continue
        for pfad, ist in sorted(treffer.items()):
            name = pfad.rsplit("/", 1)[-1]
            gezaehlt += 1
            if soll.get(name) and ist != soll[name]:
                ist_ver = VERSIONEN.get(pfad)
                soll_ver = soll_versionen.get(name)
                zusatz = (
                    f" (Host {ist_ver} / Repo {soll_ver})"
                    if ist_ver and soll_ver and ist_ver != soll_ver
                    else ""
                )
                drift.append(f"{host['name']}:{pfad}{zusatz}")
    return drift, unpruefbar, schlaeft, gezaehlt


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quiet", action="store_true", help="nur die RESULT-Zeile")
    args = ap.parse_args()

    platform_dir = Path(__file__).resolve().parents[1]
    try:
        drift, unpruefbar, schlaeft, gezaehlt = pruefe(platform_dir)
    except Exception as exc:  # noqa: BLE001 — der Runner braucht eine Zeile, keinen Traceback
        print(f"RESULT: UNGEPRUEFT — Drift-Check nicht ausfuehrbar: {exc}")
        return 3

    if not args.quiet:
        print(f"Quellen: {', '.join(QUELLEN)} — {gezaehlt} verteilte Kopie(n) gefunden")
        for d in drift:
            print(f"  ❌ DRIFT  {d}")
        for h in unpruefbar:
            print(f"  ⚠️  nicht lesbar: {h}")
        for h in schlaeft:
            print(f"  😴 schläft (auf_zuruf), kein Befund: {h}")

    if drift:
        print(
            f"RESULT: DRIFT — {len(drift)} Host-Kopie(n) weichen von Git ab: "
            f"{' '.join(drift)} (Repo-Stand ist die Quelle; Host-Kopie ersetzen)"
        )
        return 1
    if unpruefbar:
        print(
            f"RESULT: UNGEPRUEFT — nicht lesbar: {' '.join(unpruefbar)} "
            f"(die uebrigen {gezaehlt} Kopie(n) sind synchron)"
        )
        return 3
    schlaf_hinweis = f" — schlaeft (auf_zuruf): {' '.join(schlaeft)}" if schlaeft else ""
    print(
        f"RESULT: OK — {gezaehlt} verteilte Host-Kopie(n) synchron mit dem Repo"
        f"{schlaf_hinweis}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
