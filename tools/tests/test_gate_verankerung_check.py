"""Drill fuer tools/gate_verankerung_check.py (platform#2690 K4).

Der Pruefer entscheidet, ob ein Gate ueberhaupt verankert werden darf. Ein
Pruefer, der nur beweist, dass er gruen sein kann, ist genau der Melder, gegen
den er gebaut wurde — deshalb enthaelt dieser Drill zu jedem gruenen Fall die
Gegenprobe, und `test_should_positivkontrolle_realfall_altgate_rot_melden` ist
die Positivkontrolle des Pruefers auf sich selbst: ein Eintrag, der ROT sein MUSS.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gate_verankerung_check as gvc  # noqa: E402

REGISTRY_REAL = os.path.join(
    gvc.REPO_ROOT, "docs", "governance", "gate-registry.json"
)


def _gate(**over) -> dict:
    """Ein vollstaendig verankerter Eintrag; `over` bricht gezielt ein Kriterium."""
    gate = {
        "slug": "probe-gate-vollstaendig",
        "mode": "advisory",
        "owner": "achim",
        "module": "tools/probe_gate.py",
        "drill": "tools/tests/test_probe_gate.py",
        "built": "2026-09-02",
        "ref": "platform#2690",
        "positivkontrolle": {"ref": "platform#2690", "datum": "2026-09-02"},
    }
    gate.update(over)
    return gate


@pytest.fixture
def repo(tmp_path):
    """Wegwerf-Arbeitsbaum mit der Drill-Datei, auf die `_gate()` zeigt."""
    ziel = tmp_path / "tools" / "tests"
    ziel.mkdir(parents=True)
    (ziel / "test_probe_gate.py").write_text("def test_x(): pass\n", encoding="utf-8")
    return tmp_path


def _schreibe(pfad, gates: list[dict]) -> str:
    pfad.write_text(json.dumps({"gates": gates}, ensure_ascii=False), encoding="utf-8")
    return str(pfad)


def _lauf(argv: list[str]) -> int:
    return gvc.main(argv)


# --------------------------------------------------------------------------
# Einzelkriterien — je ein gruener Fall und seine Gegenprobe
# --------------------------------------------------------------------------


def test_should_vollstaendigen_eintrag_ohne_mangel_melden(repo, tmp_path):
    reg = _schreibe(tmp_path / "r.json", [_gate()])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    # Gegenprobe zum gruenen Lauf: derselbe Eintrag ohne Positivkontrolle unten.
    assert rc == 0


def test_should_fehlenden_drill_pfad_rot_melden(repo, tmp_path, capsys):
    gate = _gate(drill="tools/tests/test_gibt_es_nicht.py")
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "Drill-Datei fehlt" in capsys.readouterr().out


def test_should_leeres_drill_feld_rot_melden(repo, tmp_path, capsys):
    reg = _schreibe(tmp_path / "r.json", [_gate(drill="")])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "kein `drill`" in capsys.readouterr().out


def test_should_fehlende_positivkontrolle_rot_melden(repo, tmp_path, capsys):
    gate = _gate()
    del gate["positivkontrolle"]
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "keine `positivkontrolle`" in capsys.readouterr().out


def test_should_positivkontrolle_ohne_ref_rot_melden(repo, tmp_path, capsys):
    gate = _gate(positivkontrolle={"datum": "2026-09-02"})
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "ohne `ref`" in capsys.readouterr().out


def test_should_positivkontrolle_mit_unformigem_datum_rot_melden(repo, tmp_path, capsys):
    gate = _gate(positivkontrolle={"ref": "platform#1", "datum": "09/2026"})
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "kein ISO-Datum" in capsys.readouterr().out


def test_should_fehlenden_messpunkt_ohne_bau_datum_rot_melden(repo, tmp_path, capsys):
    gate = _gate()
    del gate["built"]
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "kein Nullpunkt" in capsys.readouterr().out


def test_should_slug_ausserhalb_der_wirkungs_slugform_rot_melden(repo, tmp_path, capsys):
    """`gate_wirkung._SLUG_TOKEN` findet `ProbeGate` in keiner Retro-Tabelle wieder."""
    reg = _schreibe(tmp_path / "r.json", [_gate(slug="ProbeGate")])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "ausserhalb der Slug-Form" in capsys.readouterr().out


def test_should_revised_als_nullpunkt_akzeptieren(repo, tmp_path):
    """`gate_wirkung.py` liest `revised or built` — der Pruefer muss dasselbe tun."""
    gate = _gate(revised="2026-09-02")
    del gate["built"]
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 0


def test_should_fremd_verankertes_gate_ohne_lokale_drill_datei_durchlassen(repo, tmp_path):
    """Der Drill laeuft in der CI des Ziel-Repos — der Beleg ist die `ref`."""
    gate = _gate(repo="ausschreibungs-hub", drill="tests/test_dort.py", ref="iilgmbh/x#7")
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 0


def test_should_fremd_verankertes_gate_ohne_ref_rot_melden(repo, tmp_path, capsys):
    gate = _gate(repo="ausschreibungs-hub", drill="tests/test_dort.py", ref="")
    reg = _schreibe(tmp_path / "r.json", [gate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1
    assert "ohne `ref`" in capsys.readouterr().out


# --------------------------------------------------------------------------
# --neu: Altbestand, Prosa-Aenderung, Neu-Verankerung
# --------------------------------------------------------------------------


def test_should_altbestand_bei_neu_ignorieren(repo, tmp_path, capsys):
    """31 Bestands-Gates haben keine Positivkontrolle — `--neu` darf sie nicht faerben."""
    alt = _gate(slug="alt-gate-ohne-kontrolle")
    del alt["positivkontrolle"]
    basis = _schreibe(tmp_path / "b.json", [alt])
    reg = _schreibe(tmp_path / "r.json", [alt])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", basis])
    assert rc == 0
    assert "kein neuer oder geaenderter" in capsys.readouterr().out


def test_should_prosa_aenderung_nicht_als_neuverankerung_werten(repo, tmp_path):
    """Ein Tippfehler-Fix im `note` eines Alt-Gates blockiert den PR nicht."""
    alt = _gate(slug="alt-gate-ohne-kontrolle", note="alter Text")
    del alt["positivkontrolle"]
    basis = _schreibe(tmp_path / "b.json", [alt])
    reg = _schreibe(tmp_path / "r.json", [{**alt, "note": "neuer Text"}])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", basis])
    assert rc == 0


def test_should_geaendertes_bau_datum_als_neuverankerung_pruefen(repo, tmp_path, capsys):
    """`revised` setzt die Rueckfall-Messung zurueck — dafuer gilt die volle Pflicht."""
    alt = _gate(slug="alt-gate-ohne-kontrolle")
    del alt["positivkontrolle"]
    basis = _schreibe(tmp_path / "b.json", [alt])
    reg = _schreibe(tmp_path / "r.json", [{**alt, "revised": "2026-09-02"}])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", basis])
    assert rc == 1
    ausgabe = capsys.readouterr().out
    assert "geaendert" in ausgabe
    assert "keine `positivkontrolle`" in ausgabe


def test_should_neues_gate_neben_rotem_altbestand_gruen_melden(repo, tmp_path):
    """Positivkontrolle der Abgrenzung: der rote Altbestand faerbt den neuen Eintrag nicht."""
    alt = _gate(slug="alt-gate-ohne-kontrolle")
    del alt["positivkontrolle"]
    basis = _schreibe(tmp_path / "b.json", [alt])
    reg = _schreibe(tmp_path / "r.json", [alt, _gate(slug="neu-gate-vollstaendig")])
    assert _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", basis]) == 0


def test_should_bei_unlesbarer_basis_exit_2_melden(repo, tmp_path, capsys):
    """Kein Verdikt ohne Vergleichsbasis — Werkzeugfehler ist nicht gruen."""
    reg = _schreibe(tmp_path / "r.json", [_gate()])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", "refs/gibt-es-nicht"])
    assert rc == 2
    assert "Basis nicht lesbar" in capsys.readouterr().out


def test_should_bei_unlesbarer_registry_exit_2_melden(tmp_path, capsys):
    kaputt = tmp_path / "r.json"
    kaputt.write_text("{ kein json", encoding="utf-8")
    assert _lauf(["--registry", str(kaputt), "--alle"]) == 2
    assert "nicht lesbar" in capsys.readouterr().out


# --------------------------------------------------------------------------
# --alle: Bilanz, nie ein Gate
# --------------------------------------------------------------------------


def test_should_bilanz_trotz_maengeln_exit_0_liefern(repo, tmp_path, capsys):
    alt = _gate(slug="alt-gate-ohne-kontrolle")
    del alt["positivkontrolle"]
    reg = _schreibe(tmp_path / "r.json", [alt, _gate()])
    assert _lauf(["--registry", reg, "--repo", str(repo), "--alle"]) == 0
    ausgabe = capsys.readouterr().out
    assert "vollstaendig verankert : 1/2" in ausgabe
    assert "ohne Positivkontrolle: 1" in ausgabe


# --------------------------------------------------------------------------
# Positivkontrolle des Pruefers + Erhaltung an der echten Registry
# --------------------------------------------------------------------------


def test_should_positivkontrolle_realfall_altgate_rot_melden(repo, tmp_path, capsys):
    """MUSS rot sein: ein Eintrag im Zuschnitt der 31 Bestands-Gates (2026-09-02).

    Faellt dieser Test je auf gruen, hat der Pruefer aufgehoert zu finden — dann
    ist er ein Melder ohne Positivkontrolle und dieses Gate seine eigene Fehlform.
    Der Eintrag traegt Drill und Messpunkt (beides bei allen 31 vorhanden), aber
    nur einen `note`-Satz statt eines Belegs, dass das Gate je getroffen hat.
    """
    altgate = {
        "slug": "blueprint-names-a-target-repo-in-an-instruction",
        "mode": "gate",
        "owner": "achim",
        "module": "tools/blaupause_check.py",
        "drill": "tools/tests/test_probe_gate.py",
        "built": "2026-09-01",
        "ref": "platform#2560",
        "note": "Positivkontrolle beim Bau: der Registry-weite Lauf fand sofort eine Stelle.",
    }
    reg = _schreibe(tmp_path / "r.json", [altgate])
    rc = _lauf(["--registry", reg, "--repo", str(repo), "--neu", "--basis", _schreibe(tmp_path / "b.json", [])])
    assert rc == 1, "Prosa im `note` darf nicht als Positivkontrolle durchgehen"
    assert "keine `positivkontrolle`" in capsys.readouterr().out


def test_should_echte_registry_ohne_drill_und_messpunkt_maengel_halten():
    """Erhaltung: jedes registrierte Gate bleibt drill- und messbar.

    Bewusst NICHT die Positivkontrolle mitgepruef — die ist Bestandsschutz
    (0/31 am 2026-09-02) und wird ueber `--neu` beim naechsten Anfassen
    eingefordert, nicht per Sammel-Rot.
    """
    gates = gvc.lade_registry(REGISTRY_REAL)
    assert gates, "Registry ohne Gates — der Test misst sonst nichts"
    maengel = [
        (g.get("slug"), name, text)
        for g in gates
        for name, text in [
            ("Drill", gvc.pruefe_drill(g)),
            ("Messpunkt", gvc.pruefe_messpunkt(g)),
        ]
        if text
    ]
    assert not maengel, f"{len(maengel)} Mangel/Maengel: {maengel}"


def test_should_eigenen_registry_eintrag_verankert_halten():
    """Der Pruefer steht selbst in der Registry — und erfuellt seine eigene Pflicht."""
    gates = gvc.lade_registry(REGISTRY_REAL)
    eigen = [g for g in gates if g.get("slug") == gvc.GATE_HEADER["slug"]]
    assert eigen, f"{gvc.GATE_HEADER['slug']} fehlt in der Registry"
    assert gvc.pruefe_gate(eigen[0])["maengel"] == []
