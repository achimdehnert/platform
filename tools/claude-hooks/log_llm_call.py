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

# SEC-5 (Issue #1198): kein stillschweigender Passwort-Fallback mehr. Der alte
# Default deckte sich zufällig mit dem lokalen docker-compose-Default
# (POSTGRES_PASSWORD:-change-me-in-production, mcp-hub/docker-compose.yml) —
# bleibt als EXPLIZITER Dev-Only-Opt-in erhalten (ALLOW_DEV_DB_FALLBACK=1),
# statt automatisch/leise verwendet zu werden. `None` heißt "DB-Write aus" und
# wird von _insert_rows/_query_* genauso fail-silent behandelt wie ein
# fehlendes psycopg (Hook-Contract: exit 0 immer, s. Docstring oben).
_DEV_FALLBACK_DB_URL = (
    "postgresql://orchestrator:change-me-in-production@127.0.0.1:15435/orchestrator_mcp"
)

# Host/Port/User/DB entsprechen mcp-hub/docker-compose.yml (Service `db`);
# nur das Passwort ist geheim und liegt als Datei unter ~/.secrets/ — nie im
# env-Block von settings.json, damit die URL nirgends im Klartext steht.
# Reihenfolge: Env > Passwort-Datei > Dev-Opt-in.
_DB_PASSWORD_FILE = Path.home() / ".secrets" / "orchestrator_mcp_db_password"
_DB_HOST_PORT_DB = "127.0.0.1:15435/orchestrator_mcp"
_DB_USER = "orchestrator"


def _resolve_db_url() -> str | None:
    url = os.environ.get("ORCHESTRATOR_DB_URL")
    if url:
        return url
    try:
        password = _DB_PASSWORD_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        password = ""
    if password:
        from urllib.parse import quote

        return f"postgresql://{_DB_USER}:{quote(password, safe='')}@{_DB_HOST_PORT_DB}"
    if os.environ.get("ALLOW_DEV_DB_FALLBACK") == "1":
        return _DEV_FALLBACK_DB_URL
    return None


DB_URL = _resolve_db_url()
STATE_DIR = Path.home() / ".claude" / "hooks" / "state"
LOG_FILE = Path.home() / ".claude" / "hooks" / "log_llm_call.log"

