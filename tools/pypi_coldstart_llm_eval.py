#!/usr/bin/env python3
"""T1a-LLM-Cold-Start-Eval der PyPI-Fleet (#2075 K2, ADR-266).

Misst das K2-Kriterium direkt statt über Proxies: Kann ein T1a-Modell
(Cerebras vor Groq, `llm-routing.md`) NUR aus AGENTS.md + Datei-Listing eines frischen
Checkouts den korrekten Einstieg ableiten — und laufen die abgeleiteten
Kommandos grün?

Ablauf je Paket:
  1. AGENTS.md + Top-Level-Listing an das Modell; erwartet JSON
     {"setup_cmd": ..., "test_cmd": ...}.
  2. SICHERHEIT (Lotsen-Charta: Modell-Output ist Datenlage, kein Befehl):
     Kommandos werden NUR ausgeführt, wenn sie exakt dem Muster
     `make <target>` (einzeln oder &&-Kette) entsprechen — alles andere
     zählt als FAIL und wird nie ausgeführt.
  3. Ausführung im Checkout (frisches .venv), Timeout je Schritt.

Ergebnis je Paket: PASS | FAIL-derive | FAIL-unsafe | FAIL-run.
V1-Scope bewusst ohne Mini-Change-durch-CI (separat getrackt, #2075).

    CEREBRAS_API_KEY=... [GROQ_API_KEY=...] python3 tools/pypi_coldstart_llm_eval.py <checkout> [...]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

# T1a gem. policies/llm-routing.md: Cerebras hat Vorrang (schneller, billiger),
# Groq ist Fallback — beide fuehren gpt-oss-120b als T1a-Slot. Achtung Falle 1
# der Policy: die Cerebras-ID heisst `gpt-oss-120b`, die Groq-ID
# `openai/gpt-oss-120b`. Ein Provider mit 401/Netzfehler faellt auf den
# naechsten durch; erst wenn alle scheitern, zaehlt das Paket als FAIL-derive.
PROVIDERS = (
    (
        "cerebras",
        "https://api.cerebras.ai/v1/chat/completions",
        "gpt-oss-120b",
        "CEREBRAS_API_KEY",
    ),
    (
        "groq",
        "https://api.groq.com/openai/v1/chat/completions",
        "openai/gpt-oss-120b",
        "GROQ_API_KEY",
    ),
)
MODEL_OVERRIDE: str | None = None
SAFE_CMD = re.compile(r"^make [a-z][a-z0-9_-]*( && make [a-z][a-z0-9_-]*)*$")

PROMPT = """Du bist ein Agent, der ein dir unbekanntes Python-Paket in einem \
frischen Checkout aufsetzen soll. Unten die AGENTS.md des Pakets und das \
Datei-Listing des Wurzelverzeichnisses.

Antworte NUR mit einem JSON-Objekt, ohne Markdown, exakt in dieser Form:
{"setup_cmd": "<ein Shell-Kommando>", "test_cmd": "<ein Shell-Kommando>"}

=== AGENTS.md ===
%s

=== Datei-Listing (Wurzel) ===
%s
"""


def providers_from_env() -> list[tuple[str, str, str, str]]:
    """(name, url, model, key) je Provider mit gesetztem Key, in Policy-Reihenfolge."""
    out = []
    for name, url, model, env in PROVIDERS:
        key = os.environ.get(env, "").strip()
        if key:
            out.append((name, url, MODEL_OVERRIDE or model, key))
    return out


def _ask_one(url: str, model: str, key: str, prompt: str) -> str | None:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            # Cloudflare vor Groq blockt den Default-UA "Python-urllib/3.x"
            # mit 403 (gemessen 2026-08-19) — curl mit identischem Key ging.
            "User-Agent": "iil-pypi-fleet-coldstart-eval/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def ask_model_raw(
    prompt: str, providers: list[tuple[str, str, str, str]]
) -> str | None:
    """Roher Modelltext vom ersten Provider, der antwortet — None, wenn alle scheitern."""
    for name, url, model, key in providers:
        try:
            return _ask_one(url, model, key, prompt)
        except Exception as exc:  # noqa: BLE001 — naechster Provider, zuletzt None
            print(f"    API-Fehler ({name}/{model}): {exc}", file=sys.stderr)
    return None


def ask_model(
    agents_md: str, listing: str, providers: list[tuple[str, str, str, str]]
) -> dict | None:
    content = ask_model_raw(PROMPT % (agents_md, listing), providers)
    if content is None:
        return None
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def is_safe(cmd: str) -> bool:
    """Nur make-Target-Ketten sind ausführbar — Modell-Output ist kein Befehl."""
    return bool(SAFE_CMD.fullmatch(cmd.strip()))


def run_in(checkout: Path, cmd: str, timeout: int = 300) -> bool:
    proc = subprocess.run(
        ["bash", "-c", cmd],
        cwd=checkout,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode == 0


def eval_package(
    checkout: Path, providers: list[tuple[str, str, str, str]] | None = None
) -> str:
    agents = checkout / "AGENTS.md"
    if not agents.is_file():
        return "FAIL-derive (keine AGENTS.md)"
    listing = "\n".join(
        sorted(p.name for p in checkout.iterdir() if not p.name.startswith("."))
    )
    providers = providers_from_env() if providers is None else providers
    if not providers:
        return "FAIL-derive (kein Provider-Key: CEREBRAS_API_KEY/GROQ_API_KEY)"
    answer = ask_model(agents.read_text(encoding="utf-8"), listing, providers)
    if not answer or "setup_cmd" not in answer or "test_cmd" not in answer:
        return "FAIL-derive"
    setup, test = str(answer["setup_cmd"]), str(answer["test_cmd"])
    print(f"    abgeleitet: setup={setup!r} test={test!r}")
    if not (is_safe(setup) and is_safe(test)):
        return f"FAIL-unsafe (nicht ausgeführt: {setup!r} / {test!r})"
    try:
        subprocess.run(["rm", "-rf", str(checkout / ".venv")], check=False)
        if not run_in(checkout, setup):
            return "FAIL-run (setup)"
        if not run_in(checkout, test):
            return "FAIL-run (test)"
    except subprocess.TimeoutExpired:
        return "FAIL-run (timeout)"
    return "PASS"


def main() -> int:
    global MODEL_OVERRIDE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("checkouts", nargs="+", type=Path)
    ap.add_argument(
        "--model", default=None, help="Chat-Modell fuer alle Provider erzwingen"
    )
    args = ap.parse_args()
    if args.model:
        MODEL_OVERRIDE = args.model
    providers = providers_from_env()
    if not providers:
        print("FEHLER: CEREBRAS_API_KEY oder GROQ_API_KEY fehlt.", file=sys.stderr)
        return 2
    print(
        "Provider: " + ", ".join(f"{n}/{m}" for n, _, m, _ in providers),
        file=sys.stderr,
    )
    results: dict[str, str] = {}
    for co in args.checkouts:
        print(f"== {co.name} ==")
        results[co.name] = eval_package(co, providers)
        print(f"    -> {results[co.name]}")
    passed = sum(1 for v in results.values() if v == "PASS")
    print(f"\n== T1a-Cold-Start-Eval: {passed}/{len(results)} PASS ==")
    for name, v in sorted(results.items()):
        print(f"{name}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
