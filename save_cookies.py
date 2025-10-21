import asyncio
import json
from playwright.async_api import async_playwright

async def save_avito_cookies():
    """Простой и надёжный сбор cookies Avito"""
    
    COOKIES_FILE = "avito_session.json"
    
    async with async_playwright() as p:
        print("\n" + "="*60)
        print("🍪 СБОР COOKIES AVITO")
        print("="*60 + "\n")
        
        desktop_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # ЗАПУСК БРАУЗЕРА
        browser = await p.chromium.launch(
            headless=False,  # Видимый браузер
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
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            geolocation={"longitude": 37.6173, "latitude": 55.7558},
            permissions=["geolocation"],
        )
        
        # Скрываем автоматизацию
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        """)
        
        page = await context.new_page()
        
        print("✅ Браузер запущен\n")
        print("📋 ЧТО ДЕЛАТЬ:")
        print("-" * 60)
        print("1. Войди в аккаунт Авито (телефон/email)")
        print("2. Посмотри 3-5 объявлений квартир")
        print("3. Добавь 1-2 в избранное")
        print("4. Поищи квартиры через поиск")
        print("5. Минимум 5 минут активности")
        print("-" * 60)
        print("\n💡 Чем больше действий - тем лучше cookies!\n")
        
        # Открываем Avito
        print("🌐 Открываю www.avito.ru...\n")
        try:
            await page.goto("https://www.avito.ru/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
            
            # Закрываем попапы
            try:
                close_selectors = [
                    "button:has-text('Закрыть')",
                    "button:has-text('Понятно')",
                    "[aria-label='Закрыть']"
                ]
                for selector in close_selectors:
                    btn = await page.query_selector(selector)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(0.5)
            except:
                pass
                
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
            print("Попробуй вручную перейти на avito.ru")
        
        print("⏳ Действуй на сайте...")
        print("⏸️  Нажми Enter когда закончишь\n")
        
        # Ждём Enter
        try:
            input()
        except KeyboardInterrupt:
            print("\n⚠️ Прервано, но cookies сохраню...")
        
        # СОХРАНЕНИЕ COOKIES
        print("\n💾 Сохраняю cookies...")
        
        try:
            await context.storage_state(path=COOKIES_FILE)
            cookies = await context.cookies()
            
            print(f"✅ Сохранено {len(cookies)} cookies в {COOKIES_FILE}")
            
            # Проверка важных cookies
            important_names = ['u', 'sessid', 'sx', 'v', 'luri', 'buyer_laas_location']
            found_cookies = [c for c in cookies if c['name'] in important_names]
            
            if found_cookies:
                print(f"\n🔑 Найдено {len(found_cookies)}/{len(important_names)} важных cookies:")
                for cookie in found_cookies:
                    value_preview = cookie['value'][:30] + "..." if len(cookie['value']) > 30 else cookie['value']
                    print(f"   ✓ {cookie['name']}: {value_preview}")
            
            if len(found_cookies) >= 3:
                print(f"\n✅ Отлично! Cookies хорошие")
            else:
                print(f"\n⚠️ Только {len(found_cookies)} важных cookies - может не хватить")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
            await browser.close()
            return
        
        await browser.close()
        print("\n✅ Первый браузер закрыт")
        
        # ПРОВЕРКА В НОВОМ БРАУЗЕРЕ
        print("\n" + "="*60)
        print("🔍 ПРОВЕРКА COOKIES")
        print("="*60 + "\n")
        
        await asyncio.sleep(2)
        
        browser2 = await p.chromium.launch(
            headless=False,
            args=['--window-size=1920,1080', f'--user-agent={desktop_ua}', '--no-sandbox']
        )
        
        context2 = await browser2.new_context(
            user_agent=desktop_ua,
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            storage_state=COOKIES_FILE  # Загружаем сохранённые cookies
        )
        
        page2 = await context2.new_page()
        
        print("✅ Новый браузер с cookies запущен")
        print("🔍 Проверяю авторизацию...\n")
        
        try:
            await page2.goto("https://www.avito.ru/", wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")
        
        # Проверка авторизации
        is_logged_in = False
        username = None
        
        # Способ 1: Кнопка профиля
        try:
            profile_btn = await page2.query_selector('[data-marker="header/username-button"]')
            if profile_btn:
                username = await profile_btn.inner_text()
                is_logged_in = True
                print(f"✅ АВТОРИЗОВАН! Пользователь: {username.strip()}")
        except:
            pass
        
        # Способ 2: Кнопка входа отсутствует
        if not is_logged_in:
            try:
                login_btn = await page2.query_selector('button:has-text("Вход и регистрация")')
                if not login_btn:
                    is_logged_in = True
                    print("✅ АВТОРИЗОВАН (кнопка входа не найдена)")
            except:
                pass
        
        # Способ 3: Аватар пользователя
        if not is_logged_in:
            try:
                avatar = await page2.query_selector('[data-marker="header/avatar"]')
                if avatar and await avatar.is_visible():
                    is_logged_in = True
                    print("✅ АВТОРИЗОВАН (найден аватар)")
            except:
                pass
        
        print("\n" + "="*60)
        if is_logged_in:
            print("🎉🎉🎉 УСПЕХ! АВТОРИЗАЦИЯ РАБОТАЕТ!")
            print("\nCookies валидны и готовы к использованию")
        else:
            print("⚠️⚠️⚠️ АВТОРИЗАЦИЯ НЕ ПОДТВЕРЖДЕНА")
            print("\nПроверь визуально в браузере:")
            print("• Виден ли твой профиль справа вверху?")
            print("• Есть ли кнопка 'Вход и регистрация'?")
        print("="*60)
        
        print("\n👀 Проверь визуально, жми Enter для закрытия...")
        
        try:
            input()
        except KeyboardInterrupt:
            pass
        
        await browser2.close()
        
        # ИНСТРУКЦИЯ ПО ЗАГРУЗКЕ
        print("\n" + "="*60)
        print("📤 ЗАГРУЗКА COOKIES НА RAILWAY")
        print("="*60)
        print("\n1. Добавь файл в Git:")
        print("   git add avito_session.json")
        print("\n2. Закоммить:")
        print("   git commit -m 'Add Avito cookies'")
        print("\n3. Запуш:")
        print("   git push origin main")
        print("\n4. Railway автоматически задеплоит!")
        print("\n5. Проверь работу парсера:")
        print("   Открой: https://твой-проект.up.railway.app/docs")
        print("="*60 + "\n")

if __name__ == "__main__":
    try:
        asyncio.run(save_avito_cookies())
    except KeyboardInterrupt:
        print("\n⛔ Отменено пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
