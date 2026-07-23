---
description: IIL-Geschäftspostfach (Microsoft 365) über Graph — lesen, in Ordner einsortieren, Antwort-Entwürfe schreiben (kein Senden, kein hartes Löschen)
mode: write
---
# /iil-mail — IIL-Geschäftspostfach über Microsoft Graph

Liest das IIL-Postfach (achim.dehnert@iil.gmbh), sortiert Mails nach Absender in Ordner
(z.B. DSGVO-Mandanten), legt Ordner an und schreibt **Antwort-Entwürfe in den Drafts-Ordner**.

> **Wann:** „Sortier die Kunden-Mails", „leg einen Ordner für Mandant X an", „entwirf mir
> eine Antwort an den Studenten/Kunden als Entwurf".
> **Wann NICHT:** Senden (bewusst nicht gebaut — Entwurf + Mensch sendet); hartes Löschen.

**SSoT Skript:** `tools/mail_agent/graph_mail.py`. **Config:** `~/.claude/calendar.env` (Konten/Client);
Tokens in `~/.claude/graph-mail-tokens/` (600). Kunden-Ordner-Zuordnung lokal, NICHT im Repo.

## Sicherheits-Design (Lotsen-Charta KONZ-025)

- **Scope Mail.ReadWrite** — lesen, verschieben, Ordner anlegen, Entwürfe schreiben,
  zur Nachverfolgung markieren (Flag), Wichtigkeit setzen. **Kein Senden** (Scope kann es
  nicht → Außenwirkung bleibt beim Menschen, Art. 7).
- **Flag/Wichtigkeit sind reversibel** und bleiben im Postfach (kein Abfluss): `--flag`/
  `--unflag` setzen den Follow-up-Status, `--importance high|normal|low` die Wichtigkeit —
  beide nur mit `--from`/`--subject`-Kriterium und Anzeige-Gate wie `--move`.
- **Draft-first:** Vorschläge landen als Entwurf im Drafts-Ordner; der Kapitän prüft und sendet
  selbst aus Outlook. Der bevorzugte Außen-Weg des Lotsen.
- **Kein hartes Löschen** — Verschieben (auch nach Papierkorb) ist die Grenze.
- **Mandantendaten (Art. 3.2):** Ausgaben Kapitäns-Kanal; Kunden-/Ordner-Zuordnung lokal, nie Repo/Memory.
- **Bestätigungs-Anzeige** vor jedem Verschieben; `--yes` überspringt (nur bei benanntem Kriterium+Ziel).

## Verwendung

```bash
python3 tools/mail_agent/graph_mail.py --login achim.dehnert@iil.gmbh   # einmalig, Browser
python3 tools/mail_agent/graph_mail.py --list-folders
python3 tools/mail_agent/graph_mail.py --scan-senders --days 180        # Domains vorschlagen
python3 tools/mail_agent/graph_mail.py --create-path "IIL.Kunden/Marold"
python3 tools/mail_agent/graph_mail.py --move-folder "Gröger" --to-parent "IIL.Kunden"
python3 tools/mail_agent/graph_mail.py --move --from "groeger-recycling.de" --to "DSGVO/Groeger"
# Nachverfolgung (Follow-up-Flag) + Wichtigkeit — reversibel, gleiches Anzeige-Gate wie --move:
python3 tools/mail_agent/graph_mail.py --flag --from "groeger-recycling.de" --subject "Frist"
python3 tools/mail_agent/graph_mail.py --unflag --from "groeger-recycling.de"       # Flag zurücknehmen
python3 tools/mail_agent/graph_mail.py --importance high --subject "Mahnung"         # high|normal|low
python3 tools/mail_agent/graph_mail.py --find --subject "Owner-Block" --days 7   # suchen, read-only
python3 tools/mail_agent/graph_mail.py --show latest --from "dehnert.team"       # eine Mail lesen
# Anhänge holen — bei Rechnungen/Mahnungen steht der Inhalt im PDF, nicht im Mailtext:
python3 tools/mail_agent/graph_mail.py --show <messageId> --save-attachments ./anhaenge
# Antwort-Entwurf (threadet, wenn --reply-to eine Message-ID bekommt):
python3 tools/mail_agent/graph_mail.py --draft --reply-to <messageId> --body-file antwort.txt
python3 tools/mail_agent/graph_mail.py --draft --to kunde@x.de --subject "..." --body-file f.txt
```

## Anti-Patterns

- ❌ Senden (nicht gebaut — Entwurf + Mensch); ❌ hartes Löschen
- ❌ Kunden-/Mandantennamen ins Repo oder CC-Memory schreiben (lokal halten)
- ❌ Pauschal-Verschieben ohne Absender-Kriterium
- ❌ Zugriff ohne Owner-Login (die Anmeldung IST die Freigabe)

## Changelog

- 2026-07-18: Initial (v1). Owner-Entscheid 168 „ja" + Draft-first-Weisung. stdlib-only.
- 2026-07-18: `--find`/`--show` (E2, Owner „go"): formalisierte Read-Ops statt Ad-hoc-Scripts;
  keine Scope-Änderung (Mail.ReadWrite konnte lesen — jetzt getestet + auditierbar).
- 2026-07-23: `--flag`/`--unflag`/`--importance` (Owner-Wunsch „Mails kennzeichnen/priorisieren").
  Keine Scope-Änderung (Mail.ReadWrite konnte es → jetzt getestet + auditierbar), reversibel,
  gleiches Kriterium+Gate wie `--move`, kein Abfluss.
