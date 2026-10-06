FROM python:3.11-slim

WORKDIR /app

# 1. Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements
COPY lib/requirements.txt /app/lib/requirements.txt
COPY services/frontend_logs/requirements.txt /app/services/frontend_logs/requirements.txt

# Устанавливаем зависимости
WORKDIR /app/services/frontend_logs
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код с сохранением структуры
COPY lib/__init__.py /app/lib/__init__.py
COPY lib/utils /app/lib/utils

# Создаем структуру services/frontend_logs
COPY services/frontend_logs/app /app/services/frontend_logs/app
COPY services/frontend_logs/__init__.py /app/services/frontend_logs/__init__.py
COPY services/__init__.py /app/services/__init__.py

# Настраиваем окружение
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

WORKDIR /app

CMD ["python", "-m", "uvicorn", "services.frontend_logs.app.main:app", "--host", "0.0.0.0", "--port", "8003"]
