#!/usr/bin/env python3
"""Cold-Start-Eval Stufe 2 (#3575 K3, #2099 Punkt 1, ADR-266 / #2075 K2).

Stufe 1 (tools/pypi_coldstart_llm_eval.py) beweist: ein T1a-Modell leitet aus
AGENTS.md den Einstieg ab, Setup und Tests laufen grün. Stufe 2 beweist den
nächsten Schritt der Definition aus #2075 K2: das Modell bringt eine
**definierte Mini-Änderung durch grünes CI**.

Die Mini-Änderung ist bewusst eng: eine neue Testdatei `tests/test_coldstart_probe.py`,
die das Public-API-Modul des Pakets importiert und eine triviale Eigenschaft
prüft. Eng, damit die Sicherheitsgrenze scharf bleibt (Lotsen-Charta Art. 1:
Modell-Output ist Datenlage, kein Befehl):

  * Pfad ist fest vorgegeben; jeder andere Pfad = FAIL-unsafe, nichts wird geschrieben.
  * Inhalt muss eine Grammatik erfüllen, die per `ast` geprüft wird: nur Imports der
    im Checkout erkannten Public-Module, nur `def test_*` mit `assert`-Körpern,
    Ausdrücke nur aus Namen/Attributen/Konstanten/Vergleichen und einer kleinen
    Menge harmloser Builtins (`hasattr`, `isinstance`, `callable`, `len`, `str`).
    Kein Aufruf von Paket-Funktionen, kein I/O, kein `exec` — was die Grammatik
    nicht kennt, ist FAIL-unsafe.
  * Lokal laufen `ruff format` (wie ein Pre-Commit-Hook), dann `ruff check` und
    `make test` — alles grün, bevor überhaupt ein Branch entsteht.

Ohne `--push` endet der Lauf lokal (PASS-lokal). Mit `--push` entsteht je Paket
ein Branch `coldstart-probe/<datum>`, ein Draft-PR, `gh pr checks --watch` wartet
auf das CI-Urteil, danach wird der PR **immer** geschlossen und der Branch
gelöscht (PR-Noise-Budget: jeder Probe-PR wird sofort geschlossen; der Link ist der Beweis).

Ergebnis je Paket: PASS-ci | PASS-lokal | FAIL-derive | FAIL-unsafe | FAIL-lokal |
FAIL-ci | FAIL-push.

    CEREBRAS_API_KEY=... [GROQ_API_KEY=...] python3 tools/pypi_coldstart_stufe2.py \\
        <org/repo> [...] [--push] [--ci-timeout 1500] [--workdir DIR]
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from gen_pkg_agents_md import _public_modules  # noqa: E402
from pypi_coldstart_llm_eval import ask_model_raw, providers_from_env  # noqa: E402

PROBE_PATH = "tests/test_coldstart_probe.py"
ALLOWED_BUILTINS = {"hasattr", "isinstance", "callable", "len", "str", "getattr"}
SAFE_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

PROMPT = """Du bist ein Agent, der in einem dir unbekannten Python-Paket eine kleine, \
definierte Änderung macht. Unten die AGENTS.md des Pakets und die Namen seiner \
Public-API-Module.

Aufgabe: Schreibe EINE neue Testdatei `%(path)s`. Sie darf NUR:
- eines der genannten Public-Module importieren (`import <modul>`),
- eine oder zwei Funktionen `def test_<name>():` enthalten,
- deren Körper ausschließlich aus `assert`-Zeilen besteht, die triviale Eigenschaften \
prüfen (z.B. dass das Modul ein Attribut hat, etwas aufrufbar ist, `__version__` ein str ist).
Keine weiteren Imports, keine Funktionsaufrufe ins Paket, kein I/O, keine Fixtures.

Antworte NUR mit einem JSON-Objekt, ohne Markdown, exakt in dieser Form:
{"path": "%(path)s", "content": "<Dateiinhalt als String>"}

