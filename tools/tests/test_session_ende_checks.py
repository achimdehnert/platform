"""Tests fuer `tools/session_ende_checks.sh` (Ende-Runner, #2690 K1/K5).

Der Runner ersetzt den mechanischen Bash-Code, der bis hierhin im Fliesstext von
`.windsurf/workflows/session-ende.md` stand. Getestet wird die **ausgelieferte**
Datei, nicht eine Kopie: `bash -n` als Syntaxnetz und ein echter Lauf gegen ein
tmp_path-Fixture mit zwei git-Repos (eines dirty), einem Lease-Verzeichnis und
einem `gh`-Stub auf dem PATH.

Die drei Invarianten, die dieser Test haelt:

1. **Vollstaendigkeit** — die Summary nennt E.0 bis E.9. Eine Phase, die still
   ausfaellt, waere genau der Zustand, gegen den der Runner gebaut ist.
2. **Positivkontrolle** — ein dirty Repo MIT eigenem Lease wird als WARN
   erkannt. Ohne diese Zeile bestuende der Test auch, wenn E.7 nie etwas faende.
3. **SKIP ist kein Gruen** — fehlt ein Werkzeug, steht `SKIP` in der Zeile,
   nicht `PASS`. „NICHT messbar" als Entwarnung zu verbuchen war die teuerste
   Fehlklasse des Start-Runners (KONZ-platform-050).
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess

import pytest

_SKRIPT = pathlib.Path(__file__).resolve().parents[1] / "session_ende_checks.sh"
_HEUTE = subprocess.run(
    ["date", "+%Y-%m-%d"], capture_output=True, text=True, check=True
).stdout.strip()

# Der Stub antwortet auf genau die drei Aufrufformen, die der Runner kennt.
# `run list` liefert einen erfolgreichen Deploy, `pr list` liefert nichts —
# damit haengt kein Test an echten GitHub-Daten oder an Netz.
_GH_STUB = """#!/usr/bin/env bash
args="$*"
case "$args" in
  *"run list"*)  echo "success completed 12345" ;;
  *"pr list"*)   : ;;
  *)             : ;;
