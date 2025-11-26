from playwright.async_api import async_playwright
import asyncio
import re
import random
import os
import json
import logging
import base64
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from dotenv import load_dotenv
from app.db_cookies import (
    fetch_cookie_record,
    mark_blocked,
)

# ============ ЛОГИРОВАНИЕ ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============ КОНСТАНТЫ ============
load_dotenv()
BASE_DIR = Path(__file__).resolve().parents[2]
COOKIES_FILE = str(BASE_DIR / "avito_session.json")
DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
DEFAULT_TELEGRAM_LOG_BOT_TOKEN = "8216085259:AAEpgRsYRYB4mKGGx5bJpQ7ICRb_W9BhUpY"
DEFAULT_TELEGRAM_LOG_CHAT_ID = "-1003405018295"
DEFAULT_TELEGRAM_LOG_TOPIC_ID = "217"
TELEGRAM_LOG_BOT_TOKEN = os.getenv("TELEGRAM_LOG_BOT_TOKEN", DEFAULT_TELEGRAM_LOG_BOT_TOKEN)
TELEGRAM_LOG_CHAT_ID = os.getenv("TELEGRAM_LOG_CHAT_ID", DEFAULT_TELEGRAM_LOG_CHAT_ID)
TELEGRAM_LOG_TOPIC_ID = os.getenv("TELEGRAM_LOG_TOPIC_ID", DEFAULT_TELEGRAM_LOG_TOPIC_ID)
BLOCKED_PARSED_VALUE = "kd"

# ============ УТИЛИТЫ ============

def _send_telegram_message_sync(message: str):
    if not TELEGRAM_LOG_BOT_TOKEN or not TELEGRAM_LOG_CHAT_ID:
        return
    payload = {
        "chat_id": TELEGRAM_LOG_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }
    if TELEGRAM_LOG_TOPIC_ID:
        payload["message_thread_id"] = TELEGRAM_LOG_TOPIC_ID
    data = urlencode(payload).encode()
    url = f"https://api.telegram.org/bot{TELEGRAM_LOG_BOT_TOKEN}/sendMessage"
    req = Request(url, data=data, method="POST")
    with urlopen(req, timeout=10) as resp:
        resp.read()

async def notify_telegram(message: str):
    """Отправляет лог в Telegram без блокировки основного потока"""
    try:
        await asyncio.to_thread(_send_telegram_message_sync, message)
    except Exception as e:
        logger.warning(f"⚠️ Ошибка отправки лога в Telegram: {e}")

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

async def log_firewall_block_if_needed(page, url: str):
    """Логирует ситуацию, когда Avito возвращает firewall-страницу"""
    # Проверяем наличие типового HTML-блока с сообщением «Доступ ограничен»
    try:
        firewall_container = await page.query_selector('.firewall-container')
        firewall_title = await page.query_selector('h2:has-text("Доступ ограничен")')
        if firewall_container or firewall_title:
            snippet = ""
            if firewall_container:
                snippet = (await firewall_container.inner_text())
                snippet = re.sub(r'\s+', ' ', snippet).strip()
            message = f"🧱 Avito заблокировал доступ по IP для {url}. Фрагмент: {snippet[:200]}"
            logger.error(message)
            await notify_telegram(message)
            return True
    except Exception as e:
        logger.debug(f"Не удалось проверить firewall-блок: {e}")
    return False


def has_many_rooms_indicator(text: str) -> bool:
    """Проверяет, говорит ли текст о 5+ комнатах"""
    if not text:
        return False
    normalized = text.replace('\xa0', ' ').lower()
    if 'многокомнатн' in normalized:
        return True
    if any(word in normalized for word in ['пятикомнат', 'шестикомнат', 'семикомнат', 'семикомнатн']):
        return True
    match = re.search(r'(\d+)', normalized)
    if match:
        try:
            if int(match.group(1)) >= 5:
                return True
        except ValueError:
            pass
    if '5 и более' in normalized or 'более 5' in normalized or '5+' in normalized:
        return True
    return False

