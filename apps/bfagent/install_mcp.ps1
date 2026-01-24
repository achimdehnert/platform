# Install bfagent_mcp in development mode
cd packages\bfagent_mcp
pip install -e . --force-reinstall --no-deps
cd ..\..

Write-Host "`n✅ Installation complete!" -ForegroundColor Green
Write-Host "`nTest import:" -ForegroundColor Cyan
python -c "import bfagent_mcp; print('✅ Version:', bfagent_mcp.__version__); print('✅ models:', hasattr(bfagent_mcp, 'models'))"
