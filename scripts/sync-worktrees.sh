#!/bin/bash
set -e

MAIN_REPO="/Users/zacharyrothstein/Code/medanki"
WORKTREES=(
    "../medanki-api:feature/api-backend"
    "../medanki-frontend:feature/frontend"
    "../medanki-tests:feature/tests"
)

cd "$MAIN_REPO"

echo "Fetching latest from origin..."
git fetch origin

for entry in "${WORKTREES[@]}"; do
    path="${entry%%:*}"
    branch_prefix="${entry##*:}"

    echo ""
    echo "=== Processing $path ==="

    cd "$MAIN_REPO/$path"

    current_branch=$(git branch --show-current)

    git clean -fd 2>/dev/null || true
    git stash 2>/dev/null || true

    timestamp=$(date +%Y%m%d-%H%M%S)
    new_branch="${branch_prefix}-${timestamp}"

    echo "Creating new branch: $new_branch (off main)"
    git checkout -b "$new_branch" main

    echo "Done. Was on: $current_branch, now on: $new_branch"
done

cd "$MAIN_REPO"
echo ""
echo "=== All worktrees synced ==="
git worktree list