async def log_auth_required_if_needed(page, url: str):
    """Проверяет, требует ли Avito авторизации, и логирует/уведомляет"""
    try:
        login_link = await page.query_selector('a[data-marker="header/login-button"]')
        if login_link:
            login_text = (await login_link.inner_text() or "").strip()
            message = f"🔐 Avito требует авторизацию перед парсингом: {url} ({login_text})"
            logger.warning(message)
            await notify_telegram(message)
            return True
    except Exception as e:
        logger.debug(f"Не удалось проверить необходимость авторизации: {e}")
    return False


async def _load_cookies_from_db():
    """
    Пытается взять cookies из таблицы avoto_cookies.
    Возвращает (record, storage_state, blocked_reason)
    """
    try:
        record = await fetch_cookie_record()
    except Exception as e:
        logger.warning(f"⚠️ Не удалось загрузить cookies из БД: {e}")
        return None, None, None

    if record.blocked:
        return record, None, "blocked_in_db"

    return record, record.storage_state, None

# ============ ГЛАВНЫЕ ФУНКЦИИ ============

async def parse_avito(url: str, mode: str = "full"):
    """
    Полный парсер Avito
    mode: "full" = полный парсинг / "check" = актуальность + цена
    """
    cookie_record = None
    db_storage_state = None
    blocked_reason = None

    # Пробуем взять cookies из БД заранее, чтобы не запускать браузер без смысла
    cookie_record, db_storage_state, blocked_reason = await _load_cookies_from_db()
    if blocked_reason == "blocked_in_db":
        warning_msg = "❌ Cookies помечены как заблокированные в БД, пропускаю парсинг"
        logger.warning(warning_msg)
        return {
            "status": "blocked",
            "message": warning_msg,
            "url": url,
        }
    if not db_storage_state:
        raise RuntimeError("⚠️ Cookies из БД не получены, парсинг остановлен")

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
        cookies_count = len(db_storage_state.get('cookies', []))
        logger.info(f"🍪 Загружаю cookies из БД: {cookies_count} шт")
        context_options["storage_state"] = db_storage_state
        
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
        firewall_blocked = await log_firewall_block_if_needed(page, url)
        auth_required = await log_auth_required_if_needed(page, url)

        if firewall_blocked or auth_required:
            reason = "firewall" if firewall_blocked else "auth_required"
            logger.error(f"❌ {reason} — Avito не даёт загрузить страницу")
            if cookie_record:
                try:
                    await mark_blocked(cookie_record)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отметить blocked в БД: {e}")
            await browser.close()
            return {
                'status': 'blocked',
                'message': f'Avito недоступен ({reason})',
                'url': url
            }
        
        if mode == "full":
            await emulate_human_behavior(page)
        
        # ====== СОХРАНЕНИЕ COOKIES ======
        # Сохранение/обновление cookies отключено по требованию (только читаем из БД)
        
                # ====== ПРОВЕРКА АКТУАЛЬНОСТИ (всегда) ======
        try:
            # Проверка 1: "Объявление не посмотреть"
            unpublished_h1 = await page.query_selector('h1:has-text("Объявление не")')
            if unpublished_h1:
                text = (await unpublished_h1.inner_text()).strip()
                if "Объявление не" in text:
                    await browser.close()
                    return {
                        'status': 'unpublished',
                        'message': 'Объявление не активно',
                        'url': url
                    }
            
            # Проверка 2: "Объявление закрыто"
            closed_p = await page.query_selector('p:has-text("Объявление закрыто")')
            if closed_p:
                await browser.close()
                return {
                    'status': 'closed',
                    'message': 'Объявление закрыто',
                    'url': url
                }
            
            # Проверка 3: Общая проверка на сообщение об ошибке
            error_msg = await page.query_selector('h1.EEPdn')
            if error_msg:
                msg_text = (await error_msg.inner_text()).strip()
                if any(word in msg_text for word in ['не', 'закрыто', 'удалено', 'снято']):
                    await browser.close()
                    return {
                        'status': 'unavailable',
                        'message': msg_text,
                        'url': url
                    }
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки актуальности: {e}")
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
        force_rooms_six_from_title = False
        
        # ====== ЗАГОЛОВОК (summary) ======
        try:
            title_el = await page.query_selector('div[data-name="MainNewTitle"] h1')
            if not title_el:
                title_el = await page.query_selector('h1[itemprop="name"]')
            flat['summary'] = (await title_el.inner_text()).strip() if title_el else None
            summary_lower = flat['summary'].lower() if flat['summary'] else ""
            if summary_lower and has_many_rooms_indicator(summary_lower):
                force_rooms_six_from_title = True
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
            params_items = []
            params_containers = await page.query_selector_all('[data-marker="item-view/item-params"]')
            for container in params_containers:
                try:
                    params_in_container = await container.query_selector_all('li')
                    params_items.extend(params_in_container)
                except:
                    continue
            if not params_items:
                params_items = await page.query_selector_all('ul.params__paramsList___XzY3MG li.params__paramsList__item___XzY3MG')
            
            rooms_count = total_area = kitchen_area = floor = floors_total = None
            room_type = bathroom = repair = appliances = None
            deposit = commission = kids = pets = year_built = None
            elevator_passenger = elevator_cargo = parking = None
            house_deposit = house_commission = utilities_counters = utilities_other = None
            living_area = balcony = additional = furniture = ceiling_height = None
            
            for param in params_items:
                try:
                    text = (await param.inner_text()).strip()
                    if ':' in text:
                        parts = text.split(':', 1)
                        key = parts[0].strip()
                        value = parts[1].strip().replace('\xa0', ' ')
                        
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
                        elif 'Жилая площадь' in key:
                            living_area = value
                        elif 'Балкон' in key or 'лоджия' in key:
                            balcony = value
                        elif 'Дополнительно' in key:
                            additional = value
                        elif 'Мебель' in key:
                            furniture = value
                        elif 'Пассажирский лифт' in key:
                            elevator_passenger = value
                        elif 'Грузовой лифт' in key:
                            elevator_cargo = value
                        elif 'Парковка' in key:
                            parking = value
                        elif 'Высота потолков' in key:
                            ceiling_height = value
                except:
                    pass
            
            if rooms_count and has_many_rooms_indicator(rooms_count):
                rooms_count = "6"
            elif force_rooms_six_from_title:
                rooms_count = "6"
            
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
                'living_area': living_area,
                'balcony': balcony,
                'additional_features': additional,
                'furniture': furniture,
                'ceiling_height': ceiling_height,
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
    cookie_record = None
    db_storage_state = None
    blocked_reason = None

    cookie_record, db_storage_state, blocked_reason = await _load_cookies_from_db()
    if blocked_reason == "blocked_in_db":
        warning_msg = "❌ Cookies помечены как blocked в БД, пропускаю запрос телефона"
        logger.warning(warning_msg)
        return {
            'status': 'blocked',
            'message': warning_msg,
            'url': url
        }
    if not db_storage_state:
        raise RuntimeError("⚠️ Cookies из БД не получены, парсинг остановлен")

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
        
        context_options["storage_state"] = db_storage_state
        logger.info("🍪 Cookies загружены из БД")
        
        context = await browser.new_context(**context_options)
        
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)
        
        page = await context.new_page()
        page.set_default_timeout(90000)
        
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        await close_modals(page)

        firewall_blocked = await log_firewall_block_if_needed(page, url)
        auth_required = await log_auth_required_if_needed(page, url)
        if firewall_blocked or auth_required:
            reason = "firewall" if firewall_blocked else "auth_required"
            if cookie_record:
                try:
                    await mark_blocked(cookie_record, BLOCKED_PARSED_VALUE)
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось отметить blocked (phone only): {e}")
            await browser.close()
            return {
                'status': 'blocked',
                'message': f'Avito недоступен ({reason})',
                'url': url
            }
        
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

        # Сохранение/обновление cookies отключено по требованию (только читаем из БД)

        await browser.close()
        
        return {
            'status': 'success' if phone else 'error',
            'phone': phone if phone else 'Не удалось получить',
            'url': url
        }
