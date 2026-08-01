---
concept_id: KONZ-platform-037
title: Betriebszustand als Spec — ADR-211-Muster für Dienste, mit eingebauter Schrumpfung
pipeline_status: idea
tier: T2
owner: Achim Dehnert
conforms_to: platform:ADR-211
spec_refs: [platform:ADR-211, dms-hub:KONZ-dms-hub-003, platform:ADR-275]
adr_threshold: "Kein neuer ADR. Dies ist die Anwendung eines bestehenden, akzeptierten Musters (ADR-211 I1–I4) auf eine zweite Artefaktklasse — nach adr-threshold.md eine Ergänzung nach bestehendem Muster. ADR-pflichtig würde erst, wenn die Selbsttest-Pflicht (§4) auf ADR-211 selbst zurückwirken soll; das ist hier ausdrücklich als Folgeentscheidung offen gelassen (§7 E5)."
review_by: 2026-11-01
kill_criteria: "Zwei harte Kriterien, beide bindend. (1) WIRKUNG: Steigt der Längsschnitt-Mittelwert von risiko_debt über die nächsten ~10 Retros nicht messbar über 2,55, ist der Ansatz widerlegt und wird GESTRICHEN, nicht um weitere Invarianten ergänzt. (2) SCHRUMPFUNG: Ist die Zahl der abgelösten Prosa-Regeln nach 90 Tagen nicht mindestens so groß wie die Zahl der neuen Invarianten, hat das Verfahren sein eigenes Versprechen verfehlt und wird gestrichen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-211-spec-zentrierte-klickdummies.md, commit_or_pr: origin/main, opened_in_session: true, provenance: direct}
  - {claim_id: C2, source_path: "dms-hub Makefile klickdummy-i1/i2/i3", commit_or_pr: origin/main, opened_in_session: true, provenance: direct}
  - {claim_id: C3, source_path: "tools/retro_kpis.py Lauf 2026-07-31", commit_or_pr: "61 Retros", opened_in_session: true, provenance: direct}
  - {claim_id: C4, source_path: docs/retros/session-retro-2026-07-31-dms-hub-77aad5.md, commit_or_pr: PR-1621, opened_in_session: true, provenance: direct}
---

# KONZ-platform-037 — Betriebszustand als Spec, mit eingebauter Schrumpfung

## 1 Executive Summary

Ein Regelwerk wächst, weil jeder Fehler eine Regel erzeugt und **nichts** eine Regel
entfernt. Der Längsschnitt zeigt, wohin das führt: `claim-before-cheapest-check` ist über
61 Retrospektiven **32-mal** aufgetreten, achtzehn Muster stehen auf „gate-pflichtig", und
`risiko_debt` ist mit einem Mittel von **2,55** seit Monaten die schwächste aller sechs
Bewertungsdimensionen. Eine Regel, die 32-mal verletzt wurde, ist keine Regel — sie ist ein
Wunsch.

Die Antwort existiert in dieser Organisation bereits, nur für eine andere Artefaktklasse:
**ADR-211** beschreibt Oberflächen nicht in Prosa, sondern als maschinenlesbare Spec mit
nummerierten Invarianten, Exit-Code-Prüfung in CI und Verfallsdatum. Dieses Konzept
überträgt dasselbe Muster auf den **Betriebszustand eines Dienstes**.

Der zweite, wichtigere Teil ist die Absicherung gegen das Problem, das ADR-211 selbst
vorführt: einundzwanzig Revisionen, und ein als Enforcement dokumentierter Prod-Probe
(`klickdummy_prod_guard.sh`) ist laut Rev 20 **unimplementiert**. Die Invariante I2 sieht
dadurch stärker aus, als sie ist. Genau dieser Zustand — **deklariert, aber wirkungslos** —
ist gefährlicher als eine fehlende Regel, weil er falsches Vertrauen erzeugt.

Deshalb trägt dieses Konzept drei Mechanismen, die eine Prosa-Regel nicht haben kann:
eine **Negativprobe je Invariante** (der Check muss beweisen, dass er rot werden *kann*),
ein **hartes Budget, das der Prüflauf selbst durchsetzt**, und ein **Verfallsdatum**, das
ohne aktive Verlängerung auf `dormant` schaltet.

## 2 Scope & Evidenzbasis

