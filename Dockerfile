FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY main.py .

# Запуск с динамическим портом из переменной $PORT
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
