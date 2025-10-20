"""
═══════════════════════════════════════════════════════════════════
ФАЙЛ: config/settings.py
НАЗНАЧЕНИЕ: Системные настройки и константы приложения
═══════════════════════════════════════════════════════════════════

ЧТО ЗДЕСЬ:
- Константы для парсера (User-Agent, пути к файлам)
- Настройки браузера Playwright
- Таймауты и параметры подключений
- Настройки сервера (порт, хост)

ЧТО ДЕЛАТЬ:
- Если нужно изменить порт → измени PORT
- Если нужно изменить таймауты → измени BROWSER_TIMEOUT
- Если нужно изменить User-Agent → измени DESKTOP_UA
═══════════════════════════════════════════════════════════════════
"""

import os

# ============== ФАЙЛЫ И ПУТИ ==============
COOKIES_FILE = "avito_session.json"  # Файл для хранения cookies Avito

# ============== БРАУЗЕР ==============
DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

BROWSER_ARGS = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    '--window-size=1920,1080',
    '--lang=ru-RU',
]

# ============== ТАЙМАУТЫ ==============
BROWSER_TIMEOUT = 90000  # 90 секунд
PAGE_TIMEOUT = 60000     # 60 секунд

# ============== СЕРВЕР ==============
PORT = int(os.environ.get("PORT", 8000))  # Railway автоматически установит PORT
HOST = "0.0.0.0"  # Слушать все интерфейсы
