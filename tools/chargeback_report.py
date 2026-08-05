#!/usr/bin/env python3
"""Kostenumlage je Anwendung aus dem Container-Speicherverbrauch (ADR-292).

Motivation: Selten genutzte Hubs sollen kostenmaessig zurechenbar werden, OHNE
sie auf eigene Server zu verteilen. Ein eigener Kleinserver kostet mindestens
rund 5 EUR/Monat und erzeugt Pflegeaufwand je Stueck; der gemessene Anteil einer
kleinen App auf einem Bestandshost liegt deutlich darunter. Statt zu trennen
wird also gemessen und umgelegt.

Rechenweg (Vollkostenumlage nach Speicheranteil):

    Anteil(App)  = RAM(App) / Summe RAM aller Apps auf dem Host
    Kosten(App)  = Hostpreis * Anteil(App)

Der Hostpreis wird VOLLSTAENDIG verteilt. Leerstand und Gemeinkosten-Container
(Monitoring-Exporter) tragen die Apps damit anteilig mit -- das ist gewollt:
der Host wird bezahlt, ob er ausgelastet ist oder nicht. Die Auslastung wird
separat ausgewiesen, damit sichtbar bleibt, wie viel Umlage auf Leerstand
entfaellt.

Grenze, die beim Verrechnen nach aussen genannt werden muss: das ist eine
Umlage, keine Verursachungsrechnung. Ein leerlaufender Container verursacht real
kaum Kosten, bekommt hier aber seinen Speicheranteil zugeteilt.

Eingabe ist eine JSON-Datei (Erhebung siehe --help-collect), damit die Rechnung
ohne Netzzugriff testbar bleibt.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Container-Namen folgen dem Muster <app>_<rolle>. Rollen werden abgeschnitten,
# um vom Container auf die Anwendung zu schliessen. Laengere Suffixe zuerst,
# sonst verkuerzt "_orchestrator_http" faelschlich auf "_http".
ROLE_SUFFIXES = (
    "_orchestrator_http",
    "_node_exporter",
    "_postgres_exporter",
    "_celery_beat",
    "_cadvisor",
    "_worker",
    "_celery",
    "_beat",
    "_minio",
    "_redis",
    "_web",
    "_db",
)

# Container, die keiner Anwendung gehoeren, sondern dem Betrieb des Hosts.
# Ihr Verbrauch wird als Gemeinkosten ausgewiesen und ueber die Umlage
# automatisch mitverteilt (sie zaehlen nicht als eigene "App").
INFRA_PREFIXES = ("mon_",)


def app_of(container: str) -> str:
    """Leitet den Anwendungs-Slug aus einem Container-Namen ab.

    >>> app_of("risk_hub_web")
    'risk-hub'
    >>> app_of("mcp_hub_orchestrator_http")
    'mcp-hub'
    >>> app_of("solo")
    'solo'
    """
    for suffix in ROLE_SUFFIXES:
        if container.endswith(suffix):
            return container[: -len(suffix)].replace("_", "-")
    return container.replace("_", "-")


def is_infra(container: str) -> bool:
    return container.startswith(INFRA_PREFIXES)


def parse_mem(value: str | float) -> float:
    """Wandelt eine docker-stats-Speicherangabe in MiB.

    Akzeptiert bereits numerische Werte unveraendert, sonst Strings wie
    "451.8MiB", "1.5GiB", "512KiB".

    >>> parse_mem("1.5GiB")
    1536.0
    >>> parse_mem("451.8MiB")
    451.8
    """
    if isinstance(value, (int, float)):
        return float(value)
    text = value.strip()
    for unit, factor in (
        ("GiB", 1024.0),
        ("MiB", 1.0),
        ("KiB", 1 / 1024.0),
        ("B", 1 / 1048576.0),
    ):
        if text.endswith(unit):
            return float(text[: -len(unit)]) * factor
    raise ValueError(f"unbekannte Speicherangabe: {value!r}")


def compute(data: dict) -> list[dict]:
    """Rechnet die Umlage je Host und Anwendung.

    Erwartet {"hosts": {"<name>": {"price_eur_month": float, "ram_gib": float,
    "containers": {"<container>": "<mem>"}}}}.
    """
    rows: list[dict] = []
    for host, spec in sorted(data["hosts"].items()):
        price = float(spec["price_eur_month"])
        per_app: dict[str, float] = {}
        infra_mib = 0.0
        for container, mem in spec["containers"].items():
            mib = parse_mem(mem)
            if is_infra(container):
                infra_mib += mib
                continue
            per_app[app_of(container)] = per_app.get(app_of(container), 0.0) + mib

        app_total = sum(per_app.values())
        if app_total <= 0:
            continue
        host_mib = float(spec.get("ram_gib", 0)) * 1024.0
        for app, mib in sorted(per_app.items(), key=lambda kv: -kv[1]):
            rows.append(
                {
                    "host": host,
                    "app": app,
                    "ram_mib": round(mib, 1),
                    "share_pct": round(100.0 * mib / app_total, 2),
                    "eur_month": round(price * mib / app_total, 2),
                }
            )
        rows.append(
            {
                "host": host,
                "app": "_SUMME",
                "ram_mib": round(app_total, 1),
                "share_pct": 100.0,
                "eur_month": round(price, 2),
                "infra_mib": round(infra_mib, 1),
                "belegt_pct": round(100.0 * (app_total + infra_mib) / host_mib, 1)
                if host_mib
                else None,
            }
        )
    return rows


def to_markdown(rows: list[dict]) -> str:
    out: list[str] = []
    for host in sorted({r["host"] for r in rows}):
        summe = next(r for r in rows if r["host"] == host and r["app"] == "_SUMME")
        out.append(f"### {host} — {summe['eur_month']:.2f} EUR/Monat brutto")
        out.append("")
        belegt = summe.get("belegt_pct")
        if belegt is not None:
            out.append(
                f"Belegt: {belegt} % des Hostspeichers "
                f"(davon {summe.get('infra_mib', 0)} MiB Monitoring-Gemeinkosten). "
                "Der Rest ist Leerstand und wird anteilig mitumgelegt."
            )
            out.append("")
        out.append("| Anwendung | RAM (MiB) | Anteil | EUR/Monat |")
        out.append("|---|---:|---:|---:|")
        for r in rows:
            if r["host"] != host or r["app"] == "_SUMME":
                continue
            out.append(
                f"| {r['app']} | {r['ram_mib']:.0f} | {r['share_pct']:.1f} % | {r['eur_month']:.2f} |"
            )
        out.append("")
    return "\n".join(out)


COLLECT_HELP = """\
Erhebung (read-only, je Host):

    ssh root@<host> 'docker stats --no-stream --format "{{.Name}}|{{.MemUsage}}"'

Die linke Haelfte von MemUsage (vor dem "/") ist der belegte Speicher. Preis und
RAM je Host aus der Hetzner-API (/v1/servers -> server_type.prices[].price_monthly.gross).

Sobald die Fleet-Scrape-Ziele UP sind (siehe infra/monitoring/README.md), kann
dieselbe Rechnung gegen PromQL laufen und dann Zeitreihen statt einer
Momentaufnahme verwenden:

    avg_over_time(container_memory_working_set_bytes{name=~".+"}[30d])
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("input", nargs="?", type=Path, help="JSON-Datei mit der Erhebung")
    ap.add_argument(
        "--json", action="store_true", help="Rohdaten statt Markdown ausgeben"
    )
    ap.add_argument(
        "--help-collect",
        action="store_true",
        help="zeigt, wie die Eingabe erhoben wird",
    )
    args = ap.parse_args(argv)

    if args.help_collect:
        print(COLLECT_HELP)
        return 0
    if not args.input:
        ap.error("Eingabedatei fehlt (oder --help-collect)")

    rows = compute(json.loads(args.input.read_text(encoding="utf-8")))
    print(
        json.dumps(rows, indent=2, ensure_ascii=False)
        if args.json
        else to_markdown(rows)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
