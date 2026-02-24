#!/bin/bash
# Stash mosquitto config/data, pull latest from GitHub, then restore stash.
# Run from repo root: ./vm_server/pull-with-stash.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# If we're in a conflicted state (unmerged files), resolve by keeping local/stashed version
if git ls-files -u | grep -q .; then
  echo "Resolving conflict (keeping your local mosquitto config and db)..."
  if git ls-files -u | grep -q mosquitto.conf; then
    git checkout --theirs -- vm_server/mqtt/config/mosquitto.conf
    git add vm_server/mqtt/config/mosquitto.conf
  fi
  if git ls-files -u | grep -q mosquitto.db; then
    git checkout --theirs -- vm_server/mqtt/data/mosquitto.db
    git add vm_server/mqtt/data/mosquitto.db
  fi
  echo "Done. Your mosquitto config is restored. You can commit or leave as-is."
  exit 0
fi

echo "Stashing mosquitto config and data..."
git stash push -m "mosquitto config before pull" -- vm_server/mqtt/config/mosquitto.conf vm_server/mqtt/data/mosquitto.db

echo "Pulling latest from origin main..."
git fetch origin main
# Force-overwrite any untracked files that would block merge (take remote version; we only protect conf files)
while IFS= read -r f; do
  if [ -f "$f" ] && [ -n "$(git ls-files --others --exclude-standard -- "$f" 2>/dev/null)" ]; then
    echo "Taking remote version: $f"
    git checkout origin/main -- "$f"
  fi
done < <(git diff --name-only HEAD origin/main 2>/dev/null || true)
git pull origin main

echo "Restoring stashed mosquitto config..."
set +e
git stash pop
POP_EXIT=$?
set -e
if [ "$POP_EXIT" -ne 0 ]; then
  echo "Resolving binary conflict on mosquitto.db (keeping your local copy)..."
  git checkout --theirs -- vm_server/mqtt/data/mosquitto.db
  git add vm_server/mqtt/data/mosquitto.db
fi

echo "Done. Your mosquitto config is restored."
