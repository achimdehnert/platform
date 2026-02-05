#!/bin/bash
# CAD-Hub API Startup Script

cd "$(dirname "$0")"
source .venv/bin/activate
cd src

echo "Starting CAD-Hub API on http://0.0.0.0:8000"
echo "API Docs: http://localhost:8000/api/docs"
echo ""

uvicorn cad_services.api.app:app --host 0.0.0.0 --port 8000 --reload
