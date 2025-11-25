import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
# По умолчанию таблица avito_cookies (можно переопределить через COOKIES_TABLE)
COOKIES_TABLE = os.getenv("COOKIES_TABLE", "avito_cookies")
# Опционально: имя набора куков (столбец name), по умолчанию 'links'
COOKIES_NAME = os.getenv("COOKIES_NAME", "links")
BLOCKED_VALUE = "kd"


@dataclass
class AvitoCookieRecord:
    id: Optional[Any]
    storage_state: Dict[str, Any]
    blocked: bool
    parsed_value: Any
    cookie_column: str = "cookies"
    blocked_column: str = "blocked"
    parsed_column: str = "parsed"
    id_column: str = "id"


def _require_supabase():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_KEY не заданы")


def _headers():
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _table_url():
    return f"{SUPABASE_URL}/rest/v1/{COOKIES_TABLE}"


def _normalize_storage_state(raw_state: Any) -> Dict[str, Any]:
    if raw_state is None:
        raise ValueError("Нет данных cookies в записи avoto_cookies")
    if isinstance(raw_state, dict):
        return raw_state
    if isinstance(raw_state, list):
        return {"cookies": raw_state}
    if isinstance(raw_state, (bytes, bytearray)):
        try:
            raw_state = raw_state.decode()
        except Exception:
            pass
    if isinstance(raw_state, str):
        return json.loads(raw_state)
    raise ValueError(f"Неизвестный формат cookies: {type(raw_state)}")


async def fetch_cookie_record() -> AvitoCookieRecord:
    """Возвращает первую запись с blocked=false."""
    _require_supabase()

    def _fetch():
        resp = requests.get(
            _table_url(),
            headers=_headers(),
            params={
                "blocked": "eq.false",
                **({"name": f"eq.{COOKIES_NAME}"} if COOKIES_NAME else {}),
                "order": "updated_at.nullsfirst,created_at.nullsfirst",
                "limit": 1,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            raise RuntimeError("Нет доступных cookies (blocked=false)")
        return data[0]

    row = await asyncio.to_thread(_fetch)
    storage_state = _normalize_storage_state(
        row.get("cookies") or row.get("storage_state") or row.get("data")
    )
    blocked = bool(row.get("blocked", False))
    parsed_value = row.get("parsed")
    record_id = row.get("id") or row.get("cookie_id") or row.get("pk")

    return AvitoCookieRecord(
        id=record_id,
        storage_state=storage_state,
        blocked=blocked,
        parsed_value=parsed_value,
    )


async def mark_blocked(record: AvitoCookieRecord, parsed_value: Optional[str] = None) -> None:
    """Помечает запись как заблокированную и parsed=kd (или своё)."""
    _require_supabase()
    if not record.id:
        return
    payload = {"blocked": True}
    if parsed_value:
        payload["parsed"] = parsed_value

    def _patch():
        resp = requests.patch(
            _table_url(),
            headers=_headers(),
            params={
                "id": f"eq.{record.id}",
                **({"name": f"eq.{COOKIES_NAME}"} if COOKIES_NAME else {}),
            },
            json=payload,
            timeout=10,
        )
        try:
            resp.raise_for_status()
        except Exception as e:
            logger.warning("⚠️ mark_blocked failed: %s - %s", e, resp.text)
            raise

    await asyncio.to_thread(_patch)


async def mark_parsed(record: AvitoCookieRecord, parsed_value: str) -> None:
    """Отмечает parsed, если запись найдена."""
    _require_supabase()
    if not record.id:
        return

    def _patch():
        resp = requests.patch(
            _table_url(),
            headers=_headers(),
            params={
                "id": f"eq.{record.id}",
                **({"name": f"eq.{COOKIES_NAME}"} if COOKIES_NAME else {}),
            },
            json={"parsed": parsed_value},
            timeout=10,
        )
        try:
            resp.raise_for_status()
        except Exception as e:
            logger.warning("⚠️ mark_parsed failed: %s - %s", e, resp.text)
            raise

    await asyncio.to_thread(_patch)


async def save_storage_state(record: AvitoCookieRecord, storage_state: Dict[str, Any]) -> None:
    """Обновляет cookies в БД и сбрасывает blocked=false."""
    _require_supabase()
    if not record.id:
        return

    payload = {"cookies": storage_state, "blocked": False}

    def _patch():
        resp = requests.patch(
            f"{_table_url()}?id=eq.{record.id}",
            headers=_headers(),
            data=json.dumps(payload),
            timeout=10,
        )
        resp.raise_for_status()

    await asyncio.to_thread(_patch)


async def ensure_db_ready(timeout: float = 3.0) -> bool:
    """Быстрая проверка доступности Supabase."""
    try:
        await fetch_cookie_record()
        return True
    except Exception as e:
        logger.warning("⚠️ БД для cookies недоступна: %s", e)
        return False
