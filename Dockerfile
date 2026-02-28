FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

# Install backend dependencies
COPY backend/requirements.txt ./requirements_backend.txt
RUN pip install --no-cache-dir -r requirements_backend.txt

# Install bot dependencies
COPY bot/requirements.txt ./requirements_bot.txt
RUN pip install --no-cache-dir -r requirements_bot.txt

# Copy backend code (to /app so uvicorn can find app.main:app)
COPY backend/ .

# Copy bot code and runner
COPY bot/ ./bot/
COPY run_bot.py .

# Create upload directories
RUN mkdir -p uploads/masters

# Database path shared between backend and bot
ENV DATABASE_PATH=/app/salon.db

# Copy and set startup script
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 8000

CMD ["sh", "./start.sh"]
