#!/usr/bin/env python3
"""Microsoft-365-Kalender-Anbindung (Weg B, Owner-Entscheid 2026-07-17) — Lese-Zugriff
über Microsoft Graph mit Geräte-Anmeldung (Device-Code-Flow).

Charta-Eigenschaften (KONZ-025):
- KEINE Passwörter — Anmeldung einmalig interaktiv im Browser des Kapitäns (MFA-fest);
  gespeichert werden nur Zugangs-/Refresh-Token (chmod 600), Werte erscheinen nie in stdout.
- Nur Lese-Scope (Calendars.Read). Schreiben/Löschen von Terminen ist nicht implementiert.
- Maschinen-Gate: läuft nur, wo ~/.claude/calendar.env existiert (Capability-Profil).
- Termine enthalten Daten Dritter (Art. 3.2): Ausgaben sind für den Kapitäns-Kanal,
  nie für Memory/Repo-Übernahme.

Konfiguration ~/.claude/calendar.env:
  GRAPH_ACCOUNTS=achim.dehnert@iil.gmbh,achim.dehnert@hnu.de
  GRAPH_CLIENT_ID=<public-client-id>   # Default: Microsoft Graph Command Line Tools
  GRAPH_TENANT=organizations
  TOKEN_DIR=~/.claude/calendar-tokens
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import stat
import sys
import time
from pathlib import Path

import requests

CONFIG_FILE = Path.home() / ".claude" / "calendar.env"
DEFAULT_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # MS Graph Command Line Tools (public)
# Per-Konto-Override: GRAPH_CLIENT_ID_<DOMAIN mit _ statt .> — z. B. GRAPH_CLIENT_ID_HNU_DE.
# Grund: Conditional-Access mancher Mandanten (Realfall HNU 2026-07-17) blockt einzelne
# Public Clients; ein anderer Microsoft-Standard-Client ist oft freigeschaltet.
SCOPES = "Calendars.Read offline_access openid profile"
TIMEZONE = "W. Europe Standard Time"


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip("'\"")
    return values


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        sys.exit(f"FEHLER: {CONFIG_FILE} fehlt — Maschine ist für Kalender nicht freigegeben (Capability-Profil)")
    cfg = parse_env(CONFIG_FILE)
    accounts = [a.strip() for a in cfg.get("GRAPH_ACCOUNTS", "").split(",") if a.strip()]
    if not accounts:
        sys.exit("FEHLER: GRAPH_ACCOUNTS leer in calendar.env")
    token_dir = Path(cfg.get("TOKEN_DIR", "~/.claude/calendar-tokens")).expanduser()
    token_dir.mkdir(parents=True, exist_ok=True)
    token_dir.chmod(stat.S_IRWXU)
    default_client = cfg.get("GRAPH_CLIENT_ID", DEFAULT_CLIENT_ID)
    client_for = {}
    for acc in accounts:
        domain_key = "GRAPH_CLIENT_ID_" + acc.split("@", 1)[1].replace(".", "_").upper()
        client_for[acc] = cfg.get(domain_key, default_client)
    return {
        "accounts": accounts,
        "client_for": client_for,
        "tenant": cfg.get("GRAPH_TENANT", "organizations"),
        "token_dir": token_dir,
    }


def token_path(cfg: dict, account: str) -> Path:
    return cfg["token_dir"] / (account.replace("@", "_at_") + ".json")


def save_tokens(path: Path, tokens: dict) -> None:
    tokens["_saved_at"] = int(time.time())
    path.write_text(json.dumps(tokens))
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def cmd_login(cfg: dict, account: str) -> None:
    if account not in cfg["accounts"]:
        sys.exit(f"FEHLER: {account} steht nicht in GRAPH_ACCOUNTS")
    base = f"https://login.microsoftonline.com/{cfg['tenant']}/oauth2/v2.0"
    client_id = cfg["client_for"][account]
    r = requests.post(f"{base}/devicecode", data={"client_id": client_id, "scope": SCOPES}, timeout=20)
    if r.status_code != 200:
        sys.exit(f"FEHLER: Device-Code-Anfrage {r.status_code} — {r.json().get('error_description', '')[:200]}")
    dc = r.json()
    print(f"\n>>> Anmeldung für {account}:")
    print(f">>> {dc['message']}\n")
    print("(Warte auf Bestätigung im Browser — MFA der Hochschule/Firma funktioniert hier normal.)")
    deadline = time.time() + int(dc.get("expires_in", 900))
    while time.time() < deadline:
        time.sleep(int(dc.get("interval", 5)))
        tr = requests.post(f"{base}/token", data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id,
            "device_code": dc["device_code"],
        }, timeout=20)
        body = tr.json()
        if tr.status_code == 200:
            save_tokens(token_path(cfg, account), body)
            who = requests.get("https://graph.microsoft.com/v1.0/me",
                               headers={"Authorization": f"Bearer {body['access_token']}"},
                               timeout=20).json()
            print(f"OK: angemeldet als {who.get('userPrincipalName', account)} — Token gespeichert (nur lesend, Calendars.Read)")
            return
        if body.get("error") in ("authorization_pending", "slow_down"):
            continue
        sys.exit(f"FEHLER: {body.get('error')} — {body.get('error_description', '')[:200]}")
    sys.exit("FEHLER: Anmeldezeit abgelaufen — bitte erneut starten")


def get_access_token(cfg: dict, account: str) -> str | None:
    p = token_path(cfg, account)
    if not p.exists():
        return None
    tokens = json.loads(p.read_text())
    age = int(time.time()) - tokens.get("_saved_at", 0)
    if age < int(tokens.get("expires_in", 3599)) - 120:
        return tokens["access_token"]
    base = f"https://login.microsoftonline.com/{cfg['tenant']}/oauth2/v2.0"
    tr = requests.post(f"{base}/token", data={
        "grant_type": "refresh_token",
        "client_id": cfg["client_for"][account],
        "refresh_token": tokens.get("refresh_token", ""),
        "scope": SCOPES,
    }, timeout=20)
    if tr.status_code != 200:
        return None
    body = tr.json()
    if "refresh_token" not in body:
        body["refresh_token"] = tokens.get("refresh_token", "")
    save_tokens(p, body)
    return body["access_token"]


def cmd_status(cfg: dict) -> None:
    for acc in cfg["accounts"]:
        tok = get_access_token(cfg, acc)
        print(f"{acc}: {'✔ angemeldet' if tok else '✘ nicht angemeldet — --login ' + acc}")


def cmd_list(cfg: dict, days: int) -> None:
    start = dt.datetime.now(dt.timezone.utc)
    end = start + dt.timedelta(days=days)
    rows = []
    for acc in cfg["accounts"]:
        tok = get_access_token(cfg, acc)
        if not tok:
            print(f"({acc}: nicht angemeldet — überspringe; --login {acc})", file=sys.stderr)
            continue
        tag = "IIL" if "iil" in acc else ("HNU" if "hnu" in acc else acc.split("@")[1][:3].upper())
        url = ("https://graph.microsoft.com/v1.0/me/calendarView"
               f"?startDateTime={start.strftime('%Y-%m-%dT%H:%M:%S')}Z"
               f"&endDateTime={end.strftime('%Y-%m-%dT%H:%M:%S')}Z"
               "&$orderby=start/dateTime&$top=50"
               "&$select=subject,start,end,location,isOnlineMeeting,organizer,isAllDay")
        r = requests.get(url, headers={"Authorization": f"Bearer {tok}",
                                       "Prefer": f'outlook.timezone="{TIMEZONE}"'}, timeout=30)
        if r.status_code != 200:
            print(f"({acc}: Abruf fehlgeschlagen HTTP {r.status_code})", file=sys.stderr)
            continue
        for ev in r.json().get("value", []):
            s = ev["start"]["dateTime"][:16].replace("T", " ")
            e = ev["end"]["dateTime"][11:16]
            loc = (ev.get("location") or {}).get("displayName", "")
            extras = " · online" if ev.get("isOnlineMeeting") else (f" · {loc}" if loc else "")
            when = s[:10] + " ganztags" if ev.get("isAllDay") else f"{s}–{e}"
            rows.append((ev["start"]["dateTime"], f"[{tag}] {when}  {ev.get('subject', '(ohne Titel)')}{extras}"))
    if not rows:
        print("Keine Termine im Zeitraum (oder keine Konten angemeldet).")
        return
    for _, line in sorted(rows):
        print(line)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--login", metavar="KONTO", help="einmalige Geräte-Anmeldung für ein Konto")
    g.add_argument("--status", action="store_true", help="Anmeldestatus beider Konten")
    g.add_argument("--today", action="store_true", help="heutige Termine beider Konten")
    g.add_argument("--list", type=int, metavar="TAGE", help="Termine der nächsten N Tage")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    cfg = load_config()
    if args.login:
        cmd_login(cfg, args.login)
    elif args.status:
        cmd_status(cfg)
    elif args.today:
        cmd_list(cfg, 1)
    else:
        cmd_list(cfg, args.list)


if __name__ == "__main__":
    main()
