#!/bin/bash

# Step 0: Check if the app is already running and stop it if needed
APP_PATTERN="uvicorn app.main:app"
echo "[0/3] Checking for existing Uvicorn app process..."
PIDS=$(ps aux | grep "$APP_PATTERN" | grep -v grep | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "Existing Uvicorn app found (PID(s): $PIDS). Stopping it..."
    kill $PIDS
    if [ $? -eq 0 ]; then
        echo "Stopped existing Uvicorn app."
    else
        echo "Failed to stop existing Uvicorn app. Exiting."
        exit 1
    fi
else
    echo "No existing Uvicorn app running."
fi

# Step 1: Change directory
APP_DIR="/home/pi/CreativeSummerAcademy"
echo "[1/3] Changing directory to $APP_DIR..."
cd "$APP_DIR" || { echo "Failed to cd to $APP_DIR"; exit 1; }
echo "[1/3] Directory changed successfully."

# Step 2: Activate virtual environment
echo "[2/3] Activating virtual environment..."
source .venv/bin/activate || { echo "Failed to activate virtual environment"; exit 1; }
echo "[2/3] Virtual environment activated."

# Step 3: Run the application in the background with nohup
echo "[3/3] Starting the application with Uvicorn in the background..."
echo "Command: nohup python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > app.log 2>&1 &"
nohup python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > app.log 2>&1 &
echo "Uvicorn app started in the background (PID: $!). Log: app.log" 