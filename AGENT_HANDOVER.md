# Agent Handover — Platform Infra Context

**Pflicht-Lektüre beim Session-Start jedes Coding-Agents.**
Enthält MCP-Tool-Mappings, Infra-Zugänge, Deploy-Targets und Scripting-Referenz.

<!-- Konvention: dieser Abschnitt hält NUR den "## ⚡ Aktueller Stand" + max. EINEN
     "## ⚡ Vorheriger Stand" (den jeweils jüngsten). Alles Ältere wandert nach
     AGENT_HANDOVER_ARCHIVE.md (siehe Verweis unten) — nicht hier anhäufen. -->

**Archiv älterer Session-Stände:** [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md)
(Blöcke älter als der aktuelle + 1 vorherige Stand).

## Zeitanker — Pflicht je Stand-Block

Jeder `## ⚡ Aktueller Stand`-Block trägt **als erste Zeile** einen Zeitanker: die
Werte, gegen die eine frische Instanz in **einem** Kommando prüfen kann, ob dieser
Text noch den Stand beschreibt oder hinterherhinkt.

```
**Zeitanker:** HEAD `<sha7>` · `rev-list --count` <n> · geschrieben <YYYY-MM-DD>
```

Prüfen (ein Kommando, read-only):

```bash
git fetch -q origin && echo "ist: $(git rev-parse --short origin/main) / $(git rev-list --count origin/main)"
```

**Weicht der Ist-Wert ab, ist der Block veraltet — nicht falsch, aber überholt.** Das ist
die einzige Aussage, die der Anker trägt; er ersetzt kein Lesen. Fehlt ein Wert, wird
`nicht erhoben` eingetragen — **nie** ein geschätzter.

Warum: Ohne Anker war „hinkt der Handover nach?" nur durch Lesen beantwortbar, und das
unterblieb — Realfall 2026-07-15, drei konkurrierende Handover-PRs nebeneinander
(`session-retro-2026-07-15-platform-c494a2`). Übernommen aus dem Fremdsystem SB-Neu, wo
derselbe Anker eine Sechs-Commit-Drift in einer Sekunde sichtbar machte.

## ⚡ Aktueller Stand (2026-08-07 — die Arbeitsliste ist nicht mehr flüchtig: todo.iil.pet)

**Zeitanker:** HEAD `6266008d` · `rev-list --count` 3001 · geschrieben 2026-08-07