**Im Scope:** der beobachtbare Betriebszustand eines Dienstes — was auf dem Host, im
Container, in der API und in CI nachprüfbar wahr sein muss. Pilot ist `doc-hub`
(`docs.iil.pet`).

**Nicht im Scope:** Anwendungsverhalten (dafür Tests im Repo), Oberflächen (dafür
ADR-211), und die fünf Freigabe-Gates aus `autonomy-gates.md` — die schrumpfen nicht mit
besseren Prüfungen, weil jede Prüfung erst *nach* der Handlung läuft.

Alle Zahlen stammen aus dem Lauf von `tools/retro_kpis.py` über 61 Retrospektiven
(2026-07-31) und aus dem Session-Retro `session-retro-2026-07-31-dms-hub-77aad5.md`.

## 3 Was von ADR-211 übernommen wird

| ADR-211 (Oberfläche) | hier (Betriebszustand) |
|---|---|
| `screens-spec.yaml` + JSON-Schema | `betrieb-spec.yaml` + JSON-Schema |
| I1 Spec-first, **bidirektionale** Coverage | jede Zusicherung hat eine Prüfung **und** jede Prüfung eine Zusicherung |
| Exit-Code-Prüfung (`make klickdummy-i1`) | Exit-Code-Prüfung (`make betrieb-check`) |
| `sunset_after` / TTL, Auto-`deprecated` | `review_by` je Invariante, Auto-`dormant` |
| `KONZ-` als idea-Vorstufe, read-only ab Spec | unverändert übernommen |

Die Bidirektionalität ist der Teil, den ich zunächst unterschätzt hatte. Auf den Betrieb
übertragen heißt sie: nicht nur „jede Zusicherung wird geprüft", sondern auch **„jede
Prüfung gehört zu einer erklärten Zusicherung"**. Ein Skript, das etwas prüft, was nirgends
zugesichert ist, ist genauso ein Defekt wie eine Zusicherung ohne Prüfung.

## 4 Die drei Mechanismen gegen Wachstum

Das ist der Kern dieses Konzepts. Ohne sie wäre es nur eine weitere Schicht.

### 4.1 Negativprobe — jede Invariante beweist, dass sie rot werden kann

Jede Invariante trägt neben ihrer Prüfung eine **Negativprobe**: eine ausführbare
Beschreibung, wie man den Zustand absichtlich verletzt. Der Prüflauf führt beide aus. Wird
die Negativprobe **nicht** rot, ist die Invariante `dormant` — sie prüft nichts.

Der Grund steht wörtlich in `evidence-discipline.md`: *„ein Check, der NICHTS findet, belegt
erst dann eine Abwesenheit, wenn derselbe Check nachweislich auch etwas finden KANN — sonst
ist die Null womöglich dein Filter, nicht die Welt."* Bislang gilt dieser Satz für einzelne
Behauptungen. Hier wird er zur Eigenschaft des Prüfwerkzeugs.

