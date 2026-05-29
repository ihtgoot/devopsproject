#!/bin/bash

# Exit on error
set -e

# Cleanup function to kill background processes on exit
cleanup() {
    echo "Stopping all services..."
    kill $TRAINER_PID $API_PID $FRONTEND_PID 2>/dev/null
    exit
}

# Register the cleanup function for signals
trap cleanup SIGINT SIGTERM EXIT

echo "======================================"
echo "Starting DevOps Project without Docker"
echo "======================================"

# 1. Start Trainer
echo "-> Setting up and starting Trainer..."
cd trainer
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip3 install -r requirements.txt 
export PORT=8000
export DATA_DIR=../data
python3 app.py &
TRAINER_PID=$!
cd ..

# 2. Start Go Backend API
echo "-> Setting up and starting API..."
cd backend-go
go mod download
export TRAINER_URL=http://localhost:8000
export PORT=8080
export DATA_DIR=./data
go run cmd/main.go &
API_PID=$!
cd ..

# 3. Start Frontend
echo "-> Starting Frontend..."
cd frontend
python3 -m http.server 3000 &
FRONTEND_PID=$!
cd ..

echo "======================================"
echo "✅ All services are running!"
echo "   Frontend: http://localhost:3000"
echo "   API:      http://localhost:8080"
echo "   Trainer:  http://localhost:8000"
echo "======================================"
echo "Press Ctrl+C to stop all services."

# Wait indefinitely until interrupted
wait
