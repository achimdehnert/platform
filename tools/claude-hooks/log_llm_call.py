#!/home/devuser/github/dev-hub/.venv/bin/python
"""Claude Code Stop hook — log every assistant turn into llm_calls.

Reads transcript_path from the Stop event, finds all assistant messages with
real (Anthropic-reported) usage, dedupes by requestId across runs of this
session via a small state file, and INSERTs one row per LLM API call into
the orchestrator's llm_calls table.

Token counts and cache tiers come straight from the transcript — these are
the same numbers Anthropic uses for billing, so cost is exact (no char/4
estimation).

Hook contract: exit 0 always so a logging failure never blocks Claude.

Shebang points at the dev-hub venv-python (has psycopg available). System
python3 lacks psycopg so the inline psycopg.connect calls would ImportError;
the hook degrades gracefully if even the venv lookup fails.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_URL = os.environ.get(
    "ORCHESTRATOR_DB_URL",
    "postgresql://orchestrator:change-me-in-production@127.0.0.1:15435/orchestrator_mcp",
)
STATE_DIR = Path.home() / ".claude" / "hooks" / "state"
LOG_FILE = Path.home() / ".claude" / "hooks" / "log_llm_call.log"

# Anthropic pricing per 1M tokens (USD). Source: anthropic.com/pricing 2026-05.
# Cache pricing relative to input: write_5m=1.25x, write_1h=2x, read=0.1x.
PRICING_USD_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5":          {"input": 3.0,  "output": 15.0},
    "claude-sonnet-4-5-20251022": {"input": 3.0,  "output": 15.0},
    "claude-sonnet-4-6":          {"input": 3.0,  "output": 15.0},
    "claude-sonnet-4":            {"input": 3.0,  "output": 15.0},
    "claude-haiku-4-5":           {"input": 1.0,  "output": 5.0},
    "claude-haiku-4-5-20251001":  {"input": 1.0,  "output": 5.0},
    "claude-opus-4":              {"input": 15.0, "output": 75.0},
    "claude-opus-4-1":            {"input": 15.0, "output": 75.0},
    "claude-opus-4-6":            {"input": 15.0, "output": 75.0},
    "claude-opus-4-7":            {"input": 15.0, "output": 75.0},
    "gpt-4o":                     {"input": 2.5,  "output": 10.0},
    "gpt-4o-mini":                {"input": 0.15, "output": 0.60},
}
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}

# Once-per-session Tier-3 nudge thresholds (issue #305).
TIER3_MIN_TURNS = 8       # need enough signal before suggesting a switch
TIER3_CHEAP_RATIO = 0.70  # fraction of turns with cost < $0.10 = "routine"
TIER3_CHEAP_MAX = 0.10    # $/turn threshold for "cheap" classification


def _log(msg: str) -> None:
    try:
        with LOG_FILE.open("a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")
    except Exception:
        pass


def _compute_cost(model: str, usage: dict) -> float:
    p = PRICING_USD_PER_MTOK.get(model, DEFAULT_PRICING)
    in_full = usage.get("input_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0
    cache_create = usage.get("cache_creation") or {}
    cache_5m = cache_create.get("ephemeral_5m_input_tokens") or 0
    cache_1h = cache_create.get("ephemeral_1h_input_tokens") or 0
    if not cache_5m and not cache_1h:
        cache_5m = usage.get("cache_creation_input_tokens") or 0
    out = usage.get("output_tokens") or 0
    cost = (
        in_full * p["input"]
        + cache_5m * p["input"] * 1.25
        + cache_1h * p["input"] * 2.0
        + cache_read * p["input"] * 0.1
        + out * p["output"]
    ) / 1_000_000.0
    return round(cost, 6)


def _total_tokens(usage: dict) -> int:
    cache_create = usage.get("cache_creation") or {}
    cache_5m = cache_create.get("ephemeral_5m_input_tokens") or 0
    cache_1h = cache_create.get("ephemeral_1h_input_tokens") or 0
    if not cache_5m and not cache_1h:
        legacy = usage.get("cache_creation_input_tokens") or 0
    else:
        legacy = cache_5m + cache_1h
    return (
        (usage.get("input_tokens") or 0)
        + legacy
        + (usage.get("cache_read_input_tokens") or 0)
        + (usage.get("output_tokens") or 0)
    )


def _state_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_") or "unknown"
    return STATE_DIR / f"{safe}.json"


def _load_state(session_id: str) -> dict:
    """Return session state dict: {logged_request_ids: set[str], tier3_nudged: bool}.

    Backward-compatible: if the state file holds a bare list (old format),
    treat it as logged_request_ids with tier3_nudged=False.
    """
    p = _state_path(session_id)
    if not p.exists():
        return {"logged_request_ids": set(), "tier3_nudged": False}
    try:
        raw = json.loads(p.read_text())
        if isinstance(raw, list):
            return {"logged_request_ids": set(raw), "tier3_nudged": False}
        return {
            "logged_request_ids": set(raw.get("logged_request_ids") or []),
            "tier3_nudged": bool(raw.get("tier3_nudged", False)),
        }
    except Exception:
        return {"logged_request_ids": set(), "tier3_nudged": False}


def _save_state(session_id: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    p = _state_path(session_id)
    keep = list(state["logged_request_ids"])[-2000:]
    p.write_text(json.dumps({
        "logged_request_ids": keep,
        "tier3_nudged": state.get("tier3_nudged", False),
    }))


def _collect_turns(transcript_path: str) -> list[dict]:
    """Return one dict per unique requestId in the transcript, in order.

    `duration_ms` is the wall-clock delta between the preceding transcript
    record (user message or tool result that triggered the call) and the
    assistant response. This is the closest proxy for inference latency
    that Claude Code transcripts expose — no `duration_ms` field is emitted
    by the SDK directly. Cap at 5 minutes to filter out idle-think gaps.
    """
    turns: list[dict] = []
    seen: set[str] = set()
    last_ts: str | None = None
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = rec.get("timestamp")
                if rec.get("type") != "assistant":
                    if ts:
                        last_ts = ts
                    continue
                rid = rec.get("requestId")
                if not rid or rid in seen:
                    if ts:
                        last_ts = ts
                    continue
                msg = rec.get("message") or {}
                usage = msg.get("usage") or {}
                if not usage:
                    if ts:
                        last_ts = ts
                    continue
                duration_ms = None
                if last_ts and ts:
                    try:
                        t1 = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                        t2 = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        delta = int((t2 - t1).total_seconds() * 1000)
                        if 0 < delta < 300_000:  # cap at 5 min — filter idle gaps
                            duration_ms = delta
                    except Exception:
                        pass
                seen.add(rid)
                turns.append(
                    {
                        "request_id": rid,
                        "model": msg.get("model") or "unknown",
                        "usage": usage,
                        "timestamp": ts,
                        "duration_ms": duration_ms,
                        "cwd": rec.get("cwd") or "",
                        "git_branch": rec.get("gitBranch") or "",
                        "session_id": rec.get("sessionId") or "",
                    }
                )
                if ts:
                    last_ts = ts
    except FileNotFoundError:
        _log(f"transcript not found: {transcript_path}")
    return turns


_INSERT_SQL = """
    INSERT INTO llm_calls
        (tenant_id, task_id, repo, source, call_type, request_id,
         model, prompt_tokens, completion_tokens, total_tokens,
         cost_usd, duration_ms, agent_role, complexity, routing_reason, error,
         created_at)
    VALUES
        (0, %(task_id)s, %(repo)s, %(source)s, 'chat', %(request_id)s,
         %(model)s, %(prompt_tokens)s, %(completion_tokens)s, %(total_tokens)s,
         %(cost_usd)s, %(duration_ms)s, 'claude_code', 'exact', %(routing_reason)s, false,
         COALESCE(%(created_at)s::timestamptz, NOW()))
    ON CONFLICT DO NOTHING
