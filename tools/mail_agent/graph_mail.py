#!/usr/bin/env python3
"""IIL-Geschäftspostfach (Microsoft 365) über Graph — LESEN, EINSORTIEREN, ENTWERFEN.

Owner-Entscheid 2026-07-18 (Lotsen-Charta Capability-Erweiterung, ausdrücklich als solche
gekennzeichnet; Punkt 168 „ja"). Zugriff wird erst scharf, wenn der Kapitän sich mit der
erweiterten Berechtigung anmeldet (--login) — die Anmeldung IST die Freigabe.

Zuschnitt (fest, KONZ-025):
- Scope Mail.ReadWrite: lesen · verschieben · Ordner anlegen · ENTWÜRFE schreiben.
- KEIN Senden (Mail.ReadWrite kann es nicht) — Vorschläge landen als Entwurf im Drafts-Ordner,
  der Kapitän prüft und sendet selbst (Art. 7 Außenwirkung bleibt beim Menschen).
- KEIN hartes Löschen — Verschieben nach Papierkorb ist die Grenze.
- Kunden-/Mandantendaten (Art. 3.2): Ausgaben sind Kapitäns-Kanal, nie Memory/Repo.
  Die Ordner-/Kunden-Zuordnung lebt lokal in ~/.claude/mail-folders.env, NICHT im Repo.

Kommandos:
  --login <konto>
  --list-folders
  --create-path "DSGVO/Groeger"          # legt Ober- + Unterordner an (idempotent)
  --scan-senders [--days N]              # Absender-Domains + Häufigkeit (Mapping-Vorschlag)
  --move --from "<domain-oder-substr>" --to "DSGVO/Groeger" [--yes]
  --find [--from S] [--subject S] [--days N] [--source PFAD]     # suchen, read-only
  --show <messageId>|latest [gleiche Filter wie --find] [--max-chars N]
  --draft --to a@b.c --subject "..." --body-file f.txt [--reply-to <messageId>] [--attach PFAD ...]
  --attach-to <messageId> --attach PFAD [--attach PFAD ...]   # Datei(en) an bestehenden Entwurf hängen
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import re
import stat
import sys
import time
from html import unescape
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


class _Resp:
    def __init__(self, status: int, text: str):
        self.status_code, self.text = status, text

    def json(self) -> dict:
        return json.loads(self.text) if self.text else {}


def _http(
    method: str, url: str, *, headers=None, data=None, json_body=None, timeout=30
) -> _Resp:
    """stdlib-only HTTP (kein Fremd-Paket, damit die Tools-CI trägt)."""
    h = dict(headers or {})
    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode()
        h.setdefault("Content-Type", "application/json")
    elif data is not None:
        body = urllib.parse.urlencode(data).encode()
        h.setdefault("Content-Type", "application/x-www-form-urlencoded")
    url = url.replace(
        " ", "%20"
    )  # OData-Filter enthalten Leerzeichen ('… ge …'); urllib lehnt rohe ab
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return _Resp(r.status, r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return _Resp(e.code, e.read().decode("utf-8", "replace"))


CONFIG_FILE = (
    Path.home() / ".claude" / "calendar.env"
)  # gleiche Maschinen-Config (Konten/Client)
TOKEN_DIR = Path.home() / ".claude" / "graph-mail-tokens"
DEFAULT_CLIENT_ID = (
    "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # MS Graph Command Line Tools (public)
)
SCOPES = "Mail.ReadWrite offline_access openid profile"
GRAPH = "https://graph.microsoft.com/v1.0"


def parse_env(path: Path) -> dict:
    v = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, val = line.partition("=")
            v[k.strip()] = val.strip().strip("'\"")
    return v


def load_cfg() -> dict:
    if not CONFIG_FILE.exists():
        sys.exit(
            f"FEHLER: {CONFIG_FILE} fehlt — Maschine nicht für Mail freigegeben (Capability-Profil)"
        )
    c = parse_env(CONFIG_FILE)
    accounts = [a.strip() for a in c.get("GRAPH_ACCOUNTS", "").split(",") if a.strip()]
    if not accounts:
        sys.exit("FEHLER: GRAPH_ACCOUNTS leer in calendar.env")
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_DIR.chmod(stat.S_IRWXU)
    return {
        "accounts": accounts,
        "client_id": c.get("GRAPH_CLIENT_ID", DEFAULT_CLIENT_ID),
        "tenant": c.get("GRAPH_TENANT", "organizations"),
    }


def _tok_path(acc: str) -> Path:
    return TOKEN_DIR / (acc.replace("@", "_at_") + ".json")


def _save(acc: str, tokens: dict) -> None:
    tokens["_saved_at"] = int(time.time())
    p = _tok_path(acc)
    p.write_text(json.dumps(tokens))
    p.chmod(stat.S_IRUSR | stat.S_IWUSR)


def cmd_login(cfg: dict, acc: str) -> None:
    if acc not in cfg["accounts"]:
        sys.exit(f"FEHLER: {acc} steht nicht in GRAPH_ACCOUNTS")
    base = f"https://login.microsoftonline.com/{cfg['tenant']}/oauth2/v2.0"
    r = _http(
        "POST",
        f"{base}/devicecode",
        data={"client_id": cfg["client_id"], "scope": SCOPES},
    )
    if r.status_code != 200:
        sys.exit(
            f"FEHLER: Device-Code {r.status_code} — {r.json().get('error_description', '')[:200]}"
        )
    dc = r.json()
    print(
        f"\n>>> Mail-Anmeldung für {acc} (Berechtigung: Mail lesen + einsortieren + entwerfen):"
    )
    print(f">>> {dc['message']}\n")
    deadline = time.time() + int(dc.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(int(dc.get("interval", 5)))
        tr = _http(
            "POST",
            f"{base}/token",
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": cfg["client_id"],
                "device_code": dc["device_code"],
            },
        )
        b = tr.json()
        if tr.status_code == 200:
            _save(acc, b)
            print(
                f"OK: Mail-Zugang für {acc} erteilt (lesen/einsortieren/entwerfen — kein Senden)."
            )
            return
        if b.get("error") in ("authorization_pending", "slow_down"):
            continue
        sys.exit(f"FEHLER: {b.get('error')} — {b.get('error_description', '')[:200]}")
    sys.exit("FEHLER: Anmeldezeit abgelaufen — bitte erneut.")


def token(cfg: dict, acc: str) -> str | None:
    p = _tok_path(acc)
    if not p.exists():
        return None
    t = json.loads(p.read_text())
    if int(time.time()) - t.get("_saved_at", 0) < int(t.get("expires_in", 3599)) - 120:
        return t["access_token"]
    base = f"https://login.microsoftonline.com/{cfg['tenant']}/oauth2/v2.0"
    tr = _http(
        "POST",
        f"{base}/token",
        data={
            "grant_type": "refresh_token",
            "client_id": cfg["client_id"],
            "refresh_token": t.get("refresh_token", ""),
            "scope": SCOPES,
        },
    )
    if tr.status_code != 200:
        return None
    b = tr.json()
    b.setdefault("refresh_token", t.get("refresh_token", ""))
    _save(acc, b)
    return b["access_token"]


def _auth(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}"}


def account(cfg: dict, args) -> tuple[str, str]:
    acc = args.account or cfg["accounts"][0]
    tok = token(cfg, acc)
    if not tok:
        sys.exit(f"FEHLER: {acc} nicht für Mail angemeldet — erst: --login {acc}")
    return acc, tok


# ---------- Ordner ----------


def _folders(tok: str) -> list[dict]:
    """Alle Ordner flach mit Pfad ('DSGVO/Groeger')."""
    out = []

    def walk(parent_id: str | None, prefix: str):
        url = (
            f"{GRAPH}/me/mailFolders"
            if parent_id is None
            else f"{GRAPH}/me/mailFolders/{parent_id}/childFolders"
        )
        url += "?$top=100&$select=id,displayName,childFolderCount"
        r = _http("GET", url, headers=_auth(tok))
        for f in r.json().get("value", []):
            path = f["displayName"] if not prefix else f"{prefix}/{f['displayName']}"
            out.append({"id": f["id"], "path": path, "name": f["displayName"]})
            if f.get("childFolderCount", 0):
                walk(f["id"], path)

    walk(None, "")
    return out


def find_folder(tok: str, path: str) -> str | None:
    for f in _folders(tok):
        if f["path"].lower() == path.strip("/").lower():
            return f["id"]
    return None


def ensure_path(tok: str, path: str) -> str:
    parent_id, prefix = None, ""
    for part in [p for p in path.strip("/").split("/") if p]:
        prefix = part if not prefix else f"{prefix}/{part}"
        fid = find_folder(tok, prefix)
        if fid is None:
            url = (
                f"{GRAPH}/me/mailFolders"
                if parent_id is None
                else f"{GRAPH}/me/mailFolders/{parent_id}/childFolders"
            )
            r = _http("POST", url, headers=_auth(tok), json_body={"displayName": part})
            if r.status_code not in (200, 201):
                sys.exit(
                    f"FEHLER: Ordner '{part}' anlegen fehlgeschlagen HTTP {r.status_code} — {r.text[:150]}"
                )
            fid = r.json()["id"]
        parent_id = fid
    return parent_id


def cmd_list_folders(tok: str) -> None:
    for f in _folders(tok):
        print(f["path"])


def cmd_move_folder(tok: str, src_path: str, dest_parent_path: str) -> None:
    """Verschiebt einen ganzen Ordner (mit Inhalt) unter einen anderen Elternordner."""
    src_id = find_folder(tok, src_path)
    if not src_id:
        sys.exit(f"FEHLER: Ordner '{src_path}' nicht gefunden.")
    dest_id = ensure_path(tok, dest_parent_path)
    r = _http(
        "POST",
        f"{GRAPH}/me/mailFolders/{src_id}/move",
        headers=_auth(tok),
        json_body={"destinationId": dest_id},
    )
    if r.status_code not in (200, 201):
        sys.exit(
            f"FEHLER: Ordner verschieben fehlgeschlagen HTTP {r.status_code} — {r.text[:150]}"
        )
    print(
        f"OK: Ordner '{src_path}' → '{dest_parent_path}/' verschoben (Inhalt bleibt erhalten)."
    )


def cmd_create_path(tok: str, path: str) -> None:
    ensure_path(tok, path)
    print(f"OK: Ordnerpfad '{path}' vorhanden/angelegt.")


# ---------- Absender-Scan ----------


def cmd_scan(tok: str, days: int, source_path: str = "inbox") -> None:
    # --source erlaubt beliebige Ordner (z.B. Junk-E-Mail), nicht nur Posteingang.
    src = (
        "inbox"
        if source_path.lower() in ("inbox", "")
        else find_folder(tok, source_path)
    )
    if not src:
        sys.exit(f"FEHLER: Quellordner '{source_path}' nicht gefunden.")
    label = "Posteingang" if src == "inbox" else source_path
    since = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(time.time() - days * 86400))
    url = (
        f"{GRAPH}/me/mailFolders/{src}/messages?$top=200&$select=from"
        f"&$filter=receivedDateTime ge {since}"
    )
    dom = Counter()
    while url:
        r = _http("GET", url, headers=_auth(tok))
        j = r.json()
        for m in j.get("value", []):
            addr = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "")
            if "@" in addr:
                dom[addr.split("@", 1)[1].lower()] += 1
        url = j.get("@odata.nextLink")
    print(f"Absender-Domains in '{label}' (letzte {days} Tage), häufigste zuerst:")
    for d, n in dom.most_common(40):
        print(f"  {n:>4}  {d}")


# ---------- Suchen / Lesen (read-only) ----------


def _match_messages(
    tok: str,
    *,
    from_sub: str = "",
    subject_sub: str = "",
    days: int = 30,
    source_path: str = "inbox",
) -> list[dict]:
    """Substring-Filter client-seitig wie bei --move ($search braucht
    ConsistencyLevel-Header und liefert instabile Treffer-Reihenfolge)."""
    src = (
        "inbox"
        if source_path.lower() in ("inbox", "")
        else find_folder(tok, source_path)
    )
    if not src:
        sys.exit(f"FEHLER: Quellordner '{source_path}' nicht gefunden.")
    since = time.strftime("%Y-%m-%dT00:00:00Z", time.gmtime(time.time() - days * 86400))
    hits, url = (
        [],
        (
            f"{GRAPH}/me/mailFolders/{src}/messages?$top=100"
            "&$select=id,subject,from,receivedDateTime"
            f"&$filter=receivedDateTime ge {since}"
            "&$orderby=receivedDateTime desc"
        ),
    )
    while url:
        r = _http("GET", url, headers=_auth(tok))
        j = r.json()
        for m in j.get("value", []):
            em = (m.get("from") or {}).get("emailAddress") or {}
            hay_from = (em.get("address", "") + " " + em.get("name", "")).lower()
            subj = m.get("subject") or ""
            if from_sub and from_sub.lower() not in hay_from:
                continue
            if subject_sub and subject_sub.lower() not in subj.lower():
                continue
            hits.append(m)
        url = j.get("@odata.nextLink")
    return hits


def cmd_find(
    tok: str, from_sub: str, subject_sub: str, days: int, source_path: str
) -> None:
    hits = _match_messages(
        tok,
        from_sub=from_sub,
        subject_sub=subject_sub,
        days=days,
        source_path=source_path,
    )
    if not hits:
        print(f"Keine Treffer in '{source_path or 'inbox'}' (letzte {days} Tage).")
        return
    print(
        f"{len(hits)} Treffer in '{source_path or 'inbox'}' (letzte {days} Tage), neueste zuerst:"
    )
    for m in hits:
        em = (m.get("from") or {}).get("emailAddress") or {}
        print(
            f"  · {m.get('receivedDateTime', '')[:16]}  {em.get('address', '')[:38]:<38} "
            f"{(m.get('subject') or '')[:60]}"
        )
        print(f"    id: {m['id']}")


def _strip_html(html_text: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", "", html_text, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>|</p>|</div>|</tr>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return unescape(text)


def cmd_show(
    tok: str,
    which: str,
    from_sub: str,
    subject_sub: str,
    days: int,
    source_path: str,
    max_chars: int,
) -> None:
    if which == "latest":
        hits = _match_messages(
            tok,
            from_sub=from_sub,
            subject_sub=subject_sub,
            days=days,
            source_path=source_path,
        )
        if not hits:
            sys.exit("FEHLER: kein Treffer für --show latest mit diesen Filtern.")
        mid = hits[0]["id"]
    else:
        mid = which
    r = _http(
        "GET",
        f"{GRAPH}/me/messages/{urllib.parse.quote(mid, safe='')}"
        "?$select=subject,from,toRecipients,receivedDateTime,body",
        headers=_auth(tok),
    )
    if r.status_code != 200:
        sys.exit(
            f"FEHLER: Nachricht nicht lesbar HTTP {r.status_code} — {r.text[:150]}"
        )
    m = r.json()
    em = (m.get("from") or {}).get("emailAddress") or {}
    tos = ", ".join(
        ((t.get("emailAddress") or {}).get("address", ""))
        for t in m.get("toRecipients", [])
    )
    body = m.get("body") or {}
    text = body.get("content", "")
    if (body.get("contentType") or "").lower() == "html":
        text = _strip_html(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    print(f"Von:     {em.get('name', '')} <{em.get('address', '')}>")
    print(f"An:      {tos}")
    print(f"Datum:   {m.get('receivedDateTime', '')}")
    print(f"Betreff: {m.get('subject', '')}")
    print("--- Body ---")
    print(
        text[:max_chars]
        + ("\n[… gekürzt, --max-chars erhöhen]" if len(text) > max_chars else "")
    )


# ---------- Verschieben ----------


def _find_messages(tok: str, from_sub: str, source_path: str):
    src = (
        "inbox"
        if source_path.lower() in ("inbox", "")
        else find_folder(tok, source_path)
    )
    if not src:
        sys.exit(f"FEHLER: Quellordner '{source_path}' nicht gefunden.")
    hits, url = (
        [],
        (
            f"{GRAPH}/me/mailFolders/{src}/messages?$top=100"
            "&$select=id,subject,from,receivedDateTime"
        ),
    )
    while url:
        r = _http("GET", url, headers=_auth(tok))
        j = r.json()
        for m in j.get("value", []):
            addr = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "")
            name = ((m.get("from") or {}).get("emailAddress") or {}).get("name", "")
            if from_sub.lower() in addr.lower() or from_sub.lower() in name.lower():
                hits.append(
                    (
                        m["id"],
                        m.get("receivedDateTime", "")[:10],
                        addr[:38],
                        (m.get("subject") or "")[:50],
                    )
                )
        url = j.get("@odata.nextLink")
    return hits


def cmd_move(
    tok: str, from_sub: str, target_path: str, source_path: str, yes: bool
) -> None:
    hits = _find_messages(tok, from_sub, source_path)
    if not hits:
        print("Keine passenden Mails gefunden — nichts verschoben.")
        return
    print(
        f"Verschieben (Absender~\"{from_sub}\") aus '{source_path or 'inbox'}' nach '{target_path}':"
    )
    for _, d, frm, subj in hits:
        print(f"  · {d}  {frm:<38} {subj}")
    print(f"  = {len(hits)} Mail(s)")
    if not yes:
        try:
            if input("Verschieben? [j/N] ").strip().lower() not in (
                "j",
                "ja",
                "y",
                "yes",
            ):
                sys.exit("Abgebrochen.")
        except EOFError:
            sys.exit("Kein --yes und keine Eingabe — abgebrochen.")
    dest = ensure_path(tok, target_path)
    for mid, *_ in hits:
        r = _http(
            "POST",
            f"{GRAPH}/me/messages/{mid}/move",
            headers=_auth(tok),
            json_body={"destinationId": dest},
        )
        if r.status_code not in (200, 201):
            print(f"  ! Fehler bei einer Mail: HTTP {r.status_code}", file=sys.stderr)
    print(f"OK: {len(hits)} Mail(s) nach '{target_path}' verschoben.")


# ---------- Entwurf ----------


def _file_attachment_payload(path: str) -> dict:
    """Graph-fileAttachment-JSON für eine lokale Datei (netzfrei, unit-testbar).

    Kleine Anhänge (<3 MB) gehen inline als base64 contentBytes — für die
    TOM-/Report-Dateien dieses Tools reicht das; große Uploads (Upload-Session)
    sind bewusst nicht abgedeckt.
    """
    p = Path(path)
    if not p.is_file():
        sys.exit(f"FEHLER: Anhang nicht gefunden: {path}")
    raw = p.read_bytes()
    if len(raw) >= 3 * 1024 * 1024:
        sys.exit(
            f"FEHLER: Anhang {p.name} ist >3 MB — Inline-Anhang nicht unterstützt."
        )
    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": p.name,
        "contentType": ctype,
        "contentBytes": base64.b64encode(raw).decode("ascii"),
    }


def _attach_files(tok: str, msg_id: str, paths: list[str]) -> None:
    for path in paths:
        payload = _file_attachment_payload(path)
        r = _http(
            "POST",
            f"{GRAPH}/me/messages/{msg_id}/attachments",
            headers=_auth(tok),
            json_body=payload,
        )
        if r.status_code not in (200, 201):
            sys.exit(
                f"FEHLER: Anhang {payload['name']} fehlgeschlagen HTTP {r.status_code} — {r.text[:150]}"
            )
        print(f"  + Anhang: {payload['name']} ({payload['contentType']})")


def cmd_draft(
    tok: str,
    to: str,
    subject: str,
    body: str,
    reply_to: str | None,
    attach: list[str] | None = None,
) -> None:
    if reply_to:
        r = _http(
            "POST",
            f"{GRAPH}/me/messages/{reply_to}/createReply",
            headers=_auth(tok),
            json_body={},
        )
        if r.status_code not in (200, 201):
            sys.exit(
                f"FEHLER: Antwort-Entwurf anlegen fehlgeschlagen HTTP {r.status_code}"
            )
        did = r.json()["id"]
        patch = {"body": {"contentType": "Text", "content": body}}
        if subject:
            patch["subject"] = subject
        _http(
            "PATCH", f"{GRAPH}/me/messages/{did}", headers=_auth(tok), json_body=patch
        )
        if attach:
            _attach_files(tok, did, attach)
        print(
            f"OK: Antwort-Entwurf im Drafts-Ordner abgelegt (Reply auf {reply_to[:12]}…). "
            "Prüfe und sende ihn selbst aus Outlook."
        )
        return
    body_json = {
        "subject": subject,
        "body": {"contentType": "Text", "content": body},
        "toRecipients": [
            {"emailAddress": {"address": a.strip()}} for a in to.split(",") if a.strip()
        ],
    }
    r = _http("POST", f"{GRAPH}/me/messages", headers=_auth(tok), json_body=body_json)
    if r.status_code not in (200, 201):
        sys.exit(
            f"FEHLER: Entwurf anlegen fehlgeschlagen HTTP {r.status_code} — {r.text[:150]}"
        )
    if attach:
        _attach_files(tok, r.json()["id"], attach)
    print(
        "OK: Entwurf im Drafts-Ordner abgelegt (NICHT gesendet). Prüfe und sende ihn selbst aus Outlook."
    )


def cmd_attach_to(tok: str, msg_id: str, attach: list[str]) -> None:
    """Datei(en) an einen bestehenden Entwurf hängen (in-place, kein Duplikat)."""
    _attach_files(tok, msg_id, attach)
    print(
        f"OK: {len(attach)} Anhang/Anhänge an Entwurf {msg_id[:12]}… gehängt (NICHT gesendet). "
        "Prüfe und sende ihn selbst aus Outlook."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--login", metavar="KONTO")
    g.add_argument("--list-folders", action="store_true")
    g.add_argument("--create-path", metavar="PFAD")
    g.add_argument("--scan-senders", action="store_true")
    g.add_argument("--move", action="store_true")
    g.add_argument(
        "--move-folder",
        metavar="QUELLPFAD",
        help="ganzen Ordner unter --to-parent verschieben",
    )
    g.add_argument("--find", action="store_true", help="Mails suchen (read-only)")
    g.add_argument(
        "--show", metavar="ID|latest", help="eine Mail vollständig lesen (read-only)"
    )
    g.add_argument("--draft", action="store_true")
    g.add_argument(
        "--attach-to",
        metavar="messageId",
        help="Anhang/Anhänge an einen bestehenden Entwurf hängen",
    )
    ap.add_argument(
        "--attach",
        action="append",
        metavar="PFAD",
        default=[],
        help="Datei anhängen (wiederholbar) — mit --draft oder --attach-to",
    )
    ap.add_argument("--to-parent", help="Ziel-Elternordner bei --move-folder")
    ap.add_argument("--account")
    ap.add_argument("--days", type=int, default=180)
    ap.add_argument("--from", dest="from_sub")
    ap.add_argument("--to")
    ap.add_argument("--source", default="inbox")
    ap.add_argument("--subject", default="")
    ap.add_argument("--body-file")
    ap.add_argument("--reply-to")
    ap.add_argument(
        "--max-chars", type=int, default=2000, help="Body-Kürzung bei --show"
    )
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass

    cfg = load_cfg()
    if args.login:
        cmd_login(cfg, args.login)
        return
    _, tok = account(cfg, args)
    if args.list_folders:
        cmd_list_folders(tok)
    elif args.create_path:
        cmd_create_path(tok, args.create_path)
    elif args.scan_senders:
        cmd_scan(tok, args.days, args.source)
    elif args.move:
        if not (args.from_sub and args.to):
            ap.error("--move braucht --from und --to")
        cmd_move(tok, args.from_sub, args.to, args.source, args.yes)
    elif args.move_folder:
        if not args.to_parent:
            ap.error("--move-folder braucht --to-parent ZIEL-ELTERNORDNER")
        cmd_move_folder(tok, args.move_folder, args.to_parent)
    elif args.find:
        if not (args.from_sub or args.subject):
            ap.error("--find braucht --from und/oder --subject")
        cmd_find(tok, args.from_sub or "", args.subject, args.days, args.source)
    elif args.show:
        cmd_show(
            tok,
            args.show,
            args.from_sub or "",
            args.subject,
            args.days,
            args.source,
            args.max_chars,
        )
    elif args.attach_to:
        if not args.attach:
            ap.error("--attach-to braucht mindestens ein --attach PFAD")
        cmd_attach_to(tok, args.attach_to, args.attach)
    else:  # --draft
        if not args.body_file:
            ap.error("--draft braucht --body-file (und --to ODER --reply-to)")
        if not (args.to or args.reply_to):
            ap.error("--draft braucht --to ODER --reply-to")
        body = Path(args.body_file).read_text()
        cmd_draft(tok, args.to or "", args.subject, body, args.reply_to, args.attach)


if __name__ == "__main__":
    main()
