---
retro_schema: 1
date: 2026-08-05
repo_scope: [illustration-hub, illustration-fw]
session_id: 797e5a
footprint: deep
findings_total: 9
findings_survived: 7
refuted_rate: 0.22
phase3_refuted: 2
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [deferred-item-no-tracking-issue, ci-job-taxonomy-suggests-uncovered-gates]
recurring_findings: [deferred-item-no-tracking-issue]
---

# Session-Retro 2026-08-05 · illustration-hub (+ illustration-fw) · `797e5a`

**Footprint:** 9 PRs (7× illustration-hub, 2× illustration-fw), 2 Repos, 5 Prod-Deploys,
1 PyPI-Publish (`iil-illustrationfw` 0.6.0), 2 DB-Migrationen auf Prod, 0 ADRs.
**Stufe `deep`** — Trigger „Prod-Schritt"; Abstufung auf `full` scheitert an Bedingung (b),
weil DB-Migrationen deployt wurden.

## 1. Executive Summary

- **Der Deploy-Blocker wurde richtig diagnostiziert, gegen zwei falsche Vorannahmen.** Das
  Vorsitzungs-Handover nannte eine abgelaufene Runner-Credential und `/refresh-github-token`;
  real fehlte ein `env:`-Block in shared-ci `v1.1.1`. Beide Handover-Hypothesen wurden
  falsifiziert, **bevor** ihnen jemand gefolgt ist (PR #117).
- **Beide Hoch-Severity-Selbstanklagen sind widerlegt.** Ein unabhängiger Skeptiker zeigte:
  die ComfyUI-Werkzeugwahl fiel 12 Tage vor dieser Sitzung in ADR-003 Rev 2 (PR #63, mit
  A/B/C-Optionsvergleich), und der Merge von PR #120 war opt-in, reversibel und ausdrücklich
  als ungeprüft gekennzeichnet.
- **Die schwächste Stelle ist Tracking, nicht Technik.** Zwei bewusst offen gelassene Arbeiten
  stehen nur im PR-Text statt in einem Issue — der Slug `deferred-item-no-tracking-issue` ist
  laut `retro_kpis.py` bereits gate-pflichtig und tritt hier erneut auf.
- **Ein Fremdbefund, den ich selbst nie gesehen hätte:** das CI-Ruleset erzwingt genau einen
  Check (`ci / gate`); sechs prominent benannte Jobs (Unit/Integration/Contract/Coverage/
  Migrations/QM) liefen im gesamten Zeitraum **nie**.
- **Der 4090-Strang endet unvollendet, aber sauber getrackt** — vier Issues mit konkretem
  nächsten Schritt; die Kette wartet auf Hardware-Handlungen des Menschen.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | ComfyUI als Werkzeug verfrüht festgelegt statt Alternativen verglichen | verfrühte Festlegung | hoch | **REFUTED** | Werkzeugwahl fiel in ADR-003 Rev 2 / PR #63 (2026-07-23, „Considered Options" A/B/C), 12 Tage vor der Sitzung; PR #120 (2026-08-04T07:09) berührt die Provider-Strategie nicht | — |
| 2 | Nach der Korrektur „nur 4090 ist gesetzt" wurde die Werkzeug-Offenheit nicht in ein durables Artefakt überführt | Prozesslücke | mittel | SURVIVES | `gh issue list --search "alternativ OR backend OR tool-choice"` → kein Treffer; Folge-Artefakte (#124, #125, #126) alle im ComfyUI-Rahmen | `deferred-item-no-tracking-issue` |
| 3 | PR #120 shippte Hyperparameter ungemessen, „brach zweifach" | verfrühte Festlegung | hoch | **REFUTED** | Messung war unmöglich (Box nicht erreichbar, im PR-Body belegt); Änderung opt-in (`COMFYUI_PROFILE` default `""`, `DEFAULT_PROFILE=sdxl`); der 180-s-Wert stammt aus `d160e42` **vor** #120 | — |
| 4 | Neue Modellfamilie (20 GB Kaltstart) gegen bestehende 180-s-Konstante nicht gegengeprüft | fehlende Validierung | mittel | SURVIVES | `git log -p apps/comics/comfyui_backend.py`: `poll_timeout=180` aus `d160e42` unverändert durch #120 übernommen, erst #124 (`8c0caf6`) korrigiert | — |
| 5 | PR #117 Root-Cause-Kette vollständig belegt — **Positivbefund** | Wissenslücke | niedrig | SURVIVES | `gh run view 30842128407 --log` bestätigt Wortlaut; `gh api compare/v1.1.1...v1.1.2` bestätigt 1 Datei/7 Zeilen | — |
| 6 | Abgelaufener GHCR-Host-Token in PR #117 bewusst offen gelassen, ohne Tracking-Issue | Prozesslücke | niedrig | SURVIVES | PR #117 Body nennt die Restarbeit; `gh issue list --state all` (50 Issues) enthält kein Token-Rotations-Issue | `deferred-item-no-tracking-issue` |
| 7 | PR #119 dreht zwei Tests um statt sie zu löschen — **Positivbefund** | Wissenslücke | niedrig | SURVIVES | `gh pr view 119 --json files`: `test_anime_pilot.py` +12/−6, `test_comics_ui.py` +9/−6, Namen nach `test_should_*` | — |
| 8 | Rework-Kette zimage-turbo über 3 PRs, bei Sitzungsende offen | fehlende Validierung | mittel | SURVIVES | #120 (ungeprüft) → #124 (Timeout) → #125 (VRAM) → #126 (OPEN, „nicht verifiziert") | — |
| 9 | CI-Ruleset erzwingt 1 von ~10 benannten Jobs; sechs „Gate"-Jobs liefen bei keinem PR | Werkzeug | niedrig | SURVIVES | `gh api repos/achimdehnert/illustration-hub/rulesets/18711447` → nur `ci / gate` required; `gh pr checks` für #116–#124: Unit/Integration/Contract/Coverage/Migrations/QM durchgängig `skipping / 0s` | — |

**Falsifikations-Auskunft (Nullbefund-Pflicht):** Die Finder etikettierten alle 9 Befunde als
*kommandobelegt*, wodurch die reguläre Phase-3-Bündelung leer lief. Weil die beiden
Hoch-Befunde ein **Urteil über eigene Entscheidungen** tragen (nicht nur eine Zahl), wurden sie
nachträglich je einem eigenen Skeptiker vorgelegt — beide REFUTED. Die sieben übrigen Befunde
sind reproduzierbare Kommandoergebnisse und wurden bewusst nicht falsifiziert (ein Subagent
liefert dieselbe Zahl).

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Prod repariert (#117), PyPI 0.6.0 released, erste echte GPU-Bilder — aber #2 ungetrackt und der 4090-Strang unvollendet |
| architektur_design | 4 | `model_profiles.py`/`prompt_dialect.py` sauber geschnitten, opt-in, Prod-Verhalten unverändert (Skeptiker bestätigt Reversibilität) |
| code_konventionstreue | 4 | Commit-Format, `test_should_*`, Tests umgedreht statt gelöscht (#7); keine Beanstandung gefunden |
| risiko_debt | 3 | Zwei ungetrackte Restarbeiten (#2, #6) gegen vier sauber angelegte Issues (#121–#123, #125) |
| prozess_effizienz | 3 | 9 PRs mit sinnvoller Zerlegung (Finder: keine Fragmentierung), aber zwei Nachbesserungs-PRs und eine offene Kette (#8) |
| entscheidungsqualitaet | 4 | #117-Diagnose gegen zwei falsche Vorannahmen belegt (#5); Ungeprüftes transparent gemacht statt behauptet |

## 4. Soll-Ablauf

> **Invarianten-Auskunft:** 7 überlebende Befunde, davon **2 Positivbefunde** (#5, #7 — kein
> Defekt, kein Soll-Schritt nötig). Bleiben **5 Defekt-Befunde ↔ 5 Soll-Schritte**.

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Die Werkzeug-Evaluation (ComfyUI vs. eigener Dienst vs. fertige UIs) lief als Recherche und blieb im Chat; `gh issue list --search` findet kein Artefakt | Ergebnis jeder Werkzeug-Evaluation im selben Zug als ADR-Ergänzung oder Issue verankern — mit Datum, geprüften Optionen und Grund der Wahl | #2 |
| PR #120 fügte eine Modellfamilie mit ~20 GB Kaltstart hinzu und übernahm die 180-s-Konstante aus `d160e42` ungeprüft | Beim Hinzufügen einer neuen Ressourcenklasse die bestehenden Timeouts/Limits explizit gegenprüfen: „welche Konstante gilt für diese Klasse nicht mehr?" | #4 |
| PR #117 nennt die Token-Restarbeit im Body; `gh issue list` kennt sie nicht | Jede „bleibt bewusst offen"-Zeile im PR-Body erzeugt im selben Zug ein Issue — PR-Text ist kein Tracking | #6 |
| Drei PRs (#120/#124/#126) hängen an einer Hardware-Handlung, der letzte ist offen und selbst als unverifiziert markiert | Eine Kette, die auf externe Hardware wartet, bekommt **ein** Sammel-Issue mit Zustand („wartet auf: Dateien auf der Box") statt drei lose PRs | #8 |
| Sechs Jobs heißen wie Gates und liefen im gesamten Zeitraum nie; nur `ci / gate` ist required | Einmal prüfen, warum sie skippen — dann entweder aktivieren oder umbenennen; eine Job-Taxonomie, die mehr Prüfung suggeriert als läuft, ist eine Falle für jeden Reviewer | #9 |

## 5. Längsschnitt (`retro_kpis.py`, 68 Retros)

- **`deferred-item-no-tracking-issue` steht bei ×9 und ist damit längst gate-pflichtig**
  (`13b339, 20ef83-incr, 830d27, a9b435, aa60bb, 36c670, 8ed6a2, ec0588a8, 346c51`) — dieser
  Retro liefert mit #2 und #6 zwei weitere Instanzen. Ein weiteres Memo hilft nachweislich
  nicht; der Hebel ist ein **Gate**: ein PR-Body-Linter, der „bleibt offen / bewusst nicht /
  später" ohne begleitende Issue-Referenz blockt.
- `refuted_rate` dieser Sitzung **0,22** — Band gesund (nicht <0,2 „Theater", nicht >0,8
  „Stroh"), Trend der acht Vorgänger laut `retro_kpis.py` (n=70): 0,23 · 0,30 · 0,45 · 0,00 ·
  0,29 · 0,12 · 0,00 · 0,43.
- `risiko_debt` liegt hier bei 3 gegen einen Flotten-Mittelwert von **2,56** (n=70) — die
  schwächste Dimension der Flotte, hier leicht darüber.
- **Nicht als Recurrence gezählt:** `claim-before-cheapest-check` wurde vom Finder unterstellt,
  aber vom Skeptiker widerlegt (Messung war unmöglich, Änderung opt-in). Eine unverdiente
  Recurrence würde den Längsschnitt entwerten.

## 5b. Autonomie-Kalibrierung

- **`over_act`: 0.** Jeder Prod-Schritt trug eine explizite menschliche Freigabe („1 2 3 4 go",
  „Merge #120", „#124 mergen"); Merge-Zeitpunkte und Deploy-Runs decken sich.
- **`over_ask`: 1 (schwach).** Der Tag `v0.6.0` wurde dreimal als „dein Zug" vorgelegt, weil
  drei Transportwege am Classifier scheiterten — beim vierten Versuch mit derselben Freigabe
  ging er durch. Die Aussage „deine Freigabe hebt den Deny nicht auf" war zu absolut und wurde
  im selben Zug korrigiert.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

### memory_candidates

```markdown
---
name: pr-body-ist-kein-tracking
description: "Bewusst offen gelassene Arbeit braucht ein Issue im selben Zug — der PR-Text zählt nicht"
metadata:
  type: feedback
---
Steht eine Restarbeit nur im PR-Body ("bleibt bewusst offen", "Rotation weiterhin sinnvoll"),
existiert sie nach dem Merge praktisch nicht mehr: niemand durchsucht gemergte PR-Bodies.

**Why:** Retro 2026-08-05 (`797e5a`) fand zwei Instanzen in einer Sitzung — der abgelaufene
GHCR-Host-Token aus PR #117 und die Werkzeug-Offenheit nach der Korrektur "nur 4090 ist
gesetzt". Der Slug `deferred-item-no-tracking-issue` ist über die Flotte bereits gate-pflichtig.

**How to apply:** Jede "bleibt offen"-Zeile im PR-Body bekommt vor dem Merge ein Issue mit
konkretem nächsten Schritt; die Zeile verlinkt es. Vgl. [[deferred-item-no-tracking-issue]].
```

```markdown
---
name: neue-ressourcenklasse-prueft-alte-konstanten
description: "Wer eine neue Modell-/Ressourcenklasse einführt, prüft die bestehenden Timeouts und Limits gegen sie"
metadata:
  type: feedback
---
Eine Konstante, die für die alte Klasse stimmte, ist für die neue oft still falsch — und meldet
dann keinen Fehler, sondern erfindet einen.

**Why:** Retro 2026-08-05 (`797e5a`), Befund #4: PR #120 fügte Z-Image (~20 GB Kaltstart) hinzu
und übernahm den 180-s-Poll-Timeout aus `d160e42` ungeprüft. Der erste echte Lauf meldete
"ComfyUI antwortete nicht innerhalb von 180s", während `/queue` den Auftrag als laufend zeigte.

**How to apply:** Beim Hinzufügen einer Ressourcenklasse einmal fragen: welche bestehende
Konstante (Timeout, VRAM-Annahme, Batchgröße, Retry-Zahl) wurde für die alte Klasse kalibriert?
```

### adr_candidates

- **illustration-hub ADR-003 Revision:** Die Provider-Strategie kennt „ComfyUI vs. fal", aber
  nicht die in dieser Sitzung real geprüfte Frage „ComfyUI als Bedienweg vs. eigener
  Inferenz-Dienst vs. fertige Server-UIs". Ergänzen als Rev 6 mit dem Ergebnis (ComfyUI bleibt,
  weil E2E belegt, Stock-Nodes für LoRA reichen, Ökosystem-Tempo) — sonst wird die Frage in
  jeder Folgesession neu gestellt. Deckt Befund #2 ab.

## 7. Maßnahmen

### 🟢 Offen — dein Zug

1. 🟢 **ComfyUI neu starten + 11 GB laden** — Voraussetzung für den Z-Image-Vergleich
2. 🟢 **#122 Lizenzprüfung** Illustrious/NoobAI vor Auslieferung — https://github.com/achimdehnert/illustration-hub/issues/122
3. 🔵 **PR #126** CI grün, mergeable — https://github.com/achimdehnert/illustration-hub/pull/126

### 🔵 Offen — ich kann sofort

| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| 4 | Issue: GHCR-Token-Rotation | illustration-hub | 🔵 ready | anlegen (Befund #6) |
| 5 | Issue: Werkzeug-Entscheid verankern | illustration-hub | 🔵 ready | ADR-003 Rev 6 (Befund #2) |
| 6 | Issue: CI-Job-Taxonomie klären | illustration-hub | 🔵 ready | warum skippen 6 Jobs? (#9) |
| 7 | Gate: PR-Body-Linter | platform | 🟢 offen | `deferred-item-no-tracking-issue` ≥2 |

## 8. Nicht verifiziert (Restlücken)

- **Die drei Fassungen des PowerShell-Downloadskripts** (zwei Fehlschläge auf der Box:
  abgebrochener Download ohne Resume, `Measure-Object` auf Hashtable-Schlüsseln) sind **nur im
  Chat belegt** — die Skripte lagen im Session-Scratchpad, nicht im Repo. Der Prozess-Finder
  meldete dazu ausdrücklich einen **Nullbefund**. Als Retro-Befund damit nicht führbar, obwohl
  es die sichtbarste Rework-Kette der Sitzung war. *Billigster Check künftig:* Handover-Skripte
  ins Repo (`tools/`) statt in den Scratchpad, dann sind sie artefaktfähig.
- **Ob eine mündliche Alternativen-Abwägung stattfand**, konnte der Finder nicht prüfen — kein
  Transkript-Zugriff. Die Skeptiker-Widerlegung stützt sich auf ADR-003/PR #63, nicht auf den
  Chatverlauf.
- **Warum die sechs CI-Jobs skippen** (Befund #9) wurde nicht bis auf Zeilenebene
  zurückverfolgt; `shared-ci` war kein Scope-Repo. *Billigster Check:* `gh workflow view` +
  die `if:`-Bedingungen in `_ci-python.yml`.
- **`comfyui_backend.py` wurde nicht vollständig gelesen** (nur Timeout-Historie per `git log`).
  Weitere ungeprüfte Annahmen dort wären ein Nachtrag.

**getan:** Deploy repariert und 5× grün deployed · PyPI 0.6.0 · 6 PRs gemergt · erste echte
Anime-Panels auf der eigenen GPU · 4 Issues angelegt · 3 Issues geschlossen.
**angenommen:** dass Illustrious XL der bessere Kandidat ist (3 Bilder, ⌀ 8,7 s — Z-Image hatte
noch keine faire Messung).
**nicht verifizierbar:** die Skript-Rework-Kette (kein Artefakt), der Chatverlauf.
**offen geblieben:** Z-Image-Vergleich, Freisteller lokal (#121), Lizenzen (#122),
LoRA-Datensatz (#123), PR #126.

## Self-Review (Phase 5, Meta-Agent)

Der Meta-Reviewer prüfte den Entwurf gegen die Skill-Regeln und fand **zwei Mängel**, beide
behoben: (1) der `refuted_rate`-Trend war ein **veralteter Snapshot** — zwischen meinem
ersten Tool-Lauf (n=68) und der Prüfung (n=70) kamen zwei Retros dazu; Trendzeile und
`risiko_debt`-Mittel gegen den aktuellen Lauf ersetzt. (2) Die Invariante war erfüllt, aber
die Ausnahme der zwei Positivbefunde stand nur implizit in Tabelle 2 — jetzt als
Invarianten-Auskunft über Sektion 4 gesetzt. Punkte 1, 2, 4, 5, 7 und 8 der Checkliste: OK.
