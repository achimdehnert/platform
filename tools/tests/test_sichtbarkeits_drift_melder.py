"""Tests fuer tools/sichtbarkeits_drift_melder.py — ohne Netz, ohne git.

Die Klone werden als Verzeichnisse mit einer .git/config gefaelscht; der Melder
liest die Identitaet daraus und grept die Dateien. Netz-Zaehler bleiben None.
"""

from __future__ import annotations

import json
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
    assert "Umzug-Freigabe nach 7 Tagen" in kurzzeile(e)
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
        lambda q: (
            [
                ("achimdehnert/m-hub", ".github/workflows/ci.yml"),
                ("achimdehnert/x-hub", ".github/workflows/lint.yml"),
            ]
            if q.startswith("repository:")
            else []
        ),
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


# ── Zielort iilgmbh/platform (Owner-Entscheid 2026-10-04, #3234) ─────────────


def test_should_verweis_auf_zielort_als_aufrufer_zaehlen(tmp_path):
    """Nach dem Umzug bricht `uses: iilgmbh/platform/…` beim Privat-Schalter genauso."""
    _klon(
        tmp_path,
        "b-hub",
        "achimdehnert/b-hub",
        {
            ".github/workflows/ci.yml": "uses: iilgmbh/platform/.github/workflows/_x.yml@v1\n",
            "fetch.sh": "curl https://raw.githubusercontent.com/iilgmbh/platform/main/x\n",
        },
    )
    treffer = scanne_lokal(tmp_path)
    assert treffer["achimdehnert/b-hub"]["aufruf"] == [".github/workflows/ci.yml"]
    assert treffer["achimdehnert/b-hub"]["raw"] == ["fetch.sh"]


def test_should_platform_am_zielort_nicht_als_konsument_zaehlen(tmp_path):
    _klon(
        tmp_path,
        "platform",
        "iilgmbh/platform",
        {".github/workflows/ci.yml": "uses: iilgmbh/platform/.github/actions/x@main\n"},
    )
    assert scanne_lokal(tmp_path) == {}


def test_should_netzsuche_beide_orte_abfragen_und_beide_selbst_ausschliessen(
    monkeypatch,
):
    gefragt = []

    def fake_suche(abfrage):
        gefragt.append(abfrage)
        return [("iilgmbh/platform", "x.yml"), ("achimdehnert/platform", "y.yml")]

    monkeypatch.setattr(sdm, "suche_code", fake_suche)
    assert sdm.scanne_netz() == {}
    assert any("iilgmbh/platform" in a for a in gefragt)
    assert any("achimdehnert/platform" in a for a in gefragt)


# ── Wache: Secret-Schutz und Actions-Kosten ──────────────────────────────────


def test_should_plattform_lage_besitzer_nach_weiterleitung_und_schutzmaengel_lesen(
    monkeypatch,
):
    antwort = (
        '{"full_name": "iilgmbh/platform", "visibility": "private", "s": '
        '{"secret_scanning": {"status": "enabled"}, '
        '"secret_scanning_push_protection": {"status": "disabled"}}}'
    )
    monkeypatch.setattr(sdm, "_gh", lambda *a: antwort)
    assert sdm.plattform_lage() == {
        "besitzer": "iilgmbh/platform",
        "sichtbarkeit": "PRIVATE",
        "schutz_fehlt": ["secret_scanning_push_protection"],
    }


def test_should_plattform_lage_ohne_security_block_alles_als_fehlend_melden(
    monkeypatch,
):
    """Privatkonto + privat: GitHub liefert den Block gar nicht — das ist der Befund."""
    antwort = '{"full_name": "achimdehnert/platform", "visibility": "private", "s": {}}'
    monkeypatch.setattr(sdm, "_gh", lambda *a: antwort)
    assert sdm.plattform_lage()["schutz_fehlt"] == list(sdm.SCHUTZ_MERKMALE)


