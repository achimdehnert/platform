# /briefing — On-demand Session-/Morgenbriefing

> **Zweck:** Beim Hinsetzen in einer Sekunde sehen, „was steht heute an" — aggregiert
> über **Postfächer + Kalender + wartende PRs/Issues + Tages-Prios**. On-demand,
> read-only, kein Versand, keine Mutation.
> **Gegenstück:** `/session-start` (lädt Repo-Kontext + Tier); `/briefing` ist der
> **persönliche** Tages-Digest darüber hinaus.
> **Wann:** Session-Anfang / morgens. **Wann NICHT:** als geplante Automatik ohne
> Freigabe (mail-haltiger Read auf Zeitplan = bewusstes Gate — s. u.).

## Portabilität (der „überall wenn ich per SSH einlogge"-Teil)

Dieser Skill wird über cc-skill-dist auf **jede** Maschine verteilt (session-start/-ende-Sync)
→ `/briefing` existiert überall. Die **Postfach-Credentials** sind maschinen-lokal
(`~/.claude/mail.env`, `~/.claude/mail-hnu.env`, `~/.claude/graph-mail-tokens/`,
`~/.secrets/`). **Graceful Degradation ist Pflicht:** fehlt auf einer Maschine ein
Zugang, wird der Abschnitt **übersprungen + als „(nicht verfügbar auf dieser Maschine)"
markiert** — das Briefing bricht NIE, es liefert, was da ist. Secrets werden **nie**
vom Skill auf andere Maschinen kopiert (Charta Art. 2).

## Modell-Routing

Reine Aggregation + Formatierung → **Haiku 4.5** oder Sonnet reicht (session-routing.md).
Kein Opus/Fable.

## Ablauf (read-only; jeder Block optional, überspringen wenn Zugang fehlt)

Arbeitsverzeichnis: `~/github/platform`. Datum „seit gestern" = letzte 24–36 h.

### 1. 📬 Wichtige neue Mail (Newsletter raus)
Pro angebundenem Postfach die INBOX seit gestern, **ohne** Bulk/Newsletter
(List-Unsubscribe / no-reply / bekannte Promo-Domains):
```bash
# ad@dehnert.team (IMAP-Default) — nur wenn ~/.claude/mail.env existiert
python3 tools/mail_agent/read_mail.py --list 25 2>/dev/null
# achim.dehnert@hnu.de — via --account (löst intern ~/.claude/mail-hnu.env auf; KEIN
# .env-Pfad im Kommando → Secret-Leak-Guard-sicher). Existenz prüft der Tool selbst.
python3 tools/mail_agent/read_mail.py --account hnu --list 25 2>/dev/null
# achim.dehnert@iil.gmbh (Graph) — nur wenn Token existiert
python3 tools/mail_agent/graph_mail.py --scan-senders --days 2 2>/dev/null   # Überblick
```
Client-seitig filtern: nur **echte Korrespondenz** zeigen (From = Mensch, nicht
`noreply@`/`newsletter@`/List-Unsubscribe). Pro Postfach max. 5–8 Zeilen `From | Betreff`.
Fehlt die Config → Zeile „(ad@/hnu/iil nicht auf dieser Maschine angebunden)".

### 2. 📅 Kalender heute
```bash
# iil.gmbh via Graph-Kalender — nur wenn ms_calendar + Token vorhanden
python3 tools/calendar_agent/ms_calendar.py --today 2>/dev/null || echo "(Kalender n/v)"
```
HNU-Kalender ist OAuth-blockiert (nur Mail via IMAP) → nicht versuchen, als Lücke nennen.

### 3. 🔀 PRs/Issues, die auf DICH warten
Owner aus git-Remote ableiten (nie hardcoden). Nur was **deinen** Zug braucht:
```bash
OWNER=$(git -C ~/github/platform remote get-url origin | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#')
gh search prs --owner "$OWNER" --state open --review-requested @me --json repository,number,title 2>/dev/null
gh search prs --owner "$OWNER" --author @me --state open --json repository,number,title,reviewDecision 2>/dev/null \
  | python3 -c "import json,sys; [print(p) for p in json.load(sys.stdin) if p.get('reviewDecision')=='APPROVED']"  # approved+offen = mergebar
```
Zeigen: (a) PRs mit deinem Review angefragt, (b) eigene PRs APPROVED+offen (ein Merge-Klick).

