import asyncio
import os
from playwright.async_api import async_playwright

async def save_avito_cookies():
    """Скрипт для сбора и проверки cookies Avito (mobile версия)"""
    
    COOKIES_FILE = "avito_session.json"
    
    async with async_playwright() as p:
        print("\n" + "="*70)
        print("🍪 СБОР И ПРОВЕРКА COOKIES ДЛЯ AVITO (MOBILE)")
        print("="*70 + "\n")
        
        mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        
        print("="*70)
        print("📱 ЭТАП 1: СБОР COOKIES")
        print("="*70 + "\n")
        
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--window-size=390,844',
                f'--user-agent={mobile_ua}',
            ]
        )
        
        context = await browser.new_context(
            user_agent=mobile_ua,
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            geolocation={"longitude": 37.6173, "latitude": 55.7558},
            permissions=["geolocation"],
        )
        
        page = await context.new_page()
        
        print("📱 Браузер запущен (iPhone 14 Pro)")
        print("\n" + "="*70)
        print("📋 ЧТО ДЕЛАТЬ:")
        print("="*70)
        print("\n1. 🔐 ЗАРЕГИСТРИРУЙСЯ или ВОЙДИ")
        print("2. 👀 ПОСМОТРИ 5-10 объявлений (30-60 сек каждое)")
        print("3. ⭐ ДОБАВЬ 2-3 в избранное")
        print("4. 🔍 ПОИЩИ квартиры")
        print("5. 📱 Походи 5-10 минут МИНИМУМ")
        print("6. ⏸️  Нажми Enter в терминале")
        print("\n" + "="*70 + "\n")
        
        print("🚀 Открываю m.avito.ru...\n")
        await page.goto("https://m.avito.ru/")
        
        print("⏳ ЖДУ твоих действий...")
        print("💡 МИНИМУМ 5-10 минут активности!\n")
        
        input("✅ Готово? Нажми Enter...")
        
        print("\n💾 Сохраняю cookies...")
        await context.storage_state(path=COOKIES_FILE)
        
        print("\n" + "="*70)
        print("✅ Cookies сохранены!")
        print("="*70)
        
        cookies = await context.cookies()
        print(f"\n📊 Сохранено: {len(cookies)} cookies")
        
        print("\n🔑 Важные:")
        for cookie in cookies:
            if cookie['name'] in ['u', 'sessid', 'sx', 'v', 'luri']:
                print(f"   ✅ {cookie['name']}: {cookie['value'][:30]}...")
        
        await browser.close()
        
        print("\n🔄 Проверяю cookies...\n")
        await asyncio.sleep(2)
        
        print("="*70)
        print("🔍 ЭТАП 2: ПРОВЕРКА")
        print("="*70 + "\n")
        
        browser2 = await p.chromium.launch(
            headless=False,
            args=[
                '--window-size=390,844',
                f'--user-agent={mobile_ua}',
            ]
        )
        
        context2 = await browser2.new_context(
            user_agent=mobile_ua,
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            geolocation={"longitude": 37.6173, "latitude": 55.7558},
            permissions=["geolocation"],
            storage_state=COOKIES_FILE
        )
        
        page2 = await context2.new_page()
        
        print("✅ Браузер с КУКАМИ запущен!")
        print("🔍 Проверяю авторизацию...\n")
        
        await page2.goto("https://m.avito.ru/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        is_logged_in = False
        profile_selectors = [
            '[data-marker="header/avatar"]',
            'a[href*="/profile"]',
            '[data-marker="profile"]'
        ]
        
        for selector in profile_selectors:
            elem = await page2.query_selector(selector)
            if elem:
                is_logged_in = True
                print(f"✅ Профиль найден: {selector}")
                break
        
        login_btn = await page2.query_selector('button:has-text("Войти"), a:has-text("Войти")')
        if login_btn:
            is_logged_in = False
        
        print("\n" + "="*70)
        if is_logged_in:
            print("✅✅✅ УСПЕХ! АВТОРИЗАЦИЯ РАБОТАЕТ!")
        else:
            print("⚠️ Авторизация не подтверждена (проверь визуально)")
        print("="*70)
        
        print("\n👀 Проверь визуально и нажми Enter...")
        input()
        
        await browser2.close()
        
        print("\n" + "="*70)
        print("📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("="*70)
        print("\n1. Загрузи на Railway:")
        print("   cd ~/parser-links")
        print("   git add avito_session.json")
        print("   git commit -m 'Add Avito cookies'")
        print("   git push origin main")
        print("\n2. Railway задеплоит автоматически!")
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(save_avito_cookies())
    except KeyboardInterrupt:
        print("\n⛔ Отменено")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
