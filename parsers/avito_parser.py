"""
═══════════════════════════════════════════════════════════════════
ФАЙЛ: parsers/avito_parser.py
НАЗНАЧЕНИЕ: Парсер объявлений Avito (полный парсинг и быстрая проверка)
═══════════════════════════════════════════════════════════════════

ЧТО ЗДЕСЬ:
- parse_avito() - основная функция парсинга
- Поддержка двух режимов:
  * "full" - полный парсинг всех данных (фото, телефон, описание)
  * "check" - быстрая проверка (только актуальность + цена)
- Работа с cookies для обхода капчи
- Парсинг всех полей: цена, адрес, метро, параметры, фото, телефон

ЧТО ДЕЛАТЬ:
- Импортируй в main.py: from parsers.avito_parser import parse_avito
- Вызывай: result = await parse_avito(url, mode="full")
- Если нужно добавить новое поле → добавь парсинг в блок "Параметры"
═══════════════════════════════════════════════════════════════════
"""

import asyncio
import json
import os
from playwright.async_api import async_playwright

# Импорт настроек
from config.settings import (
    COOKIES_FILE,
    DESKTOP_UA,
    BROWSER_ARGS,
    BROWSER_TIMEOUT
)

# Импорт вспомогательных функций
from parsers.helpers import (
    emulate_human_behavior,
    close_modals,
    click_continue_if_exists
)

# Импорт логгера
from utils.logger import logger

async def parse_avito(url: str, mode: str = "full") -> dict:
    """
    Парсит объявление с Avito
    
    Args:
        url: Ссылка на объявление
        mode: "full" (полный парсинг) или "check" (только актуальность + цена)
        
    Returns:
        Словарь с данными квартиры
    """
    async with async_playwright() as p:
        # ========== ЗАПУСК БРАУЗЕРА ==========
        browser = await p.chromium.launch(
            headless=True,
            args=BROWSER_ARGS + [f'--user-agent={DESKTOP_UA}'],
            timeout=BROWSER_TIMEOUT
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
        
        # ========== ЗАГРУЗКА COOKIES ==========
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
        
        # Скрываем автоматизацию
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });
        """)
        
        page = await context.new_page()
        page.set_default_timeout(BROWSER_TIMEOUT)
        
        # ========== ГЛАВНАЯ СТРАНИЦА (только для full mode) ==========
        if mode == "full":
            try:
                await page.goto("https://www.avito.ru/", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                await close_modals(page)
                await emulate_human_behavior(page)
            except:
                pass
        
        # ========== СТРАНИЦА ОБЪЯВЛЕНИЯ ==========
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000 if mode == "check" else 3000)
        await close_modals(page)
        
        if mode == "full":
            await emulate_human_behavior(page)
        
        # ========== СОХРАНЕНИЕ COOKIES ==========
        try:
            storage_state = await context.storage_state()
            new_cookies_count = len(storage_state.get('cookies', []))
            
            with open(COOKIES_FILE, 'w') as f:
                json.dump(storage_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"🍪 Cookies обновлены: {new_cookies_count} шт → {COOKIES_FILE}")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения cookies: {e}")
        
        # ========== ПРОВЕРКА АКТУАЛЬНОСТИ (всегда) ==========
        try:
            unpublished = await page.query_selector('h1.EEPdn:has-text("Объявление не")')
            if unpublished:
                await browser.close()
                return {'status': 'unpublished', 'message': 'Объявление снято'}
        except:
            pass
        
        # ========== ЦЕНА (всегда) ==========
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
        
        # ========== РЕЖИМ "check" - только актуальность + цена ==========
        if mode == "check":
            await browser.close()
            return {
                'status': 'active',
                'price': price,
                'mode': 'quick_check'
            }
        
        # ========== РЕЖИМ "full" - полный парсинг ==========
        messages_only = False
        try:
            no_calls = await page.query_selector('button:has-text("Без звонков")')
            if no_calls:
                messages_only = True
        except:
            pass
        
        flat = {'status': 'active', 'messages_only': messages_only, 'price': price}
        
        # Заголовок
        try:
            title_el = await page.query_selector('h1[itemprop="name"]')
            flat['summary'] = (await title_el.inner_text()).strip() if title_el else None
        except:
            flat['summary'] = None
        
        # Адрес
        try:
            addr_el = await page.query_selector('span.xLPJ6')
            flat['address'] = (await addr_el.inner_text()).strip() if addr_el else None
        except:
            flat['address'] = None
        
        # Метро
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
        
        # Описание
        try:
            desc_el = await page.query_selector('div[itemprop="description"][data-marker="item-view/item-description"]')
            flat['description'] = (await desc_el.inner_text()).strip() if desc_el else None
        except:
            flat['description'] = None
        
        # Продавец
        try:
            seller_el = await page.query_selector('[data-marker="seller-info/name"] span.TTiHl')
            flat['seller_name'] = (await seller_el.inner_text()).strip() if seller_el else None
        except:
            flat['seller_name'] = None
        
        # ========== ПАРАМЕТРЫ КВАРТИРЫ ==========
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
        
        # ========== ПАРАМЕТРЫ ДОМА ==========
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
        
        # ========== ПРАВИЛА ==========
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
        
        # ========== ФОТО ==========
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
        
        # ========== ТЕЛЕФОН ==========
        if messages_only:
            flat['phone'] = 'только сообщения'
        else:
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await asyncio.sleep(1)
                
                # ПРОВЕРКА ПЛАТНОЙ УСЛУГИ "Связаться сейчас"
                paid_service = False
                free_after_time = None
                
                try:
                    paid_header = await page.query_selector('h2:has-text("Свяжитесь сейчас")')
                    if paid_header:
                        paid_service = True
                        logger.info("Обнаружена платная услуга 'Связаться сейчас'")
                        
                        time_elem = await page.query_selector('strong.OVzrF')
                        if time_elem:
                            free_after_time = (await time_elem.inner_text()).strip()
                            logger.info(f"Бесплатно после: {free_after_time} МСК")
                except Exception as e:
                    logger.warning(f"Ошибка проверки платной услуги: {e}")
                
                if paid_service:
                    if free_after_time:
                        flat['phone'] = f'Платно сейчас, бесплатно после {free_after_time} МСК'
                    else:
                        flat['phone'] = 'Платно сейчас (новое объявление)'
                    logger.info(f"Телефон: {flat['phone']}")
                else:
                    # Обычный парсинг телефона
                    phone_clicked = False
                    for selector in ['button[data-marker="item-phone-button/card"]', 'button:has-text("Показать телефон")', 'button.QaQVm']:
                        try:
                            phone_button = await page.query_selector(selector)
                            if phone_button and await phone_button.is_visible():
                                await phone_button.scroll_into_view_if_needed()
                                await asyncio.sleep(0.5)
                                await phone_button.click()
                                phone_clicked = True
                                await asyncio.sleep(3)
                                break
                        except:
                            continue
                    
                    if phone_clicked:
                        phone_found = False
                        
                        # tel: ссылка
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
                                            break
                                except:
                                    pass
                        except:
                            pass
                        
                        # base64 картинка
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
                                                flat['phone'] = phone_src
                                                phone_found = True
                                                break
                                    if phone_found:
                                        break
                            except:
                                pass
                        
                        if not phone_found:
                            flat['phone'] = 'Не удалось получить'
                    else:
                        flat['phone'] = 'Кнопка не найдена'
            except:
                flat['phone'] = 'Ошибка'
        
        await browser.close()
        return flat
