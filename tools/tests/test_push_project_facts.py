"""Tests für den project-facts-Verteiler (platform#1516).

Deckt die beiden Defekte ab, die den Workflow sieben Wochen rot laufen ließen:
der Direkt-Push auf ein durch ein Ruleset geschütztes `main` (409) und der
hartkodierte Org-Name bei org-migrierten Repos (307).
"""

from __future__ import annotations

import base64
import importlib.util
import pathlib
import sys

import pytest

_SRC = (
    pathlib.Path(__file__).resolve().parents[2]
    / ".github"
    / "scripts"
    / "push_project_facts.py"
)
_spec = importlib.util.spec_from_file_location("push_project_facts", _SRC)
ppf = importlib.util.module_from_spec(_spec)
sys.modules["push_project_facts"] = ppf
_spec.loader.exec_module(ppf)


def _b64(text):
    return base64.b64encode(text.encode()).decode()


class FakeApi:
    """Minimaler GitHub-Doppelgänger — protokolliert jeden Aufruf."""

    def __init__(
        self,
        *,
        datei=None,
        branch_da=False,
        slug="achimdehnert/learn-hub",
        offene_prs=None,
    ):
        self.datei = datei
        self.branch_da = branch_da
        self.slug = slug
        self.offene_prs = offene_prs or []
        self.aufrufe: list[tuple[str, str]] = []

    def __call__(self, url, method="GET", body=None):
        self.aufrufe.append((method, url))
        pfad = url.split("api.github.com")[-1]
        if method == "GET" and pfad.startswith("/repos/") and pfad.count("/") == 3:
            return {"full_name": self.slug, "default_branch": "main"}
        if "/contents/" in pfad and method == "GET":
            if self.datei is None:
                return None
            return {"encoding": "base64", "content": _b64(self.datei), "sha": "altsha"}
        if "/git/ref/heads/main" in pfad:
            return {"object": {"sha": "kopfsha"}}
        if "/git/ref/heads/chore" in pfad:
            return {"object": {"sha": "branchsha"}} if self.branch_da else None
        if pfad.startswith("/repos/") and "/pulls?" in pfad:
            return self.offene_prs
        if method == "POST" and pfad.endswith("/pulls"):
            return {"number": 42}
        return {}

    def methoden_auf(self, teil):
        return [m for m, u in self.aufrufe if teil in u]


@pytest.fixture(autouse=True)
def _reset_slug_cache():
    ppf._SLUGS.clear()
    yield
    ppf._SLUGS.clear()


# --- 409: kein Direkt-Push mehr auf main ------------------------------------


def test_should_never_write_directly_to_the_default_branch(monkeypatch):
    """Der Direkt-Push scheiterte am Ruleset — es darf keinen mehr geben."""
    api = FakeApi(datei="# alt")
    monkeypatch.setattr(ppf, "_req", api)
    ppf.gh_push_file("learn-hub", "project-facts.md", "# neu", "msg")
    puts = [u for m, u in api.aufrufe if m == "PUT" and "/contents/" in u]
    assert puts, "es muss geschrieben werden"
    # Der Ziel-Branch steckt im Body, nicht in der URL — geprüft wird, dass
    # ueberhaupt ein Branch angelegt/umgebogen wurde, bevor geschrieben wird.
    assert api.methoden_auf("/git/refs"), "ohne Branch kein PR-Weg"


def test_should_open_a_pull_request(monkeypatch):
    api = FakeApi(datei="# alt")
    monkeypatch.setattr(ppf, "_req", api)
    assert (
        ppf.gh_push_file("learn-hub", "project-facts.md", "# neu", "msg")
        == "PR #42 angelegt"
    )


def test_should_reuse_an_open_pull_request(monkeypatch):
    api = FakeApi(datei="# alt", offene_prs=[{"number": 7}])
    monkeypatch.setattr(ppf, "_req", api)
    assert (
        ppf.gh_push_file("learn-hub", "project-facts.md", "# neu", "msg")
        == "PR #7 aktualisiert"
    )
    assert "POST" not in [m for m, u in api.aufrufe if u.endswith("/pulls")]


