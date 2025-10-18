FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ КОПИРУЕМ ВСЁ (включая avito_session.json)
COPY . .

# ✅ Проверяем, что cookies файл скопирован
RUN ls -la avito_session.json || echo "⚠️ WARNING: avito_session.json не найден!"

# Запуск FastAPI через uvicorn (для продакшена)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
