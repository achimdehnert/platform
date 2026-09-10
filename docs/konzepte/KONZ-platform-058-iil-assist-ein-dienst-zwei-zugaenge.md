---
concept_id: KONZ-platform-058
title: iil-assist — ein Dienst, zwei Zugänge (App und Chat)
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: ["platform#3011"]
adr_threshold: ADR nach den ersten zwei MVPs auf Staging — Evidenz statt Vorab-Entscheid; bis dahin trägt dieses KONZ die Entscheide D1–D5
review_by: 2026-10-10
kill_criteria: "Wenn bis 2026-10-24 weniger als zwei der fünf MVPs auf Staging über beide Zugänge dieselbe Antwort liefern (Test je Zugang grün), ODER der Owner die Architektur D1–D3 verwirft, ODER der Bau eines MVPs mehr als fünf PRs im Ziel-Repo braucht, wird das Programm gestoppt und die Zustandsdatei auf phase: bilanz gesetzt."
evidence_manifest:
  - {claim_id: C1, source_path: docs/messungen/3011-dienst-inventar.md, commit_or_pr: "platform#3012", opened_in_session: true}
  - {claim_id: C2, source_path: _ARCHIVED/packages/chat-agent, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C3, source_path: chat-hub/deploy/chat_lotse.py, commit_or_pr: "iilgmbh/chat-hub#48", opened_in_session: true}
  - {claim_id: C4, source_path: meiki-hub/docs/adr/ADR-044-paket-topologie-und-datenhaltung.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C5, source_path: mcp-hub/SERVERS.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C6, source_path: tools/registry_api.py, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C7, source_path: "iilgmbh/chat-hub#77", commit_or_pr: "iilgmbh/chat-hub#77", opened_in_session: true}
  - {claim_id: C8, source_path: docs/konzepte/KONZ-platform-025-lotsen-charta.md, commit_or_pr: main, opened_in_session: false}
  - {claim_id: C9, source_path: docs/adr/ADR-101-mcp-plattform-konzept.md, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C10, source_path: infra/ports.yaml, commit_or_pr: main, opened_in_session: true}
  - {claim_id: C11, source_path: iil-django-commons/pyproject.toml, commit_or_pr: main, opened_in_session: true}
created: 2026-09-10
---

# KONZ-platform-058: iil-assist — ein Dienst, zwei Zugänge (App und Chat)

