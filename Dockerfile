FROM python:3.11-slim

WORKDIR /app

# Установка системных утилит (curl для healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Делаем скрипт запуска исполняемым
RUN chmod +x /app/scripts/entrypoint.sh 2>/dev/null || true

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed_data && uvicorn src.main:app --host 0.0.0.0 --port 8000"]
