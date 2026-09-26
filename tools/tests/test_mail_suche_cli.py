"""Der Aufruf-Weg zum Mail-Index (tools/mail_agent/suche.py).

Getestet wird, was hier tatsächlich entschieden wird: **wie der Aufruf gebaut
wird**. Die Suchlogik liegt im Management-Befehl und wird dort geprüft — sie
hier nachzubauen hiesse, dieselbe Regel zweimal zu pflegen.
"""

from __future__ import annotations

import importlib.util
import io
import json
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "mail_agent" / "suche.py"
_spec = importlib.util.spec_from_file_location("suche", _SRC)
su = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(su)


# --- Ziel-Auflösung ---------------------------------------------------------


def test_should_prefer_the_environment_override(monkeypatch):
    monkeypatch.setenv("MAIL_INDEX_SSH", "root@10.0.0.1")
    assert su.ssh_ziel() == "root@10.0.0.1"


def test_should_read_the_alias_from_hosts_yaml(monkeypatch, tmp_path):
    monkeypatch.delenv("MAIL_INDEX_SSH", raising=False)
    datei = tmp_path / "hosts.yaml"
    datei.write_text(
        "hosts:\n  dev:\n    ssh_alias: hetzner-dev\n  prod:\n    ssh_alias: hetzner-prod\n",
        encoding="utf-8",
    )
    assert su.ssh_ziel(datei) == "hetzner-prod"


