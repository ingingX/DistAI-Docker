#!/bin/bash
# Run all tests with coverage

set -e

echo "Installing test dependencies..."
pip install -q -r tests/requirements.txt

echo ""
echo "Running unit tests with coverage..."
pytest tests/test_coordinator.py -v --cov=coordinator --cov-report=html --cov-report=term-missing

echo ""
echo "Coverage report generated in htmlcov/index.html"
