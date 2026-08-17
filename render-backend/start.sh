#!/bin/bash
echo "Starting Backend Services..."
# Save Render's public port BEFORE anything overwrites it
RENDER_PORT="${PORT:-10000}"
echo "Render public port: $RENDER_PORT"
# 1. Node clipper API on INTERNAL port 5000 (scoped, does not overwrite $PORT)
cd /app/clipper/backend
PORT=5000 node src/app.js &
# 2. BullMQ worker
PORT=5000 node src/worker/worker.js &
sleep 3
# 3. Python FastAPI (Humanizer + API proxy) on Render's REAL port
cd /app/humanizer
exec uvicorn app.main:app --host 0.0.0.0 --port "$RENDER_PORT"