esac
exit 0
"""


def _git(cwd: pathlib.Path, *args: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


def _repo(basis: pathlib.Path, name: str, *, dirty: bool) -> pathlib.Path:
    pfad = basis / name
    pfad.mkdir(parents=True)
    _git(pfad, "init", "-q", "-b", "main")
    (pfad / "README.md").write_text("x\n", encoding="utf-8")
    _git(pfad, "add", "README.md")
    _git(pfad, "commit", "-q", "-m", "init")
    if dirty:
        (pfad / "offen.txt").write_text("uncommitted\n", encoding="utf-8")
    return pfad


@pytest.fixture()
def umgebung(tmp_path: pathlib.Path) -> dict:
    """GITHUB_DIR mit zwei Repos, LEASE_DIR mit einem heutigen Lease auf `beta`.

    `PLATFORM_DIR` zeigt bewusst auf ein Attrappen-Repo OHNE die Python-Werkzeuge:
    so ist der Fehlt-Fall (SKIP) im selben Lauf mitgeprueft.
    """
    github = tmp_path / "github"
    github.mkdir()
    _repo(github, "alpha", dirty=False)
    _repo(github, "beta", dirty=True)

    platform = github / "alpha"  # Attrappe: git-Repo, aber ohne tools/-Baum
    (platform / "VERSION").write_text("9.9.9\n", encoding="utf-8")
    _git(platform, "add", "VERSION")
    _git(platform, "commit", "-q", "-m", "version")
    _git(platform, "remote", "add", "origin", "https://github.com/testorg/alpha.git")

    leases = tmp_path / "leases"
    leases.mkdir()
    (leases / f"{_HEUTE}-test-beta-120000.json").write_text(
        '{"session_id": "x", "repo": "beta", "branch": "b"}\n', encoding="utf-8"
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(_GH_STUB, encoding="utf-8")
    gh.chmod(0o755)

    return {"github": github, "platform": platform, "leases": leases, "bin": bin_dir}


def _lauf(
    umgebung: dict, ziel: str = "alpha", *, extra: dict | None = None, argv=()
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_DIR": str(umgebung["github"]),
            "PLATFORM_DIR": str(umgebung["platform"]),
            "LEASE_DIR": str(umgebung["leases"]),
            "PATH": f"{umgebung['bin']}{os.pathsep}{env['PATH']}",
            # Kein Netz, kein Modell: E.5 darf nicht in einen echten
            # Ollama-Aufruf laufen.
            "OLLAMA_HOST": "http://127.0.0.1:1",
            # Der git-User entscheidet ueber den Fallback „Repos mit Commits von
            # heute" — und damit ueber die Eigen/Fremd-Trennung in E.7. Er wird
            # hier ausdruecklich gesetzt, statt aus der Umgebung zu kommen: in
            # CI ist `git config user.name` leer, lokal traegt er den Namen des
            # Entwicklers, und dieser Unterschied liess denselben Test lokal
            # gruen und in CI rot werden (Lauf 33644319863).
            "SESSION_ENDE_GIT_USER": "niemand-in-diesem-fixture",
        }
    )
    if extra:
        env.update(extra)
    return subprocess.run(
        ["bash", str(_SKRIPT), ziel, *argv],
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


def _summary_zeilen(stdout: str) -> dict[str, str]:
    """Phasen-ID -> Statuswort aus der Summary-Tabelle."""
    zeilen = {}
    for m in re.finditer(
        r"^\| (E\.\d[^|]*?) \| \S+ (PASS|WARN|FAIL|SKIP) \|", stdout, re.M
    ):
        zeilen[m.group(1).split()[0]] = m.group(2)
    return zeilen


def test_should_pass_bash_syntax_check():
    """`bash -n` faengt genau die Klasse, die ein Runner am teuersten bezahlt."""
    ergebnis = subprocess.run(
        ["bash", "-n", str(_SKRIPT)], capture_output=True, text=True
    )
    assert ergebnis.returncode == 0, ergebnis.stderr


def test_should_be_executable():
    assert os.access(_SKRIPT, os.X_OK), "Runner muss ohne `bash` davor startbar sein"


def test_should_report_every_phase_from_e0_to_e9(umgebung):
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    fehlend = [f"E.{i}" for i in range(10) if f"E.{i}" not in phasen]
    assert not fehlend, f"Phasen fehlen in der Summary: {fehlend}\n{ergebnis.stdout}"


def test_should_end_with_result_ok_and_judgment_line(umgebung):
    ergebnis = _lauf(umgebung)
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    assert "RESULT: OK" in ergebnis.stdout
    assert "JUDGMENT: 0a 0b 0c 0d 0e 2 3.5 — im Skill abarbeiten" in ergebnis.stdout


def test_should_warn_about_a_dirty_repo_of_this_session(umgebung):
    """Positivkontrolle fuer E.7: `beta` ist dirty UND traegt ein heutiges Lease."""
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.7"] == "WARN", ergebnis.stdout
    assert "eigene dirty: beta" in ergebnis.stdout


def test_should_not_warn_when_no_own_repo_is_dirty(umgebung):
    """Gegenprobe: ohne Lease auf `beta` ist dasselbe dirty Repo nur ein Hinweis."""
    for lease in umgebung["leases"].glob("*.json"):
        lease.unlink()
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.7"] == "PASS", ergebnis.stdout
    assert "fremd (nur Hinweis): beta" in ergebnis.stdout


def test_should_claim_a_repo_via_the_commit_fallback(umgebung):
    """Positivkontrolle fuer den Fallback: der Autor der Fixture-Commits heisst `test`.

    Ohne diese Zeile wuerde der Gegenproben-Test oben auch bestehen, wenn der
    Fallback gar nichts mehr faende.
    """
    for lease in umgebung["leases"].glob("*.json"):
        lease.unlink()
    ergebnis = _lauf(umgebung, extra={"SESSION_ENDE_GIT_USER": "test"})
    assert "quelle=commits-heute" in ergebnis.stdout
    assert _summary_zeilen(ergebnis.stdout)["E.7"] == "WARN", ergebnis.stdout
    assert "eigene dirty: beta" in ergebnis.stdout


def test_should_drop_the_fallback_without_an_author_filter(umgebung):
    """Ohne git-User kein Fallback — sonst wird fremde Arbeit zur eigenen.

    Genau daran scheiterte CI-Lauf 33644319863: dort ist `git config user.name`
    leer, `--author` fiel ersatzlos weg, und jedes heute angelegte Fixture-Repo
    galt als von dieser Sitzung beruehrt.
    """
    for lease in umgebung["leases"].glob("*.json"):
        lease.unlink()
    ergebnis = _lauf(umgebung, extra={"SESSION_ENDE_GIT_USER": ""})
    assert "quelle=unbestimmt(kein git user.name)" in ergebnis.stdout
    assert _summary_zeilen(ergebnis.stdout)["E.7"] == "PASS", ergebnis.stdout


def test_should_skip_not_pass_when_a_tool_is_missing(umgebung):
    """`NICHT messbar` ist kein Gruen — die Werkzeug-Phasen muessen SKIP sein."""
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    for phase in ("E.3", "E.4", "E.5", "E.6", "E.9"):
        assert phasen[phase] == "SKIP", (
            f"{phase} ist {phasen[phase]}\n{ergebnis.stdout}"
        )
    assert "Werkzeug fehlt" in ergebnis.stdout
    assert "HINWEIS:" in ergebnis.stdout, "SKIP-Zahl muss unter der Tabelle stehen"


# ── E.8 Worktree-Hygiene (Umbau 2026-09-14, Retro oqu6Z6 Befund #21) ────────
#
# Bis hierhin stand E.8 auf SKIP („raeumt der naechste Sitzungsstart"). Realfall:
# 13 Baeume, zwei mit dem Git-eigenen Etikett `prunable`, einige Wochen alt —
# angezeigt, nie behandelt. Jetzt wird geprunt, und die Altersgrenze ist ein FAIL.

_ALT_TAGE = 60


def _worktree(repo: pathlib.Path, name: str, *, alt: bool) -> pathlib.Path:
    """Verknuepfter Baum `name` neben `repo`; `alt` datiert Commit UND Anlage zurueck."""
    pfad = repo.parent / name
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    subprocess.run(
        ["git", "worktree", "add", "-q", "-b", name, str(pfad)],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
    )
    if alt:
        datum = f"@{int(__import__('time').time()) - _ALT_TAGE * 86400} +0000"
        env.update({"GIT_AUTHOR_DATE": datum, "GIT_COMMITTER_DATE": datum})
        (pfad / f"{name}.txt").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=pfad, env=env, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "alt"], cwd=pfad, env=env, check=True
        )
        gitdir = subprocess.run(
            ["git", "rev-parse", "--absolute-git-dir"],
            cwd=pfad,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        stempel = __import__("time").time() - _ALT_TAGE * 86400
        os.utime(pathlib.Path(gitdir) / "HEAD", (stempel, stempel))
    return pfad


def test_should_fail_on_a_worktree_older_than_the_age_limit(umgebung):
    """POSITIVKONTROLLE: ein alter Baum ist ein FAIL, ein frischer daneben nicht."""
    alpha = umgebung["github"] / "alpha"
    _worktree(alpha, "wt-alt", alt=True)
    _worktree(alpha, "wt-frisch", alt=False)
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.8"] == "FAIL", ergebnis.stdout
    zeile = next(z for z in ergebnis.stdout.splitlines() if z.startswith("| E.8"))
    assert "wt-alt(60d)" in zeile, zeile
    assert "wt-frisch" not in zeile, zeile
    assert "RESULT: FAIL" in ergebnis.stdout


def test_should_prune_an_orphaned_worktree_entry(umgebung):
    """POSITIVKONTROLLE `prunable`: Verzeichnis weg, Eintrag bleibt — der Runner raeumt ihn."""
    alpha = umgebung["github"] / "alpha"
    verwaist = _worktree(alpha, "wt-verwaist", alt=False)
    __import__("shutil").rmtree(verwaist)
    vorher = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=alpha,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "prunable" in vorher
    ergebnis = _lauf(umgebung)
    nachher = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=alpha,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "prunable" not in nachher, nachher
    assert _summary_zeilen(ergebnis.stdout)["E.8"] == "PASS", ergebnis.stdout
    assert "prunable bereinigt: 1" in ergebnis.stdout


def test_should_accept_an_old_worktree_kept_with_a_reason(umgebung):
    """NEGATIVKONTROLLE: derselbe alte Baum mit Grund im Verwaltungsverzeichnis."""
    alpha = umgebung["github"] / "alpha"
    alt = _worktree(alpha, "wt-behalten", alt=True)
    gitdir = subprocess.run(
        ["git", "rev-parse", "--absolute-git-dir"],
        cwd=alt,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    (pathlib.Path(gitdir) / "behalten").write_text(
        "laufender Rebase\n", encoding="utf-8"
    )
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.8"] == "PASS", ergebnis.stdout
    assert "behalten mit Grund: 1" in ergebnis.stdout


# ── E.3 Handover-Frische am Sitzungsende (Umbau 2026-09-14, Befund #22) ─────

_CHECKER = (
    pathlib.Path(__file__).resolve().parents[2]
    / "scripts"
    / "checks"
    / "agent_handover_freshness_check.py"
)


def _handover_umgebung(umgebung, commits_danach: int) -> None:
    """Ziel-Repo `gamma` mit Handover-Nachtrag und `commits_danach` weiteren Commits;
    PLATFORM_DIR bekommt den echten Pruefer."""
    ziel = umgebung["platform"] / "scripts" / "checks"
    ziel.mkdir(parents=True)
    __import__("shutil").copy(_CHECKER, ziel / _CHECKER.name)
    gamma = _repo(umgebung["github"], "gamma", dirty=False)
    (gamma / "AGENT_HANDOVER.md").write_text(
        f"# Handover\n\n## Aktueller Stand ({_HEUTE})\n\nStand.\n", encoding="utf-8"
    )
    _git(gamma, "add", "AGENT_HANDOVER.md")
    _git(gamma, "commit", "-q", "-m", "docs(handover): Nachtrag")
    for i in range(commits_danach):
        (gamma / f"f{i}.txt").write_text("x\n", encoding="utf-8")
        _git(gamma, "add", f"f{i}.txt")
        _git(gamma, "commit", "-q", "-m", f"feat: Arbeit {i}")
    _git(gamma, "remote", "add", "origin", "https://github.com/testorg/gamma.git")


def test_should_fail_when_commits_landed_after_the_handover_and_no_pr_is_open(umgebung):
    """POSITIVKONTROLLE am Realfall: Nachtrag von frueher, danach Commits, kein
    Handover-PR — bisher PASS, weil E.3 ohne Schwelle nur das Datum pruefte."""
    _handover_umgebung(umgebung, commits_danach=3)
    ergebnis = _lauf(umgebung, "gamma")
    assert _summary_zeilen(ergebnis.stdout)["E.3"] == "FAIL", ergebnis.stdout
    assert "3 Commits seit dem letzten Nachtrag" in ergebnis.stdout


def test_should_pass_when_the_handover_is_open_as_a_pr(umgebung):
    """NEGATIVKONTROLLE: dieselben Commits, aber der Nachtrag liegt als PR offen."""
    _handover_umgebung(umgebung, commits_danach=3)
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace(
            '*"pr list"*)   : ;;', "*\"pr list\"*)   printf '#77@2026-09-14\\n' ;;"
        ),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung, "gamma")
    assert _summary_zeilen(ergebnis.stdout)["E.3"] == "PASS", ergebnis.stdout


def test_should_pass_when_nothing_landed_after_the_handover(umgebung):
    """NEGATIVKONTROLLE: Nachtrag ist der letzte Commit — kein Befund."""
    _handover_umgebung(umgebung, commits_danach=0)
    ergebnis = _lauf(umgebung, "gamma")
    assert _summary_zeilen(ergebnis.stdout)["E.3"] == "PASS", ergebnis.stdout


def test_should_read_touched_repos_from_todays_leases(umgebung):
    ergebnis = _lauf(umgebung)
    assert "quelle=leases" in ergebnis.stdout
    assert _summary_zeilen(ergebnis.stdout)["E.1"] == "PASS", ergebnis.stdout


def test_should_warn_when_the_last_deploy_failed(umgebung):
    """E.1-Positivkontrolle ueber den gh-Stub: `failure` darf nicht PASS werden."""
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace(
            'echo "success completed 12345"', 'echo "failure completed 999"'
        ),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.1"] == "WARN", ergebnis.stdout
    assert "nicht als fertig melden" in ergebnis.stdout.lower()


def test_should_warn_when_a_deploy_run_is_waiting(umgebung):
    """Die zweite Klasse: ein wartender Run haelt die Concurrency-Group.

    Sein `conclusion` ist null — ohne eigene Klasse zaehlt er als „kein Befund".
    """
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace('echo "success completed 12345"', 'echo "none waiting 4242"'),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.1"] == "WARN"
    assert "waiting: beta(4242)" in ergebnis.stdout


def test_should_warn_about_more_than_one_open_handover_pr(umgebung):
    """Lehre c494a2: zwei offene Handover-PRs sind konkurrierende Staende."""
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace(
            '*"pr list"*)   : ;;',
            "*\"pr list\"*)   printf '#11@2026-09-02\\n#12@2026-09-02\\n' ;;",
        ),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.2"] == "WARN", ergebnis.stdout
    assert "2 offene Handover-PRs" in ergebnis.stdout


def test_should_accept_a_single_open_handover_pr(umgebung):
    """Gegenprobe zur vorigen Zeile: einer ist der Normalfall, kein Befund."""
    (umgebung["bin"] / "gh").write_text(
        _GH_STUB.replace(
            '*"pr list"*)   : ;;', "*\"pr list\"*)   printf '#11@2026-09-02\\n' ;;"
        ),
        encoding="utf-8",
    )
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    assert _summary_zeilen(ergebnis.stdout)["E.2"] == "PASS", ergebnis.stdout


def test_should_accept_a_session_id_argument(umgebung):
    ergebnis = _lauf(umgebung, argv=("--session-id", "sitzung-42"))
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    assert "session=sitzung-42" in ergebnis.stdout


def test_should_accept_a_repo_path_and_use_its_basename(umgebung):
    """#2773: der Skill ruft mit einem PFAD auf, nicht mit einem Namen.

    Vorher landete der Pfad selbst als Repo-NAME (`$OWNER/$TARGET_REPO`) und als
    Pfadsegment (`$GITHUB_DIR/$TARGET_REPO/AGENT_HANDOVER.md`) — beides falsch.
    """
    ziel_pfad = umgebung["github"] / "beta"
    (ziel_pfad / "AGENT_HANDOVER.md").write_text("# Handover\n", encoding="utf-8")
    ergebnis = _lauf(umgebung, ziel=str(ziel_pfad))
    ziel_real = ziel_pfad.resolve()
    assert f"target=beta ({ziel_real})" in ergebnis.stdout, ergebnis.stdout
    assert "keine AGENT_HANDOVER.md" not in ergebnis.stdout


def test_should_derive_owner_from_the_target_remote(umgebung):
    """#2794: OWNER kommt aus dem Ziel-Repo, nicht aus dem Platform-Remote."""
    ziel_pfad = umgebung["github"] / "beta"
    _git(ziel_pfad, "remote", "add", "origin", "git@github.com:andereorg/repo.git")
    aufrufe = umgebung["bin"] / "gh-aufrufe.log"
    stub = f"""#!/usr/bin/env bash
echo "$*" >> "{aufrufe}"
args="$*"
case "$args" in
  *"run list"*)  echo "success completed 12345" ;;
  *"pr list"*)   : ;;
  *)             : ;;
esac
exit 0
"""
    (umgebung["bin"] / "gh").write_text(stub, encoding="utf-8")
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung, ziel=str(ziel_pfad))
    assert ergebnis.returncode == 0, ergebnis.stdout + ergebnis.stderr
    inhalt = aufrufe.read_text(encoding="utf-8") if aufrufe.exists() else ""
    # OWNER kommt aus der Remote-URL (`andereorg`), der Repo-NAME bleibt der
    # Verzeichnisname (`beta`) — die Remote heisst zwar `.../repo.git`, aber
    # der Runner nennt das Ziel nach seinem Pfadsegment, nicht nach der URL.
    assert "andereorg/beta" in inhalt, inhalt


