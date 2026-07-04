#!/usr/bin/env python3
"""YAML-Frontmatter für ADRs ohne Frontmatter nachrüsten (ein Repo pro Aufruf).
Usage: adr_fm_migrate.py <repo-name> <findings.json>
Nur ADR-*.md; Status aus Body-Metadaten, sonst Default accepted mit Review-Kommentar.
Erprobt: F-1/F-1b-Wellen 2026-07-04 (82 ADRs, 14 Repos)."""

import json
import os
import re
import subprocess
import sys

GH = os.environ.get("GITHUB_DIR", os.path.expanduser("~/github"))
repo = sys.argv[1]
findings = json.load(open(sys.argv[2]))
files = findings["phase1"][repo]["no_fm"]

MAP = (
    ("approved", "accepted"),
    ("accepted", "accepted"),
    ("akzeptiert", "accepted"),
    ("angenommen", "accepted"),
    ("implemented", "accepted"),
    ("entschieden", "accepted"),
    ("aktualisiert", "accepted"),
    ("revised", "accepted"),
    ("done", "accepted"),
    ("in progress", "proposed"),
    ("proposed", "proposed"),
    ("vorgeschlagen", "proposed"),
    ("ausstehend", "proposed"),
    ("offen", "proposed"),
    ("entwurf", "draft"),
    ("draft", "draft"),
    ("superseded", "superseded"),
    ("deprecated", "deprecated"),
    ("rejected", "rejected"),
)


def derive_status(t):
    m = (
        re.search(r"^\|\s*\**Status\**\s*\|\s*([^|]+)\|", t, re.M | re.I)
        or re.search(r"^#{1,3}\s*Status\s*\n+\s*\**([^\n*]+)", t, re.M | re.I)
        or re.search(r"\*\*Status\*\*[:\s]+([^\n|]+)", t)
    )
    if not m:
        return None, None
    raw = m.group(1).strip()
    low = re.sub(r"[^\w äöüß()./-]", "", raw).strip().lower()
    if low in ("datum", "wert", ""):  # Header-Zeilen-Artefakt -> kein Status
        return None, None
    for key, val in MAP:
        if key in low:
            return val, raw
    return None, raw  # unmappbar -> Default + Original in Report


def derive_date(t, path):
    m = re.search(
        r"^\|\s*\**(?:Entscheidungs)?[Dd]atum\**\s*\|\s*([^|]*\d{4}-\d{2}-\d{2}[^|]*)\|",
        t,
        re.M,
    ) or re.search(r"\b(\d{4}-\d{2}-\d{2})\b", t[:1500])
    if m:
        d = re.search(r"\d{4}-\d{2}-\d{2}", m.group(1))
        if d:
            return d.group(0), "body"
    out = (
        subprocess.run(
            [
                "git",
                "-C",
                os.path.dirname(path),
                "log",
                "--follow",
                "--format=%as",
                "--reverse",
                "--",
                path,
            ],
            capture_output=True,
            text=True,
        )
        .stdout.strip()
        .splitlines()
    )
    import datetime

    return (out[0] if out else datetime.date.today().isoformat()), "git-first-commit"


report = []
for fn in files:
    if not fn.split("/")[-1].startswith("ADR-"):
        report.append((fn.split("/")[-1], "SKIP: kein ADR-*.md", "", ""))
        continue
    path = f"{GH}/{fn}"
    if not os.path.exists(path):
        report.append((fn.split("/")[-1], "SKIP: fehlt auf origin-Branch", "", ""))
        continue
    t = open(path, encoding="utf-8", errors="replace").read()
    if t.startswith("---"):
        report.append((fn, "SKIP: hat schon Frontmatter", "", ""))
        continue
    st, raw = derive_status(t)
    date, dsrc = derive_date(t, path)
    if st:
        fm = f"---\nstatus: {st}\ndate: {date}\n---\n\n"
        src = f"Body ({raw!r})" if raw else "Body"
    else:
        fm = f"---\nstatus: accepted  # auto-migriert (Fleet-Audit F-1): Body ohne Status — im Review bestätigen\ndate: {date}\n---\n\n"
        src = (
            f"DEFAULT accepted (Body: {raw!r})"
            if raw
            else "DEFAULT accepted (kein Body-Status)"
        )
        st = "accepted*"
    open(path, "w", encoding="utf-8").write(fm + t)
    report.append((fn.split("/")[-1], st, src, f"{date} [{dsrc}]"))

for r in report:
    print(f"{r[0]:60s} {r[1]:11s} {r[2][:48]:50s} {r[3]}")
print(
    f"\nmigriert={sum(1 for r in report if not r[1].startswith('SKIP'))} von {len(files)}"
)
