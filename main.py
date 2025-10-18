from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import time
import re
import os
import ssl
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from playwright.async_api import async_playwright
import asyncio

app = FastAPI(title="Парсер квартир Avito (Selenium) & Cian (Playwright)")

class ParseRequest(BaseModel):
    url: HttpUrl

ssl._create_default_https_context = ssl._create_unverified_context

def close_modal_selenium(driver):
    """Закрытие модальных окон"""
    try:
        selectors = [
            ".modal-close", 
            ".close", 
            "[aria-label='Закрыть']", 
            "button[aria-label='Закрыть']",
            "[data-marker*='modal/close']"
        ]
        for sel in selectors:
            try:
                btn = driver.find_element(By.CSS_SELECTOR, sel)
                btn.click()
                print(f"[INFO] Модальное окно закрыто: {sel}")
                time.sleep(1)
                return True
            except:
                continue
        return False
    except:
        return False

def parse_avito_selenium(url: str):
    """Парсер Avito через Selenium + undetected-chromedriver"""
    print(f"[INFO] Запуск Selenium для: {url}")
    
    try:
        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=None)
        
        print("[INFO] Переход на объявление...")
        driver.get(url)
        time.sleep(5)  # Ждём загрузки
        
        # Закрываем модалки
        close_modal_selenium(driver)
        time.sleep(1)
        
        # Проверка блокировки
        page_source = driver.page_source.lower()
        if 'доступ ограничен' in page_source or 'access denied' in page_source:
            print("[WARNING] Блокировка обнаружена")
            driver.quit()
            return {'error': 'blocked', 'message': 'Avito заблокировал'}
        
        # Парсинг
        flat = {}
        
        def safe_find(selector, by=By.CSS_SELECTOR):
            try:
                elem = driver.find_element(by, selector)
                return elem.text.strip()
            except:
                return None
        
        flat['title'] = safe_find('[data-marker="item-view/title-info"]') or safe_find('h1')
        flat['price'] = safe_find('[data-marker="item-view/item-price"]')
        flat['address'] = safe_find('[data-marker="item-view/location-address"]')
        flat['description'] = safe_find('[data-marker="item-view/item-description"]')
        
        # Параметры
        params = {}
        try:
            param_sections = driver.find_elements(By.CSS_SELECTOR, '[data-marker="item-view/item-params"]')
            for section in param_sections:
                items = section.find_elements(By.TAG_NAME, 'li')
                for item in items:
                    try:
                        text = item.text.strip()
                        if ':' in text:
                            key, value = text.split(':', 1)
                            params[key.strip()] = value.strip()
                    except:
                        continue
        except:
            pass
        flat['params'] = params
        
        # Фото
        photos = []
        try:
            imgs = driver.find_elements(By.CSS_SELECTOR, 'img[src*="avito.st"]')
            for img in imgs:
                src = img.get_attribute('src')
                if src and '.jpg' in src:
                    clean_url = src.split('?')[0]
                    if len(clean_url) > 50 and clean_url not in photos:
                        photos.append(clean_url)
        except:
            pass
        flat['photos'] = photos
        
        print("[SUCCESS] Парсинг завершён")
        driver.quit()
        return flat
        
    except Exception as e:
        print(f"[ERROR] Ошибка Selenium: {e}")
        try:
            driver.quit()
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

async def parse_cian(url: str):
    """Парсер Cian через Playwright"""
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
        "service": "Парсер Avito (Selenium) & Cian (Playwright) 🚀",
        "endpoints": {
            "POST /parse": "Парсить объявление {\"url\": \"https://...\"}"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    url_str = str(request.url)
    
    try:
        if 'avito.ru' in url_str:
            # Selenium работает синхронно, оборачиваем в executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await asyncio.get_event_loop().run_in_executor(
                    executor, parse_avito_selenium, url_str
                )
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
