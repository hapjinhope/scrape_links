FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN ls -la avito_session.json || echo "⚠️ avito_session.json не найден"
RUN chmod 644 avito_session.json

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
