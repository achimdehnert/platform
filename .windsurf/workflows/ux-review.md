---
description: PFLICHT bei JEDER Arbeit an GUI, Templates, Views oder einer Bedien-Kette (Owner-Weisung 2026-08-26) — vor dem ersten Klick aufrufen, nicht danach. Prueft eine Kette klick-only durch die laufende App: Begehbarkeit ohne getippte URL, Konsole, Antwortkoerper, Funktionen ohne Aufrufer; je Befund ein Issue mit Klassen-Gate-Vorschlag (KONZ-051 Stufe 1). Ausloeser: GUI, Oberflaeche, Template, Screen, Knopf, Formular, Durchlauf, e2e, klicken, Bedienbarkeit, „funktioniert das im Browser"
mode: write
scope: geteilt
statefulness: zustandslos
trigger: interaktiv
---

# /ux-review — Kette klick-only pruefen, je Befund ein Klassen-Gate

> **Wann:** Immer, wenn GUI, Templates, Views oder eine Bedien-Kette im Spiel sind
> (Owner-Weisung 2026-08-26). Typischer Fall: eine App hat eine Kette aus mehreren Screens
> (Recherche → Angebot → Freigabe, Idee → Buch → Export), und niemand weiss, ob ein Mensch
> sie **ohne getippte URL** von Anfang bis Ende begehen kann. Operationalisiert
> **KONZ-platform-051** (Stufe 1).
>
> **Vor dem ersten Klick aufrufen, nicht danach.** Am 2026-08-25/26 lief ein kompletter
> GUI-Durchlauf durch writing-hub ohne diesen Skill — drei Fehler, gegen die er ausdruecklich
> geschrieben ist, passierten dabei erneut: die geteilte `.env` wurde umgestellt (Step 1.3),
> eine Absenz ohne zweiten Suchpfad behauptet (Step 4), und ein „0 erstellt" im Erfolgston
> uebersehen (Step 5). Alle drei standen zu dem Zeitpunkt bereits als Regel hier drin.
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

## Step 0.5: Das gemeldete Objekt zuerst — im Browser (E10, PFLICHT bei jedem Befund)

> **Owner-Weisung 2026-08-28 (org-weit, woertlich):** „Playwright und/oder Cloudflare
> KONSEQUENT einsetzen um Browser-Inhalte zu sehen und zu analysieren."
>
> **Realfall, der sie ausgeloest hat** (writing-hub, 2026-08-27/28): Der Owner meldete
> dreimal „Kapitel schreiben -> keine Reaktion". Es wurden **sieben** Hypothesen durch
> Code-Lesen und serverseitiges Rendern geprueft — JS-Syntax (`node --check` gruen),
> `data-action`-Verdrahtung, CSRF-Cookie, API-Routen (403 statt 404), CSP-Header,
> Kapitelzahl, Celery-Worker. **Alle sieben waren falsch.** Der erste echte Klick auf
> der gemeldeten Seite zeigte die Ursache in der ersten Sekunde:
>
>     SyntaxError: Unexpected token ']' … is not valid JSON
>         at JSON.parse (…/write/:1231:28)
>
> Ein nachgestelltes Komma in einem handgebauten JSON-Block riss das gesamte Skript
> mit. Drei Prod-Projekte waren tot, seit 24 Tagen entstand kein einziger Job.
> **Warum keine statische Pruefung ihn finden konnte:** `node --check` prueft Syntax,
> der Fehler lag in den **Daten**, die zur Laufzeit geparst werden.

Bei einem **gemeldeten** Befund (Owner, Ticket, Support) gilt vor allem anderen:

1. **Browser vor Code.** Erst `browser_navigate` + `browser_console_messages` +
   `browser_network_requests` auf der gemeldeten Seite, dann Quelltext lesen. Nicht
   umgekehrt. Jede Minute Code-Analyse vor dem ersten Klick ist eine Wette darauf,
   dass man das Richtige vermutet.