def test_should_skip_not_pass_when_gh_fails_in_e2(umgebung):
    """#2794: ein scheiterndes `gh` darf nicht als leere (= gruene) Liste durchgehen."""
    fehl_stub = """#!/usr/bin/env bash
args="$*"
case "$args" in
  *"run list"*)  echo "success completed 12345" ;;
  *"pr list"*)   echo "gh: rate limited" >&2; exit 1 ;;
  *)             exit 0 ;;
esac
"""
    (umgebung["bin"] / "gh").write_text(fehl_stub, encoding="utf-8")
    (umgebung["bin"] / "gh").chmod(0o755)
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.2"] == "SKIP", ergebnis.stdout
    assert "[SKIP] E.2" in ergebnis.stdout
    assert "gh scheiterte" in ergebnis.stdout


def test_should_skip_not_pass_when_gh_fails_in_e5(umgebung):
    """Gleiche Lehre fuer E.5 — zusaetzlich ein `curl`-Stub, damit die
    Ollama-Erreichbarkeitspruefung nicht schon vorher (mangels Netz) SKIPt."""
    fehl_stub = """#!/usr/bin/env bash
args="$*"
case "$args" in
  *"run list"*)  echo "success completed 12345" ;;
  *"pr list"*)   echo "gh: rate limited" >&2; exit 1 ;;
  *)             exit 0 ;;
esac
"""
    (umgebung["bin"] / "gh").write_text(fehl_stub, encoding="utf-8")
    (umgebung["bin"] / "gh").chmod(0o755)
    (umgebung["bin"] / "curl").write_text(
        "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8"
    )
    (umgebung["bin"] / "curl").chmod(0o755)
    ergebnis = _lauf(umgebung)
    phasen = _summary_zeilen(ergebnis.stdout)
    assert phasen["E.5"] == "SKIP", ergebnis.stdout
    assert "[SKIP] E.5" in ergebnis.stdout
    assert "gh scheiterte" in ergebnis.stdout