### 4. 🎯 Tages-Prios
`AGENT_HANDOVER.md` des aktuellen Repos (falls vorhanden) — Top-3 der `## Prioritäten`/
`⚡ Aktueller Stand`-Sektion, knapp.

### 5. 🔁 Offene Retro-Follow-ups (schließt den Retro→Dialog-Loop)
Damit Session-Retros nicht in git versanden, sondern dich morgens abholen:
```bash
# jüngster Retro-Report + dessen offene 🟢-Action-Items
ls -t docs/retros/session-retro-*.md 2>/dev/null | head -1
# maschinelle Längsschnitt-Eskalationen (recurring ≥2 = Gate-Pflicht)
python3 tools/retro_kpis.py 2>/dev/null | grep -iE 'Gate-PR-Pflicht|≥2' | head -3
```
Zeigen: die **offenen** 🟢/🔵-Items aus dem jüngsten Retro (nicht die erledigten) +
etwaige neue Gate-Pflicht-Slugs. Max. 3 — der Rest lebt im Report.

## Ausgabe: **Action Board** (Org-Standard, CLAUDE.md)

Die substanzielle Ausgabe ist ein **Action Board** (≥3 Items → Pflicht). **Board zuerst**,
max. 1 Info-Kopfzeile davor, dann die Bucket-Tabellen in dieser Reihenfolge (leere weglassen):

**Kopf (1 Zeile, informativ):** `🌅 <Datum> · <Konten verfügbar> · 📅 <N Termine heute> · 📬 <N relevante Mails>`

**Buckets** (feste Lean-Spalten `# | Item | Quelle | Ref | Status | Next Step`; `#` durchgezählt):
- 🟢 **Dein Zug** — Mail die Antwort braucht · PR die dein Review braucht · offene Retro-Follow-ups · Termin-Vorbereitung
- 🔵 **Ich sofort** — eigene PRs APPROVED+offen (ein Merge) · Entwürfe die ich vorbereiten kann
- 🎯 **Heute/Prios** — Termine + Handover-Top-3 (rein informativ, wenn kein Action-Item)

Regeln wie im Org-Standard: Zellen **lean** (2–6 Wörter), echte klickbare Links bei PR/Issue
(bei >78 Zeichen Zeile → nummerierte Liste statt Tabelle), Status-Emoji 🟢🔵🟡⛔✅.
`⚠️ Nicht verfügbar: <Konten ohne Zugang>` als letzte Zeile, wenn Blöcke fehlten.

Danach **1 Satz**: der **eine** naheliegendste erste Schritt.

## Anti-Patterns
- ❌ Newsletter/Bulk als „wichtige Mail" zeigen (List-Unsubscribe = raus).
- ❌ Bei fehlendem Zugang **abbrechen** statt den Block zu überspringen + zu markieren.
- ❌ Secrets auf andere Maschinen kopieren, um „überall" zu erzwingen (Charta Art. 2)
  — Graceful Degradation ist der Weg, nicht Secret-Spreading.
- ❌ Irgendetwas **senden/verschieben/löschen** — `/briefing` ist strikt read-only.
- ❌ Als geplante Cloud-Routine bauen — die Cloud-Container haben die Mail-Creds nicht;
  eine Automatik läuft lokal (cron) + braucht Freigabe (sensibler Read auf Zeitplan).
- ❌ Opus/Fable für die Aggregation (Kosten — Haiku/Sonnet trägt).

## Changelog
- 2026-07-22: Initial. On-demand persönliches Tages-Briefing über die 3 angebundenen
  Postfächer (ad@/hnu/iil) + Kalender + wartende PRs + Handover-Prios. Graceful
  Degradation je Credential (Portabilität über SSH ohne Secret-Spreading). Entstanden
  nach dem großen Postfach-Aufräumen (Mail-Zugänge frisch verfügbar).
- 2026-07-22 (v2): Ausgabe auf **Action-Board-Format** umgestellt (Org-Standard, CLAUDE.md:
  Buckets 🟢 dein Zug / 🔵 ich sofort / 🎯 heute, Lean-Spalten, echte Links). **Neuer Block 5
  „Offene Retro-Follow-ups"** — schließt den Retro→Dialog-Loop: die offenen 🟢-Items des
  jüngsten `docs/retros/`-Reports + Gate-Pflicht-Slugs aus `retro_kpis.py` erscheinen im
  Morgen-Board, statt in git zu versanden (User-Ziel „Retro automatisch im Dialog").
