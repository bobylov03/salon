FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

# Устанавливаем зависимости backend и бота
COPY backend/requirements.txt /tmp/req-backend.txt
COPY bot/requirements.txt /tmp/req-bot.txt
RUN pip install --no-cache-dir -r /tmp/req-backend.txt -r /tmp/req-bot.txt

# Копируем код backend
COPY backend/ /app/

# Копируем бота
COPY bot/ /app/bot/
COPY run_bot.py /app/

RUN mkdir -p uploads/masters

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
