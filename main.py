from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import asyncio
import re
from playwright.async_api import async_playwright

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
    """Парсер Avito (мобильная версия)"""
    # Конвертируем desktop URL в mobile
    mobile_url = url.replace('www.avito.ru', 'm.avito.ru')
    
    async with async_playwright() as p:
        # Эмулируем мобильный браузер
        iphone_13 = p.devices['iPhone 13 Pro']
        
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        context = await browser.new_context(
            **iphone_13,
            locale="ru-RU"
        )
        
        page = await context.new_page()
        
        print(f"[DEBUG] Mobile URL: {mobile_url}")
        
        await page.goto(mobile_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

        html = await page.content()
        
        # Debug
        print(f"[DEBUG] HTML length: {len(html)}")
        if 'доступ ограничен' in html.lower() or 'captcha' in html.lower():
            print("[WARNING] Мобильная версия заблокирована!")
        else:
            print("[SUCCESS] Мобильная версия загрузилась!")

        flat = {}
        
        # Заголовок
        try:
            title_elem = await page.query_selector('h1[itemprop="name"], h1')
            if title_elem:
                flat['title'] = (await title_elem.inner_text()).strip()
            else:
                flat['title'] = None
        except: 
            flat['title'] = None

        # Цена
        try:
            price_elem = await page.query_selector('[itemprop="price"], [data-marker="item-view/item-price"]')
            if price_elem:
                flat['price'] = (await price_elem.inner_text()).strip()
            else:
                flat['price'] = None
        except: 
            flat['price'] = None

        # Адрес
        try:
            addr_elem = await page.query_selector('[itemprop="address"], [class*="geo"]')
            if addr_elem:
                flat['address'] = (await addr_elem.inner_text()).strip()
            else:
                flat['address'] = None
        except: 
            flat['address'] = None

        # Описание
        try:
            desc_elem = await page.query_selector('[itemprop="description"], [class*="description"]')
            if desc_elem:
                flat['description'] = (await desc_elem.inner_text()).strip()
            else:
                flat['description'] = None
        except: 
            flat['description'] = None

        # Параметры
        params = {}
        try:
            param_items = await page.query_selector_all('li[class*="params"], [class*="item-params"] li')
            for item in param_items:
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

        # Фото
        try:
            photo_urls = []
            imgs = await page.query_selector_all('img[src*="avito.st"], img[data-marker*="image"]')
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

