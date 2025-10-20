"""
═══════════════════════════════════════════════════════════════════
ФАЙЛ: main.py
НАЗНАЧЕНИЕ: Главный файл приложения — точка входа для Railway
═══════════════════════════════════════════════════════════════════

ЧТО ЗДЕСЬ:
- Инициализация FastAPI приложения
- Роуты API: /parse (полный парсинг), /check (быстрая проверка)
- Запуск uvicorn сервера

ЧТО ДЕЛАТЬ:
- Railway автоматически запустит этот файл через Procfile
- Локально запускай: python main.py
- API будет доступно на http://0.0.0.0:8000

ЭНДПОИНТЫ:
- GET  /           → Информация о сервисе
- POST /parse      → Полный парсинг объявления
- POST /check      → Быстрая проверка (актуальность + цена)

ПРИМЕРЫ ЗАПРОСОВ:
curl -X POST "http://localhost:8000/parse" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.avito.ru/moskva/kvartiry/..."}'
═══════════════════════════════════════════════════════════════════
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

# Импорт парсеров
from parsers.avito_parser import parse_avito
from parsers.cian_parser import parse_cian

# Импорт настроек
from settings.settings import PORT, HOST, COOKIES_FILE

# Импорт логгера
from log.logger import logger

# ============== ИНИЦИАЛИЗАЦИЯ FASTAPI ==============
app = FastAPI(
    title="Парсер квартир Avito & Cian",
    description="API для парсинга объявлений аренды квартир",
    version="2.0.0"
)

# ============== PYDANTIC МОДЕЛИ ==============
class ParseRequest(BaseModel):
    """Модель запроса на парсинг"""
    url: HttpUrl
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.avito.ru/moskva/kvartiry/2-k._kvartira_56m_714et._3404467894"
            }
        }

# ============== РОУТЫ ==============

@app.get("/")
async def root():
    """
    Главная страница API
    
    Returns:
        Информация о сервисе и доступных эндпоинтах
    """
    return {
        "service": "Парсер Avito & Cian 🚀",
        "version": "2.0.0",
        "cookies_loaded": os.path.exists(COOKIES_FILE),
        "endpoints": {
            "GET /": "Информация о сервисе",
            "POST /parse": "Полный парсинг (все данные)",
            "POST /check": "Быстрая проверка (актуальность + цена)"
        },
        "example": {
            "method": "POST",
            "url": "/parse",
            "body": {
                "url": "https://www.avito.ru/moskva/kvartiry/..."
            }
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    """
    Полный парсинг объявления
    
    Args:
        request: ParseRequest с URL объявления
        
    Returns:
        JSON с полными данными квартиры
        
    Raises:
        HTTPException: 400 если сайт не поддерживается, 500 при ошибке парсинга
    """
    url_str = str(request.url)
    logger.info(f"📥 Запрос на полный парсинг: {url_str}")
    
    try:
        if 'avito.ru' in url_str:
            logger.info("🔍 Парсинг Avito (режим: full)")
            result = await parse_avito(url_str, mode="full")
        elif 'cian.ru' in url_str:
            logger.info("🔍 Парсинг Cian (режим: full)")
            result = await parse_cian(url_str, mode="full")
        else:
            logger.error(f"❌ Неподдерживаемый сайт: {url_str}")
            raise HTTPException(
                status_code=400,
                detail="Поддерживаются только Avito и Cian"
            )
        
        logger.info(f"✅ Парсинг завершён. Статус: {result.get('status')}")
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка парсинга: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check")
async def check_flat(request: ParseRequest):
    """
    Быстрая проверка объявления (актуальность + цена)
    
    Args:
        request: ParseRequest с URL объявления
        
    Returns:
        JSON с актуальностью и ценой (быстрый режим)
        
    Raises:
        HTTPException: 400 если сайт не поддерживается, 500 при ошибке
    """
    url_str = str(request.url)
    logger.info(f"📥 Запрос на быструю проверку: {url_str}")
    
    try:
        if 'avito.ru' in url_str:
            logger.info("⚡ Проверка Avito (режим: check)")
            result = await parse_avito(url_str, mode="check")
        elif 'cian.ru' in url_str:
            logger.info("⚡ Проверка Cian (режим: check)")
            result = await parse_cian(url_str, mode="check")
        else:
            logger.error(f"❌ Неподдерживаемый сайт: {url_str}")
            raise HTTPException(
                status_code=400,
                detail="Поддерживаются только Avito и Cian"
            )
        
        logger.info(f"✅ Проверка завершена. Статус: {result.get('status')}")
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка проверки: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ============== ЗАПУСК СЕРВЕРА ==============
if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"🚀 Запуск сервера на {HOST}:{PORT}")
    logger.info(f"📖 Документация: http://{HOST}:{PORT}/docs")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
