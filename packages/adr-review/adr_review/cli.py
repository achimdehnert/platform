"""adr-review — minimal AI architecture review for ADR pull requests.

Flatrate-only: routes via litellm to Cerebras/Groq (platform llm-routing
policy). NO Anthropic, no ANTHROPIC_API_KEY.

Non-blocking by default: posts a review comment + sets a score label.
Use --fail-under N to make CI red below a score (off by default — informing,
not enforcing; the ADR-199 lesson).

Env:
  GITHUB_TOKEN        (required) — PR read + comment/label write
  CEREBRAS_API_KEY    — for cerebras/* models   (one LLM key required)
  GROQ_API_KEY        — for groq/* models       (used for fallback)
  ADR_REVIEW_MODEL    (optional) default 'cerebras/qwen-3-235b-a22b-instruct-2507'
  ADR_REVIEW_FALLBACK (optional) default 'groq/llama-3.3-70b-versatile'
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import requests

GH = "https://api.github.com"
MARKER = "<!-- adr-review -->"

# Tier-1a (policy: user-visible prose), Flatrate Cerebras/Groq — kein Anthropic.
PRIMARY = os.environ.get("ADR_REVIEW_MODEL",
                         "cerebras/qwen-3-235b-a22b-instruct-2507")
FALLBACK = os.environ.get("ADR_REVIEW_FALLBACK",
                          "groq/llama-3.3-70b-versatile").strip()
_SECRET_DIRS = [Path.home() / "shared" / "secrets-inbox",
                Path.home() / ".secrets"]

CHECKLIST = """Du bist ADR-Architektur-Reviewer für die iil/achimdehnert-Plattform.
Bewerte den/die geänderten ADR(s) gegen:
- MADR-Struktur: Kontext/Problem, Entscheidung, Konsequenzen, Alternativen.
- Wird eine echte Architekturentscheidung getroffen (nicht bloße Ergänzung)?
- Trade-offs explizit & für künftige Herausforderer nachvollziehbar?
- Reversibilität, Blast-Radius, Daten-/Sicherheits-/Lizenz-Berührung benannt?
- Selbstwidersprüche zwischen Decision und Risiken?
- Status/Frontmatter konsistent (proposed/accepted/superseded).