"""


def _insert_rows(rows: list[dict]) -> int:
    """INSERT rows into llm_calls. Returns number of rows actually inserted.

    Direct psycopg connection (no subprocess fork — saves ~150ms/turn).
    Requires the venv-python shebang above to provide psycopg in sys.path.
    """
    if not rows:
        return 0
    try:
        import psycopg  # noqa: PLC0415
    except ImportError:
        _log("psycopg unavailable — hook requires venv-python shebang")
        return 0
    try:
        with psycopg.connect(DB_URL, connect_timeout=5) as conn, conn.cursor() as cur:
            inserted = 0
            for r in rows:
                cur.execute(_INSERT_SQL, r)
                inserted += cur.rowcount
            conn.commit()
            return inserted
    except Exception as exc:
        _log(f"insert failed: {type(exc).__name__}: {exc!s:.200}")
        return 0


def _query_session_total(session_id: str) -> float | None:
    """Tiny DB query for session-total in $. Direct psycopg, fail-silent."""
    try:
        import psycopg  # noqa: PLC0415
    except ImportError:
        return None
    try:
        with psycopg.connect(DB_URL, connect_timeout=2) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(cost_usd),0)::float FROM llm_calls "
                "WHERE source='claude_code' AND task_id = %s",
                (f"cc-{session_id[:36]}",),
            )
            return float(cur.fetchone()[0])
    except Exception:
        return None


def _query_session_tier3_stats(session_id: str) -> tuple[int, float, float] | None:
    """Return (turn_count, cheap_ratio, median_cost) for this session, or None.

    cheap_ratio = fraction of turns with cost_usd < TIER3_CHEAP_MAX ($0.10).
    Uses PERCENTILE_CONT for median — available in all supported Postgres versions.
    """
    try:
        import psycopg  # noqa: PLC0415
    except ImportError:
        return None
    try:
        with psycopg.connect(DB_URL, connect_timeout=2) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)::int,
                    AVG(CASE WHEN cost_usd < %(cheap_max)s THEN 1.0 ELSE 0.0 END)::float,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cost_usd)::float
                FROM llm_calls
                WHERE source = 'claude_code' AND task_id = %(task_id)s
                """,
                {"task_id": f"cc-{session_id[:36]}", "cheap_max": TIER3_CHEAP_MAX},
            )
            row = cur.fetchone()
            if not row or not row[0]:
                return None
            return (int(row[0]), float(row[1] or 0.0), float(row[2] or 0.0))
    except Exception:
        return None