**Auftrag:** [platform#3011](https://github.com/achimdehnert/platform/issues/3011).
**Zustandsdatei (Kriterium 6):** [`KONZ-platform-058/iil-assist.yaml`](KONZ-platform-058/iil-assist.yaml) —
prüfen mit `python3 tools/iil_assist_katalog.py validate`, Briefing für ein fremdes Modell mit `… briefing`.

## Kernthese

Ein Dienst ist eine reine Funktion im Service-Layer eines Hubs mit einem deklarierten Vertrag: Name,
Eingabe, Ausgabe, Datenklasse, Gate. Die App ruft die Funktion direkt, wie heute (ADR-009). Der Chat
ruft dieselbe Funktion über ein Gateway, das den Vertrag liest und den Aufruf dort ausführt, wo der Hub
läuft. Der Vertrag wird **einmal geschrieben und zweimal gelesen** — das ist der ganze Trick gegen den
Doppelbau. Alles, was heute schon als Service-Funktion, Management-Command oder MCP-Werkzeug existiert
(1575 Fundstellen in 63 Repos, C1), kann so deklariert werden, ohne verschoben zu werden.

## Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|---|---|---|---|---|
| A1 | Der Bestand ist groß und verteilt: 1191 Service-Funktionen, 315 Management-Commands, 63 MCP-Werkzeuge, 3 Toolkits | Annahme | C1, zwei Läufe byte-gleich | belegt |
| A2 | Die frühere Chat-Architektur (chat-agent, ADR-034/036) ist tot: Paket im Archiv, nur noch als Kopie in cad-hub | Annahme | C2; ADR-036 trägt trotzdem `implemented` | belegt |
| A3 | Der Lotse im Chat existiert als Stufe A (Session): lesen, senden, beobachten, entschlüsselt; der Live-Bot (Stufe B) braucht einen Owner-Grant | Annahme | C3, #48 Kriterien 1–5; Rundlauf mit Ilja noch nicht eingetreten | belegt |
| A4 | Externe Aufrufe an App-Routen scheitern an Cloudflare Access; im Host-Netz sind die Container erreichbar | Annahme | Gemessen 2026-09-10 von dev-desktop: `docs.iil.pet/api/` → 302 auf das Access-Login; `/livez/` von dev-hub und illustration-hub → 200 (Health ist ausgenommen, das sagt nichts über App-Routen); C10: 36 von 39 Diensten mit `container_name` | belegt für docs.iil.pet; für die App-Routen der übrigen Hubs Hypothese — D2 stützt sich zusätzlich auf A6 |
| A5 | Ein gemeinsames Paket für den Vertrag kann nicht `iil-django-commons` sein: `pypi_strategy: einfrieren`, kein Hub nutzt es | Annahme | C11, C6 | belegt |
| A6 | Die Hubs liegen auf mehreren Hosts (prod-b 14, prod 4, odoo 3, gx10 1, 15 ohne Angabe) | Annahme | C10 | belegt — die 15 sind Befund O3 |
| A7 | Die Morgen-Zeitung erreicht den Chat bereits täglich | Annahme | Handover 2026-09-09; der Zustellweg ist in news-hub nicht belegt | Hypothese, Befund O4 |
| D1 | Chat → Gateway → Hub, nicht Chat → jeder Hub einzeln | Entscheidung | eine Auth-Grenze, Protokoll an einer Stelle (ADR-037), Tool-Budget +2 statt +N (C9) | entschieden |
| D2 | Das Gateway ruft den Dienst als Management-Command auf dem Host des Hubs auf (`docker exec`, Routing aus `ports.yaml`), nicht über eine neue HTTP-Schnittstelle je Hub | Entscheidung | A4, A6; Latenz ~1–2 s pro Aufruf ist für Chat tragbar | entschieden |
| D3 | Der Vertrag lebt in einem kleinen neuen Paket `iil-dienst` (Dekorator, `dienste_export`, `dienst_aufruf`) | Entscheidung | A5; ADR-044 verlangt den zweiten Abnehmer — hier sind es fünf; Veröffentlichung über die bestehende PyPI-Strecke (ADR-266, [#3019](https://github.com/achimdehnert/platform/issues/3019)) | entschieden |
| D4 | Der Chat-Zugang wird in Stufe A abgenommen: der Kapitän ruft das Gateway, die Antwort steht als Lotse im Raum. Der Live-Bot ist ein Gate (#48 Stufe B), kein Kriterium | Entscheidung | A3; sonst hinge jeder MVP am Owner-Grant | entschieden |
| D5 | chat-agent wird nicht wiederbelebt; die drei lebenden Toolkits werden als Dienste deklariert | Entscheidung | A2; ADR-036 wird bei erstem MVP auf `superseded` gesetzt | entschieden |
| D6 | `iil-assist-hub` ist der Produktname des Chat-Zugangs; Repo bleibt `chat-hub`, Fachkern bleibt `iil-assist-core`; der Alias `assist.iil.pet` wird als `alias_status: nicht-angelegt` geführt, DNS ist Owner-Zug | Entscheidung | C4 (Paket-Topologie), Kriterium 8; kein Eintrag in `domain_aliases`, sonst meldet 0.7.11 NXDOMAIN | entschieden |
| R1 | Ein Dienst mit personenbezogenen oder Mandantendaten landet in einem falschen Raum | Risiko | Vertragsfeld `datenklasse` + `gate: raum-bindung`; die Zustandsdatei lehnt `chat_eignung: ja` für diese Klassen ab (validate) | verankert |
| R2 | Der Live-Bot macht einen Nicht-Kapitän zum Auslöser eines Werkzeugs | Risiko | #48 Stufe B: nur Lesen, Außenwirkung als Entwurf, Owner-Grant; Charta Art. 1/2 (C8) | verankert durch D4 |
| R3 | Das Programm stirbt leise, weil niemand die Dienste nutzt | Risiko | Kill-Gate misst Tests je Zugang und Nutzung; Bahn `verbesserung` schreibt die Zahlen täglich | verankert |
| R4 | Ein weiteres Paket rottet wie chat-agent | Risiko | `iil-dienst` ist Vertragsformat ohne Fachlogik (< 200 Zeilen); Bahn `wartung` misst Commit-Alter je Repo | verankert |

## Architektur (Kriterium 2)

Vier Schichten, drei davon existieren. Die Zustandsdatei trägt sie unter `architektur.schichten`.

| Schicht | Wo | Was | Stand |
|---|---|---|---|
| Vertrag | Hub-Repo, Paket `iil-dienst` | `@dienst(name, datenklasse, gate)` auf der Service-Funktion; `manage.py dienste_export` (JSON-Katalog); `manage.py dienst_aufruf <name> --json` | neu (D3) |
| Zugang App | Hub-Repo, Views | ruft dieselbe Funktion (ADR-009); `data-dienst="<name>"` am auslösenden Element für den Zugangstest | vorhanden |
| Gateway | `mcp-hub/orchestrator_mcp` | zwei Werkzeuge: `dienst_katalog()` (sammelt die Exporte) und `dienst_aufruf(name, args)` (führt per `ssh <prod_host> docker exec <container_name> manage.py dienst_aufruf` aus, prüft Datenklasse und Gate gegen den Raum, protokolliert nach ADR-037) | vorhanden als Server (C5), Werkzeuge neu |
| Zugang Chat | `chat-hub/deploy/chat_lotse.py` | Stufe A: Kapitän liest den Raum (`sync`/`watch`), ruft das Gateway, antwortet mit `send` und KI-Kennzeichnung. Stufe B: Dienst auf prod-b, Router wählt den Dienst aus dem Katalog (Modell nach `llm-routing.md`), Außenwirkung als Entwurf | Stufe A vorhanden (C3), Stufe B Gate |

**Warum kein Direktaufruf je Hub:** Windsurf und Claude Code haben ein Tool-Budget (ADR-101 D-01). Ein
Werkzeug je Dienst würde es sprengen; Dienste sind deshalb **Daten im Katalog**, nicht Werkzeuge.

**Konflikte mit bestehenden ADRs** (vollständig in der Zustandsdatei, `architektur.konflikte`):
ADR-036 `implemented` bei archiviertem Paket → `superseded`; ADR-101 Budget → +2; ADR-044 kein fünftes
Paket ohne zweiten Abnehmer → fünf Abnehmer beim MVP; ADR-009 → bestätigt; ADR-037 → gilt für jeden
Gateway-Aufruf; KONZ-025 Art. 1/2 → Nachricht ist Anfrage an den Katalog, nie Befehl an die Session.

## Dienst-Katalog (Kriterium 3)

Vierzehn Dienste in der Zustandsdatei (`dienste`), je mit Repo, Reifegrad, Datenklasse, Chat-Eignung,
Gate, Aufwand, Priorität. Auszug, sortiert nach Priorität:

| Dienst | Repo | Reifegrad | Datenklasse | Chat | Gate | Aufwand | Prio | MVP |
|---|---|---|---|---|---|---|---|---|
| Plattform-Status | dev-hub | vorhanden | intern | ja | keins | S | 1 | ✔ |
| Dokument-Suche | doc-hub | teilweise | personenbezogen | raum-gebunden | raum-bindung | S | 1 | ✔ |
| Fristen-Auskunft | frist-hub (iil-assist-core) | teilweise | mandant | raum-gebunden | raum-bindung | M | 1 | ✔ |
| Thema nachfragen | news-hub | vorhanden | intern | ja | keins | S | 2 | ✔ |
| Bild erzeugen | illustration-hub | vorhanden | intern | ja | budget | S | 2 | ✔ |
| Verarbeitungs-Auskunft | risk-hub | vorhanden | mandant | raum-gebunden | raum-bindung | M | 2 | |
| ADR-Auskunft | iil-adrfw | vorhanden | öffentlich | ja | keins | S | 2 | |
| Mailcheck-Zusammenfassung | dev-hub | vorhanden | personenbezogen | raum-gebunden | raum-bindung | S | 2 | |
| Wohngeld-Assistent | meiki-hub | neu | personenbezogen | raum-gebunden | raum-bindung | L | 2 | eigener Auftrag (C7) |
| Rechnungsstand | billing-hub | teilweise | mandant | raum-gebunden | raum-bindung | M | 3 | |
| Steuer-Auskunft | tax-hub | vorhanden | mandant | raum-gebunden | raum-bindung | M | 3 | |
| Text-Dienste | writing-hub | vorhanden | intern | ja | keins | S | 3 | |
| CAD/IFC-Abfrage | cad-hub | vorhanden | intern | ja | keins | M | 3 | |
| Reise/Story | travel-beat | vorhanden | intern | ja | keins | S | 4 | ruhend |

**Top 3, begründet:**
1. **Plattform-Status (dev-hub).** Reiner Lesedienst ohne Datenrisiko. Er prüft das Gateway und beide
   Zugänge, bevor irgendein sensibler Dienst folgt — und er bedient den Infra-Raum aus #2855.
2. **Dokument-Suche (doc-hub).** Der Dienst mit dem höchsten Tageswert für den Owner; ein MCP-Server
   existiert schon. Er beweist die Raum-Bindung für personenbezogene Daten, die alle Mandanten-Dienste
   danach brauchen.
3. **Fristen-Auskunft (frist-hub, iil-assist-core).** Der Fachkern der Familie. Wenn der Kern nicht
   über beide Zugänge läuft, trägt der Name iil-assist nicht.

**Die fünf MVPs (Vorschlag, Kriterium 5, Bestätigung als Kommentar in #3011 = offen O1):** die Top 3 plus
*Thema nachfragen* (news-hub — die Zeitung liegt schon im Chat, die Rückfrage ist der zweite Zugang) und
*Bild erzeugen* (illustration-hub — erster Dienst mit Kosten-Gate). Vier Repos, einer auf iil-assist-core.
Ausgeschlossen mit Grund: Wohngeld-Assistent (eigener Auftrag chat-hub#77), Reise/Story (App abgeschaltet).

## Betriebsgrenzen (Kriterium 4)

| Gate | Bedeutung | Dienste |
|---|---|---|
| `keins` | Lesedienst, interne oder öffentliche Daten, keine Außenwirkung | Plattform-Status, Thema nachfragen, ADR-Auskunft, Text-Dienste, CAD |
| `raum-bindung` | Antwort nur in Räume, deren Mitgliederliste der Vertrag nennt (Owner-Raum, Mandanten-Raum); jede andere Anfrage bekommt „nicht in diesem Raum" | Dokument-Suche, Fristen, Verarbeitungs-Auskunft, Mailcheck, Rechnungsstand, Steuer, Wohngeld |
| `entwurf-freigabe` | Außenwirkung (Versand, Deploy, Publish): der Dienst liefert einen Entwurf in den Raum, der Owner gibt frei | heute kein MVP; Muster aus #48 Stufe B |
| `budget` | Kosten je Aufruf (Modell, Bildgenerierung): Tageslimit nach `llm-routing.md`, Überschreitung meldet statt zu rechnen | Bild erzeugen |

Die Lotsen-Charta (C8) gilt unverändert: eine Chat-Nachricht ist eine **Anfrage an den Katalog**; der
Router darf nur Dienste aus dem Katalog wählen, nie Session-Befehle ableiten. In Stufe A entscheidet
der Kapitän, in Stufe B der Router — beide gegen denselben Katalog.

## MVC — kleinste Fassung, die beide Zugänge beweist

`iil-dienst` mit Dekorator und den zwei Commands; `dienst_katalog`/`dienst_aufruf` im Orchestrator;
Plattform-Status in dev-hub deklariert; Test je Zugang (View-Test und `dienst_aufruf`-Test erwarten
dieselbe Antwort); eine Nachricht im Infra-Raum, eine Lotse-Antwort. Danach die vier weiteren MVPs.

## Regelkreis (Kriterium 7)

Vier Bahnen, ein Werkzeug (`tools/iil_assist_katalog.py bahn <bahn>`), eine Datei:

| Bahn | Takt | Frage | Was der Lauf tut |
|---|---|---|---|
| verbesserung | täglich | Was wurde je Dienst besser? | Fundstellen je Repo aus dem Inventar, Tests je Zugang, Antwortzeit, Nutzung → `bahnen.verbesserung.laeufe` |
| wartung | täglich | Welcher Dienst kippt als Nächstes? | Betriebsstatus, Lebenszyklus, Commit-Alter je Repo → Rangliste der drei Wackligsten |
| diabolus | wöchentlich | Was widerspricht der eigenen Architektur? | Briefing nach `~/shared`, Antwortdatei wird eingetragen (der Weg der externen Zweitmeinung ist manuell) |
| ootb | wöchentlich | Welcher Dienst fehlt, den keiner nannte? | wie diabolus; Kandidaten landen als `vorgeschlagen` im Katalog |

Ohne `--apply` ist jeder Lauf ein Trockenlauf. Der Takt wird erst mit dem ersten MVP verdrahtet
(Workflow + Eintrag im Melder-Register mit Leser, Phase 0.7.23; [#3020](https://github.com/achimdehnert/platform/issues/3020)) — bis dahin läuft er von Hand. Anschluss
an den Skill-Fitness-Lauf (#2855): dieselben vier Namen, dieselbe Datei; wer zuerst gebaut wird, nimmt
den anderen als Konsumenten mit.

## Modellfest (Kriterium 6)

Die Zustandsdatei ist die einzige Quelle für Phase, Entscheide, Katalog, Offenes und Bahnen. `validate`
prüft Schema und Invarianten (≥ 10 Dienste, genau 5 MVPs über ≥ 3 Repos, einer auf iil-assist-core,
keine personenbezogene Klasse mit `chat_eignung: ja`). `naechster-schritt` leitet aus dem Zustand ab,
wer dran ist. **Probe:** ein frisches Modell bekommt nur `briefing` und nennt Top 3 und die fünf MVPs;
Ergebnis kommt nach `proben`. Erste Probe: offen, wird mit dem Konzept-PR angestoßen.

## Kill-Gate

Siehe `kill_criteria` im Kopf. Gemessen wird über die Bahn `verbesserung` (Tests je Zugang) und die
Zustandsdatei (`status` je MVP). Prüfdatum 2026-10-24.

## Alternativen

- **chat-agent wiederbeleben (ADR-034/036):** Toolkits je App mit eigenem LLM-Tool-Calling. Verworfen:
  das Paket ist archiviert, jede App bräuchte ihren eigenen Modell-Aufruf, und der Chat-Zugang wäre ein
  zweiter Code-Pfad neben der App.
- **Ein Matrix-Bot je Hub:** N Bots, N Schlüssel, N Räume, kein gemeinsames Gate. Verworfen (R1, R2).
- **Lotse ruft jeden MCP-Server direkt:** 14 Server, Tool-Budget, N Auth-Grenzen (C5, C9). Verworfen
  zugunsten des Gateways (D1).
- **HTTP-API je Hub statt Management-Command:** sauberer, aber Cloudflare Access sperrt externe Aufrufe
  (A4) und jeder Hub bräuchte einen neuen Endpunkt samt Token. Zurückgestellt; die Vertrags-Schicht
  erlaubt den Wechsel später ohne Änderung an den Diensten.

## Befunde

| # | Befund | Konsequenz |
|---|---|---|
| B1 | ADR-036 steht auf `implemented`, das Paket liegt im Archiv | Status korrigieren mit dem ersten MVP (D5) — [#3022](https://github.com/achimdehnert/platform/issues/3022) |
| B2 | `chat-hub` und `iil-assist-core` fehlen in der kanonischen Registry (andere Org) | Inventar führt sie als `ZUSATZ`; Registry-Eintrag ist Owner-Frage (Org-Grenze) |
| B3 | 15 von 39 Diensten in `ports.yaml` ohne `prod_host` | O3 — [#3021](https://github.com/achimdehnert/platform/issues/3021) |
| B4 | Zustellweg der Morgen-Zeitung in den Chat ist in news-hub nicht belegt | O4 — Hypothese Host-Unit; billigster Check: `systemctl list-units` auf dem Host |
| B5 | `iil-django-commons` ist eingefroren und ohne Abnehmer | D3 — neues kleines Paket statt Wiederbelebung |
| B6 | Sechs Registry-Repos archiviert, darunter bfagent mit 56 MCP-Werkzeugen und einem Toolkit | nicht im Katalog; wer bfagent reaktiviert, deklariert dort Dienste |
