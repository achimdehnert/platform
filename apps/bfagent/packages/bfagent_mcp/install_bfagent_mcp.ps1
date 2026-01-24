# ═══════════════════════════════════════════════════════════════════════════════
# BF Agent MCP Server v2.0 - PowerShell Installation Script
# ═══════════════════════════════════════════════════════════════════════════════
#
# Usage:
#   .\install_bfagent_mcp.ps1
#   .\install_bfagent_mcp.ps1 -TargetDir "C:\custom\path"
#
# ═══════════════════════════════════════════════════════════════════════════════

param(
    [string]$TargetDir = "$env:USERPROFILE\mcp_servers\bfagent"
)

Write-Host "🚀 Installing BF Agent MCP Server v2.0" -ForegroundColor Cyan
Write-Host "   Target: $TargetDir" -ForegroundColor Gray
Write-Host ""

# Create directories
New-Item -ItemType Directory -Force -Path "$TargetDir" | Out-Null
New-Item -ItemType Directory -Force -Path "$TargetDir\metaprompter" | Out-Null
New-Item -ItemType Directory -Force -Path "$TargetDir\standards" | Out-Null
New-Item -ItemType Directory -Force -Path "$TargetDir\examples" | Out-Null

# Copy from source package (already clean!)
$SourceDir = "c:\Users\achim\github\bfagent\packages\bfagent_mcp\bfagent_mcp"

Write-Host "📁 Copying files from clean package..." -ForegroundColor Yellow

# Main package file
Copy-Item "$SourceDir\__init__.py" "$TargetDir\" -Force
Write-Host "   ✅ __init__.py" -ForegroundColor Green

# MetaPrompter
Copy-Item "$SourceDir\metaprompter\__init__.py" "$TargetDir\metaprompter\" -Force
Copy-Item "$SourceDir\metaprompter\gateway.py" "$TargetDir\metaprompter\" -Force
Copy-Item "$SourceDir\metaprompter\intent.py" "$TargetDir\metaprompter\" -Force
Copy-Item "$SourceDir\metaprompter\enricher.py" "$TargetDir\metaprompter\" -Force
Write-Host "   ✅ metaprompter/ (4 files)" -ForegroundColor Green

# Standards
Copy-Item "$SourceDir\standards\__init__.py" "$TargetDir\standards\" -Force
Copy-Item "$SourceDir\standards\validator.py" "$TargetDir\standards\" -Force
Copy-Item "$SourceDir\standards\enforcer.py" "$TargetDir\standards\" -Force
Write-Host "   ✅ standards/ (3 files)" -ForegroundColor Green

# Server
Copy-Item "$SourceDir\server_metaprompter.py" "$TargetDir\server.py" -Force
Write-Host "   ✅ server.py" -ForegroundColor Green

# pyproject.toml
@"
[project]
name = "bfagent-mcp"
version = "2.0.0"
description = "BF Agent MCP Server - Universal Workflow Orchestration"
requires-python = ">=3.10"
license = {text = "MIT"}
dependencies = [
    "mcp>=1.0.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
django = ["django>=4.2", "psycopg2-binary"]
dev = ["pytest>=7.0", "pytest-asyncio", "black", "ruff"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["bfagent_mcp"]
"@ | Out-File -FilePath "$TargetDir\pyproject.toml" -Encoding utf8
Write-Host "   ✅ pyproject.toml" -ForegroundColor Green

# MCP Config Example
@"
{
  "mcpServers": {
    "bfagent": {
      "command": "python",
      "args": ["-m", "bfagent_mcp.server"],
      "env": {
        "PYTHONPATH": "$($TargetDir -replace '\\', '/')"
      }
    }
  }
}
"@ | Out-File -FilePath "$TargetDir\examples\mcp_config.json" -Encoding utf8
Write-Host "   ✅ examples/mcp_config.json" -ForegroundColor Green

# README
@"
# 🤖 BF Agent MCP Server v2.0

Universal MCP Server mit MetaPrompter Gateway und Standards Enforcement.

## Installation

``````bash
pip install mcp pydantic
``````

## Windsurf Setup

**Config Location:**
``````
%USERPROFILE%\.codeium\windsurf\mcp_config.json
``````

**Config Content:**
``````json
{
  "mcpServers": {
    "bfagent": {
      "command": "python",
      "args": ["-m", "bfagent_mcp.server"],
      "env": {
        "PYTHONPATH": "$($TargetDir -replace '\\', '\\\\')"
      }
    }
  }
}
``````

## Test

``````bash
python -c "from bfagent_mcp.server import BFAgentMCPServer; print('✅ OK')"
``````

## Features

- ✅ Universal Gateway - Ein Tool für alles
- ✅ Natural Language - Natürliche Sprache
- ✅ Standards Enforcement - 100% konformer Code
- ✅ 12 Coding Standards (H001-T001)
- ✅ Intent Classification (15+ Intents)
- ✅ Smart Defaults & Context Enrichment
"@ | Out-File -FilePath "$TargetDir\README.md" -Encoding utf8
Write-Host "   ✅ README.md" -ForegroundColor Green

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "✅ Installation abgeschlossen!" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "📁 Installiert in: $TargetDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 Nächste Schritte:" -ForegroundColor Yellow
Write-Host ""
Write-Host "   1. Dependencies installieren:" -ForegroundColor White
Write-Host "      pip install mcp pydantic" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Windsurf Config erstellen:" -ForegroundColor White
Write-Host "      $env:USERPROFILE\.codeium\windsurf\mcp_config.json" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Config Inhalt:" -ForegroundColor White
Write-Host '      Siehe: ' -NoNewline -ForegroundColor Gray
Write-Host "$TargetDir\examples\mcp_config.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "   4. Test:" -ForegroundColor White
Write-Host "      cd $TargetDir" -ForegroundColor Gray
Write-Host '      python -c "from bfagent_mcp.server import BFAgentMCPServer; print('"'"'✅ OK'"'"')"' -ForegroundColor Gray
Write-Host ""
Write-Host "   5. Windsurf → MCP Panel → Refresh" -ForegroundColor White
Write-Host ""
Write-Host "   6. Testen: @bfagent Hilfe" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
