---
retro_schema: 1
date: 2026-09-23
repo_scope: [platform, mcp-hub, news-hub]
session_id: 3bdc4e
footprint: deep
findings_total: 14
findings_survived: 8
refuted_rate: 0.43
phase3_refuted: 6
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [fixture-ohne-konsument, required-check-zeigt-auf-schwaecheren-lauf]
recurring_findings: [inline-heredoc-quoting-rework, deferred-item-no-tracking-issue, stale-local-clone-as-ground-truth]
gates_caught: [claim-before-cheapest-check, check-ohne-positivkontrolle, deferred-item-no-tracking-issue]
over_ask_klassen: []
over_act_klassen: [prod-env-flip-ohne-zitat]
widerlegung: "3 gekippt, 2 neu"
streichkandidaten: []
streich_begruendung: "Jede Phase veraenderte ein Ergebnis (0.0 -> Ausweitung gate_wirkung.py, Skeptiker kippten 6 von 11, Meta fand 3 Formfehler); die einzige stille Phase 2.5 hat ueber fruehere Reports belegte Treffer — keine der vier Belegarten anwendbar."
---

# Session-Retro 2026-09-23 — platform / mcp-hub / news-hub (3bdc4e)

## 1. Executive Summary

- Die Sitzung begann als Übergabe (#3375, Technologiescreening) und endete bei einer Reparatur der Gedächtnis-Suche: Trefferquote auf Platz 1 von **48 % über 82 % auf 89 %**, jeweils an 141 echten Anfragen durch die laufende Suche in Produktion beobachtet. **Beobachtet heißt hier nicht nachrechenbar:** der Auswerter ist nicht committet, deshalb kann die Zahl heute niemand außer mir wiederholen (Befund 6). Das ist der Unterschied zwischen „gemessen" und „belegt", und er ist der Sitzung erst in dieser Retrospektive aufgefallen.
- Die Ursache war seit Monaten unsichtbar: ein ungültiger Einbettungs-Schlüssel ließ jede Suche still auf Volltext zurückfallen — 637 Logzeilen, gelesen von niemandem.
- **Die Verbesserung hat einen Preis, der in keinem Befund stand:** das neue Modell schneidet bei 2.000 Zeichen ab. **555 der 1.370 Einträge (40,5 %)** sind länger; 779.537 Zeichen gehen nie in einen Vektor ein, und ein Rückbau ist unmöglich (beide alten Schlüssel sind tot). Für lange Einträge kann die Suche jetzt selbstbewusst falsch antworten. Gefunden hat das erst die Widerlegungsbahn (Befund 14, mcp-hub#292).
- **Zwei eigene Vorschläge fielen bei der eigenen Messung**, bevor sie gebaut wurden (Richtlinien-Ausschluss, Längen-Argument). Der schwerste Vorwurf gegen mich — verschwiegener Auslöser der gx10-Lockerung — wurde vom Skeptiker widerlegt und von der Widerlegungsbahn **wieder aufgerichtet**: die Widerlegung hatte in Repo-Dateien gesucht statt in den Issues derselben Sitzung, wo „meiki-lra" fünfmal steht.
- Was hält: eine Prüfliste ohne Konsument, eine Dublette ohne Tracking, ein Prod-Flip ohne durables Freigabe-Zitat, ein verschwiegener Auslöser — und zwei Funde, die kein Finder hatte: die gx10 trägt jetzt das Gedächtnis der ganzen Flotte, während `hosts.yaml` weiter „kein Prod-Deploy" sagt, und der Required Check in `mcp-hub` zeigt auf den **schwächeren** von zwei Testläufen.
- Dreimal an einem Tag Heredoc auf Repo-Dateien, obwohl die Regel nach dem 5. Vorkommen „nicht mehr weich" sein sollte. Der Registry-Eintrag steht auf `declined`.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Der Auftrag aus #3375 ist nur zur Hälfte geliefert: die wöchentliche Vorschlags-Komponente ist nicht gebaut. | Prozesslücke | mittel | **REFUTED** (Phase 3b) | Das Staffeln war die Entscheidung, nicht ihr Ausbleiben: #3383 (eröffnet 15:18:42Z) sagt im ersten Satz „Stufe 1 … wird **nicht** gebaut, bevor gemessen ist"; KONZ-063 §13 führt K5 als „erteilt 2026-09-22"; #3375 ist `closedAt 15:38:40Z` und trägt `cross-referenced → 3383` | — |
| 2 | Der Scope-Spiegel in #3383 nennt drei Repos, während 15 s zuvor mcp-hub#278 eröffnet wurde. | Prozesslücke | hoch | REFUTED | Spiegel ist ausdrücklich auf Stufe 1 von KONZ-063 begrenzt; mcp-hub gehört nicht zu deren Bauumfang | — |
| 3 | mcp-hub#278 bleibt offen, obwohl sechs zugehörige PRs gemergt sind. | Kommunikation | niedrig | REFUTED | Alle sechs PRs tragen „Refs #278"; Issue-Text weist sich als Sammel-Issue aus, Arbeit darin nachweislich offen | — |
| 4 | Die Aufhebung der gx10-Datenklassen-Auflage (#3413) hatte einen technischen Auslöser, den das Artefakt verschweigt. | Entscheidungs-Transparenz | **hoch** | **SURVIVES** (Phase 3b, Widerlegung gekippt) | Die Widerlegung suchte in Repo-Dateien; in mcp-hub#278 steht „meiki-lra" fünfmal, u.a. 02:58:54Z „aktive Einträge mit Org-Kennung `meiki-lra`: 20" und 03:48:49Z die Auflage als Hindernis. Kette am 23.09.: 02:58 Befund → 03:48 Auflage als Hindernis benannt → **04:03 #3413 eröffnet** → 04:24 Provider ist die gx10. In #3413, KONZ-053 Rev 1 und `hosts.yaml` kommt davon nichts vor | — |
| 5 | Das Kill-Gate in KONZ-063 wurde überstimmt (K3 nicht erfüllt, K5 trotzdem erteilt). | verfrühte Festlegung | hoch | REFUTED | K5 ist im selben Kill-Gate als Owner-Entscheidungskriterium angelegt; die Lücke ist im Dokument wörtlich offengelegt („sie wurden überstimmt, bewusst") | — |
| 6 | Die Prüfliste `gedaechtnis_goldset.json` (141 Fälle) hat **keinen Konsumenten**: kein Test, kein Skript, kein Make-Target liest sie. Die Zahlen 48/82/89 % stehen nur als Kommentar. | fehlende Validierung | **hoch** | **SURVIVES** | `git grep -in goldset` in mcp-hub → nur Docstring-Nennungen; PR #289 behauptet dennoch „ab jetzt misst sich jede Änderung daran" | neu (Familie `melder-ohne-leser`) |
| 7 | `EmbedderServiceClient` dupliziert `rag_mcp/embedder.py` bewusst, ohne Tracking-Artefakt. | Prozesslücke | mittel | **SURVIVES** | `embeddings.py` Docstring „Bewusste Dublette"; Issue-Suche über embedder/Dublette → kein Treffer | `deferred-item-no-tracking-issue` ×46 |
| 8 | Der Prod-Flip des geteilten Gedächtnis-Speichers hat kein durables Freigabe-Zitat, obwohl andere Entscheidungen derselben Sitzung wörtlich festgehalten sind. | Prozesslücke | mittel | **SURVIVES** | mcp-hub#278: genau ein als Owner-Wort markiertes Zitat, und das gilt einer anderen Entscheidung | `scope-checkpoint-not-durably-recorded` ×32 |
| 9 | Handkopie der systemd-Dateien auf den Prod-Host ohne Zweitprüfung. | Prod/Governance | hoch | REFUTED | In #290 offengelegt, begründet und getrackt; Inhalt stimmt mit `origin/main` überein; die fehlende Zweitprüfung ist kein Sonderfall dieses Schritts (siehe #10) | `stale-local-clone-as-ground-truth` ×10 |
| 10 | In `mcp-hub` ist als Required Check nur `🚦 Quality Gate` gesetzt — der **schwächere** von zwei sich überlappenden Testläufen. Der harte Lauf hätte einen Merge nicht gehalten; dazu erlaubt das Ruleset `bypass_mode: always`, sechs PRs gingen ohne Review durch. | fehlende Validierung | **hoch** | **SURVIVES** (Phase 3b, Hälfte korrigiert) | Ruleset 17621473 gegen platform 17621471; `mcp-quality.yml:141` führt `pytest … \|\| true`, aber nur über die Matrix `[deployment_mcp, llm_mcp]` — **orchestrator_mcp ist nicht darin**. Dessen Tests liefen hart in `ci.yml:79/127` gegen echtes Postgres und sind auf #281/#289 grün (57 s), nur eben nicht required | neu |
| 11 | KONZ-063 wurde in acht aufeinanderfolgenden PRs geändert — vermeidbarer CI-Overhead. | Prozess/Rework | niedrig | REFUTED | Merge-Zeitstempel #3388 (16:27) folgt auf Owner-Kommentar in #3383 (16:24), #3397 auf „33 go" (19:28); keine zeitliche Überlappung, PRs streng aufsteigend 22.09. 15:38 bis 23.09. 02:21; CI je 6–25 s | — |
| 12 | Die Restarbeit an Stufe 1 (news-hub) war terminiert, hatte aber kein eigenes Tracking-Artefakt; die Maßnahmenliste dieses Berichts zeigte zunächst auf news-hub#74, das ein anderes Thema führt. | Prozesslücke | niedrig | **SURVIVES** (Phase 3b, Restdefekt aus #1) | news-hub#74 = „Zweite Web-Naht: latent.space-Feed"; Suche über news-hub nach Register/Wochen/Screening → kein weiterer Treffer. Behoben im selben Zug: [news-hub#76](https://github.com/achimdehnert/news-hub/issues/76) | `deferred-item-no-tracking-issue` ×46 |
| 13 | Die gx10 trägt seit dieser Sitzung das geteilte Gedächtnis der gesamten Flotte, während `hosts.yaml` sie weiter mit `prod_container: false` und „kein Prod-Deploy" führt. | Prod/Governance | **hoch** | **SURVIVES** (Phase 3b, neu) | `hosts.yaml` gx10-Block unverändert nach #3413; mcp-hub#278 08:38:46Z „1.370 Einträge in 63 Sekunden"; `rag_mcp` hängt seit 2026-09-01 (71f2f61) am selben Endpunkt. Dieselbe Datei wurde an dem Tag angefasst — um eine Auflage zu entfernen, nicht um die Abhängigkeit zu notieren. [#3440](https://github.com/achimdehnert/platform/issues/3440) | neu |
| 14 | Die Umstellung hat 40,5 % des geteilten Gedächtnisses irreversibel verkürzt; der Bericht verkaufte das als 48 → 89 %. | fehlende Validierung | **hoch** | **SURVIVES** (Phase 3b, neu) | mcp-hub#278 08:38:46Z: 512-Token-Fenster, Vektor eines 32.027-Zeichen-Eintrags identisch mit seinen ersten 2.000 Zeichen (1,0000); 555 von 1.370 Einträgen betroffen, 779.537 Zeichen. Vormodell hatte 8.000 Token; Rückbau unmöglich (beide Schlüssel 401). [mcp-hub#292](https://github.com/achimdehnert/mcp-hub/issues/292) | neu |

## 3. Scorecard

| Dimension | Wert | Verankerung |
|---|---|---|
| zielerreichung | 4 | Befund 1 widerlegt — der Auftrag wurde geliefert und der Rest bewusst gegatet; Abzug für Befund 12, das Gate hatte kein eigenes Artefakt |
| architektur_design | 3 | Befund 13 — die Wahl des Dienstes folgt ADR-188, aber ihre Betriebsfolge steht in keinem Infrastruktur-Artefakt; das Gerät gilt dort weiter als prod-frei |
| code_konventionstreue | 3 | Befund 7 — die Hausregel „bewusst Ausgelassenes bekommt sofort ein Tracking-Artefakt" wurde verletzt; dazu dreimal Heredoc auf Repo-Dateien (§5, `inline-heredoc-quoting-rework`) |
| risiko_debt | 2 | Befund 14 — ein irreversibler Verlust von 40,5 % des Gedächtnisses lief als Absatz im Sammel-Issue mit, nicht als Vorgang; dazu Befunde 6/7. Die Gutschrift „#7 in der Sitzung geschlossen" trägt nicht: mcp-hub#291 ist offen und selbst ein Retro-Artefakt |
| prozess_effizienz | 4 | Befund 11 widerlegt; die Kette Messen → Vorschlagen → Bauen hat zweimal einen Fehlbau verhindert |
| entscheidungsqualitaet | 3 | Befund 5 widerlegt (Kill-Gate offen überstimmt, nicht umgangen) — aber Befund 4 hält: der technische Auslöser der gx10-Lockerung steht in keinem ihrer Artefakte |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Die Lockerung der gx10-Auflage (#3413) nennt als Anlass nur den Owner-Satz; dass 15 Minuten zuvor 20 `meiki-lra`-Einträge als Hindernis für den eigenen Umbau benannt worden waren, steht in keinem ihrer Artefakte | Ändert ein Schritt eine Auflage, von der die **eigene** laufende Arbeit abhängt, gehört dieser Zusammenhang in den ersten Absatz des PR-Bodys — nicht weil er die Entscheidung kippt, sondern weil ihr Prüfer ihn sonst nicht sieht | #4 |
| Die Prüfliste wurde als Fixture committet und im PR als künftige Regressionsprobe bezeichnet, aber kein Code liest sie (`git grep goldset` → nur Docstrings) | Eine Fixture wird **gemeinsam mit ihrem Konsumenten** committet: der Auswerter, der die Quote berechnet, gehört in denselben PR — sonst ist die Zahl im PR-Text eine Behauptung ohne Nachrechnung | #6 |
| Die Dublette zu `rag_mcp/embedder.py` wurde im Docstring benannt und damit als erledigt behandelt | Beim Satz „das wäre der sauberere Schnitt, aber …" im selben Zug ein Issue anlegen und **im Code darauf verweisen** — der Docstring nennt dann die Nummer, nicht nur die Absicht | #7 |
| Der Prod-Flip lief auf mündliche Freigabe, die anderswo (Chat) fiel und nirgends im betroffenen Issue landete | Vor dem ersten Host-Kommando das Freigabewort **wörtlich in das Issue schreiben, in dem der Schritt geführt wird** — dieselbe Regel, die für Merges längst gilt, auch für Env-/Host-Änderungen | #8 |
| Sechs PRs mit produktionskritischem Ranking-Code liefen ohne Review durch; als Required Check war der advisory-Lauf gesetzt, der harte nicht | Vor dem ersten Merge in einem fremden Repo **die Required-Check-Liste gegen die Job-Liste halten** — nicht „läuft ein Testjob?", sondern „ist der, der läuft, der erzwungene?" | #10 |
| Die Restarbeit an Stufe 1 war im Konzept terminiert, aber in keinem Issue des ausführenden Repos geführt | Beim Staffeln eines freigegebenen Bauabschnitts im **Ziel-Repo** ein Issue mit Termin anlegen, bevor das Auftrags-Issue geschlossen wird — das Konzept ist kein Arbeitsvorrat | #12 |
| Ein Dienst auf einem als prod-frei geführten Gerät wurde zur Abhängigkeit der gesamten Flotte, und die Infrastruktur-Datei blieb unverändert — obwohl sie am selben Tag für eine Lockerung angefasst wurde | Wer eine Auflage in `hosts.yaml` ändert, prüft im selben Edit die **Rollenzeile** desselben Hosts gegen das, was dort gerade dazukommt | #13 |
| Das neue Modell schneidet bei 2.000 Zeichen ab; gemessen und im Sammel-Issue notiert, aber in keiner Bewertung, keinem Befund und keiner Maßnahme berücksichtigt | Eine Verbesserungszahl wird nur zusammen mit ihrem **Verlustposten** berichtet: wer „48 → 89 %" schreibt, schreibt „und 40,5 % der Einträge sind seither verkürzt" in denselben Absatz | #14 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 135 Reports:

| Slug | Zähler | Registry-Stand | Konsequenz |
|---|---|---|---|
| `claim-before-cheapest-check` | 89 | **gebaut, blocking** | in dieser Sitzung **dreimal gefangen** → `gates_caught`, nicht Rückfall |
| `deferred-item-no-tracking-issue` | 46 | **declined** | Befund 7 ist ein neues Vorkommen; ein `declined`-Eintrag mit 46 Vorkommen gehört überprüft |
| `scope-checkpoint-not-durably-recorded` | 32 | declined/offen | Befund 8 ist ein neues Vorkommen |
| `stale-local-clone-as-ground-truth` | 10 | — | mcp-hub#290 ist ein neues Vorkommen im Nachbar-Repo |
| `inline-heredoc-quoting-rework` | 5 | **declined** | **dreimal an einem Tag** — die Begründung des `declined` („weich") trägt nicht mehr |
| `check-ohne-positivkontrolle` | 3 | **gebaut** | in dieser Sitzung gefangen → `gates_caught` |

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` meldet **ein** rückfälliges Gate: `claim-before-cheapest-check` (gebaut 2026-09-17, blocking, 2 Vorkommen seit Bau).

**Einordnung nach Prüfung: kein Rückfall, sondern Wirkung.** Beide Vorkommen dieser Sitzung wurden vom Gate **gefangen** — der Hook hielt den Zug an, der Beleg wurde nachgezogen, die Aussage korrigiert. Ein Gate, das greift, darf nicht als gescheitert gezählt werden.

**Befund am Werkzeug, nicht am Gate:** `gate_wirkung.py` kann „wiederkehrend **und gefangen**" nicht von „wiederkehrend **und durchgerutscht**" unterscheiden. Es zählt Retro-Nennungen, nicht Interventionen. Solange das so ist, produziert es bei wirksamen Gates Fehlalarme — und ein Melder mit Fehlalarmen wird abgeschaltet. Konsequenz: **ausweiten** (das Werkzeug soll `gates_caught` aus dem Frontmatter abziehen), nicht das Gate umbauen.

## 5b. Autonomie-Kalibrierung

- `over_ask`: keine. Rückfragen betrafen durchgängig Gates (Prod, drittes Repo, Regel-Änderung) oder echte Owner-Entscheidungen.
- `over_act`: **eine Klasse** — `prod-env-flip-ohne-zitat`: der Umschalter in `.env.prod` samt Neu-Einbettung wurde ausgeführt, nachdem die Freigabe mündlich fiel, aber ohne sie im führenden Issue festzuhalten (Befund 8). Erste Nennung dieser Klasse; bei einer zweiten ist die Gate-Liste in `feedback_autonomy_charter` zu schärfen.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: feedback_fixture_ohne_konsument
description: "Eine Prüfliste/Fixture ohne Konsument ist eine Behauptung, keine Regressionsprobe — Auswerter gehört in denselben PR"
metadata: {node_type: memory, type: feedback, drift: true, drift_episode: 2026-09-23-goldset-ohne-leser}
---
Eine committete Fixture beweist nichts, solange kein Test, Skript oder Make-Target sie liest.
Am 2026-09-23 wurde `gedaechtnis_goldset.json` (141 Fälle) committet und im PR als „ab jetzt
misst sich jede Änderung daran" bezeichnet — `git grep goldset` fand ausschließlich Docstrings.
Die Quoten 48/82/89 % stammen aus einem Ad-hoc-Lauf und sind aus dem Repo nicht nachrechenbar.
**Why:** Dieselbe Familie wie [[melder-ohne-leser]]: das Artefakt existiert, der Leser fehlt.
**How to apply:** Fixture und Auswerter im selben PR; die Zahl im PR-Text muss durch einen
committeten Befehl reproduzierbar sein.
```

```markdown
---
name: feedback_required_check_zeigt_auf_schwaecheren_lauf
description: "Laufender Testjob ≠ erzwungener Testjob — in mcp-hub ist der advisory-Lauf required, der harte nicht"
metadata: {node_type: memory, type: feedback, drift: true, drift_episode: 2026-09-23-required-check-schwaecherer-lauf}
---
In `achimdehnert/mcp-hub` laufen zwei sich überlappende Testläufe: `ci.yml` prüft jedes Paket
einzeln und hart (`Tests — orchestrator_mcp`, echtes Postgres, kein `|| true`), `mcp-quality.yml`
führt `pytest … || true` über die Matrix `[deployment_mcp, llm_mcp]`. Required ist **nur**
`🚦 Quality Gate` — also der advisory-Lauf über zwei von sieben Paketen. Ein rotes
`Tests — orchestrator_mcp` hält den Merge nicht. Dazu erlaubt Ruleset 17621473 dem Owner
`bypass_mode: always`; `platform` hat `bypass_actors: []`.
**Why:** Die erste Fassung dieses Befundes las den `|| true`-Schritt und schloss daraus auf alle
Tests des Repos — die Matrix darüber war nicht gelesen. Der Fehler war nicht zu wenig Misstrauen,
sondern zu wenig Lesen: die richtige Frage ist nicht „läuft ein Testjob?", sondern „ist der, der
läuft, der erzwungene?".
**How to apply:** Vor dem ersten Merge in einem fremden Repo die Required-Check-Liste gegen die
Job-Liste des Workflows halten, nicht gegen das grüne Brett.
```

**adr_candidates** — keine. Alle Entscheidungen dieser Sitzung folgten bestehenden ADRs
(188, 304, 087, 299); neue Architekturentscheidungen wurden nicht getroffen.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Auswerter zur Prüfliste | mcp-hub | [#278](https://github.com/achimdehnert/mcp-hub/issues/278) | 🔵 | Skript committen, Quote nachrechenbar |
| 2 | Dublette entscheiden | mcp-hub | [#291](https://github.com/achimdehnert/mcp-hub/issues/291) | 🟢 | Paket oder bewusst behalten |
| 3 | Harten Testlauf required setzen | mcp-hub | [#278](https://github.com/achimdehnert/mcp-hub/issues/278) | 🟢 | Ruleset-Check umhängen |
| 4 | Heredoc-Regel entscheiden | platform | [#2234](https://github.com/achimdehnert/platform/issues/2234) | 🟢 | Gate bauen oder `declined` erneuern |
| 5 | Stufe 1 news-hub | news-hub | [#76](https://github.com/achimdehnert/news-hub/issues/76) | 🟢 | bis 2026-10-22 |
| 6 | Deploy bringt Host-Dateien | mcp-hub | [#290](https://github.com/achimdehnert/mcp-hub/issues/290) | 🟢 | entscheiden |
| 7 | `gate_wirkung.py` ausweiten | platform | — | 🔵 | `gates_caught` abziehen |
| 8 | gx10-Rolle in `hosts.yaml` | platform | [#3440](https://github.com/achimdehnert/platform/issues/3440) | 🟢 | Rolle ziehen oder Dienst verlegen |
| 9 | 555 verkürzte Einträge | mcp-hub | [#292](https://github.com/achimdehnert/mcp-hub/issues/292) | 🟢 | Stückelung oder Verzicht |

## 8. Nicht verifiziert (Restlücken)

- **Getan:** Wirkungsbilanz, Artefaktsammlung über drei Repos, drei Finder in frischem Kontext, drei Skeptiker, eine Widerlegungsbahn (Tier 4), Live-Nachmessung der Suche in Produktion (141 Fälle, dreimal). Die vier tragenden Behauptungen der Widerlegungsbahn wurden vor Übernahme eigenständig nachgeprüft.
- **Angenommen:** dass die in Issues zitierten Owner-Worte den Kapitäns-Kanal korrekt wiedergeben — die Prüfer konnten nur die Zitate prüfen, nicht ihre Quelle.
- **Nicht verifizierbar:** der Chatverlauf selbst (kein Zugriff für die Prüfer). Damit bleibt offen, ob die gx10-Lockerung (#3413) durch den eigenen Umbau **motiviert** war — belegt ist nur, dass beides 15 Minuten auseinanderliegt und dass der Zusammenhang in keinem Artefakt steht. Billigster fehlender Check: der Kapitäns-Kanal zwischen 03:48 und 04:03.
- **Offen geblieben:** die Zahlen aus platform#3402 (`retro_kpis.py`-Auswertung) wurden von keinem Prüfer nachgerechnet; KONZ-053 nur in Diff-Auszügen gelesen. Ob die 20 `meiki-lra`-Einträge neu eingebettet wurden, stand hier zunächst als „nicht verifizierbar" — es war im eigenen Sammel-Issue beantwortet (1.370 von 1.370).

## Widerlegung

Ein Prüfer mit frischem Kontext (Tier 4), der nur den Entwurf, den Footprint und die Artefaktliste sah, hat das Urteil dieser Retrospektive angegriffen. **Drei Urteile gekippt, zwei Befunde neu.** Alle vier tragenden Behauptungen habe ich vor der Übernahme selbst nachgeprüft (`gh issue view`, `git show origin/main`).

| Punkt | Verdikt | Beleg |
|---|---|---|
| Befund 1 „nur zur Hälfte geliefert" | **GEKIPPT** | #3375 `closedAt 15:38:40Z`, #3383 ist das Tracking, K5 „erteilt" — das Staffeln war die Entscheidung |
| Befund 10 „Tests mit `\|\| true`" | **GEKIPPT** (Hälfte) | `mcp-quality.yml:141` gilt der Matrix `[deployment_mcp, llm_mcp]`; `orchestrator_mcp` lief hart in `ci.yml:127`, grün in 57 s |
| Befund 4 „Auslöser verschwiegen" | **GEKIPPT** (Widerlegung fiel) | „meiki-lra" steht fünfmal in den Kommentaren von mcp-hub#278 — die Widerlegung hatte Repo-Dateien durchsucht |
| Befunde 6, 7, 8 | BESTÄTIGT | Goldset: 141 Fälle, 16 Repos, kein Leser; #291 offen und selbst Retro-Artefakt; kein Freigabewort deckt den Flip |
| Befunde 2, 3, 5, 9, 11 | BESTÄTIGT | kein Gegenbeleg aus den Artefakten |
| **N1** gx10 trägt Prod, `hosts.yaml` sagt nein | **NEU** → Befund 13 | Block unverändert nach #3413; `rag_mcp` hängt seit 2026-09-01 am selben Endpunkt |
| **N2** 40,5 % verkürzt, kein Rückbauweg | **NEU** → Befund 14 | 555 von 1.370 Einträgen, 779.537 Zeichen; Vormodell hatte 8.000 Token |

**Die härteste Korrektur betrifft die Methode, nicht den Inhalt.** Zwei der drei gekippten Urteile fielen, weil der jeweilige Prüfer am falschen Ort gesucht hat: der Skeptiker zu Befund 4 griff Repo-Dateien statt der Issues derselben Sitzung, der Finder zu Befund 10 las einen `pytest`-Aufruf ohne die Matrix darüber. Beide Male war der Befund sprachlich sauber belegt und trotzdem falsch. Ein Beleg ist erst einer, wenn er am Ort der Behauptung gezogen wurde.

Die Widerlegungsbahn hat außerdem eine meiner Restlücken aufgelöst: ob die 20 `meiki-lra`-Einträge neu eingebettet wurden, stand als „nicht verifizierbar, billigster Check ist ein `SELECT`" im Bericht. Es brauchte keine Datenbank — der Kommentar vom 08:38:46Z im eigenen Sammel-Issue sagt „1.370 von 1.370, 0 übrig". Der billigste Check war, den eigenen Beleg zu lesen.

## Streichbahn

**Kein Kandidat.** In diesem Lauf hat jede Phase ein Ergebnis verändert: die Wirkungsbilanz (0.0) führte zu der Entscheidung, `gate_wirkung.py` auszuweiten statt das gemeldete Gate umzubauen (§5a); die drei Finder lieferten 11 Behauptungen, die Skeptiker kippten davon 6; der Meta-Reviewer fand drei Formfehler im Entwurf, alle behoben. **Am deutlichsten die Widerlegungsbahn (3b):** sie kippte drei fertige Urteile — darunter eine Widerlegung, die selbst auf einem falschen Beleg stand — und fand zwei Befunde, die keiner der drei Finder hatte, davon den schwersten der Sitzung (40,5 % des Gedächtnisses verkürzt). Ohne diese Phase wäre der Bericht mit zwei falschen Verdikten und einer verschwiegenen Nebenwirkung herausgegangen.

**Die eine Phase ohne Ergebnis war 2.5 (Finder-Konflikte) — und sie überlebt die Prüfung.** Ein Lauf ohne Widerspruch belegt kein „kein Effekt": über die 137 Reports hat Phase 2.5 mehrfach entschieden, was sonst falsch im Bericht gestanden hätte — u.a. eine angebliche 5-Stunden-Deploy-Verzögerung, die sich als Zuordnung zum falschen PR erwies, und eine als „nirgends offen geführt" gemeldete stale Skill-Kopie, die im Abschluss-Board als Gate-Item stand. Eine Phase, die meist still ist und gelegentlich einen Falschbefund abfängt, ist billig und wirksam.

Keine der vier zulässigen Belegarten ließ sich sonst zeigen: kein Melder ohne Leser, kein wirkungsloses Gate, keine Dublette, keine Liegezeit. Ratsche gehalten — der Kandidat früherer Läufe (`retro-phase1-sammler`) ist seit 2026-09-16 gestrichen und wurde nicht wieder eingeführt.
