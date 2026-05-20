"""feedback.iil.pet — Klickdummy Co-Creation-Loop Pfad A Endpoint.

POST /v1/issues  — Widget submittet hier, Service erzeugt GitHub-Issue.

Architektur (per platform:ADR-214 §E2):
  1. Origin-Header → Repo-Mapping (Konfig)
  2. PII-Filter (Heuristik) → payload_redacted-Flag bei Match
  3. Rate-Limit pro Origin
  4. GitHub API (Bot-PAT in Secret) → Issue create mit Label klickdummy-feedback
  5. Audit-Log (JSON-Lines)
  6. Response: { issue_url, ok }

Skelett — Deployment via Traefik (platform:ADR-212) auf feedback.iil.pet.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

log = logging.getLogger("feedback-bridge")
app = FastAPI(title="klickdummy-feedback-bridge", version="0.1.0")

# --- Config -----------------------------------------------------------------

# Origin → GitHub-Repo (owner/repo) Mapping. Erweitern pro ADR-214 §Adoption.
REPO_MAP: dict[str, str] = json.loads(os.environ.get("REPO_MAP_JSON", "{}"))
# Default-Mapping bei leerer ENV — wird in prod via Secret/ConfigMap überschrieben:
REPO_MAP = REPO_MAP or {
    "https://klickdummy.meiki-lra.iil.pet": "meiki-lra/meiki-hub",
    "https://klickdummy.writing.iil.pet":   "achimdehnert/writing-hub",
    "https://klickdummy.risk.iil.pet":      "achimdehnert/risk-hub",
}
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
RATE_LIMIT_PER_HOUR = int(os.environ.get("RATE_LIMIT_PER_HOUR", "20"))
AUDIT_LOG_PATH = Path(os.environ.get("AUDIT_LOG_PATH", "/var/log/feedback-bridge/audit.jsonl"))

# --- PII-Filter (Heuristik) -------------------------------------------------

PII_PATTERNS = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<email>"),
    (re.compile(r"\b\+?\d[\d\s\-/().]{7,}\d\b"), "<phone>"),
    (re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b"), "<iban>"),
]

def _redact(text: str) -> tuple[str, bool]:
    """Returns (redacted_text, was_redacted)."""
    redacted = False
    for pat, repl in PII_PATTERNS:
        if pat.search(text):
            text = pat.sub(repl, text)
            redacted = True
    return text, redacted

# --- Rate-Limit (in-memory, simpel) -----------------------------------------

_rate_state: dict[str, list[float]] = {}

def _rate_check(origin: str) -> bool:
    """True if within budget, False if exceeded."""
    now = dt.datetime.now().timestamp()
    window = 3600
    bucket = [t for t in _rate_state.get(origin, []) if now - t < window]
    if len(bucket) >= RATE_LIMIT_PER_HOUR:
        return False
    bucket.append(now)
    _rate_state[origin] = bucket
    return True

# --- Models -----------------------------------------------------------------

class FeedbackRequest(BaseModel):
    payload: dict[str, Any]
    markdown: str = Field(..., min_length=1, max_length=64_000)

class FeedbackResponse(BaseModel):
    ok: bool
    issue_url: str | None = None
    payload_redacted: bool = False
    note: str | None = None

# --- Endpoints --------------------------------------------------------------

@app.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}

@app.post("/v1/issues", response_model=FeedbackResponse)
async def create_issue(
    body: FeedbackRequest,
    request: Request,
    origin: Annotated[str | None, Header(alias="Origin")] = None,
) -> FeedbackResponse:
    # 1. Origin → Repo
    if not origin or origin not in REPO_MAP:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "origin not in allowlist")
    repo = REPO_MAP[origin]

    # 2. Rate-Limit
    if not _rate_check(origin):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"rate limit {RATE_LIMIT_PER_HOUR}/h exceeded for origin")

    # 3. PII-Filter
    redacted_md, was_redacted = _redact(body.markdown)
    title_base = (body.payload.get("category", "feedback")
                  + " · " + (body.payload.get("screen") or "n/a"))
    title = f"[Klickdummy-Feedback] {title_base}"

    # 4. GitHub Issue create
    if not GITHUB_TOKEN:
        # Dev-Mode: log only
        log.warning("GITHUB_TOKEN missing — dev-mode (no issue created)")
        return FeedbackResponse(ok=True, issue_url=None, payload_redacted=was_redacted,
                                note="dev-mode (no GITHUB_TOKEN)")
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            f"https://api.github.com/repos/{repo}/issues",
            headers={"Authorization": f"Bearer {GITHUB_TOKEN}",
                     "Accept": "application/vnd.github+json"},
            json={"title": title, "body": redacted_md,
                  "labels": ["klickdummy-feedback"]},
        )
    if r.status_code >= 300:
        log.error("github create failed: %s %s", r.status_code, r.text[:200])
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "github issue create failed")
    issue = r.json()

    # 5. Audit-Log
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": dt.datetime.utcnow().isoformat() + "Z",
                "origin": origin,
                "repo": repo,
                "issue_number": issue.get("number"),
                "payload_redacted": was_redacted,
                "screen": body.payload.get("screen"),
                "category": body.payload.get("category"),
                "spec_id": body.payload.get("spec_id"),
            }) + "\n")
    except OSError as e:
        log.warning("audit log write failed: %s", e)

    return FeedbackResponse(ok=True, issue_url=issue["html_url"],
                            payload_redacted=was_redacted)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
