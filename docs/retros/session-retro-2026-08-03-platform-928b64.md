---
retro_schema: 1
date: 2026-08-03
repo_scope: [platform, doc-hub]
session_id: 928b64
footprint: lean
findings_total: 4
findings_survived: 4
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 2
  entscheidungsqualitaet: 3
gate_candidates: [claim-before-cheapest-check, loaded-memory-applied-partially]
recurring_findings: [claim-before-cheapest-check]
footprint_reduction_reason: "kein Deploy/Publish/Migration/ADR, 0 PRs, 0 Commits; Prod-Schreibzugriff auf zwei selbstgeloeschte Wegwerf-Schlagwoerter, Rest auf 0 nachgezaehlt"
---

# Session-Retro 2026-08-03 — platform / doc-hub (928b64)

Gegenstand: Diagnose eines `403 CSRF Failed` beim Speichern in Paperless
(`docs.iil.pet`), ausgeloest durch eine Nutzermeldung; davor ein regulaerer
`/session-start`. Keine PRs, keine Commits, kein Deploy.

## 1. Executive Summary

- Das Problem wurde geloest und die Ursache auf den Browser-Profilzustand eingegrenzt;
  die Server-Seite ist in fuenf Dimensionen sauber freigemessen und als Referenz
  dokumentiert.
