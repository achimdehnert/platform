#!/usr/bin/env python3
"""Hosts Audit — hält infra/hosts.yaml ehrlich und fängt tote Runner-Label-Pins.

Hintergrund: Infra-/Runner-Topologie-Drift war wiederholt Outage- und Merge-Blocker-
Quelle (2026-06-15 Prod-Web-Outage, 2026-06-17 toter `hetzner`-Runner-Pin blockierte
13h alle risk-hub-Merges). Dieser Gate verankert die SoT `infra/hosts.yaml` und prüft,
dass kein Workflow auf ein Runner-Label zeigt, das kein lebender Runner in der SoT trägt.

Nutzung:
    # Alles prüfen (Schema + Frische der SoT):
    python infra/scripts/hosts_audit.py

    # Nur Schema / nur Frische:
    python infra/scripts/hosts_audit.py --check schema
    python infra/scripts/hosts_audit.py --check staleness --max-age-days 120

    # Runner-Label-Audit: jedes runs-on in <dir> gegen Online-Runner der SoT:
    python infra/scripts/hosts_audit.py --check labels --workflows ../risk-hub/.github/workflows

    # Alles inkl. Label-Audit:
    python infra/scripts/hosts_audit.py --check all --workflows .github/workflows

    # Auflage-Abgleich gegen ports.yaml (Klasse f, Deklarationsebene — KONZ-054 E5):
    python infra/scripts/hosts_audit.py --check auflage

Exit-Codes:
    0 = keine Findings
    1 = Findings (Schema/Frische/tote Labels/Auflage)
    2 = Bedienfehler (Datei fehlt o.ä.)

Referenz: platform/infra/hosts.yaml (SoT), session-retro Längsschnitt-Gate.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import sys
from pathlib import Path

import yaml

# Labels, die JEDER self-hosted Runner automatisch trägt → kein Eintrag in der SoT nötig.
_AUTO_LABELS = {"self-hosted", "Linux", "X64", "linux", "x64"}
# GitHub-hosted runs-on (keine self-hosted-Prüfung):
_HOSTED_PREFIXES = ("ubuntu", "windows", "macos")
_DEFAULT_MAX_AGE_DAYS = 120

# Architektur-Vokabular. Die Flotte deployt amd64-Images (_deploy-unified.yml);
# ein Runner auf einem anderen Knoten baut oder zieht Images, die dort nicht laufen.
_ARCH_ERLAUBT = {"amd64", "x86_64", "aarch64", "arm64"}
_ARCH_FLOTTE = {"amd64", "x86_64"}

# Auflage-Block je Host (KONZ-platform-054 E5). Bis dahin stand jede Auflage als
# Fliesstext im Feld `role:` — lesbar fuer Menschen, unsichtbar fuer jedes Werkzeug.
# Alle Felder optional; fehlt eines, gilt "erlaubt". `grund` ist Pflicht, sobald
# der Block existiert, damit die Auflage einen Beleg traegt.
_AUFLAGE_FELDER = {
    "datenklassen_verboten",  # Liste aus _DATENKLASSEN
    "prod_container",  # bool — duerfen hier Prod-Container laufen?
    "app_hubs",  # bool — duerfen hier App-Hub-Stacks laufen?
    "runner",  # bool — darf hier ein GitHub-Runner laufen?
    "oeffentlicher_ingress",  # bool — darf ein oeffentlicher Tunnel/vhost hierher zeigen?
    "nur_dienste",  # Liste — Whitelist der Dienste (Lane G)
    "grund",  # str — Verweis auf ADR/KONZ/Owner-Entscheid
    "ausnahmen",  # Mapping dienst -> {grund, entschieden, bis} (s. _check_ausnahmen)
}
_AUSNAHME_FELDER = {"grund", "entschieden", "bis"}
_DATENKLASSEN = {"gov-sozialdaten", "personenbezogen"}

# Gewaehrte Ausnahmen werden IMMER ausgegeben, auch ausserhalb des PR-Modus.
# Eine Ausnahme, die man nur im Diff sieht, ist eine Ausnahme, die niemand prueft.
_AUSNAHME_LOG: list[str] = []


def load_hosts_yaml(path: Path) -> dict:
    if not path.exists():
        print(f"FEHLER: {path} nicht gefunden", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(path.read_text()) or {}


def _today() -> _dt.date:
    return _dt.date.today()


def check_schema(data: dict) -> list[str]:
    issues: list[str] = []
    for top in ("hosts", "runners"):
        if top not in data or not isinstance(data[top], dict):
            issues.append(f"schema: Top-Level-Key '{top}' fehlt oder ist kein Mapping")
    hosts = data.get("hosts", {}) or {}
    runners = data.get("runners", {}) or {}

    for name, r in runners.items():
        if not isinstance(r, dict):
            issues.append(f"schema: runner '{name}' ist kein Mapping")
            continue
        if not isinstance(r.get("labels"), list) or not r["labels"]:
            issues.append(f"schema: runner '{name}' hat keine 'labels'-Liste")
        if not r.get("status"):
            issues.append(f"schema: runner '{name}' hat kein 'status'")
        host = r.get("host")
        if host not in (None, "UNKNOWN") and host not in hosts:
            issues.append(
                f"schema: runner '{name}'.host='{host}' referenziert keinen Host"
            )

    for name, h in hosts.items():
        if not isinstance(h, dict):
            issues.append(f"schema: host '{name}' ist kein Mapping")
            continue
        host_runners = h.get("hosts_runners", []) or []
        for rn in host_runners:
            if rn not in runners:
                issues.append(
                    f"schema: host '{name}'.hosts_runners enthält unbekannten Runner '{rn}'"
                )

        arch = h.get("arch")
        if arch is not None and arch not in _ARCH_ERLAUBT:
            issues.append(
                f"schema: host '{name}'.arch='{arch}' — erlaubt: {sorted(_ARCH_ERLAUBT)}"
            )
        elif arch is not None and arch not in _ARCH_FLOTTE and host_runners:
            issues.append(
                f"arch: host '{name}' ist {arch}, traegt aber Runner {host_runners} — "
                f"die Flotten-Images sind amd64. Ein Runner dort baut oder zieht, was "
                f"dort nicht laeuft (KONZ-053 §6: Runner fruehestens Phase 2, repo-scoped)."
            )

        if h.get("verified") is False and not h.get("verified_bis"):
            issues.append(
                f"schema: host '{name}' ist verified=false ohne 'verified_bis' — eine "
                f"Ausnahme ohne Frist ist eine Dauerausnahme (KONZ-054 E5)"
            )

        issues += _check_auflage_block(name, h)
    return issues


def _ausnahme_fuer(auflage: dict, dienst: str) -> dict | None:
    """Gibt die Ausnahme-Deklaration fuer `dienst` zurueck — oder None.

    Eine Ausnahme ist KEIN Freibrief: sie traegt einen Grund, ein Datum und
    eine Frist. Laeuft die Frist ab, wird der Verstoss wieder ein Finding
    (siehe _check_ausnahmen) — eine Ausnahme, die niemand verlaengern muss,
    ist eine Auflage, die es nicht gibt."""
    a = (auflage or {}).get("ausnahmen")
    if not isinstance(a, dict):
        return None
    e = a.get(dienst)
    return e if isinstance(e, dict) else None


def _check_ausnahmen(name: str, a: dict) -> list[str]:
    """Schema und Frist der Auflage-Ausnahmen eines Hosts."""
    issues: list[str] = []
    aus = a.get("ausnahmen")
    if aus is None:
        return issues
    if not isinstance(aus, dict):
        return [f"auflage: host '{name}'.ausnahmen ist kein Mapping dienst -> {{…}}"]
    for dienst, e in aus.items():
        if not isinstance(e, dict):
            issues.append(
                f"auflage: host '{name}'.ausnahmen['{dienst}'] ist kein Mapping"
            )
            continue
        fehlt = _AUSNAHME_FELDER - set(e)
        if fehlt:
            issues.append(
                f"auflage: ausnahme '{dienst}' auf '{name}' fehlt {sorted(fehlt)} — "
                f"eine Ausnahme ohne Grund, Datum und Frist ist ein stiller Bypass"
            )
        fremd = set(e) - _AUSNAHME_FELDER
        if fremd:
            issues.append(
                f"auflage: ausnahme '{dienst}' auf '{name}' hat unbekannte Felder "
                f"{sorted(fremd)} — erlaubt: {sorted(_AUSNAHME_FELDER)}"
            )
        bis = e.get("bis")
        if bis is None:
            continue
        if isinstance(bis, _dt.datetime):
            bis = bis.date()
        if not isinstance(bis, _dt.date):
            issues.append(
                f"auflage: ausnahme '{dienst}' auf '{name}'.bis ist kein Datum "
                f"(YYYY-MM-DD), sondern {bis!r}"
            )
        elif bis < _today():
            issues.append(
                f"auflage: ausnahme '{dienst}' auf '{name}' ist am {bis} abgelaufen — "
                f"verlaengern (mit Grund) oder den Dienst umziehen/stoppen"
            )
    return issues


def _check_auflage_block(name: str, h: dict) -> list[str]:
    """Prueft nur die Form des Auflage-Blocks und das, was aus hosts.yaml allein
    entscheidbar ist. Ob ein WORKLOAD gegen die Auflage verstoesst, entscheidet
    check_auflage() mit ports.yaml — und der Live-Abgleich (reconcile) am Knoten."""
    issues: list[str] = []
    a = h.get("auflage")
    if a is None:
        return issues
    if not isinstance(a, dict):
        return [f"auflage: host '{name}'.auflage ist kein Mapping"]
    fremd = set(a) - _AUFLAGE_FELDER
    if fremd:
        issues.append(
            f"auflage: host '{name}' hat unbekannte Felder {sorted(fremd)} — "
            f"erlaubt: {sorted(_AUFLAGE_FELDER)}"
        )
    if not a.get("grund"):
        issues.append(
            f"auflage: host '{name}' hat eine Auflage ohne 'grund' — jede Auflage "
            f"braucht einen Beleg (ADR/KONZ/Owner-Entscheid)"
        )
    dk = a.get("datenklassen_verboten")
    if dk is not None:
        if not isinstance(dk, list):
            issues.append(
                f"auflage: host '{name}'.datenklassen_verboten ist keine Liste"
            )
        else:
            for k in dk:
                if k not in _DATENKLASSEN:
                    issues.append(
                        f"auflage: host '{name}' verbietet unbekannte Datenklasse '{k}' — "
                        f"Vokabular: {sorted(_DATENKLASSEN)}"
                    )
    issues += _check_ausnahmen(name, a)
    for feld in ("prod_container", "app_hubs", "runner", "oeffentlicher_ingress"):
        if feld in a and not isinstance(a[feld], bool):
            issues.append(f"auflage: host '{name}'.{feld} muss true/false sein")
    if a.get("runner") is False and (h.get("hosts_runners") or []):
        issues.append(
            f"auflage: host '{name}' verbietet Runner, traegt aber "
            f"{h.get('hosts_runners')} — Deklaration widerspricht sich selbst"
        )
    return issues


def check_auflage(
    data: dict, ports: dict, hinweise: list[str] | None = None
) -> list[str]:
    """Klasse (f) auf Deklarationsebene: zeigt ports.yaml einen Dienst auf einen
    Knoten, dessen Auflage ihn ausschliesst? Liest `prod_host` (Default 'prod'),
    `betriebsstatus` und `datenklasse` je Dienst. Was ports.yaml nicht kennt,
    kann diese Pruefung nicht sehen — der Live-Abgleich am Knoten bleibt noetig.

    `hinweise`: wird eine Liste uebergeben, landen Verstoesse von Diensten mit
    `betriebsstatus: blockiert` dort statt in den Findings. Das ist der PR-Modus:
    ein deklarierter, getrackter Verstoss (platform#2507) darf keinen fremden PR
    blocken — ein NEUER Dienst auf einem gesperrten Knoten bleibt ein Finding."""
    issues: list[str] = []
    hosts = data.get("hosts", {}) or {}
    dienste = (ports or {}).get("services") or {}
    for dienst, cfg in dienste.items():
        if not isinstance(cfg, dict):
            continue
        # Nur `stillgelegt` ist raus. `blockiert` heisst "laeuft, wartet auf Entscheidung" —
        # genau der Fall, den dieser Check sichtbar halten muss (Lauf-2-Kritik 2026-08-30:
        # der Check war gruen auf den vier dev-desktop-Diensten, fuer die er gebaut wurde).
        status = str(cfg.get("betriebsstatus", "aktiv")).lower()
        if status == "stillgelegt":
            continue
        senke = hinweise if (hinweise is not None and status == "blockiert") else issues
        ziel = str(cfg.get("prod_host", "prod"))
        h = hosts.get(ziel)
        if not isinstance(h, dict):
            senke.append(
                f"auflage: dienst '{dienst}' zeigt auf prod_host '{ziel}', den hosts.yaml "
                f"nicht kennt"
            )
            continue
        a = h.get("auflage") or {}
        # Eine benannte, befristete Ausnahme macht aus dem Verstoss einen Hinweis —
        # nie ein Schweigen. Ihre Frist prueft _check_ausnahmen; laeuft sie ab,
        # steht der Verstoss wieder als Finding da (platform#2507, Owner 2026-09-01).
        ausnahme = _ausnahme_fuer(a, dienst)
        if ausnahme is not None:
            _AUSNAHME_LOG.append(
                f"ausnahme: dienst '{dienst}' darf auf '{ziel}' laufen bis "
                f"{ausnahme.get('bis', '?')} — {ausnahme.get('grund', 'ohne Grund')}"
            )
            continue
        if a.get("prod_container") is False:
            senke.append(
                f"auflage: dienst '{dienst}' ist auf '{ziel}' deklariert, dort sind "
                f"Prod-Container untersagt ({a.get('grund', 'ohne Grund')})"
            )
        if a.get("app_hubs") is False:
            senke.append(
                f"auflage: dienst '{dienst}' ist auf '{ziel}' deklariert, dort sind "
                f"App-Hubs untersagt ({a.get('grund', 'ohne Grund')})"
            )
        nur = a.get("nur_dienste")
        if isinstance(nur, list) and dienst not in nur:
            senke.append(
                f"auflage: dienst '{dienst}' ist auf '{ziel}' deklariert, erlaubt sind "
                f"dort nur {nur} ({a.get('grund', 'ohne Grund')})"
            )
        dk = cfg.get("datenklasse")
        if dk and dk in (a.get("datenklassen_verboten") or []):
            senke.append(
                f"auflage: dienst '{dienst}' fuehrt Datenklasse '{dk}' und ist auf '{ziel}' "
                f"deklariert, wo sie untersagt ist ({a.get('grund', 'ohne Grund')})"
            )
    return issues


def check_staleness(data: dict, max_age_days: int) -> list[str]:
    issues: list[str] = []
    today = _today()
    cutoff = today - _dt.timedelta(days=max_age_days)
    for section in ("hosts", "runners"):
        for name, item in (data.get(section, {}) or {}).items():
            if not isinstance(item, dict):
                continue
            v = item.get("verified")
            if v is False:
                # Unverifiziert ist erlaubt — aber nur bis zu einem Datum. Vorher stand
                # hier ein nacktes `continue`, und ein Eintrag durfte unbegrenzt
                # unvermessen bleiben, waehrend der Audit gruen meldete (KONZ-054 E5).
                bis = item.get("verified_bis")
                d = (
                    bis
                    if isinstance(bis, _dt.date)
                    else _parse_date(str(bis))
                    if bis
                    else None
                )
                if d is None:
                    issues.append(
                        f"staleness: {section}/{name} ist verified=false ohne gueltiges "
                        f"'verified_bis' — Frist setzen oder messen"
                    )
                elif d < today:
                    issues.append(
                        f"staleness: {section}/{name} ist verified=false, Frist "
                        f"{d} ist um {(today - d).days}d ueberschritten — messen und "
                        f"'verified' setzen, oder die Frist mit Grund verlaengern"
                    )
                continue
            if v is None:
                issues.append(f"staleness: {section}/{name} hat kein 'verified'-Datum")
                continue
            d = v if isinstance(v, _dt.date) else _parse_date(str(v))
            if d is None:
                issues.append(
                    f"staleness: {section}/{name}.verified='{v}' ist kein gültiges Datum"
                )
            elif d < cutoff:
                age = (today - d).days
                issues.append(
                    f"staleness: {section}/{name} zuletzt {d} verifiziert ({age}d alt > {max_age_days}d) "
                    f"— per server_probe.py / gh api gegenprüfen und hosts.yaml aktualisieren"
                )
    return issues


def _parse_date(s: str) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(s.strip())
    except ValueError:
        return None


def available_label_sets(data: dict) -> list[set[str]]:
    """Label-Mengen aller ONLINE-Runner aus der SoT (gegen die runs-on geprüft wird)."""
    out: list[set[str]] = []
    for name, r in (data.get("runners", {}) or {}).items():
        if str(r.get("status", "")).lower() == "online":
            out.append({str(lbl) for lbl in (r.get("labels") or [])})
    return out


def _parse_runs_on(raw) -> list[set[str]]:
    """runs-on kann String oder Liste sein → eine Menge geforderter Labels."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [{raw}]
    if isinstance(raw, list):
        return [{str(x) for x in raw}]
    return []


def _iter_runs_on(wf_path: Path) -> list[tuple[str, set[str]]]:
    """(job_id, required-labels) je Job — tolerant geparst (YAML, sonst Regex-Fallback)."""
    results: list[tuple[str, set[str]]] = []
    text = wf_path.read_text()
    try:
        doc = yaml.safe_load(text) or {}
        jobs = doc.get("jobs", {}) or {}
        for job_id, job in jobs.items():
            if isinstance(job, dict):
                for req in _parse_runs_on(job.get("runs-on")):
                    results.append((job_id, req))
        if results:
            return results
    except yaml.YAMLError:
        pass
    # Fallback: rohe runs-on-Zeilen (falls YAML wegen Templating nicht parst)
    for m in re.finditer(r"runs-on:\s*(.+)", text):
        val = m.group(1).strip()
        if val.startswith("["):
            labels = {
                x.strip().strip("'\"") for x in val.strip("[]").split(",") if x.strip()
            }
        else:
            labels = {val.strip("'\"")}
        results.append(("?", labels))
    return results


def check_labels(data: dict, workflows_dir: Path) -> list[str]:
    issues: list[str] = []
    if not workflows_dir.exists():
        print(
            f"FEHLER: workflows-Verzeichnis {workflows_dir} nicht gefunden",
            file=sys.stderr,
        )
        sys.exit(2)
    avail = available_label_sets(data)
    for wf in sorted(workflows_dir.glob("*.yml")) + sorted(
        workflows_dir.glob("*.yaml")
    ):
        for job_id, req in _iter_runs_on(wf):
            # GitHub-hosted Runner ignorieren
            if any(
                any(lbl.lower().startswith(p) for p in _HOSTED_PREFIXES) for lbl in req
            ):
                continue
            if "self-hosted" not in {lbl.lower() for lbl in req}:
                continue
            # Nur nicht-automatische Labels müssen von einem Online-Runner gedeckt sein
            needed = {lbl for lbl in req if lbl not in _AUTO_LABELS}
            if not needed:
                continue  # reines self-hosted → ok
            if not any(needed <= a for a in avail):
                issues.append(
                    f"labels: {wf.name} job '{job_id}' verlangt {sorted(req)} — "
                    f"kein ONLINE-Runner in hosts.yaml trägt {sorted(needed)}. "
                    f"Toter Label-Pin → blockiert Merges. Fix: runs-on: self-hosted "
                    f"(siehe Label-Konvention in infra/hosts.yaml)."
                )
    return issues


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--check",
        choices=["schema", "staleness", "labels", "auflage", "all"],
        default="all",
    )
    p.add_argument(
        "--hosts", type=Path, default=Path(__file__).resolve().parents[1] / "hosts.yaml"
    )
    p.add_argument(
        "--workflows",
        type=Path,
        help="Verzeichnis mit .github/workflows zum Label-Audit",
    )
    p.add_argument("--max-age-days", type=int, default=_DEFAULT_MAX_AGE_DAYS)
    p.add_argument(
        "--ports",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "ports.yaml",
        help="ports.yaml fuer den Auflage-Abgleich (Klasse f, Deklarationsebene)",
    )
    p.add_argument(
        "--blockiert-als-hinweis",
        action="store_true",
        help="PR-Modus: Verstoesse von Diensten mit betriebsstatus=blockiert nur "
        "als Hinweis ausgeben, nicht als Finding (Schedule/Push bleiben rot)",
    )
    args = p.parse_args()

    data = load_hosts_yaml(args.hosts)
    issues: list[str] = []
    hinweise: list[str] = []

    if args.check in ("schema", "all"):
        issues += check_schema(data)
    if args.check in ("staleness", "all"):
        issues += check_staleness(data, args.max_age_days)
    if args.check in ("auflage", "all"):
        if args.ports.exists():
            issues += check_auflage(
                data,
                yaml.safe_load(args.ports.read_text()) or {},
                hinweise if args.blockiert_als_hinweis else None,
            )
        elif args.check == "auflage":
            print(f"FEHLER: {args.ports} nicht gefunden", file=sys.stderr)
            sys.exit(2)
    if args.check in ("labels", "all"):
        if args.workflows:
            issues += check_labels(data, args.workflows)
        elif args.check == "labels":
            print("FEHLER: --check labels braucht --workflows <dir>", file=sys.stderr)
            sys.exit(2)

    for a in _AUSNAHME_LOG:
        print(f"⚖ {a}")
    for h in hinweise:
        print(f"⚠ deklariert (blockiert, kein Finding im PR-Modus): {h}")
    if issues:
        print(f"❌ hosts_audit: {len(issues)} Finding(s):")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)
    print(f"✅ hosts_audit ({args.check}): keine Findings (SoT: {args.hosts}).")
    sys.exit(0)


if __name__ == "__main__":
    main()
