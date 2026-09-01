"""Drill fuer den Blaupausen-Check (KONZ-platform-051 K6, Weg (a) — #2560).

Die Kernfrage ist nicht „meldet er gruen?", sondern „kann er ueberhaupt rot
werden?". Ein Blaupausen-Check, dessen Null aus dem eigenen Filter stammt,
ist schlimmer als keiner: er behauptet eine Eigenschaft, die er nie geprueft
hat. Deshalb steht hier zu jedem gruenen Fall die Gegenprobe daneben.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

TOOL = Path(__file__).resolve().parents[1] / "blaupause_check.py"
WURZEL = Path(__file__).resolve().parents[2]
ECHTE_DATEI = WURZEL / ".windsurf/workflows/ux-review.md"
ECHTE_REGISTRY = WURZEL / "registry/canonical.yaml"


def _run(datei, registry=ECHTE_REGISTRY):
    return subprocess.run(
        [sys.executable, str(TOOL), "--datei", str(datei), "--registry", str(registry)],
        capture_output=True,
        text=True,
        timeout=600,
    )


def _registry(tmp_path, **repos):
    """Minimal-Registry; Default-Typ 'django' = Ziel-Repo mit Oberflaeche."""
    pfad = tmp_path / "reg.yaml"
    pfad.write_text(
        yaml.safe_dump(
            {"repos": {n: {"rich": {"type": t}} for n, t in repos.items()}},
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return pfad


def _datei(tmp_path, inhalt):
    pfad = tmp_path / "skill.md"
    pfad.write_text(textwrap.dedent(inhalt), encoding="utf-8")
    return pfad


# ── Der echte Stand ────────────────────────────────────────────────────────

def test_should_echte_blaupause_gruen_melden():
    r = _run(ECHTE_DATEI)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "kein Ziel-Repo-Name in einer Anweisung" in r.stdout


def test_should_echte_blaupause_ueberhaupt_bloecke_pruefen():
    """Positivkontrolle zum gruenen Lauf: die Null darf nicht daher kommen,
    dass gar nichts im Scope lag."""
    r = _run(ECHTE_DATEI)
    zahl = int(r.stdout.split("Anweisungs-Bloecke:")[1].split()[0])
    assert zahl > 50, f"nur {zahl} Bloecke im Scope — der Filter frisst die Datei"
    namen = int(r.stdout.split("Ziel-Repos aus Registry:")[1].split()[0])
    assert namen > 10, f"nur {namen} Ziel-Repos — die Registry wird nicht gelesen"


# ── Gegenprobe: wird er rot, wenn er rot werden muss? ──────────────────────

def test_should_nackten_repo_namen_in_anweisung_finden(tmp_path):
    datei = _datei(
        tmp_path,
        """\
        ## Step 1: Umgebung

        1. Starte den Stack von writing-hub und melde dich an.
        """,
    )
    r = _run(datei, _registry(tmp_path, **{"writing-hub": "django"}))
    assert r.returncode == 1, r.stdout
    assert "writing-hub" in r.stdout
    assert "Step 1" in r.stdout


def test_should_denselben_satz_mit_beleg_marker_durchlassen(tmp_path):
    """Negativkontrolle zur vorigen: nur der Marker unterscheidet die Faelle."""
    datei = _datei(
        tmp_path,
        """\
        ## Step 1: Umgebung

        1. Starte den Stack von writing-hub und melde dich an (Realfall 2026-08-25).
        """,
    )
    r = _run(datei, _registry(tmp_path, **{"writing-hub": "django"}))
    assert r.returncode == 0, r.stdout


def test_should_beleg_eine_zeile_tiefer_im_selben_listenpunkt_gelten_lassen(tmp_path):
    """Der Defekt, an dem der Original-grep scheiterte (#2560, Zeile 18):
    der Beleg steht regelmaessig unter dem Namen, den er belegt."""
    datei = _datei(
        tmp_path,
        """\
        ## Step 1: Umgebung

        1. Cache nach jedem Reseed leeren, sonst misst der Lauf den alten
           Stand — writing-hub#766.
        """,
    )
    r = _run(datei, _registry(tmp_path, **{"writing-hub": "django"}))
    assert r.returncode == 0, r.stdout


def test_should_beleg_aus_fremdem_listenpunkt_nicht_gelten_lassen(tmp_path):
    """Gegenprobe zur Block-Logik: der Marker darf nicht ueber Punktgrenzen
    hinweg decken, sonst deckt ein Beleg die ganze Seite."""
    datei = _datei(
        tmp_path,
        """\
        ## Step 1: Umgebung

        1. Ein belegter Punkt — writing-hub#766, 2026-08-25.
        2. Starte den Stack von ausschreibungs-hub und melde dich an.
        """,
    )
    r = _run(
        tmp_path / "skill.md",
        _registry(tmp_path, **{"writing-hub": "django", "ausschreibungs-hub": "django"}),
    )
    assert r.returncode == 1, r.stdout
    assert "ausschreibungs-hub" in r.stdout


# ── Scope: Beleg-Abschnitte bleiben aussen vor ────────────────────────────

def test_should_repo_namen_im_changelog_nicht_melden(tmp_path):
    datei = _datei(
        tmp_path,
        """\
        ## Changelog

        - Lauf gegen writing-hub, danach ausschreibungs-hub.
        """,
    )
    r = _run(datei, _registry(tmp_path, **{"writing-hub": "django", "ausschreibungs-hub": "django"}))
    assert r.returncode == 0, r.stdout


def test_should_neuen_unbekannten_abschnitt_als_anweisung_behandeln(tmp_path):
    """Fail-closed: ein Abschnitt, den niemand ausgenommen hat, wird geprueft."""
    datei = _datei(
        tmp_path,
        """\
        ## Step 8: Ein Abschnitt, den es gestern noch nicht gab

        Starte writing-hub.
        """,
    )
    r = _run(datei, _registry(tmp_path, **{"writing-hub": "django"}))
    assert r.returncode == 1, r.stdout


# ── Ziel-Repos vs. Bibliotheken ───────────────────────────────────────────

def test_should_bibliothek_in_anweisung_nicht_als_zuschneidung_werten(tmp_path):
    """`aifw` ist nie Ziel eines Klick-Durchlaufs — es zu nennen ist so wenig
    eine Zuschneidung wie „Redis"."""
    datei = _datei(
        tmp_path,
        """\
        ## Step 1: Umgebung

        1. Nach jedem Reseed den Cache leeren (aifw: Redis, TTL 600 s).
        """,
    )
    r = _run(datei, _registry(tmp_path, aifw="library", **{"writing-hub": "django"}))
    assert r.returncode == 0, r.stdout


def test_should_dieselbe_zeile_bei_gui_typ_sehr_wohl_melden(tmp_path):
    """Gegenprobe: die Ausnahme haengt am Typ, nicht am Namen."""
    datei = _datei(
        tmp_path,
        """\
        ## Step 1: Umgebung

        1. Nach jedem Reseed den Cache leeren (aifw: Redis, TTL 600 s).
        """,
    )
    r = _run(datei, _registry(tmp_path, aifw="django", **{"writing-hub": "django"}))
    assert r.returncode == 1, r.stdout


def test_should_teilwort_nicht_als_treffer_werten(tmp_path):
    datei = _datei(
        tmp_path,
        """\
        ## Step 1: Umgebung

        1. Der Ordner heisst nicht-writing-hub-artig und ist harmlos.
        """,
    )
    r = _run(datei, _registry(tmp_path, **{"writing-hub": "django"}))
    assert r.returncode == 0, r.stdout


# ── Laut scheitern statt still gruen ──────────────────────────────────────

def test_should_leere_registry_laut_scheitern(tmp_path):
    datei = _datei(tmp_path, "## Step 1\n\nStarte writing-hub.\n")
    leer = tmp_path / "leer.yaml"
    leer.write_text("repos: {}\n", encoding="utf-8")
    r = _run(datei, leer)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "keine Repo-Namen" in r.stderr


def test_should_fehlende_datei_laut_scheitern(tmp_path):
    r = _run(tmp_path / "gibtsnicht.md")
    assert r.returncode == 2
    assert "nicht gefunden" in r.stderr
