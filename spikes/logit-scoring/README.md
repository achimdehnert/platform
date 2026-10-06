# Spike: Logit-Scoring statt Text-Klassifikation (platform#3650)

**Stand:** 2026-09-30 · **Empfehlung: vormerken** (Ollama-Nachbau), der Score-Weg selbst läuft schon über kev (#3337).

## Frage

Kann unser lokales Setup (Ollama auf der gx10) Klassifikation über Logit-Werte statt
über Textgenerierung, nach dem Muster von SGLangs `/v1/score`? Und ist das schneller
oder zuverlässiger als der heutige Text-Weg?

## 1 · Was die Server können (belegt)

| Server | Score-Endpunkt | Fundstelle |
|---|---|---|
| SGLang | ja, `POST /v1/score` („CausalLM (logprob-based) and SequenceClassification“) | `sglang/python/sglang/srt/entrypoints/http_server.py`, `v1_score_request` (main, 2026-09-30) |
| Ollama 0.33.2 (gx10) | **nein**; keine Route `/score`, kein `logit_bias`, keine Token-Allowlist | `ollama/server/routes.go` v0.33.2, Z. 1878–1926 (Routentabelle) |
| Ollama 0.33.2 (gx10) | **aber** `logprobs` + `top_logprobs` (0–20) in `/api/generate` und `/api/chat` | `ollama/api/types.go` v0.33.2, Z. 123–129, 173–179, 497–515 |
| kev (gx10, `127.0.0.1:8009`) | ja, `POST /v1/systemone`, Frage `choice` liefert `probabilities` je Option | `jaredpalmer/kev` README (Apache-2.0); Dienst läuft seit 2026-09-21 (#3337) |

Ollama 0.33.2 und das aktive kev sind auf der gx10 geprüft (`/api/version`,
`systemctl --user`). vLLM ist dort installiert, aber inaktiv (`vllm.service inactive`).

Damit lässt sich das Muster **nachbilden**: ein Token erzeugen (`num_predict: 1`), die
Top-20-Kandidaten lesen, die Wahrscheinlichkeit der Tokens, die ein Label-Präfix sind,
je Label summieren und nur über die Labels neu normieren (restricted softmax).
Grenze: Ollama liefert höchstens 20 Kandidaten, echte Logits aller Labels gibt es nicht.
Liegt ein Label außerhalb der Top 20, bekommt es 0.

## 2 · Messung

`messung.py` läuft auf der gx10 (stdlib, nur Standardbibliothek), `auswertung.py` wertet aus.
12 **erfundene** Mails, 4 Klassen (rechnung, termin, newsletter, anfrage), je Klasse 3 Fälle,
3 Runden, Aufwärmlauf vorab. Die Wege `text` und `logit` nutzen dasselbe Modell
(`qwen2.5:7b`) mit **demselben Prompt**, also unterscheidet sie nur die Auslesung.

| Weg | Treffer | p50 ms | min ms | max ms | instabile Fälle | p(Gold) je Fall, Runde 1 |
|---|---|---|---|---|---|---|
| text (heute) | 33/36 | 76.1 | 62.0 | 111.9 | 0 | — |
| logit (Ollama-Nachbau) | 33/36 | 28.9 | 26.8 | 30.9 | 0 | 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 1.00 0.00 |
| kev-4b (`choice`) | 36/36 | 69.1 | 68.2 | 70.7 | 0 | 0.99 0.96 0.45 0.98 0.99 0.98 0.99 0.98 0.90 0.95 0.95 0.73 |

Rohwerte: [`rohdaten-2026-09-30.jsonl`](rohdaten-2026-09-30.jsonl) (108 Messzeilen, 0 Fehler).

**Befunde:**

- **Schneller:** Der Logit-Weg braucht 2,6× weniger Zeit als der Text-Weg (p50 29 gegen 76 ms)
  und streut kaum (27–31 ms), weil genau ein Token entsteht.
- **Nicht zuverlässiger:** Die Antworten stimmen mit dem Text-Weg überein, auch im selben
  Fehler (Fall 12, „Rückfrage zu Ihrer Rechnung“ → rechnung). Kein Wunder: gleiches Modell,
  gleicher Prompt, deterministisch (`temperature: 0`).
- **Keine brauchbare Sicherheit:** Das Modell ist auf seinem ersten Token gesättigt. Selbst
  der Fehlgriff bekommt p = 1,00. Einen Schwellenwert oder eine Enthaltung („an einen Menschen“)
  kann man daran nicht festmachen. Das war der eigentliche Nutzen des Musters.
- **kev hat die Sicherheit:** Die zwei unscharfen Fälle liegen sichtbar tiefer (0,45 Abo-Abbuchung,
  0,73 Rückfrage), alle 12 Fälle sind richtig. kev ist ein darauf trainierter Adapter,
  kein bloßes Auslesen.

**Grenzen:** 12 Fälle sind eine Machbarkeitsprobe, keine Trefferquote. Ich habe die Fälle
selbst geschrieben, und die Klassen sind leicht. Belegt sind nur der Latenzunterschied
und die Sättigung. Über die Trefferquote sagt die Messung nichts Belastbares. Die größere
Messung mit kev auf echten Mails (544 Fälle, AUC 0,992) steht in #3337.

## 3 · Alternativen und Aufwand

| Alternative | Stand | Aufwand (grob) |
|---|---|---|
| Ollama-Logprobs-Wrapper (dieser Spike) | Funktion `restricted_softmax` in `messung.py` | ~0,5 PT bis zu einem wiederverwendbaren Helfer mit Tests |
| kev `/v1/systemone` | läuft, gemessen, Ausnahme in `hosts.yaml` bis 2026-12-01 | 0 PT Technik, offen ist die Betriebsentscheidung (#3337) |
| vLLM (installiert, inaktiv) | Logprobs über die OpenAI-Schnittstelle: **Hypothese**, hier nicht geprüft | ~0,5–1 PT, belegt ~36 GB, vorher Speicher auf der gx10 rechnen |
| SGLang `/v1/score` | Route im Code belegt, bei uns nicht installiert; Lauf auf aarch64/GB10 ungeprüft (**Hypothese**) | ~1–3 PT |

## 4 · Empfehlung: vormerken

- **Adaptieren**, wo Sicherheit gebraucht wird (Schwellen, Enthaltung): Das läuft schon über
  kev, siehe Rechnungs-Vorfilter aus #3337. Dieser Spike ändert daran nichts.
- **Vormerken:** Den Ollama-Nachbau lohnt es nur für reine Geschwindigkeit bei vielen kleinen
  Entscheidungen ohne Schwelle. Der heutige Text-Weg liegt aber schon bei 76 ms, der Gewinn
  ist also klein. Ein Anlass fehlt heute.
- **Verwerfen:** SGLang als zusätzlicher Server. kev deckt das Muster ab, und es läuft bereits.

Nicht Teil dieses Spikes: jede produktive Integration (Mail-Triage, chat-hub#157), Deploy,
Änderungen an bestehenden Klassifikationswegen.
