FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Установка Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN ls -la avito_session.json || echo "⚠️ avito_session.json не найден"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
