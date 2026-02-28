#!/bin/bash

# Бот и backend используют одну и ту же базу данных
export DATABASE_PATH=/app/salon.db

# Запускаем Telegram бота в фоне
python /app/run_bot.py &

# Запускаем backend (главный процесс — держит контейнер живым)
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
