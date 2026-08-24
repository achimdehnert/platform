---
status: accepted
decision_date: 2026-08-24
deciders: [Achim Dehnert]
consulted: [Claude Code, Zweitmeinung A (extern, LLM), Zweitmeinung B (extern, LLM)]
informed: []
supersedes: []
amends: []
related: [ADR-236, ADR-255, ADR-268]
implementation_status: partial
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

`iilgmbh` ist demgegenüber eine Organisation. **Das allein ist der belegte Unterschied**
— und er trägt die Entscheidung.

### Wie weit die Org-Vorteile heute realisiert sind — gemessen 2026-08-24

```
gh api orgs/iilgmbh/teams --jq length                       -> 0
gh api orgs/iilgmbh --jq .two_factor_requirement_enabled    -> false
gh api orgs/iilgmbh --jq .default_repository_permission     -> "read"
gh api orgs/iilgmbh --jq .members_can_create_repositories   -> true
gh api "orgs/iilgmbh/members?role=admin" --jq '.[].login'   -> achimdehnert, wirdigital
gh api  orgs/iilgmbh/members            --jq '.[].login'    -> achimdehnert, wirdigital
gh api  orgs/iilgmbh/outside_collaborators                  -> []
```

> **Nachtrag vom Nachmittag desselben Tages — zwei dieser Werte sind überholt.**
> `teams` steht auf **1** (`maintainers`, besetzt, trägt `maintain` auf `risk-hub`) und
> `two_factor_requirement_enabled` auf **true**. Die Zeilen oben bleiben stehen, weil die
> daraus gezogenen Schlüsse den Weg dorthin erklären — aber wer sie als heutigen Stand
> liest, liegt falsch. Details unter „Migration → Voraussetzungen".

Vier Dinge folgen daraus, und drei davon widersprachen dem, was vor der Messung
plausibel schien:

1. **Es gibt bereits zwei Org-Owner**, nicht einen. Die Kritik „eine Org mit einem
   einzigen Owner liefert keine Eigentümer-Kontinuität" trifft in dieser Form nicht zu.
   **Nicht geprüft** ist allerdings das, worauf es ankommt: ob `wirdigital` eine von
   `achimdehnert` unabhängige, handlungsfähige Vertretung ist (eigener 2FA-Faktor,
   eigener Recovery-Weg, im Ernstfall erreichbar) oder ein Zweitkonto derselben Person
   und derselben Geräte. **Der Owner-Zähler beantwortet die Kontinuitätsfrage nicht —
   der getestete Vertretungsweg tut es** (Voraussetzung V1, siehe Migration).
2. **`default_repository_permission: read` ist heute kein Vertraulichkeitsrisiko**, weil
   die Org genau zwei Mitglieder hat und beide ohnehin Owner (also `admin`) sind; es gibt
   null Outside Collaborators. Der Default wirkt erst in dem Moment, in dem ein **drittes,
   nicht-privilegiertes Mitglied** hinzukommt — dann bekommt es Leserechte auf **alle**
   Org-Repos, auch die kunden- und auftragsbezogenen. Das ist keine Bedingung für die
   Annahme, sondern eine Bedingung für den ersten Nicht-Owner-Zugang (Bedingung B1).
3. **Null Teams, keine 2FA-Pflicht** — zum Zeitpunkt dieser Messung. Die granulare
   Rechteverwaltung existiert erst, wenn sie eingerichtet wird; bis dahin brächte ein
   Transfer vor allem Eigentümer-Kontinuität, und die stand und fiel mit Punkt 1.
   **Beides ist noch am selben Tag eingerichtet worden** (V2 und V3, siehe Migration) —
   der Satz beschreibt damit die Ausgangslage der Entscheidung, nicht den Ist-Zustand.