2. **Am gemeldeten Objekt messen, nicht an einem neuen.** Step 1.4 verlangt fuer den
   *explorativen* Durchlauf synthetische Daten — fuer die *Reproduktion eines
   gemeldeten Befunds* gilt das ausdruecklich **nicht**. Ein frisch angelegtes Objekt
   ist per Konstruktion leer und zeigt datenabhaengige Defekte nie (siehe Klasse
   `nur-mit-daten-sichtbar`).
3. **Kein Zugang zum Zielsystem?** Zwei Wege, beide billiger als Raten:
   - **read-only rendern**: View im Ziel-Container ueber `RequestFactory` aufrufen und
     das HTML ansehen. Zeigt Serverfehler, aber **keine** Laufzeitfehler im Browser —
     im Realfall oben war dieses HTML tadellos.
   - **kurzlebige Diagnose-Session**: Session-Eintrag fuer den betroffenen Benutzer
     anlegen, Cookie im Browser setzen, messen, Session **loeschen**. Das ist ein
     Schreibvorgang auf dem Zielsystem und braucht eine **ausdrueckliche Freigabe**
     (Gate 2, `autonomy-gates.md`); der Loeschvorgang gehoert in denselben Zug.
4. **Erst wenn der Befund im Browser sichtbar ist**, beginnt die Ursachensuche im Code.

## Step 1: Eigene Umgebung (E5 — nie die geteilte)

1. **Worktree**, nie der Haupt-Tree: `bash platform/tools/repo-session.sh start ~/github/<repo>
   --task ux-review-<kette-slug>`; bei `--vor <sha>`: `git -C <wt> checkout <sha>` dort.
2. **Eigener Stack** oder Staging. Vor dem Start: `ss -tlnp | grep -E ':(8000|<dev-port>)\b'` —
   ein fremder Server auf dem Standard-Port heisst: **man misst eine fremde Instanz** (Realfall
   ausschreibungs-hub 2026-08-24). `*.localhost` loest auf `::1` auf — Basis-URL mit `127.0.0.1`.
3. **Keine Aenderung an einer geteilten `.env`.** Braucht der Lauf eine Variable, dann als
   eigene `.env.ux-review` im Worktree (gitignored) — Realfall writing-hub 2026-08-25: geteilte
   `.env` bei 12 parallelen Sessions umgestellt.
4. **Synthetische Daten** — mit **Bestand**, nicht bloss angelegt. Der Lauf legt eigene
   Objekte an (Prefix `uxr-<datum>`); Screenshots von echten Mandanten sind ein
   Abbruchgrund (R4 — `platform` ist oeffentlich). **Aber:** ein frisch angelegtes Objekt
   ist leer, und leere Objekte verdecken jeden datenabhaengigen Defekt. Mindestens **ein**
   Objekt der Kette bekommt deshalb den Zustand, den ein benutztes traegt — Unterobjekte,
   Belege, Inhalt, Verknuepfungen. Der Bericht nennt den Zustand je Station (s. Step 3.2).
   Gemessen im Realfall: 0 von 22 UX-Tests des Repos legten Belege an, 0 von 22 oeffneten
   die betroffene Seite — die Suite war gruen, drei Prod-Projekte waren tot.
   Fuer die Reproduktion eines **gemeldeten** Befunds gilt stattdessen Step 0.5.2.
5. **Seed und Doctor des Repos ausfuehren** (`grep -n 'seed\|doctor\|setup_' Makefile` bzw.
   `manage.py help | grep -i seed`), bevor die erste Station bewertet wird. Eine leere Registry
   ist eine Umgebungsluecke, kein Befund — Pilot writing-hub 2026-08-25: `AIActionType` leer,
   „No model configured", erst nach `setup_aifw_actions` messbar.
