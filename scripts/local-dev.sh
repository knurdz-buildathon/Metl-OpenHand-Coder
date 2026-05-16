#!/bin/bash
set -euo pipefail

echo "============================================"
echo " Metl Coding Agent - Local Development       "
echo "============================================"
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# --- Start infrastructure services ---
echo "[1/3] Starting infrastructure (PostgreSQL, Redis, MinIO)..."
docker compose up -d postgres redis minio

echo "[2/3] Waiting for services to be healthy..."
# Postgres
while ! docker compose exec -T postgres pg_isready -U postgres -d metl 2>/dev/null; do
    echo "Waiting for postgres..."
    sleep 2
done
echo "PostgreSQL is ready."

# Redis
while ! docker compose exec -T redis redis-cli ping 2>/dev/null; do
    echo "Waiting for redis..."
    sleep 2
done
echo "Redis is ready."

echo "[3/3] Starting development servers..."
echo ""
echo "Start the Agent API in one terminal:"
echo "  cd apps/agent-api"
echo "  pip install -e \".[dev]\""
echo "  uvicorn src.main:app --reload --port 8000"
echo ""
echo "Start the Dashboard in another terminal:"
echo "  cd apps/dashboard"
echo "  pnpm dev"
echo ""
echo "============================================"
echo ""
echo "Dashboard:  http://localhost:3000"
echo "Agent API:  http://localhost:8000"
echo "API Docs:   http://localhost:8000/docs"
echo ""
echo "To stop all services:"
echo "  docker compose down"
echo ""