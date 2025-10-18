from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import asyncio
import re
from playwright.async_api import async_playwright
import random
import os

app = FastAPI(title="Парсер квартир Avito & Cian")

class ParseRequest(BaseModel):
    url: HttpUrl

COOKIES_FILE = "avito_session.json"

# ✅ Bright Data прокси креды
PROXY_CONFIG = {
    "server": os.getenv("PROXY_SERVER", "brd.superproxy.io:33335"),
    "username": os.getenv("PROXY_USERNAME", "brd-customer-hl_e57b9d94-zone-residential_proxy1"),
    "password": os.getenv("PROXY_PASSWORD", "wh9kp18xt2ot")
}

async def human_like_mouse_move(page, from_x, from_y, to_x, to_y):
    steps = random.randint(15, 30)
    for i in range(steps):
        progress = i / steps
        curve = random.uniform(-10, 10)
        x = from_x + (to_x - from_x) * progress + curve
        y = from_y + (to_y - from_y) * progress + curve
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.03))

async def emulate_human_behavior(page):
    start_x, start_y = random.randint(100, 300), random.randint(100, 300)
    end_x, end_y = random.randint(400, 800), random.randint(200, 600)
    await human_like_mouse_move(page, start_x, start_y, end_x, end_y)
    
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    for _ in range(random.randint(2, 4)):
        scroll_amount = random.randint(150, 400)
        if random.random() < 0.3:
            scroll_amount = -scroll_amount
        await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.8, 2.0))
    
    for _ in range(random.randint(2, 5)):
        jitter_x = end_x + random.randint(-5, 5)
        jitter_y = end_y + random.randint(-5, 5)
        await page.mouse.move(jitter_x, jitter_y)
        await asyncio.sleep(random.uniform(0.1, 0.3))

async def close_modals(page):
    try:
        selectors = [
            "button:has-text('Не интересно')",
            "[data-marker*='modal/close']",
            ".modal__close",
            "button[aria-label='Закрыть']",
        ]
        for selector in selectors:
            button = await page.query_selector(selector)
            if button:
                await button.click()
                await asyncio.sleep(1)
                return True
        return False
    except:
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
                box = await button.bounding_box()
                if box:
                    click_x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
                    click_y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
                    await page.mouse.move(click_x, click_y)
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    await page.mouse.click(click_x, click_y)
                    await asyncio.sleep(5)
                    return True
        return False
    except:
        return False

