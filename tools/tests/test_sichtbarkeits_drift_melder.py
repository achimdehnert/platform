"""Tests fuer tools/sichtbarkeits_drift_melder.py — ohne Netz, ohne git.

Die Klone werden als Verzeichnisse mit einer .git/config gefaelscht; der Melder
liest die Identitaet daraus und grept die Dateien. Netz-Zaehler bleiben None.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sichtbarkeits_drift_melder as sdm  # noqa: E402
from sichtbarkeits_drift_melder import (  # noqa: E402
    abgelaufene_fristen,
    bewerte,
    kurzzeile,
    main,
    scanne_lokal,
)


def _klon(root: Path, name: str, origin: str, dateien: dict[str, str]) -> None:
    """Echter Klon mit einem Commit und origin/main — der Melder liest den Ref."""
    d = root / name
    d.mkdir(parents=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@x",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@x",
    }

    def run(*a: str) -> None:
        subprocess.run(
            ["git", "-C", str(d), *a], check=True, capture_output=True, env=env
        )

    run("init", "-q", "-b", "main")
    run("remote", "add", "origin", f"git@github.com:{origin}.git")
    for rel, inhalt in dateien.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt)
    run("add", "-A")
    run("commit", "-q", "-m", "init")
    run("update-ref", "refs/remotes/origin/main", "HEAD")


def _konzept(d: Path, cid: str, status: str, frist: str) -> None:
    (d / f"{cid}-x.md").write_text(
        f"---\nconcept_id: {cid}\npipeline_status: {status}\nreview_by: {frist}\n---\n# {cid}\n"
    )


def test_should_aufrufer_und_raw_getrennt_zaehlen_und_self_ausschliessen(tmp_path):
    _klon(
        tmp_path,
        "a-hub",
        "meiki-lra/a-hub",
        {
            ".github/workflows/ci.yml": "jobs:\n  ci:\n    uses: achimdehnert/platform/.github/workflows/_x.yml@v1\n"
        },
    )
    _klon(
        tmp_path,
        "b-hub",
        "achimdehnert/b-hub",
        {
            "apps/core/registry.py": "URL = 'https://raw.githubusercontent.com/achimdehnert/platform/main/x.yaml'\n"
        },
    )
    _klon(
        tmp_path,
        "platform",
        "achimdehnert/platform",
        {
            ".github/workflows/ci.yml": "uses: achimdehnert/platform/.github/actions/x@main\n"
        },
    )
    treffer = scanne_lokal(tmp_path)
    assert set(treffer) == {"meiki-lra/a-hub", "achimdehnert/b-hub"}
    assert treffer["meiki-lra/a-hub"]["aufruf"] == [".github/workflows/ci.yml"]
    assert treffer["achimdehnert/b-hub"]["raw"] == ["apps/core/registry.py"]


def test_should_worktree_klon_ohne_git_verzeichnis_ignorieren(tmp_path):
    d = tmp_path / "wt"
    d.mkdir()
    (d / ".git").write_text("gitdir: /irgendwo\n")
    (d / "x.yml").write_text("uses: achimdehnert/platform/.github/workflows/_x.yml\n")
    assert scanne_lokal(tmp_path) == {}


def test_should_laufzeit_nur_fuer_code_ausserhalb_ci_klickdummy_doku_melden():
    konsumenten = {
        "achimdehnert/dev-hub": {
            "aufruf": [],
            "raw": ["apps/core/platform_registry.py"],
        },
        "achimdehnert/apo-hub": {
            "aufruf": [],
            "raw": ["klickdummy/sitemap/screens-spec.yaml"],
        },
        "achimdehnert/c-hub": {
            "aufruf": [],
            "raw": ["docs/x.md", ".github/workflows/y.yml"],
        },
    }
    e = bewerte(
        konsumenten, kopien=["iilgmbh/shared-ci"], fristen=[], sichtbar="PUBLIC"
    )
    assert e["zaehler"]["raw"] == 3
    assert e["laufzeit"] == {"achimdehnert/dev-hub": ["apps/core/platform_registry.py"]}
    assert e["status"] == "WARN"
    assert "dev-hub" in kurzzeile(e)


def test_should_frist_nur_fuer_aktive_konzepte_melden(tmp_path):
    _konzept(tmp_path, "KONZ-platform-001", "decided", "2026-09-15")
    _konzept(tmp_path, "KONZ-platform-002", "sunset", "2026-01-01")
    _konzept(tmp_path, "KONZ-platform-003", "idea", "2026-12-31")
    (tmp_path / "KONZ-platform-004-ohne-frist.md").write_text(
        "---\npipeline_status: idea\n---\n"
    )
    assert abgelaufene_fristen(tmp_path, date(2026, 9, 16)) == ["KONZ-platform-001"]


def test_should_pass_bei_zielwerten_und_rolle_nach_sichtbarkeit_unterscheiden():
    e = bewerte({}, kopien=["iilgmbh/shared-ci"], fristen=[], sichtbar="PUBLIC")
    assert e["status"] == "PASS"
    assert "Flip-Freigabe nach 7 Tagen" in kurzzeile(e)
    e2 = bewerte({}, kopien=["iilgmbh/shared-ci"], fristen=[], sichtbar="PRIVATE")
    assert "kein Rueckfall" in kurzzeile(e2)


def test_should_offline_nie_entwarnen(tmp_path):
    """Ohne Netz sind Kopien und Sichtbarkeit unbekannt — das darf kein PASS sein."""
    e = bewerte({}, kopien=None, fristen=[], sichtbar=None)
    assert e["status"] == "UNKLAR"
    assert "nicht messbar" in kurzzeile(e)


def test_should_kurz_offline_lauf_ergebnisdatei_schreiben(tmp_path, capsys):
    klone = tmp_path / "github"
    _klon(
        klone,
        "a-hub",
        "iilgmbh/a-hub",
        {"deploy.sh": "git clone https://github.com/achimdehnert/platform.git\n"},
    )
    konz = tmp_path / "konzepte"
    konz.mkdir()
    ziel = tmp_path / "melder" / "sichtbarkeit.json"
    rc = main(
        [
            "--kurz",
            "--offline",
            "--github-dir",
            str(klone),
            "--konzepte-dir",
            str(konz),
            "--heute",
            "2026-09-16",
            "--ergebnis-datei",
            str(ziel),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    # Ein lokaler Treffer ist WARN, auch offline — nur die Netz-Zaehler bleiben ◌.
    assert "Aufrufer 1" in out and "Kopien ◌" in out
    assert ziel.is_file()


def test_should_archivierte_repos_nicht_als_kopie_zaehlen(monkeypatch):
    """Ein eingefrorenes Duplikat kann nicht mehr divergieren — K3 misst Divergenz."""
    antworten = {
        ("repo", "view", "achimdehnert/platform"): "false\n",
        ("repo", "view", "achimdehnert/shared-ci"): "true\n",
        ("repo", "view", "iilgmbh/shared-ci"): "false\n",
        (
            "api",
            "repos/achimdehnert/platform/contents/.github/workflows",
        ): "_a.yml\nci.yml\n",
        ("api", "repos/iilgmbh/shared-ci/contents/.github/workflows"): "_a.yml\n",
    }

    def fake_gh(*args):
        return antworten.get(args[:3] if args[0] == "repo" else args[:2])

    monkeypatch.setattr(sdm, "_gh", fake_gh)
    assert sdm.zaehle_kopien() == ["achimdehnert/platform", "iilgmbh/shared-ci"]


def test_should_origin_main_und_nicht_die_arbeitskopie_lesen(tmp_path):
    """Stale Klon: origin/main ist schon umgehaengt, die Arbeitskopie nicht — zaehlt nicht."""
    _klon(
        tmp_path,
        "x-hub",
        "achimdehnert/x-hub",
        {
            ".github/workflows/ci.yml": "uses: iilgmbh/shared-ci/.github/actions/x@main\n"
        },
    )
    (tmp_path / "x-hub" / ".github" / "workflows" / "ci.yml").write_text(
        "uses: achimdehnert/platform/.github/actions/x@main\n"
    )
    assert scanne_lokal(tmp_path) == {}
