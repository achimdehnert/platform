"""windsurf-subset: Auswahl, Staging-Swap und die beiden rmtree-Pfade.

Das Werkzeug ersetzt ein ganzes Zielverzeichnis per ``os.replace`` und raeumt
davor zwei Verzeichnisse mit ``shutil.rmtree`` ab: das Staging und das alte
Backup. Beides ist rekursiv — genau die Operation, die im selben Verzeichnis
schon einmal zu weit gegriffen hat (``generate.py --target`` tauschte ~/.claude
komplett aus). Ungetestet war bisher beides.

``git()`` wird ersetzt, statt ein Repo aufzusetzen: der Testgegenstand ist die
Auswahl- und Swap-Logik, nicht git. Das haelt die Faelle offline lauffaehig — die
echte Funktion ruft ``git fetch origin`` und braeuchte ein Remote.
"""

import importlib.util
import json
import pathlib

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[1] / "cc-skill-dist" / "windsurf-subset.py"
_spec = importlib.util.spec_from_file_location("windsurf_subset", _SRC)
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)

COMMIT = "a" * 40


def fake_git(dateien: dict[str, str]):
    """Ersetzt ws.git; liefert ls-tree/cat-file aus einem Namen->Inhalt-Mapping."""
    shas = {name: f"{i:040d}" for i, name in enumerate(sorted(dateien), start=1)}

    def _git(args, cwd):
        if args[0] == "fetch":
            return ""
        if args[0] == "rev-parse":
            return COMMIT + "\n"
        if args[0] == "ls-tree":
            return "".join(
                f"100644 blob {shas[n]}\t.windsurf/workflows/{n}\n" for n in sorted(dateien)
            )
        if args[0] == "cat-file":
            name = next(n for n, s in shas.items() if s == args[2])
            return dateien[name]
        raise AssertionError(f"unerwarteter git-Aufruf: {args}")

    return _git


def lauf(monkeypatch, dateien, ziel, *extra):
    monkeypatch.setattr(ws, "git", fake_git(dateien))
    monkeypatch.setattr(ws.sys, "argv", ["windsurf-subset.py", "--target", str(ziel), *extra])
    ws.main()


# --- reine Funktionen --------------------------------------------------------


def test_should_read_the_frontmatter_block(_=None):
    assert ws.frontmatter("---\na: 1\n---\nRumpf\n") == "a: 1"


def test_should_return_empty_frontmatter_when_absent():
    assert ws.frontmatter("kein frontmatter\n") == ""


def test_should_detect_the_windsurf_tag():
    assert ws.has_windsurf_tag("---\ntool_targets: [windsurf-review]\n---\n")


def test_should_not_detect_the_tag_for_another_target():
    assert not ws.has_windsurf_tag("---\ntool_targets: [cascade]\n---\n")


def test_should_not_detect_the_tag_outside_the_frontmatter():
    # eine Erwaehnung im Rumpf darf keine Datei ins Subset ziehen
    assert not ws.has_windsurf_tag("---\na: 1\n---\ntool_targets: [windsurf-review]\n")


# --- Sicherheitsgate ---------------------------------------------------------


def test_should_refuse_to_write_to_the_live_location_without_allow_live(monkeypatch, tmp_path):
    monkeypatch.setattr(ws, "WINDSURF_LIVE", str(tmp_path / "live"))
    monkeypatch.setattr(ws, "git", fake_git({"adr.md": "x"}))
    monkeypatch.setattr(ws.sys, "argv", ["windsurf-subset.py", "--target", str(tmp_path / "live")])

    with pytest.raises(SystemExit) as exc:
        ws.main()

    assert "ABBRUCH" in str(exc.value)
    assert not (tmp_path / "live").exists()


# --- Auswahl -----------------------------------------------------------------


def test_should_prefer_tagged_files_over_the_fallback_list(monkeypatch, tmp_path):
    ziel = tmp_path / "subset"
    lauf(monkeypatch, {
        "adr.md": "---\na: 1\n---\nohne Tag\n",
        "sonstwas.md": "---\ntool_targets: [windsurf-review]\n---\nmit Tag\n",
    }, ziel)

    manifest = json.loads((ziel / "manifest.json").read_text(encoding="utf-8"))

    assert [f["name"] for f in manifest["files"]] == ["sonstwas.md"]
    assert "Frontmatter-Tag" in manifest["selection_mode"]


def test_should_fall_back_to_the_curated_list_when_nothing_is_tagged(monkeypatch, tmp_path):
    ziel = tmp_path / "subset"
    lauf(monkeypatch, {
        "adr.md": "kein frontmatter\n",
        "unbeteiligt.md": "kein frontmatter\n",
    }, ziel)

    manifest = json.loads((ziel / "manifest.json").read_text(encoding="utf-8"))

    assert [f["name"] for f in manifest["files"]] == ["adr.md"]
    assert "FALLBACK" in manifest["selection_mode"]


def test_should_append_the_managed_footer_with_commit_and_hash(monkeypatch, tmp_path):
    ziel = tmp_path / "subset"
    lauf(monkeypatch, {"adr.md": "Inhalt\n"}, ziel)

    text = (ziel / "adr.md").read_text(encoding="utf-8")

    assert text.startswith("Inhalt")
    assert ws.MARK in text
    assert COMMIT[:12] in text
    assert "do_not_edit" in text


# --- Loeschpfade -------------------------------------------------------------


def test_should_clear_a_leftover_staging_directory(monkeypatch, tmp_path):
    ziel = tmp_path / "subset"
    staging = tmp_path / "subset.tmp"
    staging.mkdir()
    (staging / "muell.md").write_text("Rest eines Abbruchs\n", encoding="utf-8")

    lauf(monkeypatch, {"adr.md": "Inhalt\n"}, ziel)

    assert not (ziel / "muell.md").exists()
    assert not staging.exists()  # in das Ziel umbenannt


def test_should_move_an_existing_target_aside_into_bak(monkeypatch, tmp_path):
    ziel = tmp_path / "subset"
    ziel.mkdir()
    (ziel / "alt.md").write_text("Vorgaenger\n", encoding="utf-8")

    lauf(monkeypatch, {"adr.md": "Inhalt\n"}, ziel)

    assert (tmp_path / "subset.bak" / "alt.md").read_text(encoding="utf-8") == "Vorgaenger\n"
    assert (ziel / "adr.md").exists()
    assert not (ziel / "alt.md").exists()


def test_should_replace_an_older_backup_rather_than_stacking_them(monkeypatch, tmp_path):
    ziel = tmp_path / "subset"
    ziel.mkdir()
    (ziel / "runde2.md").write_text("zweiter Lauf\n", encoding="utf-8")
    backup = tmp_path / "subset.bak"
    backup.mkdir()
    (backup / "runde1.md").write_text("erster Lauf\n", encoding="utf-8")

    lauf(monkeypatch, {"adr.md": "Inhalt\n"}, ziel)

    assert (backup / "runde2.md").exists()
    assert not (backup / "runde1.md").exists()  # rmtree-Pfad


def test_should_not_touch_siblings_of_the_target_directory(monkeypatch, tmp_path):
    # Belegt, dass der Swap auf das Ziel begrenzt bleibt und nicht den Elternbaum trifft
    nachbar = tmp_path / "nicht-anfassen"
    nachbar.mkdir()
    (nachbar / "wichtig.md").write_text("bleibt\n", encoding="utf-8")

    lauf(monkeypatch, {"adr.md": "Inhalt\n"}, tmp_path / "subset")

    assert (nachbar / "wichtig.md").read_text(encoding="utf-8") == "bleibt\n"
