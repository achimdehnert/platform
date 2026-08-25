---
description: Eine benannte Kette klick-only durch die laufende App pruefen — Begehbarkeit, Konsole, Antwortkoerper; je Befund ein Issue mit Klassen-Gate-Vorschlag (KONZ-051 Stufe 1)
mode: write
scope: geteilt
statefulness: zustandslos
trigger: interaktiv
---

# /ux-review — Kette klick-only pruefen, je Befund ein Klassen-Gate

> **Wann:** Eine App hat eine Kette aus mehreren Screens (Recherche → Angebot → Freigabe,
> Idee → Buch → Export), und niemand weiss, ob ein Mensch sie **ohne getippte URL** von Anfang
> bis Ende begehen kann. Operationalisiert **KONZ-platform-051** (Stufe 1).
> **Wann NICHT:** Klickdummy pruefen → `/kd-review` (statisch, kein Login). App-Struktur
> auditieren ohne zu klicken → `/repo-ux-opt`. Einen bekannten Defekt fixen → normaler PR-Flow.
> Dieser Skill **aendert keinen Code** — er klickt, urteilt und legt Issues an.

## Verwendung

```
/ux-review <repo> --kette "<Station 1> > <Station 2> > ... > <Station n>" [--basis <url>] [--vor <sha>] [--no-issues] [--max-klicks <n>]
```

| Argument | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `<repo>` | ja | — | Ziel-Repo (Slug); Issues landen **dort** |
| `--kette` | ja | — | Stationen in Reihenfolge; „Station erreicht" ist das Abbruchkriterium je Schleife |
| `--basis` | nein | lokaler Stack aus Step 1 | Basis-URL (lokal oder Staging — **nie** eine Cloudflare-Access-Domain) |
| `--vor` | nein | `origin/main` | Commit, gegen den geprueft wird (Positivkontrolle: Stand **vor** einem Fix) |
| `--no-issues` | nein | aus | nur Bericht auf stdout, keine Issues (Trockenlauf) |
| `--max-klicks` | nein | `25` | Klicks je Station ohne neue Seite, bevor die Station `blind` wird |

## Step 0: Repo-Kontext aus project-facts.md (PFLICHT — kein Hardcoding)

Aus `.windsurf/rules/project-facts.md` des Ziel-Repos: `REPO_OWNER/REPO_NAME` (Org kann
`iilgmbh`/`ttz-lif`/`meiki-lra` sein — Issues gehen in die **richtige** Org), `TYPE`,
`HTMX_DETECTION`, Dev-Port. Testkonto: **Zeiger** aus `~/.secrets/<repo>-testuser` (Name/Zweck),
Wert nie auf stdout. Fehlt ein Testkonto → Station 0 ist `blind: kein Testkonto`, kein Raten.