# ── E.3 Fragment-Modus (#1944 K6) ────────────────────────────────────────────


def _fragment_repo(umgebung: dict) -> pathlib.Path:
    ziel = umgebung["github"] / "beta"
    frag = ziel / "docs" / "handover.d"
    frag.mkdir(parents=True)
    (frag / "2026-09-16T08-00-00Z-auf-main.md").write_text("x\n", encoding="utf-8")
    _git(ziel, "add", "docs")
    _git(ziel, "commit", "-q", "-m", "fragment")
    _git(ziel, "update-ref", "refs/remotes/origin/main", "HEAD")
    return ziel


def _e3(stdout: str) -> str:
    return next(z for z in stdout.splitlines() if "E.3 handover-frische" in z)


def test_should_pass_e3_when_session_fragment_is_on_main(umgebung):
    ziel = _fragment_repo(umgebung)
    ergebnis = _lauf(umgebung, ziel=str(ziel), argv=("--session-id", "auf-main"))
    assert "Fragment der Sitzung liegt auf main" in _e3(ergebnis.stdout)


def test_should_fail_e3_when_session_has_no_fragment(umgebung):
    ziel = _fragment_repo(umgebung)
    ergebnis = _lauf(umgebung, ziel=str(ziel), argv=("--session-id", "ohne"))
    zeile = _e3(ergebnis.stdout)
    assert "FAIL" in zeile and "kein Fragment fuer Sitzung ohne" in zeile


