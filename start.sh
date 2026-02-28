#!/bin/sh

# Start uvicorn (FastAPI backend) in background
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
UVICORN_PID=$!

# Wait for backend to be ready
sleep 3

# Start Telegram bot in background
python /app/run_bot.py &
BOT_PID=$!

# Wait for any process to exit (if one crashes, restart container)
wait $UVICORN_PID $BOT_PID