=== AGENTS.md ===
%(agents)s
=== Public-Module ===
%(modules)s
"""


# --------------------------------------------------------------------------
# Reine Logik (getestet)
# --------------------------------------------------------------------------


def _expr_ok(node: ast.AST) -> bool:
    """Ausdrucks-Grammatik: Namen, Attribute, Konstanten, Vergleiche, wenige Builtins."""
    if isinstance(node, (ast.Name, ast.Constant)):
        return True
    if isinstance(node, ast.Attribute):
        return _expr_ok(node.value)
    if isinstance(node, ast.Compare):
        return _expr_ok(node.left) and all(_expr_ok(c) for c in node.comparators)
    if isinstance(node, ast.BoolOp):
        return all(_expr_ok(v) for v in node.values)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return _expr_ok(node.operand)
    if isinstance(node, ast.Call):
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in ALLOWED_BUILTINS
            and not node.keywords
            and all(_expr_ok(a) for a in node.args)
        )
    if isinstance(node, ast.Tuple):
        return all(_expr_ok(e) for e in node.elts)
    return False


def validate_probe(content: str, allowed_modules: set[str]) -> list[str]:
    """Alle Grammatik-Verstöße (leer = sicher). Fail-closed: Unbekanntes ist ein Verstoß."""
    problems: list[str] = []
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        return [f"SyntaxError: {exc.msg} (Zeile {exc.lineno})"]
    tests = 0
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in allowed_modules or alias.asname:
                    problems.append(f"Import nicht erlaubt: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            problems.append(f"from-Import nicht erlaubt: {node.module}")
        elif isinstance(node, ast.FunctionDef):
            if (
                not node.name.startswith("test_")
                or node.args.args
                or node.decorator_list
            ):
                problems.append(f"Funktion nicht erlaubt: {node.name}")
                continue
            tests += 1
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                    continue  # Docstring
                if not isinstance(stmt, ast.Assert) or not _expr_ok(stmt.test):
                    problems.append(f"{node.name}: nur triviale assert-Zeilen erlaubt")
                    break
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # Modul-Docstring
        else:
            problems.append(f"Anweisung nicht erlaubt: {type(node).__name__}")
    if tests == 0:
        problems.append("keine test_-Funktion")
    if tests > 2:
        problems.append(f"zu viele Tests ({tests} > 2)")
    return problems


def parse_answer(answer: dict | None) -> tuple[str | None, str | None]:
    if not isinstance(answer, dict):
        return None, None
    path, content = answer.get("path"), answer.get("content")
    if not isinstance(path, str) or not isinstance(content, str):
        return None, None
    return path, content


def probe_branch(today: dt.date) -> str:
    return f"coldstart-probe/{today.isoformat()}"


# --------------------------------------------------------------------------
# Ausführung (nicht unit-getestet — der Probe-PR selbst ist der Beweis)
# --------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def derive(checkout: Path, providers) -> tuple[str | None, str | None, str]:
    agents = checkout / "AGENTS.md"
    if not agents.is_file():
        return None, None, "FAIL-derive (keine AGENTS.md)"
    modules = _public_modules(checkout)
    prompt = PROMPT % {
        "path": PROBE_PATH,
        "agents": agents.read_text(encoding="utf-8"),
        "modules": "\n".join(f"- {m}" for m in modules) or "- (keine erkannt)",
    }
    raw = ask_model_raw(prompt, providers)
    if raw is None:
        return None, None, "FAIL-derive"
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        answer = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        answer = None
    path, content = parse_answer(answer)
    if path is None:
        return None, None, "FAIL-derive (kein JSON path/content)"
    return path, content, ""


def probe_package(
    org_repo: str,
    workdir: Path,
    providers,
    *,
    push: bool,
    ci_timeout: int,
    today: dt.date,
) -> dict:
    org, repo = org_repo.split("/", 1)
    dest = workdir / repo
    if _run(
        ["gh", "repo", "clone", org_repo, str(dest), "--", "--depth", "1"], workdir, 120
    ).returncode:
        return {"result": "FAIL-push (clone)", "pr": None}
    path, content, err = derive(dest, providers)
    if err:
        return {"result": err, "pr": None}
    allowed = set(_public_modules(dest))
    if path != PROBE_PATH:
        return {"result": f"FAIL-unsafe (Pfad {path!r})", "pr": None}
    problems = validate_probe(content, allowed)
    if problems:
        return {"result": "FAIL-unsafe (" + "; ".join(problems[:3]) + ")", "pr": None}
    target = dest / PROBE_PATH
    if target.exists():
        return {"result": "FAIL-unsafe (Probe-Datei existiert schon)", "pr": None}
    target.parent.mkdir(exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")
    # Formatter zuerst — wie ein Pre-Commit-Hook beim Menschen; das Lint-Urteil
    # (ruff check, deckungsgleich mit _ci-pypi.yml) faellt danach ueber den Inhalt.
    if _run(["ruff", "format", PROBE_PATH], dest).returncode:
        return {"result": "FAIL-lokal (ruff format)", "pr": None}
    if _run(["ruff", "check", PROBE_PATH], dest).returncode:
        return {"result": "FAIL-lokal (ruff)", "pr": None}
    if _run(["make", "setup"], dest, 900).returncode:
        return {"result": "FAIL-lokal (make setup)", "pr": None}
    if _run(["make", "test"], dest, 900).returncode:
        return {"result": "FAIL-lokal (make test)", "pr": None}
    if not push:
        return {"result": "PASS-lokal", "pr": None}

    branch = probe_branch(today)
    steps = [
        ["git", "checkout", "-q", "-b", branch],
        ["git", "add", PROBE_PATH],
        [
            "git",
            "-c",
            "user.name=coldstart-probe",
            "-c",
            "user.email=noreply@iil.gmbh",
            "commit",
            "-q",
            "-m",
            f"test(coldstart-probe): Stufe-2-Probe {today} — wird nach CI-Urteil geschlossen (platform#3575 K3)",
        ],
        ["git", "push", "-q", "-u", "origin", branch],
    ]
    for cmd in steps:
        if _run(cmd, dest, 120).returncode:
            return {
                "result": f"FAIL-push ({cmd[0]} {cmd[1] if len(cmd) > 1 else ''})",
                "pr": None,
            }
    body = (
        "Automatische Stufe-2-Probe (platform#3575 K3, #2099): ein T1a-Modell hat aus AGENTS.md "
        f"die Datei `{PROBE_PATH}` abgeleitet; Grammatik per ast geprüft, lokal `make test` grün. "
        "Dieser PR wird nach dem CI-Urteil automatisch geschlossen und der Branch gelöscht — "
        "der Link ist der Beweis, nicht die Änderung.\n\n"
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
    )
    pr = _run(
        [
            "gh",
            "pr",
            "create",
            "--draft",
            "--base",
            "main",
            "--head",
            branch,
            "--title",
            f"[coldstart-probe] Stufe-2-Probe {today} (wird automatisch geschlossen)",
            "--body",
            body,
        ],
        dest,
        120,
    )
    if pr.returncode:
        return {"result": "FAIL-push (pr create)", "pr": None}
    url = pr.stdout.strip().splitlines()[-1]
    checks = _run(
        ["gh", "pr", "checks", url, "--watch", "--fail-fast"], dest, ci_timeout + 60
    )
    verdict = "PASS-ci" if checks.returncode == 0 else "FAIL-ci"
    _run(
        [
            "gh",
            "pr",
            "close",
            url,
            "--delete-branch",
            "--comment",
            f"Probe beendet: {verdict}. Automatisch geschlossen (platform#3575 K3).",
        ],
        dest,
        120,
    )
    return {"result": verdict, "pr": url}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("repos", nargs="+", help="org/repo je Paket")
    ap.add_argument(
        "--push",
        action="store_true",
        help="Branch + Draft-PR anlegen, CI abwarten, schließen",
    )
    ap.add_argument("--ci-timeout", type=int, default=1500)
    ap.add_argument("--workdir", type=Path, default=None)
    ap.add_argument("--today", type=dt.date.fromisoformat, default=None)
    args = ap.parse_args()
    today = args.today or dt.date.today()
    providers = providers_from_env()
    if not providers:
        print("FEHLER: CEREBRAS_API_KEY oder GROQ_API_KEY fehlt.", file=sys.stderr)
        return 2
    workdir = args.workdir or Path(tempfile.mkdtemp(prefix="coldstart-stufe2-"))
    results: dict[str, dict] = {}
    try:
        for org_repo in args.repos:
            print(f"== {org_repo} ==", file=sys.stderr)
            results[org_repo] = probe_package(
                org_repo,
                workdir,
                providers,
                push=args.push,
                ci_timeout=args.ci_timeout,
                today=today,
            )
            print(
                f"    -> {results[org_repo]['result']} {results[org_repo]['pr'] or ''}",
                file=sys.stderr,
            )
    finally:
        if args.workdir is None:
            shutil.rmtree(workdir, ignore_errors=True)
    passed = sum(1 for v in results.values() if v["result"].startswith("PASS"))
    print(
        f"== Cold-Start-Eval Stufe 2 ({'push' if args.push else 'lokal'}): {passed}/{len(results)} PASS =="
    )
    for name, v in sorted(results.items()):
        print(f"{name}: {v['result']}" + (f" {v['pr']}" if v["pr"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
