#!/bin/bash

# Бот и backend используют одну и ту же базу данных
export DATABASE_PATH=/data/salon.db

mkdir -p /data

# Копируем seed если:
#  1) БД вообще не существует
#  2) master_services пустой (бот не сможет найти мастеров — нерабочее состояние)
need_seed=false

if [ ! -f "$DATABASE_PATH" ]; then
    echo "База данных не найдена, копируем seed..."
    need_seed=true
else
    ms_count=$(python3 -c "
import sqlite3
try:
    c = sqlite3.connect('$DATABASE_PATH').cursor()
    c.execute('SELECT COUNT(*) FROM master_services')
    print(c.fetchone()[0])
except:
    print(0)
" 2>/dev/null || echo 0)

    if [ "$ms_count" = "0" ]; then
        echo "master_services пустой — восстанавливаем из seed..."
        need_seed=true
    else
        echo "База данных готова (master_services: $ms_count записей)"
    fi
fi

if [ "$need_seed" = "true" ] && [ -f /app/salon_seed.db ]; then
    cp /app/salon_seed.db "$DATABASE_PATH"
    echo "Seed скопирован: $DATABASE_PATH"
fi

# Запускаем backend
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} &
BACKEND_PID=$!

# Ждём пока база данных будет готова (макс. 15 секунд)
echo "Ожидание инициализации backend..."
for i in $(seq 1 15); do
    if [ -f "$DATABASE_PATH" ]; then
        echo "Backend готов, запускаем бота..."
        break
    fi
    sleep 1
done

# Запускаем Telegram бота
python /app/run_bot.py &

# Ждём завершения backend (Railway перезапустит если упадёт)
wait $BACKEND_PID