def test_should_not_count_other_sessions_fragment_with_same_suffix(umgebung):
    # "main" ist Endung von "auf-main" — darf nicht als eigenes Fragment gelten.
    ziel = _fragment_repo(umgebung)
    ergebnis = _lauf(umgebung, ziel=str(ziel), argv=("--session-id", "main"))
    assert "FAIL" in _e3(ergebnis.stdout)


def test_should_warn_e3_in_fragment_mode_without_session_id(umgebung):
    ziel = _fragment_repo(umgebung)
    ergebnis = _lauf(umgebung, ziel=str(ziel))
    zeile = _e3(ergebnis.stdout)
    assert "WARN" in zeile and "--session-id" in zeile


def test_should_name_repo_after_main_tree_when_called_from_worktree(umgebung, tmp_path):
    haupt = umgebung["github"] / "beta"
    wt = tmp_path / "worktrees" / "2026-09-16-slug-120000"
    _git(haupt, "worktree", "add", "-q", "-b", "sitzung", str(wt))
    ergebnis = _lauf(umgebung, ziel=str(wt))
    assert f"target=beta ({wt.resolve()})" in ergebnis.stdout, ergebnis.stdout


# ── Sitzungsabgrenzung E.3 + E.10 (platform#2234, Retro #3543 Befunde #2/#4) ──
#
# Beide Phasen sahen die Arbeit paralleler Sitzungen desselben Kontos (E.10)
# bzw. nur, OB ein Fragment existiert (E.3). Die Drills bauen die Realfaelle vom
# 2026-09-24 nach — mit echtem `tools/sitzungs_branches.py` und
# `tools/session_abgleich.py` im Attrappen-Platform-Baum und einem gh-Stub, der
# aus einer Fixture-Datei antwortet (kein Netz).

