#!/usr/bin/env python3
"""Kalender eines On-Prem-Exchange über EWS (Exchange Web Services) — Lesen sowie Anlegen,
Ändern und Löschen im EIGENEN Kalender (Stufe A wie ms_calendar.py, Auftrag #3300).

Warum ein zweiter Draht neben ms_calendar.py (Graph): Der HNU-Mandant blockt jeden
Public Client per Conditional Access (Graph-Fehler 53003, Gerätestatus „Unregistered"),
und das HNU-Postfach liegt gar nicht in Exchange Online, sondern auf einem On-Prem-Exchange
(outlook.hnu.de, Exchange 2019). Dessen EWS-Endpunkt nimmt NTLM mit derselben Kennung, mit
der der IMAP-Draht seit 2026-07-21 läuft (reference_hnu_mailbox_imap_access). Graph sieht
diesen Kalender nie — EWS ist der Weg. Belege: docs/runbooks/hnu-kalender-ews.md.

Charta-Eigenschaften (KONZ-025):
- Konfiguration = die Mail-Config des Postfachs (~/.claude/mail-<KONTO>.env, Schlüssel
  IMAP_HOST/MAIL_LOGIN/MAIL_CREDS_FILE; optional EWS_URL). Maschinen-Gate: ohne diese
  Datei läuft nichts. Kein neues Credential, keine Rechte-Ausweitung — dieselbe Kennung,
  anderer Kanal (Kriterium 4 in #3300).
- NTLM macht curl (Systemwerkzeug, --ntlm). Das Passwort geht nur über stdin in die
  curl-Konfiguration — nie auf die Kommandozeile, nie in die Umgebung, nie nach stdout.
- Schreiben nur im EIGENEN Kalender, nie Teilnehmer (Stufe A). --update/--delete fassen
  hart (Exit 3, keine Ausnahme über --yes) NICHT an: Besprechungen (IsMeeting), fremde
  Einladungen (nicht Organisator) und Serientermine — sonst gingen Absagen/Updates an
  Dritte (Außenwirkung, Art. 7).
- Termine enthalten Daten Dritter (Art. 3.2): Ausgaben sind für den Kapitäns-Kanal,
  nie für Memory/Repo-Übernahme.

Aufrufe:
  --account hnu --status
      Verdrahtungsprobe: EWS-Endpunkt, Anmeldung, Kalenderordner (Anzahl Einträge).
  --account hnu --list TAGE [--ids] | --today
      Termine der nächsten N Tage (Serien vom Server expandiert). Mit --ids je Termin
      eine Kennung (letzte 12 Zeichen der EWS-ItemId), besprechung=ja/nein,
      organisator=ja/nein, "serie" bei Serienterminen.
  --account hnu --create --subject … --start 'YYYY-MM-DD HH:MM' --end '…' [--location …]
      [--note …] [--yes]
  --account hnu --update KENNUNG [--subject …] [--start …] [--end …] [--location …]
      [--note …] [--tage N] [--yes]
  --account hnu --delete KENNUNG [--tage N] [--yes]
      Kennung wird über ein Listenfenster (Default 60 Tage, --tage N) eindeutig zur
      ItemId aufgelöst — 0 oder >1 Treffer beenden mit Exit 2.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

# Config-/Credentials-Parsing aus send_mail (eine SSoT, wie read_mail.py).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mail_agent"))
from send_mail import load_credentials, login_name, parse_env  # noqa: E402

try:
    from zoneinfo import ZoneInfo

    BERLIN = ZoneInfo("Europe/Berlin")
except Exception:  # pragma: no cover
    BERLIN = dt.timezone(dt.timedelta(hours=2))

NS = {
    "s": "http://schemas.xmlsoap.org/soap/envelope/",
    "t": "http://schemas.microsoft.com/exchange/services/2006/types",
    "m": "http://schemas.microsoft.com/exchange/services/2006/messages",
}
TIMEZONE = "W. Europe Standard Time"
CURL_TIMEOUT = 60
DEFAULT_WINDOW_DAYS = 60


# ---------- Konfiguration ----------


def config_path(account: str) -> Path:
    """--account NAME → ~/.claude/mail-<NAME>.env (Guard-sicher: kein .env-Pfad als Argument)."""
    return Path.home() / ".claude" / f"mail-{account}.env"


def load_config(account: str) -> dict:
    path = config_path(account)
    if not path.exists():
        sys.exit(
            f"FEHLER: {path} fehlt — Maschine ist für dieses Postfach nicht freigegeben "
            "(Capability-Profil)"
        )
    cfg = parse_env(path)
    host = cfg.get("EWS_HOST") or cfg.get("IMAP_HOST")
    if not host:
        sys.exit(f"FEHLER: weder EWS_HOST noch IMAP_HOST in {path}")
    creds_file = Path(cfg.get("MAIL_CREDS_FILE", "")).expanduser()
    if not creds_file.is_file():
        sys.exit(f"FEHLER: MAIL_CREDS_FILE fehlt oder unlesbar ({path})")
    return {
        "account": account,
        "url": cfg.get("EWS_URL") or f"https://{host}/EWS/Exchange.asmx",
        "login": login_name(cfg),
        "creds_file": creds_file,
        "mailbox": cfg.get("MAIL_FROM", ""),
    }


# ---------- Transport: curl --ntlm, Passwort nur über stdin ----------


def curl_config(user: str, password: str) -> str:
    """curl-Konfigurationstext (für `-K -`). Backslash und Anführungszeichen werden nach
    curl-Regeln escaped — sonst würde ein Passwort mit `"` die Zeile abschneiden."""

    def q(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    return f'user = "{q(user)}:{q(password)}"\n'


def ews_call(cfg: dict, body_xml: str, timeout: int = CURL_TIMEOUT) -> tuple[int, str]:
    """Ein SOAP-Aufruf gegen EWS. Rückgabe (HTTP-Status, Antworttext). Das Passwort geht
    ausschließlich über stdin in curl (-K -), der SOAP-Body über eine Datei ohne Secrets."""
    user, password = load_credentials(cfg["creds_file"], cfg["login"])
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<soap:Envelope xmlns:soap="{NS["s"]}" xmlns:t="{NS["t"]}" xmlns:m="{NS["m"]}">'
        '<soap:Header><t:RequestServerVersion Version="Exchange2016"/>'
        f'<t:TimeZoneContext><t:TimeZoneDefinition Id="{TIMEZONE}"/></t:TimeZoneContext>'
        f"</soap:Header><soap:Body>{body_xml}</soap:Body></soap:Envelope>"
    )
    cmd = [
        "curl",
        "--silent",
        "--show-error",
        "--ntlm",
        "-K",
        "-",  # Zugangsdaten aus stdin
        "--max-time",
        str(timeout),
        "-H",
        "Content-Type: text/xml; charset=utf-8",
        "--data-binary",
        envelope,
        "--write-out",
        "\n%{http_code}",
        cfg["url"],
    ]
    proc = subprocess.run(
        cmd,
        input=curl_config(user, password),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.exit(f"FEHLER: curl Exit {proc.returncode} — {proc.stderr.strip()[:200]}")
    text, _, code = proc.stdout.rpartition("\n")
    return int(code or 0), text


# ---------- SOAP-Bausteine (netzfrei, testbar) ----------


def _iso_utc(d: dt.datetime) -> str:
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def body_get_calendar_folder() -> str:
    return (
        "<m:GetFolder><m:FolderShape><t:BaseShape>Default</t:BaseShape></m:FolderShape>"
        '<m:FolderIds><t:DistinguishedFolderId Id="calendar"/></m:FolderIds></m:GetFolder>'
    )


def body_find_items(start: dt.datetime, end: dt.datetime) -> str:
    """FindItem mit CalendarView — der Server expandiert Serien selbst (anders als der
    ICS-Parser in ms_calendar.py, der nur DAILY/WEEKLY kann)."""
    return (
        '<m:FindItem Traversal="Shallow"><m:ItemShape><t:BaseShape>IdOnly</t:BaseShape>'
        "<t:AdditionalProperties>"
        '<t:FieldURI FieldURI="item:Subject"/>'
        '<t:FieldURI FieldURI="calendar:Start"/>'
        '<t:FieldURI FieldURI="calendar:End"/>'
        '<t:FieldURI FieldURI="calendar:Location"/>'
        '<t:FieldURI FieldURI="calendar:IsAllDayEvent"/>'
        '<t:FieldURI FieldURI="calendar:CalendarItemType"/>'
        '<t:FieldURI FieldURI="calendar:IsMeeting"/>'
        '<t:FieldURI FieldURI="calendar:MyResponseType"/>'
        "</t:AdditionalProperties></m:ItemShape>"
        f'<m:CalendarView MaxEntriesReturned="500" StartDate="{_iso_utc(start)}" '
        f'EndDate="{_iso_utc(end)}"/>'
        '<m:ParentFolderIds><t:DistinguishedFolderId Id="calendar"/></m:ParentFolderIds>'
        "</m:FindItem>"
    )


def parse_local(s: str) -> dt.datetime:
    """'YYYY-MM-DD HH:MM' (Europe/Berlin) → aware datetime; wirft bei Unfug."""
    s = s.strip().replace("T", " ")
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=BERLIN)


def body_create_item(
    subject: str, start: str, end: str, location: str = "", note: str = ""
) -> str:
    """CreateItem ohne Teilnehmer, SendMeetingInvitations=SendToNone — Stufe-A-Riegel:
    es gibt schlicht kein Attendees-Element, das Außenwirkung erzeugen könnte."""
    s, e = parse_local(start), parse_local(end)
    if e <= s:
        sys.exit("FEHLER: --end muss nach --start liegen")
    parts = [f"<t:Subject>{escape(subject)}</t:Subject>"]
    if note:
        parts.append(f'<t:Body BodyType="Text">{escape(note)}</t:Body>')
    parts += [
        f"<t:Start>{s.isoformat()}</t:Start>",
        f"<t:End>{e.isoformat()}</t:End>",
        "<t:IsAllDayEvent>false</t:IsAllDayEvent>",
    ]
    if location:
        parts.append(f"<t:Location>{escape(location)}</t:Location>")
    parts += [
        f'<t:StartTimeZone Id="{TIMEZONE}"/>',
        f'<t:EndTimeZone Id="{TIMEZONE}"/>',
    ]
    return (
        '<m:CreateItem SendMeetingInvitations="SendToNone">'
        "<m:Items><t:CalendarItem>" + "".join(parts) + "</t:CalendarItem></m:Items>"
        "</m:CreateItem>"
    )


def body_update_item(item_id: str, change_key: str, fields: dict[str, str]) -> str:
    """UpdateItem per SetItemField, nur für die übergebenen Felder. Reihenfolge fest
    (Subject, Body, Start, End, Location) — EWS verlangt Schema-Reihenfolge."""
    order = (
        ("subject", "item:Subject", lambda v: f"<t:Subject>{escape(v)}</t:Subject>"),
        (
            "note",
            "item:Body",
            lambda v: f'<t:Body BodyType="Text">{escape(v)}</t:Body>',
        ),
        (
            "start",
            "calendar:Start",
            lambda v: f"<t:Start>{parse_local(v).isoformat()}</t:Start>",
        ),
        (
            "end",
            "calendar:End",
            lambda v: f"<t:End>{parse_local(v).isoformat()}</t:End>",
        ),
        (
            "location",
            "calendar:Location",
            lambda v: f"<t:Location>{escape(v)}</t:Location>",
        ),
    )
    sets = [
        f'<t:SetItemField><t:FieldURI FieldURI="{uri}"/><t:CalendarItem>{render(fields[key])}'
        "</t:CalendarItem></t:SetItemField>"
        for key, uri, render in order
        if fields.get(key) is not None
    ]
    if not sets:
        sys.exit(
            "FEHLER: --update ohne Feld (--subject/--start/--end/--location/--note)"
        )
    return (
        '<m:UpdateItem ConflictResolution="AutoResolve" '
        'SendMeetingInvitationsOrCancellations="SendToNone">'
        f'<m:ItemChanges><t:ItemChange><t:ItemId Id="{escape(item_id)}" '
        f'ChangeKey="{escape(change_key)}"/><t:Updates>'
        + "".join(sets)
        + "</t:Updates>"
        "</t:ItemChange></m:ItemChanges></m:UpdateItem>"
    )


def body_delete_item(item_id: str, change_key: str) -> str:
    return (
        '<m:DeleteItem DeleteType="MoveToDeletedItems" SendMeetingCancellations="SendToNone">'
        f'<m:ItemIds><t:ItemId Id="{escape(item_id)}" ChangeKey="{escape(change_key)}"/>'
        "</m:ItemIds></m:DeleteItem>"
    )


# ---------- Antwort-Auswertung ----------


def _txt(el: ET.Element | None, path: str) -> str:
    sub = el.find(path, NS) if el is not None else None
    return (sub.text or "") if sub is not None else ""


def response_error(xml_text: str) -> str | None:
    """None bei Erfolg, sonst ResponseCode (+ MessageText) — auch SOAP-Faults."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        root = None
    if root is None or root.tag != f"{{{NS['s']}}}Envelope":
        # Portal-/Login-HTML ist wohlgeformtes XML — deshalb Wurzel prüfen, nicht nur parsen.
        return "keine SOAP-Antwort (Anmeldung/Endpunkt?)"
    fault = root.find(".//s:Fault", NS)
    if fault is not None:
        return "SOAP-Fault: " + _txt(fault, "faultstring")
    for msg in root.iter():
        if msg.get("ResponseClass") in ("Error", "Warning"):
            return _txt(msg, "m:ResponseCode") + " " + _txt(msg, "m:MessageText")
    return None