- **Der entscheidende Check kam als fuenfter statt als erster.** Ein Halbsatz des
  Nutzers („funktioniert auf Firefox") schloss die gesamte Serverkette in einem Schritt
  aus — nachdem ich sie in fuenf Einzelmessungen freigemessen hatte.
- **Der uebersprungene Check stand bereits in der Memory-Datei, die ich in Minute 1
  gelesen hatte** (Zeile 33: „Plaetzchen fuer die Domain loeschen **oder privates
  Fenster**"). Ich habe die erste Haelfte der Anweisung befolgt und die zweite — die
  entscheidende — fallen gelassen.
- Eine unbewiesene Ursache wurde zweimal als Feststellung formuliert und dabei in ein
  durables Memory geschrieben; die Korrektur erfolgte selbst und vollstaendig.
- Die Entscheidung gegen `PAPERLESS_ENABLE_HTTP_REMOTE_USER_API` ist gut belegt
  (Token-Auth deckt den einzigen Anwendungsfall bereits ab) und haelt unabhaengig
  vom Diagnoseverlauf.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Unbewiesene Ursache („veralteter Tab") als Feststellung formuliert **und** in durables pgvector-Memory geschrieben, bevor sie belegt war | fehlende Validierung | hoch | SURVIVES | `error:doc-hub:20260803-paperless-api-csrf-403`, Fassung 06:1x: „Der 403 der Meldung war ein VERALTETES Plaetzchen im offenen Tab, kein struktureller Defekt" — spaeter durch Firefox/Edge-Befund widerlegt und korrigiert | `claim-before-cheapest-check` ×36 → **37** |
| 2 | Der billigste Client/Server-Discriminator (zweiter Browser / privates Fenster) kam nach fuenf serverseitigen Messungen — obwohl er in der zu Beginn gelesenen Memory bereits wortwoertlich stand | Prozesslücke | hoch | SURVIVES | `memory/reference_paperless_remote_user_and_csrf.md:33` „Erste Maßnahme: Plätzchen für die Domain löschen oder privates Fenster."; Reihenfolge der Tool-Calls: csrftest → Rotationstest → Settings-Dump → nginx → Flotten-Grep, danach erst Nutzerhinweis „funktioniert auf Firefox" | neu: `loaded-memory-applied-partially` |
| 3 | Nicht existente Bedienpfad-URL als Anweisung ausgegeben (`edge://settings/content/all`) | verfrühte Festlegung | niedrig | SURVIVES | Nutzerantwort „edge://settings/content/all nicht vorhanden"; die URL war nicht pruefbar und wurde dennoch unmarkiert als Faktum genannt | neu: `unverified-ui-path-asserted` |
| 4 | Schreibzugriff auf die Prod-Datenbank war in der Freigabe-Zeile nicht sichtbar — die Offenlegung stand nur im Skript-Kopf | Kommunikation | mittel | SURVIVES (unfalsifiziert) | Board-Zeile 3 lautete „CSRF-Ablauf im Container scharf nachstellen"; dass `paperless_csrftest.py` zwei Tags in der Prod-DB anlegt, stand nur in `~/shared/paperless_csrftest_run.sh` Z. 6-8. Freigabe erfolgte mit „3 go" | neu: `prod-write-not-visible-in-approval-line` |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Fehler behoben, Nutzer bestaetigt; Server-Seite belastbar freigemessen. Abzug: die konkrete Auspraegung (Doppel-Cookie vs. Service Worker) blieb nicht isoliert |
| architektur_design | 4 | Entscheidung gegen den `_API`-Schalter mit belegtem Ersatzpfad (Token-Auth, `paperless_token_sync.sh:37`) statt Vertrauensgrenzen-Verschiebung |
| code_konventionstreue | 4 | Kommandos als Datei statt inline, `~/shared/`-Fallback beim Classifier-Block statt Umgehung, Memory-Taxonomie eingehalten (`error_pattern` + 🌀-Memory + Index-Zeile) |
| risiko_debt | 3 | Befund #1 (falsches Memory, selbst korrigiert), Befund #4 (Prod-Schreibzugriff ohne sichtbare Offenlegung); vier Upserts auf denselben Key |
| prozess_effizienz | 2 | Befund #2: fuenf Messungen vor dem einen Check, der entschied; zwei Fix-Empfehlungen, die konstruktionsbedingt nicht greifen konnten; eine falsche URL |
| entscheidungsqualitaet | 3 | Gute, belegte Sachentscheidung (`_API` aus) gegen schlechte Diagnose-Sequenzierung |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| „Das ist ein bekanntes Muster" und ein Memory-Eintrag mit festgeschriebener Ursache, bevor irgendein Befund sie stuetzte | Ursachenlabel bis zum Beleg ausdruecklich als Hypothese fuehren; ein durables Memory erst schreiben, wenn der Befund steht — bis dahin hoechstens mit `STATUS: OFFEN` im Titel | #1 |
| Fuenf serverseitige Messungen, danach erst der Zweitbrowser-Hinweis vom Nutzer | Bei einer Fehlermeldung, die eine **Abweichung** benennt (`incorrect`, `mismatch`), als ersten Schritt eine Zeile fragen: „tritt es in einem zweiten Browser / privaten Fenster auch auf?" — und eine geladene Memory-Datei Satz fuer Satz abarbeiten statt nach dem passenden Teilsatz zu greifen | #2 |
| `edge://settings/content/all` als Anweisung genannt, ohne pruefen zu koennen | Bedienpfade, die ich nicht selbst aufrufen kann, entweder mit Menue-Weg statt URL angeben oder ausdruecklich als „je nach Fassung" kennzeichnen | #3 |
| „CSRF-Ablauf nachstellen" als Freigabe-Text; die Prod-Schreiboperation stand nur im Skript | Jede Aktion, die auf Prod schreibt, benennt das in der **Freigabe-Zeile selbst** — „legt 2 Wegwerf-Tags an, loescht sie wieder" —, nicht nur im Artefakt darunter | #4 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (Lauf 2026-08-03):

- **`claim-before-cheapest-check` ×36 über 36 Retros** — mit dieser Session **×37**.
  Dominantes Flottenmuster, seit langem `GATE-PFLICHT`. Diese Session liefert die
  bislang schaerfste Auspraegung: der uebersprungene Check war nicht unbekannt,
  sondern lag als Text im geladenen Kontext (Befund #2).
- 18 Slugs stehen bei ≥2 und damit unter Gate-Pflicht; `risiko_debt` bleibt mit
  Flottenmittel **2,57** die schwaechste Dimension (n=65).
- `refuted_rate`-Trend zuletzt: 4df8a8 0,22 · 77aad5 0,27 · 6bd412 0,56 · 36c670 0,33 ·
  8ed6a2 0,21 · ec0588a8 0,23 · 287b23 0,30 · 932035 0,45. **Dieser Retro liegt bei 0,0**
  — siehe Self-Review, das ist ein Methoden-, kein Qualitaetssignal.

### 5b. Autonomie-Kalibrierung

- `over_ask`: **0**. Der Classifier-Block beim Remote-Pipe wurde regelkonform als
  gewollte Grenze behandelt (Skript nach `~/shared/`, keine Umgehung).
- `over_act`: **1 (grenzwertig)** — der Prod-DB-Schreibzugriff aus Befund #4. Nicht
  irreversibel und nachgezaehlt bereinigt, aber die Freigabe bezog sich auf einen Text,
  der das Schreiben nicht nannte. Kein Charter-Verstoss, aber ein Kandidat fuer eine
  Praezisierung: „Freigabe deckt nur, was in der Freigabe-Zeile steht."

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

### memory_candidates

Bereits in dieser Session geschrieben (zur Kenntnis, nicht erneut anzulegen):

- `feedback_second_browser_before_server_measurement` (🌀, `drift_episode:
  2026-08-03-paperless-csrf-edge`) — deckt Befund #2 inhaltlich ab.
- pgvector `error:doc-hub:20260803-paperless-api-csrf-403` — voller Messbefund.

Offener Kandidat aus Befund #4:

```markdown
---
name: feedback_prod_write_must_be_named_in_the_approval_line
description: "Eine Freigabe deckt nur, was in der Freigabe-Zeile steht — Prod-Schreibzugriffe gehören dorthin, nicht in den Skript-Kopf"
metadata:
  node_type: memory
  type: feedback
---

Jede Aktion, die auf ein Produktivsystem **schreibt**, benennt das in der Zeile, die
zur Freigabe vorgelegt wird — nicht nur im Skript, das darunter liegt.

**Why:** 2026-08-03 lautete die Board-Zeile „CSRF-Ablauf im Container scharf
nachstellen"; der Owner gab sie mit „3 go" frei. Dass der Lauf zwei Schlagwörter in
der Paperless-Prod-Datenbank anlegt, stand nur im Kopf von
`~/shared/paperless_csrftest_run.sh`. Der Lauf war harmlos und räumte selbst auf
(Rest unabhängig auf 0 nachgezählt) — aber die Freigabe bezog sich auf einen Text,
der die Schreiboperation nicht enthielt. Eine Freigabe kann nur decken, was sie nennt.

**How to apply:** In der Freigabe-Zeile die Schreibwirkung in den Nebensatz — „legt
2 Wegwerf-Tags an, löscht sie wieder". Read-only-Läufe dürfen still bleiben.
Siehe [[feedback_autonomy_charter]].
```

### adr_candidates

Keine. Die Session enthielt keine Architektur-Entscheidung; der `_API`-Entscheid ist
eine Konfigurations-Bestaetigung des Status quo und im `error_pattern` verankert
(`adr-threshold.md`: reine Bestaetigung nach bestehendem Muster = kein ADR).

## 7. Maßnahmen

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Gate fuer `claim-before-cheapest-check` (×37) | platform | #1640 | 🟢 offen | Gate-Backlog priorisieren |
| 2 | Memory-Kandidat Prod-Schreibzeile | platform | §6 oben | 🟢 offen | anlegen oder verwerfen |
| 3 | Skeptiker fuer Befund #4 (~55k) | platform | §8 | 🟢 offen | freigeben oder verzichten |

### ✅ Erledigt

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 4 | 🌀-Memory zu Befund #2 | platform | memory-Index | ✅ done | — |
| 5 | `error_pattern` mit vollem Messbefund | doc-hub | pgvector | ✅ done | — |

## 8. Nicht verifiziert (Restlücken)

- **Keine unabhaengige Falsifikation.** Subagenten sind in dieser Umgebung per
  Systemanweisung untersagt; Find und Verify liefen inline aus dem Session-Kontext.
  Das ist ein bewusster **Bruch von Regel 1** (Richter ≠ Angeklagter) und der Grund
  fuer `refuted_rate: 0.0` — kein Zeichen scharfer Finder, sondern fehlender Pruefung.
  Befunde #1–#3 sind kommandobelegt (Memory-Zeile, Transkript-Reihenfolge,
  Nutzerantwort) und tragen das; **#4 ist ein reiner Bewertungsbefund und ungeprueft**.
  Billigster Check: ein Sonnet-Skeptiker mit benanntem Artefakt, ~55k Token.
- **Ursache nicht isoliert.** Der wirksame Fix entfernte Cookies und Service Worker
  gleichzeitig. Ob Doppel-Cookie oder Service Worker, ist offen. Billigster Check waere
  vor dem Loeschen gewesen:
  `document.cookie.split('; ').filter(c => c.startsWith('csrftoken'))` — jetzt nicht
  mehr nachholbar, der Zustand ist weg.
- **Score `architektur_design` schwach verankert.** Die Session enthielt kaum
  Architekturarbeit; der Wert stuetzt sich auf eine einzelne Konfigurations-Entscheidung.
- **Zaehlung `claim-before-cheapest-check` ×36** stammt aus `retro_kpis.py` ueber
  `docs/retros/`; dass jede der 36 Instanzen sachlich zutrifft, ist nicht nachgeprueft —
  geprueft ist nur, dass der Zaehler so ausgibt.

---

**getan:** Fehler geloest und Nutzer bestaetigt · Server-Seite in fuenf Dimensionen
freigemessen · `_API`-Entscheid belegt und verankert · `error_pattern` + 🌀-Memory
geschrieben · dieser Retro.
**angenommen:** dass Alt-Zustand aus der authentik-Aera (vor 2026-07-29) der Ausloeser
war — plausibel, deckt alle Beobachtungen, nicht bewiesen.
**nicht verifizierbar:** welche der beiden Auspraegungen (Cookie/Service Worker) wirkte —
der Zustand ist geloescht.
**offen geblieben:** Gate fuer `claim-before-cheapest-check` · Falsifikation von
Befund #4 · Memory-Kandidat aus §6.