def test_should_kosten_je_besitzer_ueber_konto_oder_org_pfad_lesen(monkeypatch):
    pfade = []

    def fake_gh(*a):
        pfade.append(a[1])
        return (
            '[{"grossAmount": 1.5, "netAmount": 0, "unitType": "Minutes", "quantity": 250},'
            ' {"grossAmount": 2.25, "netAmount": 0.5, "unitType": "Minutes", "quantity": 375},'
            ' {"grossAmount": 0.01, "netAmount": 0, "unitType": "GigabyteHours",'
            ' "quantity": 40}]'
        )

    monkeypatch.setattr(sdm, "_gh", fake_gh)
    heute = date(2026, 10, 5)
    assert sdm.actions_kosten("achimdehnert/platform", heute) == {
        "brutto": 3.76,
        "netto": 0.5,
        "minuten": 625,
    }
    sdm.actions_kosten("iilgmbh/platform", heute)
    assert pfade[0].startswith("users/achimdehnert/settings/billing/usage?")
    assert pfade[1].startswith("organizations/iilgmbh/settings/billing/usage?")
    assert "year=2026&month=10" in pfade[1]


def test_should_kosten_ohne_billing_scope_als_nicht_messbar_melden(monkeypatch):
    monkeypatch.setattr(sdm, "_gh", lambda *a: None)
    assert sdm.actions_kosten("iilgmbh/platform", date(2026, 10, 5)) is None


def _lage(sicht="PUBLIC", fehlt=()):
    return {
        "besitzer": "iilgmbh/platform",
        "sichtbarkeit": sicht,
        "schutz_fehlt": list(fehlt),
    }


def test_should_wache_bei_fehlendem_schutz_oder_bezahlten_minuten_alarmieren():
    w = sdm.wache(_lage("PRIVATE", ["secret_scanning"]), {"brutto": 9.0, "netto": 1.0})
    assert w["alarm"] == ["schutz", "kosten"]
    e = bewerte({}, ["iilgmbh/shared-ci"], [], "PRIVATE", w)
    assert e["status"] == "WARN"
    assert "Wache: schutz, kosten" in kurzzeile(e)


def test_should_brutto_kosten_bei_oeffentlichem_repo_nicht_alarmieren():
    """Vor dem Umzug ist brutto > 0 normal — oeffentliche Repos zahlen netto 0."""
    w = sdm.wache(_lage(), {"brutto": 190.0, "netto": 0.0})
    assert w["alarm"] == [] and w["luecke"] == []
    assert bewerte({}, ["iilgmbh/shared-ci"], [], "PUBLIC", w)["status"] == "PASS"


def _kosten(minuten, netto=0.0):
    return {"brutto": minuten * 0.006, "netto": netto, "minuten": minuten}


def test_should_kontingent_last_vor_dem_umzug_org_und_platform_hochrechnen():
    """Realfall 8a0235 #7: netto 0, aber die Last waechst. Am 10. von 31 Tagen
    stehen 10 000 + 3 000 Minuten — hochgerechnet 40 300, also 81 % von 50 000."""
    lage = _lage() | {"besitzer": "achimdehnert/platform"}
    last = sdm.kontingent_last(lage, _kosten(3000), 10_000, date(2026, 10, 10))
    assert last["minuten_bisher"] == 13_000 and last["hochrechnung"] == 40_300
    w = sdm.wache(lage, _kosten(3000), last)
    assert w["alarm"] == ["kontingent"]
    e = bewerte({}, ["iilgmbh/shared-ci"], [], "PUBLIC", w)
    assert e["status"] == "WARN" and "Wache: kontingent" in kurzzeile(e)
    assert any("Org-Kontingent" in z for z in sdm.naechster_zug(e))


def test_should_kontingent_unter_der_schwelle_nicht_alarmieren():
    lage = _lage() | {"besitzer": "achimdehnert/platform"}
    last = sdm.kontingent_last(lage, _kosten(3000), 9_000, date(2026, 10, 10))
    assert last["anteil"] == 0.74
    assert sdm.wache(lage, _kosten(3000), last)["alarm"] == []


def test_should_platform_am_zielort_nicht_doppelt_zaehlen():
    """Nach dem Umzug steckt platform in den Org-Minuten — doppelt gezaehlt
    meldete die Wache Alarm, wo keiner ist."""
    last = sdm.kontingent_last(_lage(), _kosten(3000), 13_000, date(2026, 10, 10))
    assert last["minuten_bisher"] == 13_000


