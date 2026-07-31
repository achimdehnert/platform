"""hardcode_scanner: Ausnahmen, Enum-Kontext und der Scan einer Datei.

Derselbe Gedanke wie beim URL-Scanner: die Regex ist der einfache Teil, die
Ausnahmen sind es nicht. Ein Scanner, der ADR-Dokumente als Fund meldet, weil dort
die Prod-IP als Beispiel steht, wird nach zwei Laeufen ignoriert — und dann nuetzt
auch der echte Treffer nichts mehr.

Der Enum-Kontext ist die kniffligste Heuristik: sie sucht rueckwaerts nach der
naechsten class-Zeile und entscheidet daran. Ihre Grenzen sind unten explizit
festgehalten, damit ein spaeterer Umbau sie nicht unbemerkt verschiebt.
"""

import importlib.util
import pathlib
import sys

import pytest

_SRC = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "hardcode_scanner.py"
_spec = importlib.util.spec_from_file_location("hardcode_scanner", _SRC)
hs = importlib.util.module_from_spec(_spec)
# VOR exec_module registrieren: @dataclass schlaegt waehrend der Klassendefinition
# sys.modules[cls.__module__] nach. Fehlt der Eintrag, bricht der Import mit
# "'NoneType' object has no attribute '__dict__'" ab — nicht offensichtlich, wenn
# man den Vorspann von einem Modul ohne Dataclass uebernimmt.
sys.modules[_spec.name] = hs
_spec.loader.exec_module(hs)

PROD_IP = "88.198.191.108"  # steht so in PATTERNS — kein neuer Wert


# --- should_skip_file --------------------------------------------------------


def test_should_skip_a_file_inside_an_excluded_directory():
    cfg = {"exclude_dirs": {"docs/adr"}}

    assert hs.should_skip_file(pathlib.Path("repo/docs/adr/ADR-021.md"), cfg)
    assert not hs.should_skip_file(pathlib.Path("repo/apps/views.py"), cfg)


def test_should_skip_a_file_by_name_fragment():
    cfg = {"exclude_files": {"checklist"}}

    assert hs.should_skip_file(pathlib.Path("a/adr-review-checklist.md"), cfg)
    assert not hs.should_skip_file(pathlib.Path("a/review.md"), cfg)


def test_should_not_skip_when_the_pattern_has_no_exclusions():
    assert not hs.should_skip_file(pathlib.Path("a/b.py"), {})


# --- _is_inside_enum ---------------------------------------------------------


def test_should_detect_a_line_inside_an_enum_class():
    zeilen = ["class Status(Enum):", "    OFFEN = 'offen'"]

    assert hs._is_inside_enum(zeilen, 1)


@pytest.mark.parametrize("basis", ["IntEnum", "StrEnum", "TextChoices", "IntegerChoices"])
def test_should_detect_every_supported_enum_base(basis):
    zeilen = [f"class Status(models.{basis}):", "    OFFEN = 'offen'"]

    assert hs._is_inside_enum(zeilen, 1)


def test_should_not_treat_an_ordinary_class_as_enum():
    zeilen = ["class Kunde(models.Model):", "    name = 'x'"]

    assert not hs._is_inside_enum(zeilen, 1)


def test_should_stop_at_the_nearest_class_not_an_earlier_enum():
    # die naechstliegende class-Zeile entscheidet, nicht irgendeine weiter oben
    zeilen = [
        "class Status(Enum):",
        "    OFFEN = 'offen'",
        "",
        "class Kunde(models.Model):",
        "    name = 'x'",
    ]

    assert hs._is_inside_enum(zeilen, 1)
    assert not hs._is_inside_enum(zeilen, 4)


def test_should_report_no_enum_context_at_module_level():
    assert not hs._is_inside_enum(["WERT = 'x'"], 0)


def test_should_not_look_back_further_than_sixty_lines():
    """Bewusste Grenze der Heuristik — hier festgehalten, nicht als Fehler gewertet."""
    zeilen = ["class Status(Enum):"] + ["    # fueller"] * 70 + ["    OFFEN = 'offen'"]

    assert not hs._is_inside_enum(zeilen, len(zeilen) - 1)


# --- scan_file ---------------------------------------------------------------


@pytest.fixture()
def repo(tmp_path):
    def _schreib(rel: str, inhalt: str) -> pathlib.Path:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt, encoding="utf-8")
        return p

    return tmp_path, _schreib


