---
concept_id: KONZ-platform-039
title: Sichtbarkeit des platform-Repos — privat werden, ohne die Flotte abzuschneiden
pipeline_status: ready
tier: T3
owner: Achim Dehnert
spec_refs: []        # Infrastruktur-/Governance-Konzept, keine App-Spec
adr_threshold: "ADR nötig — Security-Perimeter + Cross-Repo. G1 und K2 sind erfüllt; das Konzept ist entscheidungsreif."
review_by: 2026-09-15
kill_criteria: "K1–K4 in §9; hart: bricht nach dem Schnitt CI in ≥1 öffentlichem Konsumenten länger als 24 h, wird zurückgedreht"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "gh repo view achimdehnert/platform --json visibility", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # PUBLIC; dev-hub PRIVATE
  - {claim_id: C2, source_path: ".github/workflows/_*.yml (git ls-tree origin/main)", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # 4 aktive Reusable Workflows
  - {claim_id: C3, source_path: "grep über ~/github/*/.github/workflows/ + gh search code --owner achimdehnert, VEREINIGT", commit_or_pr: "Lauf 2026-08-02 (2. Runde)", opened_in_session: true}   # 34 Konsumenten, 19 PUBLIC — Erstzählung (20/8) war zu niedrig
  - {claim_id: C8, source_path: "gh repo view über 4 Owner (achimdehnert, meiki-lra, ttz-lif, iilgmbh)", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # Konsumenten liegen in mind. 4 Orgs
  - {claim_id: C9, source_path: "G1-Experiment: g1-probe-privat / -oeffentlich / -aufrufer-privat", commit_or_pr: "Lauf 30749096578 (Kontrolle) 2026-08-02", opened_in_session: true}   # oeffentlicher Aufrufer abgelehnt, privater erfolgreich
  - {claim_id: C4, source_path: "grep raw.githubusercontent.com/achimdehnert/platform über ~/github/*/", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # 10 Repos
  - {claim_id: C5, source_path: "bootstrap.sh:71", commit_or_pr: "origin/main 2026-08-02", opened_in_session: true}   # unauthentifizierter git clone
  - {claim_id: C6, source_path: "git grep -c über origin/main", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # Prod-IP 117 Dateien, iil.pet 255, 237 ADRs, 38 KONZ
  - {claim_id: C7, source_path: "docs.github.com/actions/how-tos/reuse-automations/share-across-private-repositories", commit_or_pr: "WebFetch 2026-08-02", opened_in_session: true}   # Freigabe ist besitzer-bezogen; zur Sichtbarkeit des AUFRUFERS sagt die Doku nichts
created: 2026-08-02
---

# KONZ-platform-039 — Sichtbarkeit des platform-Repos

## Kernthese

**`platform` ist öffentlich, und das war niemandem bewusst.** Privat werden ist möglich, aber
nicht durch Umlegen eines Schalters: vier Abhängigkeitspfade führen von außen hinein, und **alle
vier brechen** — drei davon unmittelbar einsichtig, der vierte experimentell belegt (§4). Der
tragfähige Weg ist ein Schnitt entlang der Frage „muss das öffentlich lesbar sein, damit fremde
CI läuft?" — nicht ein Sichtbarkeitswechsel am Ganzen.

## 1. Wie das aufgefallen ist

Nicht durch eine Sicherheitsprüfung, sondern nebenbei: beim Anlegen eines PR gab die GitHub-API
`"private": false` zurück. Der Owner hatte in derselben Sitzung `--admin` mit der Begründung
„wegen privat" freigegeben. Die Prämisse war falsch, die Entscheidung darauf gebaut.

Im selben Zug wäre beinahe eine Test-Fixture mit **Namen Studierender und einer Anschrift** in
das öffentliche Repo gewandert (vor dem Push entpersonalisiert, platform#1670). Das ist der
eigentliche Befund: Nicht die Sichtbarkeit selbst ist das Risiko, sondern dass die
Arbeitsroutine sie falsch annimmt.

## 2. Was heute öffentlich steht (C6)

| Inhalt | Umfang |
|---|---|
| ADRs | 237 |
| Konzepte | 38 |
| Dateien mit der Prod-Server-IP | 117 |
| Dateien mit internen Hostnamen (`*.iil.pet`) | 255 |

Keine Geheimnisse im engeren Sinn — aber eine vollständige Karte der Infrastruktur, der
Entscheidungswege und der Angriffsfläche. Für ein Repo, dessen Governance-Charakter der Zweck
ist, ist das eine bewusste Entscheidung wert, keine Vorbelegung.

## 3. Die vier Abhängigkeitspfade nach außen

| # | Pfad | Umfang | Bricht bei „privat"? |
|---|---|---|---|
| P1 | Reusable Workflows `_*.yml` (C2, C3) | 4 Workflows, **37 Konsumenten, 19 davon öffentlich** | **ja — experimentell belegt** (§4) |
| P2 | `raw.githubusercontent.com/achimdehnert/platform` (C4) | 10 Repos | **ja, sicher** |
| P3 | `bootstrap.sh` klont unauthentifiziert (C5) | jede neue Maschine | **ja, sicher** |
| P4 | `git clone` in fremder CI (sqf-hub) | 1 Repo | **ja, sicher** |

**P1 ist der schwerste Pfad und zugleich der leiseste.** P2–P4 brechen sichtbar: ein Download
schlägt fehl, ein Klon fragt nach Zugangsdaten. P1 dagegen meldet `workflow was not found` —
das liest sich wie ein Tippfehler im Pfad, nicht wie eine Sichtbarkeitsfrage. Wer nur P2–P4
vorbereitet und dann umschaltet, sucht den Fehler an der falschen Stelle.

### 3.1 Wie die Konsumentenzahl zustande kam — und warum die erste falsch war

Die erste Fassung dieses Konzepts nannte **20 Konsumenten, 8 öffentlich**. Beides war zu
niedrig. Der Grund ist methodisch und wiegt schwerer als die Zahl:

| Methode | gefunden | übersehen |
|---|---|---|
| `grep` über lokale Klone `~/github/*` | 26 | 10, die nie ausgecheckt waren |
| `gh search code --owner achimdehnert` | 25 | 11, u. a. `outlinefw` |
| **Vereinigung beider** | 34 | die Repos fremder Owner |
| **+ Code-Suche über alle vier Owner** | **37** | — (K2 damit erfüllt) |

**Keine der beiden Methoden ist für sich vollständig, und keine merkt es.** Der lokale Scan
sieht nur, was jemand einmal geklont hat; die Code-Suche indiziert nicht alles und ist auf
einen Owner beschränkt. Wer nur eine von beiden fährt, bekommt eine plausible Zahl **ohne
Fehlerbalken** — genau die Form, in der eine Abwesenheitsaussage kippt.

Dazu kommt: die Konsumenten liegen in **mindestens vier Owner-Namensräumen** (C8) —
`achimdehnert`, `meiki-lra`, `ttz-lif` und `iilgmbh`. Die beiden zunächst nicht auflösbaren
Repos lagen in `iilgmbh`, der Zielorganisation der Migration nach KONZ-012; `iil-klickdummy`
ist dort **öffentlich**. Eine Suche mit `--owner achimdehnert` kann sie konstruktionsbedingt
nicht finden.

**Nachgeholt am 2026-08-02:** die Code-Suche lief anschließend über alle vier Owner. Ergebnis
**37 Konsumenten, 19 öffentlich** — verteilt auf `achimdehnert` (29), `iilgmbh` (5),
`meiki-lra` (3); `ttz-lif` **null**. Die Null dort ist kalibriert: dieselbe Suche findet in
`ttz-lif` sehr wohl Treffer für andere Muster, das Repo `ttz-hub` existiert und ist indiziert.
Sie ist damit ein Befund, kein Filterartefakt.

## 4. G1 — die offene Frage ist experimentell beantwortet

**Frage:** Darf ein **öffentliches** Repo einen Reusable Workflow aus einem **privaten** Repo
desselben Besitzers aufrufen?

**Antwort: nein.** Am 2026-08-02 mit drei Wegwerf-Repos gemessen (C9).

### Aufbau

| Rolle | Repo | Sichtbarkeit |
|---|---|---|
| Anbieter | `g1-probe-privat` | **privat**, `actions/permissions/access` = `user` |
| Versuch | `g1-probe-oeffentlich` | **öffentlich** |
| Kontrolle | `g1-probe-aufrufer-privat` | **privat** |

Beide Aufrufer tragen **dieselbe** Workflow-Datei, denselben Ref (`@main`), denselben Anbieter.

### Ergebnis

| Aufrufer | Ergebnis |
|---|---|
| öffentlich | **abgelehnt beim Auslösen**, zweimal: `-> "…/reusable.yml@main": workflow was not found` |
| privat (Kontrolle) | **erfolgreich** — Lauf `30749096578`, beide Jobs `success`, Ausgabe `Beleg=ausgefuehrt` |

Der öffentliche Aufruf wurde **erneut** abgelehnt, nachdem der private schon lief — damit ist
Replikationsverzögerung als Erklärung ausgeschlossen. Die einzige Variable, die sich zwischen
Versuch und Kontrolle unterscheidet, ist die **Sichtbarkeit des Aufrufers**.

### Was das für die Entscheidung heißt

`L5` ist damit **verifiziert**, und P1 ist kein Restrisiko mehr, sondern eine Gewissheit: Ein
Wechsel von `platform` auf privat legt die CI von **19 öffentlichen Repos** still — sofort, ohne
Vorwarnung, und mit einer Fehlermeldung (`workflow was not found`), die auf ein fehlendes File
zeigt statt auf die Ursache.

> **Zur Chronologie, weil sie zur Sache gehört:** Diese Behauptung stand früher in der Sitzung
> als Tatsache da, ohne Beleg. Sie wurde daraufhin zurückgenommen — richtig, denn unbelegt ist
> unbelegt, auch wenn man am Ende recht behält. Jetzt steht sie wieder da, diesmal mit
> Versuch **und** Kontrolle. Der Unterschied zwischen den beiden Zuständen ist der ganze Punkt
> von `evidence-discipline`: nicht das Ergebnis war falsch, sondern die Deckung.

**Aufräumen:** Die drei Wegwerf-Repos sind zu löschen (§11).

## 5. Annahmen-/Entscheidungs-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|-------------------------|--------|
| L1 | `platform` ist öffentlich, `dev-hub` privat | Beobachtung | C1 | verifiziert |
| L2 | **19** öffentliche Repos beziehen Reusable Workflows aus platform (**37** insgesamt) | Beobachtung | C3, C8 — zwei Methoden × vier Owner (§3.1) | **verifiziert** |
| L3 | 10 Repos ziehen Dateien über `raw.githubusercontent` | Beobachtung | C4 | verifiziert |
| L4 | `bootstrap.sh` klont ohne Authentifizierung | Beobachtung | C5 | verifiziert |
| L5 | Ein öffentlicher Aufrufer kann keinen privaten Reusable Workflow nutzen | Beobachtung | **C9 — Versuch + Kontrolle, §4** | **verifiziert** |
| L6 | Die vier Workflows sind der einzige Grund, platform öffentlich zu halten | Annahme | P2–P4 sind umstellbar; Konsumentenzahl inzwischen zweifach erhoben (§3.1), bleibt aber untere Schranke | offen (M) |
| L7 | Ein separates öffentliches CI-Repo erzeugt keinen zweiten Wahrheitsstand | Entscheidung | Workflows wandern **ganz**, kein Duplikat; Kill-Kriterium K3 misst Divergenz | offen |

**L6 war die unbequemste Zeile — und sie hat sich sofort bestätigt.** Der Nachscan (§3.1)
hob die Konsumentenzahl von 20 auf 34 und die öffentlichen von 8 auf 19. Die Zeile bleibt
trotzdem offen, nur mit kleinerer Restunsicherheit: auch die Vereinigung zweier unvollständiger
Methoden ist kein Beweis für Vollständigkeit.

## 6. Alternativen

### Variante A — alles bleibt öffentlich, Inhalte werden bereinigt

Prod-IP und interne Hostnamen aus 255 Dateien entfernen oder durch Platzhalter ersetzen; die
Arbeitsroutine korrigieren (jeder Commit im Bewusstsein „öffentlich").

*Dafür:* keine Brüche, sofort machbar, kein neues Repo.
*Dagegen:* 255 Dateien anfassen, und die Historie bleibt öffentlich — was einmal draußen war,
holt kein Commit zurück. Löst das Problem der **Sichtbarkeit** nicht, nur seine Symptome.

### Variante B — Schnitt: `shared-ci` öffentlich, `platform` privat

Die vier `_*.yml` wandern in ein neues, öffentliches Repo `shared-ci`. `platform` wird privat.
P2 wird auf `shared-ci` umgehängt oder auf authentifizierte Zugriffe umgestellt; `bootstrap.sh`
bekommt einen authentifizierten Klon.

*Dafür:* trennt sauber nach Zweck — was fremde CI braucht, ist öffentlich; was Governance ist,
nicht. Danach ist die Frage dauerhaft beantwortet statt bei jedem Commit neu.
*Dagegen:* neues Repo, Migration in 20 Konsumenten (Ref-Umstellung), `bootstrap.sh` braucht
einen Token — der Einstieg auf einer neuen Maschine wird unbequemer.

### Variante C — beides: Schnitt **und** Bereinigung

Wie B, zusätzlich werden vor dem Wechsel die Infrastruktur-Angaben bereinigt, weil die
öffentliche Historie ohnehin bleibt.

*Dafür:* die einzige Variante, die auch die **Vergangenheit** adressiert.
*Dagegen:* teuerste Variante; die Bereinigung ist Fleißarbeit ohne Kill-Gate.

## 7. Empfehlung

**Variante B** — G1 ist beantwortet (§4: der Schnitt ist **zwingend**, nicht optional). Es bleibt
eine Vorstufe, die sofort wirkt und nichts kostet:

1. **Sofort (unabhängig von allem):** die Arbeitsroutine korrigieren. `platform` ist öffentlich;
   das gehört in `CLAUDE.md` und `CORE_CONTEXT.md`, damit keine weitere Entscheidung auf der
   falschen Prämisse gebaut wird. **Das ist der einzige Schritt, der heute schon Schaden
   verhindert** — der Beinahe-Vorfall mit der Fixture war ein Routine-, kein Technikproblem.
2. ~~G1 ausführen~~ **erledigt** (§4) — Ergebnis: der Schnitt ist zwingend. Ohne ihn stünde die
   CI von 19 öffentlichen Repos ab der Sekunde des Umschaltens still.
3. ~~Vollständiger Konsumenten-Scan~~ **erledigt** (§3.1) — 37 Konsumenten, 19 öffentlich, vier Owner abgedeckt.
4. **Dann erst** ADR schreiben und `shared-ci` anlegen.

**Nicht empfohlen: den Sichtbarkeitsschalter vor Schritt 2–3 umzulegen.** Der Bruch wäre sofort,
org-weit und träfe genau die Repos, die publiziert werden.

## 8. Risiken

| Risiko | Eintritt | Wirkung | Gegenmaßnahme |
|---|---|---|---|
| Konsument außerhalb `~/github` übersehen | Mittel | CI bricht unbemerkt | Schritt 3 vor der Umsetzung |
| `shared-ci` und `platform` driften auseinander | Mittel | zwei Wahrheitsstände | Workflows wandern **ganz**, kein Duplikat (L7, K3) |
| `bootstrap.sh` braucht Token → Einstiegshürde | Hoch | neue Maschine langsamer aufgesetzt | dokumentierter Ein-Zeilen-Fallback im Bootstrap |
| Öffentliche Historie bleibt | **Sicher** | alte Infrastruktur-Angaben bleiben abrufbar | bewusst hinnehmen oder Variante C |

## 9. Kill-Gate

| id | Kriterium | Schwelle | Status |
|----|-----------|----------|--------|
| K1 | G1 ausgeführt und protokolliert | vor jedem weiteren Schritt | ✅ erfüllt (§4, 2026-08-02) |
| K2 | Konsumenten-Scan über **alle vier Owner**, beide Methoden vereinigt | vor der Umsetzung | ✅ erfüllt (§3.1, 2026-08-02) — 37 Konsumenten, 19 öffentlich |
| K3 | Divergenz zwischen `shared-ci` und `platform` | > 0 Dateien doppelt ⇒ Schnitt falsch geführt | ⬜ offen |
| K4 | CI-Bruch in einem öffentlichen Konsumenten | > 24 h ⇒ zurückdrehen | ⬜ offen |

**Exception-Budget:** bis `review_by` 2026-09-15. Liegt bis dahin kein G1-Ergebnis vor, wird
dieses Konzept auf `stale` gesetzt und Variante A (nur Bereinigung + Routine-Korrektur) als
Rückfall umgesetzt — ein Konzept, das ein Jahr auf einen Viertelstunden-Check wartet, ist keine
Entscheidungsvorlage mehr.

## 10. Was dieses Konzept nicht leistet

- **Kein adversarialer Agenten-Fan-out.** Der `/konzept`-Skill sieht für T3 drei unabhängige
  Gegenleser vor; in dieser Sitzung war der Einsatz von Subagenten ausgeschlossen. Die
  Gegenlesung fehlt damit — das ist eine benannte Lücke, keine erledigte Achse.
- **Keine Kostenrechnung.** Ob private Repos hier Actions-Minuten kosten (self-hosted Runner vs.
  GitHub-hosted), ist nicht erhoben.
- **Fremd-Orgs nur angerissen.** Der Nachscan (§3.1) förderte einen vierten Namensraum zutage:
  `iilgmbh` — die Zielorganisation der Migration nach KONZ-012. Zwei Konsumenten liegen dort,
  `iil-klickdummy` davon **öffentlich**. Eine Code-Suche pro Owner für `meiki-lra`, `ttz-lif`
  und `iilgmbh` steht aus; erst danach ist die Zahl mehr als eine untere Schranke.

---

## 11. Aufräumen — erledigt

Die drei Wegwerf-Repos aus G1 (`g1-probe-privat`, `g1-probe-oeffentlich`,
`g1-probe-aufrufer-privat`) wurden am **2026-08-02 vom Owner gelöscht**. Der irreversible
Schritt lag beim Menschen (Konvention `delete-repo`); vorbereitet und **nachgeprüft** wurde er
hier — `gh repo view` liefert für alle drei `Could not resolve to a Repository`. Die Meldung
„sind gelöscht" allein hätte den Eintrag nicht getragen.

**Nebenbefund für künftige Experimente dieser Art:** Der CLI-Token trägt den Scope
`delete_repo` **nicht**. Das Anlegen von Wegwerf-Repos ist damit billiger als ihr Entfernen —
wer so ein Experiment plant, klärt das Aufräumen besser vorher als hinterher. In diesem Fall
stand ein öffentliches Repo rund zwanzig Minuten länger als nötig.

---

## 12. Umsetzungsreihenfolge — Schnitt und Schalter entkoppeln

**Die wichtigste Einsicht dieses Konzepts kommt zum Schluss:** Der Umzug der Workflows nach
`shared-ci` und das Umlegen des Sichtbarkeitsschalters sind **zwei Vorhaben**, nicht eines. Der
Umzug ist für sich nützlich, risikoarm und jederzeit rückholbar; der Schalter ist ein einzelner,
scharfer Schnitt. Sie zu koppeln macht aus einer Reihe kleiner Schritte ein Ereignis mit
19 möglichen Ausfällen an einem Tag.

| Stufe | Schritt | Risiko | Umkehrbar |
|---|---|---|---|
| **0** | `platform ist öffentlich` in `CLAUDE.md` + `CORE_CONTEXT.md` | keins | ja |
| **1** | Repo `shared-ci` anlegen (**öffentlich**), die 4 `_*.yml` dorthin, Tag `v1` | keins — noch ruft niemand | ja |
| **2** | **Ein** Pilot-Konsument auf `shared-ci@v1` umstellen, CI grün abwarten | gering | ja, ein PR |
| **3** | Restliche 36 Konsumenten in Wellen (Owner-weise), je Welle CI-Kontrolle | gering, gestaffelt | ja, je PR |
| **4** | P2 umhängen (10 Repos), P3 `bootstrap.sh`, P4 `sqf-hub` | gering | ja |
| **5** | Gegenprobe: `platform` hat **keine** externen Konsumenten mehr | — | — |
| **6** | **Erst jetzt** Sichtbarkeit auf privat | hoch, aber vorbereitet | ja, ein Klick |

**Stufe 5 ist das eigentliche Gate.** Sie ist dieselbe Messung wie §3.1, nur später und mit
erwartetem Ergebnis Null — und sie muss **kalibriert** sein: dieselbe Suche muss vorher noch
Treffer geliefert haben, sonst belegt die Null nur, dass der Filter greift (Lehre aus `ttz-lif`
in §3.1).

**Nach Stufe 3 ist der größte Teil des Nutzens schon da**, auch wenn Stufe 6 nie käme:
`platform` wäre dann kein CI-Anbieter mehr, sondern nur noch Governance-Repo — die Trennung, um
die es eigentlich geht. Stufe 6 ist danach eine Fünf-Sekunden-Entscheidung statt eines Projekts.

**Wer macht was.** Stufen 1–4 sind mechanisch (Ref-Umstellung, ein Muster, 47 PRs) und gehören
auf ein günstigeres Modell-Tier; Stufe 0 und die Entscheidung zu Stufe 6 gehören dem Owner.
Die Wellen in Stufe 3 folgen der Staffelungs-Lehre aus `feedback_mass_bump_wave_stagger_preflight`:
Vorab-Check, dann Welle, nicht 36 PRs auf einmal.

**Offen und bewusst nicht entschieden:** ob die Historie von `platform` mitwandert oder
`shared-ci` bei null beginnt. Für die Workflows ist die Historie entbehrlich; wer sie will,
zahlt mit einem `git filter-repo`-Lauf. Das ist eine Umsetzungsentscheidung, keine
Konzeptfrage.
