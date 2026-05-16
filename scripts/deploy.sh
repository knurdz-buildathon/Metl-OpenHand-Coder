#!/bin/bash
set -euo pipefail

echo "============================================"
echo " Metl Coding Agent - Deploy                  "
echo "============================================"
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# --- Step 1: Pull latest changes ---
echo "[1/5] Pulling latest changes from git..."
if git rev-parse --git-dir > /dev/null 2>&1; then
    git fetch origin
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "$LOCAL")

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "New changes detected, pulling..."
        git pull origin main
    else
        echo "Already up to date."
    fi
else
    echo "Not a git repository, skipping pull."
fi

# --- Step 2: Rebuild and restart containers ---
echo "[2/5] Rebuilding and restarting containers..."
docker compose up -d --build

# --- Step 3: Wait for services to be healthy ---
echo "[3/5] Waiting for services to be healthy..."
sleep 5
MAX_WAIT=60
WAITED=0
while ! docker compose ps | grep agent-api | grep -q "(healthy)\|Up"; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "WARNING: agent-api did not become healthy within ${MAX_WAIT}s"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done

# --- Step 4: Run database migrations ---
echo "[4/5] Running database migrations..."
docker compose exec -T agent-api alembic upgrade head || {
    echo "WARNING: Database migration failed. Check the logs:"
    echo "  docker compose logs agent-api"
}

# --- Step 5: Cleanup old preview containers ---
echo "[5/5] Cleaning up old preview containers..."
docker container prune -f --filter "label=metl-type=preview" 2>/dev/null || true
docker image prune -f 2>/dev/null || true

echo ""
echo "============================================"
echo " Deployment complete!                       "
echo "============================================"
echo ""
echo "Verify:"
echo "  Dashboard:  https://code.metl.run"
echo "  API Docs:   https://code.metl.run/api/docs"
echo "  API Health: https://code.metl.run/api/health"
echo ""
echo "View logs:"
echo "  docker compose logs -f agent-api"
echo "  docker compose logs -f dashboard"
echo ""