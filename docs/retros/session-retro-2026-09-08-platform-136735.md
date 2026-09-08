---
retro_schema: 1
date: 2026-09-08
repo_scope: [platform, robo-lab, mcp-hub]
session_id: 136735
footprint: full
footprint_reduction_reason: "deep-Trigger (3 Repos + prod-nahe Eingriffe) auf full reduziert: (a) jeder Prod-Schritt einzeln per Owner-Zuruf freigegeben, Zitate im Scope-Vermerk platform#2544 15:37Z; (b) voll rollback-faehig, keine DB-Migration, Sicherung je geaenderter Datei; (c) findings-Schaetzung <=10 (tatsaechlich 14)."
findings_total: 14
findings_survived: 11
refuted_rate: 0.21
phase3_refuted: 3
pre_refuted: 0
scores:
  zielerreichung: 3
  architektur_design: 4
  code_konventionstreue: 3
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [antwort-auf-beratungsfrage-nicht-verankert, dienst-fehlt-im-port-register, sot-datei-zitiert-aber-nicht-gelesen]
recurring_findings: [scope-checkpoint-not-durably-recorded, untested-command-handed-to-user, host-fix-not-mirrored-to-iac, gate-approval-needs-pr-comment]
gates_caught: [untested-command-handed-to-user, scope-checkpoint-not-durably-recorded]
over_ask_klassen: []
over_act_klassen: [host-speicherdeckel-zweite-stufe-ohne-freigabe]
widerlegung: "3 gekippt, 2 reaktiviert, 2 neu"
streichkandidaten: [hosts-yaml-ausnahme-ohne-ports-yaml-eintrag]
---

# Session-Retro 2026-09-08 — GX10-Doppelrolle (Inferenz + Training)

## 1. Executive Summary

