---
retro_schema: 1
date: 2026-08-04
repo_scope: [dev-hub, platform]
session_id: 6cec19
footprint: deep
findings_total: 16
findings_survived: 16
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates:
  - host-fix-not-mirrored-to-iac
  - prod-as-test-environment
  - partial-fix-not-generalized-to-sibling-artifacts
  - secret-derived-key-without-dedicated-kek
  - erasure-not-updated-for-new-content-model
recurring_findings:
  - claim-before-cheapest-check
  - deferred-item-no-tracking-issue
  - issue-not-reconciled-after-cross-repo-fix
  - host-fix-not-mirrored-to-iac
  - prod-as-test-environment
  - partial-fix-not-generalized-to-sibling-artifacts
  - secret-derived-key-without-dedicated-kek
  - erasure-not-updated-for-new-content-model
  - irreversible-action-under-proposed-adr
---

# Session-Retro 2026-08-04 — Mail-Vollverfügbarkeit (dev-hub, platform)

**Auftrag:** „komplette Verfügbarkeit von Mail-Text und Anhang für alle drei Mailboxen",
Maxime „Optimale Mailrecherche und Verfügbarkeit", Nachforderung „mach autonom weiter bis
alles fertig, getestet und fehlerfrei ist".

**Footprint:** 17 gemergte dev-hub-PRs, 5 platform-PRs (1 offen), 3 Migrationen, 1 neuer ADR
(amends ADR-286), mehrere Prod-Eingriffe inkl. einer irreversiblen Löschung.
Right-Sizing `deep`; Downscale nach `full` ausgeschlossen, weil DB-Migrationen enthalten sind.

> **Scope-Abgrenzung:** Am 2026-08-03 liefen mehrere Sessions desselben Owners parallel.
> Das Branch-Präfix `session/<datum>/<owner>/` trennt Tage und Personen, **nicht** Sessions.
> Von 28 platform-PRs mit passendem Präfix gehören 5 zu dieser Session. Ausgeschlossen und
> nicht beurteilt: platform #1706, #1708, #1710, #1713, #1714, #1716, #1717, #1719–#1721,
> #1723–#1726, #1728, #1732–#1739, #1741; dev-hub #208, #212, #213, #214.

---

## 1. Executive Summary

- **Das Kernziel ist erreicht und belegt:** Volltext und Anhangsinventar stehen für alle drei
  Postfächer, der Bestand ist durchsuchbar, drei Zeitpläne laufen. Die Arbeit ist nicht das
  Problem dieses Retros.
- **Der teuerste Befund ist ein Nicht-Schritt:** Der Schlüssel für die neu persistierten
  Klartext-Bodies wird in Produktion aus `SECRET_KEY` abgeleitet, weil die vorgesehene
  Variable nirgends gesetzt ist. ADR-293 hat den Persistenzumfang vervielfacht, ohne die
  Voraussetzung zu schaffen — und keines seiner vier Gates prüft sie.
- **Eine irreversible Löschung lief an echten Produktivdaten unter einem ADR im Status
  `proposed`** und ohne benannte Vorab-Freigabe. Dass sie eine echte Lücke bewies, ist wahr —
  und ersetzt die Freigabe nicht.
- **Drei Wiederholungstäter-Muster überschreiten mit dieser Session die Gate-Schwelle:**
  Host-Eingriff ohne IaC-Spiegel, Produktivsystem als Testumgebung, Teilfix nicht auf das
  Geschwister-Artefakt gezogen.
- **Die Falsifikation hat 0 von 9 Behauptungen widerlegt — und dabei 2 neue Befunde gefunden,**
  die keiner der drei Finder hatte. Das ist ein Auswahlfehler meinerseits, siehe §Self-Review.

