---
concept_id: KONZ-platform-039
title: Sichtbarkeit des platform-Repos — privat werden, ohne die Flotte abzuschneiden
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []        # Infrastruktur-/Governance-Konzept, keine App-Spec
adr_threshold: "ADR nötig — Security-Perimeter + Cross-Repo. Erst NACH G1 (Workflow-Experiment), sonst baut der ADR auf einer ungeprüften Annahme."
review_by: 2026-09-15
kill_criteria: "K1–K4 in §9; hart: bricht nach dem Schnitt CI in ≥1 öffentlichem Konsumenten länger als 24 h, wird zurückgedreht"
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "gh repo view achimdehnert/platform --json visibility", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # PUBLIC; dev-hub PRIVATE
  - {claim_id: C2, source_path: ".github/workflows/_*.yml (git ls-tree origin/main)", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # 4 aktive Reusable Workflows
  - {claim_id: C3, source_path: "grep über ~/github/*/.github/workflows/ + gh search code --owner achimdehnert, VEREINIGT", commit_or_pr: "Lauf 2026-08-02 (2. Runde)", opened_in_session: true}   # 34 Konsumenten, 19 PUBLIC — Erstzählung (20/8) war zu niedrig
  - {claim_id: C8, source_path: "gh repo view über 4 Owner (achimdehnert, meiki-lra, ttz-lif, iilgmbh)", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # Konsumenten liegen in mind. 4 Orgs
  - {claim_id: C4, source_path: "grep raw.githubusercontent.com/achimdehnert/platform über ~/github/*/", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # 10 Repos
  - {claim_id: C5, source_path: "bootstrap.sh:71", commit_or_pr: "origin/main 2026-08-02", opened_in_session: true}   # unauthentifizierter git clone
  - {claim_id: C6, source_path: "git grep -c über origin/main", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # Prod-IP 117 Dateien, iil.pet 255, 237 ADRs, 38 KONZ
  - {claim_id: C7, source_path: "docs.github.com/actions/how-tos/reuse-automations/share-across-private-repositories", commit_or_pr: "WebFetch 2026-08-02", opened_in_session: true}   # Freigabe ist besitzer-bezogen; zur Sichtbarkeit des AUFRUFERS sagt die Doku nichts
  - {claim_id: C9, source_path: "G1-Experiment: achimdehnert/ci-sichtbarkeit-probe (privat, access_level=user) + ci-sichtbarkeit-probe-caller (public) — gh workflow run → HTTP 422 workflow was not found", commit_or_pr: "Lauf 2026-08-02", opened_in_session: true}   # L5 bestätigt: public→privat-Aufruf unmöglich
created: 2026-08-02
---

# KONZ-platform-039 — Sichtbarkeit des platform-Repos

## Kernthese

**`platform` ist öffentlich, und das war niemandem bewusst.** Privat werden ist möglich, aber
nicht durch Umlegen eines Schalters: vier Abhängigkeitspfade führen von außen hinein, zwei davon
brechen **sicher**. Der tragfähige Weg ist ein Schnitt entlang der Frage „muss das öffentlich
lesbar sein, damit fremde CI läuft?" — nicht ein Sichtbarkeitswechsel am Ganzen.

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
| P1 | Reusable Workflows `_*.yml` (C2, C3) | 4 Workflows, **34 Konsumenten, 19 davon öffentlich** | **ungeklärt** (§4) |
| P2 | `raw.githubusercontent.com/achimdehnert/platform` (C4) | 10 Repos | **ja, sicher** |
| P3 | `bootstrap.sh` klont unauthentifiziert (C5) | jede neue Maschine | **ja, sicher** |
| P4 | `git clone` in fremder CI (sqf-hub) | 1 Repo | **ja, sicher** |

**P2 bis P4 tragen die Schlussfolgerung schon allein.** Selbst wenn P1 unproblematisch wäre,
bräuchte ein Sichtbarkeitswechsel Vorarbeit an drei Stellen.

### 3.1 Wie die Konsumentenzahl zustande kam — und warum die erste falsch war

Die erste Fassung dieses Konzepts nannte **20 Konsumenten, 8 öffentlich**. Beides war zu
niedrig. Der Grund ist methodisch und wiegt schwerer als die Zahl:

| Methode | gefunden | übersehen |
|---|---|---|
| `grep` über lokale Klone `~/github/*` | 26 | 10, die nie ausgecheckt waren |
| `gh search code --owner achimdehnert` | 25 | 11, u. a. `outlinefw` |
| **Vereinigung beider** | **34** | mind. die Repos fremder Owner (s. u.) |

**Keine der beiden Methoden ist für sich vollständig, und keine merkt es.** Der lokale Scan
sieht nur, was jemand einmal geklont hat; die Code-Suche indiziert nicht alles und ist auf
einen Owner beschränkt. Wer nur eine von beiden fährt, bekommt eine plausible Zahl **ohne
Fehlerbalken** — genau die Form, in der eine Abwesenheitsaussage kippt.

Dazu kommt: die Konsumenten liegen in **mindestens vier Owner-Namensräumen** (C8) —
`achimdehnert`, `meiki-lra`, `ttz-lif` und `iilgmbh`. Die beiden zunächst nicht auflösbaren
Repos lagen in `iilgmbh`, der Zielorganisation der Migration nach KONZ-012; `iil-klickdummy`
ist dort **öffentlich**. Eine Suche mit `--owner achimdehnert` kann sie konstruktionsbedingt
nicht finden.

**Was daraus für die Umsetzung folgt:** Die Zahl 34 ist eine **untere Schranke**, keine
Erhebung. Vor dem Schnitt braucht es eine Zählung, die alle vier Owner abdeckt und beide
Methoden vereinigt — sonst bricht die CI genau dort, wo niemand hingesehen hat.

## 4. Die eine offene Frage — ausdrücklich ungeprüft

Darf ein **öffentliches** Repo einen Reusable Workflow aus einem **privaten** Repo desselben
Besitzers aufrufen?

**Ich weiß es nicht.** Die GitHub-Dokumentation beschreibt die Freigabe als besitzer-bezogen
(„Accessible from repositories owned by USERNAME") und sagt zur Sichtbarkeit des *aufrufenden*
Repos **nichts** (C7). In einem früheren Zwischenstand dieser Sitzung habe ich das Gegenteil als
Tatsache behauptet — das war nicht belegt und ist hiermit zurückgenommen.

**Billigster Check (G1):** ein Wegwerf-Repo `ci-sichtbarkeit-probe`, privat, mit einem trivialen
`workflow_call`-Workflow; Freigabe auf „repositories owned by USERNAME"; Aufruf aus einem
Zweig eines der acht öffentlichen Konsumenten. Kosten: eine Viertelstunde. Ergebnis entscheidet
zwischen Variante A und B in §6.

**G1 AUSGEFÜHRT (2026-08-02, Owner-Go im Chat):** privates Wegwerf-Repo
`ci-sichtbarkeit-probe` mit trivialem `workflow_call`-Workflow, Actions-Freigabe per API auf
`access_level=user` gesetzt; Aufruf aus dem eigens angelegten **öffentlichen** Wegwerf-Repo
`ci-sichtbarkeit-probe-caller` (`workflow_dispatch` → `uses: …/_probe.yml@main`).
**Ergebnis: GitHub verweigert den Dispatch mit „workflow was not found"** (HTTP 422 beim
Parsen des aufgerufenen Workflows) — der öffentliche Aufrufer kann den privaten
Reusable-Workflow **nicht** nutzen, die Freigabe „user" ändert daran nichts. L5 ist damit
**bestätigt**: platform privat schalten bricht die ≥19 öffentlichen Workflow-Konsumenten
sicher. Der tragfähige Weg bleibt der Schnitt (§6 Variante B) oder Variante A (Bereinigung).
Die beiden Wegwerf-Repos sind löschbar (DELETE ist per Policy Human-Only).

**Aufwandsschätzung für P1 ist damit keine Wette mehr** — die Entscheidungsgrundlage für den
ADR liegt vor; nächster Schritt ist die Owner-Wahl zwischen Variante A und B.

## 5. Annahmen-/Entscheidungs-Ledger

| id | Aussage | Typ | Evidenz / Falsifikation | Status |
|----|---------|-----|-------------------------|--------|
| L1 | `platform` ist öffentlich, `dev-hub` privat | Beobachtung | C1 | verifiziert |
| L2 | **19** öffentliche Repos beziehen Reusable Workflows aus platform (34 insgesamt) | Beobachtung | C3, C8 — zwei Methoden vereinigt (§3.1) | verifiziert als **untere Schranke** |
| L3 | 10 Repos ziehen Dateien über `raw.githubusercontent` | Beobachtung | C4 | verifiziert |
| L4 | `bootstrap.sh` klont ohne Authentifizierung | Beobachtung | C5 | verifiziert |
| L5 | Ein öffentlicher Aufrufer kann keinen privaten Reusable Workflow nutzen | Beobachtung | G1-Experiment 2026-08-02: Dispatch scheitert mit „workflow was not found" trotz `access_level=user` (§4) | **verifiziert** |
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

**Variante B, aber erst nach G1** — und mit einer Vorstufe, die sofort wirkt und nichts kostet:

1. **Sofort (unabhängig von allem):** die Arbeitsroutine korrigieren. `platform` ist öffentlich;
   das gehört in `CLAUDE.md` und `CORE_CONTEXT.md`, damit keine weitere Entscheidung auf der
   falschen Prämisse gebaut wird. **Das ist der einzige Schritt, der heute schon Schaden
   verhindert** — der Beinahe-Vorfall mit der Fixture war ein Routine-, kein Technikproblem.
2. **G1 ausführen** (Viertelstunde, §4). Fällt er negativ aus (öffentlicher Aufrufer kann
   privaten Workflow nicht nutzen), ist der Schnitt zwingend; fällt er positiv aus, wird B
   billiger, bleibt aber wegen P2–P4 nötig.
3. **Vollständiger Konsumenten-Scan** über die GitHub-Code-Suche statt über lokale Klone (L6).
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
| K1 | G1 ausgeführt und protokolliert | vor jedem weiteren Schritt | ✅ 2026-08-02 — Ergebnis in §4: öffentlicher Aufrufer scheitert, L5 bestätigt |
| K2 | Konsumenten-Scan über **alle vier Owner**, beide Methoden vereinigt | vor der Umsetzung | 🟡 teilweise — 2 Methoden × 1 Owner erhoben (§3.1), 3 Owner fehlen |
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
