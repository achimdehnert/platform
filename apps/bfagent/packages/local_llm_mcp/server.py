"""
Local LLM Analyzer MCP Server

Ein MCP-Server der lokale LLMs (Ollama) für Dokumentations-Analyse nutzt.
READ-ONLY Operationen - keine Dateien werden verändert.

Usage:
    python -m local_llm_mcp.server
    
Requires:
    - Ollama running locally (ollama serve)
    - Model loaded (ollama pull llama3:8b)
"""

import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("Warning: MCP not installed. Install with: pip install mcp")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: Ollama not installed. Install with: pip install ollama")


# Configuration
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MAX_FILES = 100  # Limit for PoC
MAX_PREVIEW_CHARS = 500


def extract_title(content: str) -> str:
    """Extract H1 title from Markdown content."""
    for line in content.split('\n')[:15]:
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return "Untitled"


def extract_date_from_content(content: str) -> Optional[str]:
    """Extract date from document content (Status, Date, Datum fields)."""
    patterns = [
        r'\*\*Date:\*\*\s*(.+)',
        r'\*\*Datum:\*\*\s*(.+)',
        r'\*\*Status:\*\*.*(\d{4}-\d{2}-\d{2})',
        r'Date:\s*(.+)',
        r'Datum:\s*(.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, content[:1000], re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def get_file_info(file_path: Path) -> dict:
    """Get metadata and preview for a single file."""
    try:
        stat = file_path.stat()
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        return {
            "path": str(file_path),
            "name": file_path.name,
            "title": extract_title(content),
            "preview": content[:MAX_PREVIEW_CHARS],
            "size_bytes": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "doc_date": extract_date_from_content(content),
            "word_count": len(content.split()),
        }
    except Exception as e:
        return {
            "path": str(file_path),
            "name": file_path.name,
            "error": str(e)
        }


def build_redundancy_prompt(files: list) -> str:
    """Build analysis prompt for redundancy detection."""
    # Simplify file info for prompt
    simplified = []
    for f in files:
        simplified.append({
            "name": f.get("name"),
            "title": f.get("title"),
            "preview": f.get("preview", "")[:200],
            "doc_date": f.get("doc_date"),
        })
    
    return f"""Analyze these documentation files for redundancy and outdated content.

FILES ({len(simplified)} total):
{json.dumps(simplified, indent=2, ensure_ascii=False)}

TASK:
1. Group files with similar titles or overlapping topics
2. Identify potential duplicates or redundant content
3. Flag outdated files based on:
   - Naming patterns like V1, V2, V3, SESSION_, PHASE_
   - Dates older than 6 months
   - Content mentioning "deprecated", "old", "obsolete"

OUTPUT FORMAT (respond ONLY with valid JSON):
{{
  "analysis_summary": {{
    "total_files": {len(files)},
    "redundant_groups_found": <number>,
    "outdated_candidates_found": <number>
  }},
  "redundancy_candidates": [
    {{
      "group_name": "<descriptive name for the group>",
      "files": ["file1.md", "file2.md"],
      "similarity_reason": "<why these are similar>",
      "suggestion": "consolidate|archive|keep",
      "priority": "high|medium|low"
    }}
  ],
  "outdated_candidates": [
    {{
      "file": "<filename>",
      "reason": "<why it's outdated>",
      "suggestion": "archive|review|delete"
    }}
  ],
  "structure_issues": [
    {{
      "issue": "<description>",
      "affected_files": ["file1.md"],
      "suggestion": "<fix>"
    }}
  ]
}}"""


def build_freshness_prompt(files: list) -> str:
    """Build analysis prompt for freshness check."""
    simplified = []
    for f in files:
        simplified.append({
            "name": f.get("name"),
            "title": f.get("title"),
            "modified": f.get("modified"),
            "doc_date": f.get("doc_date"),
            "word_count": f.get("word_count"),
        })
    
    return f"""Analyze these documentation files for freshness and currency.

FILES ({len(simplified)} total):
{json.dumps(simplified, indent=2, ensure_ascii=False)}

TASK:
1. Identify files that appear outdated based on modification dates
2. Flag files with old dates in their content
3. Identify session notes or temporary files that should be archived
4. Find version-numbered files where only latest should be kept

OUTPUT FORMAT (respond ONLY with valid JSON):
{{
  "freshness_summary": {{
    "total_files": {len(files)},
    "likely_current": <number>,
    "likely_outdated": <number>,
    "needs_review": <number>
  }},
  "outdated_files": [
    {{
      "file": "<filename>",
      "last_modified": "<date>",
      "age_assessment": "<old|very_old|ancient>",
      "reason": "<why outdated>",
      "action": "archive|review|keep"
    }}
  ],
  "session_files": [
    {{
      "file": "<filename>",
      "session_date": "<extracted date>",
      "action": "archive"
    }}
  ],
  "version_groups": [
    {{
      "base_name": "<base name without version>",
      "versions": ["v1.md", "v2.md", "v3.md"],
      "latest": "<latest version file>",
      "action": "keep_latest_archive_rest"
    }}
  ]
}}"""


def analyze_with_ollama_sync(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """Send prompt to Ollama and parse JSON response (synchronous version)."""
    if not OLLAMA_AVAILABLE:
        return {"error": "Ollama not installed"}
    
    try:
        # Use synchronous ollama.generate
        response = ollama.generate(
            model=model,
            prompt=prompt,
            format="json",
            options={
                "temperature": 0.1,  # Low temperature for consistent analysis
                "num_predict": 4096,
            }
        )
        
        result_text = response.get('response', '{}')
        
        # Try to parse JSON
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Could not parse JSON", "raw_response": result_text[:500]}
            
    except Exception as e:
        return {"error": str(e)}


async def analyze_with_ollama(prompt: str, model: str = DEFAULT_MODEL) -> dict:
    """Send prompt to Ollama and parse JSON response (async wrapper)."""
    # Run sync version in executor to avoid blocking
    import concurrent.futures
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(
            executor,
            analyze_with_ollama_sync,
            prompt,
            model
        )


def analyze_docs_for_redundancy_sync(
    docs_path: str,
    file_pattern: str = "*.md",
    model: str = DEFAULT_MODEL,
    max_files: int = MAX_FILES
) -> dict:
    """
    Synchronous version - scans docs for redundancy using local LLM.
    READ-ONLY: No files are modified.
    """
    docs_root = Path(docs_path)
    
    if not docs_root.exists():
        return {"error": f"Path does not exist: {docs_path}"}
    
    # Collect files
    all_files = list(docs_root.glob(file_pattern))
    
    # Also check subdirectories (1 level)
    for subdir in docs_root.iterdir():
        if subdir.is_dir():
            all_files.extend(list(subdir.glob(file_pattern)))
    
    # Limit files for PoC
    files_to_analyze = all_files[:max_files]
    
    # Get file info
    file_infos = [get_file_info(f) for f in files_to_analyze]
    file_infos = [f for f in file_infos if "error" not in f]
    
    # Build prompt and analyze
    prompt = build_redundancy_prompt(file_infos)
    
    # Run synchronous analysis (no event loop needed)
    result = analyze_with_ollama_sync(prompt, model)
    
    # Add metadata
    result["_metadata"] = {
        "scan_path": docs_path,
        "files_scanned": len(file_infos),
        "files_total": len(all_files),
        "model_used": model,
        "scan_time": datetime.now().isoformat(),
        "mode": "READ_ONLY"
    }
    
    return result


def analyze_docs_freshness_sync(
    docs_path: str,
    file_pattern: str = "*.md",
    model: str = DEFAULT_MODEL,
    max_files: int = MAX_FILES
) -> dict:
    """
    Synchronous version - checks documentation freshness using local LLM.
    READ-ONLY: No files are modified.
    """
    docs_root = Path(docs_path)
    
    if not docs_root.exists():
        return {"error": f"Path does not exist: {docs_path}"}
    
    # Collect files
    all_files = list(docs_root.glob(file_pattern))
    files_to_analyze = all_files[:max_files]
    
    # Get file info
    file_infos = [get_file_info(f) for f in files_to_analyze]
    file_infos = [f for f in file_infos if "error" not in f]
    
    # Build prompt and analyze
    prompt = build_freshness_prompt(file_infos)
    
    # Run synchronous analysis (no event loop needed)
    result = analyze_with_ollama_sync(prompt, model)
    
    # Add metadata
    result["_metadata"] = {
        "scan_path": docs_path,
        "files_scanned": len(file_infos),
        "model_used": model,
        "scan_time": datetime.now().isoformat(),
        "mode": "READ_ONLY"
    }
    
    return result


# ============================================================================
# MCP Server Setup
# ============================================================================

if MCP_AVAILABLE:
    app = Server("local-llm-analyzer")

    @app.list_tools()
    async def list_tools():
        return [
            Tool(
                name="analyze_docs_for_redundancy",
                description="""Scans documentation files for redundancy using a local LLM (Ollama).
                
READ-ONLY: No files are modified. Returns JSON with:
- redundancy_candidates: Groups of similar/duplicate files
- outdated_candidates: Files that appear outdated
- structure_issues: Organizational problems

Use this for bulk documentation analysis before cleanup decisions.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "docs_path": {
                            "type": "string",
                            "description": "Absolute path to the docs folder to scan"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Glob pattern for files (default: *.md)",
                            "default": "*.md"
                        },
                        "model": {
                            "type": "string",
                            "description": "Ollama model to use (default: llama3:8b)",
                            "default": "llama3:8b"
                        },
                        "max_files": {
                            "type": "integer",
                            "description": "Maximum files to analyze (default: 100)",
                            "default": 100
                        }
                    },
                    "required": ["docs_path"]
                }
            ),
            Tool(
                name="analyze_docs_freshness",
                description="""Checks documentation freshness and identifies outdated files using local LLM.
                
READ-ONLY: No files are modified. Returns JSON with:
- freshness_summary: Overview of document currency
- outdated_files: Files that need updating
- session_files: Temporary session notes to archive
- version_groups: Files with version numbers

Use this to identify stale documentation.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "docs_path": {
                            "type": "string",
                            "description": "Absolute path to the docs folder to scan"
                        },
                        "file_pattern": {
                            "type": "string",
                            "description": "Glob pattern for files (default: *.md)",
                            "default": "*.md"
                        },
                        "model": {
                            "type": "string",
                            "description": "Ollama model to use (default: llama3:8b)",
                            "default": "llama3:8b"
                        }
                    },
                    "required": ["docs_path"]
                }
            ),
            Tool(
                name="check_ollama_status",
                description="Check if Ollama is running and which models are available.",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict):
        if name == "analyze_docs_for_redundancy":
            result = analyze_docs_for_redundancy_sync(
                docs_path=arguments["docs_path"],
                file_pattern=arguments.get("file_pattern", "*.md"),
                model=arguments.get("model", DEFAULT_MODEL),
                max_files=arguments.get("max_files", MAX_FILES)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        
        elif name == "analyze_docs_freshness":
            result = analyze_docs_freshness_sync(
                docs_path=arguments["docs_path"],
                file_pattern=arguments.get("file_pattern", "*.md"),
                model=arguments.get("model", DEFAULT_MODEL)
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]
        
        elif name == "check_ollama_status":
            try:
                if not OLLAMA_AVAILABLE:
                    return [TextContent(type="text", text=json.dumps({
                        "status": "error",
                        "message": "Ollama Python package not installed"
                    }))]
                
                result = ollama.list()
                # Handle both dict and object responses
                models_list = result.get('models', []) if isinstance(result, dict) else getattr(result, 'models', [])
                model_names = []
                for m in models_list:
                    if hasattr(m, 'model'):
                        model_names.append(m.model)
                    elif isinstance(m, dict):
                        model_names.append(m.get('name') or m.get('model'))
                
                return [TextContent(type="text", text=json.dumps({
                    "status": "ok",
                    "models": model_names,
                    "default_model": DEFAULT_MODEL
                }, indent=2))]
            except Exception as e:
                return [TextContent(type="text", text=json.dumps({
                    "status": "error",
                    "message": str(e),
                    "hint": "Is Ollama running? Try: ollama serve"
                }))]
        
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())


# ============================================================================
# CLI for direct testing
# ============================================================================

def cli_test():
    """CLI for testing without MCP."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Local LLM Documentation Analyzer")
    parser.add_argument("docs_path", help="Path to docs folder")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama model")
    parser.add_argument("--max-files", type=int, default=50, help="Max files to analyze")
    parser.add_argument("--mode", choices=["redundancy", "freshness"], default="redundancy")
    
    args = parser.parse_args()
    
    print(f"Analyzing {args.docs_path} with {args.model}...")
    print(f"Mode: {args.mode}, Max files: {args.max_files}")
    print("-" * 50)
    
    if args.mode == "redundancy":
        result = analyze_docs_for_redundancy_sync(
            args.docs_path,
            model=args.model,
            max_files=args.max_files
        )
    else:
        result = analyze_docs_freshness_sync(
            args.docs_path,
            model=args.model,
            max_files=args.max_files
        )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] != "--help":
        # CLI mode
        cli_test()
    elif MCP_AVAILABLE:
        # MCP server mode
        asyncio.run(main())
    else:
        print("MCP not available. Install with: pip install mcp")
        print("Or run with path argument for CLI mode: python server.py /path/to/docs")