_WERKZEUGE = pathlib.Path(__file__).resolve().parents[1]
_SITZUNG = "e911bf49-94e1-4b4c-86ed-f4a4337ba501"
_EIGEN = "session/2026-09-24/achim-dehnert/eigen"

# Antwortet auf `pr list --head`, den kontoweiten `pr list` und `issue view`;
# jeder `--jq`-Aufruf bleibt leer (E.1/E.2/frag-pr sind hier nicht Thema).
_GH_FIXTURE_STUB = """#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
d = json.load(open(os.environ["GH_FIXTURE"]))
if "--jq" in a:
    sys.exit(0)
if a[:2] == ["pr", "list"]:
    prs = d.get("prs", [])
    if "--head" in a:
        prs = [p for p in prs if p.get("headRefName") == a[a.index("--head") + 1]]
    print(json.dumps(prs)); sys.exit(0)
if a[:2] == ["issue", "view"]:
    for i in d.get("issues", []):
        if str(i["number"]) == a[2]:
            print(json.dumps(i)); sys.exit(0)
    sys.exit(1)
print("[]")
"""


def _mit_werkzeugen(umgebung: dict, fixture: dict, tmp_path: pathlib.Path) -> dict:
    tools = umgebung["platform"] / "tools"
    tools.mkdir(exist_ok=True)
    for name in ("sitzungs_branches.py", "session_abgleich.py"):
        (tools / name).symlink_to(_WERKZEUGE / name)
    gh = umgebung["bin"] / "gh"
    gh.write_text(_GH_FIXTURE_STUB, encoding="utf-8")
    gh.chmod(0o755)
    pfad = tmp_path / "gh-fixture.json"
    pfad.write_text(__import__("json").dumps(fixture), encoding="utf-8")
    return {"GH_FIXTURE": str(pfad)}