def test_should_reset_a_leftover_branch_instead_of_diverging(monkeypatch):
    api = FakeApi(datei="# alt", branch_da=True)
    monkeypatch.setattr(ppf, "_req", api)
    ppf.gh_push_file("learn-hub", "project-facts.md", "# neu", "msg")
    assert "PATCH" in api.methoden_auf("/git/refs/heads/chore")


# --- Ruhe: nur das Datum ist kein Grund für einen PR -------------------------


def test_should_skip_when_only_the_generation_date_differs():
    alt = (
        "# Facts\n> Letzte Aktualisierung: 2026-06-01 — bei Änderungen: x\n\n## Meta\n"
    )
    neu = (
        "# Facts\n> Letzte Aktualisierung: 2026-07-28 — bei Änderungen: x\n\n## Meta\n"
    )
    assert ppf._ohne_datum(alt) == ppf._ohne_datum(neu)


def test_should_not_skip_on_real_content_change():
    alt = "# Facts\n> Letzte Aktualisierung: 2026-06-01 — x\n\n- Type: django\n"
    neu = "# Facts\n> Letzte Aktualisierung: 2026-06-01 — x\n\n- Type: fastapi\n"
    assert ppf._ohne_datum(alt) != ppf._ohne_datum(neu)


def test_should_return_unchanged_without_touching_any_branch(monkeypatch):
    inhalt = "# Facts\n> Letzte Aktualisierung: 2026-06-01 — x\n\n- Type: django\n"
    neu = inhalt.replace("2026-06-01", "2026-07-28")
    api = FakeApi(datei=inhalt)
    monkeypatch.setattr(ppf, "_req", api)
    assert (
        ppf.gh_push_file("learn-hub", "project-facts.md", neu, "msg") == "unverändert"
    )
    assert not api.methoden_auf("/git/refs"), "kein Branch, kein PR, keine Unruhe"


# --- 307: der Org-Name ist eine Voreinstellung, keine Wahrheit ---------------


def test_should_follow_a_repo_that_moved_to_another_org(monkeypatch):
    api = FakeApi(datei="# alt", slug="iilgmbh/risk-hub")
    monkeypatch.setattr(ppf, "_req", api)
    ppf.gh_push_file("risk-hub", "project-facts.md", "# neu", "msg")
    schreibend = [u for m, u in api.aufrufe if m in ("PUT", "POST", "PATCH")]
    assert schreibend, "es muss geschrieben werden"
    assert all("iilgmbh/risk-hub" in u for u in schreibend), (
        "kein Schreibzugriff darf auf den alten Org-Namen gehen (HTTP 307)"
    )


def test_should_cache_the_resolved_slug(monkeypatch):
    api = FakeApi(datei="# alt", slug="iilgmbh/risk-hub")
    monkeypatch.setattr(ppf, "_req", api)
    assert ppf.gh_slug("risk-hub") == "iilgmbh/risk-hub"
    vorher = len(api.aufrufe)
    assert ppf.gh_slug("risk-hub") == "iilgmbh/risk-hub"
    assert len(api.aufrufe) == vorher, "zweiter Aufruf darf nicht erneut fragen"


def test_should_fall_back_to_configured_org_when_repo_unknown(monkeypatch):
    def leer(url, method="GET", body=None):
        return None

    monkeypatch.setattr(ppf, "_req", leer)
    assert ppf.gh_slug("gibtsnicht") == f"{ppf.ORG}/gibtsnicht"


# --- Unerreichbare Repos faerben den Lauf nicht rot (platform#1856) ---------
#
# Drei Fremd-Org-Repos, die der Token nicht sieht, liessen den Cron seit dem
# 15.06. taeglich rot laufen, obwohl 21 Repos korrekt bearbeitet wurden. Ein
# dauerhaft roter Melder meldet nichts mehr — eine Steigerung von 3 auf 10
# waere niemandem aufgefallen.


