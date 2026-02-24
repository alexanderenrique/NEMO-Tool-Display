#!/bin/bash
# Stash mosquitto config/data, pull latest from GitHub, then restore stash.
# Run from repo root: ./vm_server/pull-with-stash.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "Stashing mosquitto config and data..."
git stash push -m "mosquitto config before pull" -- vm_server/mqtt/config/mosquitto.conf vm_server/mqtt/data/mosquitto.db

echo "Pulling latest from origin main..."
git pull origin main

echo "Restoring stashed mosquitto config..."
git stash pop

echo "Done. Your mosquitto config is restored."
