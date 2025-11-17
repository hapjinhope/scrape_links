from playwright.async_api import async_playwright
import asyncio
import re
import logging

# ============ ЛОГИРОВАНИЕ ============
logger = logging.getLogger(__name__)

# ============ КОНСТАНТЫ ============
DESKTOP_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ============ ГЛАВНАЯ ФУНКЦИЯ ============

async def parse_cian(url: str, mode: str = "full"):
    """
    Полный парсер CIAN
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
        
        # ====== ПРОВЕРКА АКТУАЛЬНОСТИ (всегда) ======
        try:
            unpublished = await page.query_selector('[data-name="OfferUnpublished"]')
            if unpublished:
                await browser.close()
                return {'status': 'unpublished', 'message': 'Объявление снято'}
        except:
            pass
        
        # ====== ЦЕНА (всегда) ======
        try:
            price_el = await page.query_selector("[data-testid='price-amount']")
            price = (await price_el.inner_text()).strip() if price_el else None
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
        flat = {'status': 'active', 'price': price}

        # ====== ЗАГОЛОВОК (summary) ======
        try:
            h1 = await page.query_selector("h1")
            flat['summary'] = (await h1.inner_text()).strip() if h1 else None
        except:
            flat['summary'] = None

        # ====== КОМНАТНОСТЬ (из summary) ======
        rooms = None
        if flat['summary']:
            summary_lower = flat['summary'].lower()
            
            if 'многокомнатн' in summary_lower:
                rooms = '6'
            elif 'студ' in summary_lower:
                rooms = '0'
            elif '1-комн' in summary_lower or 'однокомнатн' in summary_lower:
                rooms = '1'
            elif '2-комн' in summary_lower or 'двухкомнатн' in summary_lower:
                rooms = '2'
            elif '3-комн' in summary_lower or 'трёхкомнатн' in summary_lower or 'трехкомнатн' in summary_lower:
                rooms = '3'
            elif '4-комн' in summary_lower or 'четырёхкомнатн' in summary_lower or 'четырехкомнатн' in summary_lower:
                rooms = '4'
            elif '5-комн' in summary_lower or 'пятикомнатн' in summary_lower:
                rooms = '5'
            elif '6-комн' in summary_lower or 'шестикомнатн' in summary_lower:
                rooms = '6'
            elif 'своб' in summary_lower:
                rooms = '7'

        flat['rooms'] = rooms

        # ====== АДРЕС ======
        try:
            address_items = await page.query_selector_all('[data-name="AddressItem"]')
            address_parts = []
            for item in address_items:
                address_parts.append((await item.inner_text()).strip())
            flat['address'] = ', '.join(address_parts) if address_parts else None
        except:
            flat['address'] = None
        
        # ====== ЖК (жилой комплекс) ======
        try:
            jk_el = await page.query_selector('[data-name="ParentNew"] a')
            flat['jk'] = (await jk_el.inner_text()).strip() if jk_el else None
        except:
            flat['jk'] = None
        
        # ====== МЕТРО ======
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
        
        # ====== ОПЛАТА (ЖКХ, залог, комиссия) ======
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
                'payment_zhkh': payment_zhkh, 
                'payment_deposit': payment_deposit,
                'payment_commission': payment_commission, 
                'payment_prepay': payment_prepay,
                'payment_term': payment_term
            })
        except:
            pass
        
        # ====== ХАРАКТЕРИСТИКИ (площади, этаж, год) ======
        try:
            total_area = living_area = kitchen_area = floor = floors_total = year_built = None
            layout = bathroom = elevators = parking = None
            ceiling_height = repair = windows_view = balcony_count = loggia_count = None
            
            # ШАГ 1: ObjectFactoids (приоритет)
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
            
            # ШАГ 2: OfferSummaryInfoItem (fallback + новые поля)
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
                'total_area': total_area, 
                'living_area': living_area, 
                'kitchen_area': kitchen_area,
                'floor': floor, 
                'floors_total': floors_total,
                'layout': layout, 
                'bathroom': bathroom, 
                'year_built': year_built,
                'elevators': elevators, 
                'parking': parking,
                'ceiling_height': ceiling_height, 
                'repair': repair, 
                'windows_view': windows_view,
                'balcony_count': balcony_count, 
                'loggia_count': loggia_count
            })
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга характеристик: {e}")
            pass

        # ====== УДОБСТВА (amenities) ======
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
        
        # ====== ОПИСАНИЕ ======
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
            logger.error(f"❌ Ошибка парсинга описания: {e}")
            flat['description'] = None
        
        # ====== ФОТО (с навигацией по галерее) ======
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
                        logger.info(f"📸 Обнаружено {photo_count} фото")
            except:
                photo_count = 30
            
            # СПОСОБ 1: Клики по галерее (основной)
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
                
                logger.info(f"📸 Способ 1: {len(photos)} фото собрано")
            except Exception as e:
                logger.warning(f"⚠️ Способ 1 (галерея) ошибка: {e}")
            
            # СПОСОБ 2: Миниатюры (fallback)
            if len(photos) < photo_count:
                try:
                    thumbs = await page.query_selector_all('[data-name="PaginationThumbsComponent"] [data-name="ThumbComponent"] img')
                    for img in thumbs:
                        src = await img.get_attribute('src')
                        if src:
                            full_url = src.replace('-2.jpg', '-1.jpg')
                            photos.add(full_url)
                    logger.info(f"📸 Способ 2 (миниатюры): {len(photos)} фото (всего)")
                except Exception as e:
                    logger.warning(f"⚠️ Способ 2 ошибка: {e}")
            
            flat['photos'] = list(photos)
            logger.info(f"✅ ФОТО: Собрано {len(flat['photos'])} изображений")
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга фото: {e}")
            flat['photos'] = []

        # ====== ТЕЛЕФОН ======
        try:
            contacts_btn = await page.query_selector('[data-testid="contacts-button"]')
            
            if contacts_btn:
                button_text = (await contacts_btn.inner_text()).strip()
                
                if 'Назначить просмотр' in button_text or 'Связаться' in button_text:
                    flat['phone'] = 'Только связаться'
                    logger.info("📞 Доступна только опция 'Связаться'")
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
                                logger.info(f"✅ Телефон (tel:): {phone}")
                        except:
                            pass
                        
                        if not phone:
                            try:
                                phone = (await phone_link.inner_text()).strip()
                                logger.info(f"✅ Телефон (текст): {phone}")
                            except:
                                phone = 'Не удалось получить'
                    
                    flat['phone'] = phone if phone else 'Не удалось получить'
            else:
                flat['phone'] = 'Кнопка не найдена'
                logger.warning("⚠️ Кнопка контактов не найдена")
                
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга телефона: {e}")
            flat['phone'] = 'Ошибка'

        await browser.close()
        logger.info(f"✅ CIAN парсинг завершён: {len(flat)} полей данных")
        return flat
