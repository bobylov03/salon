#!/bin/bash

# Бот и backend используют одну и ту же базу данных
export DATABASE_PATH=/data/salon.db

# Запускаем backend в фоне — он создаёт salon.db при старте
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
BACKEND_PID=$!

# Ждём пока backend создаст базу данных (макс. 30 секунд)
echo "Ожидание инициализации базы данных..."
for i in $(seq 1 30); do
    if [ -f "$DATABASE_PATH" ]; then
        echo "База данных готова, запускаем бота..."
        break
    fi
    sleep 1
done

# Запускаем Telegram бота в фоне
python /app/run_bot.py &

# Ждём завершения backend (если упадёт — Railway перезапустит контейнер)
wait $BACKEND_PID
