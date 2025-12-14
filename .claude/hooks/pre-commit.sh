#!/bin/bash
echo "🔍 Running pre-commit checks..."
uv run ruff check --fix . 2>/dev/null || true
uv run ruff format . 2>/dev/null || true
echo "✅ Pre-commit complete"
