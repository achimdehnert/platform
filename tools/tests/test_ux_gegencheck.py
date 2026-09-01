"""Drill fuer die zwei Gegenchecks (KONZ-platform-051 K7/K8).

Beide Checks sollen ETWAS FINDEN, das der Klick-Durchlauf allein nicht findet.
Ein Check, der nie rot wird, erfuellt K7/K8 scheinbar und belegt nichts —
deshalb steht hier zu jedem gruenen Fall die Gegenprobe, und der teuerste Fall
ist der Kontrollmarker: schlaegt er an, ist die GANZE Messung ungueltig, nicht
nur ein Fund.
"""

import json
import subprocess
import sys
from pathlib import Path

import yaml

TOOL = Path(__file__).resolve().parents[1] / "ux_gegencheck.py"
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("ux_gegencheck", TOOL)
ug = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ug)


def _run(*args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args], capture_output=True, text=True, timeout=600
    )


def _spec_datei(tmp_path, screens):
    p = tmp_path / "spec.yaml"
    p.write_text(yaml.safe_dump({"screens": screens}, allow_unicode=True), encoding="utf-8")
    return p


def _stationen_datei(tmp_path, stationen, name="stationen.json"):
    p = tmp_path / name
    p.write_text(json.dumps(stationen, ensure_ascii=False), encoding="utf-8")
    return p


SCREENS = [
    {"id": "start", "title": "Session starten", "flow_anchor": "Phase 1", "routing_mode": "live"},
    {"id": "entwurf", "title": "Entwurf schreiben", "flow_anchor": "Phase 1", "routing_mode": "live"},
    {"id": "export", "title": "Export", "flow_anchor": "Phase 2", "routing_mode": "live"},
    {"id": "skizze", "title": "Nur gezeichnet", "flow_anchor": "Phase 1", "routing_mode": "static"},
]


# ── K7: KD-Gegencheck ──────────────────────────────────────────────────────


def test_should_find_spec_screen_without_app_path(tmp_path):
    """Der Fall, den K7 verlangt: ein Screen, den der Durchlauf nie erreicht hat."""
    spec = _spec_datei(tmp_path, SCREENS)
    st = _stationen_datei(tmp_path, [{"id": "start", "titel": "Session starten"}])
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "Phase 1")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "weg-fehlt" in r.stdout
    assert "entwurf" in r.stdout


def test_should_stay_green_when_every_live_screen_was_visited(tmp_path):
    """Gegenprobe: derselbe Aufbau, alle Live-Screens besucht."""
    spec = _spec_datei(tmp_path, SCREENS)
    st = _stationen_datei(
        tmp_path,
        [{"id": "start", "titel": "Session starten"}, {"id": "entwurf", "titel": "Entwurf schreiben"}],
    )
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "Phase 1")
    assert r.returncode == 0, r.stdout + r.stderr


def test_should_not_judge_screens_outside_the_chain(tmp_path):
    """R5-Gegenmittel: was die Kette nicht abdeckt, wird nicht beurteilt statt
    falsch beurteilt. `export` haengt an Phase 2 und darf nicht rot machen."""
    spec = _spec_datei(tmp_path, SCREENS)
    st = _stationen_datei(
        tmp_path,
        [{"id": "start", "titel": "Session starten"}, {"id": "entwurf", "titel": "Entwurf schreiben"}],
    )
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "Phase 1")
    assert "export" not in r.stdout.split("Ergebnis:")[0].split("nicht beurteilt")[0]
    assert "ausserhalb der Kette" in r.stdout


def test_should_flag_the_same_screen_when_the_chain_does_cover_it(tmp_path):
    """Gegenprobe zur vorigen: deckt die Kette Phase 2 ab, ist `export` sehr wohl
    ein Befund. Die Ausnahme haengt an der Kette, nicht am Screen."""
    spec = _spec_datei(tmp_path, SCREENS)
    st = _stationen_datei(
        tmp_path,
        [{"id": "start", "titel": "Session starten"}, {"id": "entwurf", "titel": "Entwurf schreiben"}],
    )
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "Phase 1,Phase 2")
    assert r.returncode == 1
    assert "export" in r.stdout


def test_should_not_demand_a_path_for_static_screens(tmp_path):
    """`routing_mode: static` schuldet keinen Live-Weg."""
    spec = _spec_datei(tmp_path, SCREENS)
    st = _stationen_datei(
        tmp_path,
        [{"id": "start", "titel": "Session starten"}, {"id": "entwurf", "titel": "Entwurf schreiben"}],
    )
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "Phase 1")
    assert "kein Live-Weg geschuldet" in r.stdout


def test_should_report_visited_station_missing_from_spec(tmp_path):
    spec = _spec_datei(tmp_path, SCREENS)
    st = _stationen_datei(
        tmp_path,
        [
            {"id": "start", "titel": "Session starten"},
            {"id": "entwurf", "titel": "Entwurf schreiben"},
            {"id": "neu", "titel": "Vom Team nachgebaut"},
        ],
    )
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "Phase 1")
    assert "spec-luecke" in r.stdout and "Vom Team nachgebaut" in r.stdout


def test_should_match_titles_despite_umlauts_and_dashes(tmp_path):
    spec = _spec_datei(
        tmp_path, [{"id": "a", "title": "Entwürfe – prüfen", "flow_anchor": "P", "routing_mode": "live"}]
    )
    st = _stationen_datei(tmp_path, [{"titel": "entwuerfe pruefen"}])
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "P")
    assert r.returncode == 0, r.stdout


