"""adr-review — minimal AI architecture review for ADR pull requests.

Non-blocking by default: posts a review comment + sets a score label.
Use --fail-under N to make CI red below a score (off by default — informing,
not enforcing; the ADR-199 lesson).

Env:
  GITHUB_TOKEN       (required) — PR read + comment/label write
  ANTHROPIC_API_KEY  (required) — the review model
  ADR_REVIEW_MODEL   (optional) — default 'claude-sonnet-4-6'
"""
from __future__ import annotations

import argparse
import os
import re
import sys

import requests

GH = "https://api.github.com"
MARKER = "<!-- adr-review -->"
# Default cost-conscious (ADR-201 spirit). Future: resolve via ADR-208 resolver.
MODEL = os.environ.get("ADR_REVIEW_MODEL", "claude-sonnet-4-6")

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


def review(files: list[dict], token: str) -> tuple[int, str]:
    import anthropic

    parts = []
    for f in files:
        parts.append(f"### {f['filename']}\n\n{fetch_text(f['raw_url'], token)}")
    user = "Geänderte ADR-Dateien:\n\n" + "\n\n---\n\n".join(parts)

    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL,
        max_tokens=1600,
        system=[{"type": "text", "text": CHECKLIST,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    m = re.search(r"SCORE:\s*(\d{1,2})", text)
    score = max(1, min(10, int(m.group(1)))) if m else 5
    return score, text


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
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("adr-review: ANTHROPIC_API_KEY fehlt — übersprungen.")
        return 0

    files = changed_adrs(a.repo, a.pr, token)
    if not files:
        print("adr-review: keine ADR-Dateien im PR — nichts zu tun.")
        return 0

    score, text = review(files, token)
    label = label_for(score)
    body = (f"## 🤖 ADR Review — Score {score}/10 (`{label}`)\n\n"
            f"{text}\n\n<sub>Modell: {MODEL} · {len(files)} ADR-Datei(en) · "
            f"informativ, nicht blockierend</sub>")

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
