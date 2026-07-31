"""Tests fuer memory_link_check — jede Fund-Klasse einmal positiv, einmal negativ.

Der Negativ-Teil ist der wichtigere: ein Pruefer, der nichts findet, belegt erst
dann Sauberkeit, wenn derselbe Pruefer nachweislich auch etwas finden kann.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from memory_link_check import main, pruefe_verzeichnis  # noqa: E402


def schreibe(mem: Path, slug: str, name: str | None = None, body: str = "") -> Path:
    kopf = "---\n"
    if name is not None:
        kopf += f"name: {name}\n"
    kopf += "metadata:\n  type: feedback\n---\n\n"
    p = mem / f"{slug}.md"
    p.write_text(kopf + body, encoding="utf-8")
    return p


@pytest.fixture()
def mem(tmp_path: Path) -> Path:
    d = tmp_path / "memory"
    d.mkdir()
    return d


def test_should_report_nothing_for_a_consistent_directory(mem: Path):
    schreibe(mem, "feedback_alpha", "feedback_alpha", "Siehe [[feedback_beta]].")
    schreibe(mem, "feedback_beta", "feedback_beta")
    (mem / "MEMORY.md").write_text("- [Alpha](feedback_alpha.md)\n", encoding="utf-8")

    assert pruefe_verzeichnis(mem) == []


def test_should_detect_slug_mismatch_between_frontmatter_and_filename(mem: Path):
    # der reale Hauptfall: name: mit Bindestrichen, Datei mit Unterstrichen
    schreibe(mem, "feedback_alpha", "feedback-alpha")

    funde = pruefe_verzeichnis(mem)

    assert [f.art for f in funde] == ["slug-mismatch"]
    assert "feedback-alpha" in funde[0].detail


def test_should_detect_dead_wikilink(mem: Path):
    schreibe(mem, "feedback_alpha", "feedback_alpha", "Verwandt: [[feedback_gibtsnicht]].")

    funde = pruefe_verzeichnis(mem)

    assert [f.art for f in funde] == ["dead-wikilink"]
    assert funde[0].detail == "[[feedback_gibtsnicht]]"


def test_should_detect_dead_index_link_in_memory_md(mem: Path):
    schreibe(mem, "feedback_alpha", "feedback_alpha")
    (mem / "MEMORY.md").write_text("- [Weg](feedback_geloescht.md)\n", encoding="utf-8")

    funde = pruefe_verzeichnis(mem)

    assert [f.art for f in funde] == ["dead-indexlink"]
    assert funde[0].detail == "feedback_geloescht.md"


def test_should_detect_missing_name_field(mem: Path):
    schreibe(mem, "feedback_alpha", None)

    assert [f.art for f in pruefe_verzeichnis(mem)] == ["missing-name"]


def test_should_not_flag_known_policy_references_as_dead(mem: Path):
    # Policies sind keine Memories, duerfen aber referenziert werden
    schreibe(mem, "feedback_alpha", "feedback_alpha", "s. [[evidence-discipline]]")

    assert pruefe_verzeichnis(mem) == []


def test_should_not_flag_http_links_in_index(mem: Path):
    schreibe(mem, "feedback_alpha", "feedback_alpha")
    (mem / "MEMORY.md").write_text(
        "- [Issue](https://github.com/achimdehnert/platform/issues/1.md)\n", encoding="utf-8"
    )

    assert pruefe_verzeichnis(mem) == []


def test_should_exit_1_on_findings_and_0_when_clean(mem: Path, capsys):
    schreibe(mem, "feedback_alpha", "feedback_alpha", "[[feedback_weg]]")
    assert main(["--root", str(mem)]) == 1

    (mem / "feedback_alpha.md").write_text(
        "---\nname: feedback_alpha\n---\n\nkein Verweis\n", encoding="utf-8"
    )
    assert main(["--root", str(mem)]) == 0
    assert "sauber" in capsys.readouterr().out


def test_should_exit_2_on_unusable_root(tmp_path: Path):
    assert main(["--root", str(tmp_path / "gibtsnicht")]) == 2


def test_should_scan_all_memory_dirs_under_a_projects_root(tmp_path: Path):
    for projekt in ("projekt-a", "projekt-b"):
        d = tmp_path / projekt / "memory"
        d.mkdir(parents=True)
        schreibe(d, "feedback_alpha", "feedback-alpha")  # je 1 Fund

    funde = [f for d in (tmp_path / "projekt-a" / "memory",) for f in pruefe_verzeichnis(d)]
    assert len(funde) == 1
    assert main(["--root", str(tmp_path)]) == 1


# --- Code ist kein Verweis ---------------------------------------------------


def test_should_not_flag_a_wikilink_inside_inline_code(mem: Path):
    # Realfall: design-hub-Memory dokumentiert Makro-Syntax, die nie ein Link war
    schreibe(mem, "feedback_alpha", "feedback_alpha", "Keine `[[clause:…]]`-Makros mehr.")

    assert pruefe_verzeichnis(mem) == []


def test_should_not_flag_a_wikilink_inside_a_fenced_block(mem: Path):
    body = "Beispiel:\n\n```\n[[angebot-cover]]\n[[reisekosten:...]]\n```\n"
    schreibe(mem, "feedback_alpha", "feedback_alpha", body)

    assert pruefe_verzeichnis(mem) == []


def test_should_still_flag_a_dead_link_outside_the_code_block(mem: Path):
    # die Ausnahme darf nicht den ganzen Rest der Datei stumm schalten
    body = "```\n[[in-code]]\n```\n\nVerwandt: [[feedback_weg]].\n"
    schreibe(mem, "feedback_alpha", "feedback_alpha", body)

    funde = pruefe_verzeichnis(mem)

    assert [f.detail for f in funde] == ["[[feedback_weg]]"]


def test_should_keep_line_structure_when_blanking_code(mem: Path):
    from memory_link_check import _ohne_code

    text = "a\n```\n[[x]]\n```\nb `[[y]]` c\n"
    prosa = _ohne_code(text)

    assert prosa.count("\n") == text.count("\n")
    assert len(prosa) == len(text)
    assert "[[x]]" not in prosa and "[[y]]" not in prosa
    assert prosa.startswith("a\n") and prosa.rstrip().endswith("c")
