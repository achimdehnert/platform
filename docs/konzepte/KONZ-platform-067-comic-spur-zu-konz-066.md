---
concept_id: KONZ-platform-067
title: Comic-Spur — Nachtrag zu KONZ-066, pädagogische Comics aus einem versionierten Panelplan
pipeline_status: idea
tier: T1                   # Konzept + interner Pilot; kein Kauf, kein Training, keine Veröffentlichung
owner: Achim Dehnert
spec_refs: []
adr_threshold: none        # nutzt die Comic-Engine aus ADR-252 unverändert; kein neuer Architekturentscheid
review_by: 2026-12-31
kill_criteria: "Der Owner beurteilt den Pilot-Comic am Prüfbogen als ‚nicht tragbar' UND eine Figuren-LoRA wird nicht freigegeben — dann keine weiteren Lern-Comics, Spur bleibt idea."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "https://github.com/achimdehnert/platform/issues/3668", commit_or_pr: "#3668", opened_in_session: true}
  - {claim_id: C2, source_path: "https://github.com/achimdehnert/platform/pull/3651", commit_or_pr: "#3651 (KONZ-066, offen)", opened_in_session: true}
  - {claim_id: C3, source_path: "https://github.com/achimdehnert/dev-hub/issues/423", commit_or_pr: "dev-hub#423", opened_in_session: true}
  - {claim_id: C4, source_path: "https://github.com/achimdehnert/writing-hub/pull/1334", commit_or_pr: "writing-hub#1334 (Pilot T5)", opened_in_session: true}
  - {claim_id: C5, source_path: "https://github.com/achimdehnert/illustration-hub/pull/368", commit_or_pr: "illustration-hub#368 (Render)", opened_in_session: true}
created: 2026-10-02
---

# KONZ-platform-067 — Comic-Spur (Nachtrag zu KONZ-066)

