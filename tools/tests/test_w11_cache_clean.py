"""Drill fuer tools/w11_cache_clean.py — die Gate-1-Allowlist W11 (platform#2745).

Das Werkzeug existiert, weil die sechs Bedingungen der Klasse nicht der Disziplin
des Agenten ueberlassen werden sollen. Der Drill prueft deshalb beide Richtungen:
jede Bedingung muss den Fall FANGEN, gegen den sie geschrieben ist, und den
harmlosen Nachbarfall durchlassen. Ohne die Gegenrichtung waere ein Werkzeug, das
alles ablehnt, „gruen".
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "w11_cache_clean.py"
_spec = importlib.util.spec_from_file_location("w11_cache_clean", _SCRIPT)
w = importlib.util.module_from_spec(_spec)
sys.modules["w11_cache_clean"] = w
_spec.loader.exec_module(w)

MODELLE = ["DIR  hub", "DIR  transformers", "DIR  xet"]


# --- (b) Zugangsdaten -------------------------------------------------------


@pytest.mark.f1
def test_should_refuse_a_folder_that_holds_an_access_file():
    """Der Realfall: der Cache-Ordner traegt neben Modellen eine Zugangsdatei."""
    inhalt = MODELLE + ["FILE token"]
    befunde = w.pruefe_pfad(r"C:\Users\a\.cache\huggingface", inhalt)
    assert any("(b)" in b for b in befunde), befunde


@pytest.mark.f1
def test_should_allow_the_model_subfolder_below_it():
    """Gegenrichtung: eine Ebene tiefer liegt keine Zugangsdatei — erlaubt."""
    inhalt = ["DIR  models--BAAI--bge-small-en", "DIR  .locks"]
    assert w.pruefe_pfad(r"C:\Users\a\.cache\huggingface\hub", inhalt) == []


@pytest.mark.f2
@pytest.mark.parametrize(
    "datei",
    ["token", "id_ed25519", "id_ed25519.pub", "server.key", "credentials.json", ".env"],
)
def test_should_catch_every_declared_secret_shape(datei):
    befunde = w.pruefe_pfad(r"C:\Users\a\.cache\etwas", MODELLE + [f"FILE {datei}"])
    assert any("(b)" in b for b in befunde), (datei, befunde)


@pytest.mark.f2
@pytest.mark.parametrize(
    "datei", ["readme.md", "config.json", "tokenizer.json", "keyboard.txt"]
)
def test_should_not_mistake_harmless_files_for_secrets(datei):
    """`tokenizer.json` faengt mit `token` an und ist keins — das Muster ist verankert."""
    assert w.pruefe_pfad(r"C:\Users\a\.cache\etwas", MODELLE + [f"FILE {datei}"]) == []


# --- (c) verbotene Pfade ----------------------------------------------------


@pytest.mark.f2
@pytest.mark.parametrize(
    "pfad",
    [
        r"C:\Users\a\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu_79rhkp1fndgsc",
        r"C:\Users\a\AppData\Local\Docker",
        r"C:\Users\a\Documents",
        r"C:\Users\a\OneDrive",
        r"C:\Users\a\github",
    ],
)
def test_should_refuse_forbidden_paths_even_with_clean_content(pfad):
    """Diese fuenf bleiben tabu, auch wenn der Inhalt harmlos aussieht."""
    befunde = w.pruefe_pfad(pfad, MODELLE)
    assert any("(c)" in b or "(d)" in b for b in befunde), (pfad, befunde)


@pytest.mark.f1
def test_should_allow_a_normal_cache_path():
    """Positivkontrolle: ohne sie wuerde ein Werkzeug, das ALLES ablehnt, bestehen."""
    assert w.pruefe_pfad(r"C:\Users\a\.cache\lm-studio", MODELLE) == []


# --- (d) eigener Aufraeumbefehl ---------------------------------------------


@pytest.mark.f1
def test_should_name_the_tools_own_command_instead_of_deleting():
    befunde = w.pruefe_pfad(r"C:\Users\a\AppData\Local\uv", MODELLE)
    assert any("uv cache clean" in b for b in befunde), befunde


# --- (f) Freigabe gilt der Liste --------------------------------------------


@pytest.mark.f3
def test_should_refuse_deletion_without_the_owner_wording(capsys):
    rc = w.main(["--pfad", r"C:\x", "--loeschen", "--endgueltig"])
    assert rc == 1 and "(f)" in capsys.readouterr().err


@pytest.mark.f3
def test_should_refuse_permanent_deletion_without_its_own_word(capsys):
    rc = w.main(["--pfad", r"C:\x", "--loeschen", "--freigabe", "6 go"])
    assert rc == 1 and "(e)" in capsys.readouterr().err


# --- blind ist nicht gruen ---------------------------------------------------


@pytest.mark.f3
def test_should_exit_2_when_the_box_cannot_be_reached(monkeypatch, capsys):
    """Eine unerreichbare Box darf nicht als „nichts zu tun" durchgehen."""
    monkeypatch.setattr(w, "_lauf", lambda cmd, timeout=0: (255, ""))
    rc = w.main(["--pfad", r"C:\Users\a\.cache\hub"])
    assert rc == 2
    assert "blind" in capsys.readouterr().err


@pytest.mark.f1
def test_should_report_a_missing_path_instead_of_deleting_it(monkeypatch):
    monkeypatch.setattr(w, "_lauf", lambda cmd, timeout=0: (0, "__FEHLT__\n"))
    inhalt = w.liste_inhalt(r"C:\gibtsnicht")
    assert w.pruefe_pfad(r"C:\gibtsnicht", inhalt) == ["Pfad existiert nicht"]
