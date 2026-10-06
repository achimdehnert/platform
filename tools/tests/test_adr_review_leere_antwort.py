"""#642: eine leere Modellantwort darf keinen Score erzeugen.

Liegt unter tools/tests/, weil packages/adr-review/tests/ in keiner CI laeuft.
`requests` und `litellm` werden gestubbt — der Job installiert beide nicht, und
der Test braucht sie nicht.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packages" / "adr-review"))
sys.modules.setdefault("requests", types.ModuleType("requests"))

from adr_review import cli  # noqa: E402


def _litellm_mit(antworten: dict[str, str]):
    modul = types.ModuleType("litellm")

    def completion(model, **_):
        nachricht = types.SimpleNamespace(content=antworten[model])
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=nachricht)])

    modul.completion = completion
    return modul


def test_should_not_score_an_empty_answer(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", _litellm_mit({"tief": "  \n"}))
    monkeypatch.setattr(cli, "_secret", lambda model: "key")
    assert cli.run_model("tief", "", "prompt") is None


def test_should_fall_back_when_primary_answer_is_empty(monkeypatch):
    antworten = {"erst": "", "ersatz": "Befund A\nSCORE: 8"}
    monkeypatch.setitem(sys.modules, "litellm", _litellm_mit(antworten))
    monkeypatch.setattr(cli, "_secret", lambda model: "key")
    assert cli.run_model("erst", "ersatz", "prompt") == (
        8,
        "Befund A\nSCORE: 8",
        "ersatz",
    )


def test_should_keep_scoring_a_real_answer(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", _litellm_mit({"m": "ok\nSCORE: 9"}))
    monkeypatch.setattr(cli, "_secret", lambda model: "key")
    assert cli.run_model("m", "", "prompt") == (9, "ok\nSCORE: 9", "m")