> Auftrag: [#3668](https://github.com/achimdehnert/platform/issues/3668), K2. Nachtrag zu
> **KONZ-platform-066** „KI-Erklärvideos mit gekennzeichnetem Avatar“, das noch in PR
> [#3651](https://github.com/achimdehnert/platform/pull/3651) liegt. Eigene Nummer statt
> „066a“: Der KONZ-Nummern-Guard (`scripts/konz_number_check.py`) liest nur die drei
> Ziffern und hätte 066 und 066a als Doppelvergabe gemeldet. **Tier T1**, nichts wird
> gekauft, trainiert oder veröffentlicht.

## Kernthese

KONZ-066 erklärt einen Begriff mit dem Gesicht des Owners. Die Comic-Spur erklärt denselben
Begriff mit einer **erfundenen, als solche gekennzeichneten Figur** auf einer Seite. Sie
braucht weder Gesicht noch Stimme des Owners und damit keine biometrischen Daten. Sie läuft
vollständig auf der eigenen GPU. Was sie von KONZ-066 übernimmt, ist der Weg vom Begriff zur
Seite: Thema, Quelle, Skript, Plan vor dem Rechnen.

## 1 Was übernommen wird, was sich ändert

| KONZ-066 | Comic-Spur |
|---|---|
| P1 Thema: eine Kernfrage, ein Kanal, eine Länge | **unverändert**. Länge heißt hier: eine Seite, vier Panels. |
| P2 Quellen: jede Aussage belegt | **unverändert**. Quellen stehen im Panelplan (Q1…), der Quellenfuß auf der Seite. |
| P3 Skript mit Belegspalte | **unverändert**. Die Sprechblasen sind das Skript; jedes Panel nennt seine Belege. |
| P4 Szenenplan vor dem Verbrauch von Rechenguthaben | **ersetzt durch den Panelplan**, ein versioniertes YAML mit Lernziel, Seed, Bildprompt und Sprechblasen je Panel (Abschnitt 2). |
| P5 Avatar + Stimme | **entfällt**. An ihre Stelle tritt der Figurenkanon im Panelplan. |
| P6 Schnitt | **ersetzt** durch Lettering + Seitensatz, beides automatisch und wiederholbar. |
| P7 Abnahme durch den Owner | **unverändert**. Grundlage ist der Prüfbogen zur Figurenkonsistenz. |

## 2 Der Panelplan (ersetzt P4)

Ein Panelplan legt **vor** dem ersten Render fest:

- **Thema und Einsatz** — wann im Kurs die Seite gezeigt wird. Ein Comic, der eine Übung
  vorwegnimmt, gehört hinter die Übung.
- **Lernziele** LZ1…: **jedes Panel trägt genau eines.** Eine Zuordnungstabelle neben dem
  Plan macht das prüfbar.
- **Figurenkanon** — ein fester Merkmalsatz mit Gewicht und Prüfmerkmalen für den Prüfbogen.
- **Render** — Checkpoint, Sampler, Bildgröße, Stil, Negativ-Prompt. Diese Werte stehen im
  Plan, nicht im Code; ein geänderter Default verstellt keine abgenommene Fassung.
- **Panels** — fester Seed, Bildbeschreibung, Sprechblasen und Captions mit Position.
- **Kennzeichnung und Quellenfuß** — beide stehen auf der Seite.

Der Plan durchläuft vor dem Render den **Folien-Prüfer** der Lehre (writing-hub,
`v12/pruefen.py`). Er meldet Fragen, Fragewörter am Satzanfang, Belehrungsformeln und
Autorennamen in Sprechblasen. Der Dozent behauptet, auch im Comic.

**Wiederholbarkeit** ist eine Eigenschaft des Plans, nicht ein Glück des Laufs: Gleicher Plan
auf derselben Box ergibt dieselben Bytes, das PDF eingeschlossen. Belegt ist das im
Pilot (Abschnitt 5).

## 3 Abgrenzung für Comic-Figuren

Abschnitt 3 von KONZ-066 gilt sinngemäß. Dort ging es um das Gesicht einer echten Person;
hier geht es um eine erfundene Figur. Die Regeln verschieben sich entsprechend:

| Praxis (NESTORA-Artikel, KONZ-066 §3) | Regel für Comic-Figuren |
|---|---|
| Erfundene Person, Gesicht nach fremdem Foto nachgebaut | Die Figur ist erfunden **und als erfunden gekennzeichnet**. Keine Anlehnung an reale Dritte: kein Prompt mit Personennamen, kein Referenzbild einer realen Person, keine Ähnlichkeit als Ziel. |
| Die Kunstfigur tritt als Fachautorität auf („alter Arzt“) | **Keine erfundene Autorität.** Die Figur hat keinen Titel, keine Berufsbiografie und keine Zitate. Fachliche Verantwortung trägt der Owner, belegt im Quellenfuß. |
| Wirkung „so echt, dass ich nicht zweifelte“ | Gezeichneter Stil, keine fotorealistische Darstellung. Kennzeichnung „KI-generierte Illustration · Figur frei erfunden“ im Seitenkopf. |
| „Das Publikum weiß ohnehin, dass es KI ist“ | Wir sagen es auf jeder Seite. |
| Gesundheits- und Heilsversprechen ohne Beleg | Keine Gesundheits-, Heil- oder Erfolgsversprechen in Sprechblasen. Jede Tatsachenbehauptung ist an eine Quelle im Plan gebunden. |
| Algorithmus-Taktik, Haken, künstliche Spannung | Keine Cliffhanger, keine Fragen in Sprechblasen. Die Seite erklärt, sie wirbt nicht. |
| KI-Produkt ungeprüft verkaufen | Kein Verkauf. Die Seite dient Lehre und Beratung, die der Owner selbst verantwortet. |
| — (neu für Bilder) | Figuren erwachsen, sachlich gekleidet, nicht sexualisiert. Der Negativ-Prompt schließt das aus, der Prüfbogen fragt es ab. Fehlbilder werden verworfen, nicht wegerklärt. |

Wer diese Tabelle bricht, bricht die Spur; die Seite erscheint dann nicht.

## 4 Ideen aus dev-hub#423

Das Issue fragt nach dem Stand von #3649 und nach einem Comic-Zusatz „Skript plus Panels
per LLM“. Es wurde als **Datenquelle** gelesen, nicht als Auftrag. Übernommen:

- **Skript und Panels aus einer Hand** — ja, aber als Plan, den der Owner liest, bevor
  gerendert wird. Ein Sprachmodell darf einen Panelplan **entwerfen**; die Belegbindung (P2)
  und der Folien-Prüfer entscheiden, nicht das Modell.
- **Nicht übernommen:** ein Lauf, der vom Begriff ohne Zwischenstopp bis zur fertigen Seite
  rechnet. Er überspringt P4, also genau den Schritt, den KONZ-066 aus dem Artikel behält.

Im Pilot ist der Plan von Hand geschrieben, ohne Sprachmodell. Ob ein LLM-Entwurf Zeit
spart, ist offen. Gemessen ist das nicht.

## 5 Pilot T5 — „Drei Stufen hinter einem Wort“

Thema T5 aus KONZ-066 §1, ein Grundlagenbegriff der Vorlesung. Quelle: writing-hub
`apps/lectures/inhalte/dai_strategy_session1.py`, Abschnitt „Drei Stufen hinter einem Wort“.

| Was | Wo |
|---|---|
| Panelplan, Zuordnung, Prüfbogen, PDF | writing-hub `docs/lehre/dai-strategy/comics/t5-drei-stufen/` ([#1334](https://github.com/achimdehnert/writing-hub/pull/1334)) |
| Einstiegsbefehl | `make lerncomic-t5` in writing-hub |
| Render (ComfyUI, Lettering, Seite, PDF) | illustration-hub `apps/comics/lerncomic.py` ([#368](https://github.com/achimdehnert/illustration-hub/pull/368)) |
| Modell | Illustrious-XL v2.0 auf der eigenen GPU; keine LoRA, kein Training, kein bezahlter Dienst |

Am 2026-10-02 gemessen:

- **Wiederholbar:** Zwei Läufe ergaben dieselben Bytes in allen elf Dateien, darunter das
  PDF. Der erste Lauf startete kalt nach dem Entladen des Modells.
- **Folien-Prüfer:** neun Sprechblasen und Captions, null Befunde.
- **Rechenzeit:** etwa 35 s je Seite bei geladenem Modell, rund 6 s je Panel.

Ob die Figur konsistent ist, entscheidet der Owner am Prüfbogen.

## 6 Aufwand

**Schätzung, nicht gemessen** (gemessen ist nur die Rechenzeit, Abschnitt 5)

| Posten | Einmalig | Je Seite |
|---|---|---|
| Render-Weg, Prüfer-Anbindung, Tests (im Pilot erledigt) | 1 Arbeitstag | — |
| Thema, Quellen, Lernziele, Sprechblasen bis Prüfer grün | — | 1–2 h |
| Figurenkanon und Bildprompts, Probe-Renders verwerfen | 1–2 h je neue Figur | 30–60 min |
| Prüfbogen ausfüllen, Urteil | — | 15 min (Owner) |
| Rechenzeit auf der eigenen GPU | — | unter 1 min |
| Figuren-LoRA, falls der Prüfbogen sie verlangt | 0,5–1 Tag + Trainingslauf (eigenes Gate) | — |

Je weitere Seite also etwa ein halber Tag, davon trägt der Owner rund 15 Minuten. Das ist
weniger als ein Avatar-Video nach KONZ-066 §4 und ohne laufende Lizenzkosten. Die Seite ist
aber auch weniger: kein Ton, keine Bewegung, eine Figur.

## 7 Grenzen und offene Punkte

- **Figurenkonsistenz ohne LoRA** hält nur über Kanon-Prompt und Seed. Im Pilot wechselt
  sichtbar das Umhängeband, ein Panel wirkt älter. Eine Figuren-LoRA ist bewusst
  ausgelassen (platform#3668 Out of Scope) und liegt als
  [illustration-hub#369](https://github.com/achimdehnert/illustration-hub/issues/369) bereit,
  ausgelöst nur durch das Owner-Urteil am Prüfbogen.
- **Mehrere Figuren** im selben Panel brauchen regionales Prompting. Der Pilot vermeidet
  das: [illustration-hub#370](https://github.com/achimdehnert/illustration-hub/issues/370).
- **Einsatzzeitpunkt** ist Didaktik, keine Technik. Der Plan nennt ihn, der Dozent hält ihn ein.
- **Veröffentlichung** (Moodle, LinkedIn) ist nicht Teil dieser Spur und braucht eine
  eigene Freigabe.

## Offene Entscheidungen des Owners

- **E1** Urteil am Prüfbogen des Piloten: tragbar, tragbar nach Nachbesserung oder LoRA nötig.
- **E2** Einsatz der Pilotseite in Session 1, nach der Übung, oder nicht.
- **E3** Ob eine zweite Seite (anderer Begriff, gleiche Figur) die Konsistenz über Seiten hinweg prüfen soll.
