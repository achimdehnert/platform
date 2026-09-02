---
description: PFLICHT bei JEDER Arbeit an GUI, Templates, Views oder einer Bedien-Kette (Owner-Weisung 2026-08-26) — vor dem ersten Klick aufrufen, nicht danach. Prueft eine Kette oder den kompletten Pfad klick-only durch die laufende App: Begehbarkeit ohne getippte URL, Konsole, Antwortkoerper, Inhalt je Station gegen referenzierte Kriterien, Funktionen ohne Aufrufer; je Befund ein Issue mit Klassen-Gate-Vorschlag (KONZ-051 Stufe 1), danach Ursache und Fix-PR mit Gate-Test (Stufe 1c, `--nur-melden` haelt beim Bericht an). Ausloeser: GUI, Oberflaeche, Template, Screen, Knopf, Formular, Durchlauf, e2e, klicken, Bedienbarkeit, „funktioniert das im Browser"
mode: write
scope: geteilt
statefulness: zustandslos
trigger: interaktiv
---

# /ux-review — Pfad klick-only pruefen, Inhalt lesen, je Befund ein Klassen-Gate und ein Fix

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
> Bis Step 7 **aendert dieser Skill keinen Code** — er klickt, liest, urteilt und legt Issues
> an. **Step 8 (Stufe 1c, seit 2026-09-01)** behebt danach jeden Befund `fehler` per PR im
> Zielrepo, mit belegter Ursache und dem Klassen-Gate als Test. `--nur-melden` haelt bei
> Step 7 an. Der Bericht aus Step 7 entsteht **immer zuerst** und ist in beiden Modi
> byte-gleich — das Kill-Gate (K1/K2) misst ihn, nicht den Fix (E16).

## Verwendung

```
/ux-review <repo> [--kette "<Station 1> > ... > <Station n>" | --alle] [--basis <url>] [--vor <sha>] [--no-issues] [--nur-melden] [--max-klicks <n>] [--max-seiten <n>] [-kd <name>] [-marker <name>[,<name>]]
```

| Argument | Pflicht | Default | Bedeutung |
|---|---|---|---|
| `<repo>` | ja | — | Ziel-Repo (Slug); Issues landen **dort** |
| `--kette` | eins von beiden | — | Stationen in Reihenfolge; „Station erreicht" ist das Abbruchkriterium je Schleife |
| `--alle` | eins von beiden | gilt ohne `--kette` | **Pfad-Modus:** die Stationen werden nicht vorgegeben, sondern ab dem Einstieg per Breitensuche ueber alle Klicks erlaufen — Step 2a. Liefert die Zeile `Abdeckung: besucht n / Routen m` |
| `--max-seiten` | nein | `60` | Pfad-Modus: Obergrenze besuchter Seiten, danach `blind: Seitenbudget` fuer alles Unbesuchte |
| `--nur-melden` | nein | aus | Lauf endet mit Step 7 (Bericht + Issues), Step 8 (Beheben) entfaellt — das Verhalten vor 2026-09-01 |
| `--basis` | nein | lokaler Stack aus Step 1 | Basis-URL (lokal oder Staging — **nie** eine Cloudflare-Access-Domain) |
| `--vor` | nein | `origin/main` | Commit, gegen den geprueft wird (Positivkontrolle: Stand **vor** einem Fix) |
| `--no-issues` | nein | aus | nur Bericht auf stdout, keine Issues (Trockenlauf) |
| `--max-klicks` | nein | `25` | Klicks je Station ohne neue Seite, bevor die Station `blind` wird |
| `-kd` | nein | aus | Name eines Klickdummys des Zielrepos. Das **Verzeichnis** angeben, nicht die Datei: der Bestand kennt zwei Namen (`spec.yaml` und `screens-spec.yaml`, letzterer per ADR-185). Gleicht dessen Screens gegen die besuchten Stationen ab — Step 5c |
| `-marker` | nein | aus | Eigennamen, die in Station 1 eingegeben und in jeder Folgestation gesucht werden. Ein Kontrollmarker kommt automatisch dazu — Step 5c |
| `--auswahl-bei` | nein | aus | Erste Station, die nur noch die gewaehlte von mehreren Alternativen zeigt. Ohne sie meldet `-marker` an jedem Fan-out einen Scheinriss — Step 5c |

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

### Step 2a: Pfad-Modus — Stationen erlaufen statt vorgeben (`--alle`, E22)

Ohne `--kette` gibt es keine Liste, die man abhaken koennte — der Pfad **ist** die App.

1. Start auf der Seite nach dem Login. Warteschlange = alle klickbaren Elemente dieser
   Seite (Navigation, Listenzeilen, Knoepfe, `hx-get`/`hx-post`-Trigger, Formular-Submits
   mit synthetischen Daten aus Step 1.4).
2. Breitensuche: jedes Element einmal klicken; fuehrt der Klick auf eine **neue** Seite
   (neuer Pfad ohne Query, oder neuer Hauptinhalt bei HTMX), ist das eine Station und ihre
   Klicks kommen hinten an die Warteschlange. Logout, Loeschen und externe Links werden
   notiert, nicht geklickt.
