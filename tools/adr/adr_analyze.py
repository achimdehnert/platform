#!/usr/bin/env python3
"""Minimal-Health (Phase 1) + Cross-Repo-Checks (Phase 2) über ein adr_inventory-JSON.
Usage: adr_analyze.py <inventory.json> <findings.json>"""

import json
import re
import sys
import collections
import datetime

rows = json.load(open(sys.argv[1]))
TODAY = datetime.date.today()
# Vokabular = iil-adrfw Schema v3 (Fehlermeldung von `iil-adrfw validate`, 2026-07-04)
VOCAB = {
    "draft",
    "proposed",
    "accepted",
    "deprecated",
    "superseded",
    "rejected",
    "experimental",
    "void",
}


def pdate(s):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s or "")
    if not m:
        return None
    try:
        return datetime.date(*map(int, m.groups()))
    except ValueError:
        return None


by_repo = collections.defaultdict(list)
for r in rows:
    by_repo[r["repo"]].append(r)

rep = {"phase1": {}, "phase2": {}}

# ---------- Phase 1 ----------
for repo, rs in sorted(by_repo.items()):
    f = {
        "n": len(rs),
        "no_fm": [],
        "no_status": [],
        "bad_status": [],
        "no_date": [],
        "stale_proposed": [],
        "template_rest": [],
        "dup_nums": [],
        "tiny": [],
    }
    nums = collections.Counter(r["num"] for r in rs if r["num"] is not None)
    f["dup_nums"] = [f"ADR-{n} ({c}x)" for n, c in nums.items() if c > 1]
    for r in rs:
        fn = f"{r['repo']}/docs/adr/{r['file']}"
        if not r.get("has_fm"):
            f["no_fm"].append(fn)
        st = (
            (r.get("status") or "").strip().lower().split()[0]
            if r.get("status")
            else ""
        )
        if not st:
            f["no_status"].append(fn)
        elif st not in VOCAB:
            f["bad_status"].append(f"{fn} -> {r['status']!r}")
        if not r.get("date"):
            f["no_date"].append(fn)
        d = pdate(r.get("date"))
        if st == "proposed" and d and (TODAY - d).days > 90:
            f["stale_proposed"].append(f"{fn} ({r['date']}, {(TODAY - d).days}d)")
        if r.get("template_rest"):
            f["template_rest"].append(fn)
        if r.get("bytes", 0) < 400:
            f["tiny"].append(f"{fn} ({r['bytes']}B)")
    rep["phase1"][repo] = {k: v for k, v in f.items() if v and k != "n"} | {"n": f["n"]}

# ---------- Phase 2.3 Supersession (innerhalb je Repo, da Nummern repo-lokal) ----------
broken = []
for repo, rs in by_repo.items():
    nums = {r["num"]: r for r in rs if r["num"] is not None}
    for r in rs:
        st = (r.get("status") or "").lower()
        for field, val in (
            ("superseded_by", r.get("superseded_by")),
            ("supersedes", r.get("supersedes")),
        ):
            if not val or val.lower() in ("null", "none", "~", "[]", '""'):
                continue
            for tn in re.findall(r"ADR-?(\d+)", val):
                tn = int(tn)
                tgt = nums.get(tn)
                if tgt is None:
                    broken.append(
                        f"{repo}/{r['file']}: {field}=ADR-{tn} existiert nicht in {repo}"
                    )
                elif field == "supersedes" and (
                    tgt.get("status") or ""
                ).lower() not in ("superseded", "deprecated", "void"):
                    broken.append(
                        f"{repo}/{r['file']}: supersedes ADR-{tn}, aber Ziel-status={tgt.get('status')!r} (nicht superseded)"
                    )
        if st == "superseded" and not (r.get("superseded_by") or "").strip():
            broken.append(f"{repo}/{r['file']}: status=superseded ohne superseded_by")
rep["phase2"]["supersession_broken"] = broken


# ---------- Phase 2.2 Cross-Repo Titel-Duplikate ----------
def norm(t):
    t = re.sub(r"^adr[- ]?\d+[:. ]*", "", (t or "").lower())
    return re.sub(r"[^a-z0-9äöüß]+", " ", t).strip()


titles = collections.defaultdict(set)
for r in rows:
    n = norm(r.get("title"))
    if len(n) > 12:
        titles[n].add(r["repo"])
rep["phase2"]["cross_repo_title_dups"] = {
    t: sorted(rs) for t, rs in titles.items() if len(rs) > 1
}

json.dump(rep, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)

# Summary
p1 = rep["phase1"]


def total(key):
    return sum(len(v.get(key, [])) for v in p1.values())


print(f"repos={len(p1)} files={sum(v['n'] for v in p1.values())}")
for k in (
    "no_fm",
    "no_status",
    "bad_status",
    "no_date",
    "stale_proposed",
    "template_rest",
    "dup_nums",
    "tiny",
):
    print(f"{k}: {total(k)}")
print(f"supersession_broken: {len(broken)}")
print(f"cross_repo_title_dups: {len(rep['phase2']['cross_repo_title_dups'])}")
