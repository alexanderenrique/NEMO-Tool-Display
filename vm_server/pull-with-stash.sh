#!/bin/bash
# Stash mosquitto config/data, pull latest from GitHub, then restore stash.
# Run from repo root: ./vm_server/pull-with-stash.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
GIT=(git -c "safe.directory=$REPO_ROOT")

# If we're in a conflicted state (unmerged files), resolve by keeping local/stashed version
if "${GIT[@]}" ls-files -u | grep -q .; then
  echo "Resolving conflict (keeping your local mosquitto config and db)..."
  if "${GIT[@]}" ls-files -u | grep -q mosquitto.conf; then
    "${GIT[@]}" checkout --theirs -- vm_server/mqtt/config/mosquitto.conf
    "${GIT[@]}" add vm_server/mqtt/config/mosquitto.conf
  fi
  if "${GIT[@]}" ls-files -u | grep -q mosquitto.db; then
    "${GIT[@]}" checkout --theirs -- vm_server/mqtt/data/mosquitto.db
    "${GIT[@]}" add vm_server/mqtt/data/mosquitto.db
  fi
  echo "Done. Your mosquitto config is restored. You can commit or leave as-is."
  exit 0
fi

echo "Stashing mosquitto config and data..."

# Only stash files that are actually tracked in this repo. On older checkouts or
# fresh installs these paths may not exist yet, which would otherwise cause a
# pathspec error ("Did you forget to 'git add'?").
STASH_PATHS=()
for f in vm_server/mqtt/config/mosquitto.conf vm_server/mqtt/data/mosquitto.db; do
  if "${GIT[@]}" ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    STASH_PATHS+=("$f")
  fi
done

if [ "${#STASH_PATHS[@]}" -gt 0 ]; then
  "${GIT[@]}" stash push -m "mosquitto config before pull" -- "${STASH_PATHS[@]}"
else
  echo "No tracked mosquitto config/data files to stash (skipping mosquitto stash step)."
fi

echo "Pulling latest from origin main..."
"${GIT[@]}" fetch origin main
# Force-overwrite any untracked files that would block merge (take remote version; we only protect conf files)
while IFS= read -r f; do
  if [ -f "$f" ] && [ -n "$("${GIT[@]}" ls-files --others --exclude-standard -- "$f" 2>/dev/null)" ]; then
    echo "Taking remote version: $f"
    "${GIT[@]}" checkout origin/main -- "$f"
  fi
done < <("${GIT[@]}" diff --name-only HEAD origin/main 2>/dev/null || true)
"${GIT[@]}" pull origin main

echo "Restoring stashed mosquitto config..."
set +e
"${GIT[@]}" stash pop
POP_EXIT=$?
set -e
if [ "$POP_EXIT" -ne 0 ]; then
  echo "Resolving binary conflict on mosquitto.db (keeping your local copy)..."
  "${GIT[@]}" checkout --theirs -- vm_server/mqtt/data/mosquitto.db
  "${GIT[@]}" add vm_server/mqtt/data/mosquitto.db
fi

echo "Done. Your mosquitto config is restored."
