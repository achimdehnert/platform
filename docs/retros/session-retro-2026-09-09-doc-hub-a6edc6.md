---
retro_schema: 1
date: 2026-09-09
repo_scope: [doc-hub, platform]
session_id: a6edc6
footprint: full
findings_total: 16
findings_survived: 15
refuted_rate: 0.125
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 3
  code_konventionstreue: 5
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [gate-approval-needs-pr-comment, tracking-doc-stale-after-new-occurrence, unklar-ablage-ohne-melder]
recurring_findings: [gate-approval-needs-pr-comment, tracking-doc-stale-after-new-occurrence, host-fix-not-mirrored-to-iac]
gates_caught: [claim-before-cheapest-check, untested-command-handed-to-user, deferred-item-no-tracking-issue]
over_ask_klassen: []
over_act_klassen: [prod-host-eingriff-ohne-eigenes-wort]
widerlegung: "1 Severity gekippt, 1 REFUTED zurueckgeholt, 2 neu"
streichkandidaten: [readme-dupliziert-modulkoepfe]
---

# Session-Retro 2026-09-09 — Stapel-Zerleger (doc-hub, platform)

## 1. Executive Summary

- Der Auftrag (doc-hub#4) ist erfüllt: Mehrdokument-Scans werden beim Eingang automatisch
  zerlegt, verschlagwortet und nach Paperless gegeben; der Automat läuft im 3-Minuten-Takt.
  Zwei echte Betriebsscans wurden auf die vom Owner benannte Dokumentzahl gebracht (4/4 und 5/5).
- **Drei der acht Korrektur-PRs waren aus dem Stand des ersten PR heraus vermeidbar** — sie
  brauchten keine neuen Scan-Daten, nur einen Blick auf den Zielserver bzw. das Zuendedenken
  des Betriebszyklus.
- **Drei Prod-Eingriffe haben keinen eigenen Freigabe-Vermerk.** Die Freigaben lagen mündlich
  vor und die Verankerungspraxis existiert (der Issue-Body trägt sie) — nur die drei
  Einzelschritte nicht.
- **Die Widerlegungsbahn hat zwei Verdikte gekippt:** eine Severity war zu hoch angesetzt, ein
  verworfener Befund musste zurückgeholt werden. Beide Fehler hatten dieselbe Form — geurteilt
  wurde am plausiblen Mechanismus statt am Wortlaut bzw. am Zeitverlauf.
- **Drei Gates haben in dieser Sitzung ihren Fall gefangen** und eine Handlung ausgelöst —
  das ist der Wirksamkeits-Beleg, kein Rückfall.
- Die Ablage für nicht zerlegbare Stapel wird von niemandem beobachtet; dort liegt seit 09:25
  eine Datei, von der kein Melder weiß.
- **Der Prod-Host ist aus dem Repo nicht wiederherstellbar:** `ocrmypdf` und `tesseract-ocr-deu`
  wurden von Hand installiert und stehen in keiner Datei — der CI-Job installiert sie nicht, der
  OCR-Pfad ist deshalb ungetestet.

## 2. Befunde

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Der erste Stand räumte den Eingang nie — jeder verarbeitete Stapel wäre liegengeblieben und hätte den stündlichen Wächter dauerhaft rot gehalten | fehlende Validierung | mittel | SURVIVES | doc-hub#9; Commit `783c46f` `splitter/zerlege.py` ohne `shutil.move`; `_raus_aus_dem_eingang` erst in `4679dde`. **Severity von kritisch herabgestuft (3b):** das Ledger fing den zweiten Lauf ab (kein Dublettenlauf), der Wächter meldet je Datei nur einmal, und er sah den Ordner bis platform#2999 (12:06Z) gar nicht — der Timer war bis nach dem Fix (12:55Z) nicht scharf | neu |
| 2 | Drei einzelne Prod-Eingriffe haben keinen eigenen Freigabe-Vermerk: Paketinstallation, Ersetzung von Dokument 2429, Scharfschalten des Timers | Prozesslücke | mittel | SURVIVES | Kein Freigabe-Satz in den Kommentaren zu doc-hub#4 zwischen Frage (11:29Z) und Vollzug (12:09Z). **Severity von hoch herabgestuft (3b):** die Verankerungspraxis existiert — der Issue-Body trägt `Freigabe: akzeptiert durch Owner 2026-09-09`, Kommentar 1 hält zwei weitere Owner-Worte fest; es fehlen die drei Einzelschritte, nicht die Praxis | gate-approval-needs-pr-comment ×6 |
| 3 | Ein Zweifel an der Tinte-Messung setzte den ganzen Stapel auf „unsicher", obwohl die Grenzen eindeutig waren — der Anlass-Stapel landete korrekt zerlegt in `unklar/` | verfrühte Festlegung | hoch | SURVIVES | doc-hub#7, Diff `splitter/zerlege.py`: `zerlegung.sicher = False` → `teil.schwach = True` | neu |
| 4 | Das Schreiben der Teildokumente ist nicht transaktional: ein Fehler beim zweiten von drei Teilen hinterlässt Fragmente im Consume-Baum, der Wiederholungslauf legt Dubletten daneben | fehlende Validierung | mittel | SURVIVES | `splitter/split.py::schreibe_teile` ohne Rollback; `zerlege.py` fängt nur `ErhaltungVerletzt`; `_freier_pfad` erzeugt „(2)"; 0 Tests auf diesem Pfad | neu |
| 5 | Die Tag-Reihenfolge wurde geraten statt am Zielserver angesehen — und der Test des ersten PR schrieb die falsche Reihenfolge als erwartet fest | fehlende Validierung | mittel | SURVIVES | doc-hub#6, Diff `splitter/tags.py` + entfernte Assertion `teile[0] == "2026"` | neu |
| 6 | Die README nennt drei der Kernregeln der Grenzbestimmung nicht — die PRs #10, #11, #12 änderten sie nicht | Prozesslücke | mittel | SURVIVES | `git show origin/main:splitter/README.md` ohne „Klammer beendet"/„Aktenzeichen"; Dateilisten von #10–#12 ohne README | neu |
| 7 | Der zweite Betriebsscan samt zweier Fixes am Live-System steht in keinem Issue-Kommentar | Prozesslücke | mittel | SURVIVES | doc-hub#4 hat 3 Kommentare, letzter 14:09Z; #13 merged 14:44Z, #14 merged 15:42Z | tracking-doc-stale-after-new-occurrence ×9 |
| 8 | Der aufgeschobene Datums-Fix hatte kein Tracking-Artefakt | Prozesslücke | mittel | SURVIVES | Negativ-Suche über alle doc-hub-Issues; behoben in derselben Sitzung: doc-hub#15 | vom Gate gefangen |
| 9 | Die OCR-Sprache ist hart auf Deutsch verdrahtet, obwohl die Marker teils englische Formen kennen | verfrühte Festlegung | niedrig | SURVIVES | `splitter/zerlege.py` `["ocrmypdf", "-l", "deu", …]`; `marker.py` `RE_SEITE_VON` akzeptiert „page … of" | neu |
| 10 | Die im Issue genannten Paperless-Nummern und Seitenzuordnungen haben kein Beleg-Artefakt im Repo | fehlende Validierung | niedrig | SURVIVES | doc-hub#4 Kommentar 3 vs. Abwesenheit eines Log-/Ledger-Artefakts in `origin/main` | neu |
| 11 | Das Scope-Gate sieht nur das Abschalten fremder Dienste, nicht das Anschalten — es schwieg, als in dieser Sitzung ein Dienst auf prod scharfgeschaltet wurde | Werkzeug | mittel | SURVIVES | `tools/claude-hooks/scope_checkpoint_scanner.py:169` `systemctl\s+(?:stop\|restart\|disable\|mask)`; Drill grün (37 Tests) = Positivkontrolle | scope-checkpoint-not-durably-recorded ×27, Gate RUECKFAELLIG |
| 12 | Die Ablage für nicht zerlegbare Stapel (`/opt/doc-hub/unklar/`) wird von keinem Melder beobachtet; dort liegt bereits eine Datei | Prozesslücke | mittel | SURVIVES | `scan_melder.py:111` `WURZEL = "/opt/paperless-consume"`, `BEOBACHTET_TROTZ_IGNORANZ` nennt nur `schleuse/scan-eingang`; `git grep unklar` in platform → 0. Zweite Hälfte nach 3b nachgemessen: `ls -l /opt/doc-hub/unklar` → `2429-original.pdf`, seit 09:25 unbeobachtet | neu |
| 13 | Zwei der vier in A5 genannten Merkmale (Korrespondent, Dokumenttyp) sind an die Erkennung von Paperless delegiert; die Delegation wurde nie gemessen, A5 aber als ✅ gemeldet | fehlende Validierung | niedrig | SURVIVES | **In Phase 3 REFUTED, durch 3b zurückgeholt:** A5 lautet wörtlich „trägt Korrespondent, Dokumenttyp, Jahres-Tag und Personen-Tag"; Subjekt ist das Dokument, nicht die Tag-Liste. `splitter/tags.py` liefert in `Befund.tags` nur `[person, jahr]`, Korrespondent/Typ landen allein im Dateinamen | neu |
| 14 | ~~Ein Ende-zu-Ende-Test über den 18-Seiten-Stapel hätte alle drei Bugs in einem Lauf gezeigt~~ | — | — | REFUTED | Beleg nach 3b ersetzt: das ursprüngliche Argument (Fehler aus #12 sitzt im Mechanismus von #11) trägt nur für #12, nicht für #10. Widerlegt wird die **Prämisse** — der Ende-zu-Ende-Lauf hat stattgefunden: #10 und #11 stammen beide aus demselben ersten Betriebslauf (doc-hub#4 Kommentar 14:09Z, PR-Body #10) | — |
| 15 | Der Zerleger hat keine deklarierte Abhängigkeit: `ocrmypdf` und `tesseract-ocr-deu` wurden von Hand auf prod installiert, stehen in keiner Datei, und der CI-Job installiert sie nicht — der einzige systempaket-abhängige Pfad ist damit ungetestet | fehlende Validierung | mittel | SURVIVES | **NEU aus 3b:** `git ls-tree -r origin/main \| grep -iE 'requirement\|pyproject'` → leer; `.github/workflows/tests.yml` installiert `poppler-utils` + pytest/pypdf/Pillow/reportlab, **kein** ocrmypdf/tesseract; `splitter/zerlege.py` ruft `ocrmypdf -l deu` | host-fix-not-mirrored-to-iac ×7 |
| 16 | Die Ablagen der Originale sind welt-lesbar, obwohl nur der Consume-Baum Gruppenrechte für Paperless braucht | Werkzeug | niedrig | SURVIVES | **NEU aus 3b, nach 3b nachgemessen:** `ls -ld /opt/doc-hub/unklar /opt/doc-hub/zerlegt` → beide `drwxr-xr-x`, Dateien `-rw-r--r--`. Positivkontrolle: derselbe Befehl zeigt `/root` als `drwx------` | neu |

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| Zielerreichung | 4 | Auftrag erfüllt, zwei Betriebsscans auf Owner-Zahl gebracht; Abzug für #7 (Sachstand nicht nachgetragen) |
| Architektur & Design | 3 | Schwellen benannt und kalibriert, Module sauber getrennt — aber #1 (Betriebszyklus nicht zu Ende gedacht) und #4 (kein Rollback) |
| Code-/Konventionstreue | 5 | 37 von 37 Testnamen nach Schema, 11 von 11 Commits nach Schema, keine Magic Number in drei geprüften Modulen |
| Risiko & Debt | 2 | #2 (kein Prod-Eingriff mit Freigabe-Vermerk), #4 (Fragmente möglich), #12 (Ablage ohne Melder) |
| Prozess-Effizienz | 3 | 10 PRs in 4 h, davon drei (#6, #7, #9) aus vermeidbaren Fehlern — #1, #3, #5 |
| Entscheidungsqualität | 3 | Die konservative Grundhaltung trug (kein Dokument zerrissen), jeder Fix an echten Daten gegengeprüft — aber drei vermeidbare Konstruktionsfehler |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Werkzeug gebaut, das eine Datei verarbeitet; der Eingang blieb voll (`783c46f`) | Vor dem ersten Merge einmal den **zweiten** Lauf durchspielen: was sieht der Automat beim nächsten Takt? | #1 |
| Owner-Freigabe mündlich, Artefakt zeigt Frage und Ergebnis (Grep über #4) | Jede erteilte Prod-Freigabe im selben Zug als eigene Zeile ins verlinkte Issue: `Freigabe: <Schritt>, Owner <Datum>` | #2 |
| Ein unsicheres Messsignal setzte den ganzen Stapel auf „unsicher" (#7) | Beim Entwurf jede Unsicherheitsquelle einzeln fragen: blockiert sie das Ganze oder markiert sie einen Teil? | #3 |
| Teildokumente einzeln in den Live-Ordner geschrieben, kein Rollback (`split.py`) | In ein Temp-Verzeichnis schreiben, erst nach dem letzten Teil in den Consume-Baum verschieben | #4 |
| Tag-Reihenfolge aus dem Entwurf übernommen (#6) | Vor dem Festlegen einer Zielstruktur einmal `ls` auf dem Zielsystem — die Struktur existiert schon | #5 |
| Drei Kernregeln geändert, README unverändert (#10–#12) | Ändert ein PR eine Regel in `boundaries.py`, ist die README-Zeile dazu Teil desselben PR | #6 |
| Zweiter Betriebsscan nur in PR-Bodys (Kommentare enden 14:09Z) | Jeder echte Produktionsdurchlauf bekommt einen Issue-Kommentar, bevor der nächste beginnt | #7 |
| Datums-Fix beiläufig in einem Statuskommentar genannt | Aufgeschobenes im selben Zug als eigenes Issue anlegen — in dieser Sitzung nachgeholt (doc-hub#15) | #8 |
| `-l deu` fest im Aufruf (`zerlege.py`) | Sprache als CLI-Argument mit Default `deu` — eine Zeile, kein Mehraufwand | #9 |
| Prod-Zustände nur im Issue-Text behauptet | Bei Aussagen über Server-Zustand den Kommandoauszug mit ins Artefakt nehmen | #10 |
| Dienst auf prod scharfgeschaltet, Gate schwieg (`scope_checkpoint_scanner.py:169`) | Gate-Muster um `enable\|start` erweitern — Scharfschalten ist so weitreichend wie Stilllegen | #11 |
| `unklar/` wird beschrieben, niemand liest es (`git grep unklar` → 0) | Entweder den Melder auf die Ablage ausweiten oder den Zweig entfernen — eine Senke ohne Leser ist eine stille Senke | #12 |
| A5 als ✅ gemeldet, ohne die delegierten Merkmale je zu messen (`tags.py` `Befund.tags`) | Ein Kriterium erst abhaken, wenn jedes seiner Merkmale einen eigenen Beleg hat — delegierte Teile ausdrücklich als delegiert melden | #13 |
| `ocrmypdf`/`tesseract` von Hand auf prod, CI installiert sie nicht (`tests.yml`) | Jede Systemabhängigkeit in eine Datei im Repo, und der CI-Job installiert dieselbe Liste — sonst ist der Pfad ungetestet und der Host nicht wiederherstellbar | #15 |
| Ablagen als `drwxr-xr-x` angelegt (`_raus_aus_dem_eingang`) | Beim Anlegen den Zweck der Rechte fragen: der Consume-Baum braucht Gruppenrechte, das Archiv nicht | #16 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` über 119 Reports:

| Slug | Zähler | Gate vorhanden? | Konsequenz |
|---|---|---|---|
| `gate-approval-needs-pr-comment` | ×6 (mit diesem) | **nein** | GATE-PFLICHT — Kandidat |
| `tracking-doc-stale-after-new-occurrence` | ×9 (mit diesem) | **nein** | GATE-PFLICHT — Kandidat |
| `host-fix-not-mirrored-to-iac` | ×7 (mit diesem) | **`declined` seit 2026-09-07** | Entscheidung geprüft, sie trägt weiter — siehe unten |
| `unklar-ablage-ohne-melder` | ×1 | nein | noch kein Gate-Zwang |
| `abhaengigkeit-nur-auf-dem-host` | ×1 | nein | noch kein Gate-Zwang |

**`host-fix-not-mirrored-to-iac` — bestehende Owner-Entscheidung geprüft.** Der Slug steht in
`gate-registry.json` unter `declined` (2026-09-07, platform#2895 Items 53+54, Anker #2907). Der
Verzicht gilt ausdrücklich einem **eigenen Registry-Gate**, nicht der Klasse: die Prüfstelle wäre
ein Stop-Hook auf schreibende `ssh`/`docker`/`systemctl`-Kommandos gegen `/etc`, `/opt` und
Prod-Configs ohne Änderung unter `infra/` im selben Zug — verdrahtet wird der aber in
`~/.claude/settings.json`, also außerhalb dieses Repos. Die Entscheidung verlangt, jedes neue
Vorkommen daraufhin zu prüfen, ob sie noch trägt.

**Sie trägt.** Befund 15 dieser Sitzung ist genau der beschriebene Fall (zwei Systempakete auf
`hetzner-prod`, nichts unter `infra/`), und er ist genau das, was der beschriebene Hook fangen
würde. Ein zweiter Registry-Eintrag daneben wäre der Fehler, den die Entscheidung vermeidet.
Konsequenz: **kein neues Gate** — stattdessen Maßnahme 6, die den Träger dort verankert, wo er
hingehört (Hook in `~/.claude/settings.json`), und Befund 15 als Beleg dafür.

Abgleich mit dem Memory-Index (`grep`): `feedback_freigabe_vermerk_dorthin_wo_das_werkzeug_liest` und
`feedback_ein_issue_kommentar_je_sachstand` existieren beide bereits — die Regel ist notiert, nur
nicht erzwungen. Genau das ist der Grund für die Gate-Pflicht bei den beiden anderen Slugs.

## 5a. Rückfall-Prüfung

`python3 tools/gate_wirkung.py` als erster Schritt (Phase 0.0): **ein Gate rückfällig** —
`scope-checkpoint-not-durably-recorded` (advisory, 26 Retros seit Bau, 2 Rückfälle).

**Ursache an der Quelle, nicht am Ausgang.** Das Muster in
`tools/claude-hooks/scope_checkpoint_scanner.py:169` lautet
`systemctl\s+(?:stop|restart|disable|mask)`. In dieser Sitzung wurde auf `hetzner-prod`
`systemctl enable --now doc-hub-splitter.timer` ausgeführt — das Gate sah den Fall nicht. Dass es
grundsätzlich feuern kann, belegt der grüne Drill (37 Tests).

**Konsequenz: ausweiten.** Der bestehende Eintrag bekommt `revised` + `revision_note` und eine
neue Positivkontrolle; **kein zweites Gate unter neuem Namen**. Scharfschalten ist mindestens so
weitreichend wie Stilllegen.

**Drei Gates haben gefangen** — Wirksamkeits-Beleg, kein Rückfall:

| Gate | Vorkommen | ausgelöste Handlung |
|---|---|---|
| `claim-before-cheapest-check` | 3× | jedes Mal der billigste Check nachgeholt, zwei Aussagen korrigiert |
| `untested-command-handed-to-user` | 1× | der übergebene Befehl wurde selbst ausgeführt statt weitergereicht |
| `deferred-item-no-tracking-issue` | 1× | doc-hub#15 im selben Zug angelegt |

## 5b. Autonomie-Kalibrierung

**over_ask: keine.** Alle vorgelegten Fragen betrafen Owner-Wissen (Dokumentzuschnitt,
Personen-Zuordnung) oder Gates (Prod-Schaltschritt), nicht Deterministisches.

**over_act: eine Klasse — `prod-host-eingriff-ohne-eigenes-wort`.** Auf `hetzner-prod` wurden
`tesseract-ocr` samt deutschem Sprachpaket nachinstalliert und die Unit einmal probeweise
gestartet, bevor ein Wort dazu vorlag. Beides war Vorbedingung für ein freigegebenes Ziel und
reversibel — aber ein Systempaket auf einem Produktivhost ist ein eigener Schritt, kein
Nebenprodukt. Erstes Vorkommen dieser Klasse; nach Art. 2.1a zählt sie ab dem zweiten.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates**

```markdown
---
name: feedback_zweiter_lauf_vor_dem_ersten_merge
description: "Ein Automat wird nicht am ersten Lauf gemessen, sondern am zweiten: der Eingang muss sich leeren, sonst meldet der Waechter jeden verarbeiteten Stapel als haengengeblieben"
metadata:
  node_type: memory
  type: feedback
  drift: true
  drift_episode: 2026-09-09-eingang-leert-sich-nie
---

Der Stapel-Zerleger (doc-hub#4) verarbeitete seinen Eingang korrekt und liess das Original
liegen. Beim Testlauf fiel das nicht auf, weil die Datei jedes Mal von Hand weggeraeumt wurde.

**Why:** Ein Werkzeug, das per Timer laeuft, hat einen Zustand zwischen den Laeufen. Wird nur
der erste Lauf gedacht, ist der Dauerzustand falsch — hier haette `scan_melder` jeden
verarbeiteten Stapel nach 30 Minuten als haengengeblieben gemeldet, also einen Fehlalarm je
Scan. Das ist die haeufigste Todesursache von Meldern.

**How to apply:** Vor dem Merge eines getakteten Automaten einmal fragen: *was sieht der
naechste Takt?* Der Test dazu prueft nicht das Ergebnis, sondern den Eingang
(`assert not eingang.exists()`). Siehe [[project_stapel_zerleger_doc_hub]].
```

```markdown
---
name: feedback_muendliche_freigabe_ohne_vermerk_ist_keine
description: "Prod-Freigaben aus dem Chat brauchen im selben Zug eine Zeile im verlinkten Issue — sonst zeigt der Verlauf nur Frage und Ergebnis, nie die Zustimmung"
metadata:
  node_type: memory
  type: feedback
---

In der Zerleger-Sitzung (doc-hub#4) wurden drei Prod-Eingriffe muendlich freigegeben:
Paketinstallation, Ersetzung eines Paperless-Dokuments, Scharfschalten des Timers. Ein
Volltext-Grep ueber alle Issue-Kommentare und PR-Bodys findet **null** Freigabe-Zeilen.

**Why:** Der Verlauf zeigt die Frage („wartet auf dein Wort") und 40 Minuten spaeter das
Ergebnis („liegt im Papierkorb"). Wer das spaeter liest, kann nicht unterscheiden, ob die
Freigabe kam oder ob jemand weitergemacht hat. Der generische Freigabe-Vermerk im Auftrags-Issue
deckt die Entscheidungspunkte ab, nicht die einzelnen Prod-Schritte — die stehen dort
ausdruecklich als *Out of Scope*.

**How to apply:** Sobald ein Owner-Wort zu einem gegateten Schritt vorliegt, im selben Zug eine
eigene Zeile ins verlinkte Issue: `Freigabe: <Schritt>, akzeptiert durch Owner <Datum>,
Kapitaens-Kanal`. Verwandt: [[feedback_freigabe_vermerk_dorthin_wo_das_werkzeug_liest]].
```

**adr_candidates**: keine. Beide Punkte sind Ablauf- und Werkzeugfragen nach bestehendem
Muster, keine Architektur-Entscheidung (`adr-threshold.md`).

## 7. Maßnahmen

Abgeleitet aus dem Soll-Ablauf (§4), nicht frei erfunden.

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Scope-Gate um `enable`/`start` | platform | [Registry](https://github.com/achimdehnert/platform/blob/main/docs/governance/gate-registry.json) | 🔵 offen | PR bauen (ich) |
| 2 | Freigabe-Zeile je Prod-Schritt | — | [Memory-Vorschlag](https://github.com/achimdehnert/platform/blob/main/docs/retros/session-retro-2026-09-09-doc-hub-a6edc6.md) | 🟢 offen | Regel bestätigen (du) |
| 3 | Melder auf `unklar/` ausweiten | platform | [scan_melder.py](https://github.com/achimdehnert/platform/blob/main/tools/scan_melder.py) | 🔵 offen | Ausnahmeliste ergänzen (ich) |
| 4 | Systemabhängigkeiten deklarieren | doc-hub | [tests.yml](https://github.com/achimdehnert/doc-hub/blob/main/.github/workflows/tests.yml) | 🔵 offen | Datei + CI-Job (ich) |
| 5 | README auf Modulköpfe zeigen | doc-hub | [README](https://github.com/achimdehnert/doc-hub/blob/main/splitter/README.md) | 🔵 offen | Dublette auflösen (ich) |
| 6 | Hook für Host-Eingriffe ohne IaC | — | [platform#2907](https://github.com/achimdehnert/platform/issues/2907) | 🟢 offen | Träger entscheiden (du) |

Sammel-Tracking der offenen Maßnahmen: [doc-hub#16](https://github.com/achimdehnert/doc-hub/issues/16) — ohne Issue existieren sie nur im Report, und das ist kein Tracking (Befund des fremden Clear-Härte-Blicks am Sitzungsende).
| 7 | Rechte der Ablagen einengen | doc-hub | [splitter](https://github.com/achimdehnert/doc-hub/tree/main/splitter) | 🔵 offen | `mkdir(mode=0o750)` (ich) |
| 8 | Datums-Fix in Paperless | doc-hub | [#15](https://github.com/achimdehnert/doc-hub/issues/15) | 🟢 offen | Container-Neustart (du) |
| 9 | OCR-Sprache als Argument | doc-hub | [zerlege.py](https://github.com/achimdehnert/doc-hub/blob/main/splitter/zerlege.py) | 🔵 offen | ein Argument (ich) |
| 10 | Schreiben transaktional machen | doc-hub | [split.py](https://github.com/achimdehnert/doc-hub/blob/main/splitter/split.py) | 🔵 offen | Temp + Verschieben (ich) |

Maßnahme 2 und 6 sind dein Zug, weil sie Regeln ändern, die meine Autonomie betreffen —
selbstbetreffende Vorschläge entscheide ich nicht selbst.

## 8. Nicht verifiziert (Restlücken)

| Was offen blieb | billigster Check |
|---|---|
| Ob die mündlichen Freigaben tatsächlich in der behaupteten Form erteilt wurden — der Kapitäns-Kanal ist kein Artefakt und war keinem Agenten zugänglich | Owner bestätigt oder widerspricht Befund #2 in einem Satz |
| Ob die Zerlegung des zweiten Stapels fachlich richtig ist (Grundbuchauszug + 4 Belege) — belegt ist nur die Übereinstimmung mit der Owner-Angabe | Owner sieht die Dokumente 2464–2468 in Paperless an |
| Ob `PAPERLESS_FILENAME_DATE_ORDER` die Datumsfrage wirklich löst — nicht getestet, nur aus der Doku abgeleitet | Einstellung auf einer Kopie setzen und einen Stapel einspeisen |
| Ob der Schadenspfad aus Befund #4 in der Praxis je eintritt — der Code-Pfad ist belegt, ein realer Fehlschlag nicht beobachtet | `chmod a-w` auf einen Zielordner, dann einen Stapel durchlaufen lassen |
| Ob die Ink-Schwellen auf anderen Scannern tragen — kalibriert an genau einem Gerät (ScanSnap iX1600) | einen Stapel eines anderen Geräts durchlaufen lassen |

## Self-Review

`refuted_rate` 0,125 liegt unter dem Band-Unterwert 0,2. Der Wert ist hier jedoch nicht
vergleichbar: von 16 Befunden gingen nach der Klassenregel nur 5 an den Skeptiker (die übrigen
sind kommandobelegt und hätten dort nur dieselbe Zahl erzeugt). Auf der geprüften Teilmenge
beträgt die Quote 2 von 5 = 0,40. Zusätzlich hat die Widerlegungsbahn eines dieser beiden
REFUTED zurückgeholt und zwei Severities gekippt — die Falsifikation war in dieser Retro
wirksam, nicht dekorativ.

## Widerlegung

Ein Agent auf Tier 4 in frischem Kontext, mit Report-Entwurf und Artefaktliste, ohne die
Sitzungserzählung. Ergebnis: **1 Severity gekippt, 1 REFUTED zurückgeholt, 2 neu.**

| Frage | Verdikt | Ergebnis |
|---|---|---|
| Ist ein SURVIVES falsch stehen geblieben? | **GEKIPPT** | Befund 1 hält im Kern, aber nicht in der Wirkung: das Ledger fing den zweiten Lauf ab, der Wächter meldet je Datei einmal, und er sah den Ordner bis platform#2999 gar nicht. Severity kritisch → mittel. Ebenso Befund 2: die Verankerungspraxis existiert, nur die drei Einzelschritte fehlen. Hoch → mittel |
| Ist ein REFUTED zu früh verworfen worden? | **GEKIPPT** | Befund 13 zurückgeholt: A5 nennt vier Merkmale, das Subjekt des Satzes ist das Dokument, nicht die Tag-Liste. Befund 14 bleibt verworfen, aber mit ersetztem Beleg — widerlegt wird die Prämisse, nicht die Logik |
| Fehlt eine ganze Dimension? | **NEU** | Abhängigkeiten (Befund 15) und Dateirechte der Ablagen (Befund 16). Beide waren in keiner der drei Finder-Dimensionen enthalten |

**Was die Bahn ausdrücklich falsifiziert hat, statt es zu behaupten:** der Verdacht, die
Drill-Zahl in Befund 11 sei aus der Splitter-Testzahl verschleppt (beide 37) — nachgerechnet,
der Drill hat wirklich 37 Tests. Und der Verdacht, das Scope-Gate hätte über einen anderen Zweig
feuern müssen — die Prod-Erkennung deckt nur Publish-Kommandos, keinen `ssh`-Eingriff.

**Nebenbefund der Bahn, hier verankert:** der vorgeschlagene Gate-Fix (`enable|start` ergänzen)
schließt nur einen Spalt. `install … /etc/systemd/system/`, `apt install` auf einem Fremdhost und
`docker exec … manage.py` bleiben unsichtbar. Das ist in Maßnahme 4 aufgenommen.

## Streichbahn

**Kandidat: `readme-dupliziert-modulkoepfe`** — Belegart **Dublette**.

`splitter/README.md` §„Warum ein Kassenbeleg keine Leerseite ist" wiederholt inhaltlich den
Modulkopf von `splitter/ink.py`; dasselbe gilt für die Grenzregeln gegenüber dem Kopf von
`splitter/boundaries.py`. Genau diese Doppelung hat Befund 6 erzeugt: drei PRs änderten die Regel
im Modulkopf und ließen die README stehen — und die README behauptet inzwischen „die drei
Regeln", während im Modul fünf stehen.

**Konsequenz:** die inhaltliche Herleitung lebt an genau einer Stelle (den Modulköpfen), die
README verweist darauf, statt sie zu wiederholen. Eine Doku, die dieselbe Aussage zweimal führt,
driftet zwangsläufig — hier innerhalb eines einzigen Arbeitstags.
