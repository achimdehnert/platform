#!/usr/bin/env python3
"""Run full documentation analysis."""
import json
import sys
sys.path.insert(0, '/home/dehnert/github/bfagent/packages')

from local_llm_mcp.server import analyze_docs_for_redundancy_sync

result = analyze_docs_for_redundancy_sync(
    '/home/dehnert/github/bfagent/docs',
    model='llama3:8b',
    max_files=100
)

output_file = '/home/dehnert/github/bfagent/docs/_full_analysis.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

meta = result.get('_metadata', {})
summary = result.get('analysis_summary', {})

print(f"Files scanned: {meta.get('files_scanned')}")
print(f"Files total: {meta.get('files_total')}")
print(f"Redundant groups: {summary.get('redundant_groups_found')}")
print(f"Outdated candidates: {summary.get('outdated_candidates_found')}")
print(f"Results saved to: {output_file}")
