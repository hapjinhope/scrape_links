#!/usr/bin/env python
"""
Тестирование парсеров Avito и CIAN
Запуск: python test_parsers.py
"""

import asyncio
import sys

# Проверяем импорты
print("🔍 Проверяем импорты...")
try:
    from app.parsers.avito_parser import parse_avito, parse_avito_phone_only
    print("✅ avito_parser импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта avito_parser: {e}")
    sys.exit(1)

try:
    from app.parsers.cian_parser import parse_cian
    print("✅ cian_parser импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта cian_parser: {e}")
    sys.exit(1)

try:
    from main import app
    print("✅ main.py импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта main: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ ВСЕ ИМПОРТЫ УСПЕШНЫ!")
print("="*60)

# Проверяем синтаксис функций
print("\n🔍 Проверяем функции...")

async def test_syntax():
    """Проверяем что функции определены правильно"""
    
    # Проверяем сигнатуры
    import inspect
    
    # Avito
    avito_sig = inspect.signature(parse_avito)
    print(f"✅ parse_avito: {avito_sig}")
    
    avito_phone_sig = inspect.signature(parse_avito_phone_only)
    print(f"✅ parse_avito_phone_only: {avito_phone_sig}")
    
    # CIAN
    cian_sig = inspect.signature(parse_cian)
    print(f"✅ parse_cian: {cian_sig}")
    
    # Проверяем async
    print("\n🔍 Проверяем async функции...")
    assert asyncio.iscoroutinefunction(parse_avito), "parse_avito должна быть async!"
    print("✅ parse_avito - async")
    
    assert asyncio.iscoroutinefunction(parse_avito_phone_only), "parse_avito_phone_only должна быть async!"
    print("✅ parse_avito_phone_only - async")
    
    assert asyncio.iscoroutinefunction(parse_cian), "parse_cian должна быть async!"
    print("✅ parse_cian - async")

# Запускаем тесты
try:
    asyncio.run(test_syntax())
except Exception as e:
    print(f"❌ Ошибка при проверке: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
print("="*60)

print("""
📝 Готово к коммиту!

Следующие шаги:
1. git add .
2. git commit -m "✨ Парсеры Avito и CIAN - готовы к продакшену"
3. git push

Для локального тестирования парсинга:
- Запусти: python main.py
- Тестируй эндпоинты через curl или Postman

Пример:
curl -X POST http://localhost:8000/parse \\
  -H "Content-Type: application/json" \\
  -d '{"url": "https://www.avito.ru/..."}' 

❌ ВАЖНО: Реальное тестирование нужно на живых ссылках!
""")
