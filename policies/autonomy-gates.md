# Policy: Autonomy Gates
<!-- rule_class: C | assessed_with: claude-fable-5 | reassess_by: 2027-08-01 (KONZ-038 D4) -->

**Trigger words:** freigabe, genehmigung, approval, autonom, autonomie, darf ich,
user-eingriff, gate, permission, bypass

## Rule

Der Agent arbeitet **autonom durch** und holt Freigaben nur an den fünf Gates
unten ein. Alles unterhalb der Gates läuft ohne Rückfrage — auch mehrstufig
(Branch → Edits → PR → CI-Fix → plain-Merge bei grünem CI, sofern kein Gate
berührt wird).

## Die fünf Gates (Freigabe IMMER nötig)

1. **Irreversibles** — Daten/Branches löschen, force-push, Secret-Rotation,
   destruktive Migrationen.
2. **Prod-Zustandsänderung** — Deploy auslösen, Prod-Dateien/-Container/-DBs
   anfassen. Ausnahme: explizit allowlistete, backup-first Wartungs-Wrapper.
   Merke: In Repos mit Auto-Deploy-on-main ist der **Merge selbst** ein
   Prod-Schritt und damit gate-pflichtig.

   **Klarstellung `platform` (Owner-Go 2026-08-10, D3).** Ein Merge nach
   `platform:main` löst `opt-platform-sync.yml` aus und zieht `/opt/platform`
   nach — den read-only Werkzeugklon, aus dem der nächtliche Mail-Ingest liest.
   Nach dem Buchstaben von Gate 2 wäre damit **jeder** platform-Merge
   gate-pflichtig; praktisch wäre das die Rückkehr zum Zustand, den D1/D2 gerade
   beenden.

   Maßgeblich ist die **Zustandsfrage, nicht der Dateipfad**: der Sync ist ein
   `git pull` eines Klons. Er startet keinen Dienst neu, führt keine Migration
   aus, schreibt keine Daten und wechselt kein Image. Deshalb:

   - **Gate 2 greift NICHT** für platform-Merges, deren Wirkung sich in diesem
     Dateiabgleich erschöpft und die per `git revert` + nächstem Sync vollständig
     zurücknehmbar sind. Das ist der Normalfall.
   - **Gate 2 greift weiterhin**, sobald ein Merge darüber hinaus Zustand
     anfasst: Dienst-/Container-Neustart, Migration, Schreibzugriff auf Prod-Daten,
     Secret-/Token-Wechsel, oder eine Änderung an `opt-platform-sync.yml` selbst
     (die liegt ohnehin unter `/.github/` und ist damit reviewpflichtig).

   **Restrisiko, ausdrücklich benannt:** ein fehlerhaftes Werkzeug unter
   `tools/` erreicht den nächtlichen Ingest, ohne dass ein Mensch zugestimmt hat.
   Getragen wird das von der PR-CI (`make test` als Required Check) und davon,
   dass zwischen Merge und 03:30-Lauf ein Revert genügt. Ein **paths-Filter am
   Sync ist KEINE zulässige Antwort darauf** — er ist in dessen Kopf bewusst
   ausgeschlossen, weil er genau die Drift wiederherstellt, die der Workflow
   beseitigt hat (platform#1585).
3. **Security-/Governance-Config** — Branch-Protection/Rulesets, Tokens,
   Org-Permissions, Workflow-Permissions (`issues:write` etc., deckt sich mit
   Gate `autonomous-no-human-review`).
4. **Scope-Eskalation** — drittes Repo, Publish (PyPI/Release), neue
   Automatismen mit Schreibrecht (Scope-Checkpoint, house rule).
5. **Nennenswerter Spend** — Modell-Tier-Upgrade, Cloud-/Ultra-Runs, bezahlte APIs.

## Standing-Authorization-Klassen (dauerhaft freigegeben, KEIN Einzelwort nötig)

> **Motiv (KONZ-platform-019 B2):** Der Permission-Classifier blockte wiederholt
> Aktionen, die *keinen* der fünf Gates berühren, nur weil die Freigabe nicht
> *benannt* war (Realfall 2026-07-12: „go autonom" reichte nicht, „merge PR #N"
> schon). Diese **Positiv-Liste** benennt vorab freigegebene Aktionsklassen —
> innerhalb ihrer gilt die Freigabe als **stehend erteilt**, kein Einzel-OK pro
> Fall. Es ist eine **Positiv-Liste, kein Catch-all**: was nicht gelistet ist,
> bleibt gate-geregelt wie oben. Die Klassen liegen ausschließlich **unterhalb**
> der fünf Gates; berührt eine Aktion einen Gate, gewinnt der Gate.

- **SA-1 — Merge eines CI-grünen PR in ein Repo OHNE GitHub-Review-Pflicht UND
  OHNE Auto-Deploy-on-main.** ✅ **RATIFIZIERT (Achim, 2026-07-12).** Voraussetzung:
  alle Required Checks grün, kein Ruleset verlangt Review, und `main` triggert
  **keinen** Prod-Deploy. Deckt die Hub-Repo-Merges ab, die heute an Gate 2
  hängen, obwohl der Merge dort *kein* Prod-Schritt ist. **Ausdrücklich
  AUSGESCHLOSSEN:** jedes Auto-Deploy-on-main-Repo (dort ist der Merge ein
  Prod-Schritt → Gate 2 wirkt unverändert), und jeder PR mit Migrationen/
  destruktiven Änderungen (Gate 1).
- **SA-2 — Merge eines CI-grünen NICHT-Governance-PR in `platform`.**
  ✅ **RATIFIZIERT (Achim, 2026-08-10, wörtliches „D1 D2 D3 D4 go").** Die
  Vorbedingung ist im selben Zug erfüllt: der CODEOWNERS-Catch-all ist weg
  (KONZ-platform-032 **B1** — der frühere Verweis auf „KONZ-019 B1" war ein
  Fehlzeiger, B1 stand nie in KONZ-019; das erklärt vermutlich, warum die Klasse
  vier Wochen lag).

  **Nicht-Governance heißt:** der PR berührt keinen der reviewpflichtigen Pfade
  aus `.github/CODEOWNERS` (`/.github/`, `/registry/`, `/packages/`, `/docs/adr/`,
  `/policies/`). Berührt er einen, verlangt GitHub weiterhin das Approval — die
  Klasse deckt genau die Menge ab, die GitHub durchlässt, und keinen Fall mehr.

  **Motiv (Owner, 2026-08-10):** „ich und wirdigital agieren als
  Entscheidungsinstanz, nicht als Auto-Freigeber." Gemessen über 30 Tage: 400
  gemergte platform-PRs, 0 ohne Approval, 399 Approvals von einem Konto; 73 %
  berührten keinen Governance-Pfad. Ein Approval, das 400-mal im Monat fällt,
  ist kein Vier-Augen-Prinzip mehr.

  **Ausdrücklich AUSGESCHLOSSEN:** Gate 1 (Migrationen/Destruktives), Gate 5
  (Spend), und alles, was eine wartende Owner-Entscheidung überholen würde. Zu
  Gate 2 siehe die platform-Klarstellung unten.
- **SA-3 — Datei-Hausputz in `~/.secrets` / `~/shared` (Reconcile, KEIN Inhalts-Dump).**
  ✅ **RATIFIZIERT (Achim, 2026-07-12).** Verschieben/Deduplizieren/Löschen
  byte-identischer Secret-**Dateien** nach ihrer SSoT-Konvention (KONZ-010).
  **Auflage:** Secret-**Inhalte** werden NIE ins Transkript gelesen (kein
  `cat`/`grep` über Dateiinhalte) — nur Dateinamen, Größen, Hashes. Divergente/
  nicht-identische Dateien bleiben stehen + werden gemeldet (kein blindes
  Überschreiben). Secret-**Rotation** bleibt Gate 1.
- **SA-4 — Zielzustand-Konvergenz: Umbauten, die den IST-Stand einem AKZEPTIERTEN
  Zielzustand nachweisbar näherbringen.** 🟡 **VORGESCHLAGEN (2026-08-07, Policy-PR,
  selbstbetreffend eingebracht — Ratifikation = wörtliches Owner-Go beim Review,
  nicht der Merge allein.)** Autonome Umsetzung inklusive plain-Merge, wenn ALLE
  Bedingungen erfüllt sind:
  1. Ein **akzeptiertes Artefakt** (ADR/KONZ/Issue mit Akzeptanzkriterien,
     `zielzustand.md` Pkt. 3) beschreibt den Zielzustand. „Naheliegend" heißt
     ausschließlich: der PR verlinkt das Artefakt UND benennt das
     Akzeptanzkriterium, auf das er einzahlt — nie das eigene Urteil des Agenten.
  2. Die Änderung ist **reversibel** und berührt weder Gate 1 (Irreversibles),
     Gate 2 (Prod-Zustand — in Auto-Deploy-Repos ist der Merge selbst Gate 2),
     Gate 3 (Security-/Governance-Config) noch Gate 5 (Spend). Gate 4 (drittes
     Repo) nur, wenn das Artefakt die Repos selbst benennt.
  3. **Abweichung vom Artefakt = Stopp + Scope-Checkpoint** — Zielzustand
     aktualisieren und erneut akzeptieren lassen, nicht stillschweigend erweitern.
  4. **Ratsche:** befristet bis Ritual-Lauf 2 (KONZ-038); die erste Fehlanwendung
     (Umbau ohne tragendes Artefakt oder an einem Gate vorbei) setzt die Klasse
     auf Einzelfreigabe zurück. Zählung über den Kill-Test unten (Signal G).
  **Ausdrücklich AUSGESCHLOSSEN:** Änderungen an dieser Policy, an Charta/
  Profilen/Permissions (selbstbetreffend — immer Owner), sowie alles, was eine
  wartende Owner-Entscheidung überholen würde (erkennbar an „wartet auf
  Entscheidung/Go" im Artefakt).

**Grenzen (ehrlich):** Diese Klassen wirken über die *Policy*, die der Classifier
liest — sie heben **keinen** Classifier-Hard-Deny auf (der ist Harness-seitig;
Realfall-Memory: User-Erlaubnis + Permission-Rule + Settings-Edit heben ihn nicht
auf). Sie füllen den *Graubereich*, den heute das Einzelwort füllt, nicht die
harten Denys. Neue Klasse nötig? → wird wie diese hier **ratifiziert** (Achim,
wörtlich), nicht still ergänzt.

**Kill-Test je Klasse (bindend, ADR-267-Reibungs-Kill-Muster):** Muss in >30 %
der Fälle, die unter eine SA-Klasse fallen, doch ein Einzel-OK eingeholt werden
(weil die Klasse zu weit/falsch schnitt oder ein Gate übersehen wurde), ist die
Klasse **zu überarbeiten oder zu streichen**, nicht zu flicken. Gemessen über
Signal G (unten) je Klasse.

## How to apply (Agent-Seite)

- **Pre-Flight vor jedem PR**: Merge-Pfad prüfen (Rulesets/required checks vs.
  reale Check-Namen), damit Gates VOR der Freigabe-Frage bekannt sind — nicht
  danach. (Realfall 2026-07-02: Check-Präfix `CI / gate` vs. Required-Kontext
  `ci / gate` erst nach 3 Denials entdeckt; Fix war ein gate-freier
  Workflow-Commit statt Ruleset-Edit/--admin.)
- **Root-Cause vor Eskalation**: Bevor ein Gate angefragt wird, prüfen ob ein
  gate-freier Fix existiert (Workflow/Code ändern statt Protection bypassen).
- **Ein Freigabe-Block pro Runde**: alle gated Aktionen gesammelt, mit exakten
  Kommandos und Eskalationsstufe im Wortlaut — der Permission-Classifier lässt
  wörtlich Freigegebenes durch, nicht mehr.
- **Verbale Freigabe gilt wörtlich**: „mergen" ≠ „--admin", „ausführen" ≠
  „Ruleset ändern". Präzise fragen.
- **Batch-Freigabe durable vermerken**: wird eine Freigabe für einen Batch (mehrere Repos/PRs,
  z.B. ein templated Rollout) erteilt, dies in der ERSTEN PR/Commit-Message des Batches
  wörtlich als „Batch approved by user" vermerken, damit sie später (Retro, Audit)
  nachvollziehbar bleibt. Realfall 2026-07-15 (KD-Sitemap-Rollout, 9 Repos, 6 echte
  Prod-Deploys): ein späteres Retro (`c25d21`) konnte anhand der Artefakte keine Freigabe
  für den Batch finden — nach Nutzerangabe war er freigegeben, nur nirgends vermerkt.
- **Tier-A-PRs bekommen Auto-Merge beim Anlegen** (Owner-Weisung 2026-07-18, deckt sich mit
  ADR-270 Tier A): Ein PR OHNE Prod-Deploy-on-main UND OHNE Governance-Inhalt (also Tools,
  Doku, Meta, Konzepte — nicht ADRs/Policies/Rulesets/Charta/Permissions) wird beim Erstellen
  mit GitHub-**Auto-Merge** versehen (`gh pr merge <N> --auto --squash|--merge`). Dann ist die
  **Owner-/Windsurf-Approval der einzige verbleibende Schritt** — GitHub merged selbst, sobald
  die Required Checks grün sind. Kein manueller Merge-Klick, KEIN Agent-Merge (der Classifier
  blockt Agent-Merges auf platform hart; Auto-Merge umgeht das sauber, weil GitHub merged, nicht
  der Agent). **Governance-PRs bleiben ausdrücklich manuell** — dort ist der bewusste menschliche
  Merge-Griff der Sinn des Gates (diese Policy-Änderung selbst ist so ein Fall: manuell gemergt).
  Voraussetzung repo-seitig: `allow_auto_merge=true` (bei achimdehnert/platform verifiziert 2026-07-18).

## Budget-Deklaration (Pflicht bei autonomen Läufen)

Gate 5 fragt nach der **Erlaubnis** für nennenswerten Spend. Diese Regel beantwortet die andere
Hälfte: **wie viel** ein Lauf ausgeben darf, bevor er von selbst aufhört. Beides zusammen, nicht
eines statt des anderen — eine Freigabe ohne Obergrenze ist ein offener Scheck.

**Ein autonomer Lauf** ist jeder, der ohne wartende Person weiterläuft: Queue-Abarbeitung
(`process-agent-queue`), Headless-Läufe (ADR-186), cron-getriebene Agenten, Multi-Agent-Fan-outs.

Er deklariert **vor dem Start** drei Zahlen, sichtbar im auslösenden Artefakt (Issue-Kommentar,
Job-Definition, Workflow-Kopf):

| Feld | Bedeutung | Fehlt die Angabe |
|---|---|---|
| `max_agenten` | gleichzeitige **und** insgesamt gestartete Teilagenten | **1** |
| `max_tokens` | Ausgabe-Budget des gesamten Laufs | Lauf startet **nicht** |
| `max_schreibzugriffe` | PRs, Commits, Issues, externe Aufrufe mit Wirkung | **0** — nur lesend |

Die Vorgabewerte sind mit Absicht die engste Auslegung: ein Lauf, der nichts deklariert, darf
lesen und sonst nichts. Das Fehlen einer Angabe ist damit keine stille Erlaubnis, sondern eine
laute Einschränkung — umgekehrt zum heutigen Zustand, in dem das Budget implizit ist und erst am
Rechnungsbetrag sichtbar wird.

**Erreicht ein Lauf eine seiner Grenzen, endet er als `abgebrochen: Budget`, nie als `fertig`.**
Ein Budget-Ende, das wie ein Erfolg aussieht, ist die teuerste Variante dieser Regel: der
Auftraggeber hält die Arbeit für erledigt und schaut nie nach. Dieselbe Fehlerklasse wie ein
Health-Check, der `succeeded` meldet und nichts geprüft hat (dev-hub#188).

> **Ehrliche Einschränkung — diese Regel ist heute Text, nicht Mechanik.** Sie beschreibt, was
> deklariert werden muss; **niemand liest die Felder bisher aus**. Eine Konvention ohne
> Durchsetzung driftet (`feedback_canon_decision_needs_enforcement_gate`). Der nächste Schritt ist
> deshalb kein weiterer Policy-Satz, sondern **eine** Stelle, die die Deklaration prüft und einen
> Lauf ohne sie nicht startet — sinnvollerweise dort, wo Läufe ohnehin entgegengenommen werden.
> Bis dahin gilt: fehlt die Deklaration, ist der Lauf **nicht** freigegeben, auch wenn er
> technisch startet.

**Herkunft:** Owner-Input 2026-08-02 aus einem externen Papier (dort als Pflichtfeld je autonomem
Lauf beschrieben). Zuschnitt auf die hiesigen Lauf-Arten und die Vorgabewerte stammen von hier.

## Effectiveness test (binding — falsify or cut)

Signal **G** = User-Roundtrips pro gate-pflichtiger Entscheidung (Ziel: 1).
Baseline: Session 2026-07-02 = 3 Roundtrips für 1 Entscheidungskomplex
(Merge #131). Nach ~10 Sessions messen (session-retro); wenn G nicht Richtung 1
konvergiert, Policy schneiden, nicht flicken.

## Changelog

- 2026-08-07: **SA-4 (Zielzustand-Konvergenz) VORGESCHLAGEN** — selbstbetreffend
  eingebracht (erweitert die Reichweite des Agenten), deshalb ungebündelter
  Policy-PR; Ratifikation nur durch wörtliches Owner-Go beim Review. Anlass:
  Owner-Frage „mehr Autonomie bei naheliegenden Umbauten, die IST dem Zielzustand
  näherbringen?" — Zuschnitt bindet „naheliegend" ans akzeptierte Artefakt
  (`zielzustand.md` Pkt. 3) statt ans Agenten-Urteil; Probe an zwei Realfällen
  vom selben Tag: Canary-Rückbau wäre NICHT gedeckt (wartende Owner-Entscheidung),
  D4-Regel-Extraktion wäre gedeckt gewesen.
- 2026-08-02: Abschnitt **Budget-Deklaration** ergänzt (Owner-Input aus einem externen Papier).
  Ergänzt Gate 5, ersetzt es nicht: Gate 5 regelt die Erlaubnis, die Deklaration die Obergrenze.
  Vorgabewerte bewusst als engste Auslegung (ohne Angabe: ein Agent, keine Schreibzugriffe, kein
  Start ohne Token-Budget), damit eine fehlende Angabe einschränkt statt stillschweigend zu
  erlauben. **Noch nicht durchgesetzt** — der Abschnitt sagt das ausdrücklich und benennt die
  fehlende Prüfstelle als nächsten Schritt; eine Konvention ohne Gate driftet
  (`feedback_canon_decision_needs_enforcement_gate`).
- 2026-07-12: **SA-1 + SA-3 RATIFIZIERT (Achim, wörtlich)** — Abschnitt
  „Standing-Authorization-Klassen" ergänzt (KONZ-platform-019 B2). SA-1 (Merge
  CI-grüner PR ohne Review-Pflicht+ohne Auto-Deploy) und SA-3 (Secret-Datei-
  Hausputz ohne Inhalts-Dump) gelten ab sofort. **SA-2 zurückgestellt** bis
  B1 (pfad-gescopte Review) — ID reserviert. *(Nachtrag 2026-08-10: hier stand
  „KONZ-019 B1"; B1 steht in **KONZ-platform-032**, nicht in KONZ-019. Der
  Fehlzeiger blieb vier Wochen unbemerkt, weil jede Prüfung in KONZ-019 nichts
  fand.)* Je Klasse >30%-Kill-Test
  (ADR-267-Muster). Ziel: den vom Classifier erzeugten Einzelwort-Zwang für
  gate-freie Aktionen abbauen, ohne einen Gate zu senken. Re-Ratifikation im
  Kapitäns-Kanal 2026-07-17 (PR #1105-Kommentar); SA-1/SA-3 werden erste
  Einträge der lotse-authorizations-Registry (Lotsen-Charta Art. 2.6).
- 2026-07-16: **Batch-Freigabe-Vermerk-Regel** ergänzt (How to apply) — nach Retro `c25d21`
  (KD-Sitemap-Rollout 2026-07-15, 9 Repos, 6 Prod-Deploys), das als ungegatet eingestuft wurde,
  weil eine erteilte Freigabe nirgends vermerkt war. Marker: „Batch approved by user" in der
  ersten PR/Commit-Message eines freigegebenen Batches.
- 2026-07-03: Von Achim ratifiziert (Session ausschreibungs-hub, wörtlich „3 go"
  auf den Freigabe-Block) — gilt org-weit als Policy.
- 2026-07-03: Initial DRAFT (Session ausschreibungs-hub).
