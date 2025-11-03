from playwright.async_api import async_playwright
import asyncio
import re
import random
import os
import json
import logging
import base64

# ============ ЛОГИРОВАНИЕ ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============ КОНСТАНТЫ ============
COOKIES_FILE = "avito_session.json"
DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ============ УТИЛИТЫ ============

async def human_like_mouse_move(page, from_x, from_y, to_x, to_y):
    """Имитирует естественное движение мыши"""
    steps = random.randint(10, 20)
    for i in range(steps):
        progress = i / steps
        curve = random.uniform(-5, 5)
        x = from_x + (to_x - from_x) * progress + curve
        y = from_y + (to_y - from_y) * progress + curve
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.02, 0.05))

async def emulate_human_behavior(page):
    """Имитирует поведение человека: скролл, движение мыши"""
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
    """Закрывает модальные окна на Avito"""
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
    """Кликает на кнопку 'Продолжить' если она есть"""
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

# ============ ГЛАВНЫЕ ФУНКЦИИ ============

async def parse_avito(url: str, mode: str = "full"):
    """
    Полный парсер Avito
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
        
        # ====== ЗАГРУЗКА COOKIES ======
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
        
        # ====== АНТИ-ДЕТЕКТ ======
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        """)
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        # ====== ПРОГРЕВ (только для full mode) ======
        if mode == "full":
            try:
                await page.goto("https://www.avito.ru/", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                await close_modals(page)
                await emulate_human_behavior(page)
            except:
                pass
        
        # ====== ЗАГРУЗКА ОБЪЯВЛЕНИЯ ======
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000 if mode == "check" else 3000)
        await close_modals(page)
        
        if mode == "full":
            await emulate_human_behavior(page)
        
        # ====== СОХРАНЕНИЕ COOKIES ======
        try:
            storage_state = await context.storage_state()
            new_cookies_count = len(storage_state.get('cookies', []))
            
            with open(COOKIES_FILE, 'w') as f:
                json.dump(storage_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"🍪 Cookies обновлены: {new_cookies_count} шт → {COOKIES_FILE}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения cookies: {e}")
        
        # ====== ПРОВЕРКА АКТУАЛЬНОСТИ (всегда) ======
        try:
            unpublished = await page.query_selector('h1.EEPdn:has-text("Объявление не")')
            if unpublished:
                await browser.close()
                return {'status': 'unpublished', 'message': 'Объявление снято'}
        except:
            pass
        
        # ====== ЦЕНА (всегда) ======
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
        
        # ====== РЕЖИМ "check" - возвращаем рано ======
        if mode == "check":
            await browser.close()
            return {
                'status': 'active',
                'price': price,
                'mode': 'quick_check'
            }
        
        # ====== РЕЖИМ "full" - полный парсинг ======
        
        # Проверяем "только сообщения"
        messages_only = False
        try:
            no_calls = await page.query_selector('button:has-text("Без звонков")')
            if no_calls:
                messages_only = True
        except:
            pass
        
        flat = {'status': 'active', 'messages_only': messages_only, 'price': price}
        
        # ====== ЗАГОЛОВОК (summary) ======
        try:
            title_el = await page.query_selector('h1[itemprop="name"]')
            flat['summary'] = (await title_el.inner_text()).strip() if title_el else None
        except:
            flat['summary'] = None
        
        # ====== АДРЕС (ИСПРАВЛЕНО) ======
        try:
            addr_el = await page.query_selector('span.style__item-address__string___XzQ5MT')
            flat['address'] = (await addr_el.inner_text()).strip() if addr_el else None
        except:
            flat['address'] = None
        
        # ====== МЕТРО (ИСПРАВЛЕНО) ======
        try:
            metros = []
            metro_items = await page.query_selector_all('span.style__item-address-georeferences-item___XzQ5MT')
            for item in metro_items:
                try:
                    spans = await item.query_selector_all('span')
                    if len(spans) >= 2:
                        station = (await spans[1].inner_text()).strip()
                        time_span = await item.query_selector('span.style__item-address-georeferences-item-interval___XzQ5MT')
                        if time_span:
                            time_text = (await time_span.inner_text()).strip()
                            metros.append(f"{station} ({time_text})")
                        else:
                            metros.append(station)
                except:
                    pass
            flat['metro'] = metros
        except:
            flat['metro'] = []
        
        # ====== ОПИСАНИЕ ======
        try:
            desc_el = await page.query_selector('div[itemprop="description"][data-marker="item-view/item-description"]')
            flat['description'] = (await desc_el.inner_text()).strip() if desc_el else None
        except:
            flat['description'] = None
        
        # ====== ПРОДАВЕЦ ======
        try:
            seller_el = await page.query_selector('[data-marker="seller-info/name"] span.TTiHl')
            flat['seller_name'] = (await seller_el.inner_text()).strip() if seller_el else None
        except:
            flat['seller_name'] = None
        
        # ====== ПАРАМЕТРЫ КВАРТИРЫ (ИСПРАВЛЕНО) ======
        try:
            params_list = await page.query_selector_all('ul.params__paramsList___XzY3MG li.params__paramsList__item___XzY3MG')
            
            rooms_count = total_area = kitchen_area = floor = floors_total = None
            room_type = bathroom = repair = appliances = None
            deposit = commission = kids = pets = year_built = None
            elevator_passenger = elevator_cargo = parking = None
            house_deposit = house_commission = utilities_counters = utilities_other = None
            
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
                        elif key == 'Этаж' and 'из' in value:
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
                        elif 'Залог' in key and not deposit:
                            deposit = value
                        elif 'Комиссия' in key and not commission:
                            commission = value
                        elif 'По счётчикам' in key:
                            utilities_counters = value
                        elif 'Другие ЖКУ' in key:
                            utilities_other = value
                        elif 'Можно с детьми' in key and not kids:
                            kids = value
                        elif 'Можно с животными' in key and not pets:
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
                'rooms_count': rooms_count,
                'total_area': total_area,
                'kitchen_area': kitchen_area,
                'floor': floor,
                'floors_total': floors_total,
                'room_type': room_type,
                'bathroom': bathroom,
                'repair': repair,
                'appliances': appliances,
                'deposit': deposit,
                'commission': commission,
                'kids': kids,
                'pets': pets,
                'year_built': year_built,
                'elevator_passenger': elevator_passenger,
                'elevator_cargo': elevator_cargo,
                'parking': parking,
                'house_deposit': house_deposit,
                'house_commission': house_commission,
                'utilities_counters': utilities_counters,
                'utilities_other': utilities_other
            })
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга параметров: {e}")
            pass
        
        # ====== ФОТО (ИСПРАВЛЕНО) ======
        try:
            photos = set()
            
            photo_items = await page.query_selector_all('li.images-preview__previewImageWrapper___XzJiNj img')
            
            for photo_el in photo_items:
                try:
                    src = await photo_el.get_attribute('srcset')
                    if src:
                        first_url = src.split(' ')[0]
                        if first_url.startswith('http'):
                            photos.add(first_url)
                    else:
                        src = await photo_el.get_attribute('src')
                        if src and src.startswith('http'):
                            photos.add(src)
                except:
                    pass
            
            flat['photos'] = list(photos)
            logger.info(f"📸 Собрано {len(flat['photos'])} фото")
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга фото: {e}")
            flat['photos'] = []
        
        # ====== ТЕЛЕФОН ======
        if messages_only:
            flat['phone'] = 'только сообщения'
        else:
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(1)
                
                # ---- Проверка платной услуги ----
                paid_service = False
                free_after_time = None

                try:
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
                                if ':' in time_text and len(time_text) <= 6:
                                    free_after_time = time_text
                                    logger.info(f"⏰ Бесплатно после: {free_after_time} МСК")
                                    break
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки платной услуги: {e}")

                if paid_service:
                    await browser.close()
                    return {
                        'status': 'time',
                        'message': 'Телефон платный сейчас',
                        'free_after': free_after_time if free_after_time else 'неизвестно',
                        'url': url
                    }

                # ---- Обычный парсинг телефона ----
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
                    
                    # Способ 2: base64
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
                                            flat['phone'] = phone_src
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
        logger.info(f"✅ AVITO парсинг завершён: {len(flat)} полей данных")
        return flat

async def parse_avito_phone_only(url: str) -> dict:
    """Парсит ТОЛЬКО телефон с Avito (игнорирует платную услугу)"""
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
        
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await asyncio.sleep(1)
        
        phone = None
        
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
                                    logger.info("🖼️ Найдена base64 картинка")
                                    phone = phone_src
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
