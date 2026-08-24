---
status: proposed
decision_date: 2026-08-24
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: []
supersedes: []
amends: []
related: [ADR-236, ADR-268]
implementation_status: not-started
last_reviewed: 2026-08-24
staleness_months: 6
tags: [governance, github, organisation, repo-zuordnung, ownership]
---

# ADR-297: In welche GitHub-Organisation gehört ein Repo?

## Kontext

Die Frage kam am 2026-08-23 aus einem konkreten Anlass: ein Befund über `weltenhub`
sollte als Issue verankert werden, und dabei stellte sich heraus, dass die Zuordnung
nirgends geregelt ist. Der Agent hatte zunächst behauptet, `risk-hub` liege in
`achimdehnert` — die `CLAUDE.md`-Tabelle sagt das —, während `git remote get-url`
`iilgmbh/risk-hub` liefert. Die Beschreibung war falsch, und niemand hatte es gemerkt,
weil es keine Regel gibt, an der man es hätte messen können.

### Ist-Stand, gemessen am 2026-08-24

| Ziel | Repos (lokale Klone) |
|---|---|
| `achimdehnert` | 56 |
| `iilgmbh` | 11 |
| `meiki-lra` | 3 |
| `bahn-sqf` | 2 |
| `ttz-lif` | 1 |

Die elf unter `iilgmbh`: `ausschreibungs-hub`, `chat-hub`, `iil-doc-templates`,
`iilgmbh-iil-data`, `iilgmbh-iil-relaunch`, `iil-klickdummy`, `iil-pet-portal`,
`iil-voice-agent`, `risk-hub`, `shared-ci`, `tax-hub`. Das Muster wirkt
kunden-/auftragsbezogen, ist aber nirgends ausgesprochen.

### Der Befund, der die Entscheidung trägt

```
gh api users/achimdehnert --jq .type   -> "User"
```

**`achimdehnert` ist ein persönliches Konto, keine Organisation.** Das ist keine
Geschmacksfrage, sondern eine strukturelle Grenze. Ein persönliches Konto kennt keine
Teams, keine organisationsweiten Rulesets, keine Org-Secrets und keine
Org-Sicherheitsrichtlinien — und die Repos hängen an **einer** Person. 56 von 73 Repos,
darunter produktive Dienste, liegen dort.

`iilgmbh` ist demgegenüber eine Organisation, mit `default_repository_permission: read`.
**Das allein ist der belegte Unterschied** — und er trägt die Entscheidung.

### Was heute *gegen* Eile spricht — ebenfalls gemessen

```
gh api orgs/iilgmbh/teams --jq length              -> 0
gh api orgs/iilgmbh --jq .two_factor_requirement_enabled -> false
```

**Die Org hat null Teams und keine 2FA-Pflicht.** Die Vorteile sind damit heute
*potenziell*, nicht realisiert. Ein Repo dorthin zu verschieben bringt im Moment vor
allem **Eigentümer-Kontinuität** — die granulare Rechteverwaltung existiert erst, wenn
sie eingerichtet wird.

**Nicht messbar mit dem aktuellen Token** (Scopes: `read:org`, `repo`, `workflow`,
`write:packages`, `gist`, `admin:public_key`): Org-Rulesets (`admin:org`) und der
Enterprise-Sitzverbrauch (`admin:enterprise`). Beides ist offen und gehört vor der
Annahme geprüft.

### Korrektur: „iilgmbh hat Enterprise" ist mit diesem Zugang nicht belegbar

Ein erster Entwurf dieses ADR führte `gh api orgs/iilgmbh --jq .plan.name -> "enterprise"`
als Vorteil an und leitete daraus einen Widerspruch zu ADR-236 ab. **Beides war falsch,
weil das Feld nicht unterscheidet.** Die Gegenprobe über alle vier Orgs:

| Org | `.plan` |
|---|---|
| `iilgmbh` | `{"filled_seats":3,"name":"enterprise","private_repos":999999,"seats":2,"space":976562499}` |
| `bahn-sqf` | *byte-identisch* |
| `ttz-lif` | *byte-identisch* |
| `meiki-lra` | *byte-identisch* |

ADR-236 stellt ausdrücklich fest, dass `ttz-lif` und `meiki-lra` **außerhalb** der
Enterprise laufen. Trotzdem melden sie dieselben Plandaten. Ein Wert, der bei
Zugehörigen und Nicht-Zugehörigen identisch ist, ist kein Nachweis der Zugehörigkeit —
er ist ein Artefakt der Abrechnungssicht, die dieser Token sieht. Auffällig zusätzlich:
`filled_seats: 3` bei `seats: 2`, überall gleich.

**ADR-236 bleibt damit unwidersprochen.** Ob `iilgmbh` heute in der Enterprise ist, ist
mit `read:org` **nicht** feststellbar; der Nachweis braucht `admin:enterprise`.
Vorbereitet in `platform/scripts/checks/enterprise-zugehoerigkeit.sh` — der Lauf braucht
eine interaktive Anmeldung und gehört dem Owner.

