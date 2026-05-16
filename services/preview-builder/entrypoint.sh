#!/bin/bash
set -e

echo "[metl-preview] Building preview for job: ${METL_JOB_ID}"

cd /workspace

# Detect framework
if [ -f "package.json" ]; then
    echo "[metl-preview] package.json found"
    
    # Install dependencies
    if command -v pnpm &> /dev/null; then
        pnpm install --frozen-lockfile || pnpm install
    elif [ -f "pnpm-lock.yaml" ]; then
        npm install -g pnpm && pnpm install
    elif [ -f "yarn.lock" ]; then
        yarn install --frozen-lockfile || yarn install
    else
        npm install
    fi
    
    # Build
    if [ -f "next.config.js" ] || [ -f "next.config.ts" ] || [ -f "next.config.mjs" ]; then
        echo "[metl-preview] Next.js project detected"
        npm run build
        
        # Start Next.js in background
        echo "[metl-preview] Starting Next.js on port ${PORT:-3000}"
        PORT=${PORT:-3000} npm run start &
    else
        echo "[metl-preview] Standard project detected"
        npm run build
        
        # Serve built output
        if [ -d "dist" ]; then
            echo "[metl-preview] Serving dist/ on port ${PORT:-3000}"
            cd dist && npx serve . -l ${PORT:-3000} &
        elif [ -d "build" ]; then
            echo "[metl-preview] Serving build/ on port ${PORT:-3000}"
            cd build && npx serve . -l ${PORT:-3000} &
        else
            echo "[metl-preview] No build output found"
            exit 1
        fi
    fi
else
    echo "[metl-preview] No package.json found"
    exit 1
fi

# Keep container alive
wait