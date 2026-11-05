import os
import hmac
import hashlib
import asyncio
from urllib.parse import parse_qsl
from typing import Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Импорт модулей с предыдущих спринтов
from app import search, resolver, radio

app = FastAPI(title="LammotBot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "development_bot_token_replace_me")

def verify_telegram_init_data(authorization: Optional[str] = Header(None)) -> Dict[str, str]:
    if not authorization or not authorization.startswith("tma "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header. Expected 'tma <initData>'")
    
    init_data = authorization[4:]
    try:
        parsed_data = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid initData format")

    if "hash" not in parsed_data:
        raise HTTPException(status_code=401, detail="Missing hash in initData")

    received_hash = parsed_data.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calculated_hash != received_hash:
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")
    
    return parsed_data

async def call_module_func(module, func_names, *args, **kwargs):
    """Динамически ищет и вызывает одну из возможных функций в модуле."""
    for name in func_names:
        func = getattr(module, name, None)
        if callable(func):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
    raise AttributeError(f"Ни одна из функций {func_names} не найдена в модуле {module.__name__}")

# ==========================================
# API Эндпоинты
# ==========================================

@app.get("/api/search")
async def api_search(
    q: str = Query(..., min_length=1, description="Search query for tracks"),
    user_data: Dict[str, Any] = Depends(verify_telegram_init_data)
):
    try:
        results = await call_module_func(search, ["search", "search_tracks", "search_songs", "query"], q)
        return {"ok": True, "data": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/resolve")
async def api_resolve(
    url: str = Query(..., description="Music platform URL to resolve"),
    user_data: Dict[str, Any] = Depends(verify_telegram_init_data)
):
    try:
        track_info = await call_module_func(resolver, ["resolve", "resolve_link", "resolve_url", "get_stream", "get_url"], url)
        return {"ok": True, "data": track_info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/radio")
async def api_radio(
    track_id: str = Query(..., description="Seed track ID for radio recommendations"),
    user_data: Dict[str, Any] = Depends(verify_telegram_init_data)
):
    try:
        recommendations = await call_module_func(radio, ["radio", "get_radio", "get_radio_tracks", "recommendations", "get_recommendations"], track_id)
        return {"ok": True, "data": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# Раздача статики (Frontend)
# ==========================================
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")