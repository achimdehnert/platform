---
retro_schema: 1
date: 2026-08-24
repo_scope: [platform]
session_id: 61e5fc
footprint: deep
findings_total: 11
findings_survived: 8
refuted_rate: 0.27
phase3_refuted: 2
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [partial-fix-not-generalized-to-sibling-artifacts, untested-command-handed-to-user, shared-gh-credential-overwritten-by-device-login]
recurring_findings: [partial-fix-not-generalized-to-sibling-artifacts, untested-command-handed-to-user, scope-checkpoint-not-durably-recorded, tracking-doc-stale-after-new-occurrence, claim-before-cheapest-check]
gates_caught: [claim-before-cheapest-check]
over_ask: 1
over_act: 0
---

# Session-Retro 2026-08-24 — platform, ADR-297-Strang (`61e5fc`)

## 1. Executive Summary

- **Auftrag erfüllt und weit überschritten:** aus „zwei externe Zweitmeinungen zu ADR-297 einarbeiten" wurde ADR angenommen, ADR-236 amendiert, ein Melder gebaut, die Registry an acht Stellen korrigiert, Org-Konfiguration in vier GitHub-Orgs geändert und ein Nutzer aus einer Kunden-Org entfernt. Jede Ausweitung ist per nummeriertem Board vom Owner abgenommen — aber **keine dieser Freigaben liegt in einem Artefakt**, nur im Chat.
- **Der schwerste Befund ist ein Fehler im gelieferten Werkzeug:** `check_c` im neuen Melder fehlt genau der Fallback, den `check_b` Stunden zuvor bekam — und er überspringt die Fälle lautlos, für die er gebaut wurde. Der Slug `partial-fix-not-generalized-to-sibling-artifacts` steht seit gestern als ungedeckte Gate-Pflicht auf der Liste.
- **Zwei Befehle, die der Owner ausführen sollte, funktionierten nicht** (2FA-PATCH, Audit-Filter). Beide liefen ohne Fehler durch und taten nichts. Beide wurden erst durch den Evidenz-Hook aufgedeckt, nicht durch mich.
- **Das `claim-before-cheapest-check`-Gate hat dreimal gefeuert und zweimal einen echten Defekt gefunden.** Es zählt als `gates_caught`, nicht als Rückfall — das ist der erste Sitzungsbeleg dafür, dass es trägt.
- **Zwei Befunde der Finder waren zu streng, nicht zu milde:** die Rework-Kaskade über drei PRs (die Realität änderte sich zwischen den PRs) und die Schwere der 2FA-Ausweitung (faktischer No-Op, keine dritte Person betroffen).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | `check_c` fehlt der `bekannte_konten`-Fallback, den `check_b` genau für diesen Fall bekam; bei `fetch → None` wird ohne Zählung übersprungen. Der Leitsatzverstoß — der einzige Zweck der Prüfung — verschwindet lautlos. | Logikfehler / Testlücke | **kritisch** | CONFIRMED | `git show origin/main:tools/org_zuordnung_melder.py` → `check_b` enthält `bekannte_konten` 1×, `check_c` 0×; `check_c` hat `if not antwort: continue` ohne `unerreichbar`-Liste | `partial-fix-not-generalized-to-sibling-artifacts` |
| 2 | `_gh_json` fängt weder `FileNotFoundError` noch `subprocess.TimeoutExpired`. Eine solche Exception endet mit Exit-Code 1 — laut eigenem Docstring „Fund", laut Workflow-Marker „ROT IST BEFUND". Ein Werkzeugfehler wäre von einem echten Fund nicht unterscheidbar. | Fehlerbehandlung | hoch | CONFIRMED | `grep -n except` liefert nur `json.JSONDecodeError` (Z. 146) und `(OSError, yaml.YAMLError)` (Z. 317, nur um `Registry.laden`) | `tool-error-indistinguishable-from-finding` |
| 3 | Org-weites Ruleset `default-branch-schutz` (ID 21308574) wurde live angelegt **und scharfgeschaltet**, bevor der dokumentierende PR #2272 gemergt war. ADR-297 §Durchsetzung kennt es nicht. `autonomy-gates.md` führt Security-Config als Gate; im Artefaktbestand liegt keine Freigabe. | Prozesslücke | mittel | SURVIVES | `git log -S "21308574" --all` → Commit `dad2807` auf offenem PR #2272; ADR-297 §Durchsetzung nennt drei Maßnahmen, kein Ruleset | `scope-checkpoint-not-durably-recorded` |
| 4 | Drei von fünf `owner_prefix_rules` sind tote Buchstaben: `sqf-` und `pg-` treffen null Repos, `bahn-` trifft genau `bahn-hub` — und das ist per Override ausgehebelt. Die als falsch erwiesene Regel wurde umgangen statt korrigiert. | Registry-Design / Tech-Debt | mittel | CONFIRMED | Auswertung von `registry/canonical.yaml`: `bahn-` → `['bahn-hub']`, davon per Override ausgehebelt `['bahn-hub']`; `sqf-`/`pg-` → `[]` | `workaround-without-tracking-anchor` |
| 5 | Drei Selbstkorrekturen in Issue #2263 an einem Nachmittag; zwei davon korrigieren **Befehle, die dem Owner zur Ausführung übergeben worden waren** und nicht funktionierten (2FA-PATCH auf ein Nur-Lese-Feld, Audit-Abfrage mit wirkungslosem `action:`-Filter). | fehlende Validierung | hoch | CONFIRMED | `gh issue view 2263 --json comments`: Korrekturen um 11:56:31, 13:28:36, 14:00:31 — letztere 1 Minute nach dem korrigierten Kommentar | `untested-command-handed-to-user` |
| 6 | Issues #2262 und #2263 bleiben `OPEN` mit Vormittags-Body („V3 → false", „0 Teams"), während ADR-297 dieselben Punkte als erledigt führt. Der ADR ist aktueller als sein eigenes Tracking-Artefakt. | Prozesslücke | mittel | CONFIRMED | `gh issue view 2262/2263 --json state` → beide `OPEN`; Bodies vs. ADR-297 §Offene Punkte (`~~erledigt~~`) | `tracking-doc-stale-after-new-occurrence` |
| 7 | PR #2271 wurde unter der Identität `wirdigital` erstellt, weil ein `gh auth login` für den Partner-Account das **geteilte** Credential in `~/.config/gh/hosts.yml` überschrieb. Betroffen sind alle `gh`-Aufrufe nach 14:58. Der Wechsel ist zwar in PR- und Issue-Fliesstext erklaert, aber kein Artefakt regelt, unter welcher Identitaet Agenten-PRs entstehen. | Werkzeug | mittel | CONFIRMED | `gh pr view 2271 --json author` → `wirdigital`; `gh issue view 2263` Kommentar 14:59:49 ebenfalls `wirdigital`, alle früheren `achimdehnert`; `git show origin/main:.github/CODEOWNERS` → Datei existiert nicht, `grep -ril codeowners docs/ .github/` → kein Treffer | `shared-gh-credential-overwritten-by-device-login` |
| 8 | Die 2FA-Pflicht wurde auch in `ttz-lif` und `meiki-lra` gesetzt, obwohl V3 in ADR-297 ausdrücklich nur auf `orgs/iilgmbh` gescoped ist. Kein Amendment, keine Scope-Notiz. | Prozesslücke | niedrig | SURVIVES (korrigierte Fassung) | ADR-297 V3-Messpunkt lautet `gh api orgs/iilgmbh`; PR #2272 meldet „alle vier auf true" | — |
| 9 | *Behauptet:* Rework-Kaskade — drei PRs an derselben Tabelle sei vermeidbar gewesen, Ursache „Schreiben vor Vollständigkeit". | Steuerung | hoch | **REFUTED** | Die Messwerte existierten bei #2266 noch nicht: Teams, 2FA und Ruleset entstanden erst im Lauf des Tages. Ein PR hätte stundenlanges Offenhalten bedeutet | — |
| 10 | *Behauptet:* die 2FA-Ausweitung auf zwei Kunden-Orgs sei ein Eingriff mit Kundenwirkung, Severity hoch. | Scope | hoch | **REFUTED** | `governance/exit-classes.yaml`: beide `exit-likely` mit Owner-Datenprämisse „nur Code+Demo-Daten, kein Souveränitäts-Gating"; `orgs/ttz-lif/members` → dieselben zwei Personen, die ohnehin 2FA-pflichtig sind → faktischer No-Op. Korrigierte Fassung = Befund 8 | — |
| 11 | *Behauptet:* PR #2271 sei nicht gereviewt worden. | Zuordnung | mittel | **PRE-REFUTED** | `gh pr view 2271 --json reviews` → `achimdehnert: APPROVED`. Vor Phase 3 widerlegt | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| `zielerreichung` | **4** | Auftrag und alle Folgeaufträge erfüllt, V1–V3 drei Monate vor Frist; Abzug für den kritischen Werkzeugfehler (#1) im Gelieferten und PR #2272 offen |
| `architektur_design` | **4** | Zwei-Ebenen-Trennung, Custody-Kriterium und die Stichtags-Logik im Melder tragen; Abzug für die Asymmetrie zwischen `check_b` und `check_c` (#1) |
| `code_konventionstreue` | **4** | Tests, `ruff`, Index-Regeneration, `ROT-IST-BEFUND`-Marker, Skill-Verteilung nachgezogen; Abzug für den verletzten Exit-Code-Vertrag (#2) |
| `risiko_debt` | **2** | Kritischer Bug auf `main` (#1), Werkzeugfehler nicht von Fund unterscheidbar (#2), drei tote Präfixregeln (#4), zwei Tracking-Issues veraltet (#6), Org-Config ohne durables Freigabe-Artefakt (#3) |
| `prozess_effizienz` | **3** | CI durchgehend grün, Rework-Vorwurf widerlegt (#9); Abzug für drei Selbstkorrekturen und zwei nicht funktionierende Befehle an den Owner (#5) |
| `entscheidungsqualitaet` | **4** | Negativkontrolle `pactive-de`, Goldstandard über GraphQL, Sitz-Befund an ADR-236 weitergereicht, eigene Irrtümer im ADR stehengelassen statt getilgt; Abzug für Ruleset-Alleingang (#3) und V3-Scope-Überschreitung (#8) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| `check_b` bekam nach dem `bahn-hub`-Vorfall einen Fallback; `check_c` mit identischer Aufrufform blieb unangetastet | Nach jedem Fix an einer Prüffunktion: `grep -c` der neuen Schutzmaßnahme über **alle** Schwesterfunktionen desselben Moduls, bevor committet wird. Ungleiche Zahl = offener Rest | #1 |
| `_gh_json` kapselt `subprocess.run` ohne `try`, während der Docstring Exit-Code 1 als „Fund" definiert | Wer einen Exit-Code-Vertrag in den Docstring schreibt, schreibt im selben Commit den Test, der Exit 2 bei Werkzeugfehler erzwingt | #2 |
| Ruleset per API scharfgeschaltet, dokumentierender PR blieb offen | Security-Config-Änderungen erst nach dem Merge des PRs, der sie beschreibt — oder die Freigabe als PR-Kommentar verankern, bevor die API-Aktion läuft | #3 |
| `bahn-`-Regel als falsch erwiesen, per Override umgangen | Wird eine Regel durch ein Override widerlegt, im selben PR entscheiden: Regel korrigieren oder streichen. Ein Override, das die einzige Anwendung der Regel aussticht, ist ein Streich-Signal | #4 |
| 2FA-PATCH und Audit-Filter als fertige Befehle übergeben, beide wirkungslos | Jeder Befehl, den der Owner ausführen soll, wird vorher einmal selbst ausgeführt — mindestens gegen eine Positivkontrolle, die zeigt, dass er überhaupt etwas bewirken *kann* | #5 |
| Tracking-Issues beim Anlegen befüllt, danach nur ergänzt, nie der Body nachgezogen | Wenn ein ADR-Abschnitt auf `erledigt` wechselt, wird im selben Zug die Checkbox im Tracking-Issue abgehakt oder das Issue geschlossen | #6 |
| `gh auth login` für den Partner überschrieb das geteilte Credential | Vor jedem `gh auth login` auf einer geteilten Maschine: aktuellen Account notieren und nach der Aktion zurückwechseln; Agenten-PRs nie unter einer fremden Identität erzeugen | #7 |
| 2FA-Scope über V3 hinaus ausgeweitet, ohne den Scope-Text zu berühren | Wird eine ADR-Voraussetzung über ihren geschriebenen Scope hinaus umgesetzt, bekommt der ADR im selben PR eine Zeile dazu — sonst weicht die Umsetzung stillschweigend vom Dokument ab | #8 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 91 Reports:

- **37 Slugs ≥2 ⇒ Gate-Pflicht**, davon **11 ohne registriertes Gate**. Zwei davon treten in dieser Sitzung auf:
  - `partial-fix-not-generalized-to-sibling-artifacts` (Befund #1) — steht seit dem 2026-08-23 als widerrufener Verzicht auf der Liste und ist hier **mechanisch nachgewiesen**: 1 Vorkommen von `bekannte_konten` in `check_b`, 0 in `check_c`.
  - `untested-command-handed-to-user` (Befund #5) — zwei Instanzen in einer Sitzung.
- `tracking-doc-stale-after-new-occurrence` (#6) und `scope-checkpoint-not-durably-recorded` (#3) sind ebenfalls gate-pflichtig; für letzteres existiert seit dem 2026-08-23 ein Gate.
- `refuted_rate`-Band gesund (0,25 in dieser Sitzung; Trend der letzten acht: 0,30 · 0,00 · 0,50 · 0,00 · 0,37 · 0,09 · 0,27 · 0,00).
- `risiko_debt` bleibt die schwächste Dimension der Flotte (Ø 2,56 über 91 Retros) — diese Sitzung liegt mit **2** darunter, nicht darüber.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py`:

- **`claim-before-cheapest-check`** — gemeldet als `RUECKFAELLIG` (3 Vorkommen nach Bau), zugleich **4× gefangen**. In *dieser* Sitzung feuerte der Stop-Hook **dreimal**, und zweimal führte der erzwungene Check zu einem echten Defekt (die veraltete ADR-Tabelle, der wirkungslose Audit-Filter). Damit ist er hier **`gates_caught`, kein Rückfall** — der erste Sitzungsbeleg dafür, dass das Gate trägt statt nur zu zählen.
- **`scope-checkpoint-not-durably-recorded`** — Gate gebaut 2026-08-23, Status bis heute `zu-frueh` (0 Vorkommen nach Bau). Befund #3 ist das **erste Vorkommen nach dem Bau**. Antwort nach den drei zulässigen: **ausweiten** — das Gate sieht offenbar Scope-Erweiterungen, die über GitHub-API statt über Repo-Artefakte laufen, nicht.
- **`untested-command-handed-to-user`** — Gate gebaut 2026-08-23, Status bis heute `zu-frueh` (1 Vorkommen vor Bau, 0 danach). Befund #5 ist damit — strukturgleich zu #3 — das **erste Vorkommen nach dem Bau**, und zwar gleich in zwei Instanzen an einem Nachmittag. Antwort nach den drei zulässigen: **umbauen** — das Gate greift offenbar erst, wenn ein Befehl *ausgeführt* wird, nicht wenn er *weitergegeben* wird. Der Prüfpunkt gehört an die Übergabe, nicht an die Ausführung.
- Acht weitere Gates stehen auf `zu-frueh`; kein Rückfall dort ist **kein** Wirksamkeitsbeleg.

## 5b. Autonomie-Kalibrierung

- **`over_act`: 0.** Jede Org-Konfigurationsänderung hatte eine Owner-Freigabe im Kapitäns-Kanal („4 5 6 go", „3 go", „erledigt"). Der Befund #3 ist nicht, dass ohne Freigabe gehandelt wurde, sondern dass **keine dieser Freigaben ein durables Artefakt hat** — sie existieren ausschließlich im Chat. Genau deshalb konnte kein Finder sie sehen, und genau deshalb urteilten zwei von ihnen auf Basis eines unvollständigen Bestands.
- **`over_ask`: 1.** Auf die Anweisung „überarbeiten" wurde per `AskUserQuestion` rückgefragt, statt die Schwächen selbst zu suchen; die Antwort („ADR-297 weiter") verlangte anschließend genau das eigenständige Suchen. Die Rückfrage kostete eine Runde ohne Erkenntnisgewinn.
- Der Permission-Classifier blockierte mehrfach; die Meldung nannte sich beim dritten Mal selbst transient. Die daraus gezogene Diagnose „dauerhaft gesperrt" war falsch und wurde revidiert — kein `over_act`/`over_ask`, aber ein Beleg dafür, dass Werkzeug-Fehlermeldungen genauso auf ihren Wortlaut zu prüfen sind wie API-Antworten.

## 6. Verankerung

### memory_candidates

```markdown
---
name: feedback_sibling_function_needs_the_same_guard
description: "Fix an einer Prueffunktion: dieselbe Schutzmassnahme in allen Schwesterfunktionen des Moduls nachzaehlen"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-24-check-c-ohne-fallback
---

Wird eine Pruefunktion gehaertet, bleibt die Schwesterfunktion mit identischer
Aufrufform oft unangetastet — und ausgerechnet dort wirkt die Luecke am
schwersten. Realfall 2026-08-24 (`tools/org_zuordnung_melder.py`): `check_b`
bekam nach dem bahn-hub-Vorfall einen Fallback ueber die bekannten Konten;
`check_c` rief `fetch(deklarierter_owner(repo), repo)` unveraendert weiter auf
und uebersprang bei `None` ohne Zaehlung. Der Leitsatzverstoss — der einzige
Zweck von check_c — waere lautlos verschwunden.

**Why:** Der Fix fuehlt sich vollstaendig an, weil der ausloesende Fall behoben
ist. Die Schwesterstelle hat denselben Defekt, aber keinen Ausloeser, der sie
sichtbar macht.

**How to apply:** Nach jedem Fix an einer Pruefunktion `grep -c <neue-massnahme>`
ueber alle Schwesterfunktionen desselben Moduls. Ungleiche Zahl = offener Rest,
im selben Commit. Verwandt: [[feedback_partial_fix_not_generalized]].
```

```markdown
---
name: feedback_command_handed_to_user_must_be_run_once
description: "Jeder Befehl, den der Owner ausfuehren soll, wird vorher einmal selbst gelaufen — mit Positivkontrolle"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-24-zwei-wirkungslose-befehle
---

Zwei Befehle wurden dem Owner am 2026-08-24 als fertig uebergeben und taten
nichts: `gh api -X PATCH orgs/<org> -F two_factor_requirement_enabled=true`
(Antwortfeld, kein Eingabefeld — laeuft durch, aendert nichts) und
`audit-log?phrase=actor:X+action:team` (der `action:`-Teil filtert nicht,
die Abfrage liefert alles vom Actor). Beide waeren beim Owner als erledigt
durchgegangen, wenn er nur den Exit-Code geprueft haette.

**Why:** Ein `200` ist keine Zustandsaenderung, und eine Trefferzahl ist kein
Filterbeleg. Wer einen Befehl weitergibt, haftet fuer seine Wirkung, nicht fuer
seine Syntax.

**How to apply:** Vor der Uebergabe einmal selbst ausfuehren und eine
**Positivkontrolle** danebenstellen, die zeigt, dass der Befehl ueberhaupt
etwas finden/bewirken kann. Beides in die Anleitung schreiben, nicht nur den
schreibenden Aufruf. Verwandt: [[feedback_measurement_tool_zero_is_not_absence]].
```

```markdown
---
name: feedback_shared_gh_credential_is_machine_wide
description: "gh auth login ueberschreibt die geteilte Anmeldung der Maschine — Agenten-PRs entstehen danach unter fremdem Namen"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-24-pr-unter-fremder-identitaet
---

`gh auth login` schreibt nach `~/.config/gh/hosts.yml` und gilt fuer **alle**
Nutzer dieser Shell — auch fuer den Agenten. Realfall 2026-08-24: ein
Device-Flow-Login fuer den Entwicklungspartner machte alle folgenden
`gh`-Aufrufe zu dessen Aufrufen; PR #2271 und ein Issue-Kommentar entstanden
unter der falschen Identitaet. Zusaetzlich lieferten Org-Abfragen danach leere
Felder statt Werte, weil das Konto die Org nur als Mitglied sieht — eine leere
Ausgabe sah aus wie `false`.

**Why:** Die Anmeldung ist maschinenweit, nicht sitzungsweit. Die Zuordnung
kippt still, und Berechtigungsunterschiede erzeugen leere statt falsche Werte.

**How to apply:** Vor einem Fremd-Login den aktuellen Account notieren
(`gh api user --jq .login`), danach zurueckwechseln und gegenpruefen. Bei
leerem Feld statt Wert: erst den Account pruefen, dann den Zustand.
```

### adr_candidates

Keiner. Die Sitzung hat zwei ADRs berührt (297 angenommen, 236 amendiert); die
Befunde sind Werkzeug- und Prozessfehler, keine Architekturentscheidungen.
`adr-threshold.md`: reine Korrektur nach bestehendem Muster ⇒ kein ADR.

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | `check_c`-Fallback nachziehen | platform | [#2264](https://github.com/achimdehnert/platform/issues/2264) | 🔵 ready | Fix + Test (ich) |
| 2 | Exit-Code 2 bei Werkzeugfehler | platform | [#2264](https://github.com/achimdehnert/platform/issues/2264) | 🔵 ready | try/except + Test (ich) |
| 3 | Tote Präfixregeln streichen | platform | [#2264](https://github.com/achimdehnert/platform/issues/2264) | 🔵 ready | Regel oder Override (ich) |
| 4 | Issue-Bodies nachziehen | platform | [#2262](https://github.com/achimdehnert/platform/issues/2262) | 🔵 ready | Checkboxen abhaken (ich) |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 5 | PR #2272 mergen | platform | [#2272](https://github.com/achimdehnert/platform/pull/2272) | 🟢 offen | Review (du) |
| 6 | Drei Gate-Kandidaten bauen? | platform | [#2234](https://github.com/achimdehnert/platform/issues/2234) | 🟢 offen | Entscheiden (du) |

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| **Sieht `GITHUB_TOKEN` im Melder-Workflow die privaten Repos unter `achimdehnert` überhaupt?** Wenn nicht, misst Check C in CI genau seinen Zielfall nicht — und die ADR-Behauptung „Messinstrument des Kill-Gates Ebene 1" trägt nicht. Als **Hypothese** geführt, nicht live geprüft. | Ein `workflow_dispatch`-Lauf des Melders und ein Blick in die „nicht prüfbar"-Liste des Logs |
| **Die Owner-Freigaben dieser Sitzung existieren nur im Chat.** Zwei Finder urteilten deshalb auf unvollständigem Bestand — einer davon mit Severity „hoch", die der Skeptiker kassierte. Dass die Freigaben real waren, ist Session-Wissen, kein Artefakt. | Freigabe-Zeilen als PR-/Issue-Kommentar verankern, wie es bei #2265 einmal geschah |
| **`filled_seats`-Kostenfolge** aus dem ADR-236-Amendment: ob aus dem freigewordenen Sitz real Geld wird, ist eine Vertragsfrage und bleibt offen | Rückfrage beim GitHub-Account-Team |
| **Der Rückfall von `scope-checkpoint-not-durably-recorded`** ist hier erstmals nach dem Gate-Bau gezählt; ob das Gate ausgeweitet werden muss oder der Einzelfall genügt, entscheidet erst das zweite Vorkommen | Nächster Retro mit Org-API-Änderung |

**Abschluss-Vierer**

- **getan:** ADR-297 überarbeitet und angenommen, ADR-236 amendiert, Melder gebaut und verdrahtet, Registry an acht Stellen korrigiert, V1–V3 erfüllt, 2FA in vier Orgs, Ruleset aktiv, drei Tracking-Issues angelegt.
- **angenommen:** dass `wirdigital` eine unabhängige Partei mit eigenem Recovery-Weg ist (Owner-Attest, per API nicht messbar); dass die Owner-Freigaben im Chat gültig waren.
- **nicht verifizierbar:** die Token-Sichtbarkeit des Melders in CI ohne echten Lauf; die kaufmännische Sitzfolge.
- **offen geblieben:** der kritische `check_c`-Fehler auf `main`, PR #2272, drei tote Präfixregeln, zwei veraltete Tracking-Issues.

## Self-Review (Phase 5, Meta-Agent gegen die Skill-Regeln)

Der Meta-Reviewer prüfte den Report-Entwurf gegen die zehn Skill-Regeln und fand
**drei Lücken**, alle vor der Ablage behoben:

1. **Vierter Verdikt-Bucket brach die Zähler-Arithmetik.** Befund #12 trug das Verdikt
   „GEBUENDELT mit #7" — ein Bucket, den das Schema nicht kennt. `findings_survived` (8)
   + `phase3_refuted` (2) + `pre_refuted` (1) ergaben 11 bei `findings_total: 12`.
   Behoben: #12 vollständig in #7 aufgelöst, `findings_total` auf 11, `refuted_rate`
   auf 0,27 korrigiert. Gegengeprüft: Befund-Tabelle hat 11 Zeilen, Summe stimmt.
2. **Absence-Claim ohne Suchkommando.** Die Behauptung „kein Artefakt regelt die
   Identität von Agenten-PRs" war ein Restatement. Belegt nachgetragen:
   `git show origin/main:.github/CODEOWNERS` → existiert nicht, `grep -ril codeowners`
   → kein Treffer.
3. **Zwei strukturgleiche Gates ungleich tief behandelt.** `gate_wirkung.py` führt
   `scope-checkpoint-not-durably-recorded` und `untested-command-handed-to-user` beide
   als `zu-frueh`; der Entwurf gab nur dem ersten die Erst-Vorkommen-Analyse. Ergänzt —
   mit der Antwort **umbauen**, weil das Gate an der Ausführung hängt, der Fehler aber
   an der Übergabe passiert.

**`refuted_rate` im Band:** 0,27 gegen den Trend der letzten acht Retros
(0,30 · 0,00 · 0,50 · 0,00 · 0,37 · 0,09 · 0,27 · 0,00). Weder dauerhaft >0,8 (Finder
zu lasch) noch <0,2 (Falsifikation als Theater). Echte Falsifikations-Quote
`phase3_refuted / (findings_total − pre_refuted)` = 2/10 = 0,20.

**Was der Meta-Review nicht leisten konnte:** Er beurteilt die Output-Qualität, nicht
die Richtigkeit der SURVIVES/REFUTED-Entscheide — das wäre Session-Urteil. Ob Befund #3
zu Recht überlebt, obwohl im Chat eine Owner-Freigabe vorlag, bleibt damit die offene
Frage dieses Reports; sie steht als Restlücke in §8.
