from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import asyncio
import os
from playwright.async_api import async_playwright
import random

app = FastAPI(title="Парсер квартир Avito с Cookies")

class ParseRequest(BaseModel):
    url: HttpUrl

# Путь к cookies
COOKIES_FILE = "cookies/avito_session.json"

async def close_modals(page):
    try:
        selectors = [
            "button:has-text('Не интересно')",
            "[data-marker*='modal/close']",
            ".modal__close",
        ]
        for selector in selectors:
            button = await page.query_selector(selector)
            if button:
                await button.click()
                await asyncio.sleep(1)
                return True
        return False
    except Exception as e:
        print(f"[ERROR] close_modals error: {e}")
        return False

async def click_continue_if_exists(page):
    try:
        selectors = [
            "button:has-text('Продолжить')",
            "[data-marker*='continue']",
        ]
        for selector in selectors:
            button = await page.query_selector(selector)
            if button:
                await button.click()
                await asyncio.sleep(5)
                return True
        return False
    except Exception as e:
        print(f"[ERROR] click_continue_if_exists error: {e}")
        return False

async def parse_avito(url: str):
    print(f"[INFO] Starting Avito parse for URL: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--window-size=1920,1080',
                '--lang=ru-RU',
            ],
            timeout=90000
        )
        
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "geolocation": {"longitude": 37.6173, "latitude": 55.7558},
            "permissions": ["geolocation"],
        }
        
        if os.path.exists(COOKIES_FILE):
            print(f"[INFO] Loading cookies from {COOKIES_FILE}")
            context_options["storage_state"] = COOKIES_FILE
        else:
            print(f"[WARNING] Cookies file {COOKIES_FILE} not found")
        
        context = await browser.new_context(**context_options)
        
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
            "Referer": "https://www.google.com/",
        })
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        page.set_default_navigation_timeout(90000)
        
        try:
            print("[INFO] Loading Avito main page")
            await page.goto("https://www.avito.ru/", wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(random.randint(2000, 4000))
            await close_modals(page)
            await click_continue_if_exists(page)
            print("[SUCCESS] Avito main page loaded")
        except Exception as e:
            print(f"[ERROR] Main page load failed: {e}")
            
        try:
            print("[INFO] Navigating to listing")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            await close_modals(page)
            await click_continue_if_exists(page)
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(200, 500)
                await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                await page.wait_for_timeout(random.randint(800, 1500))
                await page.mouse.move(random.randint(200, 1000), random.randint(200, 800))
                await page.wait_for_timeout(random.randint(500, 1000))
            print("[SUCCESS] Listing loaded")
        except Exception as e:
            print(f"[ERROR] Listing load failed: {e}")
        
        try:
            await context.storage_state(path=COOKIES_FILE)
            print(f"[INFO] Cookies updated")
        except Exception as e:
            print(f"[WARNING] Cookies update failed: {e}")
        
        html = await page.content()
        title = await page.title()
        if ('доступ ограничен' in html.lower() or
            'access denied' in html.lower() or
            'captcha' in title.lower()):
            print("[WARNING] Site blocked or captcha detected")
            await browser.close()
            return {'error': 'blocked', 'message': 'Avito заблокировал'}
        
        flat = {}
        try:
            title_elem = await page.query_selector('[data-marker="item-view/title-info"], h1')
            flat['title'] = await title_elem.inner_text() if title_elem else None
        except:
            flat['title'] = None
        try:
            price_elem = await page.query_selector('[data-marker="item-view/item-price"]')
            flat['price'] = await price_elem.inner_text() if price_elem else None
        except:
            flat['price'] = None
        try:
            addr_elem = await page.query_selector('[data-marker="item-view/location-address"]')
            flat['address'] = await addr_elem.inner_text() if addr_elem else None
        except:
            flat['address'] = None
        try:
            desc_elem = await page.query_selector('[data-marker="item-view/item-description"]')
            flat['description'] = await desc_elem.inner_text() if desc_elem else None
        except:
            flat['description'] = None
        
        params = {}
        try:
            params_sections = await page.query_selector_all('[data-marker="item-view/item-params"]')
            for section in params_sections:
                items = await section.query_selector_all('li')
                for item in items:
                    try:
                        text = await item.inner_text()
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
                src = await img.get_attribute('src')
                if src and '.jpg' in src:
                    clean = src.split('?')[0]
                    if len(clean) > 50:
                        photos.append(clean)
            flat['photos'] = list(set(photos))
        except:
            flat['photos'] = []
        await browser.close()
        return flat

@app.get("/")
async def root():
    return {
        "service": "Парсер Avito с Cookies",
        "cookies_loaded": os.path.exists(COOKIES_FILE),
        "endpoints": {
            "POST /parse": "Парсить объявление {\"url\": \"https://...\"}"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    url_str = str(request.url)
    try:
        if 'avito.ru' not in url_str:
            raise HTTPException(status_code=400, detail="Только Avito поддерживается")
        print(f"[INFO] Запрос на парсинг: {url_str}")
        clear_screenshots()  # Очистка скриншотов перед началом
        result = await parse_avito(url_str)
        result['source'] = 'avito'
        result['url'] = url_str
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[ERROR] Ошибка в /parse: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

def clear_screenshots():
    import shutil
    screenshots_folder = Path("screenshots")
    if screenshots_folder.exists():
        print(f"[INFO] Удаляем старые скриншоты из {screenshots_folder}")
        shutil.rmtree(screenshots_folder)
    screenshots_folder.mkdir(exist_ok=True)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print(f"[INFO] Запуск на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
