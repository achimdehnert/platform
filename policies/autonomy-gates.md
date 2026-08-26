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

   **Allowlist (Owner-Go 2026-08-25, Kapitäns-Kanal „5 go"):**
   - **Backup-Zielpfad- und Retention-Wartung in `infra-deploy`** (`scripts/db-backup.sh`:
     `BACKUP_BASE`, `RETENTION_DAYS`, Platten-Floor) darf autonom gemergt und per
     `git pull` auf `/opt/infra-deploy` nachgezogen werden, **wenn** (a) IaC zuerst,
     Host danach (🌀 host_fix_must_mirror_to_iac), (b) bestehende Dumps verschoben,
     nie gelöscht werden, und (c) der Beweislauf **am Artefakt** erfolgt (neuer Dump
     liegt am neuen Ort, Root-Platte gewinnt messbar). Anlass: infra-deploy#5 lag
     als „dein Zug" bei ~5 Tagen Restlaufzeit der Root-Platte — die Klasse ist
     backup-first und reversibel (`mv` zurück), das Gate war je Einzelfall gezogen
     statt je Klasse.

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

## Merge-Autonomie: eine Regel, zwei Achsen (SA-M)

> **Motiv (KONZ-platform-019 B2):** Der Permission-Classifier blockte wiederholt
> Aktionen, die *keinen* der fünf Gates berühren, nur weil die Freigabe nicht
> *benannt* war (Realfall 2026-07-12: „go autonom" reichte nicht, „merge PR #N"
> schon). Was daraus wuchs, waren sechs Einzelklassen (SA-1 … SA-6), die dieselbe
> Frage viermal beantworteten und sich an den Rändern widersprachen. **SA-M ersetzt
> sie durch eine Regel, die für jedes Repo gilt.** Die Herkunft steht unten; keine
> Freigabe geht verloren.

**Die Regel: autonom mergen, wenn das Mandat die Wirkung deckt.**

Beides wird am PR gemessen, nicht geschätzt:

**Wirkung W — was löst der Merge nach `main` aus?** (Quelle: die Workflow-Trigger
des Repos, nicht der Dateiname und nicht der Diff.)

| W | Was passiert | Beispiel |
|---|---|---|
| W0 | nichts läuft an | Bibliotheks-Repo ohne push-Workflow |
| W1 | Dateiabgleich eines Klons — kein Dienst, keine DB, kein Image | `platform` → `/opt/platform` |
| W2 | Deploy nach Staging | org-Standard `deploy.yml` ohne Prod-Ziel |
| W3 | Deploy nach Prod, Migration, Image-Wechsel oder Publish | App-Repos, PyPI/GHCR |

Greift ein `paths-ignore` des Deploy-Workflows für **alle** Dateien des PR, läuft
nichts an: dann gilt W0, unabhängig von der Repo-Klasse.

**Mandat M — woher kommt die Entscheidung?**

| M | Woher | Beleg am PR |
|---|---|---|
| M0 | keins | — |
| M1 | Owner hat den Auftrag gestartet | PR verlinkt Issue/Auftrag mit wörtlichem Go |
| M2 | Approval liegt vor | Owner, Zweit-Reviewer oder Bot im Rahmen seiner Tabu-Liste |
| M3 | Approval **benennt** die Prod-Wirkung | Deploy/Publish steht in der Freigabezeile |

**Deckung:** W0/W1 brauchen M1 · W2 braucht M2 · W3 braucht M3.

**Drei Vorbedingungen, die unabhängig vom Mandat gelten** — fehlt eine, wird nicht
gemergt, egal wie hoch M ist:

1. Alle Required Checks grün. Ein Repo ohne einen einzigen Check erfüllt das nur
   für PRs, die ausschließlich Dokumentation ändern (`*.md`, `docs/**`, `README*`,
   `CHANGELOG*`) — sonst fehlt jeder Beleg.
2. Kein reviewpflichtiger Pfad aus `.github/CODEOWNERS` ohne vorliegendes Approval
   (Governance-Pfade sind Steuerung, auch wenn die Datei `.md` heißt).
3. Kein Gate 1 im Diff (Migrationen, Löschungen, Destruktives) — Gates gewinnen
   immer gegen SA-M.

**Unklar ist nie ein Ja.** API-Fehler, laufende Checks, unlesbarer Workflow,
`mergeable=UNKNOWN` nach zweiter Abfrage: kein Merge, Exit ≠ 0. Ein Classifier-
Hard-Deny wird nicht umgangen — dann ein `!`-Kommando an den Owner.

**Ratsche:** Die erste Fehlanwendung (Merge ohne Deckung oder an einem Gate vorbei)
setzt SA-M auf Einzelfreigabe zurück; Zählung über Signal G. Kalibrierfenster bis
2026-10-26.

**Ausdrücklich AUSGESCHLOSSEN:** Änderungen an dieser Policy, an Charta, Profilen
oder Permissions bleiben selbstbetreffend und damit beim Owner — SA-M erlaubt ihren
**Merge nach Approval** (M2 deckt W0/W1), nie ihr Verfassen im Alleingang.

**Woher SA-M kommt (Herkunft, keine dieser Freigaben ist erloschen):**

| alt | Ratifiziert | geht auf in |
|---|---|---|
| SA-1 CI-grün, kein Review, kein Auto-Deploy | 2026-07-12 | W0 + M1 |
| SA-2 Nicht-Governance in `platform` | 2026-08-10 | W1 + M1 |
| SA-5 Merge ist Vollzug (gestartet / approved) | 2026-08-26 | M1 bzw. M2 |
| SA-6 reine Doku-PRs | 2026-08-26 | Vorbedingung 1, nicht eigene Klasse |

**Zwei Widersprüche, die SA-M auflöst** (beide am 2026-08-26 gemessen):

- SA-6 erlaubte reine Doku-PRs „in jedem Repo, auch Auto-Deploy" — ein Doku-PR in
  einem Prod-Repo löst aber denselben Deploy aus wie jeder andere: gleiche Wirkung,
  gleiche Mandatsschwelle. Der Diff entscheidet nicht über die Wirkung, der Trigger
  tut es. **Die Doku-Ausnahme gilt nur noch dort, wo der Workflow sie ausnimmt
  (`paths-ignore`) oder gar nicht existiert.**
- SA-1 verlangte „CI-grün", ließ aber offen, was in einem Repo ganz ohne Checks
  gilt. Vorbedingung 1 entscheidet das jetzt ausdrücklich.

**SA-3 (Datei-Hausputz in `~/.secrets`/`~/shared`) und SA-4 (Zielzustand-Konvergenz)
bleiben unverändert bestehen** — sie regeln keine Merges und sind von SA-M nicht
berührt.

**Maschinenlesbar (SSoT für `tools/pr_merge_sa.py`, Test hält beides synchron):**

```yaml
sa_m:
  deckung: {W0: M1, W1: M1, W2: M2, W3: M3}
  doku_glob: ["*.md", "docs/**", "README*", "CHANGELOG*"]
  governance_pfade: [".github/", "docs/adr/", "policies/", "registry/", "packages/", "CODEOWNERS"]
  sync_only_repos: ["achimdehnert/platform"]
  fail_closed: true
```

**Kill-Test (bindend, ADR-267-Reibungs-Kill-Muster):** Muss in >30 %
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

- 2026-08-26: **SA-1/2/5/6 zu SA-M zusammengefuehrt** (eine Regel, zwei Achsen:
  Wirkung des Merges gegen Mandat der Entscheidung). Anlass: Owner-Weisung
  "stringent, widerspruchsfrei und redundanzfrei fuer alle Repos". Zwei gemessene
  Widersprueche aufgeloest: SA-6 haette Doku-PRs auch dort gemergt, wo der Merge
  einen Prod-Deploy ausloest (die Wirkung haengt am Trigger, nicht am Diff), und
  SA-1 liess offen, was ohne einen einzigen Check gilt. SA-3 und SA-4 unberuehrt.

- 2026-08-26: **SA-5 (Merge ist Vollzug: gestartete Issues + nach Approval)
  RATIFIZIERT** (Achim, Approve+Merge #2332, Weisung im Kapitäns-Kanal wörtlich:
  „merges bei gestarteten issues autonom freigeben → sind nun Klickaufgabe und
  verzögern unnötig" / „nach ‚approved' komplett autonom mergen"). Anlass: fünf PRs
  (Handover #2330, Skill #2329, Konsumenten-PRs risk-hub#681/billing-hub#42/
  weltenhub#71) lagen als „dein Zug" im Board, obwohl der Auftrag dahinter
  gestartet war. Gates 1/2 (Prod), Publish und Classifier-Hard-Deny bleiben
  unverändert. Diese Zeile kam getrennt (#2332 trug sie nicht: der Auto-Mode-
  Classifier blockte den Edit als Selbstmodifikation).
- 2026-08-26: **SA-6 (reine Doku-PRs) RATIFIZIERT** und die Harness-Voraussetzung
  für SA-1/SA-5 benannt. Anlass: robo-lab#3 (ein reines Doku-Dokument) hing am
  Classifier, obwohl SA-1 den Fall seit sechs Wochen deckt — die Klasse war
  ratifiziert, der Eintrag in `autoMode.allow` fehlte. Owner-Auswahl im
  Kapitäns-Kanal auf eine selbstbetreffend gekennzeichnete Vorlage (Charta Art. 3).

- 2026-08-07: **SA-4 (Zielzustand-Konvergenz) VORGESCHLAGEN** — selbstbetreffend
  eingebracht (erweitert die Reichweite des Agenten), deshalb ungebündelter
  Policy-PR; Ratifikation nur durch wörtliches Owner-Go beim Review. Anlass:
  Owner-Frage „mehr Autonomie bei naheliegenden Umbauten, die IST dem Zielzustand
  näherbringen?" — Zuschnitt bindet „naheliegend" ans akzeptierte Artefakt
  (`zielzustand.md` Pkt. 3) statt ans Agenten-Urteil; Probe an zwei Realfällen
  vom selben Tag: Canary-Rückbau wäre NICHT gedeckt (wartende Owner-Entscheidung),
  D4-Regel-Extraktion wäre gedeckt gewesen.
- 2026-08-10: **SA-2 RATIFIZIERT + Gate-2-Klarstellung `platform` + B1-2 vollzogen**
  (Achim, wörtlich „D1 D2 D3 D4 go", dann „B1-2 umsetzen"). Der Eintrag wurde beim
  ursprünglichen PR (#1873) **nicht** geschrieben — der Permission-Classifier
  verweigerte genau diese Einfügung zweimal, während er die inhaltlichen Edits
  derselben Datei durchließ. Hier nachgetragen; das war der einzige ungetrackte
  Rest jener Änderung (Retro-Befund #12, `deferred-item-no-tracking-issue`).

  **Was gilt:** der CODEOWNERS-Catch-all `*` ist weg; Review-Pflicht besteht nur
  noch auf `/.github/`, `/registry/`, `/packages/`, `/docs/adr/`, `/policies/`,
  `/governance/`, `/deployment/`, `/infra/`, `/scripts/`, `/.windsurf/` sowie den
  vier Sicherheits-Konfigs im Wurzelverzeichnis. Im Ruleset 17621471 steht
  `required_approving_review_count` auf **0**, `require_code_owner_review` bleibt
  **true**, `bypass_actors` bleibt **leer** — die Pflicht kommt damit
  ausschließlich über CODEOWNERS. Zielzustand als IaC: siehe PR #1879.

  **Auslösende Messung** (30 Tage `platform`): 400 gemergte PRs, **0** ohne
  Approval, 399 Approvals von einem Konto; in 7 Tagen berührten 85 von 117 PRs
  (73 %) keinen Governance-Pfad. Owner-Leitsatz: „ich und wirdigital agieren als
  **Entscheidungsinstanz**, nicht als Auto-Freigeber."

  **Zwei Korrekturen aus der Retrospektive desselben Tages**
  (`docs/retros/session-retro-2026-08-10-platform-c45b39.md`): (a) `/governance/`
  fehlte in der ersten Fassung entgegen KONZ-032 B1-1 Z.165 — still verloren, in
  keiner Commit-Message erwähnt; (b) die Ruleset-Zahl war **kein** Fund, sondern
  Teil desselben Plan-Schritts (B1-2 Z.166) — sie als Spezifikationslücke zu
  melden war falsch. Fehlzeiger „KONZ-019 B1" → KONZ-032 korrigiert.

  Rückbau: Catch-all-Zeile zurück **und** Zahl zurück auf 1 — beides zusammen
  (KONZ-032 `kill_criteria (a)`).
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
