---
description: Laufende App klick-only pruefen (Kette oder ganzer Pfad), je Befund Issue mit Klassen-Gate, dann Fix-PR mit Gate-Test
mode: write
scope: geteilt
statefulness: zustandslos
trigger: interaktiv
---

# /ux-review — Pfad klick-only pruefen, Inhalt lesen, je Befund ein Klassen-Gate und ein Fix

> **Wann:** PFLICHT bei JEDER Arbeit an GUI, Templates, Views oder einer Bedien-Kette (Owner-Weisung
> 2026-08-26) — **vor dem ersten Klick aufrufen, nicht danach.** Ausloeser: GUI, Oberflaeche, Template,
> Screen, Knopf, Formular, Durchlauf, e2e, klicken, Bedienbarkeit, „funktioniert das im Browser".
> Operationalisiert KONZ-platform-051 (Stufe 1 + 1c). Realfall 2026-08-25/26: ein GUI-Durchlauf ohne
> diesen Skill wiederholte drei Fehler, gegen die er geschrieben ist — geteilte `.env` umgestellt,
> Absenz ohne Gegenprobe behauptet, „0 erstellt" im Erfolgston uebersehen.
>
> **Wann NICHT:** Klickdummy pruefen → `/kd-review` (statisch, kein Login). App-Struktur aus dem Code
> auditieren, ohne zu klicken → `/repo-ux-opt`. Bekannten Defekt fixen → normaler PR-Flow. Bis zum
> Bericht aendert dieser Skill keinen Code; erst danach (Stufe 1c) behebt er `fehler`-Befunde per PR
> im Zielrepo — `--nur-melden` haelt beim Bericht an.

## Ziel

Im Zielrepo liegt ein Sammel-Issue mit Stationstabelle (`ok | befund | blind`, Datenlage je Station)
und je Befund ein Issue mit Klassen-Gate-Vorschlag; ohne `--nur-melden` ist zudem jeder `fehler` per
Fix-PR mit Gate-Test behoben oder als Hypothese/offen getrackt.

## Akzeptanzkriterien

- **A1 Begehbarkeit:** jede Station per Klick erreicht; jede getippte URL steht als Befund
  `nicht-begehbar` im Bericht (`Getippte URLs (K4): n`), im Pfad-Modus dazu `Abdeckung: besucht n /
  Routen m` (`m` = nur seitenrendernde GET-Routen). *Pruefung:* K4-Zahl = getippte URLs im Transkript.
- **A2 Konsole + Netzwerk:** je Station `browser_console_messages` + `browser_network_requests`
  ausgewertet; jeder JS-Fehler → `befund`; jede 4xx/5xx mit zitiertem **Antwortkoerper**.
  *Pruefung:* Befund-Issue zitiert Body/Konsole.
- **A3 Inhalt je Station:** I1–I7 mit Urteil `ok | befund | n/a` (`n/a` nur mit Grund); `optimierung`
  nur mit Referenz. *Pruefung:* jedes optimierung-Issue nennt ADR/Heuristik.
- **A4 Gegenrichtung:** Routen ohne Aufrufer in zwei Zaehlungen (a: kein Aufrufer, b: keine
  Template-Verlinkung) mit Positiv- und Negativkontrolle. *Pruefung:* beide Kontrollen im Transkript;
  (b)-Treffer im Bericht als `nicht-begehbar`.
