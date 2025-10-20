"""
═══════════════════════════════════════════════════════════════════
ФАЙЛ: parsers/helpers.py
НАЗНАЧЕНИЕ: Вспомогательные функции для эмуляции человека
═══════════════════════════════════════════════════════════════════

ЧТО ЗДЕСЬ:
- human_like_mouse_move() - плавное движение мыши
- emulate_human_behavior() - скроллинг и движения как у человека
- close_modals() - закрытие всплывающих окон
- click_continue_if_exists() - клик на кнопку "Продолжить"

ЧТО ДЕЛАТЬ:
- Эти функции используются в avito_parser.py и cian_parser.py
- Не изменяй их, если не нужно менять поведение "человека"
═══════════════════════════════════════════════════════════════════
"""

import asyncio
import random
from playwright.async_api import Page

async def human_like_mouse_move(page: Page, from_x: int, from_y: int, to_x: int, to_y: int):
    """
    Плавное движение мыши по кривой (как человек)
    
    Args:
        page: Страница Playwright
        from_x, from_y: Начальные координаты
        to_x, to_y: Конечные координаты
    """
    steps = random.randint(10, 20)
    for i in range(steps):
        progress = i / steps
        curve = random.uniform(-5, 5)  # Небольшая кривизна
        x = from_x + (to_x - from_x) * progress + curve
        y = from_y + (to_y - from_y) * progress + curve
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.02, 0.05))

async def emulate_human_behavior(page: Page):
    """
    Эмуляция поведения человека: движение мыши + скроллинг
    
    Args:
        page: Страница Playwright
    """
    # Случайное движение мыши
    start_x, start_y = random.randint(100, 400), random.randint(200, 500)
    end_x, end_y = random.randint(600, 1200), random.randint(400, 800)
    await human_like_mouse_move(page, start_x, start_y, end_x, end_y)
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    # Скроллинг вниз с случайными паузами
    for _ in range(random.randint(3, 5)):
        scroll_amount = random.randint(200, 500)
        if random.random() < 0.2:  # 20% вероятность скроллинга вверх
            scroll_amount = -scroll_amount
        await page.evaluate(f'window.scrollBy(0, {scroll_amount})')
        await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Мелкие подёргивания мыши (jitter)
    for _ in range(random.randint(1, 3)):
        jitter_x = end_x + random.randint(-3, 3)
        jitter_y = end_y + random.randint(-3, 3)
        await page.mouse.move(jitter_x, jitter_y)
        await asyncio.sleep(random.uniform(0.1, 0.2))

async def close_modals(page: Page) -> bool:
    """
    Закрывает всплывающие окна (модалки)
    
    Args:
        page: Страница Playwright
        
    Returns:
        True если модалку закрыли, False если не нашли
    """
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

async def click_continue_if_exists(page: Page) -> bool:
    """
    Кликает на кнопку "Продолжить" если она есть
    
    Args:
        page: Страница Playwright
        
    Returns:
        True если кликнули, False если кнопки нет
    """
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
                    # Кликаем в случайную точку кнопки (не в центр)
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
