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

app = FastAPI(title="Парсер квартир Avito с Cookies")

class ParseRequest(BaseModel):
    url: HttpUrl

# Папки
COOKIES_DIR = Path("cookies")
SCREENSHOTS_DIR = Path("screenshots")
COOKIES_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)
COOKIES_FILE = COOKIES_DIR / "avito_session.json"

def clear_screenshots():
    if SCREENSHOTS_DIR.exists():
        print(f"[INFO] Очищаю папку скриншотов: {SCREENSHOTS_DIR}")
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(exist_ok=True)

async def save_screenshot(page, step_name: str, url: str):
    try:
        url_id = url.split('_')[-1].replace('/', '') if '_' in url else 'unknown'
        dir_path = SCREENSHOTS_DIR / url_id
        dir_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{step_name}_{timestamp}.png"
        full_path = dir_path / filename
        await page.screenshot(path=str(full_path), full_page=True)
        print(f"[SCREENSHOT] 📸 Сохранен: {full_path}")
        return str(full_path)
    except Exception as e:
        print(f"[ERROR] Ошибка скриншота: {e}")
        return None

async def close_modals(page):
    try:
        selectors = [
            "button:has-text('Не интересно')",
            "[data-marker*='modal/close']",
            ".modal__close",
        ]
        for sel in selectors:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(1)
                return True
        return False
    except Exception as e:
        print(f"[ERROR] close_modals: {e}")
        return False

async def click_continue_if_exists(page):
    try:
        selectors = [
            "button:has-text('Продолжить')",
            "[data-marker*='continue']",
        ]
        for sel in selectors:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await asyncio.sleep(5)
                return True
        return False
    except Exception as e:
        print(f"[ERROR] click_continue_if_exists: {e}")
        return False

async def parse_avito(url: str):
    print(f"[INFO] Начинаю парсинг Avito: {url}")
    screenshots = []
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
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080},
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "geolocation": {"longitude": 37.6173, "latitude": 55.7558},
            "permissions": ["geolocation"]
        }
        if COOKIES_FILE.exists():
            print(f"[INFO] Загружаю куки из {COOKIES_FILE}")
            context_options["storage_state"] = str(COOKIES_FILE)
        else:
            print(f"[WARNING] Куки не найдены: {COOKIES_FILE}")
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
            "Referer": "https://www.google.com/"
        })

        page = await context.new_page()
        page.set_default_timeout(90000)
        page.set_default_navigation_timeout(90000)

        # Загрузка главной
        try:
            print("[INFO] Загружаю главную страницу Avito")
            await page.goto("https://www.avito.ru/", wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(2000, 4000))
            await close_modals(page)
            await click_continue_if_exists(page)
            print("[SUCCESS] Главная страница загружена")
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки главной: {e}")

        # Загрузка объявления
        try:
            print("[INFO] Переход к объявлению")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(3000, 5000))
            await close_modals(page)
            await click_continue_if_exists(page)
            for _ in range(random.randint(2, 4)):
                scroll = random.randint(200, 500)
                await page.evaluate(f"window.scrollBy(0, {scroll})")
                await page.wait_for_timeout(random.randint(800, 1500))
                await page.mouse.move(random.randint(200, 1000), random.randint(200, 800))
                await page.wait_for_timeout(random.randint(500, 1000))
            print("[SUCCESS] Объявление загружено")
        except Exception as e:
            print(f"[ERROR] Ошибка перехода к объявлению: {e}")

        # Обновление cookies
        try:
            await context.storage_state(path=str(COOKIES_FILE))
            print("[INFO] Cookies обновлены")
        except Exception as e:
            print(f"[WARNING] Не удалось обновить куки: {e}")

        # Проверка на блокировку (капчу)
        html = await page.content()
        title = await page.title()

        if ('доступ ограничен' in html.lower() or
            'access denied' in html.lower() or
            'captcha' in title.lower()):
            print("[WARNING] Обнаружена блокировка или капча")
            await browser.close()
            return {'error': 'blocked', 'message': 'Avito заблокировал'}

        # Парсинг данных
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

        # Параметры
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

        # Фото
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
        "service": "Парсер Avito с Cookies",
        "cookies_loaded": COOKIES_FILE.exists(),
        "endpoints": {
            "POST /parse": "Парсить объявление (только Avito), передаём JSON {\"url\": \"https://...\"}"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    url_str = str(request.url)
    try:
        if "avito.ru" not in url_str:
            raise HTTPException(status_code=400, detail="Поддерживается только Avito")
        print(f"[INFO] Запрос на парсинг: {url_str}")
        clear_screenshots()
        result = await parse_avito(url_str)
        result["source"] = "avito"
        result["url"] = url_str
        return JSONResponse(content=result)
    except Exception as e:
        print(f"[ERROR] Ошибка parse_flat: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {e}")

def clear_screenshots():
    import shutil
    folder = Path("screenshots")
    if folder.exists():
        print(f"[INFO] Удаляю папку screenshots для очистки")
        shutil.rmtree(folder)
    folder.mkdir(exist_ok=True)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    print(f"[INFO] Запуск API на порту {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
