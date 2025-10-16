from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import asyncio
import re
from playwright.async_api import async_playwright
import random

app = FastAPI(title="Парсер квартир Avito & Cian")

class ParseRequest(BaseModel):
    url: HttpUrl

def extract_address_from_text(text):
    """Извлекает адрес из текста"""
    patterns = [
        r'(?:пр-т|проспект|ул\.|улица|бульвар|бул\.|переулок|пер\.)\s+[А-Яа-яЁё\s-]+,?\s*\d+[а-яА-Я]*\d*',
        r'[А-Яа-яЁё\s-]+,\s*\d+[а-яА-Я]*\d*',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return None


async def parse_avito(url: str):
    """Парсер Avito с эмуляцией человека + куки"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-web-security'
            ]
        )
        
        # Создаём контекст с куками
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            geolocation={"longitude": 37.6173, "latitude": 55.7558},
            permissions=["geolocation"],
        )
        
        # ===== ДОБАВЛЯЕМ КУКИ =====
        cookies = [
            {
                "name": "__ai_fp_uuid",
                "value": "117fe7e4bec96675%3A2",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "__upin",
                "value": "aSYzuudPaVOCnSKRMPAr3Q",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "_adcc",
                "value": "1.INlfy6kz1Bu+RCeJz49lFZzRImbqDE+ucIqGM2FFYD63s7/jc1GuhHzjV7OM6ze8rY7wwNg",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "_ga",
                "value": "GA1.1.1356008638.1753109631",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "_ga_M29JC28873",
                "value": "GS2.1.s1753109630$o1$g1$t1753109870$j17$l0$h0",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "_gcl_au",
                "value": "1.1.2048855763.1753109630",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "_ym_d",
                "value": "1753109630",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "_ym_uid",
                "value": "1753109630745711422",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "acs_3",
                "value": "%7B%22hash%22%3A%221aa3f9523ee6c2690cb34fc702d4143056487c0d%22%2C%22nst%22%3A1753196031204%2C%22sl%22%3A%7B%22224%22%3A1753109631204%2C%221228%22%3A1753109631204%7D%7D",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "adrcid",
                "value": "AUdKt29rO65xzslKR47qqwA",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "adrdel",
                "value": "1753109631190",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "buyer_laas_location",
                "value": "637640",
                "domain": ".avito.ru",
                "path": "/"
            }
        ]
        
        # Добавляем куки в контекст
        await context.add_cookies(cookies)
        print(f"[INFO] Добавлено {len(cookies)} куки")
        
        # Скрываем признаки автоматизации
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en'],
            });
            Object.defineProperty(navigator, 'platform', {
                get: () => 'MacIntel',
            });
            window.chrome = {
                runtime: {},
            };
        """)
        
        # Добавляем реалистичные заголовки
        await context.set_extra_http_headers({
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "Referer": "https://www.google.com/",
        })
        
        page = await context.new_page()
        
        print(f"[DEBUG] Парсинг URL: {url}")
        
        # ===== ЭМУЛЯЦИЯ РЕАЛЬНОГО ПОЛЬЗОВАТЕЛЯ =====
        
        # 1. Сначала заходим на главную Avito
        try:
            print("[INFO] Загружаем главную...")
            await page.goto("https://www.avito.ru/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(random.randint(2000, 4000))
            await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            await page.wait_for_timeout(random.randint(500, 1500))
            await page.evaluate('window.scrollTo(0, 300)')
            await page.wait_for_timeout(random.randint(1000, 2000))
            print("[SUCCESS] Главная загружена")
        except Exception as e:
            print(f"[WARNING] Ошибка главной: {e}")
        
        # 2. Теперь переходим на конкретное объявление
        try:
            print(f"[INFO] Переход на объявление...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
            # Эмуляция чтения страницы
            for _ in range(random.randint(2, 4)):
                scroll_amount = random.randint(200, 500)
                await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
                await page.wait_for_timeout(random.randint(800, 1500))
                await page.mouse.move(random.randint(200, 1000), random.randint(200, 800))
                await page.wait_for_timeout(random.randint(500, 1000))
            
            print("[SUCCESS] Объявление загружено")
        except Exception as e:
            print(f"[ERROR] Ошибка объявления: {e}")
        
        # Проверка на блокировку
        html = await page.content()
        
        if 'доступ ограничен' in html.lower() or 'captcha' in html.lower():
            print("[WARNING] Обнаружена блокировка/капча!")
            await browser.close()
            return {
                'error': 'blocked',
                'message': 'Avito заблокировал доступ'
            }
        
        # ===== ПАРСИНГ ДАННЫХ (как раньше) =====
        
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
        
        # Заголовок
        try:
            flat['title'] = (await page.inner_text("h1")).strip()
        except: 
            m = re.search(r'(Сдается [^<\n]+м²)', html)
            flat['title'] = m.group(1) if m else None

        # ЖК
        m = re.search(r'ЖК\s*[«"]([^»"<\n]+)', html)
        flat['complex'] = m.group(1).strip() if m else None

        # Цена
        try:
            price_el = await page.query_selector("[data-testid='price-amount']")
            flat['price'] = (await price_el.inner_text()).strip() if price_el else None
        except: flat['price'] = None

        # Адрес
        try:
            addr_items = await page.query_selector_all('[data-name="AddressItem"]')
            address_parts = []
            for item in addr_items:
                address_parts.append((await item.inner_text()).strip())
            flat['address'] = ', '.join(address_parts) if address_parts else None
        except: flat['address'] = None

        # Метро
        try:
            metros = []
            for elem in await page.query_selector_all('[data-name="UndergroundItem"] a'):
                metros.append((await elem.inner_text()).strip())
            flat['metro'] = metros
        except: flat['metro'] = []

        # Параметры
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
        
        # Условия аренды
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

        # В квартире есть
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

        # Описание
        try:
            desc_el = await page.query_selector("[data-mark='Description']")
            flat['description'] = (await desc_el.inner_text()).strip() if desc_el else None
        except: flat['description'] = None

        # Фото
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
        "service": "Парсер квартир Avito & Cian",
        "endpoints": {
            "POST /parse": "Парсить объявление (передать {\"url\": \"https://...\"})"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    """
    Парсит объявление с Avito или Cian
    
    Request body:
    {
        "url": "https://www.avito.ru/..."
    }
    """
    url_str = str(request.url)
    
    try:
        if 'avito.ru' in url_str:
            result = await parse_avito(url_str)
            result['source'] = 'avito'
        elif 'cian.ru' in url_str:
            result = await parse_cian(url_str)
            result['source'] = 'cian'
        else:
            raise HTTPException(status_code=400, detail="Поддерживаются только Avito и Cian")
        
        result['url'] = url_str
        return JSONResponse(content=result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

