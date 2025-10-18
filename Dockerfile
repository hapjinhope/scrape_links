FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# Установка Chrome и зависимостей для Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    chromium-browser \
    chromium-chromedriver \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё приложение (включая avito_session.json)
COPY . .

# Проверяем наличие cookies
RUN ls -la avito_session.json || echo "⚠️ WARNING: avito_session.json не найден!"

# Переменная окружения для Chromium
ENV CHROME_BIN=/usr/bin/chromium-browser
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Запуск FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