def test_should_kontingent_ohne_messung_nicht_raten():
    lage = _lage()
    assert sdm.kontingent_last(lage, None, 13_000, date(2026, 10, 10)) is None
    assert sdm.kontingent_last(lage, _kosten(1), None, date(2026, 10, 10)) is None
    assert sdm.kontingent_last(None, _kosten(1), 13_000, date(2026, 10, 10)) is None
    assert sdm.wache(lage, _kosten(1), None)["alarm"] == []


def test_should_org_minuten_ueber_alle_repos_der_zielorg_lesen(monkeypatch):
    aufrufe = []

    def fake_gh(*a):
        aufrufe.append(a)
        return '[{"unitType": "Minutes", "quantity": 990}, {"unitType": "GigabyteHours", "quantity": 8}]'

    monkeypatch.setattr(sdm, "_gh", fake_gh)
    assert sdm.org_minuten(date(2026, 10, 5)) == 990
    assert aufrufe[0][1].startswith("organizations/iilgmbh/settings/billing/usage?")
    assert "repositoryName" not in aufrufe[0][3]
    monkeypatch.setattr(sdm, "_gh", lambda *a: None)
    assert sdm.org_minuten(date(2026, 10, 5)) is None


def test_should_unmessbare_kosten_erst_nach_privat_schalter_unklar_machen():
    assert sdm.wache(_lage("PUBLIC"), None)["luecke"] == []
    w = sdm.wache(_lage("PRIVATE"), None)
    assert w["luecke"] == ["kosten"]
    e = bewerte({}, ["iilgmbh/shared-ci"], [], "PRIVATE", w)
    assert e["status"] == "UNKLAR"
    assert "nicht messbar (kosten)" in kurzzeile(e)


# ── Messreihe, Prognose, K5 ──────────────────────────────────────────────────


def _e(datum, rest_, status=None, repos=()):
    return {
        "datum": datum,
        "status": status or ("PASS" if rest_ == 0 else "WARN"),
        "rest": rest_,
        "repos": list(repos),
    }


def test_should_messreihe_einen_eintrag_je_tag_halten_letzter_lauf_gewinnt(tmp_path):
    pfad = tmp_path / "state" / "reihe.jsonl"
    reihe = sdm.schreibe_reihe(pfad, [], _e("2026-10-04", 9))
    reihe = sdm.schreibe_reihe(pfad, reihe, _e("2026-10-05", 8))
    reihe = sdm.schreibe_reihe(pfad, reihe, _e("2026-10-05", 7))
    geladen = sdm.lade_reihe(pfad)
    assert [(e["datum"], e["rest"]) for e in geladen] == [
        ("2026-10-04", 9),
        ("2026-10-05", 7),
    ]


def test_should_kaputte_zeile_ueberspringen_statt_reihe_verlieren(tmp_path):
    pfad = tmp_path / "reihe.jsonl"
    pfad.write_text('{"datum": "2026-10-01", "rest": 3}\n{kaputt\n')
    assert len(sdm.lade_reihe(pfad)) == 1


def test_should_null_datum_aus_abbau_trend_prognostizieren():
    reihe = [_e("2026-10-01", 8), _e("2026-10-03", 6), _e("2026-10-05", 4)]
    p = sdm.prognose(reihe, date(2026, 10, 5))
    assert p["steigung_pro_tag"] == -1.0
    assert p["null_am"] == "2026-10-09"


def test_should_ohne_abbau_kein_null_datum_nennen():
    reihe = [_e("2026-10-01", 4), _e("2026-10-05", 5)]
    p = sdm.prognose(reihe, date(2026, 10, 5))
    assert p["null_am"] is None and p["steigung_pro_tag"] > 0
    e = bewerte(
        {"x/y": {"aufruf": ["a"], "raw": []}}, ["iilgmbh/shared-ci"], [], "PUBLIC"
    )
    e["prognose"] = p
    assert "kein Abbau-Trend" in kurzzeile(e)


def test_should_alte_messungen_ausserhalb_des_fensters_ignorieren():
    reihe = [_e("2026-07-01", 50), _e("2026-10-01", 4), _e("2026-10-05", 4)]
    p = sdm.prognose(reihe, date(2026, 10, 5))
    assert p["steigung_pro_tag"] == 0.0 and p["null_am"] is None