def test_should_find_the_hardcoded_prod_ip(repo):
    wurzel, schreib = repo
    p = schreib("deploy.py", f"HOST = '{PROD_IP}'\n")

    funde = hs.scan_file("beispiel-hub", p, wurzel)

    assert [f.category for f in funde] == ["IP"]
    assert funde[0].severity == "critical"
    assert funde[0].line == 1
    assert funde[0].file == "deploy.py"


def test_should_honour_the_noqa_marker(repo):
    wurzel, schreib = repo
    p = schreib("deploy.py", f"HOST = '{PROD_IP}'  # {hs.NOQA_MARKER}\n")

    assert hs.scan_file("beispiel-hub", p, wurzel) == []


@pytest.mark.parametrize("praefix", ["#", "//"])
def test_should_ignore_a_finding_in_a_comment_line(repo, praefix):
    wurzel, schreib = repo
    p = schreib("deploy.py", f"{praefix} frueher: {PROD_IP}\n")

    assert hs.scan_file("beispiel-hub", p, wurzel) == []


def test_should_still_flag_a_trailing_comment_on_a_live_line(repo):
    wurzel, schreib = repo
    p = schreib("deploy.py", f"HOST = '{PROD_IP}'  # alt\n")

    assert len(hs.scan_file("beispiel-hub", p, wurzel)) == 1


def test_should_report_the_correct_line_number(repo):
    wurzel, schreib = repo
    p = schreib("deploy.py", f"a = 1\nb = 2\nHOST = '{PROD_IP}'\n")

    funde = hs.scan_file("beispiel-hub", p, wurzel)

    assert [f.line for f in funde] == [3]


def test_should_return_nothing_for_an_unreadable_file(repo):
    wurzel, _ = repo

    assert hs.scan_file("beispiel-hub", wurzel / "gibtsnicht.py", wurzel) == []


def test_should_report_a_path_relative_to_the_repo_root(repo):
    wurzel, schreib = repo
    p = schreib("apps/kunden/deploy.py", f"HOST = '{PROD_IP}'\n")

    funde = hs.scan_file("beispiel-hub", p, wurzel)

    assert funde[0].file == "apps/kunden/deploy.py"


def test_should_truncate_an_overlong_context_line(repo):
    wurzel, schreib = repo
    p = schreib("deploy.py", f"HOST = '{PROD_IP}'  " + "x" * 400 + "\n")

    funde = hs.scan_file("beispiel-hub", p, wurzel)

    assert len(funde[0].context) <= 120
    assert len(funde[0].match) <= 80


# --- discover_repos ----------------------------------------------------------


def repo_anlegen(basis: pathlib.Path, name: str) -> pathlib.Path:
    d = basis / name
    (d / ".git").mkdir(parents=True)
    return d


def test_should_list_only_real_repo_directories(tmp_path):
    repo_anlegen(tmp_path, "alpha-hub")
    repo_anlegen(tmp_path, "beta-hub")
    (tmp_path / "datei.txt").write_text("kein repo\n", encoding="utf-8")

    gefunden = hs.discover_repos(tmp_path)

    assert gefunden == ["alpha-hub", "beta-hub"]


def test_should_ignore_a_directory_without_git(tmp_path):
    """Ein Verzeichnis ohne .git ist kein Repo — daran bin ich beim Schreiben
    dieser Tests zuerst gescheitert; der Fall haelt die Bedingung fest."""
    (tmp_path / "kein-repo").mkdir()
    repo_anlegen(tmp_path, "echtes-hub")

    assert hs.discover_repos(tmp_path) == ["echtes-hub"]


def test_should_exclude_the_known_non_repo_directories(tmp_path):
    for name in hs._NON_REPO_DIRS:
        repo_anlegen(tmp_path, name)  # sogar mit .git bleiben sie draussen
    repo_anlegen(tmp_path, "echtes-hub")

    assert hs.discover_repos(tmp_path) == ["echtes-hub"]


def test_should_ignore_dotted_directories(tmp_path):
    repo_anlegen(tmp_path, ".versteckt")
    repo_anlegen(tmp_path, "echtes-hub")

    assert hs.discover_repos(tmp_path) == ["echtes-hub"]


def test_should_return_empty_for_a_missing_base_dir(tmp_path):
    assert hs.discover_repos(tmp_path / "gibtsnicht") == []