3. Abbruch: Warteschlange leer ODER `--max-seiten` erreicht. Alles, was danach unbesucht
   bleibt, ist `blind: Seitenbudget` — nie `ok`.
4. Jede erlaufene Station durchlaeuft Step 3 und Step 3.5 wie eine vorgegebene.
5. **Abdeckung** = besuchte Stationen gegen die seitenrendernden Routen aus Step 3b. Jede
   Route, die kein Klick erreicht hat, ist `nicht-begehbar` — **nicht** „nicht besucht".
   Die Zeile `Abdeckung: besucht n / Routen m` steht im Bericht (Step 7).
   **Der Nenner `m` zaehlt nur Seiten:** GET-Routen, die ein Template rendern. Routen, die
   nur per POST/JSON antworten (`require_POST`, `http_method_names`, `JsonResponse`), sind
   keine Stationen — sie gehoeren in Zaehlung (b) aus Step 3b, nicht in `m`. Gemessen
   writing-hub 2026-09-02: 204 URL-Namen, davon 48 per Klick erreicht; die sieben Routen
   ohne Template-Verlinkung waren alle JSON-/POST-Endpunkte — mit ihnen im Nenner liest
   sich `48 / 204` wie eine Luecke, die keine ist.
6. **Werkzeug:** `python3 <platform>/tools/ux_pfad.py --basis <url> --login <pfad>
   --max-seiten <n> --out /tmp/pfad.json` — Breitensuche ueber interne Anker, je Station
   Konsole, 4xx/5xx, JSON-Bloecke, HTMX-Triade, Leerzustand-Hinweis. Formular-Submits
   und `hx-post`-Knoepfe **notiert es, klickt sie nicht** — der Bericht sagt das unter
   „Nicht verifiziert", bis Step 2a.1 dafuer ein Verfahren hat. Anker nur **sichtbar**
   klicken (`:visible`): am 2026-09-02 traf `.first` einen unsichtbaren Anker und meldete
   die Outline-Detailseite `blind`, die per Klick auf das sichtbare Icon sofort stand.

Die Kettenform bleibt fuer Positivkontrollen (K1, `--vor`) das Mittel der Wahl: sie hat
ein benanntes Ziel und damit ein messbares „erreicht". Der Pfad-Modus hat statt dessen die
Abdeckung — und findet, wofuer niemand eine Kette geschrieben haette.

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

## Step 3.5: Inhalt lesen — UX, Ablauf, Logik je Station (E23, PFLICHT)

Step 3 fragt, ob die Station **steht**. Step 3.5 fragt, ob ein Mensch auf ihr **weiterkommt**
und ob das, was sie zeigt, **stimmt**. Grundlage ist der Seitentext aus dem Snapshot, nicht der
Code. Jedes Kriterium traegt seine Referenz; ein Kriterium ohne Referenz gibt es hier nicht
(R3: Geschmack ist kein Befund).