**Was das an ADR-211 gefangen hätte:** I2 dokumentiert einen externen Prod-Probe, der nicht
existiert. Eine Negativprobe („Demo-Route in Prod erreichbar machen ⇒ Check muss rot werden")
wäre nie rot geworden, weil kein Prüfer läuft. I2 stünde damit seit Rev 20 automatisch als
`dormant` im Manifest, statt in der Tabelle als Enforcement geführt zu werden.

### 4.2 Budget — vom Prüflauf durchgesetzt, nicht von der Disziplin

Die Spec trägt ein Feld `budget: <n>`. Übersteigt die Zahl aktiver Invarianten das Budget,
**scheitert der Prüflauf** — mit derselben Härte wie eine verletzte Zusicherung.

Das ist der Unterschied zwischen einem Vorsatz und einem Mechanismus. Eine elfte Invariante
lässt sich nicht hinzufügen, ohne dass CI rot wird; wer sie will, muss eine bestehende
zurückziehen oder zusammenfassen. Das Budget verteidigt sich selbst.

Für `doc-hub` schlage ich **10** vor. Die Zahl ist gesetzt, nicht hergeleitet — sie ist so
gewählt, dass sie die heute belegten Ausfälle abdeckt und keinen Platz für Bequemlichkeit
lässt. Sie zu ändern ist erlaubt, aber nur als bewusster Beschluss im Konzept, nicht
nebenbei im Prüflauf.

### 4.3 Ablöse-Nachweis — jede Invariante nennt, was sie ersetzt

Jede Invariante trägt ein Feld `ersetzt: []` mit Verweisen auf die Prosa-Regeln, Memories
oder Merksätze, die sie überflüssig macht. Leeres Feld ist erlaubt, aber es ist ein Signal:
eine Invariante, die nichts ablöst, ist reines Wachstum.

Der Zusammenhang wird gemessen, nicht behauptet: das zweite Kill-Kriterium im Frontmatter
verlangt, dass nach 90 Tagen **mindestens so viele Prosa-Regeln abgelöst wie Invarianten
hinzugefügt** wurden. Ist das nicht der Fall, wird dieses Konzept gestrichen — nicht
verlängert.

### 4.4 Warum nicht Auto-Löschung

Eine abgelaufene Invariante wird `dormant`, nicht gelöscht. Stilles Löschen wäre derselbe
Fehler wie stilles Wachsen, nur in die andere Richtung: niemand bemerkt, dass eine
Zusicherung weg ist. `dormant` ist sichtbar, zählt nicht gegen das Budget und blockiert den
Lauf nicht — aber es steht im Manifest und im Bericht.

## 5 Die Invarianten für doc-hub (Pilot, Budget 10)

Alle zehn sind aus **belegten Ausfällen** dieser und der letzten Sessions abgeleitet, keiner
ist erfunden. Die Spalte „ersetzt" nennt, was dadurch aus der Prosa verschwinden kann.

| # | Zusicherung (Zustand, nicht Handlung) | Prüfung | Negativprobe | ersetzt |
|---|---|---|---|---|
| **B1** | Es existieren ≥ 30 Backup-Stände, der jüngste ist < 26 h alt | `ls /opt/backups/doc-hub \| wc -l`; mtime | einen Stand löschen ⇒ rot | „Backups prüfen"-Merksatz |
| **B2** | Die letzte Rückspielprobe ist < 30 Tage her | Marker-Datei aus `restore-test.sh` | Marker altern lassen ⇒ rot | — |
| **B3** | Kein Objekt in der Einlese-Warteschlange ist älter als 30 min | `find /opt/paperless-consume -mmin +30` | Datei ablegen, warten ⇒ rot | dms-hub#47 Punkt 3 |
| **B4** | Jede Datei in `/opt/doc-hub/scripts/` hat ein byte-identisches Pendant in `deployment/stacks/doc-hub/` — **und umgekehrt** | `diff` beidseitig | Host-Datei ändern ⇒ rot | `feedback_host_fix_must_mirror_to_iac` |
| **B5** | Der laufende `wg0`-Zustand entspricht `wg0.conf` | `wg-quick strip` vs. `wg show` | Adresse live hinzufügen ⇒ rot | platform#1620 |
| **B6** | Kein Workflow des Repos steht auf `failure` | `gh run list --limit 20` | — (Negativprobe: Testlauf provozieren) | „CI-Farbe prüfen"-Merksatz |
| **B7** | Der Anteil Dokumente ohne Dokumenttyp liegt unter 40 % | Paperless-API-Zählung | Typen leeren ⇒ rot | KONZ-dms-hub-003 Kill-Gate |
| **B8** | Kein Dokument hat ein Titel-Datum, das von `created` um > 90 Tage abweicht | API-Vergleich | Titel manipulieren ⇒ rot | Retro-Befund B3 |
| **B9** | Jedes Dokument hat eine Archivfassung | Zählung Original vs. Archiv | — | Retro §8 |
| **B10** | Die Testsuite des Repos läuft in CI | `ci.yml` enthält einen Testschritt | Schritt entfernen ⇒ rot | dms-hub#46 |

**Zehn Zusicherungen lösen sechs Prosa-Artefakte ab.** Das erfüllt das Schrumpfungs-Kriterium
noch nicht (10 neu gegen 6 abgelöst) — und genau das soll sichtbar sein, statt in einer
Erfolgsmeldung zu verschwinden. Die Bilanz wird nach 90 Tagen erneut gezogen; bleibt sie
negativ, greift das Kill-Kriterium.

## 6 Adversariale Analyse

**„Invarianten wuchern genauso wie Regeln."** Der stärkste Einwand, und er ist berechtigt —
ADR-211 belegt ihn selbst mit 21 Revisionen. Der Unterschied ist das durchgesetzte Budget
(§4.2): eine Prosa-Regel kann man hinzufügen, ohne dass irgendwo etwas rot wird. Eine elfte
Invariante nicht. Ob das reicht, entscheidet das Kill-Kriterium, nicht dieses Argument.

**„Man optimiert dann den Test statt den Zustand."** Goodhart, real. Die Absicherung liegt in
der Formulierung: jede Zusicherung beschreibt einen **Zustand**, keine Handlung. „30
Backup-Stände liegen vor" lässt sich nicht durch geschicktes Arbeiten vortäuschen, „ich habe
an das Backup gedacht" schon. Deshalb ist die Spalte in §5 mit „Zustand, nicht Handlung"
überschrieben — das ist eine Aufnahmebedingung, kein Stilhinweis.

**„Das ersetzt die Freigaben."** Nein, und diese Grenze wird ausdrücklich nicht verwischt.
Ein Prüflauf läuft **nach** der Handlung. Für alles Umkehrbare ist das richtig. Für
Irreversibles — Löschen, Secret-Rotation, Außenwirkung — bleibt die Freigabe **vorher**, weil
kein Test ein gelöschtes Dokument zurückholt. Die fünf Gates aus `autonomy-gates.md` bleiben
unberührt.

**„Die Negativprobe ist teuer."** Sie ist der teuerste Teil, ja. Aber sie ist der einzige
Mechanismus, der Dormanz **automatisch** findet, und Dormanz ist der Zustand, der ADR-211 I2
heute betrifft. Wo eine Negativprobe unverhältnismäßig wäre (B6, B9), steht das ausdrücklich
in der Tabelle — die Invariante läuft dann mit dem Vermerk `negativprobe: manuell` und zählt
im Bericht als schwächer.

## 7 Empfehlungen

| # | Schritt | Wirkung | Risiko |
|---|---|---|---|
| E1 | `betrieb-spec.yaml` + JSON-Schema für doc-hub anlegen | Zustand wird maschinenlesbar | keins, reine Deklaration |
| E2 | Prüfläufer `tools/betrieb_check.py` (stdlib-only, analog `retro_kpis.py`) | Exit-Code statt Erinnerung | keins, read-only |
| E3 | Negativproben je Invariante ergänzen | fängt Dormanz automatisch | Aufwand |
| E4 | Täglicher Lauf + Meldung bei Rot | macht den Zustand beobachtbar | **Cron auf Prod = Gate 2** |
| E5 | Nach 90 Tagen: Bilanz Invarianten vs. abgelöste Regeln; Rückwirkung auf ADR-211 entscheiden | schließt den Loop | Entscheidung, kein Risiko |

## 8 Entscheidung + Kill-Gate + 30/60/90

**Entscheidung:** Der Betriebszustand von doc-hub wird nach dem ADR-211-Muster als Spec
geführt, mit zehn Invarianten, hartem Budget, Negativprobe und Verfallsdatum je Eintrag.

**Kill-Gate (zwei bindende Kriterien, beide im Frontmatter):** Bewegt sich `risiko_debt` über
~10 Retros nicht messbar über 2,55, **oder** ist die Bilanz aus abgelösten Regeln gegen neue
Invarianten nach 90 Tagen negativ, wird dieses Konzept **gestrichen** — nicht nachgebessert.
Das ist bewusst dieselbe Härte, die `autonomy-gates.md` und `evidence-discipline.md` gegen
sich selbst richten.

**30/60/90:** 30 Tage E1–E3 (Spec, Läufer, Negativproben) · 60 Tage E4 nach Freigabe und
erste Messreihe · 90 Tage E5 — Bilanz ziehen, Kill-Gate anwenden, und erst dann entscheiden,
ob das Muster auf weitere Dienste geht.

**Was ausdrücklich nicht passiert:** keine Übertragung auf einen zweiten Dienst, bevor die
90-Tage-Bilanz vorliegt. Ein Verfahren gegen Regelwucher, das sich vor seinem eigenen
Wirksamkeitsnachweis ausbreitet, wäre die Ironie, die es zu vermeiden gilt.
