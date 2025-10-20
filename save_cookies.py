import asyncio
import os
import json
from playwright.async_api import async_playwright

async def save_avito_cookies():
    """Улучшенный скрипт сбора cookies Avito"""
    
    COOKIES_FILE = "avito_session.json"
    
    async with async_playwright() as p:
        print("\n" + "="*70)
        print("🍪 СБОР COOKIES AVITO")
        print("="*70 + "\n")
        
        desktop_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # ЭТАП 1: Сбор cookies
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--window-size=1920,1080',
                f'--user-agent={desktop_ua}',
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
            ]
        )
        
        context = await browser.new_context(
            user_agent=desktop_ua,
            viewport={"width": 1920, "height": 1080},
            screen={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            geolocation={"longitude": 37.6173, "latitude": 55.7558},
            permissions=["geolocation", "notifications"],
        )
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        """)
        
        page = await context.new_page()
        
        print("💻 Браузер запущен (Desktop)")
        print("\n📋 ИНСТРУКЦИЯ:")
        print("1. 🔐 Войди в аккаунт")
        print("2. 👀 Посмотри 3-5 объявлений")
        print("3. ⭐ Добавь в избранное")
        print("4. 🔍 Поищи квартиры")
        print("5. ⏰ Минимум 5-10 минут активности\n")
        
        await page.goto("https://www.avito.ru/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        print("⏳ Действуй... Жми Enter когда готов\n")
        
        try:
            input()
        except KeyboardInterrupt:
            print("\n⚠️ Прервано, но cookies сохраню...")
        
        print("\n💾 Сохраняю cookies...")
        
        try:
            await context.storage_state(path=COOKIES_FILE)
            cookies = await context.cookies()
            
            print(f"✅ Сохранено: {len(cookies)} cookies")
            
            # Проверка важных cookies
            important = ['u', 'sessid', 'sx', 'v', 'luri']
            found = sum(1 for c in cookies if c['name'] in important)
            
            if found >= 3:
                print(f"✅ Найдено {found}/5 важных cookies - отлично!")
            else:
                print(f"⚠️ Найдено только {found}/5 важных cookies")
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            await browser.close()
            return
        
        await browser.close()
        
        # ЭТАП 2: Проверка в новом браузере
        print("\n🔄 Проверка cookies...\n")
        await asyncio.sleep(2)
        
        browser2 = await p.chromium.launch(
            headless=False,
            args=['--window-size=1920,1080', f'--user-agent={desktop_ua}']
        )
        
        context2 = await browser2.new_context(
            user_agent=desktop_ua,
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            storage_state=COOKIES_FILE
        )
        
        page2 = await context2.new_page()
        
        print("✅ Новый браузер с cookies запущен")
        print("🔍 Проверяю авторизацию...\n")
        
        await page2.goto("https://www.avito.ru/", wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        is_logged_in = False
        
        # Проверка авторизации
        profile_button = await page2.query_selector('[data-marker="header/username-button"]')
        if profile_button:
            try:
                username = await profile_button.inner_text()
                is_logged_in = True
                print(f"✅ АВТОРИЗОВАН! Пользователь: {username.strip()}")
            except:
                pass
        
        if not is_logged_in:
            login_btn = await page2.query_selector('button:has-text("Вход и регистрация")')
            if not login_btn or not await login_btn.is_visible():
                is_logged_in = True
                print("✅ АВТОРИЗОВАН (кнопка входа скрыта)")
        
        print("\n" + "="*70)
        if is_logged_in:
            print("✅✅✅ УСПЕХ! АВТОРИЗАЦИЯ РАБОТАЕТ!")
        else:
            print("⚠️⚠️⚠️ АВТОРИЗАЦИЯ НЕ ПОДТВЕРЖДЕНА")
            print("    Проверь визуально в браузере!")
        print("="*70)
        
        print("\n👀 Проверь визуально, жми Enter для закрытия...")
        
        try:
            input()
        except KeyboardInterrupt:
            pass
        
        await browser2.close()
        
        print("\n" + "="*70)
        print("📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("="*70)
        print("\n1. Загрузи cookies на Railway:")
        print("   git add avito_session.json")
        print("   git commit -m 'Update cookies'")
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
