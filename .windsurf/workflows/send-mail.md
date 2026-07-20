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
OK: Mail an Ilja.Lerch@deutschebahn.com via mail.example.org (SSL:465), Anhänge: create-pdf.md
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