4. `members_can_create_repositories: true` heißt: der Leitsatz dieses ADR wird von der
   Org-Konfiguration **nicht** durchgesetzt. Er wirkt nur, solange ihn jemand anwendet
   (siehe „Durchsetzung").

> **Auch das ist überholt — und der Irrtum ist lehrreicher als die Messung.** Der Satz
> unten schloss von der `gh`-Anmeldung auf „nicht messbar". Tatsächlich lag im
> Secrets-Store ein Enterprise-PAT mit `admin:org` **und** `admin:enterprise`; beide
> vermeintlich verschlossenen Fragen waren in Minuten beantwortet (Rulesets: keine;
> Enterprise: vier Member-Orgs). **Die Grenze lag nicht am Zugang, sondern daran, wo ich
> nachgesehen habe.**

**Nicht messbar mit dem aktuellen Token** (Scopes: `read:org`, `repo`, `workflow`,
`write:packages`, `gist`, `admin:public_key`): Org-Rulesets (`admin:org`) und die
Enterprise-Verwaltungssicht (`admin:enterprise`). Zur Enterprise-Zugehörigkeit selbst
siehe den nächsten Abschnitt — sie ist auch ohne diesen Scope entscheidbar, sobald man
eine Negativkontrolle mitmisst.

### Die Enterprise-Frage: zweimal falsch beantwortet, jetzt mit Negativkontrolle

Diese Frage hat den ADR bereits **zwei** Fehlschlüsse gekostet, in entgegengesetzte
Richtungen — sie ist deshalb hier vollständig ausgeschrieben.

**Fehlschluss 1 (Erstentwurf):** `gh api orgs/iilgmbh --jq .plan.name -> "enterprise"`
wurde als Beleg für Enterprise-Zugehörigkeit genommen — richtiges Ergebnis, aber ohne
Kontrolle, also kein Beleg.

**Fehlschluss 2 (die „Korrektur"):** Die Gegenprobe über `bahn-sqf`, `ttz-lif` und
`meiki-lra` ergab byte-identische Plandaten. Daraus wurde geschlossen, das Feld
unterscheide nicht. **Der Schluss war falsch, weil die Kontrolle keine war:** er stützte
sich auf ADR-236 §1.1, wonach `ttz-lif` und `meiki-lra` außerhalb der Enterprise lägen —
§1.1 ist dort aber die **Ausgangslage vom 2026-06-03**, die ADR-236 mit seiner eigenen,
am selben Tag ausgeführten Entscheidung aufhebt (S1, Enterprise-PAT-verifiziert: vier
Member-Orgs `bahn-sqf`, `iilgmbh`, `meiki-lra`, `ttz-lif`). Alle drei „Kontrollen" waren
in Wahrheit **Mitglieder**. Drei Positivfälle sind keine Negativkontrolle.

**Die echte Negativkontrolle** ist `pactive-de`: ADR-236 §2 nimmt sie ausdrücklich
**nicht** auf (`central-ok`, aber „nur mit Zustimmung der Dritt-Owner — kein einseitiger
Move"; `achimdehnert` ist dort nur `member`). Gemessen 2026-08-24:

| Org | ADR-236-Status | `gh api orgs/<org> --jq .plan` |
|---|---|---|
| `iilgmbh` | Member (S1) | `{"filled_seats":3,"name":"enterprise","seats":2,…}` |
| `bahn-sqf` | Member | *byte-identisch* |
| `ttz-lif` | Member | *byte-identisch* |
| `meiki-lra` | Member | *byte-identisch* |
| **`pactive-de`** | **nicht aufgenommen** | `{"filled_seats":9,"name":"team","seats":11,…}` |

**Das Feld unterscheidet.** Vier Mitglieder melden `enterprise` und dieselben
Enterprise-Zahlen; die eine Nicht-Mitgliedsorg meldet ihren eigenen `team`-Plan mit
eigenen Zahlen. Positiv- und Negativfall trennen sauber, und das Ergebnis deckt sich mit
der unabhängigen Enterprise-PAT-Messung in ADR-236.

**Befund: Org `iilgmbh` ist Mitglied der Enterprise `iilgmbh`.** Damit ist die Frage, die
der Erstentwurf als „entscheidungstragend offen" führte, **beantwortet** — nicht durch
einen neuen Zugang, sondern durch eine Kontrolle, die vorher fehlte.

**Am Goldstandard bestätigt (2026-08-24, noch am selben Tag).** Der Enterprise-PAT aus
`~/.secrets/github_Enterprise_PAT` trägt `admin:enterprise`; die Mitgliederliste kommt
nicht über REST (`enterprises/<slug>/organizations` → 404), sondern über GraphQL:

```
gh api graphql -f query='query { enterprise(slug:"iilgmbh") {
  organizations(first:20) { totalCount nodes { login } } } }'
-> totalCount 4: bahn-sqf, iilgmbh, meiki-lra, ttz-lif
```

Vier Mitglieder, `iilgmbh` darunter, `pactive-de` nicht. Damit ist die
Negativkontroll-Methode nicht nur plausibel, sondern **gegen den Goldstandard geprüft**
— `.plan.name` und die Mitgliedschaft stimmen bei allen fünf gemessenen Orgs überein.

**Was daraus für diesen ADR folgt:** Der Enterprise-Vorteil ist kein „käme obendrauf,
wenn", sondern eine heute vorhandene Eigenschaft des Ziels. Ein Repo, das nach Org
`iilgmbh` wandert, landet **innerhalb** der Enterprise und damit im Geltungsbereich der
dortigen Security-Konfiguration (ADR-236 §2.2: Secret Scanning + Push Protection als
apply-to-all, Config 17 als Default-for-new). Das ist der einzige Org-Vorteil, der **nicht**
erst eingerichtet werden muss — anders als Teams und 2FA. Er verbessert die Nutzenrechnung
von Ebene 2, ändert aber an Ebene 1 nichts: die Regel „Organisation statt persönliches
Konto" trägt auch ohne ihn.

**Der Nebenbefund war kein Kuriosum — er ist gemessen bestätigt.** `filled_seats: 3` bei
`seats: 2` sah nach einem Artefakt der Abrechnungssicht aus. Die Enterprise-Abfrage sagt
etwas anderes:

```
gh api enterprises/iilgmbh/consumed-licenses
-> {"total_seats_purchased": 2, "total_seats_consumed": 3}
-> Verbraucher: achimdehnert, iljalerch, wirdigital
```

ADR-236 nennt zwei Sitze (`achimdehnert`, `iljalerch`) und stellt die dort attestierte
Kostenneutralität ausdrücklich unter die Bedingung „**keine 3. Person** + keine
Vertrags-Floor". **`wirdigital` ist die dritte Person** — dieselbe, die als zweiter
Org-Owner die Eigentümer-Kontinuität trägt. Die Bedingung, unter der ADR-236 seine
Kostenaussage gestellt hat, gilt nicht mehr.

Das ist ein Befund über **ADR-236**, nicht über die Repo-Zuordnung: ein Repo-Transfer
kostet weiterhin keine Sitze (Abrechnung pro Person). Aber drei verbrauchte gegen zwei
gekaufte Sitze ist eine offene kaufmännische Frage, kein Rundungsfehler → **Amendment an
ADR-236 vorgeschlagen**, Owner-Entscheidung
([#2262](https://github.com/achimdehnert/platform/issues/2262)).

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
nicht pro Org oder Repo. **Damit ist die Sitzfrage für Repo-Transfers beantwortet: ein
Transfer kostet keine zusätzlichen Sitze.** Der Erstentwurf führte diese eine Frage als
zwei offene Punkte (2 und 4); das ist hier zusammengezogen. Was davon getrennt offen
bleibt — der überzählige belegte Sitz — steht im nächsten Abschnitt und ist ein Befund
über ADR-236, nicht über die Repo-Zuordnung.

**[ADR-255](ADR-255-iilgmbh-org-migration-pypi-family.md)** ist der nächste Verwandte auf der
Werkzeugseite: dort existiert mit `tools/iil_migration_check.py` bereits ein
idempotenter, read-only Abgleich „Registry-Behauptung gegen echten GitHub-Owner", der
genau die Fehlerklasse dieses ADR fängt (*„registry says owner/name X, gh resolves to
Y"*). Er ist auf den `iil-*`-Namensraum zugeschnitten und **in keinem Workflow
verdrahtet** — geprüft: kein Treffer in `.github/workflows/`. Das Muster ist da, die
Reichweite fehlt.

**[KONZ-platform-012](../konzepte/KONZ-platform-012-platform-org-migration.md)** ist der
Fall, den dieser ADR am wenigsten übersehen darf: dort liegt seit dem 2026-07-05 die
phasen-gegatete Vorlage, `platform` selbst vom User-Konto in die Org zu heben
(`pipeline_status: idea`, `review_by: 2026-09-15`). Zwei Konsequenzen:

1. **Die Klassenregel dieses ADR trifft `platform`.** Es ist geteilte CI-Grundlage —
   Klasse 3. Der Leitsatz sagt damit dasselbe wie KONZ-012, nur allgemeiner.
2. **Dieser ADR entscheidet den Fall trotzdem nicht.** KONZ-012 besitzt ihn, samt
   Vorbedingungen (repointbare Alias-Stelle für `uses:`-Referenzen, grüner Consumer-CI-Lauf
   gegen den neuen Pfad) und eigenem Kill-Gate. Ein zweiter Entscheidungsort für dasselbe
   Repo wäre genau die zweite Wahrheit, gegen die dieser ADR geschrieben ist. `platform`
   trägt deshalb den Status `geplant (KONZ-012)`, nicht `kandidat`.

Bemerkenswert ist das Kill-Kriterium von KONZ-012: es verlangt einen „verifizierten
2. Owner" — dieselbe Bedingung, die hier als V1 steht, dort schon seit Juli und für die
PyPI-Org. Die Sorge ist im Bestand also nicht neu; sie war nur nie verallgemeinert.

### Der „Widerspruch", der keiner war

Der Erstentwurf zitierte ADR-236 §1.1 („Enterprise `iilgmbh` enthält **nur** `bahn-sqf`;
vier weitere Orgs laufen auf separaten Team-Plänen **außerhalb**") und leitete daraus ab,
ein Repo in der Org `iilgmbh` erbe die Enterprise-Security-Konfiguration **nicht**.

**Das war ein Lesefehler mit Ansage.** §1.1 heißt „Ausgangslage" und beschreibt den
Zustand, den ADR-236 *ändern wollte*; §2.1 entscheidet dann ausdrücklich, „die Org
`iilgmbh` in die Enterprise `iilgmbh` aufzunehmen", und der Statusblock desselben ADR
vermerkt die Ausführung: „S1 ausgeführt 2026-06-03 … 4 Member-Orgs, Seats 2/2, live
verifiziert". Wer §1.1 als geltenden Stand liest, zitiert das Problem als Ergebnis.

Damit fällt der Widerspruch weg, und mit ihm die Abschwächung: der Gewinn eines Transfers
ist **nicht** auf „was jede Organisation bietet" beschränkt.

Die Namensgleichheit von Enterprise-Slug und Org-Login `iilgmbh` hat an beiden
Fehlschlüssen mitgewirkt. **Konvention ab hier:** „Enterprise `iilgmbh`" und „Org
`iilgmbh`" werden nie zu `iilgmbh` allein verkürzt; in Skripten und Datenfeldern trennen
`enterprise_slug` und `org_login`.

**Die eigentliche Lehre aus beiden Fehlschlüssen ist dieselbe wie die des ganzen ADR:**
ein Fakt, der in einem ADR steht, wirkt nicht von selbst. Er wurde hier dreimal falsch
verwendet — einmal ungeprüft übernommen, einmal mit einer Kontrolle widerlegt, die keine
war, und einmal als Ausgangslage zitiert, die längst überholt war.

Es gibt damit keine Regel, gegen die man verstoßen könnte — nur eine gewachsene
Verteilung und einen Fakt, aus dem nie eine Regel wurde.

## Annahme

**Angenommen am 2026-08-24** durch den Owner (Kapitäns-Kanal: *„adr 297 reviewed und
merged -> go"*, dann *„4 5 6 go"*). Wirksam ist damit **Ebene 1** — der Leitsatz für
Neuzugänge. **Ebene 2** (Bestandstransfers) bleibt unverändert hinter V1–V3 gegated;
die Annahme entscheidet sie ausdrücklich nicht vor.

**Zu Offenem Punkt 5 (Gegenzeichnung) — was belegt ist und was nicht.** Der Punkt
verlangte eine menschliche Gegenzeichnung aus der operativen Org-Administration.
Faktenlage: PR [#2265](https://github.com/achimdehnert/platform/pull/2265) wurde am
2026-08-24 um 11:11:51Z vom Konto `wirdigital` gemergt — dem zweiten Org-Owner, also
genau der Rolle, die der Punkt meint. **Das ist ein Handlungs-, kein Inhaltsbeleg:**
ein Merge zeigt Handlungsfähigkeit und Zustimmung zum Veröffentlichen, nicht eine
inhaltliche Prüfung der Kontinuitätsannahme. Der Punkt gilt deshalb als vom Owner
**entschieden**, nicht als sachlich erledigt — und die Substanz dahinter wandert
dorthin, wo sie messbar statt attestiert ist: nach **V1** (getesteter Vertretungsweg,
[#2263](https://github.com/achimdehnert/platform/issues/2263)).

## Entscheidung

Die Entscheidung hat **zwei Ebenen mit getrennten Kosten und getrennten Gates**. Der
Erstentwurf koppelte beide, und damit hing eine praktisch kostenlose Regel für
Neuzugänge an zwei Transfers mit gemessenen Kosten. Diese Kopplung ist hiermit gelöst:

> **Ebene 1 ist Gegenstand der Annahme. Ebene 2 wird durch die Annahme nicht
> vorentschieden.**

### Ebene 1 — Leitsatz für Neuzugänge (Gegenstand der Annahme)

**Die Organisation ist der Standard, das persönliche Konto die begründete Ausnahme.**

Wirksam **ab Annahme dieses ADR**, für jedes ab dann neu angelegte Repo. Ebene 1 hängt an
keiner Voraussetzung: sie kostet keinen Transfer, keinen GHCR-Neuaufbau und keine
Fundstellen-Pflege, und sie wirkt auch dann, wenn Teams und 2FA noch fehlen — ein neues
Repo in einer Org, die später Teams bekommt, erbt sie automatisch; ein neues Repo unter
einem persönlichen Konto nie.

#### Das Kriterium hinter den Klassen: Custody

Die Klassen unten sind der schnelle Weg. Der eigentliche Maßstab ist die
**Custody-Frage**, und sie entscheidet jeden Grenzfall:

> **Darf der Betrieb, die Wiederherstellung oder die Rechtevergabe dieses Repos von genau
> einer natürlichen Person abhängen?** Nein → Organisation. Ja → persönliches Konto.

Damit ist auch gesagt, warum die Klassen so geschnitten sind: jede von ihnen ist ein
Proxy für „mehr als eine Person muss handlungsfähig sein".

#### Klassen, in dieser Prioritätsreihenfolge

Die Klassen überlappen bewusst; die **erste zutreffende** gewinnt.

| # | Klasse | Ziel | Definition (Auslöser) |
|---|---|---|---|
| 1 | Souveränes Mandat | `ttz-lif` / `meiki-lra` | Verarbeitung im Auftrag einer Behörde bzw. eines souveränen Trägers (ADR-268 Q3/Q4). Schlägt **alles** andere. |
| 2 | Vertraglich vorgegebenes Ziel | wie im Vertrag | Der Kunde oder Auftraggeber schreibt die Zielorganisation vor. |
| 3 | Produktiver oder geteilter Betrieb | Org `iilgmbh` | Mindestens eines: Auto-Deploy auf Prod, öffentlich erreichbarer Endpunkt, oder ≥2 andere Repos hängen als Paket/CI/API daran. |
| 4 | Kunden-/Auftragsbezug ohne Betrieb | Org `iilgmbh` | Enthält Kundendaten, Angebots-/Auftragsunterlagen oder wird einem Kunden gegenüber als Artefakt geschuldet. |
| 5 | Experiment, Sandbox, Privates | `achimdehnert` | Keine Betriebsverantwortung, kein Kundenbezug, Verlust wäre folgenlos. |

**Grenzfälle, ausgeschrieben** (weil „geschäftlicher Kontext" sonst alles einfängt):

- *Ein Prototyp für einen Kundentermin, der nie deployt wird* → Klasse 5. Der Bezug
  allein reicht nicht; es zählt, ob jemand außer dem Autor handlungsfähig sein muss.
- *Ein privates Tool, das inzwischen ein Prod-Deploy hat* → Klasse 3. Der erste
  Prod-Deploy ist die Promotion, nicht die Absicht dahinter.
- *Eine Bibliothek, die nur ein einziges eigenes Repo importiert* → Klasse 5, bis das
  zweite dazukommt. Erst dann trägt sie fremde Last.
- *Ein Repo mit Kundendaten, aber ohne Betrieb* → Klasse 4, nicht 5 — Custody folgt hier
  der Vertraulichkeit, nicht dem Betrieb.

### Ebene 2 — Bestandsrepos: Migrations-Gate je Repo

Bestehende Repos wandern **nicht** pauschal und **nicht** durch die Annahme dieses ADR.
Für jedes Bestandsrepo gilt ein eigener Gate mit drei Bedingungen, **alle drei**
erforderlich:

1. **Anlass eingetreten** (Liste unten), und
2. **Voraussetzungen V1–V3 erfüllt** (siehe Migration) — solange sie fehlen, ist der
   Org-Vorteil eine Behauptung und der Ist-Zustand rational, und
3. **repo-spezifische Nutzenrechnung positiv**: die gemessenen Kosten dieses Repos (GHCR,
   Fundstellen, Deploy-Secrets, Rulesets) gegen den Gewinn. Auf der Habenseite steht seit
   der Enterprise-Messung mehr als Custody: das Ziel liegt **innerhalb** der Enterprise,
   deren Security-Konfiguration ein Repo sofort erbt — ohne dass dafür erst etwas
   eingerichtet werden muss. Für Repos, die heute unter `achimdehnert` nur den
   CI-gitleaks-Fallback aus ADR-235 haben, ist das der handfesteste Einzelposten.

#### Was ein „Anlass" ist — abschließende Liste

Ohne diese Definition bliebe der wichtigste Auslöser des ADR regellos, also genau das,
wogegen er geschrieben ist:

- **erster Prod-Deploy** eines bisher nicht produktiven Repos,
- **erster externer Mitwirkender** (Outside Collaborator oder neues Teammitglied),
- **Kundenbezug entsteht** (Klasse 2 oder 4 wird erstmals wahr),
- **GHCR-Package wird ohnehin neu angelegt** (der teuerste Posten fällt dann sowieso an),
- **Deploy wird neu aufgesetzt** (Secrets und Remotes werden ohnehin angefasst),
- **wesentliche Security-Änderung** (Rulesets, Branch Protection, Secret-Rotation über
  mehrere Repos),
- **Owner-Wechsel oder Vertretungsfall**.

Kein Anlass: eine Umbenennung, ein Refactor, ein Release, ein neuer ADR.

#### Statusvokabular je Bestandsrepo

Damit nicht auf Dauer ein Mischzustand entsteht, den niemand lesen kann, trägt jedes
Bestandsrepo genau einen Status in `registry/canonical.yaml`:

`kein-anlass` · `kandidat` (Anlass eingetreten, Gate noch nicht bewertet) · `geplant`
(Gate positiv, Termin steht) · `bewusst-ausgenommen` (mit Grund).

Ein Repo ohne Status ist `kein-anlass`. `platform` trägt `geplant (KONZ-012)` —
der Fall gehört dort hin, nicht hierher. Der Zielendzustand ist **nicht** „alles in der
Org", sondern „für jedes Repo ist die Zuordnung begründet und maschinell prüfbar".

### Die drei konkret genannten Repos

| Repo | Heute | Vorschlag | Anmerkung |
|---|---|---|---|
| `risk-hub` | Org `iilgmbh` | bleibt | **liegt bereits dort** — kein Transfer nötig |
| `writing-hub` | `achimdehnert` | `kandidat` | Klasse 3 (Auto-Deploy), Gate offen bis V1–V3 |
| `weltenhub` | `achimdehnert` | `kandidat` | Klasse 3; Cutover an `writing-hub` gekoppelt |

Beide sind damit **nicht** durch diesen ADR zum Transfer entschieden — sie sind
Kandidaten, deren Gate offen ist.

**Die Kopplung präzise statt pauschal:** Der Erstentwurf schrieb „zusammen verschoben
oder gar nicht". Belegt ist damit nur ein gemeinsamer **Cutover**, nicht dieselbe
Zielorganisation auf Dauer. Die überprüfbare Bedingung lautet:

> Solange `writing-hub` das Paket `iil-weltenfw` beziehungsweise ein GHCR-Image aus dem
> Namensraum von `weltenhub` zieht **oder** eine der beiden Seiten die laufende API der
> anderen über eine org-gebundene URL anspricht, müssen beide Transfers in **einem**
> Wartungsfenster liegen. Fällt eine dieser Kopplungen weg (Paket aus neutralem
> Namensraum, API über eigene Domain), ist ein Einzeltransfer zulässig.

## Durchsetzung

`members_can_create_repositories: true` heißt: nichts hindert das nächste produktive Repo
daran, wieder unter `achimdehnert` zu entstehen — und genau das ist der Mechanismus, der
diesen ADR nötig gemacht hat (*„ein Fakt wirkt nicht, solange keine Regel ihn anwendet"*).
Eine Regel ohne Melder ist derselbe Fehler eine Ebene höher.

**Deshalb bekommt Ebene 1 einen Melder statt einer Ermahnung**, und zwar unabhängig davon,
wie über Ebene 2 entschieden wird:

**1. Der Melder — gebaut, verdrahtet, kalibriert** (`tools/org_zuordnung_melder.py`,
Workflow `org-zuordnung-melder.yml`, täglich 05:23 UTC, `ROT-IST-BEFUND`). Drei Checks:
registry-intern (`rich.github` gegen `repo_owner`), Deklaration gegen GitHub, und der
Leitsatz selbst — Letzterer **nur für Repos, die nach dem Annahmedatum angelegt wurden**.
Ohne diesen Stichtag meldete er die gewachsenen 56 als Verstoß und wäre nach einem Lauf
abgeschaltet; er ist die Grenze zwischen Ebene 1 und Ebene 2, kein Bequemlichkeitsfilter.

Damit ist der Melder zugleich das **Messinstrument des Kill-Gates Ebene 1**.

*Erster Lauf am 2026-08-24 — die Kalibrierung, nicht nur der Bau:* elf Funde, davon acht
Repos, deren Registry-Owner GitHub widersprach (`risk-hub`, `tax-hub`,
`ausschreibungs-hub`, `nl2iot-hub`, `django-lms-lite`, `gpufw`, `iil-doc-templates`,
`bahn-hub`). Alle acht sind in `registry/canonical.yaml` korrigiert; danach lief er grün.
Ein Melder, der nie rot war, ist ungeprüft — und einer, der nie grün wird, wird
abgeschaltet.

*Was der erste Lauf über den Melder selbst lehrte:* `bahn-hub` erschien zunächst als
„nicht prüfbar", weil die Präfixregel `bahn-` jede Anfrage nach `bahn-sqf/bahn-hub`
schickte (404) — **die falsche Deklaration versteckte sich hinter ihrem eigenen 404.**
Der Melder probiert seither die übrigen bekannten Konten durch, bevor er ein Repo als
ungeprüft ablegt; beide vermeintlichen Lücken waren in Wahrheit Drift.

**2. Die `CLAUDE.md`-Org-Tabelle wird generiert, nicht gepflegt.** Sie ist der zweite
Wahrheitsstand, an dem der Auslöser dieses ADR entstanden ist; solange sie von Hand
geführt wird, ist die nächste Abweichung eine Frage der Zeit. *Noch offen.*

**3. `/onboard-repo` fragt vor dem Onboarding nach der Zielorganisation** (Step 0.05).
Das ist der billigste Zeitpunkt: noch kein GHCR-Package, keine Deploy-Secrets, keine
Fundstellen. Ein Onboarding **ist** ein Anlass im Sinne von Ebene 2 — wer hier nicht
fragt, verschiebt dieselbe Frage in den teuersten Moment.

Tracking: [#2264](https://github.com/achimdehnert/platform/issues/2264).

## Alternativen

**A · Alles bleibt, wie es ist.** Kostet nichts, löst nichts. Der Anlass — eine falsche
Org-Angabe, die niemandem auffiel — tritt wieder auf. *Verworfen für Ebene 1.* Für den
**Bestand** ist A dagegen so lange die rationale Wahl, wie V1–V3 offen sind; das ist keine
Schwäche des ADR, sondern der Inhalt von Ebene 2.

**B · Alles nach Org `iilgmbh`, auch Experimente.** Maximal einheitlich, aber jeder
Wegwerf-Prototyp belastet dann die Org-Rechteverwaltung. *Verworfen* — die Ausnahme für
Privates ist billiger als ihre Abschaffung.

**C · `achimdehnert` in eine Organisation umwandeln.** GitHub kann das, es würde alle 56
Repos auf einmal lösen. Aber: das persönliche Konto ist zugleich die Identität, mit der
committet, authentifiziert und in fremden Orgs mitgearbeitet wird — die Umwandlung ist
nicht rückgängig zu machen und trifft weit mehr als die Repo-Zuordnung. *Verworfen als
Nebenschritt*; wäre ein eigenes ADR mit eigener Risikobetrachtung.

> **Was in jenem ADR gerechnet werden muss und hier bewusst nicht gerechnet ist:** die
> **kumulierten** Kosten vieler Einzeltransfers (GHCR-Neuaufbau × n, Fundstellen × n)
> gegen die Einmal-Operation. Bei genügend vielen Transfers kann C billiger sein als der
> hier gewählte Weg — dieser ADR entscheidet das nicht, er verschiebt es. Solange Ebene 2
> aber ohnehin nur bei Anlass greift, bleibt n klein, und die Verschiebung ist tragbar.

**D · Neue, eindeutig benannte Betriebs-Organisation** (aus der Zweitmeinung). Würde die
Namenskollision Enterprise/Org und die fehlende Governance in einem Zug lösen. *Verworfen*
— eine dritte Org erhöht die Fragmentierung, erspart keine Transferkosten und ist erst
dann wieder zu bewerten, wenn Org `iilgmbh` V1–V3 nachweislich nicht erfüllen kann.

**E · Mirror statt Transfer.** *Verworfen* — erzeugt zwei Wahrheitsstände und verletzt
SSoT frontal; schlechter als A und B.

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

**Positiv, aber nach Reifegrad getrennt** — der Erstentwurf zählte alles in einem Atemzug
auf und ließ dabei offen, was heute wirkt und was erst noch gebaut werden muss:

| Vorteil | Heute |
|---|---|
| Enterprise-Security-Posture (Secret Scanning, Push Protection; Config 17 als Default-for-new) | **wirkt sofort** — die Org ist Enterprise-Mitglied, es ist nichts einzurichten |
| Eigentümer-Kontinuität | **belegt seit 2026-08-24** — `wirdigital` hat mit eigener Anmeldung Team und Repo-Recht angelegt (Audit-Log: `team.create`/`add_member`/`add_repository`, `actor: wirdigital`). Recovery-Weg owner-attestiert, nicht messbar (V1) |
| Rechtevergabe über Teams | **wirkt seit 2026-08-24** — Team `maintainers`, besetzt, trägt `maintain` auf `risk-hub` (V2) |
| 2FA-Pflicht | **wirkt seit 2026-08-24** in `iilgmbh` und `bahn-sqf` (V3); `ttz-lif`/`meiki-lra` offen |
| **Org-Secrets** einmal statt je Repo | **wirkt sofort** — neun sind angelegt und in Benutzung, darunter `DEPLOY_*`, `STAGING_*`, `PYPI_API_TOKEN` |
| Org-Rulesets einmal statt je Repo | **unrealisiert** — `gh api orgs/iilgmbh/rulesets` → `[]` |

**Stand am Abend des 2026-08-24: fünf von sechs Zeilen wirken.** Als der Entwurf
geschrieben wurde, war es eine. Offen ist allein die Ruleset-Zeile.

Der ursprüngliche Satz dieses Abschnitts lautete: die übrigen Zeilen seien der Grund für
Ebene 2. Das galt einen halben Tag. Zwei Zeilen sind Beleg, nicht Absicht: die Enterprise-Posture **und** die neun
Org-Secrets. Gerade die zweite war im Entwurf als „unrealisiert" geführt — falsch, und
zwar zuungunsten der eigenen Entscheidung: ein Repo, das in die Org wandert, erbt die
kompletten Deploy- und Staging-Zugänge, statt sie je Repo zu pflegen. Die übrigen Zeilen
bleiben der Grund für Ebene 2.

**Bedingung B1 — der erste Nicht-Owner-Zugang:** Sobald ein drittes Mitglied ohne
Owner-Rolle in die Org kommt, wirkt `default_repository_permission: read` auf **alle**
Org-Repos, auch die kunden- und auftragsbezogenen. Vorher ist zu entscheiden, ob der
Default auf `none` gesetzt und Zugriff über Teams vergeben wird. Das ist keine Bedingung
für die Annahme, aber eine harte Bedingung für den ersten solchen Zugang — und sie wird
mit jedem nach `iilgmbh` transferierten Kunden-Repo teurer.

## Migration (Vorschlag, nicht Teil der Annahme)

### Voraussetzungen — vor jedem Bestandstransfer

| # | Voraussetzung | Messpunkt | Stand 2026-08-24 |
|---|---|---|---|
| V1 | **Getestete, unabhängige Vertretung.** Nicht der Owner-Zähler, sondern ein durchgeführter Test: der zweite Owner kann ohne Zutun des ersten ein Repo-Recht setzen und sich mit eigenem 2FA-Faktor anmelden. | Audit-Log nennt den zweiten Owner als `actor` | **erfüllt** |
| V2 | **Mindestens ein Team mit realer Besetzung**, das ein Repo-Recht tatsächlich trägt — ein leeres Team ist kein erfüllter Punkt. | `gh api orgs/iilgmbh/teams --jq length` > 0 **und** `.../teams/<slug>/members` nicht leer **und** `.../teams/<slug>/repos` nicht leer | **erfüllt** |
| V3 | **2FA-Pflicht aktiv.** | `gh api orgs/iilgmbh --jq .two_factor_requirement_enabled` -> `true` | **erfüllt** |

**Alle drei erfüllt am 2026-08-24, drei Monate vor der Frist** ([#2263](https://github.com/achimdehnert/platform/issues/2263)):

- **V2 und V1 in einem Zug.** `wirdigital` hat Team, Mitgliedschaft und Repo-Recht mit
  **seiner eigenen** Anmeldung angelegt — nicht mit einem Token des ersten Owners. Der
  Beleg kommt deshalb nicht aus seinem Vollzugsbericht, sondern aus dem Enterprise-Audit-Log:
  `team.create`, `team.add_member`, `team.add_repository`, alle mit `actor: wirdigital`.
  Positivkontrolle: derselbe Filter findet 22 `pull_request`-Aktionen, er kann also finden.
- **V3** steht in `iilgmbh` und `bahn-sqf` auf `true`; niemand wurde beim Einschalten
  entfernt (Mitgliederzahl vorher und nachher 2, null Outside Collaborators).

**Was an V1 nicht gemessen ist:** die *Handlung* ist belegt, der *Recovery-Weg* nicht. Dass
der zweite Faktor auf eigenem Gerät liegt und eigene Recovery-Codes existieren, beruht auf
der Owner-Bestätigung vom 2026-08-24. Keine API kann das sehen — die Lücke gehört benannt,
nicht weggerundet.

**Was am ersten Anlauf schiefging, weil es sich wiederholen wird:** Der Versuch, V3 über
`gh api -X PATCH orgs/iilgmbh -F two_factor_requirement_enabled=true` zu setzen, läuft
durch und ändert nichts — das Feld ist in der REST-API ein Antwortfeld, kein Eingabefeld.
Wer nur den Exit-Code prüft, hält V3 danach für erledigt. Der Schalter sitzt in der
Web-UI unter Organization → Settings → Authentication security.

Zusätzlich zu entscheiden, aber kein Blocker: Org-Secrets und Org-Rulesets — entweder
genutzt oder mit einem Satz begründet nicht genutzt.

### Ablauf

1. **Preflight** (je Repo, vor dem Transfer): Fundstellen-Liste erzeugen, GHCR-Packages
   auflisten, Deploy-Secrets inventarisieren, aktuellen Ruleset-/Branch-Protection-Stand
   sichern. Verantwortlich: Owner.
2. **Pilot mit einem Repo aus Klasse 5**, das **einen** GHCR-Pfad hat. Der Erstentwurf
   wollte ausdrücklich ein Repo *ohne* GHCR — damit hätte der Pilot genau das teuerste
   benannte Risiko **nicht** validiert. Der Pilot muss den GHCR-Neuaufbau einmal echt
   durchlaufen, sonst ist er kein Beleg.
3. **Abnahme des Piloten** — alle vier müssen zutreffen, sonst gilt er als
   fehlgeschlagen: (a) Deploy läuft nach dem Transfer einmal grün **und** die Änderung ist
   am Zielsystem sichtbar; (b) `docker pull` des neuen GHCR-Pfads gelingt vom Prod-Host;
   (c) keine Fundstelle zeigt mehr auf den alten Owner (`grep` über Registry und Tools ist
   leer); (d) Branch-Protection/Ruleset am Ziel entspricht dem Preflight-Stand.
4. **Rückfallpfad:** Der Transfer ist über den umgekehrten Weg reversibel (Repo zurück auf
   das persönliche Konto), der GHCR-Namensraum jedoch **nicht** — ein zurückgeholtes Repo
   braucht erneut ein neu angelegtes Package. Abbruchkriterium: schlägt (b) fehl und ist
   binnen einer Arbeitssitzung nicht behoben, wird zurückgerollt und der Rest der Welle
   ausgesetzt.
5. `writing-hub` + `weltenhub` erst nach bestandenem Piloten, in **einem** Wartungsfenster
   (siehe Cutover-Bedingung), mit geplantem GHCR-Neuaufbau.
6. `CLAUDE.md`-Org-Tabelle korrigieren — sie ist nachweislich falsch (`risk-hub` steht
   dort unter `achimdehnert`, real Org `iilgmbh`). **Dieser Schritt hängt an nichts:** er
   ist der auslösende Defekt, braucht weder Annahme noch Voraussetzung und ist sofort
   auszuführen — idealerweise gleich als generierte Tabelle (siehe Durchsetzung).

## Offene Punkte

Jeder Punkt trägt ein eigenes Tracking-Artefakt; keiner blockiert die Annahme von Ebene 1.

| # | Punkt | Blockiert | Tracking |
|---|---|---|---|
| 1 | ~~Enterprise-Zugehörigkeit bestätigen~~ — **erledigt 2026-08-24** am Goldstandard (GraphQL, 4 Member-Orgs). | — | [#2262](https://github.com/achimdehnert/platform/issues/2262) |
| 1a | ~~Sitz-Anomalie klären~~ — **erledigt**: 3 verbraucht / 2 gekauft, dritte Person ist `wirdigital`. Offen ist die **Konsequenz**: Amendment an ADR-236. | nichts hier | [#2262](https://github.com/achimdehnert/platform/issues/2262) |
| 2 | ~~Org-Rulesets prüfen~~ — **erledigt**: keine vorhanden. Org-Secrets dagegen neun, in Benutzung. | — | [#2262](https://github.com/achimdehnert/platform/issues/2262) |
| 3 | V1–V3 herstellen und Pilot fahren. | jeder Bestandstransfer | [#2263](https://github.com/achimdehnert/platform/issues/2263) |
| 4 | Melder **gebaut und verdrahtet** (`tools/org_zuordnung_melder.py`, täglicher Workflow). Offen bleibt die generierte `CLAUDE.md`-Tabelle. | nichts | [#2264](https://github.com/achimdehnert/platform/issues/2264) |
| 5 | ~~Gegenzeichnung vor der Annahme~~ — vom Owner am 2026-08-24 entschieden, Substanz nach V1 verschoben (siehe Annahme). | erledigt | [#2263](https://github.com/achimdehnert/platform/issues/2263) |

**Haltbarkeit der Messungen:** Die entscheidungstragenden Fakten (Teams, 2FA, Owner,
Mitglieder, Enterprise-Zugehörigkeit) sind Momentaufnahmen vom 2026-08-24 mit belegter
Verfallsgeschichte — ADR-236 wurde nach zweieinhalb Monaten wiederentdeckt, statt zu
wirken. Sie sind deshalb **erneut zu messen, bevor ein Bestandstransfer beginnt**, nicht
nur einmal vor der Annahme; der Melder aus OP-4 ist der Ort, an dem das automatisch
passiert.

## Kill-Gate

Getrennt nach Ebenen, weil die Ebenen getrennt begründet sind. Der Erstentwurf hätte bei
fehlendem Team **den ganzen ADR** verworfen, obwohl der Leitsatz für Neuzugänge von Team
und 2FA gar nicht abhängt — und hätte damit fehlende *Umsetzung* als widerlegte
*Entscheidung* verbucht.

**Ebene 1 (Leitsatz).** Verworfen wird er, wenn seine Begründung widerlegt ist, nicht wenn
etwas nicht umgesetzt wurde. Messpunkt zum **2026-11-24**: Sind seit Annahme neue Repos
der Klassen 1–4 entstanden, die **nicht** in einer Organisation liegen, und lässt sich
für keines davon ein Ausnahmegrund benennen? Dann wirkt der Leitsatz nicht und ist
entweder falsch geschnitten oder braucht den Melder aus OP-4 — in beiden Fällen wird er
überarbeitet, nicht stillschweigend weitergeführt.

**Ebene 2 (Bestandsmigration).** Sind V1–V3 bis zum **2026-11-24** nicht erfüllt, wird
**keine** Bestandsmigration begonnen und Ebene 2 auf `deferred` gesetzt — mit erneuter
Bewertung. Ebene 1 bleibt davon unberührt und in Kraft.

> **Nicht ausgelöst: V1–V3 sind am 2026-08-24 erfüllt worden, drei Monate vor der Frist.**
> Damit sperrt die Readiness keinen Bestandstransfer mehr. Was bleibt, sind die beiden
> anderen Gate-Bedingungen aus Ebene 2 — **Anlass eingetreten** und **repo-spezifische
> Nutzenrechnung positiv** —, und die gelten je Repo, nicht pauschal. Der Wegfall der
> Readiness-Sperre ist ausdrücklich **keine** Freigabe für `writing-hub` und `weltenhub`:
> beide bleiben `kandidat`, bis ihr Anlass eintritt und der Pilot mit GHCR-Probe
> bestanden ist ([#2263](https://github.com/achimdehnert/platform/issues/2263)).

## Zweitmeinungen (2026-08-24)

Zwei unabhängige externe Reviews (Steelman / Advocatus Diabolus / Maintainer 2028) haben
den Entwurf geprüft; beide empfahlen **Überarbeiten**. Was daraus folgte, vollständig:

| Befund der Zweitmeinung | Antwort in dieser Fassung |
|---|---|
| Kopplung: kostenlose Neuzugangs-Regel hängt an teuren Transfers | **übernommen** — Entscheidung in Ebene 1 / Ebene 2 getrennt |
| Kill-Gate testet ein Motiv, nicht die Gültigkeit; verwirft zu viel | **übernommen** — outcome-basiert und je Ebene getrennt |
| „Anlass" undefiniert; Grenze Experiment→produktiv fehlt | **übernommen** — abschließende Anlass-Liste, Promotionskriterium, Statusvokabular |
| Klassen überlappen ohne Priorität und Definition | **übernommen** — Prioritätsreihenfolge, Auslöser je Klasse, vier Grenzfälle |
| Custody statt Klassen als eigentlicher Maßstab | **übernommen** — als Kriterium hinter den Klassen und Tiebreaker |
| Kein zweiter Org-Owner ⇒ keine Eigentümer-Kontinuität | **teilweise widerlegt** — es gibt zwei Owner (gemessen). Der berechtigte Kern (Unabhängigkeit ungeprüft) wurde zu V1 verschärft: getesteter Vertretungsweg statt Owner-Zähler |
| `default_repository_permission: read` als Vertraulichkeitsrisiko | **für heute widerlegt** — 2 Mitglieder, beide Owner, 0 Outside Collaborators. Als Bedingung B1 für den ersten Nicht-Owner-Zugang aufgenommen |
| Enterprise zugleich „nicht tragend" und „entscheidungstragend" | **überholt** — die Frage ist inzwischen beantwortet (Negativkontrolle `pactive-de`). Beide Reviews argumentierten korrekt gegen die Widersprüchlichkeit des Entwurfs, übernahmen dabei aber dessen falsche Prämisse; kein Vorwurf, sondern der Preis dafür, dass der Entwurf sie so vorgelegt hat |
| Sitzfrage doppelt geführt (OP 2 und 4) | **übernommen** — zusammengezogen; ADR-236 beantwortet die Transferkosten. Der überzählige Sitz ist als eigener Punkt an ADR-236 weitergereicht |
| Pilot ohne GHCR validiert das teuerste Risiko nicht | **übernommen** — Pilot **mit** GHCR, vier Abnahmekriterien, Rückfallpfad, Abbruchkriterium |
| „zusammen oder gar nicht" ist nicht belegt | **übernommen** — überprüfbare Cutover-Bedingung statt Dauerkopplung |
| Kein Durchsetzungsmechanismus ⇒ der Fehler wiederholt sich | **übernommen** — Abschnitt „Durchsetzung", Melder als OP-4 verankert |
| `CLAUDE.md`-Korrektur hängt grundlos an der Annahme | **übernommen** — herausgelöst, sofort auszuführen, künftig generiert |
| Offene Punkte ohne Tracking-Artefakt | **übernommen** — Tabelle mit Issue je Punkt |
| Messungen sind Momentaufnahmen mit Verfallsgeschichte | **übernommen** — Neumessung vor jedem Transfer, Melder als Dauerform |
| Alternative C nicht gegen kumulierte Einzeltransfers gerechnet | **übernommen als Auflage** an das C-ADR; hier ausdrücklich nicht gerechnet |
| Namenskollision Enterprise-Slug ↔ Org-Login | **übernommen** — Trennkonvention, `enterprise_slug` / `org_login` |
| Metadaten ohne konsultierte menschliche Rolle | **übernommen** — Gegenzeichnung des zweiten Owners als OP-5 vor der Annahme |
| Neue, eindeutig benannte Betriebs-Organisation | **abgelehnt** — als Alternative D aufgenommen und begründet verworfen |
| Mirror statt Transfer | **abgelehnt** — als Alternative E aufgenommen; zwei Wahrheitsstände |

**Was keine der beiden Zweitmeinungen finden konnte**, weil beide nur den Entwurf und
nicht die Quelle vor sich hatten: die „Korrektur" des Entwurfs war selbst falsch. Ihre
Gegenprobe bestand aus drei Enterprise-**Mitgliedern**, weil sie ADR-236 §1.1
(Ausgangslage) für den geltenden Stand hielt. Erst die Negativkontrolle `pactive-de`
trennt. Beide Reviews haben die Stelle als widersprüchlich markiert (AD-7, AD-9, M28-3)
— sie haben also richtig auf sie gezeigt, nur die Richtung des Fehlers war eine andere.
