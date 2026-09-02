---
description: E-Mail mit optionalen Anhängen über den konfigurierten SMTP-Transport der Maschine versenden
mode: write
---
# /send-mail — Mail-Versand über Maschinen-SMTP

Verschickt eine E-Mail (Text + optionale Anhänge) über den auf dieser Maschine konfigurierten
SMTP-Transport. Transport, Absender und Credentials kommen aus Maschinen-Config — **nichts davon
steht in dieser Skill-Datei** (Hardcoding-Verbot).

> **Wann:** Eine Datei/ein Report soll per Mail an eine benannte Person gehen („schicke X an Y per Mail").
> **Wann NICHT:** App-seitiger Mail-Versand (gehört in die App, z. B. Django-E-Mail-Backend);
> Benachrichtigungen an den User selbst (→ Discord/Betterstack); Massen-/Serienmails (nicht unterstützt, bewusst).

**Verwendung:**
```
/send-mail <empfänger> <betreff> [--attach <pfad>...] [body als Freitext]
/send-mail ilja "create-pdf Workflow" --attach docs/foo.md
```

**SSoT Versand-Skript:** `tools/mail_agent/send_mail.py` (dieses Repo; lokal `${GITHUB_DIR:-~/github}/platform/tools/mail_agent/send_mail.py`)

⚠️ **Nicht idempotent** — jeder Aufruf verschickt real eine Mail. Bei Wiederholung nach Fehler zuerst
prüfen, ob die erste Mail nicht doch rausging (Sent-Ordner / Empfänger fragen).

## Welches Konto darf senden (Owner-Weisung 2026-08-28)

Die Regel hängt am **Absender-Konto**, nicht am Empfänger:

| Konto | Was erlaubt ist |
|---|---|
| `ad@dehnert.team` | **echter Versand** über `send_mail.py` — hier läuft auch der Ilja/LUCA-Kanal |
| `achim.dehnert@iil.gmbh` (IIL) | **nur Entwurf** (`draft_mail.py --account iil`) — gesendet wird vom Owner |
| `achim.dehnert@hnu.de` (HNU) | **nur Entwurf** (`draft_mail.py --account hnu`) — gesendet wird vom Owner |

Ein „ja, schick das raus" im Chat bezieht sich bei IIL und HNU auf den **Entwurf**, nicht auf
den Sendeknopf. `send_mail.py` kennt heute weder `--account` noch `--config` und sendet daher
ohnehin nur als `ad@dehnert.team`; wer das ändert, muss diese Regel mit ändern — `--from`
und `--role` setzen sonst eine fremde Absenderadresse auf denselben Transport.

## Entwurf statt Versand (Draft-first)

Soll die Mail **nicht** rausgehen, sondern zur Prüfung im Postfach landen:
`tools/mail_agent/draft_mail.py` legt sie per IMAP-APPEND im Drafts-Ordner ab — für **jedes**
per `~/.claude/mail[-<account>].env` konfigurierte Postfach, nicht nur für das IIL-Postfach
(das deckt `graph_mail.py --draft` über Graph ab).

```
python3 tools/mail_agent/draft_mail.py --account hnu \
  --to a@b.de --cc c@d.de --subject "..." --html-file mail.html --signature-file sig.html
```

- **`--html-file` ist der Normalfall**: reine Text-Entwürfe bricht Outlook selbst um und
  erzeugt unerwünschte Zeilenumbrüche. Absätze als `<p>`, keine harten Umbrüche im Absatz.
- **`--signature-file` nicht vergessen** — ein per APPEND abgelegter Entwurf bekommt keine
  Signatur aus dem Mail-Client.
- Ordner wird automatisch erkannt (SPECIAL-USE `\Drafts`, sonst Namensheuristik de/en);
  `--folder` erzwingt einen bestimmten.
- Draft-first ist der bevorzugte Außen-Weg: gesendet wird vom Menschen (Lotsen-Charta Art. 2).

### Antwort statt Neu-Mail (seit 2026-07-30, platform#1555)

Eine Antwort braucht dreierlei, sonst kommt sie beim Empfänger als kontextlose neue
Mail an. Alle drei sind Schalter, keine Handarbeit:

| Was | Graph (`graph_mail.py --draft`) | IMAP (`draft_mail.py`) |
|---|---|---|
| Zitat der Ursprungsmail | `--reply-to <messageId>` | `--zitat-message-id "<mid@host>"` |
| Strang-Zuordnung | macht Graph selbst | `--in-reply-to` (+ `--references`) |
| Rollen-Design als HTML | `--role <id> --design` | `--role <id> --design` |

```
# Graph: Zitat kommt von createReply, das Design steht davor
python3 tools/mail_agent/graph_mail.py --draft --role iil --design \
  --eyebrow "Angebot 20251218" --subject "AW: ..." --body-file mail.txt \
  --reply-to "<graph-message-id>"

# IMAP: Zitat und Kopfzeilen baut das Werkzeug selbst
python3 tools/mail_agent/draft_mail.py --account hnu --role hnu --design \
  --to a@b.de --subject "AW: ..." --body-file mail.txt \
  --in-reply-to "<mid@host>" --zitat-message-id "<mid@host>"
```

- **`--design` erwartet Klartext**, nicht HTML: erste Zeile Anrede, Grußformel am Ende.
  Den Namensblock unter der Grußformel weglassen — Name, Signatur und Pflicht-Footer
  kommen aus der Rolle, sonst stehen sie doppelt. Zeilenumbrüche innerhalb eines
  Absatzes (Terminlisten) bleiben erhalten.
- **`--references`** nimmt die Kette der Ursprungsmail **plus** deren eigene Message-ID.
  Ohne Angabe wird nur die eine ID gesetzt — funktioniert, hängt den Strang aber flacher ein.
- Die Message-ID ist der stabile Anker; UIDs wandern beim Umsortieren. `anker.py` und
  `/a/<nr>` im Link-Dienst arbeiten aus demselben Grund darüber.
- **Falle, die dahinter steckte:** `createReply` legt das Zitat an, ein anschließender
  `PATCH body.content` ersetzt den **ganzen** Rumpf und löscht es wieder. Genau so gingen
  am 2026-07-30 drei Entwürfe ohne Zitat raus. Wer den Rumpf setzt, muss den vorhandenen
  erst lesen und den neuen Text davor setzen.

---

## Step 0 — Maschinen-Config prüfen (Bootstrap)

Dieses Skill ist **maschinen-level**, nicht repo-level → Config kommt nicht aus `project-facts.md`,
sondern aus `~/.claude/mail.env`:

```
SMTP_HOST=<smtp-host>
SMTP_PORT=<ssl-port>
MAIL_FROM=<standard-absender>
MAIL_CREDS_FILE=<pfad zur credentials-datei, z. B. unter ~/.secrets/>
```

- Datei fehlt → **STOP**, User nach Transport-Daten fragen und Datei anlegen (Credentials-Datei
  selbst nie anlegen/ändern — `~/.secrets/` ist read-only).
- Credentials-Datei: `user=`/`password=`-Paare; das Paar mit `user == MAIL_FROM` wird genutzt.
- **Credentials nie nach stdout** — auch nicht via `cut`/`grep` auf Dateien ohne `=`-Struktur
  (Key-Namen-Scan mit `cut -d= -f1` gibt bei solchen Dateien den *Inhalt* aus; vorher `grep -c '='`).

## Step 1 — Empfänger + Inhalt evidenzbasiert bestimmen

- Empfänger als Name („ilja") → Adresse **belegen**, nie raten: zuerst CC-Memory-Index,
  dann Repo-Doku des zugehörigen Projekts (`grep -riE '<name>[^ ]*@' <repo>/docs <repo>/*.md`).
  Keine belegte Adresse gefunden → **STOP**, User fragen.
- Anhänge: Existenz + Größe mit `ls -la` prüfen, bevor irgendetwas gesendet wird.
- Body: kurz, sachlich, mit Grußformel des Users; kein Marketing-Ton.

## Step 2 — Versand-Gate (Pflicht)

Vor dem Senden dem User kompakt zeigen: **Absender · Empfänger · Betreff · Anhänge (Name+Größe)**.

- Explizites Go einholen — **außer** der User hat Empfänger *und* Inhalt in der aktuellen
  Anweisung bereits selbst benannt („schicke Datei X an Y"), dann gilt das als Go.
- Externer Versand ist outward-facing und nicht rückholbar → im Zweifel fragen.

## Step 3 — Senden

**Freshness-Pflicht (retro f4a546 #3, Muster stale-local-clone ×4):** Das Skript liegt im lokalen
platform-Checkout — der ist nach einem Remote-Merge NICHT automatisch aktuell. Vor dem Aufruf:

```bash
SCRIPT="${GITHUB_DIR:-$HOME/github}/platform/tools/mail_agent/send_mail.py"
[ -f "$SCRIPT" ] || git -C "${GITHUB_DIR:-$HOME/github}/platform" pull --ff-only origin main
```

```bash
python3 "${GITHUB_DIR:-$HOME/github}/platform/tools/mail_agent/send_mail.py" \
  --to "<empfänger>" \
  --subject "<betreff>" \
  --body-file "<pfad_zum_body.txt>" \
  --attach "<pfad_zum_anhang>"
```

- Body per `--body-file` aus dem Scratchpad (umgeht Quoting-Fehler); Alternative `--body "<text>"`.
- Mehrere Empfänger/Anhänge: Flag wiederholen.
- Absender abweichend vom Standard: `--from <adresse>` (Credentials-Paar muss existieren).

## Step 4 — Ergebnis melden

Erfolgsmeldung des Skripts zitieren (enthält Empfänger, Host, Port-Modus, Anhänge — keine Secrets).
Fehler → Skript-Ausgabe zitieren, **nicht** blind erneut senden (siehe Nicht-Idempotenz oben).

## Output-Format

```
OK: Mail an empfaenger@example.invalid via mail.example.org (SSL:465), Anhänge: create-pdf.md
```

## Anti-Patterns

- ❌ Credentials/Passwörter in stdout, Logs, Commits oder diese Skill-Datei schreiben
- ❌ SMTP-Host, Absender oder Empfänger-Adressen in der Skill-Datei hardcoden (→ `~/.claude/mail.env`, Memory, Repo-Doku)
- ❌ Empfänger-Adresse raten oder aus anderem Kontext „übertragen" — nur belegte Adressen
- ❌ Ohne Versand-Gate senden, wenn Empfänger/Inhalt nicht explizit vom User benannt sind
- ❌ Massen-/Serienmails oder Verteiler — Skill ist für einzelne, benannte Empfänger
- ❌ Nach Fehler blind erneut senden (Doppelversand) — erst klären, ob Mail 1 raus ist
- ❌ App-Mail-Versand (Transaktionsmails etc.) hierüber abwickeln — gehört in die jeweilige App

## Changelog

- 2026-07-10: Initial. Extrahiert aus Ad-hoc-Versand (create-pdf.md an Auftraggeber); Dogfood-Beleg im PR.
- 2026-07-10 (v1.1): Step-3-Freshness-Pflicht (Existenz-Check + ff-only-Pull) — Erstaufruf nach dem
  eigenen Merge scheiterte real am stalen lokalen main (retro f4a546 #3, Muster stale-local-clone ×4).
  Dazu `tools/tests/test_send_mail.py` (Parsing-/Credentials-Contract, retro f4a546 #4).