def test_should_fail_loudly_when_the_host_is_unknown(monkeypatch, tmp_path):
    """Ein stillschweigender Fallback auf eine hartkodierte Adresse ist genau die
    Drift aus Issue #998 — lieber laut abbrechen."""
    monkeypatch.delenv("MAIL_INDEX_SSH", raising=False)
    datei = tmp_path / "hosts.yaml"
    datei.write_text("hosts:\n  dev:\n    ssh_alias: hetzner-dev\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="hetzner-prod"):
        su.ssh_ziel(datei)


def test_should_fail_loudly_when_hosts_yaml_is_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("MAIL_INDEX_SSH", raising=False)
    with pytest.raises(SystemExit, match="MAIL_INDEX_SSH"):
        su.ssh_ziel(tmp_path / "gibt-es-nicht.yaml")


# --- Aufbau des Aufrufs -----------------------------------------------------


def test_should_quote_the_remote_part_so_a_phrase_survives_the_second_shell():
    """Ein Suchbegriff mit Leerzeichen darf unterwegs nicht zerfallen.

    Die frühere Fassung dieses Tests prüfte, dass der Begriff als EIN Element in
    der lokalen Liste steht — das war er, und der Aufruf brach trotzdem: `ssh`
    fügt den fernen Teil zu einem String zusammen, den die entfernte Shell erneut
    zerlegt. Gemessen am 2026-08-18 endete `--begriff "Ihre Rückfragen"` in
    `unrecognized arguments: Rückfragen`. Geprüft wird deshalb jetzt die ferne
    Seite: Der Begriff muss dort gequotet ankommen.
    """
    befehl = su.befehl_bauen(["--begriff", "Rechnung Mittwald"], "hetzner-prod")
    assert isinstance(befehl, list)
    assert befehl[0] == "ssh"
    fern = befehl[-1]
    assert "'Rechnung Mittwald'" in fern


def test_should_leave_a_single_word_term_usable_as_before():
    befehl = su.befehl_bauen(["--begriff", "Postsortierung"], "hetzner-prod")
    assert "Postsortierung" in befehl[-1]


def test_should_call_the_management_command_in_the_container():
    befehl = su.befehl_bauen(["--json"], "hetzner-prod")
    assert befehl[-1].endswith("python manage.py mail_suche --json")
    assert befehl[:3] == ["ssh", "-o", "BatchMode=yes"]
    assert "hetzner-prod" in befehl
    fern = befehl[befehl.index("hetzner-prod") + 1]
    assert fern.startswith(f"docker exec {su.CONTAINER} ")


def test_should_use_batchmode_so_it_never_waits_for_a_password():
    befehl = su.befehl_bauen([], "hetzner-prod")
    assert "BatchMode=yes" in befehl


def test_should_reuse_one_ssh_connection_across_repeated_calls(monkeypatch, tmp_path):
    """#3069: `ablage_erledigt.py --pruefe` ruft dieses Skript bis zu 75x je
    Lauf auf; gemessen kostete jeder einzelne Aufruf 2-6,6s, fast nur
    Verbindungsaufbau. ControlMaster haengt Folgeaufrufe an eine schon
    offene Verbindung an, statt sie neu aufzubauen."""
    monkeypatch.setattr(su, "CONTROL_DIR", tmp_path / "control")
    befehl = su.befehl_bauen(["--json"], "hetzner-prod")
    assert "ControlMaster=auto" in befehl
    assert any(o.startswith("ControlPath=") for o in befehl)
    assert (tmp_path / "control").is_dir()


# --- Weiterreichen der Filter ----------------------------------------------


def _args(**kw):
    import argparse

    grund = dict(
        begriff="",
        von="",
        an="",
        seit="",
        bis="",
        ordner="",
        strang="",
        limit=50,
        tenant="",
        json=False,
        nur_deckung=False,
    )
    grund.update(kw)
    return argparse.Namespace(**grund)


def test_should_pass_only_the_filters_that_were_set():
    aus = su._durchgereichte(_args(von="offner@hnu.de"))
    assert aus == ["--von", "offner@hnu.de", "--limit", "50"]


def test_should_pass_the_flags_through():
    aus = su._durchgereichte(_args(json=True, nur_deckung=True))
    assert "--json" in aus and "--nur-deckung" in aus


def test_should_not_pass_empty_filters():
    """Ein leeres --ordner '' filterte auf den leeren Ordnernamen — also auf nichts."""
    aus = su._durchgereichte(_args(ordner="", begriff=""))
    assert "--ordner" not in aus and "--begriff" not in aus


# --- --batch (platform#3067) -------------------------------------------------


def test_should_build_the_batch_command_with_stdin_open():
    """`docker exec -i` haelt stdin offen — sonst kommt die JSON-Liste nie an."""
    befehl = su.batch_befehl_bauen("hetzner-prod")
    assert befehl[0] == "ssh"
    fern = befehl[-1]
    assert fern.endswith("python manage.py mail_suche --batch")
    assert fern.startswith(f"docker exec -i {su.CONTAINER} ")


def test_should_read_the_list_from_stdin_when_the_source_is_a_dash(monkeypatch):
    aufrufe = []

    class _Antwort:
        returncode = 0
        stdout = json.dumps([{"index": 0, "treffer": [], "deckung": {}}])
        stderr = ""

    def _run(befehl, input=None, **kw):  # noqa: A002
        aufrufe.append(input)
        return _Antwort()

    monkeypatch.setattr(su.subprocess, "run", _run)
    monkeypatch.setenv("MAIL_INDEX_SSH", "hetzner-prod")
    monkeypatch.setattr(
        su.sys, "stdin", io.StringIO(json.dumps([{"begriff": "Vertrag"}]))
    )
    aus = io.StringIO()
    monkeypatch.setattr(su.sys, "stdout", aus)

    code = su._batch_ausfuehren("-")

    assert code == 0
    assert json.loads(aufrufe[0]) == [{"begriff": "Vertrag"}]


def test_should_call_run_exactly_once_for_a_batch(monkeypatch, tmp_path):
    """Der ganze Witz von --batch: EINE Verbindung statt einer je Abfrage."""
    aufrufe = []

    class _Antwort:
        returncode = 0
        stdout = json.dumps([{"index": 0, "treffer": [], "deckung": {}}])
        stderr = ""

    def _run(befehl, input=None, **kw):  # noqa: A002
        aufrufe.append(input)
        return _Antwort()

    monkeypatch.setattr(su.subprocess, "run", _run)
    monkeypatch.setenv("MAIL_INDEX_SSH", "hetzner-prod")
    datei = tmp_path / "anfragen.json"
    datei.write_text(json.dumps([{"begriff": "Vertrag"}]), encoding="utf-8")
    aus = io.StringIO()
    monkeypatch.setattr(su.sys, "stdout", aus)

    code = su._batch_ausfuehren(str(datei))

    assert code == 0
    assert len(aufrufe) == 1
    assert json.loads(aufrufe[0]) == [{"begriff": "Vertrag"}]


def test_should_fall_back_to_single_queries_when_the_remote_batch_is_unknown(
    monkeypatch, tmp_path
):
    """Vor Merge/Deploy von dev-hub#351 kennt der entfernte Befehl --batch nicht."""
    rufe = []

    class _Batch:
        returncode = 2
        stdout = ""
        stderr = "manage.py mail_suche: error: unrecognized arguments: --batch"

    class _Einzeln:
        returncode = 0
        stdout = json.dumps({"treffer": [], "deckung": {}})
        stderr = ""

    def _run(befehl, input=None, **kw):  # noqa: A002
        rufe.append(befehl)
        return _Batch() if input is not None else _Einzeln()

    monkeypatch.setattr(su.subprocess, "run", _run)
    monkeypatch.setenv("MAIL_INDEX_SSH", "hetzner-prod")
    datei = tmp_path / "anfragen.json"
    datei.write_text(json.dumps([{"begriff": "Vertrag"}]), encoding="utf-8")
    aus = io.StringIO()
    fehler = io.StringIO()
    monkeypatch.setattr(su.sys, "stdout", aus)
    monkeypatch.setattr(su.sys, "stderr", fehler)

    code = su._batch_ausfuehren(str(datei))

    assert code == 0
    assert "Einzelabfragen" in fehler.getvalue()
    assert json.loads(aus.getvalue()) == [{"index": 0, "treffer": [], "deckung": {}}]
