#!/usr/bin/env bash

# ==============================================================================
# GRAPHONE PIPELINE: MASTER EXECUTION SCRIPT
# ==============================================================================
# Executes virtual environment setup, automated unit tests, multi-target data
# ingestion, LLM extraction, entity resolution, and Google Sheets/CSV export.
#
# Usage:
#   ./run.sh              # Run full end-to-end pipeline
#   ./run.sh --dry-run    # Fast dry-run on sample records
#   ./run.sh --limit 50   # Run with custom record limits
# ==============================================================================

set -e

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🚀 GRAPHONE DATA PIPELINE: INITIALIZING MASTER RUN"
echo "======================================================================"

# 1. Check & Activate Virtual Environment
if [ -d "venv" ]; then
    echo "▶ Activating Python virtual environment (venv)..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "▶ Activating Python virtual environment (.venv)..."
    source .venv/bin/activate
else
    echo "▶ Creating new Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "▶ Installing dependencies from requirements.txt..."
    pip install --upgrade pip
    pip install -r requirements.txt
fi

# 2. Run Test Suite
echo ""
echo "======================================================================"
echo "🧪 STAGE 1: RUNNING AUTOMATED UNIT TEST SUITE"
echo "======================================================================"
pytest tests/ -v

# 3. Run Main Pipeline Ingestion Orchestrator
echo ""
echo "======================================================================"
echo "⚡ STAGE 2: EXECUTING MULTI-TARGET INGESTION ORCHESTRATOR"
echo "======================================================================"
python3 -m src.main run all "$@"

# 4. Run Sheets / CSV Export
echo ""
echo "======================================================================"
echo "📊 STAGE 3: EXECUTING GOOGLE SHEETS / CSV EXPORT SYNC"
echo "======================================================================"
python3 -m src.main export sheets "$@"

echo ""
echo "======================================================================"
echo "✅ PIPELINE RUN COMPLETED SUCCESSFULLY!"
echo "======================================================================"
