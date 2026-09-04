#!/usr/bin/env bash
set -euo pipefail

# Ensure script is executed from project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "TRIPWIRE LOCAL CI / QUALITY GATES RUNNER"
echo "======================================================================"

# Determine Python / Venv executables
PYTHON_BIN="python3"
if [ -f "./venv/bin/python" ]; then
    PYTHON_BIN="./venv/bin/python"
elif [ -f "./.venv/bin/python" ]; then
    PYTHON_BIN="./.venv/bin/python"
fi

RUFF_BIN="ruff"
if [ -f "./venv/bin/ruff" ]; then
    RUFF_BIN="./venv/bin/ruff"
elif [ -f "./.venv/bin/ruff" ]; then
    RUFF_BIN="./.venv/bin/ruff"
fi

PYTEST_BIN="pytest"
if [ -f "./venv/bin/pytest" ]; then
    PYTEST_BIN="./venv/bin/pytest"
elif [ -f "./.venv/bin/pytest" ]; then
    PYTEST_BIN="./.venv/bin/pytest"
fi

PRECOMMIT_BIN="pre-commit"
if [ -f "./venv/bin/pre-commit" ]; then
    PRECOMMIT_BIN="./venv/bin/pre-commit"
elif [ -f "./.venv/bin/pre-commit" ]; then
    PRECOMMIT_BIN="./.venv/bin/pre-commit"
fi

echo "▶ 1. Running Python Syntax Compile Check..."
$PYTHON_BIN -m compileall -q src config evaluation tests
echo "PASSED: Python syntax check"
echo ""

echo "▶ 2. Running Ruff Lint Check (Check-only mode)..."
$RUFF_BIN check .
echo "PASSED: Ruff lint check"
echo ""

echo "▶ 3. Running Pytest Suite with Coverage..."
$PYTEST_BIN tests/ --cov=src --cov-report=term-missing
echo "PASSED: Pytest test suite"
echo ""

echo "▶ 4. Running Pre-Commit Hooks..."
$PRECOMMIT_BIN run --all-files
echo "PASSED: Pre-commit hooks"
echo ""

if [ -d "src/dashboard/frontend" ]; then
    echo "▶ 5. Running Frontend Lint Check..."
    (cd src/dashboard/frontend && npm run lint)
    echo "PASSED: Frontend lint check"
    echo ""

    echo "▶ 6. Running Frontend Production Build..."
    (cd src/dashboard/frontend && npm run build)
    echo "PASSED: Frontend production build"
    echo ""
fi

echo "======================================================================"
echo "SUCCESS: ALL TRIPWIRE QUALITY GATES PASSED"
echo "======================================================================"