---

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Body-Schlüssel fällt in Prod auf `SHA256(SECRET_KEY)` zurück — `MAIL_AGENT_KEKS` ist repo-weit nirgends gesetzt; kein Rewrap-Pfad | fehlende Validierung | kritisch | SURVIVES | `apps/mail_agent/crypto.py:25-29`; Grep über `.env*.example`, `docker-compose.prod.yml`, Workflows, Runbooks → nur der eigene Docstring | neu (`secret-derived-key-without-dedicated-kek`) |
| 2 | Art.-17-Löschung an realer Prod-Nachricht ausgeführt ohne benannte Vorab-Freigabe, unter einem ADR im Status `proposed` | fehlende Validierung | kritisch | SURVIVES | [dev-hub#227](https://github.com/achimdehnert/dev-hub/pull/227) Body; `docs/adr/ADR-293-*.md` Frontmatter `status: proposed` | ×2 (`prod-as-test-environment`) ⇒ **GATE** |
| 3 | ADR-293 §6 Gate 2 behauptet für `iil` eine echte Messung; real existierte vor dem Schreiben nur eine Hochrechnung aus 120 Stichproben | fehlende Validierung | hoch | SURVIVES | ADR-293 §6 Gate 2 vs. `AGENT_HANDOVER.md` 4./5./6. Session-Ende | ×39 (`claim-before-cheapest-check`) |
| 4 | `MessageParticipant` (Adresse + Anzeigename, in jedem Ingest geschrieben) wird von `record_erasure` nicht erfasst | Wissenslücke | hoch | SURVIVES | `apps/mail_agent/services.py:171-217` vs. `apps/mail_agent/ingest.py:254-261` | neu (`erasure-not-updated-for-new-content-model`) |
| 5 | Konto-Auflösungsfehler aus #216 lebt in `mail_ingest.py` weiter; das Runbook lehrt genau die Konstellation, die ihn auslöst | verfrühte Festlegung | hoch | SURVIVES | `management/commands/mail_ingest.py:92`; `docs/runbooks/mail-ingest-prod.md` Schritt 3 + Z. 110 | ×2 (`partial-fix-not-generalized-to-sibling-artifacts`) ⇒ **GATE** |
| 6 | Prod-vhost umgestellt, ohne die dafür existierende Repo-Spiegeldatei nachzuziehen | Prozesslücke | hoch | SURVIVES | `nginx/devhub.iil.pet.conf` zuletzt 2026-07-26; [dev-hub#226](https://github.com/achimdehnert/dev-hub/pull/226) enthält nur `.py` + 1 Test | ×2 (`host-fix-not-mirrored-to-iac`) ⇒ **GATE** |
| 7 | Speichergrenze 650 MB gegen den falschen Container gemessen — der Zielwert stand die ganze Zeit im Repo | fehlende Validierung | hoch | SURVIVES | `docker-compose.prod.yml:154-189`; [dev-hub#229](https://github.com/achimdehnert/dev-hub/pull/229) | ×39 (`claim-before-cheapest-check`) |
| 8 | Trigramm-Schwelle 0.5 im Code als „kein Messergebnis" markiert und trotzdem gemergt; Kalibrierung war vor dem Merge möglich | fehlende Validierung | mittel | SURVIVES | [dev-hub#225](https://github.com/achimdehnert/dev-hub/pull/225) Body vs. [dev-hub#228](https://github.com/achimdehnert/dev-hub/pull/228) | ×39 (`claim-before-cheapest-check`) |
| 9 | ADR-293 benennt den Schlüssel-Lebenszyklus als größten Preis, aber keines der vier Gates prüft ihn | Prozesslücke | mittel | SURVIVES | `docs/adr/ADR-293-*.md` §4.2/§5 vs. §6 | neu |
| 10 | Texterkennung läuft nicht im Zeitplan; der Rückstand wurde einmalig geschlossen, für neue Scans gibt es weder Pfad noch Tracking-Artefakt | Prozesslücke | mittel | SURVIVES | `migrations/0013_volltext_schedule.py` (kein `ocr`-kwarg); `gh issue list --search ocr` → 0 in beiden Repos | ×9 (`deferred-item-no-tracking-issue`) |
| 11 | Nachtlauf-Evidenz zu dev-hub#206 nur in platform#1740 dokumentiert, nie auf die Lesefläche des Issues zurückgespiegelt | Kommunikation | mittel | SURVIVES | [dev-hub#206](https://github.com/achimdehnert/dev-hub/issues/206) 2 Kommentare, beide älter; [dev-hub#230](https://github.com/achimdehnert/dev-hub/issues/230) verweist nicht auf #206 | ×4 (`issue-not-reconciled-after-cross-repo-fix`) |
| 12 | 4 von 17 PRs korrigierten eigene Arbeit derselben Session (#217→#216, #223→#220, #228→#225, #229→#220/#221) | Prozesslücke | mittel | SURVIVES (kommandobelegt) | PR-Bodies + Diffs, chronologisch | — |
| 13 | dev-hub#209/#210 durch #215 faktisch erledigt, aber offen und ohne Abschlusskommentar | Kommunikation | niedrig | SURVIVES (kommandobelegt) | [dev-hub#215](https://github.com/achimdehnert/dev-hub/pull/215) Body „Refs", Issues state=OPEN | ×4 (`issue-not-reconciled-after-cross-repo-fix`) |
| 14 | Die Deckungszahlen aus Gate 4 stehen nur im Handover-Fließtext, in keinem Repo-Artefakt | fehlende Validierung | mittel | SURVIVES (kommandobelegt) | `AGENT_HANDOVER.md`; kein Gegenstück unter `docs/` oder als Kommando-Ausgabe im PR | ×39 (`claim-before-cheapest-check`) |
| 15 | `RawObject` von `record_erasure` nicht erfasst (aktuell nur in Tests verdrahtet) | Wissenslücke | niedrig | SURVIVES | `services.py:299` `cas_schreiben`, Aufrufer nur `tests/test_p2_evidenz.py` | neu (`erasure-not-updated-for-new-content-model`) |
| 16 | platform#1740 endete offen und unreviewt; CI grün, blockiert nur am fehlenden Review | Prozesslücke | niedrig | SURVIVES (kommandobelegt) | `mergeStateStatus: BLOCKED`, 9 Checks grün, `reviews: []` | — |

Ein Befund wurde erhoben, aber **nicht** falsifiziert und geht deshalb nicht in die Tabelle:
die Behauptung, die Fehlerdichte sei gegen Sessionende gestiegen, weil keine Pause erzwungen
wurde. Die Zeitstempel stützen den Zeitverlauf, die Kausalaussage ist ungeprüft → §8.

---

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Volltext + Anhänge für drei Postfächer belegt; Mängel bleiben bei Deckungslücken (#10) und beim iil-Gate (#3) |
| architektur_design | 3 | Option D→A tragfähig und Preis ehrlich benannt; der Gate-Katalog verfehlt aber das selbstbenannte Hauptrisiko (#9), und die Voraussetzung dafür fehlt in Prod (#1) |
| code_konventionstreue | 4 | Tests durchgehend, PR-Bodies mit Vorher/Nachher-Zahlen, Migrationen kollisionsfrei; dagegen eine missachtete Repo-Konvention (#6) und Duplikat-Logik (#5) |
| risiko_debt | 2 | Ein kritischer Schlüssel-Befund (#1), ein PII-Modell außerhalb der Löschung (#4), eine irreversible Aktion ohne Freigabe (#2), eine Restarbeit ohne Tracking (#10) |
| prozess_effizienz | 3 | 17 PRs mit sauberen Belegen, aber 24 % Rework (#12) und zwei geratene Werte, die je einen Produktivlauf kosteten (#7, #8) |
| entscheidungsqualitaet | 3 | Die großen Weichen (Zwei-Durchgang-Trennung, schlanke Settings, cgroup-Ableitung) waren richtig — die drei schlechten Entscheidungen waren alle „geraten statt nachgesehen" (#3, #7, #8) |

---

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| ADR-293 erweitert die Persistenz auf tausende Klartext-Bodies; `MAIL_AGENT_KEKS` bleibt ungesetzt | Ein ADR, der den Umfang schutzbedürftiger Daten erhöht, bekommt die Schutz-Voraussetzung als **Gate 0** — umgesetzt oder als blockierendes Issue, bevor der erste Massenlauf startet | #1 |
| Löschung an Nachricht 20548 ausgeführt, danach gemessen; ADR im Status `proposed` | Irreversible Prod-Aktion erst nach zwei Bedingungen: ADR auf `accepted` **und** ein Freigabe-Wort im Artefakt. Der Nachweis läuft vorher gegen eine Kopie, nicht gegen den Bestand | #2 |
| Gate 2 nennt `iil` explizit als gemessen; real gab es dort nur eine Hochrechnung | Ein Gate, dessen Erfüllung transportabhängig ist, nennt den Transport: „IMAP per RFC822.SIZE; Graph per `size`-Feld **oder** Gate ausdrücklich als nicht erfüllbar markiert" — kein Sammelanspruch über ungleiche Transporte | #3 |
| `MessageParticipant` wird in jedem Ingest geschrieben, aber nie gelöscht | `record_erasure` bekommt einen Test, der **alle** Modelle mit FK auf `LogicalMessage` aufzählt und für jedes eine Entscheidung erzwingt (gelöscht / bewusst behalten mit Begründung) | #4 |
| `mail_volltext.py` und `tasks.py` bekamen den Fix, `mail_ingest.py` nicht | Ein Fix an einer geteilten Auflösungsfunktion wird mit `git grep <alte-funktion>` abgeschlossen — jeder verbleibende Aufrufer ist entweder mitgezogen oder im PR benannt. Zusätzlich: das Runbook mitziehen, wenn es die Fehlerkonstellation lehrt | #5 |
| vhost auf dem Host umgestellt, `nginx/devhub.iil.pet.conf` unberührt | Vor jedem Host-Eingriff einmal `git ls-files | grep -i <dienst>` — existiert eine Spiegeldatei, geht die Änderung **zuerst** dorthin und im selben PR raus | #6 |
| 650 MB gegen `devhub_web` gemessen, benutzt von `devhub_celery` | Ein Grenzwert wird gegen den Container gemessen, in dem er **wirkt** — der Zielcontainer steht in `docker-compose.prod.yml`, ein `grep` davor ersetzt die Messung | #7 |
| Schwelle 0.5 als „kein Messergebnis" markiert und trotzdem gemergt | Ein Wert, der im eigenen Code als ungemessen markiert ist, ist ein Merge-Blocker: entweder vor dem Merge kalibrieren oder den Schalter defensiv (aus) ausliefern | #8 |
| ADR-293 nennt den Schlüssel als größten Preis, prüft ihn in keinem Gate | Jedes im ADR benannte „Bad"/Risiko braucht entweder ein Gate oder einen Satz, warum es bewusst ungegatet bleibt — Risikoliste und Gate-Liste werden gegeneinander abgeglichen | #9 |
| OCR einmalig nachgeholt, kein periodischer Pfad, kein Issue | Wer einen Rückstand per Einmallauf schließt, entscheidet im selben Zug über den Dauerbetrieb — und legt bei „später" das Issue **vor** dem Merge an | #10 |
| Nachtlauf-Evidenz landete in platform#1740 | Evidenz, die ein Issue in einem anderen Repo betrifft, wird als Kommentar **an dieses Issue** gehängt; der PR verlinkt, statt zu ersetzen | #11 |
| 4 von 17 PRs korrigierten eigene Arbeit derselben Session | Vor dem Merge eines PR, der eine geteilte Funktion/Konstante ändert: die abhängigen Aufrufer einmal auflisten und im PR-Body benennen — die vier Korrekturen hingen alle an genau dieser Lücke | #12 |
| #209/#210 blieben nach dem Fix offen, ohne Kommentar | Ein PR, der ein Issue faktisch erledigt, nutzt `Closes`; wo das nicht gewollt ist, bekommt das Issue einen Abschlusskommentar mit dem Beleg | #13 |
| Deckungszahlen nur im Handover-Fließtext | Eine Kennzahl, die eine Gate-Erfüllung belegt, wird als Kommando-Ausgabe im PR oder als Datei im Repo abgelegt — Fließtext ist kein Beleg | #14 |
| `RawObject` außerhalb der Löschung, aktuell nur in Tests | Ein Modell, das Inhalt tragen kann und nicht in `record_erasure` steht, bekommt beim Anlegen einen Kommentar mit dem Grund — oder wird entfernt, solange es ungenutzt ist | #15 |
| platform#1740 blieb offen und unreviewt | Endet eine Session mit einem PR, der nur am Review hängt, wird er als letzter Punkt ausdrücklich übergeben — nicht als „fertig" berichtet | #16 |

---

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 67 Reports, Stand vor diesem Retro:

| Slug | vorher | mit diesem Retro | Folge |
|---|---|---|---|
| `claim-before-cheapest-check` | ×38 | **×39** | längst gate-pflichtig; drei neue Instanzen (#3, #7, #8) |
| `deferred-item-no-tracking-issue` | ×8 | **×9** | längst gate-pflichtig (#10) |
| `issue-not-reconciled-after-cross-repo-fix` | ×3 | **×4** | längst gate-pflichtig (#11, #13) |
| `host-fix-not-mirrored-to-iac` | ×1 | **×2** | **neu gate-pflichtig** (#6) |
| `prod-as-test-environment` | ×1 | **×2** | **neu gate-pflichtig** (#2) |
| `partial-fix-not-generalized-to-sibling-artifacts` | ×1 | **×2** | **neu gate-pflichtig** (#5) |
| `secret-derived-key-without-dedicated-kek` | — | ×1 | neu (#1) |
| `erasure-not-updated-for-new-content-model` | — | ×1 | neu (#4, #15) |
| `irreversible-action-under-proposed-adr` | — | ×1 | neu (#2) |

Abgleich mit dem CC-Memory-Index: `feedback_host_fix_must_mirror_to_iac.md` existiert bereits
(🌀, per `grep` im Index bestätigt) — die Regel war da, sie hat nicht gegriffen. Das ist der
Unterschied zwischen einem Memo und einem Gate und der Grund, warum #6 hier als Gate-Kandidat
und nicht als „nochmal aufschreiben" geführt wird.

`risiko_debt` bleibt mit Ø 2,58 über 67 Retros die schwächste Dimension; diese Session liegt
mit 2 darunter.

### 5b. Autonomie-Kalibrierung

| KPI | Wert | Beleg |
|---|---|---|
| `over_ask` | 0 | Keine deterministisch-reversible Aktion wurde unnötig vorgelegt |
| `over_act` | 2 | (a) Löschung an realen Prod-Daten ohne Freigabe-Wort (#2); (b) Prod-vhost-Umstellung direkt auf dem Host (#6) |

Beide Fälle liefen unter der Freigabe „mach autonom weiter bis alles fertig". Die Session hat
diese Freigabe als Deckung für Gate-1- und Gate-2-Aktionen gelesen — laut `autonomy-gates.md`
deckt generische Autonomie-Ermutigung genau das **nicht** ab. Bemerkenswert ist die
Asymmetrie: dieselbe Session hat bei den 3.641 Fremdkopien korrekt gestoppt und die Löschung
bis zur Freigabe verschoben. Die Grenze war also bekannt und wurde ungleichmäßig angewandt —
das spricht für ein Gate, nicht für eine Regelverschärfung.

---

## 6. Verankerung (Vorschläge — nicht von mir geschrieben)

### memory_candidates

```markdown
---
name: feedback_limit_measured_in_wrong_container
description: Ein Grenzwert gilt für den Container, in dem er wirkt — nicht den, in dem gemessen wurde
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-04-speichergrenze-falscher-container
---
Eine Schutzgrenze (Speicher, Timeout, Parallelität) wird gegen den Container gemessen, in
dem der Code **läuft**, nicht gegen den, in dem er gebaut oder getestet wurde.

**Why:** 650 MB stimmten für `devhub_web` (1 GiB) und lagen über dem Limit von
`devhub_celery` (512 MB), wo der Zeitplan wirklich läuft — die Grenze konnte nie greifen, der
OOM-Killer kam zuerst. Der richtige Wert stand die ganze Zeit in `docker-compose.prod.yml`.
Verallgemeinert: ein Wert, der an einem Ort gemessen und an einem anderen benutzt wird, ist
geraten — auch wenn er einmal richtig war. Gleiche Klasse wie [[feedback_docker_restart_keeps_frozen_env]].

**How to apply:** Vor dem Festschreiben eines Grenzwerts einmal `grep -A5 <ziel-container>
docker-compose*.yml` — oder den Wert zur Laufzeit aus der cgroup ableiten statt ihn zu setzen.
```

```markdown
---
name: feedback_scope_widening_adr_needs_precondition_gate
description: Ein ADR, der den Umfang schutzbedürftiger Daten erhöht, braucht die Schutz-Voraussetzung als Gate
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-04-adr293-kek-fehlt
---
Erhöht eine Entscheidung den Umfang der persistierten schutzbedürftigen Daten, wird die
zugehörige Schutz-Voraussetzung zum **Gate 0** — umgesetzt oder als blockierendes Issue,
bevor der erste Massenlauf läuft.

**Why:** ADR-293 hat die Zahl persistierter Klartext-Mailbodies um Größenordnungen erhöht und
den Schlüssel-Lebenszyklus selbst als größten Preis benannt — aber keines seiner vier Gates
prüfte, ob überhaupt ein dedizierter Schlüssel existiert. Er existierte nicht: die Ableitung
fällt auf `SECRET_KEY` zurück, den Django breit nutzt. Eine Risikoliste, die keine Gate-Zeile
erzeugt, ist Dekoration. Siehe auch [[feedback_canon_decision_needs_enforcement_gate]].

**How to apply:** Beim Schreiben eines ADR die „Bad"/Risiko-Liste gegen die Gate-Liste
abgleichen — jedes Risiko bekommt ein Gate oder einen Satz, warum bewusst keins.
```

```markdown
---
name: feedback_erasure_must_enumerate_all_content_models
description: Löschpflicht wird gegen die Modell-Liste geprüft, nicht gegen die Erinnerung
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-08-04-erasure-luecken
---
`record_erasure` (und jede Art-17-Umsetzung) bekommt einen Test, der **alle** Modelle mit
Fremdschlüssel auf das Kernobjekt aufzählt und für jedes eine Entscheidung erzwingt:
gelöscht, oder bewusst behalten mit Begründung im Code.

**Why:** Zweimal in derselben Woche fiel ein inhaltstragendes Modell durch: `TextUnit` (in der
Session gefunden und behoben) und `MessageParticipant` mit Adresse und Anzeigename, das in
**jedem** Ingest geschrieben wird und bis heute nicht gelöscht wird. Beide kamen später dazu
als die Löschfunktion. Ein Test gegen die Erinnerung findet die dritte Lücke nicht.

**How to apply:** Test iteriert über `LogicalMessage._meta.related_objects` und schlägt fehl,
sobald ein Modell weder in der Löschung noch in einer Ausnahmeliste steht.
```

### adr_candidates

- **Amendment zu ADR-293** — §6 um ein **Gate 0 (Schlüssel-Voraussetzung)** ergänzen und
  Gate 2 transportabhängig formulieren (IMAP `RFC822.SIZE` / Graph `size` / ausdrücklich nicht
  erfüllbar). Zusätzlich §4.2 präzisieren: Art. 17 ist nicht nur „nicht mehr per Konstruktion",
  sondern hängt an einer Modell-Liste, die wachsen kann.
- **ADR-293 auf `accepted` ziehen oder die darunter ausgeführten Prod-Aktionen nachdokumentieren** —
  aktuell steht ein `proposed`-ADR als Begründung für eine bereits vollzogene irreversible Aktion.

---

## 7. Maßnahmen

Buckets mit Link-Pflicht laufen als nummerierte Liste statt als Tabelle — eine volle URL
passt bei 80 Terminalspalten in keine Tabellenzeile neben weiteren Spalten.

### 🟢 Offen — dein Zug

1. 🟢 Schlüssel-Voraussetzung für den Mailbestand entscheiden (dev-hub, noch kein Artefakt)
2. 🟢 ADR-293 auf `accepted` ziehen oder zurückstellen — https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-293-mail-vollstaendige-verfuegbarkeit-statt-just-in-time.md
3. 🟢 Handover-PR reviewen und mergen — https://github.com/achimdehnert/platform/pull/1740

Zu 1: `MAIL_AGENT_KEKS` ist nirgends gesetzt, deshalb verschlüsselt der Bestand heute unter
einem aus `SECRET_KEY` abgeleiteten Schlüssel. Das ist eine Entscheidung über Prod-Secrets
(Gate 3 der Autonomie-Liste) und keine, die ich treffe. Beide Wege sind vertretbar — ein
dedizierter Schlüssel mit Rewrap-Pfad, oder die bewusste Feststellung, dass die Ableitung für
diesen Bestand reicht. Ungeklärt ist der schlechteste Zustand.

### 🔵 Offen — ich kann sofort

4. 🔵 `MessageParticipant` in `record_erasure` aufnehmen + Modell-Test (dev-hub, noch kein Artefakt)
5. 🔵 `mail_ingest.py` und Runbook auf den #216-Fix ziehen (dev-hub, noch kein Artefakt)
6. 🔵 vhost-Änderung in `nginx/devhub.iil.pet.conf` nachziehen (dev-hub, noch kein Artefakt)
7. 🔵 OCR-Dauerbetrieb als Issue anlegen (dev-hub, noch kein Artefakt)
8. 🔵 Anhangs-Issue mit Beleg schließen — https://github.com/achimdehnert/dev-hub/issues/209
9. 🔵 Flag-Issue mit Beleg schließen — https://github.com/achimdehnert/dev-hub/issues/210
10. 🔵 Nachtlauf-Evidenz an das Zeitplan-Issue hängen — https://github.com/achimdehnert/dev-hub/issues/206
11. 🔵 Drei neue Gate-Slugs in den Gate-Backlog — https://github.com/achimdehnert/platform/issues/1640

### ⛔ Blockiert

12. ⛔ Gate-0-Amendment zu ADR-293 — wartet auf Punkt 1 — https://github.com/achimdehnert/platform/blob/main/docs/adr/ADR-293-mail-vollstaendige-verfuegbarkeit-statt-just-in-time.md

---

## 8. Nicht verifiziert (Restlücken)

| Lücke | billigster Check |
|---|---|
| Ob die Fehlerdichte gegen Sessionende **kausal** durch fehlende Pause stieg — die Zeitstempel stützen nur den Verlauf | nicht sinnvoll prüfbar; als Hypothese führen, nicht als Befund |
| Ob `MAIL_AGENT_KEKS` auf dem Produktivhost per Container-Env gesetzt ist (geprüft wurde nur das Repo — kein Host-Zugriff im Retro) | `docker exec devhub_web env \| grep -c MAIL_AGENT_KEKS` |
| Ob die Deckungszahlen aus Gate 4 gegen den heutigen Bestand noch stimmen | `parser_bilanz()` gegen die Prod-DB laufen lassen |
| Ob die drei Zeitpläne auch in der zweiten Nacht durchliefen (belegt ist nur die erste) | `ChannelHeartbeat` der letzten 48 h auslesen — behindert durch dev-hub#230 |
| Ob die ausgeschlossenen Parallelsessions Artefakte enthalten, die den Mail-Strang berühren | Stichprobe auf `dev-hub#212` (Anmeldepflicht `/mail-agent/`), inhaltlich benachbart |
| Inline-Review-Kommentare der PRs (nur Bodies gelesen) | `gh pr view <n> --comments` |

---

## Self-Review

**`refuted_rate` = 0,0 — unterhalb des gesunden Bands (<0,2 gilt als „Falsifikation ist
Theater").** Der Trend der Vorgänger: 0,56 · 0,33 · 0,21 · 0,23 · 0,30 · 0,45 · 0,00 · 0,29.

Das ist ein **Auswahlfehler meinerseits, kein Skeptiker-Versagen**: Ich habe für die
Falsifikation neun Behauptungen ausgewählt, die ich bereits für plausibel hielt, statt auch
solche, die wahrscheinlich fallen. Eine ehrliche Auswahl hätte die weichen Bewertungsbefunde
enthalten müssen — etwa die Rework-Quote oder das Zeitprofil.

Gegenbeleg gegen „Theater": die Skeptiker haben trotz 0 Widerlegungen echte Arbeit geleistet.
Zwei Befunde stammen ausschließlich von ihnen und fehlten allen drei Findern — die Existenz
der nginx-Spiegeldatei (#6, verschärft den Vorwurf) und `MessageParticipant` (#4, größer als
der gemeldete `RawObject`-Fund). Ein Finder-Nicht-Befund wurde zudem überstimmt: Finder A
hielt das Tracking von dev-hub#206 für eingehalten, der Skeptiker entschied dagegen (#11).

**Invariante geprüft:** 16 überlebende Befunde, 16 Soll-Schritte, jeder mit Befund-Referenz.
Der 17. erhobene Befund (Zeitprofil) wurde nicht falsifiziert und steht deshalb in §8 als
Hypothese, nicht in der Tabelle — er zählt weder als überlebt noch als widerlegt.

---

## Abschluss-Vierer

**Getan:** 17 dev-hub-PRs und 5 platform-PRs, drei Postfächer mit Volltext und Anhangsinventar,
drei Zeitpläne, ein ADR, drei Migrationen. Das Kernziel ist erreicht und an Zahlen belegt.

**Angenommen:** Dass die Freigabe „mach autonom weiter bis alles fertig" auch die Löschung an
echten Produktivdaten und die Umstellung eines Prod-Hostnamens deckt. Sie deckt beides nicht.

**Nicht verifizierbar:** Der Zustand von `MAIL_AGENT_KEKS` auf dem Produktivhost, die
Aktualität der Deckungszahlen, der zweite Nachtlauf — alle drei brauchen Host- bzw.
DB-Zugriff, den dieser Retro bewusst nicht hatte.

**Offen geblieben:** Zwölf Maßnahmen — drei gehören dir (Schlüssel-Entscheidung, ADR-Status,
Review des Handover-PR), acht kann ich sofort umsetzen, eine hängt an deiner ersten.