def _sitzungs_lease(
    umgebung: dict, repo: str, claude_session: str | None = _SITZUNG
) -> None:
    lease = {"session_id": "l-eigen", "repo": repo, "branch": _EIGEN}
    if claude_session is not None:
        lease["claude_session"] = claude_session
    (umgebung["leases"] / "l-eigen.json.closed").write_text(
        __import__("json").dumps(lease), encoding="utf-8"
    )


def _fragment(ziel: pathlib.Path, stempel: str, erstellt: str) -> None:
    frag = ziel / "docs" / "handover.d"
    frag.mkdir(parents=True, exist_ok=True)
    (frag / f"{stempel}-e911bf49.md").write_text(
        f"---\nsession_id: e911bf49\nerstellt: {erstellt}\ntitel: t\n---\n",
        encoding="utf-8",
    )
    _git(ziel, "add", "docs")
    _git(ziel, "commit", "-q", "-m", f"fragment {stempel}")
    _git(ziel, "update-ref", "refs/remotes/origin/main", "HEAD")


_PR_NACH_FRAGMENT = {
    "number": 3540,
    "headRefName": _EIGEN,
    "state": "MERGED",
    "createdAt": "2026-09-24T15:50:00Z",
    "mergedAt": "2026-09-24T16:08:00Z",
    "files": [{"path": "tools/x.py"}],
    "body": "",
    "author": {"login": "a"},
}


def test_should_fail_e3_when_session_merged_work_after_its_fragment(umgebung, tmp_path):
    """Positivkontrolle Befund #4: Fragment 13:01Z, danach #3540 (gemergt 16:08Z)."""
    ziel = umgebung["github"] / "beta"
    _fragment(ziel, "2026-09-24T13-01-28Z", "2026-09-24T13:01:28Z")
    _sitzungs_lease(umgebung, "beta")
    extra = _mit_werkzeugen(umgebung, {"prs": [_PR_NACH_FRAGMENT]}, tmp_path)
    ergebnis = _lauf(
        umgebung, ziel=str(ziel), extra=extra, argv=("--session-id", _SITZUNG[:8])
    )
    zeile = _e3(ergebnis.stdout)
    assert "FAIL" in zeile and "veraltet" in zeile and "beta#3540" in zeile, (
        ergebnis.stdout
    )


