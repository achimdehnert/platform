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


def test_should_count_deploy_bausteine_as_laufzeit_although_they_live_in_ci():
    konsumenten = {
        "iilgmbh/shared-ci": {
            "aufruf": [],
            "raw": [
                ".github/workflows/_deploy-unified.yml",
                ".github/workflows/_deploy-hetzner.yml",
                ".github/workflows/_ci-python.yml",
            ],
        },
    }
    e = bewerte(
        konsumenten, kopien=["iilgmbh/shared-ci"], fristen=[], sichtbar="PUBLIC"
    )
    assert e["laufzeit"] == {
        "iilgmbh/shared-ci": [
            ".github/workflows/_deploy-unified.yml",
            ".github/workflows/_deploy-hetzner.yml",
        ]
    }


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


def test_should_uses_nur_unter_github_als_aufrufer_zaehlen(tmp_path):
    """Realfall mcp-hub: `uses: achimdehnert/platform/...` in docs/ADR-160 ist Doku."""
    _klon(
        tmp_path,
        "m-hub",
        "achimdehnert/m-hub",
        {
            "docs/ADR-160.md": "uses: achimdehnert/platform/.github/workflows/_x.yml@v1\n"
        },
    )
    assert scanne_lokal(tmp_path) == {}


def test_should_archivierte_konsumenten_aussortieren(monkeypatch):
    monkeypatch.setattr(
        sdm, "ist_archiviert", lambda repo: repo == "achimdehnert/research-hub"
    )
    lebend, archiviert = sdm.ohne_archivierte(
        {
            "achimdehnert/research-hub": {
                "aufruf": [".github/workflows/x.yml"],
                "raw": [],
            },
            "achimdehnert/bfagent": {"aufruf": [".github/workflows/ci.yml"], "raw": []},
        }
    )
    assert list(lebend) == ["achimdehnert/bfagent"]
    assert archiviert == ["achimdehnert/research-hub"]


def test_should_checkout_von_platform_in_fremder_ci_als_aufrufer_zaehlen(tmp_path):
    """Flotten-Workflow silent-failure-lint.yml: actions/checkout mit repository:
    achimdehnert/platform — bricht nach dem Flip, auch ohne `uses:`-Verweis."""
    _klon(
        tmp_path,
        "r-hub",
        "iilgmbh/r-hub",
        {
            ".github/workflows/silent-failure-lint.yml": (
                "steps:\n  - uses: actions/checkout@v7\n    with:\n"
                "      repository: achimdehnert/platform\n      path: _platform\n"
            )
        },
    )
    treffer = scanne_lokal(tmp_path)
    assert treffer["iilgmbh/r-hub"]["aufruf"] == [
        ".github/workflows/silent-failure-lint.yml"
    ]


def _checkout(token_zeile: str, einzug: str = "      ") -> str:
    """Checkout-Schritt wie in mcp-hub ci.yml; token_zeile leer = ohne Token."""
    return (
        "jobs:\n  t:\n    steps:\n"
        "      - uses: actions/checkout@v7\n        with:\n"
        "          repository: achimdehnert/platform\n"
        + (f"{einzug}{token_zeile}\n" if token_zeile else "")
        + "          path: _platform\n"
        "          sparse-checkout: |\n            skills\n"
        "      - name: weiter\n        run: echo ok\n"
    )


PAT = "token: ${{ secrets.PROJECT_PAT }}"


def test_should_checkout_mit_eigenem_secret_listen_aber_nicht_zaehlen(tmp_path):
    """Realfall mcp-hub ci.yml: PROJECT_PAT uebersteht den Flip — kein Aufrufer."""
    _klon(
        tmp_path,
        "m-hub",
        "achimdehnert/m-hub",
        {".github/workflows/ci.yml": _checkout(PAT, "          ")},
    )
    treffer = scanne_lokal(tmp_path)
    assert treffer["achimdehnert/m-hub"]["aufruf"] == []
    assert treffer["achimdehnert/m-hub"]["mit_token"] == [".github/workflows/ci.yml"]
    e = bewerte(treffer, [sdm.KANON], [], "PUBLIC")
    assert e["zaehler"]["aufrufer"] == 0
    assert e["mit_token"] == {"achimdehnert/m-hub": [".github/workflows/ci.yml"]}


def test_should_github_token_oder_fehlender_token_weiter_als_aufrufer_zaehlen():
    """Negativkontrollen: GITHUB_TOKEN kann ein privates Fremd-Repo nicht lesen."""
    assert not sdm.nur_token_checkouts(_checkout(""))
    assert not sdm.nur_token_checkouts(
        _checkout("token: ${{ secrets.GITHUB_TOKEN }}", "          ")
    )
    assert sdm.nur_token_checkouts(_checkout(PAT, "          "))


def test_should_token_ausserhalb_des_with_blocks_nicht_anerkennen():
    """Ein `token:` im Folgeschritt oder tiefer eingerueckt gehoert nicht zum Checkout."""
    fremd = _checkout("") + "        with:\n          " + PAT + "\n"
    assert not sdm.nur_token_checkouts(fremd)
    assert not sdm.nur_token_checkouts(_checkout(PAT, "            "))


def test_should_datei_mit_zusaetzlichem_uses_oder_klon_als_aufrufer_zaehlen():
    mit_uses = _checkout(PAT, "          ") + (
        "      - uses: achimdehnert/platform/.github/actions/x@main\n"
    )
    mit_klon = _checkout(PAT, "          ") + (
        "      - run: git clone https://github.com/achimdehnert/platform.git\n"
    )
    zweiter_ohne = _checkout(PAT, "          ") + _checkout("").split("steps:\n", 1)[1]
    for text in (mit_uses, mit_klon, zweiter_ohne, "", None):
        assert not sdm.nur_token_checkouts(text)


def test_should_netz_checkout_nach_dateiinhalt_klassifizieren(monkeypatch):
    monkeypatch.setattr(
        sdm,
        "suche_code",
        lambda q: [("achimdehnert/m-hub", ".github/workflows/ci.yml"),
                   ("achimdehnert/x-hub", ".github/workflows/lint.yml")]
        if q.startswith("repository:")
        else [],
    )
    inhalte = {
        "achimdehnert/m-hub": _checkout(PAT, "          "),
        "achimdehnert/x-hub": _checkout(""),
    }
    monkeypatch.setattr(sdm, "lies_datei_netz", lambda repo, pfad: inhalte[repo])
    netz = sdm.scanne_netz()
    assert netz["achimdehnert/m-hub"] == {
        "aufruf": [],
        "raw": [],
        "mit_token": [".github/workflows/ci.yml"],
    }
    assert netz["achimdehnert/x-hub"]["aufruf"] == [".github/workflows/lint.yml"]


def test_should_bei_widerspruch_der_quellen_aufrufer_bevorzugen():
    pfad = ".github/workflows/ci.yml"
    lokal = {"achimdehnert/m-hub": {"aufruf": [pfad], "raw": []}}
    netz = {"achimdehnert/m-hub": {"aufruf": [], "raw": [], "mit_token": [pfad]}}
    ges = sdm.vereinige(lokal, netz)
    assert ges["achimdehnert/m-hub"] == {"aufruf": [pfad], "raw": []}
