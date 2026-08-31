#!/usr/bin/env python3
"""alarmweg_probe.py — ein Kanal existiert erst, wenn er nachweislich einen Menschen erreicht.

KONZ-platform-054 E4. Gemessen am 2026-08-30: der lauteste Melder der Flotte
schrieb 177 Tage lang an `| mail` ohne MTA; ein Zertifikats-Melder an einen
auskommentierten Webhook mit `|| true`; drei Workflows dieses Repos an ein
Discord-Secret, das es nicht gibt. Gemeinsam ist allen: der Kanal galt als
vorhanden, weil ein Skript ihn NANNTE. Dieses Werkzeug dreht die Beweislast um.

Zwei Betriebsarten:

  --senden --kanal ID     Probealarm ueber den Kanal schicken. Scheitert HART bei
                          fehlendem Secret oder Nicht-2xx — genau der Fehler, den
                          `|| true` bisher verschluckt hat. Laeuft im Workflow
                          .github/workflows/alarmweg-probe.yml, ein Job je Kanal.
  --pruefen [--kurz]      Melder: fuer jeden Kanal im Register den juengsten
                          erfolgreichen Probe-Job lesen (gh api). Aelter als
                          max_alter_tage, fehlgeschlagen, oder Kanal ohne Probe
                          => der Kanal gilt als NICHT vorhanden.

Exit-Codes (--pruefen):
    0  jeder Kanal hat einen frischen, erfolgreichen Beleg
    1  mindestens ein Kanal ohne Beleg — er ist fuer die Flotte nicht da
    2  blind: gh nicht erreichbar / Register nicht lesbar — KEINE Entwarnung

Bewusst NICHT hier: die Alarme selbst. Das Werkzeug beweist den Weg, es geht
ihn nicht fuer andere.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import yaml

REGISTER = Path(__file__).resolve().parents[1] / "infra" / "alarmwege.yaml"
WORKFLOW = "alarmweg-probe.yml"
REPO = "achimdehnert/platform"
PROBE_LABEL = "alarmweg-probe"

EXIT_OK, EXIT_BEFUND, EXIT_BLIND = 0, 1, 2


def lade_register(pfad: Path = REGISTER) -> dict[str, dict]:
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
    kanaele = daten.get("kanaele") or {}
    if not isinstance(kanaele, dict):
        raise ValueError("alarmwege.yaml: 'kanaele' ist kein Mapping")
    return kanaele


# ── Senden ───────────────────────────────────────────────────────────────────


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def sende_discord(text: str, webhook: str | None) -> None:
    """POST an den Webhook. Kein Fallback, kein `|| true`: ein fehlendes Secret
    ist die Antwort, nicht ein Sonderfall."""
    if not webhook:
        raise RuntimeError("DISCORD_WEBHOOK nicht gesetzt — der Kanal existiert nicht")
    daten = json.dumps({"content": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook, data=daten, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as antwort:  # noqa: S310
        if not 200 <= antwort.status < 300:
            raise RuntimeError(f"Discord antwortete {antwort.status}")


def sende_github_issue(text: str, assignee: str, repo: str = REPO) -> str:
    """Issue anlegen UND sofort schliessen. Die Zuweisung ist die Zustellung —
    ein geschlossenes Issue benachrichtigt trotzdem. Gibt die Issue-URL zurueck."""
    subprocess.run(
        [
            "gh",
            "api",
            f"repos/{repo}/labels",
            "-f",
            f"name={PROBE_LABEL}",
            "-f",
            "color=6a737d",
            "-f",
            "description=KONZ-054 E4: Probealarm, beweist den Kanal",
        ],
        capture_output=True,
        check=False,
    )
    erzeugt = subprocess.run(
        [
            "gh",
            "issue",
            "create",
            "-R",
            repo,
            "--title",
            f"Probealarm {_jetzt().date()}",
            "--label",
            PROBE_LABEL,
            "--assignee",
            assignee,
            "--body",
            text,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    url = erzeugt.stdout.strip().splitlines()[-1]
    subprocess.run(
        [
            "gh",
            "issue",
            "close",
            url,
            "--comment",
            "Probealarm zugestellt — geschlossen vom Werkzeug selbst (tools/alarmweg_probe.py).",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return url


def senden(kanal_id: str, kanaele: dict[str, dict]) -> str:
    k = kanaele.get(kanal_id)
    if k is None:
        raise KeyError(f"Kanal '{kanal_id}' nicht im Register")
    if k.get("probe") != "workflow":
        raise RuntimeError(
            f"Kanal '{kanal_id}' hat probe={k.get('probe')!r} — nicht sendbar"
        )
    text = (
        f"🔔 Probealarm {_jetzt().strftime('%Y-%m-%d %H:%M')} UTC — Kanal `{kanal_id}` "
        f"lebt. Ohne diesen Beleg gilt er als nicht vorhanden (KONZ-054 E4)."
    )
    art = k.get("art")
    if art == "discord-webhook":
        sende_discord(text, os.environ.get("DISCORD_WEBHOOK"))
        return "Discord: 2xx"
    if art == "github-issue":
        return "Issue: " + sende_github_issue(
            text, os.environ.get("ALARMWEG_ASSIGNEE", "achimdehnert")
        )
    raise RuntimeError(f"Kanal-Art '{art}' kann nicht gesendet werden")


# ── Pruefen ──────────────────────────────────────────────────────────────────


def letzte_probe_jobs(
    repo: str = REPO, workflow: str = WORKFLOW, limit: int = 10
) -> list[dict] | None:
    """Jobs der juengsten Probe-Laeufe: [{kanal, conclusion, completed_at}]. None = blind."""
    try:
        laeufe = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "-R",
                repo,
                "--workflow",
                workflow,
                "-L",
                str(limit),
                "--json",
                "databaseId,conclusion,createdAt",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        runs = json.loads(laeufe.stdout or "[]")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None
    jobs: list[dict] = []
    for run in runs:
        try:
            r = subprocess.run(
                [
                    "gh",
                    "api",
                    f"repos/{repo}/actions/runs/{run['databaseId']}/jobs",
                    "--jq",
                    "[.jobs[]|{name:.name,conclusion:.conclusion,completed_at:.completed_at}]",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            for j in json.loads(r.stdout or "[]"):
                jobs.append(
                    {
                        "kanal": j["name"],
                        "conclusion": j["conclusion"],
                        "completed_at": j["completed_at"],
                    }
                )
        except (subprocess.SubprocessError, json.JSONDecodeError, OSError, KeyError):
            continue
    return jobs


def beurteile(
    kanaele: dict[str, dict], jobs: list[dict] | None, jetzt: datetime
) -> list[dict]:
    """Je Kanal: vorhanden | fehlt, mit Grund. Pure Funktion, testbar."""
    aus = []
    for kid, k in kanaele.items():
        max_tage = int(k.get("max_alter_tage", 10))
        # Ein bewusst abgeschalteter Kanal ist keine Luecke — aber nur, wenn der
        # Rueckbau BELEGT ist. Ohne `zurueckgebaut_am` UND `ersetzt_durch` waere
        # `probe: zurueckgebaut` ein bequemer Stummschalter, und die Zahl
        # "N von M belegt" liesse sich durch Umschreiben gruen machen statt durch
        # Arbeit. Dieselbe Absicherung wie `betriebsstatus_grund` in ports.yaml.
        if k.get("probe") == "zurueckgebaut":
            am = k.get("zurueckgebaut_am")
            ersatz = k.get("ersetzt_durch")
            if am and ersatz:
                aus.append(
                    {
                        "kanal": kid,
                        "vorhanden": True,
                        "zurueckgebaut": True,
                        "grund": f"zurueckgebaut {am}, ersetzt durch {ersatz}",
                    }
                )
            else:
                aus.append(
                    {
                        "kanal": kid,
                        "vorhanden": False,
                        "grund": "als zurueckgebaut deklariert, aber ohne "
                        "zurueckgebaut_am/ersetzt_durch — unbelegt",
                    }
                )
            continue
        if k.get("probe") != "workflow":
            aus.append(
                {
                    "kanal": kid,
                    "vorhanden": False,
                    "grund": "keine Probe — ein Kanal ohne Beweis ist keiner",
                }
            )
            continue
        if jobs is None:
            aus.append(
                {
                    "kanal": kid,
                    "vorhanden": None,
                    "grund": "blind: Probe-Laeufe nicht lesbar",
                }
            )
            continue
        erfolge = []
        for j in jobs:
            if (
                j.get("kanal") != kid
                or j.get("conclusion") != "success"
                or not j.get("completed_at")
            ):
                continue
            try:
                erfolge.append(
                    datetime.fromisoformat(
                        str(j["completed_at"]).replace("Z", "+00:00")
                    )
                )
            except ValueError:
                continue
        if not erfolge:
            letzter = next((j for j in jobs if j.get("kanal") == kid), None)
            grund = (
                f"letzte Probe {letzter.get('conclusion')}"
                if letzter
                else "noch nie geprobt"
            )
            aus.append({"kanal": kid, "vorhanden": False, "grund": grund})
            continue
        alter = (jetzt - max(erfolge)).days
        if alter > max_tage:
            aus.append(
                {
                    "kanal": kid,
                    "vorhanden": False,
                    "grund": f"letzter Erfolg vor {alter} d (> {max_tage} d)",
                }
            )
        else:
            aus.append(
                {"kanal": kid, "vorhanden": True, "grund": f"Erfolg vor {alter} d"}
            )
    return aus


def exit_code(urteile: list[dict]) -> int:
    if any(u["vorhanden"] is None for u in urteile):
        return EXIT_BLIND
    return EXIT_BEFUND if any(u["vorhanden"] is False for u in urteile) else EXIT_OK


def kurzzeile(urteile: list[dict]) -> str:
    fehlt = [u for u in urteile if u["vorhanden"] is False]
    blind = [u for u in urteile if u["vorhanden"] is None]
    rueckbau = [u for u in urteile if u.get("zurueckgebaut")]
    # Zurueckgebaute zaehlen nicht in den Nenner: sonst waere "4 von 6 belegt"
    # dauerhaft rot fuer Kanaele, die es absichtlich nicht mehr gibt.
    n = len(urteile) - len(rueckbau)
    anhang = f" · {len(rueckbau)} zurueckgebaut" if rueckbau else ""
    if blind:
        return f"blind: {len(blind)} von {n} Kanaelen nicht pruefbar — keine Entwarnung{anhang}"
    if not fehlt:
        return f"{n} von {n} Alarmwegen belegt{anhang}"
    return (
        f"{len(fehlt)} von {n} Alarmwegen NICHT vorhanden{anhang} — "
        + "; ".join(f"{u['kanal']} ({u['grund']})" for u in fehlt)
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--senden", action="store_true")
    p.add_argument("--kanal", help="Kanal-ID aus infra/alarmwege.yaml")
    p.add_argument("--pruefen", action="store_true")
    p.add_argument("--kurz", action="store_true")
    p.add_argument("--register", type=Path, default=REGISTER)
    a = p.parse_args(argv)

    try:
        kanaele = lade_register(a.register)
    except (OSError, ValueError, yaml.YAMLError) as fehler:
        print(f"blind: Register nicht lesbar ({fehler})", file=sys.stderr)
        return EXIT_BLIND

    if a.senden:
        if not a.kanal:
            print("--senden braucht --kanal", file=sys.stderr)
            return 2
        try:
            print(f"gesendet ueber {a.kanal}: {senden(a.kanal, kanaele)}")
            return 0
        except Exception as fehler:  # noqa: BLE001 — jede Ursache ist der Befund
            print(f"Probealarm ueber {a.kanal} GESCHEITERT: {fehler}", file=sys.stderr)
            return 1

    urteile = beurteile(kanaele, letzte_probe_jobs(), _jetzt())
    if a.kurz:
        print(kurzzeile(urteile))
    else:
        print("Alarmwege (KONZ-054 E4 — ein Kanal ohne frischen Beleg ist keiner):")
        for u in urteile:
            marke = {True: "✅", False: "❌", None: "◌"}[u["vorhanden"]]
            print(f"  {marke} {u['kanal']:<26} {u['grund']}")
    return exit_code(urteile)


if __name__ == "__main__":
    sys.exit(main())