Vorher ein Blick, was der Agent **nicht** neu melden darf: `gh issue list -R <owner>/<repo>
--label ux-review --state all` — bekannte Befunde werden im Bericht als „bekannt (#N)" gefuehrt,
nicht als neues Issue (Voraussetzung aus KONZ-051 ALT-1, platform#2326).

## Step 1: Eigene Umgebung (E5 — nie die geteilte)

1. **Worktree**, nie der Haupt-Tree: `bash platform/tools/repo-session.sh start ~/github/<repo>
   --task ux-review-<kette-slug>`; bei `--vor <sha>`: `git -C <wt> checkout <sha>` dort.
2. **Eigener Stack** oder Staging. Vor dem Start: `ss -tlnp | grep -E ':(8000|<dev-port>)\b'` —
   ein fremder Server auf dem Standard-Port heisst: **man misst eine fremde Instanz** (Realfall
   ausschreibungs-hub 2026-08-24). `*.localhost` loest auf `::1` auf — Basis-URL mit `127.0.0.1`.
3. **Keine Aenderung an einer geteilten `.env`.** Braucht der Lauf eine Variable, dann als
   eigene `.env.ux-review` im Worktree (gitignored) — Realfall writing-hub 2026-08-25: geteilte
   `.env` bei 12 parallelen Sessions umgestellt.
4. **Synthetische Daten.** Der Lauf legt eigene Objekte an (Prefix `uxr-<datum>`); Screenshots
   von echten Mandanten sind ein Abbruchgrund (R4 — `platform` ist oeffentlich).

## Step 2: Einstieg, dann Klick-only (E1)

MCP-Signaturen vor Nutzung pruefen: `ToolSearch select:browser_navigate,browser_snapshot,
browser_click,browser_fill_form,browser_console_messages,browser_network_requests,browser_take_screenshot`.

- **Einzige erlaubte URL:** die Basis-URL. Login per `browser_fill_form` mit dem Testkonto.
- Ab der Startseite gilt: **jeder Weg ist ein Klick.** Wird eine URL getippt, um eine Station zu
  erreichen, ist das **selbst der Befund** der Klasse `nicht-begehbar` — er wird sofort notiert
  (Station, gesuchtes Ziel, von wo aus kein Link existierte), und der Lauf geht **mit** der
  getippten URL weiter. Verschwiegen wird die URL nie (Kill-Kriterium K4).

## Step 3: Je Station — Snapshot, Konsole, Netzwerk, Zustand (E4, E6)

Schleife je Station, Abbruch messbar: **Station erreicht** ODER `--max-klicks` ohne neue Seite.

1. `browser_snapshot` (Accessibility-Tree, keine Locator-Liste — kein F18).
2. `browser_console_messages` → Errors/Warnings; `browser_network_requests` → jede 4xx/5xx
   **mit Antwortkoerper**. Bei HTMX: eine 4xx ohne sichtbare Aenderung im DOM ist der Befund
   `stiller-fehler` (kein `htmx:responseError`-Handler), nicht „Klick tut nichts".
3. **Diagnose aus dem Antwortkoerper, nie aus dem Statuscode**: 403 ist CSRF *und*
   Tenant-Sperre derselben View — nur der Body unterscheidet.
4. `browser_take_screenshot` als Beleg — nur, wenn Step 1.4 gilt.
5. **Zustand setzen**, einer von drei:
   - `befund` — mit Klasse (Tabelle unten), Beleg, Repro
   - `ok` — Station erreicht, keine Fehler in Konsole/Netzwerk, Inhalt lesbar
   - `blind` — mit Grund (kein Testkonto, Login scheitert, Klickbudget erschoepft, Dienst
     antwortet nicht). **`blind` ist nie gruen** und zaehlt im Bericht getrennt.

## Step 4: Absenz-Gegenprobe (E2 — Pflicht vor jedem „fehlt")

Bevor ein Befund „Feld/Knopf/Funktion fehlt" heisst: zweiter Suchpfad in der Quelle —
`grep -rn '<feldname\|url-name>' <wt>/templates <wt>/apps` (bzw. `<app>/templates`).
Treffer → es ist eine **Rendering-Bedingung** (leere Liste, Rolle, Feature-Flag), und der Befund
lautet so — mit Datei:Zeile. Kein Treffer in beiden Pfaden → erst dann `fehlt`.
Realfall: writing-hub #760 („Stil nicht zuweisbar") — das Feld stand in `project_form.html:171`.

## Step 5: Erfolgsaussehende Ausgaben pruefen (E7)

Zeigt eine Station generierten oder extrahierten Inhalt (Angebotstext, Dokumenttext, Export),
wird er gegen die Quelle gehalten: Ersatzzeichen-Anteil, Prompt-Fragmente, Rohbytes, HTML in einer
Datei. Sieht ein Fallback aus wie Erfolg, ist **das** der Befund (`fallback-als-erfolg`), auch wenn
die Station „funktioniert". Dreimal in einer Sitzung (ausschreibungs-hub 2026-08-25).

## Step 6: Issue je Befund im Zielrepo (E3)

Pro Befund **ein** Issue via `gh issue create -R <owner>/<repo> --label ux-review` mit diesem
Body-Schema — der Klassen-Gate-Vorschlag ist **kein** optionales Feld:

```
## Befund — <klasse> · <fehler|optimierung>
Kette: <kette> · Station: <n> <name> · Stand: <sha> · Lauf: <datum>

**Symptom:** <ein Satz, was ein Mensch sieht>
**Repro:** 1. … 2. … (Klickpfad, keine URLs — ausser die getippte, die der Befund ist)
**Antwortkoerper / Konsole:** <Zitat, gekuerzt>
**Screenshot:** <nur wenn Step 1.4 gilt>
**Gegenprobe (bei Absenz Pflicht):** `grep -rn … templates/ apps/` → <Treffer|leer>

**Klassen-Gate-Vorschlag (Pflicht):** <welcher Test ueber ALLE Routen/Templates/Aufrufe faengt
diese Klasse — Vorlage aus dem Katalog unten, oder „neue Klasse: …">
**Referenz (bei optimierung Pflicht):** ADR-048/049/040 §… oder Nielsen-Heuristik Nr. …
```

Severity `optimierung` **ohne** Referenz wird kein Issue, sondern eine Zeile im Bericht (R3).
Bekannte Befunde (Step 0) bekommen kein neues Issue. Mit `--no-issues`: Schema auf stdout.

## Step 7: Sammel-Issue = Bericht

Ein Issue `[ux-review] <repo> · <kette> · <datum>` im Zielrepo mit der Stationstabelle
(drei Zustaende), den Links auf die Befund-Issues, der Liste getippter URLs (K4) und dem
Zaehler `befund / ok / blind / bekannt`. Der Owner traegt je Befund-Issue `fehlbefund` als Label
nach — daraus rechnet das Kill-Gate K2 die Quote.

## Klassen-Katalog (Gate-Vorlagen, die der Agent kennt)

| Klasse | Symptom im Browser | Klassen-Gate (Vorlage) |
|---|---|---|
| `nicht-begehbar` | Station nur per getippter URL | Test: jede seitenrendernde Route gegen `{% url %}` aller Templates, Ausnahmen **mit Grund** — `ausschreibungs-hub/tests/test_erreichbarkeit_screens.py` |
| `stiller-fehler` | Klick „tut nichts", 4xx im Netzwerk | globaler `htmx:responseError`-Handler in `base.html` — `ausschreibungs-hub/templates/base/base.html:101` |
| `csrf-403` | HTMX-POST → 403, Body nennt CSRF | `hx-headers` mit Token am `body`, nicht je Formular |
| `markup-leck` | Django-Kommentar/Template-Syntax als sichtbarer Text | Test ueber **alle** Templates auf mehrzeilige `{# #}` |
| `fallback-als-erfolg` | plausibler Text statt Fehler | Aufrufer wertet das Fehlerfeld der Bibliothek aus; was nicht extrahiert wurde, wird nicht gespeichert |
| `eine-meldung-drei-ursachen` | derselbe Fehlersatz fuer verschiedene Faelle | Meldung traegt die Ursache aus dem Audit-Trail |
| `escape-familie` | Sonderzeichen brechen Seite/JS | Gate ueber alle `{{ … }}` in `<script>`/`on*` — writing-hub #761 |
| `daten-invariante` | Anzeige widerspricht der Sache (abgelaufene Frist bei laufender Ausschreibung) | Invarianten-Melder ueber den Datenbestand, **SKIP ist kein PASS** |

Neue Klasse gefunden → Zeile hier ergaenzen (PR nach platform), nicht nur im Issue beschreiben.

## Output-Format

```
== /ux-review <repo> · Kette: <k> · Stand: <sha> · Basis: <url> ==

Umgebung
  Worktree: <pfad> · Stack: <eigen|staging> · Port frei: ja · Testkonto: <zeiger|blind>

Stationen
  # | Station         | Zustand | Klasse            | Beleg
  1 | Login           | ok      | —                 | —
  2 | Angebotsentwurf | befund  | nicht-begehbar    | URL getippt: /angebote/review/ (kein Link ab Station 1)
  3 | Freigabe        | blind   | Klickbudget 25    | —

Getippte URLs (K4): <n> — <liste>
Zaehler: befund <b> · ok <o> · blind <x> · bekannt <k>

Issues (Zielrepo <owner>/<repo>)
  #<n> nicht-begehbar · fehler · Gate: Routen-vs-Templates
  Sammel-Issue: #<m>

Nicht verifiziert: <was der Lauf nicht sehen konnte, und der billigste Check dafuer>
```

## Anti-Patterns

- ❌ **URL tippen und weitergehen, ohne sie als Befund zu notieren** — genau die Klasse, die
  14 verwaiste Routen zwei Monate versteckt hat.
- ❌ **„fehlt" aus leerem DOM** ohne `grep` in Templates/Apps — Fehlbefund #760.
- ❌ **Diagnose aus dem Statuscode** — 403 hat zwei Ursachen, nur der Body sagt welche.
- ❌ **Geteilte `.env` oder Haupt-Tree fuer den Lauf** — parallele Sessions messen dann Fremdes.
- ❌ **Fremder Server auf dem Standard-Port ignoriert** — man prueft eine fremde Instanz.
- ❌ **Cloudflare-Access-Domain als Basis** — Auth-Wand, kein Pruefmittel (`/kd-review`-Lehre).
- ❌ **Screenshot mit Mandanten-/Personendaten** in ein oeffentliches Repo (platform ist public).
- ❌ **Zwei Zustaende** — `blind` als `ok` gezaehlt ist die Klasse, die am 2026-08-25 sechsmal versagte.
- ❌ **`optimierung` ohne Referenz** als Issue — Geschmack ist kein Befund.
- ❌ **Check-Listen durch `tail`/`head` filtern** und dann „alles gruen" melden (Retro #2325 #1).
- ❌ **Issue ohne Klassen-Gate-Vorschlag** — dann ist der Agent ein Melder, und Kill-Gate K3 faellt.

## 🌀-Memory-Discovery-Pfad

- `project_ux_review_agent_program` (platform) — Owner-Prio 2026-07-22, Stand KONZ-051
- pgvector `error:ausschreibungs-hub:20260825-screen-ohne-weg` — 14 Routen, Test ueber alle
- pgvector `error:ausschreibungs-hub:f8820cc8a690` — HTMX-4xx unsichtbar, fremder Port, `::1`
- Outline „Sechs Befunde, die nur ein Browser sehen konnte" (2026-08-25) — vier Regeln, fuenf Gates
- Retro `session-retro-2026-08-25-writing-hub-fdd368` (#2325) — Fehlbefund, geteilte `.env`, `tail`

## Bezug

- `platform:KONZ-platform-051` — Konzept, Ledger E1–E9, Kill-Gate K1–K5 (Frist 2026-09-30)
- `platform:ADR-251` — UX-Gate am Klickdummy (die Stufe davor: `/kd-review`)
- `platform:ADR-048/049/040` — Referenzmassstab fuer `optimierung`
- `platform#2326` — Klassen-Tests flottenweit (ALT-1); der Agent meldet Bekanntes nicht neu
- `policies/platform-agents.md` — Heimat fuer Stufe 2 (Dienst), erst nach Kill-Gate + ADR

## Dogfood-Tests (Pflicht-Review-Gate per `claude-skills.md`)

### Test 1 — Positivkontrolle writing-hub (K1)

```
/ux-review writing-hub --kette "Login > Projekt anlegen > Idee > Buch > Export" --vor <sha vor #761> --no-issues
```
**Erwartung:** drei bekannte Defekte (#758 escape-familie, #759, #762) als `befund`; kein
Issue (Trockenlauf); Absenz-Gegenprobe zu „Stil" liefert `project_form.html:171` → Rendering-Bedingung, **kein** Befund.

### Test 2 — Positivkontrolle ausschreibungs-hub (K1, K4)

```
/ux-review ausschreibungs-hub --kette "Login > Recherche > Analyse > Angebot > Freigabe > Abgabe" --vor <sha vor Erreichbarkeits-Fix> --no-issues
```
**Erwartung:** Station 4 und 5 nur per getippter URL erreichbar → zwei `nicht-begehbar` mit
Gate-Vorlage Routen-vs-Templates; getippte URLs im Bericht = 2.

### Test 3 — `blind` ist nie gruen (E4)

```
/ux-review <repo> --kette "Login > X" --basis http://127.0.0.1:65530   # nichts lauscht (kein Chromium-„unsafe port" wie :9 — der misst den Browser, nicht den Dienst)
```
**Erwartung:** Station 1 `blind: Dienst antwortet nicht`, Zaehler `ok 0`, kein Issue,
Exit-Zeile „Nicht verifiziert: gesamte Kette".

## Changelog

- 2026-08-25: Initial — Stufe 1 aus KONZ-platform-051 (Owner „3 go"). Abweichungen vom
  KONZ-MVC, dort nachgetragen: Bericht = Sammel-Issue statt Datei im Zielrepo (E3 erlaubt
  keine PRs dorthin); Issue-Schema lebt im Skill statt als platform-Issue-Template (das gaelte
  nur fuer Issues in platform — Doppelquelle). Klassen-Katalog mit acht Klassen aus
  writing-hub/ausschreibungs-hub. Dogfood-Tests 1–2 sind die Positivkontrolle des Kill-Gates
  und laufen im Pilot, nicht im PR dieses Skills. Dogfood beim Bau: Test 3 stand zuerst auf
  Port 9 — Chromium lehnt den als „unsafe port" ab (`ERR_UNSAFE_PORT`), der Test haette den
  Browser gemessen, nicht den Dienst; auf 65530 korrigiert (`ERR_CONNECTION_REFUSED` = `blind`).
