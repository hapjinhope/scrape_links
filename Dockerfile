FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY main.py .

# Expose порт (Railway автоматически использует переменную $PORT)
EXPOSE 8000

# Запуск uvicorn (НЕ python main.py!)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