# Anthropic pricing per 1M tokens (USD). Source: Claude-API-Referenz (Skill
# `claude-api`, Modelltabelle Stand 2026-06-24) — Opus 4.6/4.7/4.8 kosten seit
# Opus 4.5 $5/$25, nicht mehr $15/$75 wie Opus 4/4.1.
# Cache pricing relative to input: write_5m=1.25x, write_1h=2x, read=0.1x.
PRICING_USD_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-fable-5-1": {"input": 10.0, "output": 50.0},
    "claude-fable-5": {"input": 10.0, "output": 50.0},
    "claude-mythos-5-1": {"input": 10.0, "output": 50.0},
    "claude-opus-5": {"input": 5.0, "output": 25.0},
    "claude-opus-4-8": {"input": 5.0, "output": 25.0},
    "claude-opus-4-7": {"input": 5.0, "output": 25.0},
    "claude-opus-4-6": {"input": 5.0, "output": 25.0},
    "claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "claude-opus-4": {"input": 15.0, "output": 75.0},
    "claude-sonnet-5": {"input": 2.0, "output": 10.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5-20251022": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}
DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def _normalize_model(model: str) -> str:
    # Claude Code hängt die Kontextvariante als Suffix an ("claude-fable-5[1m]");
    # die Preistabelle kennt nur den nackten Modellnamen.
    return model.split("[", 1)[0].strip()


# Once-per-session Tier-3 nudge thresholds (issue #305).
TIER3_MIN_TURNS = 8  # need enough signal before suggesting a switch
TIER3_CHEAP_RATIO = 0.70  # fraction of turns with cost < $0.10 = "routine"
TIER3_CHEAP_MAX = 0.10  # $/turn threshold for "cheap" classification


def _log(msg: str) -> None:
    try:
        with LOG_FILE.open("a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} {msg}\n")
    except Exception:
        pass


def _compute_cost(model: str, usage: dict) -> float:
    p = PRICING_USD_PER_MTOK.get(_normalize_model(model), DEFAULT_PRICING)
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
    p.write_text(
        json.dumps(
            {
                "logged_request_ids": keep,
                "tier3_nudged": state.get("tier3_nudged", False),
            }
        )
    )


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


def _insert_rows(rows: list[dict]) -> int | None:
    """INSERT rows into llm_calls.

    Returns the number of rows the transaction actually wrote — or ``None``,
    wenn der Schreibweg gar nicht gelaufen ist (keine DB-URL, kein psycopg,
    Verbindungs- oder SQL-Fehler).

    **Warum die Unterscheidung ``0`` vs. ``None`` traegt:** ``0`` heisst
    „committet, aber alles lief in ``ON CONFLICT DO NOTHING``" — die Zeilen
    liegen also bereits in der DB und sind fertig protokolliert. ``None`` heisst
    „nichts geschrieben, Ausgang unbekannt". Nur im zweiten Fall darf der
    Zustand nicht fortschreiben, sonst gingen Zeilen verloren. Bis 2026-09-02
    lieferten beide Faelle ``0``, und ``main`` behandelte sie gleich — mit der
    dort beschriebenen Dauerschleife als Folge.

    Direct psycopg connection (no subprocess fork — saves ~150ms/turn).
    Requires the venv-python shebang above to provide psycopg in sys.path.
    """
    if not rows:
        return 0
    if DB_URL is None:
        _log(
            "ORCHESTRATOR_DB_URL fehlt (und ALLOW_DEV_DB_FALLBACK != 1) — DB-Write übersprungen."
        )
        return None
    try:
        import psycopg  # noqa: PLC0415
    except ImportError:
        _log("psycopg unavailable — hook requires venv-python shebang")
        return None
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
        return None


def _query_session_total(session_id: str) -> float | None:
    """Tiny DB query for session-total in $. Direct psycopg, fail-silent."""
    if DB_URL is None:
        return None
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
    if DB_URL is None:
        return None
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
        _log(
            f"missing fields: transcript={bool(transcript_path)} session={bool(session_id)}"
        )
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
        cache_create_total = (u.get("cache_creation") or {}).get(
            "ephemeral_5m_input_tokens", 0
        ) + (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0)
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
                "routing_reason": f"claude_code Stop hook · branch={t['git_branch']}"[
                    :200
                ],
                "created_at": t.get("timestamp") or None,
            }
        )

    # Zustand fortschreiben, sobald die Transaktion COMMITTET hat — auch bei
    # `inserted == 0`.
    #
    # Gemessen am 2026-09-02 im eigenen Protokoll (`log_llm_call.log`, 47.056
    # Zeilen): 12.574 Ereignisse „insert returned 0 for N candidate rows", in
    # Summe 2.686.409 vergebliche INSERT-Roundtrips, Median N=166, Maximum
    # N=1246; allein in den letzten sieben Tagen 3.397 Ereignisse mit 827.303
    # Roundtrips. Ursache war diese Bedingung: liefen alle Kandidaten in
    # `ON CONFLICT DO NOTHING` (Zustandsdatei verloren, Sitzung fortgesetzt,
    # zweiter Hook-Lauf im Rennen), blieb `inserted` 0, der Zustand wurde NIE
    # gespeichert — und derselbe Stapel ging bei JEDEM weiteren Stop erneut
    # ueber die Leitung. Am 14,4-MB-Transkript gemessen: 4.902 ms je Stop
    # gegenueber 190 ms mit vollstaendigem Zustand (Faktor 26).
    #
    # `None` bleibt der Fall, in dem NICHT fortgeschrieben werden darf: dann ist
    # der Schreibweg gar nicht gelaufen (keine DB-URL, kein psycopg, Fehler) und
    # die Zeilen fehlen wirklich noch.
    inserted = _insert_rows(rows)
    if inserted is not None:
        state["logged_request_ids"].update(t["request_id"] for t in new)
        _save_state(session_id, state)
        _log(f"inserted {inserted}/{len(new)} rows for session {session_id[:8]}")
    else:
        _log(f"insert did not run for {len(new)} candidate rows — state unchanged")

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
            bits[-1] += f", {turn_ms / 1000:.1f}s"
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


def main_sicher() -> int:
    """`main()` unter dem Hook-Vertrag: Exit 0 immer, ausser bewusstes Blocken.

    Ein Melder darf einen Turn nie kippen. Bis 2026-09-02 lag um `main()`
    KEINES der sieben Stop-Hook-Module einen Auffangbogen — jede unerwartete
    Ausnahme (kaputte Zustandsdatei, unerwartete Transkript-Form, `psycopg`
    halb installiert) haette als Traceback mit Exit 1 den Hook-Vertrag
    verlassen.

    Bewusst KEIN geteiltes Hilfsmodul: der Auffangbogen ist genau der Pfad, der
    auch dann noch tragen muss, wenn die Verteilung der Hook-Kopien unvollstaendig
    ist (`tools/hook-dist-drift.sh`). Ein Import waere ein neuer Grund zu
    scheitern an der Stelle, die das Scheitern abfangen soll.

    Bewusstes Blocken bleibt unberuehrt: es laeuft ueber `{"decision": "block"}`
    auf stdout (bereits gedruckt, bevor irgendetwas werfen koennte) bzw. ueber
    `sys.exit(2)` — `SystemExit` ist keine `Exception` und wird hier nicht
    gefangen.
    """
    try:
        return main()
    except Exception as exc:  # noqa: BLE001 — Hook-Vertrag: nie blockieren
        print(f"log_llm_call: {type(exc).__name__}: {exc}"[:400], file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main_sicher())
