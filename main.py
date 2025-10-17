from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import asyncio
from pathlib import Path
import os
from playwright.async_api import async_playwright
import random
import shutil
from datetime import datetime

app = FastAPI(title="Парсер Avito с вшитыми Cookies")

class ParseRequest(BaseModel):
    url: HttpUrl

# ========================================
# АВТОСГЕНЕРИРОВАННЫЕ COOKIES И ДЕЙСТВИЯ
# ========================================

HARDCODED_COOKIES = [
    {'name': 'USER_ID', 'value': '94e28901-a262-4538-9cb6-22fc6bc7a6c9', 'domain': 'pixel.dsp.onetarget.ru', 'path': '/buzzoola', 'expires': 1795298485.891638},
    {'name': 'BUZZOOLA_USER_ID', 'value': '714d9607-d140-4d08-6aff-914adf04d43a', 'domain': 'pixel.dsp.onetarget.ru', 'path': '/buzzoola', 'expires': 1791496885.891782},
    {'name': 'idntfy', 'value': 'VU6qoaIa0nUngQ4', 'domain': '.traffaret.com', 'path': '/core/', 'expires': 1795297864.818379},
    {'name': 'as', 'value': 'T72MF2jyukYwcONTaPK6Rz6yv0Bo8rpI', 'domain': 'kimberlite.io', 'path': '/rtb', 'expires': 1761342664.084972},
    {'name': 'da', 'value': 'z-x-nQAAAAHwVJr2AAAAARZ0j-YAAAAB', 'domain': 'kimberlite.io', 'path': '/rtb', 'expires': 1761342683.328216},
    {'name': 'idntfy', 'value': 'VU6qoaIa0nUngQ4', 'domain': '.traffaret.com', 'path': '/c/', 'expires': 1795297864.818297},
    {'name': 'srv_id', 'value': 'sLBRa5b-0C4yVWFV.JoyroKHC3xifb7n3BtXh9mmP6Pw7qQCKT2HhfFanPp2cMwwgJjs9UqASm3UKcyyw4Jpr.RLeFj_YHoVKLLBM0rCZnLUKFMCk2kHz4Ak4mbFTUIxM=.web', 'domain': '.avito.ru', 'path': '/', 'expires': 1795297854.767128},
    {'name': 'gMltIuegZN2COuSe', 'value': 'EOFGWsm50bhh17prLqaIgdir1V0kgrvN', 'domain': '.avito.ru', 'path': '/', 'expires': 1760825619.061897},
    {'name': 'u', 'value': '37bd62q6.lg004b.os4cayifqsg0', 'domain': '.avito.ru', 'path': '/', 'expires': 1795297854.768183},
    {'name': 'v', 'value': '1760737854', 'domain': '.avito.ru', 'path': '/', 'expires': 1760741020.109408},
    {'name': 'i', 'value': 'IlwA2bJ2UZy3umQOzrmM8W/iAw1btrNQ73y459aD2w/thCbGCk6Svyn6ZsfDQsqY/DaDO3UajQY2yu5DxSmJ8K3gZEw=', 'domain': '.yandex.ru', 'path': '/', 'expires': 1795297855.241842},
    {'name': 'yandexuid', 'value': '2901145061760737855', 'domain': '.yandex.ru', 'path': '/', 'expires': 1795297857.443977},
    {'name': 'yashr', 'value': '1990324311760737855', 'domain': '.yandex.ru', 'path': '/', 'expires': 1792273855},
    {'name': 'cssid', 'value': 'a1e86544-2e6f-4751-b439-03221df67840', 'domain': '.www.avito.ru', 'path': '/', 'expires': 1760739655},
    {'name': 'cssid_exp', 'value': '1760739655970', 'domain': '.www.avito.ru', 'path': '/', 'expires': 1760739655},
    {'name': 'cookie_consent_shown', 'value': '1', 'domain': 'www.avito.ru', 'path': '/', 'expires': 1765921856},
    {'name': 'buyer_laas_location', 'value': '621540', 'domain': '.avito.ru', 'path': '/', 'expires': 1792275196.425957},
    {'name': 'luri', 'value': 'all', 'domain': '.avito.ru', 'path': '/', 'expires': 1760824256.141371},
    {'name': 'buyer_location_id', 'value': '621540', 'domain': '.avito.ru', 'path': '/', 'expires': 1792275218.005729},
    {'name': '_ym_uid', 'value': '1760737857312067280', 'domain': '.avito.ru', 'path': '/', 'expires': 1792273857},
]

async def apply_hardcoded_cookies(context):
    """Применяет вшитые cookies"""
    try:
        await context.add_cookies(HARDCODED_COOKIES)
        print(f"[INFO] 🍪 Применены вшитые cookies ({len(HARDCODED_COOKIES)} шт.)")
        return True
    except Exception as e:
        print(f"[WARNING] Ошибка cookies: {e}")
        return False

async def emulate_human_behavior(page):
    """Эмуляция человека"""
    scroll_amounts = [429, 246, 335]
    for amount in scroll_amounts:
        try:
            await page.evaluate(f'window.scrollBy(0, {amount})')
            await asyncio.sleep(random.uniform(0.5, 1.0))
        except:
            pass
    
    # Дополнительные случайные движения
    for _ in range(3):
        x, y = random.randint(100, 800), random.randint(100, 600)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))
    
    print("[INFO] ✅ Эмуляция человека завершена")

# ========================================

