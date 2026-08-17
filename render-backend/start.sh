#!/bin/bash

echo "Starting Backend Services..."

# 1. Start Node.js API (Clipper) on port 5000 in background
cd /app/clipper/backend
export PORT=5000 
node src/app.js &

# 2. Start BullMQ Worker in background
node src/worker/worker.js &

# 3. Start Python FastAPI (Humanizer + API Proxy) on the Render-provided $PORT
# Render sets the $PORT environment variable automatically (usually 10000).
# Uvicorn will bind to this port so external traffic routes here.
cd /app/humanizer
uvicorn app.main:app --host 0.0.0.0 --port $PORT
