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
    """Парсер Avito с полным набором cookies"""
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
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            geolocation={"longitude": 37.6173, "latitude": 55.7558},
            permissions=["geolocation"],
        )
        
        # ===== ВСЕ 13 КУКИ ОТ ТВОЕГО БРАУЗЕРА =====
        cookies = [
            {
                "name": "_adcc",
                "value": "1.M6leiRVFrp4cYDp+89a9acQWLmRevvomcm2VRQxNbhofr/sXB6hQSWXIdfIHtG0uacSgWE8",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "_avisc",
                "value": "Q/UXqZCxiH671DkySCmC5pLjWlCSHV6+VoEFaBX22oM=",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "f",
                "value": "5.cc913c231fb04ceddc134d8a1938bf88a68643d4d8df96e9a68643d4d8df96e9a68643d4d8df96e9a68643d4d8df96e94f9572e6986d0c624f9572e6986d0c624f9572e6986d0c62ba029cd346349f36c1e8912fd5a48d02c1e8912fd5a48d0246b8ae4e81acb9fa1a2a574992f83a9246b8ae4e81acb9fa46b8ae4e81acb9fae992ad2cc54b8aa8af305aadb1df8cebc93bf74210ee38d940e3fb81381f359178ba5f931b08c66aff38e8d292af81e50df103df0c26013a2ebf3cb6fd35a0ac71e7cb57bbcb8e0ff0c77052689da50ddc5322845a0cba1aba0ac8037e2b74f92da10fb74cac1eab2da10fb74cac1eab2da10fb74cac1eabdc5322845a0cba1a0df103df0c26013a037e1fbb3ea05095de87ad3b397f946b4c41e97fe93686adff426b6cf1fd027fd476f8663ddba24a02c730c0109b9fbb72f6ee9e83550139b71fcc6d0e9258d7c5584122abfc8bae69081c2d33c8f9c0bc47737e6d23c603e2415097439d404746b8ae4e81acb9fa786047a80c779d5146b8ae4e81acb9fa8b2701e3210600292da10fb74cac1eab2da10fb74cac1eabb3ae333f3b35fe91de6c39666ae9b0d7ce067ee07b6dd903a77fbce136bf1ad8",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "ft",
                "value": "gQa0SAiNLAh8/20/ZSVkrK6YorlWICp0vrqetUoXmFipNK9pFuCT7x8hkeBhiEzvWfhLWVYGTd8qn55QIe1NVG3fM4ROFf7WheAgFbWaIwMOjzB6jO3y6uaZHuYoXdpNQqUSBv272BvCPZgPtHdyNcXmermtL414TfyWEB0tnj4vEYLhZ8g+BgywmsQDTTnv",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "gMltIuegZN2COuSe",
                "value": "EOFGWsm50bhh17prLqaIgdir1V0kgrvN",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "srv_id",
                "value": "MsbUS9kQDmW4Z2hG.3IAyeZZEQIUN2T7yBmBo88BNqruDCKzPrppEONQyqT_Fx0m79E3i-OJ3yJAe_Dv6cEfE.spS9zCiB66v8EF2KKKqrfIuNZFbDsqRnC2tKP66XCZE=.web",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "u",
                "value": "37bckues.lg004b.1qwy2n3011y00",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "uxs_uid",
                "value": "c52e1320-aae1-11f0-87c1-755c364d01d1",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "v",
                "value": "1760654700",
                "domain": ".avito.ru",
                "path": "/"
            },
            {
                "name": "csprefid",
                "value": "51e83786-5e8f-4f17-8043-d0bf08ebe827",
                "domain": ".www.avito.ru",
                "path": "/"
            },
            {
                "name": "cssid",
                "value": "df3a406b-2222-465b-aabb-e006dabd5666",
                "domain": ".www.avito.ru",
                "path": "/"
            },
            {
                "name": "cssid_exp",
                "value": "1760656499359",
                "domain": ".www.avito.ru",
                "path": "/"
            },
            {
                "name": "cookie_consent_shown",
                "value": "1",
                "domain": "www.avito.ru",
                "path": "/"
            }
        ]
        
        await context.add_cookies(cookies)
        print(f"[INFO] Добавлено {len(cookies)} куки")
        
        # Скрываем webdriver
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
            window.chrome = { runtime: {} };
        """)
        
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
        
        # Заход на главную
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
        
        # Переход на объявление
        try:
            print(f"[INFO] Переход на объявление...")
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(random.randint(3000, 5000))
            
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
        
        # Проверка блокировки
        html = await page.content()
        if 'доступ ограничен' in html.lower() or 'captcha' in html.lower():
            print("[WARNING] Блокировка!")
            await browser.close()
            return {'error': 'blocked', 'message': 'Avito заблокировал'}
        
        flat = {}
        
        # Парсинг (как раньше)
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