- Aus einer **Kaufberatung** (Amazon-Mini-PC gegen ASUS GX10) wurde eine Messreihe ueber drei Repos und zwei Owner-Rechner. Jeder Eskalationsschritt war freigegeben, der Scope-Spiegel kam aber **6,5 Stunden nach dem ersten Eingriff an fremder Hardware**.
- Die **Antwort** auf die Ausgangsfrage steht in keinem der drei Repos: 0 Preis-/Empfehlungsmarker (Positivkontrolle: dieselbe Suche findet die Durchsatzzahlen 2x, platform#2544).
- Fachlich substanziell: Mehrbenutzer-Durchsatz erstmals gemessen (Ollama 1.906 → 2.632 tok/s nach Konfiguration, vLLM 3.526), VRAM-Grenze der 4090 eingegrenzt (16.384 laeuft, 20.480 nicht).
- **Der teuerste Einzelfehler:** Der 12-GB-Deckel der WSL-Maschine stand seit dem 2026-09-07 in `infra/hosts.yaml` Zeile 166 — dieselbe Datei, die der neue Code zitiert. Ein Blick hinein haette den ersten Fehllauf und die Fehlfaehrte „sieht aus wie ein Grafikspeicher-Problem" erspart.
- **Der folgenreichste:** Der neue Dauerdienst fehlt in `infra/ports.yaml` — der Datei, die `hosts_audit.py` tatsaechlich liest. Der urspruenglich vorgeschlagene Fix zielte auf `hosts.yaml` und haette einen dritten toten Eintrag erzeugt.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Ausgangsfrage in keinem Artefakt dokumentiert | Kommunikation | hoch | REFUTED | Scope-Vermerk platform#2544 15:37Z nennt sie wortwoertlich | — |
| 2 | **Antwort** auf die Kaufberatung nirgends verankert | Kommunikation | hoch | SURVIVES | platform#2544 (6 Kommentare) + robo-lab#58 + `docs/gx10-training.md`: 0 Treffer kauf/preis/amazon; Positivkontrolle: Durchsatzzahlen 2x | neu |
| 3 | Scope-Spiegel 6,5 h nach erstem Fremdhardware-Eingriff | Prozesslücke | mittel | SURVIVES | erster Eingriff robo-lab#58 09:00:16Z (`.wslconfig`, Box mit `ci-gpu`-Runner), Spiegel platform#2544 15:37:58Z | `scope-checkpoint-not-durably-recorded` |
| 4 | Scope-Vermerk zaehlt zwei Neustarts, es waren drei | fehlende Validierung | niedrig | SURVIVES | `.wslconfig` = `memory=64GB`, mtime 16:28:53; laufende WSL meldet 62 GB (bei 100-GB-Deckel waeren es 98) ⇒ Neustart nach 16:28 belegt | — |
| 5 | Neuer Dauerdienst in keinem Register | Governance | hoch | SURVIVES | `hosts.yaml` gx10-Block: 0 Treffer `vllm`/`NUM_PARALLEL`, Positivkontrolle 7x `ollama`/`embedder`; kein Schemazwang, aber Praezedenz `embedder`+`ollama` | `host-fix-not-mirrored-to-iac` |
| 6 | Doku behauptet erledigt, was das Issue offen fuehrt | Beweisdisziplin | mittel | SURVIVES | robo-lab#58 letzter Kommentar 11:17Z fuehrt 64 GB als offenen Owner-Entscheid, Issue bis heute OPEN; Vollzug steht nur in platform#2544 — anderes Repo | `gate-approval-needs-pr-comment` |
| 7 | Speicheranteil 0,30 ohne Herleitung | verfrühte Festlegung | niedrig | SURVIVES | `--gpu-memory-utilization 0.30` erscheint einmal (platform#2544 15:01Z), kein Vergleichswert, keine Begruendung | — |
| 8 | Ollama-Vergleichszahlen sind Einzellaeufe | fehlende Validierung | niedrig | SURVIVES | 1.906/2.632/2.850 je ein Lauf ohne Streuung; die vLLM-Zahl liegt dagegen aus 3 Laeufen vor (3.522/3.493/3.526, Abweichung 0,8 % ausgewiesen) | — |
| 9 | CI von mcp-hub#262 blockiert | Werkzeug/Umgebung | hoch | SURVIVES | 3 von 4 Runnern (`ci-nonprod`) offline, nur `prod-server` online; PR-Diff beruehrt kein `.github/` | — |
| 10 | Zweite Deckel-Anhebung ohne Freigabe-Formel | Prozesslücke | mittel | SURVIVES | robo-lab#58: „Owner-Freigabe" nur beim ersten Schritt, zweiter im Praeteritum berichtet | `over_act` |
| 11 | SoT-Datei zitiert, die entscheidende Zeile nicht gelesen | Beweisdisziplin | mittel | SURVIVES | `infra/hosts.yaml:166` fuehrt seit 2026-09-07 `WSL2: 8 vCPU / 12 GB`; derselbe Lauf zitiert dieselbe Datei im Code-Kommentar | neu |
| 12 | Branch nach Merge stehen geblieben | Werkzeug | niedrig | REFUTED | robo-lab `delete_branch_on_merge: false`; 6 von 25 gemergten Branches ueberleben — Repo-Vorgabe, keine Abweichung | — |
| 13 | Dienst fehlt im Port-Register, Port undeklariert | Governance | hoch | SURVIVES | `ports.yaml` kennt auf gx10 nur `embedder` (8100); `hosts_audit.py check_auflage` iteriert `ports["services"]` — „Was ports.yaml nicht kennt, kann diese Pruefung nicht sehen"; 8000 liegt im Band „Reserviert: BF Agent/Infra-APIs" und ist auf gpu-box ComfyUI | neu |
| 14 | Register beschreibt die geaenderte Box weiter falsch | Governance | mittel | SURVIVES | `hosts.yaml:166` sagt weiterhin `12 GB`, real seit 08.09. 64 GB / 24; `verified: 2026-08-30` unangetastet | `host-fix-not-mirrored-to-iac` |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 3 | #2 — beide Issues vorangebracht, die Ausgangsfrage ohne Artefakt |
| architektur_design | 4 | mcp-hub#262 folgt exakt dem Nachbarmuster, Naht `resolve_base_url` testbar |
| code_konventionstreue | 3 | #13 — `hardcoded-ok`-Konvention formal eingehalten, aber eine undeklarierte Portvergabe in Code eingefroren |
| risiko_debt | 2 | #5, #13, #14 — Dauerdienst in keinem Register, Port undeklariert, Registerzeile seit heute falsch |
| prozess_effizienz | 3 | #3, #10, #11 — zwei Deckel-Runden, Spiegel spaet, ein vermeidbarer Fehllauf |
| entscheidungsqualitaet | 3 | #11 — die eigene SoT zitiert und nicht gelesen; #7 ohne Herleitung |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Kaufempfehlung nur im Chat gegeben | Beratungsfrage bekommt beim ersten Messschritt ein Issue; Empfehlung dort mit Preis und Datum ablegen | #2 |
| Scope-Spiegel 15:37Z, erster Fremdeingriff 09:00Z | Spiegeln beim Uebertritt ins zweite Repo ODER vor dem ersten Eingriff an fremder Hardware — nicht am Turn-Ende | #3 |
| Vermerk zaehlt „zwei `wsl --shutdown`" | Zustandsketten aus den Uebergaengen zaehlen, nicht aus der Erinnerung | #4 |
| Dienst eingerichtet, kein Registereintrag | Dauerdienst + Eintrag im selben Zug — in **`ports.yaml`** (was `hosts_audit.py` liest), nicht nur `hosts.yaml` | #5 |
| Vollzug in platform vermerkt, Frage in robo-lab offen | Die Antwort dorthin schreiben, wo die Frage steht — ein Satz im fragenden Issue | #6 |
| `--gpu-memory-utilization 0.30` gesetzt | Wert aus einer Messung ableiten oder als vorlaeufig kennzeichnen | #7 |
| Ollama-Zahlen je ein Lauf | Auch die Vergleichsseite zweimal messen, nicht nur die favorisierte | #8 |
| PR aufgesetzt, CI haengt 88 min | Vor dem PR in Repos mit self-hosted CI einmal `gh api .../actions/runners` lesen | #9 |
| Zweiter Deckel-Schritt ohne eigene Freigabe | Jede weitere Stufe desselben Eingriffs neu gaten, nicht als Fortsetzung behandeln | #10 |
| Datei zitiert, Zeile 166 nie gelesen | Wer eine SoT-Datei zitiert, liest den Block des betroffenen Knotens einmal ganz | #11 |
| Port 8000 frei gewaehlt und in Code eingefroren | Portvergabe gegen `ports.yaml` pruefen, bevor sie als Vorgabe in Code steht | #13 |
| `hosts.yaml:166` nach der Aenderung nicht nachgezogen | Wer einen Host-Kennwert aendert, korrigiert die Registerzeile im selben Zug und setzt `verified` neu | #14 |

## 5. Laengsschnitt

`retro_kpis.py`: 43 Slugs mit Zaehler >=2 (Gate-Pflicht). Aus dieser Sitzung beruehrt:
- `scope-checkpoint-not-durably-recorded` — Gate existiert **und hat heute gefeuert**, fangt aber am Turn-Ende statt am Uebertritt. Konsequenz: **nachschaerfen** (Ursache an der Quelle).
- `untested-command-handed-to-user` — Gate hat gefangen (ssh-Befehle ohne Eigenlauf). Wirksamkeits-Beleg, kein Rueckfall.
- `host-fix-not-mirrored-to-iac` — steht in der `declined`-Liste (bewusst ohne Gate). Befunde #5 und #14 sind zwei weitere Vorkommen am selben Tag; die Nicht-Gate-Entscheidung gehoert dem Owner erneut vorgelegt.
- `gate-approval-needs-pr-comment` — Befund #6 ist derselbe Mechanismus: der Vermerk landete nicht dort, wo gelesen wird.

## 5a. Rueckfall-Pruefung

`gate_wirkung.py`: **kein Gate rueckfaellig.** Ein Gate hat seinen Befund gefangen (`untested-command-handed-to-user`, 1x). 17 Gates gelten als `zu-frueh` — dort ist ein ausbleibender Rueckfall kein Wirksamkeits-Beleg.

## 5b. Autonomie-Kalibrierung

- `over_ask`: keine. Alle 7 Vorlage-Stellen betrafen Prod-Konfiguration, Host-Eingriff oder Paketinstallation — Gate-Klassen.
- `over_act`: **eine**, Klasse `host-speicherdeckel-zweite-stufe-ohne-freigabe`. Die Anhebung 64→100 GB wurde als Fortsetzung behandelt; im Artefakt steht keine Freigabe davor, nur ein nachtraegliches „bitte entscheiden".

## 6. Verankerung (Vorschlaege — nicht selbst geschrieben)

```markdown
---
name: feedback_beratungsfrage_braucht_eigenes_artefakt
description: Eine Beratungs-/Vergleichsfrage, aus der Arbeit entsteht, bekommt ein eigenes Issue — sonst ist die Antwort nur im Chat
metadata:
  type: feedback
---
Wenn aus einer Beratungsfrage (Kauf, Auswahl, Vergleich) Messarbeit entsteht, bekommt die
FRAGE beim ersten Messschritt ein Issue, und die ANTWORT wird dort abgelegt.
**Why:** Am 2026-09-08 fuehrte eine Kaufberatung zu Messreihen ueber drei Repos; die
Messungen sind vollstaendig dokumentiert, die Kaufempfehlung in keinem der drei Repos
(0 Treffer kauf/preis/amazon, Positivkontrolle positiv).
**How to apply:** Vor dem ersten Messschritt ein Issue anlegen; am Ende Empfehlung mit
Zahl und Datum hineinschreiben. Verwandt: [[feedback_zwischenstand_mit_link]].
```

```markdown
---
name: feedback_dienst_gehoert_in_ports_yaml_nicht_nur_hosts_yaml
description: Ein neuer Dauerdienst wird in ports.yaml eingetragen — hosts_audit.py liest ports.yaml, nicht hosts.yaml
metadata:
  type: feedback
---
Wer einen Dienst dauerhaft auf einem Knoten einrichtet, traegt ihn in `infra/ports.yaml`
ein. Ein `auflage.ausnahmen`-Eintrag in `hosts.yaml` allein bleibt ungelesen.
**Why:** `hosts_audit.py check_auflage` iteriert `ports["services"]` — „Was ports.yaml
nicht kennt, kann diese Pruefung nicht sehen". Der bestehende `ollama`-Ausnahmeeintrag auf
gx10 ist deshalb heute schon tot; ein Eintrag fuer `vllm` waere der dritte gewesen
(2026-09-08). Zusaetzlich lag Port 8000 in einem reservierten Band und ist auf dem
Nachbarknoten bereits belegt.
**How to apply:** Dienst + `ports.yaml`-Eintrag im selben PR; Portvergabe vorher gegen die
Baender pruefen. Verwandt: [[feedback_host_fix_must_mirror_to_iac]].
```

```markdown
---
name: feedback_sot_datei_zitiert_heisst_nicht_gelesen
description: Wer eine SoT-Datei zitiert, liest den Block des betroffenen Knotens einmal ganz
metadata:
  type: feedback
---
Eine SoT-Datei im Kommentar zu zitieren ersetzt das Lesen nicht. Vor Messungen an einem
Knoten den kompletten Block dieses Knotens lesen.
**Why:** Am 2026-09-08 stand der 12-GB-Speicherdeckel der Workstation seit dem Vortag in
`infra/hosts.yaml` Zeile 166. Derselbe Arbeitsgang zitierte diese Datei im Code-Kommentar
eines PR. Der ungelesene Wert kostete einen Fehllauf und erzeugte die Fehldiagnose
„Grafikspeicher erschoepft". Verwandt: [[feedback_plan_premises_before_step_one]].
```

**adr_candidates:** keine — keine Architekturentscheidung; der Provider folgt bestehendem Muster (Schwelle `adr-threshold.md` nicht erreicht).

## 7. Massnahmen

siehe Action-Board in der Sitzungsantwort; Kernpunkte: `ports.yaml`-Eintrag fuer den neuen Dienst (#13), Registerzeile 166 korrigieren (#14), 64-GB-Entscheid in robo-lab#58 quittieren (#6), Kaufempfehlung verankern (#2).

## 8. Nicht verifiziert (Restluecken)

| offen geblieben | billigster Check |
|---|---|
| Ob `vllm` in weiteren Provider-Listen fehlt (`model_selector.py`, `check-model-liveness.py`) | `grep -rn vllm ~/github/mcp-hub/orchestrator_mcp/ scripts/` |
| Ob der GX10 40.960 Umgebungen traegt | ein Lauf, ~20 min |
| Ob die vLLM-Einzelstromzahl einen Kaltstartanteil enthaelt | Messung mit vorgeschaltetem Aufwaermlauf |
| Ob `music-lab` Ollama ueber Konfiguration statt Code nutzt | `grep -rn OLLAMA ~/github/music-lab --include=*.env* --include=*.yml` |
| Ob ein Modellfreigabe-Verfahren ausserhalb von platform existiert | Owner-Frage, kein Kommando |
| Zuordnung der Owner-Zurufe zu den Einzelschritten | existiert nur im Chat — nicht nachtraeglich herstellbar |

**getan:** Messreihen auf zwei Rechnern, zwei PRs, sieben Issue-Kommentare, ein Dienst eingerichtet, ein Speicherdeckel korrigiert.
**angenommen:** dass die Zurufe die jeweils genannten Punkte deckten.
**nicht verifizierbar:** die Zuordnung Zuruf→Punkt aus Artefakten.
**offen geblieben:** Verbraucher-Umstellung auf vLLM, CI von mcp-hub#262 (fremdverursacht), Punkte #2, #6, #13, #14.

## Widerlegung

Ein Widerleger (Tier 4, frischer Kontext, nur Report + Artefakte) hat das Urteil angegriffen. Ergebnis: **3 gekippt, 2 reaktiviert, 2 neu.**

| Punkt | Verdikt | Was der Widerleger fand |
|---|---|---|
| #8 Streuung fehlt | **GEKIPPT → eingeengt** | Die vLLM-Zahl liegt aus drei Laeufen vor (3.522/3.493/3.526) mit ausgewiesener Abweichung. Nur die Ollama-Seite ist Einzellauf. Severity mittel → niedrig |
| #12 Branch offen | **GEKIPPT** | `delete_branch_on_merge: false` in robo-lab; 6 von 25 gemergten Branches ueberleben. Die Stichprobe „0 von 7" traf die falsche Vergleichsgruppe |
| #7 ohne Befristung | **GEKIPPT → eingeengt** | Ein `bis` haengt am Ausnahme-Eintrag, nicht am Dienst; zwei Dauerdienste auf dev-desktop haben ebenfalls keins. Nur „0,30 unbegruendet" haelt |
| #11 frueherer Check | **REAKTIVIERT** | Vorherzusagen war nicht der Bedarf, sondern der **Deckel** — und der stand in `hosts.yaml:166` |
| #6 Doku vs. Issue | **REAKTIVIERT** | Der Widerspruch ist nicht zeitlich, sondern **oertlich**: die Frage steht in robo-lab#58 (bis heute offen), der Vollzug in platform#2544 |
| #13 Port-Register | **NEU** | `hosts_audit.py` liest `ports.yaml`, nicht `hosts.yaml`. Der urspruengliche Memory-Kandidat haette einen dritten toten Eintrag erzeugt |
| #14 Registerzeile falsch | **NEU** | `hosts.yaml:166` beschreibt die Box weiter mit 12 GB — seit heute unwahr |

Der Widerleger konnte #4 nicht entscheiden (dritter Neustart aus Artefakten nicht belegbar) und nannte den billigsten Check. Der wurde danach gefahren: `.wslconfig` auf 64 GB seit 16:28:53, laufende WSL meldet 62 GB ⇒ Neustart belegt, #4 haelt mit hartem Beleg.

## Streichbahn

**Kandidat:** `hosts-yaml-ausnahme-ohne-ports-yaml-eintrag` — Belegart **kein Leser**.

`hosts_audit.py check_auflage()` iteriert ausschliesslich `ports["services"]`; der Docstring sagt es wortwoertlich: „Was ports.yaml nicht kennt, kann diese Pruefung nicht sehen." Der `ollama`-Ausnahmeeintrag im gx10-Block wird damit von keinem Lauf konsultiert, weil `ollama` in `ports.yaml` nicht existiert. Ein `auflage.ausnahmen`-Eintrag fuer einen Dienst ohne `ports.yaml`-Eintrag ist Dekoration.

**Konsequenz (Owner-Zug):** entweder die betroffenen Dienste in `ports.yaml` nachtragen — dann wird der Ausnahmemechanismus wirksam — oder Ausnahme-Eintraege ohne Port-Eintrag als unzulaessig markieren, damit niemand einen wirkungslosen Griff fuer erledigt haelt.
