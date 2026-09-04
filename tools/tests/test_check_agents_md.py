"""Tests für tools/check_agents_md.py (Schema pkg-agents-v1, #2075 K2)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_agents_md import check_text  # noqa: E402

VALID = """# iil-beispielfw — Agent-Kontext

> Schema: pkg-agents-v1

## Zweck

Tut Dinge.

## Setup & Test (Einstiegskommando)

```bash
make setup && make test
```

## Public API

- beispielfw.core

## Architektur-Constraints

- stdlib only

## Release

- publish.yml (OIDC)
"""


def test_should_accept_conforming_file():
    assert check_text(VALID) == []


def test_should_flag_missing_sections_and_marker():
    problems = check_text("# titel\n\nnur text\n")
    assert any("Schema-Marker" in p for p in problems)
    assert sum("Pflicht-Sektion" in p for p in problems) == 5


def test_should_flag_missing_h1_on_first_line():
    problems = check_text("kein titel\n" + VALID)
    assert any("H1-Titel" in p for p in problems)


def test_should_flag_multiline_entry_command():
    broken = VALID.replace("make setup && make test\n", "make setup\nmake test\n")
    problems = check_text(broken)
    assert any("GENAU 1 Zeile" in p for p in problems)


def test_should_flag_missing_bash_fence():
    broken = VALID.replace("```bash\nmake setup && make test\n```", "kein fence")
    problems = check_text(broken)
    assert any("bash-Fence" in p for p in problems)