6. **Nach jedem Reseed den Cache des Repos leeren** (aifw: Redis, TTL 600 s — ein Web-Neustart
   reicht nicht). Sonst misst der Lauf den alten Stand, und eine Fehlermeldung, die frisch aus
   der DB liest, fuehrt in die Irre (writing-hub#766).
7. **Testkonto:** Zeiger aus `~/.secrets/`; fehlt er, im eigenen Stack `createsuperuser` mit einem
   Wegwerf-Passwort, das mit dem Stack stirbt. Es steht dann im Transkript — deshalb nur im
   eigenen, geloeschten Stack, nie in einem geteilten.

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
   - **Ein JS-Fehler in der Konsole macht die Station `befund` — ohne Ausnahme**, auch
     wenn die Seite normal aussieht und alle Elemente da sind. Ein Fehler, der frueh im
     Skript geworfen wird, reisst **alles danach** mit: keine Event-Verdrahtung, kein
     Knopf, keine Meldung. Genau so sah der Realfall aus (Seite tadellos, jeder Knopf tot).
   - **„0 Fehler" ist nur ein Beleg fuer den geprueften Datenzustand.** Der Bericht nennt
     ihn deshalb mit (Station 3: `ok (Bestand: 12 Kapitel, 16 Belege)` statt bloss `ok`).
     Ohne diese Angabe ist die Null wertlos: im Realfall meldete derselbe Lauf auf einem
     frischen Objekt 0 Fehler, waehrend die Prod-Seite genau einen hatte.
3. **Diagnose aus dem Antwortkoerper, nie aus dem Statuscode**: 403 ist CSRF *und*
   Tenant-Sperre derselben View — nur der Body unterscheidet.
4. `browser_take_screenshot` als Beleg — nur, wenn Step 1.4 gilt.
5. **Zustand setzen**, einer von drei:
   - `befund` — mit Klasse (Tabelle unten), Beleg, Repro
   - `ok` — Station erreicht, keine Fehler in Konsole/Netzwerk, Inhalt lesbar
   - `blind` — mit Grund (kein Testkonto, Login scheitert, Klickbudget erschoepft, Dienst
     antwortet nicht). **`blind` ist nie gruen** und zaehlt im Bericht getrennt.

## Step 3b: Gegenrichtung — vom Code zur Oberflaeche (E8, PFLICHT)

> Die Steps 2 und 3 gehen die Kette **von vorn** und finden, was auf dem Weg kaputt ist.
> Sie finden strukturell **nicht**, was gar nicht erst auf dem Weg liegt: eine fertige
> Funktion ohne Aufrufer. Gemessen writing-hub 2026-08-26 — an einem Tag fuenf Faelle,
> alle gebaut, alle getestet, keiner erreichbar:
>
> | Baustein | Zustand |
> |---|---|
> | `extract_from_text` (generisch seit #567) | null Aufrufer |
> | `ProjectItemLink` (seit #699) | kein Erzeugungsweg |
> | `CharacterRelationship` | vollstaendig, nie gefuellt |
> | `refine_character_with_llm` | ein Aufrufer, pro Einzelobjekt |
> | zwei neue Knoepfe | im falschen `{% if %}` |

Nach dem Klick-Durchlauf **einmal umgekehrt** fragen — rein statisch, also billig:

```bash
# URL-Namen ohne JEDEN Aufrufer. Drei Orte, nicht einer — im Pilot 2026-08-26
# gemessen: templates/ allein meldete 12, davon hatten 6 einen Aufrufer in JS
# oder in einem Python-`redirect(...)`.
for name in $(grep -rhoP 'name="\K[a-z_]+' "$WT"/apps/*/urls*.py | sort -u); do
  treffer=$(grep -rnF "$name" --include=*.py --include=*.html --include=*.js "$WT" \
            | grep -vE 'urls\.py|/tests?/|\.pyc' | wc -l)
  [ "$treffer" -eq 0 ] && echo "ohne Aufrufer: $name"
done
```

**Feste Zeichenketten suchen, nicht gequotete.** Ein Muster wie `"$name"` (mit
Anführungszeichen) übersieht `redirect("projects:$name")` — der Code schreibt den
Namensraum davor. Im Pilot meldete genau dieser Fehler **alle zwölf** Kandidaten
als aufruferlos; erst `grep -F` auf den nackten Namen trennte sie in 6 und 6.

**Positivkontrolle Pflicht:** ein Name, von dem ein Aufrufer BEKANNT ist, muss aus
der Liste herausfallen. Fällt er nicht heraus, ist der Filter kaputt und die Null
sagt nichts über die Welt.

Je Treffer **eine** von zwei Antworten, nie keine: **einhaengen** (der Weg fehlt) oder
**entfernen** (die Funktion ist tot). Halb liegen lassen ist genau der Zustand, der die
fuenf Faelle oben erzeugt hat.

**Und die Umkehrung der Umkehrung:** ein Knopf, der im Template steht, ist damit noch
nicht sichtbar. Steht er in einem `{% if %}`, gehoert die Frage dazu, ob diese Bedingung
zu seiner **Phase** passt — ein Knopf, der aus dem Konzept arbeitet, darf nicht an der
Gliederung haengen.

## Step 4: Absenz-Gegenprobe (E2 — Pflicht vor jedem „fehlt")

Bevor ein Befund „Feld/Knopf/Funktion fehlt" heisst: zweiter Suchpfad in der Quelle —
`grep -rn '<feldname\|url-name>' <wt>/templates <wt>/apps` (bzw. `<app>/templates`).
Treffer → es ist eine **Rendering-Bedingung** (leere Liste, Rolle, Feature-Flag), und der Befund
lautet so — mit Datei:Zeile. Kein Treffer in beiden Pfaden → erst dann `fehlt`.
Realfall: writing-hub #760 („Stil nicht zuweisbar") — das Feld stand in `project_form.html:171`.

**Das Feld `gegenprobe` beginnt mit einer Zahl, nicht mit einem Satz (E18).** Also
`0 Treffer in {% url %} ueber alle Templates/JS`, und erst danach, optional, die Erklaerung.
Realfall 2026-08-30: dieselbe Tatsache als Satz formuliert („nur `tests/test_route_coverage.py`")
liess Step 5b den Befund als Rendering-Bedingung `widerlegt` melden, obwohl der Browser die
Station nur ueber eine getippte URL erreichte. Als Zahl passiert das nicht.

**Der Zaehler muss beide Kontrollen bestehen** — dieselbe Regel wie in Step 3b: ein Name mit
bekanntem Aufrufer faellt aus der Liste heraus, ein Name mit bekannt **fehlendem** Aufrufer steht
drin. Im selben Lauf meldete ein erster Zaehler nur **1** verwaisten Namen: er zaehlte die
View-Definition als Aufrufer, und `grep -vE '/tests?/'` griff nicht, weil die Pfade ohne
fuehrenden Schraegstrich beginnen (`tests/test_...`). Nach der Korrektur — nur `{% url %}` in
Templates/JS und `reverse`/`redirect` im Python als Aufrufer, Testpfade als `(^|/)tests?/`
ausgeschlossen — waren es **19**, und die Negativkontrolle (`review` muss drin stehen) hielt.

## Step 5: Erfolgsaussehende Ausgaben pruefen (E7)

Zeigt eine Station generierten oder extrahierten Inhalt (Angebotstext, Dokumenttext, Export),
wird er gegen die Quelle gehalten: Ersatzzeichen-Anteil, Prompt-Fragmente, Rohbytes, HTML in einer
Datei. Sieht ein Fallback aus wie Erfolg, ist **das** der Befund (`fallback-als-erfolg`), auch wenn
die Station „funktioniert". Dreimal in einer Sitzung (ausschreibungs-hub 2026-08-25).

## Step 5b: Falsifikator-Gegenpart (E13–E17, PFLICHT ab 2026-09-01)

Jeder Befund geht **vor** dem Issue durch ein zweites Modell einer **anderen
Trainingsfamilie**, das ihn zu widerlegen versucht. Es produziert keinen eigenen Befund (E13).

```bash
python3 <platform>/tools/ux_falsifikator.py --datei /tmp/befund.json
# {"spruch": "bestaetigt|widerlegt|unklar|uebersprungen", "begruendung": "…", "modell": "…", "geprueft_am": "…"}
```

Eingabe-JSON: `klasse`, `severity`, `station`, `symptom`, `antwortkoerper`, `gegenprobe`,
`referenz`, `bekannt`. Rung **T1a** (`openai/gpt-oss-120b` ueber Groq, Schluessel-Zeiger
`~/.secrets/groq_api_key`) — der Ertrag ist die andere Familie, nicht die Rung (E14).

**Drei Regeln, die hier leichter verletzt werden als sie klingen:**

1. **Der Spruch filtert nicht (E16).** `widerlegt` unterdrueckt **kein** Issue. Der Befund
   wird angelegt, der Spruch steht als Feld darin. K1/K2 zaehlen den ungefilterten Lauf —
   sonst misst das Kill-Gate ab dem 01.09. ein anderes Werkzeug als am 25.08. Deshalb liefert
   das Werkzeug auch bei `widerlegt` Exit 0; wer es als Gate verdrahtet, verletzt E16.
2. **Kein Bild, keine Echtdaten (E17).** Screenshots gehen nie an den Gegenpart — das
   Werkzeug bricht ab, wenn ein Bildfeld gesetzt ist. Lief der Durchlauf gegen echte Daten,
   dann `--echtdaten`: es wird **nicht** gefragt, das Feld traegt `uebersprungen`.
3. **`uebersprungen` und `unklar` sind keine Bestaetigung.** Kein Schluessel, Anbieter nicht
   erreichbar, unlesbare Antwort → der Befund laeuft normal weiter, und der Bericht sagt es.

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
**Falsifikator (Pflicht ab 2026-09-01):** <spruch> · <modell> · <begruendung in einem Satz>
```

Severity `optimierung` **ohne** Referenz wird kein Issue, sondern eine Zeile im Bericht (R3).
Bekannte Befunde (Step 0) bekommen kein neues Issue. Mit `--no-issues`: Schema auf stdout.

## Step 7: Sammel-Issue = Bericht

Ein Issue `[ux-review] <repo> · <kette> · <datum>` im Zielrepo mit der Stationstabelle
(drei Zustaende), den Links auf die Befund-Issues, der Liste getippter URLs (K4) und dem
Zaehler `befund / ok / blind / bekannt`. Der Owner traegt je Befund-Issue `fehlbefund` als Label
nach — daraus rechnet das Kill-Gate K2 die Quote.

Dazu **eine zweite Spalte** `Falsifikator` je Befundzeile mit dem Spruch aus Step 5b und
darunter der Zaehler `bestaetigt / widerlegt / unklar / uebersprungen`. Die Spalte steht
**neben** der Rohzahl, nie an ihrer Stelle (E16): das Gate liest links, der Gegenpart rechts.
Wo Spruch und Owner-Label auseinanderfallen, ist genau das der Ertrag des Laufs — ein
`widerlegt` ohne `fehlbefund` ist ein Fehler des Gegenparts (R7) und gehoert in den Bericht.

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
| `built-but-never-called` | Funktion existiert im Code, kein Weg in der Oberflaeche fuehrt hin | Test: jede seitenrendernde View gegen die `{% url %}`/`action=` aller Templates, Ausnahmen mit Grund — writing-hub 2026-08-26, fuenf Faelle an einem Tag |
| `sichtbar-nur-unter-falscher-bedingung` | Knopf/Feld steht in einem `{% if %}`, das nicht zu seiner Phase gehoert | UX-Test rendert die Seite **ohne** die Bedingung und prueft die Sichtbarkeit — writing-hub #775: zwei Knoepfe, die aus dem KONZEPT arbeiten, standen in `{% if has_outline %}` |
| `gemockt-und-deshalb-blind` | Alle Tests gruen, erster echter Klick bricht | Test, der die gemockte Schicht **echt** ausfuehrt (Vorlagen rendern, Router aufrufen) — writing-hub #774: drei Prompt-Vorlagen brachen, weil jeder Test den Renderer ersetzt hatte |
| `daten-invariante` | Anzeige widerspricht der Sache (abgelaufene Frist bei laufender Ausschreibung) | Invarianten-Melder ueber den Datenbestand, **SKIP ist kein PASS** |
| `nur-mit-daten-sichtbar` | Seite ist auf einem frischen Objekt tadellos und auf einem benutzten tot; Tests und Probelauf sind gruen, echte Nutzer stehen an | Test, der die Seite **mit Bestand** rendert und pruefte, was der Browser wirklich bekommt — im Realfall: jeden ausgelieferten `application/json`-Block parsen. Ausnahmen mit Grund — writing-hub#820: ein handgebauter JSON-Block trug ein nachgestelltes Komma, aber nur wenn Belege vorlagen; 3 Prod-Projekte tot, 22 UX-Tests gruen, 24 Tage kein Melder |

Neue Klasse gefunden → Zeile hier ergaenzen (PR nach platform), nicht nur im Issue beschreiben.

## Output-Format

```
== /ux-review <repo> · Kette: <k> · Stand: <sha> · Basis: <url> ==

Umgebung
  Worktree: <pfad> · Stack: <eigen|staging> · Port frei: ja · Testkonto: <zeiger|blind>

Stationen
  # | Station         | Zustand | Datenlage          | Klasse            | Beleg
  1 | Login           | ok      | —                  | —                 | —
  2 | Angebotsentwurf | befund  | 3 Pos., 2 Belege   | nicht-begehbar    | URL getippt: /angebote/review/ (kein Link ab Station 1)
  3 | Freigabe        | blind   | frisch (leer)      | Klickbudget 25    | —

  Die Spalte `Datenlage` ist Pflicht: `ok` auf einem leeren Objekt sagt nichts
  ueber ein benutztes (Klasse `nur-mit-daten-sichtbar`).

Getippte URLs (K4): <n> — <liste>
Zaehler: befund <b> · ok <o> · blind <x> · bekannt <k>
Falsifikator (E16 — neben der Rohzahl, nicht statt ihrer):
  bestaetigt <a> · widerlegt <w> · unklar <u> · uebersprungen <s>   Modell: <modell>

Issues (Zielrepo <owner>/<repo>)
  #<n> nicht-begehbar · fehler · Gate: Routen-vs-Templates · Falsifikator: bestaetigt
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
- ❌ **Code lesen, bevor die gemeldete Seite einmal im Browser stand** (Step 0.5). Sieben
  widerlegte Hypothesen gegen einen Klick, der in einer Sekunde traf — 2026-08-28.
- ❌ **Einen gemeldeten Befund an einem neu angelegten Objekt nachstellen.** Frisch ist leer,
  und leer verdeckt genau die Klasse, die den Nutzer getroffen hat.
- ❌ **`ok` ohne Datenlage berichten** — die Null gilt nur fuer den Zustand, den man geprueft hat.
- ❌ **`optimierung` ohne Referenz** als Issue — Geschmack ist kein Befund.
- ❌ **Check-Listen durch `tail`/`head` filtern** und dann „alles gruen" melden (Retro #2325 #1).
- ❌ **Issue ohne Klassen-Gate-Vorschlag** — dann ist der Agent ein Melder, und Kill-Gate K3 faellt.
- ❌ **Einen Befund wegen `widerlegt` nicht anlegen** — der Gegenpart urteilt, er filtert nicht
  (E16). Wer so zaehlt, misst ab dem 01.09. ein anderes Werkzeug als das, dessen Gate laeuft.
- ❌ **`uebersprungen` als Bestaetigung lesen** — kein Schluessel ist kein Urteil.
- ❌ **Screenshot an den Gegenpart** — E17 ist eine Grenze an der Eingabe, keine Zusicherung.

## 🌀-Memory-Discovery-Pfad

- `project_ux_review_agent_program` (platform) — Owner-Prio 2026-07-22, Stand KONZ-051
- pgvector `error:ausschreibungs-hub:20260825-screen-ohne-weg` — 14 Routen, Test ueber alle
- pgvector `error:ausschreibungs-hub:f8820cc8a690` — HTMX-4xx unsichtbar, fremder Port, `::1`
- Outline „Sechs Befunde, die nur ein Browser sehen konnte" (2026-08-25) — vier Regeln, fuenf Gates
- Retro `session-retro-2026-08-25-writing-hub-fdd368` (#2325) — Fehlbefund, geteilte `.env`, `tail`

## Bezug

- `platform:KONZ-platform-051` — Konzept, Ledger E1–E17, Kill-Gate K1–K9 (Frist 2026-09-30)
- `platform:tools/ux_falsifikator.py` + `platform#2466` — Step 5b, Gegenpart-Werkzeug
- `~/.claude/policies/llm-routing.md` — Rung T1a, warum nicht Frontier (E14)
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

### Test 4 — Ein leeres Objekt darf nicht gruen machen (E10, Klasse `nur-mit-daten-sichtbar`)

```
/ux-review writing-hub --kette "Login > Projekt > Schreiben" --vor <sha vor #820> --no-issues
```
**Erwartung, zweigeteilt — genau hier ist der Skill am 2026-08-27 durchgefallen:**
- Mit einem **frisch angelegten** Projekt: Station „Schreiben" meldet `ok`, Konsole leer.
  Dieser Lauf ist **kein** Beleg und muss im Bericht die Datenlage `frisch (leer)` tragen.
- Mit einem Projekt **mit Bestand** (Kapitel + Belege): Station `befund`, Klasse
  `nur-mit-daten-sichtbar`, Konsole zeigt `SyntaxError … JSON.parse`, und der Bericht
  fuehrt die Datenlage mit.

Besteht der Skill nur den ersten Teil, ist die Erweiterung wirkungslos.

### Test 5 — Der Gegenpart trennt Fehlbefund von Defekt (K9, Step 5b)

```
python3 tools/ux_falsifikator.py --datei <befund>.json     # drei Befunde nacheinander
```
**Erwartung, alle drei in einem Lauf — er ist erst bestanden, wenn keiner fehlt:**
- Fehlbefund der #760-Klasse (Absenz behauptet, `gegenprobe` meldet `project_form.html:171`)
  → `widerlegt`, Begruendung nennt Regel 2.
- Echter Defekt (Station nur per getippter URL, `gegenprobe` 0 Treffer) → `bestaetigt`.
- `optimierung` ohne `referenz` → `widerlegt`, Regel 3.

Gemessen am 2026-08-30 gegen `openai/gpt-oss-120b`: alle drei getroffen. **Der zweite Teil
ist der wichtigere** — ein Gegenpart, der auch den echten Defekt widerlegt, ist ein Filter
(R7), kein Pruefer, und faellt per K9 einzeln raus.

## Changelog

- 2026-08-30 (Pilot K1 ausschreibungs-hub, Stand 8c8090e — Trockenlauf, keine Issues):
  Kette Einstieg → Anmeldung → Ausschreibungen → Detail → Bid/No-Bid → Angebot → Freigabe →
  Abgabe. **2 von 6 bekannten Defekten wiedergefunden** (mehrzeiliger `{# #}` als sichtbarer
  Text auf zwei Seiten; beide unbegehbaren Stationen `angebote:review` und
  `submission_workflow`), **2 getippte URLs**, beide als Befund im Bericht (K4 gehalten).
  Dazu zwei Defekte, die erst **nach** dem Stichtag gefixt wurden und der Lauf trotzdem fand:
  „Anmelden" fuehrte auf der Startseite zur Preisliste, und `development.py` verdrahtete die
  geteilte Dev-Datenbank fest — Letzteres traf den Lauf selbst: der erste
  `migrate_schemas --shared` landete trotz gesetzter `DB_*`-Variablen auf `localhost:5436`.
  **Drei Defekte blieben blind** (R8): sie liegen hinter dem Portal-Abruf der
  Vergabeunterlagen, und die Upload-Tuer daneben weist `.docx` serverseitig ab. **Einer ist
  fuer jeden Browser-Lauf unsichtbar** (fehlendes `docx`-Extra — das fand CI). Step 5b lief
  ueber alle sieben Befunde: 6 `bestaetigt`, 1 `widerlegt` — und dieses eine war der Fehler
  des Gegenparts (R7), Anlass fuer E18 in Step 4.

- 2026-08-30: **Step 5b Falsifikator-Gegenpart** ergaenzt (KONZ-051 E13–E17, K9,
  Umsetzungs-Issue platform#2466), Werkzeug `tools/ux_falsifikator.py` + 15 Tests.
  Owner-Entscheidung: Start **2026-09-01**, also **im laufenden Kill-Gate** — deshalb ist
  E16 die harte Regel dieses Schritts: der Spruch laeuft als zweite Spalte neben der
  Rohzahl, filtert nichts weg, und K1/K2 bleiben mit dem Stand vom 25.08. vergleichbar.
  **Abweichung vom KONZ-Text** (dort nachgetragen): der Spruch steht als **Feld im
  Befund-Issue** statt als nachtraeglicher Kommentar — dieselbe Leseflaeche, ein Artefakt
  statt zwei. **Beim Bau gemessen, nicht vermutet:** der erste echte Lauf lief in
  `HTTP 403 error code: 1010` — das ist Cloudflare vor Groq, das die urllib-Vorgabe als
  Bot abweist, **nicht** ein ungueltiger Schluessel. Derselbe Schluessel mit gesetzter
  `User-Agent`-Kennung liefert 200; die Kennung ist deshalb Pflicht im Werkzeug und durch
  einen Test festgehalten. Test 5 (K9) am selben Tag gruen: Fehlbefund `widerlegt`,
  echter Defekt `bestaetigt`, Geschmacks-Issue `widerlegt`.

- 2026-08-28: **Step 0.5 „Das gemeldete Objekt zuerst — im Browser"** ergaenzt
  (Owner-Weisung, woertlich: „Playwright und/oder Cloudflare KONSEQUENT einsetzen um
  Browser-Inhalte zu sehen und zu analysieren"), dazu **Konsole als Kill-Kriterium**
  (Step 3.2), **Datenlage als Pflichtangabe** in Step 1.4 und im Bericht, und die neue
  Klasse **`nur-mit-daten-sichtbar`**. Anlass: writing-hub#820. Der Owner meldete dreimal
  „Knopf reagiert nicht"; sieben Hypothesen wurden durch Code-Lesen geprueft und alle
  sieben waren falsch, waehrend der erste echte Klick die Ursache in der ersten Sekunde
  zeigte (`SyntaxError` bei `JSON.parse`, nachgestelltes Komma in einem handgebauten
  Block). Besonders unbequem: **dieser Skill lief an dem Tag und fand nichts** — sein
  eigener Step 1.4 (synthetische Daten) legt frische, leere Objekte an, und der Defekt
  trat nur mit Bestand auf. „0 Konsolenfehler" wurde als Beleg gelesen, obwohl er nur
  fuer den leeren Zustand galt. Gemessen im Zielrepo: 0 von 22 UX-Tests legten Belege an,
  0 von 22 oeffneten die betroffene Seite; 3 Prod-Projekte waren tot, 24 Tage ohne Melder.

- 2026-08-25: Initial — Stufe 1 aus KONZ-platform-051 (Owner „3 go"). Abweichungen vom
  KONZ-MVC, dort nachgetragen: Bericht = Sammel-Issue statt Datei im Zielrepo (E3 erlaubt
  keine PRs dorthin); Issue-Schema lebt im Skill statt als platform-Issue-Template (das gaelte
  nur fuer Issues in platform — Doppelquelle). Klassen-Katalog mit acht Klassen aus
  writing-hub/ausschreibungs-hub. Dogfood-Tests 1–2 sind die Positivkontrolle des Kill-Gates
  und laufen im Pilot, nicht im PR dieses Skills. Dogfood beim Bau: Test 3 stand zuerst auf
  Port 9 — Chromium lehnt den als „unsafe port" ab (`ERR_UNSAFE_PORT`), der Test haette den
  Browser gemessen, nicht den Dienst; auf 65530 korrigiert (`ERR_CONNECTION_REFUSED` = `blind`).
- 2026-08-25 (Pilot K1 writing-hub, Stand vor #761 — writing-hub#767): Kette Login → Ideen-Studio
  → Projekt → Konzept → Kapitel → Export klick-only, 0 getippte URLs, **3 von 3 bekannten
  Defekten wiedergefunden** (#758 escapejs, #759 konzept_vorschlag ohne Fallback, #762 Wortzahl
  nicht gespeichert) und **1 neuer Befund** (Meldung ≠ Aufruf: aifw-Cache vs. frische DB-Abfrage,
  writing-hub#766). Fehlbefund-Kandidat #760 als Rendering-Bedingung erkannt (E2). Step 1 um
  Seed/Doctor, Cache-Leerung und Testkonto ergaenzt — ohne beides war Station 2 `blind`.
