---
concept_id: KONZ-platform-068
title: Robuste Modell- und Prompt-Vergleiche — mehrere Vorlagen, Streuung berichten, Einstellungen offenlegen
pipeline_status: idea
tier: T2                   # bedingt — T3, sobald die Regeln für alle Repos verbindlich werden (Policy-Änderung, Screener nach ADR-223)
owner: Achim Dehnert
spec_refs: []              # kein Klickdummy/Spec-Bezug — Mess-Methodik, keine ADR-211-Anwendung
adr_threshold: kein ADR    # Regeln = Abschnitt in einer bestehenden Policy; Amendment an ADR-223 erst, wenn der Screener gebaut wird (Frage F2)
review_by: 2027-01-31
kill_criteria: "Liefern die zwei Pilot-Nachmessungen (§9) bis 2026-12-31 in keinem Fall eine andere Entscheidung als der Ein-Vorlagen-Lauf UND ist in beiden die Vorlagen-Spanne kleiner als der halbe Abstand der Kandidaten, schrumpft der Vorschlag auf R5 (Einstellungen offenlegen); R1–R4 entfallen."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: "https://arxiv.org/html/2606.29228v2 (Volltext, Tab. 1, Tab. 3, §3.2, §4.2, §5)", commit_or_pr: "arXiv v2, 2026-07-01", opened_in_session: true}
  - {claim_id: C2, source_path: "https://arxiv.org/abs/2310.11324 (Abstract)", commit_or_pr: "Sclar et al.", opened_in_session: true}
  - {claim_id: C3, source_path: "https://arxiv.org/abs/2401.00595 (Abstract)", commit_or_pr: "Mizrahi et al.", opened_in_session: true}
  - {claim_id: C4, source_path: "dev-hub:experiments/prerouter/REPORT.md (Z. 45–80)", commit_or_pr: "Stand 2026-10-13", opened_in_session: true}
  - {claim_id: C5, source_path: "iil-voice-agent:docs/ — Ratifizierungs-Doku des Sprachassistenten (Z. 28, 112, 163–164)", commit_or_pr: "Stand 2026-10-13", opened_in_session: true}
  - {claim_id: C6, source_path: "writing-hub:docs/konzepte/messungen/README.md (Z. 8, 89–100, 131, 170–216)", commit_or_pr: "Stand 2026-10-13", opened_in_session: true}
  - {claim_id: C7, source_path: "ttz-hub:services/aifw_service/aifw_service/nl2sql_routing.lokal.json (_comment)", commit_or_pr: "dc6709a", opened_in_session: true}
  - {claim_id: C8, source_path: "docs/konzepte/KONZ-platform-063-technologiescreening-aus-der-morgen-zeitung.md §5.9b", commit_or_pr: "0c437ae1", opened_in_session: true}
  - {claim_id: C9, source_path: "docs/adr/ADR-223-llm-model-screener.md (status, P5, Phase 3+4)", commit_or_pr: "0c437ae1", opened_in_session: true}
  - {claim_id: C10, source_path: "docs/adr/ADR-302-routing-entkoppeln-statt-lernen.md (status, Auslöser)", commit_or_pr: "0c437ae1", opened_in_session: true}
  - {claim_id: C11, source_path: "~/.claude/policies/llm-routing.md (Rule, Tier list, Verfügbarkeit, Preise)", commit_or_pr: "Stand 2026-10-13", opened_in_session: true}
  - {claim_id: C12, source_path: "Inventur-Teilagent über ~/github (25 Fundstellen, Tabelle §2)", commit_or_pr: "Lauf 2026-10-13", opened_in_session: false}
created: 2026-10-13
---

# KONZ-platform-068 — Robuste Modell- und Prompt-Vergleiche

