"""Drill fuer tools/ci_deckung.py — laeuft eine lokale Pruefung auch im CI?

Die drei Tests `test_should_catch_realfall_*` bilden die Positivkontrolle: je
ein ECHTER Fall aus den Retros, gegen eine Fixture nachgebaut, die die Form des
Falls traegt (nicht nur eine Abstraktion). Jeder dieser Tests ist zweigeteilt —
"rot ohne Fix" (die Luecke wird als Befund gemeldet) und "gruen mit Fix" (nach
Nachtrag des fehlenden CI-Schritts verschwindet der Befund) — damit ein Leser
sieht, dass das Werkzeug wirklich DECKUNG misst und nicht nur "irgendwas".

**Realfall 3 (chat-hub#79) braucht eine Einschraenkung, die ehrlich hierher
gehoert:** `ruff format --check` war zum Zeitpunkt des Issues NIE ein
Makefile-Ziel in chat-hub — nachgemessen per `git show cf98084^:Makefile` (dem
Stand unmittelbar vor PR iilgmbh/chat-hub#81) war `lint` durchgehend nur
`shellcheck deploy/*.sh` + `ruff check deploy/ tests/`, seit der Einfuehrung des
Ziels am 2026-08-16 (`a7c9f0f`) unveraendert. Der reale Format-Drift lebte
ausschliesslich in einer manuellen Vorab-Push-Pruefung (platform#2860), nicht im
Makefile — dieses Werkzeug vergleicht Makefile↔CI, nicht Doku↔CI, und haette den
Fall darum nie in seinem Scope gefunden. `test_should_catch_realfall_3_..._shape`
baut darum eine REPRAESENTATIVE Fixture (ein Makefile-Ziel, das `ruff format
--check` lokal ausfuehrt, waehrend CI nur `ruff check` faehrt) — sie zeigt den
Mechanismus, der den Fall gefangen HAETTE, waere er ueber das Makefile gelaufen,
beweist aber nicht, dass er es war. Die Nachmessung gegen den echten,
AKTUELLEN chat-hub-Stand steht separat in `test_should_find_nothing_on_real_current_chat_hub`
— dort sind `lint` und `test` seit jeher/seit #81 vollstaendig gedeckt, bis auf
zwei per Verzicht ausgenommene `chat-verify*`-Ziele (Prod-Zugriff).

Run: `python3 -m pytest tools/tests/test_ci_deckung.py -q`
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_QUELLE = Path(__file__).resolve().parents[1] / "ci_deckung.py"
_spec = importlib.util.spec_from_file_location("ci_deckung", _QUELLE)
cd = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["ci_deckung"] = cd  # dataclass-Introspektion braucht den Registry-Eintrag
_spec.loader.exec_module(cd)


def _repo(tmp_path: Path, makefile: str, workflow: str | None = None, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir(exist_ok=True)
    (repo / "Makefile").write_text(makefile, encoding="utf-8")
    if workflow is not None:
        wf_dir = repo / ".github" / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        (wf_dir / "ci.yml").write_text(workflow, encoding="utf-8")
    return repo


def _befund_ziele(ergebnis: dict) -> set[str]:
    return {b["ziel"] for b in ergebnis["befunde"]}


def _gedeckt_ziele(ergebnis: dict) -> set[str]:
    return {g["ziel"] for g in ergebnis["gedeckt"]}


# ─────────────────────────── Realfall 1: robo-lab stream-gate ──────────────

def test_should_catch_realfall_1_robo_lab_stream_gate(tmp_path):
    """robo-lab 2026-08-28: `sim/test_stream_gate.py` steht im Makefile, CI installiert
    nur `mujoco numpy` und ruft es nie auf (Retro Zeile 40). Entscheidet ueber die
    Pfad-Granularitaet: CI faehrt an anderer Stelle durchaus pytest-artige Skripte,
    aber nicht DIESES."""
    makefile = (
        "stream-gate: venv\n"
        "\t$(PYTHON) sim/test_stream_gate.py\n"
    )
    ci_ohne_fix = (
        "on: [push]\n"
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        "      - run: pip install --quiet mujoco numpy\n"
        "      - run: python -m compileall -q sim\n"
    )
    repo = _repo(tmp_path, makefile, ci_ohne_fix, name="robo-lab")
    ergebnis = cd.scan_repo(str(repo))
    assert "stream-gate" in _befund_ziele(ergebnis)  # rot ohne Fix

    # gruen mit Fix: CI ruft das Skript jetzt auf
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        ci_ohne_fix + "      - run: python sim/test_stream_gate.py\n", encoding="utf-8"
    )
    ergebnis2 = cd.scan_repo(str(repo))
    assert "stream-gate" not in _befund_ziele(ergebnis2)
    assert "stream-gate" in _gedeckt_ziele(ergebnis2)


# ───────────────── Realfall 2: robo-lab exo-konformitaet-myoassist ─────────

def test_should_catch_realfall_2_robo_lab_exo_konformitaet_myoassist(tmp_path):
    """robo-lab 2026-09-07: der vendor-abhaengige Exo-Pfad laeuft nie in CI — nur
    Twin-Stub und Selbsttest sind gedeckt, die myoassist-Variante nicht (Retro
    Zeile 47, zweites Vorkommen desselben Slugs ⇒ GATE-PFLICHT). Das Rezept ruft
    weder pytest noch ein `test_*.py`-Skript — nur der Zielname traegt das
    Schluesselwort `konformitaet`, deshalb ist dieser Fall der Beleg fuer die
    Zielname-Erweiterung in ci_deckung.py."""
    makefile = (
        "exo-konformitaet: venv\n"
        "\t$(PYTHON) exo/konformitaet.py --adapter twin-stub --seed $(SEED)\n"
        "\n"
        "exo-konformitaet-myoassist: vendor venv\n"
        "\tMYOASSIST_CACHE_DIR=$${MYOASSIST_CACHE_DIR:-$$HOME/.cache/myoassist} \\\n"
        "\t$(EXO_PYTHON) exo/konformitaet.py --adapter myoassist --sim-time $(SIM_TIME) \\\n"
        "\t\t--seed $(SEED) --journal --maschine $(MASCHINE)\n"
    )
    ci_ohne_fix = (
        "on: [push]\n"
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        "      - run: python exo/konformitaet.py --adapter twin-stub\n"
    )
    repo = _repo(tmp_path, makefile, ci_ohne_fix, name="robo-lab")
    ergebnis = cd.scan_repo(str(repo))
    befunde = _befund_ziele(ergebnis)
    assert "exo-konformitaet-myoassist" in befunde  # rot ohne Fix
    assert "exo-konformitaet" not in befunde  # die Zwillings-Variante IST gedeckt
    assert "exo-konformitaet" in _gedeckt_ziele(ergebnis)

    # gruen mit Fix
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        ci_ohne_fix + "      - run: python exo/konformitaet.py --adapter myoassist --journal\n",
        encoding="utf-8",
    )
    ergebnis2 = cd.scan_repo(str(repo))
    assert "exo-konformitaet-myoassist" not in _befund_ziele(ergebnis2)
    assert "exo-konformitaet-myoassist" in _gedeckt_ziele(ergebnis2)


# ─────────────── Realfall 3: chat-hub #79, Form nachgebaut (siehe Docstring) ─

def test_should_catch_realfall_3_chat_hub_ruff_format_shape(tmp_path):
    """Repraesentative Fixture fuer die FORM von chat-hub#79 — siehe Modul-Docstring
    fuer die Einschraenkung: `ruff format --check` war real nie ein Makefile-Ziel,
    diese Fixture zeigt den Mechanismus, der es gefangen haette."""
    makefile = (
        "lint:\n"
        "\tshellcheck deploy/*.sh\n"
        "\t$(TEST_PY) -m ruff check deploy/ tests/\n"
        "\t$(TEST_PY) -m ruff format --check deploy/ tests/\n"
    )
    ci_ohne_fix = (
        "on: [push]\n"
        "jobs:\n"
        "  lint:\n"
        "    steps:\n"
        "      - run: shellcheck deploy/*.sh\n"
        "      - run: ruff check deploy/ tests/\n"
    )
    repo = _repo(tmp_path, makefile, ci_ohne_fix, name="chat-hub")
    ergebnis = cd.scan_repo(str(repo))
    befunde = _befund_ziele(ergebnis)
    assert "lint" in befunde
    assert any(b["kommando"] == "ruff format --check deploy/ tests/" for b in ergebnis["befunde"])
    # shellcheck + ruff check sind gedeckt, nur ruff format fehlt
    gedeckte_kommandos = {g["kommando"] for g in ergebnis["gedeckt"]}
    assert "shellcheck deploy/*.sh" in gedeckte_kommandos
    assert "ruff check deploy/ tests/" in gedeckte_kommandos

    # gruen mit Fix (das echte #81 hat genau das getan: Schritt ergaenzt)
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        ci_ohne_fix + "      - run: ruff format --check deploy/ tests/\n", encoding="utf-8"
    )
    ergebnis2 = cd.scan_repo(str(repo))
    assert not ergebnis2["befunde"]


def test_should_find_nothing_on_real_current_chat_hub():
    """Nachmessung gegen den ECHTEN, aktuellen chat-hub-Checkout (main, nach #81):
    `lint` und `test` sind vollstaendig gedeckt; die einzigen Ziele mit
    Pruef-Schluesselwort im Namen, die nicht laufen, sind `chat-verify` und
    `chat-verify-init` — beide per governance/ci-deckung-verzicht.yaml verzichtet
    (Prod-Zugriff, echter Homeserver noetig). Skip, wenn der Checkout fehlt (CI-
    Runner hat ~/github nicht)."""
    pfad = Path("/home/devuser/github/chat-hub")
    if not pfad.is_dir():
        import pytest

        pytest.skip("~/github/chat-hub nicht vorhanden auf diesem Runner")
    verzicht, fehler = cd.lade_verzicht(cd.DEFAULT_VERZICHT)
    ergebnis = cd.scan_repo(str(pfad), verzicht)
    assert ergebnis["befunde"] == []
    assert {v["ziel"] for v in ergebnis["verzicht"]} == {"chat-verify", "chat-verify-init"}


# ───────────────────────────── Gegenproben (duerfen NICHT anschlagen) ──────

def test_should_not_flag_a_target_covered_via_make_invocation(tmp_path):
    """Gegenprobe: `make lint` im CI deckt das Ziel, ohne dass das Kommando
    literal im Workflow steht."""
    makefile = "lint:\n\truff check src/\n"
    workflow = (
        "on: [push]\njobs:\n  ci:\n    steps:\n      - run: make lint\n"
    )
    repo = _repo(tmp_path, makefile, workflow)
    ergebnis = cd.scan_repo(str(repo))
    assert ergebnis["befunde"] == []
    assert "lint" in _gedeckt_ziele(ergebnis)


def test_should_not_flag_a_non_check_target(tmp_path):
    """Gegenprobe: ein operatives Ziel (`deploy`) ist kein Pruef-Kommando — weder
    Werkzeugname noch Schluesselwort im Zielnamen — und taucht ueberhaupt nicht
    als gemessenes Kommando auf, auch wenn kein Workflow es aufruft."""
    makefile = "deploy:\n\tssh prod 'systemctl restart app'\n"
    repo = _repo(tmp_path, makefile, "on: [push]\njobs:\n  ci:\n    steps: []\n")
    ergebnis = cd.scan_repo(str(repo))
    assert ergebnis["geprueft"] == 0
    assert ergebnis["befunde"] == []


# ───────────────────────── Normalisierung (Kernregeln aus dem Docstring) ───

def test_should_normalize_make_variable_and_output_flag_away():
    assert cd.normalize_command("$(TEST_PY) -m pytest tests/ -q") == ["pytest tests/"]


def test_should_keep_paths_as_meaningful():
    assert cd.normalize_command("pytest tests/unit -q") == ["pytest tests/unit"]


def test_should_drop_flag_when_its_value_is_a_make_variable():
    assert cd.normalize_command("$(PYTHON) x.py --seed $(SEED)") == ["x.py"]


def test_should_treat_manage_py_test_as_a_check_command():
    norm = cd.normalize_command("python manage.py test")[0]
    assert cd.is_pruef_kommando(norm)


def test_should_not_treat_latest_as_a_test_keyword():
    """Wortgrenze bei den Zielname-Schluesselwoertern: `latest` matcht NICHT auf
    `test`, `attestation` NICHT auf `test`."""
    assert not cd._ziel_ist_pruef_kandidat("build-latest")
    assert not cd._ziel_ist_pruef_kandidat("attestation-upload")
    assert cd._ziel_ist_pruef_kandidat("exo-konformitaet-myoassist")


# ───────────────────────────── Falsifikation ────────────────────────────────

def test_should_mark_repo_not_pruefbar_when_makefile_has_no_tab_recipes(tmp_path):
    repo = tmp_path / "seltsam"
    repo.mkdir()
    (repo / "Makefile").write_text("lint:\n    ruff check src/\n", encoding="utf-8")  # Leerzeichen statt TAB
    ergebnis = cd.scan_repo(str(repo))
    assert ergebnis["befunde"] == []
    assert any("Tab-Rezeptzeile" in n["grund"] for n in ergebnis["nicht_pruefbar"])


def test_should_mark_finding_not_pruefbar_when_a_reusable_workflow_is_referenced(tmp_path):
    makefile = "test:\n\tpytest tests/\n"
    workflow = (
        "on: [push]\n"
        "jobs:\n"
        "  ci:\n"
        "    uses: iilgmbh/shared-ci/.github/workflows/_ci-python.yml@v3\n"
    )
    repo = _repo(tmp_path, makefile, workflow)
    ergebnis = cd.scan_repo(str(repo))
    assert ergebnis["befunde"] == []
    assert any(n["ziel"] == "test" for n in ergebnis["nicht_pruefbar"])


def test_should_mark_finding_not_pruefbar_when_command_uses_a_matrix_expression(tmp_path):
    makefile = "test:\n\tpytest tests/\n"
    workflow = (
        "on: [push]\n"
        "jobs:\n"
        "  ci:\n"
        "    strategy:\n"
        "      matrix:\n"
        "        target: [a, b]\n"
        "    steps:\n"
        "      - run: pytest ${{ matrix.target }}\n"
    )
    repo = _repo(tmp_path, makefile, workflow)
    ergebnis = cd.scan_repo(str(repo))
    assert ergebnis["befunde"] == []
    assert any(n["ziel"] == "test" for n in ergebnis["nicht_pruefbar"])


# ───────────────────────────── Verzicht ─────────────────────────────────────

def test_should_apply_a_valid_verzicht_entry(tmp_path):
    makefile = "chat-verify:\n\tpython3 deploy/chat_verify.py\n"
    repo = _repo(tmp_path, makefile, "on: [push]\njobs:\n  ci:\n    steps: []\n", name="chat-hub")
    verzicht = {("chat-hub", "chat-verify"): "Prod-Zugriff"}
    ergebnis = cd.scan_repo(str(repo), verzicht)
    assert ergebnis["befunde"] == []
    assert ergebnis["verzicht"][0]["grund"] == "Prod-Zugriff"


def test_should_reject_a_verzicht_entry_without_grund(tmp_path):
    pfad = tmp_path / "verzicht.yaml"
    pfad.write_text(
        "- repo: chat-hub\n  ziel: chat-verify\n",  # kein grund
        encoding="utf-8",
    )
    eintraege, fehler = cd.lade_verzicht(str(pfad))
    assert eintraege == {}
    assert fehler and "OHNE Grund" in fehler[0]