def _to_berlin(iso: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(BERLIN)


def parse_items(xml_text: str) -> list[dict]:
    """FindItem-Antwort → Liste von Terminen (aware Berlin-Zeiten)."""
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iterfind(".//t:CalendarItem", NS):
        iid = it.find("t:ItemId", NS)
        items.append(
            {
                "id": iid.get("Id", "") if iid is not None else "",
                "change_key": iid.get("ChangeKey", "") if iid is not None else "",
                "subject": _txt(it, "t:Subject") or "(ohne Titel)",
                "start": _to_berlin(_txt(it, "t:Start")),
                "end": _to_berlin(_txt(it, "t:End")),
                "location": _txt(it, "t:Location"),
                "allday": _txt(it, "t:IsAllDayEvent") == "true",
                "type": _txt(it, "t:CalendarItemType") or "Single",
                "meeting": _txt(it, "t:IsMeeting") == "true",
                # MyResponseType=Organizer ⇔ eigenes Konto ist Organisator; bei
                # Nicht-Besprechungen liefert EWS "Unknown" → als eigener Termin gewertet.
                "organizer": _txt(it, "t:MyResponseType")
                in ("Organizer", "Unknown", ""),
            }
        )
    return items


def kennung(item_id: str) -> str:
    return item_id[-12:]


def format_line(ev: dict, tag: str, show_ids: bool) -> str:
    s, e = ev["start"], ev["end"]
    when = (
        s.strftime("%Y-%m-%d") + " ganztags"
        if ev["allday"]
        else s.strftime("%Y-%m-%d %H:%M") + "–" + e.strftime("%H:%M")
    )
    extras = f" · {ev['location']}" if ev["location"] else ""
    line = f"[{tag}] {when}  {ev['subject']}{extras}"
    if show_ids:
        serie = " serie" if ev["type"] != "Single" else ""
        line += (
            f"  id={kennung(ev['id'])} besprechung={'ja' if ev['meeting'] else 'nein'} "
            f"organisator={'ja' if ev['organizer'] else 'nein'}{serie}"
        )
    return line


def guard_own_single(ev: dict) -> str | None:
    """Schutzregeln für --update/--delete (hart, keine Ausnahme). None = darf."""
    if ev["meeting"]:
        return "Besprechung mit Teilnehmern — Änderung/Absage ginge an Dritte"
    if not ev["organizer"]:
        return "fremde Einladung — eigenes Konto ist nicht Organisator"
    if ev["type"] != "Single":
        return f"Serientermin ({ev['type']}) — nur Einzeltermine"
    return None


# ---------- Kommandos ----------


def _tag(cfg: dict) -> str:
    return cfg["account"].upper()


def window(days: int | None) -> tuple[dt.datetime, dt.datetime]:
    """days=None → Rest des heutigen Tages (Berlin), sonst jetzt + N Tage."""
    now = dt.datetime.now(BERLIN)
    if days is None:
        return now, (now + dt.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    return now, now + dt.timedelta(days=days)


def fetch_items(cfg: dict, days: int | None) -> list[dict]:
    start, end = window(days)
    code, text = ews_call(cfg, body_find_items(start, end))
    if code != 200:
        sys.exit(f"FEHLER: EWS HTTP {code} — {response_error(text) or 'ohne Details'}")
    err = response_error(text)
    if err:
        sys.exit(f"FEHLER: EWS {err}")
    return sorted(parse_items(text), key=lambda ev: ev["start"])


def cmd_status(cfg: dict) -> None:
    print(f"{cfg['account']}: EWS {cfg['url']} · Anmeldung als {cfg['login']}")
    code, text = ews_call(cfg, body_get_calendar_folder())
    if code == 401:
        sys.exit(
            "✘ Anmeldung abgelehnt (HTTP 401) — Kennung/Passwort oder NTLM gesperrt"
        )
    if code != 200:
        sys.exit(f"✘ HTTP {code} — {response_error(text) or 'ohne Details'}")
    err = response_error(text)
    if err:
        sys.exit(f"✘ EWS {err}")
    root = ET.fromstring(text)
    folder = root.find(".//t:CalendarFolder", NS)
    name = _txt(folder, "t:DisplayName")
    total = _txt(folder, "t:TotalCount") or "?"
    print(f"✔ angemeldet · Kalenderordner „{name}“ · {total} Einträge")


def cmd_list(cfg: dict, days: int | None, show_ids: bool) -> None:
    items = fetch_items(cfg, days)
    if not items:
        print("Keine Termine im Zeitraum.")
        return
    for ev in items:
        print(format_line(ev, _tag(cfg), show_ids))


def _confirm(prompt: str, yes: bool) -> None:
    if yes:
        return
    if input(f"{prompt} [j/N] ").strip().lower() not in ("j", "ja", "y", "yes"):
        sys.exit("Abgebrochen.")


def resolve(cfg: dict, kenn: str, days: int) -> dict:
    hits = [ev for ev in fetch_items(cfg, days) if kennung(ev["id"]) == kenn]
    if len(hits) != 1:
        print(
            f"FEHLER: Kennung {kenn} ist im Fenster von {days} Tagen "
            f"{'nicht' if not hits else 'mehrfach'} zu finden ({len(hits)} Treffer)",
            file=sys.stderr,
        )
        sys.exit(2)
    return hits[0]


def cmd_create(cfg: dict, args) -> None:
    body = body_create_item(
        args.subject, args.start, args.end, args.location, args.note
    )
    print(
        f"Anlegen in {cfg['account']} (nur eigener Kalender, keine Teilnehmer):\n"
        f"  {args.subject}\n  {args.start} – {args.end}"
        + (f"\n  {args.location}" if args.location else "")
    )
    _confirm("Anlegen?", args.yes)
    code, text = ews_call(cfg, body)
    err = response_error(text) if code == 200 else f"HTTP {code}"
    if err:
        sys.exit(f"FEHLER: {err}")
    root = ET.fromstring(text)
    iid = root.find(".//t:ItemId", NS)
    print(f"✔ angelegt · id={kennung(iid.get('Id', '')) if iid is not None else '?'}")


def cmd_update(cfg: dict, args) -> None:
    ev = resolve(cfg, args.update, args.tage)
    block = guard_own_single(ev)
    if block:
        print(f"FEHLER: nicht geändert — {block}.", file=sys.stderr)
        sys.exit(3)
    fields = {
        "subject": args.subject,
        "start": args.start,
        "end": args.end,
        "location": args.location,
        "note": args.note,
    }
    body = body_update_item(ev["id"], ev["change_key"], fields)
    print(
        f"Ändern in {cfg['account']}: {ev['subject']} ({ev['start'].strftime('%Y-%m-%d %H:%M')})\n"
        + "\n".join(f"  {k}: {v}" for k, v in fields.items() if v is not None)
    )
    _confirm("Ändern?", args.yes)
    code, text = ews_call(cfg, body)
    err = response_error(text) if code == 200 else f"HTTP {code}"
    if err:
        sys.exit(f"FEHLER: {err}")
    print("✔ geändert")


def cmd_delete(cfg: dict, args) -> None:
    ev = resolve(cfg, args.delete, args.tage)
    block = guard_own_single(ev)
    if block:
        print(f"FEHLER: nicht gelöscht — {block}.", file=sys.stderr)
        sys.exit(3)
    print(
        f"Löschen in {cfg['account']}:\n  {ev['subject']}\n"
        f"  {ev['start'].strftime('%Y-%m-%d %H:%M')} – {ev['end'].strftime('%H:%M')}"
    )
    _confirm("Löschen?", args.yes)
    code, text = ews_call(cfg, body_delete_item(ev["id"], ev["change_key"]))
    err = response_error(text) if code == 200 else f"HTTP {code}"
    if err:
        sys.exit(f"FEHLER: {err}")
    print("✔ gelöscht (Gelöschte Elemente)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--account",
        required=True,
        help="Postfach-Kürzel → ~/.claude/mail-<NAME>.env (z.B. hnu)",
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--status", action="store_true", help="Verdrahtungsprobe")
    g.add_argument(
        "--list", type=int, metavar="TAGE", help="Termine der nächsten N Tage"
    )
    g.add_argument("--today", action="store_true", help="Termine heute")
    g.add_argument("--create", action="store_true", help="Termin anlegen (Stufe A)")
    g.add_argument(
        "--update", metavar="KENNUNG", help="Termin ändern (aus --list --ids)"
    )
    g.add_argument(
        "--delete", metavar="KENNUNG", help="Termin löschen (aus --list --ids)"
    )
    ap.add_argument(
        "--ids", action="store_true", help="Kennung/Besprechung/Organisator zeigen"
    )
    ap.add_argument("--subject")
    ap.add_argument("--start", help="'YYYY-MM-DD HH:MM' (Europe/Berlin)")
    ap.add_argument("--end", help="'YYYY-MM-DD HH:MM' (Europe/Berlin)")
    ap.add_argument("--location", default="")
    ap.add_argument("--note", default="")
    ap.add_argument(
        "--tage",
        type=int,
        default=DEFAULT_WINDOW_DAYS,
        help=f"Listenfenster für Kennungs-Auflösung (Default {DEFAULT_WINDOW_DAYS})",
    )
    ap.add_argument("--yes", action="store_true", help="ohne Rückfrage")
    args = ap.parse_args()

    cfg = load_config(args.account)
    if args.status:
        cmd_status(cfg)
    elif args.list is not None:
        cmd_list(cfg, args.list, args.ids)
    elif args.today:
        cmd_list(cfg, None, args.ids)
    elif args.create:
        if not (args.subject and args.start and args.end):
            sys.exit("FEHLER: --create braucht --subject, --start und --end")
        cmd_create(cfg, args)
    elif args.update:
        # Leere Strings sind bei --update "nicht gesetzt", nicht "leeren".
        args.location = args.location or None
        args.note = args.note or None
        cmd_update(cfg, args)
    elif args.delete:
        cmd_delete(cfg, args)


if __name__ == "__main__":
    main()