def test_should_pass_e3_when_a_younger_fragment_covers_the_later_work(
    umgebung, tmp_path
):
    """Gegenprobe: Nachtrag 17:06Z liegt auf main — der Nachlauf ist gedeckt."""
    ziel = umgebung["github"] / "beta"
    _fragment(ziel, "2026-09-24T13-01-28Z", "2026-09-24T13:01:28Z")
    _fragment(ziel, "2026-09-24T17-06-22Z", "2026-09-24T17:06:22Z")
    _sitzungs_lease(umgebung, "beta")
    extra = _mit_werkzeugen(umgebung, {"prs": [_PR_NACH_FRAGMENT]}, tmp_path)
    ergebnis = _lauf(
        umgebung, ziel=str(ziel), extra=extra, argv=("--session-id", _SITZUNG[:8])
    )
    zeile = _e3(ergebnis.stdout)
    assert "PASS" in zeile and "17-06-22Z" in zeile, ergebnis.stdout


def test_should_skip_not_pass_e3_when_the_session_is_not_assignable(umgebung, tmp_path):
    """Alt-Lease ohne claude_session: Fragment da, Nachlauf nicht pruefbar — kein Gruen."""
    ziel = umgebung["github"] / "beta"
    _fragment(ziel, "2026-09-24T13-01-28Z", "2026-09-24T13:01:28Z")
    _sitzungs_lease(umgebung, "beta", claude_session=None)
    extra = _mit_werkzeugen(umgebung, {"prs": [_PR_NACH_FRAGMENT]}, tmp_path)
    ergebnis = _lauf(
        umgebung, ziel=str(ziel), extra=extra, argv=("--session-id", _SITZUNG[:8])
    )
    zeile = _e3(ergebnis.stdout)
    assert "SKIP" in zeile and "nicht zuordenbar" in zeile, ergebnis.stdout


def _flut_fixture() -> dict:
    """Realfall E.10: fremde Befunde aus Parallelsitzungen + eigener #3489 → #3469."""
    prs, issues = [], []
    for i in range(34):
        prs.append(
            {
                "number": 3400 + i,
                "state": "MERGED",
                "files": [],
                "author": {"login": "a"},
                "headRefName": f"session/2026-09-24/achim-dehnert/fremd-{i}",
                "body": f"Refs #{3300 + i}",
            }
        )
        issues.append({"number": 3300 + i, "state": "OPEN", "body": ""})
    prs.append(
        {
            "number": 3489,
            "state": "MERGED",
            "files": [],
            "author": {"login": "a"},
            "headRefName": _EIGEN,
            "body": "Refs #3469",
        }
    )
    issues.append({"number": 3469, "state": "OPEN", "body": ""})
    return {"prs": prs, "issues": issues}


def _e10(stdout: str) -> str:
    return next(z for z in stdout.splitlines() if "| E.10 session-abgleich" in z)


def test_should_name_own_open_issue_in_e10_among_foreign_findings(umgebung, tmp_path):
    """Positivkontrolle Befund #2: mit --session-id nennt E.10 genau alpha#3469."""
    _sitzungs_lease(umgebung, "alpha")
    extra = _mit_werkzeugen(umgebung, _flut_fixture(), tmp_path)
    ergebnis = _lauf(umgebung, extra=extra, argv=("--session-id", _SITZUNG[:8]))
    zeile = _e10(ergebnis.stdout)
    assert "WARN" in zeile and "1 Befund(e) dieser Sitzung: alpha#3469" in zeile, zeile


def test_should_mark_e10_as_account_wide_without_session_id(umgebung, tmp_path):
    """Gegenprobe: ohne --session-id bleibt der kontoweite Lauf — und sagt es."""
    _sitzungs_lease(umgebung, "alpha")
    extra = _mit_werkzeugen(umgebung, _flut_fixture(), tmp_path)
    ergebnis = _lauf(umgebung, extra=extra)
    zeile = _e10(ergebnis.stdout)
    assert "WARN" in zeile and "kontoweit" in zeile, zeile
    assert "1 Befund(e)" not in zeile


def test_should_skip_e10_when_no_session_branch_is_assignable(umgebung, tmp_path):
    _sitzungs_lease(umgebung, "alpha", claude_session=None)
    extra = _mit_werkzeugen(umgebung, _flut_fixture(), tmp_path)
    ergebnis = _lauf(umgebung, extra=extra, argv=("--session-id", _SITZUNG[:8]))
    zeile = _e10(ergebnis.stdout)
    assert "SKIP" in zeile and "nicht zuordenbar" in zeile, zeile
