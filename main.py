from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import asyncio
import re
from playwright.async_api import async_playwright
import random
import os
import json
import time
import logging
import base64

# Создаём глобальный reader (загружается 1 раз)
reader = None

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Парсер квартир Avito & Cian")

class ParseRequest(BaseModel):
    url: HttpUrl

COOKIES_FILE = "avito_session.json"
DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

async def human_like_mouse_move(page, from_x, from_y, to_x, to_y):
    steps = random.randint(10, 20)
    for i in range(steps):
        progress = i / steps
        curve = random.uniform(-5, 5)
        x = from_x + (to_x - from_x) * progress + curve
        y = from_y + (to_y - from_y) * progress + curve
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.02, 0.05))

async def emulate_human_behavior(page):
    start_x, start_y = random.randint(100, 400), random.randint(200, 500)
    end_x, end_y = random.randint(600, 1200), random.randint(400, 800)
    await human_like_mouse_move(page, start_x, start_y, end_x, end_y)
    await asyncio.sleep(random.uniform(0.5, 1.0))
    for _ in range(random.randint(3, 5)):
        scroll_amount = random.randint(200, 500)
        if random.random() < 0.2:
            scroll_amount = -scroll_amount
        await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.5, 1.5))
    for _ in range(random.randint(1, 3)):
        jitter_x = end_x + random.randint(-3, 3)
        jitter_y = end_y + random.randint(-3, 3)
        await page.mouse.move(jitter_x, jitter_y)
        await asyncio.sleep(random.uniform(0.1, 0.2))

