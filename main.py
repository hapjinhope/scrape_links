from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import asyncio
import re
from playwright.async_api import async_playwright
import random
import os

app = FastAPI(title="Парсер квартир Avito & Cian с Cookies")

class ParseRequest(BaseModel):
    url: HttpUrl

# Файл с cookies
COOKIES_FILE = "avito_session.json"

async def close_modals(page):
    """Закрывает модальные окна"""
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
    except:
        return False

async def click_continue_if_exists(page):
    """Клик по 'Продолжить'"""
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
    except:
        return False

async def parse_avito(url: str):
    """Парсер Avito с cookies"""
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
        
        # ЗАГРУЗКА COOKIES
        if os.path.exists(COOKIES_FILE):
            print(f"[INFO] 🍪 Загружаю cookies из {COOKIES_FILE}")
            context_options["storage_state"] = COOKIES_FILE
        else:
            print(f"[WARNING] ⚠️ Cookies не найдены")
        
        context = await browser.new_context(**context_options)
        
        # Маскировка
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
        
        # 1. ГЛАВНАЯ СТРАНИЦА
        try:
            print("[INFO] Загружаю главную Avito...")
            await page.goto("https://www.avito.ru/", wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(random.randint(2000, 4000))
            
            await close_modals(page)
            await click_continue_if_exists(page)
            
            # Эмуляция
            await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            await page.wait_for_timeout(random.randint(500, 1500))
            await page.evaluate('window.scrollTo(0, 300)')
            print("[INFO] Ожидание перед переходом на объявление (10-15 сек)")
            await page.wait_for_timeout(random.randint(10000, 15000))

# Плюс больше активности на главной
            for _ in range(5):
                await page.evaluate(f'window.scrollBy(0, {random.randint(250, 600)})')
                await page.wait_for_timeout(random.randint(2000, 4000))
                await page.mouse.move(random.randint(300, 1600), random.randint(300, 900))
                await page.wait_for_timeout(random.randint(500, 1500))
                        
            print("[SUCCESS] Главная загружена")
        except Exception as e:
            print(f"[WARNING] Ошибка главной: {e}")

            print("[INFO] Переход в каталог квартир")
            await page.goto("https://www.avito.ru/moskva/kvartiry", wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(5000, 8000))
            await emulate_human_behavior(page)
        
        # 2. ОБЪЯВЛЕНИЕ
        try:
            print(f"[INFO] Переход на объявление...")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            await close_modals(page)
            await click_continue_if_exists(page)
            
            # Эмуляция чтения
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(200, 500)
                await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                await page.wait_for_timeout(random.randint(800, 1500))
                await page.mouse.move(random.randint(200, 1000), random.randint(200, 800))
                await page.wait_for_timeout(random.randint(500, 1000))
            
            print("[SUCCESS] Объявление загружено")
        except Exception as e:
            print(f"[ERROR] Ошибка объявления: {e}")
        
        # ОБНОВЛЕНИЕ COOKIES
        try:
            await context.storage_state(path=COOKIES_FILE)
            print(f"[INFO] 🍪 Cookies обновлены")
        except Exception as e:
            print(f"[WARNING] Ошибка сохранения cookies: {e}")
        
        # Проверка блокировки
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
        
        # Парсинг
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
    """Парсер Cian"""
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
        
        try:
            fact_items = await page.query_selector_all('[data-name="OfferFactItem"]')
            for item in fact_items:
                try:
                    spans = await item.query_selector_all('span')
                    if len(spans) >= 2:
                        key = (await spans[0].inner_text()).strip()
                        value = (await spans[1].inner_text()).strip()
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
        "service": "Парсер Avito & Cian с Cookies 🍪",
        "cookies_loaded": os.path.exists(COOKIES_FILE),
        "endpoints": {
            "POST /parse": "Парсить объявление {\"url\": \"https://...\"}"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    """Парсит объявление с Avito или Cian"""
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
