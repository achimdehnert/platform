#!/usr/bin/env python3
"""flottenbild.py — das Systembild der Flotte aus den Quellen, nicht aus der Erinnerung.

KONZ-platform-054, Punkt 178 (Owner-Go 2026-08-30). Am 2026-08-30 wurde das
Flottenbild zweimal von Hand aus neun Kommandos auf sechs Hosts zusammengesetzt.
Ein Bild, das jemand zusammensetzt, ist naechste Woche eine Luege — dieses
Werkzeug setzt es aus denselben Quellen zusammen, jedes Mal gleich:

    infra/hosts.yaml            Rolle, Auflage, Zugang, Historie, verified
    infra/ports.yaml            Dienste, prod_host, betriebsstatus
    ssh je Knoten (read-only)   Load, RAM, Swap, Platte, Container, unhealthy, restarting
    Prometheus (ueber den Monitor-Host)   Targets, feuernde Alerts
    tools/befund_journal.py     offene Befunde, im Gate, ueberfaellig, mit Kommando
    tools/alarmweg_probe.py     belegte Alarmwege
    tools/erreichbarkeit_melder.py, infra/scripts/hosts_audit.py

Ausgabe: eine HTML-Seite (--out) und dieselben Daten als JSON (--json). Was nicht
erreichbar war, steht als eigener Zustand auf der Seite — nie als stilles Weglassen
(K1 aus platform#2483).

    python3 tools/flottenbild.py --out /tmp/flottenbild.html --json /tmp/flottenbild.json
    python3 tools/flottenbild.py --offline daten.json --out seite.html   # nur rendern
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

WURZEL = Path(__file__).resolve().parents[1]
HOSTS_YAML = WURZEL / "infra" / "hosts.yaml"
PORTS_YAML = WURZEL / "infra" / "ports.yaml"

#: Auf welchem Knoten laeuft der Flotten-Prometheus und wie heisst sein Container.
#: Bewusst hier und nicht in hosts.yaml: das ist eine Eigenschaft dieses Lesers,
#: nicht des Knotens. Aendert sich der Monitor-Host, aendert sich diese Zeile.
MONITOR_HOST = "odoo"
MONITOR_CONTAINER = "odoo_prometheus"

SSH_OPTS = [
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=8",
    "-o",
    "StrictHostKeyChecking=accept-new",
]

#: Ein Kommando je Knoten — alles read-only, eine Zeile Ausgabe, feste Reihenfolge.
HOST_KOMMANDO = r"""
export LC_ALL=C LANG=C; L=$(cut -d" " -f1-3 /proc/loadavg); K=$(nproc)
read -r _ MT MU _ <<<"$(free -m | awk '/^Mem:/{print $1,$2,$3}')"
read -r _ ST SU _ <<<"$(free -m | awk '/^Swap:/{print $1,$2,$3}')"
D=$(df -P / | awk 'NR==2{print $5}' | tr -d %)
R=$(docker ps -q 2>/dev/null | wc -l); A=$(docker ps -aq 2>/dev/null | wc -l)
U=$(docker ps --filter health=unhealthy --format '{{.Names}}' 2>/dev/null | tr '\n' ',')
X=$(docker ps --filter status=restarting --format '{{.Names}}' 2>/dev/null | tr '\n' ',')
UP=$(cut -d. -f1 /proc/uptime)
printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' "$L" "$K" "$MT" "$MU" "${ST:-0}" "${SU:-0}" "$D" "$R" "$A" "$U" "$X" "$UP"
"""


def _lauf(
    cmd: list[str], timeout: int = 60, stdin: str | None = None
) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, input=stdin
        )
        return r.returncode, (r.stdout or "") + (
            ("\n" + r.stderr) if r.returncode and r.stderr else ""
        )
    except (subprocess.SubprocessError, OSError) as exc:
        return 127, str(exc)


# ── Quellen ──────────────────────────────────────────────────────────────────


def lade_sot() -> tuple[dict, dict]:
    hosts = yaml.safe_load(HOSTS_YAML.read_text(encoding="utf-8")) or {}
    ports = yaml.safe_load(PORTS_YAML.read_text(encoding="utf-8")) or {}
    return hosts, ports


def messe_knoten(name: str, h: dict) -> dict:
    """Ein ssh-Aufruf je Knoten. Nicht erreichbar ist ein Zustand, kein Fehler."""
    ziel = h.get("ssh") or (h.get("ssh_alias") if h.get("ssh_alias") else None)
    if h.get("status") == "geplant":
        return {"knoten": name, "zustand": "geplant"}
    if not ziel:
        return {
            "knoten": name,
            "zustand": "kein_zugang",
            "grund": "hosts.yaml ohne ssh/ssh_alias",
        }
    # Knoten hinter wg0 (GPU-Box, GX10) haengen an einem Hop: hosts.yaml `ssh_jump`.
    # Windows-Knoten fuehren die Probe in ihrer WSL aus: hosts.yaml `ssh_shell`.
    # `ssh_via`: der Schluessel fuer den Knoten liegt NUR auf dem Hop (GPU-Box: root@prod
    # kennt achim@10.99.0.2, die Dev-Maschine nicht) — dann laeuft das ssh vom Hop aus,
    # das Skript wandert per stdin durch beide Verbindungen.
    shell = str(h.get("ssh_shell") or "bash -s")
    if h.get("ssh_via"):
        inner = f'ssh -o BatchMode=yes -o ConnectTimeout=8 {ziel} "{shell}"'
        cmd = ["ssh", *SSH_OPTS, str(h["ssh_via"]), inner]
    else:
        cmd = ["ssh", *SSH_OPTS, ziel, shell]
    rc, out = _lauf(cmd, timeout=90, stdin=HOST_KOMMANDO)
    zeile = [z for z in out.splitlines() if z.count("|") >= 10]
    if rc != 0 or not zeile:
        return {"knoten": name, "zustand": "unerreichbar", "grund": out.strip()[:160]}
    f = zeile[-1].split("|")
    try:
        mt, mu, st, su = int(f[2]), int(f[3]), int(f[4]), int(f[5])
        return {
            "knoten": name,
            "zustand": "gemessen",
            "load": f[0],
            "kerne": int(f[1]),
            "ram_pct": round(100 * mu / mt) if mt else None,
            "swap_pct": round(100 * su / st) if st else None,
            "swap_mb": st,
            "disk_pct": int(f[6]),
            "container": int(f[7]),
            "container_gesamt": int(f[8]),
            "unhealthy": [x for x in f[9].split(",") if x],
            "restarting": [x for x in f[10].split(",") if x],
            "uptime_tage": int(f[11]) // 86400,
        }
    except (ValueError, IndexError) as exc:
        return {
            "knoten": name,
            "zustand": "unlesbar",
            "grund": f"{exc}: {zeile[-1][:120]}",
        }


def lese_prometheus(hosts: dict) -> dict:
    h = (hosts.get("hosts") or {}).get(MONITOR_HOST) or {}
    ziel = h.get("ssh") or h.get("ssh_alias")
    if not ziel:
        return {"zustand": "kein_zugang"}
    skript = (
        f"docker exec {MONITOR_CONTAINER} wget -qO- http://localhost:9090/api/v1/targets; echo; echo '#SEP#'; "
        f"docker exec {MONITOR_CONTAINER} wget -qO- http://localhost:9090/api/v1/alerts"
    )
    rc, out = _lauf(["ssh", *SSH_OPTS, ziel, skript], timeout=40)
    if rc != 0 or "#SEP#" not in out:
        return {"zustand": "unerreichbar", "grund": out.strip()[:160]}
    t_raw, a_raw = out.split("#SEP#", 1)
    try:
        t = json.loads(t_raw.strip())["data"]["activeTargets"]
        a = json.loads(a_raw.strip())["data"]["alerts"]
    except (json.JSONDecodeError, KeyError) as exc:
        return {"zustand": "unlesbar", "grund": str(exc)}
    return {
        "zustand": "gemessen",
        "targets": [
            {
                "job": x["labels"].get("job"),
                "host": x["labels"].get("host", "-"),
                "health": x["health"],
            }
            for x in t
        ],
        "alerts": [
            {
                "name": x["labels"].get("alertname"),
                "host": x["labels"].get("host"),
                "name_": x["labels"].get("name", ""),
                "state": x["state"],
            }
            for x in a
        ],
    }


def lese_melder() -> dict:
    aus: dict = {}
    rc, out = _lauf(
        [
            sys.executable,
            str(WURZEL / "tools" / "befund_journal.py"),
            "--bericht",
            "--json",
            "--repo",
            "platform",
        ],
        timeout=60,
    )
    try:
        j = json.loads(out) if rc == 0 else []
        aus["journal"] = {
            "gesamt": len(j),
            "im_gate": sum(1 for x in j if x.get("im_gate")),
            "ueberfaellig": sum(1 for x in j if x.get("ueberfaellig")),
            "mit_kommando": sum(1 for x in j if x.get("kommando")),
            "eintraege": [
                {
                    "id": x["id"],
                    "laeufe": x["laeufe"],
                    "im_gate": x["im_gate"],
                    "ueberfaellig": x["ueberfaellig"],
                    "note": (x.get("note") or "")[:120],
                }
                for x in j
            ],
        }
    except json.JSONDecodeError:
        aus["journal"] = {"zustand": "unlesbar"}
    rc, out = _lauf(
        [sys.executable, str(WURZEL / "tools" / "alarmweg_probe.py"), "--pruefen"],
        timeout=120,
    )
    kanaele = []
    for z in out.splitlines():
        z = z.strip()
        if z[:1] in ("✅", "❌", "◌"):
            teile = z[1:].split(None, 1)
            kanaele.append(
                {
                    "kanal": teile[0],
                    "ok": z[0] == "✅",
                    "blind": z[0] == "◌",
                    "grund": teile[1] if len(teile) > 1 else "",
                }
            )
    aus["alarmwege"] = {"exit": rc, "kanaele": kanaele}
    rc, out = _lauf(
        [sys.executable, str(WURZEL / "tools" / "erreichbarkeit_melder.py"), "--kurz"],
        timeout=180,
    )
    aus["erreichbarkeit"] = {
        "exit": rc,
        "kurz": out.strip().splitlines()[-1] if out.strip() else "(keine Ausgabe)",
    }
    rc, out = _lauf(
        [
            sys.executable,
            str(WURZEL / "infra" / "scripts" / "hosts_audit.py"),
            "--check",
            "all",
            "--workflows",
            str(WURZEL / ".github" / "workflows"),
        ],
        timeout=60,
    )
    aus["hosts_audit"] = {
        "exit": rc,
        "kurz": out.strip().splitlines()[-1] if out.strip() else "(keine Ausgabe)",
    }
    return aus


def sammle(nur_knoten: list[str] | None = None) -> dict:
    hosts, ports = lade_sot()
    knoten = []
    for name, h in (hosts.get("hosts") or {}).items():
        if nur_knoten and name not in nur_knoten:
            continue
        m = messe_knoten(name, h)
        m.update(
            {
                "rolle": (h.get("role") or "").strip(),
                "auflage": h.get("auflage") or {},
                "historie": h.get("historie") or [],
                "verified": str(h.get("verified")),
                "verified_bis": str(h.get("verified_bis") or ""),
                "ip": h.get("ip"),
                "arch": h.get("arch"),
                "provider": h.get("provider", ""),
                "server_type": h.get("server_type", ""),
            }
        )
        knoten.append(m)
    dienste = ports.get("services") or {}
    je_host: dict[str, dict] = {}
    for d, cfg in dienste.items():
        if not isinstance(cfg, dict):
            continue
        ph = str(cfg.get("prod_host", "prod"))
        st = str(cfg.get("betriebsstatus", "aktiv"))
        je_host.setdefault(
            ph, {"aktiv": [], "stillgelegt": [], "blockiert": []}
        ).setdefault(st, []).append(d)
    return {
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "knoten": knoten,
        "dienste_je_host": je_host,
        "prometheus": lese_prometheus(hosts),
        "melder": lese_melder(),
    }


# ── Rendern ──────────────────────────────────────────────────────────────────

CSS = """
:root{--ground:#F3F5F7;--surface:#fff;--ink:#1B2430;--muted:#5B6674;--line:#D6DCE3;--accent:#1E6B75;--accent-soft:#E3F0F1;--ok:#2E7D4F;--ok-soft:#E4F2E9;--warn:#A8701A;--warn-soft:#F7EEDC;--crit:#B3261E;--crit-soft:#F8E3E1;--serif:"IBM Plex Serif",Georgia,serif;--sans:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;--mono:"IBM Plex Mono",Menlo,Consolas,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--ground:#12171D;--surface:#1A2129;--ink:#E7EBEF;--muted:#9AA5B1;--line:#2C3641;--accent:#5FB6BF;--accent-soft:#193136;--ok:#6CC594;--ok-soft:#183024;--warn:#E0A94A;--warn-soft:#34291A;--crit:#F0857C;--crit-soft:#3A1F1E}}
:root[data-theme="dark"]{--ground:#12171D;--surface:#1A2129;--ink:#E7EBEF;--muted:#9AA5B1;--line:#2C3641;--accent:#5FB6BF;--accent-soft:#193136;--ok:#6CC594;--ok-soft:#183024;--warn:#E0A94A;--warn-soft:#34291A;--crit:#F0857C;--crit-soft:#3A1F1E}
*{box-sizing:border-box}body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.55}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1080px;margin:0 auto;padding:40px 28px 80px}
header{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:1px solid var(--line);padding-bottom:22px;margin-bottom:34px}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--serif);font-weight:600;font-size:38px;line-height:1.1;margin:6px 0 10px}
h2{font-family:var(--serif);font-weight:600;font-size:26px;margin:0 0 14px}
.stamp{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right;line-height:1.7}
section{margin-bottom:48px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:0 0 22px}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:14px 16px}
.kpi .n{font-family:var(--serif);font-size:30px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}
.kpi .l{font-size:12.5px;color:var(--muted);margin-top:6px}
.kpi.crit .n{color:var(--crit)}.kpi.warn .n{color:var(--warn)}.kpi.ok .n{color:var(--ok)}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.node{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:0 0 14px;overflow:hidden}
.node .stripe{height:5px;background:var(--line)}.node.crit .stripe{background:var(--crit)}.node.warn .stripe{background:var(--warn)}.node.ok .stripe{background:var(--ok)}.node.none .stripe{background:repeating-linear-gradient(90deg,var(--line) 0 8px,transparent 8px 14px)}
.node .body{padding:14px 18px 0}.node .name{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}.node .name b{font-family:var(--serif);font-size:19px;font-weight:600}.node .name code{font-family:var(--mono);font-size:12px;color:var(--muted)}
.node .role{font-size:13px;color:var(--muted);margin:4px 0 12px}
.meter{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}.meter div{font-family:var(--mono);font-size:12px;color:var(--muted)}.meter div b{display:block;font-size:14px;color:var(--ink);font-weight:500;font-variant-numeric:tabular-nums}.meter div.bad b{color:var(--crit)}.meter div.warn b{color:var(--warn)}
.node ul{margin:0;padding-left:18px;font-size:13.5px}.node li{margin:3px 0}.node li.c::marker{color:var(--crit)}.node li.w::marker{color:var(--warn)}.node li.g::marker{color:var(--ok)}
.pill{display:inline-block;font-family:var(--mono);font-size:11px;letter-spacing:.04em;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);vertical-align:middle}
.pill.crit{background:var(--crit-soft);color:var(--crit);border-color:transparent}.pill.warn{background:var(--warn-soft);color:var(--warn);border-color:transparent}.pill.ok{background:var(--ok-soft);color:var(--ok);border-color:transparent}.pill.acc{background:var(--accent-soft);color:var(--accent);border-color:transparent}
.tablewrap{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:6px}table{border-collapse:collapse;width:100%;font-size:13.5px}
th{font-family:var(--mono);font-weight:500;font-size:11.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:left;padding:10px 14px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:10px 14px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border-bottom:none}
code{font-family:var(--mono);font-size:12.5px;background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:3px}
.foot{border-top:1px solid var(--line);padding-top:16px;color:var(--muted);font-size:12.5px}
@media (max-width:860px){.kpis{grid-template-columns:repeat(2,1fr)}.grid{grid-template-columns:1fr}header{grid-template-columns:1fr}.stamp{text-align:left}h1{font-size:30px}}
"""


def _e(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _schwere(k: dict, alerts: list[dict]) -> str:
    if k["zustand"] == "geplant":
        return "none"
    if k["zustand"] != "gemessen":
        return "crit"
    if (
        (k.get("swap_pct") or 0) >= 90
        or (k.get("disk_pct") or 0) >= 90
        or k.get("restarting")
        or any(a["host"] == k["knoten"] and a["state"] == "firing" for a in alerts)
    ):
        return "crit"
    if (
        (k.get("swap_pct") or 0) >= 60
        or (k.get("disk_pct") or 0) >= 75
        or k.get("unhealthy")
    ):
        return "warn"
    return "ok"


def _knotenkarte(k: dict, dienste: dict, alerts: list[dict]) -> str:
    s = _schwere(k, alerts)
    kopf = f'<div class="name"><b>{_e(k["knoten"])}</b><code>{_e(k.get("ip") or "—")} · {_e(k.get("server_type") or "")} · {_e(k.get("provider") or "")}</code></div>'
    rolle = f'<div class="role">{_e(k["rolle"][:260])}{"…" if len(k["rolle"]) > 260 else ""}</div>'
    if k["zustand"] == "gemessen":
        sw = "—" if k.get("swap_pct") is None else f"{k['swap_pct']} %"
        cls_sw = (
            "bad"
            if (k.get("swap_pct") or 0) >= 90
            else ("warn" if (k.get("swap_pct") or 0) >= 60 else "")
        )
        cls_d = (
            "bad" if k["disk_pct"] >= 90 else ("warn" if k["disk_pct"] >= 75 else "")
        )
        meter = (
            f'<div class="meter"><div>Load / {k["kerne"]} K<b>{_e(k["load"].split()[0])}</b></div>'
            f'<div>RAM<b>{k["ram_pct"]} %</b></div><div class="{cls_sw}">Swap<b>{sw}</b></div>'
            f'<div class="{cls_d}">Platte /<b>{k["disk_pct"]} %</b></div></div>'
        )
        zeilen = [
            f'<li class="g">{k["container"]} von {k["container_gesamt"]} Containern laufen · Uptime {k["uptime_tage"]} d</li>'
        ]
        for u in k.get("unhealthy", []):
            zeilen.append(f'<li class="w">unhealthy: <code>{_e(u)}</code></li>')
        for r in k.get("restarting", []):
            zeilen.append(f'<li class="c">Restart-Schleife: <code>{_e(r)}</code></li>')
        for a in alerts:
            if a["host"] == k["knoten"]:
                zeilen.append(
                    f'<li class="{"c" if a["state"] == "firing" else "w"}">Alert {a["state"]}: {_e(a["name"])} {_e(a["name_"])}</li>'
                )
    else:
        meter = ""
        zeilen = [
            f'<li class="{"w" if k["zustand"] == "geplant" else "c"}">{_e(k["zustand"])}{": " + _e(k.get("grund", "")) if k.get("grund") else ""}</li>'
        ]
    d = dienste.get(k["knoten"], {})
    if d.get("aktiv"):
        zeilen.append(
            f'<li class="g">deklariert aktiv: {_e(", ".join(sorted(d["aktiv"])))}</li>'
        )
    if d.get("stillgelegt"):
        zeilen.append(
            f'<li class="w">stillgelegt: {_e(", ".join(sorted(d["stillgelegt"])))}</li>'
        )
    for feld, wert in (k.get("auflage") or {}).items():
        if feld != "grund" and wert is not True:
            zeilen.append(
                f'<li class="w">Auflage <code>{_e(feld)}</code>: {_e(wert)}</li>'
            )
    for h in (k.get("historie") or [])[-2:]:
        zeilen.append(f"<li>{_e(h)}</li>")
    ver = f"verified {_e(k['verified'])}" + (
        f" · bis {_e(k['verified_bis'])}" if k.get("verified_bis") else ""
    )
    return f'<div class="node {s}"><div class="stripe"></div><div class="body">{kopf}{rolle}{meter}<ul>{"".join(zeilen)}</ul><div class="eyebrow" style="margin-top:10px">{ver}</div></div></div>'


def render(d: dict) -> str:
    kn = d["knoten"]
    prom = d.get("prometheus", {})
    mel = d.get("melder", {})
    alerts = prom.get("alerts", []) if prom.get("zustand") == "gemessen" else []
    gemessen = [k for k in kn if k["zustand"] == "gemessen"]
    nicht = [k for k in kn if k["zustand"] not in ("gemessen", "geplant")]
    firing = [a for a in alerts if a["state"] == "firing"]
    j = mel.get("journal", {})
    aw = mel.get("alarmwege", {})
    kan = aw.get("kanaele", [])
    ok_kan = sum(1 for k in kan if k["ok"])
    targets = prom.get("targets", [])
    t_up = sum(1 for t in targets if t["health"] == "up")

    def kpi(n, text, cls=""):
        return f'<div class="kpi {cls}"><div class="n">{n}</div><div class="l">{_e(text)}</div></div>'

    kpis = "".join(
        [
            kpi(
                f"{len(gemessen)} / {len(kn)}",
                "Knoten gemessen (Nenner: hosts.yaml)",
                "ok" if not nicht else "crit",
            ),
            kpi(
                f"{len(firing)}",
                "Alerts feuern (Prometheus)",
                "ok" if not firing else "crit",
            )
            if prom.get("zustand") == "gemessen"
            else kpi("?", "Prometheus nicht lesbar — keine Entwarnung", "crit"),
            kpi(
                f"{j.get('im_gate', '?')} / {j.get('gesamt', '?')}",
                f"Befunde im Gate / offen · {j.get('ueberfaellig', '?')} überfällig · {j.get('mit_kommando', '?')} mit Kommando",
                "warn" if j.get("im_gate") else "ok",
            ),
            kpi(
                f"{ok_kan} / {len(kan)}",
                "Alarmwege belegt",
                "ok" if kan and ok_kan == len(kan) else "crit",
            ),
        ]
    )
    karten = "".join(_knotenkarte(k, d["dienste_je_host"], alerts) for k in kn)
    trow = "".join(
        f'<tr><td>{_e(t["job"])}</td><td>{_e(t["host"])}</td><td><span class="pill {"ok" if t["health"] == "up" else "crit"}">{_e(t["health"])}</span></td></tr>'
        for t in targets
    )
    krow = "".join(
        f'<tr><td>{_e(k["kanal"])}</td><td><span class="pill {"ok" if k["ok"] else ("warn" if k["blind"] else "crit")}">{"belegt" if k["ok"] else ("blind" if k["blind"] else "fehlt")}</span></td><td>{_e(k["grund"])}</td></tr>'
        for k in kan
    )
    jrow = "".join(
        f"<tr><td><code>{_e(e['id'])}</code></td><td>{e['laeufe']}</td><td>{"<span class='pill warn'>im Gate</span>" if e['im_gate'] else ''}{" <span class='pill crit'>überfällig</span>" if e['ueberfaellig'] else ''}</td><td>{_e(e['note'])}</td></tr>"
        for e in j.get("eintraege", [])
    )
    melder = (
        f"<p>Erreichbarkeit: <code>{_e(mel.get('erreichbarkeit', {}).get('kurz', '?'))}</code> · hosts_audit: "
        f"<code>{_e(mel.get('hosts_audit', {}).get('kurz', '?'))}</code></p>"
    )
    nicht_html = "".join(
        f"<li><b>{_e(k['knoten'])}</b>: {_e(k['zustand'])} — {_e(k.get('grund', ''))}</li>"
        for k in nicht
    )
    return f"""<title>IIL-Flottenbild</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header><div><div class="eyebrow">Infrastruktur · generiert aus den Quellen</div><h1>IIL-Flottenbild</h1>