> Auftrag: [#3883](https://github.com/achimdehnert/platform/issues/3883), Owner-Freigabe 2026-10-13.
> Anlass: Zhang, Ren, Xie, Wei, *Understanding Evaluation Illusion in Diffusion Large Language
> Models*, arXiv 2606.29228v2. **Keine Umsetzung** — dieses Dokument schlägt Regeln vor und
> listet die nächsten Schritte.
>
> **Tier T2, bedingt.** T2, weil das Konzept eine neue Konvention vorschlägt, die mehrere Repos
> beträfe (Auto-Eskalations-Trigger Cross-Repo). **Nicht T3, solange** nichts davon verbindlich
> wird: Weder eine Policy noch ein Gate noch ein Werkzeug ändert sich durch dieses Dokument. Wer
> die Regeln in eine Policy schreibt oder den Screener aus ADR-223 baut, hebt sichtbar auf T3.
>
> Evidenz: `E4` = externe Quelle, in dieser Sitzung gelesen. `E2` = Datei in dieser Sitzung
> geöffnet. `H` = Hypothese bzw. nur vom Inventur-Teilagenten gelesen (C12).

## Kernthese

Ein Vergleich, der jeden Kandidaten mit genau einer Prompt-Vorlage misst, misst die Vorlage mit
— liegt die Streuung über Vorlagen in derselben Größenordnung wie der Abstand der Kandidaten,
ist die Rangfolge Zufall. Deshalb gehören zu jedem entscheidungsrelevanten Vergleich mindestens
drei Vorlagen, eine berichtete Spanne und offengelegte Einstellungen. Ein Abstand innerhalb der
Spanne heißt „unentschieden“, und dann entscheiden Kosten und Latenz.

## 1 Auswertung des Papers (Akzeptanz 1)

### 1.1 Was gemessen wurde (E4, C1)

| Achse | Inhalt |
|---|---|
| Modelle | LLaDA-8B-Instruct, LLaDA-1.5 — beide **Diffusions**-Sprachmodelle, eine Familie |
| Verglichen | Decodierverfahren: Vanilla (ein Token je Schritt) gegen sechs parallele Verfahren (Fast-dLLM, AdaBlock, dKV-Cache, Elastic-Cache, WINO …) |
| Aufgaben | GSM8K, MATH500 (Mathematik); Code-Benchmarks nur im Anhang |
| Vorlagen | Haupttabellen: 6 Vorlagen für GSM8K, 2 für MATH500. Sensitivität: 8 fast identische (A–H, ein Wort oder Zeichen anders), 8 semantisch gleiche, 5 Chain-of-Thought-Stufen |
| Weitere Achsen | Few-Shot 0–4, Generierungslänge, GPU-Typ, FP32 gegen niedrigere Präzision |

### 1.2 Befunde mit Zahlen (E4, C1 — am Originaltext geprüft)

| # | Befund | Beleg |
|---|---|---|
| P1 | Die Rangfolge der Verfahren wechselt mit der Vorlage. Mittlere paarweise Kendall-τ über Vorlagen: **0,539** (LLaDA-8B) und **0,495** (LLaDA-1.5). | §3.2 |
| P2 | Schon die Basislinie schwankt über die sechs GSM8K-Vorlagen von **71,72 bis 77,33** — 5,6 Punkte bei unverändertem Modell und Verfahren. | Tab. 1 |
| P3 | Bei fast identischen Vorlagen streut Vanilla mit σ = 0,355 (Spanne 1,07), Top-K k = 4 mit σ = 1,142 (Spanne 3,79). Das Verfahren mit dem schwächsten Mittelwert ist auch das empfindlichste. | Tab. 3 |
| P4 | Bei semantisch gleichen Vorlagen erreicht Vorlage H 78,47 % in 48 Schritten, Vorlage G 67,85 % in 57 Schritten — **10,62 Punkte** Abstand bei vergleichbarem Rechenaufwand. Die Vorlage wiegt mehr als die Stellschraube, die eigentlich verglichen wird. | §4.2 |
| P5 | Gleiche Einstellungen, andere GPU → abweichende Ergebnisse; unter FP32 liegen L40 und A100 fast gleich. | §4, Anh. D.3 |
| P6 | Literaturlage: Für dasselbe Modell und dasselbe Verfahren berichten verschiedene Studien GSM8K-Werte, die um bis zu 9 Punkte auseinanderliegen. Die Zahl stammt aus zitierten Arbeiten, nicht aus eigener Messung. | §1 |
| P7 | Empfehlungen der Autoren: über mehrere Vorlagen berichten, auf gleicher Hardware oder in FP32 messen, alle Einstellungen offenlegen (Vorlage, Parameter, Länge, Hardware). | §5 |

### 1.3 Grenzen

| Grenze | Art |
|---|---|
| Eine Modellfamilie, zwei Mathe-Benchmarks im Hauptteil | vom Paper nicht als Grenze benannt, aus dem Aufbau abgeleitet |
| Die Sensitivitätsläufe zeigen keine Wiederholungen; Seeds und Laufzahl je Zelle sind im Text nicht ausgewiesen | `H`, Anhang nicht vollständig gelesen |
| Die Wortwahl ist teils stärker als die Zahlen („substantially“ für 0,76 Punkte, „consistently underperform“ trotz Few-Shot-Ausnahmen in Tab. 4) | eigene Lesart |
| Die Erklärung (Abhängigkeitskonflikte beim parallelen Decodieren) ist eine Deutung, kein getesteter Mechanismus | eigene Lesart |
| Die Autoren schreiben selbst, ein systematischer Bewertungsrahmen bleibe offen | §5/Anh. A |
| Keine Aussage über autoregressive Modelle | Paper bleibt bei Diffusions-LLMs |

### 1.4 Was übertragbar ist und was nicht

Unsere Vergleiche betreffen **autoregressive** Modelle über gehostete Schnittstellen (Groq,
Cerebras, Anthropic, OpenAI) oder lokales Ollama, auf kleinen Eigen-Datensätzen
(Klassifikation, Routing, NL2SQL, Zusammenfassung, Stilurteil). Die Übertragung stützt sich
deshalb weniger auf dieses Paper allein als auf zwei ältere Arbeiten zu autoregressiven Modellen.
Sclar et al. (E4, C2) messen bis zu **76 Punkte** Unterschied allein durch Formatierung
(LLaMA-2-13B, Few-Shot), und die Format-Leistung korreliert zwischen Modellen nur schwach. Ein
Modellvergleich mit einer willkürlich gewählten festen Vorlage ist damit methodisch fragwürdig.
Mizrahi et al. (E4, C3) zeigen über 20 Modelle und 39 Aufgaben, wie brüchig Ein-Prompt-Rangfolgen
sind, und fordern Multi-Prompt-Auswertung.

| Paper-Befund | Übertragbar? | Begründung |
|---|---|---|
| P1/P2 Rangfolge hängt an der Vorlage | **ja, im Kern** | Der statistische Kern — Vorlagen-Streuung gegen Kandidaten-Abstand — gilt unabhängig von der Architektur; für autoregressive Modelle durch C2/C3 eigenständig belegt |
| P3 Schwächere Verfahren sind empfindlicher | **als Hypothese** | Bei uns unbelegt. Plausibel für kleine Modelle (T1b) gegen große; das wäre selbst eine Messfrage (F5) |
| P4 Vorlage schlägt Stellschraube | **ja, sinngemäß** | Bei uns heißt die Stellschraube Modell oder Anbieter. Eine bessere Vorlage kann den Modellwechsel ersetzen, und dann ist die billige Lösung die richtige |
| P5 Hardware-Nichtdeterminismus, FP32 | **nur das Prinzip** | Bei gehosteten Schnittstellen haben wir keinen Einfluss auf Hardware und Präzision. Das Analogon ist Nichtdeterminismus trotz `temperature=0`, bei uns schon beobachtet (E2, C5: lokales Ollama, gleicher Fall, einmal korrekt, einmal verweigert). Folge: Wiederholungen statt FP32 |
| Decodierverfahren, Entrausch-Schritte, Parallel-Decoding | **nein** | Diffusions-spezifisch; keiner unserer Vergleiche berührt das |
| Absolute Zahlen (GSM8K-Genauigkeit) | **nein** | Andere Modelle, andere Aufgaben |
| P7 Empfehlungen | **ja, angepasst** | Die drei Empfehlungen bilden §4 R1, R2 und R5; ergänzt um Wiederholungen (R3) und eine Entscheidungsregel (R4), die das Paper nicht hat |

Was bei uns **zusätzlich** wiegt und im Paper nicht vorkommt: Unsere Stichproben sind klein
(19 bis 80 Fälle). Dazu kommt oft ein LLM als Richter, dessen eigene Vorlage eine zweite
Template-Abhängigkeit einführt.

## 2 Bestandsaufnahme: wo wir heute mit einer Vorlage vergleichen (Akzeptanz 2)

Quelle: Inventur über alle lokalen Repos am 2026-10-13 (C12). Die mit `E2` markierten Zeilen
habe ich selbst geöffnet, die übrigen sind `H`. Nur entscheidungsrelevante Vergleiche, keine
reinen Erreichbarkeitsprüfungen.

| # | Ort | Verglichen | Vorlagen je Arm | Streuung berichtet | Einstellungen offen | Ev. |
|---|---|---|---|---|---|---|
| B1 | dev-hub `experiments/prerouter/` | Anbieter als Vorrouter-Stufe (Groq, Cerebras, lokales Modell) | 1 Systemprompt | nein, ein Lauf, Median | teils, nur im Code | E2 (C4) |
| B2 | iil-voice-agent, Ratifizierungs-Doku | Groq-Modell gegen lokales Modell, Antwortqualität und Trefferquote | 1 | **nein, ausdrücklich „Streuung ungemessen“** | ja (`temperature=0`) | E2 (C5) |
| B3 | iil-voice-agent, Latenz-Benchmark | 3 Groq-Modelle × 2 Spracherkenner | 1 | Latenz ja, Qualität ein Wert (75 gegen 81 % = ein Fall) | teils | H |
| B4 | ttz-hub, NL2SQL-Modellwahl | Gehostetes gegen lokales Modell, **19/19 gegen 18/19** | 1 | nein | teils, nur für die gewählte Konfiguration | E2 (C7) |
| B5 | writing-hub `docs/konzepte/messungen/` | Prompt-Bausteine A/B auf einem Modell | 1 je Arm | **ja: drei Runden je Arm, Kriterium vorab, Holdout** | teils, Temperatur fehlt | E2 (C6) |
| B6 | writing-hub, Overlay-Vergleich mit LLM-Richter | zwei Prompt-Overlays, Richter-Modell | 1 je Arm | ja (3, dann 6 Runden); Richter selbst instabil | teils | H |
| B7 | writing-hub, Stil-Blindvergleich | 3 Modelle, Stilanalyse | 1, eine Probe je Modell | nein | nein | H |
| B8 | platform `KONZ-platform-063` §5.9b | 4 Prompt-Varianten auf T1a | 4 Varianten, je 1 Lauf | nein | teils | E2 (C8) |
| B9 | platform `tools/pypi_coldstart_llm_eval.py` | kein Vergleich, Eignungsnachweis T1a (19/19) | 1 | nein, Doppellauf offen | teils | H |
| B10 | mcp-hub, Routing-Outcomes | Erfolgsquote je Modell aus Live-Verkehr | Live-Verkehr | nur Quote, `--min-n` | – | H |
| B11 | Policy `llm-routing` | Behauptet „gleichwertige Qualität bei mechanischen Aufgaben“ für T1 | – | – | belegt sind nur Verfügbarkeit und Preise, **keine Qualitätsmessung** | E2 (C11) |
| B12 | Policy `session-routing` | Modellstufen für Sitzungen, „reicht für …“ | – | – | Ausgabenschnappschuss, keine Qualitätsmessung | H |
| B13 | platform ADR-223 (Screener), ADR-302 (Kosten/Qualität), ADR-068/095 | Geplante Benchmark-Mechanik | – | geplant | – | E2 (C9, C10) für 223/302 |

**Muster.**

- **Nirgends wird eine Modell-Rangfolge gegen eine zweite Formulierung geprüft.** Modellvergleiche
  halten die Vorlage fest und tauschen das Modell (B1–B4, B7). Prompt-Vergleiche halten das Modell
  fest und geben jedem Arm genau eine Vorlage (B5, B6, B8).
- **Ein-Fall-Abstände werden als Signal gelesen:** 19/19 gegen 18/19 (B4) und 75 gegen 81 % (B3).
  Bei n = 19 liegt ein Fall Abstand tief im Rauschen. B4 wurde zusätzlich nach der Latenz
  entschieden (0,7 s gegen 7,8 s), und dieser Abstand trägt die Entscheidung auch ohne
  Qualitätsvorsprung (E2, C7). Die Entscheidung bleibt richtig, ihre Begründung im Kommentar ist
  aber stärker formuliert als belegt.
- **Gute Praxis gibt es schon, in einem Repo:** Die writing-hub-Messungen (B5) machen drei Runden je
  Arm, legen das Kriterium vor dem Lauf fest und prüfen am Holdout. Das ist das interne Vorbild für
  R3 und R4. Was dort fehlt, ist die zweite Vorlage je Arm.
- **Die Routing-Policy behauptet eine Qualitätsrangfolge ohne Qualitätsmessung** (B11). Das ist kein
  Fehler der Policy, deren Kern eine Kostenregel ist. Es zeigt aber, dass kein Vergleich die
  Tier-Leiter je unter Vorlagen-Variation geprüft hat.

## 3 Steelman — warum Ein-Vorlagen-Vergleiche bisher vertretbar waren

- **Wir vergleichen für einen Einsatz, nicht für eine Bestenliste.** Die Produktionsvorlage *ist*
  das, was später läuft. Ein Modell, das mit genau dieser Vorlage gut ist, ist für diesen Zweck gut.
- **Die meisten Entscheidungen trägt nicht die Qualität, sondern Kosten, Latenz oder
  Souveränität** (B1 Latenz, B4 Latenz, die ttz/meiki-Regel Souveränität). Ein Qualitätsrauschen
  ändert daran wenig.
- **Jede Variation vervielfacht die Kosten** (3 Vorlagen × 3 Läufe = 9×), und das bei Messungen,
  die heute oft nebenbei in einer Sitzung entstehen.
- **Die Rücknahme ist billig:** Routing-Einträge sind Konfiguration; eine falsche Wahl wird beim
  nächsten Fehlerbild korrigiert.

Das Steelman hält für **Einsatz-Entscheidungen mit klarem Kosten- oder Latenzabstand**. Es hält
nicht, sobald (a) ein Ergebnis als Regel verallgemeinert wird („T1 ist gleichwertig“, B11),
(b) die Produktionsvorlage sich danach ändert, was bei Prompt-Arbeit der Normalfall ist, oder
(c) der Qualitätsabstand die Entscheidung allein trägt. Genau für diese drei Fälle sind die
Regeln gedacht.

## 4 Vorschlag: Mindestregeln und Prüfverfahren (Akzeptanz 3)

### 4.1 Geltungsbereich

Die Regeln gelten für einen Vergleich, **dessen Ergebnis eine Entscheidung trägt**: Modell- oder
Anbieterwechsel, Routing-Eintrag, Prompt-Freigabe oder ein Satz in einer Policy bzw. einem ADR.
Sie gelten nicht für Erreichbarkeitsprüfungen (Liveness), reine Latenzmessungen und explorative
Läufe, die als solche gekennzeichnet sind.

### 4.2 Mindestregeln

| ID | Regel | Herkunft |
|---|---|---|
| **R1** | **Mindestens drei Vorlagen je Kandidat:** V0 = Produktionsvorlage, V1 = lexikalische Paraphrase (gleiche Struktur, andere Wörter), V2 = Formatvariante (andere Anordnung, Trenner oder Beschreibung des Ausgabeformats, gleiche Bedeutung). Bei Prompt-Vergleichen gilt dasselbe je Arm: V1 und V2 werden aus jeder Fassung abgeleitet. | Paper P1/P4, Sclar (C2) |
| **R2** | **Streuung berichten:** je Kandidat Mittelwert und Spanne über die Vorlagen, dazu die Rangfolge **je Vorlage**. Ein Gesamtwert ohne Spanne gilt nicht als Ergebnis. | Paper P7 |
| **R3** | **Wiederholen:** mindestens drei Läufe je Zelle (Kandidat × Vorlage), wenn `temperature > 0` oder der Anbieter nicht deterministisch ist. Bei `temperature = 0` mindestens ein Wiederholungslauf, der den Nichtdeterminismus misst. Berichtet wird Median [min–max]. | B2/C5, B5 als internes Vorbild |
| **R4** | **Entscheidungsregel, vor dem Lauf festgelegt:** Kandidat A gilt nur dann als besser, wenn er (a) in **jeder** Vorlage mindestens gleichauf und in der Mehrheit vorn liegt **und** (b) sein Mittelwert-Abstand größer ist als die größte Vorlagen-Spanne beider Kandidaten. Ein Abstand von einem Fall ist nie ein Befund. Sonst lautet das Ergebnis „kein belegter Qualitätsunterschied“, und es entscheiden Kosten, Latenz und Souveränität. Das ist der Standardpfad der Routing-Policy. | eigene Setzung (D), Alternative in §7 |
| **R5** | **Einstellungen offenlegen** im Ergebnis-Dokument, nicht nur im Code: exakte Modell-ID und Anbieter, Datum, `temperature`, `max_tokens` bzw. `num_predict`, Vorlagen-Texte oder deren Hash mit Ablageort, Anzahl der Fälle, Läufe je Zelle, Richter-Modell samt Richter-Vorlage, Kriterium vor dem Lauf. | Paper P7 |
| **R6** | **Richter sind Kandidaten zweiter Ordnung:** Bewertet ein LLM, gilt R1 auch für die Richter-Vorlage (mindestens zwei Fassungen), oder die Übereinstimmung des Richters mit sich selbst über Wiederholungen wird berichtet. | B6 (Richter instabil), eigene Ableitung |

### 4.3 Prüfverfahren „Vorlagen-Stresstest“ (klein, ein Durchgang)

Ablaufform nach Skill-Schritt 2a: **feste Kette, parallel je Zelle, keine Schleife.** Die
Schrittfolge steht vorher fest, die Zellen sind unabhängig, und eine Schleife mit Abbruch ist
nicht nötig.

1. **Steckbrief vor dem Lauf** (R4, R5): Kriterium, Kandidaten, Fälle, Einstellungen. Muster:

   ```yaml
   vergleich:
     frage: "<welche Entscheidung trägt das Ergebnis>"
     kandidaten: ["<anbieter/modell-id>", "<anbieter/modell-id>"]
     vorlagen: {V0: "<pfad|hash>", V1: "<pfad|hash>", V2: "<pfad|hash>"}
     faelle: {anzahl: <n>, quelle: "<pfad>", holdout: <ja|nein>}
     einstellungen: {temperature: <x>, max_tokens: <x>, laeufe_je_zelle: <r>}
     richter: {modell: "<id|keiner>", vorlagen: ["<pfad|hash>"]}
     kriterium: "<vorab festgelegt, R4>"
     datum: <YYYY-MM-DD>
   ```

2. **V1 und V2 ableiten:** einmal von Hand oder per T1-Modell paraphrasieren, dann von Hand prüfen,
   dass die Bedeutung gleich bleibt. Die Varianten werden neben V0 abgelegt und wiederverwendet.
3. **Lauf:** Kandidaten × Vorlagen × Läufe.
4. **Ergebnistabelle:** eine Zeile je Kandidat, Spalten V0, V1, V2 als Median [min–max], dazu
   Mittelwert, Spanne und Rang je Vorlage.
5. **Urteil nach R4:** „A besser“, „B besser“ oder „kein belegter Unterschied“, mit einem Satz,
   welche Bedingung entschieden hat.

**Kosten (Rechnung, keine Messung):** Gegenüber dem heutigen Einzellauf fallen 9 statt 1
Durchläufe an (3 × 3), bei `temperature = 0` 6 statt 1 (3 Vorlagen × 2 Läufe). Bei n = 50,
angenommen 1.000 Token Eingabe und 500 Token Ausgabe je Fall, und T1a-Preisen (C11) sind das
450 Aufrufe für rund 0,30 US-Dollar je Kandidat. Bei T3- bis T5-Kandidaten bestimmt der
Faktor 6–9 den Preis, deshalb Frage F4.

### 4.4 Wo die Regeln leben sollen (SSoT-Prüfung)

Kein neues Dokument und kein neues Gate. Zwei bestehende Orte kommen in Frage, und ein dritter
erzeugte eine zweite Wahrheit:

- **Policy `llm-routing`, Abschnitt „Vergleiche“:** R1–R6 als Kurzregel und der Steckbrief als
  Muster. Dort lesen alle, die eine Modellwahl begründen. Empfehlung.
- **ADR-223 (Screener, Status proposed, Umsetzung keine — E2, C9):** Falls der Screener gebaut wird,
  übernimmt seine Benchmark-Suite R1–R6 als Anforderung. Das wäre ein Amendment, kein neuer ADR.
- **Nicht** als eigenes Methodik-Dokument in `docs/governance/`. Das wäre eine dritte Stelle neben
  Policy und ADR und würde ohne Leser veralten.

## 5 Ledger

| id | Aussage | Typ | Evidenz/Falsifikation | Status |
|---|---|---|---|---|
| L1 | Vorlagen-Streuung kann den Kandidaten-Abstand übersteigen | Annahme | E4 (C1 P1–P4, C2, C3); bei uns ungemessen | offen bis Pilot |
| L2 | Unsere Stichproben sind zu klein, um Ein-Fall-Abstände zu deuten | Annahme | B3, B4 (n = 19 bis 80); bei n = 19 und p ≈ 0,95 beträgt die Binomial-Standardabweichung ≈ 1 Fall | belegt (E2 B4) |
| L3 | `temperature = 0` ist bei uns nicht deterministisch | Annahme | E2 (C5), ein Fall bei lokalem Ollama; für gehostete Anbieter `H` | teilweise belegt |
| L4 | R4 als Entscheidungsregel statt Signifikanztest | Entscheidung (D) | Alternative §7 A2; R4 ist ohne Statistik-Werkzeug prüfbar | vorgeschlagen |
| L5 | Regeln leben in der Routing-Policy, nicht in einem neuen Dokument | Entscheidung (D) | §4.4; Alternative: eigenes Governance-Dokument | vorgeschlagen, Frage F1 |
| L6 | Der Aufwand (Faktor 6–9) ist für T1-Kandidaten vernachlässigbar | Annahme | Rechnung §4.3; Messung beim Pilot | offen |
| R-a | Regeln werden formal erfüllt, praktisch umgangen (V1/V2 als triviale Kopien) | Risiko | §8 | offen |

## 6 Befunde inkl. Advocatus Diabolus und Maintainer 2028

| id | Befund | Konsequenz |
|---|---|---|
| D1 | **Diabolus — Scheinpräzision:** Drei Vorlagen sind keine Verteilung. Mit K = 3 ist die „Spanne“ selbst grob, und R4 kann zufällig bestehen. | R4 ist absichtlich streng (jede Vorlage, Abstand > Spanne), damit Zufall eher „unentschieden“ ergibt als einen falschen Sieger. Ein Fehler in Richtung „unentschieden“ ist billig, weil dann die Kostenregel greift. |
| D2 | **Diabolus — Regel ohne Durchsetzung:** Der Vorschlag ist eine Lese-Regel. Nichts hindert einen Routing-PR mit Ein-Vorlagen-Begründung. | Ehrlich: Das ist zunächst ein Review-Gate, kein Exit-Code. Ein Prüfer, der Ergebnis-Dokumente auf den Steckbrief prüft, ist ein möglicher Folgeschritt (N6), kein Teil dieses Konzepts. |
| D3 | **Diabolus — formale Erfüllung:** V1 = V0 mit einem Komma mehr erfüllt R1 und misst nichts. | V2 muss eine **Format**-Variante sein. In der Prüfung von Schritt 2 fragt man, ob ein Mensch beide Fassungen für unterschiedlich formuliert hält. Bleibt eine Ermessensfrage (R-a). |
| D4 | **Diabolus — zweite Wahrheit:** Policy und ADR-223 könnten beide Regeln führen. | §4.4: Die Policy führt, ADR-223 verweist. |
| D5 | **Maintainer 2028:** Die Modell-IDs der Policy sind dann veraltet (die Llama-Familie fiel schon 2026-08 weg, C11), und alte Vergleiche ohne Steckbrief sind nicht nachvollziehbar. | R5 (exakte ID und Datum im Ergebnis) ist der Teil, der auch 2028 noch Wert hat. Deshalb bleibt R5 auch im Kill-Fall. |
| D6 | **Maintainer 2028:** Gehostete Anbieter ändern Modelle hinter gleicher ID. | R5 verlangt das Datum, der Steckbrief ist wiederholbar. Ein Nachlauf mit gleichem Steckbrief zeigt die Drift. |

## 7 Alternativen

| id | Alternative | Warum nicht (jetzt) |
|---|---|---|
| A1 | **Status quo plus Offenlegung:** nur R5, keine Vorlagen-Variation | Billigster Weg und der Rückfall im Kill-Fall. Er macht Vergleiche nachvollziehbar, aber nicht belastbarer; die Illusion aus P1 bleibt. |
| A2 | **Statistischer Test statt R4** (Bootstrap-Konfidenzintervall oder McNemar je Vorlage) | Methodisch sauberer, braucht aber ein Werkzeug und Lesekompetenz für das Ergebnis. Bei n = 19 bis 80 trennt auch ein Test selten. Sinnvoll, sobald der Screener (ADR-223) eine Auswertung hat (N5). |
| A3 | **Vorlagen-Optimierung je Modell** (jedes Modell bekommt seine beste Vorlage, Sclar-Ansatz) | Vergleicht Bestfall gegen Bestfall, was für Einsatz-Entscheidungen fair ist. Kostet aber eine Suche je Modell und gehört in die Prompt-Arbeit, nicht in die Mindestregel. Offene Frage F6. |

## 8 Top-3-Risiken

| # | Risiko | Gegenmittel |
|---|---|---|
| 1 | Die Regeln verteuern kleine Entscheidungen so, dass Vergleiche gar nicht mehr stattfinden und nach Gefühl entschieden wird | Geltungsbereich §4.1 eng halten; im Zweifel A1 (nur R5) |
| 2 | Formale Erfüllung (D3) | V2 als Formatvariante verpflichtend; Stichprobe im Pilot |
| 3 | R4 erklärt fast alles für „unentschieden“, und damit greift immer die Kostenregel | Gewollt, solange die Kostenregel gilt. Wird es zum Problem, liefert der Pilot die Zahl dazu (Kill-Gate) |

## 9 Kill-Gate

**Pilot:** zwei bestehende Vergleiche nach §4.3 nachmessen, vorzugsweise B1 (Anbieter im
Vorrouter) und B8 (Prompt-Varianten, platform-intern). Die Auswahl ist Frage F3.

**Abbruchschwelle** (Frontmatter `kill_criteria`): Bis **2026-12-31** liefert keine der beiden
Nachmessungen eine andere Entscheidung als der Ein-Vorlagen-Lauf, **und** in beiden ist die
Vorlagen-Spanne kleiner als der halbe Kandidaten-Abstand. Dann schrumpft der Vorschlag auf R5,
R1–R4 entfallen. Exception-Budget: Fällt der Pilot bis 2026-12-31 aus, gilt das Konzept zum
`review_by` 2027-01-31 als `sunset`, wenn bis dahin kein Owner-Wort zur Verlängerung vorliegt.

| Kriterium | Status | Beleg |
|---|---|---|
| Pilot 1 nachgemessen (Entscheidung gleich oder anders) | offen | – |
| Pilot 2 nachgemessen (Entscheidung gleich oder anders) | offen | – |
| Spanne < ½ Abstand in beiden Piloten | offen | – |

## 10 Offene Fragen und nächste Schritte (Akzeptanz 4)

Keine Umsetzung in diesem Auftrag. Fragen an den Owner:

- **F1** Sollen R1–R6 als Abschnitt in die Policy `llm-routing` (Empfehlung §4.4) oder vorerst nur
  als Empfehlung in diesem Konzept stehen bleiben?
- **F2** Wird ADR-223 (Screener) weiterverfolgt? Wenn ja, als Amendment mit R1–R6 als Anforderung
  an die Benchmark-Suite.
- **F3** Welche zwei Vergleiche sind der Pilot? Vorschlag B1 und B8. B4 nur nach Klärung der
  Datenregeln für die ttz-lif-Org.
- **F4** Gilt R3 (drei Läufe) auch für Kandidaten ab T3, oder reicht dort ein Wiederholungslauf
  (Kostenfrage)?
- **F5** Soll die Hypothese aus P3 (schwächere Kandidaten sind vorlagen-empfindlicher) im Pilot
  mitgemessen werden? Das kostet nichts extra, wenn T1b unter den Kandidaten ist.
- **F6** Ist A3 (beste Vorlage je Modell) für Einsatz-Entscheidungen der fairere Maßstab als eine
  gemeinsame Vorlage?

Nächste Schritte, jeweils erst nach Owner-Wort:

- **N1** Pilot B1 nach §4.3 nachmessen, Ergebnis in die Tabelle §9.
- **N2** Pilot B8 ebenso.
- **N3** Je nach F1: Abschnitt „Vergleiche“ in der Policy `llm-routing`, mit Verweis auf dieses
  Konzept.
- **N4** Die Begründungs-Kommentare von B4 und B3 auf „kein belegter Qualitätsunterschied,
  entschieden nach Latenz“ anpassen. Die Entscheidung selbst ändert sich nicht.
- **N5** Je nach F2: Amendment ADR-223; A2 (Test statt R4) dort prüfen.
- **N6** Erst wenn der Pilot das Konzept trägt: einen Prüfer erwägen, der Ergebnis-Dokumente auf
  einen vollständigen Steckbrief prüft (Review-Gate → Exit-Code).

## Quellen

- Zhang, H., Ren, J., Xie, R., Wei, H.: *Understanding Evaluation Illusion in Diffusion Large
  Language Models.* arXiv 2606.29228v2, 2026. https://arxiv.org/html/2606.29228v2
- Sclar, M., Choi, Y., Tsvetkov, Y., Suhr, A.: *Quantifying Language Models' Sensitivity to
  Spurious Features in Prompt Design.* arXiv 2310.11324. https://arxiv.org/abs/2310.11324
- Mizrahi, M., Kaplan, G., Malkin, D., Dror, R., Shahaf, D., Stanovsky, G.: *State of What Art? A
  Call for Multi-Prompt LLM Evaluation.* arXiv 2401.00595. https://arxiv.org/abs/2401.00595