Antworte AUF DEUTSCH, knapp, als Advocatus Diabolus. Format EXAKT:
Erste Zeile: `SCORE: <ganzzahl 1-10>`
Dann `---`
Dann Markdown: **Verdikt** (1 Satz), **Stärken** (max 3 Bullets),
**Schwächen/Risiken** (max 5 Bullets), **Konkrete Nachbesserung** (max 3)."""


def is_adr_file(path: str) -> bool:
    """Mirror der adr-review.yml Trigger-Pfade."""
    base = path.rsplit("/", 1)[-1]
    return (
        path.startswith("docs/adr/")
        or path.startswith("adr/")
        or bool(re.match(r"ADR-.*\.md$", base))
        or (path.startswith("concepts/") and path.endswith(".md"))
    )


def _secret(model: str) -> str | None:
    """litellm-Modellstring → API-Key (env ODER ~/shared/secrets-inbox/, wie print_agent)."""
    m = model.lower()
    name = ("cerebras_api_key" if m.startswith("cerebras/")
            else "groq_api_key" if m.startswith("groq/")
            else "mistral_api_key" if m.startswith("mistral/")
            else "openai_api_key" if m.startswith(("openai/", "gpt-"))
            else None)
    if not name:
        return None
    val = os.environ.get(name.upper())
    if val:
        return val
    for d in _SECRET_DIRS:
        p = d / name
        if p.exists():
            return p.read_text().strip()
    return None


def _gh(method: str, url: str, token: str, **kw):
    h = {"Authorization": f"Bearer {token}",
         "Accept": "application/vnd.github+json"}
    r = requests.request(method, url, headers=h, timeout=30, **kw)
    r.raise_for_status()
    return r


def changed_adrs(repo: str, pr: int, token: str) -> list[dict]:
    out, page = [], 1
    while True:
        r = _gh("GET", f"{GH}/repos/{repo}/pulls/{pr}/files"
                f"?per_page=100&page={page}", token)
        batch = r.json()
        if not batch:
            break
        out += [f for f in batch if is_adr_file(f["filename"])
                and f["status"] != "removed"]
        if len(batch) < 100:
            break
        page += 1
    return out


def fetch_text(raw_url: str, token: str) -> str:
    try:
        return _gh("GET", raw_url, token).text
    except Exception as e:  # noqa: BLE001
        return f"(konnte Inhalt nicht laden: {e})"


def _complete(model: str, system: str, user: str) -> str | None:
    """Ein litellm-Versuch; None bei fehlendem Key oder Fehler."""
    key = _secret(model)
    if not key:
        print(f"adr-review: kein Key für {model} — übersprungen")
        return None
    try:
        import litellm
        resp = litellm.completion(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            max_tokens=1600,
            temperature=0.2,
            api_key=key,
            timeout=60,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:  # noqa: BLE001
        print(f"adr-review: {model} fehlgeschlagen: {e}")
        return None


def review(files: list[dict], token: str) -> tuple[int, str] | None:
    parts = [f"### {f['filename']}\n\n{fetch_text(f['raw_url'], token)}"
             for f in files]
    user = "Geänderte ADR-Dateien:\n\n" + "\n\n---\n\n".join(parts)

    text = _complete(PRIMARY, CHECKLIST, user)
    used = PRIMARY
    if text is None and FALLBACK:
        text = _complete(FALLBACK, CHECKLIST, user)
        used = FALLBACK
    if text is None:
        return None
    m = re.search(r"SCORE:\s*(\d{1,2})", text)
    score = max(1, min(10, int(m.group(1)))) if m else 5
    return score, f"{text}\n\n<sub>via {used}</sub>"


def label_for(score: int) -> str:
    if score >= 7:
        return "adr-review-passed"
    if score >= 5:
        return "adr-review-concerns"
    return "adr-review-failed"


def upsert_comment(repo: str, pr: int, body: str, token: str) -> None:
    body = f"{MARKER}\n{body}"
    existing = _gh("GET", f"{GH}/repos/{repo}/issues/{pr}/comments?per_page=100",
                   token).json()
    for c in existing:
        if MARKER in (c.get("body") or ""):
            _gh("PATCH", f"{GH}/repos/{repo}/issues/comments/{c['id']}",
                token, json={"body": body})
            return
    _gh("POST", f"{GH}/repos/{repo}/issues/{pr}/comments", token,
        json={"body": body})


def set_label(repo: str, pr: int, label: str, token: str) -> None:
    for stale in ("adr-review-passed", "adr-review-concerns",
                  "adr-review-failed"):
        if stale != label:
            try:
                _gh("DELETE",
                    f"{GH}/repos/{repo}/issues/{pr}/labels/{stale}", token)
            except Exception:  # noqa: BLE001
                pass
    _gh("POST", f"{GH}/repos/{repo}/issues/{pr}/labels", token,
        json={"labels": [label]})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="adr-review")
    ap.add_argument("--pr", type=int, required=True)
    ap.add_argument("--repo", required=True, help="owner/name")
    ap.add_argument("--fail-under", type=int, default=0,
                    help="Exit 1 wenn Score < N (default 0 = nie blockieren)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("adr-review: GITHUB_TOKEN fehlt — übersprungen.")
        return 0
    if not (_secret(PRIMARY) or (FALLBACK and _secret(FALLBACK))):
        print("adr-review: kein LLM-Key (CEREBRAS_API_KEY/GROQ_API_KEY) "
              "— übersprungen.")
        return 0

    files = changed_adrs(a.repo, a.pr, token)
    if not files:
        print("adr-review: keine ADR-Dateien im PR — nichts zu tun.")
        return 0

    res = review(files, token)
    if res is None:
        print("adr-review: Review nicht möglich (LLM) — übersprungen.")
        return 0
    score, text = res
    label = label_for(score)
    body = (f"## 🤖 ADR Review — Score {score}/10 (`{label}`)\n\n"
            f"{text}\n\n<sub>{len(files)} ADR-Datei(en) · Flatrate "
            f"(Cerebras/Groq) · informativ, nicht blockierend</sub>")

    if a.dry_run:
        print(body)
        return 0

    upsert_comment(a.repo, a.pr, body, token)
    try:
        set_label(a.repo, a.pr, label, token)
    except Exception as e:  # noqa: BLE001
        print(f"adr-review: Label konnte nicht gesetzt werden: {e}")

    print(f"adr-review: Score {score} ({label}) gepostet.")
    if a.fail_under and score < a.fail_under:
        print(f"adr-review: Score {score} < --fail-under {a.fail_under} → exit 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
