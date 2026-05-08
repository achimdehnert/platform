# Embedder Service Spike (ADR-188)

> Validiert die Annahmen aus ADR-188 E2: multilingual-e5-large auf Hetzner CPU.

## Ziel

| Metrik | Budget | Quelle |
|--------|--------|--------|
| RAM | ≤ 3 GB | ADR-188 §7 Trade-offs |
| Latenz (p50, single text) | ≤ 100ms | ADR-188 §E2 |
| Recall@1 (German legal) | ≥ 80% | ADR-188 §9 Confirmation #5 |
| Model Load Time | ≤ 60s | Akzeptabel für Container-Start |

## Quick Start

```bash
# Build (dauert ~10 min wegen Model-Download)
docker compose build

# Start
docker compose up -d

# Warten bis Model geladen (check logs)
docker compose logs -f embedder

# Health check
curl http://localhost:8100/healthz/

# Benchmark
pip install numpy  # lokal für Recall-Test
python benchmark.py --url http://localhost:8100 --rounds 50
```

## Auf Hetzner deployen

```bash
# Auf Prod-Server (88.198.191.108)
cd /opt/embedder-spike
git clone --depth 1 --filter=blob:none --sparse \
  https://github.com/achimdehnert/platform.git .
git sparse-checkout set spikes/embedder-service
cd spikes/embedder-service
docker compose up -d --build

# Benchmark vom Dev Desktop
python benchmark.py --url http://88.198.191.108:8100
```

## API

| Endpoint | Method | Beschreibung |
|----------|--------|-------------|
| `/embed` | POST | Texte embedden (max 100 pro Request) |
| `/livez/` | GET | Liveness (immer 200) |
| `/healthz/` | GET | Readiness (Model geladen?) |
| `/info` | GET | RAM, CPU, Model-Details |

### POST /embed

```json
{
  "texts": ["Der Arbeitgeber hat Schutzmaßnahmen zu treffen."],
  "prefix": "passage: "
}
```

**Wichtig:** E5-Modelle brauchen Prefix:
- `"passage: "` für Ingest (Dokumente die gespeichert werden)
- `"query: "` für Search (Suchanfragen)

### Response

```json
{
  "embeddings": [[0.012, -0.034, ...]],
  "model": "intfloat/multilingual-e5-large",
  "dimensions": 1024,
  "elapsed_ms": 45.2,
  "count": 1
}
```

## Entscheidung nach Spike

| Ergebnis | Aktion |
|----------|--------|
| Alle Budgets eingehalten | ✅ ADR-188 Phase 1 starten |
| RAM > 3.5 GB | halfvec oder kleineres Modell evaluieren |
| Latenz > 100ms p50 | GPU-Option prüfen oder async Batch-Only |
| Recall < 80% | Alternatives Modell (BGE-M3, nomic-embed-text) |
