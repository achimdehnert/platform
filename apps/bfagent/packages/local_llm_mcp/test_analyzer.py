#!/usr/bin/env python3
"""
Test script for Local LLM Analyzer

Usage (from bfagent root):
    # In WSL with Ollama running:
    python packages/local_llm_mcp/test_analyzer.py docs/

    # Or with specific model:
    python packages/local_llm_mcp/test_analyzer.py docs/ --model mistral
"""

import sys
import json
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    analyze_docs_for_redundancy_sync,
    analyze_docs_freshness_sync,
    get_file_info,
    OLLAMA_AVAILABLE,
    DEFAULT_MODEL
)


def test_file_info():
    """Test file info extraction."""
    print("=" * 60)
    print("TEST: File Info Extraction")
    print("=" * 60)
    
    test_file = Path(__file__).parent.parent.parent / "docs" / "README_STANDARDIZATION.md"
    
    if test_file.exists():
        info = get_file_info(test_file)
        print(f"File: {info.get('name')}")
        print(f"Title: {info.get('title')}")
        print(f"Size: {info.get('size_bytes')} bytes")
        print(f"Modified: {info.get('modified')}")
        print(f"Doc Date: {info.get('doc_date')}")
        print(f"Word Count: {info.get('word_count')}")
        print("✅ File info extraction works!")
    else:
        print(f"⚠️ Test file not found: {test_file}")
    
    print()


def test_ollama_connection():
    """Test Ollama connection."""
    print("=" * 60)
    print("TEST: Ollama Connection")
    print("=" * 60)
    
    if not OLLAMA_AVAILABLE:
        print("❌ Ollama package not installed")
        print("   Install with: pip install ollama")
        return False
    
    try:
        import ollama
        result = ollama.list()
        
        # Handle both dict and object responses
        models_list = result.get('models', []) if isinstance(result, dict) else getattr(result, 'models', [])
        model_names = []
        for m in models_list:
            if hasattr(m, 'model'):
                model_names.append(m.model)
            elif isinstance(m, dict):
                model_names.append(m.get('name') or m.get('model'))
        
        print(f"✅ Ollama is running!")
        print(f"   Available models: {model_names}")
        print(f"   Default model: {DEFAULT_MODEL}")
        
        if DEFAULT_MODEL not in model_names:
            print(f"\n⚠️ Default model '{DEFAULT_MODEL}' not found!")
            print(f"   Pull it with: ollama pull {DEFAULT_MODEL}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("   Is Ollama running? Try: ollama serve")
        return False
    
    print()


def test_redundancy_analysis(docs_path: str, model: str = DEFAULT_MODEL):
    """Test redundancy analysis."""
    print("=" * 60)
    print("TEST: Redundancy Analysis")
    print("=" * 60)
    
    print(f"Analyzing: {docs_path}")
    print(f"Model: {model}")
    print("This may take 30-60 seconds...")
    print()
    
    result = analyze_docs_for_redundancy_sync(
        docs_path=docs_path,
        model=model,
        max_files=30  # Smaller for quick test
    )
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    # Print summary
    metadata = result.get("_metadata", {})
    print(f"✅ Analysis complete!")
    print(f"   Files scanned: {metadata.get('files_scanned')}")
    print(f"   Model used: {metadata.get('model_used')}")
    
    # Print findings
    summary = result.get("analysis_summary", {})
    print(f"\nFindings:")
    print(f"   Redundant groups: {summary.get('redundant_groups_found', 'N/A')}")
    print(f"   Outdated candidates: {summary.get('outdated_candidates_found', 'N/A')}")
    
    # Show some examples
    redundant = result.get("redundancy_candidates", [])
    if redundant:
        print(f"\nExample redundancy groups:")
        for group in redundant[:3]:
            print(f"   - {group.get('group_name')}: {group.get('files', [])[:3]}")
    
    outdated = result.get("outdated_candidates", [])
    if outdated:
        print(f"\nOutdated candidates:")
        for item in outdated[:5]:
            print(f"   - {item.get('file')}: {item.get('reason', 'N/A')[:50]}")
    
    # Save full result
    output_file = Path(docs_path) / "_redundancy_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to: {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Local LLM Analyzer")
    parser.add_argument("docs_path", nargs="?", help="Path to docs folder")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model")
    parser.add_argument("--skip-ollama", action="store_true", help="Skip Ollama test")
    
    args = parser.parse_args()
    
    print("\n🔍 LOCAL LLM ANALYZER TEST\n")
    
    # Test 1: File info
    test_file_info()
    
    # Test 2: Ollama connection
    if not args.skip_ollama:
        ollama_ok = test_ollama_connection()
        print()
        
        if not ollama_ok:
            print("⚠️ Skipping analysis test due to Ollama issues")
            return
    
    # Test 3: Redundancy analysis
    if args.docs_path:
        test_redundancy_analysis(args.docs_path, args.model)
    else:
        print("💡 To test analysis, provide a docs path:")
        print("   python test_analyzer.py /path/to/docs")


if __name__ == "__main__":
    main()
