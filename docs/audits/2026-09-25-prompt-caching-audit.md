# Prompt-Caching-Audit — eigene Anthropic-API-Aufrufe (2026-09-25)

Auftrag: [#3562](https://github.com/achimdehnert/platform/issues/3562). Gegenstand ist nur die
Cache-Hygiene (statischer Inhalt vor dynamischem, `cache_control` gesetzt). Modellwechsel sind
ausdrücklich nicht Teil des Auftrags.

## Vorgehen

- Alle nicht archivierten Repos der drei Orgs (achimdehnert, ttz-lif, meiki-lra) liegen lokal
  unter `~/github/` (Abgleich mit `gh repo list`: keine Lücke).
- Lokale Suche nach `anthropic.Anthropic(`, `AsyncAnthropic(`, `messages.create(`,
  `api.anthropic.com`, `from anthropic import` (Python/TS/JS/Shell, ohne `_ARCHIVED`, `_archive`,
  `vendor`, Tests), gegengeprüft mit `gh search code` über die drei Orgs.
- Schwellen für die kleinste cachebare Präfixlänge: Sonnet 4.5 → 1024 Tokens, Haiku 3.5 → 2048,
  Haiku 4.5 → 4096, Opus 5/5.5-Familie → 512. Unterhalb der Schwelle ist `cache_control` ein
  stiller No-op (keine Fehlermeldung, `cache_creation_input_tokens: 0`).

## Fundliste und Befund je Repo

| Repo · Datei | Art des Aufrufs | Befund |
|---|---|---|
| aifw · `src/aifw/service.py` | zentraler LLM-Weg der Hubs (LiteLLM) | **ok** — System-Prompt bekommt bei `anthropic/`-Modellen `cache_control` (mit Test) |
| odoo-hub · `addons{,_v19}/mfg_nl2sql/controllers/nl2sql_controller.py` | Raw HTTP, System = Regeln + DB-Schema, Frage in `messages` | **Lücke** — Reihenfolge stimmt, `cache_control` fehlt; Präfix über der Schwelle (s. u.) |
| platform, meiki-hub, ttz-hub · `.github/scripts/adr_dual_review.py` | SDK, kurzer System-Prompt, ADR-Text in `messages` | **ok (kein Hebel)** — System-Prompt ≈ 200 Tokens, weit unter 2048 (Haiku 3.5) |
| mcp-hub · `llm_mcp/providers/anthropic_provider.py` | generischer Durchreicher für `system` | **strukturelle Lücke, Wirkung offen** — kein `cache_control`-Pfad; Nutzen hängt von Aufrufern ab, nicht gemessen |
| bfagent · `apps/core/services/prompt_framework/adapters.py`, `apps/control_center/views_ai_config.py` | generischer Adapter / Test-Knopf im Admin | **kein Hebel belegt** — Einmal- und Testaufrufe, Prompt-Länge je Agent konfigurierbar |
| cad-hub · `apps/dxf/handlers/pdf_vision.py` | SDK, Bild + Anweisung, einmalig je Plan | **kein Hebel** — kein wiederkehrender Präfix |
| dev-hub · `apps/ai_config/services.py` | Verbindungstest, `max_tokens: 1` | **kein Hebel** |
| aifw · `liveness.py`, platform · `tools/secrets_pruefen.py`, mcp-hub · `scripts/check-model-liveness.py` | nur `/v1/models` bzw. Liveness | **nicht betroffen** |

## Lücken-Fund odoo-hub (NL2SQL)

Der System-Prompt besteht aus festen Regeln plus dem Schema-Kontext aus
`nl2sql.schema.table` (deterministisch sortiert: `_order = 'domain, name'` bzw.
`'sequence, name'`). Die Nutzerfrage steht in `messages` — die Reihenfolge ist also schon
richtig, es fehlt nur der Cache-Marker.

**Vorher/Nachher-Schätzung** (Schema aus `data/schema_metadata.xml`, 12 Tabellen, 59 Spalten,
Prompt mit dem Code aus `_build_system_prompt` nachgebaut):

| Domäne | Zeichen | Tokens (Schätzung 3–4 Z./Token) | cachebar mit Sonnet 4.5? |
|---|---:|---:|---|
| alle (Default `domain_filter='all'`) | 4977 | 1244–1659 | ja, knapp über 1024 |
| supply_chain | 1821 | 455–607 | nein |
| production | 2150 | 538–717 | nein |
| quality | 1864 | 466–621 | nein |

**Messlücke:** `messages.count_tokens` war nicht möglich — der lokal
hinterlegte Anthropic-Schlüssel wird mit 401 abgelehnt. Die Token-Zahlen sind deshalb eine
Zeichen-basierte **Schätzung**; ob der Default-Fall die 1024er-Schwelle tatsächlich reißt, belegt
erst `cache_read_input_tokens` im Betrieb. Echte Installationen mit mehr gepflegten Tabellen
liegen höher.

**Wirkung je Anfrage** (Sonnet 4.5: Eingabe 3 $/MTok, Cache-Read 0,1×, Cache-Write 1,25×, 5 min):
ungecacht ≈ 1450 × 3 $/MTok ≈ 0,0044 $; Treffer ≈ 0,0004 $; Ersparnis ≈ 0,004 $ je Treffer,
Mehrkosten ≈ 0,001 $ je Schreibvorgang. Lohnt ab der zweiten Anfrage binnen 5 Minuten.

**Fix-Vorschlag** (beide Addon-Stände, `_call_anthropic`):

```python
'system': [{
    'type': 'text',
    'text': system_prompt,
    'cache_control': {'type': 'ephemeral'},
}],
```

Dazu die Token-Summe ergänzen, sonst sinkt die geloggte Zahl scheinbar, weil gecachte Tokens
nicht mehr in `input_tokens` stehen:

```python
usage = data.get('usage', {})
tokens = (usage.get('input_tokens', 0) + usage.get('cache_creation_input_tokens', 0)
          + usage.get('cache_read_input_tokens', 0) + usage.get('output_tokens', 0))
```

Der PR im odoo-hub steht noch aus: Das Anlegen eines Branches dort wurde in dieser Sitzung vom
Rechte-Klassifikator abgelehnt (Kriterium 3 offen, Rückfrage im Auftrag).

## Kurzbericht Kostenwirkung org-weit

- Der Großteil der Hub-Aufrufe läuft über aifw und cacht bereits.
- Einziger belegter Hebel ist odoo-hub NL2SQL: rund 0,004 $ je Cache-Treffer. Bei
  angenommenen 1000 Anfragen im Monat mit Treffern sind das **unter 4 $/Monat**; das tatsächliche
  Volumen ist nicht erhoben.
- Die Senkung des Cache-Lesepreises bei Opus 5.5 (0,20 $/MTok) ändert daran nichts, solange kein
  Pfad auf Opus 5.5 läuft — und ein Modellwechsel ist nicht Teil dieses Auftrags.
- **Fazit:** Cache-Hygiene ist org-weit weitgehend in Ordnung. Die Kostenwirkung der offenen
  Lücken liegt im einstelligen Dollarbereich pro Monat.

## Nebenbefund (außerhalb des Auftrags)

`adr_dual_review.py` (platform, meiki-hub, ttz-hub) nutzt `claude-3-5-haiku-20241022`,
`pdf_vision.py` (cad-hub) nutzt `claude-3-opus-20240229` — beide Modelle sind laut
Anthropic-Modellliste abgekündigt. Im platform-Workflow läuft der KI-Teil ohnehin nicht: Der
Lauf vom 2026-09-25 06:03 UTC meldet `AI review: skipped | tokens=0+0` — `ANTHROPIC_API_KEY` ist
dort leer, der Job endet trotzdem grün. Modellwechsel und Schlüssel brauchen eine gesonderte
Freigabe — nachgehalten in [#3563](https://github.com/achimdehnert/platform/issues/3563).