**Zielzustand dieser Session:** erreicht mit einem offenen Rand. Der Auftrag entstand
mitten im Lauf (`/mailcheck` → Owner-Frage „wäre ein persistentes todo.iil.pet nicht der
bessere Weg?") und wurde in vier Stufen A–D akzeptiert. A–C sind verifiziert, D ist
serverseitig verifiziert, aber vom Owner-Browser aus **nicht erreichbar** — siehe offener
Punkt unten. **SA-4:** nicht ratifiziert (Stand `VORGESCHLAGEN`, `autonomy-gates.md`
Z. 178) — kein Zähler zu führen.

- **`todo.iil.pet` steht und ist geschützt** ([#1822](https://github.com/achimdehnert/platform/pull/1822) gemergt, [#1823](https://github.com/achimdehnert/platform/pull/1823) offen/grün). `tools/todo_board/todo_board.py` rendert das Vorgangs-Ledger als eine Seite: drei Abschnitte (dein Zug / ich kann sofort / wartet auf andere), Fristen aufsteigend zuerst, Ampel rot ab 3 Tagen Restlaufzeit. **Bewusst ein eigener Dienst** und nicht der Mail-Link-Dienst auf 8787 — der rendert Mail*körper* live aus dem Postfach und gehört nicht hinter dieselbe Tür wie eine Aufgabenliste. Dieser hier kennt nur das Ledger, spricht kein IMAP, hat genau `/` und `/healthz`, alles andere 404, und verweigert jede Bindung außerhalb Loopback ohne `--oeffentlich-hinter-auth`. Verdrahtung: `todo-board.service` (user, Port 8789) · Ingress im bestehenden `mail-links`-Tunnel · Access-App mit derselben Owner-Regel wie `mail.iil.pet` (`admin@wir-digital.de`, `achim.dehnert@iil.gmbh`) · Cron `30 6 * * 1-5` ruft `/mailcheck` headless.
- **`todo.iil.pet` ist erreichbar — bestätigt vom Owner um 10:07.** Der Weg war rund 30 Minuten lang nur bei ihm gestört (Chrome, Edge und Firefox meldeten `DNS_PROBE_FINISHED_NXDOMAIN`), während serverseitig alles stimmte: beide autoritativen Cloudflare-NS **und** vier öffentliche Resolver antworteten durchgehend, TLS `CN=todo.iil.pet` gültig, Abruf ohne Session `302` auf das Access-Login. Es löste sich durch Warten auf — also ein **negativ zwischengespeicherter Eintrag beim Resolver des Owners**. Der Zwischenbefund „das kann der Cache aus dem Fehlfenster nicht sein", gestützt auf die Record-Zeitstempel (falscher Eintrag 09:34:02, richtiger 09:34:47 — Fenster **45 Sekunden**, vor der Meldung an den Owner), war in der Schlussfolgerung falsch: aus einem kurzen Fenster folgt nicht, dass kein Negativ-Eintrag entstand. Die daraufhin aufgestellte Ersatzthese (Filter für neu beobachtete Domains) war unnötig. **Lehre für die nächste neue Subdomain:** ein frischer Hostname kann beim Owner bis zu 30 Minuten (negative TTL der Zone `iil.pet`: 1800 s) tot aussehen, obwohl er global längst auflöst — vor der Fehlersuche einmal `nslookup <host> 1.1.1.1` gegen den lokalen Resolver stellen, das trennt die Ebenen in einem Schritt.
- **`cloudflared tunnel route dns` legt den Eintrag in der falschen Zone an.** `cloudflared tunnel route dns mail-links todo.iil.pet` erzeugte **`todo.iil.pet.iil.ai`** — das Werkzeug hängt die Standardzone des Zertifikats an, statt `iil.pet` als eigene Zone zu erkennen. Fehleintrag in `iil.ai` gelöscht, CNAME per API direkt in `iil.pet` gesetzt (proxied). **Für die nächste Subdomain unter `iil.pet`: nicht `tunnel route dns` benutzen, sondern den DNS-Record per API setzen** — und danach mit `dig @1.1.1.1` gegenprüfen, welcher Name wirklich entstanden ist. Nebenbefund: `cloudflare_api_token` darf DNS-Records **nicht** lesen (403), dafür braucht es `cloudflare_write_token`.
- **`organize_mail.py --create-folder` konnte nie einen Ordner mit Leerzeichen anlegen** ([#1821](https://github.com/achimdehnert/platform/pull/1821) gemergt). `cmd_create_folder()` reichte den Namen unquotiert an `imap.create()`/`imap.subscribe()` weiter; auf Exchange bricht das mit `BAD Command Argument Error` ab, **ohne** dass ein Ordner entsteht. Der passende Helfer `_mailbox_arg()` lag zwanzig Zeilen darüber und beschreibt in seinem eigenen Docstring exakt diesen Fehlermodus — er wurde nur von `SELECT` und `UID MOVE` benutzt. Verifiziert durch die drei tatsächlich angelegten Ordner, nicht durch einen Trockenlauf.
- **Mailcheck-Ertrag:** Zwei Entwürfe im HNU-Postfach, **nicht gesendet** — 23460 (Schönherr: Termin Mi 12.08. 11:00 bestätigt) und 23461 (Karatas: Proposal v3). Karatas hat alle drei Punkte der Vorrunde erledigt; die Effektstärke `d = 0.80` aus der Choung-Favorable-Subgruppe habe ich nachgerechnet, sie stimmt. Vier neue Punkte im Entwurf, der wichtigste: **N = 90 ist der Boden nach Ausschluss, nicht das Rekrutierungsziel** — bei 10–20 % Manipulation-Check-Ausfall bleiben ~75 übrig und die eben berechnete Power ist wieder weg. Nawaz-Entwurf 23459 war bereits gesendet (06.08. 10:10), Punkt geschlossen.
- **Drei harte Fristen stehen jetzt sichtbar im Ledger** (vorher Freitext in Notizen): Euramco AV-Prüfung **19.08.** (TOM, Subdienstleisterliste, DSMS-Audit-Nachweis, Prüfprotokolle der Subdienstleister) · DSGVO-Löschung Scheppach **22.08.**, Vollzugsmeldung fehlt seit 11 Tagen · HNU-Ausschreibung 00970 „KI Werkleiterassistent" **31.08.**, Bieterfragen bis 19.08. (Fristen per OCR aus dem gescannten Aufforderungsschreiben gezogen).
- **Ordner „Zur Löschung" in allen drei Konten**, 24 Mails einsortiert (HNU 14, Mittwald 9, IIL 1). Owner prüft und leert selbst. Verschieben löst kein Tracking aus: es ist eine reine Server-Operation ohne Body-Abruf, und weder `graph_mail` noch `organize_mail` beantworten `Disposition-Notification-To`.
- **Der Cron geht ab morgen unbeaufsichtigt in die Postfächer.** `30 6 * * 1-5` ruft `/mailcheck` headless. Er sendet nie — er **legt aber Entwürfe an**, wie heute die beiden oben. Wenn das zu weit geht, ist der Rückbau eine Zeile in der crontab. [#1823](https://github.com/achimdehnert/platform/pull/1823) schließt die Lücke, die der Cron erst aufmacht: die Seite baut bei jedem Abruf neu und sieht deshalb **immer** frisch aus, auch wenn der nächtliche Lauf seit Tagen scheitert — ab zwei Tagen ohne Erhebung sagt sie das jetzt selbst.
- **Zwei Memory-Dateien in der risk-hub-Lane hatten `name:` mit Bindestrichen statt passend zum Dateinamen** (`feedback_ci_last_log_line_lies`, `feedback_compose_interpolation_vs_env_file`) — vom Link-Guard gemeldet, korrigiert. Vorher geprüft, dass niemand auf die Bindestrich-Form verweist; `MEMORY.md` verlinkte bereits die Dateinamens-Form.
- **Eigener Fehler dieser Sitzung:** Ich habe `cloudflared tunnel route dns` benutzt, ohne danach zu prüfen, welchen Namen es tatsächlich angelegt hat — der Fehler fiel nur auf, weil das Werkzeug seine Ausgabe druckte. Hätte es geschwiegen, wäre `todo.iil.pet` einfach nie aufgelöst worden, und die Suche hätte am falschen Ende begonnen.

## ⚡ Vorheriger Stand (2026-08-05 — Werkzeuge statt Prosa; ein Anzeigetext sagte das Gegenteil des Sachverhalts)

**Zeitanker:** HEAD `bd1ffb5a` · `rev-list --count` 2919 · geschrieben 2026-08-05

- **🟢 ZUERST — die MEiKI-Anzeige ist entscheidungsreif, die Sachfrage ist geklärt.** Der Entwurf liegt im hnu-Postfach (`Entwürfe`, an `schmidt@actago.de`, 9 Anlagen, **nicht gesendet** — der Versand ist eine Owner-Entscheidung). Der Auftragsverarbeitungsvertrag LRA–OCOS **besteht**: zugesichert von OCOS selbst (C. Zeiner, telefonische Rücksprache 2026-08-03), Entscheidung des Projektleiters vom 2026-08-05, dieser Zusicherung zu folgen. Das ist die belastbarste verfügbare Quelle — Zeiner ist Vertragspartei. **Provenienz für den Fall einer Rückfrage der Aufsicht:** schriftlich übersandt hat OCOS am 2026-08-03 den eigenen AVV-Mustervertrag (`Vertraulich_AVV_Ocos.docx`); die Bestätigung des *geschlossenen* Vertrags mit dem Landratsamt erfolgte mündlich, der Nachweis in Papierform liegt in der Vertragsakte des Landratsamts. Die frühere Einstufung als Blocker (Stand vom Vormittag) ist damit zurückgezogen. Die Nebenspur ist ebenfalls geklärt (Owner, 2026-08-05): `00891_Beauftragung_Ocos Solutions GmbH.pdf` über `beschaffung@hnu.de` ist ein **Beratungsvertrag, keine Programmierung** — die Hochschule lässt sich beraten, es fließen keine Sozialdaten an OCOS. Damit **keine** zweite Auftragsverarbeitung und kein zusätzlicher Anzeigetatbestand. Die Konstellation ist sauber getrennt: LRA→OCOS Auftragsverarbeitung (Dokumentenstrom, AV besteht, angezeigt) · HNU→OCOS Beratung (ohne Datenverarbeitung) · HNU→LRA Fristenmanagement-Betrieb ab Pilot 2 (§ 80 Abs. 1 Satz 1 **und** Satz 2). Die Grenze der Beratungs-Einordnung liegt dort, wo OCOS im Zuge der Beratung Zugriff auf echte Sozialdaten bekäme — konkret relevant, weil Zeiner die Umgebungsvariablen des Produktivpfads „nach Zustimmung durch Herrn Kramer" angeboten hat.
- **[meiki-hub#138](https://github.com/meiki-lra/meiki-hub/pull/138) ist merge-fertig und wartet auf deine Entscheidung** — CI grün, kein Review-Ruleset, kein Deploy-Pfad berührt. Bewusst **nicht** autonom gemergt: Owner-Weisung 2026-08-05 — in Abläufen mit Menschen schlage ich vor, warne und weise hin; entschieden wird vom Owner. Die Standing-Authorization SA-1 beschreibt, was technisch zulässig ist, nicht was inhaltlich meine Entscheidung wäre.
- **Vier von neun Anlagen der DSB-Anfrage trugen einen falschen Sachverhalt** — korrigiert in [meiki-hub#138](https://github.com/meiki-lra/meiki-hub/pull/138) (offen, CLEAN). Sie führten die Dokumenten-Steuerung als „keine Sozialdaten · kein externer Auftragsverarbeiter · keine Anzeige" und schrieben, es komme in keiner Stufe ein lernendes Verfahren zum Einsatz. Kramer schrieb derselben Empfängerin 17 Minuten nach dem Versand der Vorfassung, die Post werde „KI-gestützt sortiert und verschlagwortet", dabei würden personenbezogene Daten verarbeitet. Betroffen war auch `anzeigetext-80-abs1-satz1-lra.pdf` — der Text an die Aufsicht selbst. `anzeigetext-80-abs1-satz2-hnu.pdf` blieb bewusst unverändert (sein „deterministisch" gilt dem Fristenmanagement und stimmt). **Zwei Rechtsfragen nebenbei geklärt:** Behörde zu sein schließt die Auftragsverarbeitung nicht aus — § 80 Abs. 1 Satz 2 SGB X **verdoppelt** die Anzeigepflicht (LRA an seine Aufsicht, HNU an ihre). Und Kramers „Anzeige nach § 80 Abs. 2" ist die falsche Fundstelle; Abs. 2 regelt den Verarbeitungsort.
- **KONZ-038 D6 abgeschlossen** ([#1766](https://github.com/achimdehnert/platform/pull/1766) gemergt): Das Slug-Wörterbuch der eingefrorenen K1-Baseline hatte **keinen maschinellen Konsumenten** — „unmappbar = nicht bewertbar" und „Instrumentenwechsel ⇒ Neuberechnung" standen als Prosa im YAML-Kopf, der Ritual-Lauf verwies auf den „manuellen Teil". `retro_kpis.py --k1` rechnet den Ausgang jetzt und ist in `regel-ritual.yml` verdrahtet. Baseline nach dem eigenen Instrumentenwechsel neu berechnet (identisch: n=20, 10/7/3, Summen-Rate 1.000), Pin nachgezogen. Suite 23 → 36.
- **Megatest: die „5 nicht scannbaren Repos" lagen nie am Token** ([#1768](https://github.com/achimdehnert/platform/pull/1768) gemergt). `megatest.yml` klonte alle 52 als `achimdehnert/$repo`; 11 liegen unter iilgmbh/meiki-lra/ttz-lif, 6 rettete GitHubs Redirect, **5 antworten mit 404** — darunter `iil-voice-agent` mit **Budget 39**, dem größten Posten von [#1682](https://github.com/achimdehnert/platform/issues/1682), nie im CI gescannt. Der Owner-Resolver lag fertig in der Registry und wurde nicht aufgerufen. Der Budget-Abbau selbst bleibt offen (App-Repos).
- **[#1549](https://github.com/achimdehnert/platform/issues/1549) geschlossen, mit ehrlichem Rand:** Prod 0 unhealthy von 43, `devhub_beat` bei 45 % statt 89,5 %. Aber `dms_hub_*` und `coach_hub_*` laufen unter dem Freeze gar nicht — ihre Null kommt aus „läuft nicht", nicht aus „läuft gesund". Steht so im Issue.
- **Neuer Skill mit eigenem Prüfer** ([#1770](https://github.com/achimdehnert/platform/pull/1770), offen, CI grün): `/arbeit-pruefen` + `tools/dokument_formalpruefung.py` (13 Prüfungen, 28 Tests) für die Formalprüfung eingereichter Arbeiten. Das Werkzeug widerlegte sofort die eigene Handprüfung (32 statt 17 betroffene Abbildungen, 26 statt 24 Belege, zwei zusätzliche Befunde). Das Quellen-Gate ist gemessen, nicht vorsichtig: von 9 belegbar falsch zugeschriebenen Literatureinträgen tragen 3 keinen Autor-Marker, 2 überhaupt keinen.
- **Zwei offene Nebenbefunde:** [#1769](https://github.com/achimdehnert/platform/issues/1769) — `read_mail.py --list` liefert **0 von 221 geprüften** Nachrichten in jedem Ordner, `treffer: []`, `fehler: []`, Exit 0; dasselbe Werkzeug trägt den Schalter `--abwesenheitsbeweis`. [#1767](https://github.com/achimdehnert/platform/issues/1767) — fsn1 3 Container unhealthy aus **drei** Ursachen (Healthcheck probt HTTP auf einem Celery-Worker · `docker exec` scheitert seit 5 Wochen · `ib_gateway` ruft ein nicht installiertes `nc`). Der Neustart wurde vom Berechtigungs-Klassifikator geblockt, das Kommando steht im Issue. Vorfrage vor dem Neustart: Der Stack ist ein Juni-Worktree-Rest mit seit 3 Wochen totem Web-Container — `down` wäre womöglich richtiger als `up`.
- **Gesendet hat der Owner selbst (verifiziert am gesendeten Text):** Rückmeldung an R. Frost zur Masterarbeit (13:24) · Rückfrage an C. Zeiner zu Verschlagwortungs-Verfahren, Azure-Verarbeitungsorten und geltendem AVV (12:49). Zeiners Antwort ist die Voraussetzung für M-6/M-7 in der Anzeigepflicht-Matrix.
- **Eigene Fehler dieser Sitzung:** `git checkout` auf eine Datei mit ungetrackter Arbeit — das komplette K1-Modul war weg und musste neu geschrieben werden, obwohl genau diese Lehre im Memory steht (im selben Zug ein zweites Mal: ein Splice traf die Erwähnung im Konventions-Kommentar statt die Überschrift) · zwei falsche Zahlen in einer Rückmeldung an einen Studenten · eine Marker-Quote ohne exaktes Auszählen behauptet, deren Korrektur zugleich eine Detektionslücke freilegte (`[a-zäöüß]` kennt „Léo" nicht) · dreimal eine Null gemeldet, ohne die Positivprobe zu fahren — dreimal hat der Evidenz-Gate es abgefangen.


**Nachtrag (2026-08-05 nachmittags, nach dem formalen Session-Ende) — Mail-Auswertung zweimal widerlegt, Verlaufsansicht gebaut:**

- **Vier Mails sind raus, vom Owner selbst gesendet** (am gesendeten Text verifiziert): Rückfrage an C. Zeiner (12:49) · Rückmeldung an R. Frost zur Masterarbeit (13:24) · **MEiKI-Anzeige an die externe DSB S. Schmidt (13:35)** · Antwort an M. Raslan (13:40) · Antwort an S. Lohwieser mit zwei Anlagen (14:12).
- **⚠️ OFFEN, konkret: Die MEiKI-Anzeige ging mit NULL Anlagen raus.** Der Text sagt an zwei Stellen „liegt bei" — Frau Schmidt hat den Sachstand, aber weder die beiden Anzeigetexte noch Anzeigepflicht-Matrix, AVV-/TOM-Entwürfe oder Erhebungsbogen. Alle neun PDFs liegen im meiki-hub-Worktree bereit. **Eine kurze Nachfass-Mail im selben Strang ist der nächste Schritt.** Inhaltlich war die gesendete Fassung korrekt (Tabelle mit `ja - OCOS`, Fristenmanagement Stufe 1 `synthetisch`, Pilot 2 `ja - HNU`); der Hinweis zu § 80 Abs. 2 fehlt, weil der Owner den Infrastruktur-Passus vor dem Senden entfernt hat — das nimmt zugleich den Termindruck von Zeiners Auskunft (Telefonat vereinbart für **Freitag 07.08.**).
- **Zwei Mail-Auswertungen gebaut und beide widerlegt — der lehrreichste Teil des Tages.** Erste Fassung verglich INBOX gegen „Gesendete Objekte": Sie meldete 29 offene Stränge, übersah aber, dass Antworten in Betreuungs- und Projektordnern liegen (Realfall Nawaz: 7 von 9 Nachrichten in `Betreuungen/Nawaz-Muhammad`, darunter eine eigene Antwort). Zweite Fassung las alle Ordner über den `thread_key` — und lief in zwei **gegenläufige** Fehler: **Kollision** (33 Nachrichten von zehn Personen über 1,5 Jahre unter EINEM Schlüssel, weil alle „HNU Kontaktformular" heißen — ohne `References` fällt die Gruppierung auf den Betreff zurück) und **Fragmentierung** (dieselbe Unterhaltung in mehreren Schlüsseln; Abel und Ullah erschienen offen, obwohl beantwortet). Dritte Fassung gruppiert **nach Gesprächspartner** statt nach Strang und ist gegen beides robust.
- **Was die dritte Fassung fand und die ersten beiden nicht:** `maryhenrietta.ezeobi@student.hnu.de`, „Re: Research Idea" vom 08.06. — **58 Tage, nie beantwortet**. In Fassung 1 unsichtbar (falscher Ordnervergleich), in Fassung 2 unsichtbar (kollidierter Strang). Ebenfalls offen: M. Schönherr fragt seit 30.07. nach einem Präsentationstermin „in der nächsten Woche" (= diese Woche); an dem Termin hängen sein ausführliches Feedback und die Note. Seine Masterarbeits-Idee vom 22.06. hat keine Mail-Antwort — in dieser Korrespondenz läuft aber vieles telefonisch.
- **[dev-hub#249](https://github.com/achimdehnert/dev-hub/pull/249) — Verlaufsansicht.** `/mail-agent/verlauf/?id=<n>` zeigt den ganzen Faden, neueste zuerst, je Nachricht Von/An/Cc/Datum/Ordner/Betreff/Text/Anhänge. Anhänge über `/mail-agent/anhang/?id=<n>` **inline**, PDFs gehen im Browser auf. Der Anhang-Lesepfad liegt jetzt einmal in `services.anhang_bytes` statt je einmal im Kommando und im View; fehlender Rohtext gibt 404 mit Grund statt 200 mit null Bytes. 391 Tests grün, Rot-Beweis geführt.
- **Zwei neue Arbeitsregeln als Memory** (Owner-Weisungen): (1) **In Abläufen mit Menschen schlage ich vor, warne und weise hin — entschieden wird vom Owner.** Anlass: Ich hatte geprüft, dass meiki-hub#138 unter SA-1 fällt, und wollte mergen; der PR ändert einen Anzeigetext an eine Aufsichtsbehörde. SA-1 beschreibt, was technisch zulässig ist, nicht was inhaltlich meine Entscheidung wäre. (2) **Mail-Umfangsregler** `knapp | normal | ausführlich` (Default `normal`) plus die davon unabhängige Regel: Jeder Fakt muss beantworten, was gefragt wurde, oder anstoßen, was ich brauche — sonst raus, auch wenn er stimmt. Dazu: **keine harten Zeilenumbrüche in Mails**, nur Absätze.
- **Eigener Fehler mit Außenwirkung:** In der Lohwieser-Mail stand „In Günzburg ist es IKOL-WG" — abgeleitet aus einer Sammelzeile, tatsächlich ist es **OK.WOBIS**. Vor dem Versand korrigiert. Ein Gefälligkeitsdetail, nach dem niemand gefragt hatte; genau der Fall, den die neue Faktenregel adressiert.
- **AV LRA–OCOS ist geklärt** (Owner 2026-08-05): Zusicherung von OCOS selbst, Zeiner ist Vertragspartei. Die HNU-Beauftragung über eBANF ist ein **Beratungsvertrag ohne Datenverarbeitung** — keine zweite Auftragsverarbeitung. Konstellation: LRA→OCOS Auftragsverarbeitung (angezeigt) · HNU→OCOS Beratung · HNU→LRA Fristenmanagement ab Pilot 2 (Satz 1 **und** Satz 2). Grenze: Sobald OCOS im Zuge der Beratung Zugriff auf echte Sozialdaten bekäme, kippt die Einordnung — Zeiner hat die Produktiv-Umgebungsvariablen „nach Zustimmung durch Herrn Kramer" angeboten.

## ⚡ Älterer Stand (2026-08-02 — Mail-Index beantwortet Vorgangsketten aus der DB statt über IMAP)

**Zeitanker:** HEAD `eaffc4c8` · `rev-list --count` 2757 · geschrieben 2026-08-02

**Nachtrag (2. Session-Ende 2026-08-02, HEAD `d24fd16f` · count 2769):**
- **Retro 287b23** gemergt ([#1661](https://github.com/achimdehnert/platform/pull/1661)): 7 Survivors, alle Maßnahmen umgesetzt ([#1664](https://github.com/achimdehnert/platform/pull/1664) + Mode-Fix [#1660](https://github.com/achimdehnert/platform/pull/1660)); Aufrufpfad-Contract-Drill neu (drillt den ECHTEN settings-Pfad); #1186/#1190 als gebaut geschlossen; Welle-2-Rangliste auf [#705](https://github.com/achimdehnert/platform/issues/705) — **workaround-Slug bis 16.09. NICHT gaten (K1-Vergleichsgruppe!)**.
- **Orchestrator-Token rotiert** (Gate 1, Owner-Wort): neuer Key in `.env.prod` + Container per compose **--force-recreate** (nicht restart!) + `~/.secrets/orchestrator_mcp_api_key` + settings.json konsistent; Container-Env-Präfix verifiziert, Service healthy. Kernlehre als 🌀-Memory: `docker restart` lädt env_file NIE neu — die Juli-Rotation war deshalb 16 Tage wirkungslos.
- **⚠️ Rotation #2: Server-Hälfte FERTIG, Client-Hälfte OFFEN — Step 0 der NÄCHSTEN frischen Session:** `~/shared/finish_token_rotation2.sh` ausführen, **VOR jedem settings.json-Read** (der Datei-Watcher spiegelt jede settings.json-Änderung einer laufenden Session komplett ins Transkript — Token #3 wäre sofort wieder exponiert; deshalb NICHT in einer laufenden Session patchen). Bis dahin trägt settings.json **bewusst** den toten Token #2 — orchestrator-MCP ist sichtbar nicht verbindbar, das ist gewollt. Server-Hälfte (Owner „3 go", dokumentiert im [#1640-Kommentar](https://github.com/achimdehnert/platform/issues/1640)): Token #3 in `.env.prod` + compose --force-recreate; unabhängig nachverifiziert 19:10 UTC per SHA256-Präfix-Vergleich (nie Klartext): `~/.secrets/orchestrator_mcp_api_key` = Server-`.env.prod` = Container-Env, StartedAt 13:36:21Z; Token #2 serverseitig tot. **Korrektur eigener Fehldoku (#1693):** die Behauptung „kein Artefakt, Ausführende Session unbekannt" war falsch — das Artefakt existierte als #1640-Kommentar; außerdem hatte #1693 die ⚠️-Zeile fälschlich als komplett erledigt ersetzt und damit die Step-0-Anweisung von der Lesefläche entfernt. Altes Voll-Rotationsskript (`rotate_orchestrator_token.sh`) aus `~/shared/` entfernt — **`finish_token_rotation2.sh` liegt weiter dort und bleibt, bis Step 0 gelaufen ist.**
- Hygiene-Kandidat (Owner): `/opt/mcp-hub/.env.prod.bak-*` tragen Alt-Keys im Klartext — Löschen ist irreversibel, daher nur vorgeschlagen.


**Kern in einem Satz:** Die vollständige Kette zu einem Thema kommt jetzt in **unter
120 ms aus der Datenbank** — über Ordner- **und** Kontengrenzen hinweg —, statt über
mehrere IMAP-Durchläufe; beide vom Owner gesetzten Abnahmefälle sind bestanden.

**Die beiden Abnahmefälle, gemessen:**

| Fall | Transport | Ergebnis |
|---|---|---|
| Offner | IMAP (hnu + mittwald) | 3er-Kette, 51 ms, Kanten `verweis` |
| Schmalberger | Graph (iil) | 11er-Kette, 119 ms, 3 Beteiligte, 4 Ordner, Kanten `konversation` |

Keine einzige Kante kam über den Betreff — alle sind über `References` bzw. Graph-
`conversationId` belegt. Bestand: **11.573 Nachrichten** aus drei Postfächern.

**Fünf Stufen gebaut (S1–S5, alle gemergt und live):**
- **S1 Antwortpfad** — `mail_suche` (dev-hub) + `tools/mail_agent/suche.py` (platform).
  Jede Antwort trägt ihre **Deckung**: Konten, Umfang, Textzonen und ausdrücklich, was
  NICHT durchsucht wurde. Ohne das liest sich ein leeres Ergebnis wie „gibt es nicht",
  wo nur „habe ich nicht indexiert" gilt.
- **S2 Vorgangs-Schicht** — `Vorgang` + `VorgangsZuordnung`, durabel, über einen
  **natürlichen Schlüssel** (`LogicalMessage.kennung` = sha256(Mandant|Message-ID bzw.
  Inhalts-Hash)). `PROTECT` macht verwaiste Kuration konstruktiv unmöglich.
- **S3 Volltext** — `mail_volltext`, Tor an ADR-286 §4.5 (nur aktiver Vorgang), **kein**
  Umgehungsschalter, als Test verankert.
- **S4 Graph-Ingest** — `mail_ingest --transport graph` mit eigener App-Registrierung
  (`iil-mail-ingest`, Client-Credentials). Dazu `mail_graph_pruefen`: vier Stufen
  Datei→Token→Berechtigung→Postfach, jede mit dem nächsten konkreten Schritt.
- **S5 Dossier** — `mail_dossier` mit Evidenz je Zeile und Ausgabezustand nach §4.6
  (`open` nur bei vollständiger Deckung), Zustand nie ohne Gründe.
- **Verkettung** — `mail_kette`, drei Kantenarten nach Verlässlichkeit; Betreff nur als
  Rückfall und nur bis `BETREFF_MAX=12`, sonst ausdrücklich verworfen **mit Meldung**.

**ADR-288 §4.1 geändert** ([#1598](https://github.com/achimdehnert/platform/pull/1598)):
„durable Referenzen zeigen nie auf Surrogat-IDs" → „hängen an stabiler **Identität**".
Der alte Wortlaut zwang dazu, an der Datenbank vorbeizubauen (Textkopie + Cache-FK +
Neuverknüpfen + Waisen-Zähler); ein natürlicher Schlüssel erfüllt das Ziel mit **einer**
Beziehung.

**Sechs Befunde am echten Bestand — alle waren still:**
1. **41 % des Index waren keine Post** — 2.488 IMAP-Platzhalter aus Kalender/Kontakte/
   Aufgaben, ohne Datum und Absender ([#1584](https://github.com/achimdehnert/platform/pull/1584)).
   Kein Deckungsproblem: es fehlte nichts, es stand zu viel drin, und die Deckung meldete
   folgerichtig `complete`.
2. **Betreff-Stränge verschmelzen Fremdes** — 43 Nachrichten *verschiedener* Studierender
   unter „Request for Thesis Supervision", 43 ResearchGate-Meldungen, 33 „HNU
   Kontaktformular"; umgekehrt zerreißt jeder Betreffwechsel eine echte Kette.
3. **Verschieben erzeugte Duplikate** — die transportspezifische Identität enthält den
   Ordner (id 1713/6045, byte-gleiche Message-ID). Behoben durch Message-ID-Korrelation
   als zweite Stufe.
4. **Der Index speicherte Sequenznummern statt UIDs**, `uidvalidity=0` fest verdrahtet.
   Am Postfach belegt: `FETCH 185` lieferte die Mail, `UID FETCH 185` nichts, Server
   meldet UIDVALIDITY 14. Eine Sequenznummer ist **nicht stabil**
   ([#1656](https://github.com/achimdehnert/platform/pull/1656) + dev-hub#195).
5. **`/opt/platform` driftet ungebremst** — 33 Commits hinter main, nichts synct
   ([#1585](https://github.com/achimdehnert/platform/issues/1585)). Ein Merge nach main
   wirkt dort **nicht**; er sieht nur so aus.
6. **Der untested-command-Hook meldete siebenmal denselben Befund** — sein Fenster wächst
   ohne Nutzereingabe unbegrenzt (166 Records, 27 Vorkommen). Entprellt
   ([#1619](https://github.com/achimdehnert/platform/pull/1619)).

**Zwingend für die nächste Session:**
- **Ein Ingest-Lauf mit echten UIDs steht aus.** Die gespeicherten Nummern stammen noch
  aus der Sequenznummer-Ära; `mail_volltext` kann bis dahin nichts abrufen.
- **`mail_volltext` hat keinen Graph-Pfad** — Kopien mit `transport=graph` tragen kein
  `uid`, `_roh_holen` gibt `None` zurück. Damit ist der Volltext für IIL blockiert und
  für den Offner-Fall teilweise (dessen Kette spannt über beide Transporte).
- **Nach jedem `platform`-Merge, der `tools/mail_agent/` berührt: `/opt/platform` ziehen.**
  Sonst läuft der Container auf altem Werkzeugstand weiter.

**Sicherheit:** Outline-API-Token lag im Klartext in `/etc/cron.d/adr-outline-sync` und
geriet beim Suchen ins Transkript → als **kompromittiert** behandeln, Rotation offen
([#1586](https://github.com/achimdehnert/platform/issues/1586)).

**Eigene Fehler, benannt:** `git add -A` sammelte fremde Arbeit einer Parallel-Sitzung ein
(zurückgenommen); ein `--amend` traf den Basis-Merge-Commit (Branch neu aufgesetzt);
`ruff format .` über den ganzen Baum formatierte fremde, unfertige Dateien um. Und der
Push-Gate meldet über den `HEAD~1`-Fallback **vorbestehende** unformatierte Dateien als
„deine" — kostete mehrere Anläufe, bis ich es gemessen statt geglaubt habe.

## Nächste Schritte (kompakt)

> **✅ hetzner-prod Speicherlage entschärft 2026-07-29 ([#1303](https://github.com/achimdehnert/platform/issues/1303), Messwerte als Kommentar):** Freies RAM **444 → 9.455 MB**, Swap von **4.095/4.095 auf 1.757/4.095**, laufende Container **113 → 45**. Auf Owner-Anweisung wurden 68 nicht benötigte Container **gestoppt** (nicht entfernt — `docker start` holt jeden zurück, Volumes unangetastet): ausschreibungs-hub, odoo, hub137, wedding-hub, coach-hub, recruiting-hub, research-hub, travel-beat, billing-hub, cad-hub, pptx-hub, learn-hub, tax-hub, ttz, bahn-hub, decks-hub, onboarding-hub, trading-hub inkl. `ib_gateway`. **Weiter laufen** risk-hub (live), dev-hub, doc-hub, Outline, mcp-hub, authentik, weltenhub, illustration, dms-hub, writing-hub, aifw. **Die Lehre daraus ist wichtiger als die Zahl:** Ein cgroup-OOM sagt nicht, dass der Container zu klein ist — in die cgroup-Bilanz zählt der Seiten-Cache, und unter Host-Druck kann der Kernel ihn nicht zurückgewinnen. `devhub_celery` fiel **ohne jede Änderung an ihm** von 370,4 auf 305,9 MiB; ein Import, der dreimal mit `rc=137` starb, lief danach durch. „Limit erhöhen" wäre bei 924 MB freiem Host-RAM die gefährlichere Antwort gewesen. **Weiterhin ungeklärt:** warum die Container am 20.07. entfernt statt neu gestartet wurden (`restart: unless-stopped` griff nicht). **Nicht geheilt und deshalb eigenes Ticket ([#1549](https://github.com/achimdehnert/platform/issues/1549)):** `devhub_beat` bei 89,5 % seines 256-MiB-Limits (echter Verbrauch, kein Cache) und Health-Checks, die seit Tagen rot sind — `iil_authentik_worker` seit **12 Tagen**, Log endet am 18.07. mit `code -9`; der Server antwortet weiter, der Worker ist tot.

1. **Ritual-Lauf 1 vorbereiten (bis 16.08., KONZ-038)** — D6 VOR der Baseline (retro_kpis-Härtung + Slug-Wörterbuch einfrieren + Baseline-Artefakt committen), FP-Auswertung der zwei neuen advisory-Scanner, danach D4/D7/D8. Tracking: [#1640](https://github.com/achimdehnert/platform/issues/1640); Gate-Backlog 13/18 offen.
2. **[#1682](https://github.com/achimdehnert/platform/issues/1682) — Megatest-Restabbau** (Nachfolger von Alt-Punkt 1): Budget-Abbau je Repo Richtung 0 und ein `owner`-Feld in `repo-registry.yaml` für die 5 Fremd-Org-Repos (meiki-lra/iilgmbh/ttz-lif), die der `MEGATEST_READ_TOKEN` nicht erreicht; optionaler Token-Tausch. Der Megatest selbst ist grün (Main-Lauf [30758611903](https://github.com/achimdehnert/platform/actions/runs/30758611903), `success`) — offen ist nur der Abbau.

> **Kein Fortschritt an 1 und 2 am 2026-08-07 — bewusst, nicht vergessen.** Die Session
> startete mit `/mailcheck` und wuchs auf Owner-Zuruf zu `todo.iil.pet` aus (Stufen A-D
> einzeln freigegeben). Beide Prios stehen unveraendert; der Ritual-Lauf-Termin **16.08.**
> ist damit neun Tage entfernt.

> **Reconciliation 2026-08-06 (Session-Start Phase 2.6, keine neue Arbeit):** Alt-Punkt 2
> (**[#1549](https://github.com/achimdehnert/platform/issues/1549)** schließen) ist entfernt —
> das Issue ist **CLOSED**, gegen die API geprüft, nicht aus der Prosa gefolgert. Es war am
> 2026-08-05 geschlossen worden und stand ab da in derselben Datei **zweimal widersprüchlich**:
> Zeile 47 im „⚡ Aktueller Stand" führte es als erledigt, die Liste hier forderte weiter das
> Schließen. Der SessionStart-Hook `handover_prio_mirror.sh` liest die **Liste** — er spiegelte
> die erledigte Aufgabe deshalb jeder neuen Session erneut als Prio 2 ein. **Exakt dasselbe
> Muster wie am 2026-08-03 und am 2026-07-28** (Blockquotes darunter); dass es zum dritten Mal
> auftritt, ist der eigentliche Befund: die Reconciliation heilt jeweils den Einzelfall, nicht
> den Mechanismus. Wer ein Issue schließt, muss die Liste im selben Zug anfassen — der
> Erledigt-Vermerk im Stand-Block genügt nicht, weil der Hook ihn nicht liest.
> Liste dadurch **3 → 2 Einträge**, lückenlos durchnummeriert (Maschinen-Vertrag:
> `claude-next-sync` matcht nur ganze Zahlen).

Die frischesten offenen Fäden stehen im **„⚡ Aktueller Stand"** oben und werden dort
gepflegt; sie sind bewusst nicht hierher dupliziert, damit nicht zwei Listen
auseinanderlaufen. Diese Liste hält nur, was über einen Session-Stand hinaus offen ist.

### Erledigt — Alt-Punkte 1–6 (Archiv, nicht mehr offen)

> **Reconciliation 2026-08-03 (Session-Start, keine neue Arbeit):** Die Punkte 1–6 standen
> weiter als offene Prio in der **Liste**, obwohl fünf davon in den Blockquotes direkt
> darunter längst als erledigt vermerkt waren. Der SessionStart-Hook
> `handover_prio_mirror.sh` liest nur die Liste, nicht die Erledigt-Vermerke — er spiegelte
> sie deshalb bei **jedem** Start erneut als Prio 1–6. Dasselbe Muster wie am 2026-07-28
> (Blockquote weiter unten), und genau das, wogegen Phase 2.6 existiert.
> **Jeder Punkt einzeln gegen die API geprüft, nicht aus der Prosa gefolgert:**
> [dev-hub#187](https://github.com/achimdehnert/dev-hub/issues/187) CLOSED 05:36 UTC ·
> [dev-hub#188](https://github.com/achimdehnert/dev-hub/issues/188) CLOSED 04:59 UTC ·
> [mcp-hub#189](https://github.com/achimdehnert/mcp-hub/issues/189) CLOSED 2026-08-02 ·
> [mcp-hub#188](https://github.com/achimdehnert/mcp-hub/pull/188) MERGED ·
> Megatest-Main-Lauf [30758611903](https://github.com/achimdehnert/platform/actions/runs/30758611903) `success` ·
> Outline-MCP in dieser Session ohne 302 erreichbar. **Eine Ausnahme:**
> [#1549](https://github.com/achimdehnert/platform/issues/1549) ist **OPEN** — deshalb
> **nicht** entfernt, sondern als neuer Punkt 2 auf den verbliebenen Rest geschärft.
> Alt-Punkt 7 ist neuer Punkt 1. Liste dadurch **7 → 3 Einträge**, lückenlos
> durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).

1. **Die 15 Megatest-Befunde abarbeiten** — der erste echte Lauf der Suite ([30619024656](https://github.com/achimdehnert/platform/actions/runs/30619024656)) meldet `15 failed, 53 passed`. **Reihenfolge nach Schwere, nicht nach Zahl:** (a) die zwei Security-Funde in Repos mit Budget 0 — dev-hub (`conftest.py:34`, Regel `SECRET_KEY=`) und research-hub; erst entscheiden, ob echt oder Test-Attrappe, der Wert wurde bewusst nicht ausgelesen. (b) die fünf Repos, die als sauber geführt waren und jetzt Violations haben (dev-hub, iil-enrichment, nl2cad, research-hub, trading-hub) — ein Budget von 0 war eine bewusste Zusage. (c) die Budget-Überschreitungen; für **bfagent** (116>72) ist eine ehrliche Neu-Basierung sinnvoller als ein Fix an totem Code, das Repo ist eingefroren (import-only). (d) `test_should_registry_budget_sync` — Repos in `repo-registry.yaml` ohne Budget. **Vor jeder Bewertung mitdenken:** die Budgets stammen vom 27.04. aus lokalen Läufen und wurden nie in CI gemessen; „über Budget" heißt hier nicht „verschlechtert", sondern „erstmals gemessen".
2. **mcp-hub: die zwei roten Jobs schließen** — [#188](https://github.com/achimdehnert/mcp-hub/pull/188) (Formatierung) und [#189](https://github.com/achimdehnert/mcp-hub/issues/189) (click/huggingface-hub-Konflikt in der geteilten Runner-Umgebung). **Der Verdacht aus dem Vor-Stand ist widerlegt:** `ci / gate` ist **kein** Konstruktionsfehler und verlangt auch keine Teilmenge — seine `needs`-Liste enthält alle elf Jobs, `lint` und `security` inklusive, im Tag `v1.0.11` **identisch** zu `main` (beide gelesen). Der echte Mechanismus ist `continue-on-error`: `security` hat es hart verdrahtet („Job blockiert Deploy nicht — aber Output ist sichtbar"), `lint` über den Input `lint_soft_fail`, den `mcp-hub/deploy.yml` bewusst auf `true` setzt (fünf Zeilen Begründung im Workflow: Polyrepo-Monorepo ohne Root-`requirements.txt`, Option 3 aus #78, **gitleaks bleibt hartes Gate**). GitHub zeigt bei `continue-on-error` die Job-**Conclusion** als `failure`, setzt aber `needs.<job>.result` auf `success` — der Gate ist damit zu Recht grün. **Was bleibt:** „`ci / gate` grün" belegt in mcp-hub **nicht**, dass Lint und Security grün waren. Das ist gewollt, muss man aber wissen. **Weiter offen:** der scharfe Negativtest zu [#184](https://github.com/achimdehnert/mcp-hub/issues/184) — über die vorhandenen Workflows nicht auslösbar (keiner trägt ein ungültiges Modell); verifiziert ist nur die Code-Präsenz im laufenden Container.
3. **`devhub_beat` und die toten Health-Checks** ([#1549](https://github.com/achimdehnert/platform/issues/1549)) — `devhub_beat` bei 89,5 % seines 256-MiB-Limits (echter Verbrauch, kein Seiten-Cache, also nicht durch die Host-Entlastung geheilt) und Health-Checks, die seit Tagen rot sind: `iil_authentik_worker` seit **12 Tagen**, Log endet am 18.07. mit `code -9` — der Server antwortet weiter, der Worker ist tot. **Stand 2026-08-02:** der tägliche 03:30-Ingest läuft jetzt wirklich (Beleg in Punkt 5), ist damit wieder ein Belastungstest für dieses Limit — die Speichermessung von `devhub_beat` steht aber weiterhin für sich und wird von einem Ingest-Lauf **nicht** beantwortet. Gegenlesen mit dem **richtigen** Task-Namen: `docker logs devhub_celery --since 6h | grep -i ingest_scheduled` (der früher hier genannte `mail_ingest` existiert nicht).
4. **Outline-MCP** — unverändert `302` in laufenden Sitzungen, eine **neue** Sitzung löst es (Belege im Vor-Stand). Kein Blocker mehr: der Umweg ist erprobt und wurde am 31.07. genutzt (`scratchpad/outline-lesson.sh` — Collection über `collections.list` suchen, dann `documents.create`; die drei Werte nur in Variablen und curl-Kopfzeilen, nie in URL oder Ausgabe). Geschrieben darüber: Doc `dde42e37-83e0-42ff-acc5-e5637ba3002e`. **Achtung beim Nachbauen:** ein `tr < ~/.secrets/…` direkt in der Bash-Kommandozeile löst den Secret-Leak-Guard aus — das Skript als Datei anlegen, nicht per Heredoc im Aufruf.
5. **Mail-Ingest läuft jetzt auf Prod — Restarbeit ist ein UID-Neulauf** (korrigiert den Vor-Stand, der ihn als „läuft nicht" führte; [dev-hub#187](https://github.com/achimdehnert/dev-hub/issues/187)). Am 2026-08-02 gemessen: `PeriodicTask` **`mail-agent-ingest-daily` → `mail_agent.ingest_scheduled`**, `30 3 * * *` Europe/Berlin, `enabled=True`, letzter Lauf **2026-08-02 01:30 UTC**; Bestand **11.573 Nachrichten** über hnu/mittwald/iil. **Was bleibt, ist nicht der Ingest, sondern sein Inhalt:** die gespeicherten Nummern stammen aus der Sequenznummer-Ära (Fix in [#1656](https://github.com/achimdehnert/platform/pull/1656) + dev-hub#195) — bis zu einem Neulauf kann `mail_volltext` **nichts** abrufen. Zweitens hat `mail_volltext` **keinen Graph-Pfad**, damit ist der Volltext für das IIL-Postfach blockiert. Drittens: **`/opt/platform` zieht sich nicht selbst** ([#1585](https://github.com/achimdehnert/platform/issues/1585)) — nach jedem Merge, der `tools/mail_agent/` berührt, dort von Hand pullen, sonst läuft der Container auf altem Werkzeugstand weiter.
   <details><summary>Vor-Stand vom 31.07. (widerlegt, zur Nachvollziehbarkeit)</summary>
   Der Satz in Punkt 3, „ab jetzt läuft täglich 03:30 ein Ingest-Lauf", war am 31.07. **widerlegt** — der Lauf hatte **nie** stattgefunden. Der dort genannte Grep nennt zudem einen Task-Namen, den es nicht gibt (`mail_ingest`); er heißt `mail_agent.ingest_scheduled`. Fünf Messungen am Prod-Host: Logs 24 h ohne Treffer · Celery-Registry 19 Tasks, keiner mit `mail` · `PeriodicTask`-Tabelle 12 Einträge, keiner für `mail_agent` · weder `/app/apps/mail_agent` noch `/app/mail_tools` im Container · Mount-Quelle `/opt/platform/tools/mail_agent` fehlt auf dem Host. Der Ingest ist auf **keiner** Schicht aktiv: kein Code im Container, kein Bind-Mount, kein `PeriodicTask`-Eintrag. Zu tun sind **zwei** Dinge, nicht eines: Code auf Prod bringen **und** den DB-Eintrag `mail-agent-ingest-daily` → `mail_agent.ingest_scheduled` anlegen. Laufendes Image vom **12.07.**, 19 Tage alt — alles, was seither in dev-hub gebaut wurde, ist auf Prod nicht vorhanden.
   </details>
6. **Health-Poll meldet `succeeded`, prüft aber nichts** ([dev-hub#188](https://github.com/achimdehnert/dev-hub/issues/188), P1, `severity:critical`) — `health.poll_all_checks` läuft alle fünf Minuten, findet `Organization.objects.count() == 0` und gibt `{'error': "Tenant 'devhub' not found"}` als **Rückgabewert** zurück; Celery verbucht den Task als **grün**. `platform_health_scan` entsprechend `servers_scanned: 0`. Zwei Fixe, getrennt zu bewerten: Organization anlegen behebt **diesen** Fall, der Task sollte **fehlschlagen** statt `succeeded` zu melden — das behebt die **Klasse**. **Mögliche Verbindung zu Punkt 3 (rote Health-Checks) — ausdrücklich Hypothese, nicht verifiziert.**

> **Erledigt 2026-08-02 (Session 932035, Megatest):** **Punkt 1 komplett** — alle 15
> Befunde trianguliert und geschlossen; Main-Lauf danach **119 passed, 0 failed**
> ([30758611903](https://github.com/achimdehnert/platform/actions/runs/30758611903)).
> Drei Wurzelursachen statt 15 Einzelfixe: (a) beide Security-Funde waren selbst-
> beschreibende Attrappen (Werte im CI-Log gelesen); (b) V-CFG-02 flaggte per Regex das
> eigene Empfehlungsmuster — präzisiert, plus klickdummy/-Skip ([#1681](https://github.com/achimdehnert/platform/pull/1681));
> (c) Megatest-CI scannte eingefrorene Erst-Klon-Stände und konnte private Repos mit dem
> repo-scoped GITHUB_TOKEN nie erreichen — Checkout zieht jetzt frisch nach, entfernt
> stale Klone, `MEGATEST_READ_TOKEN` (Enterprise-PAT, Owner-Freigabe, Token-Scrub) hebt
> die Abdeckung auf alle bis auf 5 Fremd-Org-Repos. Budgets ehrlich neu basiert
> (13 Repos ergänzt, bfagent 72→33, mcp-hub 79→34); Marker-PRs dev-hub#199,
> research-hub#53, nl2cad#61, iil-enrichment#11 gemergt (alle `[skip ci]`-konform bzw.
> ohne Deploy-Pfad). Rest-Abbau + Owner-Feld-Plan: [#1682](https://github.com/achimdehnert/platform/issues/1682);
> risk-hub-Sichtung `seed_test_user`: [iilgmbh/risk-hub#478](https://github.com/iilgmbh/risk-hub/issues/478).

> **Erledigt 2026-08-02 (Session 8ed6a2):** **Punkt 2 komplett** — mcp-hub#188-PR gemergt,
> #189 durch #192 (Security-Scan im frischen venv, je Job) geschlossen; Deploy 30741745261
> success, venv-Step im Log belegt. **Punkt 4 bestätigt:** Outline in frischer Session
> erreichbar. Punkte 1, 5, 6 unverändert offen; Details im LOG (Session 8ed6a2).
> — **Nachtrag Session 922ab2 (später am selben Tag):** für **Punkt 5** trifft „unverändert
> offen" nicht mehr zu; der Ingest läuft, am Prod-Host gemessen. Punkte 1 und 6 stimmen.

> **Erledigt 2026-08-03 (Session 9530de73, health-poll-honest-failure):** **Punkte 3 und 6
> komplett** — Details im „⚡ Aktueller Stand" oben: #1549 aufgelöst (Prod 0 unhealthy,
> pidof-Wurzelursache, [dms-hub#58](https://github.com/achimdehnert/dms-hub/pull/58)/[coach-hub#58](https://github.com/achimdehnert/coach-hub/pull/58)),
> dev-hub#188-Klasse gefixt ([dev-hub#201](https://github.com/achimdehnert/dev-hub/pull/201) live);
> die Punkt-6-Hypothese „Verbindung zu Punkt 3" ist für Prod **falsifiziert** (Prod pollte
> korrekt — der blinde Poller war fsn1). **Punkt 4 erneut bestätigt** (2 Outline-Lessons per
> MCP geschrieben, kein 302 in dieser Session). Offen bleiben Punkt 5 (UID-Neulauf,
> [dev-hub#187](https://github.com/achimdehnert/dev-hub/issues/187)) und aus Punkt 6 die
> fsn1-Datenlage (Rätsel + Skript, siehe Aktueller Stand).

> **Nachtrag 2026-07-31 — Konsequenz aus Punkt 5 für Punkt 3 (übernommen aus
> [#1612](https://github.com/achimdehnert/platform/pull/1612) vor dessen Schließung):**
> Punkt 3 führt den täglichen 03:30-Ingest als **Belastungstest** für das 256-MiB-Limit von
> `devhub_beat`. Diese Prämisse ist entfallen — der Lauf existiert nicht (Messung in Punkt 5).
> **Damit steht die Speicherfrage von `devhub_beat` für sich**: Sie wird nicht durch einen
> Ingest-Lauf beantwortet und braucht eine eigene Messung. Punkt 3 bleibt davon unberührt
> offen; nur seine Begründung über den Belastungstest trägt nicht mehr.
>
> **Überholt am 2026-08-02:** der Lauf existiert inzwischen (`mail-agent-ingest-daily`,
> letzter Lauf 01:30 UTC). Der *Kernsatz* dieses Nachtrags bleibt trotzdem gültig — die
> Speicherfrage von `devhub_beat` beantwortet ein Ingest-Lauf nicht, sie braucht eine
> eigene Messung. Nur die Begründung „weil es den Lauf nicht gibt" ist entfallen.

> **Nachtrag 2026-07-30 (Abend):** **Vier PRs im Review**, thematisch eine Kette —
> [#1562](https://github.com/achimdehnert/platform/pull/1562) (`html_to_text` lag zweimal im
> Baum, die Kopie ohne `<style>`-Fix), [#1565](https://github.com/achimdehnert/platform/pull/1565)
> (Ursprungsmail als `message/rfc822` anhängbar; RFC 2046 §5.2.1 erlaubt dort **kein** base64,
> `add_attachment(bytes, maintype="message")` wählt es aber),
> [#1566](https://github.com/achimdehnert/platform/pull/1566) (Antwort-HTML kompakt) und
> [#1568](https://github.com/achimdehnert/platform/pull/1568) (Namensdopplung nach dem Gruß).
> Auslöser war eine Kundenrückmeldung zum Rollen-Design: **„Sieht aus wie ein Newsletter."**
> Konsequenz, die über die PRs hinausgeht: `--design` ist für **Kundenkorrespondenz nicht
> geeignet** und bleibt internen Statusmails vorbehalten; Mails werden am Maßstab der
> Kundenmail gemessen (360 Zeichen), nicht am eigenen Erklärungsbedürfnis (4.000).
> **Signaturen gekürzt** (5 → 2 Zeilen, Firmenangaben nur im Pflicht-Footer, §35a jetzt auch
> für die DSB-Rolle — Absender ist die GmbH). **Offen und bewusst nicht hier abgelegt:** die
> MEiKI-Datenschutz-Analyse für die Actago-Anfrage liegt als lokales Board
> (`~/.claude/boards/meiki-datenschutz-anzeige.md`, LRA-Vorgangsdaten gehören nicht ins Repo)
> und **wird in einer anderen Session weiterbearbeitet** — Kern: § 80 Abs. 1 SGB X verlangt
> **zwei** Anzeigen, die beauftragte öffentliche Stelle zeigt bei ihrer eigenen Aufsicht an.
>
> **Erledigt 2026-07-30 (Mail-Ingest scharf, Antwort-Zitat, cf_access):** **Alt-Prio 1 (Zugangsdaten für die Mail-Ingestion auf Prod) ist komplett durch** — Runbook-Schritte 1 bis 7, nicht nur Schritt 4. Der Owner legte die Zugangsdaten selbst per stdin-Pipe ab (Agent-Sperre auf `~/.secrets` gilt unabhängig von einer Chat-Ermächtigung); die geheimnisfreien Vorstufen kamen vom Agenten: `/opt/dev-hub/mail/mail-hnu.env`, `MAIL_AGENT_ACCOUNT/CONFIG/TOOLS` in `.env.prod`, `/opt/platform` auf `main` gezogen, und die zwei read-only Bind-Mounts als [dev-hub#172](https://github.com/achimdehnert/dev-hub/pull/172). Reihenfolge bewusst: Trockenlauf über 3 Ordner → Vollaufnahme **ohne** Freigabe zum Größenvergleich (**+0,5 %** gegen den lokalen Referenzlauf, Ordnerzahlen 92/27 identisch) → erst dann `--freigeben`. Endstand **6.008 Nachrichten, 12.865 Beteiligungen, genau eine aktive Generation, Deckung `complete`**. **Alt-Prio 2 ([#1548](https://github.com/achimdehnert/platform/pull/1548) durch Code-Owner)** war beim Session-Start bereits **MERGED** — die SessionStart-Anzeige las eine 8 Commits alte Handover-Kopie und warnte selbst davor; der Agent übernahm die Prio trotzdem zunächst als offen (📌 derselbe Stale-Klon-Fehler wie in `feedback_stale_clone_as_edit_basis`, diesmal in der Board-Ausgabe statt im Edit). Ebenso war **ADR-288 Runde 4** längst abgesetzt und eingearbeitet (`f876c378`); die Statuszeile des ADR sagte trotzdem noch „nach drei externen Runden" — hier auf **vier (§11.6)** korrigiert, Frontmatter-Validierung 234/234 grün. **Alt-Prio 4 (`ci / gate` meldet grün über rotem Lauf) ist aufgeklärt und war kein Fehler** — Details in der neuen Prio 2. Liste dadurch 4 → 3 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
>
> **Erledigt 2026-07-29 (Abend-Session — o-Series-Fix und ADR-288 Runde 4):** **Alt-Prio 2 (ADR-288 in eine vierte externe Runde geben) ist abgearbeitet** — die Runde lief gegen `openai/o3`, Verdikt **überarbeiten**, 7 von 9 Befunden `[valid]`, Tag-Tabelle in §11.6 ([#1548](https://github.com/achimdehnert/platform/pull/1548), wartet auf Code-Owner). Die Runde traf **alle drei** in §11.5 als ungeprüft benannten Punkte. Folgenreichste Änderung ist eine **Herabstufung**: Gate 0 fällt von ✅ auf 🟡, weil das Argument, mit dem die alte Bestandszahl 90.967 entwertet wurde — eine Einzelmessung kann einen Zwischenzustand treffen — unverändert gegen die neue 66.580 gilt; voll erfüllt erst nach drei Wiederholungsmessungen an nicht aufeinanderfolgenden Tagen mit protokollierter Rohausgabe. Neu: §3.2.1 (drei Auslöser, ab denen die Zweckbindung zur Umdeklaration wird und ein Supersede von ADR-286 fällig ist), Gate 10, Gate 11, versionierte Ausschluss-Konfiguration, und §4.12 grenzt „gesperrt" auf den Retrievalpfad statt auf Konto oder Lauf ein. **Bewusst abgelehnt:** `open` ab ~90 % Deckung zuzulassen — bei jeder zehnten ungesehenen Nachricht kippt die Negativaussage. **Der Weg dorthin war der eigentliche Aufwand:** der Egress-Pfad war tot und meldete das nicht. Zwei Ebenen, beide gemergt — [mcp-hub#185](https://github.com/achimdehnert/mcp-hub/pull/185) (o-Series akzeptieren nur `temperature=1`; **#183 war unvollständig**, weil Weglassen die Kontrolle an aifws Default 0.7 abgab) und [mcp-hub#186](https://github.com/achimdehnert/mcp-hub/pull/186) (fehlgeschlagene LLM-Calls werfen statt leer zurückzugeben, schließt [#184](https://github.com/achimdehnert/mcp-hub/issues/184)). Liste dadurch 3 → 4 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
>
> **Erledigt 2026-07-29 (Parallel-Session Mail-Links):** **Alt-Prio 3 (#1511 mergen) entfällt** — der PR ist **CLOSED, nicht gemergt** (per `gh pr view` geprüft, nicht aus dem Vor-Stand übernommen); der Session-Stand vom 29.07. steht bereits auf `main`. Liste dadurch 3 → 2 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). **Zwei Punkte dieser Session sind noch am selben Tag geschlossen worden und stehen deshalb gar nicht erst in der Liste:** [#1544](https://github.com/achimdehnert/platform/pull/1544) (`MAIL_LOGIN` trennt Anmeldename und Absenderadresse) ist **MERGED**, und `~/.claude/mail-hnu.env` ist unmittelbar danach umgestellt — Reihenfolge eingehalten, denn mit der neuen Belegung käme der Vor-Merge-Stand nicht mehr ins Postfach; Lesepfad danach scharf gegengeprüft. **Der Verteiler-Drift ist zu** — nach Owner-Freigabe `generate.py --target ~/.claude/commands --allow-live` gelaufen, `doctor.py` meldet **DRIFT-SCORE 0** (51 Kopien fresh, 0 copy-stale, 0 dangling). Vor dem Live-Schreiben nach Staging generiert und gediffed: rein additiv, 65 → 263 Zeilen, einzige entfernte Zeile war der Verwaltungs-Footer. Die Live-Kopie war älter als der Drift-Befund vermuten ließ — ihr fehlten auch `--all-folders`, `--dossier`, `--abwesenheitsbeweis` und `--json`. Vorstand liegt als `~/.claude/commands.bak`. **Neu gebaut und gemergt:** [#1531](https://github.com/achimdehnert/platform/pull/1531) `mail_view.py`, [#1535](https://github.com/achimdehnert/platform/pull/1535) `anker.py` + `/a/`-Route, [#1536](https://github.com/achimdehnert/platform/pull/1536) `port_freigeben.py`, [#1538](https://github.com/achimdehnert/platform/pull/1538) systemd-Falle. Der Dienst läuft als User-Unit `mail-links.service` (enabled, neustartfest verifiziert). **Nicht mit erledigt:** die Rolle `dsb` hat weiterhin keine Kontaktdaten ([#1481](https://github.com/achimdehnert/platform/issues/1481)) — bei `hnu` war derselbe Platzhalter drin und wäre an eine Studentin hinausgegangen; korrigiert.
>
> **Erledigt 2026-07-29:** **Alt-Prio 1 (KONZ-012 DSB-Partner-Rolle)** — [risk-hub#455](https://github.com/iilgmbh/risk-hub/pull/455) ist MERGED. **Alt-Prio 2 (Mail-Rollen)** — [#1512](https://github.com/achimdehnert/platform/pull/1512) MERGED. **Alt-Prio 3 (Regel-Interpreter ADR-284 §7a)** — [#1513](https://github.com/achimdehnert/platform/pull/1513) MERGED; die Verdrahtung an ein echtes Postfach bleibt als [#1514](https://github.com/achimdehnert/platform/issues/1514) getrackt. **Alt-Prio 4 (scharfer Einzel-Lauf #1517)** — [#1517](https://github.com/achimdehnert/platform/pull/1517) MERGED. Liste dadurch 4 → 3 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). **Nicht mit erledigt:** die Rolle `dsb` hat weiterhin keine Kontaktdaten in der Signatur — das ist Owner-Anteil und lebt in [#1481](https://github.com/achimdehnert/platform/issues/1481) weiter.
>
> **Erledigt 2026-07-28 (Session-Start-Reconciliation):** **Alt-Prio 4 (Verteiler-Drift) entfällt** — `doctor.py` meldet **DRIFT-SCORE 0** (0 dangling, 0 symlink-stale, 51 Kopien fresh, 0 copy-stale), am 2026-07-28 um 11:2x selbst ausgeführt statt aus dem Vor-Stand übernommen. Die Zeile war seit dem Erledigt-Vermerk im Stand-Block (oben) tot, wurde aber vom Start-Hook `handover_prio_mirror.sh` weiter als offene Prio gespiegelt — genau das Muster, gegen das Phase 2.6 existiert. **Nicht dieser noch der Vor-Session zurechenbar:** kein Artefakt der Sessions vom 28.07. berührt `doctor.py` oder `generate.py`; wodurch die Lane grün wurde, ist offen und bleibt als Hypothese stehen. Liste dadurch 4 → 3 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
>
> **Erledigt 2026-07-27 (Vormittags-Session — Stub-Issues, Postfach-Aufräumen, zwei Werkzeug-Defekte):** **Alt-Prio 2 (Stub-Issues) ist abgearbeitet** — vier PRs gemergt ([#1473](https://github.com/achimdehnert/platform/pull/1473) Header-Charsets, [#1474](https://github.com/achimdehnert/platform/pull/1474) `--subject`-UND-Filter, [#1475](https://github.com/achimdehnert/platform/pull/1475) ADR-234-Restzeile, [#1477](https://github.com/achimdehnert/platform/pull/1477) Uptime-Kontingent), vier Issues CLOSED. **Zwei Prämissen sind dabei gekippt:** [#1360](https://github.com/achimdehnert/platform/issues/1360) war seit dem 22.07. im Code behoben und nur nie geschlossen worden — offen war allein der Altbestand (5 Leases mit `"repo": "."`, korrigiert); und [#1304](https://github.com/achimdehnert/platform/issues/1304) forderte einen Sweep über 76 Dateien, die inzwischen unter `_ARCHIVED/` liegen — die lebenden project-facts tragen den Header in **0** Repos, die echte Restschuld saß in ADR-234 selbst. **Der teuerste Fund war ein eigener Fehler:** ein `/mailcheck` meldete, eine DSGVO-Authentifizierungsmail sei nie gesendet worden — belegt mit einer vermeintlichen Vollerhebung. Der dafür benutzte Platzhalter `--from "@"` verwarf auf „Gesendete Elemente" **21 von 34** Nachrichten still, weil Exchange den Absender dort teils als X.500-DN **ohne `@`** liefert. Die Mail war gesendet; auf Basis des falschen Befundes bekam der Betroffene eine **zweite** Anfrage. Behoben in [#1485](https://github.com/achimdehnert/platform/pull/1485) (`--find --all`, laute Warnung bei stiller Verwerfung, `--draft --cc`), `/mailcheck` nachgezogen. **ADR-284 auf `accepted`** plus neuem §7a Regel-Lebenszyklus ([#1484](https://github.com/achimdehnert/platform/pull/1484)). **IIL-Postfach: 1366 → 185 Mails** (666 maschinelle Absender in Sachordner, 516 abgeschlossene Jahrgänge nach `Archiv/<Jahr>`), kein einziger Löschvorgang, alles reversibel — dabei fing ein Trockenlauf eine falsche Hoster-Regel ab, die 52 Sicherheitshinweise im Rechnungsordner begraben hätte. **Nicht verifiziert:** ob die verteilten Skill-Kopien die Korrekturen tragen — `doctor.py` sagt nein (Prio 4). Liste dadurch 2 → 4 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
>
> **Erledigt 2026-07-26 (Abend-Session — ADR-Sync-Hygiene abgeschlossen):** **Alt-Prio 2 ([dev-hub#157](https://github.com/achimdehnert/dev-hub/issues/157)) ist CLOSED** und **Alt-Prio 4 ([#1438](https://github.com/achimdehnert/platform/issues/1438)) ebenfalls** — Liste dadurch 4 → 2 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). **`--prune` ist nicht nur gebaut, sondern einmal real gelaufen** ([dev-hub#159](https://github.com/achimdehnert/dev-hub/pull/159)): 6 Waisen entfernt, `0 imported, 232 unchanged, 0 errors`, Backup aller 238 Zeilen inkl. Volltext vorher auf dem Prod-Host. Der Vorschlag aus dem Ticket wäre so **falsch** gewesen: ein reiner `source_path`-Präfixvergleich hätte auch `docs/adr/reviews/` gelöscht, weil die Contents-API **nicht rekursiv** listet und diese Zeilen deshalb nie „gesehen" werden — der Test dazu war vor dem Fix rot. **Die Doppel-Nummern waren durchgängig Begleitdokumente** (`-review`, `-implementation-plan`), nicht die Nummern-Erkennung: behoben in [risk-hub#456](https://github.com/iilgmbh/risk-hub/pull/456), [odoo-hub#17](https://github.com/achimdehnert/odoo-hub/pull/17) und [pptx-hub#45](https://github.com/achimdehnert/pptx-hub/pull/45)/[#46](https://github.com/achimdehnert/pptx-hub/pull/46); `bfagent` ist **archiviert** (read-only, `gh pr create` scheitert) und deshalb per [dev-hub#164](https://github.com/achimdehnert/dev-hub/pull/164) aus dem Sync genommen. **Zwei Funde, die in keinem Ticket standen:** (a) es gab **gar keine maschinenlesbare Sync-Liste** — die Repos wurden von Hand als `--repo` getippt, `PLATFORM_REPOS` treibt Concept-Scoping und wird vom Importer nie gelesen (meine eigene erste Zuordnung war falsch und ist im Issue korrigiert); (b) `odoo-hub` (12 ADRs), `dev-hub` (1) und `mcp-hub` (1) standen **nie** im Sync — nachimportiert, Bestand 318 → 331. Abschluss-Abgleich über alle 10 Sync-Repos: Dateien, eindeutige Nummern und Zeilen stimmen **10/10 exakt**. Bei pptx-hub hätte „längere Fassung behalten" die Abwägung gelöscht — `-optimized` war kein Superset, `Alternatives Considered` stand nur im Entwurf (und fehlte laut `reflex` genau dort); beide Abschnitte sind wörtlich übernommen (maschinell verglichen, 52 + 5 Zeilen identisch). **Nicht verifiziert:** ob die drei nachimportierten Repos künftig automatisch mitlaufen — es gibt weiterhin keinen Automatismus, der `ADR_SYNC_REPOS` konsumiert; die Liste ist nur die Grundlage dafür.
>
> **Erledigt 2026-07-26 (Vor-Session):** **Alt-Prio 1 ([#1447](https://github.com/achimdehnert/platform/issues/1447)) ist CLOSED** — der ADR-Sync läuft wieder über alle acht Repos, verifiziert per Mengenvergleich der ADR-Nummern gegen `git ls-tree origin/main docs/adr/` (für `platform` **keine einzige Lücke**; vorher fehlten 40). Die Ursache war **zusammengesetzt, nicht einfach** — vier Defekte mussten fallen: (a) der Token im Prod-Container lieferte 401 und wurde durch einen vorhandenen gültigen ersetzt (kein PAT des Kontos war abgelaufen — „widerrufen" ist die belastbarere Lesart); (b) `docker restart` wirkte **nicht**, weil die Container-Umgebung seit der *Erstellung* feststeht — belegt per Hash-Vergleich (Datei `6a0152e4` vs. Container `d7b49e5d`), erst `compose up -d --force-recreate` mit der aus den Container-Labels gelesenen `-f`-Kette hat beide angeglichen; (c) `raw.githubusercontent.com` meldet abgelehnte Credentials als **404**, nicht als 401 ([dev-hub#154](https://github.com/achimdehnert/dev-hub/pull/154)); (d) httpx folgt Redirects per Voreinstellung **nicht**, und `risk-hub` liegt inzwischen unter `iilgmbh/` ([dev-hub#155](https://github.com/achimdehnert/dev-hub/pull/155) samt Datenmigration). Die offene Frage des Issues ist beantwortet: der Webhook-Fallback synchronisierte **nie** — er signierte `{}`, sendete aber einen anderen Body (HMAC über `request.body` → `401 Invalid signature`), und selbst mit gültiger Signatur wäre er auf dieselbe 401 gelaufen; behoben in [#1449](https://github.com/achimdehnert/platform/pull/1449). **Selbst verursachter Zwischenschaden, benannt statt versteckt:** der erste erfolgreiche Voll-Import ließ `platform` von 241 auf 202 Zeilen fallen — die ADR-Identität war pro *Mandant* eindeutig statt pro *Repo*, also überschrieb `risk-hub`s ADR-001 die von `platform`. Der Konstruktionsfehler ist älter (vorher 7 verlorene Nummern), sichtbar wurde er durch den ersten vollständigen Import; behoben in [dev-hub#156](https://github.com/achimdehnert/dev-hub/pull/156) mit Migration und Regressionstest **inklusive Negativprobe** (mit dem alten Lookup fällt der Test durch). **Zwei Gates gegen Fehlerklassen dieser Session gebaut und live verdrahtet** ([#1454](https://github.com/achimdehnert/platform/pull/1454), [#1455](https://github.com/achimdehnert/platform/pull/1455)): ein Stop-Hook meldet Befehle, die dem User ohne eigenen Testlauf übergeben werden (drei Fehlschläge an einem Tag), ein SessionStart-Hook meldet Rückstand des lokalen Klons (eine Workflow-Datei aus veraltetem `main` gelesen und einen längst behobenen Defekt als neuen Befund gemeldet). Verteiler-Lauf grün, `doctor.py` DRIFT-SCORE 0. Liste dadurch 3 → 4 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
>
> **Nachtrag 2026-07-25 Session-Ende:** [#1416](https://github.com/achimdehnert/platform/issues/1416) ist **CLOSED (completed)** — Zweck erfüllt (Falsifikations-Gate entschieden, ADR-285 `accepted`), Wortlaut bewusst nicht: die dort genannten Migrationen von `teste-repo` und `workflow-index` sind begründet unterblieben und in ADR-285 §10 + [#1287](https://github.com/achimdehnert/platform/issues/1287) verankert. Neu aufgenommen als **Prio 1**: [#1447](https://github.com/achimdehnert/platform/issues/1447) (ADR-Sync 401), am 25.07. vom Owner ausdrücklich auf morgen vertagt — Liste dadurch 2 → 3 Einträge, lückenlos durchnummeriert.
>
> **⚙️ Branch-Protection geändert 2026-07-25 ~13:30 UTC (Owner-Freigabe — durables Audit-Artefakt):** Das Ruleset **`main-required-checks`** (ID `17621471`, `enforcement: active`, `bypass_actors: []`) verlangt ab sofort **drei** statt zwei Checks. **Vorher:** `guardian`, `gitleaks secret scan`. **Nachher:** zusätzlich **`pytest tools/tests/ + CI-tote Testorte`**. Die `pull_request`-Regel (1 Approval, Code-Owner-Review) ist unverändert, `bypass_actors` bleibt leer — weiterhin kein Self-Merge. **Rollback:** das vollständige Vorher-JSON liegt als `ruleset-17621471-BACKUP.json` im Session-Scratchpad; Rückweg ist ein `PUT` desselben Payloads ohne den dritten Eintrag. **Warum das erst jetzt ging:** ein required Check mit `paths`-Filter läuft auf docs-only-PRs gar nicht und hängt dort dauerhaft auf `pending` — er hätte ausgerechnet die PRs blockiert, die er nicht prüft. Erst das Zwilling-Muster ([#1443](https://github.com/achimdehnert/platform/pull/1443)) hat das aufgelöst, **zweifach live gegengeprüft**: auf [#1444](https://github.com/achimdehnert/platform/pull/1444) (`AGENT_HANDOVER*`) und [#1445](https://github.com/achimdehnert/platform/pull/1445) (`docs/adr/**` + `policies/**`) meldete der Check grün, Steps 5–10 je `skipped`, 7–10 s Laufzeit. Damit ist [#1414](https://github.com/achimdehnert/platform/issues/1414) abgeschlossen. **Nicht verifiziert zum Zeitpunkt der Schaltung:** dass ein PR den required Check auch wirklich als *erfüllt* verbucht (Kontext-String-Match) — **dieser PR ist der erste Lauf unter der neuen Regel und damit die Probe.** Bleibt er auf `pending` hängen, ist der Kontext-String falsch und das Backup wird eingespielt.
>
> **Erledigt 2026-07-25 (Nachmittag — diese Session):** **ADR-285 steht auf `accepted`** ([#1445](https://github.com/achimdehnert/platform/pull/1445) MERGED) — §9 auf 5/5, Bündel komplett: ADR-229 → `superseded` (Schritt 1 bleibt ausdrücklich gültig), ADR-230 §2 REC-3 aufgelöst, `policies/claude-skills.md` auf die eine Lane, neue §9a D5-Rückbau-Prozedur (6 Prüfschritte, pro Maschine), `validate` 232/232. **Accepted ≠ Rollout:** 4 Artefakte in der Skills-Lane, 51 in `commands`; Phase 2/3 bleiben über [#1287](https://github.com/achimdehnert/platform/issues/1287) gegatet, die Phase-2-Vorbedingung (`workflow-index` bricht den Index-Checker) steht in ADR-285 §10. **ADR-285 Kriterium 1 geschlossen, ohne dafür etwas zu bauen.** Der Handover führte „einmal `/issues-offen <arg>` TIPPEN" als letzten offenen Punkt — genau das passierte beiläufig beim Aufruf des Skills mit einem Marker-Argument; der Body kam substituiert zurück, der Beleg wanderte als Nachtrag in [#1441](https://github.com/achimdehnert/platform/pull/1441) (MERGED). **Beim Nachmessen fiel Kriterium 2 mit auf:** `doctor.py` meldet für beide Lanes DRIFT 0 — die stale Kopie aus dem #1408-Merge ist durch die gegatete Live-Regeneration weg. §9 steht damit auf 1–3 grün. **[#1414](https://github.com/achimdehnert/platform/issues/1414) triagiert — die Lint-Schuld existiert nicht:** mit dem gepinnten `ruff 0.15.4` meldet `ruff check tools/ scripts/` „All checks passed!", und die letzten 10 `tools-tests`-Läufe in CI sind grün; die geplanten 111 Auto-Fixes und ~291 Triage-Fälle entfallen ersatzlos. Übrig blieb der Required-Entscheid — und dabei kam ein **neues Gegenargument** heraus: ein required Check mit `paths`-Filter läuft auf docs-only-PRs gar nicht und hängt dort dauerhaft auf `pending`, blockiert also ausgerechnet die PRs, die er nicht prüft. Gelöst mit dem **Zwilling-Muster** ([#1443](https://github.com/achimdehnert/platform/pull/1443) MERGED): Job läuft immer, entscheidet intern; Pfad-Liste bleibt SSoT in `on.push.paths`, gelesen von `tools/ci_relevant_paths.py` (9 Tests, Falsifikationslauf belegt sie als nicht-vakuum). **Werkzeug-Lehre:** ein `major_outage` der GitHub-Actions färbte #1441 rot und wurde beinahe dem eigenen Commit zugeschrieben — entlastet hat ein zeitgleich gescheiterter **Cron**-Lauf, der den Branch nie berührte. Umgekehrt hing githubstatus.com beim Recovery nach: die Seite meldete noch `major_outage`, während Läufe längst wieder durchliefen. Statusseite ist Indiz, der Lauf ist der Beweis. **Nicht verifiziert:** dass der Zwilling auf einem docs-only-PR wirklich grün meldet — dieser PR hier ist der erste solche Fall und damit die Gegenprobe.
> **Erledigt 2026-07-25 (Session-Ende — Vorsession):** **Alt-Prio 1 ([#1423](https://github.com/achimdehnert/platform/issues/1423)) ist CLOSED** — `_ci-python.yml`/`_ci-odoo.yml` sind via [#1437](https://github.com/achimdehnert/platform/pull/1437) retired, gegen `main` (`7ffb8f1e`) verifiziert: beide Dateien weg, `_ci-pypi.yml` (19 Consumer, ADR-226) unangetastet, CI auf main durchgehend grün inkl. `Validate Workflows` auf dem Retire-Commit. **Die „0 Consumer"-Prämisse wurde vor dem Löschen neu gemessen** (63 non-archived Repos, davon 33 privat, alle `.github/workflows/*.yml`, echtes `uses:` von Kommentaren getrennt) — und dabei zwei eigene Fehlläufe korrigiert: `/users/<u>/repos` liefert nur **öffentliche** Repos (16 private fehlten, darunter ein echter `_ci-pypi`-Consumer), und Banner-Kommentare wurden zunächst als Consumer gezählt. **Alt-Prio 4 ([#1414](https://github.com/achimdehnert/platform/issues/1414)) inhaltlich umgedreht:** die vermutete Lint-Schuld existiert **nicht** — mit dem gepinnten `ruff 0.15.4` meldet `ruff check tools/ scripts/` „All checks passed!"; die 402 Fehler kamen vollständig aus einer ungepinnten neueren Ruff-Version. Übrig bleibt nur der Required-Entscheid (neue Prio 2). **PR-Hygiene abgeräumt:** #1418/#1408 waren nur vor dem Ruff-Pin abgezweigt (`update-branch` genügte), #1404/#1401 hatten Merge-Konflikte — bei #1404 wurde die dort vorgeschlagene 8er-Prio-Liste bewusst **nicht** übernommen (führte #1378/#1298/#1167 als offen, alle CLOSED), bei #1401 wurde der generierte ADR-Index regeneriert statt von Hand gemergt. Liste bleibt bei 4 Einträgen, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
> **Reconciliation 2026-07-25 (Session-Start, keine neue Feature-Arbeit):** Die Liste war **zwei Tage stale** — die Vorsession hat sie am 24.07. bewusst nicht angefasst (Parallel-Session-PR [#1404](https://github.com/achimdehnert/platform/pull/1404) berührte die Datei) und die Nacharbeit an die nächste reconcilende Session übergeben; das ist diese. Änderungen, alle gegen die API geprüft, nicht gefolgert: **Alt-Prio 1 ([#1117](https://github.com/achimdehnert/platform/issues/1117)) entfällt — CLOSED** (stale-closed am 24.07.: das trading-hub-Ruleset emittiert `ci / gate` längst, der 404 kam vom Legacy-Endpoint). **Alt-Prio 2 ist zu neuer Prio 1 geschärft:** [#1258](https://github.com/achimdehnert/platform/issues/1258) ist CLOSED, und der ADR-278-Guard-Sync ist seit [#1431](https://github.com/achimdehnert/platform/pull/1431) (MERGED) erledigt — die Restarbeit an [#1423](https://github.com/achimdehnert/platform/issues/1423) ist nur noch das Retiren von `_ci-python.yml`/`_ci-odoo.yml`. **Zwei getrackte Offene aus dem Log vom 24.07. in die Liste gezogen:** [#1416](https://github.com/achimdehnert/platform/issues/1416) (neue Prio 2, gatet den ADR-285-Entscheid) und [#1414](https://github.com/achimdehnert/platform/issues/1414) (neue Prio 4). **Prod-Warnblock nachgemessen** statt fortgeschrieben (`free -m`, 10:28 UTC: Swap unverändert 4095/4095). Liste dadurch 3 → 4 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). **Nicht verifiziert:** die „0 Consumer"-Prämisse für `_ci-python`/`_ci-odoo` wurde aus #1423 übernommen, nicht neu gemessen — sie wird vor dem Löschen erneut geprüft (dieselbe Behauptung war in #1423 schon einmal falsch, siehe dortige Korrektur vom 24.07.).
> **Erledigt 2026-07-24 (diese Session):** **Alt-Prio 1 ([#1298](https://github.com/achimdehnert/platform/issues/1298)), 2 ([#1378](https://github.com/achimdehnert/platform/issues/1378)) und 4 ([#1167](https://github.com/achimdehnert/platform/issues/1167)) sind alle CLOSED** (gegen die API geprüft, nicht gefolgert): #1298 wurde bereits am 2026-07-23 als **Option 4** geschlossen — der im Handover als „lokal nicht durchführbar" markierte Check wurde diese Session via `RemoteTrigger list` **nachgeholt** und bestätigt den Schließungsbefund (0 aktive Cloud-Routinen referenzieren einen `/`-Skill, der genannte Reopen-Kandidat „morning-briefing" existiert gar nicht als Routine); #1378 CLOSED nach Merge von [#1382](https://github.com/achimdehnert/platform/pull/1382) (10:31 UTC); #1167 CLOSED (KONZ-platform-001-Namenskollision via #1410 aufgelöst, KONZ-Nummern-Guard #1413 live). **KONZ-018 W1 (Alt-Prio 5, jetzt Prio 2) vorangebracht:** [#1258](https://github.com/achimdehnert/platform/issues/1258) (platform-Kopie `install-iil-packages` stale ggü. shared-ci) via [#1419](https://github.com/achimdehnert/platform/pull/1419) **MERGED** — platform-Action gelöscht, 3 Call-Sites in `_ci-python.yml` auf `iilgmbh/shared-ci/.github/actions/install-iil-packages@main`, Kontrakt verifiziert identisch (kein Consumer-Break); der Workflow-Ebenen-Rest (consumer-loses Spiegel-Triplett `_ci-python`/`_ci-pypi`/`_ci-odoo`, 63 Repos autoritativ geprüft: 0 externe Consumer) als [#1423](https://github.com/achimdehnert/platform/issues/1423) getrackt. Liste dadurch 6 → 3 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
> **Erledigt 2026-07-23 (Spät, Mail-System-Governance — diese Session):** Aus einem realen `/mailcheck`-Fehler (Domain-Sampling per `--scan-senders` übersah Kunden- + Security-Mail) wurde ein Governance-Bogen. **ADR-283** Rev 1 (pointer-first, [#1392](https://github.com/achimdehnert/platform/pull/1392) MERGED) + Owner-Entscheid **dev-hub-Postgres statt A+/SQLite** ([#1397](https://github.com/achimdehnert/platform/pull/1397) inzwischen MERGED, [#1398](https://github.com/achimdehnert/platform/pull/1398) offen); **MVP-Kern gebaut** ([dev-hub#149](https://github.com/achimdehnert/dev-hub/pull/149), CI grün, pointer-first Modelle + PII-Lint-Test). **ADR-284** (Mail-Intelligence-&-Action-System) nach **2 externen Reviews** auf Rev 1 ([#1401](https://github.com/achimdehnert/platform/pull/1401) offen): nur Phase 1 verbindlich, Coverage-Contract + Triage-Ledger („indexiert ≠ geprüft"), ephemerer purgebarer Index, nl2sql-Sicherheit korrigiert. **Skill-Fix** [#1395](https://github.com/achimdehnert/platform/pull/1395) MERGED (`ai_sparring_by` statt ungültigem `external_sparring_by`) + Live-Regen. **#1298 CLOSED** (Option 4, 6 Cloud-Routinen geprüft, 0 nutzen `/`-Skill). Mailcheck-Lehre als CC-Memory + pgvector-error_pattern. Operativ: Zinser-Draft in IIL-Entwürfen, scheppach-Löschung offen (Owner-Gate), Azure-Frist [#1400](https://github.com/achimdehnert/platform/issues/1400). **Die damals hier vorgeschlagene Prio-Liste (6 → 8, Mail-Strang vorangestellt) ist beim Konflikt-Auflösen bewusst NICHT übernommen worden** — sie führte #1378/#1298/#1167 als offen, die alle inzwischen CLOSED sind. Maßgeblich ist die Liste oben.
> **Erledigt 2026-07-23 (Mittag, ADR-280 §8.1 Kriterium 6 + Accept — diese Session):** **Alt-Prio 1 ist erledigt** — Kriterium 6 in dieser frisch gestarteten Session (Start 11:07 UTC, Stunden nach dem 06:14-Rollout) gemessen und **bestanden**: alle vier Skills schon beim Start im `/`-Menü, `commands`-Lane leer (Menü nur aus der Skills-Lane möglich), `Skill(escalate)`-Footer `source=skills/escalate/SKILL.md`. Damit §8.1 **6/6** → **„A bestanden"**, **ADR-280 `proposed` → `accepted`** (die im ADR §8.1 vorab festgelegte Konsequenz, kein neuer Grundsatzentscheid; kein Fallback D). ADR-Frontmatter + Metadaten + §8.1-Messstand + Verifikationsartefakt in diesem PR aktualisiert. **Accept ≠ Rollout fertig:** Phasen 3a/3b/4/5 bleiben offen (#1287). **Alt-Prio 3 ist erledigt** — [#1381](https://github.com/achimdehnert/platform/pull/1381) **und** [#1382](https://github.com/achimdehnert/platform/pull/1382) sind **MERGED** (10:29/10:31 UTC, gegen die API geprüft); der veraltete „warten auf Review"-Eintrag ist entfernt. **[#1297](https://github.com/achimdehnert/platform/issues/1297) ist CLOSED (completed)** — alle 5 Akzeptanzkriterien gegen den gemergten Code auf `origin/main` verifiziert (Ollama-Default `llm_gate.py:20`, kein externer Fallback `:21`, Abfluss-Zeile `:129`, `iil-extern` Anreicherung aus `profile_policy.py:38`, kein „Internes Dokument"-Untertitel `print_agent.py:961`), Beleg-Tabelle als Schließkommentar. **Neu gebaut (PR [#1390](https://github.com/achimdehnert/platform/pull/1390), offen, CI-grün):** Mail-`--flag`/`--unflag` (alle 3 Postfächer) + `--importance` (nur M365) auf Owner-Wunsch — 8 Tests, reversibel, kein Abfluss; IMAP-Importance bewusst nicht (Header-gebunden). Liste dadurch 7 → 6 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
> **Erledigt 2026-07-23 (Vormittag, Print-Agent-Datenschutz + Mirror-Befund — dieselbe Session):** **Alt-Prio 3 ist erledigt** — [#1377](https://github.com/achimdehnert/platform/pull/1377) **gemergt** (`a4115b2`), nach einem Review mit drei Befunden: der Datenschutz-Test lief in CI nie (Testort in keinem Workflow **und** `importorskip` ohne die Deps), `ollama/` galt unabhängig vom `OLLAMA_HOST` als „lokal", und die ursprünglichen Privacy-Tests waren **vakuum** (`_try_completion` schluckt jede Exception, die Wächter-Attrappe wurde zu einem stillen `None` — ohne Fix liefen sie grün). Alles drei gefixt und mit ohne-Fix-rot-Gegenprobe belegt. Die beiden Restpunkte aus #1297 (Abfluss-Hinweis, `--profile iil-extern`) liegen als [#1381](https://github.com/achimdehnert/platform/pull/1381); [#1297](https://github.com/achimdehnert/platform/issues/1297) bleibt bis zu dessen Merge offen — der PR-Text sagte „Behebt", kein Closing-Keyword, und das war richtig. **Alt-Prio 4 (Review-Stau) durch die neue Prio 3 ersetzt.** Liste bleibt bei 8 Einträgen, lückenlos durchnummeriert.
> **Erledigt 2026-07-23 (früh, ADR-280-Betriebsnachweis — diese Session):** **Alt-Prio 1 entfällt** — [#1366](https://github.com/achimdehnert/platform/pull/1366) und [#1369](https://github.com/achimdehnert/platform/pull/1369) sind **MERGED** (06:05/06:06 UTC, gegen die API geprüft, nicht gefolgert). **Alt-Prio 2 ist entsperrt und zu 5/6 gemessen:** eine Parallel-Session hat `generate.py --kind skills --allow-live` mit Owner-Freigabe ausgeführt (06:14:08 UTC, `manifest.json` → `source_commit=9371148`, 4 Skills, `doctor.py --kind skills` = DRIFT-SCORE 0, keine Lane-Dublette); darauf wurden §8.1 Kriterien 1–5 gemessen und bestanden, Artefakt [`docs/verifications/2026-07-23-adr280-betriebsnachweis.md`](docs/verifications/2026-07-23-adr280-betriebsnachweis.md). Kriterium 6 bleibt als **neue Prio 1** stehen. **Alt-Prio 4 hat jetzt einen PR** ([#1377](https://github.com/achimdehnert/platform/pull/1377), Parallel-Session). Liste dadurch 9 → 8 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). **Methoden-Befund derselben Session:** der Start-Hook `handover_prio_mirror.sh` spiegelt `${CWD}/AGENT_HANDOVER.md` **ohne `fetch` und ohne Behind-Zähler** (Zeilen 30/36) — der lokale Haupt-Tree hing 11 Commits zurück, die gespiegelte Prio war dadurch stumm veraltet (u.a. „12 offene PRs", „Kriterium 5 vorbereitet"). Getrackt als [#1378](https://github.com/achimdehnert/platform/issues/1378).
> **Erledigt 2026-07-22 (Abend-Session — ADR-281 abgeschlossen):** **Alt-Prio 2 (ADR-281 §8.1 Kriterium 5) ist ausgeführt und bestanden** — diese Session fand den am Nachmittag vorbereiteten Symlink beim Start vor, Marker + Argument-Echo korrekt, Werkzeugversion unverändert 2.1.217; §8.1 steht auf 6/6, Testartefakte entfernt, DRIFT-SCORE zurück auf 3. **Alt-Prio 3 („beide ADRs bleiben `proposed`") ist damit für ADR-281 überholt** — der ADR steht auf `accepted` ([#1366](https://github.com/achimdehnert/platform/pull/1366)); ADR-280 bleibt `proposed`. **Alt-Prio 9 entfernt:** [#1289](https://github.com/achimdehnert/platform/issues/1289) ist **CLOSED** (gegen die API geprüft, nicht gefolgert) — die Zeile widersprach ohnehin dem Erledigt-Block vom 21.07. **Alt-Prio 6 neu gemessen:** 12 → **3** offene PRs, 0 nicht-MERGEABLE. Zusätzlich neu: der §8.2-Negativtest wurde vorgezogen, gemessen und die dabei gefundenen zwei Kanten gefixt ([#1369](https://github.com/achimdehnert/platform/pull/1369) schließt [#1368](https://github.com/achimdehnert/platform/issues/1368)). Liste dadurch 11 → 9 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen).
> **Erledigt 2026-07-22 (Session-Start-Reconciliation, keine neue Arbeit):** Zwei „Nächste Schritte"-Zeilen waren **stale** und sind entfernt — beide gegen die API geprüft, nicht gefolgert. (a) Alt-Prio 1 führte [#1293](https://github.com/achimdehnert/platform/pull/1293) als `REVIEW_REQUIRED`; der PR ist **MERGED** (2026-07-22 14:35 UTC, Commit `cbc7204` auf `main`) → [#1287](https://github.com/achimdehnert/platform/issues/1287) ist PR-seitig abgeschlossen. (b) Alt-Prio 4 („`doctor.py` meldet dangling Symlink nicht, §8.2-Negativtest würde durchfallen") ist behoben durch [#1335](https://github.com/achimdehnert/platform/pull/1335) **MERGED** (09:59 UTC), Issue [#1332](https://github.com/achimdehnert/platform/issues/1332) **CLOSED**. Liste dadurch 13 → 11 Einträge, lückenlos durchnummeriert (Maschinen-Vertrag: `claude-next-sync` matcht nur ganze Zahlen). Restliche Zeilen inhaltlich unverändert bis auf Prio 6 (PR-Zahl neu gemessen) und Prio 2 (Kriterium 5 braucht Vorbereitung).
> **Erledigt 2026-07-21 (Vormittag, Aufräum- + Infra-Session — Parallel-Session, nicht diese):** **Prio „lügender Index" abgeschlossen** ([#1288](https://github.com/achimdehnert/platform/pull/1288) GEMERGT) — ADR-158 `implementation_status` von `implemented` auf `partial` korrigiert (3 tote Evidence-Pfade unter `packages/docs-agent/`, seit 2026-04-23 in `_ARCHIVED/`), ADR-072-Rollout-Tabelle auf belegten Stand zurückgesetzt. **Bewusst nicht nachgemessen** (wäre Scope-Eskalation in 4 App-Repos) → ungemessene Repos tragen jetzt explizit `❔ nicht nachgemessen`. Gate-Lücke getrackt ([#1289](https://github.com/achimdehnert/platform/issues/1289)) · **Branch-Hygiene: 442 lokale Branches gelöscht (512 → 47)**, Restore-Manifest `~/shared/branch-cleanup-platform-2026-07-21.txt`. **Lehre:** der erste Durchlauf stufte 51 gemergte Branches falsch als „lokal voraus" ein — nicht wegen Divergenz, sondern weil der gemergte `headRefOid` lokal fehlte und der Ancestor-Check scheiterte. Nach `git fetch origin <oid>` waren alle 51 sauber entscheidbar; echte Divergenz lag bei 7, nicht 56.
> **Erledigt 2026-07-21 (Infra-Entscheid GPU, kein Code — Parallel-Session):** Recherche + eigene Messung → **kein GPU-Server gemietet**. illustration-hub läuft auf der vorhandenen RTX 4090, meiki-Pilot + Dokumentenlast auf CPU des Dev-Servers. Gemessen auf 88.99.38.75 (16 Kerne, geteilte Last), Print-Agent-Prompt: `qwen2.5:3b` 7,3 tok/s / 18 s · `7b` 3,6 tok/s / 51 s · `14b` 1,1 tok/s / 153 s — alle valides JSON. Gegenrechnung: Hetzner GEX44 hat **20 GB** (weniger als die 4090; Primärquelle, keine Mindestlaufzeit, FSN1), VRAM-gleicher Scaleway L4 kostet 575 €/Mon netto bei ~⅓ Speicherbandbreite. **Nicht belegt geblieben:** GEX44-Monatspreis (Seite rendert clientseitig), Stromkosten, Preisknick Consumer↔Datacenter — 14 von 25 Recherche-Claims adversarial verworfen. **Auflage für meiki:** gegen austauschbaren OpenAI-kompatiblen Endpunkt bauen, sonst wird der spätere Umzug ins LRA-RZ zum Umbau.
>
> **meiki-Datenklassifikation (Owner-Präzisierung 2026-07-21) — trägt den Entscheid oben:** Der meiki-**Pilot** auf IIL-Infrastruktur arbeitet mit **synthetischen** Daten. Echte Daten erst ab dem **Live-Prod-Testlauf**, und dieser Übergang wird **ausdrücklich kommuniziert**. **Entscheidungsregel: solange keine solche Mitteilung vorliegt, sind meiki-Daten synthetisch** — Abwesenheit einer Mitteilung heißt *synthetisch*, nicht *unklar*. Echte Bürgerdaten liegen im Zielzustand im **LRA-Rechenzentrum**, nicht bei uns. Daraus folgt für den Pilotzeitraum: kein AVV, keine Auftragsverarbeitung, freie Anbieterwahl. Ab dem kommunizierten Umschaltpunkt kippt das vollständig (Backup-Pflicht, AVV-Prüfung, Souveränitäts-Auflagen). Korrigiert die frühere Pauschal-Einordnung „meiki-* hält Prod-Daten" (Stand 06-11), die für den Pilotzeitraum zu streng war; `writing-hub`/`risk-hub` sind davon nicht berührt.
> **Erledigt 2026-07-21 (Skill-Lanes, diese Session):** [#1290](https://github.com/achimdehnert/platform/pull/1290) GEMERGT (Phase 1: 3 Piloten nach `skills/`, Gate + CI-Trigger auf beide Lanes, 5 Tests) · [#1291](https://github.com/achimdehnert/platform/pull/1291) GEMERGT (ADR-280 Rev 1) · [#1292](https://github.com/achimdehnert/platform/pull/1292) GEMERGT (`/adr`-Skill: `gen_adr_index.py` als Pflichtschritt + Abschluss-Checkliste + Anti-Patterns) · [#1118](https://github.com/achimdehnert/platform/pull/1118) GESCHLOSSEN (superseded). **Lehre:** meine tragende Prämisse („`$ARGUMENTS` entfällt unter Skills") war **falsch** — geprüft gegen `claude --version` 2.1.216 + Doku 2026-07-21; zwei externe Zweitmeinungen fanden es, beide empfahlen „überarbeiten". Verifikationsstand mit Versionspin ist seitdem Pflichtblock in ADR-280/281.
> **Erledigt 2026-07-21 (Parallel-Session, nicht diese):** [#1284](https://github.com/achimdehnert/platform/pull/1284) GEMERGT (Handover-Stand 07-20/21) · [#1013](https://github.com/achimdehnert/platform/pull/1013) + [#954](https://github.com/achimdehnert/platform/pull/954) GEMERGT.
> **Erledigt 2026-07-21 (Abend, ADR-Evidence-Strang — eigene Session, parallel zur Nachmittags-Session):** **PR-Stau der 5 DIRTY-PRs aufgelöst** — [#986](https://github.com/achimdehnert/platform/pull/986) / [#1005](https://github.com/achimdehnert/platform/pull/1005) / [#1007](https://github.com/achimdehnert/platform/pull/1007) rebased (alle grün), [#892](https://github.com/achimdehnert/platform/pull/892) + [#893](https://github.com/achimdehnert/platform/pull/893) als von `main` überholt geschlossen (Commit `3d71952` hatte beides bereits umgesetzt; #893 hätte eine scharfe Gate-Stufe zurückgedreht). Funde beim Rebase: Archiv-Namenskollision (zwei Generationen `generate_project_facts.py`), `.windsurf/workflows/onboarding-new-repo.md` via ADR-280 gelöscht. · **ADR-234 §11.3 präzisiert** ([#1007](https://github.com/achimdehnert/platform/pull/1007)): der „Dual-Generator"-Befund ist output-seitig widerlegt — die beiden Skripte schreiben verschiedene Artefakte, A3 war nie eine Deduplizierung; Beschluss bleibt, Begründung korrigiert. · **77 project-facts-Dateien archiviert** ([#1306](https://github.com/achimdehnert/platform/pull/1306), [#1304](https://github.com/achimdehnert/platform/issues/1304)) — 0 Leser verifiziert; der ursprünglich geplante Header-Sweep wäre **falsch** gewesen (anderes Ziel, anderes Format). · **#1289 erledigt** → Evidence-Pfad-Check [#1312](https://github.com/achimdehnert/platform/pull/1312) (SUGGEST, 23 Tests) + Bereinigung [#1318](https://github.com/achimdehnert/platform/pull/1318) ([#1311](https://github.com/achimdehnert/platform/issues/1311)): **16 Findings → 0 ohne einen Ignore-Eintrag**, 10 ADRs; 7 FPs verifiziert ausgeschlossen (`orchestrator_mcp` = Teilspiegel, `packages/django-tenancy` liegt in **risk-hub**, ADR-246 in **iil-pet-portal**). · **noop-Check** [#1322](https://github.com/achimdehnert/platform/pull/1322) aus eigenem Fehler: `ruff format tools/` + `git add -A` schleuste 95 Fremddateien in #1312 (repariert, 4 Dateien). **Lehren:** (a) ein Frontmatter-Parser-Bug ließ den Evidence-Check am eigenen Anlassfall ADR-158 vorbeilaufen — nur die Tests fanden es; (b) `git diff --name-only -w` wertet `-w` **nicht** aus (Blob-Hash-Vergleich), ein darauf gebauter Detektor meldet falsch-grün; (c) „alle Packages jetzt in eigenen Repos" (Commit `2cc7289`) stimmt nicht — 6 von 7 leben nur als PyPI-Dist. **Offen:** alle 7 PRs BLOCKED = warten auf 2.-Owner-Review; Gating-Promotion beider Checks erst nach Merge von #1318.
> **Erledigt 2026-07-21 (Nachmittag, Tools-Strang-Fortsetzung + KONZ-027 + Doppel-Retro, diese Session):** [mcp-hub#180](https://github.com/achimdehnert/mcp-hub/pull/180) GEMERGT (admin-Bypass, auditiert — verify-adr156 nicht mehr falsch-grün) · **KONZ-027 Handover-Fragmente** ([#1301](https://github.com/achimdehnert/platform/pull/1301) GEMERGT, `pipeline_status: pilot`) — 2 externe Cross-Provider-Reviews fanden unabhängig 3 fatale Design-Fehler → R1-Revision; **A/B-Pilot [#1302](https://github.com/achimdehnert/platform/issues/1302): merge=union (empirisch getestet, ~5 Z.) vs. Fragment-Maschinerie** (`model:sonnet-5`) · Retro-Follow-ups [#1309](https://github.com/achimdehnert/platform/pull/1309) GEMERGT (B1-Docstring-Overclaim, ADR-156↔#181-Link) · **Haupt-Retro [#1308](https://github.com/achimdehnert/platform/pull/1308) GEMERGT** (full, 8/11 survived) + **Increment-Retro [#1313](https://github.com/achimdehnert/platform/pull/1313)** (lean) + Skill-Schärfung [#1316](https://github.com/achimdehnert/platform/pull/1316) (stale-clone: nach fetch aus dem Ref lesen). **Offen (execution-ready, `model:sonnet-5`):** [#1302](https://github.com/achimdehnert/platform/issues/1302) A/B-Pilot · [#1310](https://github.com/achimdehnert/platform/issues/1310) verify-adr156-CI-Gate. **Gate-pflichtig rezidiv:** parallel-session-pr-collision (×3, KONZ-027-Pilot ist der Fix), stale-local-clone (×8).
> **Erledigt 2026-07-21 (Abend, #1302/#1310 in Umsetzung — an Sonnet delegiert):** [#1302](https://github.com/achimdehnert/platform/issues/1302) **Arm A gebaut** ([#1319](https://github.com/achimdehnert/platform/pull/1319), offen): `merge=union` auf AGENT_HANDOVER.md + append-only-Konvention; Pilot-Check 1 (server-side Squash ehrt merge=union?) offen bis echter Parallel-PR. · [#1310](https://github.com/achimdehnert/platform/issues/1310) **CI-Gate gebaut** ([#1320](https://github.com/achimdehnert/platform/pull/1320), offen): `workflow_tool_ref_check.py` — Golden-Test verifiziert (Verneinung→FAIL, Aufruf-Form→PASS). · [mcp-hub#182](https://github.com/achimdehnert/mcp-hub/pull/182) (offen, **braucht --admin**): 9 `.py`-Checks in verify-adr156 verschärft. **Nicht im Repo (DSGVO, lokal ~/shared/risk-hub/Feha/):** Feha↔MVZ-DLG TOM-DSB-Beratung — ausfüllbares AcroForm-PDF (188 Felder) + Begleitnotizen + Louzri-Antwort-Entwurf; Kern: TOM-Fragebogen ≠ C5 (separate Instrumente).
> **Erledigt 2026-07-20/21 (Tools-Strang + Mail, 2 Parallel-Sessions):** [#1278](https://github.com/achimdehnert/platform/pull/1278) (estimate_job-Fehldiagnose) · [#1279](https://github.com/achimdehnert/platform/pull/1279) (break-glass-meter, KONZ-004) · [#1280](https://github.com/achimdehnert/platform/pull/1280) (A1 Memory-Key + C1 Lease-Sicht) · [mcp-hub#181](https://github.com/achimdehnert/mcp-hub/issues/181) (deploy_check-Defekt getrackt) · Mail-Postfach strukturiert + Ollama-on-dev + Dienst-H falsifiziert ([#1281](https://github.com/achimdehnert/platform/issues/1281) offen).
> **Erledigt 2026-07-20:** [#1275](https://github.com/achimdehnert/platform/pull/1275) GEMERGT (Ausführungstreue-Umsetzung, KONZ-001+004 Kriterium→Status-Tabellen) · [#1115](https://github.com/achimdehnert/platform/issues/1115) GESCHLOSSEN (usage-sweep: Labels behalten, 36 Skills zurückgebaut via #1257, 3 sunset-reife Skills source- **und** dist-seitig entfernt; Kill-Kriterium *nicht* erfüllt → Sweep läuft weiter) · [#1271](https://github.com/achimdehnert/platform/issues/1271) GESCHLOSSEN (cc-skill-dist DRIFT-SCORE 44→0; alle 35 Orphans durch den einen Rückbau-Commit `cfa9c0f` erklärt, Zweitquellen-Hypothese falsifiziert). **Methodik-Auflage nächster Sweep:** „keine kanonische Source" ist **kein** Tot-Signal — trifft auch frisch zurückgebaute Skills; Status steckt im löschenden Commit (`doctor.py --kind commands` + Orphan↔Commit-Diff vor Teardown).
> **Erledigt 2026-07-19:** Owner-Block #1094 komplett + geschlossen (7/7 OIDC-Bindungen, 3 Pakete live, 4 Alt-Dubletten geyankt, 2. Owner) · ADR-278 accepted (#1266) · codeguard/ingest OIDC (#1267) · django-commons#12 + learnfw#9 Auth-Fixes · shared-ci publish-auth-guard v1.0.13 · #1265 zu, #1268 (Portfolio) ausgelagert · Handover-PR #1171 (stale) geschlossen · **Guard Block-Flip scharf** (shared-ci#33) + v1.0.14 fleet-weit gebumpt (promptfw#32/outlinefw#19) → ADR-278-Enforcement komplett.
> **Erledigt 2026-07-19 (Abend-Session):** #1167-Umsetzungsschritt geliefert (#1275: KONZ-001 + KONZ-004 Kriterium→Status-Tabellen; KONZ-016/018 begründet ausgelassen) · **#1276 GEMERGT** — systemischer ADR-Frontmatter-Blocker (6 ADRs, deprecated Keys) fleet-weit gefixt, `validate` 225/225 · ADR-272-Nummernkollision gelöst (#1077 → ADR-279 umnummeriert, #1086 behält 272) · **Review-Stau von 6 auf 0 rote PRs** (#1027/#1026 gemergt; #1112/#1231/#1141/#1086/#1077/#1225 grün gezogen). **Lehre:** „stale-Index" war bei #1231/#1141 die *falsche* Erst-Diagnose — echter Root-Cause war der repo-weite Schema-Verstoß; ein Log-Blob (base64-HTML) verdeckte bei #1225 einen simplen transienten 503.
> **Erledigt 2026-07-19 (Session-Start-Folgesession):** #1268 geschlossen (Portfolio: alle 6 Pakete behalten) · #1158 geschlossen (`secrets:inherit`: coach-hub bereits auf origin/main gefixt, risk-hub **False Positive** — same-org `iilgmbh` + keine private git-Dep) · #1115 Sweep-Entscheid (Labels behalten; Skill-„tot"-Signal via cc-skill-dist-Drift widerlegt → #1271) · #1167 Stichproben-Audit fortgesetzt (~8 Fix-Kandidaten). **Lehre:** #1 (Guard) + coach-hub-Teil von #2 waren bereits erledigt — nur sichtbar durch konsequente origin/main- statt lokale-Klon-Prüfung.
> **Erledigt 2026-07-18 (Session-Start-Reconciliation, keine neue Arbeit):** Orchestrator-MCP wieder funktional — „Invalid Bearer Token" nicht mehr reproduzierbar, live verifiziert per 3 erfolgreichen Tool-Calls (`agent_memory_search` + `check_recurring_errors` + Outline-Search) am 2026-07-18; Ursache des Wieder-Funktionierens unbekannt (nicht untersucht) · Haupt-Retro [#1162](https://github.com/achimdehnert/platform/pull/1162) ist MERGED + APPROVED (war als „offen" geführt, Handover war stale).
> **Erledigt 2026-07-15:** cad-hub#42 (war schon vor Session-Start gemergt, Handover war stale) · trading-hub#150 · coach-hub#40 · ADR-270-Vorbedingung (#1152) · Increment-Retro (#1165) · session-start-Checkliste-Nachbesserung (#1166).
> **Erledigt 2026-07-13 (nachgezogen, war nur in PR #1122 unmerged dokumentiert):** KONZ-017 W1 sync-drift-meter #998 (#1009 gemergt) · usage_sweep.py (#1116 gemergt) · trading-hub Deploy-403 (#1070 zu) · PyPI-OIDC-Readiness codeguard/ingest (#1118 gemergt) · trading-hub PR #130 (README-Fix, inzwischen gemergt).

> **Ältere Stände** (2026-07-10 Mail-Skill, 2026-06-20 F4/Wave-2 usw.) → [`AGENT_HANDOVER_ARCHIVE.md`](AGENT_HANDOVER_ARCHIVE.md).

## 0. Aktuelle Prioritäten (2026-07-02 — verifiziert via API/Fleet-Scan)

| Prio | Task | Tier |
|---|---|---|
| 1 | **ADR-242 Wave 3** — Tracking **[#811](https://github.com/achimdehnert/platform/issues/811)**. **Realer Stand 2026-07-10 (gegen #811+Retro abgeglichen, weiter als der Issue selbst zeigt):** Phase 1 (learn-hub, recruiting-hub, travel-beat) komplett, gemergt UND live Wave-3-geschützt. Zusätzlich 3 Repos außerhalb der ursprünglichen Worklist live geschützt (weltenhub, illustration-hub, research-hub) — **nachträglich offiziell in #811 aufgenommen** (Entscheid Achim 07-10). Phase 2 (~23 Standalone-Libs): 13/23 verifiziert+gemergt; Rest-Kohorte in **[#987](https://github.com/achimdehnert/platform/issues/987)** (Task A: gaeb-toolkit/riskfw/weltenfw nur PR-Head-Verify; Task B: outlinefw/promptfw gated auf shared-ci#20); 5 strukturell exkludiert. Formales Phase-3-Apply-Artefakt (`wave3-repos.json` + `apply-branch-protection.yml wave=3` + Negativ-Test + Meter) **existiert noch nicht** — die 6 Live-Rulesets liefen ad-hoc außerhalb dieses Prozesses. | `[Sonnet, via #811]` |
| 2 | **Deploy-Health** (separates Programm, **nie autonom** — Owner/Infra). **Re-Check 2026-07-02: weitgehend geheilt** — onboarding-hub grün (seit 06-24), 137-hub grün (seit 06-21), weltenhub grün (07-01, cancelled=Concurrency benign); dms-hub weiter `cancelled` (benign, letzte Runs 06-09). **tax-hub „Issue Triage" 3× failure (07-01/02)** — Root-Cause `Input required and not supplied: github-token` (Repo hat 0 Secrets, `PROJECT_PAT` fehlt; risk-/coach-hub identisches Muster + PAT = grün). **Fix-PR iilgmbh/tax-hub#20 offen** (Fallback `PROJECT_PAT \|\| github.token`; Self-Approval-Block → wartet auf Owner-Merge; bei Merge `[skip ci]` beachten — deploy.yml feuert auf push:main ohne paths-Filter). Alternative: PROJECT_PAT als Secret setzen (Owner). | `[du/Owner]` |

> **Fortschritt 2026-07-03 (Session 54a76c):** Prio 1 (Wave 3): Scope +„Registry-Konsistenz required machen" (#811-Kommentar — Check ist heute NICHT required, nur `guardian`; Realfall #883/#884/#885 mergten rot). Prio 2 (Deploy-Health): **ADR-264 accepted** = strategischer Rahmen steht; travel-beat-Deploy wieder grün (#57); mcp-hub `/mcp` live; Rest-Item = shared-ci#17-Rollout.
>
> **Fortschritt 2026-07-06 (ERLEDIGT):** **Prio 1 — Wave-3 Phase 1 KOMPLETT** (alle 3 gemergt, `ci / gate` real grün verifiziert): learn-hub#25 (`name:"CI"`-Override raus) · recruiting-hub#13 + travel-beat#62 (**Option A1 = additiver `ci`-Job neben bestehender bespoke Test-CI**, kein Coverage-Verlust — der ursprüngliche #811-Befund „KEIN PR-getriggertes ci.yml" war für beide veraltet). recruiting#10/travel#55/learn#23 auto-closed. **Nächster Wave-3-Schritt = Phase 2** (~23 Standalone-Libs, Worklist in #811), dann Apply. **Prio 2 — Deploy-Health geheilt + live:** billing-hub 403 = **Package-`Manage Actions access` fehlte dem Repo** (NICHT Workflow — identische deploy.yml wie cad-hub, das grün pushte); Owner-Fix im Package-Setting → Rerun grün, `billing.iil.pet/healthz` 200. cad-hub = transienter GHA-Cache-Timeout → Rerun grün, `nl2cad.de/healthz` 200. **Neu: Runbook `docs/runbooks/ghcr-403-push-actions-access.md` (#967) + CC-Memory `reference_ghcr_403_push_package_actions_access`.**

> **Fortschritt 2026-07-08 (unmerged geblieben, PR #985, jetzt konsolidiert):** Phase 2 zu 13/23 verifiziert+gemergt; shared-ci#20-Blocker gefunden; Rest-Kohorte in #987 aufgeteilt (Task A/B). Details: s. Aktueller Stand.
>
> **Fortschritt 2026-07-09/10 (ABGEGLICHEN gegen #811 + Retro, 2026-07-10):** Wave-3-Ruleset live auf 6 Repos (nicht 9 — Memory-Zahl war falsch, korrigiert gegen Retro-Ground-Truth), davon 3 außerhalb der #811-Worklist (weltenhub/illustration-hub/research-hub, jetzt nachträglich aufgenommen) + Live-Incident selbst behoben; ADR-270 accepted. **Formales Phase-3-Apply-Artefakt fehlt weiterhin.** Details: s. Aktueller Stand + #811-Kommentar.
>
> **Fortschritt 2026-07-10 (NEU, offen):** weltenhub-Redis-Incident gelöst (s. Aktueller Stand). Drei Folge-Items offen, alle Human-Decision/Freigabe, keine autonome Ausführung: (1) `ausschreibungs-hub-staging` authentik-Provider/-Application vorbereitet (client_id/signing_key/scopes/redirect geklärt gegen risk-hub-Referenz-Pattern), Freigabe-Block gestellt, Session endete vor Bestätigung — nächste Session kann direkt ausführen, kein erneutes Research nötig. (2) `staging-demo.schutztat.de` DNS-Record (→178.104.184.168) — Entscheid offen. (3) "platform"-Governance-DB (`PLATFORM_DB_HOST=bfagent_db`, degradiert aifw-AI-Features) — Entscheid offen, braucht erst Konsumenten-Inventar. (4) KONZ-platform-015 liegt lokal in `platform` (untracked, main geschützt) — braucht Worktree+PR zum Mergen, dann User-Accept-Entscheid für die Empfehlungen REC-1..REC-7. (5) **Deploy-Health-Scan (session-start) fand 3 neue `failure`** auf coach-hub/trading-hub/pptx-hub, nicht triagiert — s. Aktueller Stand.

> **PR-Hygiene (erledigt 2026-07-02, Freigabe Achim):** #753 + #746 geschlossen (Duplikate von gemergtem #808) · **#760 gemergt** (Registry iil-adrfw/codeguard — Registry-Lücke zu) · **#759 gemergt** (gen_adr_index.py; Rebase-Konflikt in INDEX.md durch Generator-Lauf gelöst, 206 aktive + 48 archivierte ADRs indiziert).

> **✅ Retired/erledigt (2026-06-24, hart verifiziert — billigster Check gemacht):**
> - **F4 CI-grün** als Code-CI-Programm GESCHLOSSEN (Fleet-Scan: 0 Lint/Test/Coverage-Rot; alle Roten = Deploy-Stage). **Kein Sonnet-Material mehr** — nicht erneut als Sonnet-Queue listen.
> - **coach-hub #28** gemergt 2026-06-15 (+ Dep-Fix #31, PAT/Org-Transfer). Strang zu.
> - **ADR-242 Wave 1+2** live (11 Repos geschützt, `ci / gate`).
> - **F1 `.windsurf`-Nachzügler** gesweept (lastwar-bot, iil-voice-agent) — F1 ist KEIN Einmal-Endzustand, periodisch `tools/f1-windsurf-sweep.sh` (dry-run) gegen die API laufen lassen.

**✅ Erledigt (2026-06-10):** weltenhub#16 gemergt verifiziert → **ref-sweep 12/12 komplett** · **research-hub#6** gemergt (2 teardown-Bugs gefixt: async-ORM-Connection-Leak + flush-CASCADE vs django_tenancy-FK).

**✅ Erledigt (2026-06-09):** wedding-hub#19 · onboarding-hub#2 · weltenhub pytest-Fixes · F4-Fixes: weltenhub 5, wedding-hub 3, onboarding-hub 1 · **shared-ci `v1.0.2` + `v1.0.3`** · **mcp-hub#106** + **trading-hub#14** · 11/12 ref-sweep-PRs.

**✅ Erledigt (2026-06-08):** F4-acute (alle 6 `ai-assignable`-Issues closed) · ADR-212 Phase-1 (dev-hub#81 merged) · F1 .windsurf-Untrack vollständig (0 `.windsurf`-Files auf origin/main).

**KONZ-002 Enterprise-Konsolidierung:** Kill-Gate **(c) Portabilität ✅ erfüllt** (Feuerübung Runde 1, 2026-06-03; §15 D1-konform). Offen nur **extern**: (a) Kostenbestätigung + (b) Government-Sign-off, Frist **2026-08-15** — User-getrieben, keine Coding-Prio. Richtung ALT-D, Umsetzung gegated.

**CC-Skill-Dist** (platform): Drift-Score live prüfen — `python3 tools/cc-skill-dist/doctor.py` (Zahl driftet mit jedem neuen/geänderten Skill, hier nicht einfrieren)

---

## 1. MCP-Server & Tool-Calls

**Claude Code (aktuell, `mcp__<server>__<tool>` Format) — wichtigste Tool-Calls:**
- GitHub: `mcp__github__create_issue`, `mcp__github__get_pull_request`
- Memory: `mcp__orchestrator__agent_memory_context(task_description, top_k=5)`
- Deploy-Status: `mcp__orchestrator__deploy_check(action="health", repo=...)`
- Browser: `mcp__playwright__browser_navigate`, `mcp__playwright__browser_snapshot`

**Server-Übersicht (7):**

| Server | Zweck |
|--------|-------|
| **deployment-mcp** | SSH, Docker, Compose, Git, DB, DNS, SSL, Nginx, CI/CD |
| **github** | Issues, PRs, Repos, Branches, Files, Reviews, Search |
| **orchestrator** | Memory (pgvector), Task-Analyse, Agent-Team, Tests, Lint |
| **outline-knowledge** | Wiki: Runbooks, Konzepte, Lessons, ADR-Suche |
| **paperless-docs** | Dokumente, Rechnungen, Archive |
| **platform-context** | Architektur-Regeln, ADR-Compliance, Banned Patterns |
| **playwright** | Browser-Automation, UI-Tests, Screenshots, Network |

### Windsurf-Legacy (kein Coding mehr, ADR-230)

Windsurf-Agents nutzten die o. g. Server über numerische Prefixe (`mcp0_`–`mcp6_` in
derselben Reihenfolge wie oben). Seit ADR-230 wird Windsurf **nicht mehr zum Coden**
eingesetzt (nur ADR-Review-Subset) — die Prefix-Tabelle ist nur noch für das Lesen
alter Sessions/Logs relevant, kein aktives Interface mehr.

---

## 2. Hetzner Infrastructure

| Rolle | IP | User |
|-------|-----|------|
| **Prod-Server** | `88.198.191.108` | `root` (via SSH-Key) |
| **Dev-Server (WSL)** | `localhost` | `devuser` |

**Kritische Regeln:**
- `devuser` hat **KEIN sudo-Passwort** → System-Pakete: `ssh root@localhost "apt-get install -y <pkg>"`
- PROD: nur read-only via MCP — Deploys über `scripts/ship.sh` oder CI/CD
- **NIEMALS** `ping` für Server-Check — Hetzner blockiert ICMP. TCP-Check stattdessen.

**Secrets:**
- Lokal: `~/.secrets/` (einzige Location seit 2026-05-30 — `~/shared/secrets/` konsolidiert + leer)
- Server: `/opt/shared-secrets/api-keys.env` (chmod 600, root-only)
- Repo-spezifisch: `.env.prod` (nie in Git)

---

## 3. Deploy Targets (Prod — 88.198.191.108)

| Repo | Domain | Health |
|------|--------|--------|
| `risk-hub` | schutztat.de | https://schutztat.de/healthz/ |
| `coach-hub` | kiohnerisiko.de | https://kiohnerisiko.de/healthz/ |
| `billing-hub` | billing.iil.pet | https://billing.iil.pet/healthz/ |
| `travel-beat` | travel-beat.iil.pet | https://travel-beat.iil.pet/healthz/ |
| `weltenhub` | weltenforger.com | https://weltenforger.com/healthz/ |
| `trading-hub` | trading-hub.iil.pet | https://trading-hub.iil.pet/healthz/ |
| `cad-hub` | nl2cad.de | https://nl2cad.de/healthz/ |
| `pptx-hub` | prezimo.com | https://prezimo.com/healthz/ |
| `ausschreibungs-hub` | bieterpilot.de | https://bieterpilot.de/healthz/ |
| `dms-hub` | dms.iil.pet | https://dms.iil.pet/healthz/ |
| `wedding-hub` | wedding-hub.iil.pet | https://wedding-hub.iil.pet/healthz/ |

**Deploy-Befehl:** `bash ~/github/platform/scripts/ship.sh <repo>`
**Health-Check:** `mcp2_deploy_check(action="health", repo="<repo>")`

---

## 4. Master Repo Identifier

**Alle Repos in einer Registry** (Anzahl live: `python3 -c "import yaml; print(len(yaml.safe_load(open('registry/canonical.yaml'))['repos']))"`):

```bash
# project-facts.md für alle Repos generieren (nur fehlende)
python3 ~/github/platform/scripts/gen_project_facts.py

# Alle neu generieren
python3 ~/github/platform/scripts/gen_project_facts.py --force

# Einzelnes Repo
python3 ~/github/platform/scripts/gen_project_facts.py risk-hub
```

- Registry: `platform/scripts/repo-registry.yaml`
- Output: `<repo>/.windsurf/rules/project-facts.md` (trigger: always_on)
- Läuft automatisch bei `/session-start` (Step 0.3b) und `/session-ende` (Phase 3.2)

---

## 5. CC-Skills & Windsurf Rules

**CC-Skills (primär, ADR-230):** Quelle `platform/.windsurf/workflows/` → verteilt nach `~/.claude/commands/` via `cc-skill-dist`:
```bash
python3 ~/github/platform/tools/cc-skill-dist/generate.py --target ~/.claude/commands --allow-live
python3 ~/github/platform/tools/cc-skill-dist/doctor.py   # Drift-Check
```

**Windsurf Rules** (nur ADR/Review-Subset, kein Coding mehr seit ADR-230):
- Quelle: `platform/.windsurf/rules/` + `platform/.windsurf/workflows/` (tool_targets: windsurf-review)
- Verteilen: `python3 tools/cc-skill-dist/windsurf-subset.py`

**project-facts.md** (repo-spezifisch, generiert):
```bash
python3 ~/github/platform/scripts/gen_project_facts.py          # nur fehlende
python3 ~/github/platform/scripts/gen_project_facts.py --force  # alle
```

---

## 6. GitHub

**Account:** `achimdehnert`
**MCP:** `mcp1_*` für alle GitHub-Operationen
**Reusable Workflows:** SSoT ist `iilgmbh/shared-ci/.github/workflows/` (auf Tags gepinnt).
platform hält nur noch `_ci-pypi.yml` selbst (19 Consumer, ADR-226); `_ci-python.yml`/`_ci-odoo.yml`
sind retired (#1423).

**Repo-Kategorien:**
- **Django Hubs** (21): risk-hub, coach-hub, billing-hub, cad-hub, trading-hub, pptx-hub, travel-beat, weltenhub, wedding-hub, recruiting-hub, dms-hub, ausschreibungs-hub, illustration-hub, research-hub, writing-hub, learn-hub, dev-hub, odoo-hub, 137-hub, bfagent, tax-hub
- **Python Libraries** (14): aifw, authoringfw, promptfw, illustration-fw, learnfw, weltenfw, outlinefw, researchfw, testkit, iil-reflex, iil-ingest, iil-enrichment, iil-fieldprefill, nl2cad
- **Infra** (5): platform, mcp-hub, infra-deploy, iil-relaunch, lastwar-bot

(Diese Kategorien sind kein vollständiges Abbild von `registry/canonical.yaml` — Gesamtzahl
live siehe oben unter §4; bei Abweichung ist die Registry maßgeblich, nicht diese Liste.)

---

## 7. pgvector Memory (Orchestrator)

| Parameter | Wert |
|-----------|------|
| **Container** | `mcp_hub_db` (Image: `pgvector/pgvector:pg16`) |
| **Läuft auf** | Prod-Server `88.198.191.108` |
| **Port auf Prod** | `127.0.0.1:15435` (Host-Binding des Containers) |
| **Lokaler Zugriff** | `localhost:15435` via SSH-Tunnel |
| **systemd Service** | `ssh-tunnel-postgres` (dev desktop, User `adehnert`) |

```bash
# Status prüfen
ss -tlnp | grep 15435
systemctl is-active ssh-tunnel-postgres

# Manuell starten (ohne sudo)
ssh -N -L 15435:localhost:15435 -i ~/.ssh/id_ed25519 root@88.198.191.108 &

# Via systemd (empfohlen — Autostart bei Neustart)
sudo systemctl start ssh-tunnel-postgres
```

- **Kein Fallback auf Cascade Memory** — pgvector MUSS laufen
- Tunnel-Ziel: `remote:localhost:15435` (nicht `:5432` — der Container bindet auf 15435)
