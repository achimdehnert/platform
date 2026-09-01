---
retro_schema: 1
date: 2026-09-01
repo_scope: [meiki-hub, platform, risk-hub]
session_id: 33616e
footprint: deep
findings_total: 10
findings_survived: 10
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [gate-untested-command-handed-to-user-rueckfaellig, fremde-datei-ohne-zuordnung-verarbeitet, formatierer-zerstoert-handgesetztes-artefakt]
recurring_findings: [untested-command-handed-to-user, claim-before-cheapest-check, scope-checkpoint-not-durably-recorded, partial-fix-not-generalized-to-sibling-artifacts]
gates_caught: [claim-before-cheapest-check, scope-checkpoint-not-durably-recorded]
---

# Session-Retro 2026-09-01 · meiki-hub (+ platform, risk-hub)

## 1. Executive Summary

- **16 Merges auf `origin/main`, 13 davon aus dieser Sitzung.** Der Datenschutz-Strang ist abgeschlossen (Anzeigepflicht entfällt), der integrierte Klickdummy steht (#159, alle fünf Kriterien belegt), vier stille Melder sind repariert, ADR-Frontmatter von 13/36 auf 36/36.
- **Vier Defekte hatten dieselbe Form:** ein Melder, der nichts meldete — und jeder verdeckte den nächsten, bis der davor behoben war. Das ist der stärkste inhaltliche Ertrag der Sitzung.
- **Der Auslöser war `/mcp`.** Die Kette bis zu 13 PRs in drei Repos entstand ausschließlich über Owner-Freigaben Punkt für Punkt; ein Scope-Checkpoint wurde ausgesprochen und durabel abgelegt, danach wuchs der Scope aber ohne erneuten Checkpoint weiter.
- **Ein Fremdartefakt wurde in der falschen Sitzung verarbeitet** (netcup-AVV) — Zusammenhang unterstellt statt erfragt, Kommentar musste gelöscht werden.
- **Keine Falsifikation.** Subagenten sind in dieser Umgebung untersagt; die Find-Phase lief inline, Regel 1 (Richter ≠ Angeklagter) ist damit gebrochen. Steht als Restlücke in §8, nicht als Haken.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Scope wuchs von „`/mcp` anzeigen" auf 13 PRs in 3 Repos + Staging-Schreibzugriff. Checkpoint einmal abgelegt, danach kein zweiter trotz weiterem Wachstum (risk-hub, VVT, Retro) | Prozesslücke | mittel | SURVIVES (unfalsifiziert) | Checkpoint-Kommentar meiki-hub#151, danach 5 weitere PRs + Fremd-Repo | scope-checkpoint-not-durably-recorded (gefangen) |
| 2 | Der netcup-AVV wurde als Antwort auf Vorfrage (d) gelesen und geprüft, obwohl er zu einer anderen Sitzung gehörte. Zusammenhang unterstellt statt erfragt | Kommunikation | mittel | SURVIVES | Kommentar 5490768057 auf meiki-hub#148 angelegt und gelöscht; `grep -ric netcup` über Repo + Issue = 0 | neu |
| 3 | `json.dumps`-Roundtrip zerstörte die handgesetzte Spaltenausrichtung von `module-manifest.json` — 202 geänderte Zeilen für einen Modul-Eintrag | fehlende Validierung | mittel | SURVIVES | `git diff --stat` vor Rücknahme 202, nach chirurgischem Edit 15 | formatierer-zerstoert-handgesetztes-artefakt (neu) |
| 4 | Erste Messung des CI-Step-Exit-Codes maß `tail` statt des Steps (`PIPESTATUS` im Subshell) und meldete `EXIT=0` für einen fehlschlagenden Test | fehlende Validierung | niedrig | SURVIVES | Messung A/B: erst `EXIT=0/EXIT=0`, nach Korrektur `EXIT=0/EXIT=1` | claim-before-cheapest-check (gefangen) |
| 5 | Der `</script>`-Befund wurde zunächst als „kosmetisch" eingeordnet; real liefen drei Init-Funktionen nie | Wissenslücke | hoch | SURVIVES | Erstfassung meiki-hub#161 vs. Neufassung; `grep -n "initFeedback()"` → einzige Aufrufstelle hinter dem Abbruch | neu |
| 6 | #153/#154 als „Dublette" gemeldet; real zwei verschiedene Findings (ADR-171 und ADR-172 fehlen beide) | fehlende Validierung | mittel | SURVIVES | Issue-Bodies: `references ADR-171` vs. `ADR-172` | claim-before-cheapest-check (gefangen) |
| 7 | Der Konventions-Sweep löschte YAML-Kommentare mit Entscheidungsinhalt (AMENDMENT-Notiz ADR-032, Use-Case-Beschreibungen ADR-030/032). Erst die nachgeschobene Gegenprobe fand sie | fehlende Validierung | hoch | SURVIVES | Gegenprobe gegen `HEAD`: erst 2 verlorene Werte, nach Reparatur 0 | partial-fix-not-generalized-to-sibling-artifacts |
| 8 | **Gate `untested-command-handed-to-user` ist rückfällig** — 2× in dieser Sitzung ausgelöst. Sonderfall: die Ausführung war durch den Permission-Classifier gesperrt (`docker exec`), das Gate kennt diesen Zustand nicht | Werkzeug | hoch | SURVIVES | `gate_wirkung.py`: gebaut 2026-08-23, vor 1 / **nach 3**, letzter Rückfall 2026-08-28; Hook-Feedback 2× in dieser Sitzung | untested-command-handed-to-user ×4 |
| 9 | Vier Aktionen brauchten die Hand des Owners, weil der Classifier sie sperrte (`gh pr merge --admin` ×1, `docker exec` ×3) — kein `over_ask`, sondern eine Werkzeuggrenze | Werkzeug | niedrig | SURVIVES | Classifier-Ablehnungen im Verlauf; Owner führte beide Befehle aus | neu |
| 10 | Diese Retro lief ohne Falsifikation und ohne fremden Kontext (Subagenten untersagt) — Regel 1 gebrochen | Prozesslücke | mittel | SURVIVES | Repo-Memory `keine-subagents-zu-teuer`; kein Agent-Spawn in dieser Sitzung | wiederkehrend in dieser Umgebung |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Jeder freigegebene Punkt erledigt oder mit Grund zurückgegeben; Abzug für #2 (falsche Sitzung) |
| architektur_design | 4 | Neues KD-Modul nutzt ausschließlich definierte Klassen, während acht Bestandsmodule undefinierte benutzen; Manifest-Diff nach Rücknahme minimal |
| code_konventionstreue | 4 | Worktree-Disziplin durchgehend, kein Edit im Haupt-Tree; Abzug für #3 |
| risiko_debt | 4 | Jede bewusste Auslassung getrackt: #150, #161, #165, platform#2562; zehn unverankerte Session-Start-Befunde abgelegt (8 verankert, 2 Verzicht) |
| prozess_effizienz | 3 | Drei Selbstkorrekturen mitten im Lauf (#3, #4, #6), alle selbst gefangen, aber jede kostete einen Durchgang |
| entscheidungsqualitaet | 4 | Anzeigetexte vermerkt statt gelöscht; `extends`-Abbildung empirisch getestet statt geraten; Abzug für #5 (Fehleinordnung vor der Prüfung) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll | eliminiert |
|---|---|---|
| Checkpoint auf #151 abgelegt, danach fünf weitere PRs und ein Fremd-Repo ohne erneuten | Ein Checkpoint gilt für den Scope, den er beschreibt. Beim Übertritt in ein weiteres Repo wird er erneuert, nicht fortgeschrieben | #1 |
| Datei in `~/shared/` gefunden, Zusammenhang zum offenen Vorgang unterstellt | Eine Schleusen-Datei ohne Zuordnung wird zugeordnet, bevor sie verarbeitet wird — eine Zeile Rückfrage vor der ersten Prüfung | #2 |
| `json.dumps` auf handformatiertes JSON | Struktur-Roundtrips nur auf maschinengeschriebene Dateien; bei handgesetzter Ausrichtung Textedit. Prüfgröße ist der Diff-Umfang, nicht die Gültigkeit | #3 |
| `EXIT=${PIPESTATUS[0]}` hinter einer Subshell mit Pipe | Exit-Codes ohne Pipe messen (`cmd >datei; echo $?`), und jede Messung gegen einen bekannten Fehlschlag gegenprüfen | #4 |
| Befund vor der Ursachenanalyse als „kosmetisch" klassifiziert | Severity erst nach dem Aufrufstellen-Check vergeben — „was hängt daran?" vor „wie schlimm sieht es aus?" | #5 |
| Zwei gleichnamige Issues als Dublette gemeldet | Gleicher Titel ist kein Dublettenbeleg; verglichen wird der Rumpf | #6 |
| Feld-Sweep über 17 Dateien ohne Verlustkontrolle | Vor dem Commit eine Gegenprobe alt↔neu über alle geänderten Dateien, die auf verschwundene Werte prüft — inklusive Kommentarinhalten | #7 |
| Gate meldet „ungeprüft weitergegeben", obwohl die Ausführung gesperrt war | Das Gate um den Zustand „Ausführung verweigert" erweitern: eine dokumentierte Classifier-Ablehnung im selben Turn zählt als Nachweis, nicht als Verstoß | #8 |
| Vier Aktionen an den Owner zurückgegeben, ohne die Werkzeuggrenze zu benennen | Bei einer Classifier-Sperre den Grund im selben Zug nennen, damit „dein Zug" nicht wie Vorsicht aussieht | #9 |
| Retro ohne fremden Kontext gefahren | Die Bewertungsbefunde (#1, #5) mit ihrem gemessenen Preis (~55k je Skeptiker) zur Freigabe vorlegen, statt die Lücke nur zu protokollieren | #10 |

## 5. Längsschnitt

`retro_kpis.py` über 107 Reports: **40 Slugs ≥2 ⇒ Gate-Pflicht**, davon 9 ohne registriertes Gate. Aus dieser Sitzung wiederkehrend:

| Slug | Zähler | Lage in dieser Sitzung |
|---|---|---|
| `untested-command-handed-to-user` | ×4 (3 nach Gate-Bau) | 2× ausgelöst — siehe 5a |
| `claim-before-cheapest-check` | ×63 vor Gate-Bau | 4× ausgelöst, **jedes Mal gefangen und korrigiert** → `gates_caught` |
| `scope-checkpoint-not-durably-recorded` | wiederkehrend | ausgelöst, Checkpoint durabel abgelegt → `gates_caught` |
| `partial-fix-not-generalized-to-sibling-artifacts` | ×10, ohne Gate | Befund #7 gehört in diese Familie |

`refuted_rate`-Trend: `62f875:0.40 · 54195f:0.36 · 73073b:0.21 · effb03:0.17 · e016fe:0.00` — die letzten drei unter 0,2, das Werkzeug warnt „Falsifikation ist Theater". Dieser Report mit **0,0** setzt die Reihe fort und ist selbst ein Beleg dafür, nicht die Ausnahme.

## 5a. Rückfall-Prüfung

`gate_wirkung.py`: **`untested-command-handed-to-user` ist RÜCKFÄLLIG** — gebaut 2026-08-23 als `advisory`, davor 1 Vorkommen, **danach 3**, letzter Rückfall 2026-08-28. In dieser Sitzung feuerte es zweimal.

Der Befund ist damit nicht „Slug zum vierten Mal", sondern **„Gate rückfällig"**. Von den drei zulässigen Antworten passt hier **ausweiten**:

Beide Auslösungen betrafen denselben Befehl (`onboard_tenant`), dessen Ausführung der Permission-Classifier gesperrt hatte — zweimal versucht, zweimal abgelehnt. Das Gate unterscheidet nicht zwischen „nicht ausgeführt" und „nicht ausführbar". Solange es das nicht tut, erzeugt es bei jeder Classifier-Sperre einen Verstoß, den niemand vermeiden kann — und ein Gate, dem man nicht folgen kann, wird gelernt zu ignorieren. Vorschlag: Der Scanner akzeptiert eine im selben Turn dokumentierte Ablehnung (Classifier oder Hook) als Nachweis.

`gate-modul-prueft-weniger-als-sein-name` steht mit `zu-frueh` in der Registry — kein Wirksamkeitsbeleg.

## 5b. Autonomie-Kalibrierung

- `over_ask`: **0** belegt. Vier Rückgaben an den Owner waren Classifier-Sperren (#9), keine Vorsicht.
- `over_act`: **0** belegt. Der einzige Schreibzugriff außerhalb von meiki-hub (risk-hub-Mandant) wurde als Gate behandelt, mit Dry-Run vorbereitet und vom Owner ausgeführt.

## 6. Verankerung

**memory_candidates** (kopierfertig, nicht von mir geschrieben):

```markdown
---
name: schleusen-datei-erst-zuordnen
description: Dateien aus ~/shared/ ohne Zuordnung nicht in den laufenden Vorgang einbauen — erst fragen, wohin sie gehören
metadata:
  type: feedback
drift: true
drift_episode: 2026-09-01-netcup-avv-falsche-session
---

Eine Datei, die in `~/shared/` auftaucht, gehört nicht automatisch zum gerade offenen Vorgang.
Am 2026-09-01 wurde ein netcup-AVV als Antwort auf eine offene Vorfrage gelesen, vollständig
geprüft und als Kommentar an meiki-hub#148 gehängt — er gehörte zu einer anderen Sitzung. Der
Kommentar musste gelöscht werden.

**Why:** Der Zusammenhang war plausibel und deshalb unauffällig falsch. Plausibilität ist die
teuerste Form der Fehlzuordnung, weil sie keine Prüfung auslöst.

**How to apply:** Vor der ersten inhaltlichen Prüfung einer Schleusen-Datei eine Zeile Rückfrage,
wohin sie gehört. Siehe [[erhebung-zuerst-inbox-pruefen]].
```

```markdown
---
name: formatierer-zerstoert-handgesetztes-json
description: json.dumps auf handformatierte Konfigdateien macht den Diff unlesbar — Textedit statt Roundtrip
metadata:
  type: feedback
---

`module-manifest.json` in meiki-hub ist handgesetzt spaltenausgerichtet. Ein `json.load`/`json.dumps`-
Roundtrip für einen einzigen neuen Eintrag erzeugte **202 geänderte Zeilen**; nach Rücknahme und
chirurgischem Textedit waren es **15**.

**Why:** Die Datei war nach dem Roundtrip gültig — die Prüfung „JSON ok" bestand, der Schaden lag
in der Reviewbarkeit.

**How to apply:** Prüfgröße nach einem strukturellen Edit ist der **Diff-Umfang**, nicht die
Gültigkeit. Bei handgesetzter Formatierung: gezielter Textersatz.
```

**adr_candidates:** keine. Kein Befund dieser Sitzung berührt eine Architekturentscheidung; alles ist Werkzeug- oder Prozessebene (`adr-threshold.md`).

## 7. Maßnahmen

### 🔵 Offen — ich kann sofort

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 1 | Verlustkontrolle als Sweep-Schritt | platform | — | 🔵 ready | in Skill aufnehmen (ich) |

### 🟢 Offen — dein Zug

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| 2 | Gate um „Ausführung gesperrt" erweitern | platform | gate-registry | 🟢 offen | Scanner anpassen (du) |
| 3 | Zwei Memory-Kandidaten verankern | dotclaude | §6 | 🟢 offen | übernehmen (du) |
| 4 | Mandant in Prod statt nur Staging | risk-hub | — | 🟢 offen | entscheiden (du) |
| 5 | Falsifikation der Bewertungsbefunde | platform | #1, #5 | 🟢 offen | ~110k freigeben (du) |

## 8. Nicht verifiziert (Restlücken)

| Lücke | Billigster Check |
|---|---|
| **Keine Falsifikation, kein fremder Kontext.** Regel 1 gebrochen — die Find-Phase lief inline aus dem Sitzungsgedächtnis. Betroffen sind vor allem die Bewertungsbefunde #1, #5, #10 | Zwei eng geführte Sonnet-Skeptiker auf #1 und #5, ~55k je (gemessen) |
| Ob der `--import-dir`-Zweig von `onboard_tenant` idempotent ist | `dsb/import_csv.py` lesen |
| Ob das DSB-Mandat in Prod fehlt oder dort schon anders heißt | `onboard_tenant --dry-run` gegen Prod |
| Ob die acht Bestandsmodule nach dem CSS-Nachtrag wirklich anders rendern | Screenshot-Vergleich eines Fristen-Screens vor/nach |
| Ob das Juli-Schreiben inhaltlich noch weitere überholte Angaben enthält | Zeilenvergleich `schreiben-lra-dsb-gesamt.md` gegen die Matrix v0.4 |

**Der Vierer:**

- **getan:** 13 PRs gemergt, 4 stille Melder repariert, Datenschutz-Strang abgeschlossen, KD-Kette vorführbar, ADR-Frontmatter 36/36, alle zehn offenen Session-Start-Befunde abgelegt.
- **angenommen:** dass die Auskünfte zum Betriebsort und zum HNU-Zugriff belastbar sind — sie tragen den gesamten Entfall der Anzeigepflicht.
- **nicht verifizierbar:** die Bewertungsbefunde ohne fremden Kontext; der Prod-Zustand des Mandats.
- **offen geblieben:** #165 (drei VVT-Felder), zwei interne Schreiben-Entwürfe, Mandant in Prod, Gate-Erweiterung.
