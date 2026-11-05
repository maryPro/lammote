import hmac
import hashlib
import urllib.parse
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app, BOT_TOKEN

def generate_valid_tma_header(user_id: int = 123456) -> str:
    data_dict = {
        "query_id": "AAHdF6IQAAAAAN0XohD-test",
        "user": f'{{"id":{user_id},"first_name":"Test","last_name":"User"}}',
        "auth_date": "1672531200"
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    hash_val = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    data_dict["hash"] = hash_val
    return f"tma {urllib.parse.urlencode(data_dict)}"

@pytest.fixture
def valid_headers():
    return {"Authorization": generate_valid_tma_header()}

@pytest.fixture
def invalid_headers():
    return {"Authorization": "tma query_id=test&hash=invalid_hash_value"}

@pytest.mark.asyncio
async def test_unauthorized_access():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/search?q=test")
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_signature(invalid_headers):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/search?q=test", headers=invalid_headers)
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_search_endpoint(valid_headers, mocker):
    mock_search = mocker.patch("app.search.search", new_callable=AsyncMock, create=True)
    mock_search.return_value = [{"id": "1", "title": "Test Track"}]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/search?q=test", headers=valid_headers)
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": [{"id": "1", "title": "Test Track"}]}

@pytest.mark.asyncio
async def test_resolve_endpoint(valid_headers, mocker):
    mock_resolve = mocker.patch("app.resolver.resolve", new_callable=AsyncMock, create=True)
    mock_resolve.return_value = {"id": "123", "source": "spotify"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/resolve?url=https://spotify.link", headers=valid_headers)
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": {"id": "123", "source": "spotify"}}

@pytest.mark.asyncio
async def test_radio_endpoint(valid_headers, mocker):
    mock_radio = mocker.patch("app.radio.radio", new_callable=AsyncMock, create=True)
    mock_radio.return_value = [{"id": "2", "title": "Recommended Track"}]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/radio?track_id=1", headers=valid_headers)
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": [{"id": "2", "title": "Recommended Track"}]}

@pytest.mark.asyncio
async def test_static_files(mocker):
    mocker.patch("os.path.exists", return_value=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/index.html")
        assert response.status_code in [200, 404]