async def parse_avito(url: str):
    async with async_playwright() as p:
        # ✅ Добавляем прокси в launch
        browser = await p.chromium.launch(
            headless=True,
            proxy=PROXY_CONFIG,  # ← ПРОКСИ!
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
            "timezone_id": "Asia/Almaty",  # ← Казахстан timezone!
            "geolocation": {"longitude": 76.9286, "latitude": 43.2220},  # Алматы
            "permissions": ["geolocation"],
        }
        
        if os.path.exists(COOKIES_FILE):
            print(f"[INFO] 🍪 Загружаю cookies")
            context_options["storage_state"] = COOKIES_FILE
        
        context = await browser.new_context(**context_options)
        
        # ✅ Блокировка картинок (экономия 60% трафика!)
        await context.route('**/*.{png,jpg,jpeg,gif,webp,svg}', lambda route: route.abort())
        await context.route('**/yandex-metrika/**', lambda route: route.abort())
        await context.route('**/google-analytics/**', lambda route: route.abort())
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin'},
                    {name: 'Chrome PDF Viewer'},
                    {name: 'Native Client'}
                ],
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru', 'kk-KZ'] });
            window.chrome = { runtime: {} };
        """)
        
        await context.set_extra_http_headers({
            "Accept-Language": "ru-RU,ru;q=0.9,kk;q=0.8",
            "Referer": "https://www.google.com/",
        })
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        try:
            print(f"[INFO] 🚀 Переход через Bright Data (Kazakhstan)...")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            await close_modals(page)
            await click_continue_if_exists(page)
            await emulate_human_behavior(page)
            
            print("[SUCCESS] ✅ Объявление загружено")
        except Exception as e:
            print(f"[ERROR] ❌ Ошибка: {e}")
        
        try:
            await context.storage_state(path=COOKIES_FILE)
        except:
            pass
        
        html = await page.content()
        title = await page.title()
        
        is_blocked = (
            'доступ ограничен' in html.lower() or
            'access denied' in html.lower() or
            'captcha' in title.lower()
        )
        
        if is_blocked:
            print("[WARNING] ⚠️ Блокировка")
            await browser.close()
            return {'error': 'blocked', 'message': 'Avito заблокировал', 'proxy': 'Bright Data (Kazakhstan)'}
        
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
            params_sections = await page.query_selector_all('[data-marker="item-view/item-params"]')
            for section in params_sections:
                items = await section.query_selector_all('li')
                for item in items:
                    try:
                        text = (await item.inner_text()).strip()
                        if ':' in text:
                            key, value = text.split(':', 1)
                            params[key.strip()] = value.strip()
                    except: 
                        continue
        except: 
            pass
        flat['params'] = params

        flat['photos'] = []  # Отключаем для экономии трафика
        flat['proxy'] = 'Bright Data (Kazakhstan 🇰🇿)'

        await browser.close()
        return flat

async def parse_cian(url: str):
    # Циан БЕЗ прокси (работает напрямую)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU"
        )
        
        # Блокировка картинок
        await context.route('**/*.{png,jpg,jpeg,gif,webp,svg}', lambda route: route.abort())
        
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        flat = {}
        html = await page.content()
        
        try:
            flat['title'] = (await page.inner_text("h1")).strip()
        except: 
            m = re.search(r'(Сдается [^<\n]+м²)', html)
            flat['title'] = m.group(1) if m else None

        m = re.search(r'ЖК\s*[«"]([^»"<\n]+)', html)
        flat['complex'] = m.group(1).strip() if m else None

        try:
            price_el = await page.query_selector("[data-testid='price-amount']")
            flat['price'] = (await price_el.inner_text()).strip() if price_el else None
        except: 
            flat['price'] = None

        try:
            addr_items = await page.query_selector_all('[data-name="AddressItem"]')
            address_parts = []
            for item in addr_items:
                address_parts.append((await item.inner_text()).strip())
            flat['address'] = ', '.join(address_parts) if address_parts else None
        except: 
            flat['address'] = None

        try:
            metros = []
            for elem in await page.query_selector_all('[data-name="UndergroundItem"] a'):
                metros.append((await elem.inner_text()).strip())
            flat['metro'] = metros
        except: 
            flat['metro'] = []

        params = {}
        try:
            params_elems = await page.query_selector_all('[data-name="OfferSummaryInfoItem"]')
            for item in params_elems:
                try:
                    label_el = await item.query_selector('p[class*="color_gray60"]')
                    value_el = await item.query_selector('p[class*="color_text-primary"]')
                    if label_el and value_el:
                        key = (await label_el.inner_text()).strip()
                        value = (await value_el.inner_text()).strip()
                        params[key] = value
                except: 
                    continue
        except: 
            pass
        flat['params'] = params

        try:
            features = []
            feature_items = await page.query_selector_all('[data-name="FeaturesItem"]')
            for item in feature_items:
                try:
                    feature_text = (await item.inner_text()).strip()
                    if feature_text:
                        features.append(feature_text)
                except: 
                    continue
            flat['features'] = features
        except:
            flat['features'] = []

        try:
            desc_el = await page.query_selector("[data-mark='Description']")
            flat['description'] = (await desc_el.inner_text()).strip() if desc_el else None
        except: 
            flat['description'] = None

        flat['photos'] = []  # Отключаем для экономии
        flat['proxy'] = 'Direct (no proxy)'

        await browser.close()
        return flat

@app.get("/")
async def root():
    return {
        "service": "Парсер Avito & Cian (Playwright + Bright Data) 🚀",
        "proxy": {
            "provider": "Bright Data",
            "country": "Kazakhstan 🇰🇿",
            "server": PROXY_CONFIG['server'],
            "status": "Active" if PROXY_CONFIG['password'] else "Not configured"
        },
        "cookies_loaded": os.path.exists(COOKIES_FILE),
        "endpoints": {
            "POST /parse": "Парсить {\"url\": \"https://...\"}"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    url_str = str(request.url)
    
    try:
        if 'avito.ru' in url_str:
            result = await parse_avito(url_str)
            result['source'] = 'avito'
        elif 'cian.ru' in url_str:
            result = await parse_cian(url_str)
            result['source'] = 'cian'
        else:
            raise HTTPException(status_code=400, detail="Только Avito и Cian")
        
        result['url'] = url_str
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
