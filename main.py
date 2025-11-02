from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
import time
import logging
import os
from app.parsers.avito_parser import parse_avito, parse_avito_phone_only
from app.parsers.cian_parser import parse_cian

# ============ ЛОГИРОВАНИЕ ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============ МОДЕЛИ ============
class ParseRequest(BaseModel):
    url: HttpUrl

# ============ ПРИЛОЖЕНИЕ ============
app = FastAPI(title="Парсер квартир Avito & Cian 🏠")

# ============ ENDPOINTS ============

@app.get("/")
async def root():
    """Главная страница - информация о сервисе"""
    return {
        "service": "Парсер Avito & Cian 🚀",
        "version": "1.0",
        "endpoints": {
            "POST /parse": "Полный парсинг (все данные)",
            "POST /check": "Быстрая проверка (актуальность + цена)",
            "POST /phone": "Только телефон (Avito)"
        }
    }

@app.post("/parse")
async def parse_flat(request: ParseRequest):
    """Полный парсинг квартиры"""
    url_str = str(request.url)
    start_time = time.time()
    
    # Определяем источник
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
    """Получить только телефон (игнорируя платную услугу)"""
    url_str = str(request.url)
    logger.info(f"📞 ЗАПУСК /phone - {url_str[:60]}...")
    
    try:
        if 'avito.ru' in url_str:
            result = await parse_avito_phone_only(url_str)
        else:
            raise HTTPException(status_code=400, detail="Только Avito")
        
        logger.info(f"✅ ЗАВЕРШЕНО /phone - phone: {result.get('phone')[:20]}")
        return JSONResponse(content=result)
    
    except Exception as e:
        logger.error(f"❌ ОШИБКА /phone: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============ ЗАПУСК ============
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