<p style="max-width:62ch;color:var(--muted);margin:0">Jeder Wert auf dieser Seite stammt aus einer Quelle, die genannt ist — hosts.yaml, ports.yaml, ein ssh-Kommando je Knoten, Prometheus, das Befund-Journal. Was nicht erreichbar war, steht als eigener Zustand da.</p></div>
<div class="stamp">Stand {_e(d["stand"])}<br>tools/flottenbild.py · KONZ-054<br>Auftrag <a href="https://github.com/achimdehnert/platform/issues/2483">platform#2483</a></div></header>
<section><div class="kpis">{kpis}</div>{melder}{('<p class="pill crit">Nicht gemessen:</p><ul>' + nicht_html + "</ul>") if nicht else ""}</section>
<section><h2>Knoten</h2><div class="grid">{karten}</div></section>
<section><h2>Prometheus</h2>{('<div class="tablewrap"><table><thead><tr><th>Job</th><th>Knoten</th><th>Health</th></tr></thead><tbody>' + trow + "</tbody></table></div><p>" + str(t_up) + " von " + str(len(targets)) + " Targets up · " + str(len(alerts)) + " Alerts (" + str(len(firing)) + " feuern)</p>") if prom.get("zustand") == "gemessen" else '<p class="pill crit">Prometheus ' + _e(prom.get("zustand")) + ": " + _e(prom.get("grund", "")) + "</p>"}</section>
<section><h2>Alarmwege</h2><div class="tablewrap"><table><thead><tr><th>Kanal</th><th>Stand</th><th>Grund</th></tr></thead><tbody>{krow}</tbody></table></div></section>
<section><h2>Befund-Journal</h2><div class="tablewrap"><table><thead><tr><th>Befund</th><th>Läufe</th><th></th><th>Note</th></tr></thead><tbody>{jrow}</tbody></table></div></section>
<p class="foot">Generiert von <code>tools/flottenbild.py</code>. Nenner ist immer hosts.yaml: ein Knoten, der nicht antwortet, fehlt nicht — er steht als „unerreichbar" da. Handbuch für neue Knoten: docs/runbooks/neuer-knoten.md.</p>
</div>
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--out", type=Path, help="HTML-Ausgabe")
    p.add_argument("--json", type=Path, help="Rohdaten als JSON")
    p.add_argument(
        "--offline", type=Path, help="nur rendern: Rohdaten aus dieser JSON-Datei"
    )
    p.add_argument("--nur", action="append", help="nur diese Knoten messen")
    a = p.parse_args(argv)
    daten = (
        json.loads(a.offline.read_text(encoding="utf-8"))
        if a.offline
        else sammle(a.nur)
    )
    if a.json:
        a.json.write_text(
            json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8"
        )
    seite = render(daten)
    if a.out:
        a.out.write_text(seite, encoding="utf-8")
    kn = daten["knoten"]
    gem = sum(1 for k in kn if k["zustand"] == "gemessen")
    print(
        f"Flottenbild: {gem} von {len(kn)} Knoten gemessen · Prometheus {daten.get('prometheus', {}).get('zustand')} · "
        f"Journal {daten.get('melder', {}).get('journal', {}).get('im_gate', '?')} im Gate"
        + (f" · HTML {a.out}" if a.out else "")
    )
    return 0 if gem == sum(1 for k in kn if k["zustand"] != "geplant") else 1


if __name__ == "__main__":
    sys.exit(main())