def test_should_fail_loudly_when_the_filter_judges_nothing(tmp_path):
    """Die Null darf nie aus dem eigenen Filter kommen: deckt die Kette keinen
    einzigen Screen ab, ist das ein Fehler, kein gruenes Ergebnis."""
    spec = _spec_datei(tmp_path, SCREENS)
    st = _stationen_datei(tmp_path, [{"id": "start", "titel": "Session starten"}])
    r = _run("kd", "--spec", str(spec), "--stationen", str(st), "--kette-deckt", "Phase 99")
    assert r.returncode == 2
    assert "Filter frisst die Spec" in r.stderr


def test_should_fail_loudly_on_spec_without_screens(tmp_path):
    p = tmp_path / "spec.yaml"
    p.write_text(yaml.safe_dump({"title": "ohne screens"}), encoding="utf-8")
    st = _stationen_datei(tmp_path, [{"id": "x", "titel": "x"}])
    r = _run("kd", "--spec", str(p), "--stationen", str(st))
    assert r.returncode == 2 and "screens" in r.stderr


# ── K8: Marker ─────────────────────────────────────────────────────────────


def _lauf(tmp_path, texte):
    return _stationen_datei(
        tmp_path, [{"titel": f"Station {i+1}", "text": t} for i, t in enumerate(texte)], "marker.json"
    )


def test_should_find_the_break_where_the_name_disappears(tmp_path):
    """Der Realfall C11: Protagonist heisst im Konzept 'Milo Heller', in der
    erzeugten Gliederung 'Franz' — HTTP-gruen, inhaltlich gerissen."""
    st = _lauf(tmp_path, ["Konzept fuer Milo Heller", "Gliederung: Milo Heller", "Kapitel 1: Franz geht"])
    r = _run("marker", "--stationen", str(st), "--marker", "Milo Heller")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "marker-riss" in r.stdout and "Station 3" in r.stdout


def test_should_stay_green_when_the_name_survives(tmp_path):
    """Gegenprobe: derselbe Lauf, der Name haelt durch."""
    st = _lauf(tmp_path, ["Konzept fuer Milo Heller", "Gliederung: Milo Heller", "Kapitel 1: Milo Heller geht"])
    r = _run("marker", "--stationen", str(st), "--marker", "Milo Heller")
    assert r.returncode == 0, r.stdout


def test_should_declare_the_whole_measurement_invalid_when_control_marker_hits(tmp_path):
    """Der teuerste Fall: schlaegt der Kontrollmarker an, ist die Messung
    ungueltig — nicht nur dieser eine Fund."""
    st = _lauf(tmp_path, [f"Text mit {ug.KONTROLLMARKER}", "zweite Station"])
    r = _run("marker", "--stationen", str(st), "--marker", "Milo Heller")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "wertlos" in r.stderr


def test_should_confirm_control_marker_is_zero_on_a_normal_run(tmp_path):
    """Gegenprobe zur vorigen — und der Beleg, dass der Suchlauf ueberhaupt
    sucht statt alles durchzuwinken."""
    st = _lauf(tmp_path, ["Konzept fuer Milo Heller", "Gliederung: Milo Heller"])
    r = _run("marker", "--stationen", str(st), "--marker", "Milo Heller")
    assert "0 Treffer" in r.stdout and r.returncode == 0


def test_should_flag_a_marker_that_never_appeared_at_all(tmp_path):
    """Ein Marker, der schon in Station 1 fehlt, ist kein Riss, sondern ein
    Eingabefehler — und muss anders heissen, sonst sucht man an der falschen
    Stelle."""
    st = _lauf(tmp_path, ["gar nichts", "auch nichts"])
    r = _run("marker", "--stationen", str(st), "--marker", "Milo Heller")
    assert r.returncode == 1
    assert "marker-nie-gesetzt" in r.stdout


def test_should_report_the_trace_per_marker(tmp_path):
    st = _lauf(tmp_path, ["Milo Heller und Ada Brandt", "Milo Heller", "niemand"])
    r = _run("marker", "--stationen", str(st), "--marker", "Milo Heller,Ada Brandt")
    assert "Milo Heller: xx." in r.stdout
    assert "Ada Brandt: x.." in r.stdout


def test_should_fail_loudly_without_stations(tmp_path):
    st = _stationen_datei(tmp_path, [], "leer.json")
    r = _run("marker", "--stationen", str(st), "--marker", "Milo Heller")
    assert r.returncode == 2 and "ohne Text" in r.stderr


# ── Der echte Bestand ──────────────────────────────────────────────────────


def test_should_read_a_real_klickdummy_spec():
    """Positivkontrolle gegen echte Daten: das Werkzeug muss eine Spec aus dem
    Bestand lesen koennen, nicht nur die Fixtures dieses Tests."""
    echt = Path.home() / "github" / "writing-hub" / "klickdummy" / "creative-studio" / "spec.yaml"
    if not echt.is_file():
        import pytest

        pytest.skip(f"{echt} nicht vorhanden — Klon fehlt")
    screens = ug.lade_spec(echt)
    assert len(screens) >= 1
    assert all("id" in s and "title" in s for s in screens)
