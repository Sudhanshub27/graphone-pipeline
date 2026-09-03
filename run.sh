#!/usr/bin/env bash

# ==============================================================================
# TRIPWIRE PIPELINE: MASTER EXECUTION SCRIPT
# ==============================================================================
# Executes virtual environment setup, automated unit/integration tests, multi-target data
# ingestion, LLM extraction, entity resolution, vector store indexing, and dashboard Web UI.
#
# Usage:
#   ./run.sh              # Run full end-to-end pipeline
#   ./run.sh --dry-run    # Fast dry-run on sample records
#   ./run.sh --limit 50   # Run with custom record limits
#   ./run.sh --eval       # Run pipeline evaluation benchmark in mock mode
# ==============================================================================

set -e

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "🚀 TRIPWIRE DATA PIPELINE: INITIALIZING MASTER RUN"
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
echo "🧪 STAGE 1: RUNNING AUTOMATED UNIT & INTEGRATION TEST SUITE"
echo "======================================================================"
pytest tests/ -v

# Check for --eval flag
if [[ "$*" == *"--eval"* ]]; then
    echo ""
    echo "======================================================================"
    echo "📈 EXECUTING SCIENTIFIC PIPELINE EVALUATION BENCHMARK"
    echo "======================================================================"
    python3 -m evaluation.benchmark --mode mock --records 20 --iterations 3 --warmup-records 2 --output evaluation/reports/benchmark_report.json
    python3 -m evaluation.llm.evaluator --provider chain --output evaluation/reports/llm_chain_eval.json
    python3 -m evaluation.resolution.evaluator --threshold 85.0 --output evaluation/reports/resolution_eval.json
    echo "✅ Scientific benchmark execution complete. Reports saved to evaluation/reports/"
    exit 0
fi

# Default to --dry-run if no CLI flags are passed for fast launch
RUN_ARGS="$@"
if [ $# -eq 0 ]; then
    RUN_ARGS="--dry-run"
fi

# 3. Run Main Pipeline Ingestion Orchestrator
echo ""
echo "======================================================================"
echo "⚡ STAGE 2: EXECUTING MULTI-TARGET INGESTION ORCHESTRATOR"
echo "======================================================================"
python3 -m src.main run all $RUN_ARGS

# 4. Run Sheets / CSV Export
echo ""
echo "======================================================================"
echo "📊 STAGE 3: EXECUTING GOOGLE SHEETS / CSV EXPORT SYNC"
echo "======================================================================"
python3 -m src.main export sheets $RUN_ARGS

# 5. Build React Dashboard Frontend Production Bundle
if [ -d "src/dashboard/frontend" ]; then
    echo ""
    echo "======================================================================"
    echo "📦 STAGE 4: BUILDING REACT FRONTEND PRODUCTION BUNDLE"
    echo "======================================================================"
    python3 copy_assets.py
    (cd src/dashboard/frontend && npm run build)
fi

# 6. Launch Web Dashboard UI
echo ""
echo "======================================================================"
echo "🌐 STAGE 5: LAUNCHING REACT + FASTAPI DASHBOARD WEB UI"
echo "======================================================================"

# Automatically clear port 8000 if previously occupied
if fuser 8000/tcp >/dev/null 2>&1; then
    echo "▶ Port 8000 occupied. Clearing existing process..."
    fuser -k 8000/tcp || true
    sleep 1
fi

echo "▶ Dashboard server running at: http://localhost:8000"
echo "▶ Press Ctrl+C to stop the dashboard server."

# Attempt to open browser automatically
(sleep 1.5 && python3 -m webbrowser "http://localhost:8000") &

uvicorn src.dashboard.main:app --host 0.0.0.0 --port 8000
