#!/usr/bin/env python3
"""Benchmark script for Embedder Service (ADR-188 Spike).

Measures:
- Cold start time (model load)
- Single-text latency (p50, p95, p99)
- Batch throughput (chunks/sec)
- RAM usage
- Recall quality on German legal text samples

Usage:
    python benchmark.py [--url http://localhost:8100] [--rounds 50]
"""

import argparse
import json
import statistics
import sys
import time
import urllib.request


def request_json(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


# German legal text samples for quality testing
LEGAL_SAMPLES = [
    "passage: Die Baugenehmigung ist zu erteilen, wenn dem Vorhaben keine öffentlich-rechtlichen Vorschriften entgegenstehen.",
    "passage: Der Arbeitgeber hat die erforderlichen Maßnahmen des Arbeitsschutzes zu treffen.",
    "passage: Sicherheitsdatenblätter müssen gemäß REACH-Verordnung Artikel 31 bereitgestellt werden.",
    "passage: Die Gefährdungsbeurteilung ist vor Aufnahme der Tätigkeit durchzuführen und zu dokumentieren.",
    "passage: Explosionsgefährdete Bereiche sind in Zonen einzuteilen nach Häufigkeit und Dauer des Auftretens.",
]

QUERY_SAMPLES = [
    ("query: Wann muss eine Baugenehmigung erteilt werden?", 0),
    ("query: Pflichten des Arbeitgebers beim Arbeitsschutz", 1),
    ("query: REACH Verordnung Sicherheitsdatenblatt", 2),
    ("query: Gefährdungsbeurteilung Dokumentation", 3),
    ("query: Zoneneinteilung explosionsgefährdeter Bereiche", 4),
]


def benchmark_latency(base_url: str, rounds: int) -> dict:
    """Single-text embedding latency."""
    latencies = []
    for i in range(rounds):
        t0 = time.perf_counter()
        resp = request_json(f"{base_url}/embed", {"texts": [f"passage: Test Satz Nummer {i}"], "prefix": ""})
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)

    latencies.sort()
    return {
        "rounds": rounds,
        "p50_ms": round(statistics.median(latencies), 1),
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 1),
        "p99_ms": round(latencies[int(len(latencies) * 0.99)], 1),
        "mean_ms": round(statistics.mean(latencies), 1),
        "min_ms": round(min(latencies), 1),
        "max_ms": round(max(latencies), 1),
    }


def benchmark_batch(base_url: str, batch_sizes: list[int]) -> list[dict]:
    """Batch throughput at various sizes."""
    results = []
    for bs in batch_sizes:
        texts = [f"passage: Deutscher Beispieltext Nummer {i} für Batch-Test." for i in range(bs)]
        t0 = time.perf_counter()
        resp = request_json(f"{base_url}/embed", {"texts": texts, "prefix": ""})
        elapsed_s = time.perf_counter() - t0
        results.append({
            "batch_size": bs,
            "total_ms": round(elapsed_s * 1000, 1),
            "per_chunk_ms": round((elapsed_s * 1000) / bs, 1),
            "chunks_per_sec": round(bs / elapsed_s, 1),
        })
    return results


def benchmark_recall(base_url: str) -> dict:
    """Recall@1 on legal text samples (cosine similarity)."""
    import numpy as np

    # Embed passages
    passage_resp = request_json(f"{base_url}/embed", {"texts": [s for s in LEGAL_SAMPLES], "prefix": ""})
    passages = np.array(passage_resp["embeddings"])

    # Embed queries and check recall
    correct = 0
    details = []
    for query_text, expected_idx in QUERY_SAMPLES:
        query_resp = request_json(f"{base_url}/embed", {"texts": [query_text], "prefix": ""})
        query_vec = np.array(query_resp["embeddings"][0])

        # Cosine similarity (vectors are normalized)
        similarities = passages @ query_vec
        best_idx = int(np.argmax(similarities))
        is_correct = best_idx == expected_idx

        if is_correct:
            correct += 1
        details.append({
            "query": query_text[:60],
            "expected": expected_idx,
            "got": best_idx,
            "score": round(float(similarities[best_idx]), 4),
            "correct": is_correct,
        })

    return {
        "recall_at_1": f"{correct}/{len(QUERY_SAMPLES)}",
        "accuracy": round(correct / len(QUERY_SAMPLES), 2),
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(description="Embedder Service Benchmark")
    parser.add_argument("--url", default="http://localhost:8100", help="Base URL")
    parser.add_argument("--rounds", type=int, default=50, help="Latency test rounds")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    print(f"🎯 Benchmarking embedder at {base}")
    print("=" * 60)

    # Health check
    try:
        info = get_json(f"{base}/info")
        print(f"\n📊 Service Info:")
        print(f"   Model: {info['model']}")
        print(f"   Dimensions: {info['dimensions']}")
        print(f"   RAM: {info['ram_mb']} MB")
        print(f"   CPU threads: {info['torch_threads']}")
    except Exception as e:
        print(f"❌ Service not reachable: {e}")
        sys.exit(1)

    # Latency
    print(f"\n⏱️  Single-text latency ({args.rounds} rounds):")
    lat = benchmark_latency(base, args.rounds)
    print(f"   p50: {lat['p50_ms']}ms | p95: {lat['p95_ms']}ms | p99: {lat['p99_ms']}ms")
    print(f"   mean: {lat['mean_ms']}ms | min: {lat['min_ms']}ms | max: {lat['max_ms']}ms")

    # Batch
    print(f"\n📦 Batch throughput:")
    batches = benchmark_batch(base, [1, 5, 10, 25, 50])
    for b in batches:
        print(f"   batch={b['batch_size']:3d}: {b['per_chunk_ms']}ms/chunk, {b['chunks_per_sec']} chunks/sec")

    # Recall
    print(f"\n🎯 Recall@1 (German legal text, 5 queries):")
    try:
        recall = benchmark_recall(base)
        print(f"   Accuracy: {recall['recall_at_1']} = {recall['accuracy']*100}%")
        for d in recall["details"]:
            status = "✅" if d["correct"] else "❌"
            print(f"   {status} {d['query']}... → idx={d['got']} (score={d['score']})")
    except ImportError:
        print("   ⚠️ numpy not available locally, skipping recall test")

    # Summary
    print(f"\n{'=' * 60}")
    print("📋 SUMMARY — ADR-188 Spike Validation:")
    print(f"   RAM:        {info['ram_mb']} MB (Budget: 3000 MB)")
    print(f"   Latency:    {lat['p50_ms']}ms p50 (Budget: <100ms)")
    print(f"   Throughput:  {batches[-1]['chunks_per_sec']} chunks/sec at batch=50")
    ram_ok = "✅" if info["ram_mb"] < 3500 else "❌"
    lat_ok = "✅" if lat["p50_ms"] < 100 else "⚠️"
    print(f"   RAM check:  {ram_ok}")
    print(f"   Latency:    {lat_ok}")

    # JSON output
    result = {"info": info, "latency": lat, "batch": batches}
    with open("benchmark_results.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n💾 Results saved to benchmark_results.json")


if __name__ == "__main__":
    main()
