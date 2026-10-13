#!/usr/bin/env python3
"""registry_rich_sync — ableitbare ``rich``-Felder der Registry aus Deklarationen ziehen.

KONZ-platform-070 WP0 (#3903). `registry/canonical.yaml` ist SSoT der Repo-Registry;
38 von 69 Einträgen trugen keine `rich`-Daten (`github`, `lifecycle`, `deployed`).
Dieses Werkzeug leitet ab, was belegbar ist, und schreibt NICHTS, was es nur raten könnte:

| Feld            | Quelle                                             | Regel                                              |
|-----------------|----------------------------------------------------|----------------------------------------------------|
| ``github``      | ``gh api repos/<owner>/<name>`` → ``.full_name``    | Owner aus ``registry_api.owner()`` (Prefix-Regeln,  |
|                 |                                                    | ``repo_owner``); antwortet GitHub mit anderem       |
|                 |                                                    | Namen (stille Umleitung, ADR-297) → Konflikt, kein  |
|                 |                                                    | Schreiben.                                         |
| ``github_meta`` | dieselbe Antwort                                   | visibility · archived · default_branch · pushed_at  |
|                 |                                                    | (Tag, nicht Sekunde — sonst Rauschen je Push).      |
| ``lifecycle``   | ``archived`` der API-Antwort                       | nur ``archived`` ist eindeutig; alles andere bleibt |
|                 |                                                    | leer und wird als „offen“ gelistet.                 |
| ``deployed``    | ``infra/ports.yaml`` Dienst mit ``domain_prod``    | ``betriebsstatus`` aktiv/fehlt → true; blockiert/   |
|                 |                                                    | stillgelegt → false; sonst „nicht belegbar“.        |

Bestehende Werte werden nie überschrieben — weicht die Ableitung ab, steht das im Report
als Konflikt (der Mensch entscheidet, nicht der Sync). ``github_meta`` gehört dem Sync und
wird nachgeführt. Der Ziel-Ort ist dort, wo der Eintrag seine Identität trägt: schlanke
Archiv-Einträge (ADR-275: ``github``/``lifecycle`` top-level, kein ``rich``) bekommen
``github_meta`` top-level, alle anderen im ``rich``-Block (neu angelegt, wenn fehlend —
minimal, ohne ``name``/``repo``; die kommen erst mit ``in_rich: true``).

Schreiben erfolgt textuell (zeilenbasiert), weil ``yaml.safe_dump`` die 120+ Daten-Kommentare
der Datei verlieren würde und ruamel nicht in der CI-Umgebung ist. Invariante vor jedem
Schreiben: ``yaml.safe_load(neu) == erwartetes Dict`` und Kommentarzeilen unverändert.

    python3 tools/registry_rich_sync.py                  # dry-run: Tabelle Repo · Feld · alt → neu · Quelle
    python3 tools/registry_rich_sync.py --apply          # schreibt canonical.yaml; danach registry-canonical.py flip
    python3 tools/registry_rich_sync.py --cache /tmp/gh.json --only meiki-hub --only ttz-hub

Nur lesende GitHub-Aufrufe. Idempotent: ein zweiter Lauf ohne Änderung der Quellen meldet 0 Änderungen.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry_api  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CANON = ROOT / "registry" / "canonical.yaml"
PORTS = ROOT / "infra" / "ports.yaml"

#: Felder, die der Sync aus der GitHub-Antwort in ``github_meta`` übernimmt.
GITHUB_META_FELDER = ("visibility", "archived", "default_branch", "pushed_at")
#: betriebsstatus-Werte aus infra/ports.yaml (Kopf der Datei, platform#2215).
STATUS_AKTIV = (None, "aktiv")
STATUS_NICHT_DEPLOYED = ("blockiert", "stillgelegt")
LIFECYCLE_ARCHIVED = "archived"
ZIEL_RICH = "rich"
ZIEL_TOP = "top"

Fetcher = Callable[[str], dict | None]


@dataclass
class Change:
    repo: str
    feld: str
    alt: object
    neu: object
    quelle: str
    ziel: str  # ZIEL_RICH | ZIEL_TOP


@dataclass
class Report:
    changes: list[Change] = field(default_factory=list)
    konflikte: list[tuple[str, str, object, object, str]] = field(default_factory=list)
    lifecycle_offen: list[str] = field(default_factory=list)
    deployed_nicht_belegbar: list[tuple[str, str]] = field(default_factory=list)
    fehler: list[tuple[str, str]] = field(default_factory=list)


# ── GitHub ─────────────────────────────────────────────────────────────────────


def gh_fetch(full: str) -> dict | None:
    """``gh api repos/<full>`` (nur lesend); None bei 404/Netzfehler."""
    r = subprocess.run(
        ["gh", "api", f"repos/{full}"], capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def github_meta_aus(antwort: dict) -> dict:
    """Die vier Sync-Felder aus einer API-Antwort; pushed_at auf den Tag gekürzt."""
    pushed = antwort.get("pushed_at") or ""
    return {
        "visibility": antwort.get("visibility"),
        "archived": bool(antwort.get("archived")),
        "default_branch": antwort.get("default_branch"),
        "pushed_at": pushed[:10] or None,
    }


def mit_cache(fetch: Fetcher, pfad: Path | None) -> Fetcher:
    """Antworten in einer JSON-Datei puffern (Offline-Wiederholung, Nachweis)."""
    if pfad is None:
        return fetch
    cache: dict = json.loads(pfad.read_text()) if pfad.exists() else {}

    def _f(full: str) -> dict | None:
        if full not in cache:
            cache[full] = fetch(full)
            pfad.write_text(json.dumps(cache, indent=1, sort_keys=True))
        return cache[full]

    return _f


# ── Ableitung ──────────────────────────────────────────────────────────────────


def _github_feld(entry: dict) -> str | None:
    return entry.get("github") or (entry.get("rich") or {}).get("github")


def _owner_explizit(name: str, entry: dict, canon: dict) -> bool:
    """True, wenn der Owner deklariert ist (github-Feld, repo_owner, Prefix-Regel) —
    False, wenn ``registry_api.owner()`` nur auf den Default-Org zurückfällt."""
    meta = canon.get("meta") or {}
    return bool(
        _github_feld(entry)
        or (meta.get("repo_owner") or {}).get(name)
        or any(
            name.startswith(r["prefix"]) for r in meta.get("owner_prefix_rules") or []
        )
    )


def _ziel(entry: dict) -> str:
    return ZIEL_TOP if "github" in entry and "rich" not in entry else ZIEL_RICH


def _zielmap(entry: dict, ziel: str) -> dict:
    return entry if ziel == ZIEL_TOP else (entry.get("rich") or {})


def ports_beleg(ports: dict, full: str, name: str) -> tuple[bool | None, str]:
    """``deployed`` aus infra/ports.yaml belegen — (Wert, Quelle/Grund).

    Ein Dienst gehört zum Repo über ``repo: owner/name`` oder, ohne ``repo``-Feld,
    über den Dienstnamen. Nur Dienste mit ``domain_prod`` zählen.
    """
    dienste = ports.get("services") or {}
    treffer = {
        sn: s
        for sn, s in dienste.items()
        if (s or {}).get("domain_prod")
        and ((s.get("repo") == full) or ("repo" not in s and sn == name))
    }
    if not treffer:
        return None, "kein Dienst mit domain_prod in infra/ports.yaml"
    for sn, s in treffer.items():
        if s.get("betriebsstatus") in STATUS_AKTIV:
            return (
                True,
                f"infra/ports.yaml services.{sn}.domain_prod={s['domain_prod']} (aktiv)",
            )
    status = {sn: s.get("betriebsstatus") for sn, s in treffer.items()}
    if all(st in STATUS_NICHT_DEPLOYED for st in status.values()):
        sn, st = next(iter(status.items()))
        return False, f"infra/ports.yaml services.{sn}.betriebsstatus={st}"
    return None, "betriebsstatus " + ", ".join(
        f"{sn}={st}" for sn, st in status.items() if st not in STATUS_NICHT_DEPLOYED
    ) + " — nicht als deployed/nicht-deployed definiert"


def derive(
    canon: dict, ports: dict, fetch: Fetcher, only: set[str] | None = None
) -> Report:
    """Alle Änderungen und Befunde berechnen — ohne Schreiben."""
    rep = Report()
    for name, entry in canon["repos"].items():
        if only and name not in only:
            continue
        entry = entry or {}
        deklariert = _github_feld(entry) or f"{registry_api.owner(name, canon)}/{name}"
        antwort = fetch(deklariert)
        if antwort is None:
            rep.fehler.append(
                (name, f"gh api repos/{deklariert} ohne Antwort (404/Netz)")
            )
            continue
        full = antwort.get("full_name") or deklariert
        quelle_gh = f"gh api repos/{deklariert}"
        quelle_github = f"{quelle_gh} .full_name · Owner: registry_api.owner()"
        if full.lower() != deklariert.lower():
            umgeleitet = f"{quelle_gh} → .full_name (stille Umleitung)"
            gleicher_name = full.split("/", 1)[1].lower() == name.lower()
            if _owner_explizit(name, entry, canon) or not gleicher_name:
                rep.konflikte.append((name, "github", deklariert, full, umgeleitet))
                continue
            # Default-Org-Fallback traf nicht, GitHub kennt das Repo unter anderem Owner:
            # keine Deklaration widerspricht — die Antwort IST die Ableitung (ADR-297).
            quelle_github = umgeleitet
        ziel = _ziel(entry)
        zm = _zielmap(entry, ziel)

        if _github_feld(entry) is None:
            rep.changes.append(Change(name, "github", None, full, quelle_github, ziel))
        meta = github_meta_aus(antwort)
        if zm.get("github_meta") != meta:
            rep.changes.append(
                Change(
                    name, "github_meta", zm.get("github_meta"), meta, quelle_gh, ziel
                )
            )

        lc_ist = registry_api._lifecycle(entry)
        lc_soll = LIFECYCLE_ARCHIVED if meta["archived"] else None
        if lc_soll and lc_ist is None:
            rep.changes.append(
                Change(
                    name,
                    "lifecycle",
                    None,
                    lc_soll,
                    f"{quelle_gh} .archived=true",
                    ziel,
                )
            )
        elif lc_soll and lc_ist != lc_soll:
            rep.konflikte.append(
                (name, "lifecycle", lc_ist, lc_soll, f"{quelle_gh} .archived=true")
            )
        elif not lc_soll and lc_ist == LIFECYCLE_ARCHIVED:
            rep.konflikte.append(
                (name, "lifecycle", lc_ist, None, f"{quelle_gh} .archived=false")
            )
        elif not lc_soll and lc_ist is None:
            rep.lifecycle_offen.append(name)

        if (lc_ist or lc_soll) == LIFECYCLE_ARCHIVED:
            continue  # archiviert → kein Deploy-Kandidat
        dep_ist = (entry.get("rich") or {}).get("deployed")
        dep_soll, grund = ports_beleg(ports, full, name)
        if dep_soll is None:
            if dep_ist is None:
                rep.deployed_nicht_belegbar.append((name, grund))
        elif dep_ist is None:
            rep.changes.append(
                Change(name, "deployed", None, dep_soll, grund, ZIEL_RICH)
            )
        elif dep_ist != dep_soll:
            rep.konflikte.append((name, "deployed", dep_ist, dep_soll, grund))
    return rep


def erwartet(canon: dict, changes: list[Change]) -> dict:
    """Das Dict, das canonical.yaml nach dem Schreiben ergeben muss."""
    neu = copy.deepcopy(canon)
    for c in changes:
        entry = neu["repos"][c.repo]
        zm = entry if c.ziel == ZIEL_TOP else entry.setdefault("rich", {})
        zm[c.feld] = c.neu
    return neu


# ── Textuelles Schreiben (kommentarerhaltend) ──────────────────────────────────


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block_end(lines: list[str], i: int, indent: int, limit: int) -> int:
    """Erste Zeile nach dem Block, dessen Schlüssel bei ``i`` mit ``indent`` steht."""
    j = i + 1
    while j < limit and (not lines[j].strip() or _indent(lines[j]) > indent):
        j += 1
    return j


def _ohne_leerzeilen(lines: list[str], start: int, end: int) -> int:
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return end


def _find_key(
    lines: list[str], start: int, end: int, indent: int, key: str
) -> int | None:
    for i in range(start, end):
        s = lines[i].lstrip()
        if (
            _indent(lines[i]) == indent
            and not s.startswith("#")
            and re.match(rf"{re.escape(key)}\s*:", s)
        ):
            return i
    return None


def _render(key: str, value, indent: int) -> list[str]:
    text = yaml.safe_dump(
        {key: value},
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=1000,
    )
    return [" " * indent + ln for ln in text.rstrip("\n").split("\n")]


def _set_key(
    lines: list[str], start: int, end: int, indent: int, key: str, value
) -> None:
    """Schlüssel ``key`` (Einrückung ``indent``) im Mapping-Span [start, end) setzen oder anhängen."""
    neu = _render(key, value, indent)
    i = _find_key(lines, start, end, indent, key)
    if i is not None:
        j = _ohne_leerzeilen(lines, i, _block_end(lines, i, indent, end))
        lines[i:j] = neu
    else:
        k = _ohne_leerzeilen(lines, start, end)
        lines[k:k] = neu


def _entry_span(lines: list[str], name: str) -> tuple[int, int]:
    start = next(i for i, ln in enumerate(lines) if ln == "repos:")
    s = _find_key(lines, start, len(lines), 2, name)
    if s is None:
        raise KeyError(name)
    return s, _block_end(lines, s, 2, len(lines))


def apply_text(text: str, changes: list[Change]) -> str:
    """Änderungen zeilenbasiert einarbeiten — Kommentare bleiben stehen."""
    lines = text.split("\n")
    for c in changes:
        s, e = _entry_span(lines, c.repo)
        if c.ziel == ZIEL_TOP:
            _set_key(lines, s, e, 4, c.feld, c.neu)
            continue
        r = _find_key(lines, s, e, 4, "rich")
        if r is None:
            _set_key(lines, s, e, 4, "rich", {c.feld: c.neu})
            continue
        _set_key(lines, r, _block_end(lines, r, 4, e), 6, c.feld, c.neu)
    return "\n".join(lines)


def _kommentarzeilen(text: str) -> list[str]:
    return [ln for ln in text.split("\n") if ln.lstrip().startswith("#")]


def schreibe(pfad: Path, text: str, canon: dict, changes: list[Change]) -> str:
    """Patchen, Invarianten prüfen, schreiben. Gibt den neuen Text zurück."""
    neu = apply_text(text, changes)
    soll = erwartet(canon, changes)
    ist = yaml.safe_load(neu)
    if ist != soll:
        raise RuntimeError("Textpatch ≠ erwartetes Dict — nichts geschrieben")
    if _kommentarzeilen(neu) != _kommentarzeilen(text):
        raise RuntimeError("Kommentarzeilen verändert — nichts geschrieben")
    pfad.write_text(neu)
    return neu


# ── Report ─────────────────────────────────────────────────────────────────────


def orgs(canon: dict) -> dict[str, str]:
    """Repo → Owner (github-Feld, sonst registry_api.owner())."""
    return {
        name: (
            _github_feld(entry or {}) or f"{registry_api.owner(name, canon)}/"
        ).split("/", 1)[0]
        for name, entry in canon["repos"].items()
    }


def fehlstellen_je_org(
    canon: dict, org_von: dict[str, str]
) -> dict[str, dict[str, int]]:
    """Je Owner: Einträge gesamt und ohne github / lifecycle / deployed (archiviert zählt nicht).
    ``org_von`` kommt vom Nachher-Stand, damit ein Repo, das durch den Lauf den Owner
    wechselt, vorher und nachher in derselben Zeile steht."""
    out: dict[str, dict[str, int]] = {}
    for name, entry in canon["repos"].items():
        entry = entry or {}
        gh = _github_feld(entry)
        z = out.setdefault(
            org_von[name],
            {"gesamt": 0, "ohne_github": 0, "ohne_lifecycle": 0, "ohne_deployed": 0},
        )
        z["gesamt"] += 1
        z["ohne_github"] += gh is None
        lc = registry_api._lifecycle(entry)
        z["ohne_lifecycle"] += lc is None
        z["ohne_deployed"] += (
            lc != LIFECYCLE_ARCHIVED
            and (entry.get("rich") or {}).get("deployed") is None
        )
    return out


def _kurz(v) -> str:
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k}={v[k]}" for k in v) + "}"
    return "—" if v is None else str(v)


def drucke(rep: Report, vorher: dict, nachher: dict, apply: bool) -> None:
    print(f"{'Repo':<22} {'Feld':<12} {'alt → neu':<58} Quelle")
    for c in rep.changes:
        print(
            f"{c.repo:<22} {c.feld:<12} {_kurz(c.alt) + ' → ' + _kurz(c.neu):<58} {c.quelle}"
        )
    print(
        f"\n{len(rep.changes)} Änderung(en) — {'geschrieben' if apply else 'dry-run, nichts geschrieben'}"
    )
    if rep.konflikte:
        print("\nKonflikte (nicht geschrieben, Mensch entscheidet):")
        for name, feld, ist, soll, quelle in rep.konflikte:
            print(
                f"  {name:<22} {feld:<12} Registry={_kurz(ist)} · Ableitung={_kurz(soll)} · {quelle}"
            )
    if rep.lifecycle_offen:
        print(
            f"\nlifecycle offen ({len(rep.lifecycle_offen)}, nicht eindeutig ableitbar): "
            + ", ".join(rep.lifecycle_offen)
        )
    if rep.deployed_nicht_belegbar:
        print(f"\ndeployed nicht belegbar ({len(rep.deployed_nicht_belegbar)}):")
        for name, grund in rep.deployed_nicht_belegbar:
            print(f"  {name:<22} {grund}")
    if rep.fehler:
        print("\nGitHub-Fehler:")
        for name, grund in rep.fehler:
            print(f"  {name:<22} {grund}")
    print(
        "\nFehlstellen je Org (vorher → nachher): ohne github / ohne lifecycle / ohne deployed"
    )
    for org in sorted(set(vorher) | set(nachher)):
        v, n = vorher.get(org, {}), nachher.get(org, {})
        print(
            f"  {org:<14} {v.get('gesamt', 0):>3} Einträge  "
            f"{v.get('ohne_github', 0)}→{n.get('ohne_github', 0)} / "
            f"{v.get('ohne_lifecycle', 0)}→{n.get('ohne_lifecycle', 0)} / "
            f"{v.get('ohne_deployed', 0)}→{n.get('ohne_deployed', 0)}"
        )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--apply",
        action="store_true",
        help="canonical.yaml schreiben (Default: dry-run)",
    )
    ap.add_argument("--canonical", type=Path, default=CANON)
    ap.add_argument("--ports", type=Path, default=PORTS)
    ap.add_argument("--cache", type=Path, help="JSON-Puffer der GitHub-Antworten")
    ap.add_argument("--only", action="append", help="nur dieses Repo (mehrfach)")
    args = ap.parse_args(argv)

    text = args.canonical.read_text()
    canon = yaml.safe_load(text)
    ports = yaml.safe_load(args.ports.read_text())
    rep = derive(
        canon, ports, mit_cache(gh_fetch, args.cache), set(args.only or []) or None
    )
    nachher = erwartet(canon, rep.changes)
    org_von = orgs(nachher)
    drucke(
        rep,
        fehlstellen_je_org(canon, org_von),
        fehlstellen_je_org(nachher, org_von),
        args.apply,
    )
    if args.apply and rep.changes:
        schreibe(args.canonical, text, canon, rep.changes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