Für die Entscheidung ist das **nicht tragend**: sie steht auf „Organisation vs.
persönliches Konto", nicht auf dem Abrechnungsplan. Ein etwaiger Enterprise-Vorteil käme
obendrauf.

### Was die bestehenden ADRs sagen — und was nicht

**[ADR-268](ADR-268-projekt-assurance-tiers.md)** zieht die einzige benachbarte Linie, und
sie verläuft anders als vermutet: `achimdehnert` und `iilgmbh` stehen dort gemeinsam auf
der Seite `nicht-sovereign`, gegenüber `ttz-lif`/`meiki-lra` (`sovereign`). Die
Beispieltabelle führt `writing-hub` (achimdehnert) und `ausschreibungs-hub` (iilgmbh) im
**selben** Quadranten Q2. Auf der Souveränitätsachse ist die Org-Wahl also ausdrücklich
**ohne** Bedeutung.

**[ADR-236](ADR-236-altd-enterprise-boundary.md) hat den entscheidenden Satz bereits.**
Ein erster Entwurf dieses ADR schrieb, ADR-236 regele „die Enterprise-Grenze, nicht die
Zuordnung einzelner Repos" — das stimmt für die *Zuordnung*, verschweigt aber, dass dort
seit dem 2026-06-03 API-verifiziert steht:

> Der User-Account **`achimdehnert`** hält 54 Repos und kann **keiner** Enterprise
> beitreten (User ≠ Org).

Das ist genau der Befund, auf dem die Entscheidung hier steht. Er ist keine Entdeckung
dieses ADR, sondern eine **Wiederentdeckung** — zweieinhalb Monate später, weil niemand
die Konsequenz gezogen hatte. Das ist selbst ein Datenpunkt: ein Fakt in einem ADR wirkt
nicht, solange keine Regel ihn anwendet.

ADR-236 hält zusätzlich fest, dass die Abrechnung **pro Person** läuft (damals 2 Sitze),
nicht pro Org oder Repo — ein Transfer kostet demnach keine zusätzlichen Sitze.

### Der Widerspruch, der die Begründung schwächt

ADR-236 §1.1 sagt weiter:

> Enterprise **`iilgmbh`** enthält **nur** `bahn-sqf` (1 Member-Org). Vier weitere Orgs
> laufen auf **separaten Team-Plänen außerhalb** der Enterprise: `iilgmbh` (Org ≠
> Enterprise-Slug), `ttz-lif`, `meiki-lra`, `pactive-de`.
>
> Die Enterprise hat bereits die **richtige Security-Config** … aber angewandt auf **nur
> 3 `bahn-sqf`-Repos**.

**Wenn das noch gilt, ist ein hier oft unterstellter Vorteil keiner:** ein Repo, das nach
`iilgmbh` (die *Org*) wandert, erbt die Security-Konfiguration der *Enterprise* `iilgmbh`
**nicht** — die Org liegt außerhalb. Der Gewinn beschränkte sich dann auf das, was jede
Organisation bietet: Teams, Org-Secrets, Org-Rulesets, Eigentümer-Kontinuität. Das trägt
die Entscheidung immer noch, aber es ist weniger, als der Name „Enterprise" nahelegt.

Ob es noch gilt, ist **offen** (Offener Punkt 3). Der Stand ist eine Momentaufnahme vom
2026-06-03, und ADR-236 sagt selbst, er sei „nicht eingefroren gemeint". Die Messung dazu
ist damit **entscheidungstragend**, nicht kosmetisch: fällt sie so aus wie ADR-236, bleibt
die Begründung „Organisation statt persönliches Konto" — fällt sie anders aus, kommt der
Enterprise-Vorteil obendrauf.

Es gibt damit keine Regel, gegen die man verstoßen könnte — nur eine gewachsene
Verteilung und einen Fakt, aus dem nie eine Regel wurde.

## Entscheidung (Vorschlag)

**Leitsatz: die Organisation ist der Standard, das persönliche Konto die begründete
Ausnahme.**

| Klasse | Ziel | Begründung |
|---|---|---|
| Produktive Dienste mit Deploy | `iilgmbh` | Eigentümer-Kontinuität, Org-Rechte, Org-Secrets |
| Geteilte Pakete und CI | `iilgmbh` | mehrere Repos hängen daran |
| Kunden-/Auftragsbezug | `iilgmbh` | geschäftlicher Kontext |
| Souveräne Mandate | `ttz-lif` / `meiki-lra` | unverändert, ADR-268 Q3/Q4 |
| Experimente, Sandboxes, Privates | `achimdehnert` | keine Betriebsverantwortung |

**Neuzugänge folgen dem Leitsatz sofort.** Bestehende Repos wandern **nicht** pauschal,
sondern nur mit Anlass (siehe Migration).

### Die drei konkret genannten Repos

