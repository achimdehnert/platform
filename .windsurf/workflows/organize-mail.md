---
description: Postfach aufräumen über Maschinen-IMAP — Mails in Ordner verschieben, Ordner anlegen, Spam in den Papierkorb (kein hartes Löschen)
mode: write
---
# /organize-mail — Postfach aufräumen (IMAP, Verschieben statt Löschen)

Verschiebt E-Mails nach Absender/Betreff in passende Ordner, legt Ordner an und räumt Spam in den
Papierkorb. **Kein hartes Löschen** — die einzige „Lösch"-Aktion ist Verschieben in den Papierkorb
(reversibel). Bewusst getrennt vom nur-lesenden `/read-mail`, dessen Read-Only-Garantie unberührt bleibt.

> **Wann:** „Räum die Spam-Mails weg", „schieb alles von Absender X nach Ordner Y", „leg einen Ordner an".
> **Wann NICHT:** endgültiges Löschen (nicht gebaut, bewusst — Papierkorb ist die Grenze);
> App-seitige Mail-Verwaltung.

**SSoT Skript:** `tools/mail_agent/organize_mail.py`. **Config:** `~/.claude/mail.env` (wie /send-mail).

## Sicherheits-Design (Lotsen-Charta KONZ-025)

- **Nie hart löschen** — nur Verschieben; Papierkorb-Verschieben ist ein Move nach `INBOX.Trash`.
- **Nie ordner-weites EXPUNGE** — Move via `UID MOVE`, Fallback `COPY + \Deleted + gezieltes UID EXPUNGE`.
- **Bestätigungs-Anzeige vor jedem Zug** (welche Mails, wohin); `--yes` überspringt sie — nur nutzen,
  wenn der Kapitän Kriterium UND Ziel benannt hat (dann gilt das als Freigabe, analog /send-mail).
- **Kein Pauschal-Verschieben:** `--move`/`--to-trash`/`--flag`/`--unflag` verlangen `--from`
  und/oder `--subject` (kein Pauschal-Zug).
- **Flag ist reversibel und bleibt im Postfach** — `--flag`/`--unflag` setzen nur `\Flagged`
  (`STORE ±FLAGS`), kein Move, kein EXPUNGE, kein Abfluss.

## Verwendung

```bash
python3 tools/mail_agent/organize_mail.py --list-folders
python3 tools/mail_agent/organize_mail.py --create-folder "INBOX.Studenten"
# Spam in den Papierkorb (Absender-Substring):
python3 tools/mail_agent/organize_mail.py --to-trash --from "antonela"
# Nach Absender/Betreff in einen Ordner:
python3 tools/mail_agent/organize_mail.py --move --from "student.hnu.de" --to "INBOX.Studenten"
python3 tools/mail_agent/organize_mail.py --move --subject "Master Thesis" --to "INBOX.Studenten"
# Zur Nachverfolgung markieren (\Flagged — das „Fähnchen" in Outlook/Thunderbird), reversibel:
python3 tools/mail_agent/organize_mail.py --flag --from "student.hnu.de" --subject "Frist"
python3 tools/mail_agent/organize_mail.py --unflag --from "student.hnu.de"   # Flag zurücknehmen
# Anderes IMAP-Postfach (HNU / AD-privat) über --account → ~/.claude/mail-<NAME>.env:
python3 tools/mail_agent/organize_mail.py --account hnu --flag --from "student.hnu.de"
```

> **Wichtigkeitsstufe (hoch/normal/niedrig) geht über IMAP NICHT nachträglich** — sie steckt in
> Absender-Kopfzeilen. `\Flagged` ist die IMAP-Entsprechung der Nachverfolgung. Echte Importance
> nur im M365-Postfach über `/iil-mail` (`graph_mail.py --importance high|normal|low`).

## Anti-Patterns

- ❌ Endgültiges Löschen aufs Postfach (nicht gebaut — Papierkorb ist die harte Grenze)
- ❌ Pauschal-Verschieben ohne Absender-/Betreff-Kriterium
- ❌ `--yes` ohne vom Kapitän benanntes Kriterium + Ziel
- ❌ Credentials/Passwörter nach stdout (Config-Disziplin wie /send-mail Step 0)

## Changelog

- 2026-07-18: Initial (v1). Owner-Entscheid „159 bauen, Spam nur Papierkorb". Tests:
  `tools/tests/test_organize_mail.py` (Ordner-Parsing, Papierkorb-Auflösung, Header-Decode).
- 2026-07-23: `--flag`/`--unflag` (Owner-Wunsch „Mails zur Nachverfolgung kennzeichnen").
  `STORE ±FLAGS \Flagged`, reversibel, gleiches Kriterium+Gate wie `--move`; deckt HNU + AD-privat
  über `--account`. Importance über IMAP bewusst NICHT (nur M365 via `/iil-mail`). Tests ergänzt.
