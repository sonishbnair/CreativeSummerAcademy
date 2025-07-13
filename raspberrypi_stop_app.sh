#!/bin/bash

# Step 1: Find the Uvicorn process
APP_PATTERN="uvicorn app.main:app"
echo "[1/2] Searching for Uvicorn process running the app..."

# Find the PID(s) of the running Uvicorn app
PIDS=$(ps aux | grep "$APP_PATTERN" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "[2/2] No running Uvicorn app found."
    exit 0
fi

echo "[2/2] Stopping Uvicorn app (PID(s): $PIDS)..."
kill $PIDS
if [ $? -eq 0 ]; then
    echo "Successfully stopped the Uvicorn app."
else
    echo "Failed to stop the Uvicorn app."
fi 