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
            print(f"[INFO] 🍪 Загружаю cookies из {COOKIES_FILE}")
            context_options["storage_state"] = COOKIES_FILE
        
        context = await browser.new_context(**context_options)
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', description: 'Portable Document Format', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', description: '', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', description: '', filename: 'internal-nacl-plugin'}
                ],
            });
            Object.defineProperty(navigator, 'languages', { get: () => ['ru-RU', 'ru'] });
            Object.defineProperty(navigator, 'language', { get: () => 'ru-RU' });
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {} };
            
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };
            
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                const context = this.getContext('2d');
                if (context) {
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] += Math.floor(Math.random() * 3) - 1;
                        imageData.data[i+1] += Math.floor(Math.random() * 3) - 1;
                        imageData.data[i+2] += Math.floor(Math.random() * 3) - 1;
                    }
                    context.putImageData(imageData, 0, 0);
                }
                return originalToDataURL.apply(this, arguments);
            };
            
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        """)
        
        await context.set_extra_http_headers({
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": "https://www.google.com/",
        })
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        # Главная страница
        try:
            print("[INFO] Загружаю главную Avito...")
            await page.goto("https://www.avito.ru/", wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(random.randint(2000, 4000))
            
            await close_modals(page)
            await click_continue_if_exists(page)
            await emulate_human_behavior(page)
            
            print("[SUCCESS] Главная загружена")
        except Exception as e:
            print(f"[WARNING] Ошибка главной: {e}")
        
        await page.wait_for_timeout(random.randint(10000, 15000))
        
        # Объявление
        try:
            print(f"[INFO] Переход на объявление...")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            await close_modals(page)
            await click_continue_if_exists(page)
            await emulate_human_behavior(page)
            
            print("[SUCCESS] Объявление загружено")
        except Exception as e:
            print(f"[ERROR] Ошибка объявления: {e}")
        
        try:
            await context.storage_state(path=COOKIES_FILE)
            print(f"[INFO] 🍪 Cookies обновлены")
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
            print("[WARNING] Блокировка!")
            await browser.close()
            return {'error': 'blocked', 'message': 'Avito заблокировал'}
        
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

        try:
            photo_urls = []
            imgs = await page.query_selector_all('img[src*="avito.st"]')
            for img in imgs:
                src = await img.get_attribute('src')
                if src and '.jpg' in src:
                    clean_url = src.split('?')[0]
                    if len(clean_url) > 50:
                        photo_urls.append(clean_url)
            flat['photos'] = list(set(photo_urls))
        except:
            flat['photos'] = []

        await browser.close()
        return flat

async def parse_cian(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU"
        )
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
        except: flat['price'] = None

        try:
            addr_items = await page.query_selector_all('[data-name="AddressItem"]')
            address_parts = []
            for item in addr_items:
                address_parts.append((await item.inner_text()).strip())
            flat['address'] = ', '.join(address_parts) if address_parts else None
        except: flat['address'] = None

        try:
            metros = []
            for elem in await page.query_selector_all('[data-name="UndergroundItem"] a'):
                metros.append((await elem.inner_text()).strip())
            flat['metro'] = metros
        except: flat['metro'] = []

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
                except: continue
        except: pass
        
        flat['params'] = params

        try:
            features = []
            feature_items = await page.query_selector_all('[data-name="FeaturesItem"]')
            for item in feature_items:
                try:
                    feature_text = (await item.inner_text()).strip()
                    if feature_text:
                        features.append(feature_text)
                except: continue
            flat['features'] = features
        except:
            flat['features'] = []

        try:
            desc_el = await page.query_selector("[data-mark='Description']")
            flat['description'] = (await desc_el.inner_text()).strip() if desc_el else None
        except: flat['description'] = None

        try:
            photo_urls = []
            thumb_imgs = await page.query_selector_all('[data-name="PaginationThumbsComponent"] img')
            for img in thumb_imgs:
                src = await img.get_attribute('src')
                if src and 'cdn-cian.ru/images' in src:
                    full_src = src.replace('-2.jpg', '-1.jpg')
                    if full_src not in photo_urls:
                        photo_urls.append(full_src)
            flat['photos'] = photo_urls
        except:
            flat['photos'] = []

        await browser.close()
        return flat

@app.get("/")
async def root():
    return {
        "service": "Парсер Avito & Cian 🍪",
        "cookies_loaded": os.path.exists(COOKIES_FILE),
        "endpoints": {
            "POST /parse": "Парсить объявление {\"url\": \"https://...\"}"
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
