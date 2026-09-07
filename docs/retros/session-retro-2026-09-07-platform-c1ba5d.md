---
retro_schema: 1
date: 2026-09-07
repo_scope: [platform]
session_id: c1ba5d
footprint: lean
findings_total: 5
findings_survived: 4
refuted_rate: 0.2
phase3_refuted: 1
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [draft-body-claim-unscanned, public-issue-comment-doubled, owner-ack-without-vorgang-id]
recurring_findings: [claim-before-cheapest-check, retro-streichkandidat-nicht-gestrichen]
gates_caught: [claim-before-cheapest-check]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "n/a (lean) — 0 gekippt, 0 neu"
streichkandidaten: [retro-phase-6-extern-handoff, mailcheck-deckungssatz-je-vorgang]
footprint_reduction_reason: "keine PRs, keine Commits, ein Repo, kein Prod-Schritt; Außenwirkung nur über Owner-gesendete Entwürfe (draft-first)"
---

# Session-Retro 2026-09-07 — platform — Mail-Arbeitsliste (c1ba5d)

Reviewte Sitzung: eine Mail-Arbeitssitzung, in der der Owner elf Vorgänge seiner
Arbeitsliste per Kurzbefehl abarbeiten ließ (Antwort-Entwürfe zu zwei Abschlussarbeiten,
einem Exposé, einer Lieferantenanfrage, einer Kanzlei-Rückfrage, einer fehlgeleiteten
Verbraucherbeschwerde, der PyPI-Org `iil`; dazu Ledger-Pflege). Ergebnis: 7 Entwürfe
(draft-first), 6 davon vom Owner gesendet, 1 verworfen; PyPI-Org `iil` gelöscht (Owner-Klick,
404 belegt); drei Status-Kommentare in
[#2291](https://github.com/achimdehnert/platform/issues/2291). Keine Commits, keine PRs,
kein Prod-Schritt. Footprint **lean**; nach Owner-Regel vom 2026-08-20 dennoch ein
Sonnet-Finder (2 Dimensionen) und ein Sonnet-Skeptiker (gebündelt, nur Bewertungsbefunde),
je frischer Kontext. Kein 3b, kein Meta-Agent (lean).

**Phase 0.0 — Wirkungsbilanz:** `gate_wirkung.py` meldet 0 Gates `RUECKFAELLIG` (25 `zu-frueh`,
4 `unerprobt`). Nichts vorab zu behandeln; der Rückfall-Fall dieser Sitzung (§5a) ist neu.

## 1. Executive Summary

- Elf Owner-Befehle, elf Ledger-Änderungen, die sich wörtlich mit dem Auftrag decken; keine
  stille Erweiterung oder Auslassung (Finder-Abdeckung).
- Ein versendeter Entwurf trägt eine falsche Zahl („22 pages", tatsächlich 23): das bestehende
  Gate `claim-before-cheapest-check` sieht Entwurfstexte nicht (§5a, Ursache Quelle → ausweiten,
  [#2924](https://github.com/achimdehnert/platform/issues/2924)).
- Dasselbe Gate fing im Chat zwei Allaussagen ab und erzwang je eine Gegenprobe (`gates_caught`).
- Zwei Issue-Kommentare im öffentlichen Repo innerhalb von drei Minuten mit demselben Sachstand.
- Streichbahn: der Kandidat `retro-phase-6-extern-handoff` taucht zum zweiten Mal auf
  (Ratsche → Befund), neu dazu der Deckungssatz je Vorgang (33 % des Ledgers)
  ([#2925](https://github.com/achimdehnert/platform/issues/2925)).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Entwurf an Kanzlei akzeptiert Erstberatungskosten (190 € netto), obwohl der Ledger die Entscheidung dem Owner zuwies | verfrühte Festlegung | hoch | REFUTED | Ledger-Notiz 149 nennt den Satz mit Vorbehalt „Owner streicht, falls nicht gewollt"; Board-Zeile [3]; Owner „3 done" vor Versand; Spend-Gate deckt nur Modell-/API-Kosten | — |
| 2 | Versendeter Entwurf nennt „22 pages", PDF hat 23 (`pdfinfo`, 23 Formfeeds, Fußzeile 23) | fehlende Validierung | niedrig | SURVIVES | Entwurf 189 Z. 5; Sendeordner HNU #34548 | `claim-before-cheapest-check` ×77 → **Gate rückfällig** (§5a) |
| 3 | Zwei Kommentare in #2291 (13:24:48Z, 13:27:25Z) berichten dieselben vier Kernfakten doppelt | Kommunikation | niedrig | SURVIVES | [#2291](https://github.com/achimdehnert/platform/issues/2291), Kommentare 13:24Z/13:27Z; Repo ist öffentlich | neu (`public-issue-comment-doubled`) |
| 4 | Owner-Kurzbestätigung „1 done" wurde per Inhaltsabgleich auf sechs Vorgänge verteilt; Zuordnung nur über Sendeordner-Belege gesichert | Werkzeug | niedrig | SURVIVES | Ledger-Diff: „Owner '1 done'" in 137/139/149/168/189/193, je mit UID/Betreff-Beleg | neu (`owner-ack-without-vorgang-id`) |
| 5 | Streichkandidat `retro-phase-6-extern-handoff` zum zweiten Mal in Folge ohne Streichung | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `grep streichkandidaten docs/retros/session-retro-2026-09-03-platform-0f59ce.md`; `~/shared`: 2 Briefings, 0 Antworten; Phase 6 steht weiter im Skill | `retro-streichkandidat-nicht-gestrichen` ×1 (erstes Vorkommen als Slug) |

Skeptiker-Abdeckung: Ledger-Diff, beide Kommentare (Volltext, Zeitstempel), Entwürfe 149/189,
PDF-Metadaten/Formfeeds/Fußzeilen, `autonomy-gates.md` Gate 5, `schreibstil/SKILL.md`. Nicht
prüfbar: der Chat-Board-Text (bewusst nicht mitgeliefert) — siehe §8.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | elf Befehle erfüllt, sechs Entwürfe unverändert gesendet; eine falsche Zahl ging raus (#2) |
| architektur_design | 4 | Ledger-Fortschreibung sauber, aber Zuordnung ohne Vorgangs-ID im Owner-Text (#4) |
| code_konventionstreue | 4 | Stil, Anrede, Umlaute, Draft-first, Fristpflicht ohne Befund; Faktenregel einmal verletzt (#2) |
| risiko_debt | 3 | Gate-Ausweitung und Streichung nur als Issues getrackt, nicht gebaut (#2, #5) |
| prozess_effizienz | 4 | Doppel-Kommentar im öffentlichen Issue (#3) |
| entscheidungsqualitaet | 4 | Kostenzusage korrekt geflaggt statt vorbelegt (#1 REFUTED); „4 done" per HTTP-Gegenprobe nicht blind verbucht |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Seitenzahl aus dem Lese-Eindruck in den Entwurf übernommen (Entwurf 189 Z. 5) | Jede Zahl in einem Entwurf stammt aus einem Kommando (`pdfinfo`, `wc -w`) und der Universal-Claim-Scanner läuft über `--body-file` | #2 |
| Zweiter Kommentar drei Minuten nach dem ersten mit demselben Sachstand (#2291) | Ein Kommentar je Sachstand; Nachträge per `gh issue comment --edit-last`, Housekeeping ins Handover statt ins öffentliche Issue | #3 |
| „1 done" per Inhaltsabgleich auf sechs Vorgänge verteilt (Ledger-Diff) | Board-Zeilen je Vorgang mit Nummer statt Sammelzeile „Sieben Entwürfe senden"; Bestätigung wird nur mit Vorgangs-Nummer + Sendeordner-Beleg verbucht | #4 |
| Streichkandidat aus Retro 0f59ce unverändert, Phase 6 weiter im Skill | Streichkandidat bekommt im selben Zug ein Issue mit Entscheidungsfrist; zweites Auftauchen ohne Issue ist selbst gate-pflichtig | #5 |

## 5. Längsschnitt

`retro_kpis.py` (114 Reports): `claim-before-cheapest-check` ×77 (GATE-PFLICHT, Gate registriert,
Rev 4 2026-09-07). `retro-streichkandidat-nicht-gestrichen` neu (×1). Memory-Abgleich per
`grep` in `MEMORY.md`: „Aussage > Blick" und „Kalibrieren" existieren (Zahl-vor-Prüfung-Familie),
kein Eintrag zu Issue-Kommentar-Dopplung oder Owner-Bestätigung ohne Nummer.

### 5a. Rückfall-Prüfung

`gate_wirkung.py`: 0 `RUECKFAELLIG`. Befund #2 ist ein Vorkommen des registrierten Gates
`claim-before-cheapest-check` **nach** Rev 4 — der Befund heißt daher **„Gate rückfällig"**,
nicht „Slug zum 78. Mal". Ursache **an der Quelle**: der Hook prüft den Chat-Text, ein Mail-Entwurf
über `--body-file` läuft daran vorbei. Konsequenz: **ausweiten** — Scanner auch über den
Entwurfs-Body (advisory), Positivkontrolle mit Seitenzahl-Behauptung. Registry-Edit (`revised` +
`revision_note` Rev 5 + `positivkontrolle`) läuft im Bau-PR durch `gate_verankerung_check.py --neu`;
bis dahin Kandidat, getrackt in [#2924](https://github.com/achimdehnert/platform/issues/2924).
Zugleich `gates_caught`: der Hook fing in derselben Sitzung zwei Allaussagen im Chat und erzwang
Gegenproben (Sendebeleg-Zählung mit Positivkontrolle, Fristen-Check) — Beleg **für** das Gate.

### 5b. Autonomie-Kalibrierung

`over_ask` 0: die vorgelegten Punkte (Terminzusage im Thesis-Entwurf, Kostenzusage im
Kanzlei-Entwurf, Konto löschen) sind Zeit-/Geld-/Irreversibles, keine deterministischen Schritte.
`over_act` 0: keine Außenwirkung ohne Owner-Klick; Issue-Kommentare im eigenen Repo sind
Tracking, kein Gate. Klassen: keine.

## 6. Verankerung

`memory_candidates` (kopierfertig, nicht geschrieben):

```markdown
---
name: feedback_zahl_im_entwurf_nur_aus_kommando
description: "Eine Zahl in einem Mail-Entwurf (Seiten, Wörter, Beträge) kommt aus einem Kommando, nie aus dem Lese-Eindruck — 22 statt 23 Seiten ging 2026-09-07 raus"
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-07-seitenzahl-im-entwurf
---
**Fehlannahme:** Die Seitenzahl eines PDFs lässt sich beim Lesen „mitzählen". Am 2026-09-07 stand
„22 pages" in einer gesendeten Rückmeldung, `pdfinfo` sagt 23.
**Why:** Der Evidenz-Hook prüft nur den Chat-Text, nicht den Entwurfs-Body (platform#2924).
**How to apply:** Vor `draft_mail`/`graph_mail --draft` jede Zahl im Body mit dem Kommando
belegen, das sie erzeugt (`pdfinfo`, `wc -w`, `grep -c`); bis der Scanner den Body sieht, ist
Schreibstil-Check Frage 2 händisch mit Kommando abzuhaken.
```

```markdown
---
name: feedback_ein_issue_kommentar_je_sachstand
description: "Im öffentlichen platform-Repo ist jeder Issue-Kommentar eine Veröffentlichung — Nachträge per --edit-last, Housekeeping ins Handover"
metadata:
  type: feedback
---
Am 2026-09-07 standen zwei Kommentare in #2291 drei Minuten auseinander mit demselben Sachstand.
**Why:** Zwei Zwecke (Status, Handover-Notiz) wurden nicht konsolidiert; das Repo ist öffentlich.
**How to apply:** Ein Kommentar je Sachstand; Ergänzung im selben Zeitfenster per
`gh issue comment --edit-last`; Sitzungs-Housekeeping gehört in AGENT_HANDOVER, nicht ins Issue.
```

`adr_candidates`: keine (keine Architekturentscheidung berührt).

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Scanner auf Entwurfs-Body ausweiten | platform | [#2924](https://github.com/achimdehnert/platform/issues/2924) | 🟢 | Owner: Bau freigeben |
| 2 | Streichbahn entscheiden (2 Kandidaten) | platform | [#2925](https://github.com/achimdehnert/platform/issues/2925) | 🟢 | Owner: streichen ja/nein |
| 3 | Zwei Memory-Kandidaten verankern | platform | §6 dieses Reports | 🟢 | Owner: übernehmen |
| 4 | Board-Zeile je Vorgang statt Sammelzeile | platform | §4 Zeile 3 | 🔵 | ich: ab nächster Mail-Sitzung |
| 5 | Retro-Report committen | platform | dieser PR | ✅ | — |

## 8. Nicht verifiziert (Restlücken)

- **Befund #4, Bedeutung von „1 done":** Ob die Bestätigung auf die nummerierte Board-Zeile
  „[1] Sieben Entwürfe prüfen und senden" zeigte, ist aus den Artefakten nicht ablesbar (der
  Chat-Text war den Agenten bewusst entzogen). Aus dem Sitzungsgedächtnis: ja — damit ist der
  Befund eine Hypothese über die Fehlerquelle, nicht ein eingetretener Fehlgriff. Billigster Check:
  Transkript-Zeile der Antwort vor „1 done".
- **Phase 3b und Phase 5:** nicht gefahren (lean). Kein Urteils-Widerleger, kein Meta-Agent.
- **Phase 6:** n/a (lean; zugleich Streichkandidat).
- **Konto `iildehnert`-Adresse, 2FA, Recovery-Codes:** nur Owner-Wort, kein Artefakt.

## Widerlegung

n/a — Footprint lean. `widerlegung: "n/a (lean) — 0 gekippt, 0 neu"`.

## Streichbahn

- **`retro-phase-6-extern-handoff`** — Belegart *kein Leser*: 2 Briefings unter `~/shared`,
  0 zurückgelegte Antworten; zweites Auftauchen nach Retro 0f59ce → Befund #5, Issue
  [#2925](https://github.com/achimdehnert/platform/issues/2925).
- **`mailcheck-deckungssatz-je-vorgang`** — Belegart *Dublette*: 177 Vorkommen in 75 Vorgängen,
  79.386 von 233.728 Zeichen (33 %); gehört einmal je Lauf in den Ledger-Kopf. Issue
  [#2925](https://github.com/achimdehnert/platform/issues/2925).

**getan:** Wirkungsbilanz, Collect aus Ledger-Diff/Issue/Sendeordnern, Finder (2 Dimensionen),
Skeptiker (4 Bewertungsbefunde), Soll-Ablauf, KPIs, Streichbahn, zwei Issues.
**angenommen:** Owner-Meldungen zu 2FA/Recovery-Codes und zur Übertragung der vier Altnamen.
**nicht verifizierbar:** Chat-Bezug von „1 done" (§8).
**offen geblieben:** Bau der Scanner-Ausweitung, Streich-Entscheid, Memory-Übernahme.
