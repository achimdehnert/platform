"""Tests für scripts/list_megatest_repos.py (platform#1682).

Anlass: `megatest.yml` klonte 52 Repos als `achimdehnert/$repo`, obwohl 11 davon
unter `iilgmbh`/`meiki-lra`/`ttz-lif` liegen und die Registry den Owner längst
auflöst (`registry_api.owner`). Bei transferierten Repos verdeckte GitHubs
Redirect den Fehler — direkt in der Fremd-Org entstandene Repos blieben still
ungescannt. Der Resolver war gebaut, nur nicht aufgerufen.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SKRIPT = _ROOT / "scripts" / "list_megatest_repos.py"

sys.path.insert(0, str(_ROOT / "tools"))


def _lauf(*args):
    out = subprocess.run(
        [sys.executable, str(_SKRIPT), *args],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=_ROOT,
    )
    assert out.returncode == 0, out.stderr
    return out


def test_should_ohne_flag_weiter_nur_repo_namen_liefern():
    # Rückwärtskompatibilität: der alte Aufruf darf sich nicht ändern.
    namen = _lauf().stdout.split()
    assert namen
    assert all("/" not in n for n in namen)
    assert "platform" not in namen


def test_should_mit_owner_je_zeile_ein_slug_liefern():
    zeilen = [z for z in _lauf("--with-owner").stdout.splitlines() if z]
    assert zeilen
    assert all(z.count("/") == 1 for z in zeilen)


def test_should_dieselben_repos_wie_ohne_flag_abdecken():
    ohne = set(_lauf().stdout.split())
    mit = {z.split("/", 1)[1] for z in _lauf("--with-owner").stdout.splitlines() if z}
    assert mit == ohne, "Owner-Auflösung darf kein Repo verlieren oder erfinden"


def test_should_fremd_org_repos_nicht_unter_achimdehnert_adressieren():
    """Der eigentliche Fund: ohne diese Auflösung liefen 11 Repos auf den
    falschen Owner-Pfad. Der Test nennt bewusst konkrete Repos — er soll rot
    werden, wenn jemand die Auflösung wieder gegen einen Default tauscht."""
    slugs = dict(
        z.split("/", 1)[::-1] for z in _lauf("--with-owner").stdout.splitlines() if z
    )
    fremd = {r: o for r, o in slugs.items() if o != "achimdehnert"}
    assert len(fremd) >= 10, f"erwartet >=10 Fremd-Org-Repos, gefunden: {fremd}"
    assert fremd.get("frist-hub") == "meiki-lra"
    assert fremd.get("meiki-hub") == "meiki-lra"
    assert fremd.get("ttz-hub") == "ttz-lif"
    assert fremd.get("risk-hub") == "iilgmbh"
    assert fremd.get("iil-voice-agent") == "iilgmbh"


def test_should_repo_ohne_auflösbaren_owner_laut_ueberspringen(monkeypatch, capsys):
    """Kein stilles Zurückfallen auf den Default-Owner: ein Name ohne Owner
    verschwindet aus der Liste UND erzeugt eine WARN-Zeile auf stderr."""
    import registry_api

    import importlib.util

    spec = importlib.util.spec_from_file_location("lmr", _SKRIPT)
    lmr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lmr)

    echte_owner = registry_api.owner

    def kaputt(name, canon=None):
        return None if name == "risk-hub" else echte_owner(name, canon)

    monkeypatch.setattr(registry_api, "owner", kaputt)
    monkeypatch.setattr(sys, "argv", ["lmr", "--with-owner"])
    lmr.main()

    aus = capsys.readouterr()
    assert "risk-hub" not in aus.out.replace("iilgmbh/risk-hub", "")
    assert "ohne auflösbaren Owner" in aus.err
    assert "kein Default-Raten" in aus.err


@pytest.mark.parametrize("repo", ["frist-hub", "ttz-hub", "risk-hub"])
def test_should_registry_owner_und_liste_uebereinstimmen(repo):
    import registry_api

    slugs = {
        z.split("/", 1)[1]: z.split("/", 1)[0]
        for z in _lauf("--with-owner").stdout.splitlines()
        if z
    }
    assert slugs[repo] == registry_api.owner(repo)
