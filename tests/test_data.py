"""
═══════════════════════════════════════════════════════════════════
ФАЙЛ: tests/test_data.py
НАЗНАЧЕНИЕ: Тестовые URL и данные для отладки парсеров
═══════════════════════════════════════════════════════════════════

ЧТО ЗДЕСЬ:
- Тестовые ссылки на объявления Avito и Cian
- Примеры для быстрой проверки работы парсеров

ЧТО ДЕЛАТЬ:
- Используй эти URL для тестирования локально
- Замени на свои ссылки при необходимости
- Для теста: python -c "from tests.test_data import TEST_URLS; print(TEST_URLS)"
═══════════════════════════════════════════════════════════════════
"""

# Тестовые URL для парсинга
TEST_URLS = {
    "avito": {
        "active": "https://www.avito.ru/moskva/kvartiry/2-k._kvartira_56m_714et._3404467894",
        "inactive": "https://www.avito.ru/moskva/kvartiry/snyat_1-k._kvartira_35m_312et._1234567890"
    },
    "cian": {
        "active": "https://www.cian.ru/rent/flat/291863952/",
        "inactive": "https://www.cian.ru/rent/flat/123456789/"
    }
}

# Ожидаемые поля в ответе (для валидации)
EXPECTED_FIELDS = {
    "avito": [
        "status", "price", "summary", "address", "metro",
        "description", "seller_name", "rooms_count", "total_area",
        "floor", "floors_total", "photos", "phone"
    ],
    "cian": [
        "status", "price", "summary", "address", "metro",
        "description", "jk", "total_area", "living_area",
        "floor", "floors_total", "photos", "phone", "amenities"
    ]
}

# Примеры успешных ответов (для документации)
SAMPLE_RESPONSES = {
    "avito_full": {
        "status": "active",
        "price": "50000 ₽",
        "summary": "2-к. квартира, 56 м², 7/14 эт.",
        "address": "Москва, улица Кржижановского, 17к2",
        "metro": ["Профсоюзная (10 мин)"],
        "rooms_count": "2",
        "total_area": "56 м²",
        "floor": "7",
        "floors_total": "14",
        "phone": "79991234567",
        "photos": ["https://..."]
    },
    "cian_check": {
        "status": "active",
        "price": "45 000 ₽/мес",
        "mode": "quick_check"
    }
}