- **A5 Je Befund ein Issue** im Zielrepo (`--label ux-review`) nach Schema — Klassen-Gate-Vorschlag,
  Gegenprobe (Zahl zuerst), Falsifikator (`laeufe: 3`, `einig`); Bekanntes als „bekannt (#N)".
  *Pruefung:* `gh issue list --label ux-review`, Pflichtfelder vorhanden.
- **A6 Bericht = Sammel-Issue** mit Stationstabelle (drei Zustaende + Datenlage), Zaehler
  `befund/ok/blind/bekannt`, Falsifikator-Spalte **neben** der Rohzahl, `Nicht verifiziert`.
  *Pruefung:* Output-Format bis `Nicht verifiziert` eingehalten.
- **A7 Beheben (ohne `--nur-melden`):** je `fehler` ein Fix-PR mit Ursache `Datei:Zeile`, Gate-Test
  `test_should_…` (ohne Fix rot, mit Fix gruen — beides gemessen), Nachlauf klick-only mit derselben
  Datenlage; `--nur-melden` und Default liefern denselben Rohbericht. *Pruefung:* Block `Behoben`;
  `diff` beider Berichte bis `Nicht verifiziert` = 0 Zeilen.

## Harte Gates

Alles hier ist PFLICHT/STOP — der Weg darf variieren, diese Punkte nicht.

**Umgebung**
- **G1** Vor dem ersten Klick aufrufen, nicht danach (Owner-Weisung 2026-08-26).
- **G2** Owner/Repo, Org, Typ, Dev-Port, HTMX aus `.windsurf/rules/project-facts.md` des Zielrepos —
  kein Hardcoding, Org nie raten; Issues landen in **dieser** Org.
- **G3** Anmeldung auf einem von drei Wegen, in dieser Reihenfolge — Wert nie auf stdout/im Bericht:
  (1) Zeiger `~/.secrets/<repo>-testuser`; (2) dokumentierter passwortloser Anmeldeweg des Repos
  (`make login`, Token-/Einmal-Link — der Zeiger ist das Kommando); (3) fehlen beide **und** der Stack ist
  der eigene: `createsuperuser` mit Wegwerf-Passwort, das mit dem Stack stirbt — nie in einem geteilten.
  Erst wenn keiner der drei Wege geht → Station 0 `blind: kein Testkonto`, kein Raten.
- **G4** Eigener Worktree, nie der Haupt-Tree; eigener Stack, Staging oder der eigene Dev-Stack des Zielrepos
  (dann steht das so im Bericht); nie eine geteilte `.env` aendern (eigene `.env.ux-review`, gitignored).
  Lauscht etwas auf dem Dev-Port, **erst zuordnen**: `docker ps --format '{{.Names}} {{.Ports}}'` bzw.
  `ss -tlnp` — gehoert Container-/Prozessname zum Zielrepo, ist er eine zulaessige Basis; gehoert er
  **nicht** dazu = STOP (man misst sonst eine fremde Instanz).
- **G5** Basis-URL nie eine Cloudflare-Access-Domain; `*.localhost` loest auf `::1` auf → `127.0.0.1`.
- **G6** Synthetische Daten (Prefix `uxr-<datum>`); Screenshot mit Mandanten-/Personendaten = Abbruch (R4,
  platform ist oeffentlich). Mindestens ein Objekt **mit Bestand**; Datenlage je Station im Bericht —
  `ok` ohne Datenlage ist kein Beleg.
- **G7** Seed/Doctor vor der ersten Bewertung; nach jedem Reseed Cache leeren (Web-Neustart reicht nicht).
  Leere Registry = Umgebungsluecke, kein Befund.
- **G8** Schreibvorgang auf einem Zielsystem (Diagnose-Session) nur mit ausdruecklicher Freigabe (Gate 2,
  `policies/autonomy-gates.md`); Loeschung im selben Zug.

**Messen**
- **G9** Gemeldeter Befund: **Browser vor Code** — erst `browser_navigate` + Konsole + Netzwerk auf der
  gemeldeten Seite, dann Quelltext; am gemeldeten Objekt messen, nie an einem frisch angelegten.
- **G10** Klick-only ab der Startseite; erlaubte URLs sind nur die Basis-URL und der Anmeldeweg aus G3
  (ein Einmal-Login-Link zaehlt nicht als getippte URL). Jede andere getippte URL = Befund
  `nicht-begehbar`, sofort notiert, nie verschwiegen (K4); der Lauf geht damit weiter.
- **G11** Drei Zustaende; `blind` ist nie gruen, zaehlt getrennt. Nach `--max-seiten` ist Unbesuchtes
  `blind: Seitenbudget`, nie `ok`; unerreichte Route = `nicht-begehbar`, nicht „nicht besucht".
- **G12** JS-Fehler in der Konsole → Station `befund`, ohne Ausnahme. Diagnose aus dem Antwortkoerper,
  nie aus dem Statuscode (403 ist CSRF **und** Tenant-Sperre).
- **G13** Absenz („fehlt") nur nach zweitem Suchpfad (`grep -rn` in templates/apps); Treffer =
  Rendering-Bedingung mit `Datei:Zeile`. Feld `gegenprobe` beginnt mit einer Zahl (E18).
- **G14** Zaehler (Step 3b/4) bestehen Positiv- **und** Negativkontrolle; Kontrolle mit nicht existierendem
  Namen zaehlt nicht. Je Treffer eine Antwort — einhaengen oder entfernen —, nie keine.
- **G15** Inhaltskriterien nur I1–I7 mit Referenz; Geschmack ist kein Befund (R3). I7 auf leerem Objekt
  `n/a`, nie `ok`.
- **G16** Erfolgsaussehende Ausgaben gegen die Quelle halten (`fallback-als-erfolg`); Check-Listen nie
  durch `head`/`tail` filtern und „alles gruen" melden.
- **G17** `-kd`: `--kette-deckt` Pflicht bei mehreren Flows (Exit 2 bei Null aus eigenem Filter). `-marker`:
  plausible Eigennamen, nie `ZZZ-TEST` (R6); `--auswahl-bei` an jeder Kette mit Fan-out; Fund des
  Kontrollmarkers = ganze Messung ungueltig (Exit 2).
- **G18** Werkzeug klickt nur sichtbare Anker (`:visible`); Formular-Submits/`hx-post` werden notiert
  (`Nicht verifiziert`), nicht geklickt.

**Falsifikator**
- **G19** Jeder Befund vor dem Issue durch `tools/ux_falsifikator.py` (andere Trainingsfamilie, Rung T1a).
  Der Spruch filtert nicht (E16): `widerlegt` unterdrueckt kein Issue; das Werkzeug ist kein Gate.
- **G20** Kein Bild, keine Echtdaten an den Gegenpart (E17); bei Echtdaten `--echtdaten` → `uebersprungen`.
  `uebersprungen`/`unklar` sind keine Bestaetigung.
- **G21** Spruch = Mehrheit aus drei Laeufen; `einig: false` gehoert in den Bericht; drei verschiedene
  Sprueche = `unklar`, nie der zuerst gezogene; `--laeufe 1` ist kein Sparmodus.

**Melden**
- **G22** Je Befund ein Issue; Pflichtfelder: Klassen-Gate-Vorschlag, Gegenprobe (bei Absenz), Referenz
  (bei `optimierung`), Falsifikator. Bekannte Befunde: kein neues Issue.
- **G23** Falsifikator-Spalte neben der Rohzahl, nie an ihrer Stelle; `widerlegt` ohne `fehlbefund`-Label =
  Fehler des Gegenparts (R7), steht im Bericht.
- **G24** Neue Klasse → Zeile im Klassen-Katalog (PR nach platform), nicht nur im Issue.

**Beheben (ohne `--nur-melden`)**
- **G25** Fix nie vor dem Bericht: Sammel- und Befund-Issues existieren zuerst (E16, K1); Rohbericht in
  beiden Modi byte-gleich.
- **G26** Ursache belegt (`Datei:Zeile` aus Antwortkoerper/Log) oder Label **Hypothese** in PR und Bericht,
  Issue bleibt offen. Zweiter Fall derselben Klasse → Gate-Test zuerst.
- **G27** Fix + Gate-Test im selben PR; `git branch --show-current` vor der ersten Datei; `make test`, nie
  rohes `pytest`; Link-Basis gegen `git remote get-url origin` pruefen.
- **G28** Nachlauf klick-only mit derselben Datenlage; `--vor <sha>` zeigt den Befund weiter. `Closes #n`
  nur bei Nachlauf `ok` **und** belegter Ursache.
- **G29** Merge nach SA-5 bei gruenem CI — **ausser** Repos, deren Merge nach `main` ohne Environment-Schutz
  nach Prod deployt (Stand 2026-09-01: billing-hub, weltenhub): Wort-pflichtig, `Prod-Merge: Freigabe noetig`.
- **G30** Ausgelassenes bekommt im selben Lauf ein Tracking-Artefakt (offenes Issue mit Kommentar).
- **G31** Dogfood-Tests sind das Review-Gate jedes Umbaus dieses Skills (`claude-skills.md`).

## Referenzpfad (nicht bindend)

Ein faehigeres Modell darf einen anderen Weg nehmen, solange Akzeptanzkriterien und Harte Gates erfuellt
sind. Die Werkzeug-Aufrufe sind konkret und bleiben es.

### Verwendung

```
/ux-review <repo> [--kette "<Station 1> > ... > <Station n>" | --alle] [--basis <url>] [--vor <sha>] [--no-issues] [--nur-melden] [--max-klicks <n>] [--max-seiten <n>] [-kd <name>] [-marker <name>[,<name>]] [--auswahl-bei <n>]
```

| Argument | Default | Bedeutung |
|---|---|---|
| `<repo>` | — | Ziel-Repo (Slug); Issues landen dort |
| `--kette` | — | Stationen in Reihenfolge; „erreicht" ist das Abbruchkriterium je Schleife |
| `--alle` | ohne `--kette` | Pfad-Modus: Stationen per Breitensuche erlaufen; liefert `Abdeckung` |
| `--max-seiten` | `60` | Pfad-Modus: danach `blind: Seitenbudget` |
| `--nur-melden` | aus | Ende beim Bericht (Step 7), kein Beheben |
| `--basis` | eigener Stack | lokal oder Staging, nie Access-Domain (G5) |
| `--vor` | `origin/main` | Positivkontrolle: Stand **vor** einem Fix |
| `--no-issues` | aus | Trockenlauf, Schema auf stdout |
| `--max-klicks` | `25` | Klicks je Station ohne neue Seite, dann `blind` |
| `-kd` | aus | Klickdummy-**Verzeichnis** (`spec.yaml` oder `screens-spec.yaml`, ADR-185) |
| `-marker` | aus | Eigennamen aus Station 1, in jeder Folgestation gesucht |
| `--auswahl-bei` | aus | erste Station nach einem Fan-out, die nur die gewaehlte Alternative zeigt |

### Step 0 — Kontext

`project-facts.md` lesen (G2); Testkonto-Zeiger (G3); Bekanntes: `gh issue list -R <owner>/<repo>
--label ux-review --state all` → „bekannt (#N)". Bei **gemeldetem** Befund zuerst G9. Ohne Zugang:
View per `RequestFactory` read-only rendern (zeigt Serverfehler, keine Browser-Laufzeitfehler) oder
kurzlebige Diagnose-Session nach G8.

### Step 1 — Eigene Umgebung

1. `bash <platform>/tools/repo-session.sh start <pfad-zum-zielrepo> --task ux-review-<slug>`; bei
   `--vor <sha>` dort `git checkout <sha>`.
2. `ss -tlnp | grep -E ':(8000|<dev-port>)\b'`; bei Treffer `docker ps --format '{{.Names}} {{.Ports}}'` —
   Name gehoert zum Zielrepo → Basis (im Bericht als „eigener Dev-Stack"), sonst G4-STOP.
3. Seed/Doctor: `grep -n 'seed\|doctor\|setup_' Makefile` bzw. `manage.py help | grep -i seed`; danach
   Cache leeren (aifw: Redis, TTL 600 s).
4. Synthetische Objekte `uxr-<datum>`, eines davon mit Bestand (G6).

### Step 2 — Klick-only, ggf. Pfad-Modus

`ToolSearch select:browser_navigate,browser_snapshot,browser_click,browser_fill_form,browser_console_messages,browser_network_requests,browser_take_screenshot`.
Login per `browser_fill_form`; ab dann jeder Weg ein Klick (G10). Pfad-Modus (`--alle`): Warteschlange
= klickbare Elemente der Startseite; Breitensuche; neue Seite (neuer Pfad ohne Query, neuer Hauptinhalt
bei HTMX) = Station; Logout, Loeschen, externe Links notieren, nicht klicken.

```bash
python3 <platform>/tools/ux_pfad.py --basis <url> --login <pfad> --max-seiten <n> --out /tmp/pfad.json
```

Abdeckung = besuchte Stationen / seitenrendernde Routen aus Step 3b (POST-/JSON-Routen nicht im Nenner
— gemessen 2026-09-02: `48 / 204` las sich sonst wie eine Luecke, die keine war).

### Step 3 — Je Station: Snapshot, Konsole, Netzwerk, Zustand

1. `browser_snapshot` (Accessibility-Tree).
2. `browser_console_messages` + `browser_network_requests` → jede 4xx/5xx **mit Body** (G12); HTMX-4xx
   ohne DOM-Aenderung = `stiller-fehler`.
3. `browser_take_screenshot` nur unter G6.
4. Zustand `befund` (Klasse, Beleg, Repro) · `ok` (mit Datenlage) · `blind` (mit Grund).

### Step 3.5 — Inhalt lesen (I1–I7)

| # | Kriterium | Referenz | Klasse | Severity |
|---|---|---|---|---|
| I1 | Zweck am Titel/`h1` erkennbar, nicht generisch | ADR-251 | `zweck-unklar` | optimierung |
| I2 | Naechster Schritt als Klick vorhanden | ADR-251; KONZ-051 E1 | `sackgasse` | fehler |
| I3 | Leerzustand nennt eine Handlung | ADR-049 | `leerzustand-ohne-handlung` | optimierung |
| I4 | Fehler sichtbar **und** mit Handlung; Body = Anzeige | ADR-048 §Fehleranzeige | `stiller-fehler` · `fehler-unverstaendlich` | fehler |
| I5 | HTMX-Triade `hx-target` + `hx-swap` + `hx-indicator` | ADR-048 | `htmx-triade-fehlt` | optimierung |
| I6 | Pflichtfelder markiert, Fehler am Feld, Eingaben erhalten | ADR-040 | `formular-verliert-eingabe` | fehler |
| I7 | Anzeige widerspricht nicht den Daten | Klasse `daten-invariante` | `daten-invariante` | fehler |

Seitentext bis zum Ende lesen; je Zeile Urteil + Zitat als Beleg; I7 braucht Bestand (G15).

### Step 3b — Gegenrichtung: Routen ohne Aufrufer

```bash
# Feste Zeichenketten (-F), nicht gequotet: `redirect("app:name")` traegt den Namensraum davor.
for name in $(grep -rhoP 'name="\K[a-z_]+' "$WT"/apps/*/urls*.py | sort -u); do
  treffer=$(grep -rnF "$name" --include=*.py --include=*.html --include=*.js "$WT" \
            | grep -vE 'urls\.py|(^|/)tests?/|\.pyc' | wc -l)
  [ "$treffer" -eq 0 ] && echo "ohne Aufrufer: $name"
done
```

Zwei Zaehlungen: **(a)** `{% url %}` + `reverse`/`redirect` als Aufrufer → „ist der Code tot?"; **(b)** nur
`{% url %}` in Templates/JS → „kommt ein Mensch per Klick hin?". Fuer `nicht-begehbar` gilt (b). Beide
Kontrollen nach G14. Ein Knopf im Template ist noch nicht sichtbar — `{% if %}` gegen seine Phase pruefen.

### Step 4 / 5 — Absenz-Gegenprobe, erfolgsaussehende Ausgaben

`grep -rn '<feldname|url-name>' <wt>/templates <wt>/apps` vor jedem „fehlt" (G13). Generierter oder
extrahierter Inhalt gegen die Quelle: Ersatzzeichen, Prompt-Fragmente, Rohbytes, HTML in Datei (G16).

### Step 5b — Falsifikator

```bash
python3 <platform>/tools/ux_falsifikator.py --datei /tmp/befund.json [--echtdaten]
# {"spruch": "bestaetigt|widerlegt|unklar|uebersprungen", "begruendung": "…", "modell": "…",
#  "laeufe": 3, "einig": true, "sprueche": [...]}
```

Eingabe-Typen: `klasse`, `severity` (`fehler|optimierung`), `station`, `symptom`, `antwortkoerper`,
`gegenprobe`, `referenz` — alle String; **`bekannt` ist Boolean** (`true|false`, nie `"nein"`: ein
String ist truthy, das Werkzeug castet still und Regel 4 wertet einen echten Befund als `widerlegt`
ab — Dogfood 2026-09-02, platform#2616). Schluessel-Zeiger `~/.secrets/groq_api_key`. Regeln G19–G21.

### Step 5c — Gegenchecks `-kd` / `-marker` (optional)

```bash
python3 <platform>/tools/ux_gegencheck.py kd --spec <zielrepo>/klickdummy/<name>/ \
  --stationen /tmp/stationen.json --kette-deckt "Phase 1,Phase 2"
python3 <platform>/tools/ux_gegencheck.py marker --stationen /tmp/stationen.json \
  --marker "<Name 1>,<Name 2>" --auswahl-bei 4
```

`/tmp/stationen.json`: `[{"id": …, "titel": …, "text": "<sichtbarer Seitentext>"}, …]`. `weg-fehlt`
(Screen `routing_mode: live` nie erreicht) = fehler, `spec-luecke` = optimierung (R5). `marker-abgewaehlt`
vor `--auswahl-bei` ist ein Hinweis, `marker-riss` danach ein Befund. Beide laufen durch 5b und 6.

### Step 6 — Issue je Befund

`gh issue create -R <owner>/<repo> --label ux-review` mit:

```
## Befund — <klasse> · <fehler|optimierung>
Kette: <kette> · Station: <n> <name> · Stand: <sha> · Lauf: <datum>
**Symptom:** <ein Satz>
**Repro:** 1. … 2. … (Klickpfad; URLs nur, wenn sie der Befund sind)
**Antwortkoerper / Konsole:** <Zitat>
**Screenshot:** <nur unter G6>
**Gegenprobe (bei Absenz Pflicht):** <Zahl zuerst> `grep -rn …` → <Treffer|leer>
**Klassen-Gate-Vorschlag (Pflicht):** <Test ueber ALLE Routen/Templates/Aufrufe — Katalog>
**Referenz (bei optimierung Pflicht):** ADR-048/049/040 §… oder Nielsen Nr. …
**Falsifikator (Pflicht):** <spruch> · <modell> · <ein Satz> · <bei einig: false: „uneinig: …">
```

### Step 7 — Sammel-Issue = Bericht

`[ux-review] <repo> · <kette> · <datum>` nach Output-Format. Owner traegt `fehlbefund` als Label nach →
Kill-Gate K2.

### Step 8 — Beheben (ohne `--nur-melden`)

Je `fehler`, in Berichtsreihenfolge: Ursache (G26) → Branch `ux-review/<datum>/<klasse>-<station-slug>` →
Fix + Gate-Test (G27) → Nachlauf (G28) → PR `fix(<app>): <klasse> an <station> (ux-review <datum>)` →
Merge (G29). `optimierung` nur bei benannter Referenz und kleinem Diff (ein Template/eine View), sonst
`offen`. Mit `--no-issues` gibt es kein Issue zum Schliessen — der PR verlinkt Bericht und Tracking-Issue.

## Klassen-Katalog (Gate-Vorlagen)

| Klasse | Symptom | Klassen-Gate (Vorlage) · Realfall |
|---|---|---|
| `nicht-begehbar` | Station nur per getippter URL | jede seitenrendernde Route gegen `{% url %}` aller Templates, Ausnahmen mit Grund · ausschreibungs-hub 2026-08-25, 14 Routen, `tests/test_erreichbarkeit_screens.py` |
| `stiller-fehler` | Klick „tut nichts", 4xx im Netzwerk | globaler `htmx:responseError`-Handler im Basis-Template · ausschreibungs-hub 2026-08-24 |
| `csrf-403` | HTMX-POST → 403, Body nennt CSRF | `hx-headers` mit Token am `body` |
| `markup-leck` | Template-Syntax als sichtbarer Text | Test ueber alle Templates auf mehrzeilige `{# #}` |
| `fallback-als-erfolg` | plausibler Text statt Fehler | Aufrufer wertet das Fehlerfeld aus; Nicht-Extrahiertes wird nicht gespeichert |
| `eine-meldung-drei-ursachen` | derselbe Fehlersatz fuer verschiedene Faelle | Meldung traegt die Ursache aus dem Audit-Trail |
| `escape-familie` | Sonderzeichen brechen Seite/JS | Gate ueber alle `{{ … }}` in `<script>`/`on*` · writing-hub#761 |
| `built-but-never-called` | Funktion ohne Weg in der Oberflaeche | jede View gegen `{% url %}`/`action=` aller Templates · writing-hub 2026-08-26, fuenf Faelle |
| `sichtbar-nur-unter-falscher-bedingung` | Knopf im `{% if %}` der falschen Phase | Seite ohne die Bedingung rendern, Sichtbarkeit pruefen · writing-hub#775 |
| `gemockt-und-deshalb-blind` | Tests gruen, erster Klick bricht | Test fuehrt die gemockte Schicht echt aus · writing-hub#774 |
| `daten-invariante` | Anzeige widerspricht der Sache | Invarianten-Melder ueber den Bestand, SKIP ist kein PASS |
| `nur-mit-daten-sichtbar` | frisch tadellos, mit Bestand tot | Seite **mit Bestand** rendern, jeden `application/json`-Block parsen · writing-hub#820 (3 Prod-Projekte tot, 22 UX-Tests gruen) |
| `link-auf-none` | `href="None"` → 404 | Rendering-Test je Werkart/Konfiguration + Gate `href="{{ … }}"` nur in `{% if <variable> %}` · writing-hub#949/#950 (2026-09-02) |
| `sackgasse` | kein Klick zum naechsten Schritt | Vorgaengerstation traegt `{% url %}`/`hx-get` auf jede Folgestation · ohne Realfall (2026-09-01, I2) |
| `leerzustand-ohne-handlung` | leere Liste ohne Handlungs-Link | jede Listen-View mit leerem Queryset rendern · ohne Realfall (2026-09-01, I3) |
| `fehler-unverstaendlich` | Fehler ohne Ursache/Handlung | Test ueber alle `messages.error(`/`add_error(`: Verb oder Ursache, generische Saetze als Negativmuster · ohne Realfall (2026-09-01, I4) |

Klassen ohne Realfall-Marker tragen ihr Aufnahmedatum; Marker folgt mit dem ersten belegten Fall (K6, 2026-09-01).

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
  [Pfad-Modus: Abdeckung: besucht n / Routen m]

Getippte URLs (K4): <n> — <liste>
Zaehler: befund <b> · ok <o> · blind <x> · bekannt <k>
Falsifikator (E16 — neben der Rohzahl, nicht statt ihrer):
  bestaetigt <a> · widerlegt <w> · unklar <u> · uebersprungen <s> · uneinig <n>   Modell: <modell>

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

## Anti-Patterns

- ❌ URL tippen und weitergehen, ohne sie als Befund zu notieren (G10) — 14 Routen zwei Monate versteckt.
- ❌ „fehlt" aus leerem DOM ohne `grep` (G13); Diagnose aus dem Statuscode (G12).
- ❌ Geteilte `.env`, Haupt-Tree, fremder Port, Access-Domain als Basis (G4/G5); Screenshot mit
  Mandanten-/Personendaten (G6).
- ❌ `blind` als `ok`; `ok` ohne Datenlage; unbesuchte Seite im Pfad-Modus als `ok` (G11/G6).
- ❌ Code lesen, bevor die gemeldete Seite im Browser stand; gemeldeten Befund an einem frischen Objekt
  nachstellen (G9) — sieben widerlegte Hypothesen gegen einen Klick, 2026-08-28.
- ❌ `optimierung` ohne Referenz; Kriterium ausserhalb I1–I7 (G15); Check-Listen per `tail`/`head` (G16).
- ❌ Issue ohne Klassen-Gate-Vorschlag (G22) — dann ist der Agent ein Melder, K3 faellt.
- ❌ Befund wegen `widerlegt` nicht anlegen; `uebersprungen` als Bestaetigung; Bild an den Gegenpart (G19–G21).
- ❌ Fix vor Bericht; Fix ohne belegte Ursache als `behoben`; Fix-PR ohne Gate-Test; Nachlauf auf frischem
  Objekt (G25–G28).

## Abschluss-Checkliste

- ☐ A1 K4-Zeile, im Pfad-Modus Abdeckungszeile (G10, G11)
- ☐ A2 Konsole + Netzwerk je Station mit Antwortkoerper (G12)
- ☐ A3 I1–I7 je Station mit Urteil und Zitat, Referenz je `optimierung` (G15)
- ☐ A4 Zaehlungen (a)/(b) mit Positiv- und Negativkontrolle, je Treffer eine Antwort (G14)
- ☐ A5 je Befund ein Issue mit allen Pflichtfeldern, Bekanntes markiert (G22, G24)
- ☐ A6 Sammel-Issue nach Output-Format, Falsifikator neben Rohzahl, `Nicht verifiziert` (G23)
- ☐ A7 ohne `--nur-melden`: Fix-PR je `fehler` mit Ursache/Gate-Test/Nachlauf; Rohbericht byte-gleich (G25–G28)
- ☐ G1 vor dem ersten Klick aufgerufen · G2 project-facts gelesen · G3 Anmeldeweg (1/2/3) benannt, Wert nie im Bericht
- ☐ G4 eigener Worktree/.env, Dev-Port dem Zielrepo zugeordnet · G5 keine Access-Domain, `127.0.0.1`
- ☐ G6 synthetische Daten, eines mit Bestand, Datenlage je Station · G7 Seed/Doctor + Cache
- ☐ G8 kein Schreib auf Zielsystem ohne Freigabe · G9 Browser vor Code am gemeldeten Objekt
- ☐ G13 jede Absenz mit Gegenprobe, Zahl zuerst · G16 Ausgaben gegen Quelle, keine `tail`-Filter
- ☐ G17 `--kette-deckt`/`--auswahl-bei` gesetzt, Kontrollmarker sauber · G18 nur `:visible`
- ☐ G19–G21 Falsifikator je Befund, `laeufe: 3`, `einig` im Bericht, kein Bild/Echtdaten
- ☐ G29 SA-5-Merge oder `Prod-Merge: Freigabe noetig` · G30 Ausgelassenes getrackt · G31 Dogfood bei Umbau

## Dogfood-Tests (Review-Gate per `claude-skills.md`)

| # | Lauf | Erwartung | Stand |
|---|---|---|---|
| 1 | writing-hub, Kette Login > Projekt anlegen > Idee > Buch > Export, `--vor <sha vor #761> --no-issues` | #758/#759/#762 als `befund`; „Stil" → `project_form.html:171` = Rendering-Bedingung | bestanden 2026-08-25 (writing-hub#767) |
| 2 | ausschreibungs-hub, Kette Login > Recherche > Analyse > Angebot > Freigabe > Abgabe, `--vor <sha> --no-issues` | Station 4+5 `nicht-begehbar`, getippte URLs = 2 | bestanden 2026-08-30 (K1 8/9, platform#2474) |
| 3 | `--basis http://127.0.0.1:65530` (nichts lauscht; nicht Port 9, Chromium „unsafe port") | Station 1 `blind: Dienst antwortet nicht`, `ok 0`, kein Issue | bestanden 2026-08-25 |
| 4 | writing-hub, Login > Projekt > Schreiben, `--vor <sha vor #820>` | frisch: `ok` mit Datenlage `frisch (leer)`; mit Bestand: `nur-mit-daten-sichtbar`, `SyntaxError … JSON.parse` | Anlass 2026-08-28 (durchgefallen), seither Pflicht |
| 5 | `tools/ux_falsifikator.py` mit drei Befunden | Fehlbefund `widerlegt`, echter Defekt `bestaetigt`, Geschmack `widerlegt`; je `laeufe: 3` + `einig` | bestanden 2026-08-30 |
| 6 | writing-hub `--alle --no-issues --nur-melden` | `Abdeckung n < m`; (b)-Routen `nicht-begehbar`; `--max-seiten 5` → `blind: Seitenbudget`; mind. eine Station ohne Kette | bestanden 2026-09-02 (`48 / 204`, writing-hub#949) |
| 7 | Kette bis zu einem **offenen** `fehler` | Bericht vor Branch; PR mit `Datei:Zeile`, Gate rot/gruen gemessen, `Closes`; Nachlauf `ok`; `behoben 1` | bestanden 2026-09-02 (writing-hub#950) |
| 8 | derselbe Lauf mit und ohne `--nur-melden`, `diff` bis `Nicht verifiziert` | 0 Zeilen; nur `b` traegt `Behoben` | bestanden 2026-09-02 (writing-hub#948) |

## Bezug

- `platform:KONZ-platform-051` — Konzept, Ledger E1–E24, Kill-Gate K1–K9 (Frist 2026-09-30); `platform#2326`
  Klassen-Tests flottenweit; `platform#2466` Falsifikator; K6-Werkzeug `tools/blaupause_check.py`
- `platform:ADR-251` (UX-Gate am Klickdummy), `ADR-048/049/040` (Referenz fuer `optimierung`);
  `policies/llm-routing.md` (Rung T1a); `policies/error-handling.md` (Ursache belegen)
- Memory `project_ux_review_agent_program`; Retro `session-retro-2026-08-25-writing-hub-fdd368` (#2325)

## Changelog

- 2026-09-02 (4, Revision nach Dogfood v2 an platform#2616): **G4** STOP nur bei fremdem Container/Prozess
  auf dem Dev-Port (Zuordnung per `docker ps`-Name), eigener Dev-Stack zulaessig; **G3** drei Anmeldewege
  (Zeiger, passwortloser Repo-Weg wie `make login`, `createsuperuser` nur im eigenen Stack) — `blind` erst
  danach; **G10** nimmt den Anmeldeweg aus K4 aus; Step 5b nennt die Eingabe-Typen (`bekannt` Boolean).
- 2026-09-02 (3): **v2 zielorientiert, platform#2606 Stufe 3** — Ziel, Akzeptanzkriterien A1–A7, Harte
  Gates G1–G31, Referenzpfad (nicht bindend), Abschluss-Checkliste je A/G; alle bisherigen PFLICHT/nie-Gates
  abgebildet (Zuordnung im PR); Dogfood-Tests als Tabelle, Changelog verdichtet (Volltext: git-Historie).
- 2026-09-02 (2): Tests 6–8 bestanden (writing-hub#948/#949/#950); Werkzeug `tools/ux_pfad.py`, Klasse
  `link-auf-none`, Nenner nur Seiten, Anker nur `:visible`. platform#2596 geschlossen.
- 2026-09-01: Stufe 1c — Pfad-Modus `--alle` (E22), I1–I7 (E23), Step 8 Beheben (E24), `--nur-melden`;
  Rohbericht byte-gleich (E16). K6-Messung: Katalog-Zeilen tragen Realfall-Marker.
- 2026-08-30: Falsifikator (E13–E17, K9, platform#2466), Mehrheit aus drei Laeufen (E20, platform#2489);
  K1 auf 8/9 (E19, platform#2474); zwei Zaehlungen in Step 3b.
- 2026-08-28: Browser vor Code (Owner-Weisung), Konsole als Kill-Kriterium, Datenlage Pflicht, Klasse
  `nur-mit-daten-sichtbar` (writing-hub#820).
- 2026-08-25: Initial — Stufe 1 aus KONZ-platform-051; Pilot writing-hub#767; Seed/Doctor, Cache, Testkonto.