async def close_modals(page):
    try:
        selectors = [
            "button:has-text('Не интересно')",
            "button.RxKAg[aria-label='закрыть']",
            "button[data-marker='NOT_INTERESTING_MARKER']",
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

async def parse_avito(url: str, mode: str = "full"):
    """
    mode: "full" = полный парсинг / "check" = актуальность + цена
    """
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
                f'--user-agent={DESKTOP_UA}',
            ],
            timeout=90000
        )
        
        context_options = {
            "user_agent": DESKTOP_UA,
            "viewport": {"width": 1920, "height": 1080},
            "screen": {"width": 1920, "height": 1080},
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "geolocation": {"longitude": 37.6173, "latitude": 55.7558},
            "permissions": ["geolocation", "notifications"],
            "color_scheme": "light",
            "device_scale_factor": 1,
        }
        
        # ЗАГРУЗКА COOKIES
        if os.path.exists(COOKIES_FILE):
            try:
                with open(COOKIES_FILE, 'r') as f:
                    cookies_data = json.load(f)
                    cookies_count = len(cookies_data.get('cookies', []))
                    logger.info(f"🍪 Загружаю cookies: {cookies_count} шт из {COOKIES_FILE}")
                context_options["storage_state"] = COOKIES_FILE
            except Exception as e:
                logger.warning(f"⚠️ Ошибка загрузки cookies: {e}")
        else:
            logger.info(f"🍪 Cookies файл не найден, работаю без cookies")
        
        context = await browser.new_context(**context_options)
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        """)
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        # Главная (только для full mode)
        if mode == "full":
            try:
                await page.goto("https://www.avito.ru/", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                await close_modals(page)
                await emulate_human_behavior(page)
            except:
                pass
        
        # Объявление
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000 if mode == "check" else 3000)
        await close_modals(page)
        
        if mode == "full":
            await emulate_human_behavior(page)
        
        # СОХРАНЕНИЕ COOKIES
        try:
            storage_state = await context.storage_state()
            new_cookies_count = len(storage_state.get('cookies', []))
            
            with open(COOKIES_FILE, 'w') as f:
                json.dump(storage_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"🍪 Cookies обновлены: {new_cookies_count} шт → {COOKIES_FILE}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения cookies: {e}")
        
        # ПРОВЕРКА АКТУАЛЬНОСТИ (всегда)
        try:
            unpublished = await page.query_selector('h1.EEPdn:has-text("Объявление не")')
            if unpublished:
                await browser.close()
                return {'status': 'unpublished', 'message': 'Объявление снято'}
        except:
            pass
        
        # ЦЕНА (всегда)
        try:
            price_el = await page.query_selector('span[content][itemprop="price"]')
            if price_el:
                price_value = await price_el.get_attribute('content')
                currency_el = await page.query_selector('span[itemprop="priceCurrency"]')
                currency = (await currency_el.inner_text()).strip() if currency_el else ''
                price = f"{price_value} {currency}"
            else:
                price_el2 = await page.query_selector('.hQ3Iv[data-marker="item-view/item-price"]')
                price = (await price_el2.inner_text()).strip() if price_el2 else None
        except:
            price = None
        
        # РЕЖИМ "check" - только актуальность + цена
        if mode == "check":
            await browser.close()
            return {
                'status': 'active',
                'price': price,
                'mode': 'quick_check'
            }
        
        # РЕЖИМ "full" - весь парсинг
        messages_only = False
        try:
            no_calls = await page.query_selector('button:has-text("Без звонков")')
            if no_calls:
                messages_only = True
        except:
            pass
        
        flat = {'status': 'active', 'messages_only': messages_only, 'price': price}
        
        try:
            title_el = await page.query_selector('h1[itemprop="name"]')
            flat['summary'] = (await title_el.inner_text()).strip() if title_el else None
        except:
            flat['summary'] = None
        
        try:
            addr_el = await page.query_selector('span.xLPJ6')
            flat['address'] = (await addr_el.inner_text()).strip() if addr_el else None
        except:
            flat['address'] = None
        
        try:
            metro_stations = []
            metro_items = await page.query_selector_all('span.tAdYM')
            for metro in metro_items:
                try:
                    spans = await metro.query_selector_all('span')
                    if len(spans) >= 2:
                        station_name = (await spans[1].inner_text()).strip()
                        time_span = await metro.query_selector('span.LHPFZ')
                        if time_span:
                            time_text = (await time_span.inner_text()).strip()
                            metro_info = f"{station_name} ({time_text})"
                        else:
                            metro_info = station_name
                        if 'мин' not in station_name:
                            metro_stations.append(metro_info)
                except:
                    pass
            flat['metro'] = metro_stations
        except:
            flat['metro'] = []
        
        try:
            desc_el = await page.query_selector('div[itemprop="description"][data-marker="item-view/item-description"]')
            flat['description'] = (await desc_el.inner_text()).strip() if desc_el else None
        except:
            flat['description'] = None
        
        try:
            seller_el = await page.query_selector('[data-marker="seller-info/name"] span.TTiHl')
            flat['seller_name'] = (await seller_el.inner_text()).strip() if seller_el else None
        except:
            flat['seller_name'] = None
        
        # Параметры квартиры
        try:
            params_list = await page.query_selector_all('ul.HRzg1 li.cHzV4')
            rooms_count = total_area = kitchen_area = floor = floors_total = room_type = bathroom = repair = appliances = deposit = commission = kids = pets = year_built = elevator_passenger = elevator_cargo = parking = None
            
            for param in params_list:
                try:
                    text = (await param.inner_text()).strip()
                    if ':' in text:
                        parts = text.split(':', 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        
                        if 'Количество комнат' in key:
                            rooms_count = value
                        elif 'Общая площадь' in key:
                            total_area = value
                        elif 'Площадь кухни' in key:
                            kitchen_area = value
                        elif key == "Этаж" and 'из' in value:
                            try:
                                floor_parts = value.split('из')
                                floor = floor_parts[0].strip()
                                floors_total = floor_parts[1].strip()
                            except:
                                floor = value
                        elif 'Тип комнат' in key:
                            room_type = value
                        elif 'Санузел' in key:
                            bathroom = value
                        elif 'Ремонт' in key:
                            repair = value
                        elif 'Техника' in key:
                            appliances = value
                        elif 'Залог' in key:
                            deposit = value
                        elif 'Комиссия' in key:
                            commission = value
                        elif 'Можно с детьми' in key:
                            kids = value
                        elif 'Можно с животными' in key:
                            pets = value
                        elif 'Год постройки' in key:
                            year_built = value
                        elif 'Пассажирский лифт' in key:
                            elevator_passenger = value
                        elif 'Грузовой лифт' in key:
                            elevator_cargo = value
                        elif 'Парковка' in key:
                            parking = value
                except:
                    pass
            
            flat.update({
                'rooms_count': rooms_count, 'total_area': total_area, 'kitchen_area': kitchen_area,
                'floor': floor, 'floors_total': floors_total, 'room_type': room_type,
                'bathroom': bathroom, 'repair': repair, 'appliances': appliances,
                'deposit': deposit, 'commission': commission, 'kids': kids, 'pets': pets,
                'year_built': year_built, 'elevator_passenger': elevator_passenger,
                'elevator_cargo': elevator_cargo, 'parking': parking
            })
        except:
            pass
        
        # Параметры дома
        try:
            all_params_blocks = await page.query_selector_all('ul.HRzg1')
            house_deposit = house_commission = utilities_counters = utilities_other = None
            
            if len(all_params_blocks) >= 2:
                house_list = await all_params_blocks[1].query_selector_all('li.cHzV4')
                for param in house_list:
                    try:
                        text = (await param.inner_text()).strip()
                        if ':' in text:
                            parts = text.split(':', 1)
                            key = parts[0].strip()
                            value = parts[1].strip()
                            
                            if 'Залог' in key:
                                house_deposit = value
                            elif 'Комиссия' in key:
                                house_commission = value
                            elif 'По счетчикам' in key:
                                utilities_counters = value
                            elif 'Другие ЖКУ' in key:
                                utilities_other = value
                    except:
                        pass
            
            flat.update({
                'house_deposit': house_deposit, 'house_commission': house_commission,
                'utilities_counters': utilities_counters, 'utilities_other': utilities_other
            })
        except:
            pass
        
        # Правила
        try:
            all_params_blocks = await page.query_selector_all('ul.HRzg1')
            rules_kids = rules_pets = None
            
            if len(all_params_blocks) >= 3:
                rules_list = await all_params_blocks[2].query_selector_all('li.cHzV4')
                for rule in rules_list:
                    try:
                        text = (await rule.inner_text()).strip()
                        if ':' in text:
                            parts = text.split(':', 1)
                            key = parts[0].strip()
                            value = parts[1].strip()
                            
                            if 'Можно с детьми' in key:
                                rules_kids = value
                            elif 'Можно с животными' in key:
                                rules_pets = value
                    except:
                        pass
            
            flat.update({'rules_kids': rules_kids, 'rules_pets': rules_pets})
        except:
            pass
        
        # ФОТО
        try:
            photos = set()
            await page.evaluate("window.scrollTo(0, 200)")
            await asyncio.sleep(1)
            
            carousel = await page.query_selector('ul.Jue7e')
            if carousel:
                total_items = len(await page.query_selector_all('ul.Jue7e li.Kg235'))
                max_clicks = total_items if total_items > 0 else 30
                click_count = 0
                
                while click_count < max_clicks:
                    gallery_photos = await page.query_selector_all('#gallery-slider img[src*="avito.st"]')
                    
                    for photo in gallery_photos:
                        try:
                            src = await photo.get_attribute('src')
                            if src and 'avito.st' in src and 'http' in src:
                                clean_url = src.split('?')[0]
                                photos.add(clean_url)
                        except:
                            pass
                    
                    if len(photos) >= total_items:
                        break
                    
                    try:
                        next_button = await page.query_selector('button.LJZ92.bTaFV')
                        if next_button and await next_button.is_visible():
                            await next_button.click()
                            click_count += 1
                            await asyncio.sleep(0.8)
                        else:
                            break
                    except:
                        break
            
            flat['photos'] = list(photos)
        except:
            flat['photos'] = []
        
# ТЕЛЕФОН
        if messages_only:
            flat['phone'] = 'только сообщения'
        else:
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(1)
                
               # ПРОВЕРКА ПЛАТНОЙ УСЛУГИ
                paid_service = False
                free_after_time = None

                try:
                    # Пробуем множество селекторов для плашки
                    paid_selectors = [
                        'h2:has-text("Свяжитесь сейчас")',
                        'h2:has-text("Связаться сейчас")',
                        'h2:has-text("за 159")',
                        'button:has-text("Перейти к оплате")',
                        '[data-marker*="paid-contact"]',
                        '.styles-module-wrapper-kax1E:has-text("Свяжитесь")'
                    ]
                    
                    for selector in paid_selectors:
                        paid_header = await page.query_selector(selector)
                        if paid_header:
                            paid_service = True
                            logger.info(f"💰 Платная услуга найдена: {selector}")
                            break
                    
                    if paid_service:
                        # Ищем время
                        time_selectors = [
                            'strong.styles-module-root-Yaf_d',
                            'strong.OVzrF',
                            'strong:has-text(":")',
                            'p:has-text("бесплатно после") strong',
                            'p:has-text("Или бесплатно после") strong'
                        ]
                        
                        for selector in time_selectors:
                            time_elem = await page.query_selector(selector)
                            if time_elem:
                                time_text = (await time_elem.inner_text()).strip()
                                # Проверяем что это время (формат XX:XX)
                                if ':' in time_text and len(time_text) <= 6:
                                    free_after_time = time_text
                                    logger.info(f"⏰ Бесплатно после: {free_after_time} МСК")
                                    break
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки платной услуги: {e}")

                # Если платная услуга - возвращаем статус "time"
                if paid_service:
                    await browser.close()
                    return {
                        'status': 'time',
                        'message': 'Телефон платный сейчас',
                        'free_after': free_after_time if free_after_time else 'неизвестно',
                        'url': url
                    }

                
                # Обычный парсинг телефона
                phone_clicked = False
                phone_button_selectors = [
                    'button:has-text("Показать телефон")',
                    'button[data-marker="item-phone-button/card"]',
                    'button.styles-module-root-uSHbU:has-text("Показать")',
                    'button:has-text("8 958")',
                    'button.QaQVm',
                ]
                
                for selector in phone_button_selectors:
                    try:
                        phone_button = await page.query_selector(selector)
                        if phone_button and await phone_button.is_visible():
                            await phone_button.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            
                            box = await phone_button.bounding_box()
                            if box:
                                click_x = box['x'] + box['width'] / 2
                                click_y = box['y'] + box['height'] / 2
                                await page.mouse.click(click_x, click_y)
                                phone_clicked = True
                                logger.info(f"✅ Кликнул: {selector}")
                                await asyncio.sleep(3)
                                break
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка {selector}: {e}")
                        continue
                
                if phone_clicked:
                    phone_found = False
                    
                    # Способ 1: tel: ссылка
                    try:
                        phone_links = await page.query_selector_all('a[href^="tel:"]')
                        for phone_link in phone_links:
                            try:
                                href = await phone_link.get_attribute('href')
                                if href:
                                    phone_number = href.replace('tel:', '').replace('+', '').strip()
                                    if len(phone_number) >= 10:
                                        flat['phone'] = phone_number
                                        phone_found = True
                                        logger.info(f"✅ Телефон (tel:): {phone_number}")
                                        break
                            except:
                                pass
                    except:
                        pass
                    
                    # Способ 2: base64 (БЕЗ OCR, просто возвращаем)
                    if not phone_found:
                        try:
                            selectors = [
                                'img[data-marker="phone-popup/phone-image"]',
                                'img.N0VY9',
                                '[data-marker="phone-popup"] img',
                                'img[src*="base64"]'
                            ]
                            
                            for selector in selectors:
                                phone_imgs = await page.query_selector_all(selector)
                                for phone_img in phone_imgs:
                                    if await phone_img.is_visible():
                                        phone_src = await phone_img.get_attribute('src')
                                        if phone_src and 'base64' in phone_src:
                                            logger.info("🖼️ Найдена base64 картинка телефона")
                                            flat['phone'] = phone_src  # ПРОСТО ВОЗВРАЩАЕМ BASE64
                                            phone_found = True
                                            break
                                if phone_found:
                                    break
                        except Exception as e:
                            logger.error(f"❌ Ошибка поиска base64: {e}")
                    
                    if not phone_found:
                        flat['phone'] = 'Не удалось получить'
                else:
                    flat['phone'] = 'Кнопка не найдена'
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга телефона: {e}")
                flat['phone'] = 'Ошибка'

        await browser.close()
        return flat



async def parse_avito_phone_only(url: str) -> dict:
    """
    Парсит ТОЛЬКО телефон с Avito (игнорирует платную услугу)
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                f'--user-agent={DESKTOP_UA}',
            ],
            timeout=90000
        )
        
        context_options = {
            "user_agent": DESKTOP_UA,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
        }
        
        # Загрузка cookies
        if os.path.exists(COOKIES_FILE):
            try:
                context_options["storage_state"] = COOKIES_FILE
                logger.info("🍪 Cookies загружены")
            except:
                pass
        
        context = await browser.new_context(**context_options)
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await close_modals(page)
        
        # Скроллим к кнопке телефона
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1)
        
        phone = None
        
        # Кликаем на кнопку "Показать телефон"
        phone_clicked = False
        for selector in [
            'button[data-marker="item-phone-button/card"]',
            'button:has-text("Показать телефон")',
            'button.QaQVm'
        ]:
            try:
                phone_button = await page.query_selector(selector)
                if phone_button and await phone_button.is_visible():
                    await phone_button.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await phone_button.click()
                    phone_clicked = True
                    logger.info("📞 Кликнул на 'Показать телефон'")
                    await asyncio.sleep(3)
                    break
            except:
                continue
        
        if phone_clicked:
            # Способ 1: tel: ссылка
            try:
                phone_links = await page.query_selector_all('a[href^="tel:"]')
                for phone_link in phone_links:
                    try:
                        href = await phone_link.get_attribute('href')
                        if href:
                            phone_number = href.replace('tel:', '').replace('+', '').strip()
                            if len(phone_number) >= 10:
                                phone = phone_number
                                logger.info(f"✅ Телефон (tel:): {phone}")
                                break
                    except:
                        pass
            except:
                pass
            
            # Способ 2: base64 + OCR
            if not phone:
                try:
                    selectors = [
                        'img[data-marker="phone-popup/phone-image"]',
                        'img.N0VY9',
                        '[data-marker="phone-popup"] img',
                        'img[src*="base64"]'
                    ]
                    
                    for selector in selectors:
                        phone_imgs = await page.query_selector_all(selector)
                        for phone_img in phone_imgs:
                            if await phone_img.is_visible():
                                phone_src = await phone_img.get_attribute('src')
                                if phone_src and 'base64' in phone_src:
                                    logger.info("🖼️ Найдена base64 картинка, OCR...")
                                    phone = phone_src  # Просто возвращаем base64
                                    break
                        if phone:
                            break
                except Exception as e:
                    logger.error(f"❌ Ошибка OCR: {e}")
        
        await browser.close()
        
        return {
            'status': 'success' if phone else 'error',
            'phone': phone if phone else 'Не удалось получить',
            'url': url
        }

