"""Tests fuer den toleranten Secret-Leser (platform#3129, S2-Rest Stufe 1).

Anlass: eine Datei aus ``~/.secrets`` lag in ``bare``-Form vor (ganze Datei =
nackter Wert) und wurde per ``. datei`` gesourced — die Shell fuehrte den Wert
als Kommando aus und schrieb ihn in ihre eigene Fehlermeldung. Der Weg heraus
ist die ``NAME=WERT``-Form fuer alle Dateien (Stufe 3). Damit die Umstellung
keinen Leser bricht, muss VORHER jeder Leser beide Formen verstehen.

Drei Dinge werden hier geprueft:

1. ``secret_wert``/``secret_bytes`` lesen beide Formen — und zwar so, dass sich
   fuer ``bare`` **nichts** aendert (Gegenprobe gegen die alte Implementierung
   ``read_text().strip()`` in jedem bare-Test).
2. ``tools/secret_lesen.sh`` verhaelt sich genauso und haelt seine Exit-Codes.
3. Kein Leser im Repo liest eine Secret-Datei mehr selbst (Melder mit
   Positivkontrolle aus ``fixtures/secret_leser_verstoss_*.txt``).

Kein Test fasst eine echte Secret-Datei an — alles laeuft gegen ``tmp_path``
mit synthetischen Werten.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WURZEL))

from infra.lib.secrets import secret_bytes, secret_wert  # noqa: E402

LESER_SH = WURZEL / "tools" / "secret_lesen.sh"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

#: Wird in Pfaden und Mustern gebraucht, soll aber nicht als Literal durch die
#: Werkzeug-Waechter laufen.
MARKE = "." + "secrets"


def schreib(basis: Path, inhalt: str, name: str = "wert") -> Path:
    pfad = basis / name
    pfad.write_text(inhalt, encoding="utf-8")
    return pfad


def alte_implementierung(pfad: Path) -> str:
    """Genau das, was ``_read_file`` vor dem Umbau tat."""
    return pfad.read_text(encoding="utf-8").strip()


# ─── bare: Verhalten darf sich NICHT aendern ──────────────────────────────


@pytest.mark.parametrize(
    "inhalt",
    [
        "sk-test-0123456789\n",
        "  sk-test-0123456789  \n\n",
        "sk-test-0123456789",
        "K3Y0123456789==\n",  # base64-Auffuellung, kein NAME=WERT
        "AAAA=\n",
    ],
)
def test_should_read_bare_file_exactly_like_before(tmp_path: Path, inhalt: str) -> None:
    pfad = schreib(tmp_path, inhalt)
    assert secret_wert(pfad) == alte_implementierung(pfad)


def test_should_keep_bare_value_with_inner_equals(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "abc=def=ghi\n")
    # Ein nackter Wert mit Gleichheitszeichen bleibt, was er ist, solange kein
    # gueltiger Variablenname davor steht — hier ist "abc" einer, also greift
    # die KV-Lesart. Das ist der bewusst in Kauf genommene Rest-Graubereich;
    # er faellt mit Stufe 3 weg, weil dann jede Datei die KV-Form hat.
    assert secret_wert(pfad) == "def=ghi"


# ─── NAME=WERT ────────────────────────────────────────────────────────────


def test_should_read_single_kv_line(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "GROQ_API_KEY=gsk-test-42\n")
    assert secret_wert(pfad) == "gsk-test-42"


def test_should_ignore_comments_and_blank_lines(tmp_path: Path) -> None:
    pfad = schreib(
        tmp_path,
        "# angelegt 2026-09-13, Rotation halbjaehrlich\n"
        "\n"
        "  # zweiter Kommentar\n"
        "GROQ_API_KEY=gsk-test-42\n",
    )
    assert secret_wert(pfad) == "gsk-test-42"


@pytest.mark.parametrize(
    ("inhalt", "erwartet"),
    [
        ('TOK="mit leerzeichen"\n', "mit leerzeichen"),
        ("TOK='einfach'\n", "einfach"),
        ('TOK="nur links\n', '"nur links'),  # nicht beidseitig -> unveraendert
        ("TOK=  abstand  \n", "abstand"),
    ],
)
def test_should_handle_quotes_and_padding(
    tmp_path: Path, inhalt: str, erwartet: str
) -> None:
    assert secret_wert(schreib(tmp_path, inhalt)) == erwartet


def test_should_raise_on_multiple_variables_without_name(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "CF_ID=abc\nCF_SECRET=def\n")
    with pytest.raises(ValueError, match="mehrere Variablen"):
        secret_wert(pfad)


def test_should_select_variable_by_name(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "CF_ID=abc\nCF_SECRET=def\n")
    assert secret_wert(pfad, name="CF_SECRET") == "def"


def test_should_raise_when_named_variable_is_missing(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "CF_ID=abc\nCF_SECRET=def\n")
    with pytest.raises(ValueError, match="steht nicht in"):
        secret_wert(pfad, name="CF_FEHLT")


def test_should_not_leak_the_value_in_the_error_message(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "CF_ID=geheim-eins\nCF_SECRET=geheim-zwei\n")
    with pytest.raises(ValueError) as fehler:
        secret_wert(pfad)
    text = str(fehler.value)
    assert "geheim-eins" not in text and "geheim-zwei" not in text
    assert "CF_ID" in text and "CF_SECRET" in text  # Namen sind erlaubt


# ─── Bytes-Variante (Schluesselmaterial) ──────────────────────────────────


def test_should_read_bytes_bare_like_before(tmp_path: Path) -> None:
    pfad = tmp_path / "hmac"
    pfad.write_bytes(b"  K3Y0123456789==  \n")
    assert secret_bytes(pfad) == pfad.read_bytes().strip()


def test_should_read_bytes_from_kv_line(tmp_path: Path) -> None:
    pfad = tmp_path / "hmac"
    pfad.write_bytes(b"ROTATION_HMAC_KEY=ab==\n")
    assert secret_bytes(pfad) == b"ab=="


def test_should_keep_non_utf8_bytes(tmp_path: Path) -> None:
    pfad = tmp_path / "hmac"
    roh = b"\xff\xfe\x00binaer\x80"
    pfad.write_bytes(roh)
    assert secret_bytes(pfad) == roh


# ─── Shell-Leser ──────────────────────────────────────────────────────────


def lauf(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(LESER_SH), *argv],
        capture_output=True,
        text=True,
        check=False,
    )


def test_should_print_bare_value_on_stdout(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "sk-test-0123456789\n")
    ergebnis = lauf(str(pfad))
    assert ergebnis.returncode == 0
    assert ergebnis.stdout.strip() == "sk-test-0123456789"


def test_should_print_kv_value_on_stdout(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "# Kommentar\nGROQ_API_KEY=gsk-test-42\n")
    ergebnis = lauf(str(pfad))
    assert ergebnis.returncode == 0
    assert ergebnis.stdout.strip() == "gsk-test-42"


def test_should_select_variable_by_name_in_shell(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "CF_ID=abc\nCF_SECRET=def\n")
    ergebnis = lauf(str(pfad), "CF_SECRET")
    assert ergebnis.returncode == 0
    assert ergebnis.stdout.strip() == "def"


def test_should_exit_2_when_file_is_missing(tmp_path: Path) -> None:
    ergebnis = lauf(str(tmp_path / "gibtsnicht"))
    assert ergebnis.returncode == 2
    assert ergebnis.stdout == ""


def test_should_exit_3_on_multiple_variables_without_name(tmp_path: Path) -> None:
    pfad = schreib(tmp_path, "CF_ID=abc\nCF_SECRET=def\n")
    ergebnis = lauf(str(pfad))
    assert ergebnis.returncode == 3
    assert ergebnis.stdout == ""
    assert "abc" not in ergebnis.stderr and "def" not in ergebnis.stderr


def test_should_agree_with_the_python_reader(tmp_path: Path) -> None:
    """Shell und Python duerfen nie auseinanderlaufen — eine Implementierung."""
    for inhalt in ("nackt-42\n", "TOK=kv-42\n", '# k\n\nTOK="mit leerzeichen"\n'):
        pfad = schreib(tmp_path, inhalt)
        assert lauf(str(pfad)).stdout.rstrip("\n") == secret_wert(pfad)


# ─── Melder: kein Leser liest mehr selbst ─────────────────────────────────

#: Dateien, die eine Secret-Datei bewusst roh anfassen duerfen.
AUSNAHME_DATEIEN = {
    "infra/lib/secrets.py",  # der Leser selbst
    "tools/secret_lesen.sh",  # der Leser selbst (Shell-Seite)
    "tools/claude-hooks/block_env_cat.sh",  # der Leak-Waechter, zitiert Muster
}

PY_ZUWEISUNG = re.compile(
    r"^\s*(?:#:\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=\s*(.*)$"
)
PY_LESER = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.(?:read_text|read_bytes)\s*\(")
SH_ZUWEISUNG = re.compile(r"^\s*(?:local\s+|export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
SH_LESER = re.compile(
    r"(?:(?:^|[|;&(]|\$\()\s*(?:cat|head|tail|tr|source|\.)\b[^|;&\n]*|<\s*)"
)
MARKER_OK = "leser-ausnahme"


def _py_namen(text: str) -> tuple[set[str], list[tuple[int, int, str]]]:
    """Namen, die auf eine Secret-Datei zeigen — modulweit und je Funktion.

    Der zweite Teil ist noetig, weil ein Parameter mit Secret-Vorgabewert
    (``def token(pfad: Path = TOKEN_DATEI)``) nur im Rumpf SEINER Funktion
    gilt. Ohne diese Grenze faellt jedes spaetere ``pfad.read_text()`` derselben
    Datei faelschlich auf.
    """
    namen = {
        m.group(1)
        for m in (PY_ZUWEISUNG.match(z) for z in text.splitlines())
        if m and MARKE in m.group(2)
    }
    zeilen = text.splitlines()
    bereiche: list[tuple[int, int, str]] = []
    for treffer in re.finditer(
        r"^def\s+\w+\([^)]*?([A-Za-z_]\w*)\s*:[^,)=]*=\s*([A-Za-z_]\w*)",
        text,
        re.M | re.S,
    ):
        if treffer.group(2) not in namen:
            continue
        start = text[: treffer.start()].count("\n") + 1
        ende = len(zeilen)
        for nr in range(start + 1, len(zeilen) + 1):
            zeile = zeilen[nr - 1]
            if zeile and not zeile[0].isspace() and not zeile.startswith(")"):
                ende = nr - 1
                break
        bereiche.append((start, ende, treffer.group(1)))
    return namen, bereiche


def py_verstoesse(text: str) -> list[tuple[int, str]]:
    namen, bereiche = _py_namen(text)
    zeilen = text.splitlines()
    treffer = []
    for nr, zeile in enumerate(zeilen, 1):
        if zeile.lstrip().startswith("#"):
            continue
        umfeld = "\n".join(zeilen[max(0, nr - 4) : nr])
        if MARKER_OK in umfeld:
            continue
        hier = namen | {n for a, e, n in bereiche if a <= nr <= e}
        for leser in PY_LESER.finditer(zeile):
            if leser.group(1) in hier or (MARKE in zeile and ".strip()" in zeile):
                treffer.append((nr, zeile.strip()))
    return treffer


def sh_verstoesse(text: str) -> list[tuple[int, str]]:
    namen: set[str] = set()
    for _ in range(3):  # transitiv: SECRET_DIR -> ID_FILE -> …
        for zeile in text.splitlines():
            zuweisung = SH_ZUWEISUNG.match(zeile)
            if not zuweisung:
                continue
            wert = zuweisung.group(2)
            if MARKE in wert or any(
                f"${name}" in wert or f"${{{name}}}" in wert for name in namen
            ):
                namen.add(zuweisung.group(1))
    treffer = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        if zeile.lstrip().startswith("#"):
            continue
        if "secret_lesen.sh" in zeile or "LESER" in zeile or MARKER_OK in zeile:
            continue
        if not SH_LESER.search(zeile):
            continue
        if MARKE in zeile or any(
            f"${name}" in zeile or f"${{{name}}}" in zeile for name in namen
        ):
            treffer.append((nr, zeile.strip()))
    return treffer


def scanne(wurzel: Path, verzeichnisse: tuple[str, ...]) -> list[str]:
    befunde = []
    for verzeichnis in verzeichnisse:
        for datei in sorted((wurzel / verzeichnis).rglob("*")):
            if datei.suffix not in (".py", ".sh"):
                continue
            if "_ARCHIVED" in datei.parts or "fixtures" in datei.parts:
                continue
            relativ = datei.relative_to(wurzel).as_posix()
            if relativ in AUSNAHME_DATEIEN:
                continue
            text = datei.read_text(errors="replace")
            pruefer = py_verstoesse if datei.suffix == ".py" else sh_verstoesse
            befunde += [f"{relativ}:{nr}: {z}" for nr, z in pruefer(text)]
    return befunde


def test_should_find_the_planted_violation(tmp_path: Path) -> None:
    """Positivkontrolle — ohne sie waere ein leeres Ergebnis nichts wert."""
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "boese.py").write_text(
        (FIXTURES / "secret_leser_verstoss_py.txt").read_text(), encoding="utf-8"
    )
    (tmp_path / "tools" / "boese.sh").write_text(
        (FIXTURES / "secret_leser_verstoss_sh.txt").read_text(), encoding="utf-8"
    )
    befunde = scanne(tmp_path, ("tools",))
    assert any(b.startswith("tools/boese.py") for b in befunde), befunde
    assert any(b.startswith("tools/boese.sh") for b in befunde), befunde


def test_should_have_no_self_reading_secret_reader_left() -> None:
    befunde = scanne(WURZEL, ("tools", "infra", "scripts", "deployment"))
    assert not befunde, (
        "Diese Stellen lesen eine Secret-Datei selbst statt ueber "
        "infra.lib.secrets.secret_wert / tools/secret_lesen.sh:\n" + "\n".join(befunde)
    )