| # | Kriterium | Referenz | Klasse bei Verstoss | Severity |
|---|---|---|---|---|
| I1 | Zweck der Station am Titel/`h1` erkennbar, nicht generisch („Detail", „Seite") | ADR-251 (UX-Gate: jede Station benennt ihren Schritt) | `zweck-unklar` | optimierung |
| I2 | Naechster Schritt als **Klick** vorhanden — die Kette geht ohne getippte URL weiter | ADR-251; KONZ-051 E1 (klick-only) | `sackgasse` | fehler |
| I3 | Leerzustand nennt eine Handlung („Erstes Projekt anlegen"), nicht nur eine leere Tabelle | ADR-049 (Leerzustand-Pattern) | `leerzustand-ohne-handlung` | optimierung |
| I4 | Fehler ist sichtbar **und** nennt, was der Nutzer tun kann; Antwortkoerper und Anzeige sagen dasselbe | ADR-048 §Fehleranzeige; Klasse `stiller-fehler` | `stiller-fehler` (unsichtbar) · `fehler-unverstaendlich` (sichtbar, aber ohne Handlung) | fehler |
| I5 | HTMX-Triade an jedem Trigger: `hx-target` + `hx-swap` + `hx-indicator` | ADR-048 (alle drei, keine Ausnahme) | `htmx-triade-fehlt` | optimierung |
| I6 | Formular: Pflichtfelder markiert, Fehler **am Feld**, Eingaben nach Fehler erhalten | ADR-040 (Formular-Pattern) | `formular-verliert-eingabe` | fehler |
| I7 | Angezeigter Zustand widerspricht nicht den Daten (Frist, Status, Zaehler, Summen) | Klasse `daten-invariante` (Katalog) | `daten-invariante` | fehler |

Vorgehen je Station, nach Step 3:

1. Titel, Hauptinhalt, Knoepfe und Meldungen aus dem Snapshot **lesen** — bis zum Ende der
   Seite, nicht bis zum ersten Treffer.
2. I1–I7 durchgehen; jede Zeile bekommt ein Urteil `ok | befund | n/a` und bei `befund` das
   Zitat aus dem Seitentext als Beleg. `n/a` nur mit Grund (kein Formular auf der Seite).
3. I7 braucht den Datenzustand aus Step 1.4: auf einem leeren Objekt ist I7 `n/a`, nie `ok`.
4. Befunde aus Step 3.5 laufen wie alle anderen durch Step 5b (Falsifikator) und Step 6
   (Issue). `optimierung` ohne die Referenz aus der Tabelle wird kein Issue (R3).

Abgrenzung zu `/repo-ux-opt`: der liest **Code** ohne zu klicken und auditiert die ganze App
gegen das Design-System. Step 3.5 liest den **gerenderten Text** der Stationen, die der Lauf
tatsaechlich erreicht hat — und nur die.

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

**Zwei Zaehlungen, nicht eine — und sie beantworten verschiedene Fragen** (gemessen
2026-08-30 am E19-Stand `dbf86ce`, platform#2474):

| Zaehlung | Als Aufrufer zaehlt | Frage | Ergebnis am Stand |
|---|---|---|---|
| **(a) ohne jeden Aufrufer** | `{% url %}` **und** `reverse`/`redirect` im Python | Ist der Code tot? | 16 von 48 |
| **(b) ohne Template-Verlinkung** | nur `{% url %}` in Templates/JS | Kommt ein **Mensch** per Klick hin? | 18 von 57 |

Fuer die Klasse `nicht-begehbar` gilt **(b)**. `angebote:review` ist der Beleg, dass die
Unterscheidung nicht akademisch ist: die Route hat drei `redirect("angebote:review", …)`
im Python und **keine** einzige Template-Verlinkung — in (a) faellt sie heraus, in (b)
steht sie drin, und im Browser war sie nur ueber eine getippte URL erreichbar. Wer nur
(a) misst, meldet die Station als versorgt.

**Kontrollen je Zaehlung, beide Pflicht:** in (b) muss `angebote:review` drinstehen
(negativ) und eine nachweislich verlinkte Route wie `ausschreibungen:detail` draussen
bleiben (positiv). Eine Positivkontrolle mit einem Namen, den es gar nicht gibt, ist
keine — sie besteht immer.

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
# {"spruch": "bestaetigt|widerlegt|unklar|uebersprungen", "begruendung": "…", "modell": "…",
#  "geprueft_am": "…", "laeufe": 3, "einig": true, "sprueche": ["bestaetigt", …]}
```

Eingabe-JSON: `klasse`, `severity`, `station`, `symptom`, `antwortkoerper`, `gegenprobe`,
`referenz`, `bekannt`. Rung **T1a** (`openai/gpt-oss-120b` ueber Groq, Schluessel-Zeiger
`~/.secrets/groq_api_key`) — der Ertrag ist die andere Familie, nicht die Rung (E14).

**Vier Regeln, die hier leichter verletzt werden als sie klingen:**

1. **Der Spruch filtert nicht (E16).** `widerlegt` unterdrueckt **kein** Issue. Der Befund
   wird angelegt, der Spruch steht als Feld darin. K1/K2 zaehlen den ungefilterten Lauf —
   sonst misst das Kill-Gate ab dem 01.09. ein anderes Werkzeug als am 25.08. Deshalb liefert
   das Werkzeug auch bei `widerlegt` Exit 0; wer es als Gate verdrahtet, verletzt E16.
2. **Kein Bild, keine Echtdaten (E17).** Screenshots gehen nie an den Gegenpart — das
   Werkzeug bricht ab, wenn ein Bildfeld gesetzt ist. Lief der Durchlauf gegen echte Daten,
   dann `--echtdaten`: es wird **nicht** gefragt, das Feld traegt `uebersprungen`.
3. **`uebersprungen` und `unklar` sind keine Bestaetigung.** Kein Schluessel, Anbieter nicht
   erreichbar, unlesbare Antwort → der Befund laeuft normal weiter, und der Bericht sagt es.
4. **Der Spruch ist eine Mehrheit aus drei Laeufen, kein Wurf (R9, E20).** Das Werkzeug fragt
   dreimal und gibt `laeufe`, `einig` und die Einzelsprueche mit aus. **`einig: false` gehoert
   in den Bericht**, auch wenn die Mehrheit eindeutig ist — gemessen am 2026-08-30 kippten zwei
   von elf Datensaetzen bei `temperature: 0` ([#2489](https://github.com/achimdehnert/platform/issues/2489)).
   Drei verschiedene Sprueche ergeben `unklar`, nie den zuerst gezogenen. `--laeufe 1` ist ein
   Testschalter, kein Sparmodus.

## Step 5c: Die zwei Gegenchecks — `-kd` und `-marker` (E10/E11, optional)

Beide beantworten eine Frage, die der Klick-Durchlauf allein **nicht** beantworten
kann, und beide werden von einem Werkzeug entschieden, nicht im Kopf:

```bash
python3 <platform>/tools/ux_gegencheck.py kd \
  --spec <zielrepo>/klickdummy/<name>/ \
  --stationen /tmp/stationen.json \
  --kette-deckt "Phase 1,Phase 2"

python3 <platform>/tools/ux_gegencheck.py marker \
  --stationen /tmp/stationen.json --marker "Milo Heller,Ada Brandt" \
  --auswahl-bei 4          # nur wo die Kette einen Auswahl-Schritt hat
```

`/tmp/stationen.json` schreibt der Lauf selbst, in Reihenfolge der Kette:
`[{"id": "<screen-id falls bekannt>", "titel": "<Stationstitel>", "text": "<sichtbarer Seitentext>"}, …]`

**`-kd` (E10).** Der Klick-Durchlauf sieht nur, was er erreicht hat. Die Spec sagt,
was erreichbar sein **sollte**. Die Differenz hat zwei Severities: `weg-fehlt`
(Screen mit `routing_mode: live` nie erreicht) ist ein **fehler**, `spec-luecke`
(Station ohne Screen) eine **optimierung** — der Klickdummy hinkt der App
hinterher, nicht umgekehrt (R5).

`--kette-deckt` ist Pflicht, sobald die Spec mehrere Flows traegt: ohne sie meldet
das Werkzeug jeden Screen einer **anderen** Kette als `weg-fehlt`. Deckt die
Angabe keinen einzigen Screen ab, bricht es mit Exit 2 ab — eine Null, die aus dem
eigenen Filter stammt, ist kein Ergebnis.

**`-marker` (E11).** Geprueft wird Durchgaengigkeit, nicht Textqualitaet: ein
Eigenname aus Station 1 muss in jeder Folgestation wieder auftauchen. Realfall C11
— der Protagonist hiess im Konzept „Milo Heller", in der erzeugten Gliederung
„Franz"; HTTP-gruen, inhaltlich gerissen.

Marker sind **plausible Eigennamen im Genre**, kein `ZZZ-TEST` (R6) — ein Name, den
der Autor nie schreiben wuerde, verzerrt die Erzeugung und misst dann sich selbst.

**`--auswahl-bei <n>` gehoert an jede Kette mit einem Fan-out.** Erzeugt eine
Station mehrere Alternativen und waehlt der Nutzer eine davon, verschwinden die
Marker der nicht gewaehlten voellig zu Recht. `n` ist die erste Station, die nur
noch die gewaehlte Alternative zeigt. Was dort fehlt, ist `marker-abgewaehlt`
(Hinweis, kein Befund); was dort noch da ist und **danach** verschwindet, bleibt
ein `marker-riss` — genau C11 passiert nach der Auswahl.

Ohne diesen Parameter meldet die Pruefung an jedem Fan-out einen Riss, der keiner
ist. Gemessen am 2026-09-01 im ersten echten Lauf: fuenf erzeugte Ideen, der
Marker stand nur in der nicht gewaehlten zweiten. Eine Pruefung, die dort immer
rot wird, wird abgeschaltet statt befolgt.

**Der Kontrollmarker ist die eigentliche Pruefung.** Das Werkzeug sucht zusaetzlich
einen Namen, der nirgends vorkommen darf. Findet es ihn, ist **die ganze Messung
ungueltig** (Exit 2) — nicht nur dieser eine Fund. Ohne ihn waere ein Suchlauf, der
nie etwas findet, von einem Suchlauf, der nichts zu finden hat, nicht zu
unterscheiden.

Beide Befundklassen gehen als normale Issues durch Step 5b und Step 6.

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
  · <bei `einig: false`: „uneinig: bestaetigt/unklar/bestaetigt“ — sonst weglassen>
```

Severity `optimierung` **ohne** Referenz wird kein Issue, sondern eine Zeile im Bericht (R3).
Bekannte Befunde (Step 0) bekommen kein neues Issue. Mit `--no-issues`: Schema auf stdout.

## Step 7: Sammel-Issue = Bericht

Ein Issue `[ux-review] <repo> · <kette> · <datum>` im Zielrepo mit der Stationstabelle
(drei Zustaende), den Links auf die Befund-Issues, der Liste getippter URLs (K4) und dem
Zaehler `befund / ok / blind / bekannt`. Im Pfad-Modus dazu die Zeile
`Abdeckung: besucht n / Routen m` (Step 2a.5). Der Owner traegt je Befund-Issue `fehlbefund` als Label
nach — daraus rechnet das Kill-Gate K2 die Quote.

Dazu **eine zweite Spalte** `Falsifikator` je Befundzeile mit dem Spruch aus Step 5b und
darunter der Zaehler `bestaetigt / widerlegt / unklar / uebersprungen` **plus** `uneinig: <n>`
(Befunde mit `einig: false`, R9). Die Spalte steht
**neben** der Rohzahl, nie an ihrer Stelle (E16): das Gate liest links, der Gegenpart rechts.
Wo Spruch und Owner-Label auseinanderfallen, ist genau das der Ertrag des Laufs — ein
`widerlegt` ohne `fehlbefund` ist ein Fehler des Gegenparts (R7) und gehoert in den Bericht.

## Step 8: Beheben — Ursache, Fix-PR, Gate-Test, Nachlauf (Stufe 1c, E24, PFLICHT ohne `--nur-melden`)

> Startet **erst**, wenn Sammel-Issue und Befund-Issues aus Step 6/7 existieren (bei
> `--no-issues`: wenn der Bericht auf stdout steht). Der Bericht ist das Messobjekt des
> Kill-Gates; ein Fix davor wuerde K1 den Fix mitzaehlen lassen (E16). Der Melder bleibt
> der Melder — Step 8 ist ein zweiter Akt, kein Ersatz.

Je Befund mit Severity `fehler`, in der Reihenfolge des Berichts:

1. **Ursache belegen, nicht raten** (`policies/error-handling.md` Regel 1): vom
   Antwortkoerper bzw. der Konsolenzeile zum Log/Stacktrace zur `Datei:Zeile`. Steht die
   Kette nicht luekenlos, traegt der Fix das Label **Hypothese** im PR-Text und im Bericht
   (`hypothese <h>`), und das Issue bleibt offen bis zum Beleg.
2. **Zweiter Fall derselben Klasse im selben Lauf → Gate zuerst** (error-handling Regel 4):
   erst der Test ueber alle Routen/Templates/Aufrufe aus der Katalog-Vorlage, dann die
   Einzelfixe, die er rot meldet. Ein Gate, das beim ersten Lauf nur den gemeldeten Fall
   findet, hat seinen zweiten Fall noch nicht — das steht so im PR.
3. **Branch im Zielrepo-Worktree** (Step 1.1): `ux-review/<datum>/<klasse>-<station-slug>`.
   `git branch --show-current` bestaetigen, bevor die erste Datei angefasst wird.
4. **Fix + Gate-Test im selben PR.** Der Klassen-Gate-Vorschlag aus dem Issue (Step 6,
   Pflichtfeld) wird hier zum Test — das ist der K3-Mechanismus, nicht eine Prosa-Zeile.
   Regressionstest-Name `test_should_<was_der_befund_verhindert>`. Tests des Repos per
   `make test`, nie rohes `pytest`.
5. **Nachlauf:** dieselbe Station **klick-only** gegen den Fix-Stand, mit demselben
   Datenzustand wie im Befund (Step 1.4 — ein frisches Objekt beweist nichts). Ergebnis
   `ok | befund | blind` steht im Block `Behoben`. Positivkontrolle: `--vor <sha vor Fix>`
   muss den Befund weiterhin zeigen, sonst hat der Nachlauf etwas anderes gemessen.
6. **PR** im Zielrepo: Titel `fix(<app>): <klasse> an <station> (ux-review <datum>)`,
   Body verlinkt das Befund-Issue (`Closes #<n>` nur, wenn Nachlauf `ok` **und** Ursache
   belegt), nennt Ursache mit `Datei:Zeile`, Gate-Test und Nachlauf-Ergebnis. Link-Basis
   vorher gegen `git remote get-url origin` pruefen (Org-Falle).
7. **Merge nach SA-5** (`policies/autonomy-gates.md`): ein PR zu einem in diesem Lauf
   angelegten Issue wird nach gruenem CI gemergt, nicht vorgelegt. **Ausnahme:** Repos, in
   denen Merge nach `main` ohne Environment-Schutz nach Prod deployt (Stand 2026-09-01:
   billing-hub, weltenhub) — dort bleibt der Merge Wort-pflichtig; der PR wartet mit dem
   Vermerk `Prod-Merge: Freigabe noetig` im Block `Behoben`.

Befunde mit Severity `optimierung` werden nur behoben, wenn die Referenz aus Step 3.5
benannt ist **und** der Diff klein bleibt (ein Template oder eine View). Sonst bleibt das
Issue stehen und der Bericht fuehrt es unter `offen <o>`.

Was Step 8 bewusst auslaesst, bekommt **im selben Lauf** ein Tracking-Artefakt (das
Befund-Issue bleibt offen, mit Kommentar warum) — „steht im PR-Text" zaehlt nicht.

## Klassen-Katalog (Gate-Vorlagen, die der Agent kennt)

| Klasse | Symptom im Browser | Klassen-Gate (Vorlage) |
|---|---|---|
| `nicht-begehbar` | Station nur per getippter URL | Test: jede seitenrendernde Route gegen `{% url %}` aller Templates, Ausnahmen **mit Grund** — Realfall ausschreibungs-hub 2026-08-25, 14 Routen ohne Weg; dort gebaut als `tests/test_erreichbarkeit_screens.py` |
| `stiller-fehler` | Klick „tut nichts", 4xx im Netzwerk | globaler `htmx:responseError`-Handler im Basis-Template — Realfall ausschreibungs-hub 2026-08-24, HTMX-4xx unsichtbar; dort gebaut in `templates/base/base.html:101` |
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
| `link-auf-none` | Ein Link im Template traegt `href="None"` und fuehrt auf 404 — die Variable war leer, das Template hat nicht gefragt | Rendering-Test der Seite in **jeder** Werkart/Konfiguration, die eine Phase auslaesst (Sachbuch, Bilddienst aus) + Gate ueber alle Templates: `href="{{ … }}"` aus einer Variablen nur innerhalb `{% if <variable> %}` — Realfall writing-hub 2026-09-02, Pfad-Modus Station 36: „Welt & Figuren" und „Illustration" auf der Workflow-Seite, auf `main` bestaetigt (writing-hub#949) |
| `sackgasse` | Station erreicht, aber kein Klick fuehrt zum naechsten Schritt der Kette — der Nutzer muss eine URL wissen | Test: fuer jede Station der Kette existiert im gerenderten Template der Vorgaengerstation ein `{% url %}`/`hx-get` auf ihre Route; Ausnahmen mit Grund — Klasse ohne Realfall-Marker (aufgenommen 2026-09-01, Step 3.5 I2), Marker folgt mit dem ersten belegten Fall |
| `leerzustand-ohne-handlung` | Leere Liste/Tabelle ohne Satz, was der Nutzer als naechstes tut | UX-Test rendert jede Listen-View mit leerem Queryset und prueft auf einen Handlungs-Link — ohne Realfall-Marker (2026-09-01, I3) |
| `fehler-unverstaendlich` | Fehler ist sichtbar, nennt aber weder Ursache noch Handlung („Ein Fehler ist aufgetreten") | Test ueber alle `messages.error(`/`form.add_error(`-Aufrufe: Text enthaelt ein Verb oder eine Ursache aus dem Audit-Trail; Liste generischer Saetze als Negativmuster — ohne Realfall-Marker (2026-09-01, I4) |

Neue Klasse gefunden → Zeile hier ergaenzen (PR nach platform), nicht nur im Issue beschreiben.
Klassen **ohne Realfall-Marker** stammen aus Step 3.5 und tragen ihr Aufnahmedatum; sie
bekommen den Marker mit dem ersten belegten Fall (K6-Regel vom 2026-09-01).

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

--- ab hier nur ohne --nur-melden (Step 8); der Block darueber ist in beiden Modi byte-gleich ---

Behoben (Stufe 1c)
  #<n> nicht-begehbar → PR <owner>/<repo>#<p> · Ursache: <datei:zeile> · Gate-Test: <datei> · Nachlauf: ok
  #<m> stiller-fehler → PR <owner>/<repo>#<q> · Ursache: Hypothese · Nachlauf: befund   (Issue bleibt offen)
  #<k> leerzustand-ohne-handlung → offen (optimierung, Diff > 1 Template)
Zaehler: behoben <f> · offen <o> · hypothese <h> · Prod-Merge wartet <p>
```

Im Pfad-Modus (`--alle`) steht unter `Stationen` zusaetzlich `Abdeckung: besucht n / Routen m`;
die Stationen-Tabelle traegt dann die erlaufene Reihenfolge.

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
- ❌ **Fix vor Bericht** — der Rohbericht (Step 7) entsteht immer zuerst; wer vorher fixt,
  laesst K1 den Fix mitzaehlen und misst ab dann ein anderes Werkzeug (E16).
- ❌ **Fix ohne belegte Ursache als `behoben` zaehlen** — ohne `Datei:Zeile` aus dem
  Antwortkoerper ist es eine Hypothese und steht so im Bericht (error-handling Regel 1).
- ❌ **Fix-PR ohne Gate-Test** — dann ist der Klassen-Gate-Vorschlag Prosa geblieben (R1).
- ❌ **Nachlauf auf einem frischen Objekt** — derselbe Datenzustand wie im Befund, sonst
  beweist `ok` nichts (Klasse `nur-mit-daten-sichtbar`).
- ❌ **Inhaltskriterium ohne Referenz** — Step 3.5 kennt nur I1–I7; „wirkt unaufgeraeumt"
  ist kein Befund und wird keiner, indem man es in eine Tabelle schreibt.
- ❌ **Unbesuchte Seite im Pfad-Modus als `ok`** — nach `--max-seiten` ist alles Unbesuchte
  `blind: Seitenbudget`.

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
- Jede der drei Ausgaben traegt `laeufe: 3` und ein `einig`-Feld (R9/E20). Fehlt eines davon,
  laeuft eine alte Kopie des Werkzeugs — dann ist der Spruch ein Wurf, kein Urteil.

Gemessen am 2026-08-30 gegen `openai/gpt-oss-120b`: alle drei getroffen. **Der zweite Teil
ist der wichtigere** — ein Gegenpart, der auch den echten Defekt widerlegt, ist ein Filter
(R7), kein Pruefer, und faellt per K9 einzeln raus.

### Test 6 — Pfad-Modus findet, wofuer niemand eine Kette schrieb (E22)

```
/ux-review writing-hub --alle --vor <sha vor der Verlinkung der fuenf Bausteine aus Step 3b> --no-issues --nur-melden
```
**Erwartung:** Bericht traegt `Abdeckung: besucht n / Routen m` mit `n < m`; jede Route aus
Zaehlung (b) in Step 3b (ohne Template-Verlinkung) erscheint als `nicht-begehbar`, keine als
„nicht besucht"; nach `--max-seiten 5` sind alle uebrigen Seiten `blind: Seitenbudget` und
der Zaehler `ok` ist kleiner als bei `--max-seiten 60`. **Und:** der Lauf findet mindestens
eine Station, fuer die keine Kette geschrieben ist — sonst rechtfertigt der Modus seinen
Preis nicht.

**Gelaufen 2026-09-02 gegen 080a298 (bestanden, mit zwei Korrekturen am Test selbst):**
51 Stationen bei `--max-seiten 60` (Warteschlange leer), `48 / 204`; die sieben Routen aus
Zaehlung (b) alle unbesucht; bei `--max-seiten 5`: 5 besucht, 14 `blind: Seitenbudget`,
`ok 4` statt `ok 49`. **Gefunden, wofuer niemand eine Kette schrieb:** Station 36 Workflow,
zwei Phasen als `href="None"` → 404, auf `main` bestaetigt (writing-hub#949, Klasse
`link-auf-none`). Korrekturen: die urspruengliche Erwartung nannte „fuenf Bausteine aus
Step 3b" — das sind Dienstfunktionen ohne Route (#781), keine Routen; und der Nenner
enthielt POST-/JSON-Routen (Step 2a.5 praezisiert).

### Test 7 — Beheben schliesst den Kreis: Issue → PR → Gate-Test → Nachlauf (E24, K3)

```
/ux-review writing-hub --kette "Login > Projekt > Schreiben" --vor <sha vor #820>
```
**Erwartung, alle vier — der Test ist erst bestanden, wenn keiner fehlt:**
- Bericht (Step 7) zeigt Station „Schreiben" als `befund`, Klasse `nur-mit-daten-sichtbar`,
  **bevor** irgendein Branch existiert (Reihenfolge im Transkript pruefbar).
- PR im Zielrepo mit Ursache `Datei:Zeile` (das nachgestellte Komma im JSON-Block), Gate-Test,
  der **jeden** ausgelieferten `application/json`-Block parst, und `Closes #<n>`.
- Nachlauf der Station mit Bestand (Kapitel + Belege) = `ok`; `--vor` zeigt den Befund weiter.
- Block `Behoben` im Bericht mit `behoben 1 · offen 0 · hypothese 0`.

### Test 8 — `--nur-melden` und Default liefern denselben Rohbericht (E16)

```
/ux-review writing-hub --kette "Login > Projekt > Schreiben" --no-issues --nur-melden > /tmp/a.txt
/ux-review writing-hub --kette "Login > Projekt > Schreiben" --no-issues              > /tmp/b.txt
diff <(sed -n '/^Stationen/,/^Nicht verifiziert/p' /tmp/a.txt) <(sed -n '/^Stationen/,/^Nicht verifiziert/p' /tmp/b.txt)
```
**Erwartung:** Diff = 0 Zeilen (bis auf Zeitstempel); `b.txt` traegt zusaetzlich den Block
`Behoben`. Weicht die Stationen-Tabelle ab, hat Step 8 in den Bericht zurueckgewirkt — dann
ist das Kill-Gate ab diesem Lauf nicht mehr mit dem Stand vom 25.08. vergleichbar.

**Gelaufen 2026-09-02 gegen db648374 (bestanden):** zwei Laeufe, Bestand 6 Kapitel/3 Belege;
Diff des Blocks `Stationen`…`Nicht verifiziert` = 0 Zeilen, Positivkontrolle (Kopfzeile
weicht ab) gehalten. Lauf b fuehrte Step 8 einmal real aus: `htmx-triade-fehlt` an Station 1
→ writing-hub#948 (Fix + Gate `tests/test_htmx_triade.py`, ohne Fix 2 failed, mit Fix
7 passed, Nachlauf `ok`), per SA-5 gemergt; Bestand derselben Klasse getrackt (#947).
**Luecke im Skill, dabei gemessen:** mit `--no-issues` gibt es kein Befund-Issue, das der
Fix-PR schliessen koennte — Step 8.6 `Closes #<n>` laeuft dann leer. Regel bis zur
Praezisierung: der PR verlinkt den Bericht und das Tracking-Issue des Bestands.

## Abschluss-Checkliste (vor „fertig" einmal durchzaehlen — Ausfuehrungstreue)

Bis 2026-09-01 hatte dieser Skill keine; ein Skill mit zehn Steps ohne Abschluss-Checkliste
ist strukturell ueberspringbar (Realfall `session-ende.md`, platform#1164).

- [ ] Step 0: `project-facts.md` gelesen, bekannte Befunde markiert
- [ ] Step 0.5: gemeldetes Objekt im Browser gesehen, bevor Code gelesen wurde
- [ ] Step 1: eigener Worktree, eigener Stack, Seed/Doctor, Cache geleert, Datenlage je Station notiert
- [ ] Step 2/2a: klick-only; jede getippte URL als Befund; Pfad-Modus mit Abdeckungszeile
- [ ] Step 3: Konsole + Netzwerk mit Antwortkoerper je Station; `blind` getrennt gezaehlt
- [ ] Step 3.5: I1–I7 je Station mit Urteil und Zitat; `n/a` nur mit Grund
- [ ] Step 3b: Routen ohne Aufrufer ueber drei Orte gesucht
- [ ] Step 4: jede Absenz mit Gegenprobe `Datei:Zeile`
- [ ] Step 5/5b: erfolgsaussehende Ausgaben geprueft; Falsifikator je Befund, `laeufe: 3`
- [ ] Step 6/7: je Befund ein Issue mit Gate-Vorschlag; Sammel-Issue mit Rohzahl **und** Spruch-Spalte
- [ ] Step 8 (ohne `--nur-melden`): je `fehler` Ursache belegt oder als Hypothese markiert; PR mit Gate-Test; Nachlauf mit Bestand; SA-5-Merge oder `Prod-Merge: Freigabe noetig`
- [ ] Ausgelassenes hat ein offenes Issue mit Kommentar
- [ ] Neue Klasse → Katalog-Zeile hier (PR nach platform)
- [ ] Nicht verifiziert: benannt, mit billigstem Check

## Changelog

- 2026-09-02 (Dogfood 6 + 8 gegen writing-hub, Owner „go"): **Test 8 bestanden** (Diff 0,
  Step 8 einmal real: writing-hub#948 gemergt, #947 Bestand), **Test 6 bestanden mit zwei
  Korrekturen am Test** (Bausteine ≠ Routen; Nenner nur Seiten — Step 2a.5). Werkzeug
  `tools/ux_pfad.py` fuer Step 2a, Klasse `link-auf-none` mit Realfall (writing-hub#949,
  auf `main` live). Test 7 steht aus — braucht einen offenen `fehler`; #949 ist einer.
  Werkzeug-Lehre: unsichtbare Anker nie klicken (`:visible`), sonst `blind` ohne Grund.

- 2026-09-01 (Stufe 1c, Owner-Auftrag „kompletten Pfad, Inhalte lesen, Fehler analysieren und
  beseitigen"): **Step 2a** Pfad-Modus `--alle` mit Abdeckungszeile (E22), **Step 3.5** Inhalt
  lesen mit sieben referenzierten Kriterien I1–I7 (E23), **Step 8** Beheben — Ursache nach
  `error-handling.md`, Fix-PR mit Gate-Test, Nachlauf mit Bestand, Merge nach SA-5 (E24).
  `--nur-melden` stellt das Verhalten davor her. **Steps 2–7 und der Output-Block bis
  `Nicht verifiziert` sind unveraendert** — Test 8 misst das; das Kill-Gate (Frist 30.09.)
  liest weiter den Rohbericht (E16). Drei Klassen ohne Realfall-Marker aufgenommen
  (`sackgasse`, `leerzustand-ohne-handlung`, `fehler-unverstaendlich`). Abschluss-Checkliste
  neu — der Skill hatte keine. Dogfood-Tests 6–8 sind das Review-Gate dieses Umbaus und
  standen beim Merge des PR **noch aus** (Tracking: siehe PR-Text / KONZ-051 E24).

- 2026-09-01 (K6-Messung, platform#2507-Sitzung): **Zwei Exemplare im Klassen-Katalog waren
  unmarkierte Repo-Pfade** (`nicht-begehbar`, `stiller-fehler`) — sie standen ohne Realfall-Marker
  direkt in der Gate-Vorlage und lasen sich wie eine Anweisung, den Test genau dort anzulegen.
  Beide tragen jetzt Datum und Anlass, wie die uebrigen Zeilen der Tabelle.
  **K6-Messung danach:** 31 Treffer, 4 ohne zeilenweisen Marker — Z18 (Marker steht eine Zeile
  hoeher im selben Blockquote), Z44 (`meiki-lra` ist eine **Org**, kein Repo; das Suchmuster
  faengt sie mit), Z428 (Dogfood-Test, muss das Pilot-Repo nennen), Z475 (Changelog).
  Keine davon steuert eine Anweisung. **Der Sache nach haelt die Blaupause; der Buchstabe des
  Kriteriums ist mit diesem grep nicht entscheidbar** — Vorschlag zur Praezisierung liegt beim
  Owner, K6 bleibt bis dahin `offen`.

- 2026-08-30 (3, E19-Lauf gegen vier Staende — platform#2474, Owner „25 weg 1; 30 go"):
  **K1 steht auf 8/9 und ist damit erfuellt.** ausschreibungs-hub 5 von 6, je am Commit vor
  dem eigenen Fix: `f1f600c` (sichtbarer `{# #}` auf zwei Seiten; CSRF-403 an „Analyse starten",
  Antwortkoerper `CSRF token missing`), `dbf86ce` (18 Routen ohne Template-Verlinkung; die
  Sammelmeldung „Alle Extraktions-Calls sind gescheitert." im Browser, Ursache nur im
  Audit-Trail), `2259b8e` (`.docx` als ZIP-Rohbytes, `text` beginnt mit `PK\x03\x04`).
  **Nicht reproduzierbar:** das fehlende `docx`-Extra — ein Deklarationsdefekt, den eine
  Laufzeitumgebung mit installierter Abhaengigkeit nie zeigt. Zwei Lehren stehen oben:
  die **zwei Zaehlungen** in Step 3b (a: toter Code, b: klickbar) und **E21** im Konzept
  (die Aufzeichnung wird auf den Stand aufgesetzt, nicht der Stand gehoben — ein Cherry-pick
  des Fixture-Commits scheitert an den Staenden, weil er einen spaeteren Refactor mitbringt).
  Handwerklicher Nebenbefund: `pkill -f "manage.py runserver …"` traf die eigene Shell mit
  (Exit 144) — der bekannte Selbsttreffer, hier real.

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

- 2026-08-30 (2): **Der Spruch ist eine Mehrheit aus drei Laeufen** (Option B aus platform#2489,
  Ledger E20). Die K9-Gegenprobe zeigte, dass zwei von elf Datensaetzen bei `temperature: 0`
  ueber drei Laeufe kippten — ein einzelner Aufruf ist damit keine Messung. Das Werkzeug gibt
  jetzt `laeufe`, `einig` und die Einzelsprueche aus; `einig: false` gehoert in den Bericht,
  drei verschiedene Sprueche ergeben `unklar`.
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