async def parse_cian(url: str, mode: str = "full"):
    """
    mode: "full" = полный парсинг / "check" = актуальность + цена
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            user_agent=DESKTOP_UA,
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU"
        )
        page = await context.new_page()
        page.set_default_timeout(60000)
        
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000 if mode == "check" else 2000)
        
        # ПРОВЕРКА АКТУАЛЬНОСТИ (всегда)
        try:
            unpublished = await page.query_selector('[data-name="OfferUnpublished"]')
            if unpublished:
                await browser.close()
                return {'status': 'unpublished', 'message': 'Объявление снято'}
        except:
            pass
        
        # ЦЕНА (всегда)
        try:
            price_el = await page.query_selector("[data-testid='price-amount']")
            price = (await price_el.inner_text()).strip() if price_el else None
        except:
            price = None
        
        # РЕЖИМ "check"
        if mode == "check":
            await browser.close()
            return {
                'status': 'active',
                'price': price,
                'mode': 'quick_check'
            }
        
        # РЕЖИМ "full"
        flat = {'status': 'active', 'price': price}
        
        try:
            h1 = await page.query_selector("h1")
            flat['summary'] = (await h1.inner_text()).strip() if h1 else None
        except:
            flat['summary'] = None
        
        try:
            address_items = await page.query_selector_all('[data-name="AddressItem"]')
            address_parts = []
            for item in address_items:
                address_parts.append((await item.inner_text()).strip())
            flat['address'] = ', '.join(address_parts) if address_parts else None
        except:
            flat['address'] = None
        
        try:
            jk_el = await page.query_selector('[data-name="ParentNew"] a')
            flat['jk'] = (await jk_el.inner_text()).strip() if jk_el else None
        except:
            flat['jk'] = None
        
        try:
            metros = []
            metro_items = await page.query_selector_all('[data-name="UndergroundItem"]')
            for item in metro_items:
                try:
                    link = await item.query_selector('a')
                    station = (await link.inner_text()).strip() if link else None
                    time_el = await item.query_selector('.xa15a2ab7--d9f62d--underground_time')
                    if time_el:
                        time_text = (await time_el.inner_text()).strip()
                        metros.append(f"{station} ({time_text})")
                    else:
                        metros.append(station)
                except:
                    pass
            flat['metro'] = metros
        except:
            flat['metro'] = []
        
        # Оплата
        try:
            payment_items = await page.query_selector_all('[data-name="OfferFactItem"]')
            payment_zhkh = payment_deposit = payment_commission = payment_prepay = payment_term = None
            
            for item in payment_items:
                try:
                    spans = await item.query_selector_all('span')
                    if len(spans) >= 2:
                        key = (await spans[0].inner_text()).strip()
                        value = (await spans[1].inner_text()).strip()
                        
                        if 'Оплата ЖКХ' in key:
                            payment_zhkh = value
                        elif 'Залог' in key:
                            payment_deposit = value
                        elif 'Комиссии' in key or 'Комиссия' in key:
                            payment_commission = value
                        elif 'Предоплата' in key:
                            payment_prepay = value
                        elif 'Срок аренды' in key:
                            payment_term = value
                except:
                    pass
            
            flat.update({
                'payment_zhkh': payment_zhkh, 'payment_deposit': payment_deposit,
                'payment_commission': payment_commission, 'payment_prepay': payment_prepay,
                'payment_term': payment_term
            })
        except:
            pass
        
        # ПАРСИНГ ХАРАКТЕРИСТИК (приоритет ObjectFactoids → OfferSummaryInfoItem)
        try:
            total_area = living_area = kitchen_area = floor = floors_total = year_built = None
            layout = bathroom = elevators = parking = None
            ceiling_height = repair = windows_view = balcony_count = loggia_count = None
            
            # ШАГ 1: Парсим ObjectFactoids (этаж, площади, год)
            factoid_items = await page.query_selector_all('[data-name="ObjectFactoidsItem"]')
            
            for item in factoid_items:
                try:
                    spans = await item.query_selector_all('span')
                    if len(spans) >= 2:
                        key = (await spans[0].inner_text()).strip()
                        value = (await spans[1].inner_text()).strip()
                        
                        if 'Общая площадь' in key:
                            total_area = value
                        elif 'Жилая площадь' in key:
                            living_area = value
                        elif 'Площадь кухни' in key:
                            kitchen_area = value
                        elif key == 'Этаж' and 'из' in value:
                            try:
                                parts = value.split('из')
                                floor = parts[0].strip()
                                floors_total = parts[1].strip()
                            except:
                                floor = value
                        elif 'Год постройки' in key:
                            year_built = value
                except:
                    pass
            
            # ШАГ 2: Парсим OfferSummaryInfoItem (всё остальное + fallback для этажа)
            info_items = await page.query_selector_all('[data-testid="OfferSummaryInfoItem"]')
            
            for item in info_items:
                try:
                    paragraphs = await item.query_selector_all('p')
                    if len(paragraphs) >= 2:
                        key = (await paragraphs[0].inner_text()).strip()
                        value = (await paragraphs[1].inner_text()).strip()
                        
                        # Площади (если не нашли в ObjectFactoids)
                        if not total_area and 'Общая площадь' in key:
                            total_area = value
                        elif not living_area and 'Жилая площадь' in key:
                            living_area = value
                        elif not kitchen_area and 'Площадь кухни' in key:
                            kitchen_area = value
                        
                        # Этаж (fallback)
                        elif not floor and key == 'Этаж' and 'из' in value:
                            try:
                                parts = value.split('из')
                                floor = parts[0].strip()
                                floors_total = parts[1].strip()
                            except:
                                floor = value
                        
                        # Год (fallback)
                        elif not year_built and 'Год постройки' in key:
                            year_built = value
                        
                        # НОВЫЕ ПОЛЯ
                        elif 'Высота потолков' in key:
                            ceiling_height = value
                        elif 'Ремонт' in key:
                            repair = value
                        elif 'Вид из окон' in key:
                            windows_view = value
                        elif 'Балкон/лоджия' in key or 'Балкон' in key:
                            # "1 лоджия" или "2 балкона"
                            balcony_match = re.search(r'(\d+)\s*балкон', value, re.IGNORECASE)
                            loggia_match = re.search(r'(\d+)\s*лодж', value, re.IGNORECASE)
                            if balcony_match:
                                balcony_count = int(balcony_match.group(1))
                            if loggia_match:
                                loggia_count = int(loggia_match.group(1))
                        
                        # Другие поля
                        elif 'Планировка' in key:
                            layout = value
                        elif 'Санузел' in key:
                            bathroom = value
                        elif 'Количество лифтов' in key:
                            elevators = value
                        elif 'Парковка' in key:
                            parking = value
                except:
                    pass
            
            flat.update({
                'total_area': total_area, 'living_area': living_area, 'kitchen_area': kitchen_area,
                'floor': floor, 'floors_total': floors_total,
                'layout': layout, 'bathroom': bathroom, 'year_built': year_built,
                'elevators': elevators, 'parking': parking,
                'ceiling_height': ceiling_height, 'repair': repair, 'windows_view': windows_view,
                'balcony_count': balcony_count, 'loggia_count': loggia_count
            })
        except Exception as e:
            logger.error(f"Ошибка парсинга характеристик: {e}")
            pass

        
        # Удобства
        try:
            amenities = []
            amenity_items = await page.query_selector_all('[data-name="FeaturesItem"]')
            for item in amenity_items:
                try:
                    amenity = (await item.inner_text()).strip()
                    if amenity:
                        amenities.append(amenity)
                except:
                    pass
            flat['amenities'] = amenities
        except:
            flat['amenities'] = []
        
        # ПАРСИНГ ОПИСАНИЯ
        try:
            description = None
            
            # Вариант 1: Основной селектор
            desc_el = await page.query_selector('span.xa15a2ab7--dc75cc--text.xa15a2ab7--dc75cc--text_whiteSpace__pre-wrap')
            if desc_el:
                description = (await desc_el.inner_text()).strip()
            
            # Вариант 2: Fallback
            if not description:
                desc_el2 = await page.query_selector('[data-name="Description"]')
                if desc_el2:
                    description = (await desc_el2.inner_text()).strip()
            
            # Вариант 3: Ещё один fallback
            if not description:
                desc_el3 = await page.query_selector('div[itemprop="description"]')
                if desc_el3:
                    description = (await desc_el3.inner_text()).strip()
            
            flat['description'] = description
        except Exception as e:
            logger.error(f"Ошибка парсинга описания: {e}")
            flat['description'] = None
        
        # ПАРСИНГ ФОТО (с кликами - все 24 фото)
        try:
            photos = set()
            
            # Узнаём количество фото
            photo_count = 0
            try:
                count_button = await page.query_selector('button:has-text("фото")')
                if count_button:
                    count_text = (await count_button.inner_text()).strip()
                    match = re.search(r'(\d+)', count_text)
                    if match:
                        photo_count = int(match.group(1))
                        logger.info(f"Обнаружено {photo_count} фото")
            except:
                photo_count = 30
            
            # СПОСОБ 1: Клики по галерее
            try:
                await page.wait_for_selector('[data-name="GalleryInnerComponent"]', timeout=5000)
                next_button_selector = 'button[title="Следующее изображение"]'
                
                for i in range(photo_count):
                    # Достаём текущее фото
                    try:
                        current_img = await page.query_selector('[data-name="GalleryInnerComponent"] img')
                        if current_img:
                            src = await current_img.get_attribute('src')
                            if src and 'images.cdn-cian.ru' in src:
                                # Оставляем размер или добавляем -1
                                if not (src.endswith('-1.jpg') or src.endswith('-2.jpg')):
                                    full_url = src.replace('.jpg', '-1.jpg')
                                else:
                                    full_url = src
                                photos.add(full_url)
                    except:
                        pass
                    
                    # Кликаем дальше
                    if i < photo_count - 1:
                        try:
                            next_button = await page.query_selector(next_button_selector)
                            if next_button and await next_button.is_visible():
                                await next_button.click()
                                await asyncio.sleep(0.4)
                        except:
                            break
                
                logger.info(f"Способ 1: {len(photos)} фото")
            except Exception as e:
                logger.warning(f"Способ 1 ошибка: {e}")
            
            # СПОСОБ 2: Миниатюры (fallback)
            if len(photos) < photo_count:
                try:
                    thumbs = await page.query_selector_all('[data-name="PaginationThumbsComponent"] [data-name="ThumbComponent"] img')
                    for img in thumbs:
                        src = await img.get_attribute('src')
                        if src:
                            full_url = src.replace('-2.jpg', '-1.jpg')
                            photos.add(full_url)
                    logger.info(f"Способ 2: {len(photos)} фото (всего)")
                except:
                    pass
            
            flat['photos'] = list(photos)
            logger.info(f"✅ Собрано {len(flat['photos'])} фото")
            
        except Exception as e:
            logger.error(f"Ошибка фото: {e}")
            flat['photos'] = []

        
        # ПАРСИНГ ТЕЛЕФОНА
        try:
            # Проверяем, какая кнопка есть
            contacts_btn = await page.query_selector('[data-testid="contacts-button"]')
            
            if contacts_btn:
                button_text = (await contacts_btn.inner_text()).strip()
                
                # Если кнопка "Назначить просмотр" - значит телефона нет
                if 'Назначить просмотр' in button_text or 'Связаться' in button_text:
                    flat['phone'] = 'Только связаться'
                else:
                    # Кликаем на кнопку
                    await contacts_btn.click()
                    await asyncio.sleep(1)
                    
                    # Ищем телефон
                    phone_link = await page.query_selector('[data-testid="PhoneLink"]')
                    phone = None
                    
                    if phone_link:
                        try:
                            href = await phone_link.get_attribute('href')
                            if href and href.startswith('tel:'):
                                phone = href.replace('tel:', '').strip()
                        except:
                            pass
                        
                        if not phone:
                            try:
                                phone = (await phone_link.inner_text()).strip()
                            except:
                                phone = 'Не удалось получить'
                    
                    flat['phone'] = phone if phone else 'Не удалось получить'
            else:
                flat['phone'] = 'Кнопка не найдена'
                
        except Exception as e:
            logger.error(f"Ошибка парсинга телефона: {e}")
            flat['phone'] = 'Ошибка'

        
        await browser.close()
        return flat

@app.get("/")
async def root():
    return {
        "service": "Парсер Avito & Cian 🚀",
        "cookies_loaded": os.path.exists(COOKIES_FILE),
        "endpoints": {
            "POST /parse": "Полный парсинг (все данные)",
            "POST /check": "Быстрая проверка (актуальность + цена)"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    """Полный парсинг"""
    url_str = str(request.url)
    start_time = time.time()
    
    source = 'avito' if 'avito.ru' in url_str else 'cian' if 'cian.ru' in url_str else None
    
    logger.info(f"🚀 ЗАПУСК /parse - {source.upper()} - {url_str[:60]}...")
    
    try:
        if 'avito.ru' in url_str:
            result = await parse_avito(url_str, mode="full")
            result['source'] = 'avito'
        elif 'cian.ru' in url_str:
            result = await parse_cian(url_str, mode="full")
            result['source'] = 'cian'
        else:
            raise HTTPException(status_code=400, detail="Только Avito и Cian")
        
        elapsed = time.time() - start_time
        result['url'] = url_str
        result['parse_duration'] = f"{elapsed:.2f}s"
        
        status_emoji = "✅" if result.get('status') == 'active' else "⚠️"
        logger.info(f"{status_emoji} ЗАВЕРШЕНО /parse - {source.upper()} - {elapsed:.2f}s - Status: {result.get('status')}")
        
        return JSONResponse(content=result)
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ОШИБКА /parse - {source.upper()} - {elapsed:.2f}s - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.post("/check")
async def check_flat(request: ParseRequest):
    """Быстрая проверка: актуальность + цена"""
    url_str = str(request.url)
    start_time = time.time()
    
    source = 'avito' if 'avito.ru' in url_str else 'cian' if 'cian.ru' in url_str else None
    
    logger.info(f"⚡ ЗАПУСК /check - {source.upper()} - {url_str[:60]}...")
    
    try:
        if 'avito.ru' in url_str:
            result = await parse_avito(url_str, mode="check")
            result['source'] = 'avito'
        elif 'cian.ru' in url_str:
            result = await parse_cian(url_str, mode="check")
            result['source'] = 'cian'
        else:
            raise HTTPException(status_code=400, detail="Только Avito и Cian")
        
        elapsed = time.time() - start_time
        result['url'] = url_str
        result['check_duration'] = f"{elapsed:.2f}s"
        
        status_emoji = "✅" if result.get('status') == 'active' else "⚠️"
        logger.info(f"{status_emoji} ЗАВЕРШЕНО /check - {source.upper()} - {elapsed:.2f}s - Status: {result.get('status')}")
        
        return JSONResponse(content=result)
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"❌ ОШИБКА /check - {source.upper()} - {elapsed:.2f}s - {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.post("/phone")
async def get_phone_only(request: ParseRequest):
    """
    Получить только телефон (игнорируя платную услугу)
    Используй когда статус = "time" и время прошло
    """
    url_str = str(request.url)
    logger.info(f"📞 Запрос /phone (только телефон): {url_str}")
    
    try:
        if 'avito.ru' in url_str:
            result = await parse_avito_phone_only(url_str)
        else:
            raise HTTPException(status_code=400, detail="Только Avito")
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"❌ Ошибка /phone: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