def test_should_raise_repo_unerreichbar_when_the_head_is_not_readable(monkeypatch):
    def kein_kopf(url, method="GET", body=None):
        pfad = url.split("api.github.com")[-1]
        if pfad.startswith("/repos/") and pfad.count("/") == 3:
            return {"full_name": "ttz-lif/ttz-hub", "default_branch": "main"}
        if "/git/ref/heads/" in pfad:
            return None
        if "/contents/" in pfad:
            return None
        return {}

    monkeypatch.setattr(ppf, "_req", kein_kopf)
    with pytest.raises(ppf.RepoUnerreichbar):
        ppf.gh_push_file("ttz-hub", "project-facts.md", "# neu", "msg")


def test_should_exit_zero_when_the_only_failures_are_unreachable_repos(
    monkeypatch, capsys
):
    monkeypatch.setattr(ppf, "load_registry", lambda: {"a": {}, "b": {}})

    def prozess(repo, reg, dry_run):
        if repo == "b":
            raise ppf.RepoUnerreichbar("Kopf von 'main' nicht lesbar")
        return f"✅ {repo}: PR #1 angelegt"

    monkeypatch.setattr(ppf, "process_repo", prozess)
    monkeypatch.setattr(sys, "argv", ["push_project_facts.py"])
    monkeypatch.setattr(ppf, "TOKEN", "x")

    ppf.main()  # darf NICHT SystemExit werfen

    ausgabe = capsys.readouterr().out
    assert "1 unerreichbar" in ausgabe
    assert "🚫 b" in ausgabe, "der Name muss fallen, eine Zahl allein faellt nicht auf"


def test_should_still_exit_one_on_a_real_failure(monkeypatch):
    monkeypatch.setattr(ppf, "load_registry", lambda: {"a": {}, "b": {}})

    def prozess(repo, reg, dry_run):
        if repo == "b":
            raise ppf.ApiFehler("422 irgendwas kaputt")
        return f"✅ {repo}: PR #1 angelegt"

    monkeypatch.setattr(ppf, "process_repo", prozess)
    monkeypatch.setattr(sys, "argv", ["push_project_facts.py"])
    monkeypatch.setattr(ppf, "TOKEN", "x")

    with pytest.raises(SystemExit) as exc:
        ppf.main()
    assert exc.value.code == 1


# ── Archivierte Repos (platform#1953) ─────────────────────────────────────────


def test_should_skip_archived_repos_from_the_registry():
    """Ein archiviertes Repo ist auf GitHub read-only und antwortet auf jeden
    Schreibversuch mit HTTP 403.

    Realfall wedding-hub (archiviert 2026-08-11): der echte Lauf am 2026-08-13
    erledigte 23 Repos sauber — 8 PRs, davon erstmals frist-hub/meiki-hub/ttz-hub —
    und endete trotzdem ROT, weil das 24. Repo nicht mehr beschreibbar war. Ein
    Melder, der wegen eines bewusst stillgelegten Repos rot steht, wird binnen
    Wochen überlesen.
    """
    quelle = _SRC.read_text(encoding="utf-8")
    assert 'and not (cfg or {}).get("archived")' in quelle


def test_should_treat_github_archived_403_as_skip_not_failure():
    """Zweite Sicherung: die Registry kann der Stilllegung nachhinken. GitHubs
    eigene Antwort ist die verlässlichere Quelle — sie darf den Lauf nicht rot färben."""
    quelle = _SRC.read_text(encoding="utf-8")
    assert '"was archived" in str(exc)' in quelle
    # Nicht stillschweigend überspringen: der Fall muss benannt in der Ausgabe stehen.
    assert "Archiviert (read-only, bewusst uebersprungen):" in quelle