def test_should_k5_erst_bei_pass_serie_ueber_sieben_kalendertage_melden():
    sechs = [_e(f"2026-10-0{t}", 0) for t in range(1, 7)]
    assert sdm.prognose(sechs, date(2026, 10, 6))["k5"] is False
    sieben = sechs + [_e("2026-10-07", 0)]
    p = sdm.prognose(sieben, date(2026, 10, 7))
    assert p["k5"] is True and p["pass_serie_tage"] == 7


def test_should_luecke_ohne_messung_serie_nicht_brechen_warn_aber_schon():
    mit_luecke = [_e("2026-10-01", 0), _e("2026-10-07", 0)]
    assert sdm.prognose(mit_luecke, date(2026, 10, 7))["k5"] is True
    mit_warn = [_e("2026-10-01", 0), _e("2026-10-04", 1), _e("2026-10-07", 0)]
    assert sdm.prognose(mit_warn, date(2026, 10, 7))["pass_serie_tage"] == 1


def test_should_neue_repos_als_rueckfall_melden():
    reihe = [
        _e("2026-10-04", 1, repos=["a/x"]),
        _e("2026-10-05", 1, repos=["a/x", "b/neu"]),
    ]
    assert sdm.prognose(reihe, date(2026, 10, 5))["rueckfall"] == ["b/neu"]


def test_should_offline_lauf_nicht_in_messreihe_schreiben(tmp_path):
    klone = tmp_path / "github"
    _klon(
        klone,
        "a-hub",
        "iilgmbh/a-hub",
        {"deploy.sh": "git clone https://github.com/achimdehnert/platform.git\n"},
    )
    reihe = tmp_path / "reihe.jsonl"
    reihe.write_text(json.dumps(_e("2026-10-05", 3)) + "\n")
    main(
        [
            "--kurz",
            "--offline",
            "--github-dir",
            str(klone),
            "--konzepte-dir",
            str(tmp_path),
            "--heute",
            "2026-10-05",
            "--messreihe",
            str(reihe),
        ]
    )
    assert sdm.lade_reihe(reihe)[0]["rest"] == 3


# ── Naechster Zug und oeffentliche Fassung ───────────────────────────────────


def test_should_fuer_jeden_zaehler_und_jeden_alarm_einen_naechsten_zug_kennen():
    """Invariante statt Stichprobe: ein neuer Zaehler ohne Zug-Text war der Live-Fehler
    vom 2026-10-05 (KeyError 'laufzeit')."""
    assert set(sdm.ZIEL) | {"schutz", "kosten", "kontingent"} <= set(sdm.ZUG)


def test_should_bei_k5_den_umzug_als_naechsten_zug_nennen():
    e = bewerte({}, ["iilgmbh/shared-ci"], [], "PUBLIC", sdm.wache(_lage(), None))
    e["prognose"] = {"k5": False, "pass_serie_tage": 3}
    assert sdm.naechster_zug(e) == ["PASS-Serie 3/7 Tage abwarten (K5)"]
    e["prognose"] = {"k5": True, "pass_serie_tage": 7}
    assert "Owner uebertraegt platform nach iilgmbh/platform" in sdm.naechster_zug(e)[0]


def test_should_oeffentliche_fassung_keine_repo_namen_und_betraege_enthalten():
    """Kontrollprobe D5: volle Fassung nennt Kunden-Repo und Betrag, oeffentliche nicht."""
    konsumenten = {
        "kunde-org/geheim-hub": {"aufruf": [], "raw": ["apps/core/x.py"]},
    }
    w = sdm.wache(_lage(), {"brutto": 123.45, "netto": 0.0})
    e = bewerte(konsumenten, ["iilgmbh/shared-ci"], [], "PUBLIC", w)
    e["prognose"] = sdm.prognose(
        [_e("2026-10-05", 1, repos=["kunde-org/geheim-hub"])], date(2026, 10, 5)
    )
    voll = json.dumps(e) + kurzzeile(e)
    assert "geheim-hub" in voll and "123.45" in voll
    oeff = json.dumps(sdm.oeffentlich(e)) + kurzzeile(e, oeffentlich_=True)
    assert "geheim-hub" not in oeff and "kunde-org" not in oeff and "123.45" not in oeff