def _should_emit_tier3_nudge(
    model: str,
    state: dict,
    stats: tuple[int, float, float] | None,
) -> bool:
    """True iff the once-per-session Tier-3 nudge should fire now.

    Conditions (all must hold):
    - Model family is Opus
    - Session not yet nudged this session
    - >= TIER3_MIN_TURNS logged turns (enough signal)
    - >= TIER3_CHEAP_RATIO fraction of turns are cheap (routine proxy)
    """
    if state.get("tier3_nudged"):
        return False
    if "opus" not in model.lower():
        return False
    if stats is None:
        return False
    turn_count, cheap_ratio, _ = stats
    return turn_count >= TIER3_MIN_TURNS and cheap_ratio >= TIER3_CHEAP_RATIO


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except Exception as exc:
        _log(f"bad stdin: {exc!r}")
        return 0  # never block Stop

    transcript_path = event.get("transcript_path") or ""
    session_id = event.get("session_id") or ""
    if not transcript_path or not session_id:
        _log(f"missing fields: transcript={bool(transcript_path)} session={bool(session_id)}")
        return 0

    state = _load_state(session_id)
    already = state["logged_request_ids"]
    turns = _collect_turns(transcript_path)
    new = [t for t in turns if t["request_id"] not in already]
    if not new:
        return 0

    rows = []
    for t in new:
        u = t["usage"]
        cache_create_total = (
            (u.get("cache_creation") or {}).get("ephemeral_5m_input_tokens", 0)
            + (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
        )
        if cache_create_total == 0:
            cache_create_total = u.get("cache_creation_input_tokens") or 0
        prompt_tokens = (
            (u.get("input_tokens") or 0)
            + cache_create_total
            + (u.get("cache_read_input_tokens") or 0)
        )
        completion_tokens = u.get("output_tokens") or 0
        repo = (t["cwd"].rstrip("/").rsplit("/", 1)[-1] or "unknown")[:120]
        rows.append(
            {
                "task_id": f"cc-{session_id[:36]}",
                "repo": repo,
                "source": "claude_code",
                "request_id": t["request_id"][:120],
                "model": t["model"][:120],
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": _total_tokens(u),
                "cost_usd": _compute_cost(t["model"], u),
                "duration_ms": t.get("duration_ms"),
                "routing_reason": f"claude_code Stop hook · branch={t['git_branch']}"[:200],
                "created_at": t.get("timestamp") or None,
            }
        )

    inserted = _insert_rows(rows)
    if inserted > 0:
        state["logged_request_ids"].update(t["request_id"] for t in new)
        _save_state(session_id, state)
        _log(f"inserted {inserted}/{len(new)} rows for session {session_id[:8]}")
    else:
        _log(f"insert returned 0 for {len(new)} candidate rows")

    # ADR-201 Phase 1 — Stop-hook session summary to stderr
    # Claude Code surfaces hook stderr to the user.
    if rows:
        last = rows[-1]
        turn_cost = float(last["cost_usd"])
        turn_ms = last.get("duration_ms") or 0
        # short model name (e.g. claude-opus-4-7 → opus-4-7)
        m = last["model"]
        short_model = m.split("/", 1)[1] if "/" in m else m
        short_model = short_model.replace("claude-", "")
        # session-total via the same DB
        session_total = _query_session_total(session_id)
        bits = [f"turn: ${turn_cost:.4f} ({short_model}"]
        if turn_ms:
            bits[-1] += f", {turn_ms/1000:.1f}s"
        bits[-1] += ")"
        if session_total is not None and session_total > 0:
            bits.append(f"session: ${session_total:.2f}")
        # Over-spending: expensive turn on any tier → ack
        if turn_cost > 0.20:
            bits.append("🔥 burn rate hoch")
        sys.stderr.write(" │ ".join(bits) + "\n")

        # Once-per-session Tier-3 nudge — replaces per-turn flicker (issue #305).
        # Policy: mention once, do not nag (session-routing.md).
        stats = _query_session_tier3_stats(session_id) if "opus" in m.lower() else None
        if _should_emit_tier3_nudge(m, state, stats):
            assert stats is not None  # guaranteed by _should_emit_tier3_nudge
            turn_count, cheap_ratio, med_cost = stats
            pct = int(cheap_ratio * 100)
            sys.stderr.write(
                f"💡 Session auf Opus, aber {pct}% der {turn_count} Turns waren"
                f" Routine (Median ${med_cost:.4f}/Turn).\n"
                "   Tier-3 → /model sonnet ≈ 5× günstiger"
                " (session-routing.md). [einmalige Empfehlung]\n"
            )
            state["tier3_nudged"] = True
            _save_state(session_id, state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
