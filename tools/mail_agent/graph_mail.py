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
  --move --from "<domain-oder-substr>" [--subject S] --to "DSGVO/Groeger" [--yes]
  --flag   --from S [--subject S] [--source PFAD] [--yes]        # zur Nachverfolgung markieren
  --unflag --from S [--subject S] [--source PFAD] [--yes]        # Markierung wieder entfernen
  --importance high|normal|low --from S [--subject S] [--yes]    # Wichtigkeit setzen
  --find [--from S] [--subject S] [--days N] [--source PFAD]     # suchen, read-only
  --find --all [--days N] [--source PFAD]                        # Ordner VOLLSTAENDIG aufzaehlen (#1480)
  --find --category "<Vorgang>" [--source PFAD]                  # alle Mails eines Vorgangs
  --categorize "<Vorgang>" --from S [--subject S] [--yes]        # Vorgang zuordnen (ADDITIV)
  --uncategorize "<Vorgang>" --from S [--subject S] [--yes]      # Zuordnung wieder loesen
  --list-categories [--source PFAD] [--days N]                   # Vorgangs-Inventar + Restmenge
  --show <messageId>|latest [gleiche Filter wie --find] [--max-chars N] [--save-attachments DIR]
  --draft --to a@b.c [--cc c@d.e] --subject "..." --body-file f.txt [--reply-to <messageId>] [--attach PFAD ...]
  --draft --reply-to <messageId> --role iil --design [--eyebrow "..."]   # Rollen-Design, Zitat bleibt erhalten
  --attach-to <messageId> --attach PFAD [--attach PFAD ...]   # Datei(en) an bestehenden Entwurf hängen