| Repo | Heute | Vorschlag | Anmerkung |
|---|---|---|---|
| `risk-hub` | `iilgmbh` | bleibt | **liegt bereits dort** — kein Transfer nötig |
| `writing-hub` | `achimdehnert` | → `iilgmbh` | produktiv, Auto-Deploy, ADR-268 Q2 |
| `weltenhub` | `achimdehnert` | → `iilgmbh` | produktiv; bildet ein Paar mit writing-hub |

`writing-hub` und `weltenhub` sind über `iil-weltenfw` und eine laufende API verbunden.
Sie gehören **zusammen** verschoben oder gar nicht — eine Aufteilung auf zwei Orgs wäre
schlechter als der Ist-Zustand.

## Alternativen

**A · Alles bleibt, wie es ist.** Kostet nichts, löst nichts. Der Anlass — eine falsche
Org-Angabe, die niemandem auffiel — tritt wieder auf. *Verworfen*, aber siehe „Offene
Punkte": ohne Teams und 2FA ist der Gewinn heute kleiner als er klingt.

**B · Alles nach `iilgmbh`, auch Experimente.** Maximal einheitlich, aber jeder
Wegwerf-Prototyp belastet dann die Org-Rechteverwaltung und die Sitzzählung.
*Verworfen* — die Ausnahme für Privates ist billiger als ihre Abschaffung.

**C · `achimdehnert` in eine Organisation umwandeln.** GitHub kann das, es würde alle 56
Repos auf einmal lösen. Aber: das persönliche Konto ist zugleich die Identität, mit der
committet, authentifiziert und in fremden Orgs mitgearbeitet wird — die Umwandlung ist
nicht rückgängig zu machen und trifft weit mehr als die Repo-Zuordnung. *Verworfen als
Nebenschritt*; wäre ein eigenes ADR mit eigener Risikobetrachtung.

## Konsequenzen

**Ein Transfer ist nicht nur ein Klick.** GitHub legt für Repo-URLs eine Weiterleitung
an — für andere Dinge nicht:

| Betroffen | Fundstelle (gemessen für `weltenhub`) |
|---|---|
| Registry | `infra/ports.yaml:252`, `registry/repos.yaml:283`, `registry/canonical.yaml:1105` |
| Werkzeuge | `tools/bf-deploy/bf_deploy/config.py:27`, `tools/sharedci/pin_landschaft.py:7` |
| Container-Images | GHCR-Pfad `ghcr.io/<org>/<repo>` wandert **nicht** mit |
| Sonstiges | Host-Remotes, Deploy-Secrets, Branch-Protection/Rulesets je Repo |

Der GHCR-Punkt ist der teuerste: in diesem Umfeld ist ein Deploy schon einmal an einer
GHCR-Zugriffslücke hängengeblieben, die ein Neuanlegen des Packages erforderte.

**Positiv:** Repos unter einer Org überleben den Ausfall einer Person; Rechte lassen sich
über Teams statt über Einzelzugriffe vergeben; Secrets und Rulesets werden einmal statt
je Repo gesetzt.

## Migration (Vorschlag, nicht Teil der Annahme)

1. **Voraussetzung zuerst, sonst ist der Umzug ein Selbstzweck:** in `iilgmbh` mindestens
   ein Team anlegen und die 2FA-Pflicht einschalten. Solange beides fehlt, ist der
   Org-Vorteil eine Behauptung.
2. **Pilot mit einem Repo**, das keinen GHCR-Pfad hat, und die Fundstellen-Liste oben
   abarbeiten. Erst danach entscheiden, ob der Rest folgt.
3. `writing-hub` + `weltenhub` **gemeinsam**, nach dem Piloten, mit geplantem
   GHCR-Neuaufbau.
4. `CLAUDE.md`-Org-Tabelle korrigieren — sie ist heute nachweislich falsch (`risk-hub`).

## Offene Punkte vor der Annahme

1. Org-Rulesets von `iilgmbh` prüfen (`admin:org`-Scope fehlt).
2. Enterprise-Sitzverbrauch prüfen (`admin:enterprise`-Scope fehlt) — kostet ein Transfer
   Sitze?
3. **Entscheidungstragend:** Enterprise-Zugehörigkeit von `iilgmbh` klären — mit
   `admin:enterprise`, nicht über `orgs/*/plan` (siehe Korrektur oben). Liegt die Org
   weiterhin außerhalb der Enterprise (so ADR-236, Stand 2026-06-03), entfällt der
   Security-Config-Vorteil und die Begründung ruht allein auf „Organisation statt
   persönliches Konto". Skript: `scripts/checks/enterprise-zugehoerigkeit.sh`.
4. Sitzverbrauch: `filled_seats: 3` bei `seats: 2` — kostet ein Transfer Sitze?

## Kill-Gate

Wenn bis **2026-11-24** weder ein Team noch die 2FA-Pflicht in `iilgmbh` eingerichtet ist,
war der Org-Vorteil nicht der wahre Grund — dann wird dieses ADR auf „rejected" gesetzt
und der Ist-Zustand bleibt bewusst.
