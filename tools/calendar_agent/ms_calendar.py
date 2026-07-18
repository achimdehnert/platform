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
# Calendars.ReadWrite (Stufe A, Owner-Entscheid 2026-07-18): der Lotse darf in den
# EIGENEN Kalender schreiben. Einladungen an Dritte (Stufe B) sind bewusst NICHT gebaut —
# cmd_create verweigert jeden Teilnehmer hart (Außenwirkung = eigenes Gate, Art. 7).
SCOPES = "Calendars.ReadWrite offline_access openid profile"
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


# ---------- ICS-Abo (Plan C, z. B. HNU: Conditional Access 53003 blockt Public Clients) ----------

BERLIN = None
try:
    from zoneinfo import ZoneInfo
    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    BERLIN = dt.timezone(dt.timedelta(hours=2))

WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def ics_path(cfg: dict, account: str) -> Path:
    return cfg["token_dir"] / (account.replace("@", "_at_") + ".ics_url")


def _parse_ics_dt(val: str) -> tuple[dt.datetime, bool]:
    """ICS-Zeit → (aware datetime Europe/Berlin, ganztags?). TZID wird als Berlin gelesen
    (ehrliche Vereinfachung für die HNU; abweichende TZIDs wären hier falsch verortet)."""
    if len(val) == 8:  # VALUE=DATE
        d = dt.datetime.strptime(val, "%Y%m%d").replace(tzinfo=BERLIN)
        return d, True
    if val.endswith("Z"):
        d = dt.datetime.strptime(val, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
        return d.astimezone(BERLIN), False
    return dt.datetime.strptime(val, "%Y%m%dT%H%M%S").replace(tzinfo=BERLIN), False


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def ics_events(url: str, win_start: dt.datetime, win_end: dt.datetime):
    """Liefert (start, ende, titel, ort, ganztags) im Fenster. Serien: FREQ=DAILY/WEEKLY
    (INTERVAL/BYDAY/UNTIL/COUNT) werden expandiert; andere FREQ nur als Erst-Termin —
    bewusste v1-Grenze, im Output nicht markiert erscheinende Folgetermine möglich."""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    for block in r.text.split("BEGIN:VEVENT")[1:]:
        body = block.split("END:VEVENT")[0]
        props: dict[str, str] = {}
        for line in _unfold(body):
            if ":" not in line:
                continue
            key, _, val = line.partition(":")
            props.setdefault(key.split(";")[0].upper(), val.strip())
        if "DTSTART" not in props:
            continue
        start, allday = _parse_ics_dt(props["DTSTART"])
        dur = dt.timedelta(hours=1)
        if "DTEND" in props:
            end_dt, _ = _parse_ics_dt(props["DTEND"])
            dur = end_dt - start
        title = props.get("SUMMARY", "(ohne Titel)").replace("\\,", ",").replace("\\n", " · ")
        loc = props.get("LOCATION", "").replace("\\,", ",")
        rrule = dict(p.split("=", 1) for p in props.get("RRULE", "").split(";") if "=" in p)
        freq = rrule.get("FREQ", "")
        if freq not in ("DAILY", "WEEKLY"):
            if win_start <= start < win_end:
                yield start, start + dur, title, loc, allday
            continue
        interval = int(rrule.get("INTERVAL", "1"))
        until = None
        if "UNTIL" in rrule:
            until, _ = _parse_ics_dt(rrule["UNTIL"])
        count = int(rrule["COUNT"]) if "COUNT" in rrule else None
        bydays = {WEEKDAYS[d] for d in rrule.get("BYDAY", "").split(",") if d in WEEKDAYS} \
                 or {start.weekday()}
        occ, made, day = 0, 0, start
        while day < win_end and made < 500:
            fits_interval = (freq == "DAILY" and ((day - start).days % interval == 0)) or \
                            (freq == "WEEKLY" and (((day - start).days // 7) % interval == 0))
            if day.weekday() in bydays and fits_interval and day >= start:
                occ += 1
                if count and occ > count:
                    break
                if until and day > until:
                    break
                if day >= win_start:
                    yield day, day + dur, title, loc, allday
                made += 1
            day += dt.timedelta(days=1)


def cmd_login(cfg: dict, account: str) -> None:
    if ics_path(cfg, account).exists():
        sys.exit(f"{account} läuft über den Abo-Link (ICS) — keine Anmeldung nötig/möglich.")
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
        if ics_path(cfg, acc).exists():
            print(f"{acc}: ✔ Abo-Link (ICS, nur lesend)")
            continue
        tok = get_access_token(cfg, acc)
        print(f"{acc}: {'✔ angemeldet' if tok else '✘ nicht angemeldet — --login ' + acc}")


def cmd_list(cfg: dict, days: int) -> None:
    start = dt.datetime.now(dt.timezone.utc)
    end = start + dt.timedelta(days=days)
    rows = []
    for acc in cfg["accounts"]:
        tag = "IIL" if "iil" in acc else ("HNU" if "hnu" in acc else acc.split("@")[1][:3].upper())
        ipath = ics_path(cfg, acc)
        if ipath.exists():
            try:
                url = ipath.read_text().strip()
                b_start = start.astimezone(BERLIN)
                b_end = end.astimezone(BERLIN)
                for s, e, title, loc, allday in ics_events(url, b_start, b_end):
                    extras = f" · {loc}" if loc else ""
                    when = s.strftime("%Y-%m-%d") + " ganztags" if allday else \
                        s.strftime("%Y-%m-%d %H:%M") + "–" + e.strftime("%H:%M")
                    rows.append((s.isoformat(), f"[{tag}] {when}  {title}{extras}"))
            except Exception as exc:
                print(f"({acc}: Abo-Link-Abruf fehlgeschlagen — {type(exc).__name__})", file=sys.stderr)
            continue
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


def parse_local(s: str) -> str:
    """'YYYY-MM-DD HH:MM' (Europe/Berlin) → Graph-dateTime-String (ohne Zone; TZ via Objekt)."""
    s = s.strip().replace("T", " ")
    dt.datetime.strptime(s, "%Y-%m-%d %H:%M")  # validiert; wirft bei Unfug
    return s.replace(" ", "T") + ":00"


def build_event_body(subject: str, start: str, end: str, location: str, note: str) -> dict:
    body = {
        "subject": subject,
        "start": {"dateTime": parse_local(start), "timeZone": TIMEZONE},
        "end": {"dateTime": parse_local(end), "timeZone": TIMEZONE},
    }
    if location:
        body["location"] = {"displayName": location}
    if note:
        body["body"] = {"contentType": "text", "content": note}
    # Stufe-A-Riegel: niemals Teilnehmer setzen — das wäre Außenwirkung (Stufe B, Art. 7).
    body["attendees"] = []
    return body


def cmd_create(cfg: dict, account: str, args) -> None:
    if account not in cfg["accounts"]:
        sys.exit(f"FEHLER: {account} steht nicht in GRAPH_ACCOUNTS")
    tok = get_access_token(cfg, account)
    if not tok:
        sys.exit(f"FEHLER: {account} nicht angemeldet — erst: --login {account}")
    body = build_event_body(args.subject, args.start, args.end, args.location or "", args.note or "")
    # Bestätigungs-Anzeige (auch bei Eigen-Kalender — es ist ein Schreibvorgang)
    print("Anzulegen im EIGENEN Kalender (keine Einladung an Dritte):")
    print(f"  Wann:    {args.start} – {args.end}  ({TIMEZONE})")
    print(f"  Betreff: {args.subject}")
    if args.location:
        print(f"  Ort:     {args.location}")
    if not args.yes:
        try:
            if input("Anlegen? [j/N] ").strip().lower() not in ("j", "ja", "y", "yes"):
                sys.exit("Abgebrochen — nichts angelegt.")
        except EOFError:
            sys.exit("Kein --yes und keine Eingabe möglich — abgebrochen.")
    r = requests.post("https://graph.microsoft.com/v1.0/me/events",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                      json=body, timeout=30)
    if r.status_code == 403:
        sys.exit("FEHLER: nur Lese-Recht vorhanden — bitte einmal neu anmelden (--login "
                 f"{account}), damit das erweiterte Schreib-Recht erteilt wird.")
    if r.status_code not in (200, 201):
        sys.exit(f"FEHLER: Anlegen fehlgeschlagen HTTP {r.status_code} — {r.text[:200]}")
    ev = r.json()
    print(f"OK: Termin angelegt — '{ev.get('subject')}' am {args.start} (nur dein Kalender, niemand eingeladen)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--login", metavar="KONTO", help="einmalige Geräte-Anmeldung für ein Konto")
    g.add_argument("--status", action="store_true", help="Anmeldestatus beider Konten")
    g.add_argument("--today", action="store_true", help="heutige Termine beider Konten")
    g.add_argument("--list", type=int, metavar="TAGE", help="Termine der nächsten N Tage")
    g.add_argument("--create", action="store_true",
                   help="Termin im EIGENEN Kalender anlegen (Stufe A, keine Einladung an Dritte)")
    ap.add_argument("--account", help="Zielkonto (Default: erstes in GRAPH_ACCOUNTS)")
    ap.add_argument("--subject", help="Betreff (bei --create)")
    ap.add_argument("--start", help="Start 'YYYY-MM-DD HH:MM' (Europe/Berlin)")
    ap.add_argument("--end", help="Ende 'YYYY-MM-DD HH:MM'")
    ap.add_argument("--location", help="Ort (optional)")
    ap.add_argument("--note", help="Notiz im Termin-Text (optional)")
    ap.add_argument("--yes", action="store_true", help="ohne Rückfrage anlegen (Gate-Anzeige aus)")
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
    elif args.create:
        if not (args.subject and args.start and args.end):
            ap.error("--create braucht --subject, --start und --end")
        cmd_create(cfg, args.account or cfg["accounts"][0], args)
    else:
        cmd_list(cfg, args.list)


if __name__ == "__main__":
    main()
