#!/bin/bash

# Бот и backend используют одну и ту же базу данных
# /app/salon.db всегда присутствует в Docker-образе (скопирован из backend/salon.db)
export DATABASE_PATH=/app/salon.db

# Запускаем backend
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
BACKEND_PID=$!

# Ждём пока backend будет готов (макс. 15 секунд)
echo "Ожидание инициализации backend..."
for i in $(seq 1 15); do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT:-8000}/health')" > /dev/null 2>&1; then
        echo "Backend готов, запускаем бота..."
        break
    fi
    sleep 1
done

# Запускаем Telegram бота
python /app/run_bot.py &

# Ждём завершения backend (Railway перезапустит если упадёт)
wait $BACKEND_PID
