"""
Session Memory Skill — AGENT_MEMORY.md lesen und schreiben.

Kritische Design-Entscheidungen (ADR-112 Blocker B1 + B3 fixed):
- Atomares Write (tempfile + os.replace) — kein partieller Schreibzustand
- fcntl.flock() Exclusive Lock — Race Condition verhindert
- JSON-Blöcke in Markdown — strukturiert + parserbar
- Git-Commit nach Write mit explizitem user.email (B3 fixed)
- Memory-Pfad in mcp-hub, nicht platform (H2 fixed)
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .base import GateLevel, Skill, SkillResult
from .memory_schema import EntryType, MemoryEntry, MemoryStore

log = logging.getLogger(__name__)

MEMORY_FILE = Path("AGENT_MEMORY.md")
LOCK_FILE   = Path(".agent_memory.lock")

_GIT_AUTHOR_NAME  = "Agent Team"
_GIT_AUTHOR_EMAIL = "agent@iilgmbh.com"


# ─── I/O Helpers ──────────────────────────────────────────────────────────────

def _read_store(path: Path = MEMORY_FILE) -> MemoryStore:
    """AGENT_MEMORY.md lesen und in MemoryStore deserialisieren."""
    if not path.exists():
        log.info("AGENT_MEMORY.md nicht gefunden — erstelle leeren Store")
        return MemoryStore()

    content = path.read_text(encoding="utf-8")
    entries: list[MemoryEntry] = []
    meta: dict = {}
    in_json_block = False
    json_lines: list[str] = []

    for line in content.splitlines():
        if line.strip() == "```json":
            in_json_block = True
            json_lines = []
        elif line.strip() == "```" and in_json_block:
            in_json_block = False
            try:
                raw = json.loads("\n".join(json_lines))
                if raw.get("_type") == "meta":
                    meta = raw
                elif raw.get("_type") == "entry":
                    entries.append(
                        MemoryEntry(**{k: v for k, v in raw.items() if k != "_type"})
                    )
            except Exception as exc:
                log.warning("Ungültiger JSON-Block in AGENT_MEMORY.md: %s", exc)
        elif in_json_block:
            json_lines.append(line)

    return MemoryStore(
        version=meta.get("version", "1.0"),
        last_updated=(
            datetime.fromisoformat(meta["last_updated"])
            if "last_updated" in meta
            else datetime.now(timezone.utc)
        ),
        last_updated_by=meta.get("last_updated_by", "unknown"),
        entries=entries,
    )


def _write_store(store: MemoryStore, path: Path = MEMORY_FILE) -> None:
    """
    MemoryStore atomar nach AGENT_MEMORY.md schreiben.

    Atomar: tempfile → os.replace (kein partieller Schreibzustand).
    Lock:   fcntl.flock() Exclusive Lock (kein paralleles Schreiben).
    """
    lock_path = path.parent / LOCK_FILE
    with open(lock_path, "w") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            content = _render_markdown(store)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
                suffix=".tmp",
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            os.replace(tmp_path, path)
            log.info("AGENT_MEMORY.md geschrieben: %d Entries", len(store.entries))
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)


def _render_markdown(store: MemoryStore) -> str:
    """MemoryStore → Markdown mit JSON-Fences."""
    meta = {
        "_type": "meta",
        "version": store.version,
        "last_updated": store.last_updated.isoformat(),
        "last_updated_by": store.last_updated_by,
        "entry_count": len(store.entries),
    }

    lines = [
        "# Agent Memory Store",
        "<!-- Automatisch generiert — nicht manuell bearbeiten -->",
        "<!-- Editierbar via session_memory Skill oder memory_gc Workflow -->",
        "",
        "```json",
        json.dumps(meta, indent=2, ensure_ascii=False),
        "```",
        "",
    ]

    for entry_type in EntryType:
        type_entries = [e for e in store.entries if e.entry_type == entry_type]
        if not type_entries:
            continue

        lines.append(f"## {entry_type.value.replace('_', ' ').title()}")
        lines.append("")

        for entry in sorted(type_entries, key=lambda e: e.updated_at, reverse=True):
            lines += [
                f"### {entry.entry_id} — {entry.title}",
                "",
                "```json",
                json.dumps(
                    {"_type": "entry", **entry.model_dump(mode="json")},
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                ),
                "```",
                "",
            ]

    return "\n".join(lines)


def _git_commit(path: Path, message: str) -> None:
    """AGENT_MEMORY.md committen.

    B3-Fix: explizites git config user.email + user.name vor Commit.
    Non-fatal: schlägt Commit fehl, bleibt Memory-Write erhalten.
    """
    try:
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME":     _GIT_AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL":    _GIT_AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME":  _GIT_AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": _GIT_AUTHOR_EMAIL,
        })
        for cmd in [
            ["git", "config", "user.email", _GIT_AUTHOR_EMAIL],
            ["git", "config", "user.name",  _GIT_AUTHOR_NAME],
            ["git", "add", str(path)],
        ]:
            subprocess.run(cmd, check=True, capture_output=True)

        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True,
        )
        if diff.returncode == 0:
            log.debug("Kein Git-Diff — kein Commit nötig")
            return

        subprocess.run(
            ["git", "commit", "-m", message, "--no-verify"],
            check=True, capture_output=True, env=env,
        )
        log.info("Git-Commit: %s", message)
    except subprocess.CalledProcessError as exc:
        log.warning(
            "Git-Commit fehlgeschlagen (non-fatal): %s",
            exc.stderr.decode(errors="replace"),
        )


# ─── Skill ────────────────────────────────────────────────────────────────────

class SessionMemorySkill(Skill):
    """Liest und schreibt AGENT_MEMORY.md — persistenter Kontext-Store."""

    def invoke(
        self,
        operation: str = "read",
        entry: dict | None = None,
        agent: str = "unknown-agent",
        filter_type: str | None = None,
        filter_tag: str | None = None,
        commit: bool = True,
    ) -> SkillResult:
        match operation:
            case "read":
                return self._read()
            case "upsert":
                if entry is None:
                    return SkillResult.fail(self.name, "operation='upsert' benötigt 'entry'")
                return self._upsert(entry, agent, commit)
            case "gc":
                return self._gc(agent, commit)
            case "query":
                return self._query(filter_type, filter_tag)
            case _:
                return SkillResult.fail(
                    self.name,
                    f"Unbekannte Operation: '{operation}'. Erlaubt: read, upsert, gc, query",
                )

    def _read(self) -> SkillResult:
        store = _read_store()
        return SkillResult.ok(
            skill_name=self.name,
            data={
                "entries": [e.model_dump(mode="json") for e in store.entries],
                "entry_count": len(store.entries),
                "last_updated": store.last_updated.isoformat(),
                "last_updated_by": store.last_updated_by,
            },
            message=f"{len(store.entries)} Entries geladen",
        )

    def _upsert(self, entry_dict: dict, agent: str, commit: bool) -> SkillResult:
        try:
            entry = MemoryEntry(**entry_dict)
        except Exception as exc:
            return SkillResult.fail(self.name, f"Ungültiger Entry: {exc}")

        store = _read_store()
        store.upsert(entry, agent=agent)
        _write_store(store)

        if commit:
            _git_commit(
                MEMORY_FILE,
                f"agent-memory: upsert {entry.entry_id} [{entry.entry_type.value}] by {agent}",
            )
        return SkillResult.ok(
            skill_name=self.name,
            data={"entry_id": entry.entry_id, "upserted": True},
            message=f"Entry '{entry.entry_id}' gespeichert",
        )

    def _gc(self, agent: str, commit: bool) -> SkillResult:
        store = _read_store()
        removed = store.gc()
        if removed:
            _write_store(store)
            if commit:
                _git_commit(
                    MEMORY_FILE,
                    f"agent-memory: gc removed {removed} expired entries",
                )
        return SkillResult.ok(
            skill_name=self.name,
            data={"removed_entries": removed, "remaining_entries": len(store.entries)},
            message=f"GC: {removed} abgelaufene Entries entfernt",
        )

    def _query(
        self,
        filter_type: str | None,
        filter_tag: str | None,
    ) -> SkillResult:
        store = _read_store()
        entries = store.entries

        if filter_type:
            try:
                et = EntryType(filter_type)
                entries = store.by_type(et)
            except ValueError:
                return SkillResult.fail(
                    self.name,
                    f"Ungültiger filter_type: '{filter_type}'. "
                    f"Erlaubt: {[e.value for e in EntryType]}",
                )
        if filter_tag:
            entries = [e for e in entries if filter_tag in e.tags]

        return SkillResult.ok(
            skill_name=self.name,
            data={"entries": [e.model_dump(mode="json") for e in entries]},
            message=f"{len(entries)} Entries gefunden",
        )


SKILL = SessionMemorySkill(
    name="session_memory",
    version="1.0.0",
    domain="memory",
    description="Liest und schreibt AGENT_MEMORY.md — persistenter git-tracked Kontext-Store für Agent-Erkenntnisse",
    mcp_tool_name="agent_memory",
    gate_level=GateLevel.NOTIFY,
    depends_on=[],
)
