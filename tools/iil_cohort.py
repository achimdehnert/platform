#!/usr/bin/env python3
"""iil_cohort — zentral erzeugte iil-Dependency-Cohort (ADR-234 P0.5a, KONZ-platform-052 V11).

Eine Kohorte ist eine pip-constraints-Datei `constraints/iil-cohort-<YYYY.MM>.txt`, die
JEDES iil-Paket der Flotte auf **genau eine** Version festnagelt, zusammen mit einem
**Supportfenster** (`support_until`). Konsumenten (dev-hub, mcp-hub, …) pinnen dann die
Kohorte statt fuenf Einzelpakete:

    pip install -c constraints/iil-cohort-latest.txt -r requirements.txt

Warum das der Primaer-Hebel ist (ADR-234 P0.5a): Dependency-Kohaerenz **vor** Enforcement.
Ohne eine gemeinsame Version-Menge haertet die clean-state-Invariante nur die ohnehin
gesunden Repos.

Quellen (bewusst zwei, mit klarer Rollenteilung):
  * `registry/canonical.yaml` ueber `tools/registry_api.py` — die **Entscheidung**
    (`pypi_strategy: aktiv | einfrieren | archivieren-kandidat`). Nie die View-Dateien
    direkt lesen (ADR-234 §11.1, Gate `tools/check_registry_view_readers.py`).
  * `registry/pypi-fleet.yaml` (erzeugt von `tools/pypi_fleet_inventory.py`) — der
    **Dist-Name** auf PyPI. Die Registry fuehrt Kurznamen (`aifw`), PyPI kennt
    `iil-aifw`; nur das Inventar traegt die Abbildung.
  * PyPI JSON-API — die **aktuelle Version** und ihr Upload-Datum.

Strategie-Semantik in der Kohorte:
  * `aktiv`              → Pin auf die aktuelle PyPI-Version (rollt mit jeder Kohorte).
  * `einfrieren`         → Pin auf die aktuelle PyPI-Version, markiert als eingefroren
                           (bewusst kein Bump; die Zeile dokumentiert den Einfrierpunkt).
  * `archivieren-kandidat` → gar nicht in der Kohorte.

Fail-soft, aber laut (Netz):
  * **Keine Antwort** (Timeout, 5xx, DNS) = `unbekannt` → die Kohorte wird **NICHT**
    geschrieben, Exit 3. Eine halbe Kohorte ist schlimmer als keine: sie sieht
    vollstaendig aus.
  * **404** ist eine Antwort ("dieses Paket gibt es auf PyPI nicht") und darf die
    Kohorte nicht blockieren — sonst waere sie wegen zweier nie veroeffentlichter
    Pakete dauerhaft unerzeugbar. Solche Pakete werden ausgeschlossen und im Header
    der Kohorte **namentlich** aufgefuehrt (kein stiller Drop). Mit `--strict-missing`
    zaehlt auch 404 als Fehler (Exit 3).

Subcommands:
    python3 tools/iil_cohort.py build            # Kohorte erzeugen + latest-Zeiger
    python3 tools/iil_cohort.py check --file …   # installierbar? (pip --dry-run, tmp-venv)
    python3 tools/iil_cohort.py age              # Alterungs-Signal, Exit 2 wenn abgelaufen

Das Alterungs-Signal ist bewusst **kein neuer Melder**: `age` haengt als eine Zeile im
bestehenden Wochenreport `.github/workflows/pypi-fleet-health.yml` (KONZ-052 subtrahiert
Melder, es fuegt keine hinzu).

Design-Regeln: stdlib + yaml, read-only gegen die Flotte, reine Funktionen getestet in
`tools/tests/test_iil_cohort.py`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

TOOLS_DIR = Path(__file__).resolve().parent
PLATFORM_DIR = TOOLS_DIR.parent
CONSTRAINTS_DIR = PLATFORM_DIR / "constraints"
FLEET_FILE = PLATFORM_DIR / "registry" / "pypi-fleet.yaml"
LATEST_NAME = "iil-cohort-latest.txt"

sys.path.insert(0, str(TOOLS_DIR))
import registry_api  # noqa: E402

# ADR-234 nennt fuer P0.5a ein Supportfenster/Deprecation-Datum (M28-8), aber KEINE Zahl.
# 60 Tage ist das Band, in dem ADR-234 §Fristen die naechste Stufe (R1 → P0.5b) erwartet
# (Z. 193) — eine Kohorte soll nicht laenger leben als der Zyklus, der sie ablaest.
# Ueberschreibbar per --support-days; der gewaehlte Wert steht IM Kohorten-Header.
SUPPORT_DAYS_DEFAULT = 60

PYPI_JSON = "https://pypi.org/pypi/{name}/json"
STRATEGY_IN_COHORT = ("aktiv", "einfrieren")

HEADER_PREFIX = "# "


# --------------------------------------------------------------------------
# Datenmodell
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """Ein Kohorten-Kandidat: Repo + Registry-Strategie + PyPI-Dist-Name."""

    repo: str
    dist_name: str
    strategy: str


@dataclass(frozen=True)
class Resolution:
    """Antwort von PyPI zu einem Kandidaten.

    state: ok | missing | unknown
      ok      — Version + Upload-Datum ermittelt
      missing — PyPI hat geantwortet: Paket existiert dort nicht (404)
      unknown — PyPI hat NICHT geantwortet (Timeout/5xx/DNS/Parsefehler)
    """

    candidate: Candidate
    state: str
    version: str | None = None
    released: str | None = None
    detail: str = ""


@dataclass(frozen=True)
class Pin:
    """Eine geparste Kohorten-Zeile."""

    name: str
    version: str
    strategy: str
    released: str | None


# --------------------------------------------------------------------------
# Reine Funktionen (getestet ohne Netz)
# --------------------------------------------------------------------------


def cohort_label(day: date) -> str:
    """Kohorten-Kennung `YYYY.MM` — eine Kohorte je Kalendermonat."""
    return f"{day.year:04d}.{day.month:02d}"


def support_until(generated: date, days: int = SUPPORT_DAYS_DEFAULT) -> date:
    """Ende des Supportfensters (Erzeugung + `days` Tage, ADR-234 M28-8)."""
    return generated + timedelta(days=days)


def collect_candidates(flat_repos: dict, fleet_packages: dict) -> list[Candidate]:
    """Kohorten-Kandidaten aus Registry (Strategie) + Fleet-Inventar (Dist-Name).

    Join ueber den Repo-Namen. Ein Repo mit `pypi_strategy` aber ohne Fleet-Eintrag
    faellt auf den Registry-Kurznamen zurueck — dann ist der Dist-Name eine Annahme,
    die PyPI im naechsten Schritt bestaetigt oder mit 404 widerlegt.
    """
    by_repo = {}
    for entry in (fleet_packages or {}).values():
        repo = (entry or {}).get("repo")
        if repo:
            by_repo[repo] = entry

    out: list[Candidate] = []
    for repo, entry in sorted((flat_repos or {}).items()):
        entry = entry or {}
        registry_name = entry.get("pypi")
        strategy = entry.get("pypi_strategy")
        if not registry_name or strategy not in STRATEGY_IN_COHORT:
            continue
        dist = (by_repo.get(repo) or {}).get("dist_name") or registry_name
        out.append(Candidate(repo=repo, dist_name=dist, strategy=strategy))
    return sorted(out, key=lambda c: c.dist_name)


def render_cohort(
    label: str,
    generated: date,
    until: date,
    support_days: int,
    resolutions: list[Resolution],
) -> str:
    """Rendert die constraints-Datei. Erwartet, dass KEIN `unknown` enthalten ist."""
    ok = [r for r in resolutions if r.state == "ok"]
    missing = [r for r in resolutions if r.state == "missing"]
    n_aktiv = sum(1 for r in ok if r.candidate.strategy == "aktiv")
    n_frozen = sum(1 for r in ok if r.candidate.strategy == "einfrieren")

    lines = [
        f"# iil-Dependency-Cohort {label}",
        "#",
        "# Zentral erzeugt — NICHT von Hand editieren.",
        "#   regenerieren: python3 tools/iil_cohort.py build",
        "#   pruefen:      python3 tools/iil_cohort.py check --file <diese Datei>",
        "#   Alter:        python3 tools/iil_cohort.py age",
        "#",
        "# Verwendung im Konsumenten (statt Einzel-Obergrenzen je iil-Paket):",
        "#   pip install -c constraints/iil-cohort-latest.txt -r requirements.txt",
        "#",
        f"{HEADER_PREFIX}cohort: {label}",
        f"{HEADER_PREFIX}generated_at: {generated.isoformat()}",
        f"{HEADER_PREFIX}support_days: {support_days}",
        f"{HEADER_PREFIX}support_until: {until.isoformat()}",
        f"{HEADER_PREFIX}source: registry/canonical.yaml (pypi_strategy) "
        "+ registry/pypi-fleet.yaml (dist_name) + pypi.org JSON-API",
        f"{HEADER_PREFIX}tool: tools/iil_cohort.py (ADR-234 P0.5a, KONZ-platform-052 V11)",
        f"{HEADER_PREFIX}packages: {len(ok)} ({n_aktiv} aktiv, {n_frozen} eingefroren)",
    ]
    if missing:
        names = ", ".join(
            f"{r.candidate.dist_name} ({r.candidate.strategy})" for r in missing
        )
        lines += [
            f"{HEADER_PREFIX}excluded_not_on_pypi: {names}",
            "#   ^ PyPI antwortet 404: Paket ist dort nie erschienen. Bewusst ausgeschlossen",
            "#     statt still gedroppt — Registry und PyPI widersprechen sich hier.",
        ]
    lines.append("#")

    for r in ok:
        note = f"strategy={r.candidate.strategy}"
        if r.released:
            note += f", released={r.released}"
        lines.append(f"{r.candidate.dist_name}=={r.version}  # {note}")

    return "\n".join(lines) + "\n"


def parse_cohort(text: str) -> tuple[dict[str, str], list[Pin]]:
    """Liest Header-Felder (`# key: value`) und Pins aus einer Kohorten-Datei."""
    header: dict[str, str] = {}
    pins: list[Pin] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            body = line[1:].strip()
            if ": " in body and not body.startswith("^"):
                key, _, value = body.partition(": ")
                key = key.strip()
                if key and " " not in key:
                    header.setdefault(key, value.strip())
            continue
        spec, _, comment = line.partition("#")
        spec = spec.strip()
        if "==" not in spec:
            continue
        name, _, version = spec.partition("==")
        meta = {}
        for part in comment.split(","):
            k, _, v = part.strip().partition("=")
            if v:
                meta[k.strip()] = v.strip()
        pins.append(
            Pin(
                name=name.strip(),
                version=version.strip(),
                strategy=meta.get("strategy", ""),
                released=meta.get("released"),
            )
        )
    return header, pins


def age_days(until: date, today: date) -> int:
    """Verbleibende Support-Tage. Negativ = seit so vielen Tagen abgelaufen."""
    return (until - today).days


def format_age_line(label: str, days: int) -> str:
    """Die EINE Zeile fuer den Wochenreport (KONZ-052 V11: kein neuer Melder)."""
    if days < 0:
        return f"Kohorte {label}: ABGELAUFEN (seit {abs(days)} Tagen)"
    return f"Kohorte {label}: {days} Tage Support"


# --------------------------------------------------------------------------
# Netz
# --------------------------------------------------------------------------


def fetch_pypi(name: str, timeout: int = 20) -> tuple[str, dict | None, str]:
    """PyPI-JSON abrufen. Rueckgabe: (state, payload, detail).

    state: ok (payload gesetzt) | missing (404) | unknown (alles andere).
    """
    url = PYPI_JSON.format(name=name)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return "ok", json.loads(resp.read().decode("utf-8")), ""
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "missing", None, "HTTP 404"
        return "unknown", None, f"HTTP {exc.code}"
    except Exception as exc:  # Timeout, DNS, TLS, JSON — alles "keine Antwort"
        return "unknown", None, type(exc).__name__


def release_date(payload: dict, version: str) -> str | None:
    """Upload-Datum (YYYY-MM-DD) der gegebenen Version, falls PyPI es liefert."""
    for entry in payload.get("urls") or []:
        stamp = entry.get("upload_time_iso_8601") or entry.get("upload_time")
        if stamp:
            return stamp[:10]
    for entry in (payload.get("releases") or {}).get(version) or []:
        stamp = entry.get("upload_time_iso_8601") or entry.get("upload_time")
        if stamp:
            return stamp[:10]
    return None


def resolve(candidates: list[Candidate], fetch=fetch_pypi) -> list[Resolution]:
    """Kandidaten gegen PyPI aufloesen. `fetch` ist injizierbar (Tests ohne Netz)."""
    out: list[Resolution] = []
    for cand in candidates:
        state, payload, detail = fetch(cand.dist_name)
        if state != "ok" or not payload:
            out.append(Resolution(candidate=cand, state=state, detail=detail))
            continue
        version = (payload.get("info") or {}).get("version")
        if not version:
            out.append(
                Resolution(candidate=cand, state="unknown", detail="kein info.version")
            )
            continue
        out.append(
            Resolution(
                candidate=cand,
                state="ok",
                version=version,
                released=release_date(payload, version),
            )
        )
    return out


# --------------------------------------------------------------------------
# Subcommands
# --------------------------------------------------------------------------


def load_sources() -> tuple[dict, dict]:
    flat = registry_api.flat().get("repos", {})
    fleet = yaml.safe_load(FLEET_FILE.read_text()) or {}
    return flat, (fleet.get("packages") or {})


def cmd_build(args: argparse.Namespace) -> int:
    today = (
        date.fromisoformat(args.today)
        if args.today
        else datetime.now(timezone.utc).date()
    )
    label = args.month or cohort_label(today)
    days = args.support_days
    until = support_until(today, days)

    flat, fleet = load_sources()
    candidates = collect_candidates(flat, fleet)
    if not candidates:
        print(
            "FEHLER: kein Kandidat mit pypi_strategy aktiv|einfrieren.", file=sys.stderr
        )
        return 3
    print(f"Kandidaten: {len(candidates)} (Registry pypi_strategy aktiv|einfrieren)")

    resolutions = resolve(candidates)
    unknown = [r for r in resolutions if r.state == "unknown"]
    missing = [r for r in resolutions if r.state == "missing"]

    for r in missing:
        print(
            f"WARN  {r.candidate.dist_name}: nicht auf PyPI (404, strategy="
            f"{r.candidate.strategy}) — ausgeschlossen, im Header genannt",
            file=sys.stderr,
        )
    for r in unknown:
        print(
            f"# unbekannt  {r.candidate.dist_name}: keine Antwort von PyPI ({r.detail})",
            file=sys.stderr,
        )

    if unknown:
        print(
            f"FEHLER: {len(unknown)} Paket(e) unbekannt — Kohorte NICHT geschrieben "
            "(eine halbe Kohorte sieht vollstaendig aus).",
            file=sys.stderr,
        )
        return 3
    if missing and args.strict_missing:
        print(
            f"FEHLER: {len(missing)} Paket(e) nicht auf PyPI und --strict-missing gesetzt "
            "— Kohorte NICHT geschrieben.",
            file=sys.stderr,
        )
        return 3

    text = render_cohort(label, today, until, days, resolutions)
    out_dir = Path(args.out_dir) if args.out_dir else CONSTRAINTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"iil-cohort-{label}.txt"
    latest = out_dir / LATEST_NAME

    if args.dry_run:
        print(text)
        print(f"(dry-run — nicht geschrieben: {target})", file=sys.stderr)
        return 0

    target.write_text(text)
    # pip folgt keinen git-Symlinks zuverlaessig ueber Plattformen — daher Kopie,
    # nicht Symlink. Der Header nennt die Kohorte, also bleibt der Zeiger eindeutig.
    shutil.copyfile(target, latest)
    print(f"geschrieben: {target}")
    print(f"geschrieben: {latest}  (Zeiger, Kopie von {target.name})")
    print(format_age_line(label, age_days(until, today)))
    return 0


def _resolve_cohort_path(given: str | None) -> Path:
    if given:
        return Path(given)
    return CONSTRAINTS_DIR / LATEST_NAME


def cmd_check(args: argparse.Namespace) -> int:
    path = _resolve_cohort_path(args.file)
    if not path.exists():
        print(f"FEHLER: Kohorte nicht gefunden: {path}", file=sys.stderr)
        return 3
    header, pins = parse_cohort(path.read_text())
    if not pins:
        print(f"FEHLER: keine Pins in {path}", file=sys.stderr)
        return 3
    names = [p.name for p in pins]
    print(
        f"Kohorte {header.get('cohort', '?')}: {len(pins)} Pins — pip-Aufloesung gegen PyPI"
    )

    with tempfile.TemporaryDirectory(prefix="iil-cohort-check-") as tmp:
        venv = Path(tmp) / "venv"
        rc = subprocess.run(
            [sys.executable, "-m", "venv", str(venv)], capture_output=True, text=True
        )
        if rc.returncode != 0:
            print(f"FEHLER: venv-Anlage fehlgeschlagen: {rc.stderr}", file=sys.stderr)
            return 3
        pip = venv / "bin" / "pip"
        proc = subprocess.run(
            [
                str(pip),
                "install",
                "--dry-run",
                "--quiet",
                "--disable-pip-version-check",
                "-c",
                str(path.resolve()),
                *names,
            ],
            capture_output=True,
            text=True,
        )
        if proc.stdout.strip():
            print(proc.stdout.strip())
        if proc.returncode != 0:
            print(proc.stderr.strip(), file=sys.stderr)
            print(
                f"KONFLIKT: Kohorte {header.get('cohort', '?')} ist nicht gemeinsam "
                "installierbar.",
                file=sys.stderr,
            )
            return proc.returncode
    print(f"OK: alle {len(pins)} Pins gemeinsam aufloesbar (pip install --dry-run).")
    return 0


def cmd_age(args: argparse.Namespace) -> int:
    path = _resolve_cohort_path(args.file)
    if not path.exists():
        print(f"Kohorte fehlt: {path} — noch keine erzeugt (tools/iil_cohort.py build)")
        return 2
    header, _ = parse_cohort(path.read_text())
    label = header.get("cohort", "?")
    raw = header.get("support_until")
    if not raw:
        print(f"Kohorte {label}: kein support_until im Header — Datei unvollstaendig")
        return 2
    today = (
        date.fromisoformat(args.today)
        if args.today
        else datetime.now(timezone.utc).date()
    )
    days = age_days(date.fromisoformat(raw), today)
    print(format_age_line(label, days))
    return 2 if days < 0 else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="Kohorte + latest-Zeiger erzeugen")
    b.add_argument("--month", help="Kohorten-Kennung YYYY.MM (Default: heute)")
    b.add_argument(
        "--support-days",
        type=int,
        default=SUPPORT_DAYS_DEFAULT,
        help=f"Supportfenster in Tagen (Default {SUPPORT_DAYS_DEFAULT}, ADR-234 M28-8)",
    )
    b.add_argument("--out-dir", help="Zielverzeichnis (Default: constraints/)")
    b.add_argument("--today", help="Erzeugungsdatum ueberschreiben (Tests/Backfill)")
    b.add_argument(
        "--strict-missing",
        action="store_true",
        help="404 (nicht auf PyPI) ebenfalls als Fehler werten (Exit 3)",
    )
    b.add_argument(
        "--dry-run", action="store_true", help="nur ausgeben, nicht schreiben"
    )
    b.set_defaults(func=cmd_build)

    c = sub.add_parser("check", help="Kohorte gemeinsam installierbar? (tmp-venv)")
    c.add_argument(
        "--file", help="Kohorten-Datei (Default: constraints/iil-cohort-latest.txt)"
    )
    c.set_defaults(func=cmd_check)

    a = sub.add_parser("age", help="Tage bis support_until (Exit 2 wenn abgelaufen)")
    a.add_argument(
        "--file", help="Kohorten-Datei (Default: constraints/iil-cohort-latest.txt)"
    )
    a.add_argument("--today", help="Stichtag ueberschreiben (Tests)")
    a.set_defaults(func=cmd_age)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