async def close_modals(page):
    try:
        selectors = [
            "button:has-text('Не интересно')",
            "[data-marker*='modal/close']",
            ".modal__close",
            "button[aria-label='Закрыть']",
        ]
        for selector in selectors:
            try:
                buttons = await page.query_selector_all(selector)
                for button in buttons:
                    if await button.is_visible():
                        await button.click()
                        await asyncio.sleep(1)
            except:
                continue
        await page.keyboard.press('Escape')
        return True
    except:
        return False

async def click_continue_if_exists(page):
    try:
        selectors = ["button:has-text('Продолжить')", "[data-marker*='continue']"]
        for selector in selectors:
            button = await page.query_selector(selector)
            if button and await button.is_visible():
                await button.click()
                await asyncio.sleep(3)
                return True
        return False
    except:
        return False

async def parse_avito(url: str):
    print(f"[INFO] Начинаю парсинг: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--window-size=1920,1080",
                "--lang=ru-RU",
            ],
            timeout=90000
        )
        
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "geolocation": {"longitude": 37.6173, "latitude": 55.7558},
            "permissions": ["geolocation"]
        }
        
        context = await browser.new_context(**context_options)
        
        # ПРИМЕНЯЕМ ВШИТЫЕ COOKIES
        await apply_hardcoded_cookies(context)
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [{name: 'Chrome PDF Plugin'}, {name: 'Chrome PDF Viewer'}]
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru'] });
            window.chrome = { runtime: {} };
        """)
        
        await context.set_extra_http_headers({
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": "https://www.google.com/"
        })
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        page.set_default_navigation_timeout(90000)
        
        # Главная
        try:
            print("[INFO] Загружаю главную Avito")
            await page.goto("https://www.avito.ru/", wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(2000, 4000))
            
            # ЭМУЛЯЦИЯ ЧЕЛОВЕКА
            await emulate_human_behavior(page)
            
            await close_modals(page)
            await click_continue_if_exists(page)
            print("[SUCCESS] Главная загружена")
        except Exception as e:
            print(f"[ERROR] Ошибка главной: {e}")
        
        # Объявление
        try:
            print("[INFO] Переход к объявлению")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            # Закрываем модалки (5 попыток)
            for attempt in range(5):
                await close_modals(page)
                await click_continue_if_exists(page)
                await page.wait_for_timeout(500)
            
            # Скроллинг
            for _ in range(random.randint(2, 4)):
                await page.evaluate(f"window.scrollBy(0, {random.randint(200, 500)})")
                await page.wait_for_timeout(random.randint(800, 1500))
            
            print("[SUCCESS] Объявление загружено")
        except Exception as e:
            print(f"[ERROR] Ошибка объявления: {e}")
        
        # Проверка блокировки
        html = await page.content()
        title = await page.title()
        
        print(f"[DEBUG] Заголовок: {title}")
        
        if ('доступ ограничен' in html.lower() or
            'access denied' in html.lower() or
            'captcha' in title.lower()):
            print("[WARNING] Блокировка обнаружена")
            await browser.close()
            return {'error': 'blocked', 'message': 'Avito заблокировал'}
        
        # ПАРСИНГ
        flat = {}
        try:
            title_elem = await page.query_selector('[data-marker="item-view/title-info"], h1')
            flat['title'] = (await title_elem.inner_text()).strip() if title_elem else None
        except: 
            flat['title'] = None
        
        try:
            price_elem = await page.query_selector('[data-marker="item-view/item-price"]')
            flat['price'] = (await price_elem.inner_text()).strip() if price_elem else None
        except: 
            flat['price'] = None
        
        try:
            addr_elem = await page.query_selector('[data-marker="item-view/location-address"]')
            flat['address'] = (await addr_elem.inner_text()).strip() if addr_elem else None
        except: 
            flat['address'] = None
        
        try:
            desc_elem = await page.query_selector('[data-marker="item-view/item-description"]')
            flat['description'] = (await desc_elem.inner_text()).strip() if desc_elem else None
        except: 
            flat['description'] = None
        
        params = {}
        try:
            sections = await page.query_selector_all('[data-marker="item-view/item-params"]')
            for section in sections:
                items = await section.query_selector_all("li")
                for item in items:
                    try:
                        text = (await item.inner_text()).strip()
                        if ':' in text:
                            k, v = text.split(':', 1)
                            params[k.strip()] = v.strip()
                    except:
                        continue
        except: 
            pass
        flat['params'] = params
        
        try:
            photos = []
            imgs = await page.query_selector_all('img[src*="avito.st"]')
            for img in imgs:
                src = await img.get_attribute("src")
                if src and ".jpg" in src:
                    clean_src = src.split("?")[0]
                    if len(clean_src) > 50:
                        photos.append(clean_src)
            flat['photos'] = list(set(photos))
        except:
            flat['photos'] = []
        
        await browser.close()
        return flat

@app.get("/")
async def root():
    return {
        "service": "Парсер Avito с вшитыми Cookies",
        "cookies_count": len(HARDCODED_COOKIES),
        "endpoints": {
            "POST /parse": "Парсить объявление (только Avito)"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    url_str = str(request.url)
    try:
        if "avito.ru" not in url_str:
            raise HTTPException(status_code=400, detail="Только Avito")
        print(f"[INFO] Запрос: {url_str}")
        result = await parse_avito(url_str)
        result["source"] = "avito"
        result["url"] = url_str
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print(f"[INFO] Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
