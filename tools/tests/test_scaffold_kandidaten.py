"""Tests fuer tools/scaffold_kandidaten.py (#2645): Owner aus der Registry, Fremd-Org
gezaehlt statt still, ruhende Repos ausgeschlossen. Kein Netz."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scaffold_kandidaten as sk  # noqa: E402

_CANON = {
    "meta": {
        "server": {"github_org": "achimdehnert"},
        "repo_owner": {"frist-hub": "meiki-lra"},
    },
    "repos": {
        "platform": {"flat": {"type": "infra"}},
        "risk-hub": {
            "flat": {"type": "django"},
            "rich": {"github": "iilgmbh/risk-hub"},
        },
        "dev-hub": {"flat": {"type": "django"}},
        "frist-hub": {"flat": {"type": "django"}},
        "bfagent": {"flat": {"type": "agent"}, "rich": {"lifecycle": "frozen"}},
        "old-hub": {"flat": {"type": "django"}, "lifecycle": "archived"},
        "aifw": {"flat": {"type": "library"}},
    },
}


def test_should_resolve_the_real_owner_per_repo_instead_of_the_platform_owner():
    plan = sk.plane(_CANON)
    assert {"owner": "iilgmbh", "repo": "risk-hub"} in plan["eigene"]
    assert {"owner": "achimdehnert", "repo": "dev-hub"} in plan["eigene"]


def test_should_count_a_foreign_org_repo_instead_of_crashing_on_it():
    plan = sk.plane(_CANON)
    assert plan["fremd"] == [{"owner": "meiki-lra", "repo": "frist-hub"}]
    assert "frist-hub" not in [e["repo"] for e in plan["eigene"]]


def test_should_exclude_frozen_archived_library_and_platform():
    namen = sk.kandidaten(_CANON)
    assert namen == ["dev-hub", "frist-hub", "risk-hub"]


def test_should_narrow_to_a_single_repo_on_dispatch_and_reject_a_non_candidate():
    assert [e["repo"] for e in sk.plane(_CANON, "risk-hub")["eigene"]] == ["risk-hub"]
    assert sk.plane(_CANON, "aifw") == {"eigene": [], "fremd": [], "unbekannt": []}


def test_should_write_github_output_lines(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.setattr(sk.registry_api, "load_canonical", lambda: _CANON)
    out = tmp_path / "out.txt"
    assert sk.main(["--github-output", str(out)]) == 0
    text = out.read_text()
    assert "count=2\n" in text and "foreign=1\n" in text and "unknown=0\n" in text
    assert '"owner": "iilgmbh"' in text
    assert "fremd:     meiki-lra/frist-hub" in capsys.readouterr().out