"""

from __future__ import annotations

import argparse
import base64
import html
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import roles  # noqa: E402  (sibling-Modul, Konvention wie ablage_pruefung.py)


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
    category: str = "",
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
            "&$select=id,subject,from,receivedDateTime,categories"
            f"&$filter=receivedDateTime ge {since}"
            "&$orderby=receivedDateTime desc"
        ),
    )
    gesehen = 0
    ohne_smtp = 0  # Absenderfeld ohne "@": Exchange-X.500-DN oder leer (Entwuerfe)
    while url:
        r = _http("GET", url, headers=_auth(tok))
        j = r.json()
        for m in j.get("value", []):
            gesehen += 1
            em = (m.get("from") or {}).get("emailAddress") or {}
            adresse = em.get("address", "")
            hay_from = (adresse + " " + em.get("name", "")).lower()
            subj = m.get("subject") or ""
            if from_sub and from_sub.lower() not in hay_from:
                # #1480: Gesendete Elemente tragen den Absender teils als X.500-DN
                # (/o=ExchangeLabs/...), Entwuerfe gar nicht. Ein Filter wie "@"
                # verwirft die still — dann wird aus einer Teilmenge unbemerkt
                # eine vermeintliche Vollerhebung.
                if "@" not in adresse:
                    ohne_smtp += 1
                continue
            if subject_sub and subject_sub.lower() not in subj.lower():
                continue
            if category and not any(
                c.casefold() == category.casefold() for c in (m.get("categories") or [])
            ):
                continue
            hits.append(m)
        url = j.get("@odata.nextLink")

    if ohne_smtp:
        print(
            f"⚠ Absender-Filter '{from_sub}': {ohne_smtp} von {gesehen} Nachricht(en) in "
            f"'{source_path or 'inbox'}' tragen keine SMTP-Adresse im Absenderfeld "
            f"(Exchange-X.500-DN oder Entwurf) und wurden verworfen. "
            f"Fuer eine Vollerhebung --all nutzen, keinen Absender-Platzhalter.",
            file=sys.stderr,
        )
    return hits


def cmd_find(
    tok: str,
    from_sub: str,
    subject_sub: str,
    days: int,
    source_path: str,
    category: str = "",
) -> None:
    hits = _match_messages(
        tok,
        from_sub=from_sub,
        subject_sub=subject_sub,
        days=days,
        source_path=source_path,
        category=category,
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


_UNSAFE_NAME_CHARS = re.compile(r"[\x00-\x1f/\\:*?\"<>|]")


def _safe_filename(name: str) -> str:
    """Anhangsnamen entschärfen — sie kommen vom Absender, nicht von uns.

    Verzeichnisanteile, Steuerzeichen und `..` fallen weg, damit ein Anhang
    namens `../../.ssh/authorized_keys` nicht aus dem Zielordner ausbricht.
    """
    base = re.split(r"[\\/]", (name or "").strip())[-1]  # Basename ZUERST, sonst
    base = _UNSAFE_NAME_CHARS.sub("_", base)  # maskiert das Ersetzen die Trenner
    base = base.lstrip(". ").strip()
    return base or "anhang.bin"


def _decode_attachment(att: dict) -> tuple[str, bytes] | None:
    """(Dateiname, Bytes) für einen fileAttachment; None für item-/reference-Anhänge.

    Netzfrei und damit unit-testbar — der HTTP-Teil steckt in download_attachments.
    """
    if att.get("@odata.type") != "#microsoft.graph.fileAttachment":
        return None
    content = att.get("contentBytes")
    if content is None:
        return None
    return _safe_filename(att.get("name") or ""), base64.b64decode(content)


def download_attachments(
    tok: str, msg_id: str, target_dir: str
) -> list[tuple[str, int]]:
    """Alle Datei-Anhänge einer Nachricht in target_dir schreiben.

    Gibt [(Dateiname, Bytes)] zurück. Nicht-Datei-Anhänge (eingebettete Mails,
    Cloud-Verweise) werden gemeldet, aber nicht geschrieben — ihr Inhalt liegt
    nicht als contentBytes vor.
    """
    r = _http(
        "GET",
        f"{GRAPH}/me/messages/{urllib.parse.quote(msg_id, safe='')}/attachments",
        headers=_auth(tok),
    )
    if r.status_code != 200:
        sys.exit(f"FEHLER: Anhänge nicht lesbar HTTP {r.status_code} — {r.text[:150]}")
    out = Path(target_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    saved: list[tuple[str, int]] = []
    for att in r.json().get("value", []):
        decoded = _decode_attachment(att)
        if decoded is None:
            print(f"  ~ übersprungen (kein Datei-Anhang): {att.get('name', '?')}")
            continue
        name, raw = decoded
        (out / name).write_bytes(raw)
        saved.append((name, len(raw)))
    return saved


def cmd_show(
    tok: str,
    which: str,
    from_sub: str,
    subject_sub: str,
    days: int,
    source_path: str,
    max_chars: int,
    save_attachments: str | None = None,
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
        "?$select=subject,from,toRecipients,receivedDateTime,body,hasAttachments",
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
    if save_attachments:
        saved = download_attachments(tok, mid, save_attachments)
        print(f"--- Anhänge ({len(saved)}) -> {save_attachments} ---")
        for name, size in saved:
            print(f"  · {name} ({size} Bytes)")
    elif m.get("hasAttachments"):
        # Ohne diesen Hinweis bleibt der eigentliche Inhalt unsichtbar: Rechnungen,
        # Zahlungsaufforderungen o.ä. stehen im PDF, nicht im Mailtext.
        print("--- Anhänge vorhanden — mit --save-attachments DIR herunterladen ---")


# ---------- Verschieben ----------


def _find_messages(tok: str, from_sub: str, source_path: str, subject_sub: str = ""):
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
            subj = m.get("subject") or ""
            if (
                from_sub.lower() not in addr.lower()
                and from_sub.lower() not in name.lower()
            ):
                continue
            # UND-Bedingung (#1281): Sammeladressen wie microsoft-noreply@ liefern
            # Rechnungen und Abo-Mails unter derselben Adresse — eine reine
            # Absender-Regel wuerde beides in denselben Ordner werfen.
            if subject_sub and subject_sub.lower() not in subj.lower():
                continue
            hits.append(
                (
                    m["id"],
                    m.get("receivedDateTime", "")[:10],
                    addr[:38],
                    subj[:50],
                )
            )
        url = j.get("@odata.nextLink")
    return hits


def cmd_move(
    tok: str,
    from_sub: str,
    target_path: str,
    source_path: str,
    yes: bool,
    subject_sub: str = "",
    nur_ids: list[str] | None = None,
) -> None:
    """Verschieben nach Absender/Betreff — oder genau eine benannte Nachricht.

    Der Weg zu einer einzelnen Nachricht war ueber ``--trash <messageId>`` schon
    da, fuer ``--move`` aber nicht freigelegt. Ohne ihn bliebe nur der Umweg ueber
    einen Betreff-Filter, und der traefe auch fremde Mails mit demselben Wort.
    """
    if nur_ids:
        # Eine messageId aus einer Pipeline traegt gern Zeilenumbrueche oder
        # Reste der Fundzeile mit sich. Ungeprueft landete das in der URL und
        # endete in einem Stacktrace ("URL can't contain control characters")
        # statt in einer Meldung — gemessen am 2026-08-18 beim eigenen Testlauf.
        sauber = []
        for roh in nur_ids:
            mid = (roh or "").strip()
            if not mid or any(z in mid for z in "\r\n\t "):
                print(
                    f"  ! Keine brauchbare messageId: {roh!r:.60}", file=sys.stderr
                )
                continue
            sauber.append(mid)
        if not sauber:
            sys.exit("FEHLER: keine brauchbare messageId uebergeben.")
        nur_ids = sauber

        hits = []
        for mid in nur_ids:
            r = _http(
                "GET",
                f"{GRAPH}/me/messages/{mid}"
                "?$select=id,subject,receivedDateTime,from",
                headers=_auth(tok),
            )
            if r.status_code != 200:
                print(
                    f"  ! Nachricht nicht lesbar (HTTP {r.status_code}): {mid[:24]}…",
                    file=sys.stderr,
                )
                continue
            m = r.json()
            absender = (
                (m.get("from") or {}).get("emailAddress", {}).get("address") or "—"
            )
            hits.append(
                (
                    m.get("id"),
                    (m.get("receivedDateTime") or "")[:16],
                    absender,
                    m.get("subject") or "",
                )
            )
        if not hits:
            print("Keine der angegebenen Nachrichten lesbar — nichts verschoben.")
            return
        kriterium = f"{len(hits)} benannte Nachricht(en)"
        print(f"Verschieben ({kriterium}) nach '{target_path}':")
        for _, d, frm, subj in hits:
            print(f"  · {d}  {frm:<38} {subj}")
        if not yes:
            try:
                if input("Verschieben? [j/N] ").strip().lower() not in (
                    "j", "ja", "y", "yes",
                ):
                    sys.exit("Abgebrochen.")
            except EOFError:
                sys.exit("Kein --yes und keine Eingabe — abgebrochen.")
        dest = ensure_path(tok, target_path)
        bewegt = 0
        for mid, *_ in hits:
            r = _http(
                "POST",
                f"{GRAPH}/me/messages/{mid}/move",
                headers=_auth(tok),
                json_body={"destinationId": dest},
            )
            if r.status_code in (200, 201):
                bewegt += 1
            else:
                print(
                    f"  ! Fehler bei einer Mail: HTTP {r.status_code}", file=sys.stderr
                )
        print(f"OK: {bewegt} Mail(s) nach '{target_path}' verschoben.")
        return

    hits = _find_messages(tok, from_sub, source_path, subject_sub)
    if not hits:
        print("Keine passenden Mails gefunden — nichts verschoben.")
        return
    kriterium = f'Absender~"{from_sub}"'
    if subject_sub:
        kriterium += f' UND Betreff~"{subject_sub}"'
    print(
        f"Verschieben ({kriterium}) aus '{source_path or 'inbox'}' nach '{target_path}':"
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


# ---------- Markieren: Nachverfolgung (Flag) + Wichtigkeit ----------


def cmd_mark(
    tok: str,
    *,
    from_sub: str,
    subject_sub: str,
    source_path: str,
    days: int,
    yes: bool,
    patch: dict,
    label: str,
) -> None:
    """Setzt Follow-up-Flag oder Wichtigkeit auf die per Kriterium getroffenen Mails.

    Kein Pauschal-Zug: die Auswahl kommt aus _match_messages (--from/--subject),
    und ohne --yes gilt dasselbe Anzeige-Gate wie bei --move. PATCH ist reversibel
    (--unflag bzw. --importance normal) — es wird nichts verschoben oder gelöscht.
    """
    hits = _match_messages(
        tok,
        from_sub=from_sub,
        subject_sub=subject_sub,
        days=days,
        source_path=source_path,
    )
    if not hits:
        print("Keine passenden Mails gefunden — nichts geändert.")
        return
    krit = (
        " & ".join(
            filter(
                None,
                [
                    f'Absender~"{from_sub}"' if from_sub else None,
                    f'Betreff~"{subject_sub}"' if subject_sub else None,
                ],
            )
        )
        or "ALLE"
    )
    print(f"{label} in '{source_path or 'inbox'}'  (Kriterium: {krit}) — reversibel:")
    for m in hits:
        em = (m.get("from") or {}).get("emailAddress") or {}
        print(
            f"  · {m.get('receivedDateTime', '')[:10]}  {em.get('address', '')[:38]:<38} "
            f"{(m.get('subject') or '')[:50]}"
        )
    print(f"  = {len(hits)} Mail(s)")
    if not yes:
        try:
            if input(f"{label}? [j/N] ").strip().lower() not in (
                "j",
                "ja",
                "y",
                "yes",
            ):
                sys.exit("Abgebrochen — nichts geändert.")
        except EOFError:
            sys.exit("Kein --yes und keine Eingabe — abgebrochen.")
    ok = 0
    for m in hits:
        r = _http(
            "PATCH",
            f"{GRAPH}/me/messages/{urllib.parse.quote(m['id'], safe='')}",
            headers=_auth(tok),
            json_body=patch,
        )
        if r.status_code in (200, 201):
            ok += 1
        else:
            print(
                f"  ! Fehler bei einer Mail: HTTP {r.status_code} — {r.text[:120]}",
                file=sys.stderr,
            )
    print(f"OK: {ok}/{len(hits)} Mail(s) — {label}.")


def cmd_trash(tok: str, msg_id: str) -> None:
    """Verschiebt EINE Nachricht (per ID) in den Papierkorb — reversibel, kein Hard-Delete.

    Nötig, um einen einzelnen Entwurf gezielt zurückzunehmen (z.B. einen verfrüht
    oder falsch angelegten Draft): --move filtert nur nach Absender und träfe alle
    eigenen Entwürfe zugleich. Ziel ist der well-known-Ordner 'deleteditems'.
    """
    r = _http(
        "POST",
        f"{GRAPH}/me/messages/{msg_id}/move",
        headers=_auth(tok),
        json_body={"destinationId": "deleteditems"},
    )
    if r.status_code in (200, 201):
        print(
            "OK: Nachricht in den Papierkorb (Gelöschte Elemente) verschoben — reversibel."
        )
    else:
        sys.exit(f"Fehler: HTTP {r.status_code} — {r.text[:200]}")


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


#: Schrift wie ein normaler Outlook-Client — unauffaellig, kein Marketing-Look.
#: Kein Monogramm, kein Akzentbalken: Rueckmeldung eines Kunden am 2026-07-30 zum
#: Rollen-Design lautete woertlich "Sieht aus wie ein Newsletter".
_MAIL_SCHRIFT = "font-family:Calibri,'Segoe UI',sans-serif;font-size:11pt;color:#000000"


def _klartext_als_mailhtml(text: str) -> str:
    """Klartext -> kompaktes Mail-HTML: Leerzeile trennt Absaetze, Umbruch wird <br>.

    Die frueher hier stehende Fassung machte aus JEDER Zeile ein eigenes `<p>`.
    Exchange normalisiert jedes `<p>` auf `margin-top:1em; margin-bottom:1em` —
    eine fuenfzeilige Signatur bekam damit vier doppelte Leerzeilen, und die
    Leerzeilen-Absaetze (`<p>&nbsp;</p>`) klebten als Einrueckung vor dem
    Folgetext. Beides am Entwurf gemessen (2026-07-30), beides Owner-Befund.

    Absatzgrenze ist deshalb die LEERZEILE, nicht der Zeilenumbruch. Der letzte
    Absatz — Signatur und Pflichtangaben — bleibt so ein kompakter Block.
    """
    bloecke = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    absaetze = []
    for block in bloecke:
        zeilen = [html.escape(z.rstrip()) for z in block.split("\n") if z.strip()]
        absaetze.append(f'<p style="margin:0 0 10px 0">{"<br>".join(zeilen)}</p>')
    return f'<div style="{_MAIL_SCHRIFT}">{"".join(absaetze)}</div>'


def _antwort_rumpf(
    neu: str, vorhanden: str, vorhandener_typ: str, *, neu_ist_html: bool = False
) -> dict:
    """Neuen Text VOR den zitierten Ursprungstext setzen (Graph-body-Objekt).

    `createReply` liefert den Entwurf bereits mit dem zitierten Verlauf. Wer
    danach `body.content` schreibt, ersetzt den gesamten Rumpf und loescht das
    Zitat — genau dieser Fehler stand am 2026-07-30 in drei Antwort-Entwuerfen.

    Der neue Text kommt als Klartext herein. Ist der vorhandene Rumpf HTML
    (Graph liefert praktisch immer HTML), wird der Klartext escaped und in
    Absaetze gesetzt, damit Zeilenumbrueche nicht verlorengehen.
    """
    if neu_ist_html:
        # Rollen-Design (--design): der neue Teil ist fertiges HTML und wird nicht
        # escaped. Ein reines Text-Zitat kommt in <pre>, damit es lesbar bleibt.
        if not vorhanden.strip():
            return {"contentType": "HTML", "content": neu}
        zitat = (
            f"<pre>{html.escape(vorhanden)}</pre>"
            if vorhandener_typ == "text"
            else vorhanden
        )
        return {"contentType": "HTML", "content": f"{neu}{zitat}"}

    if not vorhanden.strip():
        # Kein Zitat vorhanden (z.B. Ursprungsmail ohne Rumpf) — dann wie bisher.
        return {"contentType": "Text", "content": neu}

    if vorhandener_typ == "text":
        return {"contentType": "Text", "content": f"{neu}\n\n{vorhanden}"}

    return {
        "contentType": "HTML",
        "content": f"{_klartext_als_mailhtml(neu)}{vorhanden}",
    }


def _empfaenger(adressen: str | list[str] | None) -> list[dict]:
    """Komma-Liste oder Mehrfach-Argument -> Graph-Recipient-Objekte."""
    if not adressen:
        return []
    roh = adressen if isinstance(adressen, list) else [adressen]
    out = []
    for eintrag in roh:
        for a in str(eintrag).split(","):
            if a.strip():
                out.append({"emailAddress": {"address": a.strip()}})
    return out


def _kategorien(m: dict) -> list[str]:
    """Kategorien einer Nachricht, leer-tolerant."""
    return [c for c in (m.get("categories") or []) if c]


def kategorie_setzen(
    bestand: list[str], vorgang: str, *, entfernen: bool = False
) -> list[str]:
    """Neue Kategorienliste — ADDITIV, nicht ersetzend.

    Der Kern von ADR-286 §4.9 Stufe 1: eine Nachricht kann zu MEHREREN Vorgaengen
    gehoeren (die Antwort in Thread A beantwortet zugleich einen Punkt aus Thread B).
    Wer hier die Liste ersetzt statt zu ergaenzen, loescht mit dem zweiten Vorgang
    den ersten — und hat damit genau die Ordner-Beschraenkung nachgebaut, deren
    Ueberwindung der Zweck war.

    Idempotent auch bei abweichender Schreibweise; Reihenfolge bleibt stabil.
    """
    vorhanden = [c for c in bestand if c]
    if entfernen:
        return [c for c in vorhanden if c.casefold() != vorgang.casefold()]
    if any(c.casefold() == vorgang.casefold() for c in vorhanden):
        return list(vorhanden)
    return [*vorhanden, vorgang]


def cmd_kategorisieren(
    tok: str,
    *,
    vorgang: str,
    from_sub: str,
    subject_sub: str,
    source_path: str,
    days: int,
    yes: bool,
    entfernen: bool = False,
) -> None:
    """Ordnet die getroffenen Mails einem Vorgang zu bzw. loest die Zuordnung.

    Der Zustand liegt damit im Postfach des Verantwortlichen, nicht in einer
    zweiten Datenhaltung (ADR-286 §4.9). Reversibel; nichts wird verschoben
    oder geloescht.
    """
    hits = _match_messages(
        tok,
        from_sub=from_sub,
        subject_sub=subject_sub,
        days=days,
        source_path=source_path,
    )
    if not hits:
        print("Keine passenden Mails gefunden — nichts geändert.")
        return

    verb = "Zuordnung lösen" if entfernen else "Vorgang zuordnen"
    krit = (
        " & ".join(
            filter(
                None,
                [
                    f'Absender~"{from_sub}"' if from_sub else None,
                    f'Betreff~"{subject_sub}"' if subject_sub else None,
                ],
            )
        )
        or "ALLE"
    )
    print(
        f"{verb}: '{vorgang}' in '{source_path or 'inbox'}'  "
        f"(Kriterium: {krit}) — reversibel:"
    )
    for m in hits:
        vorher = _kategorien(m)
        nachher = kategorie_setzen(vorher, vorgang, entfernen=entfernen)
        zeichen = "=" if vorher == nachher else "->"
        print(
            f"  · {m.get('receivedDateTime', '')[:10]}  "
            f"{(m.get('subject') or '')[:42]:<42} "
            f"[{', '.join(vorher) or '—'}] {zeichen} [{', '.join(nachher) or '—'}]"
        )
    print(f"  = {len(hits)} Mail(s)")

    if not yes:
        try:
            if input(f"{verb}? [j/N] ").strip().lower() not in ("j", "ja", "y", "yes"):
                sys.exit("Abgebrochen — nichts geändert.")
        except EOFError:
            sys.exit("Kein --yes und keine Eingabe — abgebrochen.")

    ok = unveraendert = 0
    for m in hits:
        vorher = _kategorien(m)
        nachher = kategorie_setzen(vorher, vorgang, entfernen=entfernen)
        if vorher == nachher:
            unveraendert += 1
            continue
        r = _http(
            "PATCH",
            f"{GRAPH}/me/messages/{urllib.parse.quote(m['id'], safe='')}",
            headers=_auth(tok),
            json_body={"categories": nachher},
        )
        if r.status_code in (200, 201):
            ok += 1
        else:
            print(
                f"  ! Fehler bei einer Mail: HTTP {r.status_code} — {r.text[:120]}",
                file=sys.stderr,
            )
    nachsatz = f", {unveraendert} bereits so" if unveraendert else ""
    print(f"OK: {ok}/{len(hits)} Mail(s) — {verb} '{vorgang}'{nachsatz}.")


def cmd_kategorien_listen(tok: str, *, days: int, source_path: str) -> None:
    """Inventar: welche Vorgaenge sind vergeben, wie viele Mails haengen daran.

    Ausgewiesen wird auch die RESTMENGE ohne Zuordnung — sie ist die Kennzahl,
    nicht die Trefferzahl (ADR-284 §7a).
    """
    hits = _match_messages(
        tok, from_sub="", subject_sub="", days=days, source_path=source_path
    )
    zaehler: Counter = Counter()
    ohne = 0
    for m in hits:
        kats = _kategorien(m)
        if not kats:
            ohne += 1
        for c in kats:
            zaehler[c] += 1
    if not zaehler:
        print(
            f"Keine Vorgangs-Zuordnung in '{source_path or 'inbox'}' "
            f"({len(hits)} Mails geprüft)."
        )
        return
    print(f"Vorgänge in '{source_path or 'inbox'}' ({len(hits)} Mails geprüft):")
    for name, n in zaehler.most_common():
        print(f"  {n:>5}  {name}")
    print(f"  {ohne:>5}  (ohne Zuordnung)")


def cmd_draft(
    tok: str,
    to: str,
    subject: str,
    body: str,
    reply_to: str | None,
    attach: list[str] | None = None,
    cc: list[str] | None = None,
    ist_html: bool = False,
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
        angelegt = r.json()
        did = angelegt["id"]

        # createReply legt den zitierten Urspruchstext bereits an. Ein PATCH mit
        # body.content ERSETZT den ganzen Rumpf — und loeschte damit genau dieses
        # Zitat (gemessen 2026-07-30: der Entwurf enthielt nur den neuen Text plus
        # Signatur). Deshalb wird der vorhandene Rumpf gelesen und der neue Text
        # DAVOR gesetzt, wie es ein Mail-Programm beim Antworten tut.
        vorhanden = (angelegt.get("body") or {}).get("content") or ""
        vorhandener_typ = (
            (angelegt.get("body") or {}).get("contentType") or ""
        ).lower()

        patch = {
            "body": _antwort_rumpf(
                body, vorhanden, vorhandener_typ, neu_ist_html=ist_html
            )
        }
        if subject:
            patch["subject"] = subject
        if cc:
            patch["ccRecipients"] = _empfaenger(cc)
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
        "body": {"contentType": "HTML" if ist_html else "Text", "content": body},
        "toRecipients": _empfaenger(to),
    }
    if cc:
        body_json["ccRecipients"] = _empfaenger(cc)
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
        "--flag",
        action="store_true",
        help="passende Mails zur Nachverfolgung markieren (Follow-up-Flag)",
    )
    g.add_argument(
        "--unflag",
        action="store_true",
        help="Nachverfolgungs-Markierung wieder entfernen",
    )
    g.add_argument(
        "--importance",
        choices=["high", "normal", "low"],
        help="Wichtigkeit passender Mails setzen (nur M365/Graph)",
    )
    g.add_argument(
        "--move-folder",
        metavar="QUELLPFAD",
        help="ganzen Ordner unter --to-parent verschieben",
    )
    g.add_argument("--find", action="store_true", help="Mails suchen (read-only)")
    g.add_argument(
        "--categorize",
        metavar="VORGANG",
        help="Mails einem Vorgang zuordnen (Kategorie, ADDITIV — Mehrfachzuordnung möglich)",
    )
    g.add_argument(
        "--uncategorize", metavar="VORGANG", help="Vorgangs-Zuordnung wieder lösen"
    )
    g.add_argument(
        "--list-categories",
        action="store_true",
        help="Inventar der Vorgänge im Ordner samt Restmenge ohne Zuordnung",
    )
    g.add_argument(
        "--show", metavar="ID|latest", help="eine Mail vollständig lesen (read-only)"
    )
    g.add_argument("--draft", action="store_true")
    g.add_argument(
        "--attach-to",
        metavar="messageId",
        help="Anhang/Anhänge an einen bestehenden Entwurf hängen",
    )
    g.add_argument(
        "--trash",
        metavar="messageId",
        help="eine bestimmte Mail/Entwurf per ID in den Papierkorb verschieben (reversibel)",
    )
    ap.add_argument(
        "--all",
        action="store_true",
        help="bei --find: Ordner VOLLSTÄNDIG aufzählen, ohne Absender-/Betreff-Filter "
        "(korrekter Weg statt eines Platzhalters wie --from '@', der Absender ohne "
        "SMTP-Adresse still verwirft — s. #1480)",
    )
    ap.add_argument(
        "--category",
        metavar="VORGANG",
        help="bei --find: nur Mails dieses Vorgangs",
    )
    ap.add_argument(
        "--cc",
        action="append",
        metavar="ADRESSE",
        help="Cc bei --draft (mehrfach möglich)",
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
    ap.add_argument(
        "--id",
        action="append",
        metavar="MESSAGEID",
        help="genau diese Nachricht verschieben (Graph-messageId); mehrfach "
        "moeglich. Alternative zu --from bei --move.",
    )
    ap.add_argument("--subject", default="")
    ap.add_argument("--body-file")
    ap.add_argument("--reply-to")
    ap.add_argument(
        "--max-chars", type=int, default=2000, help="Body-Kürzung bei --show"
    )
    ap.add_argument(
        "--save-attachments",
        metavar="DIR",
        help="bei --show: Datei-Anhänge in DIR speichern (read-only auf dem Postfach)",
    )
    ap.add_argument("--yes", action="store_true")
    ap.add_argument(
        "--role",
        default=None,
        help="Rollen-ID aus der Registry (KONZ-033) für --draft: setzt Signatur/"
        "Pflicht-Footer und erzwingt die Kanal-Grenze (#1481)",
    )
    ap.add_argument("--registry", default=None, help="alternative Rollen-Registry")
    ap.add_argument(
        "--design",
        action="store_true",
        help="mit --role: Klartext im Rollen-Design als HTML-Mail rendern "
        "(Signatur/Footer kommen aus dem Design, nicht angehängt)",
    )
    ap.add_argument(
        "--eyebrow",
        default=None,
        help="Kopfzeile über der Anrede bei --design (Default: Betreff)",
    )
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
        if not args.to:
            ap.error("--move braucht --to")
        if not (args.from_sub or args.id):
            ap.error("--move braucht --from oder --id")
        cmd_move(
            tok, args.from_sub or "", args.to, args.source, args.yes, args.subject,
            args.id,
        )
    elif args.flag or args.unflag:
        if not (args.from_sub or args.subject):
            ap.error("--flag/--unflag braucht --from und/oder --subject")
        status = "flagged" if args.flag else "notFlagged"
        label = (
            "Zur Nachverfolgung markieren"
            if args.flag
            else "Nachverfolgungs-Markierung entfernen"
        )
        cmd_mark(
            tok,
            from_sub=args.from_sub or "",
            subject_sub=args.subject,
            source_path=args.source,
            days=args.days,
            yes=args.yes,
            patch={"flag": {"flagStatus": status}},
            label=label,
        )
    elif args.importance:
        if not (args.from_sub or args.subject):
            ap.error("--importance braucht --from und/oder --subject")
        cmd_mark(
            tok,
            from_sub=args.from_sub or "",
            subject_sub=args.subject,
            source_path=args.source,
            days=args.days,
            yes=args.yes,
            patch={"importance": args.importance},
            label=f"Wichtigkeit={args.importance} setzen",
        )
    elif args.move_folder:
        if not args.to_parent:
            ap.error("--move-folder braucht --to-parent ZIEL-ELTERNORDNER")
        cmd_move_folder(tok, args.move_folder, args.to_parent)
    elif args.find:
        if not (args.from_sub or args.subject or args.all or args.category):
            ap.error(
                "--find braucht --from und/oder --subject — oder --all für den ganzen Ordner"
            )
        if args.all and (args.from_sub or args.subject):
            ap.error(
                "--all schließt --from/--subject aus (--all zählt vollständig auf)"
            )
        cmd_find(
            tok,
            "" if args.all else (args.from_sub or ""),
            "" if args.all else args.subject,
            args.days,
            args.source,
            category=args.category or "",
        )
    elif args.list_categories:
        cmd_kategorien_listen(tok, days=args.days, source_path=args.source)
    elif args.categorize or args.uncategorize:
        vorgang = args.categorize or args.uncategorize
        if not (args.from_sub or args.subject):
            ap.error("--categorize/--uncategorize braucht --from und/oder --subject")
        cmd_kategorisieren(
            tok,
            vorgang=vorgang,
            from_sub=args.from_sub or "",
            subject_sub=args.subject or "",
            source_path=args.source,
            days=args.days,
            yes=args.yes,
            entfernen=bool(args.uncategorize),
        )
    elif args.show:
        cmd_show(
            tok,
            args.show,
            args.from_sub or "",
            args.subject,
            args.days,
            args.source,
            args.max_chars,
            args.save_attachments,
        )
    elif args.attach_to:
        if not args.attach:
            ap.error("--attach-to braucht mindestens ein --attach PFAD")
        cmd_attach_to(tok, args.attach_to, args.attach)
    elif args.trash:
        cmd_trash(tok, args.trash)
    else:  # --draft
        if not args.body_file:
            ap.error("--draft braucht --body-file (und --to ODER --reply-to)")
        if not (args.to or args.reply_to):
            ap.error("--draft braucht --to ODER --reply-to")
        body = Path(args.body_file).read_text()
        ist_html = False
        if args.design and not args.role:
            ap.error("--design braucht --role (das Design kommt aus der Rolle)")
        if args.role:
            try:
                profile = roles.resolve(args.role, args.registry)
            except (FileNotFoundError, ValueError) as e:
                sys.exit(f"FEHLER: {e}")
            if profile.transport != "graph_draft":
                sys.exit(
                    f"FEHLER: Rolle '{profile.role_id}' hat transport "
                    f"'{profile.transport}', graph_mail --draft bedient nur "
                    "'graph_draft' — für smtp send_mail, für imap_append draft_mail."
                )
            # Pre-Send-Gate (#1481) VOR dem Anlegen des Entwurfs.
            try:
                roles.pruefe_kanalgrenze(profile, args.subject, body)
            except roles.KanalgrenzeVerletzt as e:
                sys.exit(f"ABBRUCH (Kanal-Grenze): {e}")
            if args.design:
                bausteine = roles.zerlege_klartext(body)
                body = roles.render_email_html(
                    profile,
                    eyebrow=args.eyebrow or args.subject or "",
                    subject=args.subject or "",
                    **bausteine,
                )
                ist_html = True
            else:
                body = roles.text_mit_signatur(profile, body)
            print(
                f"Rolle: {profile.role_id} ({profile.display_name}) — {profile.sender}"
                + (" · Design" if args.design else "")
            )
        cmd_draft(
            tok,
            args.to or "",
            args.subject,
            body,
            args.reply_to,
            args.attach,
            args.cc,
            ist_html,
        )


if __name__ == "__main__":
    main()
