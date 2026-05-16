#!/bin/bash
set -e

echo "[metl-openhands] Starting OpenHands agent for job: ${METL_JOB_ID}"

# Read prompt from mounted file
PROMPT=$(cat /workspace/.metl/prompt.txt 2>/dev/null || echo "${METL_PROMPT}")

# Run OpenHands in headless mode with the prompt
python -m openhands.core.main \
    -t "${PROMPT}" \
    -f "/workspace" \
    --model "${LLM_MODEL}" \
    --api-key "${LLM_API_KEY}" \
    --max-iterations "${MAX_ITERATIONS:-10}"

EXIT_CODE=$?

echo "[metl-openhands] OpenHands completed with exit code: ${EXIT_CODE}"
exit ${EXIT_CODE}