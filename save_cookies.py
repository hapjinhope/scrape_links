import asyncio
from playwright.async_api import async_playwright

async def save_fresh_avito_cookies():
    """Сбор свежих cookies для Avito с нуля"""
    
    COOKIES_FILE = "avito_session.json"
    
    async with async_playwright() as p:
        print("\n" + "="*70)
        print("🍪 СБОР СВЕЖИХ COOKIES ДЛЯ AVITO (БЕЗ СТАРЫХ)")
        print("="*70 + "\n")
        
        # Берём реальный Desktop UA
        desktop_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        
        print("💻 Запускаю чистый браузер...")
        
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                f'--user-agent={desktop_ua}',
            ]
        )
        
        # Контекст БЕЗ старых cookies
        context = await browser.new_context(
            user_agent=desktop_ua,
            viewport=None,  # Автоподстройка под экран
            screen={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
        )
        
        # Антидетект
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        """)
        
        page = await context.new_page()
        
        print("✅ Браузер запущен (чистая сессия)\n")
        print("="*70)
        print("📋 ЧТО ДЕЛАТЬ:")
        print("="*70)
        print("\n🔐 1. ВОЙДИ НА АВИТО:")
        print("   • Используй телефон/email/соцсети")
        print("   • Подтверди СМС если попросят")
        print("   • Убедись что авторизован (видишь своё имя)")
        print("\n👀 2. АКТИВНОСТЬ (5-10 МИНУТ):")
        print("   • Открой 3-5 объявлений квартир")
        print("   • Проскролль каждое до конца")
        print("   • Добавь 1-2 в избранное")
        print("   • Поищи что-нибудь через поиск")
        print("\n💡 ВАЖНО:")
        print("   Чем больше действий - тем дольше живут cookies!")
        print("\n" + "="*70)
        print("⏸️  Нажми Enter когда готов → cookies сохранятся")
        print("="*70 + "\n")
        
        print("🚀 Открываю Авито...\n")
        await page.goto("https://www.avito.ru/", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        
        print("⏳ ЖДУ твоих действий (минимум 5-10 минут)...")
        print("⏸️  Нажми Enter когда готов...\n")
        
        try:
            input()
        except KeyboardInterrupt:
            print("\n⚠️ Прервано, но cookies сохраню...")
        
        print("\n💾 Сохраняю cookies...")
        
        try:
            await context.storage_state(path=COOKIES_FILE)
            
            cookies = await context.cookies()
            
            print("\n" + "="*70)
            print(f"✅ COOKIES СОХРАНЕНЫ: {COOKIES_FILE}")
            print("="*70)
            print(f"\n📊 Всего: {len(cookies)} cookies")
            
            # Проверяем важные
            important = ['u', 'sessid', 'sx', 'v', 'luri', 'buyer_laas_location']
            found = []
            
            print("\n🔑 Важные cookies:")
            for cookie in cookies:
                if cookie['name'] in important:
                    found.append(cookie['name'])
                    print(f"   ✅ {cookie['name']}: {cookie['value'][:40]}...")
            
            missing = set(important) - set(found)
            if missing:
                print(f"\n⚠️  Не найдено: {', '.join(missing)}")
            else:
                print(f"\n✅ Все важные cookies на месте!")
            
        except Exception as e:
            print(f"\n❌ Ошибка сохранения: {e}")
            await browser.close()
            return
        
        await browser.close()
        
        print("\n" + "="*70)
        print("📋 СЛЕДУЮЩИЕ ШАГИ:")
        print("="*70)
        print("\n1️⃣  Загрузи на Railway:")
        print("     git add avito_session.json")
        print("     git commit -m 'Fresh Avito cookies'")
        print("     git push origin main")
        print("\n2️⃣  Railway задеплоит автоматически")
        print("\n3️⃣  Проверь парсер:")
        print("     curl -X POST https://parser-links-production.up.railway.app/parse \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{\"url\": \"https://www.avito.ru/...\"}' | jq")
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(save_fresh_avito_cookies())
    except KeyboardInterrupt:
        print("\n⛔ Отменено")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
