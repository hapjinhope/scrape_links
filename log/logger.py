"""
═══════════════════════════════════════════════════════════════════
ФАЙЛ: utils/logger.py
НАЗНАЧЕНИЕ: Настройка системы логирования для всего приложения
═══════════════════════════════════════════════════════════════════

ЧТО ЗДЕСЬ:
- Функция setup_logger() для создания логгера
- Глобальный logger, который используют все модули
- Форматирование логов с временем и уровнем

ЧТО ДЕЛАТЬ:
- Импортируй logger в любом файле: from utils.logger import logger
- Используй: logger.info("текст"), logger.error("ошибка")
- Если нужно изменить формат логов → измени formatter
═══════════════════════════════════════════════════════════════════
"""

import logging
import sys

def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Создаёт и настраивает logger с форматированием
    
    Args:
        name: Имя логгера (по умолчанию имя модуля)
        
    Returns:
        Настроенный logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Если уже есть handlers, не добавляем новые (избегаем дублирования)
    if logger.handlers:
        return logger
    
    # Формат: "2025-10-20 19:45:30 - parser - INFO - Сообщение"
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Вывод в консоль (stdout для Railway)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Глобальный logger для всего приложения
logger = setup_logger("parser_app")
