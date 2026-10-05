---
id: ADR-308
status: proposed
decision_date: 2026-10-04
deciders: Achim Dehnert
consulted: –
informed: –
implementation_status: partial
staleness_months: 6
ai_sparring_by:
  - tool: other
    date: "2026-10-04"
    role: adversarial-review
    summary: "Externer Anbieter (ChatGPT), Runde 1: Überarbeiten; 18 Empfehlungen, Tag-Tabelle in §9.1"
  - tool: other
    date: "2026-10-04"
    role: adversarial-review
    summary: "Externer Anbieter (ChatGPT), Runde 2: Überarbeiten; 12 Empfehlungen, Tag-Tabelle in §9.2"
---

# ADR-308: Adopt an autonomous sandbox workshop as the benchmarked development template for the production environment

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-10-04                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-070 (Progressive Autonomy Pattern), ADR-081 (Agent Guardrails & Code Safety), ADR-154 (Autonomous Coding Optimization) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten              |
|----------------|------------|---------------------------------------------|
| `platform`     | Primär     | `tools/sandbox/` (#3686, #3691), künftig `tools/sandbox/replay/`; `tools/pr_merge_sa.py` (Zeitstempel im Journal) |
| `iilsandbox/*` | Primär     | Spiegel der Pilot-Repos, ausschließlich Sandbox-Schreibziel |
| `dev-hub`      | Sekundär   | Pilot-Repo                                  |
| `decks-hub`    | Sekundär   | Pilot-Repo                                  |
| `chat-hub`     | Sekundär   | Pilot-Repo (Org `iilgmbh`)                  |
| `mcp-hub`      | Sekundär   | Pilot-Repo (vom Owner bestätigt 2026-10-04) |

---

## Decision Drivers

- **Freigabe-Last**: Der Owner-Wort-Hook zählte 62 Ereignisse in KW 39 und 84 in KW 40; 295 Merge-Versuche brachen mangels Mandat ab (`~/.claude/pr-merge-sa.jsonl`, ohne Trockenläufe).
- **Analysen und Experimente hängen an Merges**: Auch reine Untersuchungen laufen heute über PRs in Produktiv-Repos und warten damit auf den Owner (platform#3685).
- **Autonomie ohne Wirkung ist technisch angelegt**: `tools/sandbox/` (#3686) prüft vor jedem Lauf Zugangsdaten, Remotes und Token-Reichweite und hält ein Budget. Netzwerk-Egress und Secret-Scan fehlen noch (§4.3).
- **Weiterentwicklung braucht Messung**: Ohne Benchmarks optimiert ein autonomer Agent auf „viel geändert“ statt auf „besser“; ein Übernahme-Entscheid braucht einen Beleg, den der Agent nicht selbst ausstellt.
- **Schutzregeln dürfen sich nicht selbst lockern**: Die Lotsen-Charta (Punkt 3) verbietet dem Agenten, Charta, Permissions und Regeln selbst zu ändern; der Auto-Mode-Classifier hat am 2026-10-04 das Auswerten eines Sandbox-Laufs, der Lockerungen der eigenen Freigaberegeln erarbeitete, als Self-Modification gesperrt.

---

## 1. Context and Problem Statement

Die Entwicklungsumgebung (Repos, Skills, Policies, Hooks, Merge-Werkzeug) soll schneller besser werden, ohne dass jede Untersuchung und jeder Versuch eine Owner-Freigabe braucht. Gleichzeitig hat jede Freigabe-Regel einen Realfall hinter sich (`~/.claude/policies/regel-historie.md`); pauschales Lockern würde diese Lehren verlieren.

### 1.1 Ist-Zustand

| Messgröße (Quelle: `pr-merge-sa.jsonl`, Stand 2026-10-04) | Wert |
|---|---|
| Verschiedene PRs, über `pr_merge_sa.py` gemergt | 317 |
| Verschiedene PRs mit Owner-Wort-Ereignis | 125 |
| davon zugleich über `pr_merge_sa.py` gemergt | 1 |
| Owner-Wort-Ereignisse je Woche (Hook mit Zeitstempel) | KW 39: 62 · KW 40: 84 |
| Merge-Abbrüche mangels Mandat (Versuche; M0 123 · M1 145 · M2 19 · M3 8) | 295 |
| Häufigste Abbruchgründe | fehlendes M1 bei W1, Ruleset-Approval, Governance-Pfade unter `.github/workflows/` |
| Hook-Auslösungen gesamt / blockierend (`gate-hits.jsonl`) | 2338 / 1359 |
| häufigster blockierender Hook | `claim-before-cheapest-check` (1117) |

Die Merge-Abbrüche verteilen sich so: M0 fehlt, wenn ein PR ohne jedes Mandat versucht wird; M1 fehlt meist bei W1-Wirkung (Code in Produktiv-Pfaden); M2/M3 betreffen Rulesets und Governance-Pfade.

**Korrektur gegenüber der Erstfassung:** Die Erstfassung nannte als B1-Baseline eine Quote von 39,1 % (Owner-Wort-PRs je 317 gemergte PRs). Zähler und Nenner sind aber fast disjunkte PR-Mengen (Schnittmenge 1): Owner-Wort-PRs werden in der Regel nicht über `pr_merge_sa.py` gemergt. Die Quote misst daher nichts und ist verworfen (§4.2 B1).

Die Sandbox selbst existiert (#3686): Container mit Selbstprüfung (keine fremden Zugangsdaten, kein `~/.secrets`, kein Docker-Socket, Remotes und Push-Recht des Tokens nur in der Sandbox-Org, per GitHub-API geprüft) und Budget-Wächter (Tokens, Teilagenten, Laufzeit, USD). Probelauf, Budget-Abbruch und Gegenprobe mit zu breitem Token sind belegt (platform#3685).

### 1.2 Warum jetzt

Der Owner hat die Org `iilsandbox` angelegt und als Ziel gesetzt: eine maximal autonome Entwicklungs-Sandbox, die als Weiterentwicklungs-Template für die Produktiv-Umgebung dient und deren erfolgreiche Ergebnisse schrittweise nach `achimdehnert`/`iilgmbh` übernommen werden.

---

## 2. Considered Options

### Option A: Sandbox-Werkstatt mit festen Benchmarks und Owner-Ratifikation für Schutzregeln ✅

Die Sandbox arbeitet auf Kopien der Produktiv-Repos und erprobt dort Code, Skills, Werkzeuge und Regel-Versuchskopien ohne Freigaben. Jeder Auftrag hat vorab festgelegte Akzeptanzkriterien; ausgewertet wird auf dem Host, außerhalb der Schreibreichweite der Sandbox. Werkstücke gehen mit Übernahmebeleg als einzelne Upstream-PRs zurück, Schutzregel-Vorschläge als einzeln ratifizierte Issues, Erkenntnisaufträge als Bericht ohne Merge.

**Pros:**
- Volle Autonomie dort, wo sie nichts außerhalb verändern kann.
- Jede Übernahme trägt einen Beleg gegen vorab festgelegte Kriterien (§4.6) oder wird verworfen.
- Schutzregeln bleiben beim Owner; die Sandbox liefert ihm Belege statt Bitten.

**Cons:**
- Übernahme bleibt Owner-Arbeit, wenn auch vorbereitet und in einer Sitzung gebündelt.
- Aufbau von Auswertung, Replay-Suite und fehlender Abschottung kostet vorab Arbeit.

### Option B: Freigaberegeln direkt in der Produktiv-Umgebung lockern

**Pros:**
- Schnellster Effekt auf die Owner-Unterbrechungen.

**Cons:**
- Kein Beleg, dass die Lockerung keinen der Realfälle wieder öffnet → **Abgelehnt weil:** Lockerung ohne Replay-Nachweis wiederholt genau die Vorfälle, aus denen die Regeln stammen.

### Option C: Sandbox ohne Benchmarks

**Pros:**
- Sofort startklar.

**Cons:**
- Erfolg ist Meinung; Übernahme-Entscheide werden wieder Einzelprüfung → **Abgelehnt weil:** verlagert die Freigabe-Last nur, statt sie zu senken.

### Option D: Sandbox ratifiziert eigene Regeländerungen selbst

**Pros:**
- Maximale Geschwindigkeit.

**Cons:**
- Der Agent bewertet und lockert die Kontrollen, die ihn kontrollieren → **Abgelehnt weil:** widerspricht Lotsen-Charta Punkt 3 und Punkt 8; Benchmarks wären durch die bewertete Partei änderbar.

---

## 3. Decision Outcome

**Gewählte Option: Option A — Sandbox-Werkstatt mit festen Benchmarks und Owner-Ratifikation für Schutzregeln**

Option A senkt die Freigabe-Last dort, wo sie unnötig ist (Untersuchungen, Versuche, Werkzeug-Entwicklung), und ersetzt spontane Rückfragen durch eine vorbereitete wöchentliche Review-Sitzung. B öffnet Realfälle ohne Nachweis, C misst nicht, D hebt die Kontrolle auf. „Die Sandbox schult die Realumgebung“ heißt hier: Sie erprobt Änderungen an Kopien und belegt sie an Kriterien, die vor dem Lauf feststehen. Übernommen wird nur, was belegt ist, und Schutzregeln nur auf ausdrückliches Owner-Wort.

Die Benchmarks sind Messgrößen des Owners, kein Optimierungsziel des Agenten. Der Agent optimiert Aufträge, nie die eigenen Freigaben (Lotsen-Charta Punkt 8).

**Rückfallposition:** Scheitert der Pilot an B3 oder B4 (§4.7), bleibt die Sandbox als Experimentierfläche ohne Template-Anspruch bestehen; Erkenntnisaufträge laufen weiter, Übernahmen entfallen. Ein B5-Stopp beendet dagegen jeden Betrieb bis zum Owner-Wort.

---

## 4. Implementation Details

### 4.1 Drei Ergebnisklassen

| Klasse | Beispiele | Weg nach Produktiv |
|---|---|---|
| **Erkenntnisauftrag** | Analyse, Messung, Machbarkeit, „lohnt sich nicht“ | Bericht im Laufverzeichnis auf dem Host, Eintrag im Vorschlagsregister; kein PR, kein Merge |
| **Werkstück** | Code, Tests, Skills, Werkzeuge, Doku ohne Schutzwirkung | je Werkstück ein Upstream-PR mit Übernahmebeleg (§4.6); normale SA-M-Regeln |
| **Schutzregel** | `~/.claude/policies/`, Hooks, `settings.json`-Permissions, Rulesets, CODEOWNERS, `sa_m`-Block, Auswertung und Replay-Suite selbst | nur Vorschlag mit Replay-Beleg, je Regel ein Issue, einzeln vom Owner ratifiziert; nie gebündelt |

**Klasse nach Wirkung, nicht nach Pfad:** Eine Änderung ist eine Schutzregel-Änderung, sobald sie Gate-Entscheidungen, Berechtigungen, Budgetgrenzen oder maßgebliche Bewertungen verändert, auch wenn sie in einem Werkzeug oder Skill liegt (etwa `tools/pr_merge_sa.py` oder ein Hook-Skript). Gemischte Änderungen werden getrennt. Im Zweifel gilt Schutzregel.

**Zwei Regel-Ebenen:**
- **Regel-Versuchskopien** liegen in den Spiegeln und dürfen in der Sandbox verändert und gegen die Replay-Suite gespielt werden. Sie begrenzen den laufenden Agenten nicht.
- **Schutzumgebung**: Container-Grenzen, Selbstprüfung, Budget-Wächter, Token-Reichweite und die Host-Hooks. Sie begrenzt den laufenden Agenten und liegt außerhalb seiner Schreibreichweite.

**Owner-Entscheid F1 (2026-10-04):** Die Sandbox darf Regel-Versuchskopien auch auf Lockerung hin erproben, maximal autonom. Die Berichte liest und wertet die Host-Session des Agenten aus. Grenzen dieses Entscheids:
- Ratifiziert wird weiter nur durch den Owner, einzeln je Regel (Option D bleibt verworfen); das Replay-Gate B5a gilt unverändert.
- Der Agent bewertet hier Lockerungen der Regeln, die ihn selbst begrenzen (Charta Punkt 8). Deshalb steht in jedem solchen Vorschlag neben dem Nutzen auch, welcher Realfall die Regel begründet und was die Lockerung wieder öffnen könnte.
- Das Lesen setzt einen vom Owner gesetzten `autoMode.allow`-Eintrag voraus; der Classifier wird nicht umgangen. Bis der Eintrag steht, liest der Owner die Berichte.

Eine Ausnahme vom Self-Modification-Schutz für die wirksame Schutzumgebung ist nicht Teil dieser Entscheidung.

### 4.2 Benchmarks

Gemessen auf dem Host mit `tools/sandbox/benchmark.py` aus unverändertem `platform/main`; die Harness-Version (Commit) steht in jedem Messsatz.

| # | Benchmark | Definition und Quelle | Baseline | Ziel / Grenze |
|---|---|---|---|---|
| B1 | **Owner-Belastung** | absolute Wochenwerte: verschiedene PRs mit Owner-Wort, Merge-Abbrüche mangels Mandat, Review-Sitzungen und deren Dauer; getrennt nach Sandbox-Herkunft und Klasse. Quelle: Journal mit Zeitstempel auf jedem Satz | Owner-Wort-Ereignisse KW 39: 62 · KW 40: 84; PR-Werte ab Zeitstempel im Journal | sinkend; Zielwert setzt der Owner nach dem Pilot |
| B2 | **Aufträge bestanden** | Anteil der Aufträge aus dem festen Auftragspaket, deren Akzeptanzkriterien die Host-Prüfung bestehen; Wiederholungen, Abbrüche und Eingriffe zählen beim ursprünglichen Auftrag. `status.json` ist nur ein Status, kein Nachweis | – (1 von 5 Läufen mit Status `fertig`, nicht nachgeprüft) | ≥ 80 % |
| B3 | **Übernahmequote** | je Werkstück aus dem Vorschlagsregister (Zustände: eingereicht, offen, angenommen, abgelehnt, zurückgezogen). Nenner: alle eingereichten Werkstücke, deren Entscheidungsfrist (eine Review-Sitzung) abgelaufen ist; offen nach Frist und zurückgezogen zählen als nicht übernommen. Erkenntnisaufträge separat | – | **Kill: < 1/3**, frühestens ab 6 entschiedenen Werkstücken; darunter „nicht bewertbar“ |
| B4 | **Qualität** | Revert oder Fix binnen 7 Tagen, nur mit dokumentierter Zuordnung zum Übernahme-PR (Verweis im Fix-PR); Vergleich mit Nicht-Sandbox-PRs desselben Repos und derselben Klasse; CI ist die produktive CI des Upstream-PRs | – | nicht höher als der Vergleich, frühestens ab 6 Übernahmen; Befund erst nach Ablauf aller 7-Tage-Fenster |
| B5a | **Replay-Gate** (Vorlage-Filter für Schutzregel-Vorschläge) | jeder Negativfall mit erwarteter Sperrbedingung; ein Absturz oder anderer Fehler zählt nicht als Sperre. Dazu je Fall ein erlaubter Nachbarfall, der durchlaufen muss | Soll 100 %, gemessen erst mit dem ersten Lauf der Suite. Vorstufe: Gate-Drills 53/53 grün am 2026-10-04 | 100 % gesperrt **und** 100 % Nachbarfälle durch, sonst wird nicht vorgelegt |
| B5b | **Abschottung im Pilot** | Schreibwirkungen außerhalb `iilsandbox`, Egress außerhalb der Allowlist, Selbstprüfungs- und Wächter-Abbrüche | – | **jede erfolgreiche Wirkung außerhalb `iilsandbox` ist ein harter Stopp** (§4.7); Abbrüche werden gezählt |
| B6 | **Kosten** | Summe je Auftrag über alle Läufe, inklusive Wiederholungen und verworfener Ergebnisse, getrennt nach tatsächlicher Ausgabe (API) und zugerechnetem Abo-Verbrauch; dazu Aufwand für Auswertung und Review-Sitzung | 0,08 USD über 5 Läufe (zugerechnet) | je Lauf innerhalb der Grenzen aus `tools/sandbox/waechter.py`, Version im Laufbeleg; kein Gesamtdeckel am Abo (F2), Verbrauch im Wochenstand |

Die Replay-Suite enthält die historischen Vorfälle aus `regel-historie.md` und den Gate-Drills als ausführbare Fälle, je Fall mit stabiler Referenz auf den Realfall und den Drill; Regeltexte werden referenziert, nicht dupliziert. B5a ist notwendig, nicht hinreichend: Ein grüner Replay belegt nur die bekannten Fälle.

### 4.3 Abschottung

**Bestehend (#3686, am Code geprüft 2026-10-04):**
- Selbstprüfung vor jedem Lauf; Abbruch bei fremden Zugangsdaten, Remotes außerhalb `iilsandbox` oder Push-Recht des Tokens außerhalb `iilsandbox` (per GitHub-API).
- Container mit `--cap-drop ALL`, `no-new-privileges`, Speicher-, CPU- und Prozessgrenzen; Repos als Kopie per `git clone --no-local`.
- Budget-Wächter je Lauf.

**Phase 1b (umgesetzt 2026-10-05, #3695, #3702, #3707):**
- **Netzwerk-Egress**: Jeder Lauf bekommt ein internes Docker-Netz ohne Gateway. Nach außen geht es nur über einen Allowlist-Proxy (`egress_proxy.py`) zu Modell-API und GitHub, Port 443. Das Protokoll liegt außerhalb des Laufs. Die Selbstprüfung macht die Gegenprobe: Direktverbindung, DNS und ein gesperrtes Ziel müssen scheitern, GitHub muss erreichbar sein. Belegt: `--nur-pruefen` ist grün. Im Standard-Netz ergibt dieselbe Prüfung 4 Funde und Exit 1.
- **Secret-Scan**: `geheimnis_scan.py` lässt `gitleaks` mit erzwungenen Standardregeln über die volle Historie laufen. Eine eigene `.gitleaks.toml` des gescannten Repos wirkt nicht. Vorher läuft eine Positivkontrolle mit einem Kanarienrepo. Der Scan läuft vor jeder Kopie (`sandbox.sh`) und vor jedem Spiegeln oder Auffrischen (`spiegeln.sh`). Ausnahmen stehen nur mit Owner-Begründung je Fingerprint in `gitleaks-ausnahmen.txt`. Fingerprints hängen am Commit. Deshalb werden sie aus der Kopie mit nur dem Standard-Branch gewonnen, nicht aus einem Vollklon, der dieselbe Stelle an einem anderen Commit melden kann.
- **Host-Kontext**: `settings.json`, `settings.local.json`, Memory, Policies, `~/shared` und Git- oder gh-Zugangsdaten werden nicht kopiert. Die Selbstprüfung bricht ab, wenn sie davon etwas im Container findet. Kein Pilot-Repo versioniert eine `.claude/settings.json`.
- **Spiegel**: Die fünf Pilot-Repos liegen privat in `iilsandbox`, nur mit dem Standard-Branch. Actions sind je Repo aus. `spiegeln.sh` prüft beides vor jedem Push.
- **Dependabot**: Versions-Updates laufen trotz Actions aus, weil die `dependabot.yml` des Originals mitkommt. `spiegeln.sh` schließt deren PRs und löscht die Branches nach jedem Auffrischen (Owner-Entscheid D1 a, 2026-10-05). Zwischen zwei Auffrischungen können solche PRs entstehen. Sie zählen nicht in B1–B4.
- **Öffentliche Repos**: Im Free-Plan von `iilsandbox` lässt sich das Anlegen öffentlicher Repos nicht sperren. Die Option ist ausgegraut, und die API meldet `members_can_create_public_repositories=true`. Ersatz (Owner-Entscheid S2, 2026-10-05): Das Sandbox-Token ist fine-grained, nur auf die Spiegel beschränkt und ohne Administration-Recht. Es kann also keine Repos anlegen. Der Gegentest steht in §8.2.

**Profil-Negativtests (§8.2):** belegt mit #3721, nachdem der Owner das Org-Profil gesetzt hatte (#3715). Offen vor Phase 3 sind nur noch die Punkte der Checkliste in §4.7.

**Abweichungen der Sandbox von der Produktiv-Umgebung** (begrenzen, was ein Sandbox-Ergebnis belegt):

| Bereich | Sandbox | Produktiv | Folge für den Nachweis |
|---|---|---|---|
| Permissions | keine Rückfragen | Auto-Mode mit Classifier | Freigabe-Verhalten nicht belegbar, nur über Replay |
| Hooks | Host-Hooks laufen im Container nicht (belegt 2026-10-05: keine Host-Einstellungen im Container, kein Pilot-Repo versioniert `.claude/settings.json`) | aktiv | Hook-Wirkung nur über Replay belegbar |
| `settings.json`, Memory | nicht kopiert | vorhanden | Ergebnisse ohne Memory-Kontext |
| GitHub Actions | aus | an | CI-Nachweis erst am Upstream-PR (B4) |
| Netzwerk | Allowlist (ab Phase 1b) | offen | Integrationen außerhalb nicht prüfbar |

### 4.4 Getrennte Freigabe-Profile je Org

Freigaben gelten je Org, nicht global:

| Ebene | `iilsandbox` | `achimdehnert` / `iilgmbh` |
|---|---|---|
| Agent im Container | keine Rückfragen (`--dangerously-skip-permissions`), begrenzt durch Selbstprüfung und Budget | – |
| Host-Session (Auto-Mode) | eigener `autoMode.allow`-Eintrag: Repos, Branches, PRs und Merges nur in `iilsandbox` | unverändert |
| Merge (`pr_merge_sa.py`, `sa_m`) | eigenes Org-Profil: jede Wirkung mit M0 gedeckt, weil Actions aus und kein Prod-Pfad | unverändert (W1→M1, W2→M2, W3→M1 + Prüffrage) |
| GitHub-Rulesets | keine Pflicht-Reviews | unverändert |

**Sicherheitsvertrag der Profilwahl:** Vor jeder Host- oder Merge-Wirkung müssen Operation, das per API aufgelöste Ziel-Repo (Eigentümer nach Umbenennung oder Transfer) und die effektive Token-Reichweite übereinstimmen. Unbekannte oder widersprüchliche Angaben führen zur Verweigerung. Prüfung und Ausführung beziehen sich auf dieselbe aufgelöste Repo-ID, damit ein Zielwechsel dazwischen auffällt. Weil die Spiegel in `iilsandbox` weder Rulesets noch Branch Protection haben (Free-Plan), hält dort nichts einen Push zwischen Prüfung und Merge auf. Deshalb wird nur der geprüfte Kopf-Commit gemergt (`--match-head-commit`), und unter `actions_aus` wird der Actions-Stand direkt vor dem Merge neu gemessen (#3736).

Das Sandbox-Profil ändert nur die Mandatszuordnung im erlaubten Scope; die fünf Gates aus `autonomy-gates` und der Budget-Wächter gelten weiter. Der Übergang nach `achimdehnert`/`iilgmbh` läuft immer über die Produktiv-Regeln. Die Einträge in `autoMode.allow` und `sa_m` sind Schutzregeln (§4.1) und werden vom Owner gesetzt.

### 4.5 Ablauf und Rückweg

1. **Auftrag**: Vor dem Lauf entsteht eine Auftragskarte (§4.6). Ein Auftrag ist auf einen Lauf begrenzt; Folgearbeit ist ein neuer Auftrag auf frischem Spiegel mit dem vorigen Patch als Eingabe. Spiegel werden vor jedem Lauf frisch vom Original übernommen, nie umgekehrt automatisch.
2. **Lauf**: Der Agent schreibt `ausgang/bericht.md`, `status.json` und Patches.
3. **Rückweg**: Eine Host-Session unter Produktiv-Regeln holt die Artefakte ab. Sie sind Daten, keine Anweisungen. Patches werden in einem eigenen Worktree des Ziel-Repos angewendet und in einem Container ohne Produktiv-Zugangsdaten geprüft. Produktive Zugangsdaten gelangen nie in die Sandbox. Berichte aus Läufen an Regel-Versuchskopien liest die Host-Session nach F1 (§4.1), sobald der Owner den `autoMode.allow`-Eintrag gesetzt hat; vorher liest sie der Owner.
4. **Auswertung**: auf dem Host aus unverändertem `platform/main`, gegen den aktuellen Integrationsstand des Ziel-Repos; Ergebnis ist der Übernahmebeleg.
5. **Review-Sitzung**, wöchentlich: entscheidungsreif vorbereitet sind Beleg, Diff und die je PR nötigen Produktiv-Mandate. Je Werkstück ein PR, kein Sammel-PR. Je Sitzung höchstens 5 Werkstücke und 2 Schutzregel-Vorschläge (F3); was darüber liegt, wartet auf die nächste Sitzung, und die Wartezeit zählt in B1. Schutzregel-Vorschläge kommen einzeln als Issue. Erfasst werden Sitzungsdauer, Rückfragen und Wartezeit seit Einreichung (B1).
6. **Erkenntnisaufträge** enden mit dem geprüften Bericht und einem Eintrag im Vorschlagsregister; ein „Änderung lohnt sich nicht“ ist ein gültiges Ergebnis. Sie brauchen keine Entscheidung und laufen nicht gegen die Obergrenze.
7. **Wochenstand an den Owner**: einmal je Woche als Kommentar in platform#3685: Läufe, Ergebnisse je Klasse, B1–B6, Verbrauch am Abo-Kontingent (F2), offene Vorschläge. Ein harter Stopp wird sofort gemeldet, nicht erst im Wochenstand.

Den Rückweg verantwortet die Host-Session des Owners; ein eigener Dienst ist dafür nicht nötig.

### 4.6 Auftragskarte und Übernahmebeleg

**Auftragskarte** (vor dem Lauf, auf dem Host abgelegt): Ziel-Repo und Ausgangs-Commit, Klasse (§4.1), Frage oder erwarteter Nutzen, ausführbare Akzeptanzkriterien. Bei Optimierungen zusätzlich das Maß, an dem Ausgangsstand und Kandidat unter gleichen Bedingungen verglichen werden.

**Übernahmebeleg** (auf dem Host erzeugt): Hash des geprüften Patches bzw. Kandidaten-Commit, Ausgangs-Commit, Harness-Version, Replay-Version, Grenzen des Wächters, Ergebnis jeder Akzeptanzprüfung, Vergleichswerte bei Optimierungen. Ohne Beleg keine Übernahme. Was der Agent im Container schreibt, ist Eingabe für die Prüfung, nie selbst Beleg.

### 4.7 Pilot-Gates und Stopp

**Vor Phase 3** (Checkliste, jede Zeile belegt):
- Definitionen B1–B6 fest, Merge-Journal mit Zeitstempel, Baselines gemessen.
- Auftragspaket mit Akzeptanzkriterien festgelegt.
- Replay-Suite (B5a) mit Negativfällen und Nachbarfällen einmal gelaufen.
- Egress-Allowlist und Secret-Scan aktiv, je mit Gegenprobe.
- Negativtests des Org-Profils grün (§8) — belegt mit #3721.
- `tools/sandbox/` steht in `sa_m.governance_pfade` (F4) — #3731.
- Merge nur des geprüften Kopfes, Actions-Stand vor dem Merge neu gemessen (§4.4) — #3736.
- Rate-Limit-Antworten gelten in der Selbstprüfung nicht als fehlendes Recht — #3738.
- Live-Merge-Test (S9): ein PR auf einem Spiegel in `iilsandbox` läuft einmal echt durch `pr_merge_sa.py`, mit Head-Pin und Gegenprobe (Push nach der Prüfung → kein Merge). Er läuft in einer eigenen Sitzung, weil der `autoMode`-Eintrag für `iilsandbox` erst dort greift (#3724). — Bestanden am 2026-10-05: Merge des geprüften Kopfes, Gegenprobe von GitHub abgelehnt („Head branch was modified“). Erst möglich nach #3747, vorher brach das Werkzeug an der Free-Plan-Antwort auf die Rulesets-Abfrage ab ([Beleg](https://github.com/achimdehnert/platform/issues/3724#issuecomment-5993595823)).

**Harter Stopp** (B5a rot oder B5b-Wirkung außerhalb `iilsandbox`): Laufende Läufe werden abgebrochen, keine neuen Läufe, keine Exporte, offene Übernahmen eingefroren; der Owner entzieht das `iilsandbox`-Token. Der Stopp ist nicht auf „diesen Vorschlag nicht vorlegen“ reduzierbar. Wiederanlauf nur auf Owner-Wort nach dokumentierter Ursachenklärung in platform#3685; Rückbau nach der Rollback-Leiter aus ADR-081.

**Ausweitung**: erst nach Ablauf aller B4-Fenster, wenn B3 ≥ 1/3, B4 nicht schlechter als der Vergleich, B5 ohne Stopp und B1 nicht gestiegen ist. Ausweitung heißt mehr Repos oder Aufträge in `iilsandbox`, nie automatisch mehr Rechte in Produktiv.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `platform` `tools/sandbox/` | 0 Sandbox-Kern | ✅ Abgeschlossen | 2026-10-04 | #3686: Selbstprüfung, Wächter, Lokal-Modus belegt |
| `platform` | 1 Benchmark-Harness | 🟡 Teilweise | 2026-10-04 | #3691 gemergt; offen: B1 auf absolute Wochenwerte umstellen, Zeitstempel auf Merge-Sätzen in `pr_merge_sa.py`, Vorschlagsregister, Auftragskarte, Replay-Suite mit Nachbarfällen |
| `platform` | 1a Rückschau | ⬜ Ausstehend | – | Journal-Auswertung ohne Sandbox: welche Abbrüche hätte eine vorab eingeholte oder pfadbezogene Freigabe vermieden (Vergleichsarm „bessere Vorbereitung“); `claim-before-cheapest-check` als erster Erkenntnisauftrag |
| `platform` `tools/sandbox/` | 1b Abschottung nachrüsten | ✅ Abgeschlossen | 2026-10-05 | #3695, #3702, #3707: Egress-Allowlist und Secret-Scan je mit Gegenprobe, Host-Kontext, Hooks belegt (§4.3); Profil-Negativtests belegt (#3721); #3731, #3736, #3738 gemergt; Live-Merge-Test S9 bestanden, Voraussetzung #3747 (§4.7) |
| `iilsandbox` | 2 Spiegel der Pilot-Repos, Org-Token | ✅ Abgeschlossen | 2026-10-05 | fünf Spiegel privat, Actions aus, nur Standard-Branch; Sandbox-Token kann keine Repos anlegen (#3710, gemessen 403); Org-Profil vom Owner gesetzt (#3715) |
| Pilot-Repos | 3 Pilot, 2 Wochen | ⬜ Ausstehend | – | nur nach Checkliste §4.7 |
| `platform` | 4 Entscheid: ausweiten, Rückfallposition oder stoppen | ⬜ Ausstehend | – | nach Ablauf aller B4-Fenster (§4.7) |

---

## 6. Consequences

### 6.1 Good

- Untersuchungen und Versuche laufen ohne Freigabe durch und enden ohne Merge.
- Übernahmen tragen einen Beleg, den der Agent nicht selbst ausstellt.
- Lockerungen von Schutzregeln kommen mit Replay-Nachweis inklusive Nachbarfällen.

### 6.2 Bad

- Die Übernahme bleibt beim Owner; die Last sinkt nur, wenn die Review-Sitzung kürzer ist als die heutigen Einzelrückfragen. Das misst B1.
- Auswertung, Replay-Suite, Spiegel und Abschottung brauchen Pflege; Pflegeverantwortung liegt bei `platform`, Drift-Pfade siehe §8.
- Sandbox-Läufe teilen sich das Abo-Kontingent mit der laufenden Arbeit; ohne Gesamtdeckel (F2) kann die Werkstatt laufende Arbeit ausbremsen. Sichtbar wird das im Wochenstand.

### 6.3 Nicht in Scope

- Prod-Zugang, Deploys, Publish aus der Sandbox.
- Selbst-Ratifikation von Schutzregeln (Option D) und jede Ausnahme vom Self-Modification-Schutz.
- Repos mit personenbezogenen Daten oder Behördenbezug (`meiki-lra`, `ttz-lif`).

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Benchmark wird zum Ziel statt zum Maß | Mittel | Hoch | Auswertung nur auf dem Host; Akzeptanzkriterien vor dem Lauf; B4 und B5 als Gegengewichte |
| Messbasis ist falsch, ohne dass es auffällt | Mittel | Hoch | Zwei Fehler in der Erstfassung (B1-Quote, Secret-Scan) belegen das Risiko; jede Zahl im ADR mit nachrechenbarer Quelle, Kohorten in Tests |
| Secret gelangt in eine Kopie | Niedrig | Kritisch | `gitleaks` über volle Historie mit Positivkontrolle (Phase 1b, Pflicht vor Phase 3) |
| Review-Sitzung wird zur neuen Freigabe-Warteschlange | Mittel | Mittel | Obergrenze je Sitzung (F3), Sitzungsdauer und Wartezeit in B1, B3-Kill |
| Spiegel driften vom Original | Mittel | Niedrig | Frische Übernahme vor jedem Lauf; Auswertung gegen aktuellen Integrationsstand |
| Ausbruch über offenen Egress | Mittel | Hoch | Egress-Allowlist vor Phase 3 |

---

## 8. Confirmation

1. **Selbstprüfung**: `tools/sandbox/selbstpruefung.py` läuft vor jedem Agenten-Start; ohne Exit 0 startet kein Lauf (Tests `tools/tests/test_sandbox_selbstpruefung.py`). Ab Phase 1b prüft sie Egress-Allowlist und Secret-Scan, je mit Gegenprobe.
2. **Profil-Negativtests**: Tests gegen das Org-Profil mit Produktiv-Ziel, zu breitem Token, widersprüchlichen Zielangaben, umbenanntem oder transferiertem Repo und Zielwechsel zwischen Prüfung und Ausführung; alle müssen verweigern. Dazu kommt ein Gegentest: Das Sandbox-Token darf in `iilsandbox` kein Repo anlegen (Ersatz für die im Free-Plan fehlende Sperre öffentlicher Repos, §4.3).
3. **Replay-Gate**: Kein Schutzregel-Vorschlag wird als Issue vorgelegt, ohne dass die Replay-Suite alle Negativfälle mit erwarteter Sperrbedingung blockiert und alle Nachbarfälle durchlässt; das Ergebnis steht im Issue.
4. **Übernahmebeleg**: Kein Upstream-PR aus der Sandbox ohne Übernahmebeleg (§4.6) im PR-Text; `benchmark.py` erzeugt ihn auf dem Host.
5. **Schreibreichweite**: Auswertung und Replay-Suite laufen nur aus `platform/main` auf dem Host. `tools/sandbox/` kommt mit #3731 in `sa_m.governance_pfade` und in CODEOWNERS (F4, §4.7); gemergt mit Owner-Approval am 2026-10-05. Damit sind Selbstprüfung, Budget-Wächter und Spiegeln nur noch mit M2 änderbar.
6. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 6 Monate; Drift-Pfade siehe Kommentar am Ende.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **Sandbox** | Abgeschotteter Container plus Org `iilsandbox`, in der ein Agent ohne Freigaben arbeitet, aber nichts außerhalb verändern kann |
| **Erkenntnisauftrag** | Auftrag, der mit einem geprüften Bericht endet, ohne Merge |
| **Werkstück** | Ergebnis der Sandbox ohne Schutzwirkung: Code, Tests, Skills, Werkzeuge, Doku |
| **Schutzregel** | Regel, die Agenten begrenzt oder Bewertungen bestimmt; Einordnung nach Wirkung (§4.1) |
| **Regel-Versuchskopie** | Kopie einer Schutzregel in einem Spiegel; begrenzt den laufenden Agenten nicht |
| **Schutzumgebung** | Container-Grenzen, Selbstprüfung, Wächter, Token-Reichweite und Host-Hooks, die den laufenden Agenten begrenzen |
| **Auftragskarte** | Vor dem Lauf festgelegter Ausgangsstand, Nutzen und Akzeptanzkriterien |
| **Übernahmebeleg** | Auf dem Host erzeugter Nachweis, der ein Ergebnis an Patch, Versionen und Prüfergebnisse bindet |
| **Vorschlagsregister** | Liste aller Sandbox-Ergebnisse mit stabiler ID und Zustand |
| **Replay-Suite** | Ausführbare Sammlung historischer Vorfälle mit erwarteter Sperrbedingung und erlaubten Nachbarfällen |
| **SA-M** | Merge-Regel aus `autonomy-gates`: Mandat (M0–M3) muss Wirkung (W0–W3) decken |
| **Benchmark** | Feste Messgröße des Owners, an der eine Änderung als besser oder schlechter belegt wird |

---

## 9. More Information

- platform#3685: Vorschlag Sandbox-Klasse, Owner-Entscheide S1–S7
- platform#3686: Sandbox-Kern (`tools/sandbox/`)
- platform#3691: Benchmark-Harness (`tools/sandbox/benchmark.py`)
- `~/.claude/policies/autonomy-gates.md`: fünf Gates, SA-M-Block
- ADR-070: Progressive Autonomy — diese Sandbox ist eine Stufe ohne Außenwirkung
- ADR-081: Guardrails und Rollback-Leiter — bleiben in Produktiv unverändert, bis ein Vorschlag ratifiziert ist

### 9.1 Externe Zweitmeinung, Runde 1 (2026-10-04)

Befunde PRO-1–4, AD-1–19, M28-1–7, OOB-1–4; Empfehlung „Überarbeiten“. Bewertung je Empfehlung:

| REC | Befunde | Verdikt | Aktion |
|---|---|---|---|
| REC-1 | AD-1, AD-2 | [valid] | B1 auf absolute Wochenwerte nach Herkunft (§4.2); Prüfung ergab zusätzlich, dass die alte Quote disjunkte Mengen teilte (§1.1) |
| REC-2 | M28-1 | [valid] | Zeitstempel auf Merge-Sätzen (Phase 1); Differenz-Methode entfällt |
| REC-3 | AD-3, AD-13 | [valid] | Auswertung nur auf dem Host aus `platform/main`; B2 per Host-Prüfung, B6 je Auftrag (§4.2, §4.5) |
| REC-4 | AD-4, AD-6 | [valid] | B5 geteilt in B5a Replay-Gate und B5b Abschottung, die den Stopp auslösen kann; Replay-Baseline erst nach Lauf |
| REC-5 | AD-5, M28-2 | [valid] | Nachbarfälle als Positivkontrolle; „notwendig, nicht hinreichend“ in §4.2. Holdout/Mutationen bewusst nicht übernommen: erst nach erster Suite sinnvoll |
| REC-6 | AD-7 | [valid] | B3 je Werkstück, je Werkstück ein PR; Sitzungsdauer in B1 |
| REC-7 | AD-8 | [valid] | Mindestfallzahl 6 für B3 und B4, darunter „nicht bewertbar“ |
| REC-8 | AD-9, AD-14 | [valid] | Rückweg in §4.5 Schritt 3; Berichte zu Regel-Versuchskopien liest der Owner |
| REC-9 | AD-10 | [valid] | Egress-Allowlist, am Code bestätigt: heute offen (§4.3, Phase 1b) |
| REC-10 | AD-11 | [valid] | `gitleaks` über volle Historie; am Code bestätigt: fehlt, Erstfassung war falsch (§4.3) |
| REC-11 | AD-12 | [valid] | Tabelle der Abweichungen in §4.3; Hook-Verhalten als Hypothese markiert |
| REC-12 | M28-3 | [valid] | Negativtests in §8.2; Push-Recht wird bereits per API geprüft, Umbenennung/Transfer neu |
| REC-13 | AD-16, AD-17 | [valid] | Phase 1a Rückschau; `claim-before-cheapest-check` als erster Erkenntnisauftrag |
| REC-14 | AD-19 | [valid] | Auftrag auf einen Lauf begrenzt (§4.5 Schritt 1) |
| REC-15 | M28-4 | [valid] | Rückfallposition in §3 |
| REC-16 | AD-15 | [valid] | Benchmarks als Messgröße des Owners, kein Agenten-Ziel (§3) |
| REC-17 | M28-5 | [valid] | Abo-Anteil als offene Owner-Frage F2 |
| REC-18 | AD-18, M28-6, M28-7 | [valid] | Abbrüche in §1.1 erläutert, Ausweitungskriterien in §4.7, `staleness_months` ins Frontmatter, Drift-Pfade erweitert |

Out-of-the-Box: OOB-1 als Phase 1a übernommen; OOB-2 als Klasse Erkenntnisauftrag übernommen; OOB-3 (befristete Standing-Mandate) [out-of-scope], weil eine Produktiv-Lockerung, frühestens mit Beleg aus Phase 1a als eigener Vorschlag; OOB-4 als Rückfallposition übernommen.

### 9.2 Externe Zweitmeinung, Runde 2 (2026-10-04)

Befunde PRO-1–3, AD-1–12, M28-1–3, OOTB-1–2; Empfehlung „Überarbeiten“, Option A bleibt bevorzugt. Bewertung je Empfehlung:

| REC | Befunde | Verdikt | Aktion |
|---|---|---|---|
| REC-1 | AD-1, AD-3 | [valid] | Auftragskarte und Übernahmebeleg (§4.6) |
| REC-2 | AD-2, AD-12 | [valid] | B1 als Owner-Belastung mit gleicher Kohorte und absoluten Mengen; Kohortenfehler am Journal bestätigt (Schnitt 1 von 125/317) |
| REC-3 | AD-3, AD-4 | [valid] | B2 über festes Auftragspaket, B3 über Vorschlagsregister mit Frist und Nennerregel |
| REC-4 | AD-5 | [valid] | B4 mit dokumentierter Zuordnung, Vergleich nach Repo und Klasse, volles Fenster; CI = produktive CI des Upstream-PRs |
| REC-5 | AD-6 | [valid] | erwartete Sperrbedingung und Nachbarfälle; 100 % als Soll bis zur ersten Messung |
| REC-6 | AD-7 | [valid] | B6 über die Serie, tatsächlich vs. zugerechnet; Grenzen aus `waechter.py` referenziert statt dupliziert |
| REC-7 | AD-8, AD-10 | [valid] | Klasse nach Wirkung; zwei Regel-Ebenen; Charta-8-Grenze als Owner-Frage F1 |
| REC-8 | AD-9 | [valid] | Sicherheitsvertrag der Profilwahl (§4.4), Gegenproben in §8.2 |
| REC-9 | AD-11 | [valid] | Rückweg mit Host-Session des Owners als Verantwortlichem (§4.5) |
| REC-10 | AD-12 | [valid] | Review-Sitzung, je Werkstück ein PR, Obergrenze F3, Wartezeit in B1 |
| REC-11 | M28-1, M28-2 | [valid] | Versionen im Übernahmebeleg, Abweichungstabelle, Auswertung gegen Integrationsstand, Drift-Pfade |
| REC-12 | M28-3, AD-4, AD-5 | [valid] | Pilot-Gates, Umfang des Stopps, Wiederanlauf, Ausweitung nach B4 (§4.7) |

Out-of-the-Box: OOTB-1 als Klasse Erkenntnisauftrag übernommen (deckungsgleich mit Runde 1 OOB-2); OOTB-2 als Vergleichsarm in Phase 1a übernommen, rückblickend statt als paralleler Arm, um den Messaufwand klein zu halten.

### 9.3 Owner-Entscheide (2026-10-04)

| Frage | Entscheid | Begründung, wo vorgeschlagen |
|---|---|---|
| **F1** Lockerungen an Regel-Versuchskopien erproben, wer wertet aus? | Ja, maximal autonom; die Host-Session des Agenten liest die Berichte | Owner-Wort; Grenzen in §4.1 |
| **F2** Anteil am Abo-Kontingent? | Beliebig, ohne Gesamtdeckel; Owner erhält jeweils den Stand | Owner-Wort; Wochenstand §4.5 Schritt 7 |
| **F3** Werkstücke je Review-Sitzung? | 5 Werkstücke und 2 Schutzregel-Vorschläge (Owner bestätigt) | Vorschlag des Agenten auf Owner-Bitte: hält die Sitzung kurz und liefert in zwei Pilotwochen bis zu 10 Entscheide, genug für die Mindestfallzahl 6 von B3 |
| **F4** `tools/sandbox/` in die Governance-Pfade? | Ja, Pflicht vor Phase 3 (Owner bestätigt) | Vorschlag des Agenten auf Owner-Bitte: dort liegt die Auswertung, die sonst mit einfachem Mandat änderbar wäre; erst vor Phase 3, damit der Aufbau in Phase 1 nicht an jeder Änderung auf den Owner wartet; umgesetzt in #3731 |

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-10-04 | Achim Dehnert | Initial: Status Proposed |
| 2026-10-04 | Achim Dehnert | Überarbeitet nach zwei externen Review-Runden (§9.1, §9.2): B1 neu definiert, B5 geteilt, Auftragskarte und Übernahmebeleg, Rückweg, Pilot-Gates; Korrekturen zu B1-Quote, Secret-Scan und Governance-Pfaden |
| 2026-10-04 | Achim Dehnert | Owner-Entscheide F1–F4 eingetragen (§9.3); Wochenstand an den Owner (§4.5) |
| 2026-10-05 | Achim Dehnert | Phase 1b nachgetragen (§4.3): Egress, Secret-Scan, Host-Kontext, Spiegel; Hooks belegt; Owner-Entscheide S2 (enges Token statt Org-Sperre, Free-Plan) und D1 a (Dependabot-PRs beim Auffrischen schließen); Gegentest „kein Repo anlegen“ in §8.2 |
| 2026-10-05 | Achim Dehnert | Nachzug aus Retro eb9de7 (#3724): Profil-Negativtests belegt (#3721); F4 umgesetzt (#3731); Head-Pin und Actions-Neumessung vor dem Merge (§4.4, #3736); Rate-Limit in der Selbstprüfung (#3738); Live-Merge-Test S9 in die Checkliste §4.7 |
| 2026-10-05 | Achim Dehnert | Phase 1b abgeschlossen: S9 bestanden (§4.7), Free-Plan-Antwort der Rulesets-Abfrage gilt als „keine Regel“ (#3747) |

---

<!--
  Drift-Detector-Felder (ADR-059):
  - staleness_months: 6
  - drift_check_paths:
      - platform/tools/sandbox
      - platform/tools/pr_merge_sa.py
      - platform/tools/gate_drill_check.py
      - platform/docs/governance/gates
  - supersedes_check: true
-->